from pathlib import Path
import unittest
from datetime import datetime, timezone, timedelta
from typing import Any

from nuix_nli_lib.edrm import DirectoryEntry, EDRMBuilder, FileEntry, MappingEntry
from nuix_nli_lib.edrm import EDRMUtilities as eutes


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


class TestDatetimeUTCAware(unittest.TestCase):
    """Tests for UTC-aware datetime handling in EDRMUtilities."""

    def test_naive_datetime_formatted_as_utc(self):
        """A timezone-naive datetime is treated as UTC and the output ends with +00:00."""
        dt = datetime(2024, 6, 15, 12, 30, 45, 123000)
        result = eutes.convert_datetime_to_string(dt)
        self.assertTrue(result.endswith('+00:00'),
                        f"Expected +00:00 suffix for naive datetime, got: {result}")
        self.assertIn('2024-06-15T12:30:45.123', result)

    def test_utc_aware_datetime_formatted_correctly(self):
        """A UTC-aware datetime is formatted identically to its naive equivalent."""
        naive_dt = datetime(2024, 6, 15, 12, 30, 45, 123000)
        aware_dt = datetime(2024, 6, 15, 12, 30, 45, 123000, tzinfo=timezone.utc)
        naive_result = eutes.convert_datetime_to_string(naive_dt)
        aware_result = eutes.convert_datetime_to_string(aware_dt)
        self.assertEqual(naive_result, aware_result,
                         "UTC-aware and naive datetimes with the same wall-clock time should format identically")

    def test_non_utc_aware_datetime_converted_to_utc(self):
        """A timezone-aware datetime in a non-UTC zone is correctly converted to UTC before formatting."""
        # UTC+10 means wall clock is 10 hours ahead of UTC; so 22:00 local = 12:00 UTC
        plus_ten = timezone(timedelta(hours=10))
        aware_dt = datetime(2024, 6, 15, 22, 30, 45, 123000, tzinfo=plus_ten)
        result = eutes.convert_datetime_to_string(aware_dt)
        self.assertTrue(result.endswith('+00:00'),
                        f"Expected +00:00 suffix for non-UTC aware datetime, got: {result}")
        # The UTC equivalent of 22:30:45 UTC+10 is 12:30:45 UTC
        self.assertIn('2024-06-15T12:30:45.123', result,
                      f"Expected UTC wall-clock time 12:30:45, got: {result}")

    def test_convert_timestamp_to_string_produces_utc(self):
        """convert_timestamp_to_string produces a UTC-normalised string for a known epoch value."""
        # Unix epoch 0 = 1970-01-01T00:00:00 UTC
        result = eutes.convert_timestamp_to_string(0.0)
        self.assertTrue(result.endswith('+00:00'),
                        f"Expected +00:00 suffix for epoch timestamp, got: {result}")
        self.assertIn('1970-01-01T00:00:00.000', result,
                      f"Expected epoch UTC string, got: {result}")

    def test_convert_timestamp_to_string_matches_utc_aware_datetime(self):
        """convert_timestamp_to_string result matches convert_datetime_to_string on a UTC-aware datetime."""
        ts = 1718454645.123
        ts_result = eutes.convert_timestamp_to_string(ts)
        dt_result = eutes.convert_datetime_to_string(datetime.fromtimestamp(ts, tz=timezone.utc))
        self.assertEqual(ts_result, dt_result,
                         "convert_timestamp_to_string and convert_datetime_to_string(utc_aware) should agree")
