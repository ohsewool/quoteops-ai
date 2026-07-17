"""FastAPI application factory for the V2 security baseline."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from backend.api.errors import ApiError
from backend.api.routers.auth import router as auth_router
from backend.api.routers.approvals import router as approvals_router
from backend.api.routers.customer_requests import router as customer_requests_router
from backend.api.routers.copilot import router as copilot_router
from backend.api.routers.html_reports import router as html_reports_router
from backend.api.routers.pricing_checks import router as pricing_checks_router
from backend.api.routers.quotes import router as quotes_router
from backend.api.routers.system import router as system_router
from backend.config import Settings
from backend.db import SessionFactory, build_session_factory

REQUEST_ID_HEADER = "X-Request-ID"


def _safe_request_id(request: Request) -> str:
    supplied = request.headers.get(REQUEST_ID_HEADER)
    if supplied and len(supplied) <= 64 and supplied.replace("-", "").isalnum():
        return supplied
    return str(uuid4())


def _error_body(request: Request, error: ApiError) -> dict[str, object]:
    return {
        "detail": error.detail,
        "code": error.code,
        "field_errors": error.field_errors,
        "request_id": getattr(request.state, "request_id", str(uuid4())),
    }


def create_app(
    settings: Settings | None = None,
    session_factory: SessionFactory | None = None,
) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="QuoteOps AI V2",
        version="0.1.0",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.openapi_enabled else None,
    )
    app.state.settings = settings
    app.state.session_factory = session_factory or build_session_factory(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
    )

    @app.middleware("http")
    async def add_request_correlation_id(request: Request, call_next) -> Response:
        request.state.request_id = _safe_request_id(request)
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content=_error_body(request, error))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        field_errors = [
            {
                "field": ".".join(str(part) for part in item["loc"] if part != "body"),
                "message": item["msg"],
            }
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed",
                "code": "validation_error",
                "field_errors": field_errors,
                "request_id": getattr(request.state, "request_id", str(uuid4())),
            },
        )

    app.include_router(system_router)
    app.include_router(auth_router)
    app.include_router(customer_requests_router)
    app.include_router(quotes_router)
    app.include_router(pricing_checks_router)
    app.include_router(approvals_router)
    app.include_router(html_reports_router)
    app.include_router(copilot_router)
    return app


app = create_app()
