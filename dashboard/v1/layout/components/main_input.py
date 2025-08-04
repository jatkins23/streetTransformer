from dash import html, dcc
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
import pandas as pd
from setup import LION_DB
import numpy as np

intersections = LION_DB['StreetNames'].tolist()
df = LION_DB.copy()
df[['street1','street2']] = pd.DataFrame(df['StreetNames'].tolist(), df.index)
all_streets = np.sort(pd.concat([df['street1'], df['street2']]).unique())

def input_view_geocode():
    component =  html.Div([
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
    ], style={"marginBottom": "1rem"})

    return component


def input_view_gmailchips():
    component = html.Div([
        dmc.MultiSelect(
            id="dynamic-street-selector",
            label="Select Streets",
            placeholder="Start typing streets...",
            data=[{"label": s, "value": s} for s in all_streets],
            searchable=True,
            nothingFoundMessage="No options",
            clearable=True,
            value=[],
            styles={"input": {"color": "black"}, 
                    "dropdown": {"color": "black", "zIndex": 9999}
            }
        ),

        #dmc.Space(h=20),
        dmc.Text(id="street-selector-output", size="lg", fw='bold')
    ]
)

    return component
    