import yaml
from pathlib import Path
import geopandas as gpd
import argparse
import os

from .data_load.load_lion import load_lion_default # TODO: Switch to load_universe using lionsource
#from citydata.features_pipeline import  # TODO: Switch to load_universe using lionsource
from .imagery.download_imagery import download_and_stitch_gdf

# -----------------------------
# Load Config
# -----------------------------
def load_config(config_path: str) -> dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

project_path = Path(__file__).resolve().parent.parent
print(f'Using "{project_path}" as `project_path')

# -----------------------------
# Serialize locations file (move to locations)
# -----------------------------
def save_locations(locations_gdf:gpd.GeoDataFrame, save_path:Path) -> None:
    save_path.mkdir(parents=True, exist_ok=True)
    copy_gdf = locations_gdf.copy()
    copy_gdf['crossstreets'] = copy_gdf['crossstreets'].apply(lambda x: ' | '.join(x))

    copy_gdf.to_file(save_path)

# -----------------------------
# Preprocessing Steps
# -----------------------------
def load_locations(cfg, silent:bool=False) -> gpd.GeoDataFrame:
    """
    Step 1: Load locations and save to:
    data/universes/{universe_name}/{locations_outfile}
    """
    universe_name = cfg["universe"]["universe_name"]
    universe_boundary = cfg["universe"]["universe_boundary"]
    
    out_path = Path(cfg['universe']['universe_path']) / universe_name / cfg['locations']['locations_outfile']
    out_path.parent.mkdir(parents=True, exist_ok=True)

    locations_gdf = load_lion_default(universe_boundary, out_path) # TODO: pass with `locations_source`
    save_locations(locations_gdf, out_path)
    
    print(f"[Step 1] Loading locations from {cfg['locations']['locations_source']}...")    

    return locations_gdf


def load_and_stitch_imagery(cfg, locations_gdf, silent:bool=False):
    """
    Step 2: Load and stitch imagery for each location and year.
    Save to:
    data/universes/{universe_name}/imagery/{year}/{location_id}.png
    """
    universe_name = cfg["universe"]["universe_name"]
    imagery_dir = Path(cfg['universe']['universe_path']) / universe_name / "imagery"
    imagery_dir.mkdir(parents=True, exist_ok=True)

    # TODO: Iterate over locations and cfg['imagery']['years']
    print("[Step 2] Loading and stitching imagery...")
    for year in cfg["imagery"]["imagery_years"]:
        year_dir = imagery_dir / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        if not silent:
            print(f"\tProcessing imagery for year {year}...")

        download_and_stitch_gdf(
            locations_gdf, 
            year = year, 
            zoom=cfg['imagery']['imagery_zlevel'], 
            save_dir = year_dir
        )


def load_citydata_features(cfg, silent:bool=False):
    """
    Step 3: Load citydata features and assign to locations.
    Save to:
    data/universes/{universe_name}/citydata/features.geojson
    """
    universe_name = cfg["universe"]["universe_name"]
    out_path = Path(cfg['universe']['universe_path']) / universe_name / "citydata/features.geojson"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("[Step 3] Loading citydata features from", cfg['citydata']['citydata_dir'])
    if not silent:
        print(f"\tSaving features to {out_path}")


def load_citydata_projects(cfg, silent:bool=False):
    """
    Step 4: Load citydata projects and assign to locations.
    Save to:
    data/universes/{universe_name}/citydata/projects.geojson
    """
    universe_name = cfg["universe"]["universe_name"]
    out_path = Path(cfg['universe']['universe_path']) / universe_name / "citydata/projects.geojson"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("[Step 4] Loading citydata projects from", cfg['citydata']['citydata_projects_file_path'])
    if not silent:
        print(f"\tSaving projects to {out_path}")


def process_documents_geolocate(cfg, silent:bool=False):
    """
    Step 5: Load, geolocate documents, and assign to locations.
    Save to:
    data/universes/{universe_name}/documents/geolocated.geojson
    """
    universe_name = cfg["universe"]["universe_name"]
    out_path = Path(cfg['universe']['universe_path']) / universe_name / "documents/geolocated.geojson"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("[Step 5] Geolocating documents from", cfg['documents']['documents_ref'])
    if not silent:
        print(f"\tSaving geolocated docs to {out_path}")


def process_documents_digest(cfg, silent:bool=False):
    """
    Step 6: Load, digest documents, and assign to locations.
    Save to:
    data/universes/{universe_name}/documents/digested.geojson
    """
    universe_name = cfg["universe"]["universe_name"]
    out_path = Path(cfg['universe']['universe_path']) / universe_name / "documents/digested.geojson"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("[Step 6] Digesting documents using models:", cfg['documents']['documents_models'])
    if not silent:
        print(f"\tSaving digested docs to {out_path}")


# -----------------------------
# Main Pipeline Runner
# -----------------------------
def run_pipeline(config_path="config.yaml", silent:bool=False):
    cfg = load_config(config_path)
    print("[Pipeline] Starting preprocessing for universe:", cfg['universe']['universe_name'])

    #if cfg['']:  TODO: Some way in the config file to pass in a locations file rathert than loading one.
    locations_gdf = load_locations(cfg, silent)
    load_and_stitch_imagery(cfg, locations_gdf, silent)
    # load_citydata_features(cfg, silent)
    # load_citydata_projects(cfg, silent)
    # process_documents_geolocate(cfg, silent)
    # process_documents_digest(cfg, silent)

    print("[Pipeline] Preprocessing complete.")

# -----------------------------
# ArgParse
# -----------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(description='Collect ')

    parser.add_argument('config_path', type=str, help="Include a config file. See README for details.")
    parser.add_argument('-s','--silent', default=False, help="Run in silent mode (minimize console output)")

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = parse_arguments()
    
    run_pipeline(**vars(args))
