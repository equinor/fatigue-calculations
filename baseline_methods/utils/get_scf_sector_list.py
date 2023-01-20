import numpy as np

def get_scf_sector_list(geometry, point_angles):
    """
    Read geometry and look for angles with specific scf. 
    Return the updated list of angles and belonging scf.

    Args:
        geometry (dict): a dictionary of geometrical variables of the current elevation
        point_angles (list): of angles in degrees, evenly distributed across the geometry 

    Returns:
        list, list: updated list of angles in degrees, in the turbine reference frame (S = 0 deg, E = 90 deg), a list of the scf factors in each of these updated angles
        
    TODO the scf factors from geometry files are given in compass angles / frame. Need to account for this
    """
    
    # print('Recalculating angles and SCF')
    
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