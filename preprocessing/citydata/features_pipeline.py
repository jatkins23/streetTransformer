import os, sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import argparse


import pandas as pd
import geopandas as gpd
import numpy as np
#from geopandas import CRS
from shapely import from_wkt

project_dir = Path(__file__).resolve().parent.parent.parent
print(f"Treating '{project_dir}' as `project_dir`")
sys.path.append(str(project_dir))

#from src.streetTransformer.utils.geodata import safe_load_wkt
from features.load import load_standard
from features.clean import clean_bike_rtes, clean_bus_lanes, clean_ped_plaza, clean_traffic_calming # Note: used in 
from features.summarize import count_features_by_location
#from preprocessing.data_load.load_intersections import load_location
from geoprocessing import buffer_locations
from preprocessing.data_load.load_lion import load_lion_default

from dotenv import load_dotenv
load_dotenv()

ROOT_PATH = project_dir / Path(str(os.getenv('OPENNYC_PATH')))
FEATURE_METADATA = {
    'bike_rtes': {'file_path': 'New_York_City_Bike_Routes_20250722.csv', 
                  'load_method': 'standard', 'clean_method': 'clean_bike_rtes', 
                  'shorthand': 'bike', 'date_col': 'installdate'},
    'bus_lanes': {'file_path': 'Bus_Lanes_-_Local_Streets_20250721.csv', 
                  'load_method': 'standard', 'clean_method': 'clean_bus_lanes', 
                  'shorthand': 'bus', 'date_col': 'lastupdate'},
    'ped_plaza': {'file_path': 'NYC_DOT_Pedestrian_Plazas__Point_Feature__20250721.csv', 
                  'load_method': 'standard', 'clean_method': 'clean_ped_plaza', 
                  'shorthand': 'plaza', 'date_col': ''},
    'traffic_calming': {'file_path': 'VZV_Turn_Traffic_Calming_20250721.csv', 
                        'load_method': 'standard', 'clean_method': 'clean_traffic_calming', 
                        'shorthand': 'calm', 'date_col': 'installdate'}
}

# TODO the `[load|clean|summarize]_all_files` functions are extemely duplicative and can be 
def load_all_feature_files(feat_metadata:Dict[str, Dict], root_data_path:Path, silent:bool=False) -> Dict[str, gpd.GeoDataFrame]:

    loaded_gdfs = {}
    if not silent:
        print('\nLoading Feature Files..')

    for feat, feat_data in feat_metadata.items():
        if 'file_path' not in feat_data.keys(): # TODO: Switch to errors/validator
            raise Exception(f"{feat}: `file_path` doesn't appear in provided metadata!")
        
        if 'load_method' not in feat_data.keys():
            raise Exception(f"{feat}: `load_method` doesn't appear in provided metadata!")
            
        if feat_data['load_method'] == 'standard':
            load_method = load_standard # TODO: not wure
        else:
            load_method = feat_data['load_method']

        # Now try loading 
        try:
            loaded_gdfs[feat] = load_method(root_data_path / Path(feat_data['file_path']))
            if not silent:
                print(f'\t{feat}: Success!')
        except Exception as e: # TODO: Can replace with
            print(f'\t{feat}: Fail! {e}')

    return loaded_gdfs


def clean_all_feature_files(loaded_gdfs:Dict[str, gpd.GeoDataFrame], feat_metadata:Dict[str, Dict], silent:bool=False) -> Dict[str, gpd.GeoDataFrame]:
    cleaned_gdfs = {}

    if not silent:
        print('\nCleaning Feature Files..')
    
    for feat, feat_data in feat_metadata.items():
        if 'clean_method' not in feat_data.keys():
            raise Exception(f"{feat}: `clean_method` doesn't appear in provided metadata!")
        
        clean_method = feat_data['clean_method'] # TODO: refactor into getattr
        
        try:
            cleaned_gdfs[feat] = clean_method(loaded_gdfs[feat])
            if not silent:
                print(f'\t{feat}: Success!')
        except Exception as e:
            print(f'\t{feat}: Fail! {e}')
    
    return cleaned_gdfs

def summarize_all_features(location_buffers:gpd.GeoDataFrame, cleaned_gdfs_p:Dict[str, gpd.GeoDataFrame], 
                       features_to_summarize:List[str], silent:bool=False) -> gpd.GeoDataFrame:
    summarized_gdf = location_buffers

    if not silent:
        print('\nSummarizing Feature Files..')

    for feat in features_to_summarize:
        if feat not in FEATURE_METADATA.keys():
            raise Exception(f"Feature '{feat}' not found in FEATURE_METADATA")
        
        # Load metadata
        metadata = FEATURE_METADATA[feat]
        
        try:
            counts = count_features_by_location(location_buffers, cleaned_gdfs_p[feat], feature_shorthand = metadata['shorthand'])
            if not silent:
                print(f"\t{feat}: Success!")
        except Exception as e:
            counts = np.nan
            print(f'\t{feat}: {e}')
            
        summarized_gdf[f"n_{metadata['shorthand']}"] = counts

    return summarized_gdf 

def count_features_by_buffer(universe:str, buffer_width:int=100, silent:bool=False, outfile:Optional[Path|str]=None):
    """Count the feautres of given type within a certain buffer-zone of given locations

    Args:
        universe (str): A streetTransformer universe. This is either a saved universe that exists in `streetTransformer/data/universes` or a new location which will create one
        buffer_width (int, optional): _description_. Defaults to 100.
        silent (bool, optional): _description_. Defaults to False.
        outfile (Optional[Path | str], optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    # Load locations for the given unverse
    #nodes, _ = load_location(universe) # TODO: add `silent` 
    nodes = load_lion_default(universe) # TODO: see load_lion_default

    # Load and clean features
    loaded_gdfs = load_all_feature_files(FEATURE_METADATA, ROOT_PATH, silent=silent)
    cleaned_gdfs = clean_all_feature_files(loaded_gdfs, FEATURE_METADATA, silent=silent)
    
    # Project features 
    cleaned_gdfs = {k: v.set_crs('4326') for k, v in cleaned_gdfs.items()}
    cleaned_gdfs_p = {k: v.to_crs('2263') for k, v in cleaned_gdfs.items()}
    
    # Create buffers with width `buffer_width`
    location_buffers = buffer_locations(nodes, buffer_width=buffer_width)

    # summarize
    summarized_gdf = summarize_all_features(
        location_buffers, cleaned_gdfs_p, 
        features_to_summarize=['bike_rtes','bus_lanes','ped_plaza','traffic_calming'])

    # If outfile:
    if outfile:
        summarized_gdf.to_csv(outfile, index=True)

    return summarized_gdf

def count_features_by_buffer_time(universe:str, buffer_width:int=100, date:datetime|str='now', silent:bool=False, outfile:Optional[Path|str]=None):
    # Update the previous function with some time element. Can actually probably replace it.
    pass

if __name__ == '__main__':
    # Parse args
    parser = argparse.ArgumentParser(description='Collect Project Features from City Data Files')

    parser.add_argument('universe', type=str, help="Specify universe. Either a saved one or a place to geocode. e.g.: 'nyc' or 'Downtown Brooklyn, New York, USA'")
    parser.add_argument('-o','--outfile', type=Path, help="Path to the output file")
    parser.add_argument('-s','--silent', default=False, help="Run in silent mode (minimize console output)")

    args = parser.parse_args()

    # Count Features by buffer    
    output = count_features_by_buffer(**vars(args))
    print(output)
    

