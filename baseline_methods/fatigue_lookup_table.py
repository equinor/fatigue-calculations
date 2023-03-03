from utils.IO_handler import load_table
from utils.fastnumpyio import load as fastio_load 
from utils.setup_custom_logger import setup_custom_logger
from utils.create_geo_matrix import create_geo_matrix
from utils.create_fatigue_lookup_table import create_fatigue_table_DLC_i
from utils.setup_custom_logger import setup_custom_logger
import numpy as np
import pandas as pd 
import sys
import os
from multiprocessing import Pool
from parse_markov_matrices import get_files_in_dir_matching_identifier_natsorted
from utils.DB_turbine_name_funcs import return_turbine_name_from_path, sort_paths_according_to_turbine_names, return_cluster_name_from_path


'''
Script for calculating lifetime of a turbine's most dimensioning sector damage
'''

DLC_IDs      = ['DLC12', 'DLC24a',  'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']
T_lifetime   = 25.75
N_equivalent = 1e7
DFF          = 3.0
wohler_exp   = 5.0
data_path    = fr'{os.getcwd()}\data'
DLC_file     = data_path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'

def calculate_unweighted_damage_case_i(moment_cycles_closest_member_case_i_path, 
                                       DEM_scaling_factor_from_closest_member, 
                                       cross_section, 
                                       DFF = 3.0):
    
    # input: path to closest member's markov matrices for a case, and the corresponding scaling factor to be applied on the moment ranges
    
    # moment_cycles: (n_sectors, n_cycles, 2) array of all moment_cycles for all sectors of a given elevation's cross-section
    moment_cycles = np.array(fastio_load(moment_cycles_closest_member_case_i_path))

    # nominal stress range for all sectors, corresponding to all n_cycles cycles
    moment_ranges = moment_cycles[:, :, 0] * DEM_scaling_factor_from_closest_member# reduced to shape (n_sectors, n_cycles)
    nominal_stress_ranges = moment_ranges / cross_section['Z'] 
    
    # Adjust the stress according the stress concentration factors for certain angles
    scf_per_sector = np.repeat(np.array([cross_section['scf_per_point']]).T, nominal_stress_ranges.shape[1], axis=1)
    stress_ranges  = (nominal_stress_ranges * scf_per_sector) * cross_section['gritblast'] # elementwise multiplication row wise of stress concentration factors in the relevant sectors
    stress_ranges *= cross_section['alpha']  # elementwise thickness scaling
    
    # Put together the stress cycles in MPa for use in the miner summation
    stress_cycles = np.dstack( (stress_ranges * 1e-6, moment_cycles[:, :, 1])) # stack along third axis / in _D_epth => _D_stack
    
    n_sectors = stress_ranges.shape[0]
    damage = np.zeros(n_sectors)
    for sector_idx in range(n_sectors):
        damage[sector_idx] = cross_section['sn_curve'].miner_sum(stress_cycles[sector_idx]) * DFF
        
    return damage # (n_sectors, ) shaped array

