"""
Cross-language integration test suite for the NLI Python implementation.

These tests build an NLI from the canonical inputs in integration-tests/inputs/
and verify that the resulting EDRM XML structure matches the expected shape
defined by the canonical scenario.

All five canonical entry types are exercised:
  1. FileEntry        - a plain-text file (sample_document.txt)
  2. DirectoryEntry   - a folder of files (source_directory/)
  3. MappingEntry     - an inline dictionary (canonical mapping)
  4. CSVEntry rows    - three CSV rows from canonical_sample.csv
  5. JSONFileEntry    - a JSON object file (canonical_object.json)

Structural assertions are made against the EDRM XML using the xml.dom.minidom
API so they remain independent of serialisation order differences.  Volatile
fields (timestamps, absolute paths, file-system hash digests) are explicitly
excluded from structural comparisons.
"""

import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.dom.minidom import parseString, Element, Document

# Locate repo root so tests can be run from any working directory.
# integration_tests.py lives at <repo_root>/python/test/integration_tests.py
# so the repo root is three parents up.
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent.parent.parent  # test/ -> python/ -> <repo_root>
_PYTHON_MAIN = _REPO_ROOT / "python" / "main"
if str(_PYTHON_MAIN) not in sys.path:
    sys.path.insert(0, str(_PYTHON_MAIN))

from nuix_nli_lib.edrm import EDRMBuilder, FileEntry, DirectoryEntry, MappingEntry
from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry, JSONFileEntry
from nuix_nli_lib.nli.nli_generator import NLIGenerator

# Canonical inputs shared with the Java integration tests
_INTEGRATION_INPUTS = _REPO_ROOT / "integration-tests" / "inputs"
_CANONICAL_CSV = _INTEGRATION_INPUTS / "canonical_sample.csv"
_CANONICAL_JSON = _INTEGRATION_INPUTS / "canonical_object.json"
_CANONICAL_FILE = _INTEGRATION_INPUTS / "files" / "sample_document.txt"
_CANONICAL_DIR = _INTEGRATION_INPUTS / "source_directory"
_CANONICAL_MAPPING = {
    "source": "integration-test",
    "type": "canonical-mapping",
    "count": 42,
}

# SHA-1 of the canonical plain-text file (stable as long as the file does not change)
_EXPECTED_FILE_SHA1 = "b92f8836c67cb504fc9345936d7ddbf594dc1131"
# SHA-1 of the canonical JSON file
_EXPECTED_JSON_SHA1 = "23ec3d4af2a57fe92ffd35c110e87cf5efdb909d"
# SHA-1 of the canonical CSV file
_EXPECTED_CSV_SHA1 = "4f184422d549e0eed7a17f2a0bc963822ced1930"


class CanonicalCSVRow(CSVRowEntry):
    """Minimal CSVRowEntry subclass that surfaces the 'Name' column as the item name."""

    def get_name(self) -> str:
        return f"({self['ID'].value}) {self['Name'].value}"

    @property
    def identifier_field(self) -> str:
        return "ID"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_canonical_edrm(as_nli: bool = False) -> tuple[EDRMBuilder, str]:
    """
    Build the canonical EDRM load file using all five entry types and return
    the (builder, xml_string) tuple.  The XML is serialised in-memory so it
    can be inspected without writing to disk.
    """
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        output_path = Path(tmp.name)

    builder = EDRMBuilder()
    builder.as_nli = as_nli
    builder.output_path = output_path

    try:
        # 1. FileEntry
        file_entry = FileEntry(str(_CANONICAL_FILE), "text/plain")
        file_id = builder.add_entry(file_entry)

        # 2. DirectoryEntry
        dir_entry = DirectoryEntry(str(_CANONICAL_DIR))
        dir_id = builder.add_entry(dir_entry)

        # 3. MappingEntry (child of file)
        builder.add_mapping(_CANONICAL_MAPPING, "application/x-database-table-row", file_id)

        # 4. CSV-sourced rows (child of directory)
        csv_entry = CSVEntry(
            str(_CANONICAL_CSV),
            row_generator=CanonicalCSVRow,
            parent_id=dir_id,
        )
        csv_entry.add_to_builder(builder)

        # 5. JSON-sourced entry (top-level)
        json_entry = JSONFileEntry(str(_CANONICAL_JSON))
        json_entry.add_to_builder(builder)

        builder.save()
        xml_text = output_path.read_text(encoding="UTF-8")
    finally:
        output_path.unlink(missing_ok=True)
    return builder, xml_text


