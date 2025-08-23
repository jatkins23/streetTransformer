from pathlib import Path
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely import geometry, box
from pyproj import CRS

def load_tile_reference(file_path:str|Path, crs:CRS=CRS('4326')) -> gpd.GeoDataFrame:
    """
    Load tile metadata as a GeoDataFrame.

    Args:
        index_file_path: Path to a GeoJSON or CSV with columns:
                         ['tile_path', 'geometry']
        crs: Geo Reference System

    Returns:
        GeoDataFrame with tile geometries.
    """
    if not file_path:
        raise FileNotFoundError(file_path)

    tiles_df = pd.read_csv(file_path, index_col=0)

    def create_bbox(x):
        return geometry.box(x['topleft_x'], x['bottomright_y'], x['bottomright_x'], x['topleft_y']),
    
    coordinates = tiles_df.apply(
        create_bbox,
        axis=1
    )

    tiles_gdf = gpd.GeoDataFrame(
        tiles_df,
        crs=crs,
        geometry=coordinates
    )
        
    return tiles_gdf


def complete_dataframe(input_slice:pd.DataFrame, column_names:list[str]=['xtile','ytile']):
    col_data = []

    for c in column_names:
        col_data.append(input_slice[c].unique())

    return pd.MultiIndex.from_product(col_data, names=column_names).to_frame(index=False)

def _calculate_ideal_buffer_width(node):
    return 20

def set_buffer_width(buffer_width:str|float, nodes:gpd.GeoDataFrame|gpd.GeoSeries) -> pd.Series:
    if isinstance(buffer_width, (int, float)):
        # TODO: Should be try/except?
        buffer_value = np.repeat(float(buffer_width), nodes.shape[0])
    elif buffer_width == 'variable':
        buffer_value = nodes.apply(_calculate_ideal_buffer_width, axis=1)
    else:
        raise ValueError(f'Unknown `buffer_value`: "{buffer_width}"')
    
    return pd.Series(buffer_value)


def _calculate_square_bounds(x:pd.Series, y:pd.Series, buffer_width:pd.Series|float) -> tuple:
    minx = x - buffer_width
    maxx = x + buffer_width
    miny = y - buffer_width
    maxy = y + buffer_width

    return minx, miny, maxx, maxy

def _create_bbox_from_list(x):
    return geometry.box(x['topleft_x'], x['bottomright_y'], x['bottomright_x'], x['topleft_y']),

def cut_locations(bboxes: gpd.GeoSeries):
    # Needs:
        # Mask of the bounding box

        # pseudo-tile I guess?
    pass

def generate_buffer_geometry(centroids:gpd.GeoSeries, buffer_widths:pd.Series, buffer_type:str) -> gpd.GeoSeries:
    if buffer_type == 'round':
        buffers = [x.buffer(y) for x, y in zip(centroids, buffer_widths)]
        ret = gpd.GeoSeries(buffers)
    elif buffer_type == 'square':
        minx, miny, maxx, maxy = _calculate_square_bounds(centroids.x, centroids.y, buffer_widths)
        boxes = [
            box(xmin, ymin, xmax, ymax)
            for xmin, ymin, xmax, ymax 
            in zip(minx, miny, maxx, maxy)
        ]
        ret = gpd.GeoSeries(boxes)
    else:
        raise ValueError(f'Unknown `buffer_type` value: {buffer_type}')
    
    return ret
