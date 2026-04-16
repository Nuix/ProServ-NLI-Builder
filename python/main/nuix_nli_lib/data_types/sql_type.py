"""
This module provides classes that simplify adding SQL query results to an EDRM XML load file, or NLI file.
It contains two classes:

SQLTypeEntry:
Represents the result of a SQL query executed against a database.  It accepts either a connection string
(interpreted as an SQLite database path or ``:memory:``) or a pre-opened DB-API 2.0 connection object,
plus a SQL query string.  The query is executed once during construction and all result rows are loaded
into memory.

Any DB-API 2.0-compliant driver can be substituted by passing a live connection object directly.
For example::

    import psycopg2
    conn = psycopg2.connect("host=localhost dbname=mydb user=postgres password=secret")
    entry = SQLTypeEntry(conn, "SELECT id, name, created_at FROM documents")

For the default SQLite case, pass a file path or ``:memory:``::

    entry = SQLTypeEntry(":memory:", "SELECT * FROM my_table")

SQLRowEntry:
A subclass of :class:`~nuix_nli_lib.edrm.MappingEntry` that represents a single result row from a
``SQLTypeEntry``.  It only exists in the context of its parent ``SQLTypeEntry``.

Usage example::

    import sqlite3
    from nuix_nli_lib.data_types import SQLTypeEntry

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE employees (id INTEGER, name TEXT, department TEXT)")
    conn.execute("INSERT INTO employees VALUES (1, 'Alice', 'Engineering')")
    conn.execute("INSERT INTO employees VALUES (2, 'Bob', 'Legal')")
    conn.commit()

    entry = SQLTypeEntry(conn, "SELECT * FROM employees")
    builder = EDRMBuilder()
    builder.output_path = path_to_output
    entry.add_to_builder(builder)
    builder.save()

To customise each row (e.g. to provide meaningful names or item dates), subclass ``SQLRowEntry`` and pass
the subclass as ``row_generator``::

    class MyRowEntry(SQLRowEntry):
        def get_base_name(self):
            return self.data.get("name", super().get_base_name())

    entry = SQLTypeEntry(":memory:", "SELECT * FROM employees", row_generator=MyRowEntry)
"""

import hashlib
import sqlite3
from datetime import datetime
from typing import Any, Iterator, Tuple, Type, Union
from xml.dom.minidom import Document, Element

from nuix_nli_lib.edrm import FieldFactory, EntryField, EntryInterface
from nuix_nli_lib.edrm import EDRMUtilities as eutes
from nuix_nli_lib.edrm.EDRMBuilder import EDRMBuilder
from nuix_nli_lib.edrm.MappingEntry import MappingEntry


