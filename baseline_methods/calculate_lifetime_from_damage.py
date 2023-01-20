from utils.IO_handler import load_table
import numpy as np
import pandas as pd 
import sys
import os

'''
Script for calculating lifetime of a turbine's most dimensioning sector damage
'''

DLC_IDs   = ['DLC12', 'DLC64a', 'DLC64b', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b']
DFF       = 3.0
data_path = fr'{os.getcwd()}\data'
DLC_file  = data_path +  r'\Doc-0081164-HAL-X-13MW-DGB-A-OWF-Detailed DLC List-Fatigue Support Structure Load Assessment_Rev7.0.xlsx'
   
def get_env_from_casefile(casefile, DLC_ID):    
    case_df = pd.read_excel(casefile, sheet_name=DLC_ID)
    return case_df[['Nacelle angle [deg]', 'Wind Speed [m/s]', 'Wind Direction [deg]', 'Wave direction [deg]',  'Hs windsea [m]', 'Tp windsea [s]', 'Hs swell [m]', 'Tp swell [s]', 'Water Level [mMSL]', 'Current speed  (depth averaged) [m/s]', 'Current dir [deg]', 'Tot_Prob_in_10_percent_idling_scenario_hr_year' ]]

def create_fatigue_table(damage, casefile, dlc_id): 

    df_env = get_env_from_casefile(casefile, dlc_id)
    damage_dict = {}
    for j in range(damage.shape[1]):
            damage_dict['fatigue_damage_sector_' + str(j+1)] = damage[:,j]

    df_damage = pd.DataFrame(damage_dict, columns = damage_dict.keys())
    dlc_ids = pd.DataFrame([dlc_id]*len(df_damage), columns = ['DLC'])
    df_out = pd.concat([df_env, dlc_ids, df_damage], axis=1)     
    return df_out

def calculate_lifetimes(identifier = 'damage', method = 'python'):
    
    print(f'Calculating lifetimes from {identifier} calculations done by the {method} method')
    total_damage = []
    paths = {'python': (fr'{os.getcwd()}' + r'\output\damage_DB_JLO_{}.mat') if identifier == 'damage' else (fr'{os.getcwd()}' + r'\output\DEM_DB_JLO_{}.mat'), 
             'matlab': (fr'{os.getcwd()}' + r'\output\fatigue_DB_JLO_{}.mat')}
    
    for DLC_ID in DLC_IDs:
        path = paths[method].format(DLC_ID)
        damage, combined_damage, weights = load_table(path, identifier = identifier, method = method)
        
        if method == 'matlab':
            # Matlab method already has DFF = 3 multiplied into it. 
            # damage /= DFF
            # combined_damage /= DFF
            pass # NOTE I have removed it in the MATLAB script for now, but keeping this in case MATLAB script gets reverted
            
        if len(total_damage) == 0:
            n_geo, n_angles = combined_damage.shape
            total_damage = np.zeros((n_geo, n_angles))
        
        for geo_idx in range(n_geo):
            total_damage[[geo_idx], :] += combined_damage[geo_idx, :] # the DFF was multiplied here
           
    lifetimes = (1 / (total_damage * DFF)) # moved DFF here
    return lifetimes
    
def create_overall_lookuptable():
    lifetimes = calculate_lifetimes()
    worst_elevation_idx = divmod(lifetimes.argmin(), lifetimes.shape[1])[0] # Finds the row idx of the row containing the element with the lowest value of entire array
    fatigue_data_all_dlcs = {}
    df_all_dlcs = []
    
    for DLC_ID in DLC_IDs:
        path = rf'{os.get_cwd()}\output\damage_DB_JLO_{DLC_ID}.mat'
        damage, combined_damage, weights = load_table(path)
        
        fatigue_data_all_dlcs[DLC_ID] = {}
        fatigue_data_all_dlcs[DLC_ID]['damage_10min'] = damage[:, worst_elevation_idx, :]
        
        df_all_dlcs.append(create_fatigue_table(
                                            fatigue_data_all_dlcs[DLC_ID]['damage_10min'], 
                                            DLC_file, 
                                            DLC_ID
                                            ))
        

    df_concatted = pd.concat(df_all_dlcs, axis=0) 
    df_concatted.reset_index(inplace=True, drop=True)
    print(df_concatted)

if __name__ == '__main__':
    
    lifetimes = calculate_lifetimes(method='python', identifier='damage')
    print(lifetimes)
    print(f'Minimum lifetime: {lifetimes.min():.2f} years')
    
    lifetimes = calculate_lifetimes(method='matlab')
    print(lifetimes)
    print(f'Minimum lifetime: {lifetimes.min():.2f} years')
    
    # create_overall_lookuptable()