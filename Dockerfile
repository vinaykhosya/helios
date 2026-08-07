# Multi-stage Dockerfile for Helios AI Employee on Railway / Docker
FROM python:3.11-slim

# Install system dependencies & Playwright dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
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

ENV PORT=8000
ENV ENVIRONMENT=production

# Launch FastAPI Web Server & Mission Control Dashboard
CMD ["sh", "-c", "uvicorn backend.src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
