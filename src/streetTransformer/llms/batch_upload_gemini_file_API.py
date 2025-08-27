import argparse
import concurrent.futures as cf
import logging
import mimetypes
import os
import random
import sys
import time
import json
from dataclasses import dataclass
import pandas as pd
from pathlib import Path
from typing import Iterable, Optional, Sequence
from dotenv import load_dotenv
from tqdm.auto import tqdm  # pip install tqdm
from datetime import datetime

from google import genai
#from google.genai.types import UploadFileResponse  # type: ignore

load_dotenv()

# ---------- Configuration & types ----------

DEFAULT_EXTS: tuple[str, ...] = (".png",)
MAX_WORKERS_DEFAULT = 8
RETRY_ATTEMPTS_DEFAULT = 4
RETRY_BASE_DELAY = 0.6  # seconds (exponential backoff base)
RETRY_MAX_DELAY = 8.0

os.getenv('GEMINI_API_KEY')

@dataclass(frozen=True)
class UploadResult:
    """Outcome for a single path upload."""
    key: str
    path: str
    file_name:          Optional[str]          # server-side File.name or None on failure
    uri:                Optional[str]
    mime_type:          Optional[str]
    create_time:        Optional[datetime]
    expiration_time:    Optional[datetime]
    error:              Optional[BaseException]


#my fancy client singleton - curtuosy of HPI
_client_singleton: Optional[genai.Client] = None #fetch the same instance instead of creating a new one everytime!

def get_client() -> genai.Client:
    """Create or return the singleton Gemini client."""
    global _client_singleton
    if _client_singleton is None:
        #api_key = os.environ.get(API_KEY_ENV)
        # if not api_key:
        #     raise RuntimeError(
        #         f"missing API key. Set {API_KEY_ENV}=<key> in your environment."
        #     )
        _client_singleton = genai.Client()
    return _client_singleton


def discover_files(
        root: Path,
        exts: Sequence[str]
) -> list[Path]:

    exts_lc = {e.lower() for e in exts}
    return [p
            for p in root.rglob("*")
            if p.is_file()
            and
            p.suffix.lower() in exts_lc
            ]


def _guess_mime(path: Path) -> str:
    """
    Guess MIME type; fall back to 'application/octet-stream'.
    """
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def upload_file(path: Path):
    """
    Upload one file to the Gemini Files API and return its File resource.
    Raises on failure.
    """
    client = get_client()
    #mime = _guess_mime(path)
    mime = 'image/png'
    with path.open("rb") as fh:
        return client.files.upload(
            file=fh,
            config={"display_name": _file_key(path), "mime_type": mime}
        )
    
def _file_key(path:Path):
    return str(Path(*path.parts[-4:])).replace('.png','')


def _is_transient(err: BaseException) -> bool:
    """
    Co-Pilot generated doctstring
    Heuristic: treat most network/HTTP/service errors as transient.
    The SDK may raise different exception types; keep broad, but allow fast-fail
    on obvious non-retryables (e.g., FileNotFoundError, PermissionError).
    """
    if isinstance(err, (FileNotFoundError, PermissionError, IsADirectoryError)):
        return False
    # If you later identify specific SDK exception classes (rate limits, 5xx), (not very familiar myself)
    # add them here
    return True


def upload_file_with_retry(path: Path, attempts: int) -> UploadResult:
    """
    Upload with bounded retries and exponential backoff + jitter.
    Returns UploadResult (never raises).
    """
    attempt = 0
    while True:
        try:
            resp = upload_file(path)
            fid = getattr(resp, "name", None)
            return UploadResult(key=_file_key(path), path=str(path), file_name=fid, error=None, uri=resp.uri, mime_type=resp.mime_type, create_time=resp.create_time, expiration_time=resp.expiration_time)
        except BaseException as e:  # you can use _is_transient
            attempt += 1
            if attempt >= attempts or not _is_transient(e):
                return UploadResult(key=_file_key(path), path=str(path), file_name=None, error=None, uri=None, mime_type=None, create_time=None, expiration_time=None)
                

            delay = min(RETRY_MAX_DELAY, RETRY_BASE_DELAY * (2 ** (attempt - 1)))
            delay *= 1 + random.random() * 0.25  # +0–25% jitter
            logging.warning("Retrying %s (attempt %d/%d) after error: %r; sleep=%.2fs",
                            path, attempt, attempts, e, delay)
            time.sleep(delay)



def bulk_upload(
    paths: Iterable[Path],
    max_workers: int = MAX_WORKERS_DEFAULT,
    retry_attempts: int = RETRY_ATTEMPTS_DEFAULT,
    outfile: Optional[Path] = None,
    show_progress:bool = True
) -> list[UploadResult]:

    files = list(paths)
    if not files:
        return []

    results: list[UploadResult] = []

    max_workers = max(1, min(max_workers, len(files))) #bounding the pool


    # Ensure output file exists if requested
    if outfile:
        outfile.parent.mkdir(parents=True, exist_ok=True)
        f = outfile.open("a", encoding="utf-8")
    else:
        f = None
    
    try:
        with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(upload_file_with_retry, p, retry_attempts): p for p in files}

            pbar = tqdm(total=len(files), unit="file", desc="Uploading", disable=not show_progress)

            for fut in cf.as_completed(futures):
                res = fut.result()
                results.append(res)
                if f:
                    # serialize to JSON (make sure UploadResult is JSON serializable or convert to dict)
                    json.dump(
                        res if isinstance(res, dict) else res.__dict__,
                        f,
                        ensure_ascii=False,
                        default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o),
                    )
                    f.write("\n")    
                pbar.update(1)

            pbar.close()
    finally:
        if f:
            f.close()
    
    return results

