from contextlib import asynccontextmanager

from fastapi import FastAPI

from mechabellum_replay_parser.events.in_memory import InMemoryBroker

from .routes_events import router as events_router
from .routes_health import router as health_router
from .routes_ui import router as ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.broker = InMemoryBroker()
    yield


app = FastAPI(title="Mechabellum Coach API", lifespan=lifespan)

app.include_router(health_router)
app.include_router(events_router)
app.include_router(ui_router)
