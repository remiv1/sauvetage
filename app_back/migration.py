"""Module de gestion des migrations.

Utilise un advisory lock PostgreSQL pour garantir qu'un seul processus
exécute les migrations Alembic, même quand Gunicorn forke plusieurs workers
qui importent tous ce module simultanément.
"""

import subprocess
from os import getenv
from urllib.parse import quote

import psycopg2

# Identifiant arbitraire pour le verrou consultatif PostgreSQL.
# Tous les workers utilisant le même ID partagent le même verrou.
ADVISORY_LOCK_ID = 584210  # identifiant unique pour les migrations Sauvetage

MAIN = {
    "index": "main",
    "command": [
        "alembic",
        "-c",
        getenv("ALEMBIC_CONFIG_MAIN", "/app/main/alembic.ini"),
        "upgrade",
        "head",
    ],
}
SECURE = {
    "index": "secure",
    "command": [
        "alembic",
        "-c",
        getenv("ALEMBIC_CONFIG_SECURE", "/app/users/alembic.ini"),
        "upgrade",
        "head",
    ],
}


def _build_dsn() -> str:
    """Construit la DSN de connexion pour le rôle de migration."""
    user = quote(getenv("POSTGRES_USER_MIGR", "migr"), safe="")
    password = quote(getenv("POSTGRES_PASSWORD_MIGR", ""), safe="")
    host = getenv("POSTGRES_HOST", "db-main")
    port = getenv("POSTGRES_PORT", "5432")
    db = getenv("POSTGRES_DB_MAIN", "sauvetage_main")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _run_alembic(cmd: list, timeout: int = 300):
    """Exécute une commande Alembic dans un sous-processus."""
    try:
        print(f"[migrations] Running: {' '.join(cmd)}")
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        if proc.stdout:
            print(proc.stdout)
        if proc.returncode != 0 and proc.stderr:
            print(f"[migrations] stderr: {proc.stderr}")
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.SubprocessError as e:
        print(f"[migrations] Subprocess error: {e}")
        return 255, "", str(e)


def run_migrations_with_lock(timeout: int = 300) -> None:
    """Exécute toutes les migrations Alembic en utilisant un advisory lock PostgreSQL.

    Mécanisme :
    1. Ouvre une connexion à PostgreSQL avec le rôle de migration.
    2. Tente pg_try_advisory_lock(ADVISORY_LOCK_ID) — appel non-bloquant.
       - Si le lock est obtenu : ce worker est le premier arrivé.
         Il exécute les deux migrations (main puis users) et libère le lock.
       - Si le lock n'est PAS obtenu : un autre worker migre déjà.
         On attend avec pg_advisory_lock() (bloquant) que l'autre finisse,
         puis on continue sans migrer.
    3. Ferme la connexion (et libère automatiquement tout lock restant).
    """
    dsn = _build_dsn()
    conn = None
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = True  # les advisory locks exigent autocommit
        cur = conn.cursor()

        # Tentative non-bloquante
        cur.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_LOCK_ID,))
        got_lock = cur.fetchone()[0]  # type: ignore

        if got_lock:
            # Ce worker est le premier — il exécute les migrations
            print("[migrations] Advisory lock obtenu — lancement des migrations")
            ret_main = _run_alembic(MAIN["command"], timeout=timeout)
            print(f"[migrations] Migration main terminée (code={ret_main[0]})")

            ret_users = _run_alembic(SECURE["command"], timeout=timeout)
            print(f"[migrations] Migration users terminée (code={ret_users[0]})")

            # Libération explicite du lock
            cur.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_ID,))
            print("[migrations] Advisory lock libéré")
        else:
            # Un autre worker migre — on attend qu'il finisse
            print("[migrations] Un autre worker exécute les migrations — attente...")
            cur.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_ID,))
            # Le lock est obtenu = l'autre worker a fini et relâché
            cur.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_ID,))
            print("[migrations] Migrations terminées par un autre worker — on continue")

        cur.close()
    except psycopg2.Error as e:
        print(f"[migrations] Erreur PostgreSQL lors du verrouillage : {e}")
        # Fallback : on tente quand même la migration (mieux que ne rien faire)
        print("[migrations] Fallback — tentative de migration sans verrou")
        _run_alembic(MAIN["command"], timeout=timeout)
        _run_alembic(SECURE["command"], timeout=timeout)
    finally:
        if conn:
            conn.close()
