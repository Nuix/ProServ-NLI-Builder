#!/usr/bin/env bash
# compare_outputs.sh — Structurally compare two EDRM XML files, normalising
# volatile fields (timestamps, absolute paths) before diffing.
#
# Usage:
#   bash integration-tests/scripts/compare_outputs.sh <reference.xml> <candidate.xml>
#
# Exit code:
#   0  - outputs are structurally equivalent
#   1  - outputs differ (diff printed to stdout)
#   2  - usage / file-not-found error

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <reference.xml> <candidate.xml>" >&2
    exit 2
fi

REFERENCE="$1"
CANDIDATE="$2"

if [[ ! -f "$REFERENCE" ]]; then
    echo "Reference file not found: $REFERENCE" >&2
    exit 2
fi

if [[ ! -f "$CANDIDATE" ]]; then
    echo "Candidate file not found: $CANDIDATE" >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# Normalise a single EDRM XML file:
#   - Replace all datetime-looking values with a fixed placeholder
#   - Replace absolute file paths with just the filename (basename)
#   - Sort lines within each <FieldValues> block so order differences don't fail
# ---------------------------------------------------------------------------
normalise() {
    local file="$1"
    python3 - "$file" <<'PYEOF'
import re
import sys
from xml.dom.minidom import parse

DATETIME_RE = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+\-]\d{2}:\d{2}')
ABS_PATH_RE = re.compile(r'(?:file://)?/[^\s"<>]+')

doc = parse(sys.argv[1])

# Normalise text nodes
for node in doc.getElementsByTagName("*"):
    for child in node.childNodes:
        if child.nodeType == child.TEXT_NODE:
            val = child.nodeValue
            val = DATETIME_RE.sub('TIMESTAMP', val)
            # Replace absolute paths with just the last component
            val = ABS_PATH_RE.sub(lambda m: m.group(0).rstrip('/').split('/')[-1], val)
            child.nodeValue = val
    # Normalise FilePath and LocationURI attributes
    for attr in ('FilePath', 'LocationURI'):
        if node.hasAttribute(attr):
            raw = node.getAttribute(attr)
            raw = ABS_PATH_RE.sub(lambda m: m.group(0).rstrip('/').split('/')[-1], raw)
            node.setAttribute(attr, raw)

print(doc.toprettyxml(indent='  '))
PYEOF
}

REF_NORM=$(normalise "$REFERENCE")
CAN_NORM=$(normalise "$CANDIDATE")

if diff <(echo "$REF_NORM") <(echo "$CAN_NORM") > /tmp/nli_diff.txt 2>&1; then
    echo "PASS: outputs are structurally equivalent."
    exit 0
else
    echo "FAIL: outputs differ:"
    cat /tmp/nli_diff.txt
    exit 1
fi
