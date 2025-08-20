# Migrate two universes together into one

from pathlib import Path
import geopandas as gpd
import os
import pandas as pd
import shutil
import tqdm

UNIVERSES_PATH = Path('src/streetTransformer/data/universes/')
DISABLE_PROGRESS_BAR = False

# Combine caprecon3 and non_caprecon
os.makedirs(UNIVERSES_PATH / 'caprecon_plus_control/imagery', exist_ok=True)

# Load both Locations and combine
caprecon_locations = gpd.read_feather(UNIVERSES_PATH / 'caprecon3' / 'locations.feather')
control_locations = gpd.read_feather(UNIVERSES_PATH / 'non_caprecon' / 'locations.feather')

locations = pd.concat([caprecon_locations, control_locations], ignore_index=True, keys=['caprecon', 'control'])
locations.to_feather(UNIVERSES_PATH / 'caprecon_plus_control' / 'locations.feather')

# Combine imagery
YEARS = list(range(2006, 2025, 2))
INPUT_UNIVERSES = ['caprecon3','non_caprecon']
for year in YEARS:
    # Set the destination dir and create if necessary
    dest_dir = UNIVERSES_PATH / 'caprecon_plus_control' / 'imagery' / str(year)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for uni in INPUT_UNIVERSES:
        source_dir = UNIVERSES_PATH / uni / 'imagery' / str(year)

        total_files = len(os.listdir(source_dir))
        for file in tqdm.tqdm(source_dir.iterdir(), total=total_files, desc=f'Copying {year}-{uni} images', disable=DISABLE_PROGRESS_BAR):
            if file.is_file() and file.suffix == '.png':
                shutil.copy2(file, dest_dir / file.name)
