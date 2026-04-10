# Sauvegarde et restauration WordPress

Pipeline complet de backup/restore pour WordPress conteneurisé avec chiffrement optionnel et copie SSH.

## Architecture

| Fichier | Rôle |
| --- | --- |
| `tools/functions.py` | Utilitaires partagés (subprocess, crypto, env/DB, SCP, conteneur) |
| `tools/backup_wp.py` | Script de création de sauvegarde (dump SQL + wp-content + wp-config) |
| `tools/restore_wp.py` | Script de restauration (import SQL + restore wp-content/wp-config) |
| `tools/bkpctl.py` | CLI orchestrateur (dry-run, run, remote-*, restore-*) |
| `backup/Dockerfile` | Image Python avec mysqldump, tar, openssl, cron, openssh-client |
| `backup/entrypoint.sh` | Point d'entrée du conteneur: génère cron + run foreground |

## Format d'archive

Chaque backup produit : `wp_backup_YYYYMMDDHHMMSS.tar.gz`

Contenu:

```txt
wp_backup_*.tar.gz
├── wp_db.sql                    # Dump base de données
├── wp-content.tar.gz            # Conteneur WordPress
├── wp-config.php                # Fichier config WordPres
├── .env.wordpress               # Credentials de la base (optionnel)
└── docker-compose.yml           # (optionnel)
```

Sidecar SHA256: `wp_backup_*.tar.gz.sha256` (généré avant chiffrement).

## Commandes CLI (`bkpctl.py`)

Tous les chemins utilisent `./backups` relatif au dossier `buyer`.

### `dry-run`

Exécute une sauvegarde complète dans le conteneur, la copie localement et affiche le hash.

```bash
cd buyer/tools
python3 bkpctl.py dry-run
```

Usage: Test d'intégrité du pipeline sans étapes destructrices.

### `run`

Exécute une sauvegarde complète avec chiffrement et SCP optionnels.

```bash
python3 bkpctl.py run \
    [--encrypt-key KEY] \
    [--remote user@host:/path] \
    [--port SSH_PORT] \
    [--ssh-key /path/to/identity] \
    [--remove-plain]
```

Options:

- `--encrypt-key KEY`: Chiffre en AES-256-CBC (génère `.enc`); `--remove-plain` supprime l'archive plain.
- `--remote user@host:/path`: Copie via SCP vers une destination distante.
- `--port`: Port SSH (défaut: 22).
- `--ssh-key`: Clé privée SSH (défaut: ~/.ssh/id_rsa).

Output: Archive (plain ou `.enc`) + hash SHA256 sidecar.

### `remote-copy`

Copie une archive locale vers une destination distante via SCP.

```bash
python3 bkpctl.py remote-copy \
    --file wp_backup_YYYYMMDDHHMMSS.tar.gz \
    --dest user@host:/path \
    [--port SSH_PORT] \
    [--ssh-key /path/to/identity]
```

Usage: Ex-filtration d'une sauvegarde existante.

### `remote-get`

Récupère une archive distante vers `./backups`.

```bash
python3 bkpctl.py remote-get \
    --remote user@host:/path \
    --file wp_backup_YYYYMMDDHHMMSS.tar.gz \
    [--port SSH_PORT] \
    [--ssh-key /path/to/identity]
```

Usage: Rapatrier une sauvegarde de secours.

### `restore-last`

Restaure la dernière archive trouvée localement.

```bash
python3 bkpctl.py restore-last [--decrypt-key KEY]
```

Usage: Restauration rapide des derniers backups.

### `restore`

Restaure une archive spécifique.

```bash
python3 bkpctl.py restore \
    --file wp_backup_YYYYMMDDHHMMSS.tar.gz \
    [--decrypt-key KEY]
```

Options:

- `--decrypt-key KEY`: Déchiffre si archive `.enc`.

## Workflows typiques

### 1. Sauvegarde locale simple

```bash
cd buyer/tools
python3 bkpctl.py run
```

Archive stockée dans `./backups`.

### 2. Sauvegarde chiffrée et copie SSH

```bash
python3 bkpctl.py run \
    --encrypt-key "supersecret" \
    --remote backup@backup.example.com:/srv/backups \
    --port 2222 \
    --remove-plain
```

Produit `wp_backup_*.tar.gz.enc` chiffré + `.sha256` (plain), puis copie vers serveur distant.

### 3. Sauvegarde automatique (cron)

Le service `backup` s'exécute en cron (par défaut `0 2 * * *` = 02:00).

```bash
cd buyer
podman compose up -d --force-recreate backup
```

