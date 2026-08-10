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
# Project root (script is in backup/): allow running from anywhere
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Allow overriding via env; otherwise prefer container mount `/backups` when present,
# else fall back to project-local directories
if [ -n "${SNAP_ROOT:-}" ]; then
  SNAP_ROOT="$SNAP_ROOT"
elif [ -d "/backups" ]; then
  SNAP_ROOT="/backups/local/snapshots"
else
  SNAP_ROOT="${SNAP_ROOT:-$PROJECT_ROOT/backups/local/snapshots}"
fi
SNAP_DIR="$SNAP_ROOT/$TIMESTAMP"
if [ -n "${DOCS_SRC:-}" ]; then
  DOCS_SRC="$DOCS_SRC"
elif [ -d "/data/documents" ]; then
  DOCS_SRC="/data/documents"
else
  DOCS_SRC="$PROJECT_ROOT/documents"
fi
DOCS_DST="$SNAP_DIR/documents"
# Default PREV_LINK should be relative to SNAP_ROOT (../meta/latest)
PREV_LINK="${PREV_LINK:-$(dirname "$SNAP_ROOT")/meta/latest}"

# Logs directory: prefer container-mounted path /var/log/backup when available,
# otherwise fall back to project-local backup_logs. Allow override via LOG_DIR env.
if [ -n "${LOG_DIR:-}" ]; then
  LOG_DIR="$LOG_DIR"
elif [ -d "/var/log/backup" ] || [ -w "/var/log/backup" ]; then
  LOG_DIR="/var/log/backup"
else
  LOG_DIR="$PROJECT_ROOT/backup_logs"
fi
LOG_FILE="$LOG_DIR/backup.log"

# Ensure log and snapshot directories exist and log file is present
mkdir -p "$LOG_DIR"
mkdir -p "$SNAP_DIR/postgres" "$SNAP_DIR/mongo" "$SNAP_DIR/meta"

# Open a single safe file descriptor 3 for combined logging: append to LOG_FILE if possible,
# otherwise redirect to /dev/null so redirections in commands don't cause failures.
if exec 3>>"$LOG_FILE" 2>/dev/null; then
  :
else
  exec 3>/dev/null
fi

# Redirect stdout and stderr to fd3 so both go into the same log file (or /dev/null fallback)
exec 1>&3 2>&3

# Trap to capture failures and write diagnostics to the error log without stopping container
on_exit() {
  code=$?
  if [ "$code" -ne 0 ]; then
    {
      printf "\n[%s] SCRIPT EXIT WITH CODE %s\n" "$(date -Is)" "$code"
      printf "SNAP_DIR=%s\n" "$SNAP_DIR"
      printf "PROJECT_ROOT=%s\n" "$PROJECT_ROOT"
      printf "Last lines of %s:\n" "$LOG_FILE"
      tail -n 200 "$LOG_FILE" 2>/dev/null || true
      printf "Listing snapshot dir contents (first 200 files):\n"
      ls -lR "$SNAP_DIR" 2>/dev/null | head -n 200 || true
    } >&3
  fi
}
trap 'on_exit' EXIT

PGHOST="${POSTGRES_HOST:-db-main}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-postgres}"
PGPASSWORD="${POSTGRES_PASSWORD:-}"
export PGPASSWORD

POSTGRES_DB_MAIN="${POSTGRES_DB_MAIN:-sauvetage_main}"
POSTGRES_DB_USERS="${POSTGRES_DB_USERS:-sauvetage_users}"

echo "[$(date -Is)] Démarrage backup $TIMESTAMP"

pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --host="$PGHOST" \
  --port="$PGPORT" \
  --username="$PGUSER" \
  --dbname="$POSTGRES_DB_MAIN" \
  --file="$SNAP_DIR/postgres/${POSTGRES_DB_MAIN}.dump" 2>&3

pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --host="$PGHOST" \
  --port="$PGPORT" \
  --username="$PGUSER" \
  --dbname="$POSTGRES_DB_USERS" \
  --file="$SNAP_DIR/postgres/${POSTGRES_DB_USERS}.dump" 2>&3

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
  --gzip 2>&3

mkdir -p "$DOCS_DST"
if [ -L "$PREV_LINK" ] && [ -d "$(readlink -f "$PREV_LINK")/documents" ]; then
  LINK_DEST="$(readlink -f "$PREV_LINK")/documents"
  rsync -a --delete --link-dest="$LINK_DEST" "$DOCS_SRC/" "$DOCS_DST/" 2>&3
