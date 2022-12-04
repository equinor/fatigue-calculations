import numpy as np
import fatpack

def find_stress_cycles_ranges_reversals_fatpack(y):
    '''
    Using the fatpack package for finding stress ranges through rainflow counting - see fatpack on github for which rainflow method is used / implemented
    
    y = single stress timeseries
    
    Returns the cycles, corresponding stress ranges, the reversals and the reversal indexes
    '''
    # Find reversals (peaks and valleys), extract cycles and residue (open cycle sequence), process and extract CLOSED cycles from residue.
    reversals, reversals_ix = fatpack.find_reversals(y) # Note here that the k=64 default parameter: number of intervals to divide the min-max range of the dataseries into 
    cycles, residue         = fatpack.find_rainflow_cycles(reversals)
    processed_residue       = fatpack.concatenate_reversals(residue, residue)
    cycles_residue, _       = fatpack.find_rainflow_cycles(processed_residue)
    cycles_total            = np.concatenate((cycles, cycles_residue))
    stress_ranges           = np.abs(cycles_total[:, 1] - cycles_total[:, 0]) # Find the rainflow stress_ranges from the cycles - d_sigma in DNV standard 
    
    return cycles_total, stress_ranges, reversals, reversals_ix