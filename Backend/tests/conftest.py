import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from app.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture
def fresh_database() -> Iterator[str]:
    admin_url = make_url(settings.database_url).set(database="postgres")
    admin = create_engine(
        admin_url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 3}
    )
    try:
        admin.connect().close()
    except Exception as error:
        admin.dispose()
        message = f"Postgres not reachable ({type(error).__name__})"
        if os.environ.get("DB_TESTS_REQUIRED") == "1":
            pytest.fail(message)
        pytest.skip(message)

    name = f"smartbin_test_{uuid.uuid4().hex[:8]}"
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield (
            make_url(settings.database_url).set(database=name).render_as_string(hide_password=False)
        )
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def migrated_engine(fresh_database: str) -> Iterator[Engine]:
    command.upgrade(alembic_config(fresh_database), "head")
    engine = create_engine(fresh_database)
    yield engine
    engine.dispose()
