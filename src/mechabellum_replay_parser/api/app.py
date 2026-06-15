import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from mechabellum_replay_parser.db.models import Base
from mechabellum_replay_parser.db.service import create_persistence_service
from mechabellum_replay_parser.events.in_memory import InMemoryBroker
from mechabellum_replay_parser.watcher import REPLAY_DIR, watch

from .routes_events import router as events_router
from .routes_feedback import router as feedback_router
from .routes_health import router as health_router
from .routes_ui import router as ui_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.broker = InMemoryBroker()
    application.state.pending_supplies: dict[str, asyncio.Future] = {}

    persistence = create_persistence_service()
    application.state.persistence = persistence

    if persistence.enabled:
        from mechabellum_replay_parser.db.session import _ensure_asyncpg
        from sqlalchemy.ext.asyncio import create_async_engine as _create_engine
        _db_url = _ensure_asyncpg(os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://mechabellum:mechabellum@localhost:5432/mechabellum",
        ))
        try:
            _engine = _create_engine(_db_url)
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("[db] Tables ensured")
        except Exception as e:
            print(f"[db] Could not create tables (non-fatal — run alembic upgrade): {e}")
        else:
            await _engine.dispose()

    replay_dir = Path(os.getenv("REPLAY_DIR", str(REPLAY_DIR)))

    watcher_task = None
    if replay_dir.exists():
        watcher_task = asyncio.create_task(
            watch(
                replay_dir,
                application.state.broker,
                application.state.pending_supplies,
                persistence,
            )
        )
    else:
        print(f"[api] Replay dir not found: {replay_dir} — watcher not started")

    yield

    if watcher_task is not None:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Mechabellum Coach API", lifespan=lifespan)

app.include_router(health_router)
app.include_router(events_router)
app.include_router(ui_router)
app.include_router(feedback_router)
