FROM python:3.13-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY game_knowledge.md .

ENV PYTHONPATH=/app/src

CMD ["uv", "run", "uvicorn", "mechabellum_replay_parser.api.app:app", \
     "--host", "0.0.0.0", "--port", "8000"]
