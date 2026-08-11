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
YES=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    -y|--yes) YES=1; shift;;
    -h|--help)
      cat <<EOF
Usage: $0 [-y]

Lance le script de backup dans le conteneur déjà démarré du service compose 'backup'.
EOF
      exit 0;;
    *) echo "Argument inconnu: $1" >&2; exit 2;;
  esac
done

if [ "$YES" -ne 1 ]; then
  printf "Confirmer la sauvegarde ponctuelle ? [y/N]: "
  read ans || ans=n
  case "$ans" in
    y|Y) ;;
    *) echo "Annulé"; exit 0;;
  esac
fi

# Exécute le script dans le conteneur déjà démarré. Échoue clairement si le service n'est pas up.
if ! $COMPOSE exec -T "$SERVICE" /usr/local/bin/run-backup.sh; then
  echo "Erreur: échec de l'exécution dans le service '$SERVICE'." >&2
  echo "Vérifiez qu'il est démarré : $COMPOSE up -d $SERVICE" >&2
  echo "Consultez backup_logs/backup.log pour le détail." >&2
  exit 1
fi

echo "Dernier snapshot local:"
ls -1dt backups/local/snapshots/* 2>/dev/null | head -n1 || true
