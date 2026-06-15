"""Replay folder monitor.

In Docker mode: runs as an asyncio background task inside the FastAPI lifespan.
In CLI mode: launched via asyncio.run(watch(...)) from cli.py.

No Tkinter imports — supply and board visualization are delegated to native_ui
via WebSocket events (supply_request / recommendation_ready).
"""
import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .coach.engine import CoachEngine
from .db.service import PersistenceService
from .events.in_memory import InMemoryBroker
from .events.schemas import RecommendationReadyPayload, SupplyRequestPayload, UIEvent
from .transformer import dump_player_data_xml_fields, replay_to_dict

_log = logging.getLogger(__name__)
_coach_engine = CoachEngine()

load_dotenv(Path(__file__).parent.parent.parent / ".env")

REPLAY_DIR = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Mechabellum\ProjectDatas\Replay"
)

_STABLE_INTERVAL = 0.5
_STABLE_COUNT = 3


_DEBUG_DIR = Path(".debug")


def _supply_timeout() -> float:
    return float(os.getenv("SUPPLY_TIMEOUT", "300"))


def _write_debug(name: str, data) -> None:
    if os.getenv("DEBUG", "").lower() not in ("1", "true", "yes"):
        return
    try:
        _DEBUG_DIR.mkdir(exist_ok=True)
        path = _DEBUG_DIR / name
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except Exception as exc:
        _log.debug("Debug artifact write failed for %s: %s", name, exc)


# ── Debug helpers ─────────────────────────────────────────────────────────────

