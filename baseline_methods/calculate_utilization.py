import numpy as np
import sys
import pandas as pd
import swifter # can replace 'df.apply' with 'df.swifter.apply' which should improve speed on vectorizable functions. has more overhead than worth it on smaller functions
import os
from utils.create_geo_matrix import create_geo_matrix
from utils.fastnumpyio import load as fastio_load 
from utils.transformations import compass_2_global, global_2_compass
from utils.setup_custom_logger import setup_custom_logger
import json
from read_structural_report import read_utilization_and_store_geometries

# TODO functions? So that it can be used by other scripts as well 

def find_above_below_closest_elevations(df, member_elevations):
    df['dist_to_members'] = df.apply(lambda row: member_elevations - row['elevation'], axis=1)
    df['idx_elevation_above'] = df.apply(lambda row: np.ma.MaskedArray(row['dist_to_members'], row['dist_to_members'] < 0.0).argmin(), axis=1)
    df['idx_elevation_below'] = df.apply(lambda row: np.ma.MaskedArray(row['dist_to_members'], row['dist_to_members'] >= 0.0).argmax(), axis=1)
    df['idx_elevation_closest'] = df.apply(lambda row: np.abs(row['dist_to_members']).argmin(), axis=1)
    return member_elevations[df['idx_elevation_above']],  member_elevations[df['idx_elevation_below']], member_elevations[df['idx_elevation_closest']]

def return_worst_elevation(df):
    report_worst_elevation_idx = pd.to_numeric(df['in_place_utilization']).argmax()
    df_res = df.iloc[report_worst_elevation_idx].copy()   
    df_res = df_res[ ['elevation', 'in_out', 'description', 'in_place_utilization'] ].copy()
    all_rule_utilizations = (df['rule_miner_sum_no_DFF'] * df['rule_DFF'] * 100).copy()
    df_res['rule_utilization'] = all_rule_utilizations[report_worst_elevation_idx]
    rule_worst_elevation_idx = all_rule_utilizations.argmax()
    df_res['rule_worst_elevation'] = df.iloc[rule_worst_elevation_idx]['elevation']
    df_res['rule_worst_utilization'] = all_rule_utilizations.iloc[rule_worst_elevation_idx]
    return df_res

