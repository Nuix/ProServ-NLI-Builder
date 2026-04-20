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
        self.assertIsInstance(self.FieldType.TEXT, self.FieldType)

    def test_datetime_member_exists(self):
        self.assertIsInstance(self.FieldType.DATETIME, self.FieldType)

    def test_integer_member_exists(self):
        self.assertIsInstance(self.FieldType.INTEGER, self.FieldType)

    def test_long_text_member_exists(self):
        self.assertIsInstance(self.FieldType.LONG_TEXT, self.FieldType)

    def test_decimal_member_exists(self):
        self.assertIsInstance(self.FieldType.DECIMAL, self.FieldType)

    def test_boolean_member_exists(self):
        self.assertIsInstance(self.FieldType.BOOLEAN, self.FieldType)

    def test_exactly_six_members(self):
        self.assertEqual(len(self.FieldType), 6)

    def test_member_iteration_order(self):
        """FieldType iterates in declared definition order: TEXT, DATETIME, INTEGER, LONG_TEXT, DECIMAL, BOOLEAN."""
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
    """Deprecated EntryField.TYPE_* aliases refer to the same FieldType members.

    Warnings are suppressed here because the emission behaviour is verified
    separately by TestFieldTypeDeprecatedAliasWarnings.  Suppressing prevents
    unverified warnings from leaking into the pytest summary and polluting the
    output with noise that could mask genuinely unexpected warnings.
    """

    def setUp(self):
        import warnings
        from nuix_nli_lib.edrm import FieldType, EntryField
        self.FieldType = FieldType
        self.EntryField = EntryField
        # Suppress DeprecationWarning for the duration of each test so that
        # accessing TYPE_* only tests the return value, not the warning.
        self._warning_catcher = warnings.catch_warnings()
        self._warning_catcher.__enter__()
        warnings.simplefilter('ignore', DeprecationWarning)

    def tearDown(self):
        self._warning_catcher.__exit__(None, None, None)

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


class TestFieldTypeDeprecatedAliasWarnings(unittest.TestCase):
    """Accessing EntryField.TYPE_* aliases emits a DeprecationWarning at runtime."""

    def setUp(self):
        from nuix_nli_lib.edrm import EntryField
        self.EntryField = EntryField

    def test_type_text_emits_deprecation_warning(self):
        with self.assertWarns(DeprecationWarning) as ctx:
            _ = self.EntryField.TYPE_TEXT
        self.assertIn('TYPE_TEXT', str(ctx.warning))
        self.assertIn('FieldType.TEXT', str(ctx.warning))

    def test_type_datetime_emits_deprecation_warning(self):
        with self.assertWarns(DeprecationWarning) as ctx:
            _ = self.EntryField.TYPE_DATETIME
        self.assertIn('TYPE_DATETIME', str(ctx.warning))
        self.assertIn('FieldType.DATETIME', str(ctx.warning))

    def test_type_integer_emits_deprecation_warning(self):
        with self.assertWarns(DeprecationWarning) as ctx:
            _ = self.EntryField.TYPE_INTEGER
        self.assertIn('TYPE_INTEGER', str(ctx.warning))
        self.assertIn('FieldType.INTEGER', str(ctx.warning))

    def test_type_long_text_emits_deprecation_warning(self):
        with self.assertWarns(DeprecationWarning) as ctx:
            _ = self.EntryField.TYPE_LONG_TEXT
        self.assertIn('TYPE_LONG_TEXT', str(ctx.warning))
        self.assertIn('FieldType.LONG_TEXT', str(ctx.warning))

    def test_type_decimal_emits_deprecation_warning(self):
        with self.assertWarns(DeprecationWarning) as ctx:
            _ = self.EntryField.TYPE_DECIMAL
        self.assertIn('TYPE_DECIMAL', str(ctx.warning))
        self.assertIn('FieldType.DECIMAL', str(ctx.warning))

    def test_type_boolean_emits_deprecation_warning(self):
        with self.assertWarns(DeprecationWarning) as ctx:
            _ = self.EntryField.TYPE_BOOLEAN
        self.assertIn('TYPE_BOOLEAN', str(ctx.warning))
        self.assertIn('FieldType.BOOLEAN', str(ctx.warning))

    def test_unknown_attribute_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            _ = self.EntryField.TYPE_NONEXISTENT


class TestFieldTypeIsStr(unittest.TestCase):
    """Every FieldType member is an instance of str (StrEnum contract for backward-compatible XML serialisation)."""

    def setUp(self):
        from nuix_nli_lib.edrm import FieldType
        self.FieldType = FieldType

    def test_all_members_are_str_instances(self):
        for member in self.FieldType:
            with self.subTest(member=member):
                self.assertIsInstance(member, str)


class TestEntryFieldPlainStrDeprecation(unittest.TestCase):
    """Constructing EntryField with a plain str field_type emits a DeprecationWarning."""

    def setUp(self):
        from nuix_nli_lib.edrm import EntryField
        self.EntryField = EntryField

    def test_plain_str_field_type_emits_deprecation_warning(self):
        with self.assertWarns(DeprecationWarning) as ctx:
            self.EntryField('key', 'Name', 'Text')
        self.assertIn("'Text'", str(ctx.warning))
        self.assertIn('deprecated', str(ctx.warning))

    def test_deprecation_warning_uses_member_access_syntax(self):
        """The warning message must use FieldType.MEMBER syntax, not FieldType('value').

        FieldType('SomeCustomType') raises ValueError, so suggesting it would mislead
        callers who pass non-canonical strings. The message must direct users to member
        access (e.g. FieldType.TEXT) which is always safe.
        """
        with self.assertWarns(DeprecationWarning) as ctx:
            self.EntryField('key', 'Name', 'Text')
        warning_text = str(ctx.warning)
        # Must NOT suggest FieldType('value') call syntax
        self.assertNotIn("FieldType('", warning_text,
                         "Warning must not suggest FieldType('value') syntax — "
                         "this raises ValueError for non-canonical strings")
        # Must reference member access syntax (e.g. FieldType.TEXT)
        self.assertIn("FieldType.", warning_text,
                      "Warning must reference FieldType member access syntax (e.g. FieldType.TEXT)")

    def test_deprecation_warning_non_canonical_string(self):
        """A non-canonical string must still produce a warning that doesn't mislead the caller.

        Following FieldType('SomeCustomType') would raise ValueError — the warning
        should guide users to the enum definition instead.
        """
        with self.assertWarns(DeprecationWarning) as ctx:
            self.EntryField('key', 'Name', 'SomeCustomType')
        warning_text = str(ctx.warning)
        self.assertIn('deprecated', warning_text)
        self.assertNotIn("FieldType('SomeCustomType')", warning_text,
                         "Warning must not suggest FieldType(non_canonical_string) — "
                         "this would raise ValueError")

    def test_fieldtype_member_does_not_emit_warning(self):
        from nuix_nli_lib.edrm import FieldType
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            # Should not raise — FieldType member is the non-deprecated path
            self.EntryField('key', 'Name', FieldType.TEXT)

    def test_data_type_returns_fieldtype_when_constructed_correctly(self):
        from nuix_nli_lib.edrm import FieldType
        field = self.EntryField('key', 'Name', FieldType.TEXT)
        self.assertIsInstance(field.data_type, FieldType)
        self.assertEqual(field.data_type, FieldType.TEXT)


if __name__ == '__main__':
    unittest.main()
