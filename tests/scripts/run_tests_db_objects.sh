#!/usr/bin/env bash
set -euo pipefail

# Lance pytest sur le dossier tests/db_objects/, produit un JUnit XML,
# puis appelle le petit script Python pour afficher un tableau lisible.

TESTS_DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"
SCRIPT_DIR="${TESTS_DIR}/scripts"
JUNIT_FILE="$TESTS_DIR/reports/junit/unit_db/$(date +%y-%m-%d-%H-%M)_test_results.xml"
REPORT_FILE="$TESTS_DIR/reports/unit_db/$(date +%y-%m-%d-%H-%M)_test_report_db_objects.md"
COVERAGE_DIR="$TESTS_DIR/reports/coverage"
mkdir -p "$(dirname "$JUNIT_FILE")" "$TESTS_DIR/reports/unit_db" "$COVERAGE_DIR"

echo "🧪 Running pytest for db_objects/ (junit -> $JUNIT_FILE)"
# Run pytest and capture exit code
set +e
COVERAGE_FILE="$COVERAGE_DIR/.coverage" coverage run --parallel-mode -m pytest -v --tb=short --disable-warnings --log-cli-level=INFO "$TESTS_DIR/db_objects/" --junitxml="$JUNIT_FILE"
RC=$?
set -e

# Format the XML file with proper indentation if xmllint is available
if command -v xmllint &> /dev/null; then
	xmllint --format "$JUNIT_FILE" > "${JUNIT_FILE}.tmp" && mv "${JUNIT_FILE}.tmp" "$JUNIT_FILE"
fi

# Generate Markdown report
python3 "$SCRIPT_DIR/generate_test_report.py" "$JUNIT_FILE" "$REPORT_FILE" || true

# Print a compact table of results
python3 "$SCRIPT_DIR/print_junit_table.py" "$JUNIT_FILE" || true

exit $RC
