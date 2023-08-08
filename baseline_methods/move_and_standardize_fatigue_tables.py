import shutil
import os
from utils.DB_turbine_name_funcs import sort_paths_according_to_turbine_names, return_turbine_name_from_path
from lifetime_calculation_from_lookup import filter_paths_based_on_subseabed_scaling

'''
Script for moving the correct lookup tables from the various directories to the blob storage, with a formatted naming according to alle the other paths as well
This is supposed to be run as the very last script
To be run from the baseline_methods parent dir!
'''

if __name__ == "__main__":    
        
    # Source path
    turbine_output_dir = os.path.join(os.getcwd(), "output", "all_turbines")
    json_lookup_table_paths = [os.path.join(path, name) for path, subdirs, files in os.walk(turbine_output_dir) for name in files if (('lookup_table' in name) and ('json') in name)]
    json_lookup_table_paths = sort_paths_according_to_turbine_names(json_lookup_table_paths)
    json_lookup_table_paths = filter_paths_based_on_subseabed_scaling(json_lookup_table_paths)
    turbine_names = [return_turbine_name_from_path(p) for p in json_lookup_table_paths]
    
    # Destination path
    destination_dir = os.path.join(os.getcwd(), "output", "blob")
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
        
    destination_key = "fatigue_damage_all_dlcs_scaled_DBA_{}.json"
    
    # Copy the content of source to destination
    for lookup_path, turbine_name in zip(json_lookup_table_paths, turbine_names):
        try:
            shutil.copy2(lookup_path, os.path.join( destination_dir, destination_key.format(turbine_name))) # copy2() instead of copy() to preserve metadata
            print(f"{turbine_name} lookup_table copied to blob successfully.")
        
        except:
            print("Something wrong happened")