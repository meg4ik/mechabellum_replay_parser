import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import simpledialog

_X_MIN, _X_MAX = -285, 285
_CANVAS_W = 600
_CANVAS_H = 520
_MARGIN = 50
_RADIUS = 14

_SCALE_X = _CANVAS_W / (_X_MAX - _X_MIN)
_SCALE_Y = _CANVAS_H / 290

_DATA_DIR = Path(__file__).parent / "data"

def _load_json(name: str) -> dict:
    try:
        with open(_DATA_DIR / name) as f:
            return json.load(f)
    except Exception:
        return {}

_UNIT_SIZES: dict = _load_json("unit_data.json")
_CONSTRUCTION_SIZES: dict = _load_json("construction_data.json")

_SNAKE_TO_DISPLAY: dict[str, str] = {
    "defensive_wall": "Defensive Wall",
    "anti_armor_cannon": "Anti-Armor Cannon",
    "rapid_fire_cannon": "Rapid-Fire Cannon",
    "magnetic_barricade": "Magnetic Barricade",
    "supply_tower": "Supply Tower",
    "command_tower": "Command Tower",
    "research_tower": "Research Tower",
}


def ask_supply(round_num: int | str) -> int | None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    result = simpledialog.askinteger(
        "Supply",
        f"Round {round_num}: enter your current supply amount:",
        parent=root,
        minvalue=0,
        maxvalue=99999,
    )
    root.destroy()
    return result


def _detect_zone(units: list[dict]) -> tuple[int, int]:
    """Return (y_front, y_back) based on whether the player uses negative or positive Y."""
    ys = [u["position"]["y"] for u in units if u.get("position")]
    if not ys:
        return -10, -300
    avg_y = sum(ys) / len(ys)
    return (10, 300) if avg_y >= 0 else (-10, -300)


def _to_canvas(x: int, y: int, y_front: int, y_back: int) -> tuple[int, int]:
    cx = _MARGIN + (x - _X_MIN) / (_X_MAX - _X_MIN) * _CANVAS_W
    # front → top of canvas, back → bottom
    cy = _MARGIN + abs(y_front - y) / abs(y_front - y_back) * _CANVAS_H
    return int(cx), int(cy)


_BUILDING_ABBR = {
    "Defensive Wall": "DW",
    "Anti-Armor Cannon": "AA",
    "Rapid-Fire Cannon": "RF",
    "Magnetic Barricade": "MB",
    "Supply Tower": "ST",
    "Command Tower": "CT",
    "Research Tower": "RT",
}
_BSIZE = 12  # half-side of building square (fallback when size_x/size_y not set)


def _draw_unit(
    canvas: tk.Canvas,
    x: int,
    y: int,
    y_front: int,
    y_back: int,
    label: str,
    color: str,
    outline: str,
) -> None:
    cx, cy = _to_canvas(x, y, y_front, y_back)
    info = _UNIT_SIZES.get(label, {})
    sx, sy = info.get("size_x"), info.get("size_y")
    rx = max(6, int(sx * _SCALE_X)) if sx is not None else _RADIUS
    ry = max(6, int(sy * _SCALE_Y)) if sy is not None else _RADIUS
    canvas.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, fill=color, outline=outline, width=2)
    canvas.create_text(cx, cy, text=label[:4], fill="white", font=("Arial", 7, "bold"))
    canvas.create_text(cx, cy + ry + 7, text=label[:10], fill=outline, font=("Arial", 7))


def _draw_building(
    canvas: tk.Canvas,
    x: int,
    y: int,
    y_front: int,
    y_back: int,
    btype: str,
) -> None:
    cx, cy = _to_canvas(x, y, y_front, y_back)
    display_name = _SNAKE_TO_DISPLAY.get(btype, btype)
    abbr = _BUILDING_ABBR.get(display_name, display_name[:2].upper())
    info = _CONSTRUCTION_SIZES.get(display_name, {})
    sx, sy = info.get("size_x"), info.get("size_y")
    rx = max(6, int(sx * _SCALE_X)) if sx is not None else _BSIZE
    ry = max(6, int(sy * _SCALE_Y)) if sy is not None else _BSIZE
    canvas.create_rectangle(cx - rx, cy - ry, cx + rx, cy + ry, fill="#d4a017", outline="#8b6914", width=2)
    canvas.create_text(cx, cy, text=abbr, fill="white", font=("Arial", 7, "bold"))
    canvas.create_text(cx, cy + ry + 7, text=display_name[:12], fill="#8b6914", font=("Arial", 7))


