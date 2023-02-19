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
'''

def check_and_retrieve_output_dirs(cluster, current_working_directory = os.getcwd()):
    
    dirs = [fr'{os.getcwd()}\output', fr'{os.getcwd()}\output\all_turbines', fr'{os.getcwd()}\output\all_turbines\{cluster}', fr'{os.getcwd()}\output\all_turbines\{cluster}\markov']
    
    for dir in dirs:
        if not os.path.exists(dir):
            print(f'Did not find dir {dir}. Creating the dir.')
            os.makedirs(dir)

    return dirs[0], dirs[-1]

def calc_unweighted_values(args, n_cases, output_table = [], multiprocess = True, calc_func = calculate_DEM_case_i,):
    
    if not multiprocess:
        assert len(output_table) > 0, 'output table must be pre-initialiazed when running single CPU code'
    
    if multiprocess:
        with Pool() as p: # loop all cases multiprocessed across available CPUs 
            outputs = p.starmap(calc_func, args) # returns a list of damages/DEM of len = n_cases 
        output_table = np.array(outputs)
        
    else:
        for case_i in range(n_cases):
            output_table[[case_i], :, :] = calc_func(*args[case_i])
    
    return output_table # (n_cases, n_geos, n_sectors)

def calculate_all_DEM_sums(clusters = ['JLN', 'JLO', 'JLP'], multiprocess = True):
    logger = setup_custom_logger('DEM')
    logger.info(f'Initiating Dogger Bank DEM sum calculations for clusters {clusters}')
    
    for cluster in clusters:
        logger.info(f'Processing cluster {cluster}')
        _ = main_calculation_of_DEM_or_damage_cluster_i(cluster = cluster, logger = logger, multiprocess = multiprocess, DEM = True)
        
    logger.info(f'Finished Dogger Bank DEM sum calculations for clusters {clusters}')
    return None

def calculate_10_min_damages(clusters = ['JLN', 'JLO', 'JLP'], multiprocess = True):
    logger = setup_custom_logger('damage')
    logger.info(f'Initiating Dogger Bank damage calculations for clusters {clusters}')
    
    for cluster in clusters:
        logger.info(f'Processing cluster {cluster}')
        _ = main_calculation_of_DEM_or_damage_cluster_i(cluster = cluster, logger = logger, multiprocess = multiprocess, DEM = False, TEN_MIN_TO_HR = 1.0)
    
    logger.info(f'Finished Dogger Bank damage calculations for clusters {clusters}')
    return None

def main_calculation_of_DEM_or_damage_cluster_i(cluster, logger, multiprocess = True, DEM = True, TEN_MIN_TO_HR = 6.0):
    
    store_cycles   = True # store rainflow cycles in DEM calculations
    info_str       = "DEM" if DEM else "damage"
    calc_func      = calculate_DEM_case_i if DEM else calculate_damage_case_i
    sectors        = [float(i) for i in range(0,359,15)] # evenly distributed angles in the turbine frame
    DLC_IDs        = ['DLC12', 'DLC24a',  'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']
    DEM_CORRECTION = 1.01
    
    # Get relevant data_paths for DLC and simulation result files  
    data_path              = fr'{os.getcwd()}\data'
    DLC_file_path          = data_path +  fr'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    simulation_result_dir  = data_path +  fr'\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_{cluster}-model_fatigue_timeseries_all_elevations'
    member_geometries_path = data_path +  fr'\{cluster}_member_geos.xlsx'
    
    geometry     = pd.read_excel(member_geometries_path)
    n_geometries = geometry.shape[0]
    geo_matrix   = create_geo_matrix(geometry, sectors) # better matrix to pass to the main function

    out_dir, cycles_dir = check_and_retrieve_output_dirs(cluster)
    
    elevations = [f'{geo_matrix[i]["elevation"]} mLAT' for i in range(len(geo_matrix))]
    status_string = f'Processing {"multiprocessed" if multiprocess else "single CPU"} {info_str} calculation\nDLCs {DLC_IDs}\n{n_geometries} elevations: {elevations}'
    logger.info(status_string)
        
    for DLC in DLC_IDs:
        # Collect relevant DLC data, find the probabilities of occurence of each case and the number of cases
        df, probs, n_cases, _ = extract_and_preprocess_data(DLC_file_path, DLC, cluster, simulation_result_dir)
        cycle_storage_path    = cycles_dir + fr'\DB_{cluster}_{DLC}' + 'cycles_member{}'
        output_file_name      = out_dir + fr'\all_turbines\{cluster}\DB_{cluster}_{DLC}_{info_str}.mat'
        summary_table_DLC_i   = np.zeros((n_cases, n_geometries, len(sectors))) # pre-allocate output matrix of the current DLC
        
        logger.info(f'Starting {info_str} calculation on {cluster} {DLC} with {n_cases} cases')
        
        arguments = [(df.results_files[i], 
                      df.descr_files[i], 
                      sectors,
                      geo_matrix,
                      get_range_and_count_qats,
                      DEM_CORRECTION,
                      store_cycles,
                      cycle_storage_path + f'_case{i}.npy'
                     ) for i in range(n_cases)]
        
        summary_table_DLC_i = calc_unweighted_values(multiprocess = multiprocess, 
                                                     calc_func    = calc_func, 
                                                     output_table = summary_table_DLC_i, 
                                                     args         = arguments, 
                                                     n_cases      = n_cases)
        
        logger.info(f'Finished calculating {info_str} for {cluster} - initiating probability weighting and file storage')
        
        # Transform output to a combined damage / DEM matrix of size (n_geo, n_sectors), weighting cases by their probabilities,
        weighted_table_DLC_i = np.zeros((n_geometries, len(sectors)))
        weights = np.array([probs])
        for sector_idx in range(len(sectors)):
            # TODO note that the damage should potentially not be multiplied with the conversion factor to hours?!
            # convert to hour-based values according to "TEN_MIN_TO_HR"
            weighted_table_DLC_i[:, [sector_idx]] = np.dot(weights, summary_table_DLC_i[:,:, sector_idx]).T * TEN_MIN_TO_HR  # (n_geometries, 1) -> multiplication of weights by dot product
        
        store_table(summary_table_DLC_i, 
                    weighted_table_DLC_i, 
                    weights, 
                    output_file_name, 
                    identifier = info_str)
        
        logger.info(f'Stored {info_str} table for {cluster} {DLC} \n')
        
    logger.info(f'Main calculation script finished for cluster {cluster}')
    return None

if __name__ == '__main__':
    
    _ = calculate_all_DEM_sums(clusters = ['JLO'], multiprocess = True)