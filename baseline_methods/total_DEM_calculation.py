from utils.IO_handler import load_table
import numpy as np
import pandas as pd 
from utils.setup_custom_logger import setup_custom_logger
from utils.SN_Curve import SN_Curve_qats
from utils.create_geo_matrix import create_geo_matrix
import os

'''
Script for calculating the Damage Equivalent Load (DEL).
To run, be sure to be on the root folder as the file paths are defined using os.getcwd() (get current work directory)

Method:

"It is sometimes useful to frame the concept of fatigue damage in terms of an equivalent
fatigue load, which is the constant-amplitude stress range that would, over the same number
of cycles, cause an equivalent amount of damage as the original variable-amplitude stress
time series."

For offshore wind turbine structures, the dominating load is expected to be the bending moment according to the design reports.
Hence we talk about Damage Equivalent Moment (DEM)

The calculation is done by extracting stored tables of "internal DEM sums" from each DLC, adding them together across all DLCs, and using the resulting sum in the overall DEM formula
    - By internal DEM sum, it is meant the sum that is inside the  "[]"-brackets of the overall DEM formula below:
        # DEM = ( [sum_{i=0}^{i=k} (n_i * dM_i^m) ] * T_lifetime / N_eq )(1/m)
            - k = number of bins used for finding moment ranges in the rainflow counting
            - dM_i: a moment range from the rainflow counting method
            - n_i: the number of times this moment range has been observed in the time series
            - T_lifetime: no. of years the equivalent moment is calculated over
            - N_eq; the number of counts / year the equivalent load is calculated over 
'''

def calculate_total_DEM_sum_cluster_i(cluster, logger):
    DLC_IDs = ['DLC12', 'DLC24a',  'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']

    sectors         = [float(i) for i in range(0,359,15)]
    data_path       = os.path.join(os.getcwd(), "data")
    mbr_geo_path    = os.path.join(data_path, f"{cluster}_member_geos.xlsx")
    member_geometry = pd.read_excel(mbr_geo_path)
    geo_matrix      = create_geo_matrix(member_geometry, sectors) # better matrix to pass to the main function

    out_path = os.path.join(os.getcwd(), "output", "all_turbines")
    DEM_sum_paths_placeholder = os.path.join(out_path, cluster, f"DB_{cluster}_" + r'{}_DEM.mat')
    out_path_xlsx = os.path.join(out_path, cluster, f"{cluster}_combined_DEM.xlsx")
    
    # Store the worst DEM results in a dict for tabular presentation later on
    logger.info(f'Calculating total DEM from {len(DLC_IDs)} DLCs')
    tot_weighted_DEM_all_angles = []
    for DLC in DLC_IDs:
        '''
        Extract all precalculated internal DEM sums from each DLC, and cumulatively concatenate them together 
        -> DEM_sum_table.shape = (n_cases, n_geo, n_angles): All internal DEM sums
        -> weighted_DEM_sum_DLC_i.shape = (n_geo, n_angles): All internal DEM sums already weighted by probability of each DEM-series to occur from each case, and multiplied by a factor to get it into weighted DEM / year
        -> weights.shape = (n_cases,): All case probabilities in hr/yr
        '''
        _, weighted_DEM_sum_DLC_i, _ = load_table(DEM_sum_paths_placeholder.format(DLC), identifier = 'DEM', method = 'python')
        
        if len(tot_weighted_DEM_all_angles) == 0:
            # Initialize matrix first time we see the size of relevant extracted table
            tot_weighted_DEM_all_angles = np.zeros_like(weighted_DEM_sum_DLC_i)
        
        tot_weighted_DEM_all_angles += weighted_DEM_sum_DLC_i
        logger.info(f'Added DEM sum from DLC {DLC}')
    
    logger.info(f'Added all the weighted DEM sums together for all DLCs')
    df_out = pd.DataFrame(tot_weighted_DEM_all_angles, 
                          index     = [f'{geo_matrix[key]["elevation"]:1f}' for key in geo_matrix.keys()], 
                          columns   = [f'{sector:.1f}' for sector in sectors[:]])
    
    df_out.to_excel(out_path_xlsx, index_label = 'mLat')
    logger.info(f'Stored the weighted DEM sums pr hr, all DLCs summed together, to {out_path_xlsx}')

    return None

def sum_up_all_DEM_sums():
    logger = setup_custom_logger('total_DEM_sum') # logger.info('Message') and logger.error('Message')
    clusters = ['JLN', 'JLO', 'JLP']
    for cluster in clusters:
        logger.info(f'Summing up DEM sums for cluster {cluster}')
        _ = calculate_total_DEM_sum_cluster_i(cluster, logger)
        
    return None

if __name__ == '__main__':
    
    _ = sum_up_all_DEM_sums()