import numpy as np
from utils.read_simulation_file import read_bladed_file
import sys
import json

def calculate_DEM_case_i(binary_file_i, description_file_i, point_angles, geo_matrix, curve, rainflow_func, store_ranges, range_storage_path):
    """
    Calculates in-place Damage Equivalent (bending) Moment of a time series 
    - Reads simulation files from vendor and extracts moment time series in x and y
    - Transforms time series into resultant moment for the relevant sectors we are looking at
    - Uses rainflow counting to find the various moment ranges
    - Calculates the internal moment * count sum in order to later be weighted with the current case_i probability, and used in an overall DEM calculation 

    Args:
        binary_file_i (str): path of simulation result binary file
        description_file_i (str): path of simulation description file, containing information about the format in the binary files
        point_angles (list): angles of relevant sectors, in degrees
        geo_matrix (dict): dictionary containing the various geometry details at different elevations
        curve (SN_curve): SN_curve for the given material - NOTE unused here, but still passed as a var for this function to be passable just like calculate_DEM_case_i
        rainflow_func (func): a python function for returning (ranges, counts) from a timeseries using rainflow counting
        range_storage_path (str): path to where ranges can be stored if used later

    Returns:
        np.array: 2D array containing internal DEM sum for each geometry (rows), for each sector/angle (columns) for the current DLC case
        
    TODO use the percentage and wohler exponent as inputs to function?
    """
    DEM_scale = 1.01 # 1% increase og DEM due to time of tower without NRA during installation before operation, and after operation but before de-commissioning
    m = 5.0 # wohler exponent
    
    content_reshaped = read_bladed_file(binary_file_i, description_file_i) # (n,m) numpy array with n = no. of quantities of data,  m = no. of timesteps for each data quantity 
    DEM_sum = np.zeros( (len(geo_matrix), len(point_angles)) )
    
    all_ranges = dict()
    
    for geo_idx, geo_dict in geo_matrix.items():
        pos = (geo_dict['mx_col'] - 1, geo_dict['my_col'] - 1, geo_dict['fz_col'] - 1) # columns in DLC file to collect moments and forces, using -1 to fit Python indexing
        
        moments_x_timeseries = content_reshaped[[pos[0]], :] # Moments as (1, timesteps) array - hence the [[],:] type slice
        moments_y_timeseries = content_reshaped[[pos[1]], :] # Moments as (1, timesteps) array

        # Find angles according to possible SCF specifications
        actual_angles_rad = np.deg2rad(geo_dict['actual_angles'])
        
        # Resulting moment time series in shape (n_angles, n_timesteps)
        res_moments_timeseries_case_i = np.sin([actual_angles_rad]).T.dot(moments_x_timeseries) - np.cos([actual_angles_rad]).T.dot(moments_y_timeseries)
        
        ranges_per_ang_geo_i = dict()
        for ang_idx, timeseries_case_i_ang_j in enumerate(res_moments_timeseries_case_i):
            
            # ranges comes as (n_ranges, 2) sized matrix with col 0 = ranges and col 1 = counts. Note that "n_ranges" == k if k is given
            ranges = rainflow_func(timeseries_case_i_ang_j, k = 128)
            
            # Calculate DEM_sum[[geo_idx], [ang_idx]] = np.sum( [(moment_range * scale)**wohler * count for moment_range, count in ranges] ) - just using dot product for efficiency
            DEM_sum[[geo_idx], [ang_idx]] = ((ranges[:,[0]].T * DEM_scale)**m).dot(ranges[:,[1]]) # dem_sum per 10 min -> calculating SUM_i^k (n_i * dM_i^m) by manipulating the range matrix and using dot product for summation 
                
            if store_ranges: # NOTE only store ranges with larger than 0 counts to save space! 
                ranges_per_ang_geo_i[ang_idx] = ranges[ranges[:, 1] > 0.0].tolist() # does not need .copy() - no ops are being done, and we are not reusing these ranges. Needs tolist() to not be np.array which cannot be serialized by json
        
        if store_ranges:
            all_ranges[geo_dict['elevation']] = ranges_per_ang_geo_i
    
    if store_ranges:    
        with open(range_storage_path, 'w') as out_file:
            json.dump(all_ranges, out_file, sort_keys = True, indent = 4, ensure_ascii = False) # TODO maybe some of these items makes the files larger than they need to be
    
    return DEM_sum # (n_geo, n_angles) shaped array