import scipy.io
import numpy as np
import sys

def store_table(table, combined_table, weights, output_file_name, identifier = 'damage'):
    """
    Stores either a DEM or a damage table to a file format decided by output_file_name. Can store both .npy binaries and .mat binaries
    
    output file will contain
        - (n_cases, n_geometries, n_angles) for the table
        - (n_geometries, n_angles) for the combined table (it has already been weighted somehow, depending on damage or DEM calculation)
        - (n_cases) weights, which represent the probability of each weather-case to be observed in a 10-min period during a year

    Args:
        table (np.array): 3D array with damage or DEM stored per case (dim0), per geometry (dim1), per angle (dim2)
        combined_table (np.array): 2D array with the weighted damage or DEM where the probability of each case has been multiplied in, and the units is converted to "per hour" format
        weights (np.array): row vector of the probabilities per case of the DLC
        output_file_name (str): path to store output file in
        identifier (str, optional): identify which data is stored; DEM or damage. Defaults to 'damage'.
    """
    
    if output_file_name.split('.')[-1] == 'npy':    
        # NOTE alternative check is output_file_name.endswith('.npy')
        # NOTE fastnumpyio.py contains methods where save and load is sped up - to be considered if these functions becomes bottlenecks. As of Feb 2023, they are not.
        with open(output_file_name, 'wb') as f:
            np.save(f, table)
    
    elif output_file_name.split('.')[-1] == 'mat':
        scipy.io.savemat(output_file_name, {f'{identifier}_python': table, f'combined_{identifier}_python': combined_table, 'weights_python': weights})
        
    else:
        print('No recognizable filetype - no table stored')
        
def load_table(file_name, identifier = 'damage', method = 'python'):
    """Loads a damage / DEM table
    Can be from MATLAB method and python

    Args:
        file_name (str): path of file to load
        identifier (str, optional): identifies which data is to be loaded; DEM or damage. Defaults to 'damage'.
        method (str, optional): identifies to where the calculated data comes from; matlab or python. Defaults to 'python'.

    Returns:
        list: of three np.arrays: damage/DEM, weighted damage/DEM, and the weights
    """
    
    if method == 'matlab':
        # If the file comes from matlab, it should be a mat file a .mat
        mapper = {'damage': 'damage', 'DEM': 'damage_dem'} # a map from my identifiers to the previous MATLAB implementation's naming conventions  
        try:
            ret = scipy.io.loadmat(file_name) 
            return [ret['beam_fatigue'][f'{mapper[identifier]}'][0][0],  ret['beam_fatigue'][f'combined_{mapper[identifier]}'][0][0], ret['config']['weight'][0][0]]
        
        except Exception as err:
            print(f"Unexpected {err=}, {type(err)=} when trying to read from {method} method")
            raise
    
    elif method == 'python':
        # There is only python left
        
        if file_name.split('.')[-1] == 'npy':    
            with open(file_name, 'rb') as f:
                return np.load(f)
            
        elif file_name.split('.')[-1] == 'mat':
            ret = scipy.io.loadmat(file_name) 
            return [ret[f'{identifier}_python'],  ret[f'combined_{identifier}_python'], ret['weights_python']]
            
        else:
            print('No recognizable filetype - no table loaded')
            return np.empty((1,1,)) * np.nan
        
    else:
        print('Not a recognized method')
        return np.empty((1,1,)) * np.nan