Configuration via `docker-compose.yml`:

```yaml
backup:
    environment:
        CRON_SCHEDULE: "0 2 * * *"
        ENCRYPT_KEY: "supersecret"
        SSH_DEST: "backup@backup.example.com:/srv/backups"
        SSH_PORT: "2222"
```

Logs: `./backup_logs/backup.log`.

### 4. Restauration complète après sinistre

```bash
# 1. Arrêter et supprimer volumes
cd buyer
podman compose down -v

# 2. Redémarrer l'infra
podman compose up -d --build

# 3. Restaurer depuis local
cd tools
python3 bkpctl.py restore --file wp_backup_20260410134953.tar.gz

# Ou depuis une archive chiffrée
python3 bkpctl.py restore \
    --file wp_backup_20260410134953.tar.gz.enc \
    --decrypt-key "supersecret"
```

### 5. Récupérer un backup depuis un serveur distant

```bash
python3 bkpctl.py remote-get \
    --remote backup@backup.example.com:/srv/backups \
    --file wp_backup_20260410134953.tar.gz \
    --port 2222

python3 bkpctl.py restore --file wp_backup_20260410134953.tar.gz
```

## Configuration (docker-compose)

Extrait typique:

```yaml
services:
    backup:
        build: ./backup
        environment:
            CRON_SCHEDULE: "0 2 * * *"
            ENCRYPT_KEY: "supersecret"
            SSH_DEST: "backup@backup.example.com:/srv/backups"
            SSH_PORT: "2222"
        volumes:
            - ./backups:/backups
            - ./backup_logs:/var/log/backup
            - ./.env.wordpress:/etc/backup/.env.wordpress:ro
            - ./ssh:/root/.ssh:ro
        depends_on:
            - db
            - wordpress
```

Extensions:

- Montez votre clé SSH privée: `./ssh/id_rsa` (permissions 600).
- Montez `.env.wordpress` ou créez-le dans l'image via `COPY`.
- Modifier `CRON_SCHEDULE` (format crontab).

## Sécurité

- **Clés**: Ne stockez jamais la clé de chiffrement ou les identifiants SSH dans l'image. Utilisez des bind mounts ou des secrets Podman/Docker.
- **Répertoires**: Protégez `./backups` (contient archives en clair) et `./ssh` (contient clés privées).
- **SHA256**: Le sidecar `.sha256` est généré **avant** chiffrement; validez toujours l'intégrité en local.
- **Logs**: Consultez `./backup_logs/backup.log` pour auditer les exécutions cron.

## Dépannage

### Erreur `podman/docker compose introuvable`

Assurez-vous que `podman` (ou `docker`) est sur le PATH. Vérifiez avec:

```bash
podman compose version
```

### `mysqldump: TLS/SSL error`

Le client MySQL exige SSL, mais MariaDB local ne le supporte pas → les scripts utilisent `--skip-ssl`.

### Archive introuvable dans `./backups`

- Vérifiez le volume bind: `podman volume ls` et le mode lecture/écriture.
- Consultez les logs: `tail -f ./backup_logs/backup.log`.

### Restauration ne retrouve pas le conteneur

Assurez-vous que les conteneurs `wp_db` et `wp_app` sont en cours d'exécution:

```bash
podman ps | grep wp_
```

### Chiffrement/déchiffrement échoue

Vérifiez que `openssl` est disponible:

```bash
which openssl
```

Confirmez la clé (pas d'espaces superflus ou caractères échappés).

## Dossier attendu

```txt
buyer/
├── docker-compose.yml
├── .env.wordpress
├── backups/              # Archives (auto-généré)
├── backup_logs/          # Logs cron (auto-généré)
├── ssh/                  # Clés SSH (optionnel)
│   └── id_rsa            # Clé privée (permissions 600)
├── backup/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── README.md         # Ce fichier
└── tools/
        ├── functions.py
        ├── backup_wp.py
        ├── restore_wp.py
        └── bkpctl.py
```

## Cognitive Complexity

Afin de maintenir la maintenabilité:

- `backup_wp.py`: Complexité ≤ 15 (orchestration séparation `_dump_*`, `_archive_*`, `_collect_sources`).
- `restore_wp.py`: Complexité ≤ 15 (délégation `_extract`, `_import_sql`, `_restore_*`, `_fix_permissions`).
- `bkpctl.py`: Complexité ≤ 15 (dispatch simple des sous-commandes).
- `functions.py`: Utilitaires de faible complexité (subprocess, crypto, env parsing).
