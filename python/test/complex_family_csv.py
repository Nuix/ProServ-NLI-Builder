from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry
from nuix_nli_lib.edrm import EDRMBuilder

class ComplexFamilyCSVRowEntry(CSVRowEntry):
    # Some implementation for the complex family row
    pass

class ComplexFamilyCSVEntry(CSVEntry):
    def __init__(self, file_path: str,
                 mimetype: str = "text/csv",
                 parent_id: str = None,
                 row_generator: type[ComplexFamilyCSVRowEntry] = None,
                 delimiter = ','):
        super().__init__(file_path, mimetype, parent_id, row_generator, delimiter)
        self.__complex_generator = row_generator

    def lookup_row_parent(self, row_index) -> str | None:
        # Do work to find the parent for the row...
        pass

    def add_to_builder(self, builder:EDRMBuilder):
        row_gen = self.__complex_generator or ComplexFamilyCSVRowEntry
        builder.add_entry(self)
        for index in range(len(self.data)):
            parent_id = self.lookup_row_parent(index)
            builder.add_entry(row_gen(self, index, parent_id=parent_id))

        return self[self.identifier_field].value