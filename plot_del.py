import matplotlib.pyplot as plt
import numpy as np

#Get data from files
####################################################################
dem_results_file = 'dem_all_dlcs_rainflow_astm.txt'

SSE_reported_sectors = [np.deg2rad(165)]#Assuming that the max value from the report is the for the maximum sector from EQN computations
SSE_reported_dem = [88041*10**3]

matlab_dem = np.array([9.3158, 9.2559, 9.1866, 9.1266, 9.0702, 8.9909, 8.9180, 8.8910, 8.9525, 9.0681, 9.2277, 9.3201, 9.3158, 9.2559, 9.1866, 9.1266, 9.0702, 8.9909, 8.9180, 8.8910, 8.9525, 9.0852, 9.2277, 9.3153])*10**7


with open(dem_results_file , mode='r') as file: # b is important -> binary
    lines = file.read().split('\n')

lines = [line.replace('[', ' ') for line in lines]
lines = [line.replace(']', ' ') for line in lines]
vals = [line.split(' ') for line in lines]
vals  = [list(filter(None, val)) for val in vals]
vals = [x for x in vals if x]
vals_astm  = [float(val[1]) for val in vals]
sectors_astm  = [np.deg2rad(float(val[0].split('r')[1])) for val in vals]

#Sorting if lists are in irregular order
vals_astm = [x for _, x in sorted(zip(sectors_astm, vals_astm), key=lambda pair: pair[0])]
sectors_astm = [_ for _, x in sorted(zip(sectors_astm, vals_astm), key=lambda pair: pair[0])]

dem_results_file = 'dem_all_dlcs_rainflow_windap.txt'

with open(dem_results_file , mode='r') as file: # b is important -> binary
    lines = file.read().split('\n')

lines = [line.replace('[', ' ') for line in lines]
lines = [line.replace(']', ' ') for line in lines]
vals = [line.split(' ') for line in lines]
vals  = [list(filter(None, val)) for val in vals]
vals = [x for x in vals if x]
vals_ap = [float(val[1]) for val in vals]
sectors_ap = [np.deg2rad(float(val[0].split('r')[1])) for val in vals]

#Sorting if lists are in irregular order
vals_ap = [x for _, x in sorted(zip(sectors_ap, vals_ap), key=lambda pair: pair[0])]
sectors_ap = [_ for _, x in sorted(zip(sectors_ap, vals_ap), key=lambda pair: pair[0])]

print(sectors_ap)

print('Worst sector', sectors_ap[np.argmax(vals_ap)])

#Plot
##########################################################

print(max(vals_ap))

sectors = list(np.deg2rad(range(0,359,15)))

fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
ax.plot(sectors_astm, vals_astm)
ax.plot(sectors_ap , vals_ap)
ax.plot(sectors, matlab_dem)
ax.plot(SSE_reported_sectors , SSE_reported_dem , marker = 'o', color = 'r')#Values from report)
#ax.set_rticks([0.5, 1, 1.5, 2])  # Less radial ticks
ax.set_rlabel_position(45)  # Move radial labels away from plotted line

ax.annotate("Max val: {:.2e}".format(max(vals_astm)), xy=[sectors_astm[np.argmax(np.array(vals_astm))], max(vals_astm)], fontsize=10, color ='C0') 
ax.annotate("Max val: {:.2e}".format( max(vals_ap)), xy=[sectors_ap[np.argmax(np.array(vals_ap))]+0.15,  max(vals_ap)+( max(vals_ap)*0.05)], fontsize=10, color ='C1') 
ax.annotate("Max val: {:.2e}".format(max(matlab_dem)), xy=[sectors[np.argmax(np.array(matlab_dem))]+0.15, max(matlab_dem)+(max(matlab_dem)*0.05)], fontsize=10, color ='C2') 
ax.annotate("SSE val: {:.2e}".format(max(SSE_reported_dem)), xy=[SSE_reported_sectors[np.argmax(np.array(SSE_reported_dem))]+0.2, max(SSE_reported_dem)-(max(SSE_reported_dem)*0.15)], fontsize=10, color ='r') 

ax.set_theta_zero_location("N")  # theta=0 at the top
ax.set_theta_direction(-1)  # theta increasing clockwise
ax.set_rmax(np.max(vals_astm + vals_ap + SSE_reported_dem + list(matlab_dem) )*1.1)
#ax.set_rmax(15**7)


ax.grid(True)

ax.set_title("DEM tower bottom", va='bottom')
ax.legend(['rainflow_astm', 'rainflow_windap', 'matlab', 'SSE reported value'], loc='upper center', ncol=4,  bbox_to_anchor=(0.5, -0.05)) 
plt.show()

