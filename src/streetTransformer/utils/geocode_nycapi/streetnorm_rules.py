from __future__ import annotations
import re
from typing import Dict

_ALIAS_WORDS = {
    r"\bEXPWY\b": "EXPRESSWAY",
    r"\bEXPY\b": "EXPRESSWAY",
    r"\bPKWY\b": "PARKWAY",
    r"\bPLZ\b": "PLAZA",
    r"\bBRG\b": "BRIDGE",
    r"\bSQ\b": "SQUARE",
}

_SPECIFIC: Dict[str, str] = {
    "FDR DR": "FRANKLIN D ROOSEVELT DRIVE",
    "QUEENS PLAZA S": "QUEENS PLAZA SOUTH",
    "QUEENS PLAZA N": "QUEENS PLAZA NORTH",
    "CT SQUARE WEST": "COURT SQUARE WEST",
    "ST JAMES PL": "SAINT JAMES PLACE",
    "ST MARKS AVE": "SAINT MARKS AVE",
}

def alias_callable(
):
    compiled = [(re.compile(pat, re.I), rep) for pat, rep in _ALIAS_WORDS.items()]
    def _fn(
        s: str,
    ) -> str:
        t = s
        for cre, rep in compiled:
            t = cre.sub(rep, t)
        return _SPECIFIC.get(t, t)
    return _fn

EXTRA_ALIAS = alias_callable()