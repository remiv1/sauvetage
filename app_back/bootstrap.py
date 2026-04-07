"""Module de lancement principal du backend Sauvetage en remplacement du script shell."""

import os
import time
import threading
import subprocess
import socket
from app_back.scheduler.dilicom_scheduler import start_dilicom_scheduler


def wait_for(host: str, port: int, timeout: int = 60) -> bool:
    """
    Attends que le service à l'adresse host:port soit disponible.
    Cette fonction tente de se connecter au service à intervalles réguliers jusqu'à ce qu'il soit
    disponible ou que le timeout soit atteint.
    param :
        - host: L'adresse du service à vérifier (ex: "db-main").
        - port: Le port du service à vérifier (ex: 5432).
        - timeout: Le temps maximum en secondes à attendre.
    return :
        - True si le service devient disponible avant le timeout, sinon une exception est levée.
    raises :
        - RuntimeError si le service n'est pas disponible après le timeout.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"[BOOTSTRAP] {host}:{port} est disponible")
                return True
        except OSError:
            print(f"[BOOTSTRAP] Attente de {host}:{port}...")
            time.sleep(3)
    raise RuntimeError(f"[BOOTSTRAP] Timeout: {host}:{port} indisponible")


def build_env():
    """
    Construit les URLs de connexion aux bases de données à partir des variables d'environnement
    individuelles. Si les URLs complètes ne sont pas déjà définies, elles sont construites
    automatiquement en utilisant les variables d'environnement spécifiques à chaque base de données.
    return :
        - None. Les URLs sont définies dans les variables d'environnement.
    """
    print("[BOOTSTRAP] Construction des URLs de base de données")

    # PostgreSQL principal
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = (
            f"postgresql://{os.environ['POSTGRES_USER_APP']}:"
            f"{os.environ['POSTGRES_PASSWORD_APP']}@"
            f"{os.environ['POSTGRES_HOST']}:"
            f"{os.environ['POSTGRES_PORT']}/"
            f"{os.environ['POSTGRES_DB_MAIN']}"
        )

    # PostgreSQL sécurisé
    if "DATABASE_SECURE_URL" not in os.environ:
        os.environ["DATABASE_SECURE_URL"] = (
            f"postgresql://{os.environ['POSTGRES_USER_SECURE']}:"
            f"{os.environ['POSTGRES_PASSWORD_SECURE']}@"
            f"{os.environ['POSTGRES_HOST']}:"
            f"{os.environ['POSTGRES_PORT']}/"
            f"{os.environ['POSTGRES_DB_USERS']}"
        )

    # MongoDB
    if "MONGODB_URL" not in os.environ:
        os.environ["MONGODB_URL"] = (
            f"mongodb://{os.environ['MONGO_USER_APP']}:"
            f"{os.environ['MONGO_PASSWORD_APP']}@"
            f"{os.environ['MONGO_HOST']}:"
            f"{os.environ['MONGO_PORT']}/"
            f"{os.environ['MONGO_DB_LOGS']}"
        )


def start_gunicorn():
    """
    Démarre le serveur Gunicorn pour héberger l'application FastAPI.
    Cette fonction utilise subprocess pour lancer Gunicorn avec les paramètres appropriés
    pour lier le serveur à toutes les interfaces sur le port 8000, avec 4 workers utilisant
    UvicornWorker pour la compatibilité avec FastAPI.
    return :
        - None. Gunicorn est lancé en tant que processus séparé.
    """
    print("[BOOTSTRAP] Démarrage de Gunicorn")
    subprocess.run([
        "gunicorn",
        "--bind", "0.0.0.0:8000",
        "--workers", "4",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--log-level", "info",
        "app_back.main:app"
    ],
    check=True)


if __name__ == "__main__":
    print("[BOOTSTRAP] Initialisation du backend Sauvetage")

    build_env()
    wait_for("db-main", 5432)

    # Lancer le scheduler dans un thread
    print("[BOOTSTRAP] Lancement du scheduler Dilicom")
    threading.Thread(target=start_dilicom_scheduler, daemon=True).start()

    # Lancer Gunicorn dans le process principal
    start_gunicorn()
