import os
import PyPDF2
import pandas as pd
import sys
import copy
import re
    
def identify_pages_with_key_word(file_path, key_word, start_page = 40, end_page = 50):
    # finds page 
    pages_found = -1
    pdf_reader = PyPDF2.PdfReader(file_path)
    end_page = min(len(pdf_reader.pages), end_page)
    assert start_page < end_page, 'the start pages cannot be after the end page'
    for i in range(start_page, end_page - 1):
        text = ''
        text += pdf_reader.pages[i].extract_text()
        content = text.encode('ascii', 'ignore').lower().decode("utf-8") 
        search_result = re.search(key_word, content)
        if search_result is not None:
            pages_found = i
            break
    
    return pages_found       
    
def get_text_as_lines_from_page(file_path: str, page_no: int, above_str_ID: str, below_str_ID: str, above_idx_is_at_element = False, add_word : str = None):
    # page no is no in document, not as python indexed int
    # note that 
    # TODO allow for info scraped from top sentence and bottom sentence
    
    # Open the PDF file and extract the text from the specified page
    # page no formatted as PDF-page no, not python 0-indexed
    pdf_reader = PyPDF2.PdfReader(file_path)
    page = pdf_reader.pages[page_no - 1] # 
    text = page.extract_text()
    lines = text.split('\n') # Split the text into lines
    
    above_idx, below_idx = 0, 0
    for i, str_line in enumerate(lines):
        if above_str_ID in str_line:
            above_idx = i
        if below_str_ID in str_line:
            below_idx = i

    if not above_idx_is_at_element: # allows for True if we want to grab the very first line on the page
        above_idx += 1
        
    if above_idx >= below_idx:
        print(f'Encountered below_idx idx equal to or smaller than above_idx. Getting text at single line no {above_idx}')
        below_idx = above_idx + 1
        
    lines = lines[above_idx: below_idx]
    
    if add_word:
        lines = [line + f' {add_word}' for line in lines]
        
    return lines

def clean_row_elements_with_spaces(row, start_idx):
    # Generalized formula for finding all neighbouring string columns from start_idx, concatenate / join them with string at start_idx, and remove the neighbours afterwards
    end_idx = copy.deepcopy(start_idx)
    while True:
        try: 
            # test to see if we have reached the neighbouring column with a number -> then we know that the strings with spaces has ended
            # if that is the case, replace the description with all strings found and delete the elements that is now a part of the new description
            _ = float(row[end_idx + 1]) 
            row[start_idx] = ' '.join( [row[i].replace(' ', '') for i in range(start_idx, end_idx + 1)])
            del row[start_idx + 1: end_idx + 1] # this will not delete anything if idxes are the same, which is the case for several descriptions, and is on purpose
            break
        except ValueError as err: # cannot convert string to float -> not yet a number on the end_idx
            end_idx += 1 
                
    return row

def add_largest_thickness(lines, lines_corrected, line_idx):
    # TODO improvement - should be handling dicts instead of being very specific in line position
    row = lines_corrected[line_idx]
    if line_idx == 0:
        thickness_above = row[5] # no thickness above when upper elevation
        thickness_below = lines_corrected[line_idx + 1][5]
        return max(row[5], thickness_above, thickness_below)
    
    row_above = lines_corrected[line_idx - 1] # row above exists
    
    if line_idx == len(lines) - 1: # no thickness below when lowest elevation
        thickness_above = row_above[5]
        thickness_below = row[5]
        return max(row[5], thickness_above, thickness_below)
    
    row_below = lines_corrected[line_idx + 1] # row below exists
    
    if 0 < (line_idx) < (len(lines) - 1):
        
        # Check if neighbouring elevations are on the same TP/MP before using neighbouring thicknesses
        if row[24] != row_above[24]:
            thickness_above = row[5]
        else:
            thickness_above = row_above[5]

        if row[24] != row_below[24]:
            thickness_below = row[5]
        else:
            thickness_below = row_below[5]    
    
    return max(row[5], thickness_above, thickness_below) # largest thickness is chosen from neighbours + current elevation
    
def find_turbine_and_cluster(structural_report_path):
    
    turbine_name = None
    line = get_text_as_lines_from_page(structural_report_path, page_no = 1, above_str_ID = 'Position', below_str_ID = 'Turbine', above_idx_is_at_element = True)
    assert len(line) == 1, 'Expected only one line matching for the turbine name'
    # for some reason the PDF reader returns underscore as spaces or just no space at all, so this must be a bit manual
    turbine_name_with_spaces = line[0].split(': ')[1]
    turbine_name_without_spaces = turbine_name_with_spaces.replace(' ', '')
    turbine_name = '_'.join( (turbine_name_without_spaces[0:2], turbine_name_without_spaces[2:5], turbine_name_without_spaces[5:7]) )
    
    cluster = None
    design_position_to_cluster = {'DEEP': 'JLN', 'INT': 'JLO', 'SHA': 'JLP'}
    line = get_text_as_lines_from_page(structural_report_path, page_no = 1, above_str_ID = 'load cluster', below_str_ID = 'MP diameter', above_idx_is_at_element = True)
    assert len(line) == 1, 'Expected only one line matching for the design cluster'
    line = line[0]
    
    for key in design_position_to_cluster:
        if key in line:
            cluster = design_position_to_cluster[key]
        
    return turbine_name, cluster    

