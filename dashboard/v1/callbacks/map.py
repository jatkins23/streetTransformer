import dash
from dash import Output, Input, State, callback_context, no_update
import requests
import dash_leaflet as dl
import mercantile

from setup import YEARS, ZLEVEL, TILE_URL_TEMPLATE, GEOCODE_API

# Helper: compute grid of tiles around a lat/lon
def get_grid_tiles(lat, lon, zoom=ZLEVEL, gridsize=3):
    t = mercantile.tile(lon, lat, zoom)
    delta = gridsize // 2
    xs = [t.x + dx for dx in range(-delta, delta+1)]
    ys = [t.y + dy for dy in range(-delta, delta+1)]
    return [(x, y) for y in ys for x in xs]


def register_main_callbacks(app):# Callback: update base tile layer when base year changes
    @app.callback(
        Output("ortho-layer", "url"),
        Input("year-slider", "value")
    )
    def update_tiles(year):
        return TILE_URL_TEMPLATE.format(year=year)

    # Callback: handle map click or geocode search
    @app.callback(
        Output("marker-layer", "children"),
        Output("map", "center"),
        Output("map", "zoom"),
        Output("marker-info", "children"),
        Output("detail-store", "data"),
        Output("detail-slider", "disabled"),
        Output("detail-slider", "value"),
        Input("map", "click_lat_lng"),
        Input("search-button", "n_clicks"),
        State("search-input", "value"),
        State("year-slider", "value"),
        prevent_initial_call=True
    )
    def update_location(click_lat_lng, n_clicks, query, base_year):
        trigger = callback_context.triggered[0]["prop_id"]
        lat = lon = address = None
        if trigger == "map.click_lat_lng" and click_lat_lng:
            lat, lon = click_lat_lng
        elif trigger.startswith("search-button") and query:
            resp = requests.get(
                GEOCODE_API,
                params={"q": query, "format": "json"},
                headers={"User-Agent": "dash-app"}
            )
            data = resp.json()
            if not data:
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update
            lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
            address = data[0].get("display_name", "")
        else:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update

        marker = dl.Marker(position=[lat, lon])
        # Highlight rectangle on main map
        grid = get_grid_tiles(lat, lon, ZLEVEL)
        xs, ys = zip(*grid)
        b1 = mercantile.bounds(min(xs), min(ys), ZLEVEL)
        b2 = mercantile.bounds(max(xs)+1, max(ys)+1, ZLEVEL)
        highlight = dl.Rectangle(
            bounds=[[b1.north, b1.west], [b2.south, b2.east]],
            color="yellow", weight=3, fill=False
        )
        center = [lat, lon]
        zoom = ZLEVEL
        info = f"Lat: {lat:.5f}, Lon: {lon:.5f}"
        if address:
            info += f"\n{address}"
        grid_data = {str(year): [
            {"x": x, "y": y, "url": TILE_URL_TEMPLATE.format(year=year).format(z=ZLEVEL, x=x, y=y)}
            for x, y in grid
        ] for year in YEARS}
        return [marker, highlight], center, zoom, info, grid_data, False, base_year