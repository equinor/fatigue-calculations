
import os 
import pandas as pd 
import sys
from utils.DB_turbine_name_funcs import sort_paths_according_to_turbine_names

'''
Script used for inspecting the various lifetimes and utilizations across all turbines
'''

def get_top_five_utilizations(result_output_dir, member_geo_path):
    
    info_from_reports_paths = [os.path.join(path, name) for path, subdirs, files in os.walk(result_output_dir) for name in files if 'geos_from_structure_report' in name]
    pd.options.display.max_rows = 500 # Print more rows
    
    res_dict = {'JLN': pd.DataFrame(), 'JLO': pd.DataFrame(), 'JLP': pd.DataFrame()}
    for path in info_from_reports_paths:
        df = pd.read_excel(path)
        df = df[ df['Dd_tot'] != '-']
        df['Dd_tot'] = pd.to_numeric( df['Dd_tot'] )
        df = df.sort_values('Dd_tot', ascending=False)
        res = df[['turbine_name', 'cluster', 'elevation', 'in_out', 'description', 'in_place_utilization', 'Dd_tot']]
        if res_dict[res['cluster'][0]].empty:
            res_dict[res['cluster'][0]] = res.head()
        else:
            res_dict[res['cluster'][0]] = pd.concat([res_dict[res['cluster'][0]], res.head()])
    
    for cluster in res_dict.keys():
        mbr_geo = pd.read_excel(member_geo_path.format(cluster))
        seabed_elevation = mbr_geo['elevation'].min()
        grouped_df = res_dict[cluster].groupby('turbine_name')
        for k, i in grouped_df:
            print(f'{cluster}: seabed = {seabed_elevation:.1f}')
            print(grouped_df.get_group(k))
        
    return None

def position_to_str(pos):
    if pos == 0:
        s = '1st'
    elif pos == 1:
        s = '2nd'
    elif pos == 2:
        s = '3rd'
    else:
        s = str(pos + 1) + 'th'
    return s

def inspect_details_of_largest_util(df):
    
    for i in range(df.shape[0]):
        row = df.iloc[[i]]
        
        if row['elevation'].iloc[0] <= seabed_elevation:
                print(f'{position_to_str(i)} largest util below seabed')
                print(row)
                
        elif 'free' in row['description'].iloc[0]:
            print(f'{position_to_str(i)} largest util at free corr')
            print(row)
            
        else:
            return None
        
    return None
         
if __name__ == '__main__':

    member_geo_path     = os.path.join(os.getcwd(), "data", "{}_member_geos.xlsx") # format for cluster
    result_output_dir   = os.path.join(os.getcwd(), "output", "all_turbines")
    info_from_reports_paths = sort_paths_according_to_turbine_names([os.path.join(path, name) for path, subdirs, files in os.walk(result_output_dir) for name in files if 'geos_from_structure_report' in name])
    pd.options.display.max_rows = 500 # Print more rows
    
    inspect_dtot = True
    store_worst = True # selector for storing the worst utils as Excel files. If False, we just inspect and print
    
    if inspect_dtot:
        
        res_dict = {'JLN': pd.DataFrame(), 'JLO': pd.DataFrame(), 'JLP': pd.DataFrame()}
        for path in info_from_reports_paths:
            df = pd.read_excel(path)
            df = df[ df['Dd_tot'] != '-']
            df['Dd_tot'] = pd.to_numeric( df['Dd_tot'] )
            df = df.sort_values('Dd_tot', ascending=False)
            res = df[['turbine_name', 'cluster', 'elevation', 'in_out', 'description', 'in_place_utilization', 'Dd_tot']].copy()
            res['lifetime'] = 27.08 / (res['Dd_tot'] / 100.0)
            if res_dict[res['cluster'][0]].empty:
                if store_worst:
                    res_dict[res['cluster'][0]] = res.iloc[[0]]
                else:
                    res_dict[res['cluster'][0]] = res.head()
            else:
                if store_worst:
                    res_dict[res['cluster'][0]] = pd.concat([res_dict[res['cluster'][0]], res.iloc[[0]]])
                else:
                    res_dict[res['cluster'][0]] = pd.concat([res_dict[res['cluster'][0]], res.head()])
        
        if store_worst:
            df_new = pd.DataFrame()
            for key in res_dict.keys():
                df_new = pd.concat([df_new, res_dict[key]])
            
            print(df)
            df_new.to_excel(os.path.join(result_output_dir, 'structural_report_Dd_tot_lifetimes.xlsx'), index=False)
            print('stored design report lifetimes based on TOTAL Dd_tot utilization')
        
        else:
            for cluster in res_dict.keys():
                mbr_geo = pd.read_excel(member_geo_path.format(cluster))
                seabed_elevation = mbr_geo['elevation'].min()
                grouped_df = res_dict[cluster].groupby('turbine_name')
                for k, i in grouped_df:
                    df_temp = grouped_df.get_group(k)
                    print(df_temp['turbine_name'].iloc[0])
                    inspect_details_of_largest_util(df_temp)
            
    else:
        # we look at in_place utilization instead of total utilization
        # difference is that now the double curved corrosion points are not added
        
        res_dict = {'JLN': pd.DataFrame(), 'JLO': pd.DataFrame(), 'JLP': pd.DataFrame()}
        for path in info_from_reports_paths:
            df = pd.read_excel(path)
            df = df[ df['in_place_utilization'] != '-']
            df['in_place_utilization'] = pd.to_numeric( df['in_place_utilization'] )
            df = df.sort_values('in_place_utilization', ascending = False)
            
            res = df[['turbine_name', 'cluster', 'elevation', 'in_out', 'description', 'in_place_utilization']].copy()
            res['lifetime'] = 27.08 / (res['in_place_utilization'] / 100.0)
            if res_dict[res['cluster'][0]].empty:
                res_dict[res['cluster'][0]] = res.iloc[[0]]
            else:
                res_dict[res['cluster'][0]] = pd.concat([res_dict[res['cluster'][0]], res.iloc[[0]]])
        
        df_new = pd.DataFrame()
        for key in res_dict.keys():
            df_new = pd.concat([df_new, res_dict[key]])
            
        print(df_new)
        
        if store_worst:
            df_new.to_excel(os.path.join(result_output_dir, 'structural_report_inplace_lifetimes.xlsx'), index=False)
            print('stored design report lifetimes based on in place utilization')