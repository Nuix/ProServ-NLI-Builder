import os
from pathlib import Path
import unittest
from datetime import datetime

from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry
from nuix_nli_lib.edrm import FieldFactory, EntryField
from nuix_nli_lib.nli.nli_generator import NLIGenerator


class SanctionsEntry(CSVRowEntry):
    FILE_MIME_TYPE = 'osint/sanctionlist'
    ROW_MIME_TYPE = 'osint/sanction'

    def __init__(self, parent_csv: CSVEntry, row_index: int):
        super().__init__(parent_csv, row_index)

        self["MIME Type"] = FieldFactory.generate_field('MIME Type', EntryField.TYPE_TEXT, SanctionsEntry.ROW_MIME_TYPE)

    def get_name(self) -> str:
        return self["Name"].value

    @property
    def text(self) -> str:
        excluded_fields = ['MIME Type', 'SHA-1', 'Item Date']
        return os.linesep.join([f'{i[0]} = {i[1].value}' for i in self if i[0] not in excluded_fields])

    @property
    def time_field(self) -> str:
        return "Date of Sanction"

    @property
    def itemdate(self) -> datetime:
        return datetime.strptime(self[self.time_field].value, '%Y-%m-%d')


class SanctionsTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_data: str = r'./resources/sanctions_list.csv'
        self.output_path: Path = Path(r'./resources')

    def test_base_csv(self):
        entry = CSVEntry(self.source_data, mimetype= SanctionsEntry.FILE_MIME_TYPE, row_generator=SanctionsEntry)
        generator = NLIGenerator()
        generator.add_entry(entry)
        generator.save(self.output_path / 'sanctions.nli')

