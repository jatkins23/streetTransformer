from dash import dcc, html
import dash_bootstrap_components as dbc
from layout.timeline_tab import timeline_tab
from layout.comparison_tab import comparison_tab

layout = dbc.Container([
    html.H1("Urban Design Change Dashboard", className="my-4 text-center text-white"),

    dcc.Tabs([
        dcc.Tab(label="Timeline", children=[timeline_tab], className="custom-tab", selected_className="custom-tab--selected"),
        dcc.Tab(label="Comparison", children=[comparison_tab], className="custom-tab", selected_className="custom-tab--selected"),
    ], className="bg-secondary text-light", style={"borderRadius": "5px"}),
], fluid=True)