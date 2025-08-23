import os, sys
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import argparse

import pandas as pd
import geopandas as gpd

from .features.load import load_standard
from .geoprocessing import buffer_locations # This is awkward
from ..data_load.load_lion import load_lion_default

from streettransformer.config.constants import DATA_PATH

OPENNYC_DATA_PATH = DATA_PATH / 'raw' / 'citydata' / 'openNYC'
CORE_FILE_NAME = Path('Street_and_Highway_Capital_Reconstruction_Projects_-_Intersection_20250721.csv')

#sts_hwys_df = pd.read_csv(DATA_PATH / CORE_FILE_NAME)
#gpd.GeoDataFrame(sts_hwys_df, geometry= from_wkt(sts_hwys_df['the_geom']))

COLUMNS_TO_KEEP = ['ProjectID','ProjTitle', 'FMSID', 'FMSAgencyID',
       'LeadAgency', 'Managing Agency', 'ProjectDescription',
       'ProjectTypeCode', 'ProjectType', 'ProjectStatus', 'ConstructionFY',
       'DesignStartDate', 'ConstructionEndDate', 'CurrentFunding',
       'ProjectCost', 'OversallScope', 'SafetyScope', 'OtherScope',
       'ProjectJustification', 'OnStreetName', 'FromStreetName',
       'ToStreetName', 'OFTCode', 'DesignFY','geometry']

def load_caprecon_file(universe:str='nyc', data_path=OPENNYC_DATA_PATH, source_file_name=CORE_FILE_NAME) -> gpd.GeoDataFrame:
    source_file_path = data_path / source_file_name

    projects_gdf = load_standard(source_file_path) # TODO: confirm
    filtered_caprecon_gdf = projects_gdf[projects_gdf['ProjectType'] == 'CAPITAL RECONSTRUCTION'][COLUMNS_TO_KEEP]

    # clip to the universe
    if universe != 'nyc': # TODO: I should write a function that searches for a universe config and clips a given gdf by it.
        pass

    return filtered_caprecon_gdf


def gather_capital_projects_for_locations(locations_gdf:gpd.GeoDataFrame, outfile:Optional[Path|str]=None, buffer_width:int=100, silent:bool=False) -> gpd.GeoDataFrame:
    # Load and clean features
    # loaded_gdfs = load_all_files(FEATURE_METADATA, ROOT_PATH, silent=silent)
    # cleaned_gdfs = clean_all_files(loaded_gdfs, FEATURE_METADATA, silent=silent)
    
    # Project features 
    # cleaned_gdfs = {k: v.set_crs('4326') for k, v in cleaned_gdfs.items()}
    # cleaned_gdfs_p = {k: v.to_crs('2263') for k, v in cleaned_gdfs.items()}
    projects_gdf = load_caprecon_file(data_path=OPENNYC_DATA_PATH, source_file_name=CORE_FILE_NAME) # maybe set crs('4326')
    projects_gdf_p = projects_gdf.to_crs('2263') # TODO: store crs in config somewhere
    
    # Create buffers with width `buffer_width`
    location_buffers = buffer_locations(locations_gdf, buffer_width=buffer_width)

    # summarize
    location_projects_gdf = location_buffers.sjoin(
        projects_gdf_p,
        how='inner'
    ).rename(columns = {'index_right': 'project_id'})[
        locations_gdf.columns.tolist() + 
        ['project_id','ProjectID','ProjTitle','ProjectType', 'ProjectStatus', 'ConstructionFY',
         'DesignStartDate', 'ConstructionEndDate', 'CurrentFunding',
         'ProjectCost', 'OversallScope', 'SafetyScope', 'OtherScope',
         'ProjectJustification', 'OnStreetName', 'FromStreetName']]
    location_projects_gdf = location_projects_gdf.set_geometry('geometry') # TODO: Refactor this or just clean up
    
    # If outfile:
    if outfile:
        location_projects_gdf.to_csv(outfile, index=True) # TODO: this shouldn't work

    # So this is load, need to then do the summarize. sHERE HERE

    return location_projects_gdf

if __name__ == '__main__':
    # This is kinda gonna just copy the `features_pipeline`. TOOD: Refactor into a factory?

    # Parse Args
    parser = argparse.ArgumentParser(description='Collect Project Details from City Data Files')

    parser.add_argument('universe', type=str, help="Specify universe. Either a saved one or a place to geocode. e.g.: 'nyc' or 'Downtown Brooklyn, New York, USA'")
    parser.add_argument('-o','--outfile', type=Path, help="Path to the output file")
    parser.add_argument('-b','--buffer-width', type=int, help="Buffer width for nearby projects")
    parser.add_argument('-s','--silent', default=False, help="Run in silent mode (minimize console output)")

    args = parser.parse_args()


    # Load locations for the given unverse
    #nodes, _ = load_location(universe) # TODO: add `silent` 
    locations_gdf = load_lion_default(args.universe) # TODO: see load_lion_default

    # Run the pipeline
    ret = gather_capital_projects_for_locations(locations_gdf, args.outfile, args.buffer_width, args.silent)

    if not args.outfile:
        print(ret)