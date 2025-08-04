import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(os.getenv('INTX_PROFILING_SRC_PATH')))
from intersection import Intersections

def load_location(place, silent=False):

    inter = Intersections.from_place(place)
    inter.with_options(tolerance=20)

    nodes = inter.nodes
    edges = inter.edges

    return nodes, edges
