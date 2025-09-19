# Run this script once you have all of your basic features set up in your universe. This creates a more complex "locations" dataset.

# TODO: move this into one of the packages because its important. 
# TODO: Probably move into preprocessing

from pathlib import Path
import geopandas as gpd
import tqdm
import sys


from streettransformer.locations.location import Location
from streettransformer.locations.location_geometry import LocationGeometry
from streettransformer.config.constants import UNIVERSES_PATH

if __name__ == '__main__':
    universe_name = sys.argv[1]

    universe_locations_path = Path('..') / UNIVERSES_PATH / universe_name / 'locations'
    locations_gdf = gpd.read_parquet(universe_locations_path / 'locations_raw.parquet').to_crs('4326')

    # Let's load features data?
    locations = []
    loc_dicts_to_write = []
    lg_dicts_to_write = []
    total_locations=locations_gdf.shape[0]
    for row in tqdm.tqdm(locations_gdf.itertuples(), total=total_locations):
        # First Location
        loc = Location(location_id=row.location_id, universe_name=universe_name, crossstreets=row.crossstreets, centroid=row.geometry)
        locations.append(loc)

        # Then Location serialized
        loc_dicts_to_write.append(loc.to_db())

        # Then location geometry
        lg = LocationGeometry(location_id=row.location_id, centroid=(row.geometry.x, row.geometry.y))
        temp_dict = lg.model_dump()
        temp_df = {k: temp_dict[k] for k in temp_dict.keys() if k not in ['tile_grid']}
        temp_df['geometry'] = row.geometry

        lg_dicts_to_write.append(temp_df)    


    locs_gdf = gpd.GeoDataFrame(loc_dicts_to_write).set_geometry('geometry')
    lgs_gdf = gpd.GeoDataFrame(lg_dicts_to_write).set_geometry('geometry')
    locs_gdf.to_parquet(universe_locations_path / 'locations_compiled.parquet')
    lgs_gdf.to_parquet(universe_locations_path / 'locationgeos_compiled.parquet')
