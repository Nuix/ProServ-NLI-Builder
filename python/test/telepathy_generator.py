from datetime import datetime
from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry
from nuix_nli_lib.edrm import FieldFactory, EntryField

class TelepathyEntry(CSVRowEntry):
    FILE_MIME_TYPE = 'application/x-chat-conversation'
    ROW_MIME_TYPE = 'application/x-chat-message'

    def __init__(self, parent_csv: CSVEntry, row_index: int):
        name = parent_csv.data[row_index]["Display_name"].strip()
        parent_csv.data[row_index]["From"] = name if len(name) > 0 else f"User #{parent_csv.data[row_index]['User ID']}"
        parent_csv.data[row_index]["App"] = "Telegram"
        parent_csv.data[row_index]["Mime Type"] = [TelepathyEntry.ROW_MIME_TYPE]
        super().__init__(parent_csv, row_index)

        # self["MIME Type"] = FieldFactory.generate_field('MIME Type', EntryField.TYPE_TEXT, TelepathyEntry.ROW_MIME_TYPE)
        # self["From"] = FieldFactory.generate_field('From', EntryField.TYPE_TEXT, parent_csv.data[row_index]["Display_name"])

    def get_name(self) -> str:
        return f'({self["Timestamp"].value}) {self["Display_name"].value}'

    @property
    def text(self) -> str:
        return self["Message_text"].value

    @property
    def time_field(self) -> str:
        return "Timestamp"

    @property
    def itemdate(self) -> datetime:
        return datetime.strptime(self[self.time_field].value, '%Y-%m-%dT%H:%M:%S+00:00')

    @property
    def identifier_field(self):
        return 'Message ID'

    def add_as_parent_path(self, existing_path: str):
        return f'{self[self.identifier_field].value}/{existing_path}'
