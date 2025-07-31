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
#       - [geocode.py] take in a cross-street and translate to a point geometry
#       - reconcile multiple point geometries and see if its a linear object

#   CLI:
#       - parse_arguments
#