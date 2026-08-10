# Sauvegarde applicative (PostgreSQL + MongoDB + documents)

Ce dossier contient le système de sauvegarde principal du projet.

## Ce qui est sauvegardé

- Dumps PostgreSQL des bases `sauvetage_main` et `sauvetage_users`
- Dump MongoDB de la base `sauvetage_logs`
- Snapshot local des documents (`documents/`) avec rsync incrémental (`--link-dest`)
- Copie distante via SSH/rsync si activée

## Soft delete des documents (distant)

La synchronisation distante des documents utilise `rsync --delete --backup --backup-dir`.

- Les fichiers supprimés localement sont déplacés vers :
  - `${REMOTE_BASE_PATH}/documents/archive/<timestamp>/...`
- Les archives de suppression sont purgées automatiquement après `ARCHIVE_RETENTION_DAYS` (30 par défaut).

## Configuration

Créer le fichier `backup/.env.save` à partir de `backup/.env.exemple`.

Variables importantes :

- `REMOTE_ENABLED` : active/désactive la copie distante
- `REMOTE_STRICT` : si `true`, un échec distant fait échouer le backup; si `false`, le backup local reste valide
- `KEEP_DAYS` : rétention des snapshots locaux/distants
- `ARCHIVE_RETENTION_DAYS` : rétention des suppressions documentaires archivées
- `REMOTE_USER`, `REMOTE_HOST`, `REMOTE_PORT`, `REMOTE_BASE_PATH`
- `REMOTE_SSH_KEY` : nom de la clé montée dans `backup/ssh`

## Exécution

- Service permanent : `backup` dans `docker-compose.yml`
- Cron par défaut : `0 2 * * *`
- Lancement manuel snapshot : `./scripts/snapshot_main.sh`
- Restauration : `./scripts/restore_main_backup.sh --snapshot latest`

## Pré-requis SSH

- Ajouter la clé privée dans `backup/ssh/` (fichier non versionné)
- Ajouter la clé hôte distante dans `backup/ssh/known_hosts`
- Droits recommandés : `chmod 600` pour la clé privée
