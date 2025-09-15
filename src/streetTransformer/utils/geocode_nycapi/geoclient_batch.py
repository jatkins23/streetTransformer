# geoclient_batch.py
# NYC GeoClient batch intersection geocoder (APIM v2).
# - Input CSV columns: street1, street2, borough, unique_key
# - API key: env NYC_GEOCLIENT_SUBSCRIPTION_KEY or --key
# - Caches results to JSONL (append-only), keyed by unique_key

from __future__ import annotations

import os
import sys
import json
import csv
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import requests

try:
    from pyproj import Transformer
    _TR = Transformer.from_crs(2263, 4326, always_xy=True)
except Exception:
    _TR = None

from streetnorm import normalize_street_one

DEFAULT_BASE = "https://api.nyc.gov/geoclient/v2"
BOROS = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]
BORO_FIX = {
    "mn":"Manhattan","bx":"Bronx","bk":"Brooklyn","qn":"Queens","qns":"Queens","si":"Staten Island",
    "manhattan":"Manhattan","bronx":"Bronx","brooklyn":"Brooklyn","queens":"Queens","staten island":"Staten Island",
    "new york":"Manhattan","nyc":"Manhattan","kings":"Brooklyn","kings county":"Brooklyn",
    "richmond":"Staten Island","richmond county":"Staten Island",
}

class RateGate:
    def __init__(
        self,
        rps: float,
    ) -> None:
        if rps <= 0:
            raise ValueError("rps must be > 0")
        self.dt = 1.0 / float(rps)
        self.next_t = time.perf_counter()

    def wait(
        self,
    ) -> None:
        now = time.perf_counter()
        sleep_for = max(self.next_t - now, 0.0)
        if sleep_for > 0:
            time.sleep(sleep_for)
        self.next_t = max(self.next_t, time.perf_counter()) + self.dt

def norm_boro(
    b: Any,
) -> str:
    s = "" if b is None else str(b).strip().lower()
    return BORO_FIX.get(s, s.title() if s else "")

def boro_cycle(
    pref: str,
) -> list[str]:
    if not pref:
        return BOROS[:]
    return [pref] + [b for b in BOROS if b != pref]

def _nf(
    v: Any,
) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v,(int,float)):
            return float(v)
        s = str(v).strip()
        if not s or s.lower() == "nan":
            return None
        return float(s)
    except Exception:
        return None

def extract_coords(
    payload: Any,
) -> Tuple[Optional[float], Optional[float]]:
    stack = [payload]
    while stack:
        v = stack.pop()
        if isinstance(v, dict):
            lat = _nf(v.get("latitude")); lon = _nf(v.get("longitude"))
            if lat is not None and lon is not None:
                return lon, lat
            x = _nf(v.get("xCoordinate")); y = _nf(v.get("yCoordinate"))
            if x is not None and y is not None and _TR is not None:
                try:
                    lon2, lat2 = _TR.transform(x, y)
                    return float(lon2), float(lat2)
                except Exception:
                    pass
            stack.extend(v.values())
        elif isinstance(v, list):
            stack.extend(v)
    return None, None

def call(
    base: str,
    path: str,
    params: Dict[str, str],
    key: str,
    timeout: int,
) -> Tuple[Optional[Dict[str,Any]], Optional[str]]:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    q = dict(params)
    q.setdefault("subscription-key", key)
    headers = {"Ocp-Apim-Subscription-Key": key, "Accept": "application/json"}
    try:
        r = requests.get(url, params=q, headers=headers, timeout=timeout)
        if not r.ok:
            try:
                body = r.json()
            except Exception:
                body = r.text[:400]
            return None, f"HTTP {r.status_code}: {body}"
        try:
            return r.json(), None
        except Exception:
            return None, f"HTTP {r.status_code}: non-JSON"
    except Exception as e:
        return None, f"request_error: {e}"

def geocode_one(
    street1: str,
    street2: str,
    borough: str,
    *,
    base: str,
    key: str,
    timeout: int,
) -> Dict[str, Any]:
    s1 = normalize_street_one(street1)
    s2 = normalize_street_one(street2)
    for b in boro_cycle(norm_boro(borough)):
        for p in (
            {"crossStreetOne": s1, "crossStreetTwo": s2, "borough": b},
            {"streetName1": s1, "streetName2": s2, "borough": b},
        ):
            payload, err = call(base, "/intersection.json", p, key, timeout)
            if err:
                continue
            lon, lat = extract_coords(payload)
            if lon is not None:
                return {"ok": True, "lon": lon, "lat": lat, "src": "intersection", "params": p}
    qbase = f"{s1} and {s2}"
    for b in boro_cycle(norm_boro(borough)):
        payload, err = call(base, "/search.json", {"Input": f"{qbase}, {b}"}, key, timeout)
        if err:
            continue
        lon, lat = extract_coords(payload)
        if lon is not None:
            return {"ok": True, "lon": lon, "lat": lat, "src": "search", "query": f"{qbase}, {b}"}
    return {"ok": False, "src": "intersection+search"}

