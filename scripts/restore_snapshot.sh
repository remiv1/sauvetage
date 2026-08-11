#!/bin/bash
set -eu

# Script interactif pour choisir un snapshot local et lancer la restauration
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

SNAP_ROOT="backups/local/snapshots"
if [ ! -d "$SNAP_ROOT" ]; then
  echo "Aucun snapshot local trouvé dans $SNAP_ROOT" >&2
  exit 2
fi

SNAPS=$(ls -1dt "$SNAP_ROOT"/* 2>/dev/null || true)
if [ -z "$SNAPS" ]; then
  echo "Aucun snapshot disponible" >&2
  exit 2
fi

echo "Snapshots disponibles (du plus récent au plus ancien) :"
SNAP_ID=""
select choice in $(printf '%s\n' "$SNAPS" | xargs -n1 basename) latest quitter; do
  case "$choice" in
    quitter) echo "Annulé"; exit 0;;
    "") echo "Sélection invalide"; continue;;
    *) SNAP_ID="$choice"; break;;
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

# Exécute la restauration dans le conteneur déjà démarré. Échoue clairement si le service n'est pas up.
if ! $COMPOSE exec -T "$SERVICE" /usr/local/bin/run-restore.sh "$SNAP_ID"; then
  echo "Erreur: échec de l'exécution dans le service '$SERVICE'." >&2
  echo "Vérifiez qu'il est démarré : $COMPOSE up -d $SERVICE" >&2
  echo "Consultez backup_logs/restore.log pour le détail." >&2
  exit 1
fi

echo "Restauration terminée pour snapshot: $SNAP_ID"
