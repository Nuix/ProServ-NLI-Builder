from __future__ import annotations

import csv
from typing import Any, Generator, Optional, Type

from nuix_nli_lib.edrm.EDRMBuilder import EDRMBuilder
from nuix_nli_lib.edrm.FileEntry import FileEntry
from nuix_nli_lib.edrm.MappingEntry import MappingEntry
from nuix_nli_lib import data_types

"""
This module provides classes that can be used to simplify adding CSV files to an EDRM XML load file, or NLI file.
It contains two base classes:

CSVEntry:
This subclass of edrm.FileEntry represents a CSV file.  It will read the CSV file from disk and store its rows of data.
It can then provide access to individual rows using the `data` property.  The class also adds an `add_to_builder`
method, which, when used instead of the traditional `edrm.EDRMBuilder#add_entry` method, will also construct and add
CSVRowEntry instances to the builder representing each row in the CSV file.  Additional modifications to the base
FileEntry type include tha ability to act as a parent (generally to do so for the CSV rows).

CSVRowEntry:
This subclass of edrm.MappingEntry represents a row on a CSV file.  It only exists in the context of its parent
CSVEntry.  It will provide fields and values based on the CSVEntry's data property.

When using a CSV File, it will usually be required to customize it in some way to work with the CSVs data - for example
to provide meaningful names or correct time fields for each row.  In this case, it is usually only necessary to override
the CSVRowEnty class and provide it as the row_generator when constructing the CSVEntry.  See the test.csv_tests.EnvEntry
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

    Implementation Note: This implementation uses lazy, generator-based streaming to read the CSV file.  Rows are not
    loaded into memory at construction time.  Instead, the file is re-opened and iterated lazily each time
    `add_to_builder` is called.  This bounds peak memory usage to the working set of the current traversal rather than
    the full file size.

    The `data` property (which returns a list of all rows) is available for backward compatibility and for subclasses
    that require random access to row data (e.g. to look up parent–child relationships across rows).  Accessing `data`
    will load and cache all rows in memory on first use, so subclasses that call `parent_csv.data` will not benefit from
    streaming.

    Note: because the CSV file is re-opened by `add_to_builder`, the file path must remain accessible for the duration
    of the build phase.
    """
    def __init__(self, file_path: str,
                 mimetype: str = "text/csv",
                 parent_id: Optional[str] = None,
                 row_generator: Optional[Type[Any]] = None,
                 delimiter: str = ',') -> None:
        """
        :param file_path: Full path to the CSV file.  The file header is read immediately to obtain field names.
                          Rows are NOT loaded into memory at this point.
        :param mimetype: Optional MIME type used to represent the file in the case.  Defaults to "text/csv".
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
        super().__init__(file_path, mimetype, parent_id)

        self.__delimiter = delimiter
        self.__row_generator = row_generator

        # Lazily populated on first access to the `data` property.
        self.__data: list[dict[str, Any]] | None = None

        # Current streaming row context, set by add_to_builder during iteration so that CSVRowEntry
        # instances created during streaming can capture the row data directly without triggering a
        # full load of the `data` list.
        self._current_streaming_row: dict[str, Any] | None = None

        if not self.file_path.is_file():
            raise IOError(f'File does not exist or is not a file: {self.file_path}')

        with self.file_path.open(mode='r', encoding=str(data_types.configs['encoding'])) as file:
            reader: csv.DictReader = csv.DictReader(file, delimiter=delimiter)
            self.__row_fields = [f for f in list(reader.fieldnames or []) if len(f.strip()) > 0]
            for row in reader:
                self.__data.append(row)

    @property
    def data(self) -> list[dict[str, Any]]:
        """
        Return all rows in the CSV file as a list of dicts.  The list is loaded from disk on the first call and
        cached for subsequent calls.

        Note: Accessing this property loads the entire file into memory.  Subclasses that need random-access to
        row data (e.g. to traverse parent–child relationships across rows) should use this property.  Code that only
        needs to iterate rows linearly should prefer the `_iter_rows()` generator to keep memory usage bounded.

        :return: A list of the row data in the CSV file.  Note: This returns the actual list and actual data.
                 Modifying it can cause unexpected behavior and should be avoided.
        """
        if self.__data is None:
            self.__data = list(self._iter_rows())
        return self.__data

    @property
    def row_fields(self) -> list[str]:
        """
        :return: A list of the field names in the CSV file.
        """
        return self.__row_fields

    def _iter_rows(self) -> Generator[dict[str, Any], None, None]:
        """
        Yield each data row from the CSV file as a dict without loading all rows into memory at once.

        The file is opened and iterated lazily each time this method is called, allowing the same
        CSVEntry to be traversed more than once (e.g. during multiple builder passes) without
        retaining all rows in memory between passes.

        :return: A generator yielding one row dict per CSV data row.
        """
        with self.file_path.open(mode='r', encoding=data_types.configs['encoding']) as file:
            reader: csv.DictReader = csv.DictReader(file, delimiter=self.__delimiter)
            for row in reader:
                yield dict(row)

    def add_as_parent_path(self, existing_path: str) -> str:
        return f'{self.name}/{existing_path}'

    def add_to_builder(self, builder: EDRMBuilder) -> str:
        """
        Helper method to add this CSVEntry to the EDRM XML file, as well as an additional entry for each row in the CSV
        file.  This method will use the `row_generator` passed in to the constructor to generate the new entry for the
        row data, defaulting to creating a CSVRowEntry if none is provided.  This method does not specifically assign
        this CSVEntry as the parent to the produced rows, but the default behavior of CSVRowEntry will do so.

        Rows are iterated via a streaming generator so that only one row is held in memory at a time.  If the
        `row_generator` subclass accesses `parent_csv.data` (e.g. to resolve parent–child relationships across rows),
        the full row list will be loaded and cached on first access to that property.

        :param builder: The EDRMBuilder used to generate the EDRM XML load file
        :return: The identifier value for this entry.
        """
        row_gen = self.__row_generator or CSVRowEntry
        builder.add_entry(self)

        for index, row in enumerate(self._iter_rows()):
            # Expose the current row to CSVRowEntry so it can capture data directly
            # without triggering a full load of the `data` list.
            self._current_streaming_row = row
            try:
                builder.add_entry(row_gen(self, index))
            finally:
                self._current_streaming_row = None

        return self[self.identifier_field].value


class CSVRowEntry(MappingEntry):
    def __init__(self, parent_csv: CSVEntry, row_index: int, parent_id: Optional[str] = None) -> None:
        self.__parent_csv: CSVEntry = parent_csv
        self.__row_index: int = row_index

        # Capture the streaming row provided by CSVEntry.add_to_builder (if active).
        # When present this avoids loading the full data list just to fetch one row.
        # When None (e.g. when a custom subclass is constructed outside of add_to_builder,
        # or when the custom subclass's own __init__ runs before super().__init__),
        # fall back to parent_csv.data[row_index] on access.
        self.__captured_row: dict[str, Any] | None = parent_csv._current_streaming_row

        super().__init__({},
                         "application/x-database-table-row",
                         parent_id=parent_id or parent_csv[parent_csv.identifier_field].value)

    @property
    def column_names(self) -> list[str]:
        """
        :return: The ordered list of column names for this row, sourced from the parent :class:`CSVEntry`.
            This is distinct from :attr:`~nuix_nli_lib.edrm.EntryInterface.fields`, which returns the
            EDRM EntryField key names (e.g. ``'MIME Type'``, ``'SHA-1'``, ``'Name'``, etc.).
        """
        return [f for f in self.__parent_csv.row_fields if len(f.strip()) > 0]

    @property
    def data(self) -> dict[str, Any]:
        """
        Return the data for this row.  When constructed during streaming (via CSVEntry.add_to_builder),
        the row data is captured directly and returned without accessing the full data list on the parent.
        Otherwise, falls back to parent_csv.data[row_index] which may trigger a full load.
        """
        if self.__captured_row is not None:
            return self.__captured_row
        return self.__parent_csv.data[self.__row_index]

    @property
    def parent_csv(self) -> CSVEntry:
        return self.__parent_csv
