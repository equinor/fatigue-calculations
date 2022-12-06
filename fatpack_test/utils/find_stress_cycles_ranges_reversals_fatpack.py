import numpy as np
import fatpack

def find_stress_cycles_ranges_reversals_fatpack(y, k = 100, THIRD_PASS = False):

    '''
    Using the fatpack package for finding stress ranges, cycles and reversals through rainflow counting - see fatpack on github for which rainflow method is used / implemented
    
    y = single stress timeseries
    k = no. of levels to divide the stress ranges into. Higher k means more findings, but also includes more small ranges
    
    Returns the cycles, corresponding stress ranges, the reversals and the reversal indexes
    
    TIPS: If you only want the stress ranges, use fatpack.find_rainflow_ranges(y,k), which does the same but does not store anything other than the ranges and is pre-compiled so should be faster
    '''
    # Find reversals (peaks and valleys), extract cycles and residue (open cycle sequence), process and extract CLOSED cycles from residue.
    if not THIRD_PASS:
        reversals, reversals_ix       = fatpack.find_reversals(y, k=k) # Note here that the k=64 default parameter: number of intervals to divide the min-max range of the dataseries into 
        cycles_firstpass, residue     = fatpack.find_rainflow_cycles(reversals)
        processed_residue             = fatpack.concatenate_reversals(residue, residue)
        cycles_open_sequence_1, residue = fatpack.find_rainflow_cycles(processed_residue)
        found_cycles_firstpass          = len(cycles_firstpass.shape) == 2
        found_cycles_open_sequence_1    = len(cycles_open_sequence_1.shape) == 2
        
        if found_cycles_firstpass and found_cycles_open_sequence_1:
            cycles_total = np.concatenate((cycles_firstpass, cycles_open_sequence_1))
        elif found_cycles_firstpass:
            cycles_total = cycles_firstpass
        elif found_cycles_open_sequence_1:
            cycles_total = cycles_open_sequence_1
        else:
            raise ValueError("Could not find any cycles in sequence") # TODO better to warn and add a list of a single zero?
    
    ### Testing third pass
    if THIRD_PASS:
        reversals, reversals_ix         = fatpack.find_reversals(y, k=k) # Note here that the k=64 default parameter: number of intervals to divide the min-max range of the dataseries into 
        cycles_firstpass, residue       = fatpack.find_rainflow_cycles(reversals)
        processed_residue               = fatpack.concatenate_reversals(residue, residue)
        cycles_open_sequence_1, residue = fatpack.find_rainflow_cycles(processed_residue)
        processed_residue               = fatpack.concatenate_reversals(residue, residue)
        cycles_open_sequence_2, residue = fatpack.find_rainflow_cycles(processed_residue)
        found_cycles_firstpass          = len(cycles_firstpass.shape) == 2
        found_cycles_open_sequence_1    = len(cycles_open_sequence_1.shape) == 2
        found_cycles_open_sequence_2    = len(cycles_open_sequence_2.shape) == 2
        
        if found_cycles_firstpass and found_cycles_open_sequence_1 and found_cycles_open_sequence_2:
            cycles_total = np.concatenate((cycles_firstpass, cycles_open_sequence_1, cycles_open_sequence_2))
        elif found_cycles_firstpass and found_cycles_open_sequence_1:
            cycles_total = np.concatenate((cycles_firstpass, cycles_open_sequence_1))
        elif found_cycles_firstpass and found_cycles_open_sequence_2:
            cycles_total = np.concatenate((cycles_firstpass, cycles_open_sequence_2))
        elif found_cycles_open_sequence_1 and found_cycles_open_sequence_2: # This should never happen -> if firstpass dont contain anything, I guess sequence 1 should not either?
            cycles_total = np.concatenate((found_cycles_open_sequence_1, cycles_open_sequence_2))
        elif found_cycles_firstpass:
            cycles_total = cycles_firstpass
        elif found_cycles_open_sequence_1:
            cycles_total = cycles_open_sequence_1
        elif found_cycles_open_sequence_2:
            cycles_total = cycles_open_sequence_2
        else:
            raise ValueError("Could not find any cycles in sequence")
    ###
    
    stress_ranges = np.abs(cycles_total[:, 1] - cycles_total[:, 0]) # Find the rainflow stress_ranges from the cycles - d_sigma in DNV standard    

    
    return cycles_total, stress_ranges, reversals, reversals_ix