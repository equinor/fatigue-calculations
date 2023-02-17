from utils.extract_and_preprocess_data import extract_and_preprocess_data
from utils.setup_custom_logger import setup_custom_logger
from utils.IO_handler import store_table
from utils.create_geo_matrix import create_geo_matrix
from utils.rainflow_methods import get_range_and_count_qats
from utils.calculate_damage_case_i import calculate_damage_case_i
from utils.calculate_DEM_case_i import calculate_DEM_case_i
import numpy as np
import pandas as pd
from multiprocessing import Pool
import os
import argparse
import sys

'''
Implementation of in-place damage of the Dogger Bank wind turbines

- Use the 10 minute timeseries from vendor simulations to extract forces and moments
- Calculate the resulting axial force and bending moments on the relevant sectors of the intersection at the desired elevation on the structure -> we call these a geometry
- Translate the forces and moments into stress timeseries
- Use rainflow counting to extract the stress cycles that are present in the stress time series
- Use the stress cycles together with an SN curve and calculate the linear accumulated damage with the Palmgren-Miner rule to get total damage 
- This damage can be stored as a binary file and used for lifetime calculations etc. 

Code improvement TODO
- Create a wrapper for argparse to clean the command line input-handling
'''

def calculate_hourly_results_from_member_timeseries(damage_or_DEM = 'DEM'):
    
    
    
    return None

def calculate_DEM():
    _ = calculate_hourly_results_from_member_timeseries('DEM')
    return None

if __name__ == '__main__':
        
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--DEM", type=str, help="DEM or damage")
    args = parser.parse_args()
    
    # Get relevant data_paths for DLC and simulation result files  
    cluster = 'JLO'
    data_path              = fr'{os.getcwd()}\data'
    DLC_file               = data_path +  fr'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    sim_res_cluster_folder = data_path +  fr'\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_{cluster}-model_fatigue_timeseries_all_elevations'
    geometry_file_members  = data_path +  fr'\{cluster}_member_geos.xlsx'
    
    ###
    ### -!-!-!-!- NOTE CONFIG VARIABLES START
    ###
    if args.DEM is not None: # we have some input from the command line
        DEM = (args.DEM.lower() == 'dem')
    else: # we choose manually
        DEM = True # True = DEM, False = damage
        
    MULTIPROCESS = True # False if using only single processor, which should be done if debugging, plotting etc.
    DLC_IDs      = ['DLC12', 'DLC24a',  'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']
    geometry     = pd.read_excel(geometry_file_members)#.drop([0,1], axis=0) # TODO .drop() can be used for testing only a set of geometries
    sectors      = [float(i) for i in range(0,359,15)] # evenly distributed angles in the turbine frame
    store_cycles = True # store rainflow cycles
    ###
    ### -!-!-!-!- NOTE CONFIG VARIABLES END
    ###
    
    DEM_correction_factor = 1.01
    n_geometries  = geometry.shape[0]
    cluster    = 'JLO'
    out_file_type = 'mat' # or npy 
    logger        = setup_custom_logger('Main') # logger.info('Message') and logger.error('Message')
    rainflow_func = get_range_and_count_qats
    geo_matrix    = create_geo_matrix(geometry, sectors) # better matrix to pass to the main function
    info_str      = "DEM" if DEM else "damage"
    calc_func     = calculate_DEM_case_i if DEM else calculate_damage_case_i
    TEN_MIN_TO_HR = 6.0 # to go from damage or DEM "per 10 min" to "per hr" 

    elevations = [f'{geo_matrix[i]["elevation"]} mLAT' for i in range(len(geo_matrix))]
    logger.info(f'Initiating {info_str} calculation for the {cluster} cluster,\n\
                DLCs {DLC_IDs}\n\
                Multiprocessed = {MULTIPROCESS}, {len(sectors)} sectors, \n\
                {n_geometries} elevations: {elevations} \n')
    
    out_dir = fr'{os.getcwd()}\output'
    cycles_out_dir = out_dir + fr'\markov\{cluster}'
    if not os.path.exists(cycles_out_dir):
        os.makedirs(cycles_out_dir)
    
    for DLC in DLC_IDs:
        # Collect relevant DLC data, find the probabilities of occurence of each case and the number of cases
        df, probs, n_cases, _ = extract_and_preprocess_data(DLC_file, DLC, cluster, sim_res_cluster_folder)
        output_file_name      = out_dir + fr'\{info_str}_DB_{cluster}_{DLC}.{out_file_type}'
        cycle_storage_path    = cycles_out_dir + fr'\DB_{cluster}_{DLC}' + '_member{}'
        
        summary_table_DLC_i   = np.zeros((n_cases, n_geometries, len(sectors))) # pre-allocate output matrix of the current DLC
        
        # Prepare the calculation function arguments which can be passed to any function, either multiprocessed or not
        arguments = [(df.results_files[i], 
                      df.descr_files[i], 
                      sectors, 
                      geo_matrix, 
                      rainflow_func,
                      DEM_correction_factor,
                      store_cycles,
                      cycle_storage_path + f'_case{i}.npy'
                     ) for i in range(n_cases)]
        
        logger.info(f'Starting {info_str} calculation on {DLC} with {n_cases} cases')
        
        if MULTIPROCESS:
            with Pool() as p: # loop all cases multiprocessed across available CPUs 
                outputs = p.starmap(calc_func, arguments) # returns a list of damages/DEM of len = n_cases 
            summary_table_DLC_i = np.array(outputs)
            
        else:
            for case_i in range(n_cases):
                summary_table_DLC_i[[case_i], :, :] = calc_func(*arguments[case_i])
                
        logger.info(f'Finished calculating {info_str} - initiating probability weighting and file storage')
        
        # Transform the summary table into a combined damage / DEM matrix of size (n_geometries, n_angles), 
        # weighting each of the cases by their probabilities, and converting to hour-based damage according to "TEN_MIN_TO_HR"
        weighted_table_DLC_i = np.zeros((n_geometries, len(sectors)))
        weights = np.array([probs])
        for sector_idx in range(len(sectors)):
            weighted_table_DLC_i[:, [sector_idx]] = np.dot(weights, summary_table_DLC_i[:,:, sector_idx]).T * TEN_MIN_TO_HR  # (n_geometries, 1) -> multiplication of weights by dot product
        
        # Now save the results for later usage     
        store_table(summary_table_DLC_i, weighted_table_DLC_i, weights, output_file_name, identifier = info_str) # Stores as .mat or .npy binary file
        logger.info(f'Stored {info_str} table for {DLC} \n')
        
    logger.info(f'Main calculation script finished')