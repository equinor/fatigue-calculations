import numpy as np
import struct

def read_bladed_file(binary_file,text_file):
    '''
    Processes binary file and returns a matrix with time series data. 
    
    Loads binary files and reads the data corresponding to the specification in description text file 
    Returns a (n,m) numpy array with dimensions:
        n = no. of quantities of data,  m = no. of timesteps for each data quantity 
    '''
    with open(binary_file, mode='rb') as file:
        content = file.read()
    with open(text_file, mode='r') as file: # b is important -> binary
        lines = file.read().split('\n')
    dimens = lines[8].split() # Defining the size of the data matrix
    rows = int(dimens[1]) # Number of different quantities in the matrix
    cols = int(dimens[2]) # Number of time steps

    content_unpacked = struct.unpack("<" + "f"*(len(content) // 4), content) # Define interpretation of binary data
    content_reshaped = np.reshape(content_unpacked, (rows, cols), order='F') # Reshape for a useable numpy array
    return content_reshaped