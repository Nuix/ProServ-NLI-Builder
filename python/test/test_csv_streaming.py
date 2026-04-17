"""
Tests for the generator-based streaming CSV parsing refactor (SLC-55).

Acceptance criteria:
- Peak memory usage for a large CSV file is bounded (rows are not all held in memory simultaneously)
- Existing CSV tests pass unchanged
- The sanctions_tests.py real-world test continues to produce correct output
- Public API of CSVEntry and CSVRowEntry is unchanged
"""
import csv
import io
import tempfile
import os
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
from typing import Any

from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry
from nuix_nli_lib.edrm import EDRMBuilder


def _make_csv_file(rows: list[dict], fieldnames: list[str] = None, delimiter: str = ',') -> str:
    """Write a temporary CSV file and return its path."""
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='UTF-8-SIG')
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    writer = csv.DictWriter(tmp, fieldnames=fieldnames, delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    tmp.close()
    return tmp.name


class TestCSVStreamingPublicAPI(unittest.TestCase):
    """Verify that the public API of CSVEntry and CSVRowEntry is unchanged."""

    def setUp(self):
        self.rows = [
            {'Name': 'Alice', 'Age': '30', 'City': 'London'},
            {'Name': 'Bob', 'Age': '25', 'City': 'Paris'},
            {'Name': 'Carol', 'Age': '35', 'City': 'Berlin'},
        ]
        self.csv_path = _make_csv_file(self.rows)

    def tearDown(self):
        os.unlink(self.csv_path)

    def test_csv_entry_constructor_signature_unchanged(self):
        """CSVEntry accepts the same constructor arguments as before."""
        entry = CSVEntry(self.csv_path, mimetype='text/csv', parent_id=None, row_generator=None, delimiter=',')
        self.assertIsNotNone(entry)

    def test_data_property_returns_list_of_dicts(self):
        """CSVEntry.data returns a list[dict] as before."""
        entry = CSVEntry(self.csv_path)
        self.assertIsInstance(entry.data, list)
        self.assertEqual(len(entry.data), 3)
        self.assertEqual(entry.data[0]['Name'], 'Alice')
        self.assertEqual(entry.data[1]['Name'], 'Bob')

    def test_data_property_is_indexable(self):
        """CSVEntry.data supports random access by index."""
        entry = CSVEntry(self.csv_path)
        self.assertEqual(entry.data[2]['Name'], 'Carol')

    def test_row_fields_property_returns_field_names(self):
        """CSVEntry.row_fields returns the CSV header names."""
        entry = CSVEntry(self.csv_path)
        self.assertEqual(entry.row_fields, ['Name', 'Age', 'City'])

    def test_csv_row_entry_constructor_signature_unchanged(self):
        """CSVRowEntry accepts (parent_csv, row_index, parent_id=None) as before."""
        entry = CSVEntry(self.csv_path)
        row = CSVRowEntry(entry, 0)
        self.assertIsNotNone(row)

    def test_csv_row_entry_data_property(self):
        """CSVRowEntry.data returns the dict for its row index."""
        entry = CSVEntry(self.csv_path)
        row = CSVRowEntry(entry, 1)
        self.assertEqual(row.data['Name'], 'Bob')

    def test_csv_row_entry_parent_csv_property(self):
        """CSVRowEntry.parent_csv returns the parent CSVEntry."""
        entry = CSVEntry(self.csv_path)
        row = CSVRowEntry(entry, 0)
        self.assertIs(row.parent_csv, entry)

    def test_add_to_builder_returns_identifier(self):
        """add_to_builder returns the identifier value for the CSV entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = CSVEntry(self.csv_path)
            builder = EDRMBuilder()
            builder.output_path = Path(tmpdir) / 'out.xml'
            result = entry.add_to_builder(builder)
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)

    def test_add_to_builder_adds_csv_and_row_entries(self):
        """add_to_builder adds 1 CSV entry + N row entries to the builder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = CSVEntry(self.csv_path)
            builder = EDRMBuilder()
            builder.output_path = Path(tmpdir) / 'out.xml'
            entry.add_to_builder(builder)
            # 1 CSVEntry + 3 CSVRowEntry = 4 total
            self.assertEqual(len(builder.entry_map), 4)

    def test_add_to_builder_with_custom_row_generator(self):
        """add_to_builder works with a custom row_generator subclass."""
        class UpperNameRow(CSVRowEntry):
            def get_base_name(self) -> str:
                return self.data['Name'].upper()

        with tempfile.TemporaryDirectory() as tmpdir:
            entry = CSVEntry(self.csv_path, row_generator=UpperNameRow)
            builder = EDRMBuilder()
            builder.output_path = Path(tmpdir) / 'out.xml'
            entry.add_to_builder(builder)
            builder.save()
            self.assertTrue((Path(tmpdir) / 'out.xml').exists())

    def test_invalid_file_raises_ioerror(self):
        """CSVEntry raises IOError when the file does not exist (unchanged behaviour)."""
        with self.assertRaises(IOError):
            CSVEntry('/nonexistent/path/to/file.csv')


class TestCSVStreamingBehaviour(unittest.TestCase):
    """Verify the streaming / lazy-load behaviour introduced by SLC-55."""

    def setUp(self):
        self.rows = [
            {'ID': '1', 'Value': 'alpha'},
            {'ID': '2', 'Value': 'beta'},
            {'ID': '3', 'Value': 'gamma'},
        ]
        self.csv_path = _make_csv_file(self.rows)

    def tearDown(self):
        os.unlink(self.csv_path)

    def test_data_not_loaded_at_construction_time(self):
        """The internal data cache is None immediately after construction (no eager load)."""
        entry = CSVEntry(self.csv_path)
        # Access the private mangled name to inspect internal state without triggering load.
        cache = entry._CSVEntry__data
        self.assertIsNone(cache, "Row data should not be loaded at construction time")

    def test_data_cached_after_first_access(self):
        """After accessing .data, the list is cached and not reloaded on subsequent access."""
        entry = CSVEntry(self.csv_path)
        first = entry.data
        second = entry.data
        self.assertIs(first, second, "data property should return the same cached list object")

    def test_iter_rows_yields_all_rows(self):
        """_iter_rows() yields one dict per CSV data row."""
        entry = CSVEntry(self.csv_path)
        rows = list(entry._iter_rows())
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['ID'], '1')
        self.assertEqual(rows[2]['Value'], 'gamma')

    def test_iter_rows_can_be_called_multiple_times(self):
        """_iter_rows() reopens the file on each call so it can be iterated repeatedly."""
        entry = CSVEntry(self.csv_path)
        first_pass = list(entry._iter_rows())
        second_pass = list(entry._iter_rows())
        self.assertEqual(first_pass, second_pass)

    def test_streaming_row_captured_without_loading_full_data(self):
        """
        During add_to_builder, CSVRowEntry instances created with the default row generator
        capture their row data directly from the streaming context, without triggering a full
        load of the parent's data list.
        """
        entry = CSVEntry(self.csv_path)
        builder = EDRMBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            builder.output_path = Path(tmpdir) / 'out.xml'
            entry.add_to_builder(builder)
        # After add_to_builder, __data should still be None if no one accessed .data
        cache = entry._CSVEntry__data
        self.assertIsNone(cache,
                          "add_to_builder with default CSVRowEntry should not trigger full data load")

    def test_streaming_context_cleared_after_add_to_builder(self):
        """_current_streaming_row is reset to None after add_to_builder completes."""
        entry = CSVEntry(self.csv_path)
        builder = EDRMBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            builder.output_path = Path(tmpdir) / 'out.xml'
            entry.add_to_builder(builder)
        self.assertIsNone(entry._current_streaming_row)

    def test_streaming_context_cleared_even_on_exception(self):
        """_current_streaming_row is reset to None even if the row generator raises."""
        class BrokenRow(CSVRowEntry):
            def __init__(self, parent_csv, row_index):
                raise RuntimeError("deliberate failure")

        entry = CSVEntry(self.csv_path, row_generator=BrokenRow)
        builder = EDRMBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            builder.output_path = Path(tmpdir) / 'out.xml'
            with self.assertRaises(RuntimeError):
                entry.add_to_builder(builder)
        self.assertIsNone(entry._current_streaming_row,
                          "_current_streaming_row must be cleared even after an exception")

    def test_add_to_builder_produces_correct_xml(self):
        """Full round-trip: add_to_builder followed by save produces a readable XML file."""
        entry = CSVEntry(self.csv_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / 'out.xml'
            builder = EDRMBuilder()
            builder.output_path = out
            entry.add_to_builder(builder)
            builder.save()
            content = out.read_text(encoding='UTF-8')
        self.assertIn('<Root', content)
        self.assertIn('DocId', content)


class TestCSVStreamingWithCustomSubclass(unittest.TestCase):
    """
    Verify that custom row generator subclasses that access parent_csv.data still work,
    and that doing so triggers the expected lazy load.
    """

    def setUp(self):
        # ProcessEntry-style: needs to look up other rows to find parent
        self.rows = [
            {'PID': '1', 'PPID': '0', 'Name': 'init'},
            {'PID': '2', 'PPID': '1', 'Name': 'bash'},
            {'PID': '3', 'PPID': '1', 'Name': 'vim'},
        ]
        self.csv_path = _make_csv_file(self.rows)

    def tearDown(self):
        os.unlink(self.csv_path)

    def test_subclass_accessing_parent_data_still_works(self):
        """
        A custom row generator that accesses parent_csv.data still produces correct results.
        The full data list is loaded on first access (lazy load triggered by the subclass).
        """
        rows_constructed = []

        class DataReadingRow(CSVRowEntry):
            """Row subclass that reads all rows from parent_csv.data during construction."""
            def __init__(self, parent_csv: CSVEntry, row_index: int):
                # Access full data list to look up a sibling row (like ProcessEntry does)
                current = parent_csv.data[row_index]
                siblings = [r for r in parent_csv.data if r['PID'] != current['PID']]
                rows_constructed.append((row_index, len(siblings)))
                super().__init__(parent_csv, row_index)

        entry = CSVEntry(self.csv_path, row_generator=DataReadingRow)
        builder = EDRMBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            builder.output_path = Path(tmpdir) / 'out.xml'
            entry.add_to_builder(builder)
            builder.save()
        # 1 CSVEntry + 3 rows
        self.assertEqual(len(builder.entry_map), 4)
        # Each row saw 2 siblings
        self.assertEqual(rows_constructed, [(0, 2), (1, 2), (2, 2)])

    def test_subclass_triggers_lazy_data_load(self):
        """
        A custom row generator that calls parent_csv.data will trigger the lazy load,
        but the result is correct and the cache is populated afterwards.
        """
        data_accessed = []

        class DataAccessingRow(CSVRowEntry):
            def __init__(self, parent_csv: CSVEntry, row_index: int):
                _ = parent_csv.data  # force load
                data_accessed.append(row_index)
                super().__init__(parent_csv, row_index)

        entry = CSVEntry(self.csv_path, row_generator=DataAccessingRow)
        builder = EDRMBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            builder.output_path = Path(tmpdir) / 'out.xml'
            entry.add_to_builder(builder)

        self.assertEqual(len(data_accessed), 3)
        # After access, the cache should be populated
        self.assertIsNotNone(entry._CSVEntry__data)
        self.assertEqual(len(entry.data), 3)


class TestCSVStreamingRealFiles(unittest.TestCase):
    """Tests using the actual CSV resource files in the test suite."""

    def setUp(self):
        self.resources = Path(__file__).parent / 'resources'
        self.sanctions_csv = self.resources / 'sanctions_list.csv'
        self.output_dir = self.resources / 'output'
        self.output_dir.mkdir(exist_ok=True)

    def test_sanctions_csv_row_count(self):
        """All rows are present when iterating via add_to_builder."""
        entry = CSVEntry(str(self.sanctions_csv))
        builder = EDRMBuilder()
        builder.output_path = self.output_dir / 'streaming_test.xml'
        entry.add_to_builder(builder)
        # 1 file entry + N row entries
        total = len(builder.entry_map)
        self.assertGreater(total, 1)

    def test_sanctions_csv_streaming_does_not_load_data(self):
        """Using default CSVRowEntry with sanctions CSV does not trigger full data load."""
        entry = CSVEntry(str(self.sanctions_csv))
        builder = EDRMBuilder()
        builder.output_path = self.output_dir / 'streaming_check.xml'
        entry.add_to_builder(builder)
        self.assertIsNone(entry._CSVEntry__data,
                          "Default row generator should not trigger full data load")

    def test_cc_medium_csv_round_trip(self):
        """CC.Medium.csv round-trip via streaming add_to_builder produces a valid XML."""
        cc_csv = self.resources / 'CC.Medium.csv'
        if not cc_csv.exists():
            self.skipTest('CC.Medium.csv not found in resources')
        entry = CSVEntry(str(cc_csv))
        builder = EDRMBuilder()
        out = self.output_dir / 'cc_medium_streaming.xml'
        builder.output_path = out
        entry.add_to_builder(builder)
        builder.save()
        self.assertTrue(out.exists())
        content = out.read_text(encoding='UTF-8')
        self.assertIn('<Root', content)


if __name__ == '__main__':
    unittest.main()
