# TODO: So much here can rework a lot. Need to use the find_intersection_names, need to 
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import geopandas as gpd
import pandas as pd

load_dotenv()

sys.path.append(str(os.getenv('INTX_PROFILING_SRC_PATH')))
from intersection import Intersections

def find_intersection_names(edges_gdf:gpd.GeoDataFrame) -> pd.Series:
    """Assign names to each intersection given the street names (edges) around them."""
    # So, for each intersection (u), we want to get top 2 distinct street names (when sorting highway by priority), then concat them
    HIGHWAY_NAME_PRIORITY = ['primary','secondary','tertiary','residential', 'living_street','service','multi_use','primary_link','unclassified','pedestrian','footway','cycleway',]
    STREET_SUFFIXES = ['Street', 'Avenue', 'Road']

    # Replace segments with multiple roadway types with 'multi-use'
    edges_gdf.loc[edges_gdf['highway'].apply(lambda x: isinstance(x, list)), 'highway'] = 'multi_use'

    # Sort the values
    name_priority_map = {k: i for i, k in enumerate(HIGHWAY_NAME_PRIORITY)}
    edges_gdf['name_priority_order'] = edges_gdf['highway'].map(name_priority_map)
    edges_gdf['name_priority_order']


    grouped = edges_gdf.groupby(level=0)

    # Now generate the names
    intersection_names = grouped.apply(lambda g: '_|_'.join(
        g.sort_values('name_priority_order')['name']
        .fillna('__')
        .astype(str)
        .str.replace('|'.join(STREET_SUFFIXES), '', regex=True)
        .str.strip()
        .str.replace('  ', '_')
        .str.replace(' ', '_')
        .drop_duplicates()
        .head(2)
    ))

    return intersection_names

def load_location(place, silent=False):

    inter = Intersections.from_place(place)
    inter.with_options(tolerance=20)

    nodes = inter.nodes
    edges = inter.edges

    return nodes, edges 


