from pathlib import Path
import os, sys
import geopandas as gpd
import argparse

from st_preprocessing.config import UNIVERSES_PATH
from st_preprocessing.imagery.download_imagery import download_and_stitch_gdf
from st_preprocessing.preprocess import save_locations # TODO: this will be moved to a better location




# Now loop through the years
YEARS = list(range(2006, 2025, 2))
YEARS = [2006, 2012, 2018, 2024, 2014, 2020, 2022, 2008, 2010, 2016]

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument('locations_path', type=Path)
    # parser.add_argument('-i', '--imagery-path', type=Path)
    # parser.add_argument('-u', '--universe-path', type=Path, default=UNIVERSES_PATH)
    # parser.add_argument('-y', '--years', nargs='*', type=int, default=[2006, 2012, 2018, 2024, 2014, 2020, 2022, 2008, 2010, 2016])
    # args = parser.parse_args()

    locations_path = UNIVERSES_PATH / 'neurips' / 'locations' / 'locations_raw.parquet'
    imagery_path = UNIVERSES_PATH / 'neurips' / 'imagery'
    # if args.universe_path:
    #     locations_path = UNIVERSES_PATH / locations_path
    #     imagery_path = UNIVERSES_PATH / imagery_path
    
    locations_gdf = gpd.read_parquet(locations_path)

    #for year in args.years:
    for year in YEARS:
        year_dir = imagery_path / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        print(f"\tProcessing imagery for year {year}...")

        download_and_stitch_gdf( 
            locations_gdf, 
            year = year, 
            zoom=20, 
            save_dir = year_dir,
            quiet=True
        )

    