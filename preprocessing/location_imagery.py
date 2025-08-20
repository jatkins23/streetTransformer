from pathlib import Path
from typing import Optional, Dict, List, Tuple
from pydantic import BaseModel, Field, field_validator
import mercantile
from shapely.geometry import Point
from pyproj import Transformer, Proj

# class LocationImagery:
#     def __init__(self, coords:Tuple[float, float], tile_width:int=3, zlevel:int=20):
#         self.coords = coords
#         centroid_tile:Tile = tile(self.coords[0], self.coords[1], self.zoom_level)
#         tile_grid:List[Tile] = 
#         # coords: Tuple[float, float]
#         # tile_width: int                        = 3
#         # zoom_level: int                        = 20
#         # centroid_tile: Optional[int]           = None
#         # tile_grid: Optional[List[int]]         = None
#         # image_paths: Optional[Dict[str, Path]] = None

#     def model_post_init(self, __context):
#         self.centroid_tile = int(mercantile.tile(self.coords[0], self.coords[1], self.zoom_level))

def _centered_range(n:int) -> List[int]:
    if n % 2 == 0:
        raise ValueError(f"n must be odd, got {n}")
    start = -(n // 2)
    end = n // 2 + 1
    return list(range(start, end))


def generate_tile_grid_from_center_tile(center_tile:mercantile.Tile, tile_width: int) -> List[mercantile.Tile]:
    return [
        mercantile.Tile(x=center_tile.x + dx, y=center_tile.y + dy, z=center_tile.z)
        for dy in _centered_range(tile_width)
        for dx in _centered_range(tile_width)
    ]

def get_bounds_from_gridboxes(grid_bboxes):
    # Merge the bounding boxes for each tile one bounding box
    west   = min(b.west for b in grid_bboxes)
    south  = min(b.south for b in grid_bboxes)
    east   = max(b.east for b in grid_bboxes)
    north  = max(b.north for b in grid_bboxes)

    return [west, south, east, north]

def get_geometric_bounds_from_tile_grid(tile_grid):
    grid_bboxes = [mercantile.bounds(t) for t in tile_grid]

    bbox = get_bounds_from_gridboxes(grid_bboxes)
    return bbox
    
    
def get_projected_bounds_from_geometric_bounds(bbox:List[float], output_crs):
    transformer = Transformer.from_crs("EPSG:4326", output_crs, always_xy=True)
    minx, miny = transformer.transform(bbox[0], bbox[1])
    maxx, maxy = transformer.transform(bbox[2], bbox[3])
    
    return [minx, miny, maxx, maxy]

# TODO: Crop_location
# def crop_location(row):
#     # using bounds assumes they are square in this projection, which they aren't necessarily
    
#     coords = list(sample['tile_grid_bounds_p'].exterior.coords)
#     x_coords = [c[0] for c in  coords]
#     y_coords = [c[1] for c in  coords]

#     # Overall
#     width = max(x_coords) - min(x_coords)
#     height = max(y_coords) - min(y_coords)

#     # Centroid locations
#     centroid_x = row['geometry'].x
#     centroid_y = row['geometry'].y

#     left   = centroid_x - (width/2)
#     top    = centroid_y - (height/2)
#     right  = left + width
#     bottom = top + height

#     #new_bounds = [left + centroid_x, top + centroid_y, right + centroid_x, bottom + centroid_y]
#     new_bounds = [left, top, right, bottom]

#     # make box
#     new_bbox = box(*new_bounds)

#     return new_bbox

class LocationGeometry(BaseModel):
    centroid: Tuple[float, float]
    tile_width: int                          = 3
    zlevel: int                              = 20 
    proj_crs: str                            = 'EPSG:2263'
    bounds_gcs:  List[float]|None            = None
    bounds_proj: List[float]|None            = None
    center_tile: mercantile.Tile|None        = None
    centroid_p: Tuple[float, float]|None     = None
    tile_grid:   List[mercantile.Tile]|None  = None
    
    def model_post_init(self, __context):
        # center_tile
        self.center_tile = mercantile.tile(self.centroid[0], self.centroid[1], self.zlevel)
        
        # tile_grid
        self.tile_grid = generate_tile_grid_from_center_tile(self.center_tile, self.tile_width)
        
        # generate_bounds
        self.bounds_gcs  = get_geometric_bounds_from_tile_grid(self.tile_grid)
        self.bounds_proj = get_projected_bounds_from_geometric_bounds(self.bounds_gcs, self.proj_crs)

        # project centroid
        transformer = Transformer.from_crs("EPSG:4326", self.proj_crs, always_xy=True)
        self.centroid_p = transformer.transform(self.centroid[0], self.centroid[1])
