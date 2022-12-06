from utils.DNV_SN_Curve import DNV_SN_Curve
from utils.extract_and_preprocess_data import extract_and_preprocess_data
from utils.get_forces_and_moments_time_series import get_forces_and_moments_time_series
from utils.get_scf_sector_list import get_scf_sector_list
from utils.calculate_stress_timeseries import calculate_stress_timeseries
from utils.calculate_damage import calculate_damage
from utils.save_damage_table import save_damage_table
import numpy as np
import time
import pandas as pd

MULTIPROCESS_CASES = False # False if using only single processor, which should be done if plotting etc.
RAINFLOW_PACKAGE = True # False if using fatpack rainflow counting (which we think only uses whole cycles)

'''
The main script for calculating damage of x geometries for y points/sectors for all DLCs we have. The script was written partly by translating a matlab script, while understanding the actual problem of caclulating fatigue using rainflow counting, SN curves and miner summation.

Optimizations include changing the order of loops so that the cases are looped through first instead of the geometries -> more to gain speed-wise by multiprocessing
This should be prioritized after MATLAB-script comparison is done, but before running ALL the DLC cases

The goal of this implementation was to have a way of implementing the direct damage calculation via rainflowcounting and palm-miner summation and compare with MATLAB and DEM + Markov matrices.
The chosen tool was fatpack, and the results was compared to the result of the matlab script
Therefore it was not prioritized to add the weighting of probabilities in the end, since the calculations must be calibrated first
'''

if __name__ == '__main__':
    
    DLC_IDs = ['DLC12'] #, 'DLC64a', 'DLC64b', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b']
    
    # Get relevant data_paths for DLC and simulation result files
    data_path              = r'C:\Appl\TDI\getting_started\fatpack_test\data'
    DLC_file               = data_path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    sim_res_cluster_folder = data_path +  r'\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations'
    geometry_file          = data_path +  r'\DA_P53_CD.xlsx'
    
    geometry      = pd.read_excel(geometry_file) # .drop([1,2]) # TODO drop can be used for testing only a set of geometries
    n_geometries  = geometry.shape[0]
    point_angles  = [float(i) for i in range(0,359,15)]
    cluster_ID    = 'JLO'
    curve         = DNV_SN_Curve('D') # DNV SN curve in air, D
    out_file_type = 'mat' # or npy 
    start_time    = time.time()
    
    print(f'Calculating damage for {len(DLC_IDs)} DLCs using geometry {n_geometries} geometries and {len(point_angles)} sectors')
    
    for DLC_ID in DLC_IDs:
        
        df, probs, n_cases, n_timesteps = extract_and_preprocess_data(DLC_file, DLC_ID, cluster_ID, sim_res_cluster_folder)
        damage_table_DLC_i = np.zeros((n_cases, n_geometries, len(point_angles))) # pre-allocate output matrix of the current DLC
        combined_damage_DLC_i = np.zeros((n_geometries, len(point_angles)))
        
        appendix = '_multiprocessed' if MULTIPROCESS_CASES else '_regular'
        output_file_name = r'C:\Appl\TDI\getting_started\fatpack_test\output' + fr'\fatigue_DB_{cluster_ID}_{DLC_ID}_fatpack{appendix}.{out_file_type}'

        for geo_idx in range(geometry.shape[0]): # TODO this way of iterating geometry is not sexy, but it contains one row with headers etc nicely and is only iterated through three times
           
            print(f'Calculating damage for {DLC_ID} using geometry {int(geo_idx + 1)} of {geometry.shape[0]} with SN curve {curve.title}')
            geo_row = geometry.iloc[geo_idx]

            # For each geometry, points of extra interest wrt stress factors must be identified and the corresponding angles updated
            actual_point_angles, scf_per_point = get_scf_sector_list(geo_row, point_angles)
            print(f'T + {time.time() - start_time:.1f} s: Recalculated angles and SCF')
                            
            # Extract the time series of moments/forces for all points with its probability of occurence and calculate the occuring stress  
            forces_timeseries_batch, moments_timeseries_batch = get_forces_and_moments_time_series(df, geo_row, actual_point_angles, n_timesteps, MP = MULTIPROCESS_CASES)
            print(f'T + {time.time() - start_time:.1f} s: Got forces and moments')
                        
            # Calculate the stress timeseries as a combination of the forces, bending moments, and stress concentration factors and 
            stress_timeseries_batch = calculate_stress_timeseries(forces_timeseries_batch, moments_timeseries_batch, geo_row, actual_point_angles, scf_per_point, curve) 
            print(f'T + {time.time() - start_time:.1f} s: Calculated stress')
            
            # Find the rainflow ranges and calculate batched 10-min damage for each DLC case for all points/angles the stress timeseries      
            damage_geometry_i = calculate_damage(stress_timeseries_batch, curve, MP = MULTIPROCESS_CASES, rainflow_pck = RAINFLOW_PACKAGE)
            print(f'T + {time.time() - start_time:.1f} s: Calculated damage')    
            
            # Append the calculated damage to the overall damage table for the current DLC 
            damage_table_DLC_i[:, geo_idx, :] = damage_geometry_i
        
        # Transform the damage table into a combined_damage matrix of size (n_geometries, n_angles), weighting each of the cases by their probabilities and converting to hour-based damage    
        weights = np.array([probs])
        for ang_idx in range(len(point_angles)):
            combined_damage_DLC_i[:, [ang_idx]] = np.dot( weights, damage_table_DLC_i[:,:, ang_idx]).T * 6.0 # (n_geometries, 1) -> multiplication of weights by dot product
                
        # save damage table to a npy or mat binary file
        save_damage_table(damage_table_DLC_i, combined_damage_DLC_i, weights, output_file_name)
        print(f'T + {time.time() - start_time:.1f} s: Damage table save script finished for {DLC_ID}')
        print(f'Damage table first case, first geometry, first angle: {damage_table_DLC_i[0,0,0]}')
        
    print(f'T + {time.time() - start_time:.1f} s: Script finished for {len(DLC_IDs)} DLCs and {geometry.shape[0]} geometries')