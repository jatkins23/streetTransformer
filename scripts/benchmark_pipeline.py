# In Progress

from pathlib import Path
import os, sys
import argparse
from pprint import pprint

import numpy as np
import pandas as pd
import geopandas as gpd
import tqdm

# Set Local environment
project_path = Path(__file__).resolve().parent.parent
print(f'Treating "{project_path}" as `project_path`')
sys.path.append(str(project_path))

# Local imports
from src.streetTransformer.locations.location import Location # This creates a Location object that holds and converts all of the data for each location
from src.streetTransformer.llms.run_gemini_model import run_individual_model # Runs a gemini model 
import src.streetTransformer.llms.models.imagery_describers.gemini_imagery_describers
from src.streetTransformer.comparison.compare import get_image_compare_data, get_compare_data_for_location_id_years, show_images_side_by_side

traffic_calming_location_ids = [7571, 8887, 11738, 11800, 12116, 14271, 15283, 15375, 15709, 15852]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--location', type='int', default=15852)
    parser.add_argument('-u', '--universe', type='str', default = 'caprecon_plus_control')
    parser.add_argument('-s', '--start-year', type='int', default=2018)
    parser.add_argument('-e', '--end-year', type='int', deafult=2024)

    args = parser.parse_args()

    return args

# We know the ground truth: what has changed, if there 
if __name__ == '__main__':
    #args = parse_args()
    # Process
    # 0) Set universe 
    #UNIVERSE_NAME = args.universe
    UNIVERSE_NAME = 'caprecon_plus_control'
    UNIVERSE_PATH = project_path / 'src/streetTransformer/data/universes/' / UNIVERSE_NAME
    YEARS = list(range(2006, 2025, 2))

    # 1) Load all locations from the project database
    locations_gdf = gpd.read_feather(UNIVERSE_PATH / 'locations.feather')
    locations_gdf = locations_gdf.to_crs('4326')
    locations_gdf = locations_gdf

    # 2) Create Location Df


    # locations_gdf = locations_gdf.head(1000)
    locations_gdf = locations_gdf[locations_gdf['location_id'].isin(traffic_calming_location_ids)]
    total_locations = locations_gdf.shape[0]

    # Get comparison 
    compare2016_2024 = get_image_compare_data(locations_gdf, location_id=15852, start_year=2016, end_year=2024, universe_name=UNIVERSE_NAME)
    compare2014_2024 = get_image_compare_data(locations_gdf, location_id=15852, start_year=2014, end_year=2024, universe_name=UNIVERSE_NAME)

    response = run_individual_model(gemini_imager_describers.step1_instructions, files=compare2016_2024)
    show_images_side_by_side(compare2016_2024, UNIVERSE_PATH, labels=['2016', '2024'])

    response = run_individual_model(gemini_imager_describers.step1_instructions, files=compare2014_2024)
    show_images_side_by_side(compare2014_2024, UNIVERSE_PATH, labels=['2014', '2024'])

    print(response)
