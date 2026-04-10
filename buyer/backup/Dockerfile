FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       default-mysql-client \
       tar \
       cron \
       openssh-client \
       openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/backup

# copy scripts from repo
COPY tools/functions.py ./functions.py
COPY tools/backup_wp.py ./backup_wp.py
COPY tools/restore_wp.py ./restore_wp.py
COPY backup/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh \
    && chmod +x /opt/backup/backup_wp.py

VOLUME ["/backups", "/var/log/backup"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
