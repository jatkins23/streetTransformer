import os
from pathlib import Path
import geopandas as gpd
from typing import Optional, Dict, List
import osmnx as ox
import argparse
import numpy as np

from dotenv import load_dotenv
load_dotenv()

DATA_PATH = Path(str(os.getenv('DATA_PATH')))

LION_PATH = 'data/lion/lion.gdb'

LION_LAYERS = {'nodes': 'node', 'node_names': 'node_stname', 'altnames': 'altnames','master': 'lion'}

def _load_lion_baselayers(root_path, lion_path, layers:Dict[str, str]|str='all') -> Dict[str, gpd.GeoDataFrame]:
    if layers == 'all':
        layers = LION_LAYERS
    if not isinstance(layers, Dict):
        raise ValueError(f'Invlalid `layers` input: {layers}')

    layers_dict = {}
    for lyr_name, lyr_path in layers.items(): # layers is a dict
        try:
            layers_dict[lyr_name] = gpd.read_file(root_path / LION_PATH, layer=lyr_path)
        except Exception as e:
            raise ValueError(f'{lyr_path} not found! Only {", ".join(list(LION_LAYERS.values()))} exist as layers')
        
    # TODO: add counts or some sort of dimensional summary
    
    return layers_dict

def load_lion_location(nodes:gpd.GeoDataFrame, node_names:gpd.GeoDataFrame, location:str='all', outfile:Optional[Path]=None) -> gpd.GeoDataFrame:
    # Handle
    # all_intersections = nodes.merge(
    #     node_names
    #         .groupby('NodeId')['StreetName']
    #         .apply(' & '.join)
    #         .reset_index(),
    #     how='left',
    #     left_on = 'NODEID', right_on = 'NodeId',
    #     indicator=True
    # )[['StreetName','NODEID','geometry', 'GLOBALID']].set_index('NODEID')
    
    node_streetnames = nodes.merge(
        node_names,
        how='left',
        left_on = 'NODEID', right_on = 'NodeId',
        #indicator=True
    ).drop(['NodeId', 'VIntersect'], axis=1)

    # Clean Street Names
    street_names_cleaned = node_streetnames['StreetName'].str.strip()

    def clean_streetnames(x):
        if not isinstance(x, str):
            return np.nan
        elif (x.endswith(' BOUNDARY')) or (' RAIL ' in x) or ('SHORELINE' in x):
            return np.nan
        else:
            return x
    
    street_names_cleaned = street_names_cleaned.apply(clean_streetnames)
    node_streetnames['StreetName_cleaned'] = street_names_cleaned
    # Remove nulls
    node_streetnames_noNull = node_streetnames[node_streetnames['StreetName_cleaned'].notna()]
    nodes['StreetNames'] = node_streetnames_noNull.groupby('NODEID')['StreetName_cleaned'].agg(list).to_dict()

    # Remove nulls again
    nodes = nodes[(nodes['StreetNames'].notna())].drop(['VIntersect','GLOBALID'], axis=1)
    
    # Now filter it down to a specific location if asked
    if location != 'all':
        bounds = ox.geocoder.geocode_to_gdf(location)

        intersections_clipped = nodes.clip(
            bounds.to_crs(nodes.crs)
        )
    else:
        intersections_clipped = nodes

    if outfile:
        intersections_clipped.to_file(outfile)

    return intersections_clipped

def load_lion_default(location='all', outfile=None):
    # Load file paths
    root_path = Path(__file__).resolve().parent.parent.parent

    # Load base layers
    layers = _load_lion_baselayers(root_path, LION_PATH, {'nodes': 'node','node_names': 'node_stname'})

    # Filter and munge to the right format
    result = load_lion_location(layers['nodes'], layers['node_names'], location, outfile)
    return result

if __name__ == '__main__':
    # Parse Args
    parser = argparse.ArgumentParser()
    parser.add_argument('--location', '-l', default='all')
    parser.add_argument('--outfile', '-o', default=None)
    args = parser.parse_args()

    result = load_lion_default(args.location, args.outfile)

    if not args.outfile:
        print(result)