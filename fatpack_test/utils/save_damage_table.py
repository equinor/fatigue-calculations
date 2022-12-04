import scipy.io
import numpy as np

def save_damage_table(damage_table, output_file_name):
    
    if output_file_name.split('.')[-1] == 'npy':    
        with open(output_file_name, 'wb') as f:
            np.save(f, damage_table)
            
    elif output_file_name.split('.')[-1] == 'mat':
        scipy.io.savemat(output_file_name, {'beam_fatigue_fatpack': damage_table})
        
    else:
        print('No recognizable filetype - no damage table stored')
        
    
        
def load_damage_table(file_name):

    if file_name.split('.')[-1] == 'npy':    
        with open(file_name, 'rb') as f:
            return np.load(f)
        
    elif file_name.split('.')[-1] == 'mat':
        return scipy.io.loadmat(file_name)['beam_fatigue']
        
    else:
        print('No recognizable filetype - no damage table loaded')
        return None
