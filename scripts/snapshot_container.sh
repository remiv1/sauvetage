#!/bin/sh
set -eu

# Lance la sauvegarde dans le service 'backup' via docker/podman compose.
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

if command -v podman >/dev/null 2>&1; then
  COMPOSE="podman compose"
elif command -v docker >/dev/null 2>&1; then
  COMPOSE="docker compose"
else
  echo "podman/docker introuvable" >&2
  exit 3
fi

SERVICE="backup"
DRY_RUN=0
YES=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift;;
    -y|--yes) YES=1; shift;;
    --service) SERVICE="$2"; shift 2;;
    -h|--help)
      cat <<EOF
Usage: $0 [--dry-run] [--service backup] [-y]

Lance le script de backup dans le service compose 'backup'.
EOF
      exit 0;;
    *) echo "Argument inconnu: $1" >&2; exit 2;;
  esac
done

CMD_EXEC="$COMPOSE exec -T $SERVICE /usr/local/bin/run-backup.sh"
CMD_RUN="$COMPOSE run --rm $SERVICE /usr/local/bin/run-backup.sh"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY RUN: essayer exec, puis run si nécessaire"
  echo "$CMD_EXEC"
  echo "$CMD_RUN"
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

# Exécute la commande dans le conteneur existant. Si le service n'est pas démarré,
# la commande retournera une erreur explicite ; on affiche un message utile.
set +e
# Try exec as root to ensure mounted log dir is writable
OUTPUT=$($COMPOSE exec -T --user 0 $SERVICE /usr/local/bin/run-backup.sh 2>&1) || true
RC=$?
if [ "$RC" -ne 0 ]; then
  # Fallback: try without explicit user (may fail due to permissions)
  OUTPUT=$($COMPOSE exec -T $SERVICE /usr/local/bin/run-backup.sh 2>&1) || true
  RC=$?
fi
set -e
if [ "$RC" -ne 0 ]; then
  echo "Erreur: 'exec' a échoué (code $RC). Vérifiez que le service '$SERVICE' est démarré :" >&2
  echo "  $COMPOSE up -d $SERVICE" >&2
  echo "Sortie du compose :" >&2
  echo "$OUTPUT" >&2
  echo "Consultez aussi backup_logs/errors.log et backup_logs/backup.log pour plus de détails." >&2
  exit "$RC"
fi

echo "Dernier snapshot local:"
ls -1dt backups/local/snapshots/* 2>/dev/null | head -n1 || true
