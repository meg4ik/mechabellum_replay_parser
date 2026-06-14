import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .display import ask_supply, show_board_async
from .llm import analyze
from .transformer import dump_player_data_xml_fields, replay_to_dict

load_dotenv(Path(__file__).parent.parent.parent / ".env")


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

    # Unknown values across the whole parsed dict
    unknowns = _collect_unknowns(parsed)
    if unknowns:
        print(f"\n[!] UNKNOWN VALUES ({len(unknowns)} total):")
        for u in unknowns:
            print(f"  {u}")
    else:
        print("\n[✓] No unknown values")

    # Per-round summary
    for rnd in parsed.get("rounds", []):
        rnum = rnd["round"]
        fight = rnd.get("fight_result") or {}
        print(f"\n{'─'*70}")
        print(f"ROUND {rnum}" + (f"  fight_result={json.dumps(fight)}" if fight else "  (no fight result)"))
        for name, pdata in rnd.get("players", {}).items():
            print(f"\n  ┌─ {name}  HP={pdata.get('hp')}  outcome={pdata.get('fight_outcome')}")
            print(f"  │  Officers   : {pdata.get('officers')}")
            print(f"  │  Cmd skills : {[s['name'] for s in pdata.get('commander_skills', [])]}")
            print(f"  │  Contraption: {[c['name'] for c in pdata.get('contraptions', [])]}")
            print(f"  │  Constructs : {[c['type'] for c in pdata.get('constructions', [])]}")
            shop = pdata.get("shop", {})
            print(f"  │  Shop unlocked: {shop.get('unlocked')}  locked: {shop.get('locked')}")
            techs = pdata.get("active_techs", [])
            if techs:
                for t in techs:
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

REPLAY_DIR = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Mechabellum\ProjectDatas\Replay"
)

_STABLE_INTERVAL = 0.5
_STABLE_COUNT = 3


def _wait_for_file_stable(path: Path) -> bool:
    """Wait until the file size stops changing — Steam may still be writing."""
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
        time.sleep(_STABLE_INTERVAL)
    return True


def _delete(path: Path) -> None:
    try:
        path.unlink()
        print(f"[✓] Удалён: {path.name}")
    except OSError as e:
        print(f"[!] Не удалось удалить {path.name}: {e}")


def process_replay(path: Path) -> None:
    print(f"\n[→] Обнаружен реплей: {path.name}")

    if not _wait_for_file_stable(path):
        print(f"[!] Файл недоступен: {path.name}")
        return

    debug = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")

    print("[~] Парсинг...")
    try:
        parsed = replay_to_dict(path)
        players = [p for team in parsed["teams"] for p in team]
        print(f"[✓] Парсинг готов. Игроки: {players}, раундов: {parsed['last_round']}")
        if debug:
            dump_player_data_xml_fields(path)
            _debug_report(parsed)
        else:
            last_round = parsed["last_round"]
            supply = ask_supply(last_round)
            placement = analyze(parsed, supply=supply)
            if placement:
                player_name = os.getenv("PLAYER_NAME", "")
                last = next(
                    (r for r in parsed["rounds"] if r["round"] == last_round),
                    parsed["rounds"][-1],
                )
                player_data = last["players"].get(player_name, {})
                current_units = player_data.get("units", [])
                constructions = player_data.get("constructions", [])
                show_board_async(current_units, placement, last_round, player_name, constructions)
    except (ValueError, KeyError, AttributeError) as e:
        print(f"[!] Ошибка парсинга: {e}")
    finally:
        _delete(path)


class _ReplayHandler(FileSystemEventHandler):
    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and event.src_path.endswith(".grbr"):
            process_replay(Path(event.src_path))


def watch(replay_dir: Path = REPLAY_DIR) -> None:
    if not replay_dir.exists():
        print(f"[!] Папка не найдена: {replay_dir}")
        return

    print(f"[*] Мониторинг: {replay_dir}")
    print("[*] Нажмите Ctrl+C для остановки\n")

    # Обработать файл, если он уже есть в папке при старте
    for existing in replay_dir.glob("*.grbr"):
        process_replay(existing)

    observer = Observer()
    observer.schedule(_ReplayHandler(), str(replay_dir), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        print("\n[*] Мониторинг остановлен")
