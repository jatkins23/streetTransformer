from typing import List, Tuple, Optional
from pathlib import Path
import os, sys

from shapely.geometry import MultiPoint
import geopandas as gpd
import pandas as pd
import numpy as np
import math
import ast
import json
from argparse import ArgumentParser

from streettransformer.config.constants import UNIVERSES_PATH, DATA_PATH


# Set up local test environment
UNIVERSE_NAME = 'caprecon_plus_control'
UNIVERSE_PATH = UNIVERSES_PATH / UNIVERSE_NAME
DOCS_GEOCODED_FILE =  DATA_PATH / 'processing/documents/crossstreets_to_census_geocoded/geocoded_gemini_to_census2.csv'
DOCUMENTS_PATH = DATA_PATH / 'raw' / 'documents'

def read_docs_geocoded_json(
    filepath: str|Path,
    *,
    keep_data_col: bool = False,
    json_sep: str = "__",
    make_geo: bool = False
) -> pd.DataFrame:
    """
    Read a 2-column text file that comes from the output of a doc geocoding process

    Returns a DataFrame with flattened JSON fields as columns.
    If make_geo=True and geopandas is installed, returns a GeoDataFrame with geometry.

    Parameters
    ----------
    filepath : str
        Path to the file.
    keep_data_col : bool, default False
        If True, include the original parsed dict (or None) in a 'data' column.
    json_sep : str, default "__"
        Separator used when flattening nested JSON keys (via pandas.json_normalize).
    make_geo : bool, default False
        If True, construct a Point geometry from (lng, lat) and return a GeoDataFrame.

    Returns
    -------
    pandas.DataFrame or geopandas.GeoDataFrame
    """
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines
            # Split only on the first comma to preserve commas inside JSON
            try:
                id_str, json_str = line.split(",", 1)
            except ValueError:
                # Line without a comma; skip or raise depending on preference
                continue

            try:
                row_id = int(id_str.strip())
            except ValueError:
                # ID not an int; skip or handle as needed
                continue

            json_str = json_str.strip()
            if json_str.lower() == "null":
                data = None
            else:
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    data = None  # optionally: raise

            rec = {"id": row_id, "data": data}
            records.append(rec)

    if not records:
        return pd.DataFrame(columns=["id"])

    # Flatten JSON dicts (None -> {})
    flattened = pd.json_normalize(
        [r["data"] if isinstance(r["data"], dict) else {} for r in records],
        sep=json_sep,
        max_level=None
    )

    df = pd.DataFrame({"id": [r["id"] for r in records]})
    df = pd.concat([df, flattened], axis=1)

    # Optionally keep original parsed dict
    if keep_data_col:
        df["data"] = [r["data"] for r in records]

    # Ensure lat/lng columns exist even if only in raw.coordinates (y/x)
    # Prefer top-level lat/lng; otherwise fall back to raw__coordinates__y/x
    def _get_col(df, primary, fallback):
        if primary in df.columns:
            return df[primary]
        if fallback in df.columns:
            return df[fallback]
        return pd.Series([pd.NA] * len(df))

    lat = _get_col(df, "lat", f"raw{json_sep}coordinates{json_sep}y")
    lng = _get_col(df, "lng", f"raw{json_sep}coordinates{json_sep}x")

    # Add unified lat/lng columns if missing; don’t overwrite if already present
    if "lat" not in df.columns:
        df["lat"] = lat
    if "lng" not in df.columns:
        df["lng"] = lng

    # Optional: build geometry
    if make_geo:
        try:
            import geopandas as gpd
            from shapely.geometry import Point

            # Build Points, skipping rows without valid coords
            def mk_point(row):
                try:
                    if pd.notna(row["lng"]) and pd.notna(row["lat"]):
                        return Point(float(row["lng"]), float(row["lat"]))
                except Exception:
                    pass
                return None

            geometry = df.apply(mk_point, axis=1)
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
            return gdf
        except ImportError:
            # Fall back to plain DataFrame if geopandas is not available
            pass

    return df

def safe_multipoint(points):
    try:
        return MultiPoint(points) # points must not have nulls in them
    except:
        return None

