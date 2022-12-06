from wetb.fatigue_tools.fatigue import eq_load, eq_load_and_cycles
from read_simulation_file.read_simulation_file import read_bladed_file
import matplotlib.pyplot as plt
from wetb.fatigue_tools.rainflowcounting import rainflowcount
import numpy as np
import struct
from get_moment_time_series import get_moment_time_series
from multiprocessing import Pool
import os 



def calculate_eq_loads_case_i(sector, sectors, DLC_IDs, timeseries_lengths, cluster_ID):

    rainflow_windap = rainflowcount.rainflow_windap
    rainflow_astm = rainflowcount.rainflow_astm

    path = r'C:\Users\IDH\OneDrive - Equinor\R&T Wind\RULe\SSE Doggerbank'
    fatigue_config_file = path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
    results_folder_for_cluster = path +  r'\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations'


    print( f'Process {os.getpid()} starts sector {sector}')

    weights_all_dlcs = []
    list_of_moments = []

    for DLC_ID, timeseries_length in zip(DLC_IDs, timeseries_lengths):
        moments_all_cases, weights = get_moment_time_series(DLC_ID, cluster_ID, fatigue_config_file, results_folder_for_cluster, timeseries_length)
        
        moments_all_cases_sector_1 = moments_all_cases[:, sectors.index(sector),:]
        
        for timeseries in moments_all_cases_sector_1:
            list_of_moments.append(timeseries)

        weights_all_dlcs = weights_all_dlcs + weights
        print('DLC_ID', DLC_ID)

    weights_all_dlcs = np.array(weights_all_dlcs)*6
    #weights_all_dlcs = np.ones(len(weights_all_dlcs))
    
    moment_lists = list(zip(weights_all_dlcs, list_of_moments))

    print(np.shape(list_of_moments))
    print(np.shape(weights_all_dlcs))
    print(np.shape(moment_lists))
    print(type(moment_lists))

    eq_loads, cycles, ampl_bin_mean, ampl_bin_edges = eq_load_and_cycles(moment_lists, no_bins=46, m=[5], neq=[ 10 ** 7], rainflow_func=rainflow_astm)

    print(np.shape(eq_loads))
    print('eq_loads', eq_loads)

    with open('dem_all_dlcs.txt', 'a') as resfile:
        resfile.write('Sector' + str((sector)) + str(eq_loads) + '\n')

    return eq_loads

def calculate_eq_loads_multiprocessed():
    
    pool_args = [(sector, sectors, DLC_IDs, timeseries_lengths, cluster_ID) for  sector in sectors]

    # This corresponds to a for-loop over all cases

    with Pool() as p:

        results = p.starmap(calculate_eq_loads_case_i, pool_args)

    return np.array(results) 


if __name__ == '__main__':

    
    DLC_IDs = ['DLC12', 'DLC64a', 'DLC64b', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b'  ]

    timeseries_lengths = [1201, 1201, 1201, 1201, 1501, 201, 201]
    sectors = list((range(0,359,15)))
    cluster_ID = 'JLO'

    calculate_eq_loads_multiprocessed()


