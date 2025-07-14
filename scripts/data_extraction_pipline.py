import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import argparse

import pandas as pd
import geopandas as gpd
import numpy as np
import shapely

# Import from src
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent 
sys.path.append(str(project_root))

from data_load.load_intersections import load_location
import process_imagery.join_and_stitch as jas
from llms.run_llm_model import run_model


load_dotenv()
DATA_PATH_STEM = os.getenv('DATA_PATH')

Z_LEVEL = 20
YEAR = 2024

def run_pipeline(location, year, z_level):
    STATIC_REL_PATH = 'imagery/tiles/static/nyc'
    STATIC_REL_PATH = f'tile2net_export/dt_bk/{year}/tiles/static/nyc/256_{z_level}'
    STATIC_PATH = os.path.join(DATA_PATH_STEM, STATIC_REL_PATH)

    TILEREF_REL_PATH = f'tile2net_export/dt_bk/{year}/tiles/{year}_256_{z_level}_info.csv'
    TILEREF_PATH = os.path.join(DATA_PATH_STEM, TILEREF_REL_PATH)

    SAVE_FULLIMAGE_REL_PATH = f'test/dt_bk_test/intx_full_z{z_level}/{year}'
    SAVE_FULLIMAGE_PATH = os.path.join(DATA_PATH_STEM, SAVE_FULLIMAGE_REL_PATH)

    nodes, images_df = jas.gather_location_imagery(
        location, 
        tile_static_path=STATIC_PATH.format(year=year, z_level=z_level), 
        tile_ref_path=TILEREF_PATH.format(year=year, z_level=z_level), 
        save_path=SAVE_FULLIMAGE_PATH.format(year=year, z_level=z_level)
    )

    imagery_gdf = images_df[['name','file_path']].merge(
        nodes[['highway','geometry']],
        left_index=True, right_index=True
    )[['name','highway','file_path','geometry']]
    
    return imagery_gdf

def parse_args():
    parser = argparse.ArgumentParser(description='Run a pipeline for a location')
    parser.add_argument(
        '--location',
        type=str,
        required=True
    )

    parser.add_argument(
        '-z','--zoom',
        type=int,
        default=19
    )

    parser.add_argument(
        '-y','--year',
        type=int,
        default=2024
    )

    parser.add_argument(
        '-o','--outfile',
        type=str
    )

    args = parser.parse_args()
    return args.location, args.year, args.zoom, args.outfile

if __name__ == '__main__':
    location, year, z_level, outfile = parse_args()
    images_gdf = run_pipeline(location, year, z_level)
    images_gdf.to_csv(outfile)
    