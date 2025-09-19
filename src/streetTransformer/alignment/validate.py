# This file is to validate the results of various LLM model outputs
from __future__ import annotations
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import Dict, List, Sequence, Callable, Literal, Optional, Iterable, Hashable, Any
from ..llms.queries import QueryOutput, ChangeIdentifierOutput, DaterOutput
from .sentence_compare import compare_sentence_pairs

from dataclasses import dataclass, fields

load_dotenv()
DB_PATH = Path(str(os.getenv('DB_PATH')))
print(DB_PATH)
OAI_PATH = DB_PATH.parent / 'data_oai_files'

from shapely.geometry import Polygon
import numpy as np
import pandas as pd
import geopandas as gpd

#from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

from sklearn.metrics import (
    # Classifier
    accuracy_score,
    precision_score, 
    recall_score, 
    f1_score, 
    classification_report,
    precision_recall_fscore_support,
    confusion_matrix,
    roc_auc_score,
    log_loss,
    # Identifier (tagger)
    hamming_loss, 
    jaccard_score
)

@dataclass
class ChangeIdentifierKey:
    location_id: int
    year_start:  str
    year_end:    str

@dataclass
class DaterKey:
    location_id: int

#-- Preprocessing --#
def _resolve_path(input_path: Path|str, type:str) -> Path:
    if Path(input_path).exists():
        return Path(input_path)
    elif type == 'results':
        oai_results_path = OAI_PATH / 'results' / input_path
        if oai_results_path.exists():
            return oai_results_path
    elif type == 'groundtruth': 
        db_gt_path = DB_PATH / 'groundtruth' / input_path
        if db_gt_path.exists():
            return db_gt_path
    else:
        raise FileNotFoundError(input_path)

def validation_table( # validation_table
        response_file:Path|str, 
        groundtruth_path:Path|str,  #:Sequence[ClassifierKey]? 
        true_class_col:str,
        pred_class_col:str,
        key_obj:Callable=ChangeIdentifierKey,
        results_obj:Callable=ChangeIdentifierOutput,
        dropna=True
    ):
    # TODO: these should take in objects that are the outputs of the queries. But for now its fine that they take in a file_path. 
    response_df = pd.read_json(_resolve_path(response_file, 'results'), lines=True)
    groundtruth_df = pd.read_parquet(_resolve_path(groundtruth_path, 'groundtruth'))

    # Parse Results
    results_df = response_df['output_text'].apply(pd.Series)
    results_cols = [f.name for f in fields(results_obj)]

    # Confirm columns exist
    if true_class_col not in groundtruth_df.columns:
        raise ValueError(f'"{true_class_col}" not in ground_truth_df!')
    
    if pred_class_col not in results_df.columns:
        raise ValueError(f'"{pred_class_col}" not in results_df!')
    
    # Get Id calls
    id_cols = [f.name for f in fields(key_obj)]

    if len(id_cols) > 1:
        key_expanded = response_df['item_id'].str.split('-', expand=True).set_axis(id_cols, axis=1)
    else:
        key_name = id_cols[0]
        key_expanded = response_df.rename(columns={'item_id': key_name})[key_name]

    unified_response_df = pd.concat([
        key_expanded,
        response_df['model'],
        results_df[results_cols]
    ], axis=1, join='inner')
    unified_response_df['location_id'] = unified_response_df['location_id'].astype(int)

    # Rename class cols
    groundtruth_df = groundtruth_df.rename(columns={true_class_col : 'true_class'})
    unified_response_df = unified_response_df.rename(columns={pred_class_col : 'pred_class'})

    validate_df = unified_response_df[id_cols + ['pred_class']].merge(
        groundtruth_df[id_cols + ['true_class']],
        on=id_cols,
        how='outer'
    )

    if dropna:
        original_size = validate_df.shape[0]
        validate_df = validate_df.dropna()
        new_size = validate_df.shape[0]
        print(f'{original_size - new_size} NA records removed')

    return validate_df

### - Validators - ###
def validate_classifier(
        validation_df:pd.DataFrame, 
        true_class_col:str='true_class', pred_class_col:str='pred_class',
        average = 'binary'
        ): 
    """Validates a classifier model using [insert metric], accuracy"""

    # Note: assumes they come in as boolean
    y_true = validation_df[true_class_col].to_numpy(dtype=np.bool_)
    y_pred = validation_df[pred_class_col].to_numpy(dtype=np.bool_)
    
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, average=average, zero_division=0),
        "recall": recall_score(y_true, y_pred, average=average, zero_division=0),
        "f1": f1_score(y_true, y_pred, average=average, zero_division=0),
    }
    return metrics

