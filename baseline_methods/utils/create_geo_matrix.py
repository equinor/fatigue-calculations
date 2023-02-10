import numpy as np 
from utils.get_scf_sector_list import get_scf_sector_list
from utils.transformations import compass_2_global, global_2_compass
from utils.SN_Curve import SN_Curve_qats

def create_geo_matrix(geometry, sectors):
    """Create a dictionary of the geometries collected from a dataframe, perform some intermediate calculations that does not need to be recalculated each time the geometry is used

    Args:
        geometry (pandas DataFrame): the DataFrame containing the information collected from an Excel sheet with overall geometry data for a certain elevation
        sectors (list): angles of all relevant points / sectors on the given elevation
        curve (SN_Curve): SN curve 

    Returns:
        dict: key as elevation index, values as all relevant geometrical values at the elevation
    """  
    
    out_df = {i: dict() for i in range(geometry.shape[0])}

    for geo_idx in range(geometry.shape[0]): 
        # this way of iterating geometry is not sexy, but it contains one row with headers etc nicely and is only iterated through a few times
        geo_row = geometry.iloc[geo_idx]
        
        D = geo_row['outer_diameter'] # [m]
        t = geo_row['small_thickness'] / 1000.0 # [m] (millimeters converted to meters)
        A = np.pi * ((D/2)**2 - ((D - 2*t)/2)**2) # [m**2] Area in the plane of the current circular, holed geometry 
        I = np.pi / 64.0 * (D**4 - (D - 2*t)**4) # [m**4]
        Z = I / (D/2) if geo_row['in_out'].lower() == 'o' else I / (D/2 - t) # [m**3] - Defines inner or outer location
        out_df[geo_idx]['in_out'] = geo_row['in_out']
        
        sectors_compass = global_2_compass(sectors)
        
        out_df[geo_idx]['scf'] = geo_row['scf']
        adjusted_sectors_compass, scf_per_point = get_scf_sector_list(geo_row, sectors_compass) # (n_geo, n_angles) shaped
        adjusted_sectors = compass_2_global(adjusted_sectors_compass)
        out_df[geo_idx]['adjusted_angles'] = adjusted_sectors
        out_df[geo_idx]['scf_per_point'] = scf_per_point
        
        out_df[geo_idx]['D'] = D
        out_df[geo_idx]['t'] = t
        out_df[geo_idx]['A'] = A
        out_df[geo_idx]['I'] = I
        out_df[geo_idx]['Z'] = Z
        out_df[geo_idx]['elevation'] = geo_row['elevation']
        
        curve = SN_Curve_qats(geo_row['sn_curve'])
        out_df[geo_idx]['sn_curve'] = curve
        out_df[geo_idx]['L_t'] = geo_row['largest_weld_length']
        t_eff = min( 14.0 + 0.66 * out_df[geo_idx]['L_t'] , geo_row['large_thickness']) # [mm] Effective thickness scaling
        
        out_df[geo_idx]['t_eff'] = max(curve.t_ref, t_eff) # according to eq. 2.4.3 and 4 DNVGL-RP-C203, t_eff = t_ref when t_eff < t_ref
        out_df[geo_idx]['alpha'] = max(1.0, (out_df[geo_idx]['t_eff'] / curve.t_ref )**curve.k ) # thickness scaling factor of element vs. SN-curve element
        out_df[geo_idx]['gritblast'] =  geo_row['gritblast']
        try:
            # If the geometry is a member, it also has a column where the moments and forces are defined
            out_df[geo_idx]['member_JLO'] = geo_row['member_JLO']
            out_df[geo_idx]['mx_col'] = geo_row['mx_col']
            out_df[geo_idx]['my_col'] = geo_row['my_col']
            out_df[geo_idx]['fz_col'] = geo_row['fz_col']
            
        except KeyError as err:
            # print(f'Caught Key Error: {err} - setting member column as None and counts this as non-member node')
            out_df[geo_idx]['member_JLO'] = None
            out_df[geo_idx]['mx_col'] = None
            out_df[geo_idx]['my_col'] = None
            out_df[geo_idx]['fz_col'] = None
            # out_df[geo_idx]['member_number_lower']     = geo_row['member_number_lower']
            # out_df[geo_idx]['member_number_upper']     = geo_row['member_number_upper']
            # out_df[geo_idx]['member_elevation_lower']  = geo_row['member_elevation_lower']
            # out_df[geo_idx]['member_elevation_upper']  = geo_row['member_elevation_upper']    
            out_df[geo_idx]['design_load_cluster']     = geo_row['design_load_cluster']
            out_df[geo_idx]['in_place_utilization']    = geo_row['in_place_utilization']
        
    return out_df