def load_cache(
    p: Path,
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    out[rec["key"]] = rec["value"]
                except Exception:
                    continue
    return out


def _append_audit_row(
    audit_path: Path,
    row: dict,
) -> None:
    exists = audit_path.exists()
    with audit_path.open("a", newline="", encoding="utf-8") as f:
        fieldnames = ["unique_key","street1","street2","borough","ok","src","lon","lat","error","params","query"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)

def append_cache(
    p: Path,
    key: str,
    value: dict,
) -> None:
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")

def geocode_csv(
    input_csv: Path,
    out_csv: Path,
    cache_path: Path,
    *,
    rps: float,
    timeout: int,
    retries: int,
    base: str,
    key: str,
    dry_run: bool = False,
    audit_csv: Path | None = None,
) -> None:
    df = pd.read_csv(input_csv)
    need = {"street1","street2","borough","unique_key"}
    miss = need - set(df.columns)
    if miss:
        sys.exit(f"Input missing columns: {sorted(miss)}")

    uniq = df[["unique_key","street1","street2","borough"]].drop_duplicates()
    mask = (
        uniq["unique_key"].notna()
        & (uniq["unique_key"]!="")
        & (uniq["street1"]!="")
        & (uniq["street2"]!="")
    )
    uniq = uniq.loc[mask]

    cache = load_cache(cache_path)
    todo = uniq[~uniq["unique_key"].isin(cache.keys())]

    if dry_run:
        print(f"pending_unique_calls={len(todo)}")
        return

    gate = RateGate(rps=rps)
    for row in todo.itertuples(index=False):
        attempt = 0
        while attempt <= retries:
            gate.wait()
            try:
                res = geocode_one(
                    street1 = row.street1,
                    street2 = row.street2,
                    borough = row.borough if isinstance(row.borough, str) else "",
                    base    = base,
                    key     = key,
                    timeout = timeout,
                )
                append_cache(cache_path, row.unique_key, res)
                if audit_csv is not None:
                    _append_audit_row(
                        audit_csv,
                        {
                            "unique_key": row.unique_key,
                            "street1": row.street1,
                            "street2": row.street2,
                            "borough": row.borough if isinstance(row.borough, str) else "",
                            "ok": res.get("ok"),
                            "src": res.get("src"),
                            "lon": res.get("lon"),
                            "lat": res.get("lat"),
                            "error": res.get("error"),
                            "params": json.dumps(res.get("params"), ensure_ascii=False) if isinstance(res.get("params"), dict) else "",
                            "query": res.get("query", ""),
                        },
                    )
                break
            except Exception as e:
                if attempt == retries:
                    err_res = {"ok": False, "src": "error", "error": str(e)}
                    append_cache(cache_path, row.unique_key, err_res)
                    if audit_csv is not None:
                        _append_audit_row(
                            audit_csv,
                            {
                                "unique_key": row.unique_key,
                                "street1": row.street1,
                                "street2": row.street2,
                                "borough": row.borough if isinstance(row.borough, str) else "",
                                "ok": err_res.get("ok"),
                                "src": err_res.get("src"),
                                "lon": "",
                                "lat": "",
                                "error": err_res.get("error"),
                                "params": "",
                                "query": "",
                            },
                        )
                    break
                time.sleep(0.6 * (2 ** attempt))
                attempt += 1

    cache = load_cache(cache_path)
    out = df.copy()
    out["geocode"] = out["unique_key"].map(cache.get)
    flat = pd.json_normalize(out["geocode"])
    out = pd.concat([out.drop(columns=["geocode"]).reset_index(drop=True), flat.reset_index(drop=True)], axis=1)
    out.to_csv(out_csv, index=False)

def main(
) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="NYC GeoClient v2 batch intersection geocoder")
    ap.add_argument("--input", required=True, help="CSV with street1, street2, borough, unique_key")
    ap.add_argument("--out", required=True, help="Output CSV")
    ap.add_argument("--cache", default="geocode_cache.jsonl")
    ap.add_argument("--rps", type=float, default=3.0)
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--base", default=os.getenv("NYC_GEOCLIENT_BASE", DEFAULT_BASE))
    ap.add_argument("--key", default=os.getenv("NYC_GEOCLIENT_SUBSCRIPTION_KEY",""))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--audit", default="", help="Optional CSV audit log of each API result/error")
    args = ap.parse_args()

    key = args.key or os.getenv("NYC_GEOCLIENT_SUBSCRIPTION_KEY","")
    if not key:
        sys.stderr.write("Missing API key. Set NYC_GEOCLIENT_SUBSCRIPTION_KEY or pass --key.\n")
        return 2

    geocode_csv(
        input_csv = Path(args.input),
        out_csv   = Path(args.out),
        cache_path= Path(args.cache),
        rps       = args.rps,
        timeout   = args.timeout,
        retries   = args.retries,
        base      = args.base,
        key       = key,
        dry_run   = args.dry_run,
        audit_csv = (Path(args.audit) if args.audit else None),
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())