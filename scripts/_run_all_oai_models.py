from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import os
from typing import Optional

from streettransformer.llms.oai3 import bulk_query_on_df
from streettransformer.llms.models.queries import QUERIES

OAI_PATH = Path('data_oai_files')

SAMPLES_PATH = OAI_PATH / 'samples'
SAMPLES = [x for x in SAMPLES_PATH.iterdir()]

@dataclass
class QueryRun:
    query_name: str
    input_file: str|Path
    outfile_name: str|Path
    model: str
    head: Optional[int]=None
    test: Optional[int]=None

QUERY_RUNS = [
    # QueryRun(
    #     query_name = 'sidebyside_change_identifier',
    #     input_file = 'sidebyside_pairs',
    #     outfile_name = 'sidebyside_identifier-4o',
    #     model = 'gpt-4o'
    # ),
    # QueryRun(
    #     query_name = 'image_change_identifier',
    #     input_file = 'image_pairs',
    #     outfile_name = 'image_identifier-4o',
    #     model = 'gpt-4o'
    # ),
    # QueryRun(
    #     query_name = 'image_change_describer',
    #     input_file = 'image_pairs',
    #     outfile_name = 'image_summarizer-4o',
    #     model = 'gpt-5',
    #     test = True
    # ),
    QueryRun(
        query_name = 'image_change_dater',
        input_file = 'image_dater',
        outfile_name = 'dater-image-4o',
        model = 'gpt-4o',
        head = 500
    ),
    QueryRun(
        query_name = 'sidebyside_change_dater',
        input_file = 'sidebyside_dater',
        outfile_name = 'dater-sidebyside-4o',
        model = 'gpt-4o',
        head = 500
    ),
    # QueryRun(
    #     query_name = 'sidebyside_change_dater',
    #     input_file = 'sidebyside_dater',
    #     outfile_name = 'sidebyside_identifier-4o-lite',
    #     model = 'gpt-4o-lite',
    #     test = True
    # )
]

def run_all_models(qrs: list[QueryRun], quiet:bool=True):
    for qr in qrs:
        df = pd.read_csv(SAMPLES_PATH / f'{qr.input_file}.csv')
        if qr.head:
            df = df.head(qr.head)
        if qr.test:
            df = df.sample(qr.test)
            output_dir = OAI_PATH / 'test' / 'output'
        else:
            output_dir = OAI_PATH / 'results'

        outfile_path  = Path(output_dir) / f'{qr.outfile_name}.csv'

        try:
            query = QUERIES[qr.query_name]
            
        except Exception as e:
            print(f'{qr.query_name} not found in QUERIES!\n\tOptions are {", ".join(QUERIES.keys())}')
            raise e

        if not quiet:
            print(f'Running query text: {query.text()}')
        
        bulk_query_on_df(query, df=df, model=qr.model, outfile=outfile_path)

if __name__ == '__main__':
    run_all_models(QUERY_RUNS)