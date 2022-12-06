import numpy as np 
from utils.find_stress_cycles_ranges_reversals_fatpack import find_stress_cycles_ranges_reversals_fatpack
from utils.plot_inspection_of_single_stress_timeseries import plot_inspection_of_single_stress_timeseries
import fatpack
from multiprocessing import Pool
import matplotlib.pyplot as plt 
import rainflow

# TODO move the alpha scaling to this point where the stress ranges are multiplied instead of the  
# TODO multiply by 2? 
# Not necessarily a good idea since damage is exponential in stress due to the SN-curve shape
# 10% increased mean stress range => 30-60% increased damage vs. 100% increased stress -> 700-3100% more damage
# TODO remove the stress scaling with effective thickness and alpha, and compare results with MATLAB
# I believe this should not matter since the values for alpha is the same in MATLAB and here..

def calculate_damage(stress_timeseries_batch, curve, MP = False, rainflow_pck = True):
    ''' Calculates damage
    Input:  stress_timeseries sized (n_cases, n_angles, n_timesteps), and SN curve, all angles of our sectors, MP = multiprocessed, rainflow_pck = if rainflow pckg in Python should be used   
    Outputs: (n_cases, n_angles) sized table of damages
    '''
    print(f'Calculating damage, multiprocessed = {MP} and rainflow_pck = {rainflow_pck}')
    damage = np.zeros((stress_timeseries_batch.shape[0], stress_timeseries_batch.shape[1]))
    stress_range_finder_func = find_stress_range_and_count_with_rainflow if rainflow_pck else fatpack.find_rainflow_ranges 
    # The former uses the rainflow package with 3 point rainflow counting, and returns sorted ranges with counts incl. half cycles
    # The latter are ranges just in the observed chronological order -> not binned nor divided into half / whole cycles anything. 
    
    if MP:
        print('Calculating damage multiprocessed')
        n_cases = stress_timeseries_batch.shape[0]
        pool_args = [(stress_timeseries_batch[case_i], curve, stress_range_finder_func) for case_i in range(n_cases)]
        with Pool() as p: # This corresponds to a for-loop over all cases
            results = p.starmap(calculate_damage_case_i, pool_args) 
           
        damage = np.array(results)  # Results will now contain a list of lists of n_cases; each list contains n_angles elements for each case_i.    
    
    else:
        print('Calculating damage single process')
        for case_idx, stress_timeseries_case_i in enumerate(stress_timeseries_batch):   
            damage[[case_idx], :]  = calculate_damage_case_i(stress_timeseries_case_i, curve, stress_range_finder_func)
                            
    return damage

def calculate_damage_case_i(stress_timeseries_case_i, curve, stress_range_finder_func):
    ''' Function for looping through all sectors and calculating their damage from case_i. 
    Created to fit both multiprocessing and not, therefore the passing of a function for finding the stress ranges'''
    damage_case_i = [0]*stress_timeseries_case_i.shape[0] #n_angles
    for ang_idx, stress_timeseries_case_i_ang_j in enumerate(stress_timeseries_case_i):
        # stress_ranges comes as (N_stress_ranges, n_counts) sized matrix if rainflow. if Fatpack: (N,) stress ranges are passed -> find_miner_sum handles both
        stress_ranges = stress_range_finder_func(stress_timeseries_case_i_ang_j, k = 100)     
        damage_case_i[ang_idx] = curve.SN.find_miner_sum(stress_ranges) # TODO stress_ranges = stress_ranges[stress_ranges[:,0] > 1e-6] 
        
    return damage_case_i
        
def find_stress_range_and_count_with_rainflow(stress_timeseries_case_i_ang_j, k=100):
    ''' Returns a (N_ranges, 2) matrix with col0 = stress range and col1 = counts of this range. k is a dummy var
    '''
    # cycles = [(rng, mean, count, ix_range_start, ix_range_end) for rng, mean, count, ix_range_start, ix_range_end in rainflow.extract_cycles(stress_timeseries_case_i_ang_j) ] 
    # ranges = np.array( [c_tup[0] for c_tup in cycles ] )
    # counts = np.array( [c_tup[2] for c_tup in cycles ] )
    
    # Returns a sorted list of (ranges, counts), where counts = 0.5 for half cycles. This can be used for scaling properly in the damage estimation. 
    return np.array(rainflow.count_cycles(stress_timeseries_case_i_ang_j))

if __name__ == '__main__':
    pass