def show_board(
    current_units: list[dict],
    placement: list[dict],
    round_num: int | str,
    player_name: str,
    constructions: list[dict] | None = None,
) -> None:
    y_front, y_back = _detect_zone(current_units)

    root = tk.Tk()
    root.title(f"Round {round_num} — {player_name}")
    root.resizable(False, False)

    total_w = _CANVAS_W + 2 * _MARGIN
    total_h = _CANVAS_H + 2 * _MARGIN + 30

    canvas = tk.Canvas(root, width=total_w, height=total_h, bg="#e8e8e8")
    canvas.pack()

    canvas.create_text(
        total_w // 2,
        18,
        text=f"Round {round_num}  —  {player_name}  |  ● current   ● new / move",
        font=("Arial", 10),
    )

    zx0, zy0 = _MARGIN, _MARGIN + 30
    zx1 = _MARGIN + _CANVAS_W
    zy1 = _MARGIN + _CANVAS_H + 30
    canvas.create_rectangle(
        zx0, zy0, zx1, zy1, fill="white", outline="#aaaaaa", width=2
    )

    # Vertical grid lines
    for gx in range(-200, 201, 100):
        px, _ = _to_canvas(gx, y_front, y_front, y_back)
        canvas.create_line(px, zy0, px, zy1, fill="#dddddd")
        canvas.create_text(px, zy1 + 10, text=str(gx), fill="#999", font=("Arial", 7))

    # Horizontal grid lines
    step = 50
    y_lo, y_hi = min(y_front, y_back), max(y_front, y_back)
    for gy in range(y_lo, y_hi + 1, step):
        _, py = _to_canvas(0, gy, y_front, y_back)
        canvas.create_line(
            zx0, zy0 + py - _MARGIN, zx1, zy0 + py - _MARGIN, fill="#dddddd"
        )
        canvas.create_text(
            zx0 - 14, zy0 + py - _MARGIN, text=str(gy), fill="#999", font=("Arial", 7)
        )

    canvas.create_text(
        zx0 - 8, zy0, text="▲ front", fill="#999", font=("Arial", 7), anchor="e"
    )
    canvas.create_text(
        zx0 - 8, zy1, text="▼ back", fill="#999", font=("Arial", 7), anchor="e"
    )

    # LLM recommendations: on round 1 draw everything (all units are freely repositionable),
    # on other rounds draw only new/move entries.
    for u in placement:
        if round_num == 1 or u["action"] in ("new", "move"):
            _draw_unit(
                canvas, u["x"], u["y"], y_front, y_back, u["unit"], "#22aa55", "#116633"
            )

    # Current units from replay (dark gray) — skipped on round 1 since all are freely repositioned
    if round_num != 1:
        for u in current_units:
            pos = u.get("position") or {}
            x, y = pos.get("x"), pos.get("y")
            if x is None or y is None:
                continue
            _draw_unit(
                canvas, x, y, y_front, y_back, u.get("name", "?"), "#555555", "#333333"
            )

    # Buildings (gold squares)
    for b in constructions or []:
        pos = b.get("position") or {}
        bx, by = pos.get("x"), pos.get("y")
        if bx is None or by is None:
            continue
        _draw_building(canvas, bx, by, y_front, y_back, b.get("type", "?"))

    lx, ly = total_w - 180, 18
    canvas.create_oval(lx, ly - 6, lx + 12, ly + 6, fill="#555555", outline="#333333")
    canvas.create_text(lx + 16, ly, text="current", anchor="w", font=("Arial", 8))
    canvas.create_oval(
        lx + 60, ly - 6, lx + 72, ly + 6, fill="#22aa55", outline="#116633"
    )
    canvas.create_text(lx + 76, ly, text="new/move", anchor="w", font=("Arial", 8))
    canvas.create_rectangle(
        lx + 124, ly - 6, lx + 136, ly + 6, fill="#d4a017", outline="#8b6914"
    )
    canvas.create_text(lx + 140, ly, text="building", anchor="w", font=("Arial", 8))

    root.mainloop()


def show_board_async(
    current_units: list[dict],
    placement: list[dict],
    round_num: int | str,
    player_name: str,
    constructions: list[dict] | None = None,
) -> None:
    t = threading.Thread(
        target=show_board,
        args=(current_units, placement, round_num, player_name, constructions),
        daemon=True,
    )
    t.start()
