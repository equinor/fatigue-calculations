import numpy as np
import pandas as pd
from read_simulation_file.read_simulation_file import read_bladed_file
import os

def get_moment_time_series(DLC_ID, cluster_ID, fatigue_config_file, results_folder_for_cluster, time_series_length):

    df = pd.read_excel(fatigue_config_file, sheet_name=DLC_ID)

    df =  df.assign(filenames = df.apply(lambda x: x['simulation_name'].replace('XXX', cluster_ID), axis = 1))
    df =  df.assign(results_files = df.apply(lambda x: os.path.join(results_folder_for_cluster +  x['path'], x['filenames']) + '.$105', axis = 1))
    df =  df.assign(descr_files = df.apply(lambda x: os.path.join(results_folder_for_cluster +  x['path'], x['filenames']) + '.%105', axis = 1))

    probs = list(df.Tot_Prob_in_10_percent_idling_scenario_hr_year)
    thetas = list(np.deg2rad(range(0,359,15)))

    moments_all_cases = np.zeros((df.shape[0], len(thetas), time_series_length))

    for index, (bin_file, text_file) in enumerate(zip(df.results_files, df.descr_files)):
        content_reshaped = read_bladed_file(bin_file, text_file)

        moment_x = content_reshaped[0,:]
        moment_y = content_reshaped[1,:]
        moments = [np.sin(theta)*moment_x+np.cos(theta)*moment_y for theta in thetas]
        moments_all_cases[index, :, :] = moments

    return moments_all_cases, probs