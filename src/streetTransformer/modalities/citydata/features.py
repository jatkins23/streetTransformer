from pathlib import Path


# So this module will take data from streetTransformer/data/universes/[universe]/citydata. 
#   These are summary files generated during/by preprocessing.

# It will allow a user to do three things with it:
#   - `summarize`: For a given `location`, `date` and `buffer`, it will return a summarize view of projects in the 


# DO 

def summarize_features_at_time(coordinates, summary_data_gdf, buffer_width, date) -> pd.DataFrame:
    pass

def return_features_for_a_given_time(coordinates):
    pass

def visualize(cooridnates):
    pass