def bulk_upload(
    paths: Iterable[Path],
    max_workers: int = MAX_WORKERS_DEFAULT,
    retry_attempts: int = RETRY_ATTEMPTS_DEFAULT,
    outfile: Optional[Path] = None,
    show_progress: bool = True,
    flush_every: int = 0,  # 0 = only on close; set N to flush every N writes
) -> list[UploadResult]:

    files = list(paths)
    if not files:
        return []

    results: list[UploadResult] = []
    max_workers = max(1, min(max_workers, len(files)))

    f = None
    if outfile:
        outfile.parent.mkdir(parents=True, exist_ok=True)
        f = outfile.open("a", encoding="utf-8")

    wrote_since_flush = 0

    try:
        with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(upload_file_with_retry, p, retry_attempts): p for p in files}

            iterator = cf.as_completed(futures)
            if show_progress:
                iterator = tqdm(iterator, total=len(futures), unit="file", desc=f"Uploading. Writing to {outfile}")

            for fut in iterator:
                res = fut.result()
                results.append(res)

                if f:
                    json.dump(
                        res if isinstance(res, dict) else res.__dict__,
                        f,
                        ensure_ascii=False,
                        default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o),
                    )
                    f.write("\n")

                    if flush_every:
                        wrote_since_flush += 1
                        if wrote_since_flush >= flush_every:
                            f.flush()
                            wrote_since_flush = 0
    finally:
        if f:
            f.flush()
            f.close()

    return results

# Copilot
def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="bulk upload images to Gemini Files API.")
    parser.add_argument("folder", type=Path, help="root folder to scan (recursively).")
    parser.add_argument('-o', "--outfile", type=Path, help="file_path to write responses to.")
    parser.add_argument(
        "--ext", dest="exts", action="append",
        help=f"file extension to include (repeatable). Default: {', '.join(DEFAULT_EXTS)}",
    )
    parser.add_argument("--workers", type=int, default=MAX_WORKERS_DEFAULT,
                    help=f"max parallel uploads (default: {MAX_WORKERS_DEFAULT}).")
    parser.add_argument("--retries", type=int, default=RETRY_ATTEMPTS_DEFAULT,
                    help=f"retry attempts per file (default: {RETRY_ATTEMPTS_DEFAULT}).")
    parser.add_argument("--quiet", action="store_true", help="Less verbose logging.")
    return parser.parse_args(argv)


def setup_logging(quiet: bool) -> None:
    level = logging.WARNING if quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

EXPORT_COLUMNS = ['location_id', 'year', 'universe', 'path', 'file_name', 'uri', 'mime_type','create_time','expiration_time'] 
def read_image_paths_df(path_ndjson:Path|str, base_path:Path|str=Path('.'), outfile:Optional[Path|str]=None):
    path_ndjson = Path(path_ndjson)
    base_path = Path(base_path)
    outfile = Path(outfile) if outfile else None

    inpath = base_path / path_ndjson
    with open(inpath,'r') as f:
        l = f.readlines()
        jsons = [json.loads(li) for li in l]

    image_locations_df =pd.DataFrame(jsons)
    upload_errors = image_locations_df[image_locations_df['error'].notna()].shape[0] # confirm
    if upload_errors > 0:
        print('Upload Errors: {upload_errors}')

    image_locations_df[['universe', 'imagery','year','location_id']] = image_locations_df['key'].str.split('/', expand=True)
    ret_df = image_locations_df[EXPORT_COLUMNS]

    if outfile:
        outfile.mkdir(parents=True, exist_ok=True)
        ret_df.to_csv(outfile, index=False)

    return ret_df


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    setup_logging(args.quiet)

    exts = tuple(e.lower() if e.startswith(".") else f".{e.lower()}"
                 for e in (args.exts or DEFAULT_EXTS))

    root: Path = args.folder
    if not root.exists():
        logging.error("Folder does not exist: %s", root)
        return 2

    files = discover_files(root, exts)
    if not files:
        logging.warning("No files found under %s matching %s", root, exts)
        return 0

    t0 = time.perf_counter()
    results = bulk_upload(files, max_workers=args.workers, retry_attempts=args.retries, outfile=args.outfile)
    dt = time.perf_counter() - t0


    ok = 0
    for r in results:
        if r.file_name:
            ok += 1
            print(f"{r.path} -> {r.file_name}")
        else:
            print(f"{r.path} -> ERROR: {r.error!r}")


    total = len(results)
    print(f"\nSummary: {ok}/{total} succeeded in {dt:.2f}s "
          f"({(ok/dt) if dt > 0 else 0:.2f} files/s).")

    return 0 if ok == total else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)