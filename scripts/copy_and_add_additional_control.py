from pathlib import Path
import os

import pandas as pd
import geopandas as gpd

from st_preprocessing.data_load.load_lion import load_lion_default

#from st_preprocessing.citydata.cap_recon_pipeline import gather_capital_projects_for_locations
from st_preprocessing.data_load.load_lion import load_lion_default
from st_preprocessing.imagery.download_imagery2 import download_and_stitch_gdf
#from st_preprocessing.preprocess import save_locations # TODO: this will be moved to a better location


UNIVERSES_PATH = Path('data/runtime/universes/')

# 
ORIGINAL_UNIVERSE = 'caprecon_plus_control'

TEMP_UNIVERSE = 'control3k'
NEW_UNIVERSE = 'caprecon_plus_control5k'


# get total_locations
nyc_locations = load_lion_default('nyc')
original_locations_gdf = gpd.read_feather(UNIVERSES_PATH / ORIGINAL_UNIVERSE / 'locations.feather')
nyc_locations = nyc_locations.rename(columns={'NODEID': 'location_id', 'StreetNames': 'crossstreets'})
anti = nyc_locations.merge(original_locations_gdf['location_id'], on='location_id', how='left', indicator=True)
unused_locations_gdf = anti[anti['_merge'] == 'left_only'].drop(columns='_merge')

#new_locations_gdf = unused_locations_gdf.sample(3000)

os.makedirs(UNIVERSES_PATH / TEMP_UNIVERSE, exist_ok=True)
#new_locations_gdf.to_parquet(UNIVERSES_PATH / TEMP_UNIVERSE / 'locations.parquet')
new_locations_gdf = gpd.read_parquet(UNIVERSES_PATH / TEMP_UNIVERSE / 'locations.parquet')

# 
YEARS = list(range(2006, 2025, 2))
imagery_dir = UNIVERSES_PATH / TEMP_UNIVERSE / 'imagery'
for year in YEARS:
    year_dir = imagery_dir / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    print(f"\tProcessing imagery for year {year}...")

    download_and_stitch_gdf( 
        new_locations_gdf, 
        year = year, 
        zoom=20, 
        save_dir = year_dir,
        quiet=True
    )