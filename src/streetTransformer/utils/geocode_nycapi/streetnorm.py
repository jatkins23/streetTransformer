from __future__ import annotations
from typing import Any, Iterable
import re
import pandas as pd

_TYPE_CANON = {
    "AVENUE": "AVE",
    "STREET": "ST",
    "PLACE": "PL",
    "BOULEVARD": "BLVD",
    "ROAD": "RD",
    "COURT": "CT",
    "PARKWAY": "PKWY",
    "TERRACE": "TER",
    "LANE": "LN",
    "DRIVE": "DR",
}

_RE_ORD_ST   = re.compile(r"\b(\d+)\s+STREET\b", re.I)
_RE_ORD_AVE  = re.compile(r"\b(\d+)\s+AVENUE\b", re.I)
_RE_ORD_PL   = re.compile(r"\b(\d+)\s+PLACE\b", re.I)

def _canon_type(
    s: str,
) -> str:
    t = s
    for k, v in _TYPE_CANON.items():
        t = re.sub(rf"\b{k}\b", v, t, flags=re.I)
    return t

def normalize_street_one(
    s: Any,
    *,
    aggressive: bool = False,
    extra_alias = None,
) -> str:
    if s is None:
        return ""
    t = str(s).strip()
    t = _RE_ORD_ST.sub(r"\1 ST", t)
    t = _RE_ORD_AVE.sub(r"\1 AVE", t)
    t = _RE_ORD_PL.sub(r"\1 PL", t)
    t = _canon_type(t)
    t = re.sub(r"\s+", " ", t).strip().upper()
    if aggressive and callable(extra_alias):
        t = extra_alias(t)
    return t

def normalize_street_series(
    s: pd.Series,
    *,
    aggressive: bool = False,
    extra_alias = None,
) -> pd.Series:
    out = s.astype(str).str.strip()
    out = out.str.replace(r"\s+", " ", regex=True)
    out = out.str.replace(r"\b(\d+)\s+STREET\b", r"\1 ST", regex=True)
    out = out.str.replace(r"\b(\d+)\s+AVENUE\b", r"\1 AVE", regex=True)
    out = out.str.replace(r"\b(\d+)\s+PLACE\b", r"\1 PL", regex=True)
    for k, v in _TYPE_CANON.items():
        out = out.str.replace(rf"\b{k}\b", v, regex=True, case=False)
    out = out.str.upper()
    if aggressive and callable(extra_alias):
        out = out.map(extra_alias)
    return out

def canonical_intersection(
    parts: Iterable[str],
) -> tuple[str, str]:
    a, b = "", ""
    if parts:
        P = [p for p in parts if str(p).strip()]
        if len(P) >= 2:
            a, b = P[0], P[1]
    a = normalize_street_one(a)
    b = normalize_street_one(b)
    if a and b and a > b:
        a, b = b, a
    return a, b