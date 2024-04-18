import hashlib
import platform
import tempfile
from datetime import datetime
from pathlib import Path
import shutil
from typing import Any
from xml.dom.minidom import getDOMImplementation, Document, Element

from nuix_nli_lib import edrm
from nuix_nli_lib.edrm import DirectoryEntry, EDRMBuilder, EntryInterface, FileEntry, MappingEntry, EDRMUtilities as eutes


class NLIGenerator(object):
    """
    Factory for building Nuix Logical Images (NLI).  This class primarily acts as wrapper around an `edrm.EDRMBuilder`
    then adds additional metadata and packages the entries into the NLI container.

    The typical workflow is:
    <code>
    nli = NLIGenerator()
    l1 = nli.add_directory('Evidence_level_1')
    nli.add_file('doc1.txt', 'text/plain', l1)
    nli.add_file('doc2.txt', 'text/plain', l1)
    l2 = nli.add_directory('Evidence_level_2', l1)
    nli.add_file('doc3.txt', 'text/plain', l2)
    nli.save(pathlib.Path(r'C:/work/evidence/sample.nli'))
    </code>

    This would produce an NLI file names 'sample.nli' in the C:/work/evidence folder which would produce a structure
    in the case that looks like below:

    <pre>
    Evidence 1
    |- sample.nli
       |- Evidence_level_1
          |- doc1.txt
          |- doc2.txt
          |- Evidence_level_2
             |- doc3.txt
    </pre>
    """
    def __init__(self):
        self.__edrm_builder = EDRMBuilder()
        self.__edrm_builder.as_nli = True

    def add_entry(self, entry: EntryInterface) -> str:
        """
        Wrapper around `edrm.EDRMBuilder.add_entry()` to add a generic entry to the NLI container.  This method will
        check if the Entry has the `add_to_builder` method and uses that to add contents when present.  Otherwise it
        delegates to the underlying EDRMBuilder.add_entry() method.
        :param entry: The entry to add to the builder
        :return: The unique identifier of the added entry
        """
        if hasattr(entry, 'add_to_builder'):
            return entry.add_to_builder(self.__edrm_builder)
        else:
            return self.__edrm_builder.add_entry(entry)

    def add_file(self, file_path: str, mimetype: str, parent_id: str = None) -> str:
        """
        Wrapper for the `edrm.EDRMBuilder.add_file()` method
        """
        return self.__edrm_builder.add_file(file_path, mimetype, parent_id)

    def add_directory(self, directory_path: str, parent_id: str = None) -> str:
        """
        Wrapper for the `edrm.EDRMBuilder.add_directory()` method
        """
        return self.__edrm_builder.add_directory(directory_path, parent_id)

    def add_mapping(self, mapping: dict[str, Any], mimetype: str, parent_id: str = None) -> str:
        """
        Wrapper for the `edrm.EDRMBuilder.add_mapping()` method
        """
        return self.__edrm_builder.add_mapping(mapping, mimetype, parent_id)

    def generate_metadata_file(self, metadata_path: Path):
        """
        Generate the content_metadata.xml file for the NLI container and stores it in the provided metadata_path.
        :param metadata_path: The ._metadata path for the NLI container, used to store the metadata file.
        :return: None
        """
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
        """
        Build and save the NLI container to the provided file_path.

        This method will trigger the build process, which will build the underlying EDRM XML load file, copy contents
        to the NLI container, package the container, and store it to the file_path provided.
        :param file_path: Path to the location the NLI file should be saved, including the file name and extension
        :return: None
        """
        with tempfile.TemporaryDirectory(delete=False) as temp_loc:
            temp_path = Path(temp_loc)
            build_path = temp_path / 'NLI_Gen'
            metadata_path = build_path / '._metadata'
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
                elif isinstance(entry, MappingEntry):
                    if entry.text is not None:
                        # More likely than files to cause name collisions.  Use ID as the file name
                        mapping_path = build_path / "natives" / entry[entry.identifier_field].value
                        mapping_path.parent.mkdir(parents=True, exist_ok=True)
                        if platform.system() == 'Windows':
                            mapping_path = Path(f'\\\\?\\{mapping_path}')

                        with mapping_path.open(mode='w', encoding=edrm.configs['encoding']) as map_file:
                            map_file.write(entry.text)

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
