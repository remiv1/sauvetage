FROM postgres:18

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       rsync \
       cron \
       openssh-client \
       openssl \
       ca-certificates \
       tar \
       gzip \
       findutils \
    && rm -rf /var/lib/apt/lists/*

# Récupère les outils mongodump/mongorestore depuis l'image officielle MongoDB.
COPY --from=mongo:7.0 /usr/bin/mongodump /usr/local/bin/mongodump
COPY --from=mongo:7.0 /usr/bin/mongorestore /usr/local/bin/mongorestore

WORKDIR /opt/backup

COPY backup/run-backup.sh /usr/local/bin/run-backup.sh
COPY backup/run-restore.sh /usr/local/bin/run-restore.sh
COPY backup/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh \
    /usr/local/bin/run-backup.sh \
    /usr/local/bin/run-restore.sh

VOLUME ["/backups", "/var/log/backup", "/data/documents"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
