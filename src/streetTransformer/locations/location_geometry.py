from pathlib import Path
from typing import Optional, Dict, List, Tuple
from pydantic import BaseModel, Field, field_validator, field_serializer
import sqlite3
#from sqlmodel import SQLModel, Field
import mercantile
from pyproj import Transformer

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
    location_id: int
    centroid: Tuple[float, float]
    tile_width: int                              = 3
    zlevel: int                                  = 20 
    proj_crs: str                                = 'EPSG:2263'
    
    # Derived & Cacheable
    bounds_gcs:  Optional[List[float]]           = None
    bounds_proj: Optional[List[float]]           = None
    center_tile: Optional[mercantile.Tile]       = None
    centroid_p: Optional[Tuple[float, float]]    = None
    tile_grid:   Optional[List[mercantile.Tile]] = None
    
    # Post-init computes the derived fields
    def model_post_init(self, __context):
        # Only compute if missing so that I can load from the cache when necessary

        # Tiles
        self.center_tile = self.center_tile or mercantile.tile(self.centroid[0], self.centroid[1], self.zlevel)
        self.tile_grid = self.tile_grid or generate_tile_grid_from_center_tile(self.center_tile, self.tile_width)
        
        # generate_bounds
        self.bounds_gcs = self.bounds_gcs or get_geometric_bounds_from_tile_grid(self.tile_grid) 
        self.bounds_proj = self.bounds_proj or get_projected_bounds_from_geometric_bounds(self.bounds_gcs, self.proj_crs)

        if self.centroid_p is None:
            # project centroid
            transformer = Transformer.from_crs("EPSG:4326", self.proj_crs, always_xy=True)
            self.centroid_p = transformer.transform(self.centroid[0], self.centroid[1])

    # Serializers - for saving to database
    @field_serializer('center_tile')
    def _serialize_center_tile(self, t: Optional[mercantile.Tile], _info):
        if t is None: 
            return None
        return {'x': t.x, 'y': t.y, 'z': t.z}
    
    @field_serializer('tile_grid')
    def _serialize_tile_grid(self, tiles: Optional[List[mercantile.Tile]], _info):
        if tiles is None: 
            return None
        return [{'x': t.x, 'y': t.y, 'z': t.z} for t in tiles]
    
    # Validators can allow loading back from dicts
    @field_validator('center_tile', mode='before')
    @classmethod
    def _validate_center_tile(cls, v):
        if v is None or isinstance(v, mercantile.Tile): 
            return v
        return mercantile.Tile(x=int(v['x']), y=int(v['y']), z=int(v['z']))
    
    @field_validator('tile_grid', mode='before')
    @classmethod
    def _validate_tile_grid(cls, v):
        if v is None or (v and isinstance(v[0], mercantile.Tile)):
            return v
        return [mercantile.Tile(x=int(d['x']), y=int(d['y']), z=int(d['z'])) for d in v]


# # ---------- DB setup ----------
# dbfile = Path("locations.db")
# conn = sqlite3.connect(dbfile)
# conn.execute("""
# CREATE TABLE IF NOT EXISTS locations (
#     id INTEGER PRIMARY KEY,
#     obj TEXT NOT NULL
# );
# """)

# # ---------- Store a Pydantic instance ----------
# lg = LocationGeometry(centroid=(-73.91, 40.70))
# payload = orjson.dumps(lg.model_dump(mode="json")).decode("utf-8")

# conn.execute("INSERT OR REPLACE INTO locations (id, obj) VALUES (?, ?)", (1, payload))
# conn.commit()

# # ---------- Load back ----------
# row = conn.execute("SELECT obj FROM locations WHERE id=?", (1,)).fetchone()
# if row:
#     restored = LocationGeometry.model_validate(orjson.loads(row[0]))
#     print("Restored:", restored)