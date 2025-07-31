from src.streetTransformer.llms.run_llm_model import run_model#(model, image_paths, stream=True, show=False)
from dash import Input, Output, html, State
from setup import DATA_PATH, AVAILABLE_YEARS, AVAILABLE_INTERSECTIONS
from pathlib import Path
from setup import assemble_location_imagery
from callbacks.utils import encode_image, render_json_list
import json

def register_compare_callbacks(app):
    @app.callback(
        Output('model-output-container', 'children'),
        Input('comparison-run-models', 'n_clicks'),
        State('comparison-intersection-picker', 'value'),
        State('comparison-year-picker-before', 'value'),
        State('comparison-year-picker-after', 'value'),
        State('comparison-zlevel-picker', 'value'),
        State('comparison-model-picker', 'value'),
        prevent_initial_call=True  # ensures it only runs after the button is clicked
    )
    def on_submit(n_clicks, location_id, year_before, year_after, zlevel, models):
        # if not intersection or not year or not models:
        #     return html.Div("Please select all inputs.", style={"color": "red"})
        responses = []

        for model_name in models:
            image_paths = assemble_location_imagery(location_id, DATA_PATH, [year_before, year_after], zlevel)
            try:
                print(f'Running {model_name} model..')
                response = run_model(model_name, image_paths=list(image_paths.values()), stream=True)
                cleaned_response = response.replace("`", '').replace('json','')
                json_response = json.dumps(json.loads(cleaned_response), indent=2)
            except Exception as e:
                json_response = f'Error ({e})'

            responses.append(json_response)

            #(DATA_PATH, zlevel, startyear=year_before, endyear=year_after, outfile=None, verbose=False, write=False)
        print(responses)            
        output = render_json_list(responses, labels=models)
        return output# return html.Div([
        #     html.P(f"Intersection: {intersection}"),
        #     html.P(f"Year: {year}"),
        #     html.P(f"Models: {', '.join(models)}")
        # ])
    
    @app.callback(
            Output('comparison-image-before', 'src'),
            Output('comparison-image-after', 'src'),
            Input('comparison-intersection-picker', 'value'),
            Input('comparison-year-picker-before', 'value'),
            Input('comparison-year-picker-after', 'value'),
            Input('comparison-zlevel-picker', 'value')
    )
    def update_images(location_id, year_before, year_after, zlevel):
        if not all([location_id, year_before, year_after, zlevel]):
            return "", ""
        
        image_paths = assemble_location_imagery(location_id, DATA_PATH, AVAILABLE_YEARS, zlevel)
            
        path_before = Path(image_paths[year_before])
        path_after = Path(image_paths[year_after])

        image_before = encode_image(path_before)
        image_after = encode_image(path_after)

        return image_before, image_after
        