from pathlib import Path
from typing import Any
from copy import deepcopy

from xml.dom.minidom import getDOMImplementation, Element, Document

from edrm.DirectoryEntry import DirectoryEntry
from edrm.EntryInterface import EntryInterface
from edrm.FileEntry import FileEntry
from edrm.MappingEntry import MappingEntry
import edrm


class EDRMBuilder:
    def __init__(self):
        self.__output_path: Path = Path("./output.xml").resolve().absolute()
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

    @property
    def entry_map(self) -> dict[str, EntryInterface]:
        """
        Retrieve a dicstionary mapping each EntryInterface to its id.  Note: the returned dictionary cannot be used to
        modify the builder's collection of entries.
        :return: dictionary of strings representing an entry's id to the corresponding EntryInterface object
        """
        return deepcopy(self.__entries)

    def add_entry(self, entry: EntryInterface) -> str:
        entry_id = entry[entry.identifier_field].value
        self.__entries[entry_id] = entry
        parent_id = entry.parent

        if entry_id not in self.__families.keys():
            self.__families[entry_id] = []

        if parent_id is not None:
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

    def __add_folder(self, doc_id: str, document: Document, container: Element, families):
        doc_element = document.createElement('Document')
        doc_element.setAttribute('DocId', doc_id)
        container.appendChild(doc_element)

        if doc_id not in families:
            return

        family = families.pop(doc_id)
        if len(family) > 0:
            folder_element = document.createElement('Folder')
            folder_element.setAttribute('FolderName', doc_id)
            container.appendChild(folder_element)

            for child in self.__families[doc_id]:
                self.__add_folder(child, document, folder_element, families)

    def build(self) -> Document:
        impl = getDOMImplementation()
        doc = impl.createDocument(None, 'Root', None)
        root = doc.documentElement

        root.setAttribute('MajorVersion', '1')
        root.setAttribute('MinorVersion', '2')
        root.setAttribute('Description', 'EDRM XML Load File')
        root.setAttribute('Locale', 'US')
        root.setAttribute('DataInterchangeType', 'Update')

        field_list = doc.createElement("Fields")
        root.appendChild(field_list)
        for entry_id, entry in self.__entries.items():
            entry.serialize_field_definitions(doc, field_list)

        batch_element = doc.createElement('Batch')
        root.appendChild(batch_element)
        doc_list = doc.createElement('Documents')
        batch_element.appendChild(doc_list)

        for entry_id, entry in self.__entries.items():
            entry.serialize_entry(doc, doc_list, self.__entries, self.as_nli)

        relationship_list = doc.createElement('Relationships')
        batch_element.appendChild(relationship_list)
        for parent_id, family in self.__families.items():
            for child_id in family:
                relationship = doc.createElement('Relationship')
                relationship.setAttribute('Type', 'Container')
                relationship.setAttribute('ParentDocId', parent_id)
                relationship.setAttribute('ChildDocId', child_id)
                relationship_list.appendChild(relationship)

        folders_list = doc.createElement('Folders')
        batch_element.appendChild(folders_list)

        working_families = deepcopy(self.__families)
        for entry_id in self.__families.keys():
            if entry_id in working_families:
                self.__add_folder(entry_id, doc, folders_list, working_families)

        return doc

    def save(self, doc: Document = None):
        if doc is None:
            doc = self.build()

        with self.output_path.open(mode='w', encoding=edrm.configs['encoding']) as load_file:
            doc.writexml(load_file, encoding=edrm.configs['encoding'], standalone=True, addindent='  ', newl='\n')
