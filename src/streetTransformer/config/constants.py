from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# DATA_PATH = Path(str(os.getenv('DATA_PATH')))
# #REF_FILE_RELATIVE_PATH = Path('imagery/processed/refs')
# print(f'Reference File Path: `{DATA_PATH / REF_FILE_RELATIVE_PATH}`')
# REF_FILE_PATTERN = 'image_refs_z{zlevel}_{year}.csv'
# AVAILABLE_YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2022, 2024]
ZLEVELS = [19, 20]
# AVAILABLE_MODELS = ['complete_streets_feature_detector', 'change_identifier', 'bikelane_detector']

# Environment
YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024]
YEARS_str = ['2006', '2008', '2010', '2012', '2014', '2016', '2018', '2020', '2022', '2024']

# Paths
DATA_PATH = Path(str(os.getenv('DATA_PATH')))
UNIVERSES_PATH = DATA_PATH / 'runtime' / 'universes'
UNIVERSE_NAME = 'caprecon_plus_control'
UNIVERSE_PATH = UNIVERSES_PATH / UNIVERSE_NAME

# Test
TRAFFIC_CALMING_TEST_LOCATION_IDS = [7571, 8887, 11738, 11800, 12116, 14271, 15283, 15375, 15709, 15852]