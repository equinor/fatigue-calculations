import pandas as pd
import numpy as np 
import os 

   
def calculate():

    df = pd.read_excel(fr'{os.getcwd()}\output\DA_P53_CD_rule_vs_report.xlsx')
    
    # df = df[ df['util_fraction'].abs() < 5.0] # remove outliers - there are some severe errors related to file reading etc.
    # df = df[ df['util_fraction'].abs() > 0.1] # remove those that are fairly close to only inspect 
    
    df = df[['elevation', 'in_out', 'description', 'D', 't', 'curve',
                 'DEM_hs_MPa', 'Seq', 'scf', 'gritblast', 'Seq_hs', 'L_t', 't_eff',
                'alpha', 'rule_miner_sum_no_DFF', 'rule_DFF', 'ValType', 'in_place_utilization']]
    
    df['rule_utilization'] = df['rule_miner_sum_no_DFF'] * df['rule_DFF'] * 100
    
    df = df.drop(['rule_miner_sum_no_DFF', 'rule_DFF'], axis=1)
    
    df['util_diff'] = df['rule_utilization'] - df['in_place_utilization']
    df['util_fraction'] = df['util_diff'] / df['in_place_utilization']
    df['util_fraction'] *= 100.0 # difference from report value in percentage
    
    util_far_away = (df['util_fraction']).abs() > 1.0    
    is_inside = (df['in_out'] == 'I') | (df['in_out'] == 'i')
    is_outside = ~is_inside
    
    print(df)
    print(df[ df['util_diff'].abs() > 2.0])
    print(df)
    print(df[ df['util_fraction'].abs() < 10.0])
    # print('Nothing')

if __name__ == '__main__':
    
    turbine_output_dir  = fr'{os.getcwd()}\output\all_turbines'
    all_files = [os.path.join(path, name) for path, subdirs, files in os.walk(turbine_output_dir) for name in files if 'worst_elevation_comparison' in name]
    
    comparison_results = []
    for file in all_files:
        res = pd.read_excel(file).iloc[0]
        comparison_results.append( res )
        
    df = pd.DataFrame(comparison_results)
    pd.options.display.max_rows = 500 # Print more rows
    print(df)