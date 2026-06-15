import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from mechabellum_replay_parser.events.in_memory import InMemoryBroker
from mechabellum_replay_parser.watcher import REPLAY_DIR, watch

from .routes_events import router as events_router
from .routes_health import router as health_router
from .routes_ui import router as ui_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.broker = InMemoryBroker()
    application.state.pending_supplies: dict[str, asyncio.Future] = {}

    replay_dir = Path(os.getenv("REPLAY_DIR", str(REPLAY_DIR)))

    watcher_task = None
    if replay_dir.exists():
        watcher_task = asyncio.create_task(
            watch(replay_dir, application.state.broker, application.state.pending_supplies)
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
