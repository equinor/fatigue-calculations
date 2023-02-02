import numpy as np
from utils.read_simulation_file import read_bladed_file
import sys
import json
from utils.fastnumpyio import save as fastio_save

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
    DEM_scale = 1.01 # 1% increase of DEM due to time of tower without NRA during installation before operation, and after operation but before de-commissioning
    m = 5.0 # wohler exponent
    n_rainflow_bins = 128
    
    content_reshaped = read_bladed_file(binary_file_i, description_file_i) # (n,m) numpy array with n = no. of quantities of data,  m = no. of timesteps for each data quantity 
    DEM_sum = np.zeros((len(geo_matrix), len(point_angles)))
    
    for geo_idx, geo_dict in geo_matrix.items():
        pos = (geo_dict['mx_col'] - 1, geo_dict['my_col'] - 1, geo_dict['fz_col'] - 1) # columns in DLC file to collect moments and forces, using -1 to fit Python indexing
        
        moments_x_timeseries = content_reshaped[[pos[0]], :] # Moments as (1, timesteps) array - hence the [[],:] type slice
        moments_y_timeseries = content_reshaped[[pos[1]], :] # Moments as (1, timesteps) array

        # Find angles according to possible SCF specifications. If 'omni', angles will be as originally and SCF = 1 for all angles
        actual_angles_rad = np.deg2rad(geo_dict['actual_angles']) # TODO this works for nodes / members, but not any non-omni angle since the actual angles are given in compass angles
        
        # Resulting moment time series in shape (n_angles, n_timesteps)
        res_moments_timeseries_case_i = np.sin([actual_angles_rad]).T.dot(moments_x_timeseries) - np.cos([actual_angles_rad]).T.dot(moments_y_timeseries)
        
        ranges_and_counts_all_sectors = np.zeros((len(point_angles), n_rainflow_bins, 2)) # an array with rows representing each sector, and each cell representing one list of a [moment_range_i, count_i] pair: 
        
        for sector_idx, moment_timeseries_case_i_sector_j in enumerate(res_moments_timeseries_case_i):
            # ranges comes as (n_ranges, 2) sized matrix with col 0 = moment_ranges [Nm] and col 1 = counts [- / 10 min]. Note that "n_ranges" == k if k is given
            ranges_and_counts_sector_j = rainflow_func(moment_timeseries_case_i_sector_j, k = n_rainflow_bins)
            
            # Scale the moment ranges 1% according to reports to account for the period prior to RNA attachment during commissioning and after RNA detachment during decommissioning
            ranges_and_counts_sector_j[:, [0]] *= DEM_scale
            
            # Calculate the sum of ranges and counts ("internal DEM sum") of the point at (geo_idx, sector_idx) by
            # for moment_range, count in ranges_and_counts_sector_j:
            #   res += count * (moment_range)**wohler
            # For efficiency we use dot product instead of summing 128 elements each loop 
            
            m_ranges_sector_j = ranges_and_counts_sector_j[:, [0]]
            counts_sector_j = ranges_and_counts_sector_j[:, [1]]
            
            DEM_sum[[geo_idx], [sector_idx]] = ((m_ranges_sector_j.T)**m).dot(counts_sector_j)
                
            if store_ranges:
                # NOTE it makes sense to not store zero count-ranges, but this made it hard to create a standard sized numpy array. This can be fixed by another script later
                ranges_and_counts_all_sectors[sector_idx, :, :] = ranges_and_counts_sector_j
                
        if store_ranges:
            fastio_save(range_storage_path.format(geo_dict['member_JLO']), ranges_and_counts_all_sectors)
    
    return DEM_sum # (n_geo, n_angles) shaped array