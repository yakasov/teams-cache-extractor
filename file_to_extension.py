# pylint: disable=invalid-name, global-statement

"""
Take a directory full of files and add extensions to them if valid.
Expands compressed files if necessary first - no expanded copy is saved,
so if an expanded file is not a media file (eg it becomes a folder),
it will not be saved.

Author - James M. (yakasov)
"""

from os import listdir, mkdir, remove, rmdir
from os.path import isfile, isdir, join
from collections import Counter
import gzip
import shutil

HEADERS = { # HEADERS must be compressed headers first, then file headers second
    # COMPRESSED FILETYPE HEADERS BELOW
    '1F 8B 08': '.GZ',
    '37 7A BC AF 27 1C': '.7Z',
    '50 4B 03 04': '.ZIP',
    # We don't actually process 7z or zip files
    # But we put them here so they don't get added to UNKNOWN_CODES
    #
    # DOCUMENT-ESQUE FILETYPE HEADERS BELOW
    '50 4B 03 04 14 00 06 00': '.OOXML', # DOCX, PPTX, XLSX
    'FD FF FF FF': '.OFFICE', # These files need manual checking, rules below HEADERS dic
    '   6E 1E F0': '.PPT', #                         Prepend 0 byte   + 0x200 byte offset
    ' F 00 E8 03': '.PPT', #                         Prepend 0 nibble + 0x200 byte offset
    'A0 46 1D F0': '.PPT', #                                          + 0x200 byte offset
    'EC A5 C1 00': '.DOC', #                                          + 0x200 byte offset
    ' 9 08 10 00 00 06 05 00': '.XLS', #             Prepend 0 nibble + 0x200 byte offset
    '25 50 44 46': '.PDF',
    '52 00 6F 00 6F 00 74 00': '.MSG', # Outlook/Exchange message     + 0x200 byte offset
    #
    # MEDIA FILETYPE HEADERS BELOW
    '89 50 4E 47 0D 0A 1A 0A': '.PNG',
    'FF D8 FF': '.JPEG',
    '49 44 33': '.MP3',
    '7B 5C 72 74 66': '.RTF',
    '47 49 46 38': '.GIF',   # Followed by 37 61 or 39 61
    '77 4F 46 32': '.WOFF2', # Web Open Font Format 2
    'EF BB BF 3C': '.HTML',  # Same signature for WSC
    '3C 21': '.HTML',        # Starts with <! (for DOCTYPE)
    #
    # OTHER FILETYPE HEADERS BELOW
    '6E 70 6D': '.LOG',      # npm log files
    '22 75 73 65': '.JS',    # Fallback: these files all start with "use
    '2F 2A': '.JS',          # Fallback: these files all start with /*
    '7B 22': '.JSON',        # Fallback: these files all start with {
}

# Rules for .OFFICE file types:
#
# All the .OFFICE files are usually prepended by a 0x200 (512) byte offset
#      00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15
# PPT: FD FF FF FF nn nn 00 00
# XLS: FD FF FF FF nn 00
# or   FD FF FF FF nn 02
# or   FD FF FF FF 20 00 00 00
# DB : FD FF FF FF xx xx xx xx xx xx xx xx 04 00 00 00

FOLDER_PATH = 'C:\\Users\\Work\\Desktop\\Cache'
# Change if necessary, encode \ -> \\
# You'll need to copy your cache elsewhere so the files can be read with correct perms
# Default cache is at %appdata%\Microsoft\Teams\Cache
EXTENDED_PATH = f'{FOLDER_PATH}\\Saved\\DATA'
UNKNOWN_CODES = [] # If the header is not in HEADERS, store the first 12 characters here
NEW_GZ_FILES = []
DATA_FILES = ['data_0', 'data_1', 'data_2', 'data_3', 'index'] # 'data_3'
BYTE_COUNT = 36 # 36 is good for precise splitting, 186 is fast but not 100% complete
# The BYTE_COUNT is the length of space between data to look for
# Higher counts will mean the data gets split less
# Lower counts will mean the data gets split more, but could split up intact files
# that happen to have large empty space in them. If you get broken files, increase count
#
# A lower count will also increase processing time as more files will be generated!
# The lowest you should go is 29 I reckon

READ_COUNT = 0
WRITE_COUNT = 0
EXTRACT_COUNT = 0
SKIP_COUNT = 0

def get_file_list(path):
    """Return list of all file names in directory.

    :param path: full directory path
    :returns:    directory files as list
    """
    return [f for f in listdir(path) if isfile(join(path, f))]

