import numpy as np 
from utils.get_scf_sector_list import get_scf_sector_list
from utils.transformations import compass_2_global, global_2_compass

def create_geo_matrix(geometry, point_angles, curve):
    """Create a dictionary of the geometries collected from a dataframe, perform some intermediate calculations that does not need to be recalculated each time the geometry is used

    Args:
        geometry (pandas DataFrame): the DataFrame containing the information collected from an Excel sheet with overall geometry data for a certain elevation
        point_angles (list): angles of all relevant points / sectors on the given elevation
        curve (SN_Curve): SN curve 

    Returns:
        dict: key as elevation index, values as all relevant geometrical values at the elevation
        
    TODO maybe the curve can be a part of the geometry as well? Initially the script was created for above surface elevations
    TODO the "actual point angles" should account for that the SCF sectors are given in compass frame, while the functions here all use the turbine frame!!
    """  
    
    out_df = {i: dict() for i in range(geometry.shape[0])}

    for geo_idx in range(geometry.shape[0]): 
        # this way of iterating geometry is not sexy, but it contains one row with headers etc nicely and is only iterated through a few times
        geo_row = geometry.iloc[geo_idx]
        
        D = geo_row['od'] # [m]
        t = geo_row['wt'] / 1000.0 # [m] (millimeters converted to meters)
        A = np.pi * ((D/2)**2 - ((D - 2*t)/2)**2) # [m**2] Area in the plane of the current circular, holed geometry 
        I = np.pi / 64.0 * (D**4 - (D - 2*t)**4) # [m**4]
        Z = I / (D/2) if geo_row['inout'] == 'o' else I / (D/2 - t) # [m**3] - Defines inner or outer location
        
        # TODO translate angles from local frame to compass before finding scf_sectors, and then convert back
        actual_point_angles, scf_per_point = get_scf_sector_list(geo_row, point_angles) # (n_geo, n_angles) shaped
        
        out_df[geo_idx]['mx_col'] = geo_row['mx_col']
        out_df[geo_idx]['my_col'] = geo_row['my_col']
        out_df[geo_idx]['fz_col'] = geo_row['fz_col']
        out_df[geo_idx]['scf'] = geo_row['scf']
        out_df[geo_idx]['scf_sector'] = geo_row['scf_sector']
        out_df[geo_idx]['D'] = D
        out_df[geo_idx]['t'] = t
        out_df[geo_idx]['A'] = A
        out_df[geo_idx]['I'] = I
        out_df[geo_idx]['Z'] = Z
        out_df[geo_idx]['elevation'] = geo_row['z']
        out_df[geo_idx]['wt'] = min( 14.0 + 0.66 * geo_row['L_t'], geo_row['T']) # [mm] Effective thickness scaling
        out_df[geo_idx]['alpha'] = max(1.0, (out_df[geo_idx]['wt'] / curve.t_ref )**curve.k ) # Stress scaling factor
        out_df[geo_idx]['actual_angles'] = actual_point_angles
        out_df[geo_idx]['scf_per_point'] = scf_per_point
        out_df[geo_idx]['member_JLO'] = geo_row['member_JLO']
        
    return out_df