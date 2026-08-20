#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTS_DIR="$(dirname "$SCRIPT_DIR")"
STAMP="$(date +%y-%m-%d-%H-%M)"
JUNIT_FILE="$TESTS_DIR/reports/junit/back/${STAMP}_test_results.xml"
REPORT_FILE="$TESTS_DIR/reports/back/${STAMP}_test_report_back.md"
COVERAGE_DIR="$TESTS_DIR/reports/coverage"

mkdir -p "$(dirname "$JUNIT_FILE")" "$(dirname "$REPORT_FILE")" "$COVERAGE_DIR"

echo "🧪 Running pytest for back/ (junit -> $JUNIT_FILE)"
set +e
COVERAGE_FILE="$COVERAGE_DIR/.coverage" coverage run --parallel-mode -m pytest -v --tb=short --disable-warnings --log-cli-level=INFO "$TESTS_DIR/back/" --junitxml="$JUNIT_FILE"
RC=$?
set -e

if command -v xmllint >/dev/null 2>&1; then
	xmllint --format "$JUNIT_FILE" > "${JUNIT_FILE}.tmp" && mv "${JUNIT_FILE}.tmp" "$JUNIT_FILE"
fi

python3 "$SCRIPT_DIR/generate_test_report.py" "$JUNIT_FILE" "$REPORT_FILE" || true
python3 "$SCRIPT_DIR/print_junit_table.py" "$JUNIT_FILE" || true

exit $RC