import hashlib
from pathlib import Path

import edrm.EDRMUtilities as eutes
from edrm import FieldFactory
from edrm.EntryField import EntryField
from edrm.FileEntry import FileEntry


class DirectoryEntry(FileEntry):
    def __init__(self, directory_path: str, parent_id: str = None):
        self.__directory = Path(directory_path)
        super().__init__(directory_path, 'filesystem/directory', parent_id)

    def fill_hash_fields(self) -> None:
        self['SHA-1'] = FieldFactory.generate_field('SHA-1',
                                                    EntryField.TYPE_TEXT,
                                                    eutes.hash_directory(self.directory, hashlib.sha1()))

    @property
    def directory(self) -> Path:
        return self.__directory

    def add_as_parent_path(self, existing_path: str):
        return self.name + '/' + existing_path

    def calculate_md5(self) -> str:
        return eutes.hash_directory(self.file_path, hashlib.md5())