from pathlib import Path
from typing import List, Dict

import pandas as pd
def get_imagery_reference_path(root_path:Path, zlevel:int, year:int) -> Path:
    """get_imagery_reference_path

    Args:
        root_path (Path): the data root directory path from the `data_path` argument
        zlevel (int): 
        year (int):

    Returns:
        Path: A path to the directory contianing the reference materials for the given year and zoom-level
    """
    
    # TODO: better error handling for values that just don't exist in the database
    if zlevel not in [19,20]:
        raise ValueError(f'`zlevel` "{zlevel}" not available. Check source data')
    if year not in range(2006, 2025, 2):
        raise ValueError(f'`year` "{year}" not available. Check source data')
    
    file_name = f'image_refs_z{zlevel}_{year}.csv'

    return root_path / "imagery" / "processed" / "refs" / file_name

def assemble_location_imagery(location_id:int, root_path:Path, years:List[int], zlevel:int) -> Dict[int, Path]:
    """Assemble relevant imagery for each location

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
        try:
            image_path = pd.read_csv(ref_path).loc[location_id]['file_path']
        except Exception as e:
            print(f'{location_id}: {year}: {e})')
            image_path = None
        
        year_image_paths[year] = image_path

    return year_image_paths
