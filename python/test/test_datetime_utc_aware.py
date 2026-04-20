"""
Regression tests for SLC-185 and SLC-188:
- SLC-188: MappingEntry.itemdate must normalize naive datetimes to UTC
- SLC-185: JSONDateTimeEntry string-parse paths must normalize naive datetimes to UTC
"""
from datetime import datetime, timezone
import unittest

from nuix_nli_lib.data_types.json_file import get_datetime_value_generator
from nuix_nli_lib.edrm import MappingEntry


class TestDatetimeUTCAware(unittest.TestCase):
    """
    Regression tests for SLC-185 and SLC-188: naive datetimes must be normalized to UTC
    at the boundary in MappingEntry.itemdate and in JSONDateTimeEntry's string-parse paths.
    """

    def test_mapping_entry_naive_datetime_normalized_to_utc(self):
        """
        SLC-188: When a naive datetime is stored in a MappingEntry data dict, itemdate must
        return a UTC-aware datetime (not pass the naive value through unchanged).
        """
        naive_dt = datetime(2024, 6, 15, 10, 30, 0)  # no tzinfo
        self.assertIsNone(naive_dt.tzinfo, "precondition: datetime is naive")

        entry = MappingEntry({'timestamp': naive_dt}, "application/x-database-table-row")
        result = entry.itemdate

        self.assertIsInstance(result, datetime)
        self.assertIsNotNone(result.tzinfo,
                             "itemdate must return a tz-aware datetime for a naive input; got naive")
        self.assertEqual(result.tzinfo, timezone.utc,
                         f"Expected UTC timezone, got {result.tzinfo}")

    def test_json_datetime_entry_iso_string_no_tz_normalized_to_utc(self):
        """
        SLC-185: When JSONDateTimeEntry is constructed with a tz-naive ISO 8601 string
        (no offset suffix), the stored datetime must be normalized to UTC.
        """
        JSONDateTimeEntry = get_datetime_value_generator([])
        entry = JSONDateTimeEntry("ts", "ts", "2024-06-15T12:30:45")

        stored_dt = entry.data.get("ts")
        self.assertIsInstance(stored_dt, datetime,
                              f"Expected datetime, got {type(stored_dt)}")
        self.assertIsNotNone(stored_dt.tzinfo,
                             "ISO string with no tz offset must be normalized to UTC")
        self.assertEqual(stored_dt.tzinfo, timezone.utc,
                         f"Expected UTC timezone, got {stored_dt.tzinfo}")

    def test_json_datetime_entry_custom_format_no_tz_normalized_to_utc(self):
        """
        SLC-185: When JSONDateTimeEntry is constructed with a string matching a custom format
        that does not include %z, the resulting datetime must be normalized to UTC.
        """
        JSONDateTimeEntry = get_datetime_value_generator(["%Y/%m/%d %H:%M:%S"])
        entry = JSONDateTimeEntry("ts", "ts", "2024/06/15 12:30:45")

        stored_dt = entry.data.get("ts")
        self.assertIsInstance(stored_dt, datetime,
                              f"Expected datetime, got {type(stored_dt)}")
        self.assertIsNotNone(stored_dt.tzinfo,
                             "Custom-format string with no %z must be normalized to UTC")
        self.assertEqual(stored_dt.tzinfo, timezone.utc,
                         f"Expected UTC timezone, got {stored_dt.tzinfo}")


if __name__ == '__main__':
    unittest.main()
