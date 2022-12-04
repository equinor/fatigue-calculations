import pandas as pd
from utils.read_simulation_file import read_bladed_file
import os

def extract_and_preprocess_data(DLC_file, DLC_ID, cluster_ID, sim_res_cluster_folder):
    '''
    Creates a dataframe of the DLC case, generates paths for all the simulation files, and finds the shape of the data to be iterated through
    '''
    # TODO instert into "read_and_extract_DLC_dataframe()"
    df = pd.read_excel(DLC_file, sheet_name=DLC_ID)
    probs = list(df.Tot_Prob_in_10_percent_idling_scenario_hr_year) # Extract directly from excel
    n_cases = df.shape[0]
    
    # Assign and store the file locations for the current DLC
    df = df.assign(filenames = df.apply(lambda x: x['simulation_name'].replace('XXX', cluster_ID), axis = 1))
    df = df.assign(results_files = df.apply(lambda x: os.path.join(sim_res_cluster_folder +  x['path'], x['filenames']) + '.$105', axis = 1))
    df = df.assign(descr_files = df.apply(lambda x: os.path.join(sim_res_cluster_folder +  x['path'], x['filenames']) + '.%105', axis = 1)) 
    
    # Sneak peek one of the files to find the number of timesteps in order to pre allocate arrays and assist some functions
    n_timesteps = read_bladed_file(df.results_files[0], df.descr_files[0]).shape[1]
    
    return df, probs, n_cases, n_timesteps