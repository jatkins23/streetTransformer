import os, sys
from pathlib import Path
import json
import tqdm
from google import genai
import geopandas as gpd

from dotenv import load_dotenv

load_dotenv()
os.getenv('GEMINI_API_KEY')

# Set Local environment
project_path = Path(__file__).resolve().parent.parent
#project_path = Path(os.getcwd()).resolve().parent
#project_path = Path('..').resolve()
print(f'Treating "{project_path}" as `project_path`')
sys.path.append(str(project_path))

# Local imports
from src.streetTransformer.locations.location import Location # This creates a Location object that holds and converts all of the data for each location
from src.streetTransformer.llms.run_gemini_model import run_individual_model # Runs a gemini model 
import src.streetTransformer.llms.models.imagery_describers.gemini_imagery_describers as gemini_imagery_describers
from src.streetTransformer.comparison.compare import get_image_compare_data, get_compare_data_for_location_id_years, show_images_side_by_side

traffic_calming_location_ids = [7571, 8887, 11738, 11800, 12116, 14271, 15283, 15375, 15709, 15852]

UNIVERSE_NAME = 'caprecon_plus_control'
universe_path = Path('..') / project_path / 'src/streetTransformer/data/universes/' / UNIVERSE_NAME
print(os.listdir(Path('..') / project_path / 'src/streetTransformer/'))
YEARS = list(range(2006, 2025, 2))
YEARS = list(range(2016, 2025, 2))
OUTFILE = project_path / 'src/streetTransformer/data/results/' / UNIVERSE_NAME / 'image_describer_trial1_normal.txt'
#MODEL_NAME = 'gemini-2.5-flash-lite'
MODEL_NAME = 'gemini-2.5-flash'


# 1) Load all locations from the project database
locations_gdf = gpd.read_feather(universe_path / 'locations.feather')
locations_gdf = locations_gdf.to_crs('4326')
locations_gdf = locations_gdf # For subsetting if necessary

# 2) Create Location Df
locations_gdf = locations_gdf[locations_gdf['location_id'].isin(traffic_calming_location_ids)]
total_locations = locations_gdf.shape[0]


def permute_years(years):
    # create all permutations of comparison years 
    permutations = []
    for y1 in years:
        for y2 in years:
            if y2 > y1:
                permutations.append((y1, y2))
    return permutations
    
year_pairs = permute_years(YEARS)

# Get comparison 
results = []
total_compares = len(traffic_calming_location_ids) * len(year_pairs)

gemini_client = genai.Client=genai.Client()

for l_id in tqdm.tqdm(traffic_calming_location_ids, total=len(traffic_calming_location_ids)):
    for start_year, end_year in tqdm.tqdm(year_pairs, total=len(year_pairs), desc='location_id={l_id}'):
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