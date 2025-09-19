# Migrate two universes together into one

from pathlib import Path
import geopandas as gpd
import os
import pandas as pd
import shutil
import tqdm

# # get all locations for controls
# locations_caprecon_gdf = gpd.read_feather(UNIVERSES_PATH / 'caprecon3' / 'locations.feather')
# caprecon_location_ids = locations_caprecon_gdf['location_id']

# locations_3k_gdf = gpd.read_parquet(UNIVERSES_PATH / 'control3k' / 'locations.parquet')
# locations_3k_gdf

# locations_original_gdf = gpd.read_feather(UNIVERSES_PATH / 'caprecon_plus_control' / 'locations.feather')
# locations_original_gdf

# locations_combined_gdf = (
#     pd.concat([
#         locations_original_gdf,
#         locations_3k_gdf.drop('OBJECTID', axis=1).reset_index(drop=True),
#         ], keys=['original', 'control3k']
#     )
#     .reset_index()
#     .drop('level_1', axis=1)
#     .rename({'level_0': 'source'}, axis=1)
#     [['location_id','crossstreets', 'geometry','source']]
# )

# import numpy as np
# treatment_mask = locations_combined_gdf['location_id'].isin(caprecon_location_ids)
# new_source = np.where(treatment_mask, 'caprecon', locations_combined_gdf['source'])
# locations_combined_gdf['source'] = new_source
# locations_combined_gdf['source'] = np.where(locations_combined_gdf['source'] == 'original', 'control2k', locations_combined_gdf['source'])

# locations_combined_gdf['tc_var'] = np.where(locations_combined_gdf['source'] == 'caprecon', 'treat', 'control')
# locations_combined_gdf.value_counts(subset=['source','tc_var']).reset_index()


#UNIVERSES_PATH = Path('src/streetTransformer/data/universes/')
from streettransformer.config.constants import UNIVERSES_PATH
DISABLE_PROGRESS_BAR = False


ORIGINAL_UNIVERSE_NAME = 'caprecon_plus_control'
ADDITIONAL_UNIVERSE_NAME = 'control3k'
COMBINED_UNIVERSE_NAME = 'caprecon_control5k'

# Combine caprecon3 and non_caprecon
os.makedirs(UNIVERSES_PATH / COMBINED_UNIVERSE_NAME / 'imagery', exist_ok=True)

# Load both Locations and combine
# original_locations = gpd.read_feather(UNIVERSES_PATH / ORIGINAL_UNIVERSE_NAME / 'locations.feather')
# #addtnl_locations = gpd.read_feather(UNIVERSES_PATH / ADDITIONAL_UNIVERSE_NAME / 'locations.feather')
# addtnl_locations = gpd.read_parquet(UNIVERSES_PATH / ADDITIONAL_UNIVERSE_NAME / 'locations_raw.parquet')

# locations = pd.concat([original_locations, addtnl_locations], keys=['origin', 'new_locations'])
# locations.to_feather(UNIVERSES_PATH / COMBINED_UNIVERSE_NAME / 'locations.feather') # TODO: All of this

combined_locations_gdf = gpd.read_parquet(UNIVERSES_PATH / COMBINED_UNIVERSE_NAME / 'locations' / 'locations_raw.parquet')

# Combine imagery
YEARS = list(range(2006, 2025, 2))
INPUT_UNIVERSES = [ORIGINAL_UNIVERSE_NAME, ADDITIONAL_UNIVERSE_NAME]
for year in YEARS:
    # Set the destination dir and create if necessary
    dest_dir = UNIVERSES_PATH / COMBINED_UNIVERSE_NAME / 'imagery' / str(year)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for uni in INPUT_UNIVERSES:
        source_dir = UNIVERSES_PATH / uni / 'imagery' / str(year)

        total_files = len(os.listdir(source_dir))
        for file in tqdm.tqdm(source_dir.iterdir(), total=total_files, desc=f'Moving {year}-{uni} images', disable=DISABLE_PROGRESS_BAR):
            if file.is_file() and file.suffix == '.png':
                shutil.move(file, dest_dir / file.name)


