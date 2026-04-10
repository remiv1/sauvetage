#!/bin/sh
set -e

# Prépare les dossiers
mkdir -p /backups /var/log/backup /etc/backup

if [ -f "/etc/backup/.env.wordpress" ]; then
  echo "/etc/backup/.env.wordpress présent"
else
  echo "Warning: /etc/backup/.env.wordpress absent (montez-le si nécessaire)"
fi

# Génère le runner qui appelle le script de backup
cat > /usr/local/bin/run-backup.sh <<'EOF'
#!/bin/sh
set -e

# Commande de backup
CMD="python3 /opt/backup/backup_wp.py --in-container --env-file /etc/backup/.env.wordpress --out-dir /backups --wp-path /var/www/html"

if [ -n "${ENCRYPT_KEY}" ]; then
  CMD="$CMD --encrypt-key '${ENCRYPT_KEY}'"
fi
if [ -n "${SSH_DEST}" ]; then
  CMD="$CMD --ssh-dest '${SSH_DEST}'"
  if [ -n "${SSH_PORT}" ]; then
    CMD="$CMD --ssh-port ${SSH_PORT}"
  fi
fi

echo "Exécution: $CMD"
sh -c "$CMD"
EOF

chmod +x /usr/local/bin/run-backup.sh

# Schedule via cron. Format attendu: 'm h dom mon dow'
CRON_SCHEDULE="${CRON_SCHEDULE:-0 2 * * *}"
echo "$CRON_SCHEDULE root /usr/local/bin/run-backup.sh >> /var/log/backup/backup.log 2>&1" > /etc/cron.d/backup-cron
chmod 0644 /etc/cron.d/backup-cron

echo "Lancement de cron (foreground) — schedule: $CRON_SCHEDULE"
exec cron -f
