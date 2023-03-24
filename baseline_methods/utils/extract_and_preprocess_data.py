import pandas as pd
from utils.read_simulation_file import read_bladed_file
import os

def extract_and_preprocess_data(DLC_file, DLC_ID, cluster_ID, sim_res_cluster_folder):
    """Creates a dataframe of the DLC case, generates paths for all the simulation files, and finds the shape of the data to be iterated through

    Args:
        DLC_file (str): file path to the Excel file defining the DLC cases
        DLC_ID (str): DLC ID e.g. 'DLC12', identifying the sheet of the DLC_file to extract data from
        cluster_ID (str): which wind park cluster is the turbine a part of -> e.g. JLO for intermediate depth on Dogger Bank
        sim_res_cluster_folder (str): path to where the simulation result time series are located depending on the current DLC

    Returns:
        pd.DataFrame, list, int, int: DataFrame with DLC information, list of the DLC cases probabilities of occuring per in hr/year, the number of cases in this DLC, the number of timesteps in the result time series 
    """
    df = pd.read_excel(DLC_file, sheet_name=DLC_ID)
    probs = list(df.Tot_Prob_in_10_percent_idling_scenario_hr_year) # Extract directly from excel
    n_cases = df.shape[0]
    
    # Assign and store the file locations for the current DLC
    # Be aware of that the creation of the "path" column in the DLC file looks as if it was made for Windows. MacOS uses different backslashes
    df = df.assign(filenames = df.apply(lambda x: x['simulation_name'].replace('XXX', cluster_ID), axis = 1))
    df = df.assign(results_files = df.apply(lambda x: os.path.join(sim_res_cluster_folder, os.path.join( *x["path"].split("\\")), x['filenames'] + '.$105'), axis = 1))
    df = df.assign(descr_files = df.apply(lambda x: os.path.join(sim_res_cluster_folder, os.path.join( *x["path"].split("\\")), x['filenames'] + '.%105'), axis = 1)) 
    
    # Sneak peek one of the files to find the number of timesteps in order to pre allocate arrays and assist some functions
    n_timesteps = read_bladed_file(df.results_files[0], df.descr_files[0]).shape[1]
    
    return df, probs, n_cases, n_timesteps