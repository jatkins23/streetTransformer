from pathlib import Path
from dash import html
import base64
import dash_bootstrap_components as dbc
import json
from typing import List, Dict

# Images
def encode_image(image_path: Path):
    encoded = base64.b64encode(open(image_path, 'rb').read()).decode('utf-8')
    return 'data:image/png;base64,' + encoded

def serve_image(image_path: Path):
    source = encode_image(image_path)
    return html.Img(src=source, style={'height': '500px'})

# json list
def render_json_list(json_dumps_list: List[str], labels=None):
    if labels is None:
        labels = [f"Item {i+1}" for i in range(len(json_dumps_list))]

    print(json_dumps_list)
    return html.Div([
        dbc.Accordion([
            dbc.AccordionItem(
                title=label,
                children=html.Pre(response, style={"whiteSpace": "pre-wrap", "wordBreak": "break-word", "margin": 0}),
            )
            for label, response in zip(labels, json_dumps_list)
        ],
        start_collapsed=False,
        always_open=False,
        flush=True
        )
    ])