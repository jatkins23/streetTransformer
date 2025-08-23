# In Progress

from pathlib import Path
import os, sys
import argparse
from pprint import pprint

import numpy as np
import pandas as pd
import geopandas as gpd
import tqdm

# Local imports
from streettransformer.config.constants import UNIVERSES_PATH, TRAFFIC_CALMING_TEST_LOCATION_IDS, YEARS
from streettransformer.locations.location import Location # This creates a Location object that holds and converts all of the data for each location
from streettransformer.llms.run_gemini_model import run_individual_model # Runs a gemini model 
import streettransformer.llms.models.imagery_describers.gemini_imagery_describers as gemini_imagery_describers
from streettransformer.comparison.compare import get_image_compare_data, get_compare_data_for_location_id_years, show_images_side_by_side

#traffic_calming_location_ids = [7571, 8887, 11738, 11800, 12116, 14271, 15283, 15375, 15709, 15852]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--location-id', type=int, default=15852)
    parser.add_argument('-u', '--universe-name', type=str, default = 'caprecon_plus_control')
    parser.add_argument('-s', '--start-year', type=int, default=2018)
    parser.add_argument('-e', '--end-year', type=int, default=2024)
    parser.add_argument('-d', '--display', type=bool, default=True)


    args = parser.parse_args()

    return args

# We know the ground truth: what has changed, if there 
if __name__ == '__main__':
    args = parse_args()
    # Process
    # 0) Set universe 
    universe_name = args.universe_name
    universe_path = UNIVERSES_PATH / universe_name

    # 1) Load all locations from the project database
    locations_gdf = gpd.read_feather(universe_path / 'locations.feather')
    locations_gdf = locations_gdf.to_crs('4326')
    locations_gdf = locations_gdf # For subsetting if necessary

    # 2) Create Location Df
    # locations_gdf = locations_gdf.head(1000)
    locations_gdf = locations_gdf[locations_gdf['location_id'].isin(TRAFFIC_CALMING_TEST_LOCATION_IDS)]
    total_locations = locations_gdf.shape[0]

    # Get comparison 
    compare = get_image_compare_data(locations_gdf, location_id=args.location_id, start_year=args.start_year, end_year=args.end_year, universe='caprecon_plus_control')

    response = run_individual_model(gemini_imagery_describers.step1_instructions, files=compare)
    if args.display:
        show_images_side_by_side(compare, universe_path, labels=[str(args.start_year), str(args.end_year)])
    
    print(response)
