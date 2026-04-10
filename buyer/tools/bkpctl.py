#!/usr/bin/env python3
"""CLI: dry-run | run | remote-copy | remote-get | restore-last | restore.

Usage:
  bkpctl.py dry-run
  bkpctl.py run [--encrypt-key KEY] [--remote user@host:/path]
  bkpctl.py remote-copy --file NAME --dest user@host:/path
  bkpctl.py remote-get  --remote user@host:/path --file NAME
  bkpctl.py restore-last [--decrypt-key KEY]
  bkpctl.py restore --file NAME [--decrypt-key KEY]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from functions import (
    container_cp, container_exec, which_runtime,
    openssl_encrypt, scp_transfer, sha256_write_sidecar,
)

BACKUP_DIR = Path(__file__).resolve().parents[1] / "backups"
CONTAINER = "wp_backup"
BACKUP_SCRIPT = "/opt/backup/backup_wp.py"
RESTORE_SCRIPT = "/opt/backup/restore_wp.py"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env.wordpress"


def _run_backup_in_container() -> str:
    container_cp(ENV_FILE, CONTAINER, "/tmp/.env.wordpress")
    cmd = (
        f"python3 {BACKUP_SCRIPT} --in-container "
        "--env-file /tmp/.env.wordpress --out-dir /tmp --wp-path /var/www/html"
    )
    rc, _, err = container_exec(CONTAINER, cmd)
    if rc != 0:
        print(err, file=sys.stderr)
        raise SystemExit(rc)
    rc2, out, _ = container_exec(CONTAINER, "ls -1t /tmp/wp_backup_*.tar.gz 2>/dev/null | head -n1")
    path = out.strip()
    if rc2 != 0 or not path:
        raise SystemExit("Aucune archive trouvée dans le conteneur")
    return path


def _copy_from_container(remote: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    local = BACKUP_DIR / Path(remote).name
    subprocess.run([which_runtime(), "cp", f"{CONTAINER}:{remote}", str(local)], check=True)
    return local


def _do_restore(archive: Path, args: argparse.Namespace) -> None:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "restore_wp.py"),
        "--package",
        str(archive),
    ]
    if args.decrypt_key:
        cmd += ["--decrypt-key", args.decrypt_key]
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[1])


def dry_run(_: argparse.Namespace) -> None:
    """Effectue une simulation de sauvegarde sans modification."""
    remote = _run_backup_in_container()
    local = _copy_from_container(remote)
    digest = sha256_write_sidecar(local)
    print(f"Archive: {local}\nSHA256:  {digest}")


def run(args: argparse.Namespace) -> None:
    """Effectue une sauvegarde complète."""
    remote = _run_backup_in_container()
    local = _copy_from_container(remote)
    digest = sha256_write_sidecar(local)
    print(f"Archive: {local}\nSHA256 (pré-chiffrement): {digest}")

    if args.encrypt_key:
        local = openssl_encrypt(local, args.encrypt_key, remove_source=args.remove_plain)
        print("Chiffré:", local)

    if args.remote:
        dest = args.remote.rstrip("/") + "/" + local.name
        scp_transfer(str(local), dest, port=args.port, identity=args.ssh_key)


def remote_copy(args: argparse.Namespace) -> None:
    """Copie une archive locale vers une destination distante."""
    src = BACKUP_DIR / args.file
    if not src.exists():
        raise SystemExit(f"Introuvable: {src}")
    dest = args.dest.rstrip("/") + "/" + src.name
    scp_transfer(str(src), dest, port=args.port, identity=args.ssh_key)


def remote_get(args: argparse.Namespace) -> None:
    """Récupère une archive distante vers le répertoire local."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    remote = args.remote.rstrip("/") + "/" + args.file
    scp_transfer(remote, str(BACKUP_DIR / args.file), port=args.port, identity=args.ssh_key)


def restore_last(args: argparse.Namespace) -> None:
    """Restaure la dernière archive locale."""
    files = sorted(BACKUP_DIR.glob("wp_backup_*.tar.gz"))
    if not files:
        raise SystemExit("Aucune archive locale")
    _do_restore(files[-1], args)


def restore(args: argparse.Namespace) -> None:
    """Restaure une archive spécifique."""
    path = BACKUP_DIR / args.file
    if not path.exists():
        raise SystemExit(f"Introuvable: {path}")
    _do_restore(path, args)


def _add_scp_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--port", type=int)
    p.add_argument("--ssh-key")


def main() -> None:
    """Point d'entrée principal du script."""
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("dry-run")

    rp = sub.add_parser("run")
    rp.add_argument("--encrypt-key")
    rp.add_argument("--remote")
    rp.add_argument("--remove-plain", action="store_true")
    _add_scp_args(rp)

    cp = sub.add_parser("remote-copy")
    cp.add_argument("--file", required=True)
    cp.add_argument("--dest", required=True)
    _add_scp_args(cp)

    gp = sub.add_parser("remote-get")
    gp.add_argument("--remote", required=True)
    gp.add_argument("--file", required=True)
    _add_scp_args(gp)

    rl = sub.add_parser("restore-last")
    rl.add_argument("--decrypt-key")

    res = sub.add_parser("restore")
    res.add_argument("--file", required=True)
    res.add_argument("--decrypt-key")

    args = p.parse_args()
    dispatch = {
        "dry-run": dry_run, "run": run,
        "remote-copy": remote_copy, "remote-get": remote_get,
        "restore-last": restore_last, "restore": restore,
    }
    fn = dispatch.get(args.cmd)
    if fn is None:
        p.print_help()
    else:
        fn(args)


if __name__ == "__main__":
    main()
