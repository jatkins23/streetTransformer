# Utility functions for use with the satelite imagery and tile system

# NOTE: This was envisioned to replace utils/image_paths.py and viz/utils.py but actually they are really different and shouldn't be combined
        # keep it to use the improved docoumentation and the error integration but its not 
from pathlib import Path
import sys
from typing import List, Dict, Tuple, Optional
import io


root_dir = Path(__file__).resolve().parent.parent.parent
print(f'Treating "{root_dir}" as `root_dir`')
sys.path.append(str(root_dir))
from config.constants import REF_FILE_RELATIVE_PATH, REF_FILE_PATTERN, AVAILABLE_ZLEVELS, AVAILABLE_YEARS
from utils.validators import check_value

import pandas as pd

import base64
from PIL import Image

def get_imagery_reference_path(root_path:Path, zlevel:int, year:int) -> Path:
    """Return the path to the reference file for a given zlevel and year

    Args:
        root_path (Path): the data root directory path from the `data_pathargument
        zlevel (int): _description_
        year (int): _description_

    Returns:
        Path: A path to the csv file
    """
    check_value(zlevel, AVAILABLE_ZLEVELS, 'zlevel')
    check_value(year, AVAILABLE_YEARS, 'year')
    
    file_name = REF_FILE_PATTERN.format(zlevel=zlevel, year=year)
    
    return root_path / REF_FILE_RELATIVE_PATH / file_name

def assemble_location_imagery(location_id:int, root_path:Path, years:List[int], zlevel:int) -> Dict[int, Path]:
    """Assemble relevant imagery for a given location

    Args:
        location_id (int): _description_
        root_path (Path): _description_
        years (List[int]): years to gather
        zlevel (int): zoom-level [19,20]

    Returns:
        Dict[int, Path]: the image paths for all years associated with an image for given years
    """
    year_ref_paths = {year: get_imagery_reference_path(root_path, zlevel, year) for year in years}
    
    # TODO: Get location_name, return? -- clean this up 
    # location_name = year

    year_image_paths = {}
    for year, ref_path in year_ref_paths.items():
        try: #
            image_path = pd.read_csv(ref_path).loc[location_id]['file_path']
        except Exception as e:
            print(f'{location_id}: {year}: {e})')
            image_path = None
        
        year_image_paths[year] = image_path

    return year_image_paths



def get_image_path(location_id: int, zlevel:int, year:int, root_dir:Path, sub_dir:Optional[Path]) -> Tuple[str, Path]:
    path = root_dir
    if sub_dir:
        path = path / sub_dir

    ref_file_path = get_imagery_reference_path(path, zlevel, year)
    ref_df = pd.read_csv(ref_file_path)
    row = ref_df.loc[location_id]
    try:
        file_path = Path(str(row['file_path']))
        intx_name = str(row['name'])
        return intx_name, file_path
    except Exception as e:
        print(e)
        return "Unknown", Path("")
