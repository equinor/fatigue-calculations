import numpy as np
import sys
import pandas as pd
import swifter # can replace 'df.apply' with 'df.swifter.apply' which should improve speed on vectorizable functions. has more overhead than worth it on smaller functions
import os
from utils.create_geo_matrix import create_geo_matrix
from utils.fastnumpyio import load as fastio_load 
from utils.transformations import global_2_compass
from utils.setup_custom_logger import setup_custom_logger
from read_structural_report import read_utilization_and_store_geometries
from multiprocessing import Pool

def find_above_below_closest_elevations(df, member_elevations):
    df['dist_to_members'] = df.apply(lambda row: member_elevations - row['elevation'], axis=1)
    df['idx_elevation_above'] = df.apply(lambda row: np.ma.MaskedArray(row['dist_to_members'], row['dist_to_members'] < 0.0).argmin(), axis=1)
    df['idx_elevation_below'] = df.apply(lambda row: np.ma.MaskedArray(row['dist_to_members'], row['dist_to_members'] >= 0.0).argmax(), axis=1)
    df['idx_elevation_closest'] = df.apply(lambda row: np.abs(row['dist_to_members']).argmin(), axis=1)
    return member_elevations[df['idx_elevation_above']],  member_elevations[df['idx_elevation_below']], member_elevations[df['idx_elevation_closest']]

def return_worst_elevation(df):
    # find the elevation that the report evaluates as the one with highest utilization
    # manipulate dataframe columns to be readable in standalone
    # Then, compare it to RULe numbers:
    #   1) compare report value to the rule results at the same elevation
    #   2) calculate the elevations that the rule method evaluates as the worst wrt utilization
    # Both these metrics should match the reports'
    
    # get the row with the worst elevation according to the report
    df['in_place_utilization'] = df['in_place_utilization'].astype(float)
    report_worst_elevation_idx = df['in_place_utilization'].argmax()
    
    df_res = df.iloc[[report_worst_elevation_idx]].copy()   
    df_res = df_res[ ['turbine_name', 'cluster', 'description', 'elevation', 'in_out', 'in_place_utilization'] ].copy()
    
    df_res.rename(columns = {'description': 'reported_worst_description',
                             'elevation'  : 'reported_worst_description',
                             'in_place_utilization': 'reported_utilization'}, inplace = True)
    
    # calculate the rule utilization at this elevation 
    all_rule_utilizations = (df['rule_miner_sum_no_DFF'] * df['rule_DFF'] * 100).copy()
    df_res['rule_util_at_reported_elevation'] = all_rule_utilizations[report_worst_elevation_idx]
    
    # find the elevation and utilization that the RULe method believes is the worst (should be the same)
    rule_worst_elevation_idx = all_rule_utilizations.argmax()
    df_res['rule_worst_description'] = df.iloc[rule_worst_elevation_idx]['description']
    df_res['rule_worst_elevation'] = df.iloc[rule_worst_elevation_idx]['elevation']
    df_res['rule_worst_utilization'] = all_rule_utilizations.iloc[rule_worst_elevation_idx]
    
    return df_res

def handle_DFFs(DFFs, n_elevations):
    # the DFF can be given as a list, in order to possible change this at a later stage
    # DFF list must match the length of elevations used in the design reports   
     
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
    
    return DFFs

