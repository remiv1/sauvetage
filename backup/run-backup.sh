#!/bin/sh
set -eu

# Environnement capturé par entrypoint.sh (nécessaire pour l'exécution via cron).
[ -f /etc/backup/env.sh ] && . /etc/backup/env.sh

LOG_FILE="/var/log/backup/backup.log"
log() { printf '[%s] %s\n' "$(date -Is)" "$*" >> "$LOG_FILE"; }

TIMESTAMP="$(date +%Y%m%d%H%M%S)"
SNAP_ROOT="/backups/local/snapshots"
SNAP_DIR="$SNAP_ROOT/$TIMESTAMP"
DOCS_SRC="/data/documents"
LATEST_LINK="/backups/local/meta/latest"
WORK_DIR="$SNAP_DIR/work"

mkdir -p "$SNAP_DIR/db" "$SNAP_DIR/documents" "$SNAP_DIR/meta" "$WORK_DIR"

on_exit() {
  code=$?
  rm -rf "$WORK_DIR"
  if [ "$code" -ne 0 ]; then
    log "ÉCHEC backup $TIMESTAMP (code $code)"
  fi
}
trap on_exit EXIT

log "Démarrage backup $TIMESTAMP"

BACKUP_ENCRYPTION_PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE:-}"
if [ -z "$BACKUP_ENCRYPTION_PASSPHRASE" ]; then
  log "BACKUP_ENCRYPTION_PASSPHRASE manquant, impossible de chiffrer l'archive"
  exit 2
fi

PGHOST="${POSTGRES_HOST:-db-main}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-postgres}"
PGPASSWORD="${POSTGRES_PASSWORD:-}"
export PGPASSWORD
POSTGRES_DB_MAIN="${POSTGRES_DB_MAIN:-sauvetage_main}"
POSTGRES_DB_USERS="${POSTGRES_DB_USERS:-sauvetage_users}"

log "pg_dump $POSTGRES_DB_MAIN commencé..."
pg_dump --format=custom \
  --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
  --dbname="$POSTGRES_DB_MAIN" \
  --file="$WORK_DIR/${POSTGRES_DB_MAIN}.dump" >>"$LOG_FILE" 2>&1
log "pg_dump $POSTGRES_DB_MAIN terminé"

log "pg_dump $POSTGRES_DB_USERS commencé..."
pg_dump --format=custom \
  --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
  --dbname="$POSTGRES_DB_USERS" \
  --file="$WORK_DIR/${POSTGRES_DB_USERS}.dump" >>"$LOG_FILE" 2>&1
log "pg_dump $POSTGRES_DB_USERS terminé"

MONGO_HOST="${MONGO_HOST:-db-logs}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB_LOGS="${MONGO_DB_LOGS:-sauvetage_logs}"
MONGO_INITDB_ROOT_USERNAME="${MONGO_INITDB_ROOT_USERNAME:-admin}"
MONGO_INITDB_ROOT_PASSWORD="${MONGO_INITDB_ROOT_PASSWORD:-}"

log "mongodump $MONGO_DB_LOGS commencé..."
mongodump \
  --host="$MONGO_HOST" --port="$MONGO_PORT" \
  --username="$MONGO_INITDB_ROOT_USERNAME" --password="$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase=admin --db="$MONGO_DB_LOGS" \
  --archive="$WORK_DIR/${MONGO_DB_LOGS}.archive.gz" --gzip >>"$LOG_FILE" 2>&1
log "mongodump $MONGO_DB_LOGS terminé"

# Archive unique des bases de données, chiffrée (AES-256, clé dérivée par PBKDF2).
log "Chiffrement de l'archive DB..."
DB_ARCHIVE="$SNAP_DIR/db/db_${TIMESTAMP}.tar.enc"
tar -C "$WORK_DIR" -cf - . \
  | openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt -pass env:BACKUP_ENCRYPTION_PASSPHRASE \
  > "$DB_ARCHIVE"
log "Chiffrement de l'archive DB terminé"

# Snapshot des documents (rsync local incrémental via --link-dest sur le snapshot précédent).
DOCS_DST="$SNAP_DIR/documents"
log "Snapshot des documents depuis $DOCS_SRC vers $DOCS_DST..."
if [ -L "$LATEST_LINK" ] && [ -d "$(readlink -f "$LATEST_LINK")/documents" ]; then
  LINK_DEST="$(readlink -f "$LATEST_LINK")/documents"
  rsync -a --delete --link-dest="$LINK_DEST" "$DOCS_SRC/" "$DOCS_DST/" >>"$LOG_FILE" 2>&1
