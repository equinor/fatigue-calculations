import pandas as pd

def get_env_from_casefile(DLC_file_df, DLC_ID):
    return(DLC_file_df[['Nacelle angle [deg]', 'Wind Speed [m/s]',
                    'Wind Direction [deg]', 'Wave direction [deg]',
                    'Hs windsea [m]', 'Tp windsea [s]',
                    'Hs swell [m]', 'Tp swell [s]',
                    'Water Level [mMSL]',
                    'Current speed  (depth averaged) [m/s]', 'Current dir [deg]',
                    'Tot_Prob_in_10_percent_idling_scenario_hr_year' ]])

def create_fatigue_table_DLC_i(damage, dlc_id, probs, DLC_file_df): 
    
    damage_dict   = {f'dmg_sector_{sector_idx}': damage[:, sector_idx] for sector_idx in range(damage.shape[1])}
    df_damage     = pd.DataFrame(damage_dict)
    dlc_ids       = pd.DataFrame({'DLC': [dlc_id] * len(df_damage)})
    df_cases      = pd.DataFrame({'case_no': [i for i in range(damage.shape[0])]})
    df_case_specs = get_env_from_casefile(DLC_file_df, dlc_id) # TODO append!
    df_out        = pd.concat([dlc_ids, df_cases, df_case_specs, df_damage], axis = 1)     
    return df_out