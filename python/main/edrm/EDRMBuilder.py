from pathlib import Path
from typing import Any

from edrm.DirectoryEntry import DirectoryEntry
from edrm.EntryInterface import EntryInterface
from edrm.FileEntry import FileEntry
from edrm.MappingEntry import MappingEntry


class EDRMBuilder:
    def __init__(self):
        self.__output_path: Path = Path("./output.xml")
        self.__as_nli: bool = False

        self.__entries: dict[str, EntryInterface] = {}
        self.__families: dict[str, list[str]] = {}

    @property
    def output_path(self) -> Path:
        return self.__output_path

    @output_path.setter
    def output_path(self, output_path: Path) -> None:
        self.__output_path = output_path

    @property
    def as_nli(self) -> bool:
        return self.__as_nli

    @as_nli.setter
    def as_nli(self, as_nli: bool) -> None:
        self.__as_nli = as_nli

    def add_entry(self, entry: EntryInterface, parent_id: str = None) -> str:
        entry_id = entry[entry.identifier_field].value
        self.__entries[entry_id] = entry

        if parent_id is None:
            self.__families[entry.parent_id].append(entry_id)
        else:
            family = self.__families.get(parent_id, [])
            family.append(entry_id)
            self.__families[parent_id] = family

        return entry_id

    def add_file(self, file_path: str, mimetype: str, parent_id: str = None) -> str:
        return self.add_entry(FileEntry(file_path, mimetype, parent_id))

    def add_directory(self, directory: str, parent_id: str = None) -> str:
        return self.add_entry(DirectoryEntry(directory, parent_id))

    def add_mapping(self, mapping: dict[str, Any], mimetype: str, parent_id: str = None) -> str:
        return self.add_entry(MappingEntry(mapping, mimetype, parent_id))
