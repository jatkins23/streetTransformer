import os, sys
from pathlib import Path
import json
import tqdm
from google import genai
import geopandas as gpd
import argparse
from typing import List

from dotenv import load_dotenv

# Local imports
from streettransformer.config.constants import DATA_PATH, UNIVERSES_PATH, YEARS

#from streettransformer.locations.location import Location # This creates a Location object that holds and converts all of the data for each location
from streettransformer.llms.run_gemini_model import run_individual_model # Runs a gemini model 
import streettransformer.llms.models.imagery_describers.gemini_imagery_describers as gemini_imagery_describers
from streettransformer.comparison.compare import get_image_compare_data, get_compare_data_for_location_id_years, show_images_side_by_side

YEARS = [2016, 2024, 2018, 2022, 2020]

def permute_years(years):
        # create all permutations of comparison years 
        permutations = []
        for y1 in years:
            for y2 in years:
                if y2 > y1:
                    permutations.append((y1, y2))
        return permutations

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('universe_name', type=str)
    parser.add_argument('-o', '--outfile', type=str, default=None)
    parser.add_argument('-m', '--model-name', type=str, default='gemini-2.5-flash')
    parser.add_argument('-n', '--top-n', type=int, default=None)
    parser.add_argument('-y', '--years', type=int, nargs='+', default=YEARS)
    
    args = parser.parse_args()
    
    return args

def safe_try_and_export_model(locations_gdf:gpd.GeoDataFrame, l_id:int, start_year:int, end_year:int, 
                              universe_name:str, model_instructions:str, client, model_name): 
    output = {
        'location_id'   : l_id,
        'start_year'    : start_year,
        'end_year'      : end_year
    }
    
    try:
        compare_images = get_image_compare_data(
            locations_gdf, 
            location_id=l_id,
            start_year=start_year, 
            end_year=end_year, 
            universe_name=universe_name
        )
        output['start_image_path'] = str(compare_images[0])
        output['end_image_path'] = str(compare_images[1])

        response = run_individual_model(model_instructions, files=compare_images, client=client, model_name=model_name)    
        
        output['response'] = response

    except Exception as e:
        output['error'] = str(e)
    finally:
        results.append(output)
    
    return output

if __name__ == '__main__':
    args = parse_args()
    universe_name = args.universe_name
    universe_path = UNIVERSES_PATH / universe_name

    results_path = DATA_PATH / 'runtime' / 'results' / universe_name
    

    # 1) Load all locations from the project database
    locations_path = universe_path / 'locations' / 'locations_raw.parquet'
    locations_gdf = gpd.read_parquet(locations_path)
    locations_gdf = locations_gdf.to_crs('4326')
    
    if args.top_n is not None and isinstance(args.top_n, int): 
        locations_gdf = locations_gdf.head(args.top_n) # For subsetting if necessary

    total_locations = locations_gdf.shape[0]
    years = args.years if len(args.years) > 1 else YEARS
    year_pairs = permute_years(args.years)

    # Get comparison 
    results = []
    total_compares = locations_gdf.shape[0] * len(year_pairs)

    # Model
    load_dotenv()
    os.getenv('GEMINI_API_KEY')
    gemini_client = genai.Client=genai.Client()
    model_instructions = gemini_imagery_describers.step1_instructions

    if args.outfile:
        outfile =  results_path / args.outfile
        outfile.parent.mkdir(parents=True, exist_ok=True)

    
    for start_year, end_year in tqdm.tqdm(year_pairs, total=len(year_pairs), disable=(args.outfile is None)):
        for l_id in tqdm.tqdm(locations_gdf['location_id'], total=locations_gdf.shape[0], desc=f'{start_year} -> {end_year}', disable=(args.outfile is None)):
            output = safe_try_and_export_model(locations_gdf, l_id, start_year, end_year, universe_name, model_instructions, gemini_client, args.model_name)

            if args.outfile:
                with outfile.open('a+', encoding='utf-8') as f:
                    f.write(json.dumps(output) + '\n')
            else:
                print(output)