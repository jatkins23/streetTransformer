# normalize_inputs_v2.py
# Build GeoClient-ready CSV from NDJSON and project->borough map.

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import json
import pandas as pd
from streetnorm import canonical_intersection, normalize_street_one

def norm_boro(
    s: str | None,
) -> str:
    t = (s or "").strip().lower()
    if t in {"mn","manhattan","new york","nyc"}:
        return "manhattan"
    if t in {"bx","bronx","the bronx"}:
        return "bronx"
    if t in {"bk","brooklyn","kings","kings county"}:
        return "brooklyn"
    if t in {"qn","qns","queens"}:
        return "queens"
    if t in {"si","staten island","richmond","richmond county"}:
        return "staten island"
    if t in {"citywide","multiple","all"}:
        return ""
    return ""

def run(
    ndjson_path: Path,
    docmap_csv: Path,
    out_csv: Path,
) -> None:
    dm = pd.read_csv(docmap_csv)
    proj_to_boro = dict(
        zip(
            dm["project_id"].astype(int),
            dm["borough"].map(norm_boro),
        )
    )

    rows = []
    with ndjson_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            pid = int(obj.get("id"))
            text = obj.get("text")
            if not text:
                continue
            try:
                items = json.loads(text)
            except Exception:
                continue
            if not isinstance(items, list):
                continue
            for item in items:
                cross = item.get("cross_streets", [])
                if isinstance(cross, list) and len(cross) >= 2:
                    s1, s2 = canonical_intersection(cross[:2])
                else:
                    s1, s2 = "", ""
                borough = proj_to_boro.get(pid, "")
                rows.append(
                    {
                        "project_id": pid,
                        "page_found": item.get("page_found"),
                        "confidence": item.get("confidence"),
                        "street1": s1,
                        "street2": s2,
                        "borough": borough,
                    }
                )

    df = pd.DataFrame(rows)
    key = (df["street1"] + "|" + df["street2"]).where(
        df["street1"] <= df["street2"],
        df["street2"] + "|" + df["street1"],
    )
    df["unique_key"] = key + "|" + df["borough"]
    df.to_csv(out_csv, index=False)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Normalize NDJSON + docmap to GeoClient-ready CSV")
    ap.add_argument("--ndjson", required=True)
    ap.add_argument("--docmap", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run(
        ndjson_path = Path(args.ndjson),
        docmap_csv  = Path(args.docmap),
        out_csv     = Path(args.out),
    )