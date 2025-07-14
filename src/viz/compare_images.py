import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd

import matplotlib.pyplot as plt
from PIL import Image

load_dotenv(override=True)

DATA_PATH = str(os.getenv('DATA_PATH'))
REF_REL_PATH = 'imagery/processed/refs/'

# example usage:
#   python src/viz/compare_images.py -s 2008 -e 2024 -i 0 -z 20


def process_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--intersection_id','-i',required=True, type=int)
    parser.add_argument('--startyear','-s',required=True, type=int)
    parser.add_argument('--endyear','-e',required=True, type=int)
    parser.add_argument('--z_level','-z',required=True, type=int)

    args = parser.parse_args()
    return args

def _get_image_path(idx:int, year:int, z_level:int, root_dir:Path|str) -> tuple[str, Path]:
    ref_file_path = Path(root_dir).joinpath(f'image_refs_z{z_level}_{year}.csv')
    ref_df = pd.read_csv(ref_file_path)
    row = ref_df.loc[idx]
    try:
        file_path = row['file_path']
        intx_name = row['name']
        return intx_name, file_path
    except Exception as e:
        print(e)


def compare_year_images(intx_id:int, start_year:int, end_year:int, z_level:int=20) -> None:
    ref_dir_path = Path(DATA_PATH).joinpath(REF_REL_PATH)
        
    # Get Image Paths
    title, start_image_path = _get_image_path(intx_id, start_year, z_level, ref_dir_path)
    _, end_image_path = _get_image_path(intx_id, end_year, z_level, ref_dir_path)

    # Load the Images
    start_image = Image.open(start_image_path)
    end_image = Image.open(end_image_path)

    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    # Show first image
    axes[0].imshow(start_image)
    axes[0].axis("off")
    axes[0].set_title(start_year)

    # Show second image
    axes[1].imshow(end_image)
    axes[1].axis("off")
    axes[1].set_title(end_year)

    # Main title
    fig.suptitle(title, fontsize=16)

    # Display
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()
    

if __name__ == '__main__':
    args = process_args()
    
    compare_year_images(args.intersection_id, args.startyear, args.endyear, args.z_level)
    