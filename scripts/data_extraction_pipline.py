
# Example Usage
# python scripts/data_extraction_pipline.py -y 2016 -z 20 --location "Downtown Brooklyn, New York, USA" --outfile data/test_runs/downtown_bk/imagery/processed/refs/image_refs_z20_2016.csv


import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import argparse


# Import from src
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent 
sys.path.append(str(project_root))

#from src.data_load.load_intersections import load_location
import src.process_imagery.join_and_stitch as jas

load_dotenv(override=True)
DATA_PATH_STEM = Path(str(os.getenv('DATA_PATH')))

def run_pipeline(location, year, z_level):
    STATIC_REL_PATH = Path('imagery', 'raw_static', f'z{z_level}/{year}/')
    STATIC_PATH = DATA_PATH_STEM / STATIC_REL_PATH

    TILEREF_REL_PATH = f'imagery/raw_static/z{z_level}/{year}/{year}_256_info.csv'
    TILEREF_PATH = os.path.join(DATA_PATH_STEM, TILEREF_REL_PATH)

    SAVE_FULLIMAGE_REL_PATH = f'imagery/processed/stitched/z{z_level}/{year}/'
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
    
    parser.add_argument('--location', type=str, required=True)
    parser.add_argument('-z','--z_level', type=int, default=20)
    parser.add_argument('-y','--year', type=int,default=2024)
    parser.add_argument('-o','--outfile', type=str)

    args = parser.parse_args()

    return args

if __name__ == '__main__':

    args = parse_args()

    images_gdf = run_pipeline(**vars(args))
    
    os.makedirs(Path(args.outfile).parent, exist_ok=True)
    
    images_gdf.to_csv(args.outfile)

