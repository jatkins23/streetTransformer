import dash
from dash import html, dcc, Output, Input, State, callback_context, no_update, dash_table
import dash_bootstrap_components as dbc
import dash_leaflet as dl

from layout.layout_detail_view import detail_card
from layout.layout_main_view import main_card
from callbacks.map import register_main_callbacks
from callbacks.detail import register_detail_callbacks
from setup import YEARS, ZLEVEL, TILE_URL_TEMPLATE, INITIAL_CENTER, INITIAL_ZOOM

# Initialize Dash app with dark theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])


# App layout
app.layout = dbc.Container(
    fluid=True,
    className="bg-dark text-light p-3",
    children=[
        dbc.Row([
            # Left: Controls + Map
            dbc.Col(width=8, children=[
                main_card()
            ]),
            # Right: Image Grid, Table, and Links
            dbc.Col(width=4, children=[
                detail_card()
            ])
        ])
    ]
)

register_main_callbacks(app)
register_detail_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True)
