from pathlib import Path
import pandas as pd
import geopandas as gpd
from typing import List, Dict, Optional
from ..config import constants
from shapely.geometry import Point
import mercantile
import re
from ..utils.streets import match_streetname
from ..utils.geodata import normalize_coord

# TODO: make type: location with id = int??

# TODO: add the locations to constants or some sort of config. there should be a config file for each universe?
PATH = Path()
DATA_ROOT = Path('src/streetTransformer/data')
UNIVERSE = 'nyc'
#LION_df = pd.read_csv(PATH / DATA_ROOT / 'universes' / UNIVERSE / 'locations/lion.geojson')
#LION_gdf = gpd.GeoDataFrame(LION_df, crs='4326', geometry='geometry')

def geolocate_coords_to_location(coordinates:tuple|list|dict|Point|str, reference_gdf:gpd.GeoDataFrame, id_column='location_id', projected_crs='2263') -> gpd.GeoSeries:
    lng, lat = normalize_coord(coordinates)
    point = Point(lng, lat)

    # Handle CRS
    if reference_gdf.crs.is_geographic:
        gdf_proj = reference_gdf.to_crs(projected_crs)
        point_proj = gpd.GeoSeries([point], crs=reference_gdf.crs).to_crs(projected_crs).iloc[0]
    else:
        gdf_proj = reference_gdf
        point_proj = point
    
    gdf_proj['distance'] = gdf_proj.geometry.distance(point_proj)
    closest_row = gdf_proj.loc[gdf_proj['distance'].idxmin()]
        
    return closest_row


def geolocate_crossstreets_to_location(cross_streets:List, nodes_gdf:gpd.GeoDataFrame, 
                                       node_names_gdf:pd.DataFrame, StreetNameid_column:str='NodeId') -> pd.DataFrame:
    # cross_streets = [_normalize_streetname(n) for n in cross_streets]

    # node_names_gdf['StreetName']

    subset = node_names_gdf.copy()
    for s in cross_streets:
        #print(s)
        subset_nodeids = match_streetname(s, subset['StreetName'], subset[StreetNameid_column])
        subset = subset[subset[StreetNameid_column].isin(subset_nodeids)]
        
    # Group by
    subset_named = (
        subset
            .groupby(StreetNameid_column)['StreetName']
            .apply(lambda x: 
                   ' & '.join(x.str.strip().str.title()) # TODO: Replace with build_oneline_address?
            )
    )

    # Now merge back to the main node dataset
    subset_nodes_full = nodes_gdf.merge(
        subset_named,
        left_on='NODEID', right_on='NodeId'
    ).set_geometry('geometry').rename(columns={'StreetName': 'InteresectionName'})
    
    return subset_nodes_full

def geolocate_coord_to_tile(coordinates:tuple|list|dict|Point|str, locations_gdf, tiles_gdf:gpd.GeoDataFrame, zlevel=20, gridsize=3):
    lng, lat = _normalize_coord(coordinates)
    t = mercantile.tile(lng, lat, zlevel)
    delta = gridsize // 2
    xs = [t.x + dx for dx in range(-delta, delta+1)]
    ys = [t.y + dy for dy in range(-delta, delta+1)]
    return [(x, y) for y in ys for x in xs]


if __name__ == '__main__':
    #print(LION_df)
    print('here')
    #print(geolocate_coords_to_location('40.6962, 73.9886', LION_INTX))