def get_file(path):
    """Return file contents for given file.

    :param path: full file path including extension
    :returns:    file contents as bytes
    """
    with open(path, 'rb') as f:
        global READ_COUNT
        READ_COUNT += 1
        return f.read()

def unzip_gz(path):
    """Use gzip to read the extracted contents of a compressed GZ file.

    :param path: full file path including extension
    :returns:    file contents as bytes + two null (0x00) bytes as a trailer
    """
    print(f'Unzipping .gz at {path}.gz...')
    try:
        with gzip.open(path, 'rb') as f:
            global EXTRACT_COUNT
            EXTRACT_COUNT += 1
            return f.read() + b'\x00\x00'
    except (FileNotFoundError, EOFError, gzip.BadGzipFile):
        return ''

def save_file(path, content, extension):
    """Save content to path as matching extension.

    :param path:      full file path excluding extension (file yet to be created)
    :param content:   file content as bytes to be written
    :param extension: extension to be appended to file path
    """
    path_with_extension = f'{path}{extension}'
    if not isfile(path_with_extension): # We don't need to rewrite the file if it already exists
        try:
            with open(path_with_extension, 'wb') as f:
                f.write(content)
                f.close()
                global WRITE_COUNT
                WRITE_COUNT += 1
            print(f'NEW FILE: {path_with_extension}')
        except PermissionError:
            print('PermissionError: File save failed, file is likely locked / in use.')
        except FileNotFoundError:
            pass
    else:
        print(f'{path_with_extension} already exists, skipping...')
        global SKIP_COUNT
        SKIP_COUNT += 1

def save_split_file(fname, path, content, i):
    """Save content from split data file - no extension.

    :param fname:   original un-split data file name
    :param path:    full directory path (...path\\Saved)
    :param content: file content as hex to be converted to bytes and written
    :param i:       unique number to identify new split data files
    """
    path_with_extension = f'{path}\\DATA\\{fname}_{i}'
    if not isfile(path_with_extension):
        try:
            with open(path_with_extension, 'wb') as f:
                if len(content) % 2 == 1:
                    f.write(bytes.fromhex(f'{content}0'))
                else:
                    f.write(bytes.fromhex(content))
                f.close()
                global WRITE_COUNT
                WRITE_COUNT += 1
            print(f'NEW DATA FILE: {path_with_extension}')
        except (PermissionError, FileNotFoundError):
            pass
    else:
        global SKIP_COUNT
        SKIP_COUNT += 1
        print(f'{path_with_extension} already exists, skipping...')


def check_directories(check_folder_path):
    """Check if certain directories already exist. If not, create them.

    :param check_folder_path: full directory path (...path\\Saved)
    """
    if not isdir(check_folder_path):
        mkdir(check_folder_path)
        print(f'Couldn\'t find {check_folder_path}! Creating new directory...')
    if not isdir(f'{check_folder_path}\\DATA') and '\\Saved\\DATA' not in check_folder_path:
        mkdir(f'{check_folder_path}\\DATA')
    for _, extension in HEADERS.items():
        check_ext_path = f'{check_folder_path}\\{extension.replace(".", "")}'
        if not isdir(check_ext_path):
            mkdir(check_ext_path)
            print(f'Couldn\'t find {check_ext_path}! Creating new directory...')

def check_validity(content, sig):
    """Compare file headers and make sure the we're not looking at a file
    that already has the correct extension.

    :param content: file contents as bytes
    :param sig:     signature from HEADERS to check against file contents
    :return:        True/False if signature is present at start of file
    """
    try:
        return content.hex()[:len(sig)].upper() == sig
    except AttributeError:
        return False

