from pathlib import Path
import unittest
from datetime import datetime
from typing import Union

from nuix_nli_lib.edrm import EDRMBuilder
from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry

_RESOURCES = Path(__file__).parent / "resources"


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

    def get_base_name(self) -> str:
        """
        Not strictly necessary, but this shows the name can be constructed any way you want.  Override `get_base_name`
        rather than `get_name` so that the parent's XML and filename sanitization in `get_name` is still applied.
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

    def get_base_name(self) -> str:
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


class TestCSVRowEntryFields(unittest.TestCase):
    """Verify that CSVRowEntry.fields returns EDRM EntryField keys, not raw CSV column names."""

    def setUp(self):
        self.csv_path = str(_RESOURCES / "text_thread.csv")
        self.parent_csv = CSVEntry(self.csv_path)
        self.row = CSVRowEntry(self.parent_csv, 0)

    def test_column_names_returns_csv_headers(self):
        """column_names must return the raw CSV header names."""
        cols = self.row.column_names
        self.assertEqual(cols, ["To", "From", "Date Sent", "Message"])

    def test_fields_includes_edrm_field_names(self):
        """fields must include the required EDRM EntryField keys (was broken: only returned column names)."""
        field_names = list(self.row.fields)
        self.assertIn("MIME Type", field_names)
        self.assertIn("SHA-1", field_names)
        self.assertIn("Name", field_names)
        self.assertIn("Item Date", field_names)

    def test_set_custodian_on_csv_row_entry(self):
        """custodian setter must work on CSVRowEntry (was broken when fields returned column names)."""
        self.row.custodian = "Bob"
        self.assertEqual(self.row.custodian, "Bob")

    def test_custodian_update_does_not_duplicate_field_on_csv_row_entry(self):
        """Setting custodian twice must update in place — no duplicate custodian fields (SLC-264).

        The original bug caused a new EntryField to be appended on every setter call
        instead of updating the existing one.  This test exercises the update path in
        EntryInterface.custodian.setter (the ``if 'custodian' in self.fields`` branch).

        The update-in-place behaviour is verified by capturing the EntryField object after
        the first set and asserting it is the exact same object (assertIs) after the second
        set.  If the setter were broken and re-inserted a new EntryField, the reference would
        differ.  A simple field-count check cannot catch this regression because the backing
        store is a dict, and dict keys are inherently unique.
        """
        self.row.custodian = "Bob"
        custodian_field_after_first_set = self.row["custodian"]
        self.row.custodian = "Carol"
        self.assertEqual(self.row.custodian, "Carol", "Second custodian value must be returned by getter")
        self.assertIs(self.row["custodian"], custodian_field_after_first_set,
                      "custodian setter must update the existing EntryField in place, not replace it")

    def test_set_field_value_on_csv_row_entry(self):
        """set_field_value must not raise KeyError for valid EDRM field names on CSVRowEntry."""
        self.row.set_field_value("MIME Type", "application/octet-stream")
        self.assertEqual(self.row["MIME Type"].value, "application/octet-stream")
