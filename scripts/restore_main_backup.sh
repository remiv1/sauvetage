#!/bin/sh
set -eu

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

SNAPSHOT_ID="latest"
RESTORE_DOCS="true"
YES=0
DRY_RUN=0
SERVICE="backup"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --snapshot) SNAPSHOT_ID="$2"; shift 2;;
    --no-docs) RESTORE_DOCS="false"; shift;;
    --service) SERVICE="$2"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    -y|--yes) YES=1; shift;;
    -h|--help)
      cat <<EOF
Usage: $0 [--snapshot ID|latest] [--no-docs] [--dry-run] [--service backup] [-y]
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

CMD="$COMPOSE exec -T $SERVICE sh -c 'RESTORE_DOCS=$RESTORE_DOCS /usr/local/bin/run-restore.sh $SNAPSHOT_ID'"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY RUN: $CMD"
  exit 0
fi

if [ "$YES" -ne 1 ]; then
  printf "Confirmer la restauration (destructive) ? [y/N]: "
  read ans || ans=n
  case "$ans" in
    y|Y) ;;
    *) echo "Annulé"; exit 0;;
  esac
fi

sh -c "$CMD"
