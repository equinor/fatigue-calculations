import numpy as np

def calculate_stress_timeseries(forces, moments, geometry, actual_angles, scf_per_point, curve):
    '''
    Inputs forces (similar for all angles) and moments (for various angles) time series and the given geometry and angles of interest.
    Calculates the stress timeseries as a combination of bending moment and axial force
    
    Outputs 3D array of stress with dims (case, theta, timestep)
    
    TODO double check the calculation for units etc. etc., including the alpha and unit scaling at the end - this has been stolen from 
    Note that the Matlab script finds rainflow cycles first!! then scales with alpha before looking into the SN table. Maybe this can affect rainflow differences
    Matlab script multiplies with 1e-6 in the end, do not understand why. I want to go from 1 Pa to MPa, depending on what the curve calculations want 
    '''
    print('Calculating stress timeseries')
    
    D = geometry['od'] # meters
    t = geometry['wt'] / 1000.0 # millimeters concerted to millimeters
    A = np.pi * ( (D/2)**2 - ((D - 2*t)/2)**2) # m**2 Area in the plane of the current circular, holed geometry 
    I = np.pi / 64.0 * (D**4 - (D - 2*t)**4) # m**4
    Z = I / (D/2) if geometry['inout'] == 'o' else I / (D/2 - t) # m**3 - Defines inner or outer location
    
    # Effective thickness scaling copied from MATLAB
    wt = min( 14.0 + 0.66 * geometry['L_t'], geometry['T']) # millimeters
    alpha = max(1.0, (wt / curve.t_ref )**curve.k ) # From MATLAB script
    
    stress = forces / A + moments / Z # N / m**2 + Nm / m**3 = N / m**2 = Pa
    
    # Adjust the stress according the stress concentration factors for certain angles
    for i, _ in enumerate(actual_angles): # TODO I am sure this can be done with some kind of columnwise numpy function if scf_array
        stress[:,i,:] *= scf_per_point[i]
        
    return stress * alpha * 1e-6  