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
- Backup manuel avec confirmation :

    ```bash
    ./scripts/snapshot_container.sh
    ```

    Pour ne pas demander de confirmation : `./scripts/snapshot_container.sh --yes`.

- Restauration interactive d’un snapshot daté :

    ```bash
    ./scripts/restore_snapshot.sh
    ```

    Ajouter `--new-cluster` pour restaurer sans conserver les propriétaires et privilèges PostgreSQL.

### Restauration directe

Pour utiliser les options récentes du script sans dépendre de la version du conteneur permanent, exécuter un conteneur ponctuel. Cette commande reconstruit l’image, ne démarre pas les services de base et contourne l’entrypoint (donc ne déclenche pas de backup automatique) :

```bash
podman compose run --build --no-deps --rm -T \
    --entrypoint /usr/local/bin/run-restore.sh backup \
    latest --encrypted true --dry-run
```

Le `--dry-run` déchiffre l’archive dans un répertoire temporaire et vérifie les dumps, sans modifier les bases ni les documents. Après vérification du fichier affiché et de sa provenance, retirer `--dry-run` pour lancer la restauration réelle. Celle-ci remplace le contenu des bases ciblées.

Pour restaurer un snapshot précis, remplacer `latest` par son horodatage, par exemple `20261013111303`.

Les anciennes archives DB chiffrées qui ne sont pas rangées dans un dossier de snapshot peuvent être données directement au script :

```bash
podman compose run --build --no-deps --rm -T \
    --entrypoint /usr/local/bin/run-restore.sh backup \
    /backups/local/snapshots/db_20261013082732.tar.enc --dry-run
```

Retirer `--dry-run` pour restaurer. Une archive DB fournie seule ne contient pas de snapshot de documents : ceux-ci ne sont donc pas restaurés. `--encrypted true|false` choisit le format lorsque le script sélectionne une archive dans un snapshot ; pour un fichier direct, le format est déduit de son extension (`.tar.enc` ou `.tar`). `--passphrase CLE` est accepté, mais il est préférable de configurer `BACKUP_ENCRYPTION_PASSPHRASE` dans `config/env/.env.backup` pour ne pas exposer la clé dans l’historique du shell ou la liste des processus.

## Logs et verbosité

Les scripts de backup/restauration écrivent leurs traces dans :

- `backup_logs/backup.log` : log principal des opérations de sauvegarde.
- `backup_logs/restore.log` : log principal des opérations de restauration.

Par défaut `pg_dump` et `pg_restore` ne sont pas lancés en mode verbeux pour éviter
une surcharge de sortie dans les logs. Les scripts inscrivent toutefois des marqueurs
`pg_dump <db> commencé...` / `pg_dump <db> terminé` et redirigent toute la sortie
standard et d'erreur vers les fichiers de log cités ci‑dessus.

Si vous souhaitez activer la verbosité pour diagnostiquer un problème, il faut
modifier les scripts `backup/run-backup.sh` et `backup/run-restore.sh`, puis
reconstruire l’image. Un conteneur ponctuel permet d’utiliser cette image sans
recréer le service permanent :

```bash
# Backup ponctuel avec l’image reconstruite
podman compose run --build --no-deps --rm -T \
    --entrypoint /usr/local/bin/run-backup.sh backup

# Suivre les logs
tail -f backup_logs/backup.log
tail -f backup_logs/restore.log
```

Attention : activer `-v` pour `pg_dump`/`pg_restore` peut générer beaucoup de
sortie pour de grosses bases, pensez à ne l'activer que pour la durée du
diagnostic.

## Pré-requis SSH

- Déposer la clé privée existante dans `backup/ssh/` (fichier non versionné, `chmod 600`)
- Déposer le `known_hosts` correspondant au serveur distant dans `backup/ssh/known_hosts`
