import pandas as pd 
import os 
from utils.setup_custom_logger import setup_custom_logger
from lifetime_calculation_from_lookup import calculate_lifetime_from_fatigue_lookup_table
from multiprocessing import Pool
import sys

'''
Script for scaling fatigue tables from RULe that has 
'''

def update_summary_table_with_worst_elevation(worst_util_summary_path, turbine_name, df_worst_Dd_tot, logger):
    
    updated_table_path = worst_util_summary_path.replace(".xlsx", "_subseabed_scaled.xlsx")
    try:
        df = pd.read_excel(updated_table_path, index_col = None)
    except:
        logger.info(f"First time reading the util summary for adjustment, opening original. From here the updated file will be read")
        df = pd.read_excel(worst_util_summary_path, index_col = None)
    
    # Update the values of the turbine 
    df.loc[df["turbine_name"] == turbine_name, "el_rule"] = df_worst_Dd_tot['elevation'].iloc[0]
    df.loc[df["turbine_name"] == turbine_name, "io_rule"] = df_worst_Dd_tot['in_out'].iloc[0]
    df.loc[df["turbine_name"] == turbine_name, "desc_rule"] = df_worst_Dd_tot['description'].iloc[0]
    df.loc[df["turbine_name"] == turbine_name, "util_rule"] = df_worst_Dd_tot['Dd_tot'].iloc[0]
    
    df.to_excel(updated_table_path, index = False)
    logger.info(f"[{turbine_name}] Updated summary table for with new subseabed point")
    return None

def load_rescale_and_save_lookup(lookup_path, util_relation, logger, turbine_name, worst_dd_tot_elevation, worst_dd_tot_util, df_rule_worst_elevation, df_rule_worst_util):
    
        logger.info(f'[{turbine_name}] Found worst util at {worst_dd_tot_elevation} mLat with util = {worst_dd_tot_util:.2f}')
        logger.info(f'[{turbine_name}] Compared to rule methods worst at {df_rule_worst_elevation} mLat with util = {df_rule_worst_util:.2f} ')
        logger.info(f'[{turbine_name}] Fatigue table will be upscaled with a factor of {util_relation:.2f}')    
    
        logger.info(f'[{turbine_name}] Loading fatigue table')
        lookup_table_df = pd.read_excel(lookup_path, index_col=None)
        logger.info(f'[{turbine_name}] Loaded fatigue table')
        
        logger.info(f'[{turbine_name}] Lifetime of worst sector according to original fatigue table: {calculate_lifetime_from_fatigue_lookup_table(lookup_table_df).min():.2f}')
        logger.info(f'[{turbine_name}] Lifetime of worst sector according to sub-seabed point over 27.08 years: {27.08 / (worst_dd_tot_util / 100.0):.2f}')
        
        logger.info(f'[{turbine_name}] Scaling all damages according to relationship between worst and best')  
        lookup_table_df.loc[:, lookup_table_df.columns.str.contains('sector')] *= util_relation # in-place multiplication
        logger.info(f'[{turbine_name}] Lifetime of worst sector according to adjusted fatigue table: {calculate_lifetime_from_fatigue_lookup_table(lookup_table_df).min():.2f}')
        
        out_path = lookup_path.replace(".", "_subseabed_scaled.")
        
        lookup_table_df.to_json(out_path.replace('.xlsx', '.json'), double_precision = 15, force_ascii = True, indent = 4)
        lookup_table_df.to_excel(out_path, index = False)
        
        return None

def find_utils_subseabed_and_scale_lookup_table(info_path, lookup_path, worst_rule_path, member_geo_path, worst_util_summary_path, logger, rescale = False):
    df_info = pd.read_excel(info_path)
    turbine_name = df_info['turbine_name'].iloc[0]
    cluster = df_info['cluster'].iloc[0]
    logger.info(f'[{turbine_name}]: Investigating turbine for subseabed scaling options')
    
    # filter for below seabed elevations
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
            load_rescale_and_save_lookup(lookup_path, util_relation, logger, turbine_name, worst_dd_tot_elevation, worst_dd_tot_util, df_rule_worst_elevation, df_rule_worst_util)
            update_summary_table_with_worst_elevation(worst_util_summary_path, turbine_name, df_worst_Dd_tot, logger)
        else:
            # This slot is left for any testing or printing if needed in the future
            logger.info(f"[{turbine_name}] Found scalable relation, but selector to scale and store is False")
            
    else:
        logger.info(f'[{turbine_name}] No points with largest util below seabed found for {cluster} ')
        
    return None
    

if __name__ == '__main__':
    
    member_geo_path         = os.path.join(os.getcwd(), "data", "{}_member_geos.xlsx")# format for cluster
    result_output_dir       = os.path.join(os.getcwd(), "output", "all_turbines")
    info_from_reports_paths = [os.path.join(path, name) for path, subdirs, files in os.walk(result_output_dir) for name in files if 'utils_and_geos_from_structure_report.xlsx' in name]
    lookup_table_paths      = [os.path.join(path, name) for path, subdirs, files in os.walk(result_output_dir) for name in files if 'lookup_table.xlsx' in name]
    worst_util_rule_paths   = [os.path.join(path, name) for path, subdirs, files in os.walk(result_output_dir) for name in files if 'util_worst_elevation_comparison.xlsx' in name]
    
    worst_util_summary_path = os.path.join(result_output_dir, "utilization_summary_worst_points_Ddtot_vs_inplace_vs_rule.xlsx")
    logger = setup_custom_logger(f'sub-seabed_scaler')
    rescale = True
    
    if rescale and os.path.isfile(worst_util_summary_path.replace(".xlsx", "_subseabed_scaled.xlsx")):
        logger.info(f"Subseabed scaled util summary already found. Removing file before calculating sub seabed scaled summary table again")
        os.remove( worst_util_summary_path.replace(".xlsx", "_subseabed_scaled.xlsx") )
            
    # Prepare arguments for the scaling function. Can be run multiprocessed or not 
    args = [(info_path, lookup_path, worst_rule_path, member_geo_path, worst_util_summary_path, setup_custom_logger(f'sub-seabed_scaler_{i}'), rescale) 
            for info_path, lookup_path, worst_rule_path, i 
            in zip(info_from_reports_paths, lookup_table_paths, worst_util_rule_paths, range(len(info_from_reports_paths)))]
    
    for i in range(len(info_from_reports_paths)):
            _ = find_utils_subseabed_and_scale_lookup_table(*args[i])
            
    logger.info("Subseabed scaling of lookup tables and utilization summary finished")