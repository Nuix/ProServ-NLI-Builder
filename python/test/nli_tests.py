from pathlib import Path
import unittest
from datetime import datetime

from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry
from nuix_nli_lib.nli.nli_generator import NLIGenerator


class EnvEntry(CSVRowEntry):
    def __init__(self, parent_csv: CSVEntry, row_index: int):
        super().__init__(parent_csv, row_index)

    def get_name(self) -> str:
        return f'({self['PID'].value}) {self['Process'].value} [{self['Variable'].value}]'

    @property
    def text(self) -> str:
        return f'{self['Variable'].value} = {self["Value"]}'


class CCEntry(CSVRowEntry):
    def __init__(self, parent_csv: CSVEntry, row_index: int):
        super().__init__(parent_csv, row_index)

    @property
    def identifier_field(self) -> str:
        return 'Complaint ID'

    def get_name(self) -> str:
        return f'({self['Complaint ID'].value}) {self['Company'].value}'

    @property
    def text(self) -> str:
        return self['Consumer complaint narrative'].value

    @property
    def time_field(self) -> str:
        return "Date received"

    @property
    def itemdate(self) -> datetime:
        return datetime.strptime(self[self.time_field].value, '%m/%d/%y')


class PsListSimple(CSVRowEntry):
    @property
    def itemdate(self):
        return datetime.strptime(self['CreateTime'].value, '%Y-%m-%d %H:%M:%S.%f ')

    def get_name(self):
        return f'({self['PID'].value}) {self['ImageFileName'].value}'

    @ property
    def identifier_field(self):
        return 'PID'


class NLITests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.envars: str = str(Path(".", "resources", "envars.csv").absolute())
        self.pslist: str = str(Path('.', 'resources', 'windows.pslist.PsList.csv').absolute())
        self.minps: str = str(Path('.', 'resources', 'windows.pslist.MinPsList.csv').absolute())
        self.memory: str = str(Path('.', 'resources', 'example.ps1').absolute())
        self.folder: str = str(Path(".", "resources", "source").absolute())
        self.output_path: Path = Path(".", "resources", "output").absolute()

    def test_base_csv(self):
        entry = CSVEntry(self.envars, row_generator=EnvEntry)
        generator = NLIGenerator()
        generator.add_entry(entry)
        generator.save(self.output_path / 'csv_test.nli')

    def test_cc_csv(self):
        entry = CSVEntry(str(Path('.', 'resources', 'CC.Medium.csv').absolute()), row_generator=CCEntry)
        generator = NLIGenerator()
        generator.add_entry(entry)
        generator.save(self.output_path / 'cc_test.nli')

    def test_pslist1_csv(self):
        generator = NLIGenerator()
        f = generator.add_file(self.memory, 'application/x-memory-dump')
        d = generator.add_directory(self.folder)
        entry = CSVEntry(self.pslist, row_generator=PsListSimple, parent_id=d)
        generator.add_entry(entry)
        generator.save(self.output_path / 'pslist_simple.nli')

    # def test_nli_csv(self):
    #     entry = CSVEntry(self.envars)
    #     builder = EDRMBuilder()
    #     builder.as_nli = True
    #     builder.output_path = self.output_path / 'csv_nli_test.xml'
    #     entry.add_to_builder(builder)
    #     builder.save()
    #
    # def test_process_csv(self):
    #     entry = ProcessCSVEntry(self.pslist)
    #     builder = EDRMBuilder()
    #     builder.as_nli = False
    #     builder.output_path = self.output_path / 'process_test.xml'
    #     entry.add_to_builder(builder)
    #     builder.save()
    #
    # def test_process_csv_nli(self):
    #     entry = ProcessCSVEntry(self.pslist)
    #     builder = EDRMBuilder()
    #     builder.as_nli = True
    #     builder.output_path = self.output_path / 'process_nli_test.xml'
    #     entry.add_to_builder(builder)
    #     builder.save()
    #
    # def test_minprocess_csv(self):
    #     builder = EDRMBuilder()
    #     builder.as_nli = False
    #     builder.output_path = self.output_path / 'minprocess_test.xml'
    #     mem_id = builder.add_file(self.memory, 'application/octet-stream')
    #     entry = ProcessCSVEntry(self.minps, mem_id)
    #     entry.add_to_builder(builder)
    #     builder.save()
    #
    # def test_minprocess_csv_nli(self):
    #     builder = EDRMBuilder()
    #     builder.as_nli = True
    #     builder.output_path = self.output_path / 'minprocess_nli_test.xml'
    #     mem_id = builder.add_file(self.memory, 'application/octet-stream')
    #     entry = ProcessCSVEntry(self.minps, mem_id)
    #     entry.add_to_builder(builder)
    #     builder.save()
