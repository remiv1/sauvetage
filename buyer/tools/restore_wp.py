#!/usr/bin/env python3
"""Restauration d'une archive créée par backup_wp.py.

Usage: python3 restore_wp.py --package /path/to/wp_backup.tar.gz [--decrypt-key KEY]
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from functions import (
    DBConfig, load_env, parse_db_config,
    run_with_stdin, openssl_decrypt, find_compose_exec,
)

LOG = logging.getLogger("restore_wp")


def _extract(package: Path, tmpdir: Path) -> None:
    with tarfile.open(package, "r:gz") as tf:
        tf.extractall(path=tmpdir)


def _import_sql(pfx: list[str], db_service: str, sql_file: Path, db: DBConfig) -> None:
    run_with_stdin(
        pfx + [db_service, "mysql", "--skip-ssl", f"-u{db.user}", f"-p{db.password}", db.name],
        sql_file,
    )


def _restore_content(pfx: list[str], wp_service: str, tar_path: Path) -> None:
    if not tar_path.exists():
        return
    run_with_stdin(pfx + [wp_service, "tar", "xzf", "-", "-C", "/var/www/html"], tar_path)


def _restore_config(pfx: list[str], wp_service: str, cfg_path: Path) -> None:
    if not cfg_path.exists():
        return
    run_with_stdin(
        pfx + [wp_service, "sh", "-c", "cat > /var/www/html/wp-config.php"],
        cfg_path,
    )


def _fix_permissions(pfx: list[str], wp_service: str) -> None:
    try:
        subprocess.run(
            pfx + [wp_service, "chown", "-R", "www-data:www-data", "/var/www/html"],
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as e:
        LOG.warning("chown non-fatal: %s", e)


def restore(args: argparse.Namespace) -> None:
    """Restaure une archive backup_wp.py."""
    package = Path(args.package).expanduser().resolve()
    if not package.exists():
        raise SystemExit(f"Package introuvable: {package}")
    if package.suffix == ".enc":
        if not args.decrypt_key:
            raise SystemExit("Archive chiffrée: --decrypt-key requis")
        package = openssl_decrypt(package, args.decrypt_key)

    tmpdir = Path(tempfile.mkdtemp(prefix="wp_restore_"))
    try:
        _extract(package, tmpdir)
        sql_file = tmpdir / "wp_db.sql"
        if not sql_file.exists():
            raise SystemExit("wp_db.sql introuvable dans l'archive")

        db = parse_db_config(
            load_env(tmpdir / ".env.wordpress"),
            user=args.db_user,
            password=getattr(args, "db_pass", None),
            name=args.db_name,
        )
        pfx = find_compose_exec()
        db_service = args.db_service or "db"
        wp_service = args.wp_service or "wordpress"
        _import_sql(pfx, db_service, sql_file, db)
        _restore_content(pfx, wp_service, tmpdir / "wp-content.tar.gz")
        _restore_config(pfx, wp_service, tmpdir / "wp-config.php")
        _fix_permissions(pfx, wp_service)
        LOG.info("Restauration terminée")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    p = argparse.ArgumentParser(description="Restaure une archive backup_wp.py")
    p.add_argument("--package", required=True, help="Archive .tar.gz ou .tar.gz.enc")
    p.add_argument("--decrypt-key", help="Clé de déchiffrement")
    p.add_argument("--db-service", help="Service DB (défaut: db)")
    p.add_argument("--wp-service", help="Service WP (défaut: wordpress)")
    p.add_argument("--db-user", help="User MySQL (override .env)")
    p.add_argument("--db-pass", help="Password MySQL (override .env)")
    p.add_argument("--db-name", help="Nom de la base (override .env)")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def main() -> None:
    """Point d'entrée principal du script."""
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    try:
        restore(args)
    except (RuntimeError, subprocess.CalledProcessError, OSError, tarfile.TarError) as e:
        LOG.exception("Échec: %s", e)
        sys.exit(2)


if __name__ == "__main__":
    main()
