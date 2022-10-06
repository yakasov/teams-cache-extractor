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
