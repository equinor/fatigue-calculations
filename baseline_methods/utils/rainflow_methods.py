import numpy as np 
import rainflow 
import qats

'''
Scripts for rainflow cycle counting
Previously contained fatpack, but not used now
'''

def get_range_and_count_rainflow(stress_timeseries, k = 128):
    '''
    Uses rainflow counting for finding stress ranges and their respective counts 
    '''
    ''' Returns a (N_ranges, 2) matrix with col0 = stress range and col1 = counts of given ranges.
    '''
    # Example of manual inspection
    # cycles = [(rng, mean, count, ix_range_start, ix_range_end) for rng, mean, count, ix_range_start, ix_range_end in rainflow.extract_cycles(stress_timeseries) ] 
    # ranges = np.array( [c_tup[0] for c_tup in cycles ] )
    # counts = np.array( [c_tup[2] for c_tup in cycles ] )
    
    # Returns a sorted list of (ranges, counts), where counts = 0.5 for half cycles. This can be used for scaling properly in the damage estimation. 
    return np.array(rainflow.count_cycles(stress_timeseries, nbins = k))

def get_range_and_count_qats(stress_timeseries, k = 128):
    '''
    Uses rainflow counting for finding stress ranges and their respective counts using the qats package
    Typically finds 1 or 2 cycles less than the rainflow package, which is ~1% deviation in no. of cycles
    k is no. of bins
    '''
    
    cycles = qats.fatigue.rainflow.count_cycles(stress_timeseries) # Note - the returned array is sorted by INCREASING cycle range, handy for summation later to avoid roundoff errors
    ranges, mean, counts = qats.fatigue.rainflow.rebin(cycles, binby='range', n=k).T # rebin into k equidistant bins
    
    # ranges, mean, counts = qats.fatigue.rainflow.count_cycles(stress_timeseries).T # No rebinning
    return np.hstack((ranges.reshape(-1,1), counts.reshape(-1,1))) 