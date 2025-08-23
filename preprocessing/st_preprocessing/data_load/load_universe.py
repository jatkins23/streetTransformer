# TODO: define load_universe 9?)
# This module is the beginning of the process. 
# It defines a `load_universe` function which takes in:
    # `universe_name`
    # `source` (LION, OSM, TIGER, etc)
    # `boundaries` (either a boundary file or OSM place geocode, etc).
    # File locations (somehow)
    # `cache`: If true, doesn't re-run the whole transformation

# It checks if the `universe_name` exists in src/streetTransformer/data/universes:
    # If not it creates one, and processes the raw files from the `source` and puts them there
    # If it does, it updates them from the location
    #

# Questions
# - Should this be part of streetTransformer? I don't think it needs to be? But maybe?
# - Should this be a class of some sort? a streetTransformer.universe? Maybe! This is getting out of hand