def calculate_utilization_single_turbine(util_and_geo_path, 
                                         member_path,
                                         DEM_data_path,
                                         member_markov_path,
                                         result_path,
                                         logger,
                                         DFFs: list,
                                         single_cluster = False):

    
    sectors = [float(i) for i in range(0,359,15)]

    # Define DEM variables
    wohler_exp = 5.0
    
    # Load geometries of interest TODO temp solution for when testing the read_pdf-file and this util-script separately - the main code is based on running both script, but the read_pdf output can be directly gathered 
    geometries_of_interest_df = pd.read_excel(util_and_geo_path)
    turbine_name = geometries_of_interest_df.iloc[0]['turbine_name']
    cluster = geometries_of_interest_df.iloc[0]['cluster']
    
    # TODO temporary before all timeseries' has been processed for the other clusters
    if single_cluster:
        if cluster != single_cluster:
            print(f'{turbine_name} not in single cluster {single_cluster} - skipping')
            return None
    
    member_geometry = pd.read_excel(member_path.format(cluster))
    df_DEM_members_xlsx = pd.read_excel(DEM_data_path.format(cluster, cluster))
    
    member_2_elevation_map = {k: v for k, v in zip(member_geometry[f'member_id'], member_geometry['elevation'])}
    
    # Create geometries with pre-calculated A, I, Z, alpha etc
    geometries_of_interest = create_geo_matrix(geometries_of_interest_df, sectors)
    
    # Calculate the DEM of all member elevations, to be used for interpolation
    member_elevations = np.array([float(key) for key in (df_DEM_members_xlsx['mLat'].values)])
    
    df = pd.DataFrame(pd.DataFrame(geometries_of_interest)).T
    df = df[df['elevation'] >= member_elevations.min()] # we cannot interpolate locations below the lowest member elevation with available time series
    
    DFFs = handle_DFFs(DFFs, df.shape[0])
   
    logger.info(f'Manipulating main dataframe for {cluster}, turbine {turbine_name}')
    # Find the geo properties, closest member elevations and DEM values, and interpolate 
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
    
    # Find the corresponding DEM at hotspot, and the DEM scaling factor relative to the closest elevation + sector
    df['DEM_hs_MPa'] = df.apply(lambda row: row['DEM_interpolated'][row['closest_sector_idx']] / 1e6, axis=1)  
    df['DEM_scaling_factor'] = df.apply(lambda row: row['DEM_interpolated'][row['closest_sector_idx']] / row['DEM_elevation_closest'][row['closest_sector_idx']], axis=1)   
    
    # Gather pre calculated markov matrices from member elevations')
    markov_matrices = {}
    for mbr in member_2_elevation_map.keys():
        path = member_markov_path.format(cluster, mbr)
        member_elevation = member_2_elevation_map[mbr]
        print(f'loading matrix for {member_elevation}')
        markov_matrices[member_elevation] = np.array(fastio_load(path))
    
    # Calculate utilization for all other elevations
    
    # choose closest sector as reference markov matrix
    logger.info('Collecting markov reference for closest elevations at worst sector')
    df['markov_reference'] = df.apply(lambda row: markov_matrices[row['elevation_closest']][row['closest_sector_idx']], axis=1)
    
    # NOTE sorting could be beneficial to avoid rounding errors, but takes a lot of time
    #df['markov_reference'] = df.apply(lambda row: row['markov_reference'][ row['markov_reference'][:, 0].argsort() ], axis=1) # sort according to ascending moment ranges

    # Scale reference markov for hotspot: moment ranges scaled according to the DEM_scf / DEM_elevation_closest factor
    df['markov_hotspot'] = df.apply(lambda row: np.hstack( (row['markov_reference'][:, [0]] * row['DEM_scaling_factor'], row['markov_reference'][:, [1]])), axis=1)
    
    logger.info('Calculating stress ranges and damage')
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
    
    df = df[['elevation', 'in_out', 'description', 'D', 't', 
             'curve', 'DEM_hs_MPa', 'Seq', 'scf', 'gritblast',
             'Seq_hs', 'L_t', 't_eff', 'alpha', 'rule_miner_sum_no_DFF', 
             'rule_DFF', 'in_place_utilization', 'DEM_scaling_factor',
             'elevation_closest', 'closest_sector_idx', 'ValType', 'turbine_name', 'cluster']].copy()
    
    result_path = result_path + fr'\{cluster}\{turbine_name}'
    if not os.path.exists(result_path):
        os.makedirs(result_path)
    
    df_path = result_path + fr'\util_rule_vs_report.xlsx'
    df.to_excel(df_path, index = False)
    pd.options.display.max_rows = 100 # Print more rows
    print(df)
    
    df_res = return_worst_elevation(df)
    df_res_path = result_path + fr'\util_worst_elevation_comparison.xlsx'
    df_res.to_excel(df_res_path, index = False)
    
    return df, df_path, df_res, df_res_path 

def preprocess_structure_reports(preprocess_reports, structure_file_paths, preprocessed_dir, logger):
     
    preprosessed_structure_file_contents_paths = []
    
    if preprocess_reports:
        for filename in structure_file_paths:
            print('Reading', filename.split(' - ')[1])
            path = read_utilization_and_store_geometries(filename, preprocessed_dir)
            preprosessed_structure_file_contents_paths.append(path)
            
        logger.info('Read and preprocessed all structural reports and stored results')
    else: 
        # we do not want to pre-process reports -> find all files matching 
        try:
            # preprocess_files_names = next(os.walk(preprocessed_dir), (None, None, []))[2]
            all_files = [os.path.join(path, name) for path, subdirs, files in os.walk(preprocessed_dir) for name in files if 'utils_and_geos_from_structure_report' in name]
            preprosessed_structure_file_contents_paths = all_files
            # preprosessed_structure_file_contents_paths = [preprocessed_dir + fr'\{filename}' for filename in preprocess_files_names if 'utils_and_geos_from_structure_report' in filename ]
            logger.info('Read all already preprocessed and stored structural reports')
        except:
            logger.info('Error retrieving already preprocessed structural reports - exiting')
            sys.exit()
    
    return preprosessed_structure_file_contents_paths

