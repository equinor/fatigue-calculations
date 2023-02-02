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

def open_json_range_and_scale_counts(file, weight):
    with open(file, 'r') as f:
        range_dict = json.load(f)
        df_case_i = pd.DataFrame.from_dict(range_dict)
    
        # transform the counts from observations per 10-min window to a weighted hr/year metric
        # TODO this is a computational bottleneck
        # "on all df elements (which is a list of lists), convert list to numpy array, add moment ranges in col 0, add scaled counts in col 1, and convert back to list of lists"
        return df_case_i.applymap( lambda lst: (np.hstack( (np.array(lst)[:, [0]], np.array(lst)[:, [1]] * weight * 6.0) )).tolist() ) 
    
def add_contents_of_list_of_dataframes(df_list, dummy=None):
    df_out = pd.DataFrame()
    for df in df_list:
        if df_out.empty:
            df_out = df.copy()
        else:
            df_out = df_out + df # TODO check: plus operator is overloaded to use the datatypes of each cell's operator. Here, + on lists will concatenate the lists
    return df_out

def parse_markov_files_json(range_storage_path, 
                       DLC_IDs = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b'], 
                       cluster_ID = 'JLO'):
    
    data_path = fr'{os.getcwd()}\data'
    DLC_file  = data_path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    df_out = pd.DataFrame()
    
    for DLC_ID in DLC_IDs:
        
        DLC_info_df = pd.read_excel(DLC_file, sheet_name=DLC_ID)
        probabilities = list(DLC_info_df.Tot_Prob_in_10_percent_idling_scenario_hr_year) # Extract directly from excel
        n_cases = DLC_info_df.shape[0] # TODO not necessary?
        
        # Note this is one entire loop over all files, just to loop over files again afterwards during calculations
        # but it is readable and can be changed later to do operations during file loading
        file_paths_DLC_i = get_markov_files_paths(range_storage_path, identifier = fr'DB_{cluster_ID}_{DLC_ID}') 
        n_cases = len(file_paths_DLC_i)
        
        multiprocess_args = [(file_paths_DLC_i[i],
                              probabilities[i]
                             ) for i in range(n_cases)]
        
        logger.info(f'Starting markov concatenation on {DLC_ID} with {n_cases} cases')
        
        # each case will have <= k ranges and counts. these can be stored in dataframes, per geometry and sector
        # loop through the cases, scale the counts according to case probability (into hr-basis), and concatenate the scaled ranges for each case into one DF for the current DLC 
        with Pool() as p: 
            list_of_dfs = p.starmap(open_json_range_and_scale_counts, multiprocess_args) # returns a list, len n_cases, of DataFrames with [ranges, counts]         
        
        logger.info(f'Found and scaled all ranges in {DLC_ID} - starting concatenation of the ranges')
        # TODO this was a bottleneck of the computational resource demand of this code
        # The concatenated dataframes becomes very large, and takes a long time to concatenate. However, we can concatenate e.g. a tenth at a time
        size_of_chunks = max(10, int(n_cases / 10)) # must be smaller than the fewest number of cases (12 cases for DLC41b)
        
        # TODO we can let the size of chunks be decided by the size of the list, so that if it is a large list we can use larger chunks!
        chunks = [list_of_dfs[i : i + max(1, size_of_chunks)] for i in range(0, len(list_of_dfs), max(1, size_of_chunks))]
        multiprocess_args = [(chunks[i], 
                              i
                             ) for i in range(len(chunks))]
        
        logger.info(f'Divided ranges per case into {len(chunks)} chunks')
        with Pool() as p: 
            new_list_of_dfs = p.starmap(add_contents_of_list_of_dataframes, multiprocess_args) # returns a list, len n_cases, of DataFrames with [ranges, counts]  
        
        logger.info(f'Found and scaled all ranges in {DLC_ID} - expanding dataframe elements of DLC_i with every new range')
        # TODO the code below could be solved with scaled_markov_DLC_i = add_contents_of_list_of_dataframes(new_list_of_dfs)
        scaled_markov_DLC_i = new_list_of_dfs[0]
        for idx in range(1, len(new_list_of_dfs)):
            scaled_markov_DLC_i = scaled_markov_DLC_i + list_of_dfs[idx]
        
        logger.info(f'Appending to the overall dataframe for all DLCs')
        # Create or append to the final dataframe   
        if df_out.empty:
            df_out = scaled_markov_DLC_i.copy()
        else:
            # Large dataframes
            df_out = df_out + scaled_markov_DLC_i
            
        logger.info(f'Finished with {DLC_ID}')
        
    return df_out

def get_markov_files_paths(range_storage_path: str, identifier: str):
    return [(range_storage_path + '\\' + file_name) for file_name in os.listdir(range_storage_path) if (identifier in file_name)]

def open_npy_range_and_scale_counts(file, weight, case_no):
    # return the array with scaled counts according to weights and 10min->yr factor
    # this can maybe be done faster if all arrays are just loaded regularly, then hstacked, then elementwise multiplied with an extended weight matrix
    ranges = np.array(fastio_load(file))
    ranges[:, :, 1] *= weight * 6.0
    
    # To test if correct weight and case is assigned: NOTE do not use with multiprocessing as it is random in which order things appear in console
    # print(case_no)
    # print(file)
    # print(weight)
    return ranges

def parse_markov_files_npy_member_i(range_storage_path: str, 
                                    member: int = 72,
                                    DLC_IDs: list = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b'], 
                                    cluster_ID: str = 'JLO'):
    
    data_path = fr'{os.getcwd()}\data'
    DLC_file  = data_path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    
    all_ranges = [] # To store all the ranges for each sector, for all DLCs
    for DLC_ID in DLC_IDs:
        
        DLC_info_df = pd.read_excel(DLC_file, sheet_name = DLC_ID)
        probabilities = list(DLC_info_df.Tot_Prob_in_10_percent_idling_scenario_hr_year) # Extract directly from excel
        
        # Collect file paths of prepared ranges from main script previously
        # Files are found as strings, so Python sorts them lexicographical where ['1', '2', '10'].sort() = ['1', '10', '2' ]. natsort sorts like expected - tested
        file_paths_DLC_i = natsorted(get_markov_files_paths(range_storage_path, identifier = fr'DB_{cluster_ID}_{DLC_ID}_member{member}')) 
        
        n_cases = len(file_paths_DLC_i)
        multiprocess_args = [(file_paths_DLC_i[i], probabilities[i], i) for i in range(n_cases)] # TODO check if done properly
        
        logger.info(f'Starting markov concat on {DLC_ID} with {n_cases} cases')
        
        # list_of_npy_ranges_per_case = []
        # for args in multiprocess_args:
        #     list_of_npy_ranges_per_case.append(open_npy_range_and_scale_counts(*args))
        
        with Pool() as p: 
            list_of_npy_ranges_per_case = p.starmap(open_npy_range_and_scale_counts, multiprocess_args)       
        
        # TODO maybe multiply with the probabilities here instead of in function above -> create p = [p[0]*128, p[1]*128, ...] and dot product
        # TODO only save ranges with nonzero counts?
        scaled_markov_DLC_i = np.concatenate(list_of_npy_ranges_per_case, axis = 1) # concatenate along axis 1 (the ranges) -> same as np.hstack(lst) or appending
        
        all_ranges.append(scaled_markov_DLC_i) # TODO could try to only store ranges with non-zero counts
        
        logger.info(f'Finished with {DLC_ID}')

    logger.info('Starting concatenation of ranges from all DLCs')
    all_ranges = np.concatenate(all_ranges, axis = 1)
            
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
    