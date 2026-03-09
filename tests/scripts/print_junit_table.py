#!/usr/bin/env python3
"""Parse a pytest JUnit XML and print a compact ASCII table of test outcomes."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: print_junit_table.py <junit-xml>")
    sys.exit(1)

xml_path = Path(sys.argv[1])
if not xml_path.exists():
    print(f"No junit xml file: {xml_path}")
    sys.exit(0)

try:
    tree = ET.parse(xml_path)
except ET.ParseError as e:
    print(f"Failed to parse XML: {e}")
    sys.exit(0)

root = tree.getroot()
rows = []
for testcase in root.iter('testcase'):
    status: str = 'UNKNOWN'
    classname = testcase.get('classname') or ''
    name = testcase.get('name') or ''
    file = testcase.get('file') or ''
    failure = testcase.find('failure')
    error = testcase.find('error')
    skipped = testcase.find('skipped')
    if failure is not None:
        status = 'FAILED'   # pylint: disable=invalid-name
        msg = (failure.get('message') or '')
    elif error is not None:
        status = 'ERROR'   # pylint: disable=invalid-name
        msg = (error.get('message') or '')
    elif skipped is not None:
        status = 'SKIPPED'   # pylint: disable=invalid-name
        msg = (skipped.get('message') or '')
    else:
        status = 'PASSED'   # pylint: disable=invalid-name
        msg = ''   # pylint: disable=invalid-name
    # keep only first line of message
    first_line = msg.strip().splitlines()[0] if msg else ''
    rows.append((file or classname, name, status, first_line))

if not rows:
    print('No tests recorded in JUnit XML')
    sys.exit(0)

# Compute column widths
cols = list(zip(*rows))
headers = ('File', 'Test', 'Status', 'Message')
col_widths = [max(len(headers[i]), max(len(str(x)) for x in cols[i])) for i in range(4)]

sep = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'   # pylint: disable=invalid-name
fmt = '| ' + ' | '.join('{:' + str(w) + '}' for w in col_widths) + ' |'   # pylint: disable=invalid-name

print('\n' + sep)
print(fmt.format(*headers))
print(sep)
for r in rows:
    print(fmt.format(*r))
print(sep + '\n')

# Exit code not handled here; caller should use pytest rc
sys.exit(0)
