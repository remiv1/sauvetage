#!/bin/sh
set -eu

# Script interactif pour choisir un snapshot local et lancer la restauration
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

SNAP_ROOT="backups/local/snapshots"
if [ ! -d "$SNAP_ROOT" ]; then
  echo "Aucun snapshot local trouvé dans $SNAP_ROOT" >&2
  exit 2
fi

# Build list
SNAPS=$(ls -1dt "$SNAP_ROOT"/* 2>/dev/null || true)
if [ -z "$SNAPS" ]; then
  echo "Aucun snapshot disponible" >&2
  exit 2
fi

# Present numbered menu
i=0
for s in $SNAPS; do
  i=$((i+1))
  name=$(basename "$s")
  echo "$i) $name"
done

echo "l) latest"

while true; do
  printf "Sélectionnez un snapshot (numéro ou 'l' pour latest, 'q' pour quitter): "
  read choice || exit 1
  case "$choice" in
    q|Q) echo "Annulé"; exit 0;;
    l|L)
      SNAP_ID=latest
      break;;
    '' ) ;;
    *)
      if echo "$choice" | grep -qE '^[0-9]+$'; then
        idx=$(expr "$choice" : '\([0-9]\+\)')
        sel=$(echo "$SNAPS" | sed -n "${idx}p")
        if [ -n "$sel" ]; then
          SNAP_ID=$(basename "$sel")
          break
        fi
      fi
      echo "Sélection invalide";;
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

SERVICE="backup"

printf "Confirmer restauration du snapshot '%s' ? [y/N]: " "$SNAP_ID"
read ans || ans=n
case "$ans" in
  y|Y) ;;
  *) echo "Annulé"; exit 0;;
esac

# Ensure service is running; use exec in existing container (no 'run' fallback)
set +e
# Try exec as root to ensure mounted log dir is writable
OUTPUT=$($COMPOSE exec -T --user 0 $SERVICE /usr/local/bin/run-restore.sh "$SNAP_ID" 2>&1) || true
RC=$?
if [ "$RC" -ne 0 ]; then
  OUTPUT=$($COMPOSE exec -T $SERVICE /usr/local/bin/run-restore.sh "$SNAP_ID" 2>&1) || true
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

echo "Restauration demandée pour snapshot: $SNAP_ID"
