#!/bin/sh

set -e

echo "[ENTRYPOINT] Démarrage du frontend Sauvetage"

# Construction dynamique des URLs à partir des variables BD
if [ -z "$DATABASE_URL" ]; then
    if [ -z "$POSTGRES_USER_APP" ] || [ -z "$POSTGRES_PASSWORD_APP" ] || [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_PORT" ] || [ -z "$POSTGRES_DB_MAIN" ]; then
        echo "[ENTRYPOINT] ERREUR: Variables PostgreSQL incomplètes"
        exit 1
    fi
    export DATABASE_URL="postgresql://${POSTGRES_USER_APP}:${POSTGRES_PASSWORD_APP}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB_MAIN}"
    echo "[ENTRYPOINT] DATABASE_URL construit depuis les variables BD"
fi

if [ -z "$SECURE_DATABASE_URL" ]; then
    if [ -z "$POSTGRES_USER_SECURE" ] || [ -z "$POSTGRES_PASSWORD_SECURE" ] || [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_PORT" ] || [ -z "$POSTGRES_DB_USERS" ]; then
        echo "[ENTRYPOINT] ERREUR: Variables PostgreSQL incomplètes pour SECURE_DATABASE_URL"
        exit 1
    fi
    # Encodage du mot de passe pour l'URL
    POSTGRES_PASSWORD_SECURE_ENC=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$POSTGRES_PASSWORD_SECURE'''))")
    export SECURE_DATABASE_URL="postgresql://${POSTGRES_USER_SECURE}:${POSTGRES_PASSWORD_SECURE_ENC}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB_USERS}"
    echo "[ENTRYPOINT] SECURE_DATABASE_URL construit depuis les variables BD (encodé)"
fi

if [ -z "$MONGODB_URL" ]; then
    if [ -z "$MONGO_USER_APP" ] || [ -z "$MONGO_PASSWORD_APP" ] || [ -z "$MONGO_HOST" ] || [ -z "$MONGO_PORT" ] || [ -z "$MONGO_DB_LOGS" ]; then
        echo "[ENTRYPOINT] ERREUR: Variables MongoDB incomplètes"
        exit 1
    fi
    # Encodage du mot de passe pour l'URL
    MONGO_PASSWORD_APP_ENC=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$MONGO_PASSWORD_APP'''))")
    export MONGODB_URL="mongodb://${MONGO_USER_APP}:${MONGO_PASSWORD_APP_ENC}@${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB_LOGS}?authSource=${MONGO_DB_LOGS}"
    echo "[ENTRYPOINT] MONGODB_URL construit depuis les variables BD (encodé, authSource ajouté)"
fi

if [ -z "$FLASK_SECRET_KEY" ]; then
    echo "[ENTRYPOINT] AVERTISSEMENT: FLASK_SECRET_KEY non défini, utilisation de la clé de développement"
    export FLASK_SECRET_KEY="dev-secret-key-change-in-production"
fi

# Affichage de la configuration
echo "[ENTRYPOINT] Configuration:"
echo "[ENTRYPOINT]   DATABASE_URL=$DATABASE_URL"
echo "[ENTRYPOINT]   SECURE_DATABASE_URL=$SECURE_DATABASE_URL"
echo "[ENTRYPOINT]   MONGODB_URL=$MONGODB_URL"
echo "[ENTRYPOINT]   LOG_LEVEL=${LOG_LEVEL:-info}"
echo "[ENTRYPOINT]   DEBUG=${DEBUG:-false}"

# Démarrage de Gunicorn avec Werkzeug
echo "[ENTRYPOINT] Démarrage de Gunicorn (4 workers)"

exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --worker-class sync \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    app_front.main:app
