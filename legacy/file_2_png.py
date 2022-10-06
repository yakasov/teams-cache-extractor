"""
The plan here is to take Microsoft Team files,
check if they start with the GZ/TGZ header,
and if they do, extract them,
then check their headers again for the PNG header,
and change their extensions to .png.
"""

from os import listdir
from os.path import isfile, join
import gzip

GZ_HEADER = '1F8B08' # 1F 8B 08
PNG_HEADER = '89504E470D0A1A0A' # 89 50 4E 47 0D 0A 1A 0A
FOLDER_PATH = 'C:\\Users\\Work\\Desktop\\Cache' # Change if necessary

def get_file_list(path):
    """Return list of all file names in directory."""
    return [f for f in listdir(path) if isfile(join(path, f))]

FILE_LIST = get_file_list(FOLDER_PATH)

def get_file_header(path, byte_length):
    """Return file header of given length for given file."""
    with open(path, 'rb') as f:
        hex_data = f.read().hex()
    return hex_data[:byte_length*2].upper()

def unzip_gz(path):
    """Use gzip to read the extracted contents of a GZ file."""
    with gzip.open(path, 'rb') as f:
        return f.read()

def save_png(path, content):
    """Save content to path as png."""
    if not path.isfile:
        with open(f'{path}.png', 'wb') as f:
            f.write(content)
            f.close()


for file_path in FILE_LIST:
    full_path = f'{FOLDER_PATH}\\{file_path}'
    if get_file_header(full_path, 3) == GZ_HEADER:
        file_content = unzip_gz(full_path)
        if file_content.hex()[:16].upper() == PNG_HEADER:
            save_png(full_path, file_content)
            print(f'{full_path}.png')