else
  rsync -a --delete "$DOCS_SRC/" "$DOCS_DST/" >>"$LOG_FILE" 2>&1
fi
log "Snapshot des documents terminé"

cat > "$SNAP_DIR/meta/manifest.txt" <<EOF
timestamp=$TIMESTAMP
postgres_main=$POSTGRES_DB_MAIN
postgres_users=$POSTGRES_DB_USERS
mongo_db=$MONGO_DB_LOGS
db_archive=db_${TIMESTAMP}.tar.enc
EOF

sha256sum "$DB_ARCHIVE" > "$SNAP_DIR/meta/sha256sums.txt"

ln -sfn "$SNAP_DIR" "$LATEST_LINK"

KEEP_DAYS="${KEEP_DAYS:-30}"
PURGED_LOCAL="$(find "$SNAP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -printf '%f\n')"
if [ -n "$PURGED_LOCAL" ]; then
  find "$SNAP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} +
  log "Snapshots locaux purgés (> $KEEP_DAYS j): $(echo "$PURGED_LOCAL" | tr '\n' ' ')"
fi

REMOTE_ENABLED="${REMOTE_ENABLED:-false}"
if [ "$REMOTE_ENABLED" = "true" ]; then
  REMOTE_USER="${REMOTE_USER:?REMOTE_USER manquant}"
  REMOTE_HOST="${REMOTE_HOST:?REMOTE_HOST manquant}"
  REMOTE_PORT="${REMOTE_PORT:-22}"
  REMOTE_BASE_PATH="${REMOTE_BASE_PATH:?REMOTE_BASE_PATH manquant}"
  REMOTE_SSH_KEY="${REMOTE_SSH_KEY:-id_ed25519}"
  ARCHIVE_RETENTION_DAYS="${ARCHIVE_RETENTION_DAYS:-30}"

  SSH_KEY_PATH="/root/.ssh/$REMOTE_SSH_KEY"
  [ -f "$SSH_KEY_PATH" ] || { log "Clé SSH introuvable: $SSH_KEY_PATH"; exit 2; }

  SSH_OPTS="-p $REMOTE_PORT -i $SSH_KEY_PATH -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/root/.ssh/known_hosts"
  # scp utilise -P (majuscule) pour le port, contrairement à ssh/rsync.
  SCP_OPTS="-P $REMOTE_PORT -i $SSH_KEY_PATH -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/root/.ssh/known_hosts"

  ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" \
    "mkdir -p '$REMOTE_BASE_PATH/db' '$REMOTE_BASE_PATH/documents/current' '$REMOTE_BASE_PATH/documents/archive'" \
    >>"$LOG_FILE" 2>&1

  # Canal 1 : archive DB chiffrée, transfert point à point via SCP.
  scp $SCP_OPTS "$DB_ARCHIVE" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/db/db_${TIMESTAMP}.tar.enc" \
    >>"$LOG_FILE" 2>&1

  # Canal 2 : documents, synchronisation incrémentale via rsync/SSH (soft delete archivé).
  rsync -az --delete --backup --backup-dir="$REMOTE_BASE_PATH/documents/archive/$TIMESTAMP" \
    -e "ssh $SSH_OPTS" \
    "$DOCS_SRC/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/documents/current/" \
    >>"$LOG_FILE" 2>&1

  # Purge distante : archives soft-delete des documents, archives DB, au-delà des rétentions configurées.
  REMOTE_PURGE_LOG="$(ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "
    find '$REMOTE_BASE_PATH/documents/archive' -mindepth 1 -maxdepth 1 -type d -mtime +$ARCHIVE_RETENTION_DAYS -printf 'archive:%f\n' -exec rm -rf {} +
    find '$REMOTE_BASE_PATH/db' -type f -mtime +$KEEP_DAYS -printf 'db:%f\n' -delete
  ")"
  [ -n "$REMOTE_PURGE_LOG" ] && log "Purge distante: $(echo "$REMOTE_PURGE_LOG" | tr '\n' ' ')"

  log "Copie distante terminée"
fi

log "Backup terminé: $SNAP_DIR"
