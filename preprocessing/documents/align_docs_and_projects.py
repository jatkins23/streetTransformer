# Note: this kinda works but is mostly not useful since I need to call the geocode_crossstreets_census

#import os
from pathlib import Path
#from typing  import List

import json
import numpy as np
import pandas as pd
import geopandas as gpd

from ..config import DATA_PATH, UNIVERSES_PATH, DOCUMENTS_PATH

# Universe
UNIVERSE_NAME = 'caprecon3'
UNIVERSE_PATH = UNIVERSES_PATH / UNIVERSE_NAME

# Documents
documents_df = pd.read_csv(DOCUMENTS_PATH / 'projects_df.csv', index_col=0, na_values='.')

# Imagery
IMAGERY_PATH = UNIVERSE_PATH / 'imagery/'

# Locations
LOCATIONS_PATH = UNIVERSE_PATH / 'locations.feather'

locations_gdf = gpd.read_feather(LOCATIONS_PATH)
DOCUMENTS_PROCESSED_PATH = DATA_PATH / 'processing/documents/raw_to_gemini_crossstreets'
documents_ndjson = DOCUMENTS_PROCESSED_PATH / 'gemini_output.ndjson'

## Pipeline

# This is the real pipeline
def _load_json_safe(x):
    try: 
        return json.loads(x)
    except Exception as e:
        #print(x, e)
        return ''


def load_documents_geocoded(ndjson_path=documents_ndjson):
    print(ndjson_path)
    return pd.read_json(ndjson_path, lines=True)#.set_index('id')

def _swap_latlng(input_gdf:gpd.GeoDataFrame) -> gpd.GeoDataFrame: 
    return_gdf = input_gdf.copy()
    saved_lats = return_gdf['lat']
    swap_latlngs = return_gdf[saved_lats < 0][['lat','lng']]

    return_gdf.loc[swap_latlngs.index, ['lng','lat']] = swap_latlngs.values
    
    return return_gdf

def parse_documents_json(documents_geocoded_json, clean_periods:bool=True) -> pd.DataFrame: 
    # 
    document_ids = documents_geocoded_json['id']
    documents_text = documents_geocoded_json['text']
    
    # Clean the text portion
    cleaned_text = (
        documents_text
        .str.replace(r'\s+', ' ', regex=True)
        .str.strip()
    )
    
    # Parse the JSON 
    parsed_json = cleaned_text.apply(_load_json_safe)

    # Flatten list-like JSONs into one long Series of dicts
    flat_series = (
        parsed_json.dropna()
            .map(lambda v: v if isinstance(v, (list, tuple)) else [v])
            .explode()
    )
    
    # Save the index

    #document_ids = flat_series.index

    # Recreate json dataframe
    flat_df = pd.json_normalize(flat_series)
    flat_df['document_id'] = document_ids

    if clean_periods:
        flat_df.replace('.', np.nan) # TODO

    return flat_df

def _make_coordinates_df(coords_series:pd.Series):
    coordinates_df = pd.DataFrame(
        coords_series.tolist(),
        index=coords_series.index,
        #columns=['lat','lng']
    )
    coordinates_df = coordinates_df.iloc[:,0:2]
    coordinates_df.columns = ['lat','lng']

    return coordinates_df

def clean_parsed_df(flat_df:pd.DataFrame, clean_periods:bool=True) -> gpd.GeoDataFrame: 
    # Generate coordinates columns for those with 
    coords_series = flat_df.dropna(subset='coordinates')['coordinates']
    
    coordinates_df = _make_coordinates_df(coords_series)
    
    # join them back
    merged_df = flat_df.merge(
        coordinates_df,
        left_index=True, right_index=True,
        how='left'
    )

    # convert back to GDF
    if clean_periods:
        merged_df['lat'] = merged_df['lat'].replace(r'^\.$', str(np.nan), regex=True).astype(float).replace(0, np.nan)
        merged_df['lng'] = merged_df['lng'].replace(r'^\.$', str(np.nan), regex=True).astype(float).replace(0, np.nan)

    merged_gdf = gpd.GeoDataFrame(
        merged_df, 
        geometry=gpd.points_from_xy(merged_df['lng'], merged_df['lat']), 
        crs='4326'
    )

    merged_gdf_confirmed = _swap_latlng(merged_gdf)

    return merged_gdf_confirmed

def pipeline(documents_ndjson_path):
    documents_gecoded = load_documents_geocoded(documents_ndjson_path)
    #documents_gecoded
    flat_df = parse_documents_json(documents_gecoded)

    parsed_gdf =  clean_parsed_df(flat_df)

    return parsed_gdf
    

if __name__ == '__main__':
    print(pipeline(DOCUMENTS_PROCESSED_PATH / 'gemini_output.ndjson'))
    # print(pipeline(DOCUMENTS_PROCESSED_PATH / 'gemini_output2.ndjson'))