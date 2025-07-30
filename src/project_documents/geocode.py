from pathlib import Path
from typing import List, Dict, Optional

from geopy.geocoders import Nominatim
from geopandas import gpd
import argparse

import pandas as pd

# A framework for digesting document pdf files and translating them to geocoded data

# Goals:
# - for a given project:

# - for a given document:
#   - convert to a usable format:
#   - Extract all mentioned intersection locations/cross streets
#   - geocode each using a geocode API
#   - convert this to a multi-string

# Functions: 
#   - take in a document and output a usable format
#   - take in a usable format, run a model, and output a list of geocoded texts
#   - take in a document and output a list of 
#   - take in a list of documents/proects and output a datafile of addresses
#   geocoding: 
#       - take in a cross-street and translate to a point geometry
#       - reconcile multiple point geometries and see if its a linear object

#   CLI:
#       - parse_arguments
#

## ---------------- CLI -----------------##
def parse_arguments():
    parser = argparse.ArgumentParser()
    
    parser.add_argument('location')

    args = parser.parse_args()

    return args


## -------------- Geocoding ---------------##

# Helper function to parse the geocoded text output
def _parse_geocoded_object(geocoded_object, input_text:str): 
    if geocoded_object is None:
        ret = {
            "input_name": input_text,
            "geocoded": None,
            "lat": None,
            "lng": None
        }
    else:
        ret = {
            "input_name": input_text,
            "geocoded": geocoded_object,
            "lat": geocoded_object.latitude,
            "lng": geocoded_object.longitude
        }

    return ret

def geocode_single_text_location(text: str, region:Optional[str]=None, geolocator:Optional[Nominatim]=None): #  -> gpd.Point
    if geolocator is None:
        geolocator = Nominatim(user_agent='test_dfsdsdsf')

    if region is not None:
        text = text + ', ' + region

    try:
        geocoded_location = geolocator.geocode(text)
    except Exception as e:
        print(e)
        geocoded_location = None

    # Parse
    ret = _parse_geocoded_object(geocoded_location, text)

    return ret


def run_model():
    pass


## ---------- Digest Document --------------##
VALID_FILE_EXTENSIONS = ['.png']
def get_locations_from_document(doc_path: Path) -> List[Dict[str, str]]: # outputs a json object
    # Takes in a well formatted document, runs a model to search for locaion data in it
    
    # Check the document type
    if doc_path.suffix.lower() not in VALID_FILE_EXTENSIONS: # TODO: Modularize
        raise ValueError(f'Invalid Filetype. Allowed: {",".join(VALID_FILE_EXTENSIONS)}')

    # Run the model on the file
    model_output = run_model()

    return model_output


def digest_document(doc_path):
    # Check File extension
    # if not in VALID_FILE_EXTENSIONS:
        # convert_document(doc_path, doc_path.suffix.lower())
    # output = get_locations_from_document()
    # output['intersection'].apply(geocode_single_text_location, axis=1)

    pass

if __name__ == '__main__':
    args = parse_arguments()
    geocoded_location = geocode_single_text_location(args.location)

    print(geocoded_location)