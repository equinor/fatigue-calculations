import numpy as np

def global_2_compass(angles):
    """Transform a list of angles in the "global" reference frame used for each turbine into the compass angles

    Args:
        angles (list): floating point angles, in degrees, where 0 deg = South and 90 deg = East (positive dir = counter clockwise)

    Returns:
        list: floating point angles, in degress, in the compass reference frame where 0 deg = North and 90 deg = East (positive dir = clockwise)
    """
    if isinstance(angles, list):
        return list(np.mod(180.0 - np.array(angles), 360))
    elif isinstance(angles, np.array):
        assert len(angles.shape) == 1, 'Numpy array of angles is only meant to be one dimensional'
        return np.mod(180.0 - angles, 360)
    elif isinstance(angles, float) or isinstance(angles, np.float64) or isinstance(angles, np.float32):
        return np.mod(180.0 - angles, 360)
    else:
        raise ValueError(f'The angle transformation only accepts a one dimensional list or numpy array, but was given type {type(angles)}')
    
    
def compass_2_global(angles):
    """Transform a list of angles in the compass reference frame into the "global" frame used for each turbine
    
    The exact same transformation can be used as for the transformation the other way around.

    Args:
        angles (list): floating point angles, in degrees, where 0 deg = North and 90 deg = East (positive dir = clockwise)

    Returns:
        list: floating point angles, in degress, in the global reference frame where 0 deg = South and 90 deg = East (positive dir = counter clockwise)
    """
    
    return global_2_compass(angles)