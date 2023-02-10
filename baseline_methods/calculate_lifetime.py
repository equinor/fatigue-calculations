import os 
from utils.IO_handler import load_table
import pandas as pd 
import numpy as np 

'''
Used for inspecting the damage calculations, to see min lifetime
'''

def calculate_lifetime_from_fatigue_lookup_table(df):
    # Assumes damage has been calculated with DFF already
    
    probability_hr_per_yr = df['probs'].to_numpy()
    unweighted_dmg_pr_yr  = df.filter(regex = 'dmg').to_numpy() * 6.0 # array of n_cases, n_sectors -> # six 10-min periods in one hr
    weighted_dmg_pr_yr    = probability_hr_per_yr[:, None] * unweighted_dmg_pr_yr # elementwise multiplication along all rows of the damage-array
    yearly_damage_per_sector = weighted_dmg_pr_yr.sum(axis = 0) # summation of all yearly weighted damages for all DLCs, sectorwise; axis=0
    return 1.0 / yearly_damage_per_sector

if __name__ == '__main__':
    
    turbine_name = 'DA_P53_CD'
    df = pd.read_excel(fr'{os.getcwd()}\output\lookup_table_{turbine_name}.xlsx')
    lifetimes = calculate_lifetime_from_fatigue_lookup_table(df)
    print(lifetimes)
    print(f'Lifetime at limiting sector for {turbine_name} = {lifetimes.min():.2f} years')
    