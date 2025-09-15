from shapely.geometry import Point, box
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import os, sys
import json
from dataclasses import dataclass, asdict
import logging

import geopandas as gpd
import pandas as pd

from ..config.constants import UNIVERSES_PATH, YEARS

def _generate_universe_path(universe_name:str, universes_path:Path) -> Path:
    universe_path = universes_path / universe_name
    if universe_path.exists():
        return universe_path
    else:
        raise FileNotFoundError(f"{universe_path} doesn't exist!")
    
def _read_filtered_json(path:Path, location_id):
    rows = []
    with open(path, "r") as f:
        for line in f:
            row = json.loads(line)
            if row.get("location_id") == location_id:
                rows.append(row)
    return rows

from shapely.geometry import Point
from .location_geometry import LocationGeometry

@dataclass
class Location: 
    def __init__(self, 
                 location_id:int, 
                 universe_name:str, 
                 crossstreets:List[str], 
                 centroid:Point, 
                 years:List[int|str]=YEARS, 
                 universe_path:Optional[Path]=None):
        self.centroid:Point         = centroid       
        self.location_id:int        = location_id
        self.universe_name:str      = universe_name
        self.crossstreets:List[str] = crossstreets
        self.years:List[str]        = [str(y) for y in years]

        # Universe Path
        abs_universe_path = universe_path or _generate_universe_path(self.universe_name, UNIVERSES_PATH)
        #self.universe_path:Path = abs_universe_path.relative_to(PROJECT_PATH)
        self.universe_path = abs_universe_path
    
        # Geometry - ensure centroid is 4326 somehow
        self.geometry = LocationGeometry(location_id=location_id, centroid=(centroid.x, centroid.y)) or None
        
        # Load Imagery
        self.imagery_paths:Dict[str, Optional[Path]] = self.load_imagery(self.years) or None

        # Load Documents
        try:
            self.documents:gpd.GeoDataFrame = self.load_documents()
        except Exception as e:
            self.documents:gpd.GeoDataFrame = None

        # Load citydata Projects
        self.citydata_projects = self.load_citydata_projects()
        
        
        # Load citydata Features
        try:
            self.citydata_features = self.load_citydata_features() or None
        except Exception as e:
            self.citydata_features = None

        # Results Placeholder
        self.results = {}
    
    # Dunders
    def __repr__(self):
        return_string = f"*location_id*: {self.location_id}\n"
        return_string += f"*crossstreets*: {self.crossstreets}"
        return_string += f"*images*: {', '.join(self.imagery_paths.keys())}\n"
        # Geometry
        return_string += f"*geometry*: \n" # add a self.geometry print 
        return_string += f"    *base_tile*: {self.geometry.center_tile}\n"
        return_string += f"    *bbox*: {self.geometry.bounds_gcs}\n"
        # Documents
        return_string += f"*documents*: \n{self.documents[['project_id', 'year', 'name', 'borough']]}\n"
        return_string += f"*features*: \n{self.citydata_features}"
        
        # Print docs
        return return_string
    
    __str__ = __repr__
    
    # Input Functions
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
    
    def load_documents(self, years:List[str]=YEARS, documents_gdf_path:Optional[Path]=None) -> gpd.GeoDataFrame|None:
        if documents_gdf_path is None:
            documents_gdf_path = self.universe_path / 'documents.parquet'
        
        if not documents_gdf_path.exists():
            raise Warning(f'"{documents_gdf_path}" not found!')
        
        else:
            # load the geocoded documents
            #documents_gdf = gpd.read_file(documents_gdf_path)
            documents_gdf = gpd.read_parquet(documents_gdf_path)

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
        features_path = self.universe_path / 'features'
        features = {}
        for year in self.years:
            features[year] = {}
            fts_year_path = features_path / year 
            fts_files = os.listdir(fts_year_path)
            
            for file in fts_files:
                features_file = gpd.read_parquet(fts_year_path / file)
                features_file_in_location = features_file[features_file['location_id'] == self.location_id]
                features[year][Path(file).stem] = features_file_in_location

        # Generate summary
        self.citydata_features_summary = pd.DataFrame({
            year: {
                feat_name: feats.shape[0]
                for feat_name, feats in features[year].items()
            }
            for year in features.keys()
        })
        
        return features
    
    def load_citydata_projects(self):
        return {}
    

