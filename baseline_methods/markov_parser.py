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

def get_markov_files_paths(range_storage_path: str, identifier: str):
    # Files are found as strings, so Python sorts them lexicographical where ['10', '1', '2'].sort() = ['1', '10', '2' ]
    # natsort sorts like expected: ['1', '2', '10']
    return natsorted([(range_storage_path + '\\' + file_name) for file_name in os.listdir(range_storage_path) if (identifier in file_name)])

def open_npy_range_and_scale_counts(file, weight):
    # return the array with scaled counts according to weights and 10min->yr factor
    # this can maybe be done faster if all arrays are just loaded regularly, then hstacked, then elementwise multiplied with an extended weight matrix
    ranges = np.array(fastio_load(file))
    ranges[:, :, 1] *= weight * 6.0
    return ranges

def parse_markov_files_npy_member_i(range_storage_path: str, 
                                    member: int = 72,
                                    DLC_IDs: list = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b'], 
                                    cluster_ID: str = 'JLO'):
    
    data_path  = fr'{os.getcwd()}\data'
    DLC_file   = data_path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    all_ranges = [] # To store all the ranges for each sector, for all DLCs
    
    for DLC_ID in DLC_IDs:
        
        DLC_info_df = pd.read_excel(DLC_file, sheet_name = DLC_ID)
        probabilities = list(DLC_info_df.Tot_Prob_in_10_percent_idling_scenario_hr_year) # Extract directly from excel
        
        # Collect file paths of prepared ranges from main script previously. Scale all counts according to prob of occurence of case
        file_paths_DLC_i = get_markov_files_paths(range_storage_path, identifier = fr'DB_{cluster_ID}_{DLC_ID}_member{member}')
        multiprocess_args = [(file_paths_DLC_i[i], probabilities[i]) for i in range(len(file_paths_DLC_i))]
        
        logger.info(f'Starting markov concat on {DLC_ID} with {len(file_paths_DLC_i)} cases')
        
        with Pool() as p: 
            list_of_npy_ranges_per_case = p.starmap(open_npy_range_and_scale_counts, multiprocess_args)       
        
        # Concatenate results along axis 1 (the ranges) -> same as np.hstack(lst) or appending. Add to overall list
        scaled_markov_DLC_i = np.concatenate(list_of_npy_ranges_per_case, axis = 1) 
        all_ranges.append(scaled_markov_DLC_i)
        
        logger.info(f'Finished with {DLC_ID}')

    all_ranges = np.concatenate(all_ranges, axis = 1) # add all ranges together
    
    return all_ranges 


if __name__ == '__main__':
    logger = setup_custom_logger('Main')
    range_storage_path = fr'{os.getcwd()}\output\markov'
    output_path = fr'{os.getcwd()}\output\total_markov_member' + '{}.npy'
    DLC_IDs = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']
    mbr_to_el_map = {54: 22.4, 72: 11.2, 84: 6.5, 91: 4.275} # TODO this should be handled by the geometry file
    
    logger.info(f'Starting markov parsing for {len(mbr_to_el_map)} elevations: {list(mbr_to_el_map.values())}')
    
    for member in list(mbr_to_el_map.keys()):
        
        logger.info(f'Parsing markov ranges for member {member} @ {mbr_to_el_map[member]} mLat')
        ranges_elevation_i = parse_markov_files_npy_member_i(range_storage_path = range_storage_path, member = member, DLC_IDs = DLC_IDs)
        
        logger.info(f'Storing npy array for member {member}')
        fastio_save(output_path.format(member), ranges_elevation_i)
        del ranges_elevation_i # this improves speed signifificantly, not quite sure why, thought it would matter the most for memory, which is not really affected here
    
    logger.info('Stored total markov matrices')
    