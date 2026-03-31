#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Charger helpers partagés
if [ -f "$SCRIPT_DIR/scripts/functions.sh" ]; then
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/scripts/functions.sh"
fi

echo "Détection du runtime (podman/docker)..."
detect_compose_cmd || true

if [ "${#COMPOSE_CMD[@]}" -gt 0 ]; then
  echo "Compose command: ${COMPOSE_CMD[*]}"
else
  echo "Compose command: none"
fi

COMPOSE_FILE="$(find_compose_file "$SCRIPT_DIR/docker-compose.test.yml" "$REPO_ROOT/tests/docker-compose.test.yml" "$REPO_ROOT/docker-compose.test.yml" 2>/dev/null || true)"

if [ "${#COMPOSE_CMD[@]}" -gt 0 ] && [ -n "$COMPOSE_FILE" ]; then
  echo "Arrêt des conteneurs de test via: $COMPOSE_FILE"
  set +e
  compose_down_with_file "$COMPOSE_FILE"
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    echo "  -> commande compose retournée $rc (ignorée)"
  fi
else
  echo "Aucun runtime compose ou fichier trouvé – conteneurs non arrêtés"
fi

echo
echo "Suppression des dossiers __pycache__..."
find "$REPO_ROOT" -type d -name "__pycache__" -print0 | xargs -0 -r rm -rf || true

echo
echo "Suppression des dossiers .pytest_cache (tous) ..."
find "$REPO_ROOT" -type d -name ".pytest_cache" -print0 | xargs -0 -r rm -rf || true

echo
echo "Suppression des dossiers test_migrations (tous) ..."
find "$REPO_ROOT" -type d -name "test_migrations" -print0 | xargs -0 -r rm -rf || true

echo
echo "Suppression du fichier test_results.xml si présent (dans tests)..."
if [ -f "$SCRIPT_DIR/test_results.xml" ]; then
  rm -f "$SCRIPT_DIR/test_results.xml"
  echo "  -> test_results.xml supprimé"
else
  echo "  -> test_results.xml absent"
fi

echo
echo "Nettoyage terminé."
