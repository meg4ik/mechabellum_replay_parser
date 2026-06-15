FROM python:3.13-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install dependencies first (cached layer — only re-runs when pyproject.toml/uv.lock change)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source after dependencies (changing src/ doesn't bust the dependency cache)
COPY src/ src/
COPY game_knowledge.md .

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "--no-sync", "uvicorn", "mechabellum_replay_parser.api.app:app", \
     "--host", "0.0.0.0", "--port", "8000"]
