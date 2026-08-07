# Multi-stage Dockerfile for Helios AI Employee on Railway / Docker
FROM python:3.11-slim

# Install system dependencies, LuaLaTeX for resume compilation, and Chromium Playwright dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    texlive-latex-base \
    texlive-luatex \
    texlive-fonts-recommended \
    libnss3 \
    libatk-bridge2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libcups2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications
COPY pyproject.toml .
COPY README.md .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx pyyaml pytest pytest-asyncio playwright sqlalchemy[asyncio] asyncpg aiosqlite alembic pydantic pydantic-settings python-dotenv

# Install Playwright browser binaries
RUN python -m playwright install chromium

# Copy application source code
COPY . .

# Install local package in editable mode
RUN pip install --no-cache-dir -e .

# Expose port for Railway / Docker
EXPOSE 8000

# Environment variables default
ENV PORT=8000
ENV ENVIRONMENT=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch FastAPI Web Server & Mission Control Dashboard
CMD uvicorn backend.src.main:app --host 0.0.0.0 --port ${PORT:-8000}
