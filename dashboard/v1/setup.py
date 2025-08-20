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
from preprocessing.citydata.features_pipeline import count_features_for_locations
from preprocessing.citydata.cap_recon_pipeline import gather_capital_projects_for_locations

#UNIVERSE = 'dt_bk'
#LION_DB = gpd.read_file(project_dir / 'src/streetTransformer/data/universes/' / UNIVERSE / 'locations/lion.geojson')
#LION_DB_temp = load_lion_default('nyc')
LION_DB_temp = gpd.read_feather(project_dir / 'src/streetTransformer/data/universes/caprecon3/locations.feather')
LOCATIONS_GDF = LION_DB_temp[LION_DB_temp['StreetNames'].apply(len) == 2] # TODO: fix this

FEATURES_GDF = count_features_for_locations(LOCATIONS_GDF, buffer_width=100).to_crs('4326')
PROJECTS_GDF = gather_capital_projects_for_locations(LOCATIONS_GDF).to_crs('4326')

print(FEATURES_GDF)
print(PROJECTS_GDF)