def calculate_damage_from_DEM_scale(sectors, cluster, turbine_name, res_base_dir, DLC_file_path, logger, multiprocess_cases = True):
    # we must backtrack the final DEM calculations to 10-min scenarios for each DLC, unweighted

    logger.info(f'Calculating DEM-scaled damage for {cluster} turbine {turbine_name}')
    n_cpus_in_mp = int(os.cpu_count()) # TODO in case I want to use the computer for something else during iteration
    if multiprocess_cases:
        logger.info(f'Multiprocessing with {n_cpus_in_mp} out of {os.cpu_count()} cores')
    
    # Create geometries with pre-calculated A, I, Z, alpha etc
    geometries_of_interest_df = pd.read_excel(os.path.join(res_base_dir, cluster, turbine_name, 'utils_and_geos_from_structure_report.xlsx'))
    geometries_of_interest_cross_sections = create_geo_matrix(geometries_of_interest_df, sectors)
    util_df = pd.read_excel(os.path.join(res_base_dir, cluster, turbine_name, 'util_rule_vs_report.xlsx'))
    
    util_df['rule_utilization'] = util_df['rule_miner_sum_no_DFF'] * util_df['rule_DFF'] * 100.0
    idx_for_worst_elevation = util_df['rule_utilization'].argmax()
    
    cross_section_at_worst_elevation = geometries_of_interest_cross_sections[idx_for_worst_elevation] 
    worst_elevation_df = util_df.iloc[ idx_for_worst_elevation ]
    closest_member_no  = worst_elevation_df['member_closest']
    DEM_scaling_factor = worst_elevation_df['DEM_scaling_factor']
        
    out_dfs = []
    for DLC_idx, DLC in enumerate(DLC_IDs):
        # Calculate unweighted, 10-min damage from the scaled ranges for the worst elevation for every individual DLC
        DLC_file_df = pd.read_excel(DLC_file_path, sheet_name = DLC)
        n_cases = DLC_file_df.shape[0]
        
        paths_to_markov_cycles_closest_member = get_files_in_dir_matching_identifier_natsorted(cycle_storage_dir = os.path.join(res_base_dir, cluster, 'markov'), identifier = fr'DB_{cluster}_{DLC}cycles_member{closest_member_no}')
        DFF = worst_elevation_df['rule_DFF']
        
        args = [(paths_to_markov_cycles_closest_member[case_i], 
                 DEM_scaling_factor, 
                 cross_section_at_worst_elevation, 
                 DFF
                 ) for case_i in range(n_cases)]
        
        damages_per_case_DLC_i = np.zeros( (n_cases, len(sectors)) )
        
        logger.info(f'[DLC {DLC_idx+1} / {len(DLC_IDs)}] Scaling and calculating for DLC {DLC} with {n_cases} cases')
        if multiprocess_cases:
            with Pool(n_cpus_in_mp) as pool:
                damages_per_case_DLC_i = np.array( pool.starmap(calculate_unweighted_damage_case_i, args) )
        else:
            for case_i in range(n_cases):
                damages_per_case_DLC_i[case_i, :] = calculate_unweighted_damage_case_i(*args[case_i])
                
        out_dfs.append(create_fatigue_table_DLC_i(damages_per_case_DLC_i, DLC, DLC_file_df))
        logger.info(f'[DLC {DLC_idx+1} / {len(DLC_IDs)}] Scaled and calculated DLC {DLC} with {n_cases} cases')
    
    overall_fatigue_table = pd.concat(out_dfs, axis = 0) 
    return overall_fatigue_table 

if __name__ == '__main__':
    
    ## TODO 
    
    # Adujust script to account for the elevations with largest util on elevations with two sn curves throughout the lifetime...
    
    logger = setup_custom_logger('lookup_table')
    logger.info('Initiating damage calculation and fatigue lookup table creation + storage')
    sectors  = [float(i) for i in range(0, 359, 15)]
    res_base_dir = fr'{os.getcwd()}\output\all_turbines'
    paths_to_worst_elevation_comparisons = [os.path.join(path, name) for path, subdirs, files in os.walk(res_base_dir) for name in files if 'worst_elevation_comparison' in name]
    paths_to_worst_elevation_comparisons = sort_paths_according_to_turbine_names(paths_to_worst_elevation_comparisons)
    
    # Final input to calculations
    turbine_names = [return_turbine_name_from_path(path) for path in paths_to_worst_elevation_comparisons]
    clusters = [return_cluster_name_from_path(path) for path in paths_to_worst_elevation_comparisons]
    DLC_file_path = fr'{os.getcwd()}\data' + r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    
    # # TODO for testing testing testing 
    # turbine_names = ['DA_P53_CD']
    # clusters = ['JLO']
    
    for turbine_i, (cluster, turbine_name) in enumerate(zip(clusters, turbine_names)):
        logger.info(f'[Turbine {turbine_i+1} / {len(turbine_names)}] Calculating fatigue table for {cluster} {turbine_name}')
        overall_fatigue_table = calculate_damage_from_DEM_scale(sectors            = sectors, 
                                                                cluster            = cluster, 
                                                                turbine_name       = turbine_name, 
                                                                res_base_dir       = res_base_dir,
                                                                DLC_file_path      = DLC_file_path, 
                                                                logger             = logger, 
                                                                multiprocess_cases = True)
        overall_fatigue_table.to_excel(os.path.join(res_base_dir, cluster, turbine_name, 'lookup_table.xlsx'), index = False)
        logger.info(f'[Turbine {turbine_i+1} / {len(turbine_names)}] Stored fatigue lookup table for {turbine_name}')
    
    logger.info(f'Stored overall lookuptables for all {len(turbine_names)} turbine_names, in their respective folders')
    
    # --- DONE  NOTE STEP 1 - reshape fatigue table like Ida Oline's, including DFF per sector
    # NOTE STEP 2 - calculate lifetime from damages, and verify vs. utilization over 27.1 years!