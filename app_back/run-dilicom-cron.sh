#!/bin/bash
set -euo pipefail

ACTION="${1:-}"
BASE_URL="${DILICOM_API_URL:-http://localhost:8000/api/v1}"
LOG_FILE="${DILICOM_CRON_LOG_FILE:-/var/log/dilicom/dilicom-cron.log}"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
  printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$LOG_FILE" >&2
}

run_request() {
  local url="$1"
  local method="${2:-GET}"
  local response_file
  response_file="$(mktemp)"

  log "[DILICOM-CRON] Début: méthode=$method url=$url"

  local curl_output
  local curl_status
  set +e
  curl_output="$(curl -sS -L --max-time 180 -D - -o "$response_file" -w '\nHTTP_STATUS:%{http_code}' -X "$method" "$url" 2>&1)"
  curl_status=$?
  set -e

  log "[DILICOM-CRON] curl exit code: $curl_status"
  if [[ -n "$curl_output" ]]; then
    printf '%s\n' "$curl_output" | tee -a "$LOG_FILE" >&2
  fi

  if [[ -s "$response_file" ]]; then
    log "[DILICOM-CRON] Réponse HTTP body: $(tr '\n' ' ' < "$response_file" | head -c 2000)"
  fi

  local http_status
  http_status="$(printf '%s\n' "$curl_output" | sed -n 's/.*HTTP_STATUS:\([0-9][0-9][0-9]\).*/\1/p' | tail -n 1)"

  rm -f "$response_file"

  if [[ "$curl_status" -ne 0 ]]; then
    log "[DILICOM-CRON] ERREUR: curl a échoué sur $url"
    return 1
  fi

  if [[ -z "$http_status" ]]; then
    log "[DILICOM-CRON] ERREUR: code HTTP non détecté sur $url"
    return 1
  fi

  if [[ "$http_status" -lt 200 || "$http_status" -ge 300 ]]; then
    log "[DILICOM-CRON] ERREUR HTTP: code=$http_status sur $url"
    return 1
  fi

  log "[DILICOM-CRON] Succès: code=$http_status sur $url"
  return 0
}

if [[ -z "$ACTION" ]]; then
  log "[DILICOM-CRON] Usage: $0 <post|fetch>"
  exit 1
fi

case "$ACTION" in
  post)
    url="$BASE_URL/dilicom/background/post-referencial"
    log "[DILICOM-CRON] Envoi des référentiels Dilicom"
    run_request "$url" "POST"
    ;;
  fetch)
    ARCHIVES="${DILICOM_FETCH_ARCHIVES:-false}"
    url="$BASE_URL/dilicom/background/fetch-returns?archives=$ARCHIVES"
    log "[DILICOM-CRON] Récupération des retours Dilicom (archives=$ARCHIVES)"
    run_request "$url" "POST"
    ;;
  *)
    log "[DILICOM-CRON] Action inconnue: $ACTION"
    exit 2
    ;;
esac
