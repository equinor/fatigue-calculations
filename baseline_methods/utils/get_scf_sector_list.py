import numpy as np

def get_scf_sector_list(geometry, sectors):
    """
    Read geometry and look for angles with specific scf. 
    Return the adjusted list of angles and belonging scf.
    
    Args:
        geometry (dict): a dictionary of geometrical variables of the current elevation
        sectors (list): of angles in degrees IN COMPASS FRAME, evenly distributed across the geometry 

    Returns:
        list, list: adjusted list of angles in degrees, a list of the scf factors in each of these adjusted angles
    """
    
    adjusted_angles = np.array(sectors) # Initialize with all angles
    
    scf_per_point = np.ones_like(sectors) * geometry['scf'] # If omni -> all angles have same SCF
    
    scf_sectors = np.array([geometry['sn_curve_direction_1'], geometry['sn_curve_direction_2']])
    scf_sectors = scf_sectors[np.isfinite(scf_sectors)]
    
    if not scf_sectors.size == 0: # The sectors are not omnidirectionally affected by stress
        # specific_angles = list(map(float, map(str.strip, geometry['scf_sector'].split(',')))) # Split by , remove spaces and convert 2 float 
        
        scf_per_point = np.ones_like(sectors) # Initialize with scf = 1 for all angles

        for new_angle in scf_sectors:
            min_idx = np.absolute(adjusted_angles - new_angle).argmin() # find angles with least distance from the new one
            adjusted_angles[min_idx] = new_angle # replace the closest angle with the new angle
            scf_per_point[min_idx] = geometry['scf'] # correct the scf for the new angle      
     
    return adjusted_angles.tolist(), scf_per_point.tolist()