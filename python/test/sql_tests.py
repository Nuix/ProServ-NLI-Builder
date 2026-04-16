"""
Tests for data_types.sql_type — SQLTypeEntry and SQLRowEntry.

All tests use in-memory SQLite databases so there are no external dependencies or file system side
effects.
"""

import sqlite3
import unittest
from pathlib import Path
from typing import Any
from xml.dom import minidom

from nuix_nli_lib.data_types import SQLTypeEntry, SQLRowEntry
from nuix_nli_lib.edrm.EDRMBuilder import EDRMBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(schema: str, rows: list[tuple]) -> sqlite3.Connection:
    """Create a fresh in-memory SQLite connection, apply *schema*, and insert *rows*."""
    conn = sqlite3.connect(":memory:")
    conn.execute(schema)
    conn.executemany(
        f"INSERT INTO test VALUES ({','.join(['?'] * len(rows[0]))})" if rows else "",
        rows,
    )
    conn.commit()
    return conn


def _simple_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE employees (id INTEGER, name TEXT, department TEXT)")
    conn.executemany(
        "INSERT INTO employees VALUES (?, ?, ?)",
        [
            (1, "Alice", "Engineering"),
            (2, "Bob", "Legal"),
            (3, "Carol", "Engineering"),
        ],
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# SQLTypeEntry tests
# ---------------------------------------------------------------------------

class TestSQLTypeEntryBasicQuery(unittest.TestCase):
    """Test that SQLTypeEntry correctly reads rows and columns from a simple query."""

    def setUp(self):
        self.conn = _simple_conn()
        self.entry = SQLTypeEntry(self.conn, "SELECT * FROM employees")

    def test_row_fields_match_columns(self):
        self.assertEqual(self.entry.row_fields, ["id", "name", "department"])

    def test_data_length_matches_row_count(self):
        self.assertEqual(len(self.entry.data), 3)

    def test_row_values_are_correct(self):
        self.assertEqual(self.entry.data[0], {"id": 1, "name": "Alice", "department": "Engineering"})
        self.assertEqual(self.entry.data[1], {"id": 2, "name": "Bob", "department": "Legal"})
        self.assertEqual(self.entry.data[2], {"id": 3, "name": "Carol", "department": "Engineering"})

    def test_query_property_matches_input(self):
        self.assertEqual(self.entry.query, "SELECT * FROM employees")

    def tearDown(self):
        self.conn.close()


class TestSQLTypeEntryWithFilePath(unittest.TestCase):
    """Test that a string connection argument (SQLite path) is handled correctly."""

    def test_in_memory_string_connection(self):
        # Create a file-based db in memory — we use ':memory:' as the connection string.
        # Pre-populate via a separate real connection, then use the string path variant with
        # an in-memory db that has data inserted before the SQLTypeEntry reads it.
        # Because ':memory:' creates a fresh database, we embed the setup in a subquery.
        entry = SQLTypeEntry(
            ":memory:",
            "SELECT 1 AS num, 'hello' AS greeting",
        )
        self.assertEqual(entry.row_fields, ["num", "greeting"])
        self.assertEqual(len(entry.data), 1)
        self.assertEqual(entry.data[0], {"num": 1, "greeting": "hello"})

    def test_entry_name_defaults(self):
        entry = SQLTypeEntry(":memory:", "SELECT 1 AS x")
        self.assertEqual(entry.name, "SQL Query Results")

    def test_entry_name_custom(self):
        entry = SQLTypeEntry(":memory:", "SELECT 1 AS x", name="Employees")
        self.assertEqual(entry.name, "Employees")


class TestSQLTypeEntryFiltering(unittest.TestCase):
    """Test that WHERE clauses and column projections are handled."""

    def setUp(self):
        self.conn = _simple_conn()

    def test_filtered_query_returns_subset(self):
        entry = SQLTypeEntry(
            self.conn,
            "SELECT id, name FROM employees WHERE department = 'Engineering'",
        )
        self.assertEqual(len(entry.data), 2)
        self.assertEqual(entry.row_fields, ["id", "name"])

    def test_empty_result_set(self):
        entry = SQLTypeEntry(
            self.conn,
            "SELECT * FROM employees WHERE id = 999",
        )
        self.assertEqual(len(entry.data), 0)
        self.assertEqual(entry.row_fields, ["id", "name", "department"])

    def tearDown(self):
        self.conn.close()


class TestSQLTypeEntryEDRMFields(unittest.TestCase):
    """Test that required EDRM fields are populated on the entry itself."""

    def setUp(self):
        self.conn = _simple_conn()
        self.entry = SQLTypeEntry(self.conn, "SELECT * FROM employees")

    def test_has_mime_type_field(self):
        self.assertIn("MIME Type", list(self.entry.fields))
        self.assertEqual(self.entry["MIME Type"].value, "application/x-database-table")

    def test_has_sha1_field(self):
        self.assertIn("SHA-1", list(self.entry.fields))
        sha1 = self.entry["SHA-1"].value
        self.assertIsNotNone(sha1)
        self.assertGreater(len(sha1), 0)

    def test_has_item_date_field(self):
        self.assertIn("Item Date", list(self.entry.fields))

    def test_has_name_field(self):
        self.assertIn("Name", list(self.entry.fields))
        self.assertEqual(self.entry["Name"].value, "SQL Query Results")

    def test_identifier_field_is_sha1(self):
        self.assertEqual(self.entry.identifier_field, "SHA-1")

    def tearDown(self):
        self.conn.close()


class TestSQLTypeEntryParentRelationship(unittest.TestCase):
    """Test that parent_id is respected."""

    def test_no_parent_by_default(self):
        entry = SQLTypeEntry(":memory:", "SELECT 1 AS x")
        self.assertIsNone(entry.parent)

    def test_parent_id_is_stored(self):
        entry = SQLTypeEntry(":memory:", "SELECT 1 AS x", parent_id="some-parent-id")
        self.assertEqual(entry.parent, "some-parent-id")

    def test_add_as_parent_path_prepends_name(self):
        entry = SQLTypeEntry(":memory:", "SELECT 1 AS x", name="MyQuery")
        result = entry.add_as_parent_path("child.txt")
        self.assertEqual(result, "MyQuery/child.txt")


# ---------------------------------------------------------------------------
# SQLRowEntry tests
# ---------------------------------------------------------------------------

class TestSQLRowEntry(unittest.TestCase):
    """Test that SQLRowEntry correctly wraps individual rows."""

    def setUp(self):
        self.conn = _simple_conn()
        self.parent = SQLTypeEntry(self.conn, "SELECT * FROM employees")

    def test_row_data_matches_parent_row(self):
        row = SQLRowEntry(self.parent, 0)
        self.assertEqual(row.data, {"id": 1, "name": "Alice", "department": "Engineering"})

    def test_row_fields_sourced_from_parent(self):
        row = SQLRowEntry(self.parent, 1)
        self.assertEqual(row.fields, ["id", "name", "department"])

    def test_parent_sql_property(self):
        row = SQLRowEntry(self.parent, 2)
        self.assertIs(row.parent_sql, self.parent)

    def test_row_parent_id_defaults_to_parent_sha1(self):
        row = SQLRowEntry(self.parent, 0)
        expected_parent_id = self.parent[self.parent.identifier_field].value
        self.assertEqual(row.parent, expected_parent_id)

    def test_row_parent_id_can_be_overridden(self):
        row = SQLRowEntry(self.parent, 0, parent_id="override-id")
        self.assertEqual(row.parent, "override-id")

    def test_mime_type_is_database_table_row(self):
        row = SQLRowEntry(self.parent, 0)
        self.assertEqual(row["MIME Type"].value, "application/x-database-table-row")

    def tearDown(self):
        self.conn.close()


# ---------------------------------------------------------------------------
# SQLTypeEntry.add_to_builder integration tests
# ---------------------------------------------------------------------------

class TestSQLAddToBuilder(unittest.TestCase):
    """Test that add_to_builder produces correct entries in the EDRM builder."""

    def setUp(self):
        self.conn = _simple_conn()
        self.entry = SQLTypeEntry(self.conn, "SELECT * FROM employees")

    def test_add_to_builder_adds_parent_and_rows(self):
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = Path("/tmp/sql_test.xml")
        self.entry.add_to_builder(builder)
        # 3 rows + 1 parent = 4 entries
        self.assertEqual(len(builder.entry_map), 4)

    def test_add_to_builder_returns_sha1_identifier(self):
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = Path("/tmp/sql_test2.xml")
        result = self.entry.add_to_builder(builder)
        self.assertEqual(result, self.entry["SHA-1"].value)

    def test_add_to_builder_with_custom_row_generator(self):
        """Custom row_generator is used instead of SQLRowEntry."""

        class NamedRow(SQLRowEntry):
            def get_base_name(self):
                return self.data.get("name", super().get_base_name())

        conn = _simple_conn()
        entry = SQLTypeEntry(conn, "SELECT * FROM employees", row_generator=NamedRow)
        builder = EDRMBuilder()
        builder.as_nli = False
        builder.output_path = Path("/tmp/sql_test3.xml")
        entry.add_to_builder(builder)
        all_entries = list(builder.entry_map.values())
        # 1 parent + 3 named rows
        self.assertEqual(len(all_entries), 4)
        row_entries = [e for e in all_entries if isinstance(e, NamedRow)]
        self.assertEqual(len(row_entries), 3)
        conn.close()

    def tearDown(self):
        self.conn.close()


class TestSQLImportFromDataTypes(unittest.TestCase):
    """Verify that SQLTypeEntry and SQLRowEntry are importable from the data_types package."""

    def test_import_sql_type_entry(self):
        from nuix_nli_lib.data_types import SQLTypeEntry as STE  # noqa: F401
        self.assertIsNotNone(STE)

    def test_import_sql_row_entry(self):
        from nuix_nli_lib.data_types import SQLRowEntry as SRE  # noqa: F401
        self.assertIsNotNone(SRE)


if __name__ == "__main__":
    unittest.main()
