#!/usr/bin/env python3
"""Generate a Markdown test report from JUnit XML results."""

import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


def parse_junit_xml(xml_file: str) -> dict: # pylint: disable=redefined-outer-name
    """Parse JUnit XML file and extract test results."""
    tree = ET.parse(xml_file)
    root = tree.getroot()

    results = { # pylint: disable=redefined-outer-name
        "tests": [],
        "suite_name": root.get("name", "Test Suite"),
        "timestamp": root.get("timestamp", datetime.now().isoformat()),
        "total": int(root.get("tests", 0)),
        "failures": int(root.get("failures", 0)),
        "skipped": int(root.get("skipped", 0)),
        "passed": 0,
    }

    results["passed"] = results["total"] - results["failures"] - results["skipped"]

    # Extract testcase elements
    for testcase in root.findall(".//testcase"):
        test_name = testcase.get("name", "Unknown")
        classname = testcase.get("classname", "Unknown")
        time = testcase.get("time", "0")

        # Check for failure, skip, or pass
        failure = testcase.find("failure")
        skip = testcase.find("skipped")

        if failure is not None:
            status = "❌ FAILED"
            message = failure.get("message", "")
        elif skip is not None:
            status = "⊘ SKIPPED"
            message = skip.get("message", "")
        else:
            status = "✅ PASSED"
            message = ""

        results["tests"].append({
            "classname": classname,
            "name": test_name,
            "status": status,
            "time": float(time),
            "message": message[:80] if message else "",  # Truncate long messages
        })

    return results


def generate_markdown_report(results: dict, output_file: str) -> None:  # pylint: disable=redefined-outer-name
    """Generate a Markdown report from test results."""

    # Calculate pass rate
    total = results["total"]
    passed = results["passed"]
    pass_rate = (passed / total * 100) if total > 0 else 0

    # Status color
    if results["failures"] == 0:
        status_icon = "✅"
        status_text = "ALL TESTS PASSED"
    else:
        status_icon = "❌"
        status_text = f"{results['failures']} TEST(S) FAILED"

    # Header
    report = f"""# Rapport des Tests - {results['suite_name']}

**Date:** {results['timestamp']}
**Suite:** {results['suite_name']}

---

## Summary

| Metric | Value |
| ------ | ----- |
| **Status** | {status_icon} {status_text} |
| **Total Tests** | {total} |
| **Passed** | ✅ {passed} |
| **Failed** | ❌ {results['failures']} |
| **Skipped** | ⊘ {results['skipped']} |
| **Pass Rate** | {pass_rate:.1f}% |

---

## Detailed Results

| Test Class | Test Name | Status | Time (s) |
| ---------- | --------- | ------ | -------- |
"""

    # Generate table rows
    for test in results["tests"]:
        classname = test["classname"].replace("test_", "").replace(".py", "")
        name = test["name"].replace("test_", "")
        if len(name) > 60:
            name = name[:57] + "..."
        report += f"| {classname} | {name} | {test['status']} | {test['time']:.3f} |\n"

    # Footer
    report += f"\n---\n\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ Rapport Markdown généré: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_test_report.py <junit_xml_file> [output_markdown_file]")
        sys.exit(1)

    xml_file = sys.argv[1]
    prefix = datetime.now().strftime("%Y-%m-%d")
    output_file = sys.argv[2] if len(sys.argv) > 2 else f"{prefix}_test_report.md"

    if not Path(xml_file).exists():
        print(f"❌ Error: XML file not found: {xml_file}")
        sys.exit(1)

    try:
        results = parse_junit_xml(xml_file)
        generate_markdown_report(results, output_file)
    except (ET.ParseError, FileNotFoundError, IOError) as e:
        print(f"❌ Error generating report: {e}")
        sys.exit(1)
