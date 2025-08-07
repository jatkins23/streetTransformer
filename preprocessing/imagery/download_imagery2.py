# TODO: Generate a reference dataframe

# TODO: Improve speed:
# [ ] Can calculate tile locations only once for each location (all years)
# [ ] Can pull each tile-year only once (rather than multiple times per )
# [X] Remove iterrows (!important)n

import io
import math
import logging
from pathlib import Path
from typing import Tuple, Dict, Optional, List
from tqdm import tqdm


import requests
import mercantile
from PIL import Image
import geopandas as gpd
from shapely.geometry import Point

# -----------------------------------------------------------------------------
# Env variables
# -----------------------------------------------------------------------------

TILE_URL_TEMPLATE = (
    "https://tiles.arcgis.com/tiles/yG5s3afENB5iO9fj/arcgis/rest/"
    "services/NYC_Orthos_{year}/MapServer"
)

# -----------------------------------------------------------------------------
# Logger Setup
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s %(levelname)s] %(message)s")
    )
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------
def reproject_to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame: # TODO: necessary?
    """
    Ensure GeoDataFrame is in EPSG:4326 for mercantile.
    """
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        return gdf.to_crs(epsg=4326)
    return gdf


def get_center_tile(point: Point, zoom: int) -> Tuple[int, int]: # TODO: necessary?
    """
    Compute the central tile indices (x, y) for a given point at zoom.
    """
    tile = mercantile.tile(point.x, point.y, zoom)
    return tile.x, tile.y


def download_tile(
    session: requests.Session,
    base_url: str,
    zoom: int,
    x: int,
    y: int
) -> Optional[Image.Image]:
    """
    Fetch a single tile as a PIL Image, or return None on failure.
    """
    url = f"{base_url}/tile/{zoom}/{y}/{x}"
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as e:
        logger.warning(f"Tile ({x},{y}) failed: {e}")
        return None


def _generate_offset_grid(radius:int) -> List[Tuple[int, int]]:
    """
    For a given offset radius (a natural int), generate a 0-anchored square 
    with dimensions `(2*radius)+1`
    """
    if (int(radius) != radius) or (radius < 0):
        raise TypeError(f'`radius` must be a natural int. Given: "{radius}"') # TODO: wrong type of error. Incorporate errors/validators

    offsets = [
        (dx, dy)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
    ]
    return offsets


def download_tiles(
    session: requests.Session,
    base_url: str,
    center_x: int,
    center_y: int,
    zoom: int,
    radius: int
) -> Dict[Tuple[int, int], Optional[Image.Image]]:
    """
    Download a square block of tiles around (center_x, center_y).
    Radius of 1 => 3x3 grid; radius of 2 => 5x5 grid.
    """
    offsets = _generate_offset_grid(radius)
    #tiles: Dict[Tuple[int, int], Optional[Image.Image]] = {}
    tiles = {}
    x0, y0 = center_x, center_y

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=len(offsets)) as executor:
        futures = {executor.submit(download_tile, session, base_url, zoom, x0+dx, y0+dy): (dx, dy)
                   for dx, dy in offsets}
        for fut in as_completed(futures):
            dx, dy = futures[fut]
            tiles[(dx, dy)] = fut.result()
    return tiles


def stitch_tiles(
    tile_map: Dict[Tuple[int, int], Optional[Image.Image]],
    tile_size: Tuple[int, int],
    radius: int,
    fill_color: Tuple[int, int, int] = (0, 0, 0)
) -> Image.Image:
    """
    Stitch downloaded tiles into a single canvas.
    """
    tw, th = tile_size
    canvas_size = ((2 * radius + 1) * tw, (2 * radius + 1) * th)
    canvas = Image.new("RGB", canvas_size, fill_color)

    for (dx, dy), img in tile_map.items():
        px = (dx + radius) * tw
        py = (dy + radius) * th
        patch = img or Image.new("RGB", (tw, th), fill_color)
        canvas.paste(patch, (px, py))

    return canvas


