import os
from pathlib import Path
import unittest
from datetime import datetime

from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry
from nuix_nli_lib.edrm import FieldFactory, EntryField, FieldType
from nuix_nli_lib.nli.nli_generator import NLIGenerator


class TextEntry(CSVRowEntry):
    FILE_MIME_TYPE = 'application/x-chat-conversation'
    ROW_MIME_TYPE = 'application/x-chat-message'
    UID = '9ec3e307-2f3d-4d62-b62a-04aa78b5bd36'

    def __init__(self, parent_csv: CSVEntry, row_index: int):
        super().__init__(parent_csv, row_index)

        self["MIME Type"] = FieldFactory.generate_field('MIME Type', FieldType.TEXT, TextEntry.ROW_MIME_TYPE)

    def get_base_name(self) -> str:
        return f'({self["Date Sent"].value}) {self["From"].value}'

    @property
    def text(self) -> str:
        return self["Message"].value

    @property
    def time_field(self) -> str:
        # This test stub always returns a valid field name — no None guard needed.
        # (EntryInterface.time_field is -> str; only MappingEntry uses Union[str, None].)
        return "Date Sent"

    @property
    def itemdate(self) -> datetime:
        return datetime.strptime(self[self.time_field].value, '%Y-%m-%d %H:%M:%S')


class SanctionsTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_data: str = r'./resources/text_thread.csv'
        self.output_path: Path = Path(r'./resources')

    def test_base_csv(self):
        entry = CSVEntry(self.source_data, mimetype=TextEntry.FILE_MIME_TYPE, row_generator=TextEntry)
        generator = NLIGenerator()
        generator.add_entry(entry)
        generator.save(self.output_path / 'texts.nli')

