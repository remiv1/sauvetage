# Scripts de sauvegarde WordPress

Utilitaires Python refactorisés pour backup/restore conteneurisé avec complexité cognitive ≤ 15 par fonction.

## Architecture logicielle

### `functions.py` (~210 lignes)

Utilitaires partagés — **aucune dépendance circulaire**, importé par tous les autres modules.

#### Subprocess (exécution de commandes)

- `run_to_file(cmd, out_path, *, cwd=None)`: Exécute `cmd` → redirige stdout vers `out_path`. Lève `RuntimeError`.
- `run_capture(cmd, *, cwd=None) -> bytes`: Exécute `cmd` → retourne stdout. Lève `RuntimeError`.
- `run_with_stdin(cmd, input_path)`: Exécute `cmd` avec `input_path` en stdin. Lève `RuntimeError`.

#### Env / DB parsing

- `load_env(env_path: Path) -> dict`: Parse fichier KEY=VALUE simple. Ignore `#` et lignes vides.
- `@dataclass DBConfig`: `user`, `password`, `name`, `host`, `port`.
- `parse_db_config(env: dict, *, user=None, password=None, name=None) -> DBConfig`: Résout configuration DB avec surcharges → env → defaults. Supporte fallback: `WORDPRESS_DB_*`, `DB_*`, `MYSQL_*`.

#### Chiffrement symétrique

- `openssl_encrypt(src: Path, key: str, *, remove_source=True) -> Path`: AES-256-CBC + PBKDF2 + salt. Retourne `.enc`, supprime source optionnel.
- `openssl_decrypt(src: Path, key: str) -> Path`: Déchiffre `.enc` → fichier plain.

#### Hachage

- `sha256_file(path: Path) -> str`: Hash hexadécimal du fichier.
- `sha256_write_sidecar(path: Path) -> str`: Écrit `path.sha256` avec `digest  basename`, retourne digest.

#### SCP

- `scp_transfer(src: str, dest: str, *, port=None, identity=None)`: Copie SCP unifiée (local→remote ou remote→local).

#### Compose / Conteneur

- `find_compose_exec() -> list[str]`: Détecte `podman compose` / `docker-compose` / `docker compose` → retourne `[prog, "compose", "exec", "-T"]` (ou `[prog, "exec", "-T"]`).
- `which_runtime() -> str`: Détecte `podman` ou `docker`.
- `container_cp(src: Path, container: str, dest: str)`: Copie fichier → conteneur (via runtime).
- `container_exec(container: str, cmd: str) -> tuple[int, str, str]`: Exécute `sh -c cmd` dans conteneur → `(rc, stdout, stderr)`.

---

### `backup_wp.py` (~130 lignes)

Orchestre la création d'archives WordPress. **Dépend uniquement de `functions.py` et stdlib.**

#### Fonctions privées (orchestration d'étapes)

- `_dump_local(db: DBConfig, sql_path: Path)`: Dump SQL local via `mysqldump --skip-ssl`.
- `_dump_compose(db: DBConfig, db_service: str, sql_path: Path, cwd: Path)`: Dump MySQL via composé.
- `_archive_wpcontent_local(wp_root: Path, dest: Path)`: Archive local `wp-content` en tarball.
- `_archive_wpcontent_compose(wp_service: str, dest: Path, cwd: Path)`: Archive `wp-content` via composé + tar.
- `_collect_sources(args, tmpdir, db, db_service, wp_service, cwd)`: Orchestre dump + archive + config.
- `_pack(tmpdir, package_path)`: Crée tarball final.

#### Interface principale

- `make_backup(args: argparse.Namespace) -> Path`: Entrée logique. Crée tmpdir tmpdir → load_env → parse_db_config → collect_sources → pack → sha256 → optionnel encrypt/scp → cleanup tmpdir.
- `parse_args()`: Expose `--compose-dir`, `--env-file`, `--out-dir`, `--db-service`, `--wp-service`, `--in-container`, `--wp-path`, `--encrypt-key`, `--ssh-*`.
- `main()`: Point d'entrée CLI. Logging → `make_backup()` → error handling.

---

### `restore_wp.py` (~110 lignes)

Restaure archives WordPress. **Dépend uniquement de `functions.py` et stdlib.**

#### Fonctions privées (étapes de restauration)

- `_extract(package: Path, tmpdir: Path)`: Décompresse tarball.
- `_import_sql(pfx, db_service, sql_file, db)`: Import SQL via `mysql --skip-ssl`.
- `_restore_content(pfx, wp_service, tar_path)`: Restaure `wp-content` via tar in conteneur.
- `_restore_config(pfx, wp_service, cfg_path)`: Restaure `wp-config.php`.
- `_fix_permissions(pfx, wp_service)`: Exécute `chown www-data:www-data /var/www/html` (warning non-blocking si échoue).

#### Interface principale de restauration

