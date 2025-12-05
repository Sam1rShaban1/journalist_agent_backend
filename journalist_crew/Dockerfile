FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Setup Environment
ENV VIRTUAL_ENV=/app/.venv
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy dependency files
COPY pyproject.toml .

# Install Python Deps
RUN uv pip install crewai "crewai[tools]" duckduckgo-search langdetect pydantic chromadb chainlit sqlalchemy aiosqlite

# Copy App Code
COPY src/ src/
COPY public/ public/
COPY .chainlit/ .chainlit/
# Copy scripts
COPY init_chainlit_db.py .
COPY launcher.py .

# Create data directory (Just in case)
RUN mkdir -p data

EXPOSE 8000

# FIX: Run the launcher, which handles DB creation + App Start
CMD ["python", "launcher.py"]