def validate_identifier(validation_df:pd.DataFrame,
    true_class_col:str='true_class', pred_class_col:str='pred_class',
) -> Dict[str, Any]:
    y_true = [x.tolist() for x in validation_df[true_class_col].tolist()]
    y_pred = validation_df[pred_class_col].tolist()

    assert len(y_true) == len(y_pred)
    micro_tp = micro_fp = micro_fn = exact = 0
    n = len(y_true)

    for t, p in zip(y_true, y_pred):
        tset = set(t or [])
        pset = set(p or [])
        tp = len(tset & pset)
        fp = len(pset - tset)
        fn = len(tset - pset)
        micro_tp += tp; micro_fp += fp; micro_fn += fn
        exact += int(tset == pset)

    def f1(tp, fp, fn):
        prec = 0.0 if tp + fp == 0 else tp / (tp + fp)
        rec  = 0.0 if tp + fn == 0 else tp / (tp + fn)
        return 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)

    subset_acc = 0.0 if n == 0 else exact / n
    micro_prec = 0.0 if (micro_tp + micro_fp) == 0 else micro_tp / (micro_tp + micro_fp)
    micro_rec  = 0.0 if (micro_tp + micro_fn) == 0 else micro_tp / (micro_tp + micro_fn)
    micro_f1   = f1(micro_tp, micro_fp, micro_fn)
    micro_jacc = 0.0 if (micro_tp + micro_fp + micro_fn) == 0 else micro_tp / (micro_tp + micro_fp + micro_fn)

    return {
        "subset_accuracy": subset_acc,
        "micro": {"precision": micro_prec, "recall": micro_rec, "f1": micro_f1, "jaccard": micro_jacc},
        "counts": {"tp": micro_tp, "fp": micro_fp, "fn": micro_fn, "n_samples": n},
    }
def validate_linker(results_file:Path, answers:Sequence) -> Sequence[bool]:
    results_df = pd.read_json(results_file, lines=True)
    

def validate_dater(
    validation_df:pd.DataFrame,
    true_class_col:str='true_class', pred_class_col:str='pred_class', #TODO: change to true_year
):
    y_true = validation_df[true_class_col].astype(str)
    y_pred = validation_df[pred_class_col].astype(str)
    
    accuracy = np.mean(y_true == y_pred)

    avg_distance = np.mean(np.abs(y_true - y_pred))

    return {
        "accuracy": accuracy,
        "avg_distance": avg_distance
    }

    # takes in a 

def _read_and_clean_summarizer_results(response_path:Path) -> pd.DataFrame:
    response_df = pd.read_json(OAI_PATH / 'results' / response_path, lines=True)
    results = response_df[['item_id', 'model']].copy()
    results['item_id'] = results['item_id'].str.strip("\"")
    results['text_output'] = response_df['output_text'].apply(pd.Series)['description']
    return results

def validate_summarizer(summaries1_path: Path, summaries2_path: Path):
    results1_df = _read_and_clean_summarizer_results(_resolve_path(summaries1_path, 'results'))
    results2_df = _read_and_clean_summarizer_results(_resolve_path(summaries2_path, 'results'))

    joined_summaries = results1_df.merge(
        results2_df,
        on = 'item_id',
        how='outer', indicator=True,
        suffixes=['_1', '_2']
    )

    joined_summaries = joined_summaries.dropna().reset_index()

    metrics = compare_sentence_pairs(
        joined_summaries['text_output_1'],
        joined_summaries['text_output_2']
    )

    metric_summaries = {k: m.mean() for k, m in metrics.items()}
    return metric_summaries
    
def bulk_validate(inputs:dict[tuple[str, str], str], 
                  validation_function:Callable, groundtruth_path:Path|str, 
                  true_class_col:str, pred_class_col:str,
                  key_obj:Callable=ChangeIdentifierKey, results_obj:Callable=ChangeIdentifierOutput,
                  metrics:Optional[list[str]]=None): 
    results = {}
    for key, response_file in inputs.items():
        val_df = validation_table(
            response_file    = response_file, 
            groundtruth_path = groundtruth_path,
            true_class_col   = true_class_col,
            pred_class_col   = pred_class_col,
            key_obj          = key_obj,
            results_obj      = results_obj
        ).dropna()
        print(val_df)
        results[key] = validation_function(val_df)

    return pd.DataFrame(results).T.reset_index(names=['format', 'model'])

if __name__ == '__main__':
    print(validation_table(
        'image_identifier-4o.csv', 
        'location_pair_change_identifier.parquet',
        'change_identifier_safety',
        'change_detected'
    ))

    print(validation_table(
        'sidebyside_identifier-4o.csv', 
        'location_pair_change_identifier.parquet',
        'change_identifier_safety',
        'change_detected'
    ))

    # print(set_up_validation_dataframe(
    #     'image_identifier-4o.csv', 
    #     'location_pair_change_identifier.parquet',
    #     'safety_scope_plus',
    #     'features'
    # ))