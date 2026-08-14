#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/backup/backup.log"
mkdir -p /backups/local/snapshots /backups/local/meta /var/log/backup /etc/backup /etc/cron.d
touch "$LOG_FILE" /var/log/backup/restore.log

log() { printf '[%s] %s\n' "$(date -Is)" "$*" >> "$LOG_FILE"; }

# Cron démarre avec un environnement vide : on capture les variables utiles du conteneur
# pour que run-backup.sh dispose des identifiants et de la configuration distante.
{
  for var in $(compgen -e); do
    case "$var" in
      POSTGRES_*|MONGO_*|REMOTE_*|BACKUP_*|KEEP_DAYS|ARCHIVE_RETENTION_DAYS)
        value="${!var}"
        printf "%s='%s'\n" "$var" "$(printf '%s' "$value" | sed "s/'/'\\\\''/g")"
        ;;
    esac
  done
} > /etc/backup/env.sh
chmod 600 /etc/backup/env.sh

CRON_SCHEDULE="${CRON_SCHEDULE:-1 2 * * *}"
cat > /etc/cron.d/backup-cron <<EOF
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
$CRON_SCHEDULE root /usr/local/bin/run-backup.sh
EOF
chmod 0644 /etc/cron.d/backup-cron

if [ "${RUN_ON_STARTUP:-true}" = "true" ]; then
  log "Sauvegarde initiale au démarrage"
  /usr/local/bin/run-backup.sh || log "Échec de la sauvegarde initiale"
fi

log "Cron démarré (schedule: $CRON_SCHEDULE)"
exec cron -f
