# teams-cache-extractor

#### by James M. (yakasov)

## Description

Python script for extracting files from the Microsoft Teams cache.

Given a directory to look in, each file in the directory will have it's signature
checked against a list of known file signatures. If there is a match, the file
will be converted to that file type.

The script also includes other functionalities - it can unzip GZ files (as Teams
compresses many files this way), and can also split up larger files with multiple
smaller files inside. The smaller files will be resolved and saved separately.

## How to use

Clone the repo, then open `file_to_extension.py`. You will need to change line 64
to the location of your Teams cache - whilst the default location for the cache is
`%appdata%\Microsoft\Teams\Cache`, I highly recommend copying the cache somewhere
else first to avoid damaging any files or running into permissions errors.

The resulting code may look similar to the following:

```python
FOLDER_PATH = 'C:\\Users\\Work\\Desktop\\Cache'
```

If you do not use a raw string, don't forget to encode the backslashes!

After this, you can run `file_to_extension.py` normally. The resulting output will
be at your `FOLDER_PATH\Saved`. Every time you want to rerun the script, you will
need to delete your Saved folder.

## Header instructions (from file_to_extension.py)

```python
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

# Rules for .OFFICE file types:
#
# All the .OFFICE files are usually prepended by a 0x200 (512) byte offset
#      00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15
# PPT: FD FF FF FF nn nn 00 00
# XLS: FD FF FF FF nn 00
# or   FD FF FF FF nn 02
# or   FD FF FF FF 20 00 00 00
# DB : FD FF FF FF xx xx xx xx xx xx xx xx 04 00 00 00
```
