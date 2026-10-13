#!/bin/sh
set -eu

[ -f /etc/backup/env.sh ] && . /etc/backup/env.sh

LOG_FILE="/var/log/backup/restore.log"
log() { printf '[%s] %s\n' "$(date -Is)" "$*" >> "$LOG_FILE"; }

SNAPSHOT_ID="latest"
SNAPSHOT_SET="false"
ENCRYPTED="true"
ENCRYPTED_SET="false"
NEW_CLUSTER_FLAG="false"
DRY_RUN="false"
BACKUP_ENCRYPTION_PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE:-}"

usage() {
  printf 'Usage: %s [SNAPSHOT_ID|ARCHIVE_FILE] [--encrypted true|false] [--passphrase CLE] [--new-cluster] [--dry-run]\n' "$0"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --encrypted)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      case "$2" in
        true|false) ENCRYPTED="$2"; ENCRYPTED_SET="true" ;;
        *) printf '%s\n' '--encrypted accepte uniquement true ou false' >&2; exit 2 ;;
      esac
      shift 2
      ;;
    --passphrase)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      BACKUP_ENCRYPTION_PASSPHRASE="$2"
      shift 2
      ;;
    --new-cluster) NEW_CLUSTER_FLAG="true"; shift ;;
    --dry-run) DRY_RUN="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) printf 'Option inconnue: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    *)
      if [ "$SNAPSHOT_SET" = "true" ]; then
        printf 'Un seul identifiant de snapshot est autorisé: %s\n' "$1" >&2
        usage >&2
        exit 2
      fi
      SNAPSHOT_ID="$1"
      SNAPSHOT_SET="true"
      shift
      ;;
  esac
done

FILE_MODE="false"
DB_ARCHIVE=""
if [ -f "$SNAPSHOT_ID" ]; then
  FILE_MODE="true"
  DB_ARCHIVE="$SNAPSHOT_ID"
  case "$DB_ARCHIVE" in
    *.tar.enc) ARCHIVE_ENCRYPTED="true" ;;
    *.tar) ARCHIVE_ENCRYPTED="false" ;;
    *) printf 'Format d’archive non pris en charge: %s\n' "$DB_ARCHIVE" >&2; exit 2 ;;
  esac
  if [ "$ENCRYPTED_SET" = "true" ] && [ "$ENCRYPTED" != "$ARCHIVE_ENCRYPTED" ]; then
    printf 'Le flag --encrypted ne correspond pas au fichier %s\n' "$DB_ARCHIVE" >&2
    exit 2
  fi
  ENCRYPTED="$ARCHIVE_ENCRYPTED"
  RESTORE_DOCS="false"
