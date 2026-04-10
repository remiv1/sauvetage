#!/usr/bin/env python3
"""Sauvegarde WordPress conteneurisé.

Usage: python3 backup_wp.py --out-dir ./backups [--env-file .env.wordpress]
                            [--encrypt-key KEY] [--ssh-dest user@host:/path]
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from functions import (
    CONFIG_PHP, WP_ROOT,
    DBConfig, load_env, parse_db_config,
    run_to_file, run_capture,
    openssl_encrypt, scp_transfer,
    sha256_write_sidecar, find_compose_exec,
)

LOG = logging.getLogger("backup_wp")



def _dump_local(db: DBConfig, sql_path: Path) -> None:
    if not shutil.which("mysqldump"):
        raise SystemExit("mysqldump introuvable")
    run_to_file([
        "mysqldump", "-h", db.host, "-P", str(db.port),
        f"-u{db.user}", f"-p{db.password}", db.name,
        "--skip-ssl",
        "--single-transaction", "--quick",
    ], sql_path)


def _dump_compose(db: DBConfig, db_service: str, sql_path: Path, cwd: Path) -> None:
    run_to_file(
        find_compose_exec() + [
            db_service, "mysqldump",
            f"-u{db.user}", f"-p{db.password}", db.name,
            "--skip-ssl",
            "--single-transaction", "--quick",
        ],
        sql_path, cwd=cwd,
    )


def _archive_wpcontent_local(wp_root: Path, dest: Path) -> None:
    src = wp_root / "wp-content"
    if not src.exists():
        LOG.warning("wp-content introuvable dans %s", wp_root)
        return
    with tarfile.open(dest, "w:gz") as tf:
        tf.add(src, arcname="wp-content")


def _archive_wpcontent_compose(wp_service: str, dest: Path, cwd: Path) -> None:
    run_to_file(
        find_compose_exec() + [wp_service, "tar", "czf", "-", "-C", WP_ROOT, "wp-content"],
        dest, cwd=cwd,
    )


def _collect_sources(
    args: argparse.Namespace,
    tmpdir: Path,
    db: DBConfig,
    db_service: str,
    wp_service: str,
    cwd: Path,
) -> None:
    sql_path = tmpdir / "wp_db.sql"
    wpcontent_tar = tmpdir / "wp-content.tar.gz"
    wpconfig_dst = tmpdir / CONFIG_PHP
    wp_root = Path(args.wp_path)

    if args.in_container:
        _dump_local(db, sql_path)
        _archive_wpcontent_local(wp_root, wpcontent_tar)
        src_cfg = wp_root / CONFIG_PHP
        if src_cfg.exists():
            wpconfig_dst.write_bytes(src_cfg.read_bytes())
        else:
            LOG.warning("wp-config.php introuvable dans %s", wp_root)
    else:
        _dump_compose(db, db_service, sql_path, cwd)
        _archive_wpcontent_compose(wp_service, wpcontent_tar, cwd)
        data = run_capture(
            find_compose_exec() + [wp_service, "cat", f"{WP_ROOT}/{CONFIG_PHP}"],
            cwd=cwd,
        )
        wpconfig_dst.write_bytes(data)


def _pack(tmpdir: Path, package_path: Path) -> None:
    with tarfile.open(package_path, "w:gz") as tf:
        for p in sorted(tmpdir.iterdir()):
            tf.add(p, arcname=p.name)


def make_backup(args: argparse.Namespace) -> Path:
    """Crée une sauvegarde WordPress."""
    cwd = Path(args.compose_dir).resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    env_file = Path(args.env_file) if args.env_file else cwd / ".env.wordpress"
    env = load_env(env_file)
    db = parse_db_config(env)
    db_service = args.db_service or db.host
    wp_service = args.wp_service or "wordpress"

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    tmpdir = Path(tempfile.mkdtemp(prefix=f"wp_backup_{ts}_"))
    try:
        _collect_sources(args, tmpdir, db, db_service, wp_service, cwd)
        for extra in (env_file, cwd / "docker-compose.yml"):
            if extra.exists():
                shutil.copy2(extra, tmpdir / extra.name)

        package_path = out_dir / f"wp_backup_{ts}.tar.gz"
        _pack(tmpdir, package_path)
        sha256_write_sidecar(package_path)

        if args.encrypt_key:
            package_path = openssl_encrypt(package_path, args.encrypt_key)
        if args.ssh_dest:
            scp_transfer(str(package_path), args.ssh_dest, port=args.ssh_port)

        LOG.info("Sauvegarde terminée: %s", package_path)
        return package_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    """Analyse les arguments de la ligne de commande."""
    p = argparse.ArgumentParser(description="Sauvegarde WordPress conteneurisé")
    p.add_argument("--compose-dir", default=".", help="Dossier contenant docker-compose.yml")
    p.add_argument("--env-file", default=".env.wordpress", help="Fichier .env wordpress")
    p.add_argument("--out-dir", default="./backups", help="Répertoire de sortie")
    p.add_argument("--db-service", help="Nom du service DB")
    p.add_argument("--wp-service", help="Nom du service WordPress")
    p.add_argument("--in-container", action="store_true",
                   help="Mode conteneur (mysqldump local + fichiers montés)")
    p.add_argument("--wp-path", default=WP_ROOT, help="Racine WordPress (mode conteneur)")
    p.add_argument("--encrypt-key", help="Clé openssl AES-256-CBC")
    p.add_argument("--ssh-dest", dest="ssh_dest", help="Copie SSH (user@host:/path)")
    p.add_argument("--ssh-port", type=int)
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
        package = make_backup(args)
        print("Sauvegarde créée:", package)
    except (RuntimeError, subprocess.CalledProcessError, OSError, tarfile.TarError) as e:
        LOG.exception("Échec: %s", e)
        sys.exit(2)


if __name__ == "__main__":
    main()