def compute_fractional_pixel(
    point: Point,
    center_x: int,
    center_y: int,
    zoom: int,
    tile_size: Tuple[int, int]
) -> Tuple[float, float]:
    """
    Compute the pixel coordinates of `point` within the stitched canvas.
    """
    west, south, east, north = mercantile.bounds(center_x, center_y, zoom)
    tw, th = tile_size

    fx = (point.x - west) / (east - west)
    fy = (north - point.y) / (north - south)

    px_in_tile = fx * tw
    py_in_tile = fy * th

    cx = tw + px_in_tile
    cy = th + py_in_tile
    return cx, cy


# TODO: Update this so that it then can be cropped back down
def crop_to_center(
    canvas: Image.Image,
    center_px: float,
    center_py: float
) -> Image.Image:
    """
    Crop the stitched canvas so that (center_px, center_py) becomes the image center.
    """
    w, h = canvas.size
    left   = center_px - w / 2
    top    = center_py - h / 2
    right  = left   + w
    bottom = top    + h
    return canvas.crop((left, top, right, bottom))

# -----------------------------------------------------------------------------
# Main Processing Function
# -----------------------------------------------------------------------------
def process_point(
    session: requests.Session,
    base_url: str,
    point: Point,
    zoom: int,
    radius: int,
    fill_color: Tuple[int, int, int] = (0, 0, 0)
) -> Optional[Image.Image]:
    """
    Download, stitch, and crop a mosaic image centered on `point`.
    """
    x0, y0 = get_center_tile(point, zoom)
    tile_map = download_tiles(session, base_url, x0, y0, zoom, radius)

    if not all([x is None for x in tile_map.values()]):
        sample = next(img for img in tile_map.values() if img)
        tile_size = sample.size

        canvas = stitch_tiles(tile_map, tile_size, radius, fill_color)

        cx, cy = compute_fractional_pixel(point, x0, y0, zoom, tile_size)
        return crop_to_center(canvas, cx, cy)
    
    else: 
        return None


def _format_base_url(url_template:str, year:int) -> str:
    year_string = year if year != 2020 else '-_2020'
    return url_template.format(year=year_string)

def download_and_stitch_gdf(
    gdf: gpd.GeoDataFrame,
    year: int,
    zoom: int,
    save_dir: Path,
    service_url_template: str=TILE_URL_TEMPLATE,
    id_col: Optional[str] = None,
    geom_col: str = "geometry",
    radius: int = 1,
    fill_color: Tuple[int, int, int] = (0, 0, 0),
    quiet=False
) -> None:
    """
    Process each point in `gdf` and save a pixel-accurate mosaic.
    """

    save_dir.mkdir(parents=True, exist_ok=True)
    gdf = reproject_to_wgs84(gdf)
    session = requests.Session()
    base_url = _format_base_url(str(service_url_template), year)

    total_rows = gdf.shape[0]

    for row in tqdm(gdf.itertuples(index=True, name="Row"), total=total_rows, desc="Proecessing points"):
        #ident = getattr(row, id_col) if (id_col and id_col in gdf.columns) else row.Index
        ident = row.Index # TODO: this should be NODEID, then eventually renamed and standardized to location_id
        pt = row.geometry # geom_col
        if not isinstance(pt, Point):
            logger.error(f"[{ident}] geometry not Point – skipping")
            continue

        mosaic = process_point(session, base_url, pt, zoom, radius, fill_color)
        out_path = save_dir / f"{ident}.png"
        if out_path and mosaic:
            mosaic.save(out_path)
            if not quiet:
                logger.info(f"[{ident}] saved → {out_path}")

# -----------------------------------------------------------------------------
# Example Usage
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    df = gpd.GeoDataFrame({
        'id': [1, 2],
        'geometry': [Point(-74.0060, 40.7128), Point(-73.9851, 40.7580)]
    }, crs='EPSG:4326')

    download_and_stitch_gdf(
        gdf=df,
        year=2024,
        zoom=20,
        save_dir=Path("./mosaic_test"),
        service_url_template=TILE_URL_TEMPLATE
    )
