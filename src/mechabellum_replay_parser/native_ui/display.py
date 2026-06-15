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

import tkinter as tk
from collections.abc import Callable
from tkinter import scrolledtext

# ── Board geometry ─────────────────────────────────────────────────────────────
_X_MIN, _X_MAX = -285, 285
_BOARD_W = 840
_BOARD_H = 460
_MARGIN = 50
_RADIUS = 17

# ── Colour palette (dark gaming theme) ────────────────────────────────────────
_BG = "#1a1a2e"          # window background
_PANEL = "#16213e"       # panel / card background
_SURFACE = "#0f3460"     # canvas background
_FG = "#e0e0e0"          # primary text
_FG2 = "#9aa0b0"         # secondary / muted text
_GREEN = "#00c853"       # new / move units
_GREEN_DK = "#007c33"
_GRAY = "#78909c"        # current units
_GRAY_DK = "#37474f"
_GOLD = "#ffd600"        # buildings
_GOLD_DK = "#b29100"
_RED = "#ef5350"         # error
_BORDER = "#2e3a59"
_GRID = "#1e2d4a"

_LOADING_FRAMES = ["●  ○  ○", "●  ●  ○", "●  ●  ●", "○  ●  ●", "○  ○  ●", "○  ○  ○"]

_BUILDING_ABBR = {
    "Supply Tower": "ST",
    "Command Tower": "CT",
    "Research Tower": "RT",
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

        self._show_idle_impl()

    # ── Public API (thread-safe — can be called from any thread) ──────────────

    def mainloop(self) -> None:
        self._root.mainloop()

    def show_idle(self) -> None:
        self._schedule(self._show_idle_impl)

    def show_supply_prompt(
        self,
        round_num: int,
        player_name: str,
        on_submit: Callable[[int | None, bool], None],
    ) -> None:
        self._schedule(lambda: self._show_supply_impl(round_num, player_name, on_submit))

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
        on_feedback: Callable[[str, int, str | None, str | None, bool | None], None] | None = None,
    ) -> None:
        self._schedule(lambda: self._show_result_impl(
            round_num, player_name, summary, coach_text,
            current_units, placement, constructions,
            recommendation_id, on_feedback,
        ))

    def show_error(self, message: str) -> None:
        self._schedule(lambda: self._show_error_impl(message))

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

    def _lbl(self, parent: tk.Widget, text: str, size: int = 14,
             bold: bool = False, color: str = _FG, **kw) -> tk.Label:
        weight = "bold" if bold else "normal"
        return tk.Label(parent, text=text, bg=_BG, fg=color,
                        font=("Segoe UI", size, weight), **kw)

    # ── State: idle ───────────────────────────────────────────────────────────

    def _show_idle_impl(self) -> None:
        self._clear()
        frame = tk.Frame(self._root, bg=_BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(frame, "⚔  Mechabellum Coach", size=30, bold=True, color=_GREEN).pack(pady=(0, 14))
        self._lbl(frame, "Ожидаю новую партию…", size=16, color=_FG2).pack()

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

        self._lbl(outer, f"РАУНД  {round_num}", size=42, bold=True, color=_GREEN).pack(pady=(0, 4))
        self._lbl(outer, player_name, size=16, color=_FG2).pack(pady=(0, 36))
        self._lbl(outer, "Введите текущий Supply:", size=18).pack(pady=(0, 12))

        supply_var = tk.StringVar()
        entry = tk.Entry(
            outer, textvariable=supply_var,
            font=("Segoe UI", 34), width=7, justify="center",
            bg=_PANEL, fg=_FG, insertbackground=_GREEN,
            relief="flat", bd=10,
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
            btn_row, text="✓  Подтвердить", font=("Segoe UI", 15, "bold"),
            command=_submit,
            bg=_GREEN, fg="#000000", activebackground=_GREEN_DK,
            relief="flat", padx=28, pady=10, cursor="hand2",
        ).pack(side="left", padx=12)

        tk.Button(
            btn_row, text="✕  Пропустить", font=("Segoe UI", 15),
            command=_cancel,
            bg=_PANEL, fg=_FG2, activebackground=_BORDER,
            relief="flat", padx=28, pady=10, cursor="hand2",
        ).pack(side="left", padx=12)

        self._lbl(outer, "Enter — подтвердить", size=11, color=_FG2).pack(pady=(18, 0))

    # ── State: loading ────────────────────────────────────────────────────────

    def _show_loading_impl(self, round_num: int, player_name: str) -> None:
        self._clear()

        outer = tk.Frame(self._root, bg=_BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(outer, f"Раунд {round_num}  —  {player_name}", size=18, color=_FG2).pack(pady=(0, 30))
        self._lbl(outer, "AI анализирует позицию…", size=24, bold=True).pack(pady=(0, 28))

        dots = tk.Label(outer, text=_LOADING_FRAMES[0], bg=_BG, fg=_GREEN,
                        font=("Segoe UI", 30))
        dots.pack()

        self._lbl(outer, "Это займёт несколько секунд", size=13, color=_FG2).pack(pady=(18, 0))
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
        on_feedback: Callable[[str, int, str | None, str | None, bool | None], None] | None = None,
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
            top, text=f"РАУНД {round_num}  —  {player_name}",
            bg=_PANEL, fg=_FG, font=("Segoe UI", 17, "bold"),
        ).pack(side="left", padx=22)
        tk.Label(
            top, text="✓  Рекомендация готова",
            bg=_PANEL, fg=_GREEN, font=("Segoe UI", 13),
        ).pack(side="right", padx=22)

        # ── text section ──────────────────────────────────────────────────────
        text_outer = tk.Frame(outer, bg=_BG)
        text_outer.pack(fill="x", side="top", padx=22, pady=(14, 0))

        tk.Label(
            text_outer,
            text=summary,
            bg=_BG, fg=_FG,
            font=("Segoe UI", 18, "bold"),
            wraplength=960, justify="left", anchor="w",
        ).pack(fill="x", pady=(0, 12))

        if coach_text and coach_text.strip():
            tk.Frame(text_outer, bg=_BORDER, height=1).pack(fill="x", pady=(0, 10))
            coach_box = scrolledtext.ScrolledText(
                text_outer,
                bg=_PANEL, fg=_FG,
                font=("Segoe UI", 13),
                wrap="word", height=6,
                relief="flat", padx=14, pady=10,
                state="normal", borderwidth=0,
            )
            coach_box.insert("1.0", coach_text)
            coach_box.config(state="disabled")
            coach_box.pack(fill="x")

        # ── divider + board label ─────────────────────────────────────────────
        tk.Frame(outer, bg=_BORDER, height=2).pack(fill="x", side="top", padx=22, pady=(14, 8))
        tk.Label(
            outer, text="РАССТАНОВКА",
            bg=_BG, fg=_FG2, font=("Segoe UI", 10, "bold"), anchor="w",
        ).pack(fill="x", side="top", padx=26, pady=(0, 6))

        # ── board canvas — takes all remaining vertical space ─────────────────
        board_frame = tk.Frame(outer, bg=_BG)
        board_frame.pack(fill="both", expand=True, side="top", padx=22, pady=(0, 12))

        canvas_w = _BOARD_W + 2 * _MARGIN
        canvas_h = _BOARD_H + 2 * _MARGIN + 30
        canvas = tk.Canvas(
            board_frame,
            width=canvas_w, height=canvas_h,
            bg=_PANEL, highlightthickness=1,
            highlightbackground=_BORDER,
        )
        canvas.pack(expand=True)
        self._draw_board(canvas, current_units, placement, constructions, round_num)

    def _build_feedback_bar(
        self,
        parent: tk.Frame,
        recommendation_id: str,
        on_feedback: Callable[[str, int, str | None, str | None, bool | None], None] | None,
    ) -> None:
        inner = tk.Frame(parent, bg=_PANEL)
        inner.pack(expand=True)

        tk.Label(
            inner, text="Совет помог?",
            bg=_PANEL, fg=_FG2, font=("Segoe UI", 12),
        ).pack(side="left", padx=(0, 16))

        status_lbl = tk.Label(inner, text="", bg=_PANEL, fg=_GREEN, font=("Segoe UI", 12))
        status_lbl.pack(side="left", padx=(0, 10))

        if on_feedback is None or not recommendation_id:
            tk.Label(
                inner, text="(обратная связь недоступна)",
                bg=_PANEL, fg=_FG2, font=("Segoe UI", 11),
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
            inner, text="👍  Помогло",
            font=("Segoe UI", 12), command=lambda: _send(5, "good"),
            bg="#1a3a1a", fg=_GREEN, activebackground="#2a5a2a",
            relief="flat", padx=18, pady=6, cursor="hand2",
        )
        btn_yes.pack(side="left", padx=4)

        btn_no = tk.Button(
            inner, text="👎  Нет",
            font=("Segoe UI", 12), command=lambda: _send(1, "bad_strategy"),
            bg="#3a1a1a", fg=_RED, activebackground="#5a2a2a",
            relief="flat", padx=18, pady=6, cursor="hand2",
        )
        btn_no.pack(side="left", padx=4)

    # ── State: error ──────────────────────────────────────────────────────────

    def _show_error_impl(self, message: str) -> None:
        self._clear()

        outer = tk.Frame(self._root, bg=_BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(outer, "⚠  Ошибка", size=26, bold=True, color=_RED).pack(pady=(0, 18))
        self._lbl(outer, message, size=14, color=_FG, wraplength=700, justify="center").pack()

        tk.Button(
            outer, text="OK", font=("Segoe UI", 13),
            command=self._show_idle_impl,
            bg=_PANEL, fg=_FG, relief="flat", padx=28, pady=8,
            cursor="hand2",
        ).pack(pady=(28, 0))

    # ── Board drawing ─────────────────────────────────────────────────────────

    @staticmethod
    def _detect_zone(units: list[dict]) -> tuple[int, int]:
        ys = [u["position"]["y"] for u in units if u.get("position")]
        if not ys:
            return -45, -295
        avg_y = sum(ys) / len(ys)
        return (45, 295) if avg_y >= 0 else (-45, -295)

    @staticmethod
    def _to_canvas(x: int, y: int, y_front: int, y_back: int) -> tuple[int, int]:
        cx = _MARGIN + (x - _X_MIN) / (_X_MAX - _X_MIN) * _BOARD_W
        cy = _MARGIN + abs(y_front - y) / abs(y_front - y_back) * _BOARD_H
        return int(cx), int(cy)

    def _draw_board(
        self,
        canvas: tk.Canvas,
        current_units: list[dict],
        placement: list[dict],
        constructions: list[dict],
        round_num: int | str,
    ) -> None:
        y_front, y_back = self._detect_zone(current_units)
        total_w = _BOARD_W + 2 * _MARGIN

        # Legend row at top of canvas
        legend_y = 16
        self._dot_legend(canvas, 26, legend_y, _GRAY, _GRAY_DK, "действующие")
        self._dot_legend(canvas, 180, legend_y, _GREEN, _GREEN_DK, "новые / переставить")
        self._rect_legend(canvas, 390, legend_y, _GOLD, _GOLD_DK, "постройки")

        # Board zone rectangle
        zx0, zy0 = _MARGIN, _MARGIN + 30
        zx1 = _MARGIN + _BOARD_W
        zy1 = _MARGIN + _BOARD_H + 30
        canvas.create_rectangle(zx0, zy0, zx1, zy1, fill=_SURFACE, outline=_BORDER, width=2)

        # Vertical grid lines
        for gx in range(-200, 201, 100):
            px, _ = self._to_canvas(gx, y_front, y_front, y_back)
            canvas.create_line(px, zy0, px, zy1, fill=_GRID)
            canvas.create_text(px, zy1 + 11, text=str(gx), fill=_FG2, font=("Arial", 7))

        # Horizontal grid lines
        y_lo, y_hi = min(y_front, y_back), max(y_front, y_back)
        for gy in range(y_lo, y_hi + 1, 50):
            _, py = self._to_canvas(0, gy, y_front, y_back)
            canvas.create_line(zx0, zy0 + py - _MARGIN, zx1, zy0 + py - _MARGIN, fill=_GRID)
            canvas.create_text(
                zx0 - 14, zy0 + py - _MARGIN,
                text=str(gy), fill=_FG2, font=("Arial", 7),
            )

        canvas.create_text(zx0 - 10, zy0, text="▲ front", fill=_FG2, font=("Arial", 7), anchor="e")
        canvas.create_text(zx0 - 10, zy1, text="▼ back", fill=_FG2, font=("Arial", 7), anchor="e")

        # Placement (green — new/move)
        for u in placement:
            if round_num == 1 or u.get("action") in ("new", "move"):
                self._draw_unit(canvas, u["x"], u["y"], y_front, y_back,
                                u["unit"], _GREEN, _GREEN_DK)

        # Current units (gray — existing positions)
        if round_num != 1:
            for u in current_units:
                pos = u.get("position") or {}
                x, y = pos.get("x"), pos.get("y")
                if x is None or y is None:
                    continue
                self._draw_unit(canvas, x, y, y_front, y_back,
                                u.get("name", "?"), _GRAY, _GRAY_DK)

        # Buildings (gold squares)
        for b in (constructions or []):
            pos = b.get("position") or {}
            bx, by = pos.get("x"), pos.get("y")
            if bx is None or by is None:
                continue
            self._draw_building(canvas, bx, by, y_front, y_back, b.get("type", "?"))

    def _draw_unit(
        self, canvas: tk.Canvas,
        x: int, y: int, y_front: int, y_back: int,
        label: str, fill: str, outline: str,
    ) -> None:
        cx, cy = self._to_canvas(x, y, y_front, y_back)
        canvas.create_oval(
            cx - _RADIUS, cy - _RADIUS, cx + _RADIUS, cy + _RADIUS,
            fill=fill, outline=outline, width=2,
        )
        canvas.create_text(cx, cy, text=label[:4], fill="#ffffff", font=("Arial", 8, "bold"))
        canvas.create_text(cx, cy + _RADIUS + 9, text=label[:12], fill=outline, font=("Arial", 8))

    def _draw_building(
        self, canvas: tk.Canvas,
        x: int, y: int, y_front: int, y_back: int, btype: str,
    ) -> None:
        cx, cy = self._to_canvas(x, y, y_front, y_back)
        abbr = _BUILDING_ABBR.get(btype, btype[:2].upper())
        s = 13
        canvas.create_rectangle(cx - s, cy - s, cx + s, cy + s,
                                 fill=_GOLD, outline=_GOLD_DK, width=2)
        canvas.create_text(cx, cy, text=abbr, fill="#000000", font=("Arial", 8, "bold"))
        canvas.create_text(cx, cy + s + 9, text=btype[:14], fill=_GOLD_DK, font=("Arial", 8))

    # ── Legend helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _dot_legend(canvas: tk.Canvas, x: int, y: int,
                    fill: str, outline: str, text: str) -> None:
        r = 7
        canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=outline)
        canvas.create_text(x + r + 4, y, text=text, anchor="w", fill=_FG2, font=("Arial", 9))

    @staticmethod
    def _rect_legend(canvas: tk.Canvas, x: int, y: int,
                     fill: str, outline: str, text: str) -> None:
        s = 7
        canvas.create_rectangle(x - s, y - s, x + s, y + s, fill=fill, outline=outline)
        canvas.create_text(x + s + 4, y, text=text, anchor="w", fill=_FG2, font=("Arial", 9))
