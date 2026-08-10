#!/bin/sh
set -eu

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

DRY_RUN=0
YES=0
LOCAL_ONLY=0
SERVICE="backup"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift;;
    --local-only) LOCAL_ONLY=1; shift;;
    --service) SERVICE="$2"; shift 2;;
    -y|--yes) YES=1; shift;;
    -h|--help)
      cat <<EOF
Usage: $0 [--dry-run] [--local-only] [--service backup] [-y]
EOF
      exit 0;;
    *) echo "Argument inconnu: $1" >&2; exit 2;;
  esac
done

if command -v podman >/dev/null 2>&1; then
  COMPOSE="podman compose"
elif command -v docker >/dev/null 2>&1; then
  COMPOSE="docker compose"
else
  echo "podman/docker introuvable" >&2
  exit 3
fi

CMD="$COMPOSE exec -T $SERVICE /usr/local/bin/run-backup.sh"
if [ "$LOCAL_ONLY" -eq 1 ]; then
  CMD="$COMPOSE exec -T $SERVICE sh -c 'REMOTE_ENABLED=false /usr/local/bin/run-backup.sh'"
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY RUN: $CMD"
  exit 0
fi

if [ "$YES" -ne 1 ]; then
  printf "Confirmer la sauvegarde ponctuelle ? [y/N]: "
  read ans || ans=n
  case "$ans" in
    y|Y) ;;
    *) echo "Annulé"; exit 0;;
  esac
fi

sh -c "$CMD"

echo "Dernier snapshot:"
ls -1dt backups/local/snapshots/* 2>/dev/null | head -n1 || true