def remove_empty_directories(path):
    """Look through the created directories and delete any that are empty.

    :param path: full directory path
    """
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
    This lets us identify common signatures we've missed in the HEADERS dictionary.
    """
    UNKNOWN_CODES.sort()
    with open(f'{FOLDER_PATH}\\Saved\\unknown_codes.json', 'wb') as f:
        f.write(str(Counter(UNKNOWN_CODES)).strip('Counter()').encode())
        f.close()

def split_hex_files(fname, path, content):
    """Split file by hex whitespace to create multiple smaller files.

    :param fname:   original un-split data file name
    :param path:    full directory path (...path\\Saved)
    :param content: file content as bytes
    """
    split_files = content.hex().split('00' * BYTE_COUNT) # Brute force method
    i = 0
    for file in split_files:
        file = file.lstrip('0') # Only strip from start of hex string
        if len(file) > 64: # Any file less than 128 bytes is probably worthless
            i += 1
            save_split_file(fname, path, file, i)

def move_data_files():
    """Move files created when unpacking data files to main Saved directory."""
    data_folder_paths = listdir(f'{EXTENDED_PATH}\\Saved')
    for path in data_folder_paths:
        try:
            data_file_paths = listdir(f'{EXTENDED_PATH}\\Saved\\{path}')
        except NotADirectoryError:
            data_file_paths = [path] # If NotADirectory, it must be a file
        for file in data_file_paths:
            if isfile(f'{EXTENDED_PATH}\\Saved\\{path}\\{file}') and \
            not isfile(f'{FOLDER_PATH}\\Saved\\{path}\\{file}'):
                shutil.move(
                    f'{EXTENDED_PATH}\\Saved\\{path}\\{file}', f'{FOLDER_PATH}\\Saved\\{path}')

def recover_gz_files(path_to_use, file_content, file_name):
    """Some split up data files are files with a bunch of junk data, then a valid GZ file signature.
    If this is the case, we should try and recover the file.

    :param path_to_use:  full directory path
    :param file_content: file content as bytes
    :param file_name:    file name
    """
    try: # See if there's a GZ file signature that hasn't been split properly
        gz_index = file_content.index(bytes(b'\x1f\x8b\x08'))
        save_file(f'{path_to_use}\\{file_name}', file_content[gz_index:] + \
            b'\x00\x00', '_GZ') # Add two null (0x00) bytes as trailer
        NEW_GZ_FILES.append(f'{file_name}_GZ')
    except ValueError:
        pass

def cleanup_js_files(path_to_use, file_content, full_path):
    """A lot of split data files end up being junk data combined with a URL to an online JS file.
    These are essentially useless to us, so we can safely delete them.

    :param path_to_use:  full directory path
    :param file_content: file content as bytes
    :param full_path:    full file path (essentially path_to_use\\file_name from above)
    """
    try: # Remove all files ending in .js from the DATA folder
         # This only affects files with the incorrect file signatures
        if path_to_use == EXTENDED_PATH and file_content[-3:].hex() == '2e6a73':
            remove(full_path)
    except (AttributeError, FileNotFoundError):
        pass

def main(path_to_use):
    """Main function. We gotta run it thrice!

    :param path_to_use: full directory path to folders to read (essentially our root folder to use)
    """
    for file_path in FILE_LIST:
        hex_code_found = False
        full_path = f'{path_to_use}\\{file_path}'
        save_path = f'{path_to_use}\\Saved'
        check_directories(save_path)
        file_content = get_file(full_path)

        if file_path in DATA_FILES and path_to_use == FOLDER_PATH:
            # Only run this on the first expand
            split_hex_files(file_path, save_path, file_content)

        for hex_code, ext in HEADERS.items():
            if check_validity(file_content, hex_code.replace(' ', '')) and \
            (ext not in file_path.upper() or FILE_LIST == NEW_GZ_FILES):
                hex_code_found = True
                if ext == '.GZ':
                    file_content = unzip_gz(full_path)
                else:
                    save_path += f'\\{ext.replace(".", "")}\\{file_path}'
                    save_file(save_path, file_content, ext)
                    if path_to_use == EXTENDED_PATH:
                        remove(full_path)
                    break
        if not hex_code_found:
            UNKNOWN_CODES.append(file_content.hex()[:12])

        if path_to_use == EXTENDED_PATH and not hex_code_found and FILE_LIST != NEW_GZ_FILES:
            recover_gz_files(path_to_use, file_content, file_path)
        cleanup_js_files(path_to_use, file_content, full_path)

    if path_to_use == EXTENDED_PATH:
        move_data_files()


if isdir(f'{FOLDER_PATH}\\Saved'):
    raise Exception('Please delete your Saved folder then try running again!')

FILE_LIST = get_file_list(FOLDER_PATH)
main(FOLDER_PATH) # Run for the untouched cache files

FILE_LIST = get_file_list(EXTENDED_PATH)
main(EXTENDED_PATH) # Run for the split up data files

FILE_LIST = NEW_GZ_FILES
main(EXTENDED_PATH) # Run for any recovered data with GZ signatures from the split up data files

remove_empty_directories(f'{FOLDER_PATH}\\Saved')
remove_empty_directories(f'{EXTENDED_PATH}\\Saved')

try:
    if len(listdir(f'{EXTENDED_PATH}\\Saved')) == 0:
        rmdir(f'{EXTENDED_PATH}\\Saved')
except FileNotFoundError:
    pass

output_unknown_headers()

print(f'\nRead {READ_COUNT} -- Wrote {WRITE_COUNT}\
-- Extracted {EXTRACT_COUNT} -- Skipped {SKIP_COUNT}')
