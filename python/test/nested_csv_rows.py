from nuix_nli_lib.data_types import CSVRowEntry

class NestableProcessesCSVRowEntry(CSVRowEntry):
    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'

    @property
    def parent_process(self) -> str:
        return 'pprocess'

    def parent(self) -> str:
        pprocess = self.data.get(self.parent_process, None)
        return pprocess if pprocess else super().parent
