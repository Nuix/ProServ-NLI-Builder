import unittest


class TestFieldTypeImportability(unittest.TestCase):
    """FieldType is publicly importable from nuix_nli_lib.edrm."""

    def test_import_from_edrm_package(self):
        from nuix_nli_lib.edrm import FieldType  # noqa: F401


class TestFieldTypeMembership(unittest.TestCase):
    """All six documented FieldType members exist."""

    def setUp(self):
        from nuix_nli_lib.edrm import FieldType
        self.FieldType = FieldType

    def test_text_member_exists(self):
        _ = self.FieldType.TEXT

    def test_datetime_member_exists(self):
        _ = self.FieldType.DATETIME

    def test_integer_member_exists(self):
        _ = self.FieldType.INTEGER

    def test_long_text_member_exists(self):
        _ = self.FieldType.LONG_TEXT

    def test_decimal_member_exists(self):
        _ = self.FieldType.DECIMAL

    def test_boolean_member_exists(self):
        _ = self.FieldType.BOOLEAN

    def test_exactly_six_members(self):
        self.assertEqual(len(self.FieldType), 6)

    def test_member_iteration_order(self):
        expected = [
            self.FieldType.TEXT,
            self.FieldType.DATETIME,
            self.FieldType.INTEGER,
            self.FieldType.LONG_TEXT,
            self.FieldType.DECIMAL,
            self.FieldType.BOOLEAN,
        ]
        self.assertEqual(list(self.FieldType), expected)


class TestFieldTypeStringEquality(unittest.TestCase):
    """Each FieldType member compares equal to its canonical string value (StrEnum contract)."""

    def setUp(self):
        from nuix_nli_lib.edrm import FieldType
        self.FieldType = FieldType

    def test_text_equals_string(self):
        self.assertEqual(self.FieldType.TEXT, 'Text')

    def test_datetime_equals_string(self):
        self.assertEqual(self.FieldType.DATETIME, 'DateTime')

    def test_integer_equals_string(self):
        self.assertEqual(self.FieldType.INTEGER, 'LongInteger')

    def test_long_text_equals_string(self):
        self.assertEqual(self.FieldType.LONG_TEXT, 'LongText')

    def test_decimal_equals_string(self):
        self.assertEqual(self.FieldType.DECIMAL, 'Decimal')

    def test_boolean_equals_string(self):
        self.assertEqual(self.FieldType.BOOLEAN, 'Boolean')


class TestFieldTypeCaseSensitivity(unittest.TestCase):
    """FieldType string comparisons are case-sensitive."""

    def setUp(self):
        from nuix_nli_lib.edrm import FieldType
        self.FieldType = FieldType

    def test_text_not_equal_lowercase(self):
        self.assertNotEqual(self.FieldType.TEXT, 'text')

    def test_datetime_not_equal_lowercase(self):
        self.assertNotEqual(self.FieldType.DATETIME, 'datetime')

    def test_datetime_not_equal_wrong_case(self):
        # 'Datetime' (lowercase 't') is a common typo
        self.assertNotEqual(self.FieldType.DATETIME, 'Datetime')


class TestFieldTypeInvalidValueRejection(unittest.TestCase):
    """Constructing a FieldType from an unrecognised string raises ValueError."""

    def setUp(self):
        from nuix_nli_lib.edrm import FieldType
        self.FieldType = FieldType

    def test_wrong_case_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.FieldType('Datetime')

    def test_completely_invalid_value_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.FieldType('NotAFieldType')

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.FieldType('')


class TestFieldTypeDeprecatedAliases(unittest.TestCase):
    """Deprecated EntryField.TYPE_* aliases refer to the same FieldType members."""

    def setUp(self):
        from nuix_nli_lib.edrm import FieldType, EntryField
        self.FieldType = FieldType
        self.EntryField = EntryField

    def test_type_text_is_fieldtype_text(self):
        self.assertIs(self.EntryField.TYPE_TEXT, self.FieldType.TEXT)

    def test_type_datetime_is_fieldtype_datetime(self):
        self.assertIs(self.EntryField.TYPE_DATETIME, self.FieldType.DATETIME)

    def test_type_integer_is_fieldtype_integer(self):
        self.assertIs(self.EntryField.TYPE_INTEGER, self.FieldType.INTEGER)

    def test_type_long_text_is_fieldtype_long_text(self):
        self.assertIs(self.EntryField.TYPE_LONG_TEXT, self.FieldType.LONG_TEXT)

    def test_type_decimal_is_fieldtype_decimal(self):
        self.assertIs(self.EntryField.TYPE_DECIMAL, self.FieldType.DECIMAL)

    def test_type_boolean_is_fieldtype_boolean(self):
        self.assertIs(self.EntryField.TYPE_BOOLEAN, self.FieldType.BOOLEAN)


if __name__ == '__main__':
    unittest.main()