def _parse_xml(xml_text: str) -> Document:
    return parseString(xml_text)


def _get_documents(doc: Document) -> list[Element]:
    """
    Return Document elements that are direct children of the <Documents> container.
    Using getElementsByTagName would also return <Document> nodes nested inside
    <Folder> elements in the Folders section, giving an inflated count.
    """
    docs_container = doc.getElementsByTagName("Documents").item(0)
    if docs_container is None:
        return []
    return [
        n for n in docs_container.childNodes
        if n.nodeType == n.ELEMENT_NODE and n.tagName == "Document"
    ]


def _doc_by_id(documents: list[Element], doc_id: str) -> Element | None:
    for d in documents:
        if d.getAttribute("DocID") == doc_id:
            return d
    return None


def _get_relationships(doc: Document) -> list[tuple[str, str]]:
    """Return a list of (parent_id, child_id) tuples from the Relationships section."""
    rels = []
    for rel in doc.getElementsByTagName("Relationship"):
        parent = rel.getAttribute("ParentDocId")
        child = rel.getAttribute("ChildDocId")
        rels.append((parent, child))
    return rels


def _field_value(document_element: Element, field_key: str) -> str | None:
    """Return the text content of the field element with the given key tag name."""
    nodes = document_element.getElementsByTagName(field_key)
    if nodes.length == 0:
        return None
    return nodes.item(0).firstChild.nodeValue if nodes.item(0).firstChild else ""


def _get_field_key_for_name(edrm_doc: Document, field_name: str) -> str | None:
    """
    Look up the field key (e.g. 'field_7') for a given EDRM field name (e.g. 'Name').
    """
    for field in edrm_doc.getElementsByTagName("Field"):
        if field.getAttribute("Name") == field_name:
            return field.getAttribute("Key")
    return None


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestCanonicalDocumentCount(unittest.TestCase):
    """Verify that the canonical scenario produces the expected number of Documents."""

    @classmethod
    def setUpClass(cls):
        _, xml = _build_canonical_edrm()
        cls.doc = _parse_xml(xml)
        cls.documents = _get_documents(cls.doc)

    def test_total_document_count(self):
        """
        Expected breakdown:
          1  FileEntry  (sample_document.txt)
          1  DirectoryEntry (source_directory)
          1  MappingEntry (canonical-mapping, child of file)
          1  CSVEntry (canonical_sample.csv, child of dir)
          3  CSVRowEntry (Alpha, Beta, Gamma)
          1  JSONFileEntry (canonical_object.json)
          1  JSONObjectEntry (top-level JSON Object child)
          1  JSONObjectEntry (metadata nested object)
          1  JSONArrayEntry (tags array)
        Total = 11
        """
        self.assertEqual(len(self.documents), 11)

    def test_document_mime_types_present(self):
        """All five canonical MIME types must appear in the output."""
        mime_types = {d.getAttribute("MimeType") for d in self.documents}
        self.assertIn("text/plain", mime_types, "FileEntry MIME type missing")
        self.assertIn("filesystem/directory", mime_types, "DirectoryEntry MIME type missing")
        self.assertIn("application/x-database-table-row", mime_types, "MappingEntry MIME type missing")
        self.assertIn("text/csv", mime_types, "CSVEntry MIME type missing")
        self.assertIn("application/json", mime_types, "JSONFileEntry MIME type missing")


