import numpy as np 
from utils.get_scf_sector_list import get_scf_sector_list
from utils.transformations import compass_2_global, global_2_compass
from utils.SN_Curve import SN_Curve_qats

def calculate_cross_section_properties(geo_row):
    """Calculate general geometric properties of a turbine's cross section as defined by properties in the input

    Args:
        geo_row (pandas.DataFrame): cross section properties

    Returns:
        float x 5: diameter | smallest wall thickness | area | second moment of inertia | section modulus
    """
    
    D = geo_row['diameter'] # [m]
    t = geo_row['small_thickness'] / 1000.0 # [m] (millimeters converted to meters)
    
    if geo_row['in_out'].lower() == 'o':
        A = np.pi * ((D/2)**2 - ((D - 2*t)/2)**2) # [m**2] Area in the plane of the current circular, holed geometry 
        I = np.pi / 64.0 * (D**4 - (D - 2*t)**4) # [m**4]
        Z = I / (D / 2)
    else:
        out_D = D + 2*t
        A = np.pi * (((out_D)/2)**2 - ((out_D - 2*t)/2)**2)
        I = np.pi / 64.0 * (out_D**4 - (D)**4)
        Z = I / (D / 2)
        
    return D, t, A, I, Z

def calculate_thickness_scaling_factors(geo_row, curve):
    """Calculate the thickness scaling parameters used when accounting for the thickness of fatigue specimen relative to the reference thickness used in the DNVGL-RP-C203 SN-curves

    Args:
        geo_row (pandas.DataFrame): the Dataframe containing information about a single elevation
        curve (SN_Curve_qats): implementation of the related DNVGL-RP-C203 SN-curve for the specific elevation

    Returns:
        (float, float, float): largest weld length as defined by DNVGL-RP-C203 | effective thickness | thickness scaling factor
    """
    L_t   = geo_row['largest_weld_length']
    t_eff = min( 14.0 + 0.66 * L_t , geo_row['large_thickness']) # [mm] Effective thickness scaling
    t_eff = max(curve.t_ref, t_eff) # according to eq. 2.4.3 and 4 DNVGL-RP-C203, t_eff = t_ref when t_eff < t_ref
    alpha = max(1.0, (t_eff / curve.t_ref )**curve.k ) # thickness scaling factor of element vs. SN-curve element
    return L_t, t_eff, alpha

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
        
        out_df[geo_idx]['elevation']   = geo_row['elevation']
        out_df[geo_idx]['in_out']      = geo_row['in_out']
        out_df[geo_idx]['description'] = geo_row['description']
        
        D, t, A, I, Z = calculate_cross_section_properties(geo_row)
        out_df[geo_idx]['D'] = D
        out_df[geo_idx]['t'] = t
        out_df[geo_idx]['A'] = A
        out_df[geo_idx]['I'] = I
        out_df[geo_idx]['Z'] = Z
        
        sectors_compass = global_2_compass(sectors)
        adjusted_sectors_compass, scf_per_point = get_scf_sector_list(geo_row, sectors_compass) # (n_geo, n_angles) shaped
        adjusted_sectors = compass_2_global(adjusted_sectors_compass)
        out_df[geo_idx]['adjusted_angles'] = adjusted_sectors
        out_df[geo_idx]['scf_per_point'] = scf_per_point
        
        out_df[geo_idx]['sn_curve']    = SN_Curve_qats(geo_row['sn_curve'])
        out_df[geo_idx]['scf']         = geo_row['scf']
        out_df[geo_idx]['gritblast']   = geo_row['gritblast']
        out_df[geo_idx]['orientation'] = compass_2_global(geo_row['orientation']) if (geo_row['orientation'] != 'omni' and geo_row['orientation'] != 'Omni') else None
        
        L_t, t_eff, alpha = calculate_thickness_scaling_factors(geo_row, out_df[geo_idx]['sn_curve'])
        out_df[geo_idx]['L_t']   = L_t
        out_df[geo_idx]['t_eff'] = t_eff
        out_df[geo_idx]['alpha'] = alpha
        
        try:
            # If the geometry is a member, it also has a column where the moments and forces are defined
            out_df[geo_idx]['member_id'] = geo_row['member_id']
            out_df[geo_idx]['mx_col']    = geo_row['mx_col']
            out_df[geo_idx]['my_col']    = geo_row['my_col']
            out_df[geo_idx]['fz_col']    = geo_row['fz_col']
            
        except KeyError as err:
            # print(f'Caught Key Error: {err} - setting member column as None and counts this as non-member node')
            out_df[geo_idx]['member_id'] = None
            out_df[geo_idx]['mx_col']     = None
            out_df[geo_idx]['my_col']     = None
            out_df[geo_idx]['fz_col']     = None
            out_df[geo_idx]['lifetime']      = geo_row['lifetime']
            out_df[geo_idx]['cluster']       = geo_row['cluster']
            out_df[geo_idx]['turbine_name']  = geo_row['turbine_name']
            out_df[geo_idx]['ValType']       = geo_row['ValType']
            out_df[geo_idx]['Nref']          = geo_row['Nref']
            out_df[geo_idx]['in_place_utilization'] = geo_row['in_place_utilization']
            
    return out_df