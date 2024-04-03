import csv
from typing import Any

from edrm.EDRMBuilder import EDRMBuilder
from edrm.FileEntry import FileEntry
from edrm.MappingEntry import MappingEntry
import data_types


class CSVEntry(FileEntry):
    def __init__(self, file_path: str, parent_id: str = None):
        super().__init__(file_path, "text/csv", parent_id)

        self.__data: list[dict[str, Any]] = []
        self.__row_fields: list[str] = []

        if not self.file_path.is_file():
            raise IOError(f'File does not exist or is not a file: {self.file_path}')

        with self.file_path.open(mode='r', encoding=data_types.configs['encoding']) as file:
            reader: csv.DictReader = csv.DictReader(file)
            self.__row_fields = list(reader.fieldnames)
            for row in reader:
                self.__data.append(row)

    @property
    def data(self) -> list[dict[str, Any]]:
        return self.__data

    @property
    def row_fields(self) -> list[str]:
        return self.__row_fields

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'

    def add_to_builder(self, builder: EDRMBuilder) -> None:
        this_id = builder.add_entry(self)
        for index in range(len(self.data)):
            builder.add_entry(CSVRowEntry(self, index))


class CSVRowEntry(MappingEntry):
    def __init__(self, parent_csv: CSVEntry, row_index: int):
        self.__parent_csv: CSVEntry = parent_csv
        self.__row_index: int = row_index

        super().__init__({},
                         "application/x-database-table-row",
                         parent_id=parent_csv[parent_csv.identifier_field].value)

    @property
    def fields(self) -> list[str]:
        return self.__parent_csv.row_fields

    @property
    def data(self) -> dict[str, Any]:
        return self.__parent_csv.data[self.__row_index]

