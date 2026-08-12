# Sauvegarde applicative (PostgreSQL + MongoDB + documents)

Ce dossier contient le système de sauvegarde principal du projet.

## Ce qui est sauvegardé

Chaque snapshot local (`/backups/local/snapshots/<timestamp>/`) contient deux artefacts distincts :

- `db/db_<timestamp>.tar.enc` : archive unique (tar) des dumps PostgreSQL (`sauvetage_main`,
  `sauvetage_users`) et du dump MongoDB (`sauvetage_logs`), **chiffrée en AES-256** (openssl,
  dérivation PBKDF2, passphrase dans `BACKUP_ENCRYPTION_PASSPHRASE`).
- `documents/` : snapshot incrémental des documents (rsync local avec `--link-dest`).

## Copie distante (si `REMOTE_ENABLED=true`)

Deux canaux séparés, chacun avec sa propre connexion SSH :

- **SCP** : envoi de l'archive DB chiffrée vers `${REMOTE_BASE_PATH}/db/`.
- **rsync sur SSH** : synchronisation des documents vers `${REMOTE_BASE_PATH}/documents/current/`,
  avec soft delete (`--backup --backup-dir`) vers `${REMOTE_BASE_PATH}/documents/archive/<timestamp>/`.

La connexion distante est toujours stricte : hôte connu (`known_hosts`) et clé privée obligatoires.
Un échec de copie distante fait échouer le backup (le snapshot local reste néanmoins conservé).

Les archives de suppression distantes et les archives DB distantes sont purgées après
`ARCHIVE_RETENTION_DAYS` / `KEEP_DAYS` jours respectivement.

## Configuration

Créer le fichier `config/env/.env.backup` à partir de `backup/.env.exemple` et le monter dans le conteneur backup.

Variables importantes :

- `BACKUP_ENCRYPTION_PASSPHRASE` : passphrase de chiffrement de l'archive DB (obligatoire)
- `REMOTE_ENABLED` : active/désactive la copie distante
- `KEEP_DAYS` : rétention des snapshots locaux et des archives DB distantes
- `ARCHIVE_RETENTION_DAYS` : rétention des suppressions documentaires archivées
- `REMOTE_USER`, `REMOTE_HOST`, `REMOTE_PORT`, `REMOTE_BASE_PATH`
- `REMOTE_SSH_KEY` : nom de la clé montée dans `backup/ssh`

## Exécution

- Service permanent : `backup` dans `docker-compose.yml` (cron interne, `CRON_SCHEDULE=0 2 * * *`)
- Lancement manuel (dans le conteneur déjà démarré) : `./scripts/snapshot_container.sh`
- Restauration : `./scripts/restore_snapshot.sh`

## Logs et verbosité

Les scripts de backup/restauration écrivent leurs traces dans :

- `backup_logs/backup.log` : log principal des opérations de sauvegarde.
- `backup_logs/restore.log` : log principal des opérations de restauration.

Par défaut `pg_dump` et `pg_restore` ne sont pas lancés en mode verbeux pour éviter
une surcharge de sortie dans les logs. Les scripts inscrivent toutefois des marqueurs
`pg_dump <db> commencé...` / `pg_dump <db> terminé` et redirigent toute la sortie
standard et d'erreur vers les fichiers de log cités ci‑dessus.

Si vous souhaitez activer la verbosité pour diagnostiquer un problème, il faut
modifier les scripts `backup/run-backup.sh` et `backup/run-restore.sh` : ajouter
le flag `-v` aux appels `pg_dump` / `pg_restore`, puis rebuild/recréer le conteneur
backup. Exemple :

```bash
# Rebuild (podman)
podman compose up --build -d --no-deps --force-recreate backup

# Lancer un backup manuel et suivre les logs
./scripts/snapshot_container.sh
tail -f backup_logs/backup.log

# Lancer une restauration (interactif via le script) et consulter le log
./scripts/restore_snapshot.sh
tail -f backup_logs/restore.log
```

Attention : activer `-v` pour `pg_dump`/`pg_restore` peut générer beaucoup de
sortie pour de grosses bases, pensez à ne l'activer que pour la durée du
diagnostic.

## Pré-requis SSH

- Déposer la clé privée existante dans `backup/ssh/` (fichier non versionné, `chmod 600`)
- Déposer le `known_hosts` correspondant au serveur distant dans `backup/ssh/known_hosts`