class TestFileEntryStructure(unittest.TestCase):
    """Assertions about the canonical FileEntry (sample_document.txt)."""

    @classmethod
    def setUpClass(cls):
        _, xml = _build_canonical_edrm()
        cls.doc = _parse_xml(xml)
        cls.documents = _get_documents(cls.doc)
        # The file's DocID is its SHA-1 hash
        cls.file_doc = _doc_by_id(cls.documents, _EXPECTED_FILE_SHA1)

    def test_file_document_exists(self):
        """The FileEntry must appear in the EDRM output with its SHA-1 as the DocID."""
        self.assertIsNotNone(
            self.file_doc,
            f"Document with DocID={_EXPECTED_FILE_SHA1} not found",
        )

    def test_file_mime_type(self):
        """The FileEntry must carry the MIME type it was registered with."""
        self.assertEqual(self.file_doc.getAttribute("MimeType"), "text/plain")

    def test_file_name_field(self):
        """The 'Name' field must equal the file name."""
        name_key = _get_field_key_for_name(self.doc, "Name")
        self.assertIsNotNone(name_key, "Name field not defined in EDRM Fields section")
        name_value = _field_value(self.file_doc, name_key)
        self.assertEqual(name_value, "sample_document.txt")

    def test_file_sha1_field(self):
        """The 'SHA-1' field must equal the known digest of the file."""
        sha1_key = _get_field_key_for_name(self.doc, "SHA-1")
        sha1_value = _field_value(self.file_doc, sha1_key)
        self.assertEqual(sha1_value, _EXPECTED_FILE_SHA1)

    def test_file_has_native_file_element(self):
        """The FileEntry must include a <File FileType="Native"> element."""
        files_elem = self.file_doc.getElementsByTagName("Files")
        self.assertGreater(files_elem.length, 0, "No <Files> element found")
        file_elems = files_elem.item(0).getElementsByTagName("File")
        native_files = [
            f for f in file_elems
            if f.getAttribute("FileType") == "Native"
        ]
        self.assertGreater(len(native_files), 0, "No Native <File> element found")


class TestDirectoryEntryStructure(unittest.TestCase):
    """Assertions about the canonical DirectoryEntry (source_directory/)."""

    @classmethod
    def setUpClass(cls):
        _, xml = _build_canonical_edrm()
        cls.doc = _parse_xml(xml)
        cls.documents = _get_documents(cls.doc)
        # Locate by MIME type; there is exactly one directory
        cls.dir_doc = next(
            (d for d in cls.documents if d.getAttribute("MimeType") == "filesystem/directory"),
            None,
        )

    def test_directory_document_exists(self):
        """A DirectoryEntry must appear with MimeType=filesystem/directory."""
        self.assertIsNotNone(self.dir_doc, "DirectoryEntry not found in EDRM output")

    def test_directory_name_field(self):
        """The 'Name' field of the directory must equal the folder name."""
        name_key = _get_field_key_for_name(self.doc, "Name")
        name_value = _field_value(self.dir_doc, name_key)
        self.assertEqual(name_value, "source_directory")

    def test_directory_is_parent_of_csv(self):
        """The DirectoryEntry must be the parent of the CSVEntry in the Relationships."""
        dir_id = self.dir_doc.getAttribute("DocID")
        rels = _get_relationships(self.doc)
        csv_doc = next(
            (d for d in self.documents if d.getAttribute("MimeType") == "text/csv"),
            None,
        )
        self.assertIsNotNone(csv_doc, "CSVEntry not found")
        csv_id = csv_doc.getAttribute("DocID")
        self.assertIn(
            (dir_id, csv_id),
            rels,
            f"Expected Relationship ({dir_id} -> {csv_id}) not found",
        )