- `restore(args: argparse.Namespace)`: Entrée logique. Valide package → decrypt optionnel → extract → parse_db_config → import_sql → restore_* → fix_permissions.
- `parse_args()`: Expose `--package`, `--decrypt-key`, `--db-*-service`, `--db-*`, `--db-name`.
- `main()`: Point d'entrée CLI. Logging → `restore()` → error handling.

---

### `bkpctl.py` (~175 lignes)

CLI orchestrateur pour workflows backup/restore. **Dépend de `functions.py` + stdlib.**

#### Helpers internes

- `_run_backup_in_container()`: Container exec → backup → grep last archive → copy from container → retourne chemin remote.
- `_copy_from_container(remote)`: Copie archive depuis conteneur vers `./backups`.
- `_do_restore(archive, args)`: Exécute `restore_wp.py` en subprocess local depuis dossier `buyer`.

#### Sous-commandes (dispatch via argparse)

- `dry_run(args)`: Sauvegarde test → copie locale → SHA256 display.
- `run(args)`: Sauvegarde test → copie locale → SHA256 → optionnel encrypt → optionnel scp. Produce archive plain/enc + sidecar.
- `remote_copy(args)`: SCP archive local → destination distante.
- `remote_get(args)`: SCP archive distante → `./backups`.
- `restore_last(args)`: Cherche dernier `wp_backup_*.tar.gz` → `_do_restore`.
- `restore(args)`: Spécifie un fichier → `_do_restore`.

#### Point d'entrée

- `main()`: Argparse subparsers → dispatch → appel fonction correspondante.

---

## Graphe des dépendances

```txt
backup_wp.py ─┐
              ├──→ functions.py ──→ subprocess, pathlib, hashlib, shutil
restore_wp.py─┤                    (pas de dépendance externe)
              │
bkpctl.py ────┘
```

**Cyclic import: AUCUN.** Chaque script importe `functions` une seule fois au module level.

---

## Complexité cognitive

| Fichier | Max complexité | Stratégies |
| --- | --- | --- |
| `functions.py` | ~4-8 | Utilitaires simples: crypto basique, subprocess wrapper, env parser linéaire |
| `backup_wp.py` | ~12 | Délégation à `_dump_*`, `_archive_*`, `_collect_sources`, `_pack` |
| `restore_wp.py` | ~10 | Délégation à `_extract`, `_import_sql`, `_restore_*`, `_fix_permissions` |
| `bkpctl.py` | ~8 | Dispatch simple + helpers unitaires (`_run_backup_in_container`, `_copy_from_container`, `_do_restore`) |

---

## Tests manuels validés

### 1. Dry-run

```bash
cd buyer/tools
python3 bkpctl.py dry-run
# Valide: dump SQL ✓ archive wp-content ✓ archive produite ✓ SHA256 ✓
```

### 2. Run + validation

```bash
python3 bkpctl.py run
# Valide: package local ✓ sidecar SHA256 ✓
sha256sum -c ../backups/wp_backup_*.tar.gz.sha256
# Output: ... OK
```

### 3. Restauration après sinistre

```bash
# Nouveau conteneur WP
podman compose down -v
podman compose up -d --build

# Restauration
cd tools
python3 bkpctl.py restore --file wp_backup_20260410134953.tar.gz

# Valide: DB tables ✓ wp_posts=511 ✓ wp-content restored ✓ upload files ✓
podman exec wp_db mysql -N -uwpuser -pwppassword wordpress \
  -e "SELECT COUNT(*) FROM wp_posts;"
# Output: 511
```

---

## Gestion des erreurs

Tous les scripts capturent et formatent les erreurs:

```python
try:
    # exécution
except (RuntimeError, subprocess.CalledProcessError, OSError, tarfile.TarError) as e:
    LOG.exception("Échec: %s", e)
    sys.exit(2)
```

**Codes de sortie:**

- `0`: Succès
- `1`: Erreur argparse ou configuration
- `2`: Erreur d'exécution (subprocess, I/O, etc.)

---

## Principes de maintenabilité

1. **Aucune duplication**: Code commun centralisé dans `functions.py`.
2. **Complexité délimitée**: Chaque fonction ≤ 15.
3. **Nommage explicite**: Préfixe `_` pour fonctions privées, noms descriptifs.
4. **Logging structuré**: Tous les scripts utilisent `logging` module (pas de `print` exceptions).
5. **Gestion d'erreurs précise**: Exceptions spécifiques, pas de `except Exception`.
6. **Documentation inline**: Docstrings sur les fonctions publiques, comments sur les blocs complexes.

---

## Extension future

Pour ajouter une nouvelle commande `bkpctl.py`:

1. Ajouter la fonction dans `bkpctl.py` avec signature `def cmd_name(args):`.
2. Ajouter subparser dans `main()`: `sub.add_parser("cmd-name")`.
3. Ajouter mapping dans dispatch dict: `"cmd-name": cmd_name`.
4. Importer/appeler fonctions de `functions.py` au besoin.
5. Suivre les règles de complexité: déléguer les étapes à des helpers si besoin.
