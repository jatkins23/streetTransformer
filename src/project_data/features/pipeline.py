import os, sys
from pathlib import Path
from typing import Dict, List, Optional
import argparse


import pandas as pd
import geopandas as gpd
import numpy as np
#from geopandas import CRS
from shapely import from_wkt

src_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(src_dir))
from utils.geodata import safe_load_wkt
from project_data.features.clean import clean_bike_rtes, clean_bus_lanes, clean_ped_plaza, clean_traffic_calming
from project_data.features.load import load_standard
from project_data.features.summarize import count_features_by_location
from data_load.load_intersections import load_location

from dotenv import load_dotenv
load_dotenv()

ROOT_PATH = src_dir.parent / Path(str(os.getenv('OPENNYC_PATH')))
FEATURE_METADATA = {
    'bike_rtes': {'file_path': 'New_York_City_Bike_Routes_20250722.csv', 'load_method': 'standard', 'clean_method': 'clean_bike_rtes', 
                  'shorthand': 'bike', 'date_col': 'installdate'},
    'bus_lanes': {'file_path': 'Bus_Lanes_-_Local_Streets_20250721.csv', 'load_method': 'standard', 'clean_method': 'clean_bus_lanes', 
                  'shorthand': 'bus', 'date_col': 'lastupdate'},
    'ped_plaza': {'file_path': 'NYC_DOT_Pedestrian_Plazas__Point_Feature__20250721.csv', 'load_method': 'standard', 'clean_method': 'clean_ped_plaza', 
                  'shorthand': 'plaza', 'date_col': ''},
    'traffic_calming': {'file_path': 'VZV_Turn_Traffic_Calming_20250721.csv', 'load_method': 'standard', 'clean_method': 'clean_traffic_calming', 'shorthand': 'calm', 'date_col': 'installdate'}
}

def buffer_locations(location_nodes, buffer_width=100, crs='EPSG:2263'): #crs:CRS='EPSG'):
    location_nodes['buffer'] = location_nodes.to_crs(crs).buffer(buffer_width)
    location_buffers = location_nodes.set_geometry('buffer')

    return location_buffers


# TODO the `[load|clean|summarize]_all_files` functions are extemely duplicative and can be 
def load_all_files(feat_metadata:Dict[str, Dict], root_data_path:Path, silent:bool=False) -> Dict[str, gpd.GeoDataFrame]:

    loaded_gdfs = {}
    if not silent:
        print('\nLoading Feature Files..')

    for feat, feat_data in feat_metadata.items():
        if 'file_path' not in feat_data.keys():
            raise Exception(f"{feat}: `file_path` doesn't appear in provided metadata!")
        
        if 'load_method' not in feat_data.keys():
            raise Exception(f"{feat}: `load_method` doesn't appear in provided metadata!")
            
        if feat_data['load_method'] == 'standard':
            load_method = globals()['load_standard'] #
        else:
            load_method = feat_data['load_method']

        # Now try loading 
        try:
            loaded_gdfs[feat] = load_method(root_data_path / Path(feat_data['file_path']))
            if not silent:
                print(f'\t{feat}: Success!')
        except Exception as e:
            print(f'\t{feat}: Fail! {e}')

    return loaded_gdfs


def clean_all_files(loaded_gdfs:Dict[str, gpd.GeoDataFrame], feat_metadata:Dict[str, Dict], silent:bool=False) -> Dict[str, gpd.GeoDataFrame]:
    cleaned_gdfs = {}

    if not silent:
        print('\nCleaning Feature Files..')
    
    for feat, feat_data in feat_metadata.items():
        if 'clean_method' not in feat_data.keys():
            raise Exception(f"{feat}: `clean_method` doesn't appear in provided metadata!")
        
        clean_method = globals()[feat_data['clean_method']] # TODO: refactor into getattr
        
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

def pipeline(location:str, silent:bool=False, outfile:Optional[Path|str]=None):
    # Load locations
    nodes, _ = load_location(location) # TODO: add `silent` 

    # Load and clean features
    loaded_gdfs = load_all_files(FEATURE_METADATA, ROOT_PATH, silent=silent)
    cleaned_gdfs = clean_all_files(loaded_gdfs, FEATURE_METADATA, silent=silent)
    
    # Project features 
    cleaned_gdfs = {k: v.set_crs('4326') for k, v in cleaned_gdfs.items()}
    cleaned_gdfs_p = {k: v.to_crs('2263') for k, v in cleaned_gdfs.items()}
    
    location_buffers = buffer_locations(nodes)

    summarized_gdf = summarize_all_features(location_buffers, cleaned_gdfs_p, features_to_summarize=['bike_rtes','bus_lanes','ped_plaza','traffic_calming'])

    # If outfile:
    if outfile:
        summarized_gdf.to_csv(outfile, index=True)

    return summarized_gdf

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collect Project Data from Project Files')

    parser.add_argument('location', type=str, help="Specify location")
    parser.add_argument('-s','--silent', default=False, help="Run in silent mode (minimize console output)")
    parser.add_argument('-o','--outfile', type=Path, help="Path to the output file")

    args = parser.parse_args()
    
    output = pipeline(**vars(args))
    print(output)
    

