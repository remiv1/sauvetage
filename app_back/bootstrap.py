"""Module de lancement principal du backend Sauvetage en remplacement du script shell."""

import os
import time
import subprocess
import socket
import urllib.parse


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
    Les mots de passe sont correctement encodés en URL pour éviter les problèmes avec les caractères
    spéciaux.
    return :
        - None. Les URLs sont définies dans les variables d'environnement.
    """
    print("[BOOTSTRAP] Construction des URLs de base de données")

    # PostgreSQL principal
    if "DATABASE_URL" not in os.environ:
        postgres_password_app_enc = urllib.parse.quote(
            os.environ['POSTGRES_PASSWORD_APP'], safe=''
        )
        os.environ["DATABASE_URL"] = (
            f"postgresql://{os.environ['POSTGRES_USER_APP']}:"
            f"{postgres_password_app_enc}@"
            f"{os.environ['POSTGRES_HOST']}:"
            f"{os.environ['POSTGRES_PORT']}/"
            f"{os.environ['POSTGRES_DB_MAIN']}"
        )

    # PostgreSQL sécurisé
    if "DATABASE_SECURE_URL" not in os.environ:
        postgres_password_secure_enc = urllib.parse.quote(
            os.environ['POSTGRES_PASSWORD_SECURE'], safe=''
        )
        os.environ["DATABASE_SECURE_URL"] = (
            f"postgresql://{os.environ['POSTGRES_USER_SECURE']}:"
            f"{postgres_password_secure_enc}@"
            f"{os.environ['POSTGRES_HOST']}:"
            f"{os.environ['POSTGRES_PORT']}/"
            f"{os.environ['POSTGRES_DB_USERS']}"
        )

    # MongoDB
    if "MONGODB_URL" not in os.environ:
        mongo_password_app_enc = urllib.parse.quote(
            os.environ['MONGO_PASSWORD_APP'], safe=''
        )
        os.environ["MONGODB_URL"] = (
            f"mongodb://{os.environ['MONGO_USER_APP']}:"
            f"{mongo_password_app_enc}@"
            f"{os.environ['MONGO_HOST']}:"
            f"{os.environ['MONGO_PORT']}/"
            f"{os.environ['MONGO_DB_LOGS']}?authSource={os.environ['MONGO_DB_LOGS']}"
        )


def configure_dilicom_cron() -> None:
    """
    Configure les tâches cron du conteneur pour l'envoi des référentiels et le fetch des retours.
    """
    cron_post = os.getenv("DILICOM_POST_CRON", "0 22 * * *")
    cron_fetch = os.getenv("DILICOM_FETCH_CRON", "0 6-12 * * *")
    cron_path = "/etc/cron.d/dilicom-cron"
    log_dir = "/var/log/dilicom"
    log_file = f"{log_dir}/dilicom-cron.log"
    api_url = os.getenv("DILICOM_API_URL", "http://localhost:8000/api/v1")
    fetch_archives = os.getenv("DILICOM_FETCH_ARCHIVES", "false")

    os.makedirs("/etc/cron.d", exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    with open(cron_path, "w", encoding="utf-8") as cron_file:
        cron_file.write("SHELL=/bin/bash\n")
        cron_file.write(
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
        )
        cron_file.write(f"DILICOM_API_URL={api_url}\n")
        cron_file.write(f"DILICOM_FETCH_ARCHIVES={fetch_archives}\n")
        cron_file.write(
            f"{cron_post} root /usr/local/bin/run-dilicom-cron.sh post >> {log_file} 2>&1\n"
        )
        cron_file.write(
            f"{cron_fetch} root /usr/local/bin/run-dilicom-cron.sh fetch >> {log_file} 2>&1\n"
        )
    os.chmod(cron_path, 0o640)


def configure_woocommerce_orders_cron() -> None:
    """Configure le cron des commandes WooCommerce entre 7h et 19h, toutes les 2h."""
    cron_path = "/etc/cron.d/woocommerce-orders-cron"
    log_dir = "/var/log/woocommerce"
    log_file = f"{log_dir}/orders-sync.log"
    api_url = os.getenv("API_URL", "http://localhost:8000/api/v1")
    cron_schedule = os.getenv("WOOCOMMERCE_ORDERS_CRON", "0 7-19/2 * * *")

    try:
        os.makedirs(log_dir, exist_ok=True)
    except PermissionError:
        log_dir = "/tmp/woocommerce"
        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/orders-sync.log"
        print(
            "[BOOTSTRAP] Permission refusée pour /var/log/woocommerce ;"
            "logs du cron WooCommerce redirigés vers /tmp/woocommerce"
        )

    try:
        with open(cron_path, "w", encoding="utf-8") as cron_file:
            cron_file.write("SHELL=/bin/bash\n")
            cron_file.write(
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
            )
            endpoint = f"{api_url}/woo-commerce/background/sync-orders"
            cron_file.write(
                f"{cron_schedule} root curl -fsS -X POST '{endpoint}' >> {log_file} 2>&1\n"
            )
        os.chmod(cron_path, 0o640)
    except PermissionError:
        print(
            "[BOOTSTRAP] Permission refusée pour /etc/cron.d ;"
            "cron WooCommerce non installé dans cet environnement."
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
    log_level = os.getenv("LOG_LEVEL", "info")
    print("[BOOTSTRAP] Démarrage de Gunicorn")
    subprocess.run([
        "gunicorn",
        "--bind", "0.0.0.0:8000",
        "--workers", "4",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--log-level", log_level,
        "app_back.main:app"
    ],
    check=True)


if __name__ == "__main__":
    print("[BOOTSTRAP] Initialisation du backend Sauvetage")

    build_env()
    wait_for("db-main", 5432)

    # Configurer les tâches cron du conteneur pour Dilicom et WooCommerce.
    print("[BOOTSTRAP] Configuration du cron Dilicom")
    configure_dilicom_cron()
    print("[BOOTSTRAP] Configuration du cron WooCommerce orders")
    configure_woocommerce_orders_cron()
    subprocess.Popen(["cron", "-f"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Lancer Gunicorn dans le process principal
    start_gunicorn()
