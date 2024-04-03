import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
import shutil
from xml.dom.minidom import getDOMImplementation, Document, Element

import edrm
from edrm.DirectoryEntry import DirectoryEntry
from edrm.EDRMBuilder import EDRMBuilder
from edrm.EntryInterface import EntryInterface
from edrm.FileEntry import FileEntry
import edrm.EDRMUtilities as eutes


class NLIGenerator(object):
    def __init__(self):
        self.__edrm_builder = EDRMBuilder()
        self.__edrm_builder.as_nli = True

    def add_entry(self, entry: EntryInterface):
        if hasattr(entry, 'add_to_builder'):
            entry.add_to_builder(self.__edrm_builder)
        else:
            self.__edrm_builder.add_entry(entry)

    def generate_metadata_file(self, metadata_path: Path):
        metadata_file: Document = getDOMImplementation().createDocument(None, "image-metadata", None)
        property_list: Element = metadata_file.createElement('properties')

        case_element: Element = metadata_file.createElement('property')
        case_element.setAttribute("key", "case-number")
        case_element.setAttribute("value", "01")
        property_list.appendChild(case_element)

        datetime_element: Element = metadata_file.createElement('property')
        datetime_element.setAttribute("key", "creation-datetime")
        datetime_element.setAttribute("value", datetime.now().strftime('%Y/%m/%d %H:%M:%S.%f')[:-3] + " UTC")
        property_list.appendChild(datetime_element)

        sw_element: Element = metadata_file.createElement('property')
        sw_element.setAttribute("key", "creation-software-name")
        sw_element.setAttribute("value", "Nuix Memory Analysis Tool")
        property_list.appendChild(sw_element)

        swv_element: Element = metadata_file.createElement('property')
        swv_element.setAttribute("key", "creation-software-version")
        swv_element.setAttribute("value", "0.0.1")
        property_list.appendChild(swv_element)

        evidence_element: Element = metadata_file.createElement('property')
        evidence_element.setAttribute("key", "evidence-number")
        evidence_element.setAttribute("value", "01")
        property_list.appendChild(evidence_element)

        examiner_element: Element = metadata_file.createElement('property')
        examiner_element.setAttribute("key", "examiner-name")
        examiner_element.setAttribute("value", "Unknown")
        property_list.appendChild(examiner_element)

        metadata_file.documentElement.appendChild(property_list)

        metadata_file_path: Path = metadata_path / 'image_metadata.xml'
        with metadata_file_path.open(mode='w', encoding=edrm.configs['encoding']) as metadata_xml:
            metadata_file.writexml(metadata_xml, encoding=edrm.configs['encoding'], addindent='    ', newl='\n')

    def save(self, file_path: Path):
        with tempfile.TemporaryDirectory(delete=False) as temp_loc:
            temp_path = Path(temp_loc)
            build_path = temp_path / 'NLI_Gen'
            metadata_path = build_path / '.metadata'
            metadata_path.mkdir(parents=True, exist_ok=True)

            # Make the EDRM XML 1.2 file
            self.__edrm_builder.output_path = metadata_path / 'image_contents.xml'
            self.__edrm_builder.save()

            # Copy files and folders to their temp location
            entry_map = self.__edrm_builder.entry_map
            for entry in self.__edrm_builder.entry_map.values():
                if isinstance(entry, FileEntry):
                    relative_path = eutes.generate_relative_path(entry, entry_map)
                    destination_path = build_path / relative_path

                    if destination_path.parent is not None:
                        destination_path.parent.mkdir(parents=True, exist_ok=True)

                    if isinstance(entry, DirectoryEntry):
                        destination_path.mkdir(exist_ok=True)
                    else:
                        shutil.copy2(entry.file_path, destination_path)

            # make the .metadata/image_metadata.xml file
            self.generate_metadata_file(metadata_path)

            # make the .metadata/image_contents.sha1_hash file
            metadata_hash = edrm.EDRMUtilities.hash_file(self.__edrm_builder.output_path,
                                                         hashlib.sha1(),
                                                         as_string=False)
            metadata_hash_path = metadata_path / 'image_contents.sha1_hash'
            with metadata_hash_path.open(mode='wb') as metadata_hash_file:
                metadata_hash_file.write(metadata_hash)

            # Zip the contents
            temp_nli_path = temp_path / f'{file_path.stem}'
            shutil.make_archive(str(temp_nli_path), 'zip', root_dir=build_path)

            # Copy to file_path
            shutil.copy(f'{temp_nli_path}.zip', str(file_path))
