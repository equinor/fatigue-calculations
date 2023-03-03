import os 
import pandas as pd 
import numpy as np 
from utils.DB_turbine_name_funcs import return_turbine_name_from_path, sort_paths_according_to_turbine_names, return_cluster_name_from_path
from utils.setup_custom_logger import setup_custom_logger
import sys

'''
Used for inspecting the damage calculations, to see min lifetime
'''

# TODO calculate utilization over 27.08 years of lifetime to verify that util numbers match with initial DEM scaled calculations

def calculate_lifetime_from_fatigue_lookup_table(df):
    # Assumes damage has been calculated with DFF already
    
    probability_hr_per_yr = df['Tot_Prob_in_10_percent_idling_scenario_hr_year'].to_numpy()
    unweighted_dmg_pr_yr  = df.filter(regex = 'dmg').to_numpy() * 6.0 # array of n_cases, n_sectors -> # six 10-min periods in one hr
    weighted_dmg_pr_yr    = probability_hr_per_yr[:, None] * unweighted_dmg_pr_yr # elementwise multiplication along all rows of the damage-array
    damage_pr_sector_pr_year = weighted_dmg_pr_yr.sum(axis = 0) # summation of all yearly weighted damages for all DLCs, sectorwise; axis=0
    return 1.0 / damage_pr_sector_pr_year

if __name__ == '__main__':
    
    logger = setup_custom_logger('lifetime')
    
    # turbine_name = 'DA_P53_CD'
    # df = pd.read_excel(fr'{os.getcwd()}\output\lookup_table_{turbine_name}.xlsx')
    # lifetimes = calculate_lifetime_from_fatigue_lookup_table(df)
    # print(lifetimes)
    # print(f'Lifetime at limiting sector for {turbine_name} = {lifetimes.min():.2f} years')
    
    res_base_dir = fr'{os.getcwd()}\output\all_turbines'
    paths_to_lookup_tables = [os.path.join(path, name) for path, subdirs, files in os.walk(res_base_dir) for name in files if 'lookup_table' in name]
    paths_to_lookup_tables = sort_paths_according_to_turbine_names(paths_to_lookup_tables)
    turbine_names = [return_turbine_name_from_path(path) for path in paths_to_lookup_tables]
    clusters = [return_cluster_name_from_path(path) for path in paths_to_lookup_tables]
    
    if False:
        df = pd.read_excel( os.path.join(res_base_dir, 'JLO', 'DA_P53_CD', 'lookup_table.xlsx') )
        probability_hr_per_yr = df.groupby('DLC')['Tot_Prob_in_10_percent_idling_scenario_hr_year'].sum() # .to_numpy()
        print(probability_hr_per_yr.sum())
        sys.exit()
    
    res = {}
    for turbine_i, (cluster, turbine_name, lookup_path) in enumerate(zip(clusters, turbine_names, paths_to_lookup_tables)):
        logger.info(f'[Turbine {turbine_i+1} / {len(turbine_names)}] Lifetime calculations from fatigue table for {cluster} {turbine_name}')
        df = pd.read_excel(os.path.join(res_base_dir, cluster, turbine_name, 'lookup_table.xlsx'))
        lifetimes = calculate_lifetime_from_fatigue_lookup_table(df)
        min_lifetime = lifetimes.min()
        res[f'{cluster}_{turbine_name}': min_lifetime]
        print(f'Lifetime at limiting sector for {turbine_name} = {min_lifetime:.2f} years')
        
    pd.DataFrame(res).to_excel( os.path.join(res_base_dir, 'all_lifetimes.xlsx'), index=False)
    logger.info(f'Finished lifetime calc for all {len(turbine_names)} turbine_names')
    