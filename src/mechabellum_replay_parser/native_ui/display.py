"""Single persistent Tkinter coach window.

The window opens once and transitions between four states:
  idle      – waiting for a replay to appear
  supply    – player enters current supply amount
  loading   – AI is analysing (animated dots)
  result    – coach text + placement board + feedback bar

Thread safety: background threads call window.show_*() which schedule
the actual Tkinter code via root.after(0, ...) on the main thread.
"""

from __future__ import annotations

import json
import math
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import scrolledtext

# ── Board geometry ─────────────────────────────────────────────────────────────
_X_MIN, _X_MAX = -300, 300  # derived: arclight center ±290, size_x=10
_Y_FRONT = -10  # derived: arclight center -20, size_y=10
_Y_BACK = -310  # derived: arclight center -300, size_y=10
_BOARD_W = 840
_BOARD_H = 420
_MARGIN = 50
_RADIUS = 17

# Uniform scale: game board is 600×300 (2:1), canvas is 840×420 (2:1)
_SCALE = _BOARD_W / (_X_MAX - _X_MIN)  # 1.4 px per game-unit

# unit_data.json / construction_data.json store sizes in game grid cells;
# 1 grid cell = 2.5 coordinate units.
_GRID_SCALE = 2.5

# ── Size data ──────────────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_json(name: str) -> dict:
    try:
        with open(_DATA_DIR / name, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


_UNIT_SIZES: dict[str, dict] = _load_json("unit_data.json")
_CONSTRUCTION_SIZES: dict[str, dict] = _load_json("construction_data.json")

# Maps snake_case coach names → display names used as keys in construction_data.json
_SNAKE_TO_DISPLAY: dict[str, str] = {
    "defensive_wall": "Defensive Wall",
    "anti_armor_cannon": "Anti-Armor Cannon",
    "rapid_fire_cannon": "Rapid-Fire Cannon",
    "magnetic_barricade": "Magnetic Barricade",
    "supply_tower": "Supply Tower",
    "command_tower": "Command Tower",
    "research_tower": "Research Tower",
}

# ── Colour palette (dark gaming theme) ────────────────────────────────────────
_BG = "#1a1a2e"  # window background
_PANEL = "#16213e"  # panel / card background
_SURFACE = "#0f3460"  # canvas background
_FG = "#e0e0e0"  # primary text
_FG2 = "#9aa0b0"  # secondary / muted text
_GREEN = "#00c853"  # new / move units
_GREEN_DK = "#007c33"
_BLUE = "#42a5f5"  # keep units (recommended to stay)
_BLUE_DK = "#1565c0"
_GRAY = "#78909c"  # current units (not in recommendation)
_GRAY_DK = "#37474f"
_GOLD = "#ffd600"  # buildings
_GOLD_DK = "#b29100"
_RED = "#ef5350"  # error
_RED_UNIT = "#e57373"  # opponent units
_RED_UNIT_DK = "#b71c1c"
_TEAL = "#26a69a"  # teammate units
_TEAL_DK = "#00695c"
_BORDER = "#2e3a59"
_GRID = "#1e2d4a"
_MIDFIELD = "#4a3a1e"  # midfield separator

_LOADING_FRAMES = ["●  ○  ○", "●  ●  ○", "●  ●  ●", "○  ●  ●", "○  ○  ●", "○  ○  ○"]

_BUILDING_ABBR = {
    # combat constructions
    "Defensive Wall": "DW",
    "Anti-Armor Cannon": "AA",
    "Rapid-Fire Cannon": "RF",
    "Magnetic Barricade": "MB",
    # utility towers
    "Supply Tower": "S",
    "Command Tower": "C",
    "Research Tower": "R",
    # normalized names (coach engine)
    "supply_tower": "S",
    "command_tower": "C",
    "research_tower": "R",
    "defensive_wall": "DW",
    "anti_armor_cannon": "AA",
    "rapid_fire_cannon": "RF",
}


class CoachWindow:
    """Single Tkinter root window with dynamic state transitions."""

    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.title("⚔ Mechabellum Coach")
        self._root.configure(bg=_BG)
        self._root.geometry("1020x900")
        self._root.minsize(900, 700)
        self._root.resizable(True, True)

        self._is_connected: bool = False
        self._state: str = "idle"
        self._show_idle_impl()

    # ── Public API (thread-safe — can be called from any thread) ──────────────

    def mainloop(self) -> None:
        self._root.mainloop()

    def show_idle(self) -> None:
        self._schedule(self._show_idle_impl)

    def show_connected(self) -> None:
        self._is_connected = True
        if self._state == "idle":
            self._schedule(self._show_idle_impl)

    def show_supply_prompt(
        self,
        round_num: int,
        player_name: str,
        on_submit: Callable[[int | None, bool], None],
    ) -> None:
        self._schedule(
            lambda: self._show_supply_impl(round_num, player_name, on_submit)
        )

    def show_loading(self, round_num: int, player_name: str) -> None:
        self._schedule(lambda: self._show_loading_impl(round_num, player_name))

    def show_result(
        self,
        round_num: int,
        player_name: str,
        summary: str,
        coach_text: str,
        current_units: list[dict],
        placement: list[dict],
        constructions: list[dict],
        recommendation_id: str = "",
        on_feedback: Callable[[str, int, str | None, str | None, bool | None], None]
        | None = None,
        opponent_units: list[dict] | None = None,
        opponent_constructions: list[dict] | None = None,
        teammate_units: list[dict] | None = None,
        teammate_constructions: list[dict] | None = None,
    ) -> None:
        self._schedule(
            lambda: self._show_result_impl(
                round_num,
                player_name,
                summary,
                coach_text,
                current_units,
                placement,
                constructions,
                recommendation_id,
                on_feedback,
                opponent_units,
                opponent_constructions,
                teammate_units,
                teammate_constructions,
            )
        )

    def show_error(self, message: str) -> None:
        self._schedule(lambda: self._show_error_impl(message))

    def show_backend_unavailable(self) -> None:
        self._schedule(self._show_backend_unavailable_impl)

    # ── Thread-safe scheduler ─────────────────────────────────────────────────

    def _schedule(self, func: Callable[[], None]) -> None:
        try:
            self._root.after(0, func)
        except tk.TclError:
            pass  # window was already closed

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _clear(self) -> None:
        """Destroy all child widgets and unbind Return."""
        self._root.unbind("<Return>")
        for widget in self._root.winfo_children():
            widget.destroy()

    def _lbl(
        self,
        parent: tk.Widget,
        text: str,
        size: int = 14,
        bold: bool = False,
        color: str = _FG,
        **kw,
    ) -> tk.Label:
        weight = "bold" if bold else "normal"
        return tk.Label(
            parent, text=text, bg=_BG, fg=color, font=("Segoe UI", size, weight), **kw
        )

    # ── State: idle ───────────────────────────────────────────────────────────

    def _show_idle_impl(self) -> None:
        self._state = "idle"
        self._clear()
        frame = tk.Frame(self._root, bg=_BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(frame, "⚔  Mechabellum Coach", size=30, bold=True, color=_GREEN).pack(
            pady=(0, 14)
        )
        self._lbl(frame, "Ожидаю новую партию…", size=16, color=_FG2).pack()

        if self._is_connected:
            dot, msg, color = "●", "Подключено к серверу", _GREEN
        else:
            dot, msg, color = "○", "Нет соединения с сервером", _FG2
        self._lbl(frame, f"{dot}  {msg}", size=11, color=color).pack(pady=(20, 0))

    # ── State: supply prompt ──────────────────────────────────────────────────

    def _show_supply_impl(
        self,
        round_num: int,
        player_name: str,
        on_submit: Callable[[int | None, bool], None],
    ) -> None:
        self._clear()

        outer = tk.Frame(self._root, bg=_BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(outer, f"РАУНД  {round_num}", size=42, bold=True, color=_GREEN).pack(
            pady=(0, 4)
        )
        self._lbl(outer, player_name, size=16, color=_FG2).pack(pady=(0, 36))
        self._lbl(outer, "Введите текущий Supply:", size=18).pack(pady=(0, 12))

        supply_var = tk.StringVar()
        entry = tk.Entry(
            outer,
            textvariable=supply_var,
            font=("Segoe UI", 34),
            width=7,
            justify="center",
            bg=_PANEL,
            fg=_FG,
            insertbackground=_GREEN,
            relief="flat",
            bd=10,
        )
        entry.pack(pady=(0, 10))
        entry.focus_set()

        hint = self._lbl(outer, "", size=11, color=_RED)
        hint.pack(pady=(0, 24))

        def _submit() -> None:
            val = supply_var.get().strip()
            try:
                supply = int(val)
                if supply < 0:
                    raise ValueError
            except ValueError:
                hint.config(text="Введите целое число ≥ 0")
                entry.focus_set()
                return
            on_submit(supply, False)

        def _cancel() -> None:
            on_submit(None, True)

        self._root.bind("<Return>", lambda _e: _submit())

        btn_row = tk.Frame(outer, bg=_BG)
        btn_row.pack()

        tk.Button(
            btn_row,
            text="✓  Подтвердить",
            font=("Segoe UI", 15, "bold"),
            command=_submit,
            bg=_GREEN,
            fg="#000000",
            activebackground=_GREEN_DK,
            relief="flat",
            padx=28,
            pady=10,
            cursor="hand2",
        ).pack(side="left", padx=12)

        tk.Button(
            btn_row,
            text="✕  Пропустить",
            font=("Segoe UI", 15),
            command=_cancel,
            bg=_PANEL,
            fg=_FG2,
            activebackground=_BORDER,
            relief="flat",
            padx=28,
            pady=10,
            cursor="hand2",
        ).pack(side="left", padx=12)

        self._lbl(outer, "Enter — подтвердить", size=11, color=_FG2).pack(pady=(18, 0))

    # ── State: loading ────────────────────────────────────────────────────────

    def _show_loading_impl(self, round_num: int, player_name: str) -> None:
        self._clear()

        outer = tk.Frame(self._root, bg=_BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(
            outer, f"Раунд {round_num}  —  {player_name}", size=18, color=_FG2
        ).pack(pady=(0, 30))
        self._lbl(outer, "AI анализирует позицию…", size=24, bold=True).pack(
            pady=(0, 28)
        )

        dots = tk.Label(
            outer, text=_LOADING_FRAMES[0], bg=_BG, fg=_GREEN, font=("Segoe UI", 30)
        )
        dots.pack()

        self._lbl(outer, "Это займёт несколько секунд", size=13, color=_FG2).pack(
            pady=(18, 0)
        )
        self._animate(dots, 0)

    def _animate(self, label: tk.Label, step: int) -> None:
        try:
            if not label.winfo_exists():
                return
        except tk.TclError:
            return
        label.config(text=_LOADING_FRAMES[step % len(_LOADING_FRAMES)])
        self._root.after(260, lambda: self._animate(label, step + 1))

    # ── State: result ─────────────────────────────────────────────────────────

    def _show_result_impl(
        self,
        round_num: int,
        player_name: str,
        summary: str,
        coach_text: str,
        current_units: list[dict],
        placement: list[dict],
        constructions: list[dict],
        recommendation_id: str = "",
        on_feedback: Callable[[str, int, str | None, str | None, bool | None], None]
        | None = None,
        opponent_units: list[dict] | None = None,
        opponent_constructions: list[dict] | None = None,
        teammate_units: list[dict] | None = None,
        teammate_constructions: list[dict] | None = None,
    ) -> None:
        self._clear()

        outer = tk.Frame(self._root, bg=_BG)
        outer.pack(fill="both", expand=True)

        # ── feedback bar — packed at bottom first so expand=True on board works ──
        fb_bar = tk.Frame(outer, bg=_PANEL, pady=10)
        fb_bar.pack(fill="x", side="bottom")
        self._build_feedback_bar(fb_bar, recommendation_id, on_feedback)

        # ── title strip ───────────────────────────────────────────────────────
        top = tk.Frame(outer, bg=_PANEL, pady=10)
        top.pack(fill="x", side="top")
        tk.Label(
            top,
            text=f"РАУНД {round_num}  —  {player_name}",
            bg=_PANEL,
            fg=_FG,
            font=("Segoe UI", 17, "bold"),
        ).pack(side="left", padx=22)
        tk.Label(
            top,
            text="✓  Рекомендация готова",
            bg=_PANEL,
            fg=_GREEN,
            font=("Segoe UI", 13),
        ).pack(side="right", padx=22)

        # ── text section ──────────────────────────────────────────────────────
        text_outer = tk.Frame(outer, bg=_BG)
        text_outer.pack(fill="x", side="top", padx=22, pady=(14, 0))

        tk.Label(
            text_outer,
            text=summary,
            bg=_BG,
            fg=_FG,
            font=("Segoe UI", 18, "bold"),
            wraplength=960,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 12))

        if coach_text and coach_text.strip():
            tk.Frame(text_outer, bg=_BORDER, height=1).pack(fill="x", pady=(0, 10))
            coach_box = scrolledtext.ScrolledText(
                text_outer,
                bg=_PANEL,
                fg=_FG,
                font=("Segoe UI", 13),
                wrap="word",
                height=6,
                relief="flat",
                padx=14,
                pady=10,
                state="normal",
                borderwidth=0,
            )
            coach_box.insert("1.0", coach_text)
            coach_box.config(state="disabled")
            coach_box.pack(fill="x")

        # ── divider + board label ─────────────────────────────────────────────
        tk.Frame(outer, bg=_BORDER, height=2).pack(
            fill="x", side="top", padx=22, pady=(14, 8)
        )
        tk.Label(
            outer,
            text="РАССТАНОВКА",
            bg=_BG,
            fg=_FG2,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", side="top", padx=26, pady=(0, 6))

        # ── board canvas — scrollable when full board doesn't fit ────────────
        board_frame = tk.Frame(outer, bg=_BG)
        board_frame.pack(fill="both", expand=True, side="top", padx=22, pady=(0, 12))

        has_others = bool(
            opponent_units
            or opponent_constructions
            or teammate_units
            or teammate_constructions
        )
        full_board = has_others
        board_h = int(_BOARD_W * 620 / 600) if full_board else _BOARD_H
        canvas_w = _BOARD_W + 2 * _MARGIN
        canvas_h = board_h + 2 * _MARGIN + 30

        canvas = tk.Canvas(
            board_frame,
            bg=_PANEL,
            highlightthickness=1,
            highlightbackground=_BORDER,
            scrollregion=(0, 0, canvas_w, canvas_h),
        )
        if full_board:
            scrollbar = tk.Scrollbar(
                board_frame,
                orient="vertical",
                command=canvas.yview,
            )
            scrollbar.pack(side="right", fill="y")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            canvas.bind_all(
                "<MouseWheel>",
                lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"),
            )
        else:
            canvas.configure(width=canvas_w, height=canvas_h)
            canvas.pack(expand=True)

        self._draw_board(
            canvas,
            current_units,
            placement,
            constructions,
            round_num,
            board_h,
            opponent_units or [],
            opponent_constructions or [],
            teammate_units or [],
            teammate_constructions or [],
        )

        if full_board:
            canvas.yview_moveto(1.0)

    def _build_feedback_bar(
        self,
        parent: tk.Frame,
        recommendation_id: str,
        on_feedback: Callable[[str, int, str | None, str | None, bool | None], None]
        | None,
    ) -> None:
        inner = tk.Frame(parent, bg=_PANEL)
        inner.pack(expand=True)

        tk.Label(
            inner,
            text="Совет помог?",
            bg=_PANEL,
            fg=_FG2,
            font=("Segoe UI", 12),
        ).pack(side="left", padx=(0, 16))

        status_lbl = tk.Label(
            inner, text="", bg=_PANEL, fg=_GREEN, font=("Segoe UI", 12)
        )
        status_lbl.pack(side="left", padx=(0, 10))

        if on_feedback is None or not recommendation_id:
            tk.Label(
                inner,
                text="(обратная связь недоступна)",
                bg=_PANEL,
                fg=_FG2,
                font=("Segoe UI", 11),
            ).pack(side="left")
            return

        btn_yes: tk.Button
        btn_no: tk.Button

        def _send(rating: int, label: str) -> None:
            on_feedback(recommendation_id, rating, label, None, None)
            status_lbl.config(text="✓ Спасибо!")
            btn_yes.config(state="disabled")
            btn_no.config(state="disabled")

        btn_yes = tk.Button(
            inner,
            text="👍  Помогло",
            font=("Segoe UI", 12),
            command=lambda: _send(5, "good"),
            bg="#1a3a1a",
            fg=_GREEN,
            activebackground="#2a5a2a",
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
        )
        btn_yes.pack(side="left", padx=4)

        btn_no = tk.Button(
            inner,
            text="👎  Нет",
            font=("Segoe UI", 12),
            command=lambda: _send(1, "bad_strategy"),
            bg="#3a1a1a",
            fg=_RED,
            activebackground="#5a2a2a",
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
        )
        btn_no.pack(side="left", padx=4)

    # ── State: backend unavailable ───────────────────────────────────────────

    def _show_backend_unavailable_impl(self) -> None:
        self._is_connected = False
        self._state = "unavailable"
        self._clear()

        outer = tk.Frame(self._root, bg=_BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(outer, "⟳  Подключение…", size=24, bold=True, color=_FG2).pack(
            pady=(0, 16)
        )
        self._lbl(
            outer,
            "Сервер недоступен — повторное подключение через 2 с",
            size=13,
            color=_FG2,
        ).pack()

    # ── State: error ──────────────────────────────────────────────────────────

    def _show_error_impl(self, message: str) -> None:
        self._clear()

        outer = tk.Frame(self._root, bg=_BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(outer, "⚠  Ошибка", size=26, bold=True, color=_RED).pack(pady=(0, 18))
        self._lbl(
            outer, message, size=14, color=_FG, wraplength=700, justify="center"
        ).pack()

        tk.Button(
            outer,
            text="OK",
            font=("Segoe UI", 13),
            command=self._show_idle_impl,
            bg=_PANEL,
            fg=_FG,
            relief="flat",
            padx=28,
            pady=8,
            cursor="hand2",
        ).pack(pady=(28, 0))

    # ── Board drawing ─────────────────────────────────────────────────────────

    @staticmethod
    def _detect_zone(units: list[dict]) -> tuple[int, int]:
        ys = [u["position"]["y"] for u in units if u.get("position")]
        if not ys:
            return _Y_FRONT, _Y_BACK
        avg_y = sum(ys) / len(ys)
        return (-_Y_FRONT, -_Y_BACK) if avg_y >= 0 else (_Y_FRONT, _Y_BACK)

    @staticmethod
    def _to_canvas(
        x: int,
        y: int,
        y_top: int,
        y_bot: int,
        board_w: int,
        board_h: int,
    ) -> tuple[int, int]:
        cx = _MARGIN + (x - _X_MIN) / (_X_MAX - _X_MIN) * board_w
        cy = _MARGIN + 30 + abs(y_top - y) / abs(y_top - y_bot) * board_h
        return int(cx), int(cy)

    def _draw_board(
        self,
        canvas: tk.Canvas,
        current_units: list[dict],
        placement: list[dict],
        constructions: list[dict],
        round_num: int | str,
        board_h: int = _BOARD_H,
        opponent_units: list[dict] | None = None,
        opponent_constructions: list[dict] | None = None,
        teammate_units: list[dict] | None = None,
        teammate_constructions: list[dict] | None = None,
    ) -> None:
        y_front, y_back = self._detect_zone(current_units)
        full_board = bool(
            opponent_units
            or opponent_constructions
            or teammate_units
            or teammate_constructions
        )

        if full_board:
            y_top = -y_back  # opponent's back (top of canvas)
            y_bot = y_back  # player's back (bottom of canvas)
        else:
            y_top = y_front
            y_bot = y_back

        bw = _BOARD_W
        tc = lambda gx, gy: self._to_canvas(gx, gy, y_top, y_bot, bw, board_h)

        # Legend row at top of canvas
        legend_y = 16
        self._dot_legend(canvas, 26, legend_y, _GREEN, _GREEN_DK, "новые/двигать")
        self._dot_legend(canvas, 200, legend_y, _BLUE, _BLUE_DK, "оставить")
        self._rect_legend(canvas, 350, legend_y, _GOLD, _GOLD_DK, "постройки")
        if full_board:
            self._dot_legend(
                canvas, 500, legend_y, _RED_UNIT, _RED_UNIT_DK, "противник"
            )

        # Board zone rectangle
        zx0, zy0 = _MARGIN, _MARGIN + 30
        zx1 = _MARGIN + bw
        zy1 = _MARGIN + board_h + 30
        canvas.create_rectangle(
            zx0, zy0, zx1, zy1, fill=_SURFACE, outline=_BORDER, width=2
        )

        # Vertical grid lines
        for gx in range(-200, 201, 100):
            px, _ = tc(gx, y_top)
            canvas.create_line(px, zy0, px, zy1, fill=_GRID)
            canvas.create_text(px, zy1 + 11, text=str(gx), fill=_FG2, font=("Arial", 7))

        # Horizontal grid lines
        y_lo, y_hi = min(y_top, y_bot), max(y_top, y_bot)
        first_gy = math.ceil(y_lo / 50) * 50
        for gy in range(first_gy, y_hi + 1, 50):
            _, py = tc(0, gy)
            canvas.create_line(zx0, py, zx1, py, fill=_GRID)
            canvas.create_text(zx0 - 14, py, text=str(gy), fill=_FG2, font=("Arial", 7))

        # Midfield zone (y = -10 .. +10)
        if full_board:
            _, mid_top = tc(0, _Y_FRONT)
            _, mid_bot = tc(0, -_Y_FRONT)
            canvas.create_rectangle(
                zx0,
                mid_top,
                zx1,
                mid_bot,
                fill="#2a2518",
                outline="",
                stipple="",
            )
            canvas.create_line(
                zx0,
                mid_top,
                zx1,
                mid_top,
                fill=_MIDFIELD,
                width=1,
            )
            canvas.create_line(
                zx0,
                mid_bot,
                zx1,
                mid_bot,
                fill=_MIDFIELD,
                width=1,
            )
            mid_cy = (mid_top + mid_bot) // 2
            canvas.create_text(
                zx0 - 10,
                mid_cy,
                text="— mid —",
                fill=_MIDFIELD,
                font=("Arial", 8, "bold"),
                anchor="e",
            )
        else:
            canvas.create_text(
                zx0 - 10, zy0, text="▲ front", fill=_FG2, font=("Arial", 7), anchor="e"
            )
            canvas.create_text(
                zx0 - 10, zy1, text="▼ back", fill=_FG2, font=("Arial", 7), anchor="e"
            )

        # Placement (green=new/move, blue=keep)
        placed_unit_names: set[str] = set()
        for u in placement:
            action = u.get("action", "")
            action_str = action.value if hasattr(action, "value") else str(action)
            unit_name = u.get("unit", "?")
            placed_unit_names.add(unit_name.lower())
            if action_str in ("new", "move"):
                color, color_dk = _GREEN, _GREEN_DK
            else:
                color, color_dk = _BLUE, _BLUE_DK
            self._draw_unit(
                canvas,
                u["x"],
                u["y"],
                y_top,
                y_bot,
                bw,
                board_h,
                unit_name,
                color,
                color_dk,
            )

        # Current units (gray) — only those NOT already in placement
        for u in current_units:
            if u.get("name", "").lower() in placed_unit_names:
                continue
            pos = u.get("position") or {}
            x, y = pos.get("x"), pos.get("y")
            if x is None or y is None:
                continue
            self._draw_unit(
                canvas,
                x,
                y,
                y_top,
                y_bot,
                bw,
                board_h,
                u.get("name", "?"),
                _GRAY,
                _GRAY_DK,
            )

        # Player buildings (gold)
        for b in constructions or []:
            pos = b.get("position") or {}
            bx, by = pos.get("x"), pos.get("y")
            if bx is None or by is None:
                continue
            self._draw_building(
                canvas,
                bx,
                by,
                y_top,
                y_bot,
                bw,
                board_h,
                b.get("type", "?"),
            )

        # Opponent units (red)
        for u in opponent_units or []:
            pos = u.get("position") or {}
            x, y = pos.get("x"), pos.get("y")
            if x is None or y is None:
                continue
            self._draw_unit(
                canvas,
                x,
                y,
                y_top,
                y_bot,
                bw,
                board_h,
                u.get("name", "?"),
                _RED_UNIT,
                _RED_UNIT_DK,
            )

        # Opponent buildings (gold, same as player)
        for b in opponent_constructions or []:
            pos = b.get("position") or {}
            bx, by = pos.get("x"), pos.get("y")
            if bx is None or by is None:
                continue
            self._draw_building(
                canvas,
                bx,
                by,
                y_top,
                y_bot,
                bw,
                board_h,
                b.get("type", "?"),
            )

        # Teammate units (blue)
        for u in teammate_units or []:
            pos = u.get("position") or {}
            x, y = pos.get("x"), pos.get("y")
            if x is None or y is None:
                continue
            self._draw_unit(
                canvas,
                x,
                y,
                y_top,
                y_bot,
                bw,
                board_h,
                u.get("name", "?"),
                _BLUE,
                _BLUE_DK,
            )

        # Teammate buildings (gold, same as others)
        for b in teammate_constructions or []:
            pos = b.get("position") or {}
            bx, by = pos.get("x"), pos.get("y")
            if bx is None or by is None:
                continue
            self._draw_building(
                canvas,
                bx,
                by,
                y_top,
                y_bot,
                bw,
                board_h,
                b.get("type", "?"),
            )

    def _draw_unit(
        self,
        canvas: tk.Canvas,
        x: int,
        y: int,
        y_top: int,
        y_bot: int,
        board_w: int,
        board_h: int,
        label: str,
        fill: str,
        outline: str,
    ) -> None:
        cx, cy = self._to_canvas(x, y, y_top, y_bot, board_w, board_h)
        info = _UNIT_SIZES.get(label, {})
        sx, sy = info.get("size_x"), info.get("size_y")
        rx = max(3, int(sx * _GRID_SCALE * _SCALE)) if sx is not None else _RADIUS
        ry = max(3, int(sy * _GRID_SCALE * _SCALE)) if sy is not None else _RADIUS
        canvas.create_rectangle(
            cx - rx, cy - ry, cx + rx, cy + ry, fill=fill, outline=outline, width=2
        )
        canvas.create_text(
            cx, cy, text=label[:4], fill="#ffffff", font=("Arial", 8, "bold")
        )
        canvas.create_text(
            cx, cy + ry + 9, text=label[:12], fill=outline, font=("Arial", 8)
        )

    def _draw_building(
        self,
        canvas: tk.Canvas,
        x: int,
        y: int,
        y_top: int,
        y_bot: int,
        board_w: int,
        board_h: int,
        btype: str,
    ) -> None:
        cx, cy = self._to_canvas(x, y, y_top, y_bot, board_w, board_h)
        abbr = _BUILDING_ABBR.get(btype, btype[:2].upper())
        display_name = _SNAKE_TO_DISPLAY.get(btype, btype)
        info = _CONSTRUCTION_SIZES.get(display_name, {})
        sx, sy = info.get("size_x"), info.get("size_y")
        rx = max(4, int(sx * _GRID_SCALE * _SCALE)) if sx is not None else 13
        ry = max(4, int(sy * _GRID_SCALE * _SCALE)) if sy is not None else 13
        canvas.create_rectangle(
            cx - rx, cy - ry, cx + rx, cy + ry, fill=_GOLD, outline=_GOLD_DK, width=2
        )
        canvas.create_text(cx, cy, text=abbr, fill="#000000", font=("Arial", 8, "bold"))
        canvas.create_text(
            cx, cy + ry + 9, text=display_name[:14], fill=_GOLD_DK, font=("Arial", 8)
        )

    # ── Legend helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _dot_legend(
        canvas: tk.Canvas, x: int, y: int, fill: str, outline: str, text: str
    ) -> None:
        r = 7
        canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=outline)
        canvas.create_text(
            x + r + 4, y, text=text, anchor="w", fill=_FG2, font=("Arial", 9)
        )

    @staticmethod
    def _rect_legend(
        canvas: tk.Canvas, x: int, y: int, fill: str, outline: str, text: str
    ) -> None:
        s = 7
        canvas.create_rectangle(x - s, y - s, x + s, y + s, fill=fill, outline=outline)
        canvas.create_text(
            x + s + 4, y, text=text, anchor="w", fill=_FG2, font=("Arial", 9)
        )
