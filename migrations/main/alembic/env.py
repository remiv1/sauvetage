"""env.py"""
import sys
import os
from os.path import abspath, dirname, join
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from dotenv import load_dotenv
from alembic import context

# Import main base model
env_path = join(abspath(join(dirname(__file__), '../../..')), 'databases', 'main', '.env.db_main')
load_dotenv(env_path)

# Ajout du chemin du projet au sys.path
sys.path.insert(0, dirname(dirname(dirname(abspath(__file__)))))

# Import main base model après avoir chargé les variables
from db_models import WorkingBase

# this is the Alembic Config object, which provides
config = context.config

# Construire l'URL SQLAlchemy avec les variables d'environnement
database_url = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER_APP')}:"
    f"{os.getenv('POSTGRES_PASSWORD_APP')}@"
    f"{os.getenv('POSTGRES_HOST')}:"
    f"{os.getenv('POSTGRES_PORT')}/"
    f"{os.getenv('POSTGRES_DB_MAIN')}"
)

# Définir l'URL de la base de données
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = WorkingBase.metadata

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
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        as_sql=True
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
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


# if context.is_offline_mode():
run_migrations_offline()
# else:
#     run_migrations_online()
