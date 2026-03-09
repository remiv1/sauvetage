#!/usr/bin/env bash
set -euo pipefail

# Script d'initialisation d'une base de test + exécution des tests unitaires.
# Facteur commun extrait dans tests/scripts/functions.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Charger les fonctions partagées (si disponibles)
if [ -f "$SCRIPT_DIR/scripts/functions.sh" ]; then
	# shellcheck source=/dev/null
	source "$SCRIPT_DIR/scripts/functions.sh"
fi

PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Cherche un docker-compose.test.yml sur plusieurs emplacements possibles
COMPOSE_FILE="$(find_compose_file "$SCRIPT_DIR/docker-compose.test.yml" "$PROJECT_ROOT/tests/docker-compose.test.yml" "$PROJECT_ROOT/docker-compose.test.yml" 2>/dev/null || true)"

# Choix du moteur de conteneurs: passer 'docker' ou 'podman' en premier argument
# Exemple: `bash tests/run_db_test_up.sh podman`
ENGINE_ARG="${1:-${CONTAINER_ENGINE:-auto}}"
detect_compose_cmd "$ENGINE_ARG" || {
	echo "❌ Aucun moteur de conteneur détecté ou compose introuvable (docker|podman requis)"
	exit 1
}

echo "⚙️  Conteneur engine choisi: ${COMPOSE_ENGINE} -> using: ${COMPOSE_CMD[*]}"

ENV_TEST_FILE="$PROJECT_ROOT/databases/main/.env.db_main"

echo "📁 Script dir: $SCRIPT_DIR"

if [ ! -f "$ENV_TEST_FILE" ]; then
	echo "❌ Fichier d'environnement introuvable: $ENV_TEST_FILE"
	exit 1
fi

# Charger proprement les variables d'environnement (helper)
safe_source_env_file "$ENV_TEST_FILE" || {
	echo "❌ Impossible de charger les variables depuis $ENV_TEST_FILE"
	exit 1
}

echo "🔨 Building + starting service test-db..."
compose_build_and_up test-db "$COMPOSE_FILE"

HOST=${POSTGRES_HOST:-localhost}
PORT=${POSTGRES_PORT:-5433}
DB=${POSTGRES_DB_MAIN:-sauvetage_test}
USER=${POSTGRES_USER_APP:-app}
PW=${POSTGRES_PASSWORD_APP:-}

# Lorsque le script est exécuté depuis l'hôte, utiliser l'adresse locale
# et le port mappé pour atteindre le conteneur (évite d'essayer 'db-main:5432')
# Permettre de désactiver ce comportement en définissant NO_HOST_OVERRIDE=1
if [ "${NO_HOST_OVERRIDE:-0}" != "1" ] && [ "$HOST" != "localhost" ] ; then
	echo "🔁 Override POSTGRES host/port for local access: 127.0.0.1:5433"
	# Prefer IPv4 explicit address to avoid connecting to ::1 which may not be forwarded
	export POSTGRES_HOST=127.0.0.1
	export POSTGRES_PORT=${TEST_DB_LOCAL_PORT:-5433}
	HOST=$POSTGRES_HOST
	PORT=$POSTGRES_PORT
fi

echo "⏳ Waiting for database to be ready on $HOST:$PORT..."
MAX_TRIES=60
TRY=0

until check_pg_ready || [ $TRY -ge $MAX_TRIES ]; do
	sleep 1
	TRY=$((TRY+1))
	echo "  waiting... ($TRY/$MAX_TRIES)"
done

if [ $TRY -ge $MAX_TRIES ]; then
	echo "❌ La base de données n'est pas prête après $MAX_TRIES secondes"
	exit 1
fi

echo "✅ Base de données prête, préparation des migrations de test"

# Préparer les migrations de tests dans un répertoire temporaire
TMP_MIGR="$SCRIPT_DIR/test_migrations"
prepare_test_migrations "$PROJECT_ROOT" "$TMP_MIGR"

echo "🔧 Variables d'environnement pour alembic (depuis $ENV_TEST_FILE)"
export TEST_PROJECT_ROOT="$PROJECT_ROOT"

# Avant de lancer Alembic, s'assurer que l'utilisateur de migration peut se connecter
MIGR_USER=${POSTGRES_USER_MIGR:-migr}
MIGR_PW=${POSTGRES_PASSWORD_MIGR:-}
MIGR_DB=${POSTGRES_DB_MAIN:-sauvetage_main}
echo "⏳ Vérification de connexion pour l'utilisateur de migration '$MIGR_USER' sur $HOST:$PORT..."

# Vérification de connexion pour l'utilisateur de migration
# (on ré-utilise globalement les variables `USER`/`PW`/`DB` pour check_pg_ready)
OLD_USER="$USER"; OLD_PW="$PW"; OLD_DB="$DB"
USER="$MIGR_USER"; PW="$MIGR_PW"; DB="$MIGR_DB"
MIGR_TRIES=0
MIGR_MAX=30
until check_pg_ready || [ $MIGR_TRIES -ge $MIGR_MAX ]; do
	sleep 1
	MIGR_TRIES=$((MIGR_TRIES+1))
	echo "  waiting migr... ($MIGR_TRIES/$MIGR_MAX)"
done

# Restaurer variables originales
USER="$OLD_USER"; PW="$OLD_PW"; DB="$OLD_DB"
if [ $MIGR_TRIES -ge $MIGR_MAX ]; then
	echo "❌ Impossible de se connecter en tant que $MIGR_USER après $MIGR_MAX secondes"
	echo "Afficher les logs du conteneur pour diagnostic: ${COMPOSE_CMD[*]} -f $COMPOSE_FILE logs test-db"
	exit 1
fi

echo "🚀 Lancement des migrations 'main'"
run_alembic_with_retry "$TMP_MIGR/main/alembic.ini" ${ALEMBIC_ATTEMPTS:-3} ${ALEMBIC_RETRY_DELAY:-10}

echo "🚀 Lancement des migrations 'users'"
run_alembic_with_retry "$TMP_MIGR/users/alembic.ini" ${ALEMBIC_ATTEMPTS:-3} ${ALEMBIC_RETRY_DELAY:-10}

echo "✅ Migrations appliquées avec succès"

echo "🚀 Lancement des tests (db_objects/) via tests/scripts/run_tests_db_objects.sh"
"$SCRIPT_DIR/scripts/run_tests_db_objects.sh" "$SCRIPT_DIR"
