import os, sys
from pathlib import Path


@dataclass
class Location:
    def __init__(self, location_id, centroid, bbox, stitched)