def calculate_utilization_all_turbines( structure_file_paths, 
                                        preprosessed_structure_file_contents_paths, 
                                        member_geo_path,
                                        DEM_data_path,
                                        turbine_output_dir, 
                                        member_markov_path,
                                        logger,
                                        DFFs = [], 
                                        single_cluster = False):
    
    multiprocess = False
    # TODO mutliprocessed get access denied when trying to access the markov matrices
    
    '''
    File "C:\Appl\TDI\fatigue-calculations\baseline_methods\calculate_utilization.py", line 141, in calculate_utilization_single_turbine
        markov_matrices[member_elevation] = np.array(fastio_load(path))
    File "C:\Appl\TDI\fatigue-calculations\baseline_methods\utils\fastnumpyio.py", line 26, in load
        file=open(file,"rb")
    PermissionError: [Errno 13] Permission denied: 'C:\\Appl\\TDI\\fatigue-calculations\\baseline_methods\\output\\all_turbines'
    '''
        
    args = [(preprosessed_structure_file_contents_paths[i], 
             member_geo_path,
             DEM_data_path,
             turbine_output_dir, 
             member_markov_path,
             logger,
             DFFs, 
             single_cluster
            ) for i in range(len(structure_file_paths))]
    
    if multiprocess:
        logger.info(f'Calculating utilization for all turbines multiprocessed')
        with Pool() as p:
            _ = p.starmap(calculate_utilization_single_turbine, args)
    
    else:
        for i, filename in enumerate(structure_file_paths):
            logger.info(f'[{i}/{len(structure_file_paths)}] Calculating utilization for {filename.split(" - ")[1].split(" Foundation")[0]}')
            _ = calculate_utilization_single_turbine(*args[i])
            logger.info(f'[{i}/{len(structure_file_paths)}] Ended utilization script for turbine {filename.split(" - ")[1].split(" Foundation")[0]}')

if __name__ == '__main__':
    
    logger = setup_custom_logger('utilization')
       
    # extract directory with structure reports
    structural_file_dir = os.getcwd() + r'\data\structural_specific_reports'
    structure_file_names = next(os.walk(structural_file_dir), (None, None, []))[2]
    
    # ignore the spare "SL" turbines and generate paths to the structure reports
    structure_file_names = [filename for filename in structure_file_names if 'sl_' not in filename.lower()]
    structure_file_paths = [structural_file_dir + fr'\{filename}' for filename in structure_file_names]
    turbine_names = [filename.split(' ')[2] for filename in structure_file_names]
    single_cluster = False
    # prepare file paths with formatting for cluster ID and turbine name
    turbine_output_dir  = fr'{os.getcwd()}\output\all_turbines'
    member_geo_path     = fr'{os.getcwd()}\data' +  r'\{}_member_geos.xlsx' # format for cluster
    DEM_data_path       = turbine_output_dir + r'\{}\{}_combined_DEM.xlsx' # format for (cluster, cluster)
    member_markov_path  = turbine_output_dir + r'\{}\total_markov_member{}.npy' # format for (cluster, member_no)
    # geo_path          = fr'{os.getcwd()}\output' + r'\{}_util_and_geos.xlsx' # format for turbine_name
    
    logger.info('Reading all utils')
    
    preprocess_reports = False # can be set to false if we already have preprocessed the structural report files
    preprocessed_dir = os.getcwd() + r'\output\all_turbines'
    preprosessed_structure_file_contents_paths = preprocess_structure_reports(preprocess_reports, structure_file_paths, preprocessed_dir, logger)
    
    logger.info('Initiating utilization results')
    _ = calculate_utilization_all_turbines( structure_file_paths, 
                                            preprosessed_structure_file_contents_paths, 
                                            member_geo_path,
                                            DEM_data_path,
                                            turbine_output_dir, 
                                            member_markov_path,
                                            logger,
                                            DFFs = [], 
                                            single_cluster = single_cluster)

    logger.info('Utilization complete')
