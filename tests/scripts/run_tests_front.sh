#!/usr/bin/env bash
set -euo pipefail

# Lance pytest sur le dossier tests/front/, produit un JUnit XML,
# puis appelle le petit script Python pour afficher un tableau lisible.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTS_DIR="$(dirname "$SCRIPT_DIR")"
JUNIT_FILE="$TESTS_DIR/reports/junit/front/$(date +%y-%m-%d-%H-%M)_test_results.xml"

echo "🧪 Running pytest for front/ (junit -> $JUNIT_FILE)"
# Run pytest and capture exit code
pytest -v --tb=short --disable-warnings --log-cli-level=INFO "$TESTS_DIR/front/" --junitxml="$JUNIT_FILE"
RC=$?
# Format the XML file with proper indentation if xmllint is available
if command -v xmllint &> /dev/null; then
	xmllint --format "$JUNIT_FILE" > "${JUNIT_FILE}.tmp" && mv "${JUNIT_FILE}.tmp" "$JUNIT_FILE"
fi

# Generate Markdown report
REPORT_FILE="$TESTS_DIR/reports/front/$(date +%y-%m-%d-%H-%M)_test_report_front.md"
python3 "$SCRIPT_DIR/generate_test_report.py" "$JUNIT_FILE" "$REPORT_FILE" || true

# Print a compact table of results
python3 "$SCRIPT_DIR/print_junit_table.py" "$JUNIT_FILE" || true

exit $RC
