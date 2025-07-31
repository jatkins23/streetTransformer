# TODO
from dash import Output, Input, State, no_update, html
import numpy as np

# Imagery Card
def imagery_card(grid_data, year):
    # Return a card with the images
    if not grid_data:
        return no_update
    items = grid_data.get(str(year), [])

    pass


# Features Card
def get_feature_data(latlng):
    return np.arange(1,5)

def featurize_imagery(images):
    return np.arange(1,5)

def featurize_documents(documents):
    return np.arange(1,5)

def features_card(latlng=None, images = None, documents=None,):
    # Return a card with the relevant location data
    city_data = get_feature_data(latlng, )
    features_from_imagery = featurize_imagery(images)
    features_from_documents = featurize_documents(documents)

    return np.concat([city_data, features_from_imagery, features_from_documents], axis=1)

# Links Card
def assemble_documents(latlng=None):
    return []

def links_card(latlng=None):
    # Return a card with the relevant project links
    links = assemble_documents(latlng)

    return links

def register_detail_callbacks(app):
    # Callback: update images, table, links when detail-slider changes
    @app.callback(
        Output("detail-images", "children"),
        Output("detail-table", "data"),
        Output("detail-table", "columns"),
        Output("detail-links", "children"),
        Input("detail-slider", "value"),
        State("detail-store", "data")
    )
    def update_detail_view(year, grid_data):
        if not grid_data:
            return no_update
        items = grid_data.get(str(year), [])
        imgs = []
        table_data = []
        links = []
        for _, itm in enumerate(items):
            style = {"width": "30%", "margin": ""}
            imgs.append(html.Img(src=itm["url"], style=style))
            table_data.append({"x": itm["x"], "y": itm["y"], "url": itm["url"]})
        columns = [{"name": c, "id": c} for c in ["x", "y", "url"]]
        corner_idxs = [0, len(items)-1] if len(items) > 1 else [0]
        for ci in corner_idxs:
            itm = items[ci]
            links.append(html.Div(html.A(
                f"Tile {itm['x']},{itm['y']}", href=itm['url'], target="_blank"
            ), style={"marginBottom": "0.5rem"}))
        return imgs, table_data, columns, links
