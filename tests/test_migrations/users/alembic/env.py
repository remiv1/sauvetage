# Auto-generated env.py for tests
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
# project root injected by test script
project_root = os.getenv("TEST_PROJECT_ROOT", "/home/remi-verschuur/Projets/sauvetage")
sys.path.insert(0, project_root)
"""env.py"""

import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Ajout du chemin du projet au sys.path

# Import main base model après avoir chargé les variables
from db_models import SecureBase  # pylint: disable=wrong-import-position
from db_models.objects.users import *  # pylint: disable=wrong-import-position,wildcard-import,unused-wildcard-import # type: ignore

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config  # pylint: disable=no-member

# Construire l'URL SQLAlchemy avec les variables d'environnement
database_url = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER_MIGR')}:"
    f"{os.getenv('POSTGRES_PASSWORD_MIGR')}@"
    f"{os.getenv('POSTGRES_HOST')}:"
    f"{os.getenv('POSTGRES_PORT')}/"
    f"{os.getenv('POSTGRES_DB_USERS')}"
)

# Définir l'URL de la base de données
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = SecureBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(  # pylint: disable=no-member
        url=url,
        target_metadata=target_metadata,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="migr_users",
    )

    with context.begin_transaction():  # pylint: disable=no-member
        context.run_migrations()  # pylint: disable=no-member


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(  # pylint: disable=no-member
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="migr_users",
            version_table="alembic_version",
        )

        with context.begin_transaction():  # pylint: disable=no-member
            context.run_migrations()  # pylint: disable=no-member


if context.is_offline_mode():  # pylint: disable=no-member
    run_migrations_offline()
else:
    run_migrations_online()
