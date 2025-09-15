# Basic
import os, sys
# import io
# import base64
from pathlib import Path
import json

# Data
import pandas as pd

# Dash
from dash import Dash, html, dcc
from dash.dependencies import Output, Input
import dash_bootstrap_components as dbc

# Import Local tabs etc
from layout.tabs import layout as main_layout
from callbacks.timeline_callbacks import register_timeline_callbacks
from callbacks.compare_callbacks import register_compare_callbacks

# Set root path

# Import Local Modules
from streettransformer.utils.image_paths import get_imagery_reference_path, assemble_location_imagery
from streettransformer.config.constants import DATA_PATH, REF_FILE_RELATIVE_PATH, AVAILABLE_YEARS
from ..scripts.test_compare_models import run_all_models
from streettransformer.viz.compare_images import create_comparison_figure
from streettransformer.viz.utils import load_images

location_15_images = assemble_location_imagery(15, DATA_PATH, AVAILABLE_YEARS, 20)

# Initialize Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

# Layout
app.layout = main_layout

# Callbacks
register_timeline_callbacks(app)
register_compare_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True)
