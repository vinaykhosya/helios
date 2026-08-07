"""
backend/src/main.py

FastAPI Web Application Entry Point.
Configures app startup lifecycle, mounts API route endpoints, serves static frontend assets,
and renders the Helios Mission Control Web Dashboard.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
    title="Helios API & Mission Control",
    version="3.0.0",
    description="Helios — Autonomous AI Career Agent Mission Control & Backend API",
    lifespan=lifespan,
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API route endpoints
app.include_router(jobs_router)
app.include_router(companies_router)

# Mount static frontend assets if static directory exists
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
static_dir = os.path.join(base_dir, "static")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/app", include_in_schema=False)
    @app.get("/dashboard", include_in_schema=False)
    @app.get("/jobs", include_in_schema=False)
    @app.get("/applications", include_in_schema=False)
    @app.get("/automation", include_in_schema=False)
    @app.get("/recovery", include_in_schema=False)
    @app.get("/company", include_in_schema=False)
    @app.get("/resume", include_in_schema=False)
    @app.get("/analytics", include_in_schema=False)
    @app.get("/telegram", include_in_schema=False)
    @app.get("/settings", include_in_schema=False)
    async def serve_dashboard():
        """Serves the Helios Mission Control Single-Page Application."""
        return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Liveness check for container orchestration and monitoring tools."""
    return {"status": "healthy"}
