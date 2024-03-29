import hashlib
from datetime import datetime
from pathlib import Path

from edrm import FieldFactory
from edrm.EntryField import EntryField
from edrm.EntryInterface import EntryInterface


class DirectoryEntry(EntryInterface):
    def __init__(self, directory_path: str, parent_id: str):
        super().__init__()

        self.__directory = Path(directory_path)
        self.__parent_id = parent_id

    def __fill_basic_fields(self) -> None:
        self['MIME Type'] = FieldFactory.generate_field('MIME Type',
                                                        EntryField.TYPE_TEXT,
                                                        'application/x-directory')
        self.__item_date = datetime.fromtimestamp(self.directory.stat().st_ctime)
        self['Item Date'] = FieldFactory.generate_field('Item Date',
                                                        EntryField.TYPE_DATETIME,
                                                        FieldFactory.convert_datetime_to_string(self.__item_date))
        self['Path Name'] = FieldFactory.generate_field('Path Name',
                                                        EntryField.TYPE_TEXT,
                                                        str(self.directory.resolve().absolute()))
        self['File Accessed'] = FieldFactory.generate_field('File Accessed',
                                                            EntryField.TYPE_DATETIME,
                                                            FieldFactory.convert_timestamp_to_string(
                                                                self.directory.stat().st_atime))
        self['File Created'] = FieldFactory.generate_field('File Created',
                                                           EntryField.TYPE_DATETIME,
                                                           FieldFactory.convert_timestamp_to_string(
                                                               self.directory.stat().st_birthtime))
        self['File Modified'] = FieldFactory.generate_field('File Modified',
                                                            EntryField.TYPE_DATETIME,
                                                            FieldFactory.convert_timestamp_to_string(
                                                                self.directory.stat().st_mtime))
        self['File Owner'] = FieldFactory.generate_field('File Owner',
                                                         EntryField.TYPE_TEXT,
                                                         self.directory.stat().st_creator if hasattr(
                                                             self.directory.stat, 'st_creator') else '')
        self['Name'] = FieldFactory.generate_field('Name', EntryField.TYPE_TEXT, self.directory.name)
        self['SHA-1'] = FieldFactory.generate_field('SHA-1',
                                                    EntryField.TYPE_TEXT,
                                                    FieldFactory.hash_directory(self.directory, hashlib.sha1()))
        self['File Size'] = FieldFactory.generate_field('File Size', EntryField.TYPE_INTEGER,
                                                        str(self.directory.stat().st_size))

    @property
    def directory(self) -> Path:
        return self.__directory

    @property
    def identifier_field(self) -> str:
        return 'SHA-1'

    @property
    def name(self) -> str:
        return self['Name'].value

    @property
    def time_field(self) -> str:
        return 'Item Date'

    @property
    def itemdate(self) -> datetime:
        return self.__item_date

    @property
    def parent(self) -> str:
        return self.__parent_id
