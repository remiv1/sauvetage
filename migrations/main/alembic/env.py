"""env.py"""
import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from dotenv import load_dotenv
from alembic import context

# Import des variables d'environnement depuis le fichier .env.migr
load_dotenv('/app/.env.migr')

# Ajout du chemin du projet au sys.path
sys.path.insert(0, '/app')

# Import main base model après avoir chargé les variables
from db_models import WorkingBase
from db_models.objects.customers import *
from db_models.objects.orders import *
from db_models.objects.invoices import *
from db_models.objects.shipments import *
from db_models.objects.suppliers import *
from db_models.objects.objects import *
from db_models.objects.inventory import *

# this is the Alembic Config object, which provides
config = context.config

# Construire l'URL SQLAlchemy avec les variables d'environnement
database_url = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER_MIGR')}:"
    f"{os.getenv('POSTGRES_PASSWORD_MIGR')}@"
    f"{os.getenv('POSTGRES_HOST')}:"
    f"{os.getenv('POSTGRES_PORT')}/"
    f"{os.getenv('POSTGRES_DB_MAIN')}"
)

# Définir l'URL de la base de données
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = WorkingBase.metadata

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
    context.configure(
        url=url,
        target_metadata=target_metadata,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="migr_main"
    )

    with context.begin_transaction():
        context.run_migrations()


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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="migr_main"
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
