from wetb.fatigue_tools.fatigue import eq_load
from read_simulation_file.read_simulation_file import read_bladed_file
import matplotlib.pyplot as plt
from wetb.fatigue_tools.rainflowcounting import rainflowcount
import numpy as np
import struct

rainflow_windap = rainflowcount.rainflow_windap
rainflow_astm = rainflowcount.rainflow_astm

#binary_file = r'C:\Users\moksh\Downloads\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations\1_Fatigue\F1.2_PowerProd\WD000\04\JLO12-04-000-000-00p26-03p11-0-s1.$105'
#text_file = r'C:\Users\moksh\Downloads\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations\1_Fatigue\F1.2_PowerProd\WD000\04\JLO12-04-000-000-00p26-03p11-0-s1.%105'

binary_file = r'C:\Users\IDH\OneDrive - Equinor\R&T Wind\RULe\SSE Doggerbank\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations\1_Fatigue\F1.2_PowerProd\WD000\04\JLO12-04-000-000-00p26-03p11-0-s1.$105'
text_file = r'C:\Users\IDH\OneDrive - Equinor\R&T Wind\RULe\SSE Doggerbank\Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_JLO-model_fatigue_timeseries_all_elevations\1_Fatigue\F1.2_PowerProd\WD000\04\JLO12-04-000-000-00p26-03p11-0-s1.%105'


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
damage_equivalent_moment = np.reshape(damage_equivalent_moment, [1, len(damage_equivalent_moment)])[0]

print(damage_equivalent_moment)