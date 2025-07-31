import pandas as pd
from shapely import wkt

def safe_load_wkt(w):
    if pd.isna(w) or w == 'nan':
        return None
    try:
        return wkt.loads(w)
    except Exception:
        return None
