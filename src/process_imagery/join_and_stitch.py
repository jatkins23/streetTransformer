import os
import sys
from pathlib import Path
from dotenv import load_dotenv

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely import geometry, box
from pyproj import CRS

from PIL import Image
import matplotlib.pyplot as plt

src_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(src_dir))
from data_load.load_intersections import load_location

load_dotenv()

# TODO: fix
STATIC_PATH = 'imagery/tiles/static/nyc/256_19'
static_path = Path(str(os.getenv('DATA_PATH'))) / STATIC_PATH

# Load
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

def _calculate_ideal_buffer_width(node):
    return 20

def _set_buffer_width(buffer_width:str|float, nodes:gpd.GeoDataFrame|gpd.GeoSeries) -> pd.Series:
    if isinstance(buffer_width, float) | isinstance(buffer_width, int):
        # Should be try/ecept
        buffer_value = np.repeat(float(buffer_width), nodes.shape[0])
    elif buffer_width == 'variable':
        buffer_value = nodes.apply(_calculate_ideal_buffer_width, axis=1)
    else:
        raise ValueError(f'Unknown `buffer_value`: {buffer_width}')
    
    return pd.Series(buffer_value)

def calculate_square_bounds(x:pd.Series, y:pd.Series, buffer_width:pd.Series|float) -> tuple:
    minx = x - buffer_width
    maxx = x + buffer_width
    miny = y - buffer_width
    maxy = y + buffer_width

    return minx, miny, maxx, maxy

def generate_buffer_geometry(centroids:gpd.GeoSeries, buffer_widths:pd.Series, buffer_type:str) -> gpd.GeoSeries:
    if buffer_type == 'round':
        buffers = [x.buffer(y) for x, y in zip(centroids, buffer_widths)]
        ret = gpd.GeoSeries(buffers)
    elif buffer_type == 'square':
        minx, miny, maxx, maxy = calculate_square_bounds(centroids.x, centroids.y, buffer_widths)
        boxes = [
            box(xmin, ymin, xmax, ymax)
            for xmin, ymin, xmax, ymax 
            in zip(minx, miny, maxx, maxy)
        ]
        ret = gpd.GeoSeries(boxes)
    else:
        raise ValueError(f'Unknown `buffer_type` value: {buffer_type}')
    
    return ret

# Move to utils
def complete_dataframe(input_slice:pd.DataFrame, column_names:list[str]=['xtile','ytile']):
    col_data = []

    for c in column_names:
        col_data.append(input_slice[c].unique())

    return pd.MultiIndex.from_product(col_data, names=column_names).to_frame(index=False)

def buffer_and_load(nodes_gdf: gpd.GeoDataFrame, tile_ref_gdf:gpd.GeoDataFrame, 
                    static_path:Path, buffer_width:int|str='variable', buffer_type:str='round') -> pd.DataFrame:
    # TODO: Variable `buffer_width` depending on type
    """Create a buffer around each location, join it to the tiles, and extract the """
    # Set buffer value
    buffer_values = _set_buffer_width(buffer_width, nodes_gdf)

    # Now create buffer_geometries for each
    buffer_geometries = generate_buffer_geometry(
        nodes_gdf.geometry, 
        buffer_values, 
        buffer_type
    )
    
    # Add buffer geometry column
    nodes_buffered = nodes_gdf.copy()
    nodes_buffered['geometry'] = buffer_geometries

    # Swap geom to buffer
    #nodes_buffered = nodes_buffered.set_geometry('buffer_geometries')

    # Conduct Spatial Join
    intersections_df = (
        nodes_buffered.sjoin(
            tile_ref_gdf.to_crs(nodes_buffered.crs)
        ) # Spatial join 
        .reset_index()
        .rename(columns={'osmid':'intersection_id'}) #FLAG
    )

    # Create Cross-walk
    intersection2tile = (
        intersections_df[['intersection_id','xtile','ytile']]
        .value_counts()
        .reset_index()
        .drop(columns='count')
        .rename(columns={'index_right':'tile_id'})
        .set_index('intersection_id')
    )

    # Now fill the dataframe so that it has every combination of x/y tiles 
    intersection2tile_complete = intersection2tile.groupby(level=0).apply(complete_dataframe, column_names=['xtile','ytile'])

    # Add file_path
    intersection2tile_complete['file_path'] = intersection2tile_complete.apply(lambda x: os.path.join(static_path, f"{x['xtile']}_{x['ytile']}.png"), axis=1)

    return intersection2tile_complete.reset_index().set_index(['intersection_id','xtile','ytile']).drop('level_1',axis=1)

