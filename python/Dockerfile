# Build stage
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy workspace configuration
COPY pyproject.toml uv.lock ./
COPY packages/dyscount-core/pyproject.toml packages/dyscount-core/
COPY packages/dyscount-api/pyproject.toml packages/dyscount-api/
COPY packages/dyscount-cli/pyproject.toml packages/dyscount-cli/

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy source code
COPY packages/dyscount-core/src packages/dyscount-core/src
COPY packages/dyscount-api/src packages/dyscount-api/src
COPY packages/dyscount-cli/src packages/dyscount-cli/src

# Install projects
RUN uv sync --frozen

# Runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Run the server
CMD ["dyscount-server", "--host", "0.0.0.0", "--port", "8000"]
