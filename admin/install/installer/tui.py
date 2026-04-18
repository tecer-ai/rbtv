"""Zero-dependency terminal UI for interactive selection.

Works on Windows (msvcrt), macOS (tty/termios), and Linux (tty/termios).
Uses ANSI escape codes for rendering.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Callable

# --- Key constants -----------------------------------------------------------

KEY_UP = "UP"
KEY_DOWN = "DOWN"
KEY_SPACE = "SPACE"
KEY_ENTER = "ENTER"
KEY_ESCAPE = "ESC"
KEY_UNKNOWN = "UNKNOWN"

# --- ANSI helpers ------------------------------------------------------------

HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_TO_END = "\033[J"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

_ANSI_RE = re.compile(r"\033\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _term_cols() -> int:
    try:
        return os.get_terminal_size().columns
    except (AttributeError, ValueError, OSError):
        return 80


def _visual_line_count(text: str, cols: int) -> int:
    """Count how many visual terminal rows *text* occupies, accounting for wrapping."""
    total = 0
    for line in text.split("\n"):
        w = len(_strip_ansi(line))
        if w == 0:
            total += 1
        else:
            total += (w + cols - 1) // cols
    return total


def _enable_ansi_windows() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


_ansi_initialized = False


def _ensure_ansi() -> None:
    global _ansi_initialized
    if not _ansi_initialized:
        _enable_ansi_windows()
        _ansi_initialized = True


# --- Cross-platform key reading ----------------------------------------------


def _read_key() -> str:
    if os.name == "nt":
        import msvcrt

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            return {
                "H": KEY_UP,
                "P": KEY_DOWN,
            }.get(ch2, KEY_UNKNOWN)
        if ch == "\r":
            return KEY_ENTER
        if ch == " ":
            return KEY_SPACE
        if ch == "\x1b":
            return KEY_ESCAPE
        return ch
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    return {"A": KEY_UP, "B": KEY_DOWN}.get(ch3, KEY_UNKNOWN)
                return KEY_ESCAPE
            if ch in ("\r", "\n"):
                return KEY_ENTER
            if ch == " ":
                return KEY_SPACE
            if ch == "\x03":
                raise KeyboardInterrupt
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# --- Widgets -----------------------------------------------------------------


def checkbox(
    title: str,
    items: list[dict[str, Any]],
    *,
    min_selected: int = 0,
    detail_callback: Callable[[int], str] | None = None,
) -> list[int]:
    """Interactive checkbox selector.

    Each item in *items* is a dict:
        label       — display text (required)
        selected    — initial state (default False)
        disabled    — cannot be toggled (default False)
        hint        — right-side hint text (optional)

    Keys:
        UP/DOWN   navigate
        SPACE     toggle
        ENTER     confirm (if >= min_selected checked)
        a         toggle all non-disabled items
        i / ?     show details (if detail_callback provided)

    Returns list of selected indices.
    """
    _ensure_ansi()
    cursor = 0
    selected = [item.get("selected", False) for item in items]
    disabled = [item.get("disabled", False) for item in items]
    prev_visual_rows = 0

    def _write(text: str) -> None:
        sys.stdout.write(text)

    def _build_output() -> str:
        keys = "up/down move | space toggle | enter confirm"
        if detail_callback:
            keys += " | i info"
        keys += " | a all"

        lines: list[str] = []
        lines.append(f"{BOLD}{title}{RESET}")
        lines.append(f"{DIM}  {keys}{RESET}")

        for i, item in enumerate(items):
            prefix = f"{CYAN}>{RESET} " if i == cursor else "  "
            if disabled[i]:
                box = f"{DIM}[x]{RESET}"
                label = f"{DIM}{item['label']} (always installed){RESET}"
            elif selected[i]:
                box = f"{GREEN}[x]{RESET}"
                label = item["label"]
            else:
                box = "[ ]"
                label = item["label"]
            hint = f"  {DIM}{item['hint']}{RESET}" if item.get("hint") else ""
            lines.append(f"{prefix}{box} {label}{hint}")

        return "\n".join(lines)

    def render(first_draw: bool = False) -> None:
        nonlocal prev_visual_rows
        cols = _term_cols()

        if not first_draw and prev_visual_rows > 0:
            _write(f"\033[{prev_visual_rows - 1}A\r")

        _write(CLEAR_TO_END)

        output = _build_output()
        _write(output)
        sys.stdout.flush()

        prev_visual_rows = _visual_line_count(output, cols)

    def _show_detail() -> None:
        nonlocal prev_visual_rows
        if not detail_callback:
            return
        cols = _term_cols()
        detail_text = detail_callback(cursor)

        if prev_visual_rows > 0:
            _write(f"\033[{prev_visual_rows - 1}A\r")
        _write(CLEAR_TO_END)
        _write(detail_text)
        _write(f"\n{DIM}  Press any key to return...{RESET}")
        sys.stdout.flush()

        detail_full = detail_text + "\n  Press any key to return..."
        prev_visual_rows = _visual_line_count(detail_full, cols)

        _read_key()
        render()

    _write(HIDE_CURSOR)
    try:
        render(first_draw=True)
        while True:
            key = _read_key()
            if key == KEY_UP:
                cursor = (cursor - 1) % len(items)
            elif key == KEY_DOWN:
                cursor = (cursor + 1) % len(items)
            elif key == KEY_SPACE:
                if not disabled[cursor]:
                    selected[cursor] = not selected[cursor]
            elif key in ("i", "?"):
                _show_detail()
                continue
            elif key == "a":
                non_disabled_selected = all(
                    selected[i] for i in range(len(items)) if not disabled[i]
                )
                for i in range(len(items)):
                    if not disabled[i]:
                        selected[i] = not non_disabled_selected
            elif key == KEY_ENTER:
                count = sum(1 for s in selected if s)
                if count >= min_selected:
                    break
            render()
    except KeyboardInterrupt:
        _write(SHOW_CURSOR)
        sys.stdout.flush()
        raise SystemExit(1)
    finally:
        _write(f"\n{SHOW_CURSOR}")
        sys.stdout.flush()

    return [i for i, s in enumerate(selected) if s]


def confirm(prompt: str, *, default: bool = True) -> bool:
    _ensure_ansi()
    hint = "Y/n" if default else "y/N"
    sys.stdout.write(f"{prompt} [{hint}]: ")
    sys.stdout.flush()
    response = input().strip().lower()
    if not response:
        return default
    return response in ("y", "yes")


def text_input(
    prompt: str,
    *,
    default: str = "",
    validator: Callable[[str], str | None] | None = None,
) -> str:
    _ensure_ansi()
    while True:
        if default:
            sys.stdout.write(f"{prompt} [{DIM}{default}{RESET}]: ")
        else:
            sys.stdout.write(f"{prompt}: ")
        sys.stdout.flush()
        value = input().strip()
        if not value and default:
            value = default
        if not value:
            print(f"  {YELLOW}Value required.{RESET}")
            continue
        if validator:
            error = validator(value)
            if error:
                print(f"  {YELLOW}{error}{RESET}")
                continue
        return value
