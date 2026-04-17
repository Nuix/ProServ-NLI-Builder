# Cross-Language Integration Tests

This directory contains the canonical test inputs, reference outputs, helper
scripts, and documentation needed to verify that the Python and Java NLI
implementations produce structurally equivalent EDRM XML output for the same
inputs.

---

## Purpose

Both implementations (Python in `python/`, Java in `java/`) are expected to
produce structurally identical EDRM XML and NLI ZIP output for the same input
data.  As features are added or changed in one implementation and later
back-ported to the other, behavioural drift can accumulate silently.

These integration tests provide a shared set of canonical inputs and a
reference output so that both implementations can be compared automatically.

---

## Directory Layout

```
integration-tests/
├── inputs/                    # Shared canonical inputs (checked into VCS)
│   ├── files/
│   │   └── sample_document.txt        # FileEntry scenario
│   ├── source_directory/              # DirectoryEntry scenario
│   │   ├── readme.txt
│   │   └── data.txt
│   ├── canonical_sample.csv           # CSVEntry + CSVRowEntry scenario
│   └── canonical_object.json          # JSONFileEntry scenario
├── reference/                 # Reference EDRM XML (generated, checked into VCS)
│   └── canonical_edrm.xml             # Known-good output from Python implementation
├── scripts/
│   ├── generate_reference.py  # Regenerate reference/canonical_edrm.xml
│   └── compare_outputs.sh     # Compare Python vs Java outputs structurally
└── README.md                  # This file
```

---

## Canonical Scenario

The canonical scenario exercises all five required entry types in a single
EDRM load file:

| # | Entry Type     | Input                          | Parent         |
|---|----------------|-------------------------------|----------------|
| 1 | `FileEntry`    | `inputs/files/sample_document.txt` | (top-level) |
| 2 | `DirectoryEntry` | `inputs/source_directory/`   | (top-level) |
| 3 | `MappingEntry` | inline dict `{source, type, count}` | FileEntry |
| 4 | `CSVEntry` + rows | `inputs/canonical_sample.csv` | DirectoryEntry |
| 5 | `JSONFileEntry` | `inputs/canonical_object.json` | (top-level) |

The expected EDRM output document contains **11 Documents** total:

- 1 FileEntry (sample_document.txt)
- 1 DirectoryEntry (source_directory)
- 1 MappingEntry (canonical mapping)
- 1 CSVEntry (canonical_sample.csv)
- 3 CSVRowEntry (Alpha Record, Beta Record, Gamma Record)
- 1 JSONFileEntry (canonical_object.json)
- 1 JSONObjectEntry (top-level JSON Object)
- 1 JSONObjectEntry (nested `metadata` object)
- 1 JSONArrayEntry (`tags` array)

---

## Running the Python Integration Tests

From the repository root (or `python/` directory):

```bash
cd python/test
PYTHONPATH=../main python -m pytest integration_tests.py -v
```

Or from anywhere using the installed package:

```bash
python -m pytest python/test/integration_tests.py -v
```

The tests verify:
- Correct document count and MIME types
- SHA-1 hashes match known-good digests for stable files
- Parent-child relationships in the `<Relationships>` section
- Field values for CSV rows and JSON entries
- NLI ZIP structure (metadata XML, SHA-1 sidecar, native files)

---

## Regenerating the Reference Output

If the canonical inputs change, regenerate the reference EDRM XML:

```bash
python integration-tests/scripts/generate_reference.py
```

This will overwrite `integration-tests/reference/canonical_edrm.xml`.

After regenerating, update the SHA-1 constants in
`python/test/integration_tests.py` if any input files changed.

---

## Cross-Language Comparison (Manual)

Use the comparison script to diff Python and Java outputs structurally:

```bash
# 1. Generate Python output
python integration-tests/scripts/generate_reference.py

# 2. Generate Java output (adjust path to the Java project's equivalent command)
cd java && ./gradlew integrationTest && cd ..

# 3. Compare
bash integration-tests/scripts/compare_outputs.sh \
    integration-tests/reference/canonical_edrm.xml \
    java/build/integration-test-output/canonical_edrm.xml
```

The comparison script normalises volatile fields (timestamps, absolute paths)
before diffing so that environment differences do not cause false failures.

---

## What Is and Is Not Compared

### Compared (structural)
- Document count
- Document MIME types
- Relationship parent/child structure
- Field names defined in the `<Fields>` section
- Stable field values: `Name`, `SHA-1`, CSV field values, JSON field values

### Not compared (volatile, environment-specific)
- Timestamps (`Item Date`, `File Accessed`, `File Created`, `File Modified`)
- Absolute file paths (`Path Name`, `LocationURI`, `FilePath` in `<ExternalFile>`)
- MD5 hashes in `<ExternalFile>` (these depend on file content which is the same, but the field is only checked for presence)

---

## Adding New Scenarios

1. Add input files to `inputs/`.
2. Update `scripts/generate_reference.py` to include the new entries.
3. Run `generate_reference.py` to update the reference XML.
4. Add corresponding test cases to `python/test/integration_tests.py`.
5. Add corresponding Java test cases to the Java project.