# Example usage
    def load_results_data(self, file_path:Path, model_name:str):
        # Reads in an ndjson that 
        try:
            data = _read_filtered_json(file_path, self.location_id)
            self.results[model_name] = data
        except Exception as e:
            print(e)
    
    # Serialization
    def to_dict(self) -> dict:
        # imagery_paths: Dict[str, Optional[Path]] -> Dict[str, Optional[str]]
        imgs = {k: (None if v is None else str(v)) for k, v in self.imagery_paths.items()}
        return {
            "location_id": self.location_id,
            "universe_name": self.universe_name,
            "crossstreets": self.crossstreets,         # list[str]
            # "years": self.years,                       # list[str]
            "universe_path": str(self.universe_path),  # str
            "imagery_paths": imgs,                     # dict[str, str|None]
            "geometry_json": self.geometry.model_dump_json(),  # str
            #"project_docs": self.documents[['project_id', 'year','name', 'relative_paths']].to_json()
        }
    
    # Serialization
    def to_db(self) -> dict:
        # imagery_paths: Dict[str, Optional[Path]] -> Dict[str, Optional[str]]
        imgs = {k: (None if v is None else str(v)) for k, v in self.imagery_paths.items()}
        return {
            "location_id"   : self.location_id,
            "universe_name" : self.universe_name,
            "crossstreets"  : self.crossstreets,         # list[str]
            "universe_path" : str(self.universe_path),  # str
            "imagery_paths" : imgs,                     # dict[str, str|None]
            "geometry"      : self.centroid,
            #"geometry_id"   : 0,
            #"geometry_obj"  : self.geometry.model_dump_json(),  # str
            "project_docs"  : self.documents[['project_id', 'year','name', 'relative_paths']].to_json(),
            'features'      : self.citydata_features,
            'features_summary': self.citydata_features_summary
        }
    
    # Manipulation
    def compare_years(self, year1:str|int, year2:str|int):
        year1 = str(year1)
        year2 = str(year2)
        if (year1 not in self.years) or (year2 not in self.years):
            raise ValueError('Years: {year1, year2} not valid')
        
        # Images
        image1_path = self.imagery_paths[year1]
        image2_path = self.imagery_paths[year2]

        # Documents
        document_paths = self.documents['relative_paths'] # Can't really filter these

        # Projects
        project_data_cols = []
        project_data = self.citydata_projects # filter to those with completed before 

        # Features
        FEATURE_SUBSETS = ['traffic_calming']
        FEATURE_COLS = ['treatment', 'install_date']
        features1 = {feat: self.citydata_features[year1][feat][FEATURE_COLS].to_dict() for feat in FEATURE_SUBSETS}
        features2 = {feat: self.citydata_features[year2][feat][FEATURE_COLS].to_dict() for feat in FEATURE_SUBSETS}

        compare_data =  {
            'location_id': self.location_id, 
            'state': {
                'before': {
                    'year': year1,
                    'image': image1_path,
                    'features': features1
                },
                'after': {
                    'year': year2,
                    'image': image2_path,
                    'features': features2
                }
            },
            'change': {
                'documents' : document_paths,
                'projects'  : project_data,
            }
        }
        
        return compare_data
        
# from geoalchemy2 import Geometry
# from sqlalchemy import Column, Integer, String, ARRAY, JSON, create_engine
# #from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Base = declarative_base()

# class LocationDB(Base):
#     __tablename__ = 'locations'

#     id = Column(Integer, primary_key = True)
#     location_id     = Column(Integer, primary_key=True)
#     universe_name   = Column(String)
#     crossstreets    = Column(ARRAY(String))
#     universe_path   = Column(String)
#     imagery_paths   = Column(JSON)
#     centroid        = Column(Geometry())
#     geometry_id     = Column(Integer)
#     geometry_obj    = Column(JSON)
#     project_docs    = Column(JSON)