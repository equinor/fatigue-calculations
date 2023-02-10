import pandas as pd
import numpy as np 
import os 

if __name__ == '__main__':
    

    df = pd.read_excel(fr'{os.getcwd()}\output\DA_P53_CD_rule_vs_report.xlsx')
    
    # df = df[ df['util_fraction'].abs() < 5.0] # remove outliers - there are some severe errors related to file reading etc.
    # df = df[ df['util_fraction'].abs() > 0.1] # remove those that are fairly close to only inspect 
    
    df['util_fraction'] *= 100.0
    util_far_away = (df['util_fraction']).abs() > 1.10 # over 10% off
    is_inside = (df['in_out'] == 'I') | (df['in_out'] == 'i')
    is_outside = ~is_inside
    above_sealevel = df['elevation'] >= 0.0
    below_sealevel = ~above_sealevel

    submerged = df[below_sealevel]
    in_air = df[above_sealevel]
    print(in_air)
    print(in_air['util_fraction'].mean(), in_air['util_fraction'].std())
    print(submerged)
    print(submerged['util_fraction'].mean(), submerged['util_fraction'].std())
    
    # print(df[ is_inside & util_far_away])
    # print(df[ (~is_inside) & util_far_away])