def _stitch_image(itx_df, show=False, verbose=False):
    # Sort to be safe
    sorted_df = itx_df.sort_index()

    # Confirm its square
    #vals_X =  sorted_df.index.get_level_values(0).unique()
    vals_X = set(sorted_df.groupby(level=0).count()['file_path'])
    vals_Y = set(sorted_df.groupby(level=1).count()['file_path'])

    if (len(vals_X) != 1) or (len(vals_Y) != 1):
        raise ValueError('Tile array is not a square: {vals_0} {vals_1}')
    dimX = vals_Y.pop()
    #dimY = vals_X.pop() # Not necessary because its square but for completeness

    # Get list an array of all images
    tile_arrays = [np.array(Image.open(i)) for i in sorted_df['file_path']]
    tile_rows = []
    for i in range(dimX):
        id_min = i*dimX
        id_max = ((i+1)*dimX)
        new_row = np.vstack(tile_arrays[id_min:id_max])
        tile_rows.append(new_row)

    final_image = np.hstack(tile_rows)

    # if verbose:
    #     print(f'\t{itx_df.name}: Loading {tile_arrays.shape[0]} ({tile_arrays.shape[1:3]}) tiles in a {dimX}X{dimY} grid.')
    
    # Stack back together
    if show:  
        plt.imshow(final_image)

    return final_image

def write_image(row, save_path):
    print(f"Writing {row.name}-{row['name']}...")
    return _write_image(
        row['image'],
        row.name,
        row['name'],
        dir_path=save_path
    )

def _write_image(img:np.ndarray, id:int|str, name:str, dir_path:Path) -> Path:
    if isinstance(img, np.ndarray):
        img = Image.fromarray(img)
    
    if not dir_path:
        os.makedirs(dir_path, exist_ok=True)
        print(f'Creating {dir_path}')

    outfile = f'{id}_{name}.png'
    full_outfile = dir_path / outfile

    img.save(full_outfile)

    return full_outfile


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

def _safe_stitch_image(itx_df, verbose=True):
    """A wrapper to stitch images with a try/except statement"""
    try:
        return _stitch_image(itx_df, verbose=verbose)
    except Exception as e:
        print(f'{itx_df.name}: {e}')
        return np.nan


def cut_locations(bboxes: gpd.GeoSeries):
    # Needs:
        # Mask of the bounding box

        # pseudo-tile I guess?
    pass

def gather_location_imagery(location_name, tile_static_path, tile_ref_path, 
                            save_path, subset_ids:list[int]|str = 'all', write=True):
    # Get all intersections from Downtown 
    nodes, edges = load_location(location_name)

    # Load the references tiles for all of Brooklyn
    tile_reference_gdf = load_tile_reference(tile_ref_path)

    # Buffer and Load
    intersection2tile = buffer_and_load(nodes, tile_reference_gdf, static_path=tile_static_path)

    # Downsample to requested
    if subset_ids != 'all':
        intersection2tile = intersection2tile.loc[subset_ids]

    # Stitch images
    imgs = intersection2tile.groupby('intersection_id').apply(_safe_stitch_image)
    
    # Save if asked
    itx_names = find_intersection_names(edges)
    images_df = pd.concat([itx_names, imgs], axis=1)
    images_df.columns = ['name','image']

    if write:
        #_write_image()
        for r in images_df[images_df['image'].notna()].to_records():
            print(f"Writing {r.index}-{r['name']}...")
            file_path = _write_image(r['image'], r.index, r['name'], dir_path=save_path)

        # Only operate on rows where 'image' is notna
        mask = images_df['image'].notna()

        # Apply the function, assigning the result to a new column
        images_df.loc[mask, 'file_path'] = images_df.loc[mask].apply(write_image, save_path=save_path, axis=1)

    return nodes, images_df

if __name__ == '__main__':
    gather_location_imagery('Downtown Brooklyn, New York, USA', static_path)