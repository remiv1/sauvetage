#!/usr/bin/env bash
set -euo pipefail

# Lance pytest sur le dossier tests/e2e/, produit un JUnit XML,
# puis génère les rapports lisibles associés.

TESTS_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
SCRIPT_DIR="${TESTS_DIR}/scripts"
STAMP="$(date +%y-%m-%d-%H-%M)"
JUNIT_FILE="$TESTS_DIR/reports/junit/e2e/${STAMP}_test_results.xml"
REPORT_FILE="$TESTS_DIR/reports/e2e/${STAMP}_test_report_e2e.md"
COVERAGE_DIR="$TESTS_DIR/reports/coverage"
mkdir -p "$(dirname "$JUNIT_FILE")" "$TESTS_DIR/reports/e2e" "$COVERAGE_DIR"

echo "🧪 Running pytest for e2e/ (junit -> $JUNIT_FILE)"
set +e
COVERAGE_FILE="$COVERAGE_DIR/.coverage" coverage run --parallel-mode -m pytest -v --tb=short --disable-warnings --log-cli-level=INFO "$TESTS_DIR/e2e/" --junitxml="$JUNIT_FILE"
RC=$?
set -e

if command -v xmllint &> /dev/null; then
	xmllint --format "$JUNIT_FILE" > "${JUNIT_FILE}.tmp" && mv "${JUNIT_FILE}.tmp" "$JUNIT_FILE"
fi

python3 "$SCRIPT_DIR/generate_test_report.py" "$JUNIT_FILE" "$REPORT_FILE" || true
python3 "$SCRIPT_DIR/print_junit_table.py" "$JUNIT_FILE" || true

exit $RC