from typing import Any, Union
from pathlib import Path
from xml.dom.minidom import Document, Element

from nuix_nli_lib.edrm import FieldFactory, EntryField, EntryInterface, EDRMUtilities as eutes, MappingEntry
from nuix_nli_lib import edrm


class EmailFileEntry(MappingEntry):
    def __init__(self, mapping: dict[str, Any], mimetype: str, file_path: Path = None, parent_id: str = None,):
        self.__mapping: dict[str, Any] = mapping
        self.__mimetype: str = mimetype
        self.__file_path: Path = file_path
        super().__init__(mapping,mimetype,parent_id=parent_id)

    @property
    def identifier_field(self) -> str:
        return 'Message-ID'

    # @property
    # def file_path(self) -> Path:
    #     """
    #     :return: Path the file being added to the load file.
    #
    #     """
    #     return self.__file_path
    #
    # def add_file(self, document: Document, container: Element, entry_map: dict[str, EntryInterface], for_nli: bool):
    #     """
    #     See edrm.EntryInterface.add_file for details about this method.
    #
    #     As the FileEntry represents a physical file on disk, this type of Entry will provide a File element to locate
    #     it.  If the target of the EDRM load file is an NLI (for_nli=True), this method will use a relative path built
    #     from the parent entries for the file location.  Otherwise, it provides the full `file_path` property.
    #     """
    #
    #     if self.__file_path is None:
    #         super().add_file(document, container, entry_map, for_nli)
    #     else:
    #         files_list = document.createElement('Files')
    #         container.appendChild(files_list)
    #
    #         file_element = document.createElement('File')
    #         file_element.setAttribute('FileType', 'Native')
    #         files_list.appendChild(file_element)
    #
    #         external_file = document.createElement('ExternalFile')
    #         file_element.appendChild(external_file)
    #
    #         if for_nli:
    #             from nuix_nli_lib.edrm import DirectoryEntry
    #             if self.parent is None or isinstance(self.parent, DirectoryEntry):
    #                 relative_path = relative_path = Path(eutes.generate_relative_path(self, entry_map))
    #             else:
    #                 relative_path = Path("natives") / self.name
    #
    #             file_path = relative_path.parent if relative_path.parent != Path('') else ''
    #             external_file.setAttribute('FilePath', str(file_path))
    #         else:
    #             external_file.setAttribute('FilePath', str(self.file_path))
    #
    #         external_file.setAttribute('FileName', self.file_path.name)
    #         md5 = self.calculate_md5()
    #         external_file.setAttribute('Hash', md5)
    #         external_file.setAttribute('HashType', 'MD5')