else
  case "$SNAPSHOT_ID" in
    */*|*.tar|*.tar.enc) printf 'Fichier d’archive introuvable: %s\n' "$SNAPSHOT_ID" >&2; exit 2 ;;
  esac
  RESTORE_DOCS="${RESTORE_DOCS:-true}"
fi

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

if [ "$ENCRYPTED" = "true" ] && [ -z "$BACKUP_ENCRYPTION_PASSPHRASE" ]; then
  log "BACKUP_ENCRYPTION_PASSPHRASE manquant"
  exit 2
fi
export BACKUP_ENCRYPTION_PASSPHRASE

if [ "$FILE_MODE" = "true" ]; then
  SNAP_DIR=""
else
  if [ "$SNAPSHOT_ID" = "latest" ]; then
    SNAP_DIR="$(readlink -f "$LATEST_LINK")"
  else
    SNAP_DIR="$SNAP_ROOT/$SNAPSHOT_ID"
  fi

  if [ ! -d "$SNAP_DIR" ]; then
    log "Snapshot introuvable: $SNAP_DIR"
    exit 2
  fi
fi

if [ "$FILE_MODE" != "true" ]; then
  if [ "$ENCRYPTED" = "true" ]; then
    DB_ARCHIVE_PATTERN='*.tar.enc'
  else
    DB_ARCHIVE_PATTERN='*.tar'
  fi
  DB_ARCHIVES="$(find "$SNAP_DIR/db" -maxdepth 1 -type f -name "$DB_ARCHIVE_PATTERN")"
  DB_ARCHIVE_COUNT="$(printf '%s\n' "$DB_ARCHIVES" | sed '/^$/d' | wc -l | tr -d ' ')"
  if [ "$DB_ARCHIVE_COUNT" -gt 1 ]; then
    log "Plusieurs archives correspondent à --encrypted $ENCRYPTED dans $SNAP_DIR/db"
    printf '%s\n' "$DB_ARCHIVES" >&2
    exit 2
  fi
  DB_ARCHIVE="$DB_ARCHIVES"
  if [ -z "$DB_ARCHIVE" ]; then
    log "Archive DB correspondant à --encrypted $ENCRYPTED introuvable dans $SNAP_DIR/db"
    exit 2
  fi
fi

if [ "$FILE_MODE" = "true" ]; then
  log "Restauration depuis le fichier $DB_ARCHIVE"
else
  log "Restauration depuis $SNAP_DIR"
fi

if [ "$ENCRYPTED" = "true" ]; then
  log "Déchiffrement de l'archive DB..."
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -pass env:BACKUP_ENCRYPTION_PASSPHRASE \
    -in "$DB_ARCHIVE" | tar -C "$WORK_DIR" -xf -
  log "Déchiffrement de l'archive DB terminé"
else
  log "Extraction de l'archive DB non chiffrée..."
  tar -C "$WORK_DIR" -xf "$DB_ARCHIVE"
  log "Extraction de l'archive DB terminée"
fi

PGHOST="${POSTGRES_HOST:-db-main}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-postgres}"
PGPASSWORD="${POSTGRES_PASSWORD:-}"
export PGPASSWORD
POSTGRES_DB_MAIN="${POSTGRES_DB_MAIN:-sauvetage_main}"
POSTGRES_DB_USERS="${POSTGRES_DB_USERS:-sauvetage_users}"
MONGO_DB_LOGS="${MONGO_DB_LOGS:-sauvetage_logs}"

for RESTORE_FILE in "$WORK_DIR/${POSTGRES_DB_MAIN}.dump" "$WORK_DIR/${POSTGRES_DB_USERS}.dump" "$WORK_DIR/${MONGO_DB_LOGS}.archive.gz"; do
  if [ ! -f "$RESTORE_FILE" ]; then
    log "Fichier attendu absent de l'archive: $RESTORE_FILE"
    exit 2
  fi
done

if [ "$DRY_RUN" = "true" ]; then
  log "Validation des archives en mode dry-run..."
  pg_restore --list "$WORK_DIR/${POSTGRES_DB_MAIN}.dump" >/dev/null
  pg_restore --list "$WORK_DIR/${POSTGRES_DB_USERS}.dump" >/dev/null
  gzip -t "$WORK_DIR/${MONGO_DB_LOGS}.archive.gz"
  printf 'DRY-RUN: archive sélectionnée: %s\n' "$DB_ARCHIVE"
  printf 'DRY-RUN: restauration PostgreSQL: %s, %s\n' "$POSTGRES_DB_MAIN" "$POSTGRES_DB_USERS"
  printf 'DRY-RUN: restauration MongoDB: %s\n' "$MONGO_DB_LOGS"
  if [ "$RESTORE_DOCS" = "true" ]; then
    printf 'DRY-RUN: restauration des documents depuis %s/documents/ vers /data/documents/\n' "$SNAP_DIR"
  fi
  log "Dry-run terminé: aucune base ni aucun document n'a été modifié"
  exit 0
fi

log "pg_restore $POSTGRES_DB_MAIN commencé..."

# Choose pg_restore flags depending on cluster intent
if [ "$NEW_CLUSTER_FLAG" = "true" ]; then
  RESTORE_FLAGS="--clean --if-exists --no-owner --no-privileges"
else
  RESTORE_FLAGS="--clean --if-exists"
fi

pg_restore \
  $RESTORE_FLAGS \
  --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
  --dbname="$POSTGRES_DB_MAIN" \
  "$WORK_DIR/${POSTGRES_DB_MAIN}.dump" >>"$LOG_FILE" 2>&1
log "pg_restore $POSTGRES_DB_MAIN terminé"

log "pg_restore $POSTGRES_DB_USERS commencé..."
pg_restore \
  $RESTORE_FLAGS \
  --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
  --dbname="$POSTGRES_DB_USERS" \
  "$WORK_DIR/${POSTGRES_DB_USERS}.dump" >>"$LOG_FILE" 2>&1
log "pg_restore $POSTGRES_DB_USERS terminé"

MONGO_HOST="${MONGO_HOST:-db-logs}"
MONGO_PORT="${MONGO_PORT:-27017}"
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
