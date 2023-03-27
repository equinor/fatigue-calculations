from utils.extract_and_preprocess_data import extract_and_preprocess_data
from utils.setup_custom_logger import setup_custom_logger
from utils.IO_handler import store_table
from utils.create_geo_matrix import create_geo_matrix
from utils.rainflow_methods import get_range_and_count_qats
from utils.calculate_damage_case_i import calculate_damage_case_i
from utils.calculate_DEM_case_i import calculate_DEM_case_i
import numpy as np
import pandas as pd
from multiprocessing import Pool
import os

'''
Implementation of in-place damage and DEM calculation of the Dogger Bank wind turbines

- Use the 10 minute timeseries from vendor simulations to extract forces and moments
- Calculate the resulting axial force and bending moments on the relevant sectors of the intersection at the desired elevation on the structure -> we call these a geometry
- Translate the forces and moments into stress timeseries
- Use rainflow counting to extract the stress cycles that are present in the stress time series
- Use the stress cycles together with an SN curve and calculate the linear accumulated damage with the Palmgren-Miner rule to get total damage 
- This damage can be stored as a binary file and used for lifetime calculations etc. 
'''
def create_dir_if_not_existing(dir):
    if not os.path.exists(dir):
        print(f'Did not find dir {dir}. Creating the dir.')
        os.makedirs(dir)

def check_and_retrieve_output_dirs(cluster):
    """Checks the output dir of the main scripts to see if they exist from previous runs.
    If not, it creates all necessary dirs for running the main.py script.
    It returns the base directory and the deepest directory of the output dir structure

    Args:
        cluster (str): DBA cluster name

    Returns:
        str, str: paths to base output dir and the markov cycle storage dir
    """
    dirs = [os.path.join(os.getcwd(), "output"), 
            os.path.join(os.getcwd(), "output", "all_turbines"), 
            os.path.join(os.getcwd(), "output", "all_turbines", f"{cluster}"), 
            os.path.join(os.getcwd(), "output", "all_turbines", f"{cluster}", "markov")
            ]
    
    for dir in dirs:
        create_dir_if_not_existing(dir)

    return dirs[0], dirs[-1]

def calc_unweighted_values(args, n_cases, output_table = [], multiprocess = True, calc_func = calculate_DEM_case_i,):
    """Calculates DEM or damage based on the calc func, without weighting it according to case probabilities

    Args:
        args (tuple): tuple of arguments to the Pool.starmap
        n_cases (int): number of cases
        output_table (list, optional): Defaults to [].
        multiprocess (bool, optional): Defaults to True.
        calc_func (func, optional): calculation function of DEM or damage. Defaults to calculate_DEM_case_i.

    Returns:
        np.ndarray: of size n_cases, n_geometries, n_sectors. contains damage or internal DEM sum for each of the combinations
    """
    
    if multiprocess:
        with Pool() as p: # loop all cases multiprocessed across available CPUs 
            outputs = p.starmap(calc_func, args) # returns a list of damages/DEM of len = n_cases 
        output_table = np.array(outputs)
        
    else:
        assert len(output_table) > 0, 'output table must be pre-initialiazed when running single CPU code'
        for case_i in range(n_cases):
            output_table[[case_i], :, :] = calc_func(*args[case_i])
    
    return output_table # (n_cases, n_geos, n_sectors)

def calculate_all_DEM_sums(clusters = ['JLN', 'JLO', 'JLP'], multiprocess = True):
    """Calculate the internal DEM sums, to be used in the overall DEM formula when all DEMs for all DLCs has been concatenated
    The results are stored, not returned.

    Args:
        clusters (list, optional): list of str with cluster names. Defaults to ['JLN', 'JLO', 'JLP'].
        multiprocess (bool, optional): Defaults to True.

    Returns:
        None: None
    """
    logger = setup_custom_logger('DEM')
    logger.info(f'Initiating Dogger Bank DEM sum calculations for clusters {clusters}')
    
    for cluster in clusters:
        logger.info(f'Processing cluster {cluster}')
        _ = main_calculation_of_DEM_or_damage_cluster_i(cluster = cluster, logger = logger, multiprocess = multiprocess, DEM = True)
        
    logger.info(f'Finished Dogger Bank DEM sum calculations for clusters {clusters}')
    return None

def calculate_10_min_damages(clusters = ['JLN', 'JLO', 'JLP'], multiprocess = True):
    """Calculates damages per 10 min instead of DEM.
    NOTE that this only works for elevations exactly where we have moment time series results!
    This means that running this code for elevations other than the members / nodes does not make any sense.
    For those elevations, the entire codebase must be run in order to use rainflow counting and DEM interpolation for estimating utiliation and damage calculation

    Args:
        clusters (list, optional): list of clusters to computer over. Defaults to ['JLN', 'JLO', 'JLP'].
        multiprocess (bool, optional): switch deciding to multiprocess over all cases. Defaults to True.

    Returns:
        None: None
    """
    logger = setup_custom_logger('damage')
    logger.info(f'Initiating Dogger Bank damage calculations for clusters {clusters}')
    
    for cluster in clusters:
        logger.info(f'Processing cluster {cluster}')
        _ = main_calculation_of_DEM_or_damage_cluster_i(cluster = cluster, logger = logger, multiprocess = multiprocess, DEM = False, TEN_MIN_TO_HR = 1.0)
    
    logger.info(f'Finished Dogger Bank damage calculations for clusters {clusters}')
    return None

