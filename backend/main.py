from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.db import create_db_and_tables
from backend.routers import (
    approval_requests_api,
    candidate_prices_api,
    competitors_api,
    cost_profiles_api,
    explanations_api,
    health_api,
    price_tables_api,
    products_api,
    quote_preview_api,
    validation_api,
)
from backend.seed import seed_demo_data

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    seed_demo_data()
    yield


app = FastAPI(
    title="QuoteOps AI API",
    description="AI-assisted pricing and quoting operations backend.",
    version="0.1.0-dev",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_api.router)
app.include_router(approval_requests_api.router)
app.include_router(candidate_prices_api.router)
app.include_router(products_api.router)
app.include_router(competitors_api.router)
app.include_router(cost_profiles_api.router)
app.include_router(explanations_api.router)
app.include_router(price_tables_api.router)
app.include_router(quote_preview_api.router)
app.include_router(validation_api.router)


@app.get("/")
def root():
    return {
        "name": "QuoteOps AI",
        "message": "Backend is running. Visit /docs for API docs.",
    }
