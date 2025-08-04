# Constants
YEARS = list(range(2006, 2025, 2))
ZLEVEL = 20  # Fixed zoom level for tile grid
TILE_URL_TEMPLATE = (
    "https://tiles.arcgis.com/tiles/yG5s3afENB5iO9fj/arcgis/rest/"
    "services/NYC_Orthos_{year}/MapServer/tile/{{z}}/{{y}}/{{x}}"
)
INITIAL_CENTER = [40.7128, -74.0060]
INITIAL_ZOOM = 12
GEOCODE_API = "https://nominatim.openstreetmap.org/search"

import sys
from pathlib import Path
import pandas as pd

project_dir = Path(__file__).resolve().parent.parent.parent
print(f'Treating "{project_dir}" as `project_dir`')
sys.path.append(str(project_dir))

import geopandas as gpd
from preprocessing.data_load.load_lion import load_lion_default

#UNIVERSE = 'dt_bk'
#LION_DB = gpd.read_file(project_dir / 'src/streetTransformer/data/universes/' / UNIVERSE / 'locations/lion.geojson')
LION_DB_temp = load_lion_default()
LION_DB = LION_DB_temp[LION_DB_temp['StreetNames'].apply(len) == 2]
