import pandas as pd
import geopandas as gpd

def join_feature(location_buffer_gdf:gpd.GeoDataFrame, feature_gdf_p:gpd.GeoDataFrame, feature_shorthand:str='feat', features_to_keep=['osmid_original', 'street_count','buffer']) -> gpd.GeoDataFrame:
    features_missing = [x 
                        for x in features_to_keep
                        if x not in location_buffer_gdf]

    if len(features_missing) > 0:
        quoted_features_missing = [f"'{f}'" for f in features_missing]
        joined_features_missing = ', '.join(quoted_features_missing)
        msg = f'Error: {joined_features_missing} are missing from `location_buffer_gdf.\n\tEnsure your input gdf is correct or modify `features_to_keep` to be safe'
        raise Exception(msg) 

    ret_gdf =  location_buffer_gdf[features_to_keep].sjoin(
        feature_gdf_p.rename(columns = lambda x: f'{feature_shorthand}_{x}' if x != 'geometry' else 'geometry'),
        how='left',
        rsuffix=feature_shorthand
    )

    return ret_gdf


def count_features_by_location(location_gdf:gpd.GeoDataFrame, feature_gdf_p:gpd.GeoDataFrame, feature_shorthand:str) -> pd.Series:
    joined_gdf = join_feature(location_gdf, feature_gdf_p, feature_shorthand)
    right_index_colname = f'index_{feature_shorthand}'
    grouped = joined_gdf.groupby(level=0)[right_index_colname].nunique(dropna=True)

    return grouped