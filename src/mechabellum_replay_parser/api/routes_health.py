from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/debug/events")
async def debug_events(request: Request) -> dict:
    broker = request.app.state.broker
    pending = broker.pending_supply()
    pending_supplies: dict = request.app.state.pending_supplies
    persistence = getattr(request.app.state, "persistence", None)
    return {
        "ws_subscribers": broker.subscriber_count(),
        "pending_supply_event": pending.model_dump() if pending is not None else None,
        "pending_supply_futures": list(pending_supplies.keys()),
        "persistence_enabled": persistence.enabled if persistence else None,
    }


@router.get("/debug/watcher")
async def debug_watcher(request: Request) -> dict:
    import os
    from pathlib import Path

    replay_dir = Path(os.getenv("REPLAY_DIR", "/data/replays"))
    files: list[str] = []
    exists = replay_dir.exists()
    if exists:
        files = [f.name for f in replay_dir.glob("*.grbr")]
    return {
        "replay_dir": str(replay_dir),
        "replay_dir_exists": exists,
        "grbr_files_found": files,
        "player_name": os.getenv("PLAYER_NAME", ""),
    }
