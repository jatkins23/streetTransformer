from dash import html, dcc
import dash_bootstrap_components as dbc
from layout.components.ui_elements import location_picker
from setup import AVAILABLE_YEARS

timeline_tab = dbc.Container([
    html.H4("Timeline", className="text-white"),

    location_picker('intersection-picker'),

    html.Div([
        html.Img(
            id='timeline-active-image',
            src='',  # Empty by default
            className='fade-in',
            style={
                'height': '500px',
                'border': '2px solid #ccc',
                'padding': '10px',
                'borderRadius': '8px',
                'backgroundColor': '#f8f9fa',
                'boxShadow': '0px 4px 10px rgba(0,0,0,0.1)'
            }
        )
    ], style={
        'display': 'flex',
        'justifyContent': 'center',
        'alignItems': 'center',
        'marginTop': '40px'
    }),

    dcc.Slider(
        id='year-slider',
        min=min(AVAILABLE_YEARS),
        max=max(AVAILABLE_YEARS),
        included=False,
        step=2,
        value=AVAILABLE_YEARS[0],
        marks={year: str(year) for year in AVAILABLE_YEARS},
        className="mt-4"
    )
], className="mt-3")
