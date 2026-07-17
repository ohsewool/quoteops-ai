from io import StringIO

from alembic import command
from alembic.config import Config


def test_initial_migration_renders_postgresql_sql_without_connecting() -> None:
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url", "postgresql+psycopg://v2:password@localhost:5432/quoteops_v2"
    )
    output = StringIO()
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)

    sql = output.getvalue()
    assert "CREATE TABLE users" in sql
    assert "CREATE TABLE audit_events" in sql
    assert "CREATE TYPE user_role" in sql
    assert sql.count("CREATE TYPE user_role") == 1


def test_initial_migration_renders_reversible_downgrade_sql_without_connecting() -> None:
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url", "postgresql+psycopg://v2:password@localhost:5432/quoteops_v2"
    )
    output = StringIO()
    config.output_buffer = output

    command.downgrade(config, "0001_security_foundation:base", sql=True)

    sql = output.getvalue()
    assert "DROP TABLE audit_events" in sql
    assert "DROP TABLE users" in sql
    assert sql.count("DROP TYPE user_role") == 1
