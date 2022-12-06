import numpy as np
import pandas as pd
from utils.read_simulation_file import read_bladed_file
import matplotlib.pyplot as plt 
from multiprocessing import Pool

def get_forces_and_moments_time_series(df, geo_row, point_angles, n_timesteps, MP = False):
    '''
    Extracts time series of forces and moments over the varius points on the structure, and returns the forces and resultant moment
    
    Processes the config file over conditions over all DLCs, and uses the simulation result time series for a variety of geometrical locations
    Extract the moments from the correct time series and calculate + store the resultant for all points in all DLC cases 
    
    Returns forces and moments as 3D tensors with dims (case, theta, timestep)
    
    TODO 1 note:    Currently the program runs over e.g. 3090 cases for 24 angles per case, and creates a new list -> array each time
                    List comprehension and single trigonometry calc per angle seems inefficient -> can we use the power of numpy?
                    If instead we first extract the Mx and My values, and before the function returns we do matrix operations with numpy with sin/cos(angles)
                    So, dont allocate a matrix with space for all theta values, but instead create a new larger numpy array with matrix operations afterwards
    '''
    print(f'Getting forces and moment timeseries, multiprocess = {MP}')
    
    # Create dataframe over all information in the current DLC specification, 
    # and add columns corresponding to where the relevant simulation and timeseries files etc. are located
    n_cases  = df.shape[0]
    n_angles = len(point_angles)
    thetas   = np.deg2rad(point_angles) # note that this was originally 'list(np.deg2rad(np.array(point_angles)))'
    pos      = (geo_row['mx_col'] - 1, geo_row['my_col'] - 1, geo_row['fz_col'] - 1)

    moments_all_cases = np.zeros((n_cases, n_angles, n_timesteps))
    forces_all_cases  = np.zeros((n_cases, n_angles, n_timesteps))
    
    # For all time series, go through the pairs of binary files and description files, extract the time series of moments, forces etc., and extract only the quantities we want  
    if MP:
        pool_args = [(df.results_files[i], df.descr_files[i], pos, thetas) for i in range(n_cases)]   
        # This corresponds to a for-loop over all cases only done by 8 cores at the same time
        with Pool() as p:
            results = p.starmap(get_forces_and_moments_time_series_case_i, pool_args) 
    
        for case_i, res in enumerate(results):
            forces_all_cases[case_i, :, :] = res[0]
            moments_all_cases[case_i, :, :] = res[1]

    else:
        for case_i, (binary_file, text_file) in enumerate(zip(df.results_files, df.descr_files)):
            forces, resultant_moments = get_forces_and_moments_time_series_case_i(binary_file, text_file, pos, thetas)
            # Append to the overall matrices - Note that the axial force is the same for all angles
            moments_all_cases[case_i, :, :]  = resultant_moments
            forces_all_cases[case_i, :, :]   = forces
    
    return forces_all_cases, moments_all_cases

def get_forces_and_moments_time_series_case_i(binary_file_i, description_file_i, pos, thetas):  
    
    content_reshaped = read_bladed_file(binary_file_i, description_file_i) # (n,m) numpy array with n = no. of quantities of data,  m = no. of timesteps for each data quantity 
        
    # Calculate resultant moment for all points on circumference and store in global 3D tensor for moments per 
    moments_x_timeseries = content_reshaped[pos[0],:] # Moments as (timesteps, ) array
    moments_y_timeseries = content_reshaped[pos[1],:] # Moments as (timesteps, ) array
    forces_z_case_i      = content_reshaped[[pos[2]],:] # Axial forces as (1, timesteps) array - hence the [] slice

    # Calculate resultant moment in all thetas for the current case -> (theta, timestep)-shaped array    
    moments_case_i = np.array([np.sin(theta) * moments_x_timeseries + np.cos(theta) * moments_y_timeseries for theta in thetas]) # TODO 1 I believe this could be optimized - see comment in documentation
    
    # Return arrays to add to the overall matrices - Note that the axial force is the same for all angles so the values are just repeated to create a same-sized tensor as the moment tensor
    return np.repeat(forces_z_case_i, len(thetas), axis=0), moments_case_i