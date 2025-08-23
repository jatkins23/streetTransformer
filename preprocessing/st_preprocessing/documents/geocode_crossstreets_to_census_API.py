import os, sys
import time
import json
import math
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json

import pandas as pd
import geopandas as gpd
import xyzservices.providers as xyz
from pandas.api.types import is_string_dtype, is_object_dtype

from streettransformer.utils.geocode_crossstreets import geocode_intersection
from align_docs_and_projects import pipeline, DOCUMENTS_PROCESSED_PATH


# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
CACHE_PATH = Path("geocode_cache.jsonl")   # append-only JSONL cache (resilient & simple)
MAX_WORKERS = 16                           # tune for your API; IO-bound → higher is fine
MAX_RETRIES = 4
BASE_DELAY = 0.5                           # seconds (exponential backoff)
RATE_LIMIT_PER_SEC = None                  # e.g., 5 if your API allows ~5 RPS; None to disable

# ------------------------------------------------------------------------------
# Helpers: normalization & cache
# ------------------------------------------------------------------------------
def _normalize_key(s: str) -> str:
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return ""
    s = str(s)
    return " ".join(s.lower().strip().replace("&", "and").split())

def _load_cache(path: Path) -> dict:
    cache = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    cache[rec["key"]] = rec["value"]
                except Exception:
                    continue
    return cache

_cache_lock = threading.Lock()  # protect file appends
def _append_cache(path: Path, key: str, value):
    with _cache_lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")

# ------------------------------------------------------------------------------
# Optional: very light rate limiter (token bucket-ish)
# ------------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, rps: float | None):
        self.rps = rps
        self.lock = threading.Lock()
        self.next_time = 0.0

    def acquire(self):
        if not self.rps:
            return
        with self.lock:
            now = time.perf_counter()
            wait_until = max(self.next_time, now)
            delay = wait_until - now
            if delay > 0:
                time.sleep(delay)
            # schedule next slot
            self.next_time = max(wait_until, time.perf_counter()) + 1.0 / self.rps

rate_limiter = RateLimiter(RATE_LIMIT_PER_SEC)

# ------------------------------------------------------------------------------
# Threaded fetch with retries/backoff
# ------------------------------------------------------------------------------
def _fetch_one(key: str, user_fn) -> tuple[str, object]:
    """
    key: normalized cross-street string
    user_fn: your geocoding callable, e.g. geocode_intersection(raw_string)
    returns (key, result)
    """
    # We call user_fn with the *original* phrase (not normalized), but we only store under `key`.
    # If you rely on normalization inside your API, pass `key` instead.
    attempt = 0
    last_exc = None
    while attempt <= MAX_RETRIES:
        try:
            rate_limiter.acquire()
            result = user_fn(key)  # or pass the *original* if you prefer
            return key, result
        except Exception as e:
            last_exc = e
            delay = BASE_DELAY * (2 ** attempt) + (0.1 * os.getpid() % 0.1)  # jitter
            time.sleep(delay)
            attempt += 1
    # Out of retries
    return key, {"error": str(last_exc)}

# ------------------------------------------------------------------------------
# Public function: vectorized, cached, multithreaded geocoding
# ------------------------------------------------------------------------------
def geocode_cross_streets_column(df: pd.DataFrame,
                                 col: str,
                                 geocode_fn,
                                 cache_path: Path = CACHE_PATH,
                                 max_workers: int = MAX_WORKERS) -> pd.Series:
    # Validate column
    if col not in df.columns:
        raise KeyError(f"Column '{col}' not in DataFrame")
    if not (is_string_dtype(df[col]) or is_object_dtype(df[col])):
        # we’ll still coerce to string; warn if you like
        pass

    # Normalize & collect unique keys
    norm_series = df[col].map(_normalize_key)
    unique_keys = pd.unique(norm_series.fillna(""))

    # Load cache
    cache = _load_cache(cache_path)

    # Figure out which keys we still need to fetch (exclude null/empty)
    to_fetch = [k for k in unique_keys if k and k not in cache]

    # Fan out
    if to_fetch:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_fetch_one, k, geocode_fn): k for k in to_fetch}
            for fut in tqdm(as_completed(futures), total=len(futures), desc="Geocoding"):
                k, val = fut.result()
                cache[k] = val
                _append_cache(cache_path, k, val)

    # Map back to the original rows
    out = norm_series.map(lambda k: cache.get(k, None))

    return out

# ------------------------------------------------------------------------------
# Example usage in your case:
# ------------------------------------------------------------------------------
# geocoded_documents['geocoded_query_result'] = geocode_cross_streets_column(
#     geocoded_documents,
#     col='cross_streets',
#     geocode_fn=geocode_intersection,  # your existing function
#     cache_path=Path("geocode_cache.jsonl"),
#     max_workers=16
# )

def display_map(gdf:gpd.GeoDataFrame, input_tiles=xyz.CartoDB.Positron):
     m = gdf.explore(tiles=input_tiles)
     return m

def load_gemini_geocoded_files(path: str) -> pd.DataFrame:
    """
    Flatten NDJSON lines like:
      {"id": 841, "text": "[{...}, {...}]"}
    into a DataFrame with one row per item in the 'text' array.
    
    Handles null or empty 'text' fields safely.
    """
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {line_no} is not valid JSON: {e}") from e

            doc_id = obj.get("id")
            text_field: Union[str, None] = obj.get("text")

            # Skip if text is None or empty
            if not text_field:
                continue

            try:
                items = json.loads(text_field)
            except json.JSONDecodeError:
                # If not valid JSON array, skip
                continue

            if not isinstance(items, list):
                continue

            for item in items:
                cross_streets = item.get("cross_streets", [])
                coords = item.get("coordinates", [None, None])
                lat = coords[0] if isinstance(coords, (list, tuple)) and len(coords) >= 2 else None
                lng = coords[1] if isinstance(coords, (list, tuple)) and len(coords) >= 2 else None

                rows.append({
                    "document_id": doc_id,
                    "page_found": item.get("page_found"),
                    "confidence": item.get("confidence"),
                    "lat": lat,
                    "lng": lng,
                    "cross_streets": cross_streets,
                    "cross_streets_str": "; ".join(map(str, cross_streets)) if cross_streets else None,
                })

    return pd.DataFrame(rows)

if __name__ == '__main__':
    geocoded_documents = load_gemini_geocoded_files(DOCUMENTS_PROCESSED_PATH / 'gemini_output2.ndjson')
    # geocoded_query_result = geocode_cross_streets_column(
    #     geocoded_documents.head(10), 
    #     'cross_streets',
    #     geocode_fn=geocode_intersection
    # )
    geocoded_query_result = {}
    geocoded_documents = geocoded_documents
    
    with open('data/project_documents/geocoded_gemini_to_census.csv', 'w+') as f:
        for row in tqdm(geocoded_documents.itertuples(index=True), total=len(geocoded_documents)):
            result = geocode_intersection(row.cross_streets)

            geocoded_query_result[row.Index] = result
            result_json = json.dumps(result)
            f.write(f'{row.document_id}, {result_json}\n')

        print(pd.DataFrame(result))
