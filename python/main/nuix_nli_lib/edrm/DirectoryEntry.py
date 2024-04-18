import hashlib
from pathlib import Path

from nuix_nli_lib.edrm import EDRMUtilities as eutes
from nuix_nli_lib.edrm import FieldFactory, EntryField, FileEntry


class DirectoryEntry(FileEntry):
    """
    Represents a Directory entry in the EDRM load file reflecting a folder or directory in the Case rather than on
    the source file system.

    The DirectoryEntry will be used as a Folder layer for Container-type relationships and will not have a native
    document associated with it.  It is generally used as a parent for other entries.  The DirectoryEntry will have
    a SHA-1 and/or calculated from the contents of all the non-empty files in it (recursively through subdirectories).

    If the desired output structure would be:
    <code>
    Main
    |- Doc1.doc
    |- Doc2.doc
    |- Sub
      |- Doc3.doc
    </code>

    Then both Main, and Sub would be created as DirectoryEntrys:
    <code>
    main = DirectoryEntry('Main')                 # Note: This is not the best way to add a directory or file entry
    main_id = main[main.identifier_field].value   # See the EDRMBuilder class for better options, especially around
    doc1 = FileEntry('Doc1.doc', main_id)         # getting the ids for the parent items.
    doc2 = FileEntry('Doc2.doc', main_id)
    sub = DirectoryEntry('Sub', main_id)
    sub_id = sub[sub.identifier_field].value
    doc3 = FileEntry('Doc3.doc', sub_id)
    </code>

    """

    def __init__(self, directory_path: str, parent_id: str = None):
        """
        :param directory_path: The name of the directory to create the entry for.  Note, this SHOULD be a relative path.
                               and usually should be a single layer.  If nested directories are needed, each should be
                               added as a separate entry.
        :param parent_id: Unique identifier for the parent of this directory.  If not specified, this will be added at
                          the top level of the load file.
        """
        self.__directory = Path(directory_path)
        super().__init__(directory_path, 'filesystem/directory', parent_id)

    def fill_hash_fields(self) -> None:
        self['SHA-1'] = FieldFactory.generate_field('SHA-1',
                                                    EntryField.TYPE_TEXT,
                                                    eutes.hash_directory(self.directory, hashlib.sha1()))

    @property
    def directory(self) -> Path:
        return self.__directory

    def add_file(self, document, container, entry_map: dict[str, object], for_nli: bool) -> None:
        # No Native for a directory
        return

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'

    def calculate_md5(self) -> str:
        return eutes.hash_directory(self.file_path, hashlib.md5())