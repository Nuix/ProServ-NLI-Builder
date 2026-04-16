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
"""

import sys
from pathlib import Path

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


class CanonicalCSVRow(CSVRowEntry):
    """Minimal CSVRowEntry subclass that surfaces the 'Name' column as the item name."""

    def get_name(self) -> str:
        return f"({self['ID'].value}) {self['Name'].value}"

    @property
    def identifier_field(self) -> str:
        return "ID"


def build_reference_edrm(output_path: Path, as_nli: bool = False) -> None:
    builder = EDRMBuilder()
    builder.as_nli = as_nli
    builder.output_path = output_path

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
    print(f"Reference EDRM XML written to: {output_path}")


if __name__ == "__main__":
    build_reference_edrm(REFERENCE / "canonical_edrm.xml", as_nli=False)
