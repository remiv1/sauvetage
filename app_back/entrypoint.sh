#!/bin/sh
set -e

# Log de démarrage
echo "[ENTRYPOINT] Demarrage du backend Sauvetage"

# Construction dynamique des URLs a partir des variables BD
if [ -z "$DATABASE_URL" ]; then
    if [ -z "$POSTGRES_USER_APP" ] || [ -z "$POSTGRES_PASSWORD_APP" ] || [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_PORT" ] || [ -z "$POSTGRES_DB_MAIN" ]; then
        echo "[ENTRYPOINT] ERREUR: Variables PostgreSQL incompletes"
        exit 1
    fi
    export DATABASE_URL="postgresql://${POSTGRES_USER_APP}:${POSTGRES_PASSWORD_APP}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB_MAIN}"
    echo "[ENTRYPOINT] DATABASE_URL construit depuis les variables BD"
fi

if [ -z "$MONGODB_URL" ]; then
    if [ -z "$MONGO_USER_APP" ] || [ -z "$MONGO_PASSWORD_APP" ] || [ -z "$MONGO_HOST" ] || [ -z "$MONGO_PORT" ] || [ -z "$MONGO_DB_LOGS" ]; then
        echo "[ENTRYPOINT] ERREUR: Variables MongoDB incompletes"
        exit 1
    fi
    export MONGODB_URL="mongodb://${MONGO_USER_APP}:${MONGO_PASSWORD_APP}@${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB_LOGS}"
    echo "[ENTRYPOINT] MONGODB_URL construit depuis les variables BD"
fi

# Affichage de la configuration
echo "[ENTRYPOINT] Configuration:"
echo "[ENTRYPOINT]   DATABASE_URL: [REDACTED]"
echo "[ENTRYPOINT]   MONGODB_URL: [REDACTED]"
echo "[ENTRYPOINT]   LOG_LEVEL=${LOG_LEVEL:-info}"
echo "[ENTRYPOINT]   DEBUG=${DEBUG:-false}"

# Demarrage de Gunicorn avec Uvicorn
echo "[ENTRYPOINT] Demarrage de Gunicorn (4 workers)"

exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    main:app
