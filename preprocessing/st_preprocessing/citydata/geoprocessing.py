import geopandas as gpd

def buffer_locations(location_nodes, buffer_width=100, crs='EPSG:2263'): #crs:CRS='EPSG'):
    location_nodes_copy = location_nodes.copy()
    location_nodes_copy['buffer'] = location_nodes_copy.to_crs(crs).buffer(buffer_width)
    location_nodes_copy = location_nodes_copy.set_geometry('buffer')

    return location_nodes_copy
