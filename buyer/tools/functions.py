#!/usr/bin/env python3
"""Fonctions utilitaires partagées pour les scripts de backup WordPress."""

from __future__ import annotations

import hashlib
import logging
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

LOG = logging.getLogger("wp_backup")

WP_ROOT = "/var/www/html"
CONFIG_PHP = "wp-config.php"


# ── Subprocess ────────────────────────────────────────────────────────────────

def run_to_file(cmd: list[str], out_path: Path, *, cwd: Path | None = None) -> None:
    """Redirige stdout de cmd vers out_path. Lève RuntimeError si échec."""
    with out_path.open("wb") as fh:
        p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.PIPE, cwd=cwd)
        _, err = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(f"{shlex.join(cmd)}: {err.decode(errors='replace')}")


def run_capture(cmd: list[str], *, cwd: Path | None = None) -> bytes:
    """Exécute cmd et retourne stdout. Lève RuntimeError si échec."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    out, err = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(f"{shlex.join(cmd)}: {err.decode(errors='replace')}")
    return out


def run_with_stdin(cmd: list[str], input_path: Path) -> None:
    """Exécute cmd avec input_path en stdin. Lève RuntimeError si échec."""
    with input_path.open("rb") as fh:
        p = subprocess.Popen(cmd, stdin=fh, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, err = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {err.decode(errors='replace')}")


# ── Env / DB ──────────────────────────────────────────────────────────────────

def load_env(env_path: Path) -> dict[str, str]:
    """Parse KEY=VALUE, ignore commentaires et lignes invalides."""
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


@dataclass
class DBConfig:
    """Paramètres de connexion MySQL."""
    user: str
    password: str
    name: str
    host: str
    port: int


def _env_first(env: dict[str, str], *keys: str) -> str | None:
    """Retourne la première valeur non-vide trouvée parmi keys dans env."""
    for k in keys:
        if env.get(k):
            return env[k]
    return None


def parse_db_config(
    env: dict[str, str],
    *,
    user: str | None = None,
    password: str | None = None,
    name: str | None = None,
) -> DBConfig:
    """Résout la configuration DB (surcharges > env > défauts)."""
    host_val = _env_first(env, "WORDPRESS_DB_HOST", "DB_HOST", "MYSQL_HOST") or "db:3306"
    if ":" in host_val:
        host, port_s = host_val.split(":", 1)
        try:
            port = int(port_s)
        except ValueError:
            port = 3306
    else:
        host, port = host_val, 3306

    return DBConfig(
        user=user or _env_first(env, "WORDPRESS_DB_USER", "DB_USER", "MYSQL_USER") or "root",
        password=password or _env_first(
            env, "WORDPRESS_DB_PASSWORD", "DB_PASSWORD", "MYSQL_PASSWORD"
            ) or "",
        name=name or _env_first(
            env, "WORDPRESS_DB_NAME", "DB_NAME", "MYSQL_DATABASE"
            ) or "wordpress",
        host=host,
        port=port,
    )


# ── Crypto ────────────────────────────────────────────────────────────────────

def openssl_encrypt(src: Path, key: str, *, remove_source: bool = True) -> Path:
    """Chiffre src AES-256-CBC. Retourne le .enc. Lève SystemExit si openssl absent."""
    if not shutil.which("openssl"):
        raise SystemExit("openssl introuvable")
    dst = src.with_suffix(src.suffix + ".enc")
    subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt",
         "-in", str(src), "-out", str(dst), "-pass", f"pass:{key}"],
        check=True,
    )
    if remove_source:
        src.unlink()
    return dst


def openssl_decrypt(src: Path, key: str) -> Path:
    """Déchiffre src AES-256-CBC. Retourne le fichier déchiffré."""
    if not shutil.which("openssl"):
        raise SystemExit("openssl introuvable")
    dst = src.with_suffix("")
    subprocess.run(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2",
         "-in", str(src), "-out", str(dst), "-pass", f"pass:{key}"],
        check=True,
    )
    return dst


# ── SHA256 ────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    """Retourne le digest SHA256 hex du fichier."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_write_sidecar(path: Path) -> str:
    """Écrit path.sha256 à côté de path. Retourne le digest."""
    digest = sha256_file(path)
    path.with_name(path.name + ".sha256").write_text(f"{digest}  {path.name}\n")
    LOG.info("SHA256: %s", digest)
    return digest


# ── SCP ───────────────────────────────────────────────────────────────────────

def scp_transfer(
    src: str,
    dest: str,
    *,
    port: int | None = None,
    identity: str | None = None,
) -> None:
    """Lance scp src→dest. Lève SystemExit si scp absent."""
    if not shutil.which("scp"):
        raise SystemExit("scp introuvable")
    cmd = ["scp"]
    if port:
        cmd += ["-P", str(port)]
    if identity:
        cmd += ["-i", identity]
    cmd += [src, dest]
    subprocess.run(cmd, check=True)


# ── Compose / conteneur ───────────────────────────────────────────────────────

def find_compose_exec() -> list[str]:
    """Retourne le préfixe compose exec -T (podman compose, docker-compose ou docker compose)."""
    if shutil.which("podman"):
        return ["podman", "compose", "exec", "-T"]
    if shutil.which("docker-compose"):
        return ["docker-compose", "exec", "-T"]
    if shutil.which("docker"):
        return ["docker", "compose", "exec", "-T"]
    raise SystemExit("podman/docker compose introuvable")


def which_runtime() -> str:
    """Retourne 'podman' ou 'docker', lève SystemExit si aucun n'est disponible."""
    for rt in ("podman", "docker"):
        if shutil.which(rt):
            return rt
    raise SystemExit("podman ou docker introuvable")


def container_cp(src: Path, container: str, dest: str) -> None:
    """Copie src dans container:dest."""
    subprocess.run([which_runtime(), "cp", str(src), f"{container}:{dest}"], check=True)


def container_exec(container: str, cmd: str) -> tuple[int, str, str]:
    """Exécute 'sh -c cmd' dans container. Retourne (rc, stdout, stderr)."""
    p = subprocess.run(
        [which_runtime(), "exec", container, "sh", "-c", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return p.returncode, p.stdout.decode(), p.stderr.decode()
