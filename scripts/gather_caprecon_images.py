from pathlib import Path
import os, sys

#project_root = Path.cwd().parent
project_root = Path(__file__).resolve().parent.parent
print(f'Treating "{project_root}" as `project_root`')
sys.path.append(str(project_root))

from preprocessing.citydata.cap_recon_pipeline import gather_capital_projects_for_locations
from preprocessing.data_load.load_lion import load_lion_default
from preprocessing.imagery.download_imagery2 import download_and_stitch_gdf
from preprocessing.preprocess import save_locations # TODO: this will be moved to a better location

TILE_URL_TEMPLATE = (
    "https://tiles.arcgis.com/tiles/yG5s3afENB5iO9fj/arcgis/rest/"
    "services/NYC_Orthos_{year}/MapServer"
)


# Load NYC locations
nyc_locations = load_lion_default('nyc')


# Load cap-recon projects
location_projects_gdf = gather_capital_projects_for_locations(nyc_locations)
location_projects_gdf_existant = location_projects_gdf[location_projects_gdf['project_id'].notna()]

# locations_gdf = location_projects_gdf_existant # TODO: FOR CAPRECON
# print(nyc_locations)
# print(location_projects_gdf)

# Create the control group 
# anti = nyc_locations.merge(location_projects_gdf['location_id'], on='location_id', how='left', indicator=True) # TODO: FOR RANDOM 
# locations_gdf = anti[anti['_merge'] == 'left_only'].drop(columns='_merge')

# locations_gdf = locations_gdf.sample(2000)
# locations_gdf.to_feather('src/streetTransformer/data/universes/non_caprecon/locations.feather')

import geopandas as gpd
locations_gdf = gpd.read_feather('src/streetTransformer/data/universes/non_caprecon/locations.feather')

# Now loop through the years
YEARS = list(range(2006, 2025, 2))

imagery_dir = Path('src/streetTransformer/data/universes/non_caprecon/imagery')
for year in YEARS:
    year_dir = imagery_dir / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    print(f"\tProcessing imagery for year {year}...")

    download_and_stitch_gdf(
        locations_gdf, 
        year = year, 
        zoom=20, 
        save_dir = year_dir,
        quiet=True
    )