import json 
from utils.extract_and_preprocess_data import extract_and_preprocess_data
import os
from utils.setup_custom_logger import setup_custom_logger
import pandas as pd 
import numpy as np
import sys
from multiprocessing import Pool


def find_markov_file_paths(range_storage_path, identifier):
    return [(range_storage_path + '\\' + file_name) for file_name in os.listdir(range_storage_path) if (identifier in file_name)]

def open_range_json_and_scale_counts(file, weight):
    
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

def parse_markov_files(range_storage_path, DLC_IDs = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b'], cluster_ID = 'JLO'):
    
    data_path = fr'{os.getcwd()}\data'
    DLC_file  = data_path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    
    df_out = pd.DataFrame()
    
    for DLC_ID in DLC_IDs:
        
        DLC_info_df = pd.read_excel(DLC_file, sheet_name=DLC_ID)
        probs = list(DLC_info_df.Tot_Prob_in_10_percent_idling_scenario_hr_year) # Extract directly from excel
        n_cases = DLC_info_df.shape[0] # TODO not necessary?
        
        # Note this is one entire loop over all files, just to loop over files again afterwards during calculations
        # but it is readable and can be changed later to do operations during file loading
        file_paths_DLC_i = find_markov_file_paths(range_storage_path, identifier = fr'DB_{cluster_ID}_{DLC_ID}') 
        n_cases = len(file_paths_DLC_i)
        
        multiprocess_args = [(file_paths_DLC_i[i],
                              probs[i]
                             ) for i in range(n_cases)]
        
        logger.info(f'Starting markov concatenation on {DLC_ID} with {n_cases} cases')
        
        # each case will have <= k ranges and counts. these can be stored in dataframes, per geometry and sector
        # loop through the cases, scale the counts according to case probability (into hr-basis), and concatenate the scaled ranges for each case into one DF for the current DLC 
        with Pool() as p: 
            list_of_dfs = p.starmap(open_range_json_and_scale_counts, multiprocess_args) # returns a list, len n_cases, of DataFrames with [ranges, counts]         
        
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

if __name__ == '__main__':
    
    range_storage_path = fr'{os.getcwd()}\output\markov'
    # range_storage_path = fr'{os.getcwd()}\output\markov\test' # dir with 50 cases for testing
    output_path = fr'{os.getcwd()}\output' + fr'\total_markov.json'
    
    logger = setup_custom_logger('Main') # logger.info('Message') and logger.error('Message')
    logger.info('Starting markov parsing')
    DLC_IDs = ['DLC12', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']
    ranges_per_elevation_and_ang = parse_markov_files(range_storage_path = range_storage_path, 
                                                      DLC_IDs = DLC_IDs) # dict with {geo: {ang : np.array()}}
    
    logger.info('Finished parsing markov files - storing overall file')
    with open(output_path, 'w') as out_file:
            json.dump(ranges_per_elevation_and_ang.to_dict(), out_file, sort_keys = True, indent = 4, ensure_ascii = False)
            
    logger.info('Stored total markov matrix')
    