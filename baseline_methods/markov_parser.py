import json 
from utils.extract_and_preprocess_data import extract_and_preprocess_data
import os
from utils.setup_custom_logger import setup_custom_logger
import pandas as pd 
import numpy as np
import sys
from multiprocessing import Pool
from utils.fastnumpyio import load as fastio_load 
from utils.fastnumpyio import save as fastio_save
from natsort import natsorted

def get_markov_files_paths(cycle_storage_path: str, identifier: str):
    # Files are found as strings, so Python sorts them lexicographical where ['10', '1', '2'].sort() = ['1', '10', '2' ]
    # natsort sorts like expected: ['1', '2', '10']
    return natsorted([(cycle_storage_path + '\\' + file_name) for file_name in os.listdir(cycle_storage_path) if (identifier in file_name)])

def open_npy_cycle_file_and_scale_counts(file, weight):
    # return the array with scaled counts according to weights and 10min->yr factor
    # possible optimization: all arrays just loaded regularly, then hstacked, then elementwise multiplied with an extended weight matrix
    
    # cycles are shaped (n_sectors, n_cycles, 2: (m_range, count) )
    cycles = np.array(fastio_load(file))
    cycles[:, :, 1] *= weight * 6.0
    return cycles

def parse_markov_files_npy_member_i(cycle_storage_path: str, 
                                    member: int = 72,
                                    DLC_IDs: list = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b'], 
                                    cluster_ID: str = 'JLO'):
    
    # First concatenate all cycles for all cases within each DLC [scaled_markov_DLC_i], then concatenate all cycles for all DLCs [all_ranges] 
    
    DLC_file   = fr'{os.getcwd()}\data' +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    all_cycles = [] # To store all the cycles : [[ranges, counts]] for each sector, for all DLCs
    
    for DLC_ID in DLC_IDs:
        
        DLC_info_df = pd.read_excel(DLC_file, sheet_name = DLC_ID)
        probabilities = list(DLC_info_df.Tot_Prob_in_10_percent_idling_scenario_hr_year) # Extract directly from excel
        
        # Collect file paths of prepared cycles from main script previously. Scale all counts according to prob of occurence of case
        file_paths_DLC_i = get_markov_files_paths(cycle_storage_path, identifier = fr'DB_{cluster_ID}_{DLC_ID}_member{member}')
        multiprocess_args = [(file_paths_DLC_i[i], probabilities[i]) for i in range(len(file_paths_DLC_i))]
        
        logger.info(f'Starting markov concatenation on {DLC_ID} with {len(file_paths_DLC_i)} cases')
        
        with Pool() as p: 
            list_of_cycles_all_cases_DLC_i = p.starmap(open_npy_cycle_file_and_scale_counts, multiprocess_args)       
        
        # Concatenate results along axis 1 (the cycles) to create a large list with all observed cycles
        scaled_markov_DLC_i = np.concatenate(list_of_cycles_all_cases_DLC_i, axis = 1) 
        all_cycles.append(scaled_markov_DLC_i)
        
        logger.info(f'Finished concatenating {DLC_ID}')

    all_cycles = np.concatenate(all_cycles, axis = 1) # add all ranges together
    
    return all_cycles 


if __name__ == '__main__':
    logger = setup_custom_logger('Main')
    
    cluster_ID = 'JLO'
    DLC_IDs = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']
    cycle_storage_path = fr'{os.getcwd()}\output\markov'
    output_path = fr'{os.getcwd()}\output\all_turbines\{cluster_ID}\total_markov_member' + '{}.npy'
    member_geometry = pd.read_excel(fr'{os.getcwd()}\data\{cluster_ID}_members.xlsx')
    member_2_elevation_map = {k: v for k, v in zip(member_geometry[f'member_{cluster_ID}'], member_geometry['elevation'])}
    
    logger.info(f'Starting markov parsing for {cluster_ID}, {len(member_2_elevation_map)} elevations: {list(member_2_elevation_map.values())}')
    for member in list(member_2_elevation_map.keys()):
        logger.info(f'Parsing markov ranges for member {member} @ {member_2_elevation_map[member]} mLat')
        ranges_elevation_i = parse_markov_files_npy_member_i(cycle_storage_path = cycle_storage_path, member = member, DLC_IDs = DLC_IDs)
        
        logger.info(f'Storing npy array for member {member}\n')
        fastio_save(output_path.format(member), ranges_elevation_i)
        del ranges_elevation_i # this improves speed signifificantly, not quite sure why, thought it would matter the most for memory, which is not really affected here
    
    logger.info('Stored total markov matrices')
    