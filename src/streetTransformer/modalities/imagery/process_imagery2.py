import os, sys
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely import geometry, box
from pyproj import CRS

from PIL import Image
import matplotlib.pyplot as plt

import osmnx as ox

from dotenv import load_dotenv
load_dotenv()

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(root_dir)

from data_load import load_lion


#STATIC_PATH = 'imagery/tiles/static/nyc/256_19'
#static_path = Path(str(os.getenv('DATA_PATH'))) / STATIC_PATH

load_lion()

class location(self, lco)


def get_location_bounds() -> gpd.GeoDataFrame:
    # call ox.
    pass

def write_images():
    pass

def gather_location_imagery(
        location_name:str, 
        tile_static_path:Path, 
        tile_ref_path:Path, 
        out_dir:Optional[Path]=None, 
        subset_ids:Optional[List[int]]=None,
        write:bool=False):
    # Pull raw imagery
    # Done: have to do via commandline and rename manually

    # Find all intersections in given location
    nodes = load_lion.load_location(location_name)

    # Load the reference tiles from tile2net
    tile_reference_gdf = load_tile_reference(tile_ref_path)

    # Buffer and Load
    intersection_tile_walk = buffer_and_load(nodes, tile_reference_gdf, static_path=tile_static_path)

    # Downsample to requested
    if subset_ids:
        intersection_tile_walk = intersection_tile_walk.loc[subset_ids]

    # Stitch images 
    imgs = intersection_tile_walk.groupby('location_id').apply(_safe_stitch_image)

    # Save if quested
    # itx_names = 
    # images_df = pd.concat
    # 

    if write:
        if not out_dir:
            raise UserWarning("Need `out_dir` to be able to save images")
        write_images()

    return nodes, images_df



if __name__ == '__main__':
    print(gather_location_imagery('Downtown Brooklyn, New York, USA'))