# Use Python 3.12 slim
FROM python:3.12-slim

# Install system dependencies
# curl is useful for healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Get uv binary directly
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# --- LAYER 1: DEPENDENCIES (Cached) ---
COPY pyproject.toml uv.lock ./

# Install dependencies from the lockfile.
RUN uv sync --frozen --no-install-project

# --- LAYER 2: APPLICATION CODE ---
COPY src/ src/
COPY public/ public/
COPY .chainlit/ .chainlit/

# Install the project itself (links your src/ folder)
RUN uv sync --frozen

# --- ENVIRONMENT ---
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Run Command
CMD ["chainlit", "run", "src/journalist_crew/ui.py", "--host", "0.0.0.0", "--port", "8000"]