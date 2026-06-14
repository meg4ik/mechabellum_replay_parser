import threading
import tkinter as tk

# Player deployment zone bounds (game coordinates)
_X_MIN, _X_MAX = -285, 285
_Y_FRONT, _Y_BACK = -45, -295  # front = closest to enemy, back = furthest

# Canvas drawing area (pixels)
_CANVAS_W = 600
_CANVAS_H = 520
_MARGIN = 50
_RADIUS = 14


def _to_canvas(x: int, y: int) -> tuple[int, int]:
    cx = _MARGIN + (x - _X_MIN) / (_X_MAX - _X_MIN) * _CANVAS_W
    # y=-45 (front) → top, y=-295 (back) → bottom
    cy = _MARGIN + (_Y_FRONT - y) / (_Y_FRONT - _Y_BACK) * _CANVAS_H
    return int(cx), int(cy)


def _draw_unit(canvas: tk.Canvas, x: int, y: int, label: str, color: str, outline: str) -> None:
    cx, cy = _to_canvas(x, y)
    canvas.create_oval(
        cx - _RADIUS, cy - _RADIUS,
        cx + _RADIUS, cy + _RADIUS,
        fill=color, outline=outline, width=2,
    )
    canvas.create_text(cx, cy, text=label[:4], fill="white", font=("Arial", 7, "bold"))
    canvas.create_text(cx, cy + _RADIUS + 7, text=label[:10], fill=outline, font=("Arial", 7))


def show_board(
    current_units: list[dict],
    placement: list[dict],
    round_num: int | str,
    player_name: str,
) -> None:
    root = tk.Tk()
    root.title(f"Round {round_num} — {player_name}")
    root.resizable(False, False)

    total_w = _CANVAS_W + 2 * _MARGIN
    total_h = _CANVAS_H + 2 * _MARGIN + 30

    canvas = tk.Canvas(root, width=total_w, height=total_h, bg="#e8e8e8")
    canvas.pack()

    # Title
    canvas.create_text(
        total_w // 2, 18,
        text=f"Round {round_num}  —  {player_name}  |  ● current   ● new / move",
        font=("Arial", 10),
    )

    # Zone rectangle (white)
    zx0, zy0 = _MARGIN, _MARGIN + 30
    zx1 = _MARGIN + _CANVAS_W
    zy1 = _MARGIN + _CANVAS_H + 30
    canvas.create_rectangle(zx0, zy0, zx1, zy1, fill="white", outline="#aaaaaa", width=2)

    # Grid lines (faint)
    for gx in range(-200, 201, 100):
        x0, y0 = _to_canvas(gx, _Y_FRONT)
        x1, y1 = _to_canvas(gx, _Y_BACK)
        canvas.create_line(x0, y0 + 30, x1, y1 + 30, fill="#dddddd")
        canvas.create_text(x0, zy1 + 10, text=str(gx), fill="#999", font=("Arial", 7))

    for gy in range(-250, -44, 50):
        x0, y0 = _to_canvas(_X_MIN, gy)
        x1, y1 = _to_canvas(_X_MAX, gy)
        canvas.create_line(x0, y0 + 30, x1, y1 + 30, fill="#dddddd")
        canvas.create_text(zx0 - 12, y0 + 30, text=str(gy), fill="#999", font=("Arial", 7))

    # Front/back labels
    canvas.create_text(zx0 - 8, zy0, text="▲ front", fill="#999", font=("Arial", 7), anchor="e")
    canvas.create_text(zx0 - 8, zy1, text="▼ back", fill="#999", font=("Arial", 7), anchor="e")

    # New/moved units from LLM (green) — draw first so current overlaps if same spot
    new_actions = {u["action"] for u in placement}
    for u in placement:
        if u["action"] in ("new", "move"):
            cx, cy = _to_canvas(u["x"], u["y"])
            _draw_unit(canvas, u["x"], u["y"] - 30, u["unit"], "#22aa55", "#116633")

    # Current units from replay (dark gray)
    for u in current_units:
        pos = u.get("position") or {}
        x, y = pos.get("x"), pos.get("y")
        if x is None or y is None:
            continue
        _draw_unit(canvas, x, y - 30, u.get("name", "?"), "#555555", "#333333")

    # Legend
    lx, ly = total_w - 120, 18
    canvas.create_oval(lx, ly - 6, lx + 12, ly + 6, fill="#555555", outline="#333333")
    canvas.create_text(lx + 16, ly, text="current", anchor="w", font=("Arial", 8))
    canvas.create_oval(lx + 60, ly - 6, lx + 72, ly + 6, fill="#22aa55", outline="#116633")
    canvas.create_text(lx + 76, ly, text="new/move", anchor="w", font=("Arial", 8))

    root.mainloop()


def show_board_async(
    current_units: list[dict],
    placement: list[dict],
    round_num: int | str,
    player_name: str,
) -> None:
    t = threading.Thread(
        target=show_board,
        args=(current_units, placement, round_num, player_name),
        daemon=True,
    )
    t.start()
