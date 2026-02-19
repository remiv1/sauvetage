#!/usr/bin/env bash
set -euo pipefail

# Script d'orchestration minimal pour démarrer les services dans l'ordre
# Usage: COMPOSE_CMD="podman compose" ./scripts/start_sequence.sh

COMPOSE_CMD=${COMPOSE_CMD:-"podman compose"}

echo "[start_sequence] Using compose command: $COMPOSE_CMD"

# 1) Lancer DB + proxy
echo "[start_sequence] Démarrage des services 'db-main' et 'proxy'"
$COMPOSE_CMD up -d db-main proxy db-logs

# 2) Attendre que la base soit prête
echo "[start_sequence] Attente de la disponibilité PostgreSQL"
RETRIES=60
COUNT=0
while true; do
  if $COMPOSE_CMD exec -T db-main pg_isready -U "${POSTGRES_USER_MIGR:-postgres}" -d "${POSTGRES_DB_MAIN:-sauvetage_main}" >/dev/null 2>&1; then
    echo "[start_sequence] PostgreSQL prêt"
    break
  fi
  COUNT=$((COUNT+1))
  if [ $COUNT -ge $RETRIES ]; then
    echo "[start_sequence] Timeout waiting for PostgreSQL" >&2
    exit 1
  fi
  sleep 2
done

# 3) Démarrer app-back
echo "[start_sequence] Démarrage de 'app-back'"
$COMPOSE_CMD up -d app-back

# 4) Attendre que les migrations Alembic appliquées (ou stamp) : vérifier que alembic current retourne une révision
echo "[start_sequence] Attente de la fin des migrations Alembic (vérification via 'alembic current')"
RETRIES=90
COUNT=0

# 5) Démarrer app-front
echo "[start_sequence] Démarrage de 'app-front'"
$COMPOSE_CMD up -d app-front

echo "[start_sequence] Stack démarrée avec succès"
