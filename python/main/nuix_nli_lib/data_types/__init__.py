configs = {
    'encoding': 'UTF-8-SIG'
}

from nuix_nli_lib.data_types.csv_file import CSVEntry, CSVRowEntry
from nuix_nli_lib.data_types.json_file import JSONValueEntry, JSONArrayEntry, JSONObjectEntry, JSONFileEntry

"""
When this module is complete, it will represent a set of special data types that can be used alongside the EDRM builder
framework to ease the use of complex data types.  The planned types are:

1. A Generic CSV format (implemented in data_types.csv_file
2. A Generic JSON format
3. A Generic Database format
4. A Slightly less generic SQLite Database format
"""
