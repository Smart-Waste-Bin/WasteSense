from alembic import command
from sqlalchemy import create_engine, inspect

from app.models import Base
from tests.conftest import alembic_config


def table_names(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"spatial_ref_sys", "alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_downgrade_upgrade(fresh_database):
    config = alembic_config(fresh_database)

    command.upgrade(config, "head")
    assert table_names(fresh_database) == set(Base.metadata.tables)

    command.downgrade(config, "base")
    assert table_names(fresh_database) == set()

    command.upgrade(config, "head")
    assert table_names(fresh_database) == set(Base.metadata.tables)
