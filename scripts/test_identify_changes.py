# Example Usage
# python scripts/change_identifier_test.py -s 2016 -e 2024 -z 2020 --outfile tests/change_dentifier_2016_2024.csv

import sys
from pathlib import Path
import json
import argparse
from typing import Optional

import geopandas as gpd

# Import from src
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent  # assuming scripts and src are siblings
sys.path.append(str(project_root))

from src.streetTransformer.llms.run_llm_model import run_model
from src.streetTransformer.utils.image_paths import get_imagery_reference_path

def parse_args():
    parser = argparse.ArgumentParser(
        description='Change Identifier Test Script'
    )

    # Add image paths Argument
    parser.add_argument('--startyear','-s', required=True, type=int)
    parser.add_argument('--endyear','-e', required=True, type=int)

    parser.add_argument(
        '--zlevel','-z', type=int, default=20,
        help='Zoom level: 1-20. Generally you will want 19 or 20.'
    )
    
    # outfile
    parser.add_argument('--outfile','-o', type=Path,
        help="A file path to write the results of the modeling to."
    )

    # data_path
    parser.add_argument(
        '--data_path','-d', type=Path,
        default='data/test_runs/downtown_bk',
        help='A file path to the root directory containing the data for this project'
    )

    parser.add_argument('--verbose','-v',type=bool)

    args = parser.parse_args()

    return args

def identify_changes(
        data_path:Path,
        zlevel:int,
        startyear:int, 
        endyear:int,
        outfile:Optional[Path]=None,
        verbose:bool=False,
        write:bool=False
):
    # Load the reference files
    file_start = gpd.read_file(get_imagery_reference_path(data_path, zlevel, startyear))
    file_end = gpd.read_file(get_imagery_reference_path(data_path, zlevel, endyear))
    
    # TODO: clean this up by using pd.read_csv and making the join more clear and less hacky
    combined_df = file_start.merge(file_end, left_on = ['field_1','name','geometry'], right_on=['field_1','name', 'geometry'], suffixes=['_start','_end']).rename(columns={'field_1': 'idx'})
    
    for row in combined_df.to_records():
        if Path(row['file_path_start']).is_file() and Path(row['file_path_end']).is_file():
            # Refactor: to run_model_once()?
            try:
                response = run_model('change_identifier', image_paths=[row['file_path_start'], row['file_path_end']], stream=True)
            except Exception as e:
                print(e)
            
            cleaned_response = response.replace("`", '').replace('json','')
            if verbose:
                print(cleaned_response)

            try:
                data = json.loads(cleaned_response)
                with open(outfile, 'a+', encoding='utf-8') as f:
                    f.write(f"{row['idx']}, {row['name']},  {json.dumps(data)}\n")

            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON {row['name']}: {e}")

if __name__ == '__main__':
    args = parse_args()

    identify_changes(**vars(args))
    