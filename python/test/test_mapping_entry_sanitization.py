"""
Tests for SLC-79: Fix getName() sanitization bypass in JSONArrayEntry and JSONObjectEntry.

Verifies that MappingEntry subclasses which override get_base_name() still have XML and
filename sanitization applied by the parent's get_name() method.  Subclasses that previously
overrode get_name() directly bypassed this sanitization.
"""
import json
import tempfile
import unittest
from pathlib import Path

from nuix_nli_lib.edrm import MappingEntry
from nuix_nli_lib.data_types.json_file import JSONArrayEntry, JSONObjectEntry, JSONValueEntry


class TestMappingEntrySanitization(unittest.TestCase):
    """Tests that get_name() always applies sanitization regardless of what get_base_name() returns."""

    def test_get_base_name_returns_raw_name(self):
        """get_base_name() on MappingEntry returns the raw value from data without sanitization."""
        mapping = {'Name': 'hello<world>'}
        entry = MappingEntry(mapping, 'text/plain')
        # get_base_name returns the raw value
        self.assertEqual(entry.get_base_name(), 'hello<world>')

    def test_get_name_sanitizes_xml_chars(self):
        """get_name() applies XML sanitization to the value from get_base_name()."""
        mapping = {'Name': 'hello<world>'}
        entry = MappingEntry(mapping, 'text/plain')
        # get_name sanitizes XML illegal characters
        result = entry.get_name()
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)

    def test_name_property_delegates_to_get_name(self):
        """The name property returns the same value as get_name()."""
        mapping = {'Name': 'hello<world>'}
        entry = MappingEntry(mapping, 'text/plain')
        self.assertEqual(entry.name, entry.get_name())

    def test_subclass_overriding_get_base_name_gets_sanitization(self):
        """A MappingEntry subclass that overrides get_base_name() still gets sanitization via get_name()."""
        class SpecialEntry(MappingEntry):
            def get_base_name(self) -> str:
                return 'item<with>special&chars'

        entry = SpecialEntry({'key': 'value'}, 'text/plain')
        # get_name() should sanitize the value from get_base_name()
        result = entry.get_name()
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertEqual(result, entry.name)

    def test_json_array_entry_get_base_name_returns_mapping_name(self):
        """JSONArrayEntry.get_base_name() returns the mapping_name passed to the constructor."""
        entry = JSONArrayEntry(mapping_name='My Array', array={})
        self.assertEqual(entry.get_base_name(), 'My Array')

    def test_json_array_entry_name_is_sanitized(self):
        """JSONArrayEntry.name sanitizes the mapping_name for XML and filename safety."""
        entry = JSONArrayEntry(mapping_name='Array<With>Special:Chars', array={})
        # The name property should be sanitized (no XML-illegal or filename-illegal chars)
        result = entry.name
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertNotIn(':', result)

    def test_json_array_entry_get_name_sanitizes(self):
        """JSONArrayEntry.get_name() applies XML and filename sanitization."""
        entry = JSONArrayEntry(mapping_name='Array<Item>', array={})
        sanitized = entry.get_name()
        self.assertNotIn('<', sanitized)
        self.assertNotIn('>', sanitized)
        # get_name() and name should agree
        self.assertEqual(sanitized, entry.name)

    def test_json_object_entry_get_base_name_returns_mapping_name(self):
        """JSONObjectEntry.get_base_name() returns the mapping_name passed to the constructor."""
        entry = JSONObjectEntry(mapping_name='My Object', obj={})
        self.assertEqual(entry.get_base_name(), 'My Object')

    def test_json_object_entry_name_is_sanitized(self):
        """JSONObjectEntry.name sanitizes the mapping_name for XML and filename safety."""
        entry = JSONObjectEntry(mapping_name='Object<With>Angle:Brackets', obj={})
        result = entry.name
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertNotIn(':', result)

    def test_json_object_entry_get_name_sanitizes(self):
        """JSONObjectEntry.get_name() applies XML and filename sanitization."""
        entry = JSONObjectEntry(mapping_name='Object<Item>', obj={})
        sanitized = entry.get_name()
        self.assertNotIn('<', sanitized)
        self.assertNotIn('>', sanitized)
        self.assertEqual(sanitized, entry.name)

    def test_json_value_entry_get_base_name_returns_mapping_name(self):
        """JSONValueEntry.get_base_name() returns the mapping_name passed to the constructor."""
        entry = JSONValueEntry(mapping_name='My Value', key_name='key', value='val')
        self.assertEqual(entry.get_base_name(), 'My Value')

    def test_json_value_entry_name_is_sanitized(self):
        """JSONValueEntry.name sanitizes the mapping_name for XML and filename safety."""
        entry = JSONValueEntry(mapping_name='Value<With>Brackets', key_name='key', value='val')
        result = entry.name
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)

    def test_clean_name_unchanged(self):
        """A clean name without special characters is returned as-is."""
        entry = JSONArrayEntry(mapping_name='Clean Array Name', array={})
        self.assertEqual(entry.get_base_name(), 'Clean Array Name')
        self.assertEqual(entry.get_name(), 'Clean Array Name')
        self.assertEqual(entry.name, 'Clean Array Name')

    def test_json_file_entry_produces_sanitized_names(self):
        """JSONFileEntry produces child entries with sanitized names when JSON keys contain special chars."""
        # Use a nested structure so that special-char keys become mapping_name values on child entries.
        # The key 'object<with>brackets' will be passed as mapping_name to a child JSONObjectEntry.
        data = {'object<with>brackets': {'nested_key': 'value'}, 'normal_key': 42}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_path = f.name

        try:
            from nuix_nli_lib.data_types.json_file import JSONFileEntry
            from nuix_nli_lib.edrm import EDRMBuilder
            import tempfile as tf

            with tf.TemporaryDirectory() as out_dir:
                file_entry = JSONFileEntry(tmp_path)
                builder = EDRMBuilder()
                builder.as_nli = False
                builder.output_path = Path(out_dir) / 'test.xml'
                file_entry.add_to_builder(builder)

                # Collect the name of every child entry registered in the builder
                child_names = [entry.name for entry in builder.entry_map.values()]

                # At least one child entry must exist
                self.assertGreater(len(child_names), 0,
                                   "Builder should contain at least one entry after add_to_builder()")

                # No entry name should contain XML-illegal or filename-illegal characters
                for entry_name in child_names:
                    self.assertNotIn('<', entry_name,
                                     f"Entry name {entry_name!r} contains '<' which is not sanitized")
                    self.assertNotIn('>', entry_name,
                                     f"Entry name {entry_name!r} contains '>' which is not sanitized")
                    self.assertNotIn(':', entry_name,
                                     f"Entry name {entry_name!r} contains ':' which is not sanitized")

                # Confirm the child entry derived from the special-char key has a sanitized name
                sanitized_names_concat = ' '.join(child_names)
                self.assertNotIn('object<with>brackets', sanitized_names_concat,
                                 "Raw unsanitized key 'object<with>brackets' must not appear in any entry name")
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
