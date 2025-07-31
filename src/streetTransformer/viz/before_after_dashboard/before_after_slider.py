# Basic datatypes
import os
import sys
from pathlib import Path
import json
from typing import Optional

# Data Processing
import pandas as pd

from PIL import Image

# Viz
import dash
from dash import html
from dash_extensions import BeforeAfter
import dash_bootstrap_components as dbc

#from scripts.test_compare_models import run_all_models
from src.streetTransformer.utils.image_paths import assemble_location_imagery, get_imagery_reference_path
#from src.streetTransformer.viz.compare_images import load_images, create_comparison_figure

# cp data/test_runs/downtown_bk/imagery/processed/stitched/z20/2006/15_Jay_\|_Tech_Place.png viz/before_after_dashboard/assets/15_Jay_\|_Tech_Place_2006.png
# cp data/test_runs/downtown_bk/imagery/processed/stitched/z20/2016/15_Jay_\|_Tech_Place.png viz/before_after_dashboard/assets/15_Jay_\|_Tech_Place_2016.png
# cp data/test_runs/downtown_bk/imagery/processed/stitched/z20/2024/15_Jay_\|_Tech_Place.png viz/before_after_dashboard/assets/15_Jay_\|_Tech_Place_2024.png


# Define functions
def beforeAfterSlider(location_id:int=None, before_year:int=None, after_year:int=None, zlevel:int=None):
    #before_path = 'assets/15_Jay__Tech_Place_2006.png'
    before_path = '../../../data/test_runs/downtown_bk/imagery/processed/stitched/z20/2006/15_Jay_|_Tech_Place.png'
    after_path = '../../../data/test_runs/downtown_bk/imagery/processed/stitched/z20/2024/15_Jay_|_Tech_Place.png'

    before_image = {'src': Image.open(before_path)}
    after_image = {'src': Image.open(after_path)}
    
    component = BeforeAfter(before=before_image, after=after_image,
                            width=512,height=412, value=50, )
    
    return component


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container([
    dbc.Row(
        dbc.Col([
            html.H1("Before-After Dash Component", style={'textAlign':'center'})
        ], width=12)
    ),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.H2("Before and After"),
            beforeAfterSlider(),
        ], width=6),
    ])
])

if __name__ == '__main__':
    app.run(debug=True)