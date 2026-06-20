# ---- Stage 1: Builder ----
FROM python:3.10-slim-bookworm AS builder

# Install uv for fast Python package resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project metadata files first (layer caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies into the build environment
# No venv needed at system level for builder; we use uv sync --no-install-project
RUN uv sync --frozen --no-install-project --no-editable

# ---- Stage 2: Runtime ----
FROM python:3.10-slim-bookworm AS runtime

# Install system deps needed at runtime
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
        ca-certificates \
        curl \
        tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy uv-installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY --chown=appuser:appuser . .

# Ensure reports directory exists and is writable
RUN mkdir -p /app/tradingagents/reports && chown -R appuser:appuser /app/tradingagents/reports

# Copy entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

USER appuser

# Streamlit default port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/docker-entrypoint.sh"]