class TestMappingEntryStructure(unittest.TestCase):
    """Assertions about the canonical MappingEntry (inline dictionary)."""

    @classmethod
    def setUpClass(cls):
        _, xml = _build_canonical_edrm()
        cls.doc = _parse_xml(xml)
        cls.documents = _get_documents(cls.doc)
        # The mapping is identified by its 'source' field value = "integration-test"
        # and is child of the FileEntry
        cls.mapping_doc = None
        source_key = _get_field_key_for_name(cls.doc, "source")
        if source_key:
            for d in cls.documents:
                if _field_value(d, source_key) == "integration-test":
                    cls.mapping_doc = d
                    break

    def test_mapping_document_exists(self):
        """The MappingEntry with source='integration-test' must exist."""
        self.assertIsNotNone(self.mapping_doc, "MappingEntry not found in EDRM output")

    def test_mapping_mime_type(self):
        """The MappingEntry must carry the application/x-database-table-row MIME type."""
        self.assertEqual(
            self.mapping_doc.getAttribute("MimeType"),
            "application/x-database-table-row",
        )

    def test_mapping_is_child_of_file(self):
        """The MappingEntry must be a child of the FileEntry in the Relationships section."""
        mapping_id = self.mapping_doc.getAttribute("DocID")
        rels = _get_relationships(self.doc)
        parent_ids = [parent for parent, child in rels if child == mapping_id]
        self.assertIn(
            _EXPECTED_FILE_SHA1,
            parent_ids,
            "MappingEntry is not a child of the FileEntry",
        )

    def test_mapping_count_field(self):
        """The 'count' field must contain the value 42."""
        count_key = _get_field_key_for_name(self.doc, "count")
        self.assertIsNotNone(count_key)
        count_value = _field_value(self.mapping_doc, count_key)
        self.assertEqual(count_value, "42")

    def test_mapping_has_inline_content(self):
        """The MappingEntry must have an InlineContent element (text content)."""
        inline = self.mapping_doc.getElementsByTagName("InlineContent")
        self.assertGreater(inline.length, 0, "No <InlineContent> found for MappingEntry")


class TestCSVEntryStructure(unittest.TestCase):
    """Assertions about the canonical CSV scenario (CSVEntry + CSVRowEntry)."""

    @classmethod
    def setUpClass(cls):
        _, xml = _build_canonical_edrm()
        cls.doc = _parse_xml(xml)
        cls.documents = _get_documents(cls.doc)
        cls.csv_doc = _doc_by_id(cls.documents, _EXPECTED_CSV_SHA1)
        # CSV rows have DocIDs "1", "2", "3" (the ID column values)
        cls.row_docs = [
            _doc_by_id(cls.documents, "1"),
            _doc_by_id(cls.documents, "2"),
            _doc_by_id(cls.documents, "3"),
        ]

    def test_csv_document_exists(self):
        """The CSVEntry must appear in the EDRM output."""
        self.assertIsNotNone(self.csv_doc, "CSVEntry (canonical_sample.csv) not found")

    def test_csv_row_count(self):
        """There must be exactly 3 CSV row documents."""
        self.assertTrue(all(r is not None for r in self.row_docs), "Not all 3 CSV rows found")

    def test_csv_row_names(self):
        """Each CSV row must have the expected Name value."""
        name_key = _get_field_key_for_name(self.doc, "Name")
        expected_names = {
            "1": "(1) Alpha Record",
            "2": "(2) Beta Record",
            "3": "(3) Gamma Record",
        }
        for row_id, expected_name in expected_names.items():
            row_doc = _doc_by_id(self.documents, row_id)
            self.assertIsNotNone(row_doc, f"CSV row DocID={row_id} not found")
            actual_name = _field_value(row_doc, name_key)
            self.assertEqual(actual_name, expected_name, f"Name mismatch for row {row_id}")

    def test_csv_rows_are_children_of_csv(self):
        """Each CSV row must be a child of the CSVEntry in Relationships."""
        rels = _get_relationships(self.doc)
        for row_id in ("1", "2", "3"):
            self.assertIn(
                (_EXPECTED_CSV_SHA1, row_id),
                rels,
                f"CSV row {row_id} is not a child of the CSVEntry",
            )

    def test_csv_category_field(self):
        """The Category field must be present for CSV row documents."""
        category_key = _get_field_key_for_name(self.doc, "Category")
        self.assertIsNotNone(category_key, "Category field not defined")
        row1 = _doc_by_id(self.documents, "1")
        self.assertEqual(_field_value(row1, category_key), "TypeA")
        row2 = _doc_by_id(self.documents, "2")
        self.assertEqual(_field_value(row2, category_key), "TypeB")


