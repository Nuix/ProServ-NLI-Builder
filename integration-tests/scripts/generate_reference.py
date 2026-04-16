"""
Generate the canonical reference EDRM XML used by the integration test suite.

Run this script from the repository root to regenerate the reference output:
    python integration-tests/scripts/generate_reference.py

This script exercises all five canonical input scenarios:
  1. A FileEntry (sample_document.txt)
  2. A DirectoryEntry (source_directory/)
  3. A MappingEntry (inline dictionary)
  4. A CSV-sourced row (canonical_sample.csv via CSVEntry + CSVRowEntry)
  5. A JSON-sourced entry (canonical_object.json via JSONFileEntry)

The generated XML is normalised before being committed so that the reference
file is machine-independent:
  - Absolute file paths are reduced to their basename only.
  - Timestamps are replaced with a fixed placeholder (TIMESTAMP).
  - <FieldValues> child elements are sorted by tag name so serialisation-order
    differences between environments don't create spurious git diffs.
"""

import re
import sys
import tempfile
from pathlib import Path
from xml.dom.minidom import parse

# Allow running from the repo root without installing the package
repo_root = Path(__file__).parent.parent.parent
python_main = repo_root / "python" / "main"
if str(python_main) not in sys.path:
    sys.path.insert(0, str(python_main))

from nuix_nli_lib.edrm import EDRMBuilder, FileEntry, DirectoryEntry, MappingEntry
from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry, JSONFileEntry

INPUTS = Path(__file__).parent.parent / "inputs"
REFERENCE = Path(__file__).parent.parent / "reference"
REFERENCE.mkdir(exist_ok=True)

DATETIME_RE = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+\-]\d{2}:\d{2}')
ABS_PATH_RE = re.compile(r'(?:file://|(?<!\w))/[^\s"<>]+')


class CanonicalCSVRow(CSVRowEntry):
    """Minimal CSVRowEntry subclass that surfaces the 'Name' column as the item name."""

    def get_name(self) -> str:
        return f"({self['ID'].value}) {self['Name'].value}"

    @property
    def identifier_field(self) -> str:
        return "ID"


def _normalise_xml(raw_xml_path: Path) -> str:
    """
    Parse the given XML file and return a normalised XML string that is
    machine-independent and stable across runs:
      - Timestamps replaced with 'TIMESTAMP'
      - Absolute paths reduced to their basename
      - <FieldValues> children sorted by tag name
    """
    doc = parse(str(raw_xml_path))

    for node in doc.getElementsByTagName("*"):
        for child in node.childNodes:
            if child.nodeType == child.TEXT_NODE:
                val = child.nodeValue
                val = DATETIME_RE.sub('TIMESTAMP', val)
                val = ABS_PATH_RE.sub(
                    lambda m: m.group(0).rstrip('/').split('/')[-1], val
                )
                child.nodeValue = val
        for attr in ('FilePath', 'LocationURI'):
            if node.hasAttribute(attr):
                raw = node.getAttribute(attr)
                raw = ABS_PATH_RE.sub(
                    lambda m: m.group(0).rstrip('/').split('/')[-1], raw
                )
                node.setAttribute(attr, raw)

    # Sort <FieldValues> children by tag name for stable, order-independent output.
    for fv in doc.getElementsByTagName("FieldValues"):
        children = [n for n in fv.childNodes if n.nodeType == n.ELEMENT_NODE]
        for child in children:
            fv.removeChild(child)
        for child in sorted(children, key=lambda n: n.tagName):
            fv.appendChild(child)

    return doc.toprettyxml(indent='  ')


def build_reference_edrm(output_path: Path, as_nli: bool = False) -> None:
    # Build to a temp file first so we can post-process before committing.
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        builder = EDRMBuilder()
        builder.as_nli = as_nli
        builder.output_path = tmp_path

        # 1. FileEntry
        file_entry = FileEntry(
            str(INPUTS / "files" / "sample_document.txt"),
            "text/plain",
        )
        file_id = builder.add_entry(file_entry)

        # 2. DirectoryEntry
        dir_entry = DirectoryEntry(str(INPUTS / "source_directory"))
        dir_id = builder.add_entry(dir_entry)

        # 3. MappingEntry (inline dictionary)
        mapping = {
            "source": "integration-test",
            "type": "canonical-mapping",
            "count": 42,
        }
        map_id = builder.add_mapping(mapping, "application/x-database-table-row", file_id)

        # 4. CSV-sourced rows (CSVEntry + CSVRowEntry)
        csv_entry = CSVEntry(
            str(INPUTS / "canonical_sample.csv"),
            row_generator=CanonicalCSVRow,
            parent_id=dir_id,
        )
        csv_entry.add_to_builder(builder)

        # 5. JSON-sourced entry (JSONFileEntry)
        json_entry = JSONFileEntry(str(INPUTS / "canonical_object.json"))
        json_entry.add_to_builder(builder)

        builder.save()

        # Post-process: normalise paths and timestamps so the reference is portable.
        normalised = _normalise_xml(tmp_path)
        output_path.write_text(normalised, encoding="utf-8")
        print(f"Reference EDRM XML written to: {output_path}")
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    build_reference_edrm(REFERENCE / "canonical_edrm.xml", as_nli=False)
