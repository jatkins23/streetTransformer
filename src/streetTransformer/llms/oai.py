from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable, Sequence, Optional, Dict, Any
import base64, json, os, time, concurrent.futures as cf
from tqdm import tqdm
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()
os.getenv('OPENAI_API_KEY') 

# pip install openai>=1.44.0 pymupdf pillow pandas tqdm
from openai import OpenAI, APIStatusError, APITimeoutError, RateLimitError
from PIL import Image
import fitz  # PyMuPDF

from .models.queries import QUERIES, Query

# -----------------------------
# Config
# -----------------------------
DEFAULT_MODEL = "gpt-4o-mini"  # fast vision-capable; swap as needed
MAX_WORKERS_DEFAULT = 8
MAX_RETRIES = 5
TIMEOUT_S = 120
MAX_FILES_PER_ITEM = 5         # hard cap to protect tokens
PDF_PAGES_PER_FILE = 1         # render first N pages per PDF

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


def safe_chat_with_retries(client: OpenAI, model: str, messages: list[dict[str, Any]], output_schema:dict) -> dict[str, Any]:
    delay = 1.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=TIMEOUT_S,
                response_format={
                    "type": "json_schema",  # 👈 enforce JSON
                    'json_schema': {
                        'name': 'output_name',
                        'schema': output_schema[1]
                    }
                }
            ).to_dict()
        except (RateLimitError, APITimeoutError, APIStatusError) as e:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(delay)
            delay = min(30.0, delay * 1.8)

def extract_json(resp: dict[str, Any]) -> dict[str, Any]:
    raw = resp["choices"][0]["message"]["content"]
    return json.loads(raw)

def process_item(client: OpenAI, model: str, w: WorkItem) -> dict[str, Any]:
    messages = build_messages(w.prompt, w.files)
    resp = safe_chat_with_retries(client, model, messages, w.json_schema)
    return {
        "item_id": w.item_id,
        "model": model,
        "output_text": extract_json(resp),
        "raw_response": resp,  # keep for auditing
    }

# -----------------------------
# Runner
# -----------------------------
def run_bulk(
    items: Iterable[WorkItem],
    out_ndjson: Path,
    model: str = DEFAULT_MODEL,
    max_workers: int = MAX_WORKERS_DEFAULT,
) -> None:
    out_ndjson.parent.mkdir(parents=True, exist_ok=True)

    # Resumability: load prior IDs
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

    lock = cf.thread.Lock() if hasattr(cf, "thread") else None

    def write_record(rec: Dict[str, Any]):
        line = json.dumps(rec, ensure_ascii=False)
        if lock:
            with lock:
                with out_ndjson.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
        else:
            with out_ndjson.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(process_item, client, model, w): w for w in work}
        for fut in tqdm(cf.as_completed(futures), total=len(work), desc="Processing"):
            w = futures[fut]
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"item_id": w.item_id, "error": str(e)}
            write_record(rec)

def bulk_query_on_df(query: Query, df: pd.DataFrame, outfile:Path, model:str=DEFAULT_MODEL, max_workers:int=MAX_WORKERS_DEFAULT, pdf_pages_per_file:int=PDF_PAGES_PER_FILE, pbar:bool=True):
    # allow override for this run
    pprint(query.output_schema.json_schema()['allOf'])

    # In CLI section after reading df
    items: list[WorkItem] = []
    for row in df.itertuples(index=False):
        #print(row)
        files: list[tuple[str, Path]] = []
        if hasattr(row, "file_labels") and isinstance(row.file_labels, str) and row.file_labels.strip():
            for pair in str(row.file_labels).split(";"):
                if ":" not in pair:
                    continue
                label, path_str = pair.split(":", 1)
                p = Path(path_str.strip())
                if p.exists() and p.suffix.lower() in (".png", ".pdf"):
                    files.append((label.strip(), p))
        items.append(WorkItem(item_id=str(row.item_id), prompt=query.text(), files=files, json_schema=query.output_schema.json_schema()['allOf']))

    run_bulk(items, out_ndjson=outfile, model=model, max_workers=max_workers)


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    import argparse, pandas as pd

    p = argparse.ArgumentParser(description="Bulk ChatGPT vision calls over PNG/PDF files.")
    p.add_argument("-m", "--model", default=DEFAULT_MODEL)
    p.add_argument("-q", "--query", default='image_change_identifier')
    p.add_argument("--input", type=Path, required=True,
                   help="CSV with columns: item_id,prompt,file_paths (semicolon-separated, each .png or .pdf).")
    p.add_argument("--out", type=Path, required=True, help="Output NDJSON path.")
    p.add_argument("--max-workers", type=int, default=MAX_WORKERS_DEFAULT)
    p.add_argument("--pdf-pages-per-file", type=int, default=PDF_PAGES_PER_FILE,
                   help="How many pages to render per PDF (default 1). Still capped by total files per item.")
    args = p.parse_args()

    df = pd.read_csv(args.input)
    # Reconcile query
    try:
        query = QUERIES[args.query]
        
    except Exception as e:
        print(f'{args.query} not found in QUERIES!\n\tOptions are {", ".join(QUERIES.keys())}')
        raise e
    
    pdf_pages_per_file = max(1, args.pdf_pages_per_file)

    run_query_on_df(query=query, df=df, model=args.model, outfile=args.out, max_workers=args.max_workers, pdf_pages_per_file=pdf_pages_per_file)

    
    
    