#!/usr/bin/env python3
"""overview-compact — one dashboard frame for the control panel's overview strip.

Invoked by `tmux-overview --compact` on every refresh. Renders ≤7 lines using the FULL pane
width, two blocks side by side:

  left  — session totals + Claude plan-usage BAR CHARTS (5h session window, 7d all-models,
          plus any model-specific window the statusline payload reports), colored by headroom
          (green <60%, yellow <85%, red ≥85%), with reset times and data age.
  right — every tmux window with its member SEAT NAMES. Pane titles are unreliable for claude
          panes (the TUI rewrites them with status text), so names resolve pane-id → agent from
          the run package's coordination/workers.md roster when --package is given; fallback is
          the cleaned pane title.

Usage: overview-compact.py <session> [--package <run-package>] [--width N]
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BAR_W = 22
LEFT_W = 58
LABELS = {"five_hour": "claude 5h", "seven_day": "claude 7d"}
GREEN, YELLOW, RED, DIM, BOLD, OFF = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"
UL = "\033[4m"
NO_API = f"{YELLOW}no usage API{OFF} {DIM}>{OFF} sakana"


def tmux_lines(*args):
    r = subprocess.run(["tmux", *args], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def label_for(key):
    if key in LABELS:
        return LABELS[key]
    if key.startswith("seven_day_"):
        return f"cl 7d {key[len('seven_day_'):]}"
    if key.startswith("five_hour_"):
        return f"cl 5h {key[len('five_hour_'):]}"
    return key


def provider_rows():
    """([(label, pct, reset, note)], footer_text) from provider-usage.json (see
    provider-usage.py: Z.AI + codex plan windows, DeepSeek balance, Sakana console-only)."""
    p = Path.home() / ".claude" / "rbtv-runtime" / "provider-usage.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], f"{DIM}providers: no data yet (provider-usage.py has not run){OFF}"
    rows = []
    for w in (d.get("zai") or {}).get("windows", []):
        rows.append((f"glm {w['label']}", float(w["pct"]), fmt_reset(w.get("resets_at")), ""))
    cx = d.get("codex") or {}
    note = ""
    as_of = cx.get("as_of")
    if as_of and datetime.now().timestamp() - as_of > 5400:  # >90 min: snapshot, not live
        note = f"as of {datetime.fromtimestamp(as_of).strftime('%a %H:%M')}"
    for w in cx.get("windows", []):
        rows.append((f"codex {w['label']}", float(w["pct"]),
                     note or fmt_reset(w.get("resets_at")), ""))
    ds = d.get("deepseek") or {}
    bits = []
    if ds.get("balance") is not None:
        cur = {"USD": "$", "CNY": "¥"}.get(ds.get("currency"), ds.get("currency") or "")
        bits.append(f"deepseek {cur}{ds['balance']} left")
    elif ds.get("error"):
        bits.append(f"deepseek: {ds['error']}")
    return rows, f"{DIM}{' · '.join(bits)}{OFF}  " + NO_API


def fmt_reset(epoch):
    try:
        dt = datetime.fromtimestamp(int(epoch))
    except (TypeError, ValueError, OSError):
        return ""
    if dt.date() == datetime.now().date():
        return dt.strftime("%H:%M")
    return dt.strftime("%a %H:%M")


def bar(pct):
    filled = max(0, min(BAR_W, round(pct / 100 * BAR_W)))
    color = GREEN if pct < 60 else (YELLOW if pct < 85 else RED)
    return f"{color}{'█' * filled}{DIM}{'░' * (BAR_W - filled)}{OFF}"


def plan_block():
    """[(label, pct, reset)], age_minutes — from the statusline-persisted JSON."""
    p = Path.home() / ".claude" / "rbtv-runtime" / "plan-usage.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], None
    rows = []
    for key, win in (d.get("rate_limits") or {}).items():
        if isinstance(win, dict) and win.get("used_percentage") is not None:
            rows.append((label_for(key), float(win["used_percentage"]),
                         fmt_reset(win.get("resets_at"))))
    age = None
    if d.get("ts"):
        age = max(0, int((datetime.now().timestamp() - d["ts"]) // 60))
    return rows, age


def roster_map(package):
    """pane-id -> agent name, from the run package's active roster rows."""
    out = {}
    if not package:
        return out
    path = Path(package) / "coordination" / "workers.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for m in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*yes\s*\|\s*(%\d+)\s*\|", text, re.M):
        out[m.group(2)] = m.group(1)
    return out


BUSY_GLYPHS = r"[⠀-⣿✳✻✽✶✢]"  # frozen title spinner != activity; CHANGE across two samples is
SHELLS = {"bash", "zsh", "sh", "fish", "dash"}  # pane_current_command = shell -> harness exited
# the honest, harness-agnostic working signal (spinner cycling / tokens streaming / tool output).
BUSY_SAMPLE_GAP = 0.6


