import os
from pathlib import Path
import geopandas as gpd
from typing import Optional
import osmnx as ox

from dotenv import load_dotenv
load_dotenv()

DATA_PATH = Path(str(os.getenv('DATA_PATH')))

root_path = Path(__file__).resolve().parent.parent.parent
LION_PATH = 'data/lion'

lion_nodes = gpd.read_file(root_path / LION_PATH / 'lion.gdb', layer='node')
lion_node_names = gpd.read_file(root_path / LION_PATH / 'lion.gdb', layer='node_stname')
lion_altnames = gpd.read_file(root_path / LION_PATH / 'lion.gdb', layer='altnames') # Alternate names for streets (e.g. Ave of Americas)
lion_lion = gpd.read_file(root_path / LION_PATH / 'lion.gdb', layer='lion')

# lion_nodes.explore()

def load_location(location:str, outfile:Optional[Path]=None) -> gpd.GeoDataFrame:
    all_intersections = lion_nodes.merge(
        lion_node_names
            .groupby('NodeId')['StreetName']
            .apply(' & '.join)
            .reset_index(),
        how='left',
        left_on = 'NODEID', right_on = 'NodeId',
        indicator=True
    )[['StreetName','NODEID','geometry', 'GLOBALID']].set_index('NODEID')

    bounds = ox.geocode.geocode_to_gdf(location)

    intersections_clipped = all_intersections.clip(
        bounds.to_crs(all_intersections.crs)
    )

    if outfile:
        intersections_clipped.to_csv(outfile, index=False)

    return intersections_clipped