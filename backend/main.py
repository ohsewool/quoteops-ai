from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from datetime import datetime, timezone

app = FastAPI(
    title="QuoteOps AI API",
    description="AI-assisted pricing and quoting operations backend.",
    version="0.1.0",
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    llm_enabled: bool


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="quoteops-ai",
        timestamp=datetime.now(timezone.utc).isoformat(),
        llm_enabled=os.getenv("LLM_ENABLED", "false").lower() == "true",
    )


@app.get("/")
def root():
    return {
        "name": "QuoteOps AI",
        "message": "Backend is running. Visit /docs for API docs.",
    }
