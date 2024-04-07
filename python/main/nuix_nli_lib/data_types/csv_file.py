import csv
from typing import Any, Type

from nuix_nli_lib.edrm.EDRMBuilder import EDRMBuilder
from nuix_nli_lib.edrm.FileEntry import FileEntry
from nuix_nli_lib.edrm.MappingEntry import MappingEntry
from nuix_nli_lib import data_types

"""
This module provides classes that can be used to simplifying adding CSV files to an EDRM XML load file, or NLI file.
It contains two base classes:

CSVEntry:
This subclass of edrm.FileEntry represents a CSV file.  It will read the CSV file from disk and store its rows of data.
It can then provide access to individual rows using the `data` property.  The class also adds an `add_to_builder`
method, which, when used instead of the traditional `edrm.EDRMBuilder#add_entry` method, will also construct and add
CSVRowEntry instances to the builder representing each row in the CSV file.  Additional modifications to the base
FileEntry type include tha abolity to act as a parent (generally to do so for the CSV rows).

CSVRowEntry:
This subclass of edrm.MappingEntry represents a row on a CSV file.  It only exists in the context of its parent
CSVEntry.  It will provide fields and values based on the CSVEntry's data property.

When using a CSV File, it will usually be required to customize it in some way to work with the CSVs data - for example
to provide meaningful names or correct time fields for each row.  In this case, it is usually only necessary to override
the CSVRowEnty class and provide it as the row_generator when constucting the CSVEntry.  See the test.csv_tests.EnvEntry
as a basic example, and test.csv_tests.ProcessEntry for a more complete example.

<code>
from data_types import CSVEntry, CSVRowEntry
class MyRowEntry(CSVRowEntry):
  # my implementation here...

csv = CSVEntry(path_to_csv, row_generator=MyRowEntry)
builder = EDRMBuilder()
builder.output_path = path_to_output
csv.add_to_builder(builder)
builder.save()
</code>
"""

class CSVEntry(FileEntry):
    """
    Represents a CSV file and manages storing and retrieving rows of data for the target EDRM XML file.

    Implementation Note: This implementation fully reads the CSV file into memory.  Although this is a reference
    implementation for other similar constructs, such as mapping databases or JSON files, this may not work the best
    for large files.  If memory is an issue, then consider subclassing this class and reading the content in line
    by line upon need.
    """
    def __init__(self, file_path: str, parent_id: str = None, row_generator: Type[Any] = None):
        """
        :param file_path: Full path to the CSV file.  This will read the file into memory.  Errors will occur if the
                          file is not accessible or not in the expected CSV format
        :param parent_id: Optional: Unique identifier for this file's container, if it has one.  None (the default) will
                          make this a top-level file.
        :param row_generator: Optional: A generator to use for creating row data.  If not provided, an unmodified
                              CSVRowEntry will be created for each row.  If provided it should be a callable that
                              accepts two parameters:
                              1. A CSVEntry instance (self) that provides the source of the data
                              2. An integer - the index into the data that holds the row of data
                              The generated object produced should be an EntryInterface instance, and should likely be
                              a subclass of MappingEntry (and more likely a subclass of CSVRowEntry).
        """
        super().__init__(file_path, "text/csv", parent_id)

        self.__data: list[dict[str, Any]] = []
        self.__row_fields: list[str] = []
        self.__row_generator = row_generator

        if not self.file_path.is_file():
            raise IOError(f'File does not exist or is not a file: {self.file_path}')

        with self.file_path.open(mode='r', encoding=data_types.configs['encoding']) as file:
            reader: csv.DictReader = csv.DictReader(file)
            self.__row_fields = list(reader.fieldnames)
            for row in reader:
                self.__data.append(row)

    @property
    def data(self) -> list[dict[str, Any]]:
        """
        :return: A list of the row data in the CSV file.  Note: This returns the actual list and actual data.  Modifying
                 it can cause unexpected behavior and should be avoided.
        """
        return self.__data

    @property
    def row_fields(self) -> list[str]:
        """
        :return: A list of the field names in the CSV file.
        """
        return self.__row_fields

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'

    def add_to_builder(self, builder: EDRMBuilder) -> str:
        """
        Helper method to add this CSVEntry to the EDRM XML file, as well as an additional entry for each row in the CSV
        file.  This method will use the `row_generator` passed in to the constructor to generate the new entry for the
        row data, defaulting to creating a CSVRowEntry if none is provided.  This method does not specifically assign
        this CSVEntry as the parent to the produced rows, but the default behavior of CSVRowEntry will do so.
        :param builder: The EDRMBuilder used to generate the EDRM XML load file
        :return: None
        """
        row_gen = self.__row_generator or CSVRowEntry
        builder.add_entry(self)
        for index in range(len(self.data)):
            builder.add_entry(row_gen(self, index))

        return self[self.identifier_field].value


class CSVRowEntry(MappingEntry):
    def __init__(self, parent_csv: CSVEntry, row_index: int, parent_id: str = None):
        self.__parent_csv: CSVEntry = parent_csv
        self.__row_index: int = row_index

        super().__init__({},
                         "application/x-database-table-row",
                         parent_id=parent_id or parent_csv[parent_csv.identifier_field].value)

    @property
    def fields(self) -> list[str]:
        return self.__parent_csv.row_fields

    @property
    def data(self) -> dict[str, Any]:
        return self.__parent_csv.data[self.__row_index]

