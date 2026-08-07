"""
backend/src/main.py

FastAPI Web Application Entry Point.
Configures app startup lifecycle, registers route endpoints, and provides health checks.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status

from backend.src.core.di import DIContainer
from backend.src.api.jobs import router as jobs_router
from backend.src.api.companies import router as companies_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown events."""
    # Initialize Dependency Injection container and DB connection pool
    DIContainer.initialize()
    yield
    # Cleanup database connection pool
    await DIContainer.shutdown()


app = FastAPI(
    title="Helios API",
    version="0.1.0",
    description="Helios — AI Career Intelligence Platform Backend API",
    lifespan=lifespan,
)

# Mount API route endpoints
app.include_router(jobs_router)
app.include_router(companies_router)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Liveness check for container orchestration and monitoring tools."""
    return {"status": "healthy"}
