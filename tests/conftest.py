"""La configuration de pytest pour les tests unitaires du projet."""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv


def pytest_configure(config):
    """Hook pytest pour configurer avant les tests."""
    # Charger les variables d'environnement
    env_file = Path(__file__).parent.parent / "databases" / "logs" / ".env.db_logs"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    app_front_env = Path(__file__).parent.parent / "app_front" / ".env.flask"
    if app_front_env.exists():
        load_dotenv(app_front_env, override=True)

    # Configurer le port MongoDB pour les tests (docker-compose.test.yml: 27018:27017)
    os.environ["TEST_MONGO_PORT"] = "27018"

    # Patcher le MongoDBLogger pour éviter les erreurs de connexion à l'import
    mock_instance = MagicMock()
    mock_instance.log = MagicMock()

    patcher_mongo = patch("logs.logger.MongoDBLogger", MagicMock(return_value=mock_instance))
    patcher_get_logger = patch("logs.logger.get_logger", MagicMock(return_value=mock_instance))

    patcher_mongo.start()
    patcher_get_logger.start()

    # Marquer pour la cleanup
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )


pytest_plugins = [
    "tests.fixtures.db_fixture",
    "tests.fixtures.f_customers",
    "tests.fixtures.f_inventory",
    "tests.fixtures.f_objects",
    "tests.fixtures.f_orders",
    "tests.fixtures.f_suppliers",
    "tests.fixtures.f_stock",
    "tests.fixtures.f_users",
]