else
  rsync -a --delete "$DOCS_SRC/" "$DOCS_DST/" 2>&3
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
    echo "REMOTE_ENABLED=true mais REMOTE_USER/REMOTE_HOST/REMOTE_BASE_PATH manquants"
    exit 2
  fi

  # Prepare SSH options, handling missing key or unknown host gracefully.
  SSH_KEY_PATH="/root/.ssh/$REMOTE_SSH_KEY"
  KNOWN_HOSTS_FILE="/root/.ssh/known_hosts"
  SSH_OPTS_BASE="-p $REMOTE_PORT"

  if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "Warning: Identity file $SSH_KEY_PATH not accessible: No such file or directory." >&3
    if [ "$REMOTE_STRICT" = "true" ]; then
      echo "REMOTE_STRICT=true and SSH key missing ($SSH_KEY_PATH)"
      exit 2
    else
      echo "REMOTE_STRICT=false — continuer sans clé explicite (agent/host-key auth)" >&3
      SSH_OPTS_BASE="$SSH_OPTS_BASE -o IdentitiesOnly=no"
    fi
  else
    SSH_OPTS_BASE="$SSH_OPTS_BASE -i $SSH_KEY_PATH"
  fi

  # Ensure host key is known; try to add via ssh-keyscan when possible.
  HOST_KNOWN=0
  if [ -f "$KNOWN_HOSTS_FILE" ]; then
    if ssh-keygen -F "$REMOTE_HOST" -f "$KNOWN_HOSTS_FILE" >/dev/null 2>&1; then
      HOST_KNOWN=1
    fi
  fi

  if [ "$HOST_KNOWN" -eq 0 ]; then
    # Try ssh-keyscan if available and known_hosts writable
    if command -v ssh-keyscan >/dev/null 2>&1 && [ -w "$(dirname "$KNOWN_HOSTS_FILE")" ] && [ -w "${KNOWN_HOSTS_FILE:-$(dirname "$KNOWN_HOSTS_FILE")}" ] 2>/dev/null; then
      echo "ssh-keyscan $REMOTE_HOST:$REMOTE_PORT" >&3
      ssh-keyscan -p "$REMOTE_PORT" "$REMOTE_HOST" >>"$KNOWN_HOSTS_FILE" 2>&3 || true
      if ssh-keygen -F "$REMOTE_HOST" -f "$KNOWN_HOSTS_FILE" >/dev/null 2>&1; then
        HOST_KNOWN=1
      fi
    fi
  fi

  if [ "$HOST_KNOWN" -eq 0 ]; then
    echo "No ED25519 host key is known for $REMOTE_HOST and StrictHostKeyChecking requested." >&3
    if [ "$REMOTE_STRICT" = "true" ]; then
      echo "REMOTE_STRICT=true — aborting remote copy"
      exit 2
    else
      echo "REMOTE_STRICT=false — disabling StrictHostKeyChecking for this session" >&3
      SSH_OPTS_BASE="$SSH_OPTS_BASE -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    fi
  else
    SSH_OPTS_BASE="$SSH_OPTS_BASE -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$KNOWN_HOSTS_FILE"
  fi

  SSH_OPTS="$SSH_OPTS_BASE"

  set +e
    ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "mkdir -p '$REMOTE_BASE_PATH/snapshots' '$REMOTE_BASE_PATH/documents/current' '$REMOTE_BASE_PATH/documents/archive'" 2>&3
  REMOTE_RC=$?

  if [ "$REMOTE_RC" -eq 0 ]; then
    rsync -az --delete \
      -e "ssh $SSH_OPTS" \
      "$SNAP_DIR/postgres/" \
      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/snapshots/$TIMESTAMP/postgres/" 2>&3
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    rsync -az --delete \
      -e "ssh $SSH_OPTS" \
      "$SNAP_DIR/mongo/" \
      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/snapshots/$TIMESTAMP/mongo/" 2>&3
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    rsync -az \
      -e "ssh $SSH_OPTS" \
      "$SNAP_DIR/meta/" \
      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/snapshots/$TIMESTAMP/meta/" 2>&3
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    rsync -az --delete --backup \
      --backup-dir="$REMOTE_BASE_PATH/documents/archive/$TIMESTAMP" \
      -e "ssh $SSH_OPTS" \
      "$DOCS_SRC/" \
      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE_PATH/documents/current/" 2>&3
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "find '$REMOTE_BASE_PATH/documents/archive' -mindepth 1 -maxdepth 1 -type d -mtime +$ARCHIVE_RETENTION_DAYS -exec rm -rf {} +" 2>&3
    REMOTE_RC=$?
  fi

  if [ "$REMOTE_RC" -eq 0 ]; then
    ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "find '$REMOTE_BASE_PATH/snapshots' -mindepth 1 -maxdepth 1 -type d -mtime +$KEEP_DAYS -exec rm -rf {} +" 2>&3
    REMOTE_RC=$?
  fi
  set -e

  if [ "$REMOTE_RC" -ne 0 ]; then
    if [ "$REMOTE_STRICT" = "true" ]; then
      echo "Copie distante en échec (REMOTE_STRICT=true)"
      exit "$REMOTE_RC"
    fi
    echo "Copie distante en échec, backup local conservé (REMOTE_STRICT=false)"
  fi
fi

echo "[$(date -Is)] Backup terminé: $SNAP_DIR"
