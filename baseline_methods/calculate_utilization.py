import numpy as np
import sys
import pandas as pd
import swifter # can replace 'df.apply' with 'df.swifter.apply' which should improve speed on vectorizable functions. has more overhead than worth it on smaller functions
import os
from utils.create_geo_matrix import create_geo_matrix
from utils.fastnumpyio import load as fastio_load 
from utils.transformations import compass_2_global, global_2_compass
from utils.setup_custom_logger import setup_custom_logger

if __name__ == '__main__':
    
    logger = setup_custom_logger('utilization')
    logger.info(f'Initiating utilization for turbine DA_P53_CD')

    # Get relevant data_paths for DLC and simulation result files
    data_path     = fr'{os.getcwd()}\data'
    member_geometry_file_path = data_path +  r'\DA_P53_CD_members.xlsx'
    sectors  = [float(i) for i in range(0,359,15)] 
    
    # Extract file for all DEM sums per geo, per elevation
    DEM_data_path = fr'{os.getcwd()}\output\python_combined_DEM.xlsx'
    df_DEM_members_xlsx = pd.read_excel(DEM_data_path)

    # Define DEM and utilization variables
    T_lifetime = 25.75 # 27.08
    N_equivalent = 1e7
    wohler_exp = 5.0
    DFF = 3.0
    
    # Load geometries of interest
    geometries_of_interest_df = pd.read_excel(fr'{os.getcwd()}\unused\marius\DA_P53_CD_all.xlsx')
    geometries_of_interest_df['gritblast'] = geometries_of_interest_df['gritblast'].fillna(1.0)
    geometries_of_interest_df['scf'] = geometries_of_interest_df['scf'].fillna(1.0)
    
    # Create geometries with pre-calculated A, I, Z, alpha etc
    geometries_of_interest = create_geo_matrix(geometries_of_interest_df, sectors)
    
    # Calculate the DEM of all member elevations, to be used for interpolation
    member_elevations = np.array([float(key) for key in (df_DEM_members_xlsx['mLat'].values)])
    weighted_DEM_sums_per_elevation = np.array( [df_DEM_members_xlsx.iloc[idx][1:] for idx, _ in enumerate(member_elevations)]) # 1: needed to not bring on mLat col also
    DEM_tot_all_members_all_angles = ((T_lifetime / N_equivalent * weighted_DEM_sums_per_elevation )**(1 / wohler_exp))
    
    
    df = pd.DataFrame(pd.DataFrame(geometries_of_interest)).T
    df = df[df['elevation'] >= member_elevations.min()] # we cannot interpolate locations below the seabed
    
    logger.info(f'Manipulating result df of shape {df.shape}')
    df['geo'] = df.apply(lambda row: geometries_of_interest[row.name], axis=1)
    df['dist_to_members'] = df.apply(lambda row: member_elevations - row['elevation'], axis=1)
    df['idx_above'] = df.apply(lambda row: np.ma.MaskedArray(row['dist_to_members'], row['dist_to_members'] < 0.0).argmin(), axis=1)
    df['idx_below'] = df.apply(lambda row: np.ma.MaskedArray(row['dist_to_members'], row['dist_to_members'] >= 0.0).argmax(), axis=1)
    df['idx_closest'] = df.apply(lambda row: np.abs(row['dist_to_members']).argmin(), axis=1)
    df['elevation_above'] = member_elevations[df['idx_above']]
    df['elevation_below'] = member_elevations[df['idx_below']]
    df['elevation_closest'] = member_elevations[df['idx_closest']]
    df['above_is_closest'] = df['elevation_closest'] > df['elevation']
    df['above_DEM_sums'] = df.apply(lambda row: np.array(df_DEM_members_xlsx.iloc[row['idx_above']][1:]), axis=1)
    df['below_DEM_sums'] = df.apply(lambda row: np.array(df_DEM_members_xlsx.iloc[row['idx_below']][1:]), axis=1)
    df['DEM_elevation_above'] = ((T_lifetime / N_equivalent * df['above_DEM_sums'])**(1 / wohler_exp))
    df['DEM_elevation_below'] = ((T_lifetime / N_equivalent * df['below_DEM_sums'])**(1 / wohler_exp))
    df['DEM_elevation_closest'] = df.apply(lambda row: row['DEM_elevation_above'] if row['above_is_closest'] else row['DEM_elevation_below'], axis=1)
    df['DEM_interpolated'] = df['DEM_elevation_below'] + (df['DEM_elevation_above'] - df['DEM_elevation_below']) * ( (df['elevation'] - df['elevation_below']) / (df['elevation_above'] - df['elevation_below']) )
    df['largest_DEM_hotspot_MNm'] = df.apply(lambda row: row['DEM_interpolated'].max() / 1e6, axis=1)
    df['largest_DEM_sector_idx'] = df.apply(lambda row: row['DEM_interpolated'].argmax(), axis=1)
    df['reference_sector_compass'] = df.apply(lambda row: global_2_compass(sectors[row['largest_DEM_sector_idx']]), axis=1)
    
    logger.info('Gathering pre calculated markov matrices from member elevations')
    markov_path = fr'{os.getcwd()}\output\total_markov_member' + '{}.npy'
    member_geometry = pd.read_excel(member_geometry_file_path)
    mbr_to_el_map = {k: v for k, v in zip(member_geometry['member_JLO'], member_geometry['elevation'])}
    markov_matrices = {}
    for mbr in mbr_to_el_map.keys():
        path = markov_path.format(mbr)
        member_elevation = mbr_to_el_map[mbr]
        logger.info(f'loading matrix for {member_elevation}')
        markov_matrices[member_elevation] = np.array(fastio_load(path))
    
    logger.info('Calculating utilization for all other elevations:')
    # choose worst or nearest sector as reference markov matrix
    # starting with worst: reason is that report, table E80, chooses 11.2mLat, 180degN as reference for 9.69mLat, 166.7degN, when actually 165 degN is closest. 
    logger.info('Collecting markov reference for closest elevations at worst sector')
    df['markov_reference'] = df.apply(lambda row: markov_matrices[row['elevation_closest']][row['largest_DEM_sector_idx']], axis=1)
    
    logger.info('Sorting markov reference by ascending moment range order')
    df['markov_reference'] = df.apply(lambda row: row['markov_reference'][ row['markov_reference'][:, 0].argsort() ], axis=1) # sort according to ascending moment ranges

    logger.info('Scale reference markov for hotspot')
    # Create markov ranges for the hotspots where the moment ranges has been scaled according to the DEM_scf / DEM_elevation_closest factor
    df['DEM_hotspot_vs_reference'] = df.apply(lambda row: row['DEM_interpolated'][row['largest_DEM_sector_idx']] / row['DEM_elevation_closest'][row['largest_DEM_sector_idx']], axis=1) 
    df['markov_hotspot'] = df.apply(lambda row: np.hstack( (row['markov_reference'][:, [0]] * row['DEM_hotspot_vs_reference'], row['markov_reference'][:, [1]])), axis=1)
    
    logger.info('Calculate stress')
    # Calculate nominal stress ranges, then calculate stress ranges with scf, alpha and grit blasting, and translate to MPa
    #df['stress_ranges_nominal'] = df.apply(lambda row: row['markov_hotspot'][:, [0]] * row['D'] / (2 * row['I']), axis=1)
    #df['stress_ranges_scaled'] = df.apply(lambda row: row['stress_ranges_nominal'] * row['scf'] * row['alpha'] * row['gritblast'], axis=1)
    
    df['stress_ranges_scaled'] = df.apply(lambda row: (row['markov_hotspot'][:, [0]] * row['D'] / (2 * row['I'])) * row['scf'] * row['alpha'] * row['gritblast'], axis=1)
    
    # create stress cycles made out of stress in MPa and counts over entire lifetime
    df['stress_cycles_MPa_lifetime'] = df.apply(lambda row: np.hstack( (row['stress_ranges_scaled'] / 1e6, row['markov_reference'][:, [1]] * T_lifetime)), axis=1)
    
    logger.info('Calculate utilization')
    # calculate utilization through miner sum with DFF
    df['rule_utilization'] = df.apply(lambda row: row['sn_curve'].miner_sum(row['stress_cycles_MPa_lifetime']) * DFF * 100, axis=1)

    logger.info('Saving out df')
    df_out = df[['elevation', 't', 'largest_DEM_hotspot_MNm', 'scf', 'gritblast', 'L_t', 't_eff', 'alpha',  'rule_utilization', 'in_place_utilization']].copy()
    del df
    df_out['util_diff'] = df_out['in_place_utilization'] - df_out['rule_utilization']
    df_out['util_fraction'] = df_out['rule_utilization'] / df_out['in_place_utilization']
    # df_out.loc[:, (df_out.columns != 'alpha') | (df_out.columns != 'gritblasting') | (df_out.columns != 'scf') | (df_out.columns != 'util_fraction')] = df_out.loc[:, (df_out.columns != 'alpha') | (df_out.columns != 'gritblasting') | (df_out.columns != 'scf') | (df_out.columns != 'util_fraction')].round(1)
    df_out.to_excel(os.path.join(os.getcwd(), ('\output\DA_P53_CD' + '_rule_vs_report' + '.xlsx')))
    print(df_out[ (df_out['util_fraction'] < 0.9) | (df_out['util_fraction'] > 1.0) ])
    logger.info('Utilization script finished')