def _collect_unknowns(obj, path: str = "") -> list[str]:
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            results.extend(_collect_unknowns(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            results.extend(_collect_unknowns(v, f"{path}[{i}]"))
    elif isinstance(obj, str) and "unknown" in obj:
        results.append(f"{path} = {obj!r}")
    return results


def _debug_report(parsed: dict) -> None:
    sep = "=" * 70
    print(f"\n{sep}")
    print("DEBUG REPORT")
    print(sep)

    meta = parsed.get("metadata", {})
    print(f"Version : {meta.get('version')}  |  Mode: {meta.get('match_mode')}")
    print(f"Teams   : {parsed.get('teams')}")
    print(f"Rounds  : {parsed.get('last_round')}")

    unknowns = _collect_unknowns(parsed)
    if unknowns:
        print(f"\n[!] UNKNOWN VALUES ({len(unknowns)} total):")
        for u in unknowns:
            print(f"  {u}")
    else:
        print("\n[✓] No unknown values")

    for rnd in parsed.get("rounds", []):
        rnum = rnd["round"]
        fight = rnd.get("fight_result") or {}
        print(f"\n{'─' * 70}")
        print(f"ROUND {rnum}" + (f"  fight_result={json.dumps(fight)}" if fight else "  (no fight result)"))
        for name, pdata in rnd.get("players", {}).items():
            print(f"\n  ┌─ {name}  HP={pdata.get('hp')}  outcome={pdata.get('fight_outcome')}")
            print(f"  │  Officers   : {pdata.get('officers')}")
            print(f"  │  Cmd skills : {[s['name'] for s in pdata.get('commander_skills', [])]}")
            print(f"  │  Contraption: {[c['name'] for c in pdata.get('contraptions', [])]}")
            print(f"  │  Constructs : {[c['type'] for c in pdata.get('constructions', [])]}")
            shop = pdata.get("shop", {})
            print(f"  │  Shop unlocked: {shop.get('unlocked')}  locked: {shop.get('locked')}")
            for t in pdata.get("active_techs", []):
                print(f"  │  Tech  : {t['unit']} → {t['tech']}")
            units = pdata.get("units", [])
            print(f"  │  Units ({len(units)}):")
            for u in units:
                eq = f"  equip={u['equipment']}" if u.get("equipment") else ""
                print(f"  │    [{u['index']}] {u['name']}  lvl={u['level']}  pos={u['position']}{eq}")
            actions = pdata.get("actions", [])
            print(f"  │  Actions ({len(actions)}):")
            for a in actions:
                print(f"  │    {a}")

    print(f"\n{sep}\n")


# ── File handling ─────────────────────────────────────────────────────────────

async def _wait_for_file_stable(path: Path) -> bool:
    """Wait until the file size stops changing (Steam may still be writing)."""
    prev_size = -1
    stable = 0
    while stable < _STABLE_COUNT:
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if size > 0 and size == prev_size:
            stable += 1
        else:
            stable = 0
            prev_size = size
        await asyncio.sleep(_STABLE_INTERVAL)
    return True


def _handle_after_process(path: Path) -> None:
    """Delete, archive, or keep the replay file after processing."""
    policy = os.getenv("REPLAY_AFTER_PROCESS", "delete").lower()
    if policy == "keep":
        return
    if policy == "archive":
        archive_dir = path.parent / "processed"
        archive_dir.mkdir(exist_ok=True)
        try:
            path.rename(archive_dir / path.name)
            print(f"[✓] Archived: {path.name}")
        except OSError as e:
            print(f"[!] Archive failed {path.name}: {e}")
    else:
        try:
            path.unlink()
            print(f"[✓] Deleted: {path.name}")
        except OSError as e:
            print(f"[!] Delete failed {path.name}: {e}")


# ── Core pipeline ─────────────────────────────────────────────────────────────

async def process_replay(
    path: Path,
    broker: InMemoryBroker,
    pending_supplies: dict[str, asyncio.Future],
    persistence: PersistenceService | None = None,
) -> None:
    _log.info("stage=replay_detected file=%s", path.name)
    print(f"\n[→] Replay detected: {path.name}")

    if not await _wait_for_file_stable(path):
        _log.warning("stage=replay_stabilized_failed file=%s", path.name)
        print(f"[!] File unavailable: {path.name}")
        return

    _log.info("stage=replay_stabilized file=%s", path.name)
    debug = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")

    print("[~] Parsing...")
    try:
        parsed = replay_to_dict(path)
        players = [p for team in parsed["teams"] for p in team]
        _log.info("stage=replay_parsed file=%s players=%s rounds=%d", path.name, players, parsed["last_round"])
        _write_debug("latest_parsed.json", parsed)
        print(f"[✓] Parsed. Players: {players}, rounds: {parsed['last_round']}")

        if debug:
            dump_player_data_xml_fields(path)
            _debug_report(parsed)
            return

        last_round = parsed["last_round"]
        player_name = os.getenv("PLAYER_NAME", "")
        rec_id = f"rec_{uuid.uuid4().hex}"

        # Publish supply_request; native UI will respond via POST /ui/supply-response
        loop = asyncio.get_running_loop()
        supply_future: asyncio.Future = loop.create_future()
        pending_supplies[rec_id] = supply_future

        await broker.publish(UIEvent(
            type="supply_request",
            payload=SupplyRequestPayload(
                recommendation_id=rec_id,
                round=last_round,
                player_name=player_name,
            ).model_dump(),
        ))
        _log.info("stage=supply_requested rec_id=%s round=%d player=%s", rec_id, last_round, player_name)

        supply: int | None = None
        try:
            supply = await asyncio.wait_for(supply_future, timeout=_supply_timeout())
            _log.info("stage=supply_received rec_id=%s supply=%s", rec_id, supply)
        except asyncio.TimeoutError:
            _log.warning("stage=supply_timeout rec_id=%s — proceeding without supply", rec_id)
            print("[!] Supply timeout — proceeding without supply")
        finally:
            pending_supplies.pop(rec_id, None)

        analysis = await _coach_engine.analyze_replay_detailed(parsed, supply, player_name)
        recommendation = analysis.recommendation

        if persistence is not None:
            try:
                await persistence.save_match_analysis(
                    rec_id=rec_id,
                    source_file=path.name,
                    parsed=parsed,
                    round_number=last_round,
                    player_name=player_name,
                    supply=supply,
                    analysis=analysis,
                )
            except Exception as pe:
                print(f"[!] Persistence error (non-fatal): {pe}")

        if recommendation.placement:
            last = next(
                (r for r in parsed["rounds"] if r["round"] == last_round),
                parsed["rounds"][-1],
            )
            player_data = last["players"].get(player_name, {})
            current_units = player_data.get("units", [])
            constructions = player_data.get("constructions", [])

            await broker.publish(UIEvent(
                type="recommendation_ready",
                payload=RecommendationReadyPayload(
                    recommendation_id=rec_id,
                    round=last_round,
                    player_name=player_name,
                    summary=recommendation.summary,
                    current_units=current_units,
                    constructions=constructions,
                    placement=recommendation.placement,
                    coach_text=recommendation.coach_text,
                ).model_dump(),
            ))
            _log.info("stage=ui_event_sent type=recommendation_ready rec_id=%s", rec_id)

    except (ValueError, KeyError, AttributeError) as e:
        print(f"[!] Pipeline error: {e}")
        await broker.publish(UIEvent(
            type="error",
            payload={"message": str(e), "details": ""},
        ))
    finally:
        _handle_after_process(path)


# ── Watchdog integration ──────────────────────────────────────────────────────

class _ReplayHandler(FileSystemEventHandler):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        broker: InMemoryBroker,
        pending_supplies: dict,
        persistence: PersistenceService | None = None,
    ) -> None:
        self._loop = loop
        self._broker = broker
        self._pending_supplies = pending_supplies
        self._persistence = persistence

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and event.src_path.endswith(".grbr"):
            asyncio.run_coroutine_threadsafe(
                process_replay(
                    Path(event.src_path),
                    self._broker,
                    self._pending_supplies,
                    self._persistence,
                ),
                self._loop,
            )


async def watch(
    replay_dir: Path = REPLAY_DIR,
    broker: InMemoryBroker | None = None,
    pending_supplies: dict | None = None,
    persistence: PersistenceService | None = None,
) -> None:
    if broker is None:
        broker = InMemoryBroker()
    if pending_supplies is None:
        pending_supplies = {}

    if not replay_dir.exists():
        print(f"[!] Replay dir not found: {replay_dir}")
        return

    print(f"[*] Watching: {replay_dir}")
    print("[*] Press Ctrl+C to stop\n")

    loop = asyncio.get_running_loop()

    # Handle any files already present at startup
    for existing in replay_dir.glob("*.grbr"):
        asyncio.ensure_future(process_replay(existing, broker, pending_supplies, persistence))

    handler = _ReplayHandler(loop, broker, pending_supplies, persistence)
    observer = Observer()
    observer.schedule(handler, str(replay_dir), recursive=False)
    observer.start()

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        observer.stop()
        observer.join()
        print("\n[*] Watcher stopped")
