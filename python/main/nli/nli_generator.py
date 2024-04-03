import tempfile
from pathlib import Path
import shutil

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

    def save(self, file_path: Path):
        with tempfile.TemporaryDirectory() as build_loc:
            build_path = Path(build_loc)
            metadata_path = build_path / '.metadata'
            metadata_path.mkdir(parents=True, exist_ok=True)
            self.__edrm_builder.output_path = metadata_path / 'image_contents.xml'
            self.__edrm_builder.save()

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
            # make the .metadata/image_contents.sha1_hash file
            # Zip the contents
            # Copy to file_path