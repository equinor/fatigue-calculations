from utils.save_damage_table import load_damage_table
import numpy as np

path = r'C:\Appl\TDI\getting_started\fatpack_test\fatigue_table\fatigue_DB_JLO_DLC12_fatpack_multiprocessed.mat'
DLC_IDs = ['DLC12'] #, 'DLC64a', 'DLC64b', 'DLC24a', 'DLC31', 'DLC41a', 'DLC41b']

if __name__ == '__main__':
    
    total_damage = []
    
    for DLC_ID in DLC_IDs:
        path = rf'C:\Appl\TDI\getting_started\fatpack_test\fatigue_table\fatigue_DB_JLO_{DLC_ID}_fatpack_multiprocessed.mat'
        damage, combined_damage, weights = load_damage_table(path)
        
        if len(total_damage) == 0:
            n_geo, n_angles= combined_damage.shape
            total_damage = np.zeros((n_geo, n_angles))
        
        for geo_idx in range(n_geo):
            total_damage[[geo_idx], :] += combined_damage[geo_idx, :]
           
    print(1 / total_damage) 
        