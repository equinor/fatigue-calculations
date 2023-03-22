import os 
import pandas as pd 
import numpy as np 
from utils.DB_turbine_name_funcs import return_turbine_name_from_path, sort_paths_according_to_turbine_names, return_cluster_name_from_path
from utils.setup_custom_logger import setup_custom_logger
import sys

'''
Used for inspecting the damage calculations, to see min lifetime
'''

def calculate_lifetime_from_fatigue_lookup_table(df):
    # Assumes damage has been calculated with DFF already
    probability_hr_per_yr = df['Tot_Prob_in_10_percent_idling_scenario_hr_year'].to_numpy()
    unweighted_dmg_pr_yr  = df.filter(regex = 'damage').to_numpy() * 6.0 # array of n_cases, n_sectors -> # six 10-min periods in one hr
    weighted_dmg_pr_yr    = probability_hr_per_yr[:, None] * unweighted_dmg_pr_yr # elementwise multiplication along all rows of the damage-array
    damage_pr_sector_pr_year = weighted_dmg_pr_yr.sum(axis = 0) # summation of all yearly weighted damages for all DLCs, sectorwise; axis=0
    return 1.0 / damage_pr_sector_pr_year

def read_any_filetype(file):
    print(file)
    if file.endswith(('.csv', 'tsv')) :
        df = pd.read_csv(file)
    elif file.endswith('.json'):
        df = pd.read_json(file)
    elif file.endswith('.xml'):
        df = pd.read_xml(file)
    elif file.endswith(('.xls','xlsx')):
        df = pd.read_excel(file)
    elif file.endswith('.hdf'):
        df = pd.read_hdf(file)           
    elif file.endswith('.sql'):
        df = pd.read_sql(file)
    else:
        raise ValueError(f'Unsupported filetype: {file}')
    return df

if __name__ == '__main__':
    
    logger = setup_custom_logger('lifetime')    
    
    file_format = '.json' # xlsx or json
    file_name_key = 'fatigue_damage' # lookup_table or fatigue_damage
    file_loc = "blob" # blob or all_turbines
    
    res_base_dir = os.path.join( os.getcwd(), "output", file_loc)
    paths_to_lookup_tables = [os.path.join(path, name) for path, subdirs, files in os.walk(res_base_dir) 
                              for name in files if ((file_name_key in name) and (file_format) in name)]
    
    paths_to_lookup_tables = sort_paths_according_to_turbine_names(paths_to_lookup_tables)
    
    # Example of calculating lifetime for a single turbine:
    if False:
        paths_to_lookup_tables = [p for p in paths_to_lookup_tables if 'DA_P57_DE' in p]
        store_result = False
    else:  
        store_result = True
    
    store_result = False
    
    paths_to_lookup_tables = sort_paths_according_to_turbine_names(paths_to_lookup_tables)
    turbine_names = [return_turbine_name_from_path(path) for path in paths_to_lookup_tables]
    clusters = [return_cluster_name_from_path(path) for path in paths_to_lookup_tables]
    
    res = {'turbine_name': [], 'cluster' : [], 'min_lifetime': []}
    for turbine_i, (cluster, turbine_name, lookup_path) in enumerate(zip(clusters, turbine_names, paths_to_lookup_tables)):
        
        logger.info(f'[Turbine {turbine_i+1} / {len(turbine_names)}] Lifetime calculations from fatigue table for {cluster} {turbine_name}')
        df = read_any_filetype(lookup_path)
        lifetimes = calculate_lifetime_from_fatigue_lookup_table(df)
        min_lifetime = lifetimes.min()
            
        res['turbine_name'].append(turbine_name)
        res['cluster'].append(cluster)
        res['min_lifetime'].append(min_lifetime)
        
        logger.info(f'[{turbine_name}] = util @ 27.08 yrs = {27.08 / min_lifetime * 100:.2f}, lifetime = {min_lifetime:.2f} years')
        
    df = pd.DataFrame(res)
    print(df)
    
    storage_path = os.path.join(res_base_dir, "all_lifetimes_from_fatigue_tables{}".format(f"_fromjson.xlsx" if 'json' in file_format else ".xlsx"))
    if store_result:
        df.to_excel(storage_path, index=False)
        logger.info(f'Stored lifetime calc results in {storage_path}')
    else:
        logger.info(f'Selector for storing file was selected as False - no file stored')
    
    logger.info(f'Finished lifetime calc for all {len(turbine_names)} turbine_names')
    