class TestJSONEntryStructure(unittest.TestCase):
    """Assertions about the canonical JSON scenario (JSONFileEntry)."""

    @classmethod
    def setUpClass(cls):
        _, xml = _build_canonical_edrm()
        cls.doc = _parse_xml(xml)
        cls.documents = _get_documents(cls.doc)
        cls.json_file_doc = _doc_by_id(cls.documents, _EXPECTED_JSON_SHA1)
        # Locate the top-level JSON Object child (child of the JSONFileEntry)
        cls.json_object_doc = None
        rels = _get_relationships(cls.doc)
        json_object_children = [c for p, c in rels if p == _EXPECTED_JSON_SHA1]
        if json_object_children:
            cls.json_object_doc = _doc_by_id(cls.documents, json_object_children[0])

    def test_json_file_document_exists(self):
        """The JSONFileEntry must appear with its SHA-1 as DocID."""
        self.assertIsNotNone(
            self.json_file_doc,
            f"JSONFileEntry with DocID={_EXPECTED_JSON_SHA1} not found",
        )

    def test_json_file_mime_type(self):
        """The JSONFileEntry must carry MIME type application/json."""
        self.assertEqual(
            self.json_file_doc.getAttribute("MimeType"), "application/json"
        )

    def test_json_object_is_child_of_file(self):
        """The JSONObjectEntry child must exist and be a child of the JSONFileEntry."""
        self.assertIsNotNone(
            self.json_object_doc,
            "No child of JSONFileEntry found (expected a JSONObjectEntry)",
        )
        self.assertEqual(
            self.json_object_doc.getAttribute("MimeType"), "application/x-json-object"
        )

    def test_json_object_project_field(self):
        """The 'project' field of the JSON Object must equal 'NLI Integration Test'."""
        project_key = _get_field_key_for_name(self.doc, "project")
        self.assertIsNotNone(project_key, "'project' field not defined in EDRM output")
        value = _field_value(self.json_object_doc, project_key)
        self.assertEqual(value, "NLI Integration Test")

    def test_json_object_has_nested_metadata_child(self):
        """The 'metadata' nested object must be a child of the JSON Object."""
        json_obj_id = self.json_object_doc.getAttribute("DocID")
        rels = _get_relationships(self.doc)
        children = [c for p, c in rels if p == json_obj_id]
        self.assertGreater(len(children), 0, "JSON Object has no children")
        # Find the metadata child (MimeType x-json-object, name='metadata')
        name_key = _get_field_key_for_name(self.doc, "Name")
        metadata_doc = None
        for child_id in children:
            child_doc = _doc_by_id(self.documents, child_id)
            if child_doc and _field_value(child_doc, name_key) == "metadata":
                metadata_doc = child_doc
                break
        self.assertIsNotNone(metadata_doc, "Nested 'metadata' JSON object not found as a child")

    def test_json_array_tags_is_child_of_json_object(self):
        """The 'tags' JSON array must be a child of the top-level JSON Object."""
        json_obj_id = self.json_object_doc.getAttribute("DocID")
        rels = _get_relationships(self.doc)
        children = [c for p, c in rels if p == json_obj_id]
        name_key = _get_field_key_for_name(self.doc, "Name")
        tags_doc = None
        for child_id in children:
            child_doc = _doc_by_id(self.documents, child_id)
            if (child_doc
                    and child_doc.getAttribute("MimeType") == "application/x-json-array"
                    and _field_value(child_doc, name_key) == "tags"):
                tags_doc = child_doc
                break
        self.assertIsNotNone(tags_doc, "JSON Array 'tags' not found as a child of JSON Object")


