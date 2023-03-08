 
'''
TEST
copy fatigue table for a test

for clusters, turbines
    
    load the util geo from structure report
    inspect if there are any sub-seabed utils that are larger than the ones within the DEM interpol region (below lowest node available - see memeber geos)
        if there is, load the fatigue table and scale damages 
        
do a final check of lifetime

'''

import pandas as pd 
import os 
from utils.setup_custom_logger import setup_custom_logger
from lifetime_calculation_from_lookup import calculate_lifetime_from_fatigue_lookup_table
from multiprocessing import Pool
import sys

def load_and_rescale_lookup_table(lookup_path, util_relation, logger, turbine_name, worst_dd_tot_elevation, worst_dd_tot_util, df_rule_worst_elevation, df_rule_worst_util):
    
        logger.info(f'[{turbine_name}]: Found worst util at {worst_dd_tot_elevation} mLat with util = {worst_dd_tot_util:.2f}')
        logger.info(f'[{turbine_name}]: Compared to rule methods worst at {df_rule_worst_elevation} mLat with util = {df_rule_worst_util:.2f} ')
        logger.info(f'[{turbine_name}]: Fatigue table will be upscaled with a factor of {util_relation:.2f}')    
    
        logger.info(f'[{turbine_name}]: Loading fatigue table')
        lookup_table_df = pd.read_excel(lookup_path, index_col=None)
        logger.info(f'[{turbine_name}]: Loaded fatigue table')
        
        logger.info(f'[{turbine_name}]: Lifetime of worst sector according to original fatigue table: {calculate_lifetime_from_fatigue_lookup_table(lookup_table_df).min():.2f}')
        logger.info(f'[{turbine_name}]: Lifetime of worst sector according to sub-seabed point over 27.1 years: {27.08 / (worst_dd_tot_util / 100):.2f}')
        
        logger.info(f'[{turbine_name}]: Scaling all damages according to relationship between worst and best')  
        lookup_table_df.loc[:, lookup_table_df.columns.str.contains('sector')] *= util_relation # in-place multiplication
        logger.info(f'[{turbine_name}]: Lifetime of worst sector according to adjusted fatigue table: {calculate_lifetime_from_fatigue_lookup_table(lookup_table_df).min():.2f}')
        
        lookup_table_df.to_json(lookup_path.replace('.xlsx', '.json'), double_precision = 15, force_ascii = True, indent = 4)
        lookup_table_df.to_excel(lookup_path, index = False)
        logger.info(f'Stored new lookup table in xlsx and json format')

def find_utils_subseabed_and_scale_lookup_table(info_path, lookup_path, worst_rule_path, member_geo_path, logger, rescale = False):
    df_info = pd.read_excel(info_path)
    turbine_name = df_info['turbine_name'].iloc[0]
    cluster = df_info['cluster'].iloc[0]
    logger.info(f'[{turbine_name}]: Investigating turbine')
    
    # filter for above seabed elevations
    mbr_geo = pd.read_excel(member_geo_path.format(cluster))
    seabed_elevation = mbr_geo['elevation'].min()
    df_info = df_info[ df_info['elevation'] < seabed_elevation ]
    
    # format and sort on Dd_tot values
    df_info = df_info[ df_info['Dd_tot'] != '-'] # filter for - and convert to numeric
    df_info['Dd_tot'] = pd.to_numeric( df_info['Dd_tot'] )
    df_info = df_info.sort_values('Dd_tot', ascending = False)
    
    # find worst util below seabed
    df_worst_Dd_tot = df_info.iloc[[0]]
    worst_dd_tot_elevation = df_worst_Dd_tot['elevation'].iloc[0]
    worst_dd_tot_util = df_worst_Dd_tot['Dd_tot'].iloc[0]
    
    # find worst util where RULe has calculated
    df_rule_worst = pd.read_excel(worst_rule_path)
    df_rule_worst_elevation = df_rule_worst['rule_worst_elevation'].iloc[0]
    df_rule_worst_util = df_rule_worst['rule_worst_utilization'].iloc[0]
    
    # evaluate if the sub-seabed util is worse
    util_relation = worst_dd_tot_util / df_rule_worst_util
    if util_relation > 1.0:
        
        if rescale:
            load_and_rescale_lookup_table(lookup_path, util_relation, logger, turbine_name, worst_dd_tot_elevation, worst_dd_tot_util, df_rule_worst_elevation, df_rule_worst_util)
        else:       
            update_table_with_worst_elevation(path_to_overall_table, turbine_name, logger, df_worst_Dd_tot)
        
    else:
        logger.info('No points with largest util below seabed found')
        
    return None
    

if __name__ == '__main__':
    
    member_geo_path         = fr'{os.getcwd()}\data' +  r'\{}_member_geos.xlsx' # format for cluster
    result_output_dir       = fr'{os.getcwd()}\output\all_turbines'
    info_from_reports_paths = [os.path.join(path, name) for path, subdirs, files in os.walk(result_output_dir) for name in files if 'geos_from_structure_report' in name]
    lookup_table_paths      = [os.path.join(path, name) for path, subdirs, files in os.walk(result_output_dir) for name in files if 'lookup_table.xlsx' in name]
    worst_util_rule_paths   = [os.path.join(path, name) for path, subdirs, files in os.walk(result_output_dir) for name in files if 'worst_elevation' in name]
    
    logger = setup_custom_logger(f'sub-seabed_scaler')
    logger.error('Running this code will alter fatigue tables that might already been adjusted. This leads to corrupted fatigue tables')
    logger.error('Please reconsider why you are running this script, and ensure that the scaling is being done on the original fatigue table')
    sys.exit()
    
    # TODO here we should add a code snippet for generating an overview table of which point that is the defining one as selected by RULE
    # To be a simple with turbine name, cluster, elevation, description/type/name of elevation
    
    # If you want to test functionality for a single turbine: 
    if True:
        info_from_reports_paths = [p for p in info_from_reports_paths if 'DA_P48_AE' in p]
        lookup_table_paths = [p for p in lookup_table_paths if 'DA_P48_AE' in p]
        worst_util_rule_paths = [p for p in worst_util_rule_paths if 'DA_P48_AE' in p]
    
    # Prepare arguments for the scaling function. Can be run multiprocessed or not 
    args = [(info_path, lookup_path, worst_rule_path, member_geo_path, setup_custom_logger(f'sub-seabed_scaler_{i}')) 
            for info_path, lookup_path, worst_rule_path, i 
            in zip(info_from_reports_paths, lookup_table_paths, worst_util_rule_paths, range(len(info_from_reports_paths)))]
    
    if False:
        with Pool() as p:
            _ = p.starmap(find_utils_subseabed_and_scale_lookup_table, args)
            
    else:
        for i in range(len(info_from_reports_paths)):
            _ = find_utils_subseabed_and_scale_lookup_table(*args[i])