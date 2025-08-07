# TODO: see load_universe. This should be factored into a singular function that can load a universe from a few different source types
# TODO: also clean up the errors to use the validator module?
import os
from pathlib import Path
from typing import Optional, Dict
import osmnx as ox
import argparse
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

from dotenv import load_dotenv
load_dotenv()

DATA_PATH = Path(str(os.getenv('DATA_PATH')))

LION_PATH = 'data/lion/lion.gdb'

LION_LAYERS = {'nodes': 'node', 'node_names': 'node_stname', 'altnames': 'altnames','master': 'lion'}

def _load_lion_baselayers(root_path, lion_path, layers:Dict[str, str]|str='all') -> Dict[str, gpd.GeoDataFrame]:
    # TODO: call (and write) helper function that auto-converts a string to a path
    if layers == 'all':
        layers = LION_LAYERS
    if not isinstance(layers, Dict):
        raise ValueError(f'Invlalid `layers` input: {layers}')

    layers_dict = {}
    for lyr_name, lyr_path in layers.items(): # layers is a dict
        try:
            layers_dict[lyr_name] = gpd.read_file(root_path / LION_PATH, layer=lyr_path)
        except Exception as e:
            raise ValueError(f'{lyr_path} not found! Only {", ".join(list(LION_LAYERS.values()))} exist as layers. {e}') # TODO: auto-generate this.
        
    # TODO: add counts or some sort of dimensional summary
    
    return layers_dict

def _clean_streetnames(x): # TODO: standardize street name cleaning in someway
    if not isinstance(x, str):
        return pd.NA
    elif (x.endswith(' BOUNDARY')) or (' RAIL ' in x) or ('SHORELINE' in x):
        return pd.NA
    else:
        return x.strip()

def interpret_boundary(universe_boundary:str|Path|Polygon|gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    print(type(universe_boundary), universe_boundary)
    if isinstance(universe_boundary, (Polygon, gpd.GeoDataFrame)):
        bounds=universe_boundary
    elif isinstance(universe_boundary, str) and os.path.exists(universe_boundary):
        bounds = gpd.read_file(Path(str(universe_boundary)))
    elif str(universe_boundary) in ['nyc','all']:
        bounds = None
    else: # Geocodable address
        bounds = ox.geocoder.geocode_to_gdf(str(universe_boundary))

    return bounds

def clip_gdf_by_boundary(locations_gdf:gpd.GeoDataFrame, universe_boundary:str|Path|Polygon|gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Handle boundary -- TODO: move this to load_location? Also rename universe?
    bounds = interpret_boundary(universe_boundary)
    
    if bounds is not None:
        locations_clipped = locations_gdf.clip(
            bounds.to_crs(locations_gdf.crs)
        )
    else:
        locations_clipped = locations_gdf

    return locations_clipped

# Load_lion_universe
def load_lion_universe(nodes_gdf:gpd.GeoDataFrame, node_names_gdf:gpd.GeoDataFrame, universe:str='nyc', outfile:Optional[Path]=None) -> gpd.GeoDataFrame:
    # 1) Merge the nodes and street names
    node_streetnames = nodes_gdf.merge(
            node_names_gdf,
            how='left',
            left_on = 'NODEID', right_on = 'NodeId',
            #indicator=True
        ).drop(['NodeId', 'VIntersect'], axis=1)

    # 2) Clean the street names # TODO: Allow for different methods of cleaning
    node_streetnames['StreetName_cleaned'] = node_streetnames['StreetName'].apply(_clean_streetnames)

    # 3) Now remove the null street values (those that were removed by the cleaning process)
    node_streetnames_noNull = node_streetnames[node_streetnames['StreetName_cleaned'].notna()]
    nodes_with_streetnames = nodes_gdf.merge(
        node_streetnames_noNull
            .groupby('NODEID')['StreetName_cleaned']
            .agg(list),
        left_on = 'NODEID', right_index=True,
        how = 'inner'
    ).rename({'StreetName_cleaned': 'StreetNames'}, axis=1).drop(['VIntersect', 'GLOBALID'], axis=1)

    # 4) Now filter down to the specific boudnary
    locations_clipped = clip_gdf_by_boundary(nodes_with_streetnames, universe)

    # 5) Save if necessary
    if outfile:
        locations_clipped.to_file(outfile)

    # 6) Return
    return locations_clipped

def load_lion_default(universe='all', outfile=None): # TODO: this should take in a unvierse_name, check if it exists in data/universes, if not, geocode it and create a new one. Also should be named better and refactored to reflect this. Maybe should be generalized to allow for different sources
    # Load file paths
    root_path = Path(__file__).resolve().parent.parent.parent

    # Load base layers
    layers = _load_lion_baselayers(root_path, LION_PATH, {'nodes': 'node','node_names': 'node_stname'})

    # Filter and munge to the right format
    result = load_lion_universe(layers['nodes'], layers['node_names'], universe, outfile)
    return result

if __name__ == '__main__':
    # Parse Args
    parser = argparse.ArgumentParser()
    parser.add_argument('--universe', '-u', default='nyc')
    parser.add_argument('--outfile', '-o', default=None)
    args = parser.parse_args()

    result = load_lion_default(args.universe, args.outfile)

    if not args.outfile:
        print(result)