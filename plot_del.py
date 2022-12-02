import matplotlib.pyplot as plt
import numpy as np

dem_results_file = 'dem_all_dlcs_rainflow_astm.txt'

SSE_reported_sectors = [np.deg2rad(165)]#Assuming that the max value from the report is the for the maximum sector from EQN computations
SSE_reported_dem = [88041*10**3]

with open(dem_results_file , mode='r') as file: # b is important -> binary
    lines = file.read().split('\n')

lines = [line.replace('[', ' ') for line in lines]
lines = [line.replace(']', ' ') for line in lines]
vals = [line.split(' ') for line in lines]
vals  = [list(filter(None, val)) for val in vals]
vals = [x for x in vals if x]
vals_astm  = [float(val[1]) for val in vals]


dem_results_file = 'dem_all_dlcs_rainflow_windap.txt'

with open(dem_results_file , mode='r') as file: # b is important -> binary
    lines = file.read().split('\n')

lines = [line.replace('[', ' ') for line in lines]
lines = [line.replace(']', ' ') for line in lines]
vals = [line.split(' ') for line in lines]
vals  = [list(filter(None, val)) for val in vals]
vals = [x for x in vals if x]
vals_ap = [float(val[1]) for val in vals]
sectors_ap = [val[0] for val in vals]

print('Worst sector', sectors_ap[np.argmax(vals_ap)])

#PLOT
##########################################################

sectors = list(np.deg2rad(range(0,359,15)))

fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
ax.plot(sectors, vals_astm)
ax.plot(sectors, vals_ap)
ax.plot(SSE_reported_sectors , SSE_reported_dem , marker = 'o', color = 'r')#Values from report)
#ax.set_rticks([0.5, 1, 1.5, 2])  # Less radial ticks
ax.set_rlabel_position(45)  # Move radial labels away from plotted line

for s, v in zip(sectors[::2], vals_astm[::2]):
    ax.annotate("{:.2e}".format(v), xy=[s, v], fontsize=10, color ='C0') 

for s, v in zip(sectors[::2], vals_ap[::2]):
    ax.annotate("{:.2e}".format(v), xy=[s+0.15, v+(v*0.05)], fontsize=10, color ='C1') 

for s, v in zip(SSE_reported_sectors, SSE_reported_dem):
    ax.annotate("{:.2e}".format(v), xy=[s+0.2, v+(v*0.05)], fontsize=10, color ='r') 

ax.set_theta_zero_location("N")  # theta=0 at the top
ax.set_theta_direction(-1)  # theta increasing clockwise
ax.set_rmax(np.max(vals_astm + vals_ap + SSE_reported_dem )*1.1)

ax.grid(True)

ax.set_title("DEM tower bottom", va='bottom')
ax.legend(['rainflow_astm', 'rainflow_windap', 'SSE reported value'], loc='upper center', bbox_to_anchor=(0.5, -0.05)) 
plt.show()

