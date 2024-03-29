import hashlib
import urllib.parse
from datetime import datetime
from pathlib import Path
from xml.dom.minidom import Document, Element

import edrm.EDRMUtilities as eutes
from edrm import FieldFactory
from edrm.EntryField import EntryField
from edrm.EntryInterface import EntryInterface


class FileEntry(EntryInterface):
    def __init__(self, file_path: str, mime_type: str, parent_id: str = None):
        super().__init__()

        self.__file_path = Path(file_path).absolute().resolve()
        self.__parent_id = parent_id

        self.fill_basic_fields(mime_type)

    def fill_basic_fields(self, mime_type: str):
        self['MIME Type'] = FieldFactory.generate_field('MIME Type', EntryField.TYPE_TEXT, mime_type)
        self.__item_date = datetime.fromtimestamp(self.file_path.stat().st_ctime)
        self['Item Date'] = FieldFactory.generate_field('Item Date',
                                                        EntryField.TYPE_DATETIME,
                                                        eutes.convert_datetime_to_string(self.__item_date))
        self['Path Name'] = FieldFactory.generate_field('Path Name',
                                                        EntryField.TYPE_TEXT,
                                                        str(self.file_path.resolve().absolute()))
        self['File Accessed'] = FieldFactory.generate_field('File Accessed',
                                                            EntryField.TYPE_DATETIME,
                                                            eutes.convert_timestamp_to_string(
                                                                self.file_path.stat().st_atime))
        self['File Created'] = FieldFactory.generate_field('File Created',
                                                           EntryField.TYPE_DATETIME,
                                                           eutes.convert_timestamp_to_string(
                                                               self.file_path.stat().st_birthtime))
        self['File Modified'] = FieldFactory.generate_field('File Modified',
                                                            EntryField.TYPE_DATETIME,
                                                            eutes.convert_timestamp_to_string(
                                                                self.file_path.stat().st_mtime))
        self['File Owner'] = FieldFactory.generate_field('File Owner',
                                                         EntryField.TYPE_TEXT,
                                                         self.file_path.stat().st_creator if hasattr(
                                                             self.file_path.stat, 'st_creator') else '')
        self['Name'] = FieldFactory.generate_field('Name', EntryField.TYPE_TEXT, self.file_path.name)

        self.fill_hash_fields()

        self['File Size'] = FieldFactory.generate_field('File Size', EntryField.TYPE_INTEGER,
                                                        str(self.file_path.stat().st_size))

    def fill_hash_fields(self):
        self['SHA-1'] = FieldFactory.generate_field('SHA-1',
                                                    EntryField.TYPE_TEXT,
                                                    eutes.hash_file(self.file_path, hashlib.sha1()))

    @property
    def file_path(self):
        return self.__file_path

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

    def calculate_md5(self) -> str:
        return eutes.hash_file(self.file_path, hashlib.md5())

    def add_location_uri(self,
                         document: Document,
                         container: Element,
                         entry_map: dict[str, EntryInterface],
                         for_nli: bool):
        location_uri_element = document.createElement('LocationURI')
        if for_nli:
            location_uri = eutes.generate_relative_path(self, entry_map)
            location_uri = urllib.parse.quote_plus(location_uri, safe='/')
        else:
            location_uri = self.file_path.as_uri()

        location_uri_element.appendChild(document.createTextNode(location_uri))
        container.appendChild(location_uri_element)

    def add_file(self, document: Document, container: Element, entry_map: dict[str, EntryInterface], for_nli: bool):
        files_list = document.createElement('Files')
        container.appendChild(files_list)

        file_element = document.createElement('File')
        file_element.setAttribute('FileType', 'Native')
        files_list.appendChild(file_element)

        external_file = document.createElement('ExternalFile')
        file_element.appendChild(external_file)

        if for_nli:
            relative_path = eutes.generate_relative_path(self, entry_map)
            external_file.setAttribute('FilePath', relative_path)
        else:
            external_file.setAttribute('FilePath', str(self.file_path))

        external_file.setAttribute('FileName', self.file_path.name)
        md5 = self.calculate_md5()
        external_file.setAttribute('Hash', md5)
        external_file.setAttribute('HashType', 'MD5')
