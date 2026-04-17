configs: dict[str, object] = {
    'encoding': 'UTF-8-SIG'
}

from nuix_nli_lib.data_types.csv_file import CSVEntry, CSVRowEntry
from nuix_nli_lib.data_types.json_file import JSONValueEntry, JSONArrayEntry, JSONObjectEntry, JSONFileEntry
from nuix_nli_lib.data_types.sql_type import SQLTypeEntry, SQLRowEntry

"""
This module provides a set of special data types that can be used alongside the EDRM builder framework
to ease ingestion of complex data sources.  The implemented types are:

1. A Generic CSV format (data_types.csv_file): CSVEntry, CSVRowEntry
2. A Generic JSON format (data_types.json_file): JSONValueEntry, JSONArrayEntry, JSONObjectEntry, JSONFileEntry
3. A SQL / database format (data_types.sql_type): SQLTypeEntry, SQLRowEntry
   - Uses Python's built-in sqlite3 by default; any DB-API 2.0 driver can be substituted
"""
