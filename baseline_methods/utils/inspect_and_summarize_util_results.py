import pandas as pd
import numpy as np 
import os 
import sys

'''
Script for inspecting the RULe utilization results

Meant to be run from parent folder
'''

if __name__ == '__main__':
    
    turbine_output_dir  = os.path.join(os.getcwd(), "output", "all_turbines")
    info_from_reports_paths = [os.path.join(path, name) for path, subdirs, files in os.walk(turbine_output_dir) for name in files if 'geos_from_structure_report' in name]
    pd.options.display.max_rows = 500 # Print more rows

    # reported total util results
    max_dtot = []
    for path in info_from_reports_paths:
        file = pd.read_excel(path)
        file = file[ file['Dd_tot'] != '-']
        res = pd.DataFrame(file.iloc[[pd.to_numeric(file['Dd_tot']).argmax()]])
        res = res[['turbine_name', 'cluster', 'elevation', 'in_out', 'description', 'Dd_tot']].copy()
        res.rename(columns = {"elevation": "el_Ddtot", "in_out": "io_Ddtot", "description" : "desc_Ddtot", "Dd_tot": 'util_Ddtot'}, inplace = True)
        max_dtot.append(res.squeeze())
    
    df_reported_Ddtot = pd.DataFrame(max_dtot)
    
    # reported inplace results
    max_inplace = []
    for path in info_from_reports_paths:
        file = pd.read_excel(path)
        file = file[ file['in_place_utilization'] != '-']
        res = pd.DataFrame( file.iloc[ [pd.to_numeric(file['in_place_utilization']).argmax()] ])
        res = res[["turbine_name", "cluster", 'elevation', 'in_out', 'description', 'in_place_utilization']].copy()
        res.rename(columns = {"elevation": "el_inplace", "in_out": "io_inplace", "description" : "desc_inplace", "in_place_utilization": 'util_inplace'}, inplace = True)
        max_inplace.append(res.squeeze())
    
    df_reported_inplace = pd.DataFrame(max_inplace)
    
    # RULe results
    report_vs_rule_comparison_paths = [os.path.join(path, name) for path, subdirs, files in os.walk(turbine_output_dir) for name in files if 'worst_elevation_comparison' in name]
    comparison_results = []
    for file in report_vs_rule_comparison_paths:
        res = pd.read_excel(file).iloc[[0]] # the worst elevation comparison simply contains one row of information
        res = res[['turbine_name', "cluster", 'rule_worst_elevation', 'rule_worst_in_out', 'rule_worst_description',  'rule_worst_utilization']].copy()
        res.rename(columns = {"rule_worst_elevation": "el_rule", "rule_worst_in_out": "io_rule", "rule_worst_description" : "desc_rule", "rule_worst_utilization": 'util_rule'}, inplace = True)
        
        #res = res[['turbine_name', "cluster", 'rule_worst_elevation', 'rule_worst_description', 'rule_worst_utilization']].copy()
        #res.rename(columns = {"elevation": "elevation_rule", "description" : "desc_rule", "rule_worst_utilization": 'util_rule'}, inplace = True)
        comparison_results.append(res.squeeze())
        
    df_comparison = pd.DataFrame(comparison_results)
    
    # Concatenate into one table. Turbine name and cluster is confirmed to be the same along all rows for all reported values, 
    # so we just use the first df for turbine name and cluster info
    
    df_reported_Ddtot.reset_index(drop=True, inplace=True)
    
    df_reported_inplace.reset_index(drop=True, inplace=True)
    df_reported_inplace.drop(columns={"turbine_name", "cluster"}, inplace=True)
    
    df_comparison.reset_index(drop=True, inplace=True)
    df_comparison.drop(columns={"turbine_name", "cluster"}, inplace=True)
    
    df_out = pd.concat( [df_reported_Ddtot, df_reported_inplace, df_comparison], axis=1) 
    print(df_out) 
    
    out_path = os.path.join(turbine_output_dir, "utilization_summary_worst_points_Ddtot_vs_inplace_vs_rule.xlsx")
    df_out.to_excel(out_path, index=False)
    print(f"Stored util summary to {out_path}")