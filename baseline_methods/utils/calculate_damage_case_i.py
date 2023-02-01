import numpy as np
from utils.read_simulation_file import read_bladed_file
import sys

def calculate_damage_case_i(binary_file_i, description_file_i, point_angles, geo_matrix, curve, rainflow_func, store_ranges, range_storage_path):
    """
    Calculates in-place damage of a turbine geometry for a single DLC case
    - Reads simulation files from vendor and extracts moments, forces time series
    - Transforms time series into stress and scales it according to SCF and alpha
    - Uses rainflow counting to find the various stress ranges over the given time period
    - Calculates damage by assuming linear damage accumulation via the Palmgren-Miner summation, using DNVGL SN-curves 

    Args:
        binary_file_i (str): path of simulation result binary file
        description_file_i (str): path of simulation description file, containing information about the format in the binary files
        point_angles (list): angles of relevant sectors, in degrees
        geo_matrix (dict): dictionary containing the various geometry details at different elevations
        curve (SN_curve): SN_curve for the given material, used here to calculate the miner sum of the found stress ranges
        rainflow_func (func): a python function for returning (ranges, counts) from a timeseries using rainflow counting
        store_ranges (bool): a decider on weather or not ranges shall be stored. Used in RFC of moment ranges in DEM
        range_storage_path (str): path to where ranges can be stored if used later. Used in RFC of moment ranges in DEM

    Returns:
        np.array: 2D array containing damage for each geometry (rows), for each sector/angle (columns) for the current DLC case
    """

    content_reshaped = read_bladed_file(binary_file_i, description_file_i) # (n,m) numpy array with n = no. of quantities of data,  m = no. of timesteps for each data quantity 
    damage = np.zeros( (len(geo_matrix), len(point_angles)) )
    
    for geo_idx, geo_dict in geo_matrix.items():
        pos = (geo_dict['mx_col'] - 1, geo_dict['my_col'] - 1, geo_dict['fz_col'] - 1) # columns in DLC file to collect moments and forces, using -1 to fit Python indexing
        
        moments_x_timeseries = content_reshaped[[pos[0]], :] # Moments as (1, timesteps) array - hence the [[],:] type slice
        moments_y_timeseries = content_reshaped[[pos[1]], :] # Moments as (1, timesteps) array
        forces_z_case_i      = content_reshaped[[pos[2]], :] # Axial F as (1, timesteps) array 
        
        # Resultant moment for the current case will be a (theta, timestep)-shaped array    
        actual_angles_rad = np.deg2rad(geo_dict['actual_angles'])
        
        res_moments_timeseries_case_i = np.sin([actual_angles_rad]).T.dot(moments_x_timeseries) - np.cos([actual_angles_rad]).T.dot(moments_y_timeseries)
        res_force_timeseries_case_i = np.repeat(forces_z_case_i, len(actual_angles_rad), axis = 0)
                
        # size (n_thetas, n_timesteps)
        stress_timeseries_case_i = res_force_timeseries_case_i / geo_dict['A'] + res_moments_timeseries_case_i / geo_dict['Z'] # [Pa] Quick check: N / m**2 + Nm / m**3 = N / m**2 = Pa
        
        # Adjust the stress according the stress concentration factors for certain angles
        stress_timeseries_case_i *= np.array(geo_dict['scf_per_point'])[:, None] # Elementwise multiplication row wise 
        stress_timeseries_case_i *= geo_dict['alpha'] * 1e-6 # [MPa]
        
        # def calculate_damage_case_i(stress_timeseries_case_i, curve, rainflow_func):
        for ang_idx, stress_timeseries_case_i_ang_j in enumerate(stress_timeseries_case_i):
            
            # stress_ranges comes as (N_stress_ranges, n_counts) sized matrix
            stress_ranges = rainflow_func(stress_timeseries_case_i_ang_j, k = 128)   
            damage[geo_idx, ang_idx] = curve.miner_sum(stress_ranges)
            
    return damage # (n_geo, n_angles) shaped array