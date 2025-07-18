from pathlib import Path
from dash import html
import base64

def encode_image(image_path: Path):
    encoded = base64.b64encode(open(image_path, 'rb').read()).decode('utf-8')
    return 'data:image/png;base64,' + encoded

def serve_image(image_path: Path):
    source = encode_image(image_path)
    return html.Img(src=source, style={'height': '500px'})