def read_utilization_and_store_geometries(structural_report_path, result_dir, STORE = True):
    # This is created for reading only the files ending with "{turbine_name} Foundation Structural Design Report.pdf""
    MP_table_page_no = identify_pages_with_key_word(structural_report_path, 'appendix d') + 1
    TP_table_page_no = MP_table_page_no + 1
    
    turbine_name, cluster = find_turbine_and_cluster(structural_report_path)
    lines = get_text_as_lines_from_page(structural_report_path, page_no = TP_table_page_no, above_str_ID = '[LAT]', below_str_ID = 'Table D.2', add_word = 'TP')
    lines += get_text_as_lines_from_page(structural_report_path, page_no = MP_table_page_no, above_str_ID = '[LAT]', below_str_ID = 'Table D.1', add_word = 'MP')
    
    cols = ['z-level', 'Side', 'Orientation', 'Description', 'D', 't', 'Duration', 'Curve', 'Insp', 'DFF', 'Nref', 'Meq', 'S_nominal', 'SCF', 'gritblast', 'S_scf', 'tref', 'Lt', 'teff', 'k', 'alpha', 'ValType', 'Dd', 'Dd_tot']
    cols = ['elevation', 'in_out', 'orientation', 'description', 'diameter', 'small_thickness', 'lifetime', 'sn_curve', 'insp', 'DFF', 'Nref', 'Meq', 'S_nominal', 'scf', 'gritblast', 'S_scf', 't_ref', 'largest_weld_length', 't_eff', 'k', 'alpha', 'ValType', 'in_place_utilization', 'Dd_tot', 'MP_TP', 'cluster', 'turbine_name', 'large_thickness']

    lines_corrected = [str_line.split(' ') for str_line in lines]
    
    # correct the lines according to variations in the table
    # some descriptions have spaces in their titles, some elevations have different SN-curves at different lifetimes etc.)
    
    for line_idx, str_line in enumerate(lines):
        words = str_line.split(' ')
        row = lines_corrected[line_idx]
        
        if words[0].lower() == 'omni': # first worst == omni means that this elevation is a continuation of the lifetime of the same elevation in the line above, after cathodic protection is gone after 20 years
            words_above = lines[line_idx - 1].split(' ')
            row.insert(0, words_above[0]) # elevation
            row.insert(1, words_above[1]) # in_out
            row.insert(3, words_above[3] + '-free') # description
            
        row[1] = 'I' if row[1] == 'in' else 'O'
        row[2] = None if row[2].lower() == 'omni' else row[2]
        
        # Handle the descriptions and validation types that are given in the table with spaces
        description_start_idx, valType_start_idx = 3, 21
        row = clean_row_elements_with_spaces(row, description_start_idx)
        row = clean_row_elements_with_spaces(row, valType_start_idx)
        
        row.append(cluster) # for member_cluster
        row.append(turbine_name) # for member_cluster
        row.append('0.0') # placeholder for largest thickness - needs to wait until everything is cleaned up first
    
    # Correct the remaining lines
    for line_idx, str_line in enumerate(lines):
        row = lines_corrected[line_idx]  
        row[6] = row[6].replace('.1', '.08') # TODO this is a very stupid manual addition, but it is to correct 27.1 to 27.08 yrs
        row[10] = str(float(row[10]) * 1e6) # Nref is given in millions     
        row[-1] = add_largest_thickness(lines, lines_corrected, line_idx) # for large_thickness
    
    # Store the data as a Pandas DataFrame
    dict_df = {col: [] for col in cols}
    for line_idx, line in enumerate(lines_corrected):
        for col_idx, col in enumerate(cols):
            dict_df[col].append(line[col_idx])
    
    df = pd.DataFrame(dict_df)
    result_dir = result_dir + fr'\{cluster}\{turbine_name}'
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    result_path = result_dir + fr'\utils_and_geos_from_structure_report.xlsx'
    if STORE:
        df.to_excel(result_path)
        print(f'stored util and geos for {turbine_name}:')
        
    pd.options.display.max_rows = 100 
    print(df)
    return result_path
    
if __name__ == '__main__':
    
    structural_report_path = os.getcwd() + r'\data\structural_specific_reports\P0061-C1224-WP03-REP-002-F - DA_J01_JC Foundation Structural Design Report.pdf'
    result_dir = os.getcwd() + r'\output\all_turbines'
    path = read_utilization_and_store_geometries(structural_report_path, result_dir, STORE = False)