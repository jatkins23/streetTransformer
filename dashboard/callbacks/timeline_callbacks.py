from dash import Input, Output, html
from setup import DATA_PATH, AVAILABLE_YEARS, AVAILABLE_INTERSECTIONS
from PIL import Image
from pathlib import Path
from setup import assemble_location_imagery
from callbacks.utils import serve_image, encode_image

def register_timeline_callbacks(app):
    @app.callback(
        Output('timeline-active-image', 'src'),
        Output('timeline-active-image', 'className'),
        Input('year-slider', 'value'),
        Input('intersection-picker', 'value')
    )
    def update_snapshot_image(year, location_id):
        print(year, location_id)

        if location_id:
            image_paths = assemble_location_imagery(location_id, DATA_PATH, AVAILABLE_YEARS, 20)
            return encode_image(Path(image_paths[year])), "fade-in visible"
        
        return "", "fade-in"

