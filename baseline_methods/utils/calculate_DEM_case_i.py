import numpy as np
from utils.read_simulation_file import read_bladed_file
import sys
import json
from utils.fastnumpyio import save as fastio_save

def calculate_DEM_case_i(binary_file_i, description_file_i, sectors, geo_matrix, rainflow_func, DEM_correction_factor, store_cycles, cycle_storage_path):
    """
    Calculates in-place Damage Equivalent (bending) Moment of a time series 
    - Reads simulation files from vendor and extracts moment time series in x and y
    - Transforms time series into resultant moment for the relevant sectors we are looking at
    - Uses rainflow counting to find the various moment ranges
    - Calculates the internal moment * count sum in order to later be weighted with the current case_i probability, and used in an overall DEM calculation 

    Args:
        binary_file_i (str): path of simulation result binary file
        description_file_i (str): path of simulation description file, containing information about the format in the binary files
        sectors (list): angles of relevant sectors, in degrees
        geo_matrix (dict): dictionary containing the various geometry details at different elevations
        rainflow_func (func): a python function for returning (ranges, counts) from a timeseries using rainflow counting
        DEM_correction_factor (float): a factor for increasing or decreasing the ranges according to details such as prolonged design lifetime due to commissioning/de-commissioning etc.
        store_cycles (bool): a decider on weather or not cycles shall be stored. Used in RFC of moment ranges in DEM
        cycle_storage_path (str): path to where ranges can be stored if used later

    Returns:
        np.array: 2D array containing internal DEM sum for each geometry (rows), for each sector/angle (columns) for the current DLC case
        
    TODO use the percentage and wohler exponent as inputs to function?
    """
    m = 5.0 # wohler exponent
    n_rainflow_bins = 128
    
    content_reshaped = read_bladed_file(binary_file_i, description_file_i) # (n,m) numpy array with n = no. of quantities of data,  m = no. of timesteps for each data quantity 
    DEM_sum = np.zeros((len(geo_matrix), len(sectors)))
    
    for geo_idx, geo_dict in geo_matrix.items():
        
        pos = (geo_dict['mx_col'] - 1, geo_dict['my_col'] - 1, geo_dict['fz_col'] - 1) # columns in DLC file to collect moments and forces, using -1 to fit Python indexing
        moments_x_timeseries = content_reshaped[[pos[0]], :] # Moments as (1, timesteps) array - hence the [[],:] type slice
        moments_y_timeseries = content_reshaped[[pos[1]], :] # Moments as (1, timesteps) array

        sectors_rad = np.deg2rad(sectors)
        # Resulting moment time series in shape (n_angles, n_timesteps)
        res_moments_timeseries_case_i = np.sin([sectors_rad]).T.dot(moments_x_timeseries) - np.cos([sectors_rad]).T.dot(moments_y_timeseries)
        
        cycles_all_sectors = np.zeros((len(sectors), n_rainflow_bins, 2)) # an array with rows representing each sector, and each cell representing one list of a [moment_range_i, count_i] pair: 
        
        for sector_idx, moment_timeseries_case_i_sector_j in enumerate(res_moments_timeseries_case_i):
            # cycles comes as (n_cycles, 2) sized matrix with col 0 = moment_ranges [Nm] and col 1 = counts [- / 10 min]. Note that "n_cycles" == k if k is given as binning factor
            cycles_sector_j = rainflow_func(moment_timeseries_case_i_sector_j, k = n_rainflow_bins)
            
            # Scale the moment ranges 1% according to reports to account for the period prior to RNA attachment during commissioning and after RNA detachment during decommissioning
            cycles_sector_j[:, [0]] *= DEM_correction_factor
            
            ''' 
            Calculate the sum of ranges and counts ("internal DEM sum") of the point at (geo_idx, sector_idx) by
            for moment_range, count in cycles_sector_j:
              res += count * (moment_range)**wohler
            For efficiency we use dot product instead of summing 128 elements each loop 
            '''
            
            moment_ranges_sector_j = cycles_sector_j[:, [0]]
            counts_sector_j = cycles_sector_j[:, [1]]
            
            DEM_sum[[geo_idx], [sector_idx]] = ((moment_ranges_sector_j.T)**m).dot(counts_sector_j)
                
            if store_cycles:
                cycles_all_sectors[sector_idx, :, :] = cycles_sector_j
                
        if store_cycles:
            path_cycles_at_member = cycle_storage_path.format(geo_dict['member_id'])
            fastio_save(path_cycles_at_member, cycles_all_sectors)
    
    return DEM_sum # (n_geo, n_angles) shaped array