#!/bin/sh
set -eu

mkdir -p /backups/local/snapshots /backups/local/meta /var/log/backup /etc/backup /etc/cron.d /var/run/cron
LOG_FILE="/var/log/backup/backup.log"
: > "$LOG_FILE"

CRON_SCHEDULE="${CRON_SCHEDULE:-0 2 * * *}"
cat > /etc/cron.d/backup-cron <<EOF
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
$CRON_SCHEDULE root /usr/local/bin/run-backup.sh >> /var/log/backup/backup.log 2>&1
EOF
chmod 0644 /etc/cron.d/backup-cron

if [ "${RUN_ON_STARTUP:-true}" = "true" ]; then
  echo "Exécution initiale de la sauvegarde au démarrage" | tee -a "$LOG_FILE"
  /usr/local/bin/run-backup.sh || echo "Échec de la sauvegarde initiale" | tee -a "$LOG_FILE"
fi

echo "Lancement de cron (foreground) - schedule: $CRON_SCHEDULE" | tee -a "$LOG_FILE"
exec cron -f
