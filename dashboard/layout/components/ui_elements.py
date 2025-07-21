from setup import AVAILABLE_INTERSECTIONS
from dash import dcc

DEFAULT_OPTIONS = [{"label": f'{value}_{label}', "value": value} for label, value in AVAILABLE_INTERSECTIONS.items()]
DEFAULT_LOCATION = 15

def location_picker(element_id, options=DEFAULT_OPTIONS, placeholder='Select a Location...', searchable=True, initial_value=DEFAULT_LOCATION):
    component = dcc.Dropdown(
        id=element_id,
        options=options,
        placeholder=placeholder,
        searchable=searchable,
        value=initial_value,
        style={'width': '50%', 'margin': 'auto'}
    )
    return component