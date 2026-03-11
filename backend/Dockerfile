# ── Stage 1: Builder ──
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies (gcc for compiled packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ──
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1

# matplotlib needs libglib2.0 for Agg backend in headless mode
RUN apt-get update && \
    apt-get install -y --no-install-recommends libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Security: run as non-root
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Writable dirs for SQLite DB and charts
RUN mkdir -p /app/data /app/charts && chown -R appuser:appuser /app

# Copy only the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY app/ app/

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# Default: run the API server.  Override with "worker" to start the queue consumer.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
