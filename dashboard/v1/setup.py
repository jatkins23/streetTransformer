# Constants
YEARS = list(range(2006, 2025, 2))
ZLEVEL = 20  # Fixed zoom level for tile grid
TILE_URL_TEMPLATE = (
    "https://tiles.arcgis.com/tiles/yG5s3afENB5iO9fj/arcgis/rest/"
    "services/NYC_Orthos_{year}/MapServer/tile/{{z}}/{{y}}/{{x}}"
)
INITIAL_CENTER = [40.7128, -74.0060]
INITIAL_ZOOM = 12
GEOCODE_API = "https://nominatim.openstreetmap.org/search"