import numpy as np
import struct

def read_bladed_file(binary_file,text_file):
    with open(binary_file, mode='rb') as file:
        content = file.read()
    with open(text_file, mode='r') as file: # b is important -> binary
        lines = file.read().split('\n')
    dimens = lines[8].split()
    rows = int(dimens[1])
    cols = int(dimens[2])

    content_unpacked = struct.unpack("<" + "f"*(len(content) // 4), content)
    content_reshaped = np.reshape(content_unpacked, (rows, cols), order='F')
    return content_reshaped

#add read_sima_file() here