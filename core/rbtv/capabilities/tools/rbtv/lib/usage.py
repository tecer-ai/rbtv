"""Plan usage of provider accounts: the readers, the parsers and the two views.

Each key is sent only to its own provider's usage address, the one
providers.json names. A stored token is never refreshed here: an expired one is
reported as expired, never shown as an empty or 0% window. Nothing here prints
a key or a token; a failed read carries the error's class name only.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from . import present, providers, tui

TIMEOUT = 10
INTERVAL_DEFAULT = 120
INTERVAL_MIN = 30
_ANSI = re.compile(r"\033\[[0-9;]*m")


def get_json(url: str, headers: dict) -> dict:
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as reply:
        return json.loads(reply.read().decode("utf-8"))


# --- parsers: pure ------------------------------------------------------------


def fmt_epoch(epoch) -> str:
    try:
        when = datetime.fromtimestamp(int(epoch))
    except (TypeError, ValueError, OSError):
        return ""
    return when.strftime("%H:%M" if when.date() == datetime.now().date() else "%a %H:%M")


def iso_epoch(stamp) -> int | None:
    try:
        return int(datetime.fromisoformat(stamp).timestamp())
    except (TypeError, ValueError):
        return None


def parse_zai(reply: dict) -> dict:
    """data.limits[] TOKENS_LIMIT rows: unit 3 number 5 is the 5-hour window,
    unit 6 the weekly one; `percentage` is used percent, nextResetTime is in
    milliseconds; data.level is the plan."""
    data = reply.get("data") or {}
    windows = []
    for limit in data.get("limits") or []:
        if limit.get("type") != "TOKENS_LIMIT" or limit.get("percentage") is None:
            continue
        unit, number = limit.get("unit"), limit.get("number")
        label = "5h" if (unit == 3 and number == 5) else ("7d" if unit == 6 else f"u{unit}n{number}")
        reset = limit.get("nextResetTime")
        windows.append({"label": label, "pct": float(limit["percentage"]),
                        "resets_at": int(reset / 1000) if reset else None})
    if not windows:
        return {"error": "no TOKENS_LIMIT windows"}
    return {"windows": windows, "plan": data.get("level")}


def parse_deepseek(reply: dict) -> dict:
    infos = reply.get("balance_infos") or []
    if not infos:
        return {"error": "no balance_infos"}
    return {"balance": infos[0].get("total_balance"), "currency": infos[0].get("currency")}


def _kimi_window(detail: dict, label: str) -> dict | None:
    """One {limit, used, resetTime} block. The counts arrive as strings."""
    try:
        limit, used = int(detail["limit"]), int(detail["used"])
    except (KeyError, TypeError, ValueError):
        return None
    if limit <= 0:
        return None
    return {"label": label, "pct": round(100.0 * used / limit, 1),
            "resets_at": iso_epoch(detail.get("resetTime"))}


def parse_kimi(reply: dict) -> dict:
    """`limits[]` rows each carry a `window` (duration and timeUnit) and a
    `detail` counter; the top-level `usage` is the plan-wide counter, whose
    window the reply does not name."""
    windows = []
    for row in reply.get("limits") or []:
        window = row.get("window") or {}
        minutes = (window.get("duration") or 0) * (60 if window.get("timeUnit") == "TIME_UNIT_HOUR" else 1)
        label = (f"{minutes // 60}h" if minutes and minutes % 60 == 0
                 else f"{minutes}m" if minutes else "window")
        found = _kimi_window(row.get("detail") or {}, label)
        if found:
            windows.append(found)
    plan = _kimi_window(reply.get("usage") or {}, "plan")
    if plan:
        windows.append(plan)
    return {"windows": windows} if windows else {"error": "no usage rows"}


def parse_claude(reply: dict) -> dict:
    """limits[] rows: session, weekly_all, and weekly_scoped (one model's
    share of the weekly window, named by scope.model.display_name)."""
    windows = []
    for limit in reply.get("limits") or []:
        pct, kind = limit.get("percent"), limit.get("kind")
        if pct is None:
            continue
        if kind == "weekly_scoped":
            scope = ((limit.get("scope") or {}).get("model") or {}).get("display_name")
            label = f"7d {(scope or 'scoped').lower()}"
        else:
            label = {"session": "5h", "weekly_all": "7d"}.get(kind, kind or "?")
        windows.append({"label": label, "pct": float(pct),
                        "resets_at": iso_epoch(limit.get("resets_at"))})
    return {"windows": windows, "fresh": True} if windows else {"error": "no windows returned"}


def _codex_windows(limits: dict) -> list[dict]:
    windows = []
    for name in ("primary", "secondary"):
        window = limits.get(name)
        if isinstance(window, dict) and window.get("used_percent") is not None:
            minutes = window.get("window_minutes") or 0
            label = "5h" if minutes <= 360 else ("7d" if minutes >= 10000 else f"{minutes}m")
            windows.append({"label": label, "pct": float(window["used_percent"]),
                            "resets_at": window.get("resets_at")})
    return windows


def parse_codex_sessions(sessions: Path, max_files: int = 5) -> dict:
    """The last rate_limits record of the newest session file that holds one."""
    try:
        files = sorted(sessions.glob("*/*/*/rollout-*.jsonl"),
                       key=lambda path: path.stat().st_mtime, reverse=True)
    except OSError:
        return {"error": "no sessions folder"}
    for path in files[:max_files]:
        last = None
        try:
            with open(path, encoding="utf-8") as lines:
                for line in lines:
                    if "rate_limits" not in line:
                        continue
                    try:
                        limits = (json.loads(line).get("payload") or {}).get("rate_limits")
                    except (ValueError, AttributeError):
                        continue
                    if isinstance(limits, dict):
                        last = limits
        except (OSError, UnicodeDecodeError):
            continue
        if last:
            return {"windows": _codex_windows(last), "plan": last.get("plan_type"),
                    "as_of": int(path.stat().st_mtime)}
    return {"error": "no rate_limits in recent sessions"}


# --- readers ------------------------------------------------------------------

# A key provider's parser and the Authorization header its usage address takes.
KEY_ENDPOINTS = {
    "zai": (parse_zai, "{key}"),
    "deepseek": (parse_deepseek, "Bearer {key}"),
    "kimi": (parse_kimi, "Bearer {key}"),
}


def _fetch(parse, url: str, headers: dict) -> dict:
    try:
        return parse(get_json(url, headers))
    except Exception as exc:  # noqa: BLE001 - the class name only: a request holds a key
        return {"error": type(exc).__name__}


def claude_usage(url: str, credentials: dict | None, account: str | None) -> dict:
    """The windows of one claude account, read with its own stored token."""
    oauth = (credentials or {}).get("claudeAiOauth") or {}
    token, expires = oauth.get("accessToken"), oauth.get("expiresAt")
    if not token:
        return {"error": "no stored token"}
    if expires and expires / 1000 < time.time() + 60:
        return {"error": f"token expired {fmt_epoch(expires / 1000)}; run rbtv providers switch "
                         f"claude {account or 'NAME'}, start one session, then read again"}
    return _fetch(parse_claude, url, {"Authorization": f"Bearer {token}",
                                      "anthropic-beta": "oauth-2025-04-20"})


def rows(data: dict, target: Path, only: str | None, account: str | None) -> list[dict]:
    """One row per account whose usage has a source: {provider, account, live, label, data}."""
    found = []
    for name in ([only] if only else data["providers"]):
        spec = data["providers"][name]
        source, login = spec["usage"], spec.get("saved_login")
        live = providers.live_login(login) if login else None
        current = providers.live_name(target, name, login, live) if login else None
        if source.get("per_account"):
            names = providers.saved_names(target, name)
            for saved in names:
                if account in (None, saved):
                    held = live if saved == current else providers.read_saved(target, name, saved)
                    found.append({"provider": name, "account": saved, "live": saved == current,
                                  "data": claude_usage(source["url"], (held or {}).get("credentials"),
                                                       saved)})
            if live is not None and current is None and account is None:
                found.append({"provider": name, "account": None, "live": True,
                              "data": claude_usage(source["url"], live.get("credentials"), None)})
            marked = len(names) > 1
        else:
            if account not in (None, current):
                continue
            if source["source"] == "local":
                usage = parse_codex_sessions(Path(os.path.expanduser(source["path"])))
            else:
                key, _where = providers.credential(data, spec, target)
                if source["source"] == "console":
                    present = ("logged in" if spec["login"] == "account" else "key present")
                    absent = ("not logged in" if spec["login"] == "account" else "no key")
                    usage = {"note": f"{present if key else absent}; no usage source",
                             "console": source["url"]}
                elif not key:
                    usage = {"error": "no key"}
                else:
                    parse, header = KEY_ENDPOINTS[name]
                    usage = _fetch(parse, source["url"], {"Authorization": header.format(key=key)})
            found.append({"provider": name, "account": current, "live": True, "data": usage})
            marked = False
        for row in found:
            if row["provider"] == name:
                # `*` marks the live account only where there are several to tell apart.
                row["label"] = (name + (f":{row['account']}" if row["account"]
                                        else " (unsaved)" if login and live is not None else "")
                                + ("*" if row["live"] and marked else ""))
    return found


def errors(found: list[dict]) -> int:
    return sum(1 for row in found if "error" in row["data"])


# --- the plain view -----------------------------------------------------------


def _money(usage: dict) -> str:
    currency = usage.get("currency")
    return {"USD": "$", "CNY": "¥"}.get(currency, (currency or "") + " ") + str(usage["balance"])


def _renews(window: dict, usage: dict) -> str:
    """When the window renews; a figure read from local files also says how old it is."""
    text = f"renews {fmt_epoch(window['resets_at'])}" if window.get("resets_at") else ""
    if usage.get("as_of") and not usage.get("fresh"):
        text += f"{'  ' if text else ''}(as of {fmt_epoch(usage['as_of'])})"
    return text


def plain_lines(found: list[dict]) -> list[str]:
    """One line per window, balance, note or error, led by a count of unread rows."""
    width = max((len(row["label"]) for row in found), default=10)
    failed = errors(found)
    lines = [f"{failed} of {len(found)} rows could not be read."] if failed else []
    for row in found:
        usage, label = row["data"], row["label"].ljust(width)
        if usage.get("windows"):
            lines += [f"{label}  {window['label']:<10} {window['pct']:5.1f}%  "
                      f"{_renews(window, usage)}".rstrip() for window in usage["windows"]]
        elif usage.get("balance") is not None:
            lines.append(f"{label}  balance {_money(usage)}")
        elif usage.get("note"):
            lines.append(f"{label}  {usage['note']} ({usage['console']})")
        else:
            lines.append(f"{label}  ERROR: {usage.get('error', '?')}")
    return lines


# --- the full-screen view -----------------------------------------------------


def _palette() -> dict:
    """The colours of the full-screen view; none when NO_COLOR is set."""
    codes = {"bold": "1", "dim": "2", "cyan": "36", "green": "32", "yellow": "33",
             "red": "31", "off": "0"}
    plain = "NO_COLOR" in os.environ
    return {name: "" if plain else f"\033[{code}m" for name, code in codes.items()}


def _clip(line: str, width: int, off: str) -> str:
    """Cut a line to the terminal width, counting only what is displayed: a
    line that wraps pushes the top of the frame off the screen."""
    if len(_ANSI.sub("", line)) <= width:
        return line
    out, shown = "", 0
    for chunk in re.split(r"(\033\[[0-9;]*m)", line):
        if chunk.startswith("\033"):
            out += chunk
            continue
        out += chunk[:max(0, width - 1 - shown)]
        shown += len(chunk)
        if shown >= width - 1:
            break
    return out + "…" + off


def _until(epoch, now: float) -> str:
    if not epoch:
        return ""
    seconds = int(epoch - now)
    if seconds <= 0:
        return "due"
    days, hours, minutes = seconds // 86400, seconds % 86400 // 3600, seconds % 3600 // 60
    return f"in {days}d{hours}h" if days else (f"in {hours}h{minutes:02d}m" if hours else f"in {minutes}m")


def posh_lines(found: list[dict], cols: int, read_at: float, now: float | None = None) -> list[str]:
    """One frame: a bar per window, with a countdown that moves between reads."""
    now = time.time() if now is None else now
    c = _palette()
    age = int(now - read_at)
    lines = [f"{c['bold']}rbtv providers usage{c['off']} · {datetime.now():%H:%M:%S} · {c['dim']}read "
             + (f"{age}s" if age < 90 else f"{age // 60}m") + f" ago{c['off']}", ""]
    label_w = max((len(row["label"]) for row in found), default=16)
    bar_w = max(8, min(34, cols - label_w - 36))
    for row in found:
        usage = row["data"]
        # Pad the plain label, then colour it.
        base = f"{c['cyan'] if row['live'] else c['dim']}{row['label'].ljust(label_w)}{c['off']}"
        if usage.get("windows"):
            for window in usage["windows"]:
                pct = window["pct"]
                filled = max(0, min(bar_w, round(pct / 100 * bar_w)))
                colour = c["green"] if pct < 60 else (c["yellow"] if pct < 85 else c["red"])
                bar = f"{colour}{'█' * filled}{c['dim']}{'░' * (bar_w - filled)}{c['off']}"
                lines.append(f"  {base} {window['label']:<9} {bar} {pct:5.1f}%  "
                             f"{c['dim']}{_until(window.get('resets_at'), now)}{c['off']}".rstrip())
        elif usage.get("balance") is not None:
            lines.append(f"  {base} {c['green']}balance {_money(usage)}{c['off']}")
        elif usage.get("note"):
            lines.append(f"  {base} {c['yellow']}{usage['note']}{c['off']} "
                         f"{c['dim']}({usage['console']}){c['off']}")
        else:
            lines.append(f"  {base} {c['red']}{usage.get('error', '?')}{c['off']}")
    lines += ["", f"{c['dim']}ctrl-c to exit{c['off']}"]
    return [_clip(line, cols, c["off"]) for line in lines]


def run_posh(read, interval: int) -> int:
    """Redraw every second and call `read()` again every `interval` seconds,
    until Ctrl-C, which ends the view as a success."""
    tui._ensure_ansi()
    read_at, found = 0.0, []
    try:
        while True:
            if time.time() - read_at > interval:
                found, read_at = read(), time.time()
            cols = shutil.get_terminal_size((100, 40)).columns
            sys.stdout.write("\033[H\033[2J" + "\n".join(posh_lines(found, cols, read_at)))
            sys.stdout.flush()
            time.sleep(1)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
    return 0


def command(args, data: dict, target: Path) -> int:
    """`rbtv providers usage`: check the arguments, read the rows, print them."""
    name, account, as_json = args.provider, args.account, bool(args.json)
    if name is not None:
        spec = providers.provider(data, name, "usage")
        if account is not None and "saved_login" not in spec:
            raise providers.usage_refusal(f"{name} holds one key, so it has no account names",
                                   f"rbtv providers usage {name}")
    if args.interval is not None and not args.posh:
        raise providers.usage_refusal("--interval is valid only with --posh", "rbtv providers usage -h")
    interval = INTERVAL_DEFAULT if args.interval is None else args.interval
    if interval < INTERVAL_MIN:
        raise providers.usage_refusal(f"--interval must be {INTERVAL_MIN} seconds or more",
                               "rbtv providers usage -h")
    if args.posh and as_json:
        raise providers.usage_refusal("--posh draws a full-screen view; it has no --json output",
                               "rbtv providers usage --json")
    if args.posh and not tui.rich_mode():
        raise providers.usage_refusal("--posh needs a terminal", "rbtv providers usage")

    def read() -> list[dict]:
        return rows(data, target, name, account)

    if args.posh:
        return run_posh(read, interval)
    found = read()
    if not found:
        names = providers.saved_names(target, name)
        raise providers.usage_refusal(f"no {name} usage row is named {account!r}. "
                               f"Saved names: {', '.join(names) or 'none'}",
                               f"rbtv providers list {name}")
    if as_json:
        print(json.dumps({"ok": True, "installation": str(target), "rows": found,
                          "errors": errors(found), "next": "rbtv providers list"},
                         indent=2))
    else:
        print(present.title("providers usage"))
        print()
        print("\n".join(plain_lines(found)))
    return 0
