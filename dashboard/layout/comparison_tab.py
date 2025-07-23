from dash import html, dcc, dash_table, Dash
from layout.components.ui_elements import location_picker
import dash_bootstrap_components as dbc
from setup import AVAILABLE_YEARS, AVAILABLE_INTERSECTIONS, AVAILABLE_ZLEVELS, AVAILABLE_MODELS, PROJDATA_FEATURES

comparison_tab = dbc.Container([
    html.H4("Comparison View", className="text-white"),

    # Top control row: zoom and intersection
    html.Div([
        dcc.Dropdown(
            id='comparison-zlevel-picker',
            options=AVAILABLE_ZLEVELS,
            placeholder='Z-Level',
            searchable=False,
            value=AVAILABLE_ZLEVELS[-1],
            style={'width': '150px'}
        ),
        html.Div(style={'flex': 1}),  # spacer
        location_picker('comparison-intersection-picker'),
    ], style={
        'display': 'flex',
        'justifyContent': 'space-between',
        'alignItems': 'center',
        'marginBottom': '30px'
    }),

    # Year pickers and images in side-by-side "boxes"
    html.Div([

        # Left column: Before
        html.Div([
            dcc.Dropdown(
                id='comparison-year-picker-before',
                options=AVAILABLE_YEARS,
                placeholder='Before Year',
                searchable=True,
                value=AVAILABLE_YEARS[0],
                style={'width': '200px', 'margin': '0 auto 10px'}
            ),
            html.Img(id='comparison-image-before', style={
                'height': '500px',
                'border': '2px solid #ccc',
                'padding': '10px',
                'borderRadius': '8px',
                'backgroundColor': '#f8f9fa',
                'boxShadow': '0px 4px 10px rgba(0,0,0,0.1)'
            })
        ], style={
            'display': 'flex',
            'flexDirection': 'column',
            'alignItems': 'center',
            'padding': '20px',
            'backgroundColor': '#ffffff',
            'border': '1px solid #ddd',
            'borderRadius': '10px',
            'boxShadow': '0px 4px 12px rgba(0, 0, 0, 0.05)'
        }),

        # Right column: After
        html.Div([
            dcc.Dropdown(
                id='comparison-year-picker-after',
                options=AVAILABLE_YEARS,
                placeholder='After Year',
                searchable=True,
                value=AVAILABLE_YEARS[-1],
                style={'width': '200px', 'margin': '0 auto 10px'}
            ),
            html.Img(id='comparison-image-after', style={
                'height': '500px',
                'border': '2px solid #ccc',
                'padding': '10px',
                'borderRadius': '8px',
                'backgroundColor': '#f8f9fa',
                'boxShadow': '0px 4px 10px rgba(0,0,0,0.1)'
            })
        ], style={
            'display': 'flex',
            'flexDirection': 'column',
            'alignItems': 'center',
            'padding': '20px',
            'backgroundColor': '#ffffff',
            'border': '1px solid #ddd',
            'borderRadius': '10px',
            'boxShadow': '0px 4px 12px rgba(0, 0, 0, 0.05)'
        })

    ], style={
        'display': 'flex',
        'gap': '40px',
        'justifyContent': 'center',
        'marginBottom': '40px'
    }),

    # Project Data Summary
    html.Div([html.H3('Project Data (In Progress)')]),
    html.Div([
        dash_table.DataTable(
            id="dynamic-table",
            columns=[{"name": col, "id": col} for col in ['n_bike','n_bus','n_plaza','n_calm']],
            data=[],  # Start empty
            style_table={"width": "50%"},
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"}
        )
    ], style={
        "display": "flex",
        "justifyContent": "center",
        "alignItems": "center",
        "flexDirection": "column",
        "width": "100%",
        "padding": "20px",
        "border": "1px solid #ccc",
        "borderRadius": "8px"
    }),

    # Model picker and button
    html.Div([html.H2('Analyze Changes')]),
    html.Div([
        dcc.Dropdown(
            id='comparison-model-picker',
            options=AVAILABLE_MODELS,
            multi=True,
            placeholder='Select Model(s)',
            style={'width': '300px'}
        ),
        html.Button(
            'Run Analysis',
            id='comparison-run-models',
            n_clicks=0,
            style={'marginLeft': '20px'}
        )
    ], style={
        'display': 'flex',
        'justifyContent': 'center',
        'alignItems': 'center',
        'gap': '15px',
        'marginBottom': '30px'
    }),

    dcc.Loading(
        type="circle",  # or "dot", "graph"
        color="#0d6efd",  # bootstrap primary
        children=html.Div(id='model-output-container'),
        style={'marginTop': '20px'}
    )
], className="mt-3")
