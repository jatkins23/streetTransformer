import pandas as pd
from shapely import wkt

def safe_load_wkt(w):
    if pd.isna(w) or w == 'nan':
        return None
    try:
        return wkt.loads(w)
    except Exception:
        return None

def normalize_coord(coord):
    """
    Normalize different coordinate representations into (x, y) = (lon, lat).
    """
    if coord is None:
        raise ValueError("Coordinate is None.")

    # Case 1: Tuple or list
    if isinstance(coord, (tuple, list)) and len(coord) == 2:
        return float(coord[0]), float(coord[1])

    # Case 2: Dict with lat/lng keys
    if isinstance(coord, dict):
        if "lng" in coord and "lat" in coord:
            return float(coord["lng"]), float(coord["lat"])
        if "longitude" in coord and "latitude" in coord:
            return float(coord["longitude"]), float(coord["latitude"])
        if "coordinates" in coord and isinstance(coord["coordinates"], (list, tuple)):
            return float(coord["coordinates"][0]), float(coord["coordinates"][1])

    # Case 3: GeoJSON Point
    if isinstance(coord, dict) and coord.get("type") == "Point":
        coords = coord.get("coordinates", [])
        if len(coords) == 2:
            return float(coords[0]), float(coords[1])

    # Case 4: String "lat,lon" or "lon,lat"
    if isinstance(coord, str):
        parts = coord.split(",")
        if len(parts) == 2:
            return float(parts[0].strip()), float(parts[1].strip())

    raise ValueError(f"Unsupported coordinate format: {coord}")
