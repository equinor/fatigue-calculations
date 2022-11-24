from wetb.fatigue_tools.fatigue import eq_load, eq_load_and_cycles
from read_simulation_file.read_simulation_file import read_bladed_file
import matplotlib.pyplot as plt
from wetb.fatigue_tools.rainflowcounting import rainflowcount
import numpy as np
import struct
from get_moment_time_series import get_moment_time_series

rainflow_windap = rainflowcount.rainflow_windap
rainflow_astm = rainflowcount.rainflow_astm

path = r'C:\Users\IDH\OneDrive - Equinor\R&T Wind\RULe\SSE Doggerbank'
fatigue_config_file = path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
results_folder_for_cluster = path +  r'\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations'

DLC_ID = 'DLC12'
#DLC_ID = 'DLC64a'
#DLC_ID = 'DLC64b'
#DLC_ID = 'DLC24a' 
#DLC_ID = 'DLC31' # events
#DLC_ID = 'DLC41a' # events 
#DLC_ID = 'DLC41b' # events
DLC_IDs = ['DLC12', 'DLC64a', 'DLC64b', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b'  ]

timeseries_lengths = [1201, 1201, 1201, 1201, 1501, 201, 201]
sectors = list((range(0,359,15)))
cluster_ID = 'JLO'


eq_loads_all_sectors = []
for index, val in enumerate(sectors):

    weights_all_dlcs = []
    list_of_moments = []

    for DLC_ID, timeseries_length in zip(DLC_IDs, timeseries_lengths):
        moments_all_cases, weights = get_moment_time_series(DLC_ID, cluster_ID, fatigue_config_file, results_folder_for_cluster, timeseries_length)
        
        moments_all_cases_sector_1 = moments_all_cases[:,index,:]
        
        for timeseries in moments_all_cases_sector_1:
            list_of_moments.append(timeseries)

        weights_all_dlcs = weights_all_dlcs + weights
        print('DLC_ID', DLC_ID)

    weights_all_dlcs = np.array(weights_all_dlcs)*6

    moment_lists = list(zip(weights_all_dlcs, list_of_moments))

    print(np.shape(list_of_moments))
    print(np.shape(weights_all_dlcs))
    print(np.shape(moment_lists))
    print(type(moment_lists))

    eq_loads, cycles, ampl_bin_mean, ampl_bin_edges = eq_load_and_cycles(moment_lists, no_bins=46, m=[5], neq=[ 10 ** 7], rainflow_func=rainflow_astm)

    print(np.shape(eq_loads))
    print('eq_loads', eq_loads)

    with open('dem_all_dlcs.txt', 'a') as resfile:
        resfile.write('Sector' + str((val)) + str(eq_loads) + '\n')

    eq_loads_all_sectors = eq_loads_all_sectors + eq_loads

print(eq_loads_all_sectors)