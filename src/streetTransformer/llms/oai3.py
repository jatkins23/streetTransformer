from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable, Sequence, Optional, Dict, Any
import base64, json, os, time, concurrent.futures as cf
from tqdm import tqdm
from dotenv import load_dotenv
from contextlib import contextmanager
import random
import threading

load_dotenv()
os.getenv('OPENAI_API_KEY') 

# pip install openai>=1.44.0 pymupdf pillow pandas tqdm
from openai import OpenAI, APIStatusError, APITimeoutError, RateLimitError
from PIL import Image
import fitz  # PyMuPDF
from ..config.constants import DATA_PATH

from .models.queries import QUERIES, Query

# -----------------------------
# Config
# -----------------------------
DEFAULT_MODEL = "gpt-4o-mini"  # fast vision-capable; swap as needed
MAX_WORKERS_DEFAULT = 8
MAX_RETRIES = 5
TIMEOUT_S = 120
MAX_FILES_PER_ITEM = 5         # hard cap to protect tokens
PDF_PAGES_PER_FILE = 10         # render first N pages per PDF: 0 = all
PDF_DPI_SCALE = 2.0

class RateLimiter:
    """
    Simple global rate limiter across threads:
    - rps: target requests per second (min interval between starts)
    - max_concurrent: cap on simultaneous in-flight requests (helps 429s)
    """
    def __init__(self, rps: float = 2.0, max_concurrent: int = 2):
        self.min_interval = 1.0 / max(1e-6, float(rps))
        self._lock = threading.Lock()
        self._next_allowed = 0.0
        self._sem = threading.Semaphore(max(1, int(max_concurrent)))

    @contextmanager
    def slot(self):
        # Concurrency gate first
        self._sem.acquire()
        try:
            # Spacing between request starts
            with self._lock:
                now = time.monotonic()
                wait = max(0.0, self._next_allowed - now)
                if wait:
                    time.sleep(wait)
                # Reserve the next slot time
                start = time.monotonic()
                self._next_allowed = max(start, self._next_allowed) + self.min_interval
            yield
        finally:
            self._sem.release()

# -----------------------------
# Data structures
# -----------------------------
@dataclass(frozen=True)
class WorkItem:
    item_id: str
    prompt: str
    json_schema: dict
    files: list[tuple[str, Path]] = ()   # now store (label, path)

# -----------------------------
# Image helpers
# -----------------------------
def pil_to_base64_png(img: Image.Image, max_side: int = 1600, quality_hint: int = 85) -> str:
    """
    Downscale to control tokens (vision models see fewer pixels → fewer tokens).
    Returns base64 data URL (PNG).
    """
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # PNG: lossless; if you want smaller payloads, switch to JPEG via img.convert("RGB") + format="JPEG".
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)  # lossless; simple default
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def render_pdf_pages_to_images(pdf_path: Path, pages: int = PDF_PAGES_PER_FILE) -> list[Image.Image]:
    """
    Render first `pages` of a PDF to PIL images.
    """
    images: list[Image.Image] = []
    with fitz.open(pdf_path) as doc:
        count = min(len(doc), pages)
        for i in range(count):
            page = doc.load_page(i)
            # 144 dpi-ish matrix (2x zoom) is usually ample for vision
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
    return images

def load_file_as_images(path: Path) -> list[Image.Image]:
    if path.suffix.lower() == ".png":
        return [Image.open(path)]
    if path.suffix.lower() == ".pdf":
        return render_pdf_pages_to_images(path, pages=PDF_PAGES_PER_FILE)
    raise ValueError(f"Unsupported file type: {path}")

