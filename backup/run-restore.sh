#!/bin/sh
set -eu

if [ -f /etc/backup/.env.save ]; then
  # shellcheck disable=SC1090
  . /etc/backup/.env.save
fi

SNAPSHOT_ID="${1:-latest}"
RESTORE_DOCS="${RESTORE_DOCS:-true}"
SNAP_ROOT="/backups/local/snapshots"
LATEST_LINK="/backups/local/meta/latest"

if [ "$SNAPSHOT_ID" = "latest" ]; then
  SNAP_DIR="$(readlink -f "$LATEST_LINK")"
else
  SNAP_DIR="$SNAP_ROOT/$SNAPSHOT_ID"
fi

if [ ! -d "$SNAP_DIR" ]; then
  echo "Snapshot introuvable: $SNAP_DIR" >&2
  exit 2
fi

echo "Restauration depuis $SNAP_DIR"

PGHOST="${POSTGRES_HOST:-db-main}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-postgres}"
PGPASSWORD="${POSTGRES_PASSWORD:-}"
export PGPASSWORD
POSTGRES_DB_MAIN="${POSTGRES_DB_MAIN:-sauvetage_main}"
POSTGRES_DB_USERS="${POSTGRES_DB_USERS:-sauvetage_users}"

pg_restore \
  --clean --if-exists --no-owner --no-privileges \
  --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
  --dbname="$POSTGRES_DB_MAIN" \
  "$SNAP_DIR/postgres/${POSTGRES_DB_MAIN}.dump"

pg_restore \
  --clean --if-exists --no-owner --no-privileges \
  --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
  --dbname="$POSTGRES_DB_USERS" \
  "$SNAP_DIR/postgres/${POSTGRES_DB_USERS}.dump"

MONGO_HOST="${MONGO_HOST:-db-logs}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB_LOGS="${MONGO_DB_LOGS:-sauvetage_logs}"
MONGO_INITDB_ROOT_USERNAME="${MONGO_INITDB_ROOT_USERNAME:-admin}"
MONGO_INITDB_ROOT_PASSWORD="${MONGO_INITDB_ROOT_PASSWORD:-}"

mongorestore \
  --drop \
  --host="$MONGO_HOST" \
  --port="$MONGO_PORT" \
  --username="$MONGO_INITDB_ROOT_USERNAME" \
  --password="$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase=admin \
  --nsInclude="$MONGO_DB_LOGS.*" \
  --archive="$SNAP_DIR/mongo/${MONGO_DB_LOGS}.archive.gz" \
  --gzip

if [ "$RESTORE_DOCS" = "true" ]; then
  rsync -a --delete "$SNAP_DIR/documents/" /data/documents/
fi

echo "Restauration terminée"
