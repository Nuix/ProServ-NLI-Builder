import hashlib
import urllib.parse
from datetime import datetime
from pathlib import Path
from xml.dom.minidom import Document, Element

from nuix_nli_lib.edrm import FieldFactory, EntryField, EntryInterface, EDRMUtilities as eutes


class FileEntry(EntryInterface):
    """
    Represents a generic File or Document in the EDRM load file.  This is the 'default' type of EntryInterface to use
    when providing actual source evidence.

    A FileEntry will usually represent a physical file on disk, and as such will have a File element identifying its
    source data, and a LocationURI element locating the evidence in the final Case.  Generally, a FileEntry will not
    be a container, and by default has no children items.

    If the desired output structure would be:
    <code>
    Main
    |- Doc1.doc
    |- Doc2.doc
    |- Sub
      |- Doc3.doc
    </code>

    Doc1, Doc2, and Doc3 would be created as FileEntrys:
    <code>
    main = DirectoryEntry('Main')
    main_id = main[main.identifier_field].value
    doc1 = FileEntry('Doc1.doc', main_id)
    doc2 = FileEntry('Doc2.doc', main_id)
    sub = DirectoryEntry('Sub', main_id)
    sub_id = sub[sub.identifier_field].value
    doc3 = FileEntry('Doc3.doc', sub_id)
    </code>
    """

    def __init__(self, file_path: str, mime_type: str, parent_id: str = None):
        """
        :param file_path: Path, usually the full absolute path, to the file being added to the load file.
        :param mime_type: The mime-type to assign to the file.
        :param parent_id: Optional: The id of the parent to this entry.  If not provided this entry will be a top-level
                          document with no containing folder.
        """
        super().__init__()

        self.__file_path = Path(file_path).absolute().resolve()
        self.__parent_id = parent_id
        self.__item_date = None

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
                                                               getattr(self.file_path.stat(),
                                                                       'st_birthtime',
                                                                       self.file_path.stat().st_ctime)))
        self['File Modified'] = FieldFactory.generate_field('File Modified',
                                                            EntryField.TYPE_DATETIME,
                                                            eutes.convert_timestamp_to_string(
                                                                self.file_path.stat().st_mtime))
        self['File Owner'] = FieldFactory.generate_field('File Owner',
                                                         EntryField.TYPE_TEXT,
                                                         getattr(self.file_path.stat(), 'st_creator', 'Undefined'))
        self['Name'] = FieldFactory.generate_field('Name', EntryField.TYPE_TEXT, str(self.file_path.name))

        self.fill_hash_fields()

        self['File Size'] = FieldFactory.generate_field('File Size', EntryField.TYPE_INTEGER,
                                                        str(self.file_path.stat().st_size))

    def fill_hash_fields(self):
        self['SHA-1'] = FieldFactory.generate_field('SHA-1',
                                                    EntryField.TYPE_TEXT,
                                                    eutes.hash_file(self.file_path, hashlib.sha1()))

    @property
    def file_path(self) -> Path:
        """
        :return: Path the file being added to the load file.

        """
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
                         for_nli: bool) -> None:
        """
        See edrm.EntryInterface.add_location_uri for details about this method.

        As the FileEntry will have an associated File object locating the document within the source file system, it
        will also provide a LocationURL placing that object in the Case.
        """
        location_uri_element = document.createElement('LocationURI')
        if for_nli:
            location_uri = eutes.generate_relative_path(self, entry_map)
            location_uri = urllib.parse.quote_plus(location_uri, safe='/')
        else:
            location_uri = self.file_path.as_uri()

        location_uri_element.appendChild(document.createTextNode(location_uri))
        container.appendChild(location_uri_element)

    def add_file(self, document: Document, container: Element, entry_map: dict[str, EntryInterface], for_nli: bool):
        """
        See edrm.EntryInterface.add_file for details about this method.

        As the FileEntry represents a physical file on disk, this type of Entry will provide a File element to locate
        it.  If the target of the EDRM load file is an NLI (for_nli=True), this method will use a relative path built
        from the parent entries for the file location.  Otherwise, it provides the full `file_path` property.
        """
        files_list = document.createElement('Files')
        container.appendChild(files_list)

        file_element = document.createElement('File')
        file_element.setAttribute('FileType', 'Native')
        files_list.appendChild(file_element)

        external_file = document.createElement('ExternalFile')
        file_element.appendChild(external_file)

        if for_nli:
            relative_path = Path(eutes.generate_relative_path(self, entry_map))
            file_path = relative_path.parent if relative_path.parent != Path('') else ''
            external_file.setAttribute('FilePath', str(file_path))
        else:
            external_file.setAttribute('FilePath', str(self.file_path))

        external_file.setAttribute('FileName', self.file_path.name)
        md5 = self.calculate_md5()
        external_file.setAttribute('Hash', md5)
        external_file.setAttribute('HashType', 'MD5')
