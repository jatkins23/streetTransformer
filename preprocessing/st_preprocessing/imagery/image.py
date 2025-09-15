import os
import numpy as np
from pathlib import Path

from PIL import Image
import matplotlib.pyplot as plt

def safe_stitch_tilegrid(tiles_df, verbose=True):
    """A wrapper to stitch images with a try/except statement"""
    try:
        return stitch_tilegrid(tiles_df, verbose=verbose)
    except Exception as e:
        print(f'{tiles_df.name}: {e}')
        return np.nan

def stitch_tilegrid(tiles_df, show=False, verbose=False):
    # Sort to be safe
    sorted_df = tiles_df.sort_index()

    # Confirm its square) # TODO: simplify this validation. Lots of ways to do so: int(len(tile_arrays)**.5)**2 == len(tile_arrays)? 
    #vals_X =  sorted_df.index.get_level_values(0).unique()
    vals_X = set(sorted_df.groupby(level=0).count()['file_path'])
    vals_Y = set(sorted_df.groupby(level=1).count()['file_path'])

    if (len(vals_X) != 1) or (len(vals_Y) != 1):
        raise ValueError('Tile array is not a square: {vals_0} {vals_1}')
    dim = vals_Y.pop()
    #dimY = vals_X.pop() # Not necessary because its square but for completeness

    # Get list an array of all images
    tile_arrays = [np.array(Image.open(i)) for i in sorted_df['file_path']]

    # Stitch the rows horizontally then vertically
    rows = [
        np.hstack(tile_arrays[i*dim:(i+1)*dim])
        for i in range(dim)
    ]
    # Stack back together
    final_image = np.vstack(rows)

    if show:  
        plt.imshow(final_image)

    return final_image


def write_image_row(row, save_path):
    print(f"Writing {row.name}-{row['name']}...")
    return _write_image(
        row['image'],
        row.name,
        row['name'],
        dir_path=save_path
    )

def _write_image(img:np.ndarray, id:int|str, name:str, dir_path:Path) -> Path:
    if isinstance(img, np.ndarray):
        img = Image.fromarray(img) # TODO: Fix typing here
    
    if not dir_path:
        os.makedirs(dir_path, exist_ok=True)
        print(f'Creating {dir_path}')

    outfile = f'{id}_{name}.png'
    full_outfile = dir_path / outfile

    img.save(full_outfile)

    return full_outfile


# def _stitch_image(itx_df, show=False, verbose=False):
#     # Sort to be safe
#     sorted_df = itx_df.sort_index()

#     # Confirm its square
#     #vals_X =  sorted_df.index.get_level_values(0).unique()
#     vals_X = set(sorted_df.groupby(level=0).count()['file_path'])
#     vals_Y = set(sorted_df.groupby(level=1).count()['file_path'])

#     if (len(vals_X) != 1) or (len(vals_Y) != 1):
#         raise ValueError('Tile array is not a square: {vals_0} {vals_1}')
#     dimX = vals_Y.pop()
#     #dimY = vals_X.pop() # Not necessary because its square but for completeness

#     # Get list an array of all images
#     tile_arrays = [np.array(Image.open(i)) for i in sorted_df['file_path']]
#     tile_rows = []
#     for i in range(dimX):
#         id_min = i*dimX
#         id_max = ((i+1)*dimX)
#         new_row = np.vstack(tile_arrays[id_min:id_max])
#         tile_rows.append(new_row)

#     final_image = np.hstack(tile_rows)

#     # if verbose:
#     #     print(f'\t{itx_df.name}: Loading {tile_arrays.shape[0]} ({tile_arrays.shape[1:3]}) tiles in a {dimX}X{dimY} grid.')
    
#     # Stack back together
#     if show:  
#         plt.imshow(final_image)

#     return final_image