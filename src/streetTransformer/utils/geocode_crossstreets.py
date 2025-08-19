from __future__ import annotations

from pathlib import Path
import time
import logging
from typing import Optional, Dict, Any, Iterable
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

from shapely.geometry import Point
import pandas as pd
import geopandas as gpd

from .streets import build_onelineaddress


CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
DEFAULT_BENCHMARK = "Public_AR_Current"   # good default; others: 4=2020, 8=2010 etc.


logger = logging.getLogger('census_geocoder')
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)


# -- helpers
def _request_census(
        oneline_address: str,
        *, 
        benchmark: str = DEFAULT_BENCHMARK,
        timeout: int = 10,
        session: Optional[requests.Session] = None
) -> Dict[str, Any]:
    """Call the API"""
    params = {
        'address': oneline_address,
        'benchmark': benchmark,
        'format': 'json'
    }
    s = session or requests.Session()
    r = s.get(CENSUS_URL, params=params, timeout=timeout)
    r.raise_for_status

    return r.json()

import requests

# def esri_intersection(streetnames:Iterable[str], city:str='New York', state:str='NY', *, max_locations=1):
#     url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
#     params = {
#         "f": "json",
#         "SingleLine": f"{' & '.join(streetnames)}, {city}, {state}",
#         "category": "StreetInt",
#         "maxLocations": max_locations,
#         "outFields": "Match_addr,Addr_type,Score"
#     }
#     r = requests.get(url, params=params, timeout=15); r.raise_for_status()
#     cands = r.json().get("candidates", [])
#     if not cands: return None
#     top = cands[0]
#     loc = top["location"]
#     return {"lon": loc["x"], "lat": loc["y"], "name": top.get("address"), "score": top.get("score")}

# def google_intersection(streetnames:Iterable[str], city:str='New York', state:str='NY', api_key=GMAPS_API_KEY):
#     #addr = f"{' & '.join(streetnames)}, {city}, {state}"
#     addr = '54 Riverside Dr. New York, NY, USA'
#     url = "https://maps.googleapis.com/maps/api/geocode/json"
#     params = {"address": addr, "components": f"locality:{city}|administrative_area:{state}", "key": api_key}
#     r = requests.get(url, params=params, timeout=10); r.raise_for_status()
#     res = r.json().get("results", [])
#     print(r.json())
#     if not res: return None
#     loc = res[0]["geometry"]["location"]
#     return {"lon": loc["lng"], "lat": loc["lat"], "name": res[0].get("formatted_address")}


def geocode_intersection(
        streetnames:Iterable[str],
        *,
        city: str = 'New York',
        state: str = 'NY',
        zipcode: Optional[str] = None,
        benchmark: str = DEFAULT_BENCHMARK,
        timeout: int = 10,
        max_retries: int = 3,
        backoff: float = 0.8,
        session: Optional[requests.Session] = None
) -> Optional[Dict[str, Any]]:
    """
    Returns a dict with [lng, lat, matched_address, tigerline_id, side] or None if no match
    """

    query = build_onelineaddress(streetnames, city=city, state=state, zipcode=zipcode)

    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            data = _request_census(query, benchmark=benchmark, timeout=timeout, session=session)
            matches = data.get("result", {}).get("addressMatches", [])

            if not matches:
                return None
            
            m = matches[0]
            coords = m.get("coordinates", {}) # Get Coordinates
            tiger = m.get("tigerLine", {}) or {} # Get TIGER
            return {
                "query": query,
                "matched_address": m.get("matchedAddress"),
                "lng": coords.get("x"),
                "lat": coords.get("y"),
                "tierline_id": tiger.get("tigerLineId"),
                "side": tiger.get("side"),
                "raw": m,
            }
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(backoff * (2 ** attempt))
            else:
                logger.warning(f"Failed to geocode after {max_retries} retries: {query} ({e})")

    return None


if __name__ == '__main__':
    tests = [
        ['W 78 St', 'Riverside Dr'],
        ['Jay St', 'Willoughby St'],
        ['W 54 ST', 'BROADWAY'],
    ]
    for i in tests:
        print(f'{" & ".join(i)}: {geocode_intersection(i)["lng"], geocode_intersection(i)["lat"]}')
        #print(f'{" & ".join(i)}: {esri_intersection(i)}')
        #print(f'{" & ".join(i)}: {google_intersection(i)}')
    print('geocoding from CENSUS API')
