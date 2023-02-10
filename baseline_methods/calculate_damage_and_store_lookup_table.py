from utils.IO_handler import load_table
from utils.fastnumpyio import load as fastio_load 
from utils.setup_custom_logger import setup_custom_logger
from utils.create_geo_matrix import create_geo_matrix
from utils.create_fatigue_lookup_table import create_fatigue_table_DLC_i
import numpy as np
import pandas as pd 
import sys
import os
from multiprocessing import Pool
from markov_parser import get_markov_files_paths

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

def calculate_damage_scaled_by_DEM_case_i(moment_cycles_path_case_i, DEM_scaling_factor, cross_section, DFF = 3.0):
    # input: path to closest member's markov matrices for a case, and the corresponding scaling factor to be applied on the moment ranges
    
    # moment_cycles: (n_sectors, n_cycles, 2) array of all moment_cycles for all sectors of a given elevation's cross-section
    moment_cycles = np.array(fastio_load(moment_cycles_path_case_i))

    # nominal stress range for all sectors, corresponding to all n_cycles cycles
    moment_ranges = moment_cycles[:, :, 0] * DEM_scaling_factor # reduced to shape (n_sectors, n_cycles)
    nominal_stress_ranges = moment_ranges / cross_section['Z'] 
    
    # Adjust the stress according the stress concentration factors for certain angles
    scf_per_sector = np.repeat(np.array([cross_section['scf_per_point']]).T, nominal_stress_ranges.shape[1], axis=1)
    stress_ranges  = (nominal_stress_ranges * scf_per_sector) * cross_section['gritblast'] # elementwise multiplication row wise of stress concentration factors in the relevant sectors
    stress_ranges *= cross_section['alpha']  # elementwise thickness scaling
    
    # Put together the stress cycles for use in the miner summation
    stress_cycles = np.dstack( (stress_ranges * 1e-6, moment_cycles[:, :, 1])) # stack along third axis / in _D_epth
    
    n_sectors = stress_ranges.shape[0]
    damage = np.zeros(n_sectors)
    for sector_idx in range(n_sectors):
        damage[sector_idx] = cross_section['sn_curve'].miner_sum(stress_cycles[sector_idx]) * DFF
        
    return damage # (n_sectors, ) shaped array

def calculate_damage_from_DEM_scale(logger, sectors, cluster_ID, DLC_file_path):
    logger.info('Calculating scaled damage')
    # we must backtrack the final DEM calculations to 10-min scenarios for each DLC, unweighted
    
    # Create geometries with pre-calculated A, I, Z, alpha etc
    geometries_of_interest_df = pd.read_excel(fr'{os.getcwd()}\unused\marius\DA_P53_CD_all.xlsx')
    geometries_of_interest_df['gritblast'] = geometries_of_interest_df['gritblast'].fillna(1.0)
    geometries_of_interest_df['scf'] = geometries_of_interest_df['scf'].fillna(1.0)
    geometries_of_interest_df['largest_weld_length'] = geometries_of_interest_df['largest_weld_length'].fillna(70)
    geometries_of_interest_cross_sections = create_geo_matrix(geometries_of_interest_df, sectors)
    
    util_df = pd.read_excel(fr'{os.getcwd()}\output\DA_P53_CD_rule_vs_report.xlsx')
    idx_for_worst_elevation = util_df['in_place_utilization'].argmax()
    worst_elevation_cross_section = geometries_of_interest_cross_sections[util_df['in_place_utilization'].argmax()]
    
    worst_elevation_df = util_df.iloc[ idx_for_worst_elevation ]
    closest_member_no  = worst_elevation_df['member_closest']
    DEM_scaling_factor = worst_elevation_df['DEM_scaling_factor']
        
    out_dfs = []
    for DLC_ID in DLC_IDs:
        logger.info(f'DLC {DLC_ID} - start')
        
        # Calculate unweighted, 10-min damage from the scaled ranges for the worst elevation for every individual DLC
        DLC_file_df = pd.read_excel(DLC_file_path, sheet_name = DLC_ID)
        n_cases = DLC_file_df.shape[0]
        probs = list(DLC_file_df['Tot_Prob_in_10_percent_idling_scenario_hr_year'])
        
        file_paths_DLC_i = get_markov_files_paths(cycle_storage_path = fr'{os.getcwd()}\output\markov', identifier = fr'DB_{cluster_ID}_{DLC_ID}_member{closest_member_no}')
        args = [(file_paths_DLC_i[case_i], DEM_scaling_factor, worst_elevation_cross_section) for case_i in range(n_cases)]
        
        with Pool() as pool:
            damages_per_case = np.array( pool.starmap(calculate_damage_scaled_by_DEM_case_i, args) )
        
        out_dfs.append(create_fatigue_table_DLC_i(damages_per_case, DLC_ID, probs))

        logger.info(f'DLC {DLC_ID} - end')
    
    overall_fatigue_table = pd.concat(out_dfs, axis = 0) 
    return overall_fatigue_table 

if __name__ == '__main__':
    
    logger = setup_custom_logger('main')
    sectors = [float(i) for i in range(0, 359, 15)]
    cluster_ID = 'JLO'
    DLC_file_path = fr'{os.getcwd()}\data' + r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'

    overall_fatigue_table = calculate_damage_from_DEM_scale(logger, sectors, cluster_ID, DLC_file_path)
    overall_fatigue_table.to_excel(fr'{os.getcwd()}\output\lookup_table_DA_P53_CD.xlsx')
    
    # Future: use that damage to re-calculate lifetimes

    # lifetimes = calculate_lifetime_at_members(method='python', identifier='damage')
    # print(lifetimes)
    # print(f'Minimum lifetime: {lifetimes.min():.2f} years')
    # lifetimes = calculate_lifetime_at_members(method='matlab')
    # print(lifetimes)
    # print(f'Minimum lifetime: {lifetimes.min():.2f} years')
    # create_overall_lookuptable()