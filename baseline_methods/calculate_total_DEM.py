from utils.IO_handler import load_table
import numpy as np
import pandas as pd 
from utils.setup_custom_logger import setup_custom_logger
from utils.SN_Curve import SN_Curve_qats
from utils.create_geo_matrix import create_geo_matrix
from utils.SN_Curve import SN_Curve_qats
from utils.transformations import global_2_compass
import os
import sys # for testing / debugging

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
   
if __name__ == '__main__':
    
    ###
    ### Initialize variables and collect data files
    ###
    DLC_IDs = ['DLC12', 'DLC24a',  'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']
    
    logger = setup_custom_logger('Main') # logger.info('Message') and logger.error('Message')
    logger.info(f'Calculating total DEM from {len(DLC_IDs)} DLCs')

    point_angles  = [float(i) for i in range(0,359,15)]
    compass_angles = global_2_compass(point_angles)
    DFF           = 3.0
    T_lifetime    = 25.0
    N_equivalent  = 10.0**7
    wohler_exp    = 5.0
    curve         = SN_Curve_qats('D')
    data_path     = fr'{os.getcwd()}\data'
    geometry_file = data_path +  r'\DA_P53_CD.xlsx'
    geometry      = pd.read_excel(geometry_file) # .drop(geo_2_drop, axis=0) # TODO drop can be used for testing only a set of geometries
    geo_matrix    = create_geo_matrix(geometry, point_angles, curve) # better matrix to pass to the main function

    ###
    ### Compute DEM and damage
    ###
        
    # Compare python and matlab implementations. Python and matlab uses two different conventions on file storage naming 
    methods = ['matlab', 'python'] 
    paths = {'python': (fr'{os.getcwd()}' + r'\output\DEM_DB_JLO_{}.mat'), 
             'matlab': (fr'{os.getcwd()}' + r'\output\fatigue_DB_JLO_{}.mat')} # formatted so that the str DLC_ID can be used in path
    
    out_path_xlsx = fr'{os.getcwd()}' + r'\output\python_combined_DEM.xlsx'
    
    # Store the worst DEM results in a dict for tabular presentation later on
    res_data = {m: [] for m in methods}
    df_row_labels = []
    for method_idx, method in enumerate(methods):  
        tot_weighted_DEM_all_angles = []
        
        for DLC_ID in DLC_IDs:
            '''
            Extract all precalculated internal DEM sums from each DLC, and cumulatively concatenate them together 
            -> DEM_sum_table.shape = (n_cases, n_geo, n_angles): All internal DEM sums
            -> weighted_DEM_sum_DLC_i.shape = (n_geo, n_angles): All internal DEM sums already weighted by probability of each DEM-series to occur from each case, and multiplied by a factor to get it into weighted DEM / year
            -> weights.shape = (n_cases,): All case probabilities in hr/yr
            '''
            path = paths[method].format(DLC_ID)
            DEM_sum_table, weighted_DEM_sum_DLC_i, weights = load_table(path, identifier = 'DEM', method = method)
            
            if len(tot_weighted_DEM_all_angles) == 0:
                # Initialize matrix first time we see the size of relevant extracted table
                tot_weighted_DEM_all_angles = np.zeros_like(weighted_DEM_sum_DLC_i)
            
            tot_weighted_DEM_all_angles += weighted_DEM_sum_DLC_i
            
        if method == 'python':
            df_out = pd.DataFrame(tot_weighted_DEM_all_angles, 
                                  index = [f'{geo_matrix[key]["elevation"]:1f}' for key in geo_matrix.keys()], 
                                  columns = [f'{a:.1f}' for a in point_angles[:]])
            df_out.to_excel(out_path_xlsx, index_label = 'mLat')
            print(df_out)
                
        for geo_idx, geo_row in enumerate(tot_weighted_DEM_all_angles):
            '''
            TODO map the geo idx to the DataFrame indexes after having dropped some geometries
            E.g, solution can be as below, but i suspect the "idx" must be rescaled in the geometry df
            for geo_idx in range(geometry.shape[0]): 
                geo_row = geometry.iloc[geo_idx]
                
                actual_angles_geo_i = geo_row['actual_angles']
                compass_angles_geo_i = global_2_compass(actual_angles_geo_i)
            '''
            
            actual_angles_geo_i = point_angles[:]
            compass_angles_geo_i = compass_angles[:]
            # test_df = pd.DataFrame(data = [geo_row], columns = [f'DEM {i} deg' for i in point_angles])
            DEM_geo_i_all_angles = tot_weighted_DEM_all_angles[geo_idx]
            DEM_max = (T_lifetime / N_equivalent * DEM_geo_i_all_angles.max() )**(1 / wohler_exp)
            
            res_data[method].append(DEM_max / 10**6)
            el = geo_matrix[geo_idx]['elevation']
            
            if method_idx == 0:
                df_row_labels.append(f'Elevation {el:.2f} mLat')
            
     
    # Add values from the c2wind final result verification, and print the 
    res_data['c2wind'] = [88.92, 98.21, 102.18, 104.06]
    vals = np.array(list(res_data.values())).T
    pd.set_option("display.precision", 2)
    df = pd.DataFrame(vals, index = df_row_labels, columns = [f'DEM {m} [MNm]' for m in res_data.keys()])  
    logger.info(f'Comparison of largest DEM found at each elevation per method') 
    print(df)
    sys.exit()
    
    logger.info(f'Finding overall max DEM of worst geo/elevation for the python method')
    # TODO this is just because the python method is the last one in the methods list

    worst_elevation_idx = divmod(tot_weighted_DEM_all_angles.argmax(), tot_weighted_DEM_all_angles.shape[1])[0] # Finds the row idx of the row containing the element with the lowest value of entire array
    worst_overall_sector_idx = tot_weighted_DEM_all_angles[worst_elevation_idx].argmax()
    mLAT_at_worst_elevation = geo_matrix[worst_elevation_idx]['elevation']
    
    # actual_angles_worst_el = geometry[worst_elevation_idx]['actual_angles']
    # compass_angles_worst_el = global_2_compass(actual_angles_worst_el)
    actual_angles_worst_el = point_angles[:]
    compass_angles_worst_el = compass_angles[:]
    
    worst_overall_DEM = (T_lifetime / N_equivalent * tot_weighted_DEM_all_angles[worst_elevation_idx].max() )**(1 / wohler_exp)
    print(f'Overall largest DEM found on:')
    print(f'Elevation {mLAT_at_worst_elevation:.2f} mLAT')
    print(f'Max DEM = {worst_overall_DEM / 10**6:.2f} MNm at {actual_angles_worst_el[worst_overall_sector_idx]} deg / {compass_angles_worst_el[DEM_geo_i_all_angles.argmax()]:.0f} degN')

    # Calculate damage, and lifetime (hard to compare right now since the % utilization for existing geometries is not available)
    equivalent_stress = worst_overall_DEM * geo_matrix[worst_elevation_idx]['D'] / (2 * geo_matrix[worst_elevation_idx]['I'])
    
    # TODO here information about the SCF and specific angles needs to be used -> all angles must be evaluated!
    # The code below is not valid
    
    
    # test = out_df[geo_idx]['scf_per_point']
    
    equivalent_stress /= 10**6 # scale to MPa for use with SN-curves or others
    dmg = curve.miner_sum(np.array([[equivalent_stress, N_equivalent]])) * DFF
    print(f'In-place damage for S_eq {equivalent_stress:.2f} MPa, D = sum_i^k (n_i / N_i) = N_eq / N_[S_eq] \t{dmg * 100.0:.2f} %')
    
    # Explicit method
    # dmg = N_equivalent * equivalent_stress**curve.SN.m2 / curve.SN.a2 * DFF
    # print(f'In-place damage, D = N_eq*S^m/a2 \t{dmg * 100.0:.2f} %')
    
    # print(f'Expected lifetime T_lifetime / D\t{1 / dmg * T_lifetime:.2f} years') # Damage has here during "equivalent"-methods been calculated on a 25-year basis. Therefore it must be multiplied to be absolute damage

    logger.info(f'Total DEM calculation script finished')
    
    '''
    Some notes
    
    log N = log a - m log S
        
    From relevant paper ->
    Wohler's equation for material failure; 
        - N_f * S^m = K
    Expressed in the famous SN-curve fashion
        - log S = (log K - log N)/m = (log K) / m - (log N) / m
    
    For N * S^m = a, we have that S < S_k @ N = N_f => a < K, and so the material is below the failure zone. 
    Hence the total damage can be expressed as the fraction
    
    D = N * S^m / K
    
    The Miner sum simply extends this to the possibility of observing different stress ranges
    over time such that for all individual observed stress ranges S_i, we have
    
    D = sum_i^k S_i^m / K
    
    This is called the Palmgren-Miner sum when assuming linear damage accumulation, expressing the damage in
    
    D = sum_i^k (n_i / N_i)
    
    Note that this damage is always expressed as a 
    
    Note that K in paper = a in the qats SN-curve implementaton
    Selected a = a2 in qats which corresponds to the wohler exp m = 5.0 => loga2 = 15.606 => a2 = 10 ** loga2
    qats curves stores a2 directly
    '''
    