import numpy as np

def get_scf_sector_list(geometry, point_angles):
    ''' 
    Read geometry and look for angles with specific scf. 
    Return the updated list of angles and belonging scf.
    '''
    
    print('Recalculating angles and SCF')
    
    updated_angles = np.array(point_angles) # Initialize with all angles
    scf_per_point = np.ones_like(point_angles) * geometry['scf'] # If omni -> all angles have same SCF
    
    if geometry['scf_sector'] != 'omni': # The angles are not omnidirectionally affected by stress
        specific_angles = list(map(float, map(str.strip, geometry['scf_sector'].split(',')))) # Split by , remove spaces and convert 2 float 
        scf_per_point = np.ones_like(point_angles) # Initialize with scf = 1 for all angles

        for new_angle in specific_angles:
            min_idx = np.absolute(updated_angles - new_angle).argmin() # find angles with least distance from the new one
            updated_angles[min_idx] = new_angle # replace the closest angle with the new angle
            scf_per_point[min_idx] = geometry['scf'] # correct the scf for the new angle      
        
    return updated_angles.tolist(), scf_per_point.tolist()