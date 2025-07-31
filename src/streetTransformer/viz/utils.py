from pathlib import Path
from typing import Tuple
import io

import pandas as pd

import base64
from PIL import Image

def get_image_path(location_id:int, year:int, z_level:int, root_dir:Path) -> Tuple[str, Path]:
    ref_file_path = root_dir / f'image_refs_z{z_level}_{year}.csv'
    ref_df = pd.read_csv(ref_file_path)
    row = ref_df.loc[location_id]
    try:
        file_path = Path(str(row['file_path']))
        intx_name = str(row['name'])
        return intx_name, file_path
    except Exception as e:
        print(e)
        return "Unknown", Path("")

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
    title, start_image_path = get_image_path(intx_id, start_year, z_level, ref_dir_path)
    _, end_image_path = get_image_path(intx_id, end_year, z_level, ref_dir_path)
    start_image = Image.open(start_image_path)
    end_image = Image.open(end_image_path)
    
    return title, start_image, end_image


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode()
    return f"data:image/png;base64,{encoded}"
