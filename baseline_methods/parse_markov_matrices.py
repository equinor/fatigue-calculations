import os
from utils.setup_custom_logger import setup_custom_logger
import pandas as pd 
import numpy as np
from multiprocessing import Pool
from utils.fastnumpyio import load as fastio_load 
from utils.fastnumpyio import save as fastio_save
from natsort import natsorted
import sys

# TODO this function is more general purpose than initially intended, so makes no sense to be here
def get_files_in_dir_matching_identifier(cycle_storage_dir: str, identifier: str):
    # Files are found as strings, so Python sorts them lexicographical where ['10', '1', '2'].sort() = ['1', '10', '2' ]
    # natsort sorts like expected: ['1', '2', '10']
    '''
    matched_files = []
    all_files_in_dir = os.listdir(cycle_storage_dir)
    for file_name in all_files_in_dir:
        if identifier in file_name:
            matched_files.append(cycle_storage_dir + '\\' + file_name)
    return natsorted(matched_files)
    '''
    
    return natsorted([(cycle_storage_dir + '\\' + file_name) for file_name in os.listdir(cycle_storage_dir) if (identifier in file_name)])

def open_npy_cycle_file_and_scale_counts(file, weight):
    # return the array with scaled counts according to weights and 10min->yr factor
    
    # cycles are shaped (n_sectors, n_cycles, 2: (m_range, count) )
    cycles = np.array(fastio_load(file))
    cycles[:, :, 1] *= weight * 6.0
    return cycles

def get_all_moment_cycles_weighted_by_probs_member_i(cycle_storage_dir: str,
                                    logger, 
                                    member: int = 54,
                                    DLC_IDs: list = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b'], 
                                    cluster: str = 'JLN'):
    
    # First concatenate all cycles for all cases within each DLC [scaled_markov_DLC_i], then concatenate all cycles for all DLCs [all_ranges] 
    DLC_file   = fr'{os.getcwd()}\data' +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    all_cycles = [] # To store all the cycles : [[ranges, counts]] for each sector, for all DLCs
    
    for DLC in DLC_IDs:
        
        DLC_info_df = pd.read_excel(DLC_file, sheet_name = DLC)
        probabilities = list(DLC_info_df.Tot_Prob_in_10_percent_idling_scenario_hr_year) # Extract directly from excel
        
        # Collect file paths of prepared cycles from main script previously. Scale all counts according to prob of occurence of case
        file_paths_DLC_i = get_files_in_dir_matching_identifier(cycle_storage_dir, identifier = fr'DB_{cluster}_{DLC}cycles_member{member}')
        multiprocess_args = [(file_paths_DLC_i[i], 
                              probabilities[i]
                             ) for i in range(len(file_paths_DLC_i))]
        
        logger.info(f'Starting markov concatenation on {DLC} with {len(file_paths_DLC_i)} cases')
        with Pool() as p: 
            list_of_cycles_all_cases_DLC_i = p.starmap(open_npy_cycle_file_and_scale_counts, multiprocess_args)       
        
        # Concatenate results along axis 1 (the cycles) to create a large list with all observed cycles
        scaled_markov_DLC_i = np.concatenate(list_of_cycles_all_cases_DLC_i, axis = 1) 
        all_cycles.append(scaled_markov_DLC_i)
        logger.info(f'Finished concatenating {DLC}')

    return np.concatenate(all_cycles, axis = 1) # add all ranges together 

def parse_markov_files_cluster_i(cluster, logger, DLC_IDs = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']):
    out_dir = fr'{os.getcwd()}\output'
    cycles_dir = out_dir + fr'\all_turbines\{cluster}\markov'
    mbr_geos = pd.read_excel(fr'{os.getcwd()}\data\{cluster}_member_geos.xlsx')
    member_2_elevation_map = {k: v for k, v in zip(mbr_geos[f'member_id'], mbr_geos['elevation'])}
    res_path = fr'{os.getcwd()}\output\all_turbines\{cluster}\total_markov_member' + '{}.npy'
    
    logger.info(f'Starting markov parsing for {cluster}, {len(member_2_elevation_map)} members @ {list(member_2_elevation_map.values())} mLat')
    for mbr_idx, member in enumerate( list(member_2_elevation_map.keys()) ):
        logger.info(f'[{mbr_idx}/{len(member_2_elevation_map)}] Adding and weighting all markov ranges for {cluster} member {member} @ {member_2_elevation_map[member]} mLat')
        cycles_member_i = get_all_moment_cycles_weighted_by_probs_member_i(cycle_storage_dir = cycles_dir, logger = logger, member = member, DLC_IDs = DLC_IDs, cluster = cluster)
        
        logger.info(f'Storing npy array for member {member}\n')
        fastio_save(res_path.format(member), cycles_member_i)
        del cycles_member_i # this improves speed signifificantly, not quite sure why, thought it would matter the most for memory, which is not really affected here
        logger.info(f'Stored concatenated cycles in markov matrix for member {member}\n')
    
    logger.info(f'Stored all total markov matrices for each member of cluster {cluster}\n')
    
    return None 

def concatenate_all_DBA_markov_matrices(clusters = ['JLN', 'JLO', 'JLP']):
    logger = setup_custom_logger('markov_parser')
    for cluster in clusters:
        _ = parse_markov_files_cluster_i(cluster, logger)
    return None 

if __name__ == '__main__':
    
    _ = concatenate_all_DBA_markov_matrices(clusters = ['JLN', 'JLO', 'JLP'])
    