from pathlib import Path
import sys
from typing import List

from dash import html, dash_table, dcc
import dash_bootstrap_components as dbc


script_dir = Path(__file__).resolve()
dashboard_root = script_dir.parent.parent
sys.path.append(str(dashboard_root))

from setup import YEARS

def detail_images_card():
    component = dbc.CardBody([
            html.Div(
                "No location selected",
                id="marker-info",
                className="border border-warning p-2 mb-3",
                style={"whiteSpace": "pre-wrap"}
            ),
            # Image Grid
            html.Div(
                id="detail-images",
                style={"display": "flex", "flexWrap": "wrap", "marginBottom": "1rem"}
            ),
            # Detail grid slider
            html.Div([
                html.Label("Detail Grid Year:", className="text-light"),
                dcc.Slider(
                    id="detail-slider", min=YEARS[0], max=YEARS[-1], step=2,
                    marks={y: {'label': str(y), 'style': {'color': 'lightgray'}} for y in YEARS},
                    value=YEARS[-1], disabled=True
                )
            ], style={"marginBottom": "1rem"})
        ]
    )
    
    return component


def detail_citydata_card():
    # citydata_features = html.Div([
    #     html.Label("Location Features", className="text-light"),
    #     dash_table.DataTable(
    #         id="detail-table",
    #         style_table={'overflowX': 'auto'},
    #         style_header={'backgroundColor': '#333', 'color': 'white'},
    #         style_cell={'backgroundColor': '#222', 'color': 'white', 'textAlign': 'left'},
    #     )
    # ], style={"marginBottom": "1rem"})
    citydata_features = html.Div([
        html.Label("Location Features", className="text-light"),
        dash_table.DataTable(
            id="detail-table",
            style_table={'overflowX': 'auto'},
            style_header={
                'backgroundColor': '#333',
                'color': 'white',
                'textAlign': 'center'
            },
            style_cell={
                'backgroundColor': '#222',
                'color': 'white',
                'textAlign': 'center'  # Center all cell content
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{value} = Y'},
                    'backgroundColor': '#d4edda',  # Light green
                    'color': '#155724'
                },
                {
                    'if': {'filter_query': '{value} = N'},
                    'backgroundColor': '#f8d7da',  # Light red
                    'color': '#721c24'
                }
            ]
        )
    ], style={"marginBottom": "1rem"})

    component = dbc.CardBody([
        citydata_features
    ])
    
    return component

def detail_documents_card():
    pass

def detail_cardHeader(size_options:List[int]=[1,3,5], options_placeholder='Select detail size..'):
    header_text = html.H5("Location Detail", className="m-0 text-white"),

    options_list = [{'label': f'{d}x{d}', 'value': d} for d in size_options]

    detail_select = dcc.Dropdown(
        id='detail-size-select',
        options=options_list,
        placeholder=options_placeholder,
        clearable=False,
        style={'min-width': '150px', 'color':'black'}
    )

    element = dbc.CardHeader(
        dbc.Row(
            [
                dbc.Col(header_text, width='auto'),        
                dbc.Col(detail_select, width='auto', className='ms-auto')
            ],
            align='center',
            justify='between', className='g-0'
        ),
        className='bg-secondary'
    )

    return element

def detail_card():
    element = dbc.Card(
        color="dark", inverse=True,
        children=[
            detail_cardHeader(),
            detail_images_card(),
            detail_citydata_card(),
            dbc.CardBody([
                # Data Table
                # Corner Links
                html.Div([
                    html.Label("Project Documents:", className="text-light"),
                    html.Div(id="detail-links")
                ]),
                dcc.Store(id="detail-store")
            ])
        ]
    )

    return element