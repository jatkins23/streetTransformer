from typing import Optional, List
import argparse

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

import geopandas as gpd
import pandas as pd
from shapely import geometry
from pyproj import CRS
import mercantile

from preprocessing.imagery.geoprocessing import generate_buffer_geometry, load_tile_reference, complete_dataframe, set_buffer_width

project_dir = Path(__file__).resolve().parent.parent.parent
print(f'Using "{project_dir}" as `project_dir`')
sys.path.append(str(project_dir))

from preprocessing.data_load.load_lion import load_lion_default

def buffer_and_load(locations_gdf: gpd.GeoDataFrame, tile_ref_gdf:gpd.GeoDataFrame, 
                    static_path:Path, buffer_width:int|str='variable', buffer_type:str='round') -> pd.DataFrame:
    # TODO: Variable `buffer_width` depending on type
    """Create a buffer around each location, join it to the tiles, and extract the """
    # Set buffer value
    buffer_values = set_buffer_width(buffer_width, locations_gdf)
    
    # Now create buffer_geom column 
    locations_buffered = locations_gdf.copy()
    locations_buffered['buffer_geom'] = generate_buffer_geometry(
        locations_gdf.geometry, 
        buffer_values, 
        buffer_type
    )

    # Swap geom to buffer
    # locations_buffered.set_geometry('buffer_geom') # Not necessary? Was commented out in the original

    # Conduct Spatial Join
    proj_crs = locations_buffered.crs
    locations_df = (
        locations_buffered.sjoin(
            tile_ref_gdf.to_crs(proj_crs)
        ) # Spatial join 
        .reset_index()
        .rename(columns={'osmid':'intersection_id'}) # TODO: need to fix this. Should assume that a locations_dataset comes in with [a location_id]
    )

    # Create Cross-walk
    location_to_tile_xwalk = (
        locations_df[['location_id','xtile','ytile']] # TODO: This can be a groupby, or unique, right??
        .value_counts()
        .reset_index()
        .drop(columns='count')
        .rename(columns={'index_right':'tile_id'})
        .set_index('location_id')
    )

    # Now fill the dataframe so that it has every combination of x/y tiles 
    location_to_tile_xwalk_complete = location_to_tile_xwalk.groupby(level=0).apply(complete_dataframe, column_names=['xtile','ytile'])

    # Add file_path
    location_to_tile_xwalk_complete['file_path'] = location_to_tile_xwalk_complete.apply(lambda x: os.path.join(static_path, f"{x['xtile']}_{x['ytile']}.png"), axis=1)

    # Reset Index
    location_to_tile_xwalk_complete = location_to_tile_xwalk_complete.reset_index().set_index(['location_id','xtile','ytile']).drop('level_1',axis=1)

    return location_to_tile_xwalk_complete


# TODO: write a version that gathers imagery

def gather_imagery_for_locations(
        locations_gdf:gpd.GeoDataFrame, 
        tile_static_path:Path, 
        tile_ref_path:Path,
        save_path:Path, subset:Optional[List[int]]=None) -> None: # TODO: Return DataFrame
    # Load the reference_tiles:
    tile_static_path = load_tile_reference(tile_ref_path)

    # 


if __name__ == '__main__':
    # Parse Args
    parser = argparse.ArgumentParser()
    parser.add_argument('universe')

    args = parser.parse_args()

    locations_gdf = load_lion_default(args.universe)
    #gather_imagery_for_locations(locations_gdf, static_path, tile_ref, save_path)
    buffer_and_load(locations_gdf, tile_ref_gdf, static_path=tile_static_path, )