from pathlib import Path
import sys

import geopandas as gpd

# Set Local environment
# project_path = Path(__file__).resolve().parent.parent.parent.parent
# print(f'compare: Treating "{project_path}" as `project_path`')
# sys.path.append(str(project_path))

# Local imports
from ..locations.location import Location

def get_compare_data_for_location_id_years(locations_gdf: gpd.GeoDataFrame, location_id:int, start_year:int|str, end_year:int|str, universe_name:str):
    row = locations_gdf[locations_gdf['location_id'] == location_id].iloc[0].T.to_dict()

    temp_location = Location(
            location_id=row['location_id'],
            universe_name=universe_name,
            crossstreets=row['crossstreets'],
            centroid=row['geometry']
        )
    
    # Comparison
    comparison = temp_location.compare_years(start_year, end_year)

    return comparison

def get_image_compare_data(locations_gdf: gpd.GeoDataFrame, location_id:int, start_year:int|str, end_year:int|str, universe_name:str):
    compare_data = get_compare_data_for_location_id_years(locations_gdf, location_id, start_year, end_year, universe_name)
    compare_images_list = [
        Path(compare_data['state']['before']['image']),
        Path(compare_data['state']['after']['image'])
    ]
    return compare_images_list


from PIL import Image, ImageDraw, ImageFont

def show_images_side_by_side(image_paths, universe_path: Path, labels=None):
    """
    Open two image paths from a list and show them side by side with optional labels.
    """
    if len(image_paths) != 2:
        raise ValueError("Please provide exactly two image paths.")

    # Open both images
    img1 = Image.open(universe_path / image_paths[0])
    img2 = Image.open(universe_path / image_paths[1])

    # Font setup (default Pillow font if nothing else available)
    try:
        font = ImageFont.load_default()
    except:
        font = None

    # Extra space at bottom if labels are provided
    label_height = 20 if labels else 0

    # Create new canvas
    new_width = img1.width + img2.width
    new_height = max(img1.height, img2.height) + label_height
    combined = Image.new("RGB", (new_width, new_height), "white")

    # Paste images
    combined.paste(img1, (0, 0))
    combined.paste(img2, (img1.width, 0))

    # Draw labels if given
    if labels:
        draw = ImageDraw.Draw(combined)
        if len(labels) != 2:
            raise ValueError("Please provide exactly two labels if using labels.")
        draw.text((img1.width // 2, img1.height + 2), labels[0], fill="black", anchor="ms", font=font)
        draw.text((img1.width + img2.width // 2, img2.height + 2), labels[1], fill="black", anchor="ms", font=font)

    combined.show()