# -----------------------------
# OpenAI call
# -----------------------------
def build_messages(prompt: str, files: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    """
    Build Chat Completions 'messages' with a user message that contains the text prompt
    plus up to MAX_FILES_PER_ITEM image parts derived from PNGs or rendered PDFs.
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

    selected = files[:MAX_FILES_PER_ITEM]
    for label, p in selected:
        imgs = load_file_as_images(p)
        if not imgs:
            continue
        img = imgs[0]
        data_url = pil_to_base64_png(img)
        content.append({
            "type": "text", 
            "text": f"Label: {label}"   # add label inline
        })
        content.append({
            "type": "image_url",
            "image_url": {"url": data_url, "detail": "high"}
        })

    return [{"role": "user", "content": content}]

class RateLimiter:
    """
    Simple global rate limiter across threads:
    - rps: target requests per second (min interval between starts)
    - max_concurrent: cap on simultaneous in-flight requests (helps 429s)
    """
    def __init__(self, rps: float = 2.0, max_concurrent: int = 2):
        self.min_interval = 1.0 / max(1e-6, float(rps))
        self._lock = threading.Lock()
        self._next_allowed = 0.0
        self._sem = threading.Semaphore(max(1, int(max_concurrent)))

    @contextmanager
    def slot(self):
        # Concurrency gate first
        self._sem.acquire()
        try:
            # Spacing between request starts
            with self._lock:
                now = time.monotonic()
                wait = max(0.0, self._next_allowed - now)
                if wait:
                    time.sleep(wait)
                # Reserve the next slot time
                start = time.monotonic()
                self._next_allowed = max(start, self._next_allowed) + self.min_interval
            yield
        finally:
            self._sem.release()


def _parse_retry_after_seconds(err: Exception) -> Optional[float]:
    """
    Try to parse Retry-After from OpenAI errors if present.
    """
    # openai>=1.0 errors often have .response with headers
    retry_after = None
    try:
        resp = getattr(err, "response", None)
        if resp is not None:
            # Try header
            ra = None
            try:
                ra = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
            except Exception:
                ra = None
            if ra:
                try:
                    retry_after = float(ra)
                except ValueError:
                    # Sometimes Retry-After can be a date; ignore for simplicity
                    retry_after = None
    except Exception:
        pass
    return retry_after

def safe_chat_with_retries(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    output_schema: dict,
    limiter: Optional[RateLimiter] = None,
) -> dict[str, Any]:
    """
    Makes the chat call with:
      - global rate limiter slots
      - retries on RateLimit / timeouts / transient server errors
      - honors Retry-After when available
    """
    base_delay = 1.0
    delay = base_delay

    for attempt in range(1, MAX_RETRIES + 1):
        # Acquire a rate-limit slot for *this* attempt
        if limiter is not None:
            with limiter.slot():
                try:
                    return client.chat.completions.create(
                        model=model,
                        messages=messages,
                        timeout=TIMEOUT_S,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {"name": "output_name", "schema": output_schema[1]},
                        },
                    ).to_dict()
                except (RateLimitError, APITimeoutError, APIStatusError) as e:
                    # On last attempt, bubble it up
                    if attempt == MAX_RETRIES:
                        raise

                    # Prefer server guidance if present
                    ra = _parse_retry_after_seconds(e)
                    # Exponential backoff with jitter
                    sleep_s = ra if ra is not None else delay + random.uniform(0, 0.4 * delay)
                    time.sleep(min(60.0, sleep_s))
                    delay = min(30.0, delay * 1.8)
        else:
            # No limiter provided (shouldn't happen in bulk, but keep parity)
            try:
                return client.chat.completions.create(
                    model=model,
                    messages=messages,
                    timeout=TIMEOUT_S,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": "output_name", "schema": output_schema[1]},
                    },
                ).to_dict()
            except (RateLimitError, APITimeoutError, APIStatusError) as e:
                if attempt == MAX_RETRIES:
                    raise
                ra = _parse_retry_after_seconds(e)
                sleep_s = ra if ra is not None else delay + random.uniform(0, 0.4 * delay)
                time.sleep(min(60.0, sleep_s))
                delay = min(30.0, delay * 1.8)


def extract_json(resp: dict[str, Any]) -> dict[str, Any]:
    raw = resp["choices"][0]["message"]["content"]
    return json.loads(raw)

def process_item(client: OpenAI, model: str, w: WorkItem, limiter: Optional[RateLimiter] = None) -> dict[str, Any]:
    messages = build_messages(w.prompt, w.files)
    resp = safe_chat_with_retries(client, model, messages, w.json_schema, limiter=limiter)
    return {
        "item_id": w.item_id,
        "model": model,
        "output_text": extract_json(resp),
        "raw_response": resp,
    }


# -----------------------------
# Runner
# -----------------------------
def run_bulk(
    items: Iterable[WorkItem],
    out_ndjson: Path,
    model: str = DEFAULT_MODEL,
    max_workers: int = MAX_WORKERS_DEFAULT,
    query_name: str = '',
    rps: float = 2.0,
    max_inflight: int = 2,
) -> None:
    out_ndjson.parent.mkdir(parents=True, exist_ok=True)

    done_ids: set[str] = set()
    if out_ndjson.exists():
        with out_ndjson.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if "item_id" in rec:
                        done_ids.add(str(rec["item_id"]))
                except json.JSONDecodeError:
                    pass

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    work = [w for w in items if w.item_id not in done_ids]
    if not work:
        print("Nothing to do; everything is already processed.")
        return

    lock = threading.Lock()

    def write_record(rec: Dict[str, Any]):
        line = json.dumps(rec, ensure_ascii=False)
        with lock:
            with out_ndjson.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    limiter = RateLimiter(rps=rps, max_concurrent=max_inflight)

    # Keep thread pool reasonable vs inflight cap
    pool_workers = min(max_workers, max_inflight * 2)

    with cf.ThreadPoolExecutor(max_workers=pool_workers) as ex:
        futures = {ex.submit(process_item, client, model, w, limiter): w for w in work}
        for fut in tqdm(cf.as_completed(futures), total=len(work), desc=f"Processing {query_name}"):
            w = futures[fut]
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"item_id": w.item_id, "error": str(e)}
            write_record(rec)

def bulk_query_on_df(
    query: Query,
    df: pd.DataFrame,
    outfile: Path,
    model: str = DEFAULT_MODEL,
    max_workers: int = MAX_WORKERS_DEFAULT,
    pdf_pages_per_file: int = PDF_PAGES_PER_FILE,
    pbar: bool = True,
    rps: float = 2.0,
    max_inflight: int = 2,
):
    items: list[WorkItem] = []
    for row in df.itertuples(index=False):
        files: list[tuple[str, Path]] = []
        if hasattr(row, "file_labels") and isinstance(row.file_labels, str) and row.file_labels.strip():
            for pair in str(row.file_labels).split(";"):
                if ":" not in pair:
                    continue
                label, path_str = pair.split(":", 1)
                p = Path(path_str.strip())
                if p.exists() and p.suffix.lower() in (".png", ".pdf"):
                    files.append((label.strip(), p))
                else:
                    p2 = DATA_PATH / p
                    if p2.exists() and p2.suffix.lower() in (".png", ".pdf"):
                        files.append((label.strip(), p2))
            if len(files) == 0:
                raise ValueError("Files not found! Check paths")

        items.append(
            WorkItem(
                item_id=str(row.item_id),
                prompt=query.text(),
                files=files,
                json_schema=query.output_schema.json_schema()["allOf"],
            )
        )

    run_bulk(
        items,
        out_ndjson=outfile,
        model=model,
        max_workers=max_workers,
        query_name=query.name,
        rps=rps,
        max_inflight=max_inflight,
    )


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    import argparse, pandas as pd

    p = argparse.ArgumentParser(description="Bulk ChatGPT vision calls over PNG/PDF files.")
    p.add_argument("-m", "--model", default=DEFAULT_MODEL)
    p.add_argument("-q", "--query", default='image_change_identifier')
    p.add_argument("-i", "--input", type=Path, required=True,
                   help="CSV with columns: item_id,prompt,file_paths (semicolon-separated, each .png or .pdf).")
    p.add_argument("-o", "--out", type=Path, required=True, help="Output NDJSON path.")
    p.add_argument("-w", "--max-workers", type=int, default=MAX_WORKERS_DEFAULT)
    p.add_argument("--pdf-pages-per-file", type=int, default=PDF_PAGES_PER_FILE,
                   help="How many pages to render per PDF (default 1). Still capped by total files per item.")
    p.add_argument("--rps", type=float, default=2.0, help="Target requests per second (global).")
    p.add_argument("--max-inflight", type=int, default=2, help="Max simultaneous in-flight API calls.")
    args = p.parse_args()

    df = pd.read_csv(args.input)
    # Reconcile query
    try:
        query = QUERIES[args.query]
        
    except Exception as e:
        print(f'{args.query} not found in QUERIES!\n\tOptions are {", ".join(QUERIES.keys())}')
        raise e
    
    pdf_pages_per_file = max(1, args.pdf_pages_per_file)

    bulk_query_on_df(
        query=query,
        df=df,
        model=args.model,
        outfile=args.out,
        max_workers=args.max_workers,
        pdf_pages_per_file=pdf_pages_per_file,
        rps=args.rps,
        max_inflight=args.max_inflight,
    )


    
    
    