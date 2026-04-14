from pathlib import Path
import unittest
from datetime import datetime
from typing import Union

from nuix_nli_lib.edrm import EDRMBuilder
from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry


class ProcessEntry(CSVRowEntry):
    """
    This is an example CSVEntry / MappingEntry which allows parent-child relationships between rows in the data.  It
    uses the CSV value 'PPID' to identify the parent row, and if that isn't known, then uses the CSV file itself as the
    parent.

    This would be about as full-featured as a subclass for a CSVEntry needs to get.
    """
    def __init__(self, parent_csv: CSVEntry, row_index: int):
        ppid = parent_csv.data[row_index]['PPID']
        known_ppid = len([row for row in parent_csv.data if row['PID'] == ppid]) > 0

        super().__init__(parent_csv, row_index, parent_id=ppid if known_ppid else None)

    @property
    def identifier_field(self) -> str:
        """
        Override the identifier field so it can be predictably used when looking up the parent / child relationship.
        The child will have the parent's PID stored as its PPID, so using PID as the unique identifier simplifies the
        lookup.
        """
        return 'PID'

    def get_name(self) -> str:
        """
        Not strictly necessary, but this shows the name can be constructed any way you want.  Reminder to use the
        `get_name` method to override name generation as the calculated value may need to be corrected in various ways
        """
        return f'({self['PID'].value}) {self['ImageFileName'].value}'

    @property
    def time_field(self) -> str:
        """
        Not technically required, as it matches the `edrm.configs` value but specified for completeness
        """
        return 'CreateTime'

    @property
    def itemdate(self) -> datetime:
        """
        Again, not technically required, as it matches the default behavior, but specified for completeness.
        """
        return datetime.strptime(self['CreateTime'].value.strip(), '%Y-%m-%d %H:%M:%S.%f')

    @property
    def text(self) -> Union[str, None]:
        """
        For this particular CSV, there is no meaningful text content, just fields, so don't return any text.
        """
        return None

    def add_as_parent_path(self, existing_path: str):
        """
        A mapping isn't usually capable of being a parent, but in this case it is, so override this method to add it
        as a parent to a child's relative path.
        """
        return f'{self.name}/{existing_path}'


class EnvEntry(CSVRowEntry):
    """
    This is a simpler example of a CSVRowEntry subclass.  This one overrides how the name is generated, and what text
    to use as the content.
    """
    def __init__(self, parent_csv: CSVEntry, row_index: int):
        super().__init__(parent_csv, row_index)

    def get_name(self) -> str:
        return f'({self['PID'].value}) {self['Process'].value} [{self['Variable'].value}]'

    @property
    def text(self) -> Union[str, None]:
        return f'({self['Variable'].value})={self['Value'].value}'


class CSVTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.envars: str = r'\\innovation.nuix.com\SharedFolder\Koblenz\data\envars.csv'
        self.pslist: str = r'\\innovation.nuix.com\SharedFolder\Koblenz\data\pslist.csv'
        self.minps: str = r'C:\projects\proserv\Koblenz\NuixMemoryAnalysis\running\physmem.raw\windows.pslist.MinPsList.csv'
        self.memory: str = r'C:\projects\proserv\Koblenz\example.ps1'
        self.output_path: Path = Path(r'C:\projects\proserv\Koblenz\output')

    def test_base_csv(self):
        entry = CSVEntry(self.envars)
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'csv_test.xml'
        entry.add_to_builder(builder)
        builder.save()

    def test_nli_csv(self):
        entry = CSVEntry(self.envars)
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'csv_nli_test.xml'
        entry.add_to_builder(builder)
        builder.save()

    def test_generator_csv(self):
        entry = CSVEntry(self.envars, row_generator=EnvEntry)
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'gen_test.xml'
        entry.add_to_builder(builder)
        builder.save()

    def test_process_csv(self):
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'process_test.xml'
        entry = CSVEntry(self.pslist, row_generator=ProcessEntry)
        entry.add_to_builder(builder)
        builder.save()

    def test_process_csv_nli(self):
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'process_nli_test.xml'
        entry = CSVEntry(self.pslist, row_generator=ProcessEntry)
        entry.add_to_builder(builder)
        builder.save()

    def test_minprocess_csv(self):
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'minprocess_test.xml'
        mem_id = builder.add_file(self.memory, 'application/octet-stream')
        entry = CSVEntry(self.pslist, row_generator=ProcessEntry, parent_id=mem_id)
        entry.add_to_builder(builder)
        builder.save()

    def test_minprocess_csv_nli(self):
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'minprocess_nli_test.xml'
        mem_id = builder.add_file(self.memory, 'application/octet-stream')
        entry = CSVEntry(self.pslist, row_generator=ProcessEntry, parent_id=mem_id)
        entry.add_to_builder(builder)
        builder.save()
