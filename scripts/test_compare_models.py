# Example Usage
# python scripts/change_identifier_test.py -s 2016 -e 2024 -z 2020 --outfile tests/change_dentifier_2016_2024.csv

import os, sys
from pathlib import Path
import json
import argparse
from typing import List, Dict, Optional

import geopandas as gpd
import pandas as pd

# Import from src
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent  # assuming scripts and src are siblings
sys.path.append(str(project_root))

from src.llms.run_llm_model import run_model
from src.viz.compare_images import create_comparison_figure, load_images, save_figure

from src.utils.tiles import assemble_location_imagery
import matplotlib.pyplot as plt

def parse_args():
    parser = argparse.ArgumentParser(description = 'Generic Model Tester: Intersection')

    parser.add_argument('-location_id','-i', required=True, type=int)
    parser.add_argument('-years','-y', required=True, type=int, 
                        nargs=2, help='Two years to proces.s')
    parser.add_argument('--zlevel','-z', type=int, default=20,
                        help='Zoom level: 1-20. Generally you will want 19 or 20.')
    parser.add_argument('--models','-m', required=True, type=str, nargs='+', help='TODO:')
    parser.add_argument('--outfile','-o', type=Path, help="A file path to write the results of the modeling to.")
    parser.add_argument(
        '--data_path','-d', type=Path,
        default=Path(str(os.getenv('DATA_URL'))),
        help='A file path to the root directory containing the data for this project'
    )
    parser.add_argument(
        '--no-stream', type=bool, default=False, 
        help='Turn off streaming for the model. Streaming responses will help it not crash.'
    )

    args = parser.parse_args()

    return args
    


# For a given intersection, and set of year:
    # gather all imagery
    # combine into a list and export
    # feed to the model

# TODO: Refactor
from src.utils.tiles import get_imagery_reference_path

# TODO: refactor this into its own function that can be used elsewher

def run_all_models(
        models:List[str],
        image_paths:List[Path],
        stream:bool
) -> Dict[int, str]:
    model_responses = {}
    for model in models:
        response = run_model(model, image_paths=image_paths, stream=stream)
        response_cleaned = response.replace("`", '').replace('json','')

        try:
            model_responses[model] = json.loads(response_cleaned)
        except Exception as e:
            print(f'{model}: {e}')
        
    return model_responses


import json
from tabulate import tabulate

def frmat_model_response_HTML(response_dict:Dict):
    pass

def format_model_response_ascii_table(response_dict:Dict) -> str:
    rows = []
    for model_name, parsed in response_dict.items():
        significant_changes = parsed.get("significant_changes", "")
        confidence = parsed.get("confidence", "")
        manual_refernce = parsed.get("manual_refernce", "")
        rows.append([model_name, significant_changes, confidence, manual_refernce])

    headers = ["Model Name", "Significant Changes", "Confidence", "Manual Refernce"]
    table = tabulate(rows, headers, tablefmt="grid")
    return table

def format_response_generic(response_dict:Dict) -> str: # TODO: add `model` type. Figure out what to do about json data type 
    #rows = [f'model_name for ]
    rows = []
    for model_name, parsed in response_dict.items():
        row = f'**{model_name}**: {parsed}'
        rows.append(row)

    rows_joined =  "\n".join(rows)
    
    return 'Model Comparison\n' + rows_joined

def compare_models(
        location_id:int,
        models:List[str],
        data_path:Path,
        years:List[int],
        zlevel:int=20,
        outfile:Optional[Path]=None,
        no_stream:bool=True
    ) -> plt.Figure:
    
    # Gather all image paths
    image_paths = assemble_location_imagery(location_id, data_path, years, zlevel)
    image_paths_list = list(image_paths.values())

    # Run all models
    model_responses = run_all_models(models, image_paths_list, not(no_stream))

    # Format Responses
    response_text = "-\n-\n-\n-\n" + format_response_generic(model_responses)

    # Load Images -- TODO: Deal with this by refactoring get_imagery_reference_path
    ref_dir_path = data_path / "imagery" / "processed" / "refs" 
    title, start_image, end_image = load_images(location_id, years[0], years[1], zlevel, ref_dir_path)
    
    # Build dashboard
    fig = create_comparison_figure(
        title, start_image, end_image, 
        start_year=years[0], end_year=years[1],
        caption=response_text
    )

    # Save (if requested)
    if outfile:
        save_figure(fig, outfile, 300)

    return fig

if __name__ == '__main__':
    args = parse_args()

    fig = compare_models(**vars(args))
    # Display the change
    plt.show()

# TODO: find a way for it to gather model data from a file, not just re-run it