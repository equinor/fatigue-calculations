from utils.SN_Curve import SN_Curve_qats
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
- Create a wrapper for argparse to clean the command line input
'''

if __name__ == '__main__':
        
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--DEM", type=str, help="DEM or damage")
    args = parser.parse_args()
    
    # Get relevant data_paths for DLC and simulation result files  
    data_path              = fr'{os.getcwd()}\data'
    DLC_file               = data_path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    sim_res_cluster_folder = data_path +  r'\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations'
    geometry_file          = data_path +  r'\DA_P53_CD.xlsx'
    
    ###
    ### -!-!-!-!- NOTE CONFIG VARIABLES
    ###
    if args.DEM is not None: # we have some input from the command line
        DEM = (args.DEM.lower() == 'dem')
    else: # we choose manually
        DEM = True # True = DEM, False = damage
        
    MULTIPROCESS = True # False if using only single processor, which should be done if debugging, plotting etc.
    DLC_IDs      = ['DLC12', 'DLC24a',  'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']
    geometry     = pd.read_excel(geometry_file)#.drop([0,1], axis=0) # TODO .drop() can be used for testing only a set of geometries
    point_angles = [float(i) for i in range(0,359,15)] # evenly distributed angles in the turbine frame. All iterations are done with these, but each geometry might have sectors / angles that deviate some
    store_ranges = True
    ###
    ### -!-!-!-!- NOTE CONFIG VARIABLES
    ###
    
    # TODO transform between "global turbine frame" and the compass frame, as the SCF angles are given in the latter
    n_geometries       = geometry.shape[0]
    cluster_ID         = 'JLO'
    out_file_type      = 'mat' # or npy 
    logger             = setup_custom_logger('Main') # logger.info('Message') and logger.error('Message')
    rainflow_func      = get_range_and_count_qats
    curve              = SN_Curve_qats('D')
    geo_matrix         = create_geo_matrix(geometry, point_angles, curve) # better matrix to pass to the main function
           
    info_str  = "DEM" if DEM else "damage"
    calc_func = calculate_DEM_case_i if DEM else calculate_damage_case_i
    factor    = 6.0

    logger.info(f'Initiating {info_str} calculation for the {cluster_ID} cluster, DLCs {DLC_IDs}')
    elevations = [str(geo_matrix[i]['elevation']) + ' mLAT' for i in range(len(geo_matrix))]
    logger.info(f'Settings: multiprocessed = {MULTIPROCESS}, {len(point_angles)} angles, {n_geometries} geometries: {elevations} \n')
    
    for DLC_ID in DLC_IDs:
        # Collect relevant DLC data, find the probabilities of occurence of each case and the number of cases
        df, probs, n_cases, _ = extract_and_preprocess_data(DLC_file, DLC_ID, cluster_ID, sim_res_cluster_folder)
        output_file_name      = fr'{os.getcwd()}\output' + fr'\{info_str}_DB_{cluster_ID}_{DLC_ID}.{out_file_type}'
        summary_table_DLC_i   = np.zeros((n_cases, n_geometries, len(point_angles))) # pre-allocate output matrix of the current DLC
        range_storage_path    = fr'{os.getcwd()}\output\markov' + fr'\DB_{cluster_ID}_{DLC_ID}'
        
        # Prepare the calculation function arguments which can be passed to any function, either multiprocessed or not
        arguments = [(df.results_files[i], 
                      df.descr_files[i], 
                      point_angles, 
                      geo_matrix, 
                      curve,
                      rainflow_func,
                      store_ranges,
                      range_storage_path + f'_case{i}.json' 
                     ) for i in range(n_cases)]
        
        logger.info(f'Starting {info_str} calculation on {DLC_ID} with {n_cases} cases')
        
        if MULTIPROCESS:
            with Pool() as p: 
                # loop all cases multiprocessed across available CPUs
                outputs = p.starmap(calc_func, arguments) # returns a list of damages/DEM of len = n_cases 
            
            summary_table_DLC_i = np.array(outputs)
        else:
            for case_i in range(n_cases):
                summary_table_DLC_i[[case_i], :, :] = calc_func(*arguments[case_i])
        
        logger.info(f'Finished calculating {info_str}')
        
        # Transform the summary table into a combined damage / DEM matrix of size (n_geometries, n_angles), 
        # weighting each of the cases by their probabilities, and converting to hour-based damage according to "factor"
        logger.info(f'Initiating aggregating calculation and file storage')
        
        weighted_table_DLC_i = np.zeros((n_geometries, len(point_angles)))
        weights = np.array([probs])
        for ang_idx in range(len(point_angles)):
            weighted_table_DLC_i[:, [ang_idx]] = np.dot(weights, summary_table_DLC_i[:,:, ang_idx]).T * factor # (n_geometries, 1) -> multiplication of weights by dot product
        
        # Now save the results for later usage     
        store_table(summary_table_DLC_i, weighted_table_DLC_i, weights, output_file_name, identifier = info_str) # Stores as .mat or .npy binary file
        logger.info(f'Stored {info_str} table for {DLC_ID} \n')
        
    logger.info(f'Main calculation script finished')