def pane_signature(pane):
    r = subprocess.run(["tmux", "capture-pane", "-p", "-t", pane],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    return "\n".join(r.stdout.splitlines()[-8:])


def busy_panes(pids, gap=BUSY_SAMPLE_GAP):
    if not pids:
        return set()
    a = {pid: pane_signature(pid) for pid in pids}
    time.sleep(gap)
    b = {pid: pane_signature(pid) for pid in pids}
    return {pid for pid in pids if a.get(pid) and a[pid] != b.get(pid)}


def clean_title(title):
    t = re.sub(BUSY_GLYPHS, "", title or "").strip()
    return (t[:18] + "~") if len(t) > 19 else (t or "?")


def window_entries(session, roster):
    wins = []
    for ln in tmux_lines("list-windows", "-t", session, "-F",
                         "#{window_index}\t#{window_name}\t#{window_active}"):
        idx, name, active = ln.split("\t")
        wins.append({"idx": idx, "name": name, "active": active == "1", "panes": []})
    by_idx = {w["idx"]: w for w in wins}
    rows = []
    for ln in tmux_lines("list-panes", "-s", "-t", session, "-F",
                         "#{window_index}\t#{pane_id}\t#{pane_current_command}\t#{pane_title}"):
        idx, pid, cmd, title = ln.split("\t", 3)
        if idx in by_idx:
            rows.append((idx, pid, cmd, title))
    working = busy_panes([pid for _i, pid, cmd, _t in rows if cmd not in SHELLS])
    for idx, pid, cmd, title in rows:
        name = roster.get(pid) or clean_title(title)
        if cmd in SHELLS:
            name = f"{DIM}{name}{OFF}"
        elif pid in working:
            name += "+"
        by_idx[idx]["panes"].append(name)
    return wins, len(wins), sum(len(w["panes"]) for w in wins)




LEGEND = f"{DIM}+ working · ~ name cut · * active window{OFF}"


def pad_to(s, width):
    return s + " " * max(0, width - visible_len(s))


def window_grid(wins, width, max_rows):
    """Windows as ASCII columns: window name as header (bold), panes stacked beneath."""
    cols = []
    for w in wins:
        header = ("*" if w["active"] else "") + w["name"]
        panes = list(w["panes"]) or ["-"]
        colw = max([len(header)] + [len(p) for p in panes])
        cols.append((header, panes, colw))
    banks, bank, used = [], [], 0
    for c in cols:
        need = c[2] + 2
        if bank and used + need > width:
            banks.append(bank)
            bank, used = [], 0
        bank.append(c)
        used += need
    if bank:
        banks.append(bank)
    lines, shown = [], 0
    for bank in banks:
        depth = max(len(p) for _h, p, _w in bank)
        need = 1 + depth + (1 if lines else 0)
        if lines and len(lines) + need > max_rows:
            break
        if lines:
            lines.append("")
        lines.append("".join(pad_to(f"{BOLD}{UL}{h}{OFF}", w + 2) for h, _p, w in bank))
        for r in range(depth):
            lines.append("".join(pad_to(p[r] if r < len(p) else "", w + 2)
                                 for _h, p, w in bank))
        lines = lines[:max_rows]
        shown += len(bank)
    if shown < len(cols):
        lines.append(f"{DIM}(+{len(cols) - shown} more windows){OFF}")
    return lines[:max_rows]


def flow(tokens, width, max_lines):
    lines, cur = [], ""
    for t in tokens:
        cand = t if not cur else f"{cur}   {t}"
        if len(cand) <= width or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = t
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        dropped = sum(1 for _ in lines[max_lines:])
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:max(0, width - 12)] + f" {DIM}(+{dropped} more){OFF}"
    return lines


def visible_len(s):
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--package", default="")
    ap.add_argument("--width", type=int, default=220)
    a = ap.parse_args()

    roster = roster_map(a.package)
    wins, nwin, npane = window_entries(a.session, roster)
    plan, age = plan_block()

    prows, footer = provider_rows()
    session = f"{BOLD}{a.session}{OFF} · {nwin} windows · {npane} panes · {datetime.now().strftime('%H:%M:%S')}"
    left = []
    bars = []
    if plan:
        stale = f"  {DIM}({age}m old){OFF}" if age is not None and age > 15 else ""
        for i, (label, pct, reset) in enumerate(plan):
            bars.append((label, pct, reset, stale if i == 0 else ""))
    else:
        left.append(f"{DIM}claude: no data yet (needs one statusline refresh){OFF}")
    bars.extend(prows)
    for label, pct, reset, note in bars[:5]:
        left.append(f"{label:<10} {bar(pct)} {pct:3.0f}%"
                    + (f" {DIM}{reset if reset.startswith('as of') else 'renews ' + reset}{OFF}"
                       if reset else "") + note)
    left.append(footer)

    # Row 0: session stats (own line). Row 1: the two table titles (bold+underlined, each
    # clearly scoped). Rows 2+: the tables. So the session line is never read as a table header.
    limits_hdr = f"{BOLD}{UL}PLAN LIMITS{OFF}"
    windows_hdr = f"{BOLD}{UL}WINDOWS · PANES{OFF}"
    right_w = a.width - LEFT_W - 3
    print(session)
    if right_w >= 40:
        right = window_grid(wins, right_w, max_rows=6)
        print(f"{limits_hdr}{' ' * max(0, LEFT_W - visible_len(limits_hdr))}{DIM}|{OFF} {windows_hdr}")
        for i in range(max(len(left), len(right))):
            lseg = left[i] if i < len(left) else ""
            pad = " " * max(0, LEFT_W - visible_len(lseg))
            rseg = right[i] if i < len(right) else ""
            print(f"{lseg}{pad}{DIM}|{OFF} {rseg}")
    else:  # narrow pane: stack, each table under its own header
        print(limits_hdr)
        for ln in left:
            print(ln)
        print(windows_hdr)
        for ln in window_grid(wins, a.width, max_rows=max(1, 5 - len(left))):
            print(ln)


if __name__ == "__main__":
    main()