def main_calculation_of_DEM_or_damage_cluster_i(cluster, logger, multiprocess = True, DEM = True, TEN_MIN_TO_HR = 6.0):
    """The main script of calculating all internal DEM sums or 10 min damage of the member elevations

    Args:
        cluster (str): cluster name
        logger (logger): logger
        multiprocess (bool, optional): Defaults to True.
        DEM (bool, optional): True if DEM, False if damage. Defaults to True.
        TEN_MIN_TO_HR (float, optional): convertion from 10-min values to hourly values. Defaults to 6.0.

    Returns:
        None: None
    """
    
    store_cycles   = True # store rainflow cycles in DEM calculations
    info_str       = "DEM" if DEM else "damage"
    calc_func      = calculate_DEM_case_i if DEM else calculate_damage_case_i
    sectors        = [float(i) for i in range(0,359,15)] # evenly distributed angles in the turbine frame
    DLC_IDs        = ['DLC12', 'DLC24a',  'DLC31', 'DLC41a', 'DLC41b', 'DLC64a', 'DLC64b']
    DEM_CORRECTION = 1.01 # 1 percent increase in all moment cycles due to lifetime of tower without, not accounted for in the moment time series from GE which was calculated over ~25 years of production
    
    # Get relevant data_paths for DLC and simulation result files  
    data_path              = os.path.join(os.getcwd(), 'data')
    DLC_file_path          = os.path.join(data_path, f'Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx')
    simulation_result_dir  = os.path.join(data_path, f'Doc-0089427-HAL-X-13MW DB-A OWF-ILA3_{cluster}-model_fatigue_timeseries_all_elevations')
    member_geometries_path = os.path.join(data_path, f'{cluster}_member_geos.xlsx')
    
    geometry     = pd.read_excel(member_geometries_path)
    n_geometries = geometry.shape[0]
    geo_matrix   = create_geo_matrix(geometry, sectors) # summary of the geometric properties. Note that when reading from Excel file, MacOS needs the file to be saved in order to run formulas that shall be read as numbers in Python. 

    out_dir, cycles_dir = check_and_retrieve_output_dirs(cluster)
    
    elevations = [f'{geo_matrix[i]["elevation"]} mLAT' for i in range(len(geo_matrix))]
    status_string = f'Processing {"multiprocessed" if multiprocess else "single CPU"} {info_str} calculation\nDLCs {DLC_IDs}\n{n_geometries} elevations: {elevations}'
    logger.info(status_string)
        
    for DLC in DLC_IDs:
        # Collect relevant DLC data, find the probabilities of occurence of each case and the number of cases
        df, probs, n_cases, _ = extract_and_preprocess_data(DLC_file_path, DLC, cluster, simulation_result_dir)
        cycle_storage_path    = os.path.join(cycles_dir, f"DB_{cluster}_{DLC}")
        create_dir_if_not_existing(cycle_storage_path)
        cycle_storage_path    = os.path.join(cycle_storage_path, "cycles_member{}")
        output_file_name      = os.path.join(out_dir, "all_turbines", cluster, f"DB_{cluster}_{DLC}_{info_str}.mat")
        summary_table_DLC_i   = np.zeros((n_cases, n_geometries, len(sectors))) # pre-allocate output matrix of the current DLC
        
        logger.info(f'Starting {info_str} calculation on {cluster} {DLC} with {n_cases} cases')
        
        arguments = [(df.results_files[i], 
                      df.descr_files[i], 
                      sectors,
                      geo_matrix,
                      get_range_and_count_qats,
                      DEM_CORRECTION,
                      store_cycles,
                      cycle_storage_path + f'_case{i}.npy'
                     ) for i in range(n_cases)]
        
        summary_table_DLC_i = calc_unweighted_values(multiprocess = multiprocess, 
                                                     calc_func    = calc_func, 
                                                     output_table = summary_table_DLC_i, 
                                                     args         = arguments, 
                                                     n_cases      = n_cases)
        
        logger.info(f'Finished calculating {info_str} for {cluster} - initiating probability weighting and file storage')
        
        # Transform output to a combined damage / DEM matrix of size (n_geo, n_sectors), weighting cases by their probabilities,
        weighted_table_DLC_i = np.zeros((n_geometries, len(sectors)))
        weights = np.array([probs])
        for sector_idx in range(len(sectors)):
            # convert to hour-based values according to "TEN_MIN_TO_HR". Might be == 1 if using 10-min based values
            weighted_table_DLC_i[:, [sector_idx]] = np.dot(weights, summary_table_DLC_i[:,:, sector_idx]).T * TEN_MIN_TO_HR  # (n_geometries, 1) -> multiplication of weights by dot product
        
        store_table(summary_table_DLC_i, 
                    weighted_table_DLC_i, 
                    weights, 
                    output_file_name, 
                    identifier = info_str)
        
        logger.info(f'Stored {info_str} table for {cluster} {DLC} \n')
        
    logger.info(f'Main calculation script finished for cluster {cluster}')
    return None

if __name__ == '__main__':
    
    _ = calculate_all_DEM_sums(multiprocess = True)