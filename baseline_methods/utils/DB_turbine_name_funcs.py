import re
from natsort import natsorted

def return_turbine_name_from_path(path):
        search_result = re.search(r'\w\w_\w\d\d_\w\w', path) # surch for the DB turbine name pattern
        return search_result.group() if search_result is not None else path 

def return_cluster_name_from_path(path):
        search_result = re.search(r'JL\w', path) # surch for the DB turbine name pattern
        return search_result.group() if search_result is not None else path 

def sort_paths_according_to_turbine_names(paths):
    return natsorted(paths, key = return_turbine_name_from_path)  