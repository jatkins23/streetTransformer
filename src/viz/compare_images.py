import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Tuple

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
    parser.add_argument('--outfile','-o', type=Path)
    parser.add_argument('--show', type=bool)

    args = parser.parse_args()
    return args

def _get_image_path(idx:int, year:int, z_level:int, root_dir:Path|str) -> Tuple[str, Path]:
    ref_file_path = Path(root_dir).joinpath(f'image_refs_z{z_level}_{year}.csv')
    ref_df = pd.read_csv(ref_file_path)
    row = ref_df.loc[idx]
    try:
        file_path = row['file_path']
        intx_name = row['name']
        return intx_name, file_path
    except Exception as e:
        print(e)

def load_images(
    intx_id: int,
    start_year: int,
    end_year: int,
    z_level: int,
    ref_dir_path: Path
) -> Tuple[str, Image.Image, Image.Image]:
    """
    Load the start and end year images for the given intersection.
    """
    title, start_image_path = _get_image_path(intx_id, start_year, z_level, ref_dir_path)
    _, end_image_path = _get_image_path(intx_id, end_year, z_level, ref_dir_path)
    start_image = Image.open(start_image_path)
    end_image = Image.open(end_image_path)
    return title, start_image, end_image

def create_comparison_figure(
    title: str,
    start_image: Image.Image,
    end_image: Image.Image,
    start_year: int,
    end_year: int,
    caption: Optional[str] = None
) -> plt.Figure:
    """
    Create a matplotlib figure comparing two images with optional caption.
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].imshow(start_image)
    axes[0].axis("off")
    axes[0].set_title(str(start_year))

    axes[1].imshow(end_image)
    axes[1].axis("off")
    axes[1].set_title(str(end_year))

    fig.suptitle(title, fontsize=16)
    
    fig.subplots_adjust(bottom=0.5)

    if caption:
        fig.text(
            0.5,
            0.01,
            caption,
            ha="center",
            va="bottom",
            wrap=True,
            fontsize=10
        )

    plt.tight_layout(rect=[0, 0.03, 1, 0.90])
    return fig

def save_figure(
    fig: plt.Figure,
    save_path: Optional[Path],
    dpi: int = 300
) -> None:
    """
    Save the figure to disk if a save path is provided.
    """
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight", format=save_path.suffix[1:])
        print(f"Saved figure to: {save_path.resolve()}")

def compare_year_images(
        intx_id:int, 
        start_year:int, 
        end_year:int, # TODO: expand to any arbitrary number of images/years
        z_level:int=20, 
        caption:Optional[str]=None, 
        save_path:Optional[Path]=None, 
        show:bool=True,
        dpi:int = 300) -> None:
    """_summary_

    Args:
        intx_id (int): _description_
        start_year (int): _description_
        end_year (int): _description_
        dpi (_type_): _description_
        z_level (int, optional): _description_. Defaults to 20.
        caption (Optional[Path], optional): _description_. Defaults to None.
        save_path (Optional[Path], optional): _description_. Defaults to None.
    """
    ref_dir_path = Path(DATA_PATH).joinpath(REF_REL_PATH)
        
    # Get Image Paths
    title, start_image, end_image = load_images(intx_id, start_year, end_year, z_level, ref_dir_path)

    # Create figure
    fig = create_comparison_figure(
        title, start_image, end_image, start_year, end_year, caption
    )
    # 
    if save_path:
        save_figure(fig, save_path, dpi)

    if show:
        plt.show()

if __name__ == '__main__':
    args = process_args()
    
    compare_year_images(args.intersection_id, args.startyear, args.endyear, args.z_level, args.outfile, args.show)
    