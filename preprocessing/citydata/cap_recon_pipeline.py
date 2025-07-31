import os, sys
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd
import geopandas as gpd

project_dir = Path(__file__).resolve().parent.parent.parent
print(f"Treating '{project_dir}' as `project_dir`")
sys.path.append(str(project_dir))

from features.load import load_standard 
from features_pipeline import load_location, buffer_locations # This is awkward

load_dotenv()

DATA_PATH = project_dir / Path(str(os.getenv('OPENNYC_PATH')))
CORE_FILE_NAME = Path('Street_and_Highway_Capital_Reconstruction_Projects_-_Intersection_20250721.csv')


#sts_hwys_df = pd.read_csv(DATA_PATH / CORE_FILE_NAME)
#gpd.GeoDataFrame(sts_hwys_df, geometry= from_wkt(sts_hwys_df['the_geom']))

COLUMNS_TO_KEEP = ['ProjectID','ProjTitle', 'FMSID', 'FMSAgencyID',
       'LeadAgency', 'Managing Agency', 'ProjectDescription',
       'ProjectTypeCode', 'ProjectType', 'ProjectStatus', 'ConstructionFY',
       'DesignStartDate', 'ConstructionEndDate', 'CurrentFunding',
       'ProjectCost', 'OversallScope', 'SafetyScope', 'OtherScope',
       'ProjectJustification', 'OnStreetName', 'FromStreetName',
       'ToStreetName', 'OFTCode', 'DesignFY','geometry']

if __name__ == '__main__':
    location_nodes, _ = load_location('Downtown Brooklyn, New York, USA')
    location_buffers = buffer_locations(location_nodes)

    sts_hwys_gdf = load_standard(DATA_PATH / CORE_FILE_NAME)
    sts_hwys_gdf_caprecon = sts_hwys_gdf[sts_hwys_gdf['ProjectType'] == 'CAPITAL RECONSTRUCTION'][COLUMNS_TO_KEEP]

    joined_buffers = location_buffers[['buffer']].sjoin(
        sts_hwys_gdf.set_crs('4326').to_crs('2263'),
        how='left'
    ).rename(columns = {'index_right': 'project_idx'})[['project_idx','ProjectID','ProjTitle','ProjectType', 
                                                        'ProjectStatus', 'ConstructionFY',
              'DesignStartDate', 'ConstructionEndDate', 'CurrentFunding',
              'ProjectCost', 'OversallScope', 'SafetyScope', 'OtherScope',
              'ProjectJustification', 'OnStreetName', 'FromStreetName']]

       # All cols
       #     Index(['buffer', 'index_right', 'the_geom', 'ProjectID', 'ProjTitle', 'FMSID',
       #        'FMSAgencyID', 'LeadAgency', 'Managing Agency', 'ProjectDescription',
       #        'ProjectTypeCode', 'ProjectType', 'ProjectStatus', 'ConstructionFY',
       #        'DesignStartDate', 'ConstructionEndDate', 'CurrentFunding',
       #        'ProjectCost', 'OversallScope', 'SafetyScope', 'OtherScope',
       #        'ProjectJustification', 'OnStreetName', 'FromStreetName',
       #        'ToStreetName', 'BoroughName', 'OFTCode', 'DesignFY', 'Latitude',
       #        'Longitude', 'x', 'y'],
    
    joined_buffers.to_csv(project_dir / Path('data/test_runs/downtown_bk/project_data/changes.csv')) # TODO: make programmatic
    
    print('cap_recon_pipeline')
    print(joined_buffers.columns)