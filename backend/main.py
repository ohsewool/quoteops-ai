from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import get_settings
from backend.db import get_connection, initialize_database
from backend.routers.agent_api import router as agent_api_router
from backend.routers.approval_api import router as approval_api_router
from backend.routers.audit_api import router as audit_api_router
from backend.routers.auth_api import router as auth_api_router
from backend.routers.bulk_api import router as bulk_api_router
from backend.routers.candidate_api import router as candidate_api_router
from backend.routers.dashboard_api import router as dashboard_api_router
from backend.routers.market_api import router as market_api_router
from backend.routers.price_comparison_api import router as price_comparison_api_router
from backend.routers.pricing_api import router as pricing_api_router
from backend.routers.quote_api import router as quote_api_router
from backend.routers.quote_request_api import router as quote_request_api_router
from backend.routers.read_api import router as read_api_router
from backend.routers.report_api import router as report_api_router
from backend.routers.scenario_comparison_api import router as scenario_comparison_api_router
from backend.routers.simulation_api import router as simulation_api_router
from backend.routers.strategy_template_api import router as strategy_template_api_router
from backend.routers.workflow_api import router as workflow_api_router

APP_VERSION = "0.1.0"
REQUIRED_TABLES = [
    "products",
    "competitors",
    "cost_profiles",
    "price_tables",
    "admin_users",
    "audit_logs",
    "agent_jobs",
]

logger = logging.getLogger("quoteops")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


def parse_allowed_origins() -> list[str]:
    return get_settings().allowed_origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    database_type = get_database_type()
    app.state.started_at = datetime.now(timezone.utc).isoformat()
    app.state.ready = False
    logger.info("QuoteOps AI startup begins")
    logger.info("Application environment: %s", settings.safe_app_env_label)
    logger.info("Database type selected: %s", database_type)
    logger.info("CORS origins loaded: %s", ",".join(settings.allowed_origins))
    logger.info("OpenAI explanation mode: %s", "openai" if settings.openai_api_key else "fallback")
    initialize_database()
    app.state.ready = True
    logger.info("Database schema initialization and seed checks completed")
    logger.info("QuoteOps AI startup completed")
    yield


app = FastAPI(
    title="QuoteOps AI API",
    description="AI-assisted pricing and quoting operations backend.",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(read_api_router)
app.include_router(auth_api_router)
app.include_router(quote_api_router)
app.include_router(quote_request_api_router)
app.include_router(market_api_router)
app.include_router(price_comparison_api_router)
app.include_router(pricing_api_router)
app.include_router(candidate_api_router)
app.include_router(dashboard_api_router)
app.include_router(bulk_api_router)
app.include_router(simulation_api_router)
app.include_router(scenario_comparison_api_router)
app.include_router(report_api_router)
app.include_router(strategy_template_api_router)
app.include_router(agent_api_router)
app.include_router(approval_api_router)
app.include_router(audit_api_router)
app.include_router(workflow_api_router)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    llm_enabled: bool


class DatabaseHealthResponse(BaseModel):
    status: str
    database_type: str
    connectivity: str
    error: str | None = None


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


class SystemStatusResponse(BaseModel):
    status: str
    service: str
    version: str
    generated_at: str
    started_at: str | None
    backend: dict[str, object]
    database: dict[str, object]
    configuration: dict[str, bool]
    features: dict[str, bool]


def get_database_type() -> str:
    settings = get_settings()
    if settings.is_sqlite:
        return "sqlite"
    if settings.is_postgres:
        return "postgresql"
    return "unsupported"


def safe_error_message(exc: Exception) -> str:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    lowered = message.lower()
    if any(term in lowered for term in ("password", "token", "secret", "postgresql://", "sqlite:///")):
        return f"{exc.__class__.__name__}: database configuration error"
    return f"{exc.__class__.__name__}: {message}"[:240]


def check_database() -> DatabaseHealthResponse:
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return DatabaseHealthResponse(
            status="ok",
            database_type=get_database_type(),
            connectivity="ok",
        )
    except Exception as exc:
        return DatabaseHealthResponse(
            status="error",
            database_type=get_database_type(),
            connectivity="error",
            error=safe_error_message(exc),
        )


def check_schema() -> str:
    try:
        with get_connection() as connection:
            for table_name in REQUIRED_TABLES:
                connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
        return "ok"
    except Exception:
        return "error"


def check_seed_data() -> str:
    try:
        with get_connection() as connection:
            product_count = connection.execute("SELECT COUNT(*) AS count FROM products").fetchone()[0]
            admin_count = connection.execute("SELECT COUNT(*) AS count FROM admin_users").fetchone()[0]
        if product_count >= 2 and admin_count >= 1:
            return "ok"
        return "missing"
    except Exception:
        return "error"


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="QuoteOps AI",
        version=APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        llm_enabled=settings.llm_enabled,
    )


@app.get("/api/health/db", response_model=DatabaseHealthResponse)
def database_health() -> DatabaseHealthResponse:
    return check_database()


@app.get("/api/health/ready", response_model=ReadyResponse)
def readiness() -> ReadyResponse:
    database = check_database()
    checks = {
        "app_started": "ok",
        "database": database.connectivity,
        "schema": check_schema(),
        "seed_data": check_seed_data(),
    }
    status = "ready" if all(value == "ok" for value in checks.values()) else "not_ready"
    return ReadyResponse(status=status, checks=checks)


@app.get("/api/system/status", response_model=SystemStatusResponse)
def system_status() -> SystemStatusResponse:
    settings = get_settings()
    db_health = check_database()
    now = datetime.now(timezone.utc).isoformat()
    return SystemStatusResponse(
        status="ok" if db_health.status == "ok" else "degraded",
        service="QuoteOps AI",
        version=APP_VERSION,
        generated_at=now,
        started_at=getattr(app.state, "started_at", None),
        backend={
            "status": "ok",
            "environment": settings.safe_app_env_label,
        },
        database={
            "status": db_health.status,
            "type": db_health.database_type,
            "connectivity": db_health.connectivity,
        },
        configuration={
            "database_configured": bool(os.getenv("DATABASE_URL", "")),
            "openai_configured": bool(settings.openai_api_key),
            "openai_model_configured": bool(settings.openai_model),
            "allowed_origins_configured": bool(settings.allowed_origins),
        },
        features={
            "fallback_explanation_available": True,
            "auth_enabled": True,
            "audit_logging_enabled": True,
            "job_system_enabled": True,
        },
    )


@app.get("/")
def root():
    return {
        "name": "QuoteOps AI",
        "message": "Backend is running. Visit /docs for API docs.",
    }
