#!/bin/sh
set -eu

CALLER_REMOTE_ENABLED="${REMOTE_ENABLED-__UNSET__}"
CALLER_REMOTE_STRICT="${REMOTE_STRICT-__UNSET__}"

if [ -f /etc/backup/.env.save ]; then
  # shellcheck disable=SC1090
  . /etc/backup/.env.save
fi

if [ "$CALLER_REMOTE_ENABLED" != "__UNSET__" ]; then
  REMOTE_ENABLED="$CALLER_REMOTE_ENABLED"
fi

if [ "$CALLER_REMOTE_STRICT" != "__UNSET__" ]; then
  REMOTE_STRICT="$CALLER_REMOTE_STRICT"
fi

TIMESTAMP="$(date +%Y%m%d%H%M%S)"
SNAP_ROOT="/backups/local/snapshots"
SNAP_DIR="$SNAP_ROOT/$TIMESTAMP"
DOCS_SRC="/data/documents"
DOCS_DST="$SNAP_DIR/documents"
PREV_LINK="/backups/local/meta/latest"
LOG_FILE="/var/log/backup/backup.log"

mkdir -p "$SNAP_DIR/postgres" "$SNAP_DIR/mongo" "$SNAP_DIR/meta"

PGHOST="${POSTGRES_HOST:-db-main}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-postgres}"
PGPASSWORD="${POSTGRES_PASSWORD:-}"
export PGPASSWORD

POSTGRES_DB_MAIN="${POSTGRES_DB_MAIN:-sauvetage_main}"
POSTGRES_DB_USERS="${POSTGRES_DB_USERS:-sauvetage_users}"

echo "[$(date -Is)] Démarrage backup $TIMESTAMP" | tee -a "$LOG_FILE"

pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --host="$PGHOST" \
  --port="$PGPORT" \
  --username="$PGUSER" \
  --dbname="$POSTGRES_DB_MAIN" \
  --file="$SNAP_DIR/postgres/${POSTGRES_DB_MAIN}.dump"

pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --host="$PGHOST" \
  --port="$PGPORT" \
  --username="$PGUSER" \
  --dbname="$POSTGRES_DB_USERS" \
  --file="$SNAP_DIR/postgres/${POSTGRES_DB_USERS}.dump"

MONGO_HOST="${MONGO_HOST:-db-logs}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB_LOGS="${MONGO_DB_LOGS:-sauvetage_logs}"
MONGO_INITDB_ROOT_USERNAME="${MONGO_INITDB_ROOT_USERNAME:-admin}"
MONGO_INITDB_ROOT_PASSWORD="${MONGO_INITDB_ROOT_PASSWORD:-}"

mongodump \
  --host="$MONGO_HOST" \
  --port="$MONGO_PORT" \
  --username="$MONGO_INITDB_ROOT_USERNAME" \
  --password="$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase=admin \
  --db="$MONGO_DB_LOGS" \
  --archive="$SNAP_DIR/mongo/${MONGO_DB_LOGS}.archive.gz" \
  --gzip

mkdir -p "$DOCS_DST"
if [ -L "$PREV_LINK" ] && [ -d "$(readlink -f "$PREV_LINK")/documents" ]; then
  LINK_DEST="$(readlink -f "$PREV_LINK")/documents"
  rsync -a --delete --link-dest="$LINK_DEST" "$DOCS_SRC/" "$DOCS_DST/"
else
  rsync -a --delete "$DOCS_SRC/" "$DOCS_DST/"
fi

cat > "$SNAP_DIR/meta/manifest.txt" <<EOF
timestamp=$TIMESTAMP
postgres_main=$POSTGRES_DB_MAIN
postgres_users=$POSTGRES_DB_USERS
mongo_db=$MONGO_DB_LOGS
EOF

(
  cd "$SNAP_DIR"
  find . -type f -print0 | sort -z | xargs -0 sha256sum > "$SNAP_DIR/meta/sha256sums.txt"
)

ln -sfn "$SNAP_DIR" "$PREV_LINK"

KEEP_DAYS="${KEEP_DAYS:-30}"
find "$SNAP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} +

REMOTE_ENABLED="${REMOTE_ENABLED:-false}"
if [ "$REMOTE_ENABLED" = "true" ]; then
  REMOTE_USER="${REMOTE_USER:-}"
  REMOTE_HOST="${REMOTE_HOST:-}"
  REMOTE_PORT="${REMOTE_PORT:-22}"
  REMOTE_BASE_PATH="${REMOTE_BASE_PATH:-}"
  REMOTE_SSH_KEY="${REMOTE_SSH_KEY:-id_ed25519}"
  ARCHIVE_RETENTION_DAYS="${ARCHIVE_RETENTION_DAYS:-30}"
  REMOTE_STRICT="${REMOTE_STRICT:-false}"

  if [ -z "$REMOTE_USER" ] || [ -z "$REMOTE_HOST" ] || [ -z "$REMOTE_BASE_PATH" ]; then
    echo "REMOTE_ENABLED=true mais REMOTE_USER/REMOTE_HOST/REMOTE_BASE_PATH manquants" | tee -a "$LOG_FILE"
    exit 2
  fi

  SSH_OPTS="-i /root/.ssh/$REMOTE_SSH_KEY -p $REMOTE_PORT -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/root/.ssh/known_hosts"

  set +e
  ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "mkdir -p '$REMOTE_BASE_PATH/snapshots' '$REMOTE_BASE_PATH/documents/current' '$REMOTE_BASE_PATH/documents/archive'"
  REMOTE_RC=$?

  if [ "$REMOTE_RC" -eq 0 ]; then
    rsync -az --delete \
      -e "ssh $SSH_OPTS" \
      "$SNAP_DIR/postgres/" \
      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/snapshots/$TIMESTAMP/postgres/"
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    rsync -az --delete \
      -e "ssh $SSH_OPTS" \
      "$SNAP_DIR/mongo/" \
      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/snapshots/$TIMESTAMP/mongo/"
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    rsync -az \
      -e "ssh $SSH_OPTS" \
      "$SNAP_DIR/meta/" \
      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/snapshots/$TIMESTAMP/meta/"
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    rsync -az --delete --backup \
      --backup-dir="$REMOTE_BASE_PATH/documents/archive/$TIMESTAMP" \
      -e "ssh $SSH_OPTS" \
      "$DOCS_SRC/" \
      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/documents/current/"
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "find '$REMOTE_BASE_PATH/documents/archive' -mindepth 1 -maxdepth 1 -type d -mtime +$ARCHIVE_RETENTION_DAYS -exec rm -rf {} +"
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "find '$REMOTE_BASE_PATH/snapshots' -mindepth 1 -maxdepth 1 -type d -mtime +$KEEP_DAYS -exec rm -rf {} +"
    REMOTE_RC=$?
  fi
  set -e

  if [ "$REMOTE_RC" -ne 0 ]; then
    if [ "$REMOTE_STRICT" = "true" ]; then
      echo "Copie distante en échec (REMOTE_STRICT=true)" | tee -a "$LOG_FILE"
      exit "$REMOTE_RC"
    fi
    echo "Copie distante en échec, backup local conservé (REMOTE_STRICT=false)" | tee -a "$LOG_FILE"
  fi
fi

echo "[$(date -Is)] Backup terminé: $SNAP_DIR" | tee -a "$LOG_FILE"
