import os, sys
from pathlib import Path
import json
import tqdm
from google import genai
import geopandas as gpd

from dotenv import load_dotenv

load_dotenv()
os.getenv('GEMINI_API_KEY')

# Local imports
from streettransformer.config.constants import DATA_PATH, UNIVERSES_PATH, YEARS

from streettransformer.locations.location import Location # This creates a Location object that holds and converts all of the data for each location
from streettransformer.llms.run_gemini_model import run_individual_model # Runs a gemini model 
import streettransformer.llms.models.imagery_describers.gemini_imagery_describers as gemini_imagery_describers
from streettransformer.comparison.compare import get_image_compare_data, get_compare_data_for_location_id_years, show_images_side_by_side

UNIVERSE_NAME = 'caprecon_plus_control_downsampled'
universe_path = UNIVERSES_PATH / UNIVERSE_NAME

OUTFILE = DATA_PATH / 'runtime' / 'results' / UNIVERSE_NAME / 'image_describer_trial2_normal.txt'
#MODEL_NAME = 'gemini-2.5-flash-lite'
MODEL_NAME = 'gemini-2.5-flash'


# 1) Load all locations from the project database
locations_gdf = gpd.read_feather(universe_path / 'locations.feather')
locations_gdf = locations_gdf.to_crs('4326')
locations_gdf = locations_gdf # For subsetting if necessary

total_locations = locations_gdf.shape[0]

def permute_years(years):
    # create all permutations of comparison years 
    permutations = []
    for y1 in years:
        for y2 in years:
            if y2 > y1:
                permutations.append((y1, y2))
    return permutations
    
#year_pairs = permute_years(YEARS)
YEARS = [2016, 2024, 2018, 2022, 2020]
year_pairs = permute_years(YEARS)

# Get comparison 
results = []
total_compares = locations_gdf.shape[0] * len(year_pairs)

gemini_client = genai.Client=genai.Client()

for start_year, end_year in tqdm.tqdm(year_pairs, total=len(year_pairs)):
    for l_id in tqdm.tqdm(locations_gdf['location_id'], total=locations_gdf.shape[0], desc=f'{start_year} -> {end_year}'):
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
                universe_name=UNIVERSE_NAME
            )

            response = run_individual_model(gemini_imagery_describers.step1_instructions, files=compare_images, client=gemini_client, model_name=MODEL_NAME)    
            output['start_image_path'] = str(compare_images[0])
            output['end_image_path'] = str(compare_images[1])

            output['response'] = response

        except Exception as e:
            output['error'] = 'error'
        finally:
            results.append(output)
        
            OUTFILE.parent.mkdir(parents=True, exist_ok=True)
            with OUTFILE.open('a+', encoding='utf-8') as f:
                f.write(json.dumps(output) + '\n')