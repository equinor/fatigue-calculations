import numpy as np 
from utils.find_stress_cycles_ranges_reversals_fatpack import find_stress_cycles_ranges_reversals_fatpack
from utils.plot_inspection_of_single_stress_timeseries import plot_inspection_of_single_stress_timeseries
import fatpack
from multiprocessing import Pool

'''
Uses fatpack to calculate the damage from a given batch of stress timeseries 

Includes a multiprocessed version

'''

def calculate_damage_fatpack(stress_timeseries_batch, curve, plotting = False):
    '''
    Calculates damage using fatpack curves and miner sum implementation
    
    Input:  
            - (n_cases, n_angles, n_timesteps) sized batch of stress timeseries
            - an SN curve for the given material used
            
    Outputs: 
            - (n_cases, n_angles) sized table of damages
    '''
    print('Calculating damage')
    damage = np.zeros((stress_timeseries_batch.shape[0], stress_timeseries_batch.shape[1]))
    
    for case_idx, stress_timeseries_case_i in enumerate(stress_timeseries_batch):
        for ang_idx, stress_timeseries_case_i_ang_j in enumerate(stress_timeseries_case_i):
            cycles_total, stress_ranges, reversals, reversals_ix = find_stress_cycles_ranges_reversals_fatpack(stress_timeseries_case_i_ang_j) 
            
            # Stress ranges is just the observed ranges found in chronological order -> not binned or anything. The miner summation is done based on which N corresponds to the observed S-values in the range
            # TODO this returns a runtime error once in a while complaining on stress_ranges equal to zero. Maybe there should be some code that sets all <= 0 values to 1e-6 or something
            damage[case_idx, ang_idx] = curve.SN.find_miner_sum(stress_ranges) 
            
            if plotting:
                N, S = fatpack.find_range_count(stress_ranges, 100) # Range of rainflow stress_ranges and the number of equally sized bins 
                plot_inspection_of_single_stress_timeseries(stress_timeseries_case_i_ang_j, N, S, cycles_total, reversals_ix, curve)
                
    return damage

def calculate_damage_fatpack_case_i(stress_timeseries_case_i, case_i, curve, n_angles):
    '''
    stress time series for case_i is a timeseries of x time steps with n_angles many angles to consider
    
    output is then one list / row of the damage for each angle in case i
    
    Returns a list of floats 
    
    Tips do not sys.exit() a Pooled process
    '''
    # print( f'Process {os.getpid()} starts case {case_i}')
    
    damage_case_i = [0]*len(n_angles) # create empty return list
    
    for ang_idx, stress_timeseries_case_i_ang_j in enumerate(stress_timeseries_case_i):
            _, stress_ranges, _, _ = find_stress_cycles_ranges_reversals_fatpack(stress_timeseries_case_i_ang_j)
            damage_case_i[ang_idx] = curve.SN.find_miner_sum(stress_ranges)
            
    return damage_case_i
    
def calculate_damage_fatpack_multiprocessed(stress_timeseries_batch, point_angles, curve):
    '''
    Calculates damage using fatpack curves and miner sum implementation
    
    Input:  
            - (n_cases, n_angles, n_timesteps) sized batch of stress timeseries
            - an SN curve for the given material used
            
    Outputs: 
            - (n_cases, n_angles) sized table of damages
    '''
    print('Calculating damage multiprocessed')
    
    n_cases = stress_timeseries_batch.shape[0]
    pool_args = [(stress_timeseries_batch[case_i], case_i, curve, point_angles) for case_i in range(n_cases)]
    
    # This corresponds to a for-loop over all cases
    with Pool() as p:
        results = p.starmap(calculate_damage_fatpack_case_i, pool_args) 
    
    # Results will now contain a list of lists of n_cases; each list contains n_angles elements for each case_i.       
    return np.array(results)  


if __name__ == '__main__':
    pass