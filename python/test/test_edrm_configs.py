"""
Tests for SLC-210: Validate edrm.configs runtime values match their declared types.

These tests confirm that the default configuration dictionary contains values
of the correct types, catching any future drift between documentation and reality.
"""
import unittest

from nuix_nli_lib import edrm


class TestEDRMConfigs(unittest.TestCase):
    """Runtime type checks for edrm.configs default values."""

    def test_hash_buffer_size_is_int(self):
        """hash_buffer_size must be an int so it can be passed to file.read()."""
        value = edrm.configs['hash_buffer_size']
        self.assertIsInstance(value, int,
                              f"hash_buffer_size must be int, got {type(value).__name__}")

    def test_hash_buffer_size_is_positive(self):
        """hash_buffer_size must be positive to avoid infinite-loop in hash helpers."""
        self.assertGreater(edrm.configs['hash_buffer_size'], 0,
                           "hash_buffer_size must be > 0")

    def test_date_time_format_is_str(self):
        """date_time_format must be a str for use with strftime."""
        self.assertIsInstance(edrm.configs['date_time_format'], str)

    def test_time_zone_format_is_str(self):
        """time_zone_format must be a str for use with strftime."""
        self.assertIsInstance(edrm.configs['time_zone_format'], str)

    def test_encoding_is_str(self):
        """encoding must be a str for use with open() calls."""
        self.assertIsInstance(edrm.configs['encoding'], str)

    def test_custodian_is_str(self):
        """custodian must be a str for use as an XML text node."""
        self.assertIsInstance(edrm.configs['custodian'], str)

    def test_default_itemdate_field_is_str(self):
        """default_itemdate_field must be a str used as a dict key lookup."""
        self.assertIsInstance(edrm.configs['default_itemdate_field'], str)

    def test_default_rowname_field_is_str(self):
        """default_rowname_field must be a str used as a dict key lookup."""
        self.assertIsInstance(edrm.configs['default_rowname_field'], str)

    def test_all_required_keys_present(self):
        """All required config keys must be present in the default configs dict."""
        required_keys = {
            'date_time_format',
            'time_zone_format',
            'hash_buffer_size',
            'encoding',
            'custodian',
            'default_itemdate_field',
            'default_rowname_field',
        }
        missing = required_keys - set(edrm.configs.keys())
        self.assertEqual(set(), missing,
                         f"Missing required config keys: {missing}")


if __name__ == '__main__':
    unittest.main()
