import re
import pandas as pd
from typing import Iterable, Optional

STREET_ABBREVIATIONS = {
    # TODO: Confirm and expand
    "avenue": "Ave", "street": "St", "boulevard": "Blvd", "place": "Pl",
    "road": "Rd", "drive": "Dr", "lane": "Ln", "court": "Ct", "terrace": "Ter",
    "parkway": "Pkwy", "highway": "Hwy"
}

# TODO: Refactor out
def normalize_streetname(streetname:str, verbose=False) -> str:
    cleaned_street_name = streetname.lower().strip()

    # TODO -> fix abbreviations, maybe remove boundaries
    
    # Remove numeric ordinal suffixes
    cleaned_street_name = re.sub(r'\b(\d+)(st|nd|rd|th)\b', r'\1', cleaned_street_name)
    
    if verbose:
        print('Converted "{street_name}" to "{cleaned_street_name}"')

    return cleaned_street_name

# other normalize street
    if not streetname:
        return streetname
    n = streetname.strip()
    n = " ".join(w if w.isupper() else w.capitalize() for w in n.split())
    lower = n.lower().split()
    if lower and lower[-1] in STREET_ABBREVIATIONS:
        lower[-1] = STREET_ABBREVIATIONS[lower[-1]]
        n = " ".join(w.capitalize() if i != len(lower)-1 else lower[-1]
                    for i, w in enumerate(n.split()))
    return n

def match_streetname(query_name:str, ref_names:pd.Series, ref_ids:Optional[pd.Series]=None) -> pd.Series: # TODO: Iterable
    # normalize streetnames
    normalized_query = normalize_streetname(query_name)
    normalized_ref = ref_names.apply(normalize_streetname)

    # match them - # TODO: can replace with matching function of your choosing
    matched_mask = normalized_ref.str.match(normalized_query)

    if ref_ids is not None:
        assert ref_ids.shape[0] == ref_names.shape[0]
        return ref_ids[matched_mask].values
    else:
        return normalized_ref[matched_mask].index.values

def build_onelineaddress(
    streetnames:Iterable[str], *, city: str, state: str, zipcode: Optional[str] = None
) -> str:
    """
    Build the onelineaddress string the Census Geocoder expects for intersections.
    Either 'AND' or '&' works; 'AND' is explicit and reliable.
    """
    try:
        normalized_streetnames = [normalize_streetname(s) for s in streetnames]
        parts = [" AND ".join(normalized_streetnames), city, state]
        if zipcode:
            parts.append(str(zipcode))
        return ", ".join(p for p in parts if p)
    except Exception as e:
        print(f'{e} -- {streetnames}')
        return ''