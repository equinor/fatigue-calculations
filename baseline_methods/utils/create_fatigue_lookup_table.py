import pandas as pd

# TODO there must be some logic here where the fatigue table contains weather params in order to linearly interpolate between weather scenarios

def create_fatigue_table_DLC_i(damage, dlc_id, probs): 
    damage_dict = {f'dmg_sector_{sector_idx}': damage[:, sector_idx] for sector_idx in range(damage.shape[1])}
    df_damage   = pd.DataFrame(damage_dict)
    df_cases    = pd.DataFrame({'case_no': [i for i in range(damage.shape[0])]})
    dlc_ids     = pd.DataFrame({'DLC': [dlc_id] * len(df_damage)})
    worst_idx   = pd.DataFrame({'probs': probs })
    df_out      = pd.concat([dlc_ids, df_cases, worst_idx, df_damage], axis=1)     
    return df_out