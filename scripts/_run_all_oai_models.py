from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import os
from typing import Optional

from streettransformer.llms.oai3 import bulk_query_on_df
from streettransformer.llms.queries import QUERIES

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
    QueryRun( # Dater - Image - 4o
        query_name = 'image_change_dater',
        input_file = 'image_dater',
        outfile_name = 'dater-image-4o',
        model = 'gpt-4o',
    ),
    QueryRun( # Dater - SidebySide - 4o
        query_name = 'sidebyside_change_dater',
        input_file = 'sidebyside_dater',
        outfile_name = 'dater-sidebyside-4o',
        model = 'gpt-4o',
    ),
    QueryRun( # Dater - Image - 5
        query_name = 'image_change_dater',
        input_file = 'image_dater',
        outfile_name = 'dater-image-5',
        model = 'gpt-4o',
        head=100
    ),
    # 4o
    QueryRun( # Change ID - Image - 4o
        query_name = 'image_change_identifier',
        input_file = 'image_pairs',
        outfile_name = 'identifier-image-4o',
        model = 'gpt-4o'
    ),
    QueryRun( # Change ID - SbS - 4o
        query_name = 'sidebyside_change_identifier',
        input_file = 'sidebyside_pairs',
        outfile_name = 'identifier-sidebyside-4o',
        model = 'gpt-4o'
    ),
    QueryRun( # Describer - Image - 4o
        query_name = 'image_change_describer',
        input_file = 'image_describers',
        outfile_name = 'summarizer-image-4o',
        model = 'gpt-4o',
    ),
    QueryRun( # Describer - SbS - 4o
        query_name = 'sidebyside_change_describer',
        input_file = 'sidebyside_describers',
        outfile_name = 'summarizer-sidebyside-4o',
        model = 'gpt-4o',
    ),
    QueryRun( # Describer - Document - 4o
        query_name = 'document_summarizer',
        input_file = 'document_describers',
        outfile_name = 'summarizer-document-4o',
        model = 'gpt-4o',
    ),
    QueryRun( # FeatureTagger - Document - 4o
        query_name = 'document_feature_tagger',
        input_file = 'document_describers',
        outfile_name = 'featuretagger-document-4o',
        model = 'gpt-4o',
        head = 100
    ),
    QueryRun( # Dater - Image - 4o
        query_name = 'image_change_dater',
        input_file = 'image_dater',
        outfile_name = 'dater-image-4o',
        model = 'gpt-4o',
        head = 500
    ),
    QueryRun( # Dater - SidebySide - 4o
        query_name = 'sidebyside_change_dater',
        input_file = 'sidebyside_dater',
        outfile_name = 'dater-sidebyside-4o',
        model = 'gpt-4o',
        head = 500
    ),
    QueryRun( # Dater - SidebySide - 5
        query_name = 'sidebyside_change_dater',
        input_file = 'sidebyside_dater',
        outfile_name = 'dater-sidebyside-5',
        model = 'gpt-5',
        head=100
    ),
    # 5
    QueryRun( # Change ID - SbS - 5
        query_name = 'sidebyside_change_identifier',
        input_file = 'sidebyside_pairs',
        outfile_name = 'identifier-sidebyside-5',
        model = 'gpt-5',
        head=100
    ),
    QueryRun( # Change ID - Image - 5
        query_name = 'image_change_identifier',
        input_file = 'image_pairs',
        outfile_name = 'identifier-image-5',
        model = 'gpt-5',
        head=100
    ),
    # QueryRun( # Describer - Image - 4o
    #     query_name = 'image_change_describer',
    #     input_file = 'image_describers',
    #     outfile_name = 'summarizer-image-4o',
    #     model = 'gpt-4o'
    # ),
    # QueryRun( # Describer - SbS - 4o
    #     query_name = 'sidebyside_change_describer',
    #     input_file = 'sidebyside_describers',
    #     outfile_name = 'summarizer-sidebyside-4o',
    #     model = 'gpt-4o',
    # ),
    # QueryRun( # Describer - Document - 4o
    #     query_name = 'document_summarizer',
    #     input_file = 'document_describers',
    #     outfile_name = 'summarizer-document-4o',
    #     model = 'gpt-4o',
    # ),
    # QueryRun( # FeatureTagger - Document - 4o
    #     query_name = 'document_feature_tagger',
    #     input_file = 'document_describers',
    #     outfile_name = 'featuretagger-document-4o',
    #     model = 'gpt-4o',
    #     head = 100
    # ),
    # QueryRun( # Dater - Image - 4o
    #     query_name = 'image_change_dater',
    #     input_file = 'image_dater',
    #     outfile_name = 'dater-image-4o',
    #     model = 'gpt-4o',
    #     head = 500
    # ),
    # QueryRun( # Dater - SidebySide - 4o
    #     query_name = 'sidebyside_change_dater',
    #     input_file = 'sidebyside_dater',
    #     outfile_name = 'dater-sidebyside-4o',
    #     model = 'gpt-4o',
    #     head = 500
    # ),
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
    run_all_models(QUERY_RUNS, quiet=True)