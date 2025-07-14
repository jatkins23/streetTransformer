import os
import sys
from pathlib import Path
import json

import geopandas as gpd
import pandas as pd

# Import from src
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent  # assuming scripts and src are siblings
sys.path.append(str(project_root))

from src.llms.run_llm_model import run_model


if __name__ == '__main__':
    z2024 = gpd.read_file('data/dt_bk/images_z19_2024.csv')
    z2018 = gpd.read_file('data/dt_bk/images_z19_2018.csv')

    df2018_2024 = z2018.merge(z2024, left_on = ['field_1','name','geometry'], right_on=['field_1','name', 'geometry'], suffixes=['_2018','_2024'])

    print(df2018_2024.shape)
    for row in df2018_2024.to_records():
        if Path(row['file_path_2024']).is_file() and Path(row['file_path_2018']).is_file():
            print(row['name'])
            response = run_model('change_identifier', image_paths=[row['file_path_2018'], row['file_path_2024']])
        
            try:
                data = json.loads(response)
                data[0]['name'] = row['name']
                with open('data/dt_bk/change_test_results.csv', 'a+', encoding='utf-8') as f:
                    f.write(json.dumps(data))

            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON {row['name']}: {e}")

        
