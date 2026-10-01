"""Asks the human ONE question at a time — a multi-select, a single choice, a
yes/no, a line of text — with arrow keys when both ends are a real terminal
(Windows via msvcrt, macOS and Linux via termios/tty) and with a numbered list
plus typed input when they are not: piped stdin, a script, another program.
The degradation is decided INSIDE each widget, so a caller has exactly one code
path and never branches on terminal capability; in the typed-input mode not one
ANSI escape byte is written, so captured output stays plain text.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Callable

try:  # POSIX key reading; on Windows msvcrt does the job instead
    import termios
    import tty
except ImportError:
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]

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

_MAX_ATTEMPTS = 3

# A raw-mode read fails on a terminal that will not answer (no controlling
# tty, a pty that went away). Both families are caught so the widget can drop
# to typed input instead of killing the install.
_KEY_ERRORS: tuple[type[BaseException], ...] = (
    (OSError, termios.error) if termios is not None else (OSError,)
)

# --- Mode --------------------------------------------------------------------

RICH_MODE_OVERRIDE: bool | None = None


def rich_mode() -> bool:
    """True when the arrow-key widgets are usable: both ends are a terminal.

    Assign `RICH_MODE_OVERRIDE` to force either mode under test. `isatty` is
    guarded because a closed or replaced stdin RAISES instead of answering,
    and that has to read as "not a terminal", never as a crash.
    """
    if RICH_MODE_OVERRIDE is not None:
        return RICH_MODE_OVERRIDE
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def _style(text: str, *codes: str) -> str:
    """Colour `text` only in a terminal — piped output must stay plain."""
    if not codes or not rich_mode():
        return text
    return "".join(codes) + text + RESET


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


DEFAULT_COLS = 80


def _term_cols() -> int:
    """The usable terminal width, ALWAYS at least 1.

    A pty whose window size was never set reports 0 columns rather than
    raising — a freshly forked pty, some CI runners, a detached multiplexer
    pane. Zero is not a width, and every caller divides by this number, so the
    floor is applied HERE, at the one place the value is born, instead of in
    each consumer.
    """
    try:
        cols = os.get_terminal_size().columns
    except (AttributeError, ValueError, OSError):
        return DEFAULT_COLS
    return cols if cols > 0 else DEFAULT_COLS


def _visual_line_count(text: str, cols: int) -> int:
    """How many terminal ROWS `text` occupies once wrapping is counted."""
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
    """One keystroke, raw. Ctrl-C arrives as a byte here — raw mode disables
    the signal, so it is turned back into KeyboardInterrupt by hand.
    """
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
        # Restored on EVERY exit path, including KeyboardInterrupt: a shell
        # left in raw mode stops echoing what the human types.
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# --- Terminal-mode menu ------------------------------------------------------


class _Screen:
    """Redraws a frame in place by counting the rows the LAST frame used.

    A line wider than the terminal occupies several rows, so moving the cursor
    up by the line count would leave the previous frame's tail on screen. Every
    frame is therefore measured, not counted.
    """

    def __init__(self) -> None:
        self._rows = 0

    def draw(self, output: str) -> None:
        cols = _term_cols()
        if self._rows > 0:
            sys.stdout.write(f"\033[{self._rows - 1}A\r")
        sys.stdout.write(CLEAR_TO_END)
        sys.stdout.write(output)
        sys.stdout.flush()
        self._rows = _visual_line_count(output, cols)


def _disabled_note(radio: bool) -> str:
    return " (unavailable)" if radio else " (always installed)"


def _rich_menu(
    title: str,
    items: list[dict[str, Any]],
    *,
    radio: bool,
    selected: list[bool],
    disabled: list[bool],
    cursor: int,
    min_selected: int,
    detail_callback: Callable[[int], str] | None,
) -> tuple[int, list[bool]]:
    """The arrow-key loop behind both `checkbox` and `select_one`.

    `radio` is the only difference between the two widgets, so they share one
    loop rather than one each: in radio mode the cursor IS the answer, space
    and toggle-all are inert, and the marker is a radio button.
    """
    _ensure_ansi()
    screen = _Screen()

    def build() -> str:
        if radio:
            for i in range(len(items)):
                selected[i] = i == cursor
        keys = "up/down move | "
        keys += "enter choose" if radio else "space toggle | enter confirm"
        if detail_callback:
            keys += " | i info"
        if not radio:
            keys += " | a all"

        lines = [_style(title, BOLD), _style(f"  {keys}", DIM)]
        for i, item in enumerate(items):
            prefix = _style(">", CYAN) + " " if i == cursor else "  "
            label = item["label"]
            if radio:
                box = "(o)" if selected[i] else "( )"
            else:
                box = "[ ]"
                if selected[i]:
                    box = _style("[x]", GREEN)
            if disabled[i]:
                box = _style("[x]" if not radio else "( )", DIM)
                label = _style(label + _disabled_note(radio), DIM)
            hint = "  " + _style(item["hint"], DIM) if item.get("hint") else ""
            lines.append(f"{prefix}{box} {label}{hint}")
        return "\n".join(lines)

    sys.stdout.write(HIDE_CURSOR)
    try:
        screen.draw(build())
        while True:
            key = _read_key()
            if key == KEY_UP:
                cursor = (cursor - 1) % len(items)
            elif key == KEY_DOWN:
                cursor = (cursor + 1) % len(items)
            elif key == KEY_SPACE and not radio:
                if not disabled[cursor]:
                    selected[cursor] = not selected[cursor]
            elif key in ("i", "?") and detail_callback:
                screen.draw(detail_callback(cursor) + "\n"
                            + _style("  Press any key to return...", DIM))
                _read_key()
            elif key == "a" and not radio:
                all_on = all(selected[i] for i in range(len(items))
                             if not disabled[i])
                for i in range(len(items)):
                    if not disabled[i]:
                        selected[i] = not all_on
            elif key == KEY_ENTER:
                if radio:
                    if not disabled[cursor]:
                        break
                elif sum(1 for s in selected if s) >= min_selected:
                    break
            screen.draw(build())
    except KeyboardInterrupt:
        raise SystemExit(1)
    finally:
        # The cursor was hidden by this function; it is shown again whatever
        # ends the loop — answer, Ctrl-C, or a failed read.
        sys.stdout.write(f"\n{SHOW_CURSOR}")
        sys.stdout.flush()
    return cursor, selected


# --- Typed-input menu --------------------------------------------------------


def _plain_list(
    title: str,
    items: list[dict[str, Any]],
    selected: list[bool],
    disabled: list[bool],
    radio: bool,
) -> None:
    print(title)
    for i, item in enumerate(items):
        if radio:
            box = "(o)" if selected[i] else "( )"
        else:
            box = "[x]" if selected[i] else "[ ]"
        label = item["label"]
        if disabled[i]:
            label += _disabled_note(radio)
        hint = f"  {item['hint']}" if item.get("hint") else ""
        print(f" {i + 1:>3}. {box} {label}{hint}")


def _parse_picks(
    raw: str,
    count: int,
    radio: bool,
    disabled: list[bool],
) -> list[int]:
    """Typed line -> indices. The message NAMES the token that failed, which
    is the only thing the human can act on when the input came from a script.
    """
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if radio and len(tokens) != 1:
        raise ValueError(f"type exactly one number, not {raw!r}")
    picks: list[int] = []
    for token in tokens:
        if not token.isdigit():
            raise ValueError(f"not a number: {token!r}")
        index = int(token) - 1
        if not 0 <= index < count:
            raise ValueError(f"no such option: {token!r}")
        if radio and disabled[index]:
            raise ValueError(f"option {token!r} cannot be chosen")
        picks.append(index)
    return picks


def _plain_menu(
    title: str,
    items: list[dict[str, Any]],
    *,
    radio: bool,
    selected: list[bool],
    disabled: list[bool],
    min_selected: int,
    default_index: int,
) -> list[int]:
    """Numbered list, one typed answer, at most `_MAX_ATTEMPTS` tries.

    The last try RAISES instead of asking a fourth time: input that is not a
    human cannot learn, so an endless loop would hang the caller forever.
    """
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        _plain_list(title, items, selected, disabled, radio)
        if radio:
            prompt = f"Select one number [blank = {default_index + 1}]: "
        else:
            prompt = ("Select numbers (comma-separated, blank keeps the "
                      "current selection): ")
        try:
            raw = input(prompt).strip()
        except EOFError:
            # Input ran out: read it as the blank answer, which keeps what is
            # already selected. The caller still gets an answer.
            print()
            raw = ""
        if not raw:
            if radio:
                return [default_index]
            return [i for i, s in enumerate(selected) if s]

        try:
            picks = _parse_picks(raw, len(items), radio, disabled)
        except ValueError as exc:
            if attempt == _MAX_ATTEMPTS:
                raise
            print(f"  {exc}")
            continue
        if radio:
            return picks

        # A disabled item is installed whatever the human typed.
        chosen = sorted(set(picks) | {i for i, d in enumerate(disabled) if d})
        if len(chosen) < min_selected:
            message = f"select at least {min_selected} option(s)"
            if attempt == _MAX_ATTEMPTS:
                raise ValueError(message)
            print(f"  {message}")
            continue
        return chosen


# --- Widgets -----------------------------------------------------------------


def checkbox(
    title: str,
    items: list[dict[str, Any]],
    *,
    min_selected: int = 0,
    detail_callback: Callable[[int], str] | None = None,
) -> list[int]:
    """Multi-select. Returns the selected indices.

    Each item in `items` is a dict:
        label       — display text (required)
        selected    — initial state (default False)
        disabled    — cannot be toggled, always returned (default False)
        hint        — right-side hint text (optional)

    Terminal keys:
        UP/DOWN   navigate
        SPACE     toggle
        ENTER     confirm (if >= min_selected checked)
        a         toggle all non-disabled items
        i / ?     show details (if detail_callback provided)

    Without a terminal the same question is asked as a numbered list
    read from stdin, and Ctrl-C is left to propagate untouched.
    """
    disabled = [bool(item.get("disabled", False)) for item in items]
    selected = [bool(item.get("selected", False)) or disabled[i]
                for i, item in enumerate(items)]
    if rich_mode():
        try:
            _, selected = _rich_menu(
                title, items, radio=False, selected=selected,
                disabled=disabled, cursor=0, min_selected=min_selected,
                detail_callback=detail_callback)
            return [i for i, s in enumerate(selected) if s]
        except _KEY_ERRORS:
            pass
    return _plain_menu(title, items, radio=False, selected=selected,
                       disabled=disabled, min_selected=min_selected,
                       default_index=0)


def select_one(
    title: str,
    items: list[dict[str, Any]],
    *,
    default_index: int = 0,
    detail_callback: Callable[[int], str] | None = None,
) -> int:
    """Single choice. Returns the chosen index.

    Same `items` shape as `checkbox`; `selected` is ignored — `default_index`
    is where the cursor starts and what a blank typed answer means. A disabled
    item is shown but cannot be chosen.
    """
    disabled = [bool(item.get("disabled", False)) for item in items]
    selected = [i == default_index for i in range(len(items))]
    if rich_mode():
        try:
            cursor, _ = _rich_menu(
                title, items, radio=True, selected=selected,
                disabled=disabled, cursor=default_index, min_selected=1,
                detail_callback=detail_callback)
            return cursor
        except _KEY_ERRORS:
            pass
    return _plain_menu(title, items, radio=True, selected=selected,
                       disabled=disabled, min_selected=1,
                       default_index=default_index)[0]


def confirm(prompt: str, *, default: bool = True) -> bool:
    """Yes/no. Input that ran out (EOF) answers with `default`."""
    if rich_mode():
        _ensure_ansi()
    hint = "Y/n" if default else "y/N"
    sys.stdout.write(f"{prompt} [{hint}]: ")
    sys.stdout.flush()
    try:
        response = input().strip().lower()
    except EOFError:
        print()
        return default
    if not response:
        return default
    return response in ("y", "yes")


def text_input(
    prompt: str,
    *,
    default: str = "",
    allow_empty: bool = False,
    validator: Callable[[str], str | None] | None = None,
) -> str:
    """One line of text. `validator` returns an error message, or None to pass.

    EOF answers with `default` where there is one, and with `""` where
    `allow_empty` is set — the same as a blank typed line. With neither there
    is no answer to give, so it raises rather than returning a value nobody
    chose.
    """
    if rich_mode():
        _ensure_ansi()
    while True:
        if default:
            sys.stdout.write(f"{prompt} [{_style(default, DIM)}]: ")
        else:
            sys.stdout.write(f"{prompt}: ")
        sys.stdout.flush()
        try:
            value = input().strip()
        except EOFError:
            print()
            if default:
                return default
            if allow_empty:
                return ""
            raise ValueError(f"no answer for {prompt!r} and no default")
        if not value and default:
            value = default
        if not value:
            if allow_empty:
                return ""
            print(f"  {_style('Value required.', YELLOW)}")
            continue
        if validator:
            error = validator(value)
            if error:
                print(f"  {_style(error, YELLOW)}")
                continue
        return value