class TestRelationshipIntegrity(unittest.TestCase):
    """Cross-cutting assertions about the complete Relationships structure."""

    @classmethod
    def setUpClass(cls):
        _, xml = _build_canonical_edrm()
        cls.doc = _parse_xml(xml)
        cls.documents = _get_documents(cls.doc)
        cls.rels = _get_relationships(cls.doc)

    def test_all_child_doc_ids_exist(self):
        """Every ChildDocId in Relationships must correspond to a real Document."""
        doc_ids = {d.getAttribute("DocID") for d in self.documents}
        for parent, child in self.rels:
            self.assertIn(
                child, doc_ids, f"Relationship child DocID={child} has no matching Document"
            )

    def test_all_parent_doc_ids_exist(self):
        """Every ParentDocId in Relationships must correspond to a real Document."""
        doc_ids = {d.getAttribute("DocID") for d in self.documents}
        for parent, child in self.rels:
            self.assertIn(
                parent, doc_ids, f"Relationship parent DocID={parent} has no matching Document"
            )

    def test_mapping_child_of_file(self):
        """The MappingEntry must be a child of the FileEntry."""
        source_key = _get_field_key_for_name(self.doc, "source")
        mapping_id = None
        if source_key:
            for d in self.documents:
                if _field_value(d, source_key) == "integration-test":
                    mapping_id = d.getAttribute("DocID")
                    break
        self.assertIsNotNone(mapping_id)
        self.assertIn((_EXPECTED_FILE_SHA1, mapping_id), self.rels)

    def test_csv_parent_of_all_rows(self):
        """The CSVEntry must be parent to all three CSV row documents."""
        for row_id in ("1", "2", "3"):
            self.assertIn((_EXPECTED_CSV_SHA1, row_id), self.rels)


class TestNLIPackaging(unittest.TestCase):
    """Verify that the NLI ZIP container is correctly structured."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.nli_path = Path(self.tmp_dir) / "integration_test.nli"
        generator = NLIGenerator()

        file_id = generator.add_file(str(_CANONICAL_FILE), "text/plain")
        dir_id = generator.add_directory(str(_CANONICAL_DIR))
        generator.add_mapping(_CANONICAL_MAPPING, "application/x-database-table-row", file_id)

        csv_entry = CSVEntry(
            str(_CANONICAL_CSV),
            row_generator=CanonicalCSVRow,
            parent_id=dir_id,
        )
        generator.add_entry(csv_entry)

        json_entry = JSONFileEntry(str(_CANONICAL_JSON))
        generator.add_entry(json_entry)

        generator.save(self.nli_path)

    def test_nli_file_created(self):
        """The NLI file must be created at the expected path."""
        self.assertTrue(self.nli_path.exists(), f"NLI file not found at {self.nli_path}")

    def test_nli_is_valid_zip(self):
        """The NLI file must be a valid ZIP archive."""
        self.assertTrue(zipfile.is_zipfile(self.nli_path), "NLI file is not a valid ZIP")

    def test_nli_contains_metadata_xml(self):
        """The NLI ZIP must contain ._metadata/image_contents.xml."""
        with zipfile.ZipFile(self.nli_path, "r") as zf:
            names = zf.namelist()
        self.assertIn(
            "._metadata/image_contents.xml",
            names,
            "._metadata/image_contents.xml not found in NLI ZIP",
        )

    def test_nli_contains_sha1_sidecar(self):
        """The NLI ZIP must contain ._metadata/image_contents.sha1_hash."""
        with zipfile.ZipFile(self.nli_path, "r") as zf:
            names = zf.namelist()
        self.assertIn(
            "._metadata/image_contents.sha1_hash",
            names,
            "._metadata/image_contents.sha1_hash not found in NLI ZIP",
        )

    def test_sha1_sidecar_matches_metadata_xml(self):
        """The SHA-1 sidecar must contain the correct hash of image_contents.xml."""
        with zipfile.ZipFile(self.nli_path, "r") as zf:
            xml_bytes = zf.read("._metadata/image_contents.xml")
            sha1_bytes = zf.read("._metadata/image_contents.sha1_hash")
        expected_hash = hashlib.sha1(xml_bytes, usedforsecurity=False).digest()
        self.assertEqual(
            sha1_bytes,
            expected_hash,
            "SHA-1 sidecar content does not match hash of image_contents.xml",
        )

    def test_nli_contains_native_file(self):
        """The NLI ZIP must contain the native file from the FileEntry."""
        with zipfile.ZipFile(self.nli_path, "r") as zf:
            names = zf.namelist()
        native_entries = [n for n in names if "sample_document.txt" in n]
        self.assertGreater(
            len(native_entries),
            0,
            "sample_document.txt not found in NLI ZIP",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
