import sys
from pathlib import Path
from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_leaflet as dl

script_dir = Path(__file__).resolve()
dashboard_root = script_dir.parent.parent
sys.path.append(str(dashboard_root))

from setup import YEARS, ZLEVEL, TILE_URL_TEMPLATE, INITIAL_CENTER, INITIAL_ZOOM

def main_card():
    return dbc.Card(
        color="dark", inverse=True,
        children=dbc.CardBody([
            html.Div([
                html.H2('Select a Location...'),
                dcc.Input(
                    id="search-input",
                    type="text",
                    placeholder="Enter address...",
                    style={"width": "70%"},
                    className="bg-secondary text-light"
                ),
                html.Button(
                    "Go", id="search-button", n_clicks=0,
                    className="ms-2 btn btn-secondary"
                )
            ], style={"marginBottom": "1rem"}),
            # Main Map
            dl.Map(
                id="map",
                center=INITIAL_CENTER,
                zoom=INITIAL_ZOOM,
                minZoom=0,
                maxZoom=25,
                children=[
                    dl.TileLayer(
                        id="ortho-layer",
                        url=TILE_URL_TEMPLATE.format(year=YEARS[-1]),
                        maxNativeZoom=20,
                        maxZoom=25
                    ),
                    dl.ZoomControl(),
                    dl.ScaleControl(),
                    dl.LayerGroup(id="marker-layer")
                ],
                style={"width": "100%", "height": "75vh", "border": "2px solid #444"}
            ),
            # Main Slider
            html.Div([
                html.Label("Base Imagery Year:", className="text-light"),
                dcc.Slider(
                    id="year-slider",
                    min=YEARS[0], max=YEARS[-1], step=2,
                    marks={y: {'label': str(y), 'style': {'color': 'lightgray'}} for y in YEARS},
                    value=YEARS[-1]
                )
            ], style={"marginBottom": "1rem"})
        ])
    )