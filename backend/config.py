import os
from dataclasses import dataclass


DEFAULT_DATABASE_URL = "sqlite:///./quoteops.db"


@dataclass(frozen=True)
class Settings:
    database_url: str
    allowed_origins: list[str]
    openai_configured: bool
    demo_tools_enabled: bool

    @property
    def database_type(self) -> str:
        if self.database_url.startswith("sqlite"):
            return "sqlite"
        if self.database_url.startswith("postgresql"):
            return "postgresql"
        return "other"


def get_settings() -> Settings:
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        allowed_origins=[
            origin.strip() for origin in allowed_origins.split(",") if origin.strip()
        ],
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        demo_tools_enabled=os.getenv("DEMO_TOOLS_ENABLED", "false").lower() == "true",
    )
