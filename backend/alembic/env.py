from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from generate_admin.core.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

MIGRATION_SCHEME = "postgresql+psycopg://"
DATABASE_URL = (
    get_settings()
    .database.url.get_secret_value()
    .replace("postgresql+asyncpg://", MIGRATION_SCHEME, 1)
)


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        context.configure(connection=connection)

        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
