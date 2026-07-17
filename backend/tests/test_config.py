from pydantic import ValidationError
import pytest

from backend.config import Environment, Settings


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql+psycopg://v2:password@localhost:5432/quoteops_v2",
        "test_database_url": "postgresql+psycopg://v2_test:password@localhost:5432/quoteops_v2_test",
        "auth_secret": "local-test-secret",
    }
    values.update(overrides)
    return Settings(**values)


def test_local_configuration_is_typed_and_secret_safe() -> None:
    configured = settings(cors_origins="http://localhost:5173,http://localhost:4173")

    assert configured.environment is Environment.LOCAL
    assert configured.cors_origins == ("http://localhost:5173", "http://localhost:4173")
    assert configured.safe_summary() == {
        "environment": "local",
        "database_configured": True,
        "docs_enabled": True,
        "openapi_enabled": True,
        "demo_enabled": False,
        "cors_origin_count": 2,
    }


def test_settings_reads_comma_separated_environment_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUOTEOPS_DATABASE_URL", "postgresql+psycopg://v2:password@localhost:5432/quoteops_v2")
    monkeypatch.setenv("QUOTEOPS_TEST_DATABASE_URL", "postgresql+psycopg://v2_test:password@localhost:5432/quoteops_v2_test")
    monkeypatch.setenv("QUOTEOPS_CORS_ORIGINS", "http://localhost:5173,http://localhost:4173")

    configured = Settings(_env_file=None)

    assert configured.cors_origins == ("http://localhost:5173", "http://localhost:4173")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"database_url": "sqlite:///not-allowed.db"}, "must target PostgreSQL"),
        ({"cors_origins": "*"}, "Wildcard CORS"),
        ({"test_database_url": "postgresql+psycopg://v2:password@localhost:5432/quoteops_v2"}, "must be distinct"),
    ],
)
def test_invalid_foundation_configuration_is_rejected(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        settings(**overrides)


def test_production_rejects_docs_demo_and_placeholder_secret() -> None:
    with pytest.raises(ValidationError, match="Demo mode"):
        settings(environment=Environment.PRODUCTION, demo_enabled=True, docs_enabled=False, openapi_enabled=False)

    with pytest.raises(ValidationError, match="docs and OpenAPI"):
        settings(environment=Environment.STAGING, docs_enabled=True, openapi_enabled=True)

    with pytest.raises(ValidationError, match="authentication secret"):
        settings(
            environment=Environment.PRODUCTION,
            docs_enabled=False,
            openapi_enabled=False,
            auth_secret="CHANGE_ME_WITH_A_LONG_RANDOM_VALUE",
        )

    with pytest.raises(ValidationError, match="authentication secret"):
        settings(
            environment=Environment.STAGING,
            docs_enabled=False,
            openapi_enabled=False,
            auth_secret=None,
        )