class SQLTypeEntry(EntryInterface):
    """
    Represents the result set of a SQL query and acts as a logical container for its rows in the EDRM
    load file.

    This class executes a SQL query at construction time, reads all result rows into memory, and exposes
    them via the :attr:`data` and :attr:`row_fields` properties.  It acts as the *parent* entry for the
    individual :class:`SQLRowEntry` objects produced by :meth:`add_to_builder`.

    **Driver selection**

    The default driver is Python's built-in ``sqlite3`` module.  To use a different DB-API 2.0-compliant
    driver (e.g. ``psycopg2`` for PostgreSQL, ``pyodbc`` for ODBC sources), open a connection with that
    driver yourself and pass the live connection object as ``connection``::

        import psycopg2
        conn = psycopg2.connect(dsn)
        entry = SQLTypeEntry(conn, "SELECT * FROM my_table")

    When a *string* is supplied for ``connection`` it is interpreted as an SQLite database path (or
    ``:memory:``) and ``sqlite3.connect()`` is called automatically.  The connection is closed after the
    query runs.

    Implementation note: the full result set is loaded into memory at construction time.  For very large
    result sets, consider subclassing and overriding :meth:`add_to_builder` to stream rows.
    """

    def __init__(self,
                 connection: Union[str, Any],
                 query: str,
                 name: str = "SQL Query Results",
                 parent_id: str = None,
                 row_generator: Type[Any] = None):
        """
        :param connection: Either a file path / connection string for SQLite (a ``str``), or an open
            DB-API 2.0 connection object.  When a string is given, ``sqlite3.connect(connection)`` is
            called and the connection is closed automatically after the query runs.
        :param query: The SQL query to execute.  Only queries that return rows (e.g. ``SELECT``) are
            meaningful here.  The query is executed once during construction.
        :param name: Display name for this entry in the EDRM XML.  Defaults to ``"SQL Query Results"``.
        :param parent_id: Optional identifier of the parent entry.  ``None`` makes this a top-level item.
        :param row_generator: Optional callable used to produce row entries.  Must accept
            ``(parent: SQLTypeEntry, index: int)`` and return an
            :class:`~nuix_nli_lib.edrm.EntryInterface` instance.  Defaults to :class:`SQLRowEntry`.
        """
        super().__init__()

        self.__name = name
        self.__parent_id = parent_id
        self.__query = query
        self.__row_generator = row_generator
        self.__data: list[dict[str, Any]] = []
        self.__row_fields: list[str] = []
        self.__item_date = datetime.now()

        self._execute_query(connection, query)
        self._fill_fields()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_query(self, connection: Union[str, Any], query: str) -> None:
        """Execute *query* against *connection* and populate :attr:`data` / :attr:`row_fields`."""
        owns_connection = isinstance(connection, str)
        conn = sqlite3.connect(connection) if owns_connection else connection
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [description[0] for description in cursor.description] if cursor.description else []
            self.__row_fields = columns
            for row in cursor.fetchall():
                self.__data.append(dict(zip(columns, row)))
        finally:
            if owns_connection:
                conn.close()

    def _fill_fields(self) -> None:
        """Populate the standard EDRM fields (MIME Type, Name, SHA-1, Item Date)."""
        self['MIME Type'] = FieldFactory.generate_field('MIME Type', EntryField.TYPE_TEXT,
                                                        'application/x-database-table')
        self['Name'] = FieldFactory.generate_field('Name', EntryField.TYPE_TEXT, self.__name)
        sha1_value = eutes.hash_data({'query': self.__query, 'data': self.__data}, hashlib.sha1())
        self['SHA-1'] = FieldFactory.generate_field('SHA-1', EntryField.TYPE_TEXT, sha1_value)
        self['Item Date'] = FieldFactory.generate_field('Item Date', EntryField.TYPE_DATETIME,
                                                        self.__item_date)

    # ------------------------------------------------------------------
    # EntryInterface implementation
    # ------------------------------------------------------------------

    @property
    def identifier_field(self) -> str:
        return 'SHA-1'

    @property
    def name(self) -> str:
        return self.__name

    @property
    def time_field(self) -> str:
        return 'Item Date'

    @property
    def itemdate(self) -> datetime:
        return self.__item_date

    @property
    def parent(self) -> str:
        return self.__parent_id

    def add_as_parent_path(self, existing_path: str) -> str:
        return f'{self.__name}/{existing_path}'

    def add_file(self, document: Document, container: Element,
                 entry_map: dict[str, EntryInterface], for_nli: bool) -> None:
        # SQL result sets have no native file representation.
        return

    def add_location_uri(self, document: Document, container: Element,
                         entry_map: dict[str, EntryInterface], for_nli: bool) -> None:
        # No physical location URI for a virtual SQL container.
        return

    def calculate_md5(self) -> str:
        return eutes.hash_data({'query': self.__query, 'data': self.__data}, hashlib.md5())

    # ------------------------------------------------------------------
    # SQL-specific interface
    # ------------------------------------------------------------------

    @property
    def data(self) -> list[dict[str, Any]]:
        """
        :return: The full list of result rows, each represented as a ``{column_name: value}`` dictionary.
            This is the live list; do not mutate it.
        """
        return self.__data

    @property
    def row_fields(self) -> list[str]:
        """
        :return: Ordered list of column names returned by the query.
        """
        return self.__row_fields

    @property
    def query(self) -> str:
        """
        :return: The SQL query string that was executed to populate this entry.
        """
        return self.__query

    def add_to_builder(self, builder: EDRMBuilder) -> str:
        """
        Add this ``SQLTypeEntry`` to the EDRM builder as a container, then add one :class:`SQLRowEntry`
        (or custom ``row_generator`` instance) for each result row.

        :param builder: The :class:`~nuix_nli_lib.edrm.EDRMBuilder` used to assemble the EDRM XML file.
        :return: The identifier value (SHA-1) of this entry.
        """
        row_gen = self.__row_generator or SQLRowEntry
        builder.add_entry(self)
        for index in range(len(self.__data)):
            builder.add_entry(row_gen(self, index))
        return self[self.identifier_field].value


class SQLRowEntry(MappingEntry):
    """
    Represents a single result row from a :class:`SQLTypeEntry` SQL query.

    Instances are created automatically by :meth:`SQLTypeEntry.add_to_builder` and should not normally
    be constructed directly.  To customise row behaviour (names, item dates, extra fields), subclass this
    class and pass the subclass as the ``row_generator`` argument to :class:`SQLTypeEntry`.
    """

    def __init__(self, parent_sql: SQLTypeEntry, row_index: int, parent_id: str = None):
        """
        :param parent_sql: The :class:`SQLTypeEntry` that owns this row.
        :param row_index: Zero-based index of this row within :attr:`SQLTypeEntry.data`.
        :param parent_id: Optional override for the parent identifier.  Defaults to the SHA-1 of
            ``parent_sql``.
        """
        self.__parent_sql: SQLTypeEntry = parent_sql
        self.__row_index: int = row_index

        super().__init__(
            parent_sql.data[row_index],
            "application/x-database-table-row",
            parent_id=parent_id or parent_sql[parent_sql.identifier_field].value,
        )

    @property
    def column_names(self) -> list[str]:
        """
        :return: The ordered list of column names for this row, sourced from the parent
            :class:`SQLTypeEntry`.  This is distinct from
            :attr:`~nuix_nli_lib.edrm.EntryInterface.fields`, which returns the EDRM EntryField
            key names (e.g. ``'MIME Type'``, ``'SHA-1'``, ``'Name'``, etc.).
        """
        return self.__parent_sql.row_fields

    @property
    def data(self) -> dict[str, Any]:
        """
        :return: The ``{column_name: value}`` dictionary for this specific row.
        """
        return self.__parent_sql.data[self.__row_index]

    @property
    def parent_sql(self) -> SQLTypeEntry:
        """
        :return: The :class:`SQLTypeEntry` that is the source of this row.
        """
        return self.__parent_sql
