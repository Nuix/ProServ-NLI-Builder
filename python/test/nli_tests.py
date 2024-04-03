from pathlib import Path
import unittest
from datetime import datetime

from edrm.EDRMBuilder import EDRMBuilder
from data_types.csv_file import CSVEntry, CSVRowEntry
from nli.nli_generator import NLIGenerator


class ProcessEntry(CSVRowEntry):
    def __init__(self, parent_csv: CSVEntry, row_index: int, parent_id: str):
        super().__init__(parent_csv, row_index)
        self.__parent_id = parent_id

    @property
    def identifier_field(self) -> str:
        return 'PID'

    @property
    def name(self) -> str:
        return f'({self['PID'].value}) {self['ImageFileName'].value}'

    @property
    def parent(self) -> str:
        return self.__parent_id

    @property
    def time_field(self) -> str:
        return 'CreateTime'

    @property
    def itemdate(self) -> datetime:
        return datetime.strptime(self['CreateTime'].value.strip(), '%Y-%m-%d %H:%M:%S.%f')

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'


class ProcessCSVEntry(CSVEntry):
    def add_to_builder(self, builder: EDRMBuilder) -> None:
        known_pids = sorted([row['PID'] for row in self.data])
        this_id = builder.add_entry(self)
        for index in range(len(self.data)):
            ppid = self.data[index]['PPID']
            parent_id = ppid if ppid in known_pids else this_id
            builder.add_entry(ProcessEntry(self, index, parent_id))


class NLITests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.envars: str = r'\\innovation.nuix.com\SharedFolder\Koblenz\data\envars.csv'
        self.pslist: str = r'\\innovation.nuix.com\SharedFolder\Koblenz\data\pslist.csv'
        self.minps: str = r'C:\projects\proserv\Koblenz\NuixMemoryAnalysis\running\physmem.raw\windows.pslist.MinPsList.csv'
        self.memory: str = r'C:\projects\proserv\Koblenz\example.ps1'
        self.output_path: Path = Path(r'C:\projects\proserv\Koblenz\output')

    def test_base_csv(self):
        entry = CSVEntry(self.envars)
        generator = NLIGenerator()
        generator.add_entry(entry)
        generator.save(self.output_path / 'csv_test.nli')

    def test_nli_csv(self):
        entry = CSVEntry(self.envars)
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'csv_nli_test.xml'
        entry.add_to_builder(builder)
        builder.save()

    def test_process_csv(self):
        entry = ProcessCSVEntry(self.pslist)
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'process_test.xml'
        entry.add_to_builder(builder)
        builder.save()

    def test_process_csv_nli(self):
        entry = ProcessCSVEntry(self.pslist)
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'process_nli_test.xml'
        entry.add_to_builder(builder)
        builder.save()

    def test_minprocess_csv(self):
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'minprocess_test.xml'
        mem_id = builder.add_file(self.memory, 'application/octet-stream')
        entry = ProcessCSVEntry(self.minps, mem_id)
        entry.add_to_builder(builder)
        builder.save()

    def test_minprocess_csv_nli(self):
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'minprocess_nli_test.xml'
        mem_id = builder.add_file(self.memory, 'application/octet-stream')
        entry = ProcessCSVEntry(self.minps, mem_id)
        entry.add_to_builder(builder)
        builder.save()