def get_document_paths(documents_df:pd.DataFrame, documents_path:Path=DOCUMENTS_PATH) -> Tuple[pd.Series, pd.Series]:
    def _generate_doc_paths(project_id:int, title:str, docs:List[str], base_path:Path, data_path:Path=DATA_PATH) -> Tuple[List[Path], List[Path]]:
        # Note: some projects have multiple paths
        abs_paths = []
        rel_paths = []
        for i in range(len(docs)):
            url = docs[i]
            stem = Path(url).stem
            folder = Path(f'{project_id}--{title}')
            file_name = f'{project_id}--{i}--{stem}.pdf'
            abs_path = base_path / folder / file_name
            abs_paths.append(abs_path)
            rel_path = os.path.relpath(abs_path, data_path)
            rel_paths.append(str(rel_path))

        return abs_paths, rel_paths
    
    absolute_paths = []
    relative_paths = []

    for row in documents_df.itertuples():
        abs_paths, rel_paths = _generate_doc_paths(
            project_id   = row.project_id, 
            title        = row.name,
            docs         = ast.literal_eval(row.document_links),
            base_path    = DOCUMENTS_PATH,
            data_path = DATA_PATH
        )

        absolute_paths.append(abs_paths)
        relative_paths.append(rel_paths)
    
    absolute_paths_series = pd.Series(absolute_paths, index=documents_df.index)
    relative_paths_series = pd.Series(relative_paths, index=documents_df.index)

    return absolute_paths_series, relative_paths_series

def group_coordinates_by_project(docs_geocoded_loaded:pd.DataFrame) -> pd.Series:
    temp_docs = docs_geocoded_loaded.copy()
    temp_docs['coord'] = list(zip(temp_docs['lng'], temp_docs['lat']))

    # Create a coords series while removing missing points
    coords = (
        temp_docs
        .groupby('project_id')['coord']
        .agg(lambda xs: [
            pt
            for pt in xs
            if not (isinstance(pt, tuple)
                    and all(math.isnan(v) for v in pt))
        ])
    )
    docs_geocoded_loaded['coords'] = coords

    return docs_geocoded_loaded['coords']

def pipeline(
        docs_geocoded_path:Path = DOCS_GEOCODED_FILE, 
        documents_path:Path = DOCUMENTS_PATH,
        documents_df_path:Path = DOCUMENTS_PATH / 'projects_df.csv',
        out_path:Optional[Path] = None
    ) -> gpd.GeoDataFrame: 
    
    # Load documents df (from the scrape) and add an id
    documents_df = pd.read_csv(documents_df_path, index_col=0)
    documents_df['project_id'] = documents_df.index.values # Not necessary

    # Load the geocoded docs (from gemini output) and add a grouped coordinates
    docs_geocoded_loaded = read_docs_geocoded_json(docs_geocoded_path).rename(columns={'id': 'project_id'})
    
    # Group the coordinates by project_id and set to coords in documents
    documents_df['coords'] = group_coordinates_by_project(docs_geocoded_loaded)
    
    # Document Paths:
    documents_df['absolute_paths'], documents_df['relative_paths'] = get_document_paths(documents_df)

    # Turn into a gdf
    documents_gdf = gpd.GeoDataFrame(
        documents_df, 
        geometry=documents_df['coords'].apply(safe_multipoint), 
        crs='4326')
    
    # Remove columns
    cleaned_gdf = documents_gdf.drop(['document_links','source_url'], axis=1)
    # Write to 
    if out_path:
        cleaned_gdf.drop(['absolute_paths'], axis=1).to_parquet(out_path)

    return cleaned_gdf

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('universe_name', type=str)

    args = parser.parse_args()

    universe_path = UNIVERSES_PATH / args.universe_name

    cleaned_gdf = pipeline(
        docs_geocoded_path  = DOCS_GEOCODED_FILE, 
        documents_path      = DOCUMENTS_PATH,
        out_path            = universe_path / f'documents.parquet'
    )

    # #print(cleaned_gdf.loc[1]['geometry'])
    print(cleaned_gdf[['relative_paths', 'absolute_paths']])

