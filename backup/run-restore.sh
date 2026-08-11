#!/bin/sh
set -eu

[ -f /etc/backup/env.sh ] && . /etc/backup/env.sh

LOG_FILE="/var/log/backup/restore.log"
log() { printf '[%s] %s\n' "$(date -Is)" "$*" >> "$LOG_FILE"; }

SNAPSHOT_ID="${1:-latest}"
RESTORE_DOCS="${RESTORE_DOCS:-true}"
SNAP_ROOT="/backups/local/snapshots"
LATEST_LINK="/backups/local/meta/latest"
WORK_DIR="$(mktemp -d)"

on_exit() {
  code=$?
  rm -rf "$WORK_DIR"
  if [ "$code" -ne 0 ]; then
    log "ÉCHEC restauration $SNAPSHOT_ID (code $code)"
  fi
}
trap on_exit EXIT

log "Démarrage restauration $SNAPSHOT_ID"

BACKUP_ENCRYPTION_PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE:-}"
if [ -z "$BACKUP_ENCRYPTION_PASSPHRASE" ]; then
  log "BACKUP_ENCRYPTION_PASSPHRASE manquant"
  exit 2
fi

if [ "$SNAPSHOT_ID" = "latest" ]; then
  SNAP_DIR="$(readlink -f "$LATEST_LINK")"
else
  SNAP_DIR="$SNAP_ROOT/$SNAPSHOT_ID"
fi

if [ ! -d "$SNAP_DIR" ]; then
  log "Snapshot introuvable: $SNAP_DIR"
  exit 2
fi

DB_ARCHIVE="$(find "$SNAP_DIR/db" -maxdepth 1 -name '*.tar.enc' | head -n1)"
if [ -z "$DB_ARCHIVE" ]; then
  log "Archive DB introuvable dans $SNAP_DIR/db"
  exit 2
fi

log "Restauration depuis $SNAP_DIR"

log "Déchiffrement de l'archive DB..."
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -pass env:BACKUP_ENCRYPTION_PASSPHRASE \
  -in "$DB_ARCHIVE" | tar -C "$WORK_DIR" -xf -
log "Déchiffrement de l'archive DB terminé"

PGHOST="${POSTGRES_HOST:-db-main}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-postgres}"
PGPASSWORD="${POSTGRES_PASSWORD:-}"
export PGPASSWORD
POSTGRES_DB_MAIN="${POSTGRES_DB_MAIN:-sauvetage_main}"
POSTGRES_DB_USERS="${POSTGRES_DB_USERS:-sauvetage_users}"

log "pg_restore $POSTGRES_DB_MAIN commencé..."
pg_restore \
  --clean --if-exists --no-owner --no-privileges \
  --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
  --dbname="$POSTGRES_DB_MAIN" \
  "$WORK_DIR/${POSTGRES_DB_MAIN}.dump" >>"$LOG_FILE" 2>&1
log "pg_restore $POSTGRES_DB_MAIN terminé"

log "pg_restore $POSTGRES_DB_USERS commencé..."
pg_restore \
  --clean --if-exists --no-owner --no-privileges \
  --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
  --dbname="$POSTGRES_DB_USERS" \
  "$WORK_DIR/${POSTGRES_DB_USERS}.dump" >>"$LOG_FILE" 2>&1
log "pg_restore $POSTGRES_DB_USERS terminé"

MONGO_HOST="${MONGO_HOST:-db-logs}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB_LOGS="${MONGO_DB_LOGS:-sauvetage_logs}"
MONGO_INITDB_ROOT_USERNAME="${MONGO_INITDB_ROOT_USERNAME:-admin}"
MONGO_INITDB_ROOT_PASSWORD="${MONGO_INITDB_ROOT_PASSWORD:-}"

log "mongorestore $MONGO_DB_LOGS commencé..."
mongorestore \
  --drop \
  --host="$MONGO_HOST" \
  --port="$MONGO_PORT" \
  --username="$MONGO_INITDB_ROOT_USERNAME" \
  --password="$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase=admin \
  --nsInclude="$MONGO_DB_LOGS.*" \
  --archive="$WORK_DIR/${MONGO_DB_LOGS}.archive.gz" \
  --gzip >>"$LOG_FILE" 2>&1
log "mongorestore $MONGO_DB_LOGS terminé"

if [ "$RESTORE_DOCS" = "true" ]; then
  log "Restauration des documents depuis $SNAP_DIR/documents..."
  rsync -a --delete "$SNAP_DIR/documents/" /data/documents/ >>"$LOG_FILE" 2>&1
  log "Restauration des documents terminée"
fi

log "Restauration terminée: $SNAPSHOT_ID"
