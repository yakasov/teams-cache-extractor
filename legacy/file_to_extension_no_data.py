# pylint: disable=invalid-name, redefined-outer-name, global-statement

"""
Take a directory full of files and add extensions to them if valid.
Expands compressed files if necessary first - no expanded copy is saved,
so if an expanded file is not a media file (eg it becomes a folder),
it will not be saved.
"""

from os import listdir, mkdir, rmdir
from os.path import isfile, isdir, join
import gzip
import re

HEADERS = { # HEADERS must be compressed headers first, then file headers second
    # COMPRESSED FILETYPE HEADERS BELOW
    '1F 8B 08': '.GZ',
    '37 7A BC AF 27 1C': '.7Z',
    '50 4B 03 04': '.ZIP',
    # We don't actually process 7z or zip files
    # But we put them here so they don't get added to UNKNOWN_CODES
    #
    # MEDIA FILETYPE HEADERS BELOW
    '89 50 4E 47 0D 0A 1A 0A': '.PNG',
    'FF D8 FF': '.JPEG',
    '49 44 33': '.MP3',
    '7B 5C 72 74 66': '.RTF',
    '47 49 46 38': '.GIF', # Followed by 37 61 or 39 61
    '77 4F 46 32': '.WOFF2', # Web Open Font Format 2
    'EF BB BF 3C': '.HTML', # Actually WSC but I had a double positive
    '3C 21': '.HTML', # Starts with <! (for DOCTYPE)
    #
    # OTHER FILETYPE HEADERS BELOW
    '6E 70 6D': '.LOG', # npm log files
    '22 75 73 65': '.JS', # Fallback: these files all start with "use
    '2F 2A': '.JS', # Fallback: these files all start with /*
    '7B': '.JSON', # Fallback: these files all start with {
    '22': '.JSON', # Fallback: these files all start with "
    '5B': '.RELATED1', # Fallback: these files all start with [ - related?
    '': '.TXT' # Any remaining files change to .txt to look at manually
}

FOLDER_PATH = 'C:\\Users\\Work\\Desktop\\Cache' # Change if necessary
UNKNOWN_CODES = [] # If the header is not in HEADERS, store the first 12 characters here
ARCHIVED_FILES = [] # Store the locations of zip or 7z files, to be opened manually by the user

READ_COUNT = 0
WRITE_COUNT = 0
EXTRACT_COUNT = 0
SKIP_COUNT = 0

def get_file_list(path):
    """Return list of all file names in directory."""
    return [f for f in listdir(path) if isfile(join(path, f))]

FILE_LIST = get_file_list(FOLDER_PATH)

def get_file(path):
    """Return file contents for given file."""
    with open(path, 'rb') as f:
        return f.read()

def unzip_gz(path):
    """Use gzip to read the extracted contents of a compressed GZ file."""
    print(f'Unzipping .gz at {path}.gz...')
    try:
        with gzip.open(path, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        pass

def save_file(path, content, extension):
    """Save content to path as matching extension."""
    path_with_extension = f'{path}{extension}'
    if not isfile(path_with_extension): # We don't need to rewrite the file if it already exists
        try:
            with open(path_with_extension, 'wb') as f:
                f.write(content)
                f.close()
            print(f'NEW FILE: {path_with_extension}')
            global WRITE_COUNT
            WRITE_COUNT += 1
        except PermissionError:
            print('PermissionError: File save failed, file is likely locked / in use.')
        except FileNotFoundError:
            pass
    else:
        print(f'{path_with_extension} already exists, skipping...')
        global SKIP_COUNT
        SKIP_COUNT += 1

def check_directories(check_folder_path):
    """Check if certain directories already exist. If not, create them."""
    if not isdir(check_folder_path):
        mkdir(check_folder_path)
        print(f'Couldn\'t find {check_folder_path}! Creating new directory...')
    if not isdir(f'{check_folder_path}\\DATA'):
        mkdir(f'{check_folder_path}\\DATA')
    for _, extension in HEADERS.items():
        check_ext_path = f'{check_folder_path}\\{extension.replace(".", "")}'
        if not isdir(check_ext_path):
            mkdir(check_ext_path)
            print(f'Couldn\'t find {check_ext_path}! Creating new directory...')

def check_validity(content, code):
    """Compare file headers and make sure the we're not looking at a file
    that already has the correct extension."""
    try:
        is_hex_valid = content.hex()[:len(code)].upper() == code
        if not is_hex_valid and content.hex()[:12] not in UNKNOWN_CODES:
            UNKNOWN_CODES.append(content.hex()[:12])
        return is_hex_valid
    except AttributeError:
        return False

def remove_empty_directories(path):
    """Look through the created directories and delete any that are empty."""
    for _, extension in HEADERS.items():
        check_ext_path = f'{path}\\{extension.replace(".", "")}'
        try:
            if len(listdir(check_ext_path)) == 0:
                rmdir(check_ext_path)
                print(f'{check_ext_path} is empty, deleting...')
        except FileNotFoundError:
            pass

def output_unknown_headers():
    """Look through UNKNOWN_CODES and output the list into a file.
    This lets us identify common signatures we've missed in the HEADERS dictionary."""
    UNKNOWN_CODES.sort()
    with open(f'{FOLDER_PATH}\\Saved\\unknown_codes.txt', 'wb') as f:
        for unknown_hex in UNKNOWN_CODES:
            unknown_hex = (' ').join(re.findall('..', unknown_hex))
            f.write(f'{unknown_hex}\n'.encode())

def print_archives():
    """Print the locations of 7z or zip files, to be opened manually."""
    if ARCHIVED_FILES:
        print('\n.zip and .7z files are currently unsupported, sorry!\n\
Because of this, here are the locations of files you can open manually:')
        for file in ARCHIVED_FILES:
            print(f'{file[1]} @ {file[0]}')

def main(path_to_use):
    """Main function. We gotta run it twice!"""
    for file_path in FILE_LIST:
        full_path = f'{path_to_use}\\{file_path}'
        save_path = f'{path_to_use}\\Saved'
        check_directories(save_path)
        file_content = get_file(full_path)
        global READ_COUNT
        READ_COUNT += 1

        for hex_code, ext in HEADERS.items():
            if check_validity(file_content, hex_code.replace(' ', '')) and \
            ext not in file_path.upper():
                if ext == '.GZ':
                    file_content = unzip_gz(full_path)
                    global EXTRACT_COUNT
                    EXTRACT_COUNT += 1
                else:
                    if ext in ('ZIP', '.7Z'):
                        ARCHIVED_FILES.append([full_path, ext])
                    save_path += f'\\{ext.replace(".", "")}\\{file_path}'
                    save_file(save_path, file_content, ext)
                    break

        FILE_LIST.remove(file_path)

    remove_empty_directories(f'{path_to_use}\\Saved')
    output_unknown_headers()
    print_archives()

main(FOLDER_PATH)

print(f'\nRead {READ_COUNT} -- Wrote {WRITE_COUNT}\
 -- Extracted {EXTRACT_COUNT} -- Skipped {SKIP_COUNT}')
