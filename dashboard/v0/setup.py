import sys
from pathlib import Path
import pandas as pd

project_dir = Path(__file__).resolve().parent.parent.parent
print(f'Treating "{project_dir}" as `project_dir`')
sys.path.append(str(project_dir))

import ollama

from src.streetTransformer.utils.constants import DATA_PATH, REF_FILE_RELATIVE_PATH, REF_FILE_PATTERN, AVAILABLE_YEARS, AVAILABLE_ZLEVELS, AVAILABLE_MODELS
from src.streetTransformer.utils.image_paths import get_imagery_reference_path, assemble_location_imagery

#DATA_PATH = Path('..') / DATA_PATH
if not DATA_PATH.is_dir():
    raise FileNotFoundError(f'{DATA_PATH} doesnt exist')

ref_file = get_imagery_reference_path(DATA_PATH, AVAILABLE_ZLEVELS[-1], AVAILABLE_YEARS[-1])
INTERSECTIONS = pd.read_csv(ref_file)
INTERSECTIONS[INTERSECTIONS['name'].notna()]
values = [int(x) for x in INTERSECTIONS.index.values]
AVAILABLE_INTERSECTIONS = dict(zip(INTERSECTIONS['name'], values))