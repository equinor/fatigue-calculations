from wetb.fatigue_tools.fatigue import eq_load, eq_load_and_cycles
from read_simulation_file.read_simulation_file import read_bladed_file
import matplotlib.pyplot as plt
from wetb.fatigue_tools.rainflowcounting import rainflowcount
import numpy as np
import struct

rainflow_windap = rainflowcount.rainflow_windap
rainflow_astm = rainflowcount.rainflow_astm

path = 'C:\Users\IDH\OneDrive - Equinor\R&T Wind\RULe\SSE Doggerbank'
#stress_params_file = path +  'DA_P53_CD.xlsx'
fatigue_config_file = path +  'Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
results_folder_for_cluster = path +  'Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations'
DLC_ID = '12'
#DLC_ID = '64a'
#DLC_ID = '64b'
#DLC_ID = '24a' 
#DLC_ID = '31'
#DLC_ID = '41a' 
#DLC_ID = '41b'

cluster_ID = 'JLO'

moments = get_moment_time_series(DLC_ID, cluster_ID, fatigue_config_file, results_folder_for_cluster)

binary_file = r'C:\Users\IDH\OneDrive - Equinor\R&T Wind\RULe\SSE Doggerbank\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations\1_Fatigue\F1.2_PowerProd\WD120\08\JLO12-08-120-150-00p70-04p33-0-s16.$105'
text_file = r'C:\Users\IDH\OneDrive - Equinor\R&T Wind\RULe\SSE Doggerbank\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations\1_Fatigue\F1.2_PowerProd\WD120\08\JLO12-08-120-150-00p70-04p33-0-s16.%105'


content_reshaped = read_bladed_file(binary_file,text_file)

#plt.plot(content_reshaped[0,:])
#plt.show()

moment_x = content_reshaped[0,:]
moment_y = content_reshaped[1,:]

thetas = list(range(0,359,15))

moments = [np.sin(theta)*moment_x+np.cos(theta)*moment_y for theta in thetas]

damage_equivalent_moment = [eq_load(moment, no_bins=100, m=5, neq=1e7, rainflow_func=rainflow_windap) for moment in moments]

eq_load_and_cycles(signals, no_bins=46, m=[5], neq=[ 10 ** 7], rainflow_func=rainflow_windap)


damage_equivalent_moment = np.reshape(damage_equivalent_moment, [1, len(damage_equivalent_moment)])[0]

print(damage_equivalent_moment)