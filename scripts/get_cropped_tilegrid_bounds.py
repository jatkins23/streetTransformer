import geopandas as gpd
import os

SAMPLE_IMAGES_PATH = Path('data/sample_images/')
LOCATIONS_PATH = Path('src/streetTransformer/data/universes/caprecon3/locations.feather')

YEARS = [2014, 2018, 2022, 2024]

#os.listdir(SAMPLE_)
locations_gdf = gpd.read_feather(LOCATIONS_PATH).set_index('location_id')
original_crs = locations_gdf.crs
locations_gdf = locations_gdf.to_crs('4326')


sample_location_ids = [int(x.replace('.png', '')) for x in os.listdir(SAMPLE_IMAGES_PATH / '2024')]
print(len(sample_location_ids))

sample_locations_gdf = locations_gdf.loc[sample_location_ids]



centroid_tiles = [mercantile.tile(location.x, location.y, 20) for location in sample_locations_gdf.geometry]
#[mercantile.bounds(t) for t in centroid_tiles]
centroid_tiles[0].x + 1

tile_grids = [
    [
        mercantile.Tile(x=centroid.x + dx, y=centroid.y + dy, z=centroid.z)
        for dy in [-1, 0, 1]
        for dx in [-1, 0, 1]
    ]
    for centroid
    in centroid_tiles
]

tile_grids
grid_bboxes = [[mercantile.bounds(t) for t in location] for location in tile_grids]

def get_bounds(grid_bboxes):
    # Merge into one bounding box
    west   = min(b.west for b in grid_bboxes)
    south  = min(b.south for b in grid_bboxes)
    east   = max(b.east for b in grid_bboxes)
    north  = max(b.north for b in grid_bboxes)

    return (west, south, east, north)


sample_locations_gdf['tile_grid_bounds'] = [get_bounds(bb) for bb in grid_bboxes]

#sample_locations_gdf.to_csv('data/sample_images/locations.csv')

sample_locations_gdf_p = sample_locations_gdf.to_crs(original_crs)

from shapely.geometry import box
sample_locations_gdf_p['tile_grid_bounds_p'] = gpd.GeoSeries(sample_locations_gdf['tile_grid_bounds'].apply(lambda b: box(*b)), crs='4326').to_crs(original_crs)
sample = sample_locations_gdf_p.iloc[0]

sample.geometry


def crop_location(row):
    # using bounds assumes they are square in this projection, which they aren't necessarily
    
    coords = list(sample['tile_grid_bounds_p'].exterior.coords)
    x_coords = [c[0] for c in  coords]
    y_coords = [c[1] for c in  coords]

    # Overall
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)

    # Centroid locations
    centroid_x = row['geometry'].x
    centroid_y = row['geometry'].y

    left   = centroid_x - (width/2)
    top    = centroid_y - (height/2)
    right  = left + width
    bottom = top + height

    #new_bounds = [left + centroid_x, top + centroid_y, right + centroid_x, bottom + centroid_y]
    new_bounds = [left, top, right, bottom]

    # make box
    new_bbox = box(*new_bounds)

    return new_bbox

cropped_bboxes_p = sample_locations_gdf_p.apply(crop_location, axis=1)
cropped_bboxes_coords = cropped_bboxes_p.set_crs(original_crs).to_crs('4326').apply(lambda x: list(x.exterior.coords))
cropped_bboxes_coords_x = cropped_bboxes_coords.apply(lambda c: [c[0] for c in c])
cropped_bboxes_coords_y = cropped_bboxes_coords.apply(lambda c: [c[1] for c in c])

min_x = cropped_bboxes_coords_x.apply(min)
max_x = cropped_bboxes_coords_x.apply(max)
min_y = cropped_bboxes_coords_y.apply(min)
max_y = cropped_bboxes_coords_y.apply(max)


#pd.DataFrame(columns={'min_x': min_x, 'min_y': min_y, 'max_x': max_x, 'max_y': max_y})
bounds_df = pd.concat(
    [min_x, min_y, max_x, max_y], axis = 1 
)
bounds_df.columns = 'min_x, min_y, max_x, max_y'.split(', ')
#bounds_df.apply(lambda row: )



sample_locations_gdf['cropped_grid_bounds'] = [list(x) for x in zip(min_x, min_y, max_x, max_y)]
sample_locations_gdf.to_csv('data/sample_images/locations.csv')