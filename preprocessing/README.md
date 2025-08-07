# Preprocessing Pipeline

## Config Inputs:
- `universe`
    - `universe_name`: str
    - `universe_boundaries`: str|shape|gpd.GeoDataFrame # string is an Overpass-geocodable place
    - `universe_cache`: ??
- `locations`:
    - `locations_cache`: bool
    - `locations_source`: str # e.g. LION, OSM, etc
    - `locations_outfile`: Path # e.g. 'lion_loctions.geojson'
- `imagery`:
    - `imagery_dir`: Path # to a directory containing the tile2net output raster files or maybe a raw file # could maybe be live?
    - `tile_size`: int # default: 256
    - `zoom_level`: int # default: 20
    - `tile_gridwidth`: int (odd) # e.g. 3: 3x3 grid around
    - `years`: List[int] # e.g. [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024]
- `citydata`:
    - `citydata_dir`: Path # e.g. OPENNYC_PATH
    - `citydata_features`: Dict[str, json] # default: FEATURE_METADATA
    - `citydata_features_bufferwidth`: int # default: 200 (feet) # streetTransformer
    - `citydata_projects_file_path`: Path # 
    - `citydata_projects_bufferwidth`: int # default: 500 (feet) # streetTransformer
    # TODO: can add some stuff about change
- `documents`:
    - `documents_dir`: Path # e.g. data/project_documents
    - `documents_ref`: Path # path to reference csv with columns: projectid, document_url
    - `documents_ref_columns`: List[str] # e.g. ['projectid', 'document_url']
    - `documents_bufferwidth`: int # default: 1000 (feet). Can make smaller once we confirm they are correctly geocoded
    - `docuemnts_outfile`: Path # path
    - `documents_analyze`: bool # whether to analyze (should this be part of streetTransformer ratgher than? )
    - `documents_models`: ?
- `index`: ??
    - future?

## Questions
Some of these things depend a bit on how we much we want to precompute . I can for now, get away with not precomputing:
- buffers, tile_grids (? - this should be the frist thing I do)

## Goals of Processing Pipeline
- So my goal is to get preprocessing to do the following things:
    1) Load locations (save to data/universes/`universe_name`/`locations_outfile`)
    2) Load and stitch imagery for each location, year (save to data/universes/`universe_name`/imagery/[year]/`location_id`.png)
    3) Load citydata features and assign to locations (save to data/universes/`universe_name`/citydata/features.geojson)
    4) Load citydata project data and assign to locations (save to data/universes/`universe_name`/citydata/projects.geojson)
    5) Load, geolocate documents and assign to locations (save to data/universe/`universe_name`/documents/geolocated.geojson)
    6) Load, digest documents and assign to locations (save to data/universe/`universe_name`/documents/digested.geojson)

## Process
### 1) Load Location
This function finds all `locations` (e.g. intersections) in a given `universe` (e.g. New York City)

- Source Data
locations = load_universe(location, outfile = universe, cache = cache) # If cache, this checks if the universe exists and uses


# Load Project Data