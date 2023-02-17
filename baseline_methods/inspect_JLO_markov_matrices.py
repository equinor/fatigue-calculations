import numpy as np
import pandas as pd
from utils.fastnumpyio import load

'''
Test to see if the cycles were calculated the same way before and after separating into different clusters (the code was developed with a single turbine in a single cluster, and expanded afterwards)
'''
if __name__ == '__main__':
    
    arr1 = np.array( load( r'C:\Appl\TDI\fatigue-calculations\baseline_methods\output\markov\DB_JLO_DLC12_member54_case333.npy' ) )
    arr2 =  np.array( load( r'C:\Appl\TDI\fatigue-calculations\baseline_methods\output\all_turbines\JLO\markov\DB_JLO_DLC12cycles_member54_case333.npy' ) )
    
    print('Moments')
    print( '¤ Gammel ¤ '*10 )
    print( arr1[:,:,0] )
    print( '¤ Ny ¤ '*10 )
    print( arr2[:,:,0] )
    print(' ')
    print('Counts')
    print( '¤ Gammel ¤ '*10 )
    print( arr1[:,:,1] )
    print( '¤ Ny ¤ '*10 )
    print( arr2[:,:,1] )