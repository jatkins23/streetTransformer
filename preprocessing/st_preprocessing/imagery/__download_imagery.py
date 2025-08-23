import io
import logging
from pathlib import Path
from typing import Union, Optional, Tuple, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import mercantile
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from PIL import Image
from tqdm import tqdm

TILE_URL_TEMPLATE = (
    "https://tiles.arcgis.com/tiles/yG5s3afENB5iO9fj/arcgis/rest/"
    "services/NYC_Orthos_{year}/MapServer/tile/{{z}}/{{y}}/{{x}}"
)

TILE_URL_TEMPLATE = (
    "https://tiles.arcgis.com/tiles/yG5s3afENB5iO9fj/arcgis/rest/"
    "services/NYC_Orthos_2024/MapServer"
)


# -----------------------------------------------------------------------------
# Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
# Core Function
# -----------------------------------------------------------------------------
def download_and_stitch_gdf(
    gdf: gpd.GeoDataFrame,
    year: int,
    zoom: int,
    save_dir: Union[str, Path],
    service_url_template: str = TILE_URL_TEMPLATE,
    id_col: Optional[str] = None,
    geom_col: str = "geometry",
    max_workers: int = 9,
    fill_color: Tuple[int, int, int] = (0, 0, 0),
) -> pd.DataFrame:
    """
    For each Point in `gdf`, download the 3×3 tile grid around it, stitch into one image,
    save to `save_dir`, and return a DataFrame of file paths.

    Args:
      gdf:       GeoDataFrame of Point geometries.
      service_url_template: e.g.
          "https://tiles.arcgis.com/tiles/.../services/NYC_Orthos_{year}/MapServer"
      year:      Plug into the template.
      zoom:      Desired zoom level.
      save_dir:  Where to write PNGs.
      id_col:    Column for filenames; defaults to index.
      geom_col:  Name of geometry column.
      max_workers:Number of threads for tile downloads.
      fill_color:RGB for missing tiles.

    Returns:
      DataFrame indexed by point ID with `file_path` column.
    """
    # Prepare
    save_dir = Path(save_dir); save_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    base_url = service_url_template.format(year=year)

    # Discover supported zooms
    meta = session.get(f"{base_url}?f=json", timeout=10)
    meta.raise_for_status()
    lods = meta.json().get("tileInfo", {}).get("lods", [])
    max_supported = max(l["level"] for l in lods) if lods else None
    # if max_supported is None or zoom > max_supported:
    #     raise ValueError(f"Zoom {zoom} unavailable (max supported: {max_supported})")

    offsets = [(dx, dy) for dy in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2)]
    out_records: List[Dict] = []

    # Iterate points with progress bar
    for idx, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Points"):
        ident = row[id_col] if id_col and id_col in row else idx
        pt = row[geom_col]
        if not isinstance(pt, Point):
            logger.error(f"[{ident}] geometry not Point – skipping")
            continue

        # Center tile
        tile = mercantile.tile(pt.x, pt.y, zoom)
        x0, y0 = tile.x, tile.y

        # Fetch closure
        def _fetch(dxy: Tuple[int,int]) -> Tuple[Tuple[int,int], Optional[Image.Image]]:
            dx, dy = dxy
            x, y = x0 + dx, y0 + dy
            url = f"{base_url}/tile/{zoom}/{y}/{x}"
            try:
                rsp = session.get(url, timeout=5.0)
                rsp.raise_for_status()
                return dxy, Image.open(io.BytesIO(rsp.content)).convert("RGB")
            except Exception as e:
                logger.warning(f"[{ident}] tile {dxy} failed: {e}")
                return dxy, None

        # Parallel download
        tile_map: Dict[Tuple[int,int], Image.Image] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch, off): off for off in offsets}
            for fut in as_completed(futures):
                off, img = fut.result()
                tile_map[off] = img

        # Determine tile dims
        sample = next((img for img in tile_map.values() if img), None)
        tw, th = sample.size if sample else (256, 256)

        # Build canvas & paste
        canvas = Image.new("RGB", (tw * 5, th * 5), fill_color)
        for (dx, dy), img in tile_map.items():
            px, py = (dx + 2) * tw, (dy + 2) * th
            patch = img or Image.new("RGB", (tw, th), fill_color)
            canvas.paste(patch, (px, py))

        # Save
        out_path = save_dir / f"{ident}.png"
        canvas.save(out_path)
        logger.info(f"[{ident}] saved → {out_path}")
        out_records.append({"id": ident, "file_path": str(out_path)})

    return pd.DataFrame.from_records(out_records).set_index("id")
