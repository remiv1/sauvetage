#!/usr/bin/env bash
set -euo pipefail

# Lance pytest sur le dossier tests/db_objects/, produit un JUnit XML,
# puis appelle le petit script Python pour afficher un tableau lisible.

SCRIPT_DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"
JUNIT_FILE="$SCRIPT_DIR/test_results.xml"

echo "🧪 Running pytest for db_objects/ (junit -> $JUNIT_FILE)"
# Run pytest and capture exit code
pytest -v --tb=short --disable-warnings --log-cli-level=INFO "$SCRIPT_DIR/db_objects/" --junitxml="$JUNIT_FILE"
RC=$?

# Print a compact table of results
python3 "$SCRIPT_DIR/scripts/print_junit_table.py" "$JUNIT_FILE" || true

exit $RC
