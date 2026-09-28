#!/usr/bin/env python3
"""statusline-usage — Claude Code statusline script that also persists plan usage.

Claude Code invokes this on every statusline refresh, piping the session payload JSON to stdin
(configured in .claude/settings.local.json under "statusLine"). Two jobs:

1. Print the status line: model | cwd | plan windows (5h / 7d, plus any model-specific window
   the payload carries, e.g. a weekly Opus/Fable window).
2. Persist the plan-usage block for the team-kit control panel: any live Claude session keeps
   ~/.claude/rbtv-runtime/plan-usage.{json,txt} fresh, and `tmux-overview` renders the .txt.
3. Persist the session's pid map: ~/.claude/rbtv-runtime/session-pids/<session_id>.json with
   {pid, transcript, ts} — pid is the claude ANCESTOR process of this script. ctx-monitor
   (rbtv orchestration CLI) reads it to map a tmux pane's claude process to its EXACT
   transcript, which no cwd heuristic can do when sessions share a working directory.

Plan windows come from the payload's `rate_limits` object (subscription plans only; populated
after the session's first API response). No credentials are read — the payload is pushed to us.

Self-check:  echo '<sample payload json>' | python3 statusline-usage.py
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

RUNTIME = Path.home() / ".claude" / "rbtv-runtime"
LABELS = {"five_hour": "5h", "seven_day": "7d(all)"}


def account_tag():
    """Multi-account support: sessions run under a non-default CLAUDE_CONFIG_DIR (e.g.
    ~/.claude-tecer) get their usage persisted to plan-usage-<tag>.json so each account's
    windows are tracked separately. Default dir -> no tag (plan-usage.json, unchanged)."""
    cfg = os.environ.get("CLAUDE_CONFIG_DIR", "")
    if not cfg:
        return ""
    p = Path(cfg).expanduser()
    try:
        if p.resolve() == (Path.home() / ".claude").resolve():
            return ""
    except OSError:
        pass
    name = p.name.lstrip(".")
    name = name[len("claude-"):] if name.startswith("claude-") else name
    return "-" + (name or "alt")


def label_for(key):
    if key in LABELS:
        return LABELS[key]
    # e.g. seven_day_opus -> 7d(opus), seven_day_sonnet -> 7d(sonnet)
    if key.startswith("seven_day_"):
        return f"7d({key[len('seven_day_'):]})"
    if key.startswith("five_hour_"):
        return f"5h({key[len('five_hour_'):]})"
    return key


def fmt_reset(epoch):
    try:
        dt = datetime.fromtimestamp(int(epoch))
    except (TypeError, ValueError, OSError):
        return ""
    # plain ASCII — the U+2192 arrow renders double-width/broken in ambiguous-width fonts
    if dt.date() == datetime.now().date():
        return dt.strftime(" renews %H:%M")
    return dt.strftime(" renews %a %H:%M")


def render_windows(rate_limits):
    parts = []
    for key, win in (rate_limits or {}).items():
        if not isinstance(win, dict):
            continue
        pct = win.get("used_percentage")
        if pct is None:
            continue
        reset = fmt_reset(win.get("resets_at"))
        parts.append(f"{label_for(key)} {round(pct)}%{reset}")
    return " · ".join(parts)


def claude_ancestor_pid():
    """Walk /proc parents from this script to the claude process that spawned the statusline
    (there may be a shell in between). None off-Linux or when no claude ancestor exists."""
    pid = os.getpid()
    for _ in range(8):
        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
            ppid = int(stat.rsplit(")", 1)[1].split()[1])
            comm = Path(f"/proc/{ppid}/comm").read_text().strip()
        except (OSError, ValueError, IndexError):
            return None
        if comm == "claude" or comm.startswith("claude"):
            return ppid
        if ppid <= 1:
            return None
        pid = ppid
    return None


def persist_session_pid(payload):
    """Best-effort per-session record for ctx-monitor: pid, transcript, and the payload's
    EXACT context_window block (size/used%/token totals — the same numbers /context shows,
    which no outside heuristic can compute because the window size is plan-dependent).
    Prunes records older than 7 days. Never breaks the status line."""
    sid = payload.get("session_id")
    transcript = payload.get("transcript_path")
    if not sid or not transcript:
        return
    pid = claude_ancestor_pid()
    if not pid:
        return
    try:
        d = RUNTIME / "session-pids"
        d.mkdir(parents=True, exist_ok=True)
        now = time.time()
        rec = {"pid": pid, "transcript": transcript, "ts": int(now),
               "model": (payload.get("model") or {}).get("id")}
        cw = payload.get("context_window") or {}
        if cw.get("context_window_size"):
            rec["ctx"] = {"window": cw.get("context_window_size"),
                          "tokens": cw.get("total_input_tokens"),
                          "pct": cw.get("used_percentage")}
        tmp = d / f"{sid}.json.tmp"
        tmp.write_text(json.dumps(rec), encoding="utf-8")
        os.replace(tmp, d / f"{sid}.json")
        for old in d.glob("*.json"):
            try:
                if now - old.stat().st_mtime > 7 * 86400:
                    old.unlink()
            except OSError:
                pass
    except OSError:
        pass


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}
    persist_session_pid(payload)
    model = ((payload.get("model") or {}).get("display_name")
             or (payload.get("model") or {}).get("id") or "claude")
    cwd = os.path.basename((payload.get("workspace") or {}).get("current_dir")
                           or payload.get("cwd") or "")
    usage = render_windows(payload.get("rate_limits"))

    # Persist for the control panel — best-effort, never break the status line.
    if usage:
        try:
            tag = account_tag()
            RUNTIME.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%H:%M")
            tmp = RUNTIME / f"plan-usage{tag}.txt.tmp"
            tmp.write_text(f"{usage}   (reported {stamp})\n", encoding="utf-8")
            os.replace(tmp, RUNTIME / f"plan-usage{tag}.txt")
            tmpj = RUNTIME / f"plan-usage{tag}.json.tmp"
            tmpj.write_text(json.dumps({"ts": int(time.time()),
                                        "rate_limits": payload.get("rate_limits")}),
                            encoding="utf-8")
            os.replace(tmpj, RUNTIME / f"plan-usage{tag}.json")
        except OSError:
            pass

    bits = [model]
    if cwd:
        bits.append(cwd)
    bits.append(usage or "plan: n/a yet")
    print(" | ".join(bits))


if __name__ == "__main__":
    main()
