from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker, create_async_engine

_DEFAULT_URL = "postgresql+asyncpg://mechabellum:mechabellum@localhost:5432/mechabellum"

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_db_engine(url: str | None = None) -> AsyncEngine:
    global _engine, _session_factory
    db_url = url or os.getenv("DATABASE_URL", _DEFAULT_URL)
    _engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        create_db_engine()
    assert _session_factory is not None
    return _session_factory
