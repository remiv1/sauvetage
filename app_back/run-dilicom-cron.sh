#!/bin/bash
set -euo pipefail

ACTION="${1:-}"
BASE_URL="${DILICOM_API_URL:-http://localhost:8000/api/v1}"

if [[ -z "$ACTION" ]]; then
  echo "Usage: $0 <post|fetch>" >&2
  exit 1
fi

case "$ACTION" in
  post)
    echo "[DILICOM-CRON] Envoi des référentiels Dilicom" >&2
    curl --fail --silent --show-error -X POST "$BASE_URL/dilicom/background/post-referencial"
    ;;
  fetch)
    ARCHIVES="${DILICOM_FETCH_ARCHIVES:-false}"
    echo "[DILICOM-CRON] Récupération des retours Dilicom (archives=$ARCHIVES)" >&2
    curl --fail --silent --show-error -X POST "$BASE_URL/dilicom/background/fetch-returns?archives=$ARCHIVES"
    ;;
  *)
    echo "[DILICOM-CRON] Action inconnue: $ACTION" >&2
    exit 2
    ;;
esac
