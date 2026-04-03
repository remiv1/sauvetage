"""Module de gestion des migrations.

Utilise un advisory lock PostgreSQL pour garantir qu'un seul processus
exécute les migrations Alembic, même quand Gunicorn forke plusieurs workers
qui importent tous ce module simultanément.
"""
from datetime import datetime, timezone
from collections import namedtuple
import subprocess
from os import getenv
from urllib.parse import quote
import psycopg2
from db_models.objects.vat import VatRate
from app_back.db_connection import config as db_config


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


def run_startup_tasks(timeout: int = 300) -> None:
    """Exécute les migrations Alembic et l'initialisation des données de référence
    en utilisant un advisory lock PostgreSQL.

    Mécanisme :
    1. Ouvre une connexion à PostgreSQL avec le rôle de migration.
    2. Tente pg_try_advisory_lock(ADVISORY_LOCK_ID) — appel non-bloquant.
       - Si le lock est obtenu : ce worker est le premier arrivé.
         Il exécute les deux migrations (main puis users), puis ensure_vat,
         et libère le lock.
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

            # Initialisation des données de référence (TVA, etc.)
            ensure_vat(db_config.get_main_session())
            print("[migrations] Données de référence initialisées")

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
        ensure_vat(db_config.get_main_session())
    finally:
        if conn:
            conn.close()

def ensure_vat(session):
    """S'assure que les taux de TVA de base sont présents dans la base."""

    existing_rates = session.query(VatRate).filter(VatRate.rate.in_([2.1, 5.5, 10.0, 20.0])).all()
    existing_codes = {rate.code for rate in existing_rates}

    Rates = namedtuple("Rates", ["code", "rate", "label"])
    default_rates = [
        Rates(00, 2.1, "Taux super-réduit"),
        Rates(10, 5.5, "Taux réduit"),
        Rates(20, 10.0, "Taux intermédiaire"),
        Rates(30, 20.0, "Taux normal"),
    ]

    for rate in default_rates:
        if rate.code not in existing_codes:
            new_rate = VatRate(
                code=rate.code,
                rate=rate.rate,
                label=rate.label,
                date_start=datetime.now(timezone.utc),
            )
            session.add(new_rate)
            print(f"[migrations] Ajout du taux de TVA manquant : {new_rate}")
    try:
        session.commit()
    except db_config.SQLAlchemyError as e:
        session.rollback()
        print(f"[migrations] Erreur lors de l'ajout des taux de TVA : {e}")
