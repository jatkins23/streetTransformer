from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = Path(str(os.getenv('DATA_PATH')))
REF_FILE_RELATIVE_PATH = Path('imagery/processed/refs')
REF_FILE_PATTERN = 'image_refs_z{zlevel}_{year}.csv'
AVAILABLE_YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2022, 2024]
AVAILABLE_ZLEVELS = [19, 20]
AVAILABLE_MODELS = ['change_identifier', 'walkability_rater', 'bikelane_detector']