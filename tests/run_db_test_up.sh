#!/usr/bin/env bash
set -euo pipefail

# Script pour créer et lancer le conteneur de base de données de test
# 1) crée `tests/.env.db_test` si absent
# 2) build du service `test-db`
# 3) up du service
# 4) copie/adapte les deux jeux de migrations et lance `alembic upgrade head`

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.test.yml"

# Choix du moteur de conteneurs: passer 'docker' ou 'podman' en premier argument
# Exemple: `bash tests/run_db_test_up.sh podman`
ENGINE_ARG="${1:-${CONTAINER_ENGINE:-auto}}"
if [ "$ENGINE_ARG" = "auto" ]; then
	if command -v docker >/dev/null 2>&1; then
		ENGINE=docker
	elif command -v podman >/dev/null 2>&1; then
		ENGINE=podman
	else
		echo "❌ Aucun moteur de conteneur détecté (docker ou podman requis)"
		exit 1
	fi
else
	ENGINE="$ENGINE_ARG"
fi

# Déterminer la commande compose adaptée selon l'engine
COMPOSE_CMD=()
if [ "$ENGINE" = "docker" ]; then
	if docker compose version >/dev/null 2>&1; then
		COMPOSE_CMD=(docker compose)
	elif command -v docker-compose >/dev/null 2>&1; then
		COMPOSE_CMD=(docker-compose)
	else
		echo "❌ docker trouvé mais aucune commande 'docker compose' ou 'docker-compose' disponible"
		exit 1
	fi
elif [ "$ENGINE" = "podman" ]; then
	if podman compose version >/dev/null 2>&1; then
		COMPOSE_CMD=(podman compose)
	elif command -v podman-compose >/dev/null 2>&1; then
		COMPOSE_CMD=(podman-compose)
	else
		echo "❌ podman trouvé mais aucun 'podman compose' ou 'podman-compose' disponible"
		exit 1
	fi
else
	echo "❌ Engine invalide: $ENGINE. Choisir 'docker' ou 'podman'"
	exit 1
fi

echo "⚙️  Conteneur engine choisi: $ENGINE -> using: ${COMPOSE_CMD[*]}"

ENV_TEST_FILE="$PROJECT_ROOT/databases/main/.env.db_main"

echo "📁 Script dir: $SCRIPT_DIR"

if [ ! -f "$ENV_TEST_FILE" ]; then
	echo "❌ Fichier d'environnement unique introuvable: $ENV_TEST_FILE"
	exit 1
fi

# Source the single env file safely using process substitution (no extra files)
set -a
# shellcheck disable=SC2046,SC1090
source <(awk '
	/^[[:space:]]*#/ { next }
	/^[[:space:]]*$/ { next }
	/^[A-Za-z_][A-Za-z0-9_]*=/ {
		split($0, a, "=");
		key=a[1];
		val=substr($0, length(key)+2);
		gsub(/\\/, "\\\\", val);
		gsub(/"/, "\\\"", val);
		print "export " key "=\"" val "\"";
	}
' "$ENV_TEST_FILE")
set +a

echo "🔨 Building service test-db..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" build test-db

echo "⬆️  Starting service test-db..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d test-db

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

check_pg_ready() {
	# 1) pg_isready if available
	if command -v pg_isready >/dev/null 2>&1; then
		PGHOST="$HOST" PGPORT="$PORT" pg_isready -h "$HOST" -p "$PORT" -U "$USER" >/dev/null 2>&1 && return 0 || return 1
	fi

	# 2) psql if available
	if command -v psql >/dev/null 2>&1; then
		PGPASSWORD="$PW" psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" -c '\q' >/dev/null 2>&1 && return 0 || return 1
	fi

	# 3) TCP socket fallback (bash built-in /dev/tcp)
	if bash -c "</dev/tcp/$HOST/$PORT" >/dev/null 2>&1; then
		return 0
	fi

	return 1
}

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

# Répertoire temporaire de migrations de test
TMP_MIGR="$SCRIPT_DIR/test_migrations"
rm -rf "$TMP_MIGR"
mkdir -p "$TMP_MIGR/main/alembic/versions"
mkdir -p "$TMP_MIGR/users/alembic/versions"

# Copier les fichiers alembic & versions pour 'main'
cp -a "$PROJECT_ROOT/migrations/main/alembic/versions/"*.py "$TMP_MIGR/main/alembic/versions/"
cp "$PROJECT_ROOT/migrations/main/alembic.ini" "$TMP_MIGR/main/alembic.ini"
# Réécrire script_location pour pointer vers le répertoire temporaire
sed -i "s|^script_location\s*=.*|script_location = $TMP_MIGR/main/alembic|" "$TMP_MIGR/main/alembic.ini"

# Copier et adapter env.py pour utiliser le chemin du projet courant
# Méthode robuste : écrire un en-tête qui injecte TEST_PROJECT_ROOT, puis
# concaténer le env.py original en supprimant la ligne sys.path.insert
MAIN_ORIG_ENV="$PROJECT_ROOT/migrations/main/alembic/env.py"
MAIN_TMP_ENV="$TMP_MIGR/main/alembic/env.py"
printf "%s\n" "# Auto-generated env.py for tests" \
	"import os" \
	"import sys" \
	"from logging.config import fileConfig" \
	"from sqlalchemy import engine_from_config" \
	"from sqlalchemy import pool" \
	"from alembic import context" \
	"# project root injected by test script" \
	"project_root = os.getenv(\"TEST_PROJECT_ROOT\", \"$PROJECT_ROOT\")" \
	"sys.path.insert(0, project_root)" > "$MAIN_TMP_ENV"
# Append the rest of the original env.py but remove existing sys.path.insert lines
sed '/sys.path.insert(0/ d' "$MAIN_ORIG_ENV" >> "$MAIN_TMP_ENV"

# Copier les fichiers alembic & versions pour 'users'
cp -a "$PROJECT_ROOT/migrations/users/alembic/versions/"*.py "$TMP_MIGR/users/alembic/versions/"
cp "$PROJECT_ROOT/migrations/users/alembic.ini" "$TMP_MIGR/users/alembic.ini"
# Réécrire script_location pour pointer vers le répertoire temporaire
sed -i "s|^script_location\s*=.*|script_location = $TMP_MIGR/users/alembic|" "$TMP_MIGR/users/alembic.ini"
USERS_ORIG_ENV="$PROJECT_ROOT/migrations/users/alembic/env.py"
USERS_TMP_ENV="$TMP_MIGR/users/alembic/env.py"
printf "%s\n" "# Auto-generated env.py for tests" \
	"import os" \
	"import sys" \
	"from logging.config import fileConfig" \
	"from sqlalchemy import engine_from_config" \
	"from sqlalchemy import pool" \
	"from alembic import context" \
	"# project root injected by test script" \
	"project_root = os.getenv(\"TEST_PROJECT_ROOT\", \"$PROJECT_ROOT\")" \
	"sys.path.insert(0, project_root)" > "$USERS_TMP_ENV"
sed '/sys.path.insert(0/ d' "$USERS_ORIG_ENV" >> "$USERS_TMP_ENV"

echo "🔧 Variables d'environnement pour alembic (depuis $ENV_TEST_FILE)"
# Les variables ont déjà été exportées plus haut via process-substitution.
export TEST_PROJECT_ROOT="$PROJECT_ROOT"

# Avant de lancer Alembic, s'assurer que l'utilisateur de migration peut se connecter
MIGR_USER=${POSTGRES_USER_MIGR:-migr}
MIGR_PW=${POSTGRES_PASSWORD_MIGR:-}
MIGR_DB=${POSTGRES_DB_MAIN:-sauvetage_main}
echo "⏳ Vérification de connexion pour l'utilisateur de migration '$MIGR_USER' sur $HOST:$PORT..."
# Réutiliser la fonction check_pg_ready (qui fait pg_isready -> psql -> TCP)
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

run_alembic_with_retry() {
	local cfg="$1"
	local attempts=${2:-3}
	local delay=${3:-10}
	local i=1
	while :; do
		echo "🚀 Alembic: tentative $i/$attempts pour $cfg"
		set +e
		alembic -c "$cfg" upgrade head
		rc=$?
		set -e
		if [ $rc -eq 0 ]; then
			echo "✅ Alembic succeeded for $cfg"
			return 0
		fi
		if [ $i -ge $attempts ]; then
			echo "❌ Alembic failed for $cfg after $attempts attempts (rc=$rc)"
			return $rc
		fi
		echo "⚠️ Alembic failed (rc=$rc), attente $delay s avant nouvelle tentative..."
		sleep "$delay"
		i=$((i+1))
	done
}

echo "🚀 Lancement des migrations 'main'"
run_alembic_with_retry "$TMP_MIGR/main/alembic.ini" ${ALEMBIC_ATTEMPTS:-3} ${ALEMBIC_RETRY_DELAY:-10}

echo "🚀 Lancement des migrations 'users'"
run_alembic_with_retry "$TMP_MIGR/users/alembic.ini" ${ALEMBIC_ATTEMPTS:-3} ${ALEMBIC_RETRY_DELAY:-10}

echo "✅ Migrations appliquées avec succès"