def calculate_utilization_single_turbine(sectors, member_path, DEM_data_path, geo_path, member_markov_path, result_path, DFFs: list, store_utils_all_elevations = False):
    
    # Define DEM variables
    wohler_exp = 5.0
    
    # Load geometries of interest
    geometries_of_interest_df = pd.read_excel(geo_path)
    turbine_name = geometries_of_interest_df.iloc[0]['turbine_name']
    cluster_ID = geometries_of_interest_df.iloc[0]['cluster_ID']
    
    member_geometry = pd.read_excel(member_path.format(cluster_ID))
    df_DEM_members_xlsx = pd.read_excel(DEM_data_path.format(cluster_ID))
    
    member_2_elevation_map = {k: v for k, v in zip(member_geometry[f'member_{cluster_ID}'], member_geometry['elevation'])}
    
    # Create geometries with pre-calculated A, I, Z, alpha etc
    geometries_of_interest = create_geo_matrix(geometries_of_interest_df, sectors)
    
    # Calculate the DEM of all member elevations, to be used for interpolation
    member_elevations = np.array([float(key) for key in (df_DEM_members_xlsx['mLat'].values)])
    
    df = pd.DataFrame(pd.DataFrame(geometries_of_interest)).T
    df = df[df['elevation'] >= member_elevations.min()] # we cannot interpolate locations below the lowest member elevation with available time series
    n_elevations = df.shape[0]
    
    if not DFFs: # handles None, 0, empty list 
        print('Encountered empty list / None value - interpreting all DFFs as 3.0')
        DFFs = [3.0] * n_elevations
    else:
        if (type(DFFs) in [list, np.ndarray]) and (len(DFFs) != n_elevations): 
            # DFFs given as list must be matching the number of elevations of interest - trying to use first given DFF for all
            try: 
                DFFs = [DFFs[0]] * n_elevations
            except IndexError as err: # DFFS given as empty list 
                DFFs = [3.0] * n_elevations
            except TypeError as err: # DFFS given as something non-subscriptable
                DFFs = [3.0] * n_elevations
            
    # Start adding the various properties
    df['curve'] = df.apply(lambda row: row['sn_curve'].SN.name, axis=1)
    above, below, close = find_above_below_closest_elevations(df,member_elevations)
    df['elevation_above'] = above
    df['elevation_below'] = below
    df['elevation_closest'] = close
    df['above_DEM_sums'] = df.apply(lambda row: np.array(df_DEM_members_xlsx.iloc[row['idx_elevation_above']][1:]), axis=1) # 1: is used since first column contains the member mLat values
    df['below_DEM_sums'] = df.apply(lambda row: np.array(df_DEM_members_xlsx.iloc[row['idx_elevation_below']][1:]), axis=1)
    df['DEM_elevation_above'] = df.apply(lambda row: ((row['lifetime'] / row['Nref'] * row['above_DEM_sums'])**(1 / wohler_exp)), axis=1) #((T_lifetime / N_equivalent * df['above_DEM_sums'])**(1 / wohler_exp))
    df['DEM_elevation_below'] = df.apply(lambda row: ((row['lifetime'] / row['Nref'] * row['below_DEM_sums'])**(1 / wohler_exp)), axis=1) #((T_lifetime / N_equivalent * df['below_DEM_sums'])**(1 / wohler_exp))
    df['DEM_elevation_closest'] = df.apply(lambda row: row['DEM_elevation_above'] if (row['elevation_closest'] > row['elevation']) else row['DEM_elevation_below'], axis=1)
    df['DEM_interpolated'] = df['DEM_elevation_below'] + (df['DEM_elevation_above'] - df['DEM_elevation_below']) * ( (df['elevation'] - df['elevation_below']) / (df['elevation_above'] - df['elevation_below']) )
    
    # Choose DEM at the closest sector to the SCF orientation. If omnidirectional => choose the largest DEM at the reference elevation
    df['closest_sector_idx'] = df.apply(lambda row: row['DEM_interpolated'].argmax() if row['orientation'] == None else np.absolute(sectors - row['orientation']).argmin(), axis=1)
    df['ref_orientation'] = df.apply(lambda row: global_2_compass(sectors[row['closest_sector_idx']]), axis=1)
    df['DEM_hs_MPa'] = df.apply(lambda row: row['DEM_interpolated'][row['closest_sector_idx']] / 1e6, axis=1)    
    
    # Gather pre calculated markov matrices from member elevations')
    markov_matrices = {}
    for mbr in member_2_elevation_map.keys():
        path = member_markov_path.format(mbr)
        member_elevation = member_2_elevation_map[mbr]
        print(f'loading matrix for {member_elevation}')
        markov_matrices[member_elevation] = np.array(fastio_load(path))
    
    # Calculate utilization for all other elevations
    
    # choose closest sector as reference markov matrix
    print('Collecting markov reference for closest elevations at worst sector')
    df['markov_reference'] = df.apply(lambda row: markov_matrices[row['elevation_closest']][row['closest_sector_idx']], axis=1)
    
    # NOTE sorting could be beneficial to avoid rounding errors, but takes a lot of time
    #logger.info('Sorting markov reference by ascending moment range order')
    #df['markov_reference'] = df.apply(lambda row: row['markov_reference'][ row['markov_reference'][:, 0].argsort() ], axis=1) # sort according to ascending moment ranges

    # Scale reference markov for hotspot: moment ranges scaled according to the DEM_scf / DEM_elevation_closest factor
    df['DEM_scaling_factor'] = df.apply(lambda row: row['DEM_interpolated'][row['closest_sector_idx']] / row['DEM_elevation_closest'][row['closest_sector_idx']], axis=1) 
    df['markov_hotspot'] = df.apply(lambda row: np.hstack( (row['markov_reference'][:, [0]] * row['DEM_scaling_factor'], row['markov_reference'][:, [1]])), axis=1)
    
    # Calculate stress
    df['stress_ranges_scaled'] = df.apply(lambda row: row['markov_hotspot'][:, [0]] / row['Z'] * row['scf'] * row['gritblast'] * row['alpha'], axis=1)
    
    # Store the equivalent nominal and hotspot stress range 
    df['Seq'] = df['DEM_hs_MPa'] / df['Z']
    df['Seq_hs'] = df['Seq'] * df['scf'] * df['gritblast']
    
    # Create stress cycles made out of stress in MPa and counts over entire lifetime, 
    # Exception is if validation type is "Equivalent", in which we skip the markov matrix scaling and calculate stress directly from DEM
    df['stress_cycles_MPa_lifetime'] = df.apply(lambda row: 
        np.hstack( (row['stress_ranges_scaled'] / 1e6, row['markov_reference'][:, [1]] * row['lifetime'])) if row['ValType'].lower() != 'equivalent' 
        else np.array([[row['Seq_hs'] * row['alpha'], row['Nref']]]), axis=1)
    
    # Calculate utilization through miner sum, without DFF, as DFF is stored to be applied and possibly changedlater
    df['rule_miner_sum_no_DFF'] = df.apply(lambda row: row['sn_curve'].miner_sum(row['stress_cycles_MPa_lifetime']), axis=1)
    df['rule_DFF'] = df.apply(lambda row: DFFs[row.name], axis=1)
    
    print('Saving out df')
    df = df[['elevation', 'in_out', 'description', 'D', 't', 
             'curve', 'DEM_hs_MPa', 'Seq', 'scf', 'gritblast',
             'Seq_hs', 'L_t', 't_eff', 'alpha', 'rule_miner_sum_no_DFF', 
             'rule_DFF', 'in_place_utilization', 'DEM_scaling_factor',
             'elevation_closest', 'closest_sector_idx', 'ValType']].copy()
    
    if store_utils_all_elevations:
        df.to_excel(result_path + fr'\{turbine_name}_util_rule_vs_report.xlsx', index = False)
        pd.options.display.max_rows = 100 # Print more rows
        print(df)
    
    df_res = return_worst_elevation(df)
    result_path.format(cluster_ID)
    
    if not os.path.exists(result_path):
        os.makedirs(result_path)
        
    df_res.to_excel(result_path + fr'\{turbine_name}_util_comparison.xlsx', index = False)
    
    return df

