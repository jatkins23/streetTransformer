
# Given location:
# - Make bounding box around it
# - Find all tiles in rerference table within those bounds


import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from typing import Tuple

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from pyproj import CRS

from PIL import Image
import matplotlib.pyplot as plt

load_dotenv()

STATIC_PATH = 'imagery/tiles/static/nyc/256_19'
static_path = os.path.join(os.getenv('DATA_PATH'), STATIC_PATH)

# Load the reference tile df
def load_tile_reference(file_path:str|Path, crs:CRS='4326') -> gpd.GeoDataFrame:
    """
    Load tile metadata as a GeoDataFrame.

    Args:
        index_file_path: Path to a GeoJSON or CSV with columns:
                         ['tile_path', 'geometry']
        crs: Geo Reference System

    Returns:
        GeoDataFrame with tile geometries.
    """
    tile_ref_df = pd.read_csv(file_path, index_col=0)

    coordinates = tile_ref_df.apply(
        lambda x:
        shapely.geometry.box(x['topleft_x'], x['bottomright_y'], x['bottomright_x'], x['topleft_y']),
        axis=1
    )

    tile_ref_gdf = gpd.GeoDataFrame(
        tile_ref_df,
        crs=crs,
        geometry=coordinates
    )
        
    return tile_ref_gdf

# Calculate based on intersection type (probably needs to include edges as)
def _calculate_ideal_buffer_width(node):
    # TODO: Stub
    return 20

def _set_buffer_width(buffer_width, nodes):
    if isinstance(buffer_width, int):
        buffer_value = buffer_width
    elif buffer_width == 'variable':
        buffer_value = nodes.apply(_calculate_ideal_buffer_width, axis=1)
    else:
        raise ValueError(f'Unknown `buffer_value`: {buffer_width}')
    
    return buffer_value
