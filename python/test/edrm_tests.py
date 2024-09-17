from pathlib import Path
import unittest
from typing import Any

from nuix_nli_lib.edrm import DirectoryEntry, EDRMBuilder, FileEntry, MappingEntry


class TestEDRM(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sample_directory: str = str(Path(".", "resources", "certificates").absolute())
        self.sample_file: str = str(Path(".", "resources", "top-level-MD5-digests.txt").absolute())
        self.sample_mapping: dict[str, Any] = {'a': 1, 'b': 2}
        self.output_path: Path = Path(".", "resources", "output").absolute()

    def test_simple_file(self):
        file_entry = FileEntry(self.sample_file, "plain/text")
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'edrm_test.xml'
        builder.add_entry(file_entry)
        builder.save()

    def test_nli_file(self):
        file_entry = FileEntry(self.sample_file, "application/powershell_script")
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'nli_test.xml'
        builder.add_entry(file_entry)
        builder.save()

    def test_simple_directory(self):
        dir_entry = DirectoryEntry(self.sample_directory)
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'dir_test.xml'
        builder.add_entry(dir_entry)
        builder.save()

    def test_nli_directory(self):
        dir_entry = DirectoryEntry(self.sample_directory)
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'dir_nli_test.xml'
        builder.add_entry(dir_entry)
        builder.save()

    def test_simple_mapping(self):
        mapping_entry = MappingEntry(self.sample_mapping, "application/x-database-table-row")
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'map_test.xml'
        builder.add_entry(mapping_entry)
        builder.save()

    def test_nli_mapping(self):
        mapping_entry = MappingEntry(self.sample_mapping, "application/x-database-table-row")
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'map_nli_test.xml'
        builder.add_entry(mapping_entry)
        builder.save()

    def test_file_with_mapping(self):
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'file_and_map_test.xml'
        file_id = builder.add_file(self.sample_file, "application/powershell_script")
        map_id = builder.add_mapping(self.sample_mapping, "application/x-database-table-row", file_id)
        builder.save()

    def test_file_with_map_nli(self):
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'file_and_map_nli_test.xml'
        file_id = builder.add_file(self.sample_file, "application/powershell_script")
        map_id = builder.add_mapping(self.sample_mapping, "application/x-database-table-row", file_id)
        builder.save()

    def test_file_in_folder(self):
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'file_and_folder_test.xml'
        folder_id = builder.add_directory(self.sample_directory)
        file_id = builder.add_file(self.sample_file, "application/powershell_script", folder_id)
        builder.save()

    def test_file_in_folder_nli(self):
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'file_and_folder_nli_test.xml'
        folder_id = builder.add_directory(self.sample_directory)
        file_id = builder.add_file(self.sample_file, "application/powershell_script", folder_id)
        builder.save()

    def test_file_in_folder_with_mapping(self):
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = self.output_path / 'file_and_folder_and_map_test.xml'
        folder_id = builder.add_directory(self.sample_directory)
        file_id = builder.add_file(self.sample_file, "application/powershell_script", parent_id=folder_id)
        map_id = builder.add_mapping(self.sample_mapping, "application/x-database-table-row", parent_id=file_id)
        builder.save()

    def test_file_in_folder_with_mapping_nli(self):
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = self.output_path / 'file_and_folder_and_map_nli_test.xml'
        folder_id = builder.add_directory(self.sample_directory)
        file_id = builder.add_file(self.sample_file, "application/powershell_script", parent_id=folder_id)
        map_id = builder.add_mapping(self.sample_mapping, "application/x-database-table-row", parent_id=file_id)
        builder.save()