if __name__ == '__main__':
    
    structural_file_path = os.getcwd() + r'\data\structural_specific_reports'
    filenames = next(os.walk(structural_file_path), (None, None, []))[2]
    filenames = [filename for filename in filenames if 'sl_' not in filename.lower()]
    
    filenames = [os.getcwd() + r'\data\structural_specific_reports\P0061-C1224-WP03-REP-002-F - DA_P53_CD Foundation Structural Design Report.pdf']

    turbine_names = [filename.split(' ')[2] for filename in filenames]
    util_result_path = [os.getcwd() + fr'\output\{turbine_name}_util_and_geos.xlsx' for turbine_name in turbine_names]
    
    for file_i, file in filenames:
        _ = read_utilization_and_store_geometries(filenames, util_result_path[file_i])
    
    logger = setup_custom_logger('util')
    sectors = [float(i) for i in range(0,359,15)]
    
    # prepare file paths with formatting for cluster ID and turbine name
    member_geo_path = fr'{os.getcwd()}\data' +  r'\{}_members.xlsx' # format for cluster_ID
    DEM_data_path = fr'{os.getcwd()}\output' + r'\{}_combined_DEM.xlsx' # format for cluster_ID
    result_path = fr'{os.getcwd()}\output\all_turbines' + r'\{}' # format for cluster_ID
    member_markov_path = fr'{os.getcwd()}\output\total_markov_member' + r'{}.npy' # # format for member_no
    geo_path = fr'{os.getcwd()}\output' + r'\{}_util_and_geos.xlsx'
        
    for i, turbine in enumerate(filenames):
        logger.info(f'Initiating utilization for turbine {turbine_names[i]}')
        _ = calculate_utilization_single_turbine(sectors = sectors,
                                                member_path = member_geo_path,
                                                DEM_data_path = DEM_data_path,
                                                geo_path = geo_path, 
                                                result_path = result_path, 
                                                member_markov_path = member_markov_path,
                                                DFFs = [], 
                                                store_utils_all_elevations = True)
        logger.info(f'Finished utilization for turbine {turbine_names[i]}')

