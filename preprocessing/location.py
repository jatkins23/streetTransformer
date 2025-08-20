from shapely.geometry import Point, box
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import os, sys
import json

import geopandas as gpd
import pandas as pd
from pydantic import BaseModel

PROJECT_PATH = Path(__file__).resolve().parent.parent
print(f'Treating "{PROJECT_PATH}" as `project_path`')
sys.path.append(PROJECT_PATH)

UNIVERSE_NAME = 'caprecon3'
UNIVERSE_PATH = PROJECT_PATH / 'src/streetTransformer/data/universes/' / UNIVERSE_NAME
YEARS = os.listdir(UNIVERSE_PATH / 'imagery')

def _generate_universe_path(universe_name:str) -> Path:
    universe_path = PROJECT_PATH / 'src/streetTransformer/data/universes' / universe_name
    if universe_path.exists():
        return universe_path
    else:
        raise FileNotFoundError(f"{universe_path} doesn't exist!")

from pydantic import BaseModel
from shapely.geometry import Point
from shapely.ops import transform
from pyproj import Proj, Transformer
from .location_imagery import LocationGeometry

# def assemble_images_from_location_id(location_id:int, imagery_path=UNIVERSE_PATH / 'imagery', years:List[str]=YEARS) -> Dict[str, Path|None]:
#     #years_available = os.listdir(imagery_path)
#     potential_paths = {year : imagery_path / year / f'{location_id}.png' for year in years}
#     final_paths = {str(y): (path if path.exists() else None) for y, path in potential_paths.items() if path.exists}
#     return final_paths

class Location: 
    def __init__(self, 
                 location_id:int, 
                 universe_name:str, 
                 crossstreets:List[str], 
                 centroid:Point, 
                 years:List[int|str]=YEARS, 
                 universe_path:Optional[Path]=None):
        self.location_id:int = location_id
        self.universe_name:str = universe_name
        self.crossstreets:List[str] = crossstreets
        self.years:List[str] = [str(y) for y in years]

        # Universe Path
        abs_universe_path = universe_path or _generate_universe_path(self.universe_name)
        self.universe_path:Path = abs_universe_path.relative_to(PROJECT_PATH)
    
        # Geometry - ensure centroid is 4326 somehow
        self.geometry = LocationGeometry(centroid=(centroid.x, centroid.y))
        
        # Load Imagery
        self.imagery_paths:Dict[str, Optional[Path]] = self.load_imagery(self.years)

        # Load Documents
        self.documents:gpd.GeoDataFrame = self.load_documents()

        # Load citydata Projects
        
        # Load citydata Features
        
    def __repr__(self):
        return_string = f"*location_id*: {self.location_id}\n"
        return_string += f"*crossstreets*: {self.crossstreets}"
        return_string += f"*images*: {', '.join(self.imagery_paths.keys())}\n"
        # Geometry
        return_string += f"*geometry*: \n" # add a self.geometry print 
        return_string += f"    *base_tile*: {self.geometry.center_tile}\n"
        return_string += f"    *bbox*: {self.geometry.bounds_gcs}\n"
        # Documents
        return_string += f"*documents*: \n{self.documents[['project_id', 'year', 'name', 'borough']]}"
        
        # Print docs
        return return_string
    
    __str__ = __repr__
    
    def load_imagery(self, years, imagery_path:Optional[Path]=None) -> Dict[str, Optional[Path]]:
        if imagery_path is None:
            imagery_path = self.universe_path / 'imagery'

        if not imagery_path.exists():
            raise FileNotFoundError(f'{imagery_path} not found!')

        potential_paths = {year : imagery_path / year / f'{self.location_id}.png' for year in years}
        final_paths = {
            str(y): (path if path.exists() else None) 
            for y, path in potential_paths.items() 
        }

        # Make relative to universe_path
        relative_paths = {
            y: (path.relative_to(self.universe_path) if path is not None else None)
            for y, path in final_paths.items()
        }
        return relative_paths
    
    def load_documents(self, years:List[str]=YEARS, documents_gdf_path:Optional[Path]=None) -> gpd.GeoDataFrame:
        if documents_gdf_path is None:
            documents_gdf_path = self.universe_path / 'documents.geojson'

        # load the geocoded documents
        documents_gdf = gpd.read_file(documents_gdf_path)

        # Create buffer
        # bbox_p = Point(self.geometry.centroid_p).buffer(1000)

        # Create a bounding box
        documents_gdf_p = documents_gdf.to_crs(self.geometry.proj_crs)
        bbox_p = box(*self.geometry.bounds_proj)

        # Clip by bounding box
        documents_gdf_clipped_p = documents_gdf_p.clip(bbox_p)

        # Filter to years
        # documents_gdf_clipped_filtered_p = documents_gdf_clipped_p[documents_gdf_clipped_p['year'].isin(years)]
        return documents_gdf_clipped_p
    
    def load_citydata_features(self):
        return {}
    
    def load_citydata_projects(self):
        return {}
    
    def to_dict(self) -> dict:
        # imagery_paths: Dict[str, Optional[Path]] -> Dict[str, Optional[str]]
        img = {k: (None if v is None else str(v)) for k, v in self.imagery_paths.items()}
        return {
            "location_id": self.location_id,
            "universe_name": self.universe_name,
            "crossstreets": self.crossstreets,         # list[str]
            # "years": self.years,                       # list[str]
            "universe_path": str(self.universe_path),  # str
            "imagery_paths": img,                     # dict[str, str|None]
            "geometry_json": self.geometry.model_dump_json(),  # str
            "project_docs": self.documents[['project_id', 'year','name']].to_json()
        }
    



