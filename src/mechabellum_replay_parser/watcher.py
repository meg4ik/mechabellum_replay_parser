import time
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .llm import analyze
from .transformer import replay_to_dict

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

    print("[~] Парсинг...")
    parsed = None
    try:
        parsed = replay_to_dict(path)
        players = [p for team in parsed["teams"] for p in team]
        print(f"[✓] Парсинг готов. Игроки: {players}, раундов: {parsed['last_round']}")
        analyze(parsed)
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
