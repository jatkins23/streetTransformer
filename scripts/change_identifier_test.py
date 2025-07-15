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
        '--startyear',
        required=True,
        type=int
    )
    
    parser.add_argument(
        '--endyear',
        required=True,
        type=int
    )

    parser.add_argument(
        '--zlevel','-z',
        type=int,
        default=19,
        help='Provide a file containing labels '
    )

    parser.add_argument(
        '--outfile','-o',
        type=str,
        #default = f'{start_year}_{end_year}_change_test_results.csv'
    )

    args = parser.parse_args()

    return args.startyear, args.endyear, args.zlevel, args.outfile


if __name__ == '__main__':
    start_year, end_year, z_level, outfile = parse_args()

    file_end = gpd.read_file(f'data/dt_bk/images_z{z_level}_{end_year}.csv')
    file_start = gpd.read_file(f'data/dt_bk/images_z{z_level}_{start_year}.csv')

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
                with open(outfile, 'a+', encoding='utf-8') as f:
                    f.write(f"{row['idx']}, {row['name']},  {json.dumps(data)}\n")

            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON {row['name']}: {e}")

        
