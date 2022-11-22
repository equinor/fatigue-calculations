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
DLC_ID = 'DLC64a'
DLC_ID = 'DLC64b'
cluster_ID = 'JLO'

moments_all_cases, weights = get_moment_time_series(DLC_ID, cluster_ID, fatigue_config_file, results_folder_for_cluster)

moments_all_cases_sector_1 = moments_all_cases[:,0,:]
list_of_moments = []
for timeseries in moments_all_cases_sector_1:
    list_of_moments.append(timeseries)

moment_lists = np.array([[weight, moment] for (weight, moment) in zip(weights, list_of_moments)])
moment_lists = list(zip(weights, list_of_moments))

print(np.shape(list_of_moments))
print(np.shape(weights))
print(np.shape(moment_lists))
print(type(moment_lists))

#plt.plot(moments_all_cases[1, 1, :])
#plt.show()
#damage_equivalent_moment = [eq_load(moment, no_bins=100, m=5, neq=1e7, rainflow_func=rainflow_windap) for moment in moments]

eq_loads, cycles, ampl_bin_mean, ampl_bin_edges = eq_load_and_cycles(moment_lists, no_bins=46, m=[5], neq=[ 10 ** 7], rainflow_func=rainflow_windap)

print(np.shape(eq_loads))
print('eq_loads', eq_loads)
#damage_equivalent_moment = np.reshape(damage_equivalent_moment, [1, len(damage_equivalent_moment)])[0]

#print(damage_equivalent_moment)

#DLC 12 = eq_loads [[25359289.980154537]]
#DLC64a = eq_loads [[27978500.797801655]]
#DLC64b = eq_loads [[20842588.818950817]]