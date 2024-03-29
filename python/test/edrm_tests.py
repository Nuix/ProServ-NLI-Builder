import pathlib
import unittest

from edrm.DirectoryEntry import DirectoryEntry
from edrm.EDRMBuilder import EDRMBuilder
from edrm.FileEntry import FileEntry
from edrm.MappingEntry import MappingEntry


class TestEDRM(unittest.TestCase):

    def test_simple_file(self):
        file = r'C:\projects\proserv\Koblenz\example.ps1'

        file_entry = FileEntry(file, "application/powershell_script")
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\edrm_test.xml')
        builder.add_entry(file_entry)
        builder.save()

    def test_nli_file(self):
        file = r'C:\projects\proserv\Koblenz\example.ps1'

        file_entry = FileEntry(file, "application/powershell_script")
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\nli_test.xml')
        builder.add_entry(file_entry)
        builder.save()

    def test_simple_directory(self):
        file = r'C:\projects\proserv\Koblenz\output\certificates'

        dir_entry = DirectoryEntry(file)
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\dir_test.xml')
        builder.add_entry(dir_entry)
        builder.save()

    def test_nli_directory(self):
        file = r'C:\projects\proserv\Koblenz\output\certificates'

        dir_entry = DirectoryEntry(file)
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\dir_nli_test.xml')
        builder.add_entry(dir_entry)
        builder.save()

    def test_simple_mapping(self):
        data = {'a': 1, 'b': 2}

        mapping_entry = MappingEntry(data, "application/x-database-table-row")
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\map_test.xml')
        builder.add_entry(mapping_entry)
        builder.save()

    def test_nli_mapping(self):
        data = {'a': 1, 'b': 2}

        mapping_entry = MappingEntry(data, "application/x-database-table-row")
        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\map_nli_test.xml')
        builder.add_entry(mapping_entry)
        builder.save()

    def test_file_with_mapping(self):
        file = r'C:\projects\proserv\Koblenz\example.ps1'
        data = {'a': 1, 'b': 2}

        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\file_and_map_test.xml')
        file_id = builder.add_file(file, "application/powershell_script")
        map_id = builder.add_mapping(data, "application/x-database-table-row", file_id)
        builder.save()

    def test_file_with_map_nli(self):
        file = r'C:\projects\proserv\Koblenz\example.ps1'
        data = {'a': 1, 'b': 2}

        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\file_and_map_nli_test.xml')
        file_id = builder.add_file(file, "application/powershell_script")
        map_id = builder.add_mapping(data, "application/x-database-table-row", file_id)
        builder.save()

    def test_file_in_folder(self):
        file = r'C:\projects\proserv\Koblenz\example.ps1'
        folder = r'C:\projects\proserv\Koblenz\output\certificates'

        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\file_and_folder_test.xml')
        folder_id = builder.add_directory(folder)
        file_id = builder.add_file(file, "application/powershell_script", folder_id)
        builder.save()

    def test_file_in_folder_nli(self):
        file = r'C:\projects\proserv\Koblenz\example.ps1'
        folder = r'C:\projects\proserv\Koblenz\output\certificates'

        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\file_and_folder_nli_test.xml')
        folder_id = builder.add_directory(folder)
        file_id = builder.add_file(file, "application/powershell_script", folder_id)
        builder.save()

    def test_file_in_folder_with_mapping(self):
        file = r'C:\projects\proserv\Koblenz\example.ps1'
        folder = r'C:\projects\proserv\Koblenz\output\certificates'
        data = {'a': 1, 'b': 2}

        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\file_and_folder_and_map_test.xml')
        folder_id = builder.add_directory(folder)
        file_id = builder.add_file(file, "application/powershell_script", parent_id=folder_id)
        map_id = builder.add_mapping(data, "application/x-database-table-row", parent_id=file_id)
        builder.save()

    def test_file_in_folder_with_mapping_nli(self):
        file = r'C:\projects\proserv\Koblenz\example.ps1'
        folder = r'C:\projects\proserv\Koblenz\output\certificates'
        data = {'a': 1, 'b': 2}

        builder = EDRMBuilder()
        builder.as_nli = True
        builder.output_path = pathlib.Path(r'C:\projects\proserv\Koblenz\output\file_and_folder_and_map_nli_test.xml')
        folder_id = builder.add_directory(folder)
        file_id = builder.add_file(file, "application/powershell_script", parent_id=folder_id)
        map_id = builder.add_mapping(data, "application/x-database-table-row", parent_id=file_id)
        builder.save()
