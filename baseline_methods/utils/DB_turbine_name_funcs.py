import re
from natsort import natsorted

def return_turbine_name_from_path(path):
    """Search for and return the turbine name matching the DBA turbine naming format. If not found, the input is returned in its entirety 

    Args:
            path (str): Absolute path to the file in question

    Returns:
            str: Turbine name
    """
    search_result = re.search(r'\w\w_\w\d\d_\w\w', path) # search for the DB turbine name pattern
    return search_result.group() if search_result is not None else path 

def return_cluster_name_from_path(path):
    """Search for and return the cluster name matching the DBA ILA3 cluster naming format. If not found, the input is returned in its entirety 

    Args:
            path (str): Absolute path to the file in question

    Returns:
            str: Cluster name
    """
    search_result = re.search(r'JL\w', path) # search for the DB turbine name pattern
    return search_result.group() if search_result is not None else path 

def sort_paths_according_to_turbine_names(paths):
    """Takes a list of paths to some turbine data, and sort the paths naturally according to the turbine names

    Args:
        paths (list): Of paths represented as r-strings

    Returns:
        list: List of sorted paths of type r-strings
    """
        
    return natsorted(paths, key = return_turbine_name_from_path)  