# Example Usage
# python scripts/change_identifier_test.py -s 2016 -e 2024 -z 2020 --outfile tests/change_dentifier_2016_2024.csv

import sys
from pathlib import Path
import json
import argparse

import geopandas as gpd

# Import from src
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent  # assuming scripts and src are siblings
sys.path.append(str(project_root))

from src.llms.run_llm_model import run_model

def parse_args():
    parser = argparse.ArgumentParser(
        description='Change comparison Script'
    )

    # Add image paths Argument
    parser.add_argument(
        '--startyear','-s',
        required=True,
        type=int
    )
    
    parser.add_argument(
        '--endyear','-e',
        required=True,
        type=int
    )

    parser.add_argument(
        '--zlevel','-z',
        type=int,
        default=20,
        help='Zoom level for the imagery. 1-20. Generally you will want 19 or 20'
    )

    parser.add_argument(
        '--outfile','-o',
        type=Path,
        help="A file path to write the results of the modeling to"
    )

    parser.add_argument(
        '--data_path','-d',
        type=Path,
        default='data/test_runs/downtown_bk',
        help='A file path to the root directory containing the data for this project'
    )

    args = parser.parse_args()

    return args

def _get_ref_route(root_path:Path, zlevel:int, year:int) -> Path:
    """_summary_

    Args:
        root_path (Path): the data root directory path from the `data_path` argument

    Returns:
        Path: A path to the directory contianing the reference materials
    """
    
    # TODO: better error handling for values that just don't exist in the database
    if zlevel not in [19,20]:
        raise ValueError(f'`zlevel` "{zlevel}" not available. Check source data')
    if year not in range(2006, 2025, 2):
        raise ValueError(f'`year` "{year}" not available. Check source data')
    
    file_name = f'image_refs_z{zlevel}_{year}.csv'

    return root_path / "imagery" / "processed" / "refs" / file_name

if __name__ == '__main__':
    args = parse_args()

    # Load the reference files
    file_start = gpd.read_file(_get_ref_route(args.data_path, args.zlevel, args.startyear))
    file_end = gpd.read_file(_get_ref_route(args.data_path, args.zlevel, args.endyear))
    
    # TODO: clean this up by using pd.read_csv and making the join more clear and less hacky
    combined_df = file_start.merge(file_end, left_on = ['field_1','name','geometry'], right_on=['field_1','name', 'geometry'], suffixes=['_start','_end']).rename(columns={'field_1': 'idx'})
    
    for row in combined_df.to_records():
        if Path(row['file_path_start']).is_file() and Path(row['file_path_end']).is_file():
            try:
                response = run_model('change_identifier', image_paths=[row['file_path_start'], row['file_path_end']], stream=True)
            except Exception as e:
                print(e)
            
            cleaned_response = response.replace("`", '').replace('json','')
            print(cleaned_response)
            try:
                data = json.loads(cleaned_response)
                with open(args.outfile, 'a+', encoding='utf-8') as f:
                    f.write(f"{row['idx']}, {row['name']},  {json.dumps(data)}\n")

            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON {row['name']}: {e}")

        
