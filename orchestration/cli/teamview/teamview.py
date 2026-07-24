#!/usr/bin/env python3
"""teamview — responsive tmux team-run dashboard: session windows/panes + provider plan limits.

One screen for a multi-agent tmux run: what seats are running where, and how much headroom
every AI provider account has. Generalized — nothing user- or workspace-specific is baked in:

  * Session: defaults to the tmux session teamview runs INSIDE (any session works); override
    with a positional session name. Windows and panes are listed live; pane -> agent names
    resolve from a team-kit run package's roster (`--package`, optional) because agent TUIs
    rewrite their own pane titles.
  * Accounts: a config file (default ~/.config/rbtv/teamview.json, env RBTV_TEAMVIEW_CONFIG)
    declares any number of accounts per provider; with no config, accounts are auto-discovered
    from the harness credential stores present on the machine. The account a harness actually
    uses (harness-backed source) is highlighted as IN USE; extra accounts render dim.
  * Layout: responsive to the pane it runs in — full-screen view, wide-short strip (bars fold
    into columns), narrow-tall stack, and a tiny 1/6-screen mode.

Providers and their usage sources (read-only; keys are never printed, and are sent ONLY to
that provider's own documented endpoint):

  claude    statusline-persisted rate_limits file (pushed by a Claude Code statusline script;
            path per account, default ~/.claude/rbtv-runtime/plan-usage.json)  -> 5h/7d bars
  codex     LOCAL parse of ~/.codex/sessions rollout files' payload.rate_limits -> plan bars
            (fresh only while a codex session runs; staleness shown as "as of", never hidden)
  zai       GET https://api.z.ai/api/monitor/usage/quota/limit (Authorization: <key>, no
            Bearer) -> 5h + weekly used-% bars + plan tier
  deepseek  GET https://api.deepseek.com/user/balance (Bearer) -> money balance (no windows)
  kimi      subscription login (~/.kimi/credentials) has no usage endpoint -> login state;
            a Moonshot API-key account uses GET /v1/users/me/balance (api.moonshot.ai|.cn)
  google    no usage-read endpoint -> account presence + console pointer (aistudio)
  sakana    no balance endpoint (checked 2026-07-24) -> account presence + console pointer

Config file shape (all fields optional except provider; `source.type` one of
opencode | env | file | statusline | codex-local | kimi-local | none):

  {"accounts": [
     {"provider": "zai",      "name": "main", "source": {"type": "opencode"}},
     {"provider": "zai",      "name": "alt",  "source": {"type": "env", "var": "ZAI_KEY_ALT"}},
     {"provider": "deepseek", "name": "main", "source": {"type": "opencode"}},
     {"provider": "claude",   "name": "main", "source": {"type": "statusline",
                                              "path": "~/.claude/rbtv-runtime/plan-usage.json"}},
     {"provider": "codex",    "name": "main", "source": {"type": "codex-local"}},
     {"provider": "kimi",     "name": "api",  "source": {"type": "env", "var": "MOONSHOT_API_KEY"}}
  ]}

Usage:
  teamview [session] [--package DIR] [--once] [--interval N] [--config PATH]
           [--refresh] [--provider-ttl SECS] [--width N] [--height N]
  teamview --poll-providers [--config PATH]     # fetch + cache only (the loop spawns this)
  teamview --selftest

Provider data is cached at ~/.cache/rbtv/teamview-providers.json and re-polled in the
background when older than --provider-ttl (default 600s). Stdlib only; no install step.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

TIMEOUT = 10
BOLD, DIM, OFF = "\033[1m", "\033[2m", "\033[0m"
GREEN, YELLOW, RED = "\033[32m", "\033[33m", "\033[31m"
CONSOLE_URLS = {"google": "aistudio.google.com", "sakana": "console.sakana.ai",
                "kimi": "kimi.com"}
OPENCODE_STORE_KEYS = {"zai": "zai-coding-plan", "deepseek": "deepseek", "sakana": "sakana",
                       "google": "google", "kimi": "moonshot"}
CLAUDE_WINDOW_LABELS = {"five_hour": "5h", "seven_day": "7d"}


def cache_file():
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "rbtv"
    return root / "teamview-providers.json"


def config_path(arg):
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("RBTV_TEAMVIEW_CONFIG")
    if env:
        return Path(env).expanduser()
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "rbtv" / "teamview.json"


# ---------- accounts ----------

def opencode_store(path=None):
    p = Path(path) if path else Path.home() / ".local" / "share" / "opencode" / "auth.json"
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def discover_accounts(home=None, opencode_path=None):
    """Default account set from whatever harness credential stores exist on this machine."""
    home = Path(home) if home else Path.home()
    acc = []
    if (home / ".claude").is_dir():
        acc.append({"provider": "claude", "name": "main",
                    "source": {"type": "statusline",
                               "path": str(home / ".claude" / "rbtv-runtime" / "plan-usage.json")}})
    # extra Claude accounts: one config dir per account (CLAUDE_CONFIG_DIR=~/.claude-<tag>);
    # the statusline script persists each account's windows to plan-usage-<tag>.json
    for extra in sorted(home.glob(".claude-*")):
        if extra.is_dir():
            tag = extra.name[len(".claude-"):] or "alt"
            acc.append({"provider": "claude", "name": tag,
                        "source": {"type": "statusline",
                                   "path": str(home / ".claude" / "rbtv-runtime"
                                               / f"plan-usage-{tag}.json")}})
    if (home / ".codex" / "sessions").is_dir():
        acc.append({"provider": "codex", "name": "main",
                    "source": {"type": "codex-local", "path": str(home / ".codex" / "sessions")}})
    store = opencode_store(opencode_path)
    for provider, store_key in OPENCODE_STORE_KEYS.items():
        if store_key in store:
            acc.append({"provider": provider, "name": "main", "source": {"type": "opencode"}})
    if (home / ".kimi" / "credentials").is_dir() and not any(a["provider"] == "kimi" for a in acc):
        acc.append({"provider": "kimi", "name": "main", "source": {"type": "kimi-local"}})
    return acc


HARNESS_BACKED = {"opencode", "codex-local", "statusline", "kimi-local"}


def load_accounts(cfg_path, home=None, opencode_path=None):
    accounts = None
    if cfg_path.is_file():
        try:
            accounts = json.load(open(cfg_path, encoding="utf-8")).get("accounts")
        except (OSError, json.JSONDecodeError) as e:
            print(f"warning: unreadable config {cfg_path}: {e}", file=sys.stderr)
    if not accounts:
        accounts = discover_accounts(home, opencode_path)
    for a in accounts:
        src = a.get("source") or {}
        if "in_use" not in a:  # harness-backed sources are what the harnesses actually read
            a["in_use"] = src.get("type") in HARNESS_BACKED
    return accounts


def resolve_key(account, opencode_path=None):
    src = account.get("source") or {}
    t = src.get("type")
    if t == "opencode":
        store_key = src.get("store_key") or OPENCODE_STORE_KEYS.get(account["provider"],
                                                                    account["provider"])
        return (opencode_store(opencode_path).get(store_key) or {}).get("key")
    if t == "env":
        return os.environ.get(src.get("var", ""))
    if t == "file":
        try:
            return Path(src["path"]).expanduser().read_text(encoding="utf-8").strip()
        except (OSError, KeyError):
            return None
    return None


# ---------- provider fetchers (parsers are pure; network isolated in fetch_account) ----------

def get_json(url, headers):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def fmt_epoch(epoch):
    try:
        dt = datetime.fromtimestamp(int(epoch))
    except (TypeError, ValueError, OSError):
        return ""
    return dt.strftime("%H:%M") if dt.date() == datetime.now().date() else dt.strftime("%a %H:%M")


def parse_zai(d):
    """Observed 2026-07-24: data.limits[] TOKENS_LIMIT entries — unit3/number5 = 5h window,
    unit6 = weekly; `percentage` = used %, nextResetTime epoch-ms; data.level = tier."""
    data = d.get("data") or {}
    windows = []
    for lim in data.get("limits") or []:
        if lim.get("type") != "TOKENS_LIMIT" or lim.get("percentage") is None:
            continue
        unit, num = lim.get("unit"), lim.get("number")
        label = "5h" if (unit == 3 and num == 5) else ("7d" if unit == 6 else f"u{unit}n{num}")
        reset = lim.get("nextResetTime")
        windows.append({"label": label, "pct": float(lim["percentage"]),
                        "resets_at": int(reset / 1000) if reset else None})
    if not windows:
        return {"error": "no TOKENS_LIMIT windows"}
    return {"windows": windows, "plan": data.get("level")}


def parse_deepseek(d):
    infos = d.get("balance_infos") or []
    if not infos:
        return {"error": "no balance_infos"}
    b = infos[0]
    return {"balance": b.get("total_balance"), "currency": b.get("currency"),
            "available": d.get("is_available")}


def parse_moonshot(d):
    data = d.get("data") or {}
    if data.get("available_balance") is None:
        return {"error": "no available_balance"}
    return {"balance": str(data["available_balance"]), "currency": "CNY"}


def parse_claude_statusline(d):
    windows = []
    for key, win in (d.get("rate_limits") or {}).items():
        if not isinstance(win, dict) or win.get("used_percentage") is None:
            continue
        label = CLAUDE_WINDOW_LABELS.get(key)
        if not label:
            for pref, short in (("seven_day_", "7d "), ("five_hour_", "5h ")):
                if key.startswith(pref):
                    label = short + key[len(pref):]
            label = label or key
        windows.append({"label": label, "pct": float(win["used_percentage"]),
                        "resets_at": win.get("resets_at")})
    if not windows:
        return {"error": "no rate_limits yet"}
    return {"windows": windows, "as_of": d.get("ts")}


def codex_windows_from_rl(rl):
    out = []
    for name in ("primary", "secondary"):
        w = rl.get(name)
        if isinstance(w, dict) and w.get("used_percent") is not None:
            mins = w.get("window_minutes") or 0
            label = "5h" if mins <= 360 else ("7d" if mins >= 10000 else f"{mins}m")
            out.append({"label": label, "pct": float(w["used_percent"]),
                        "resets_at": w.get("resets_at")})
    return out


def parse_codex_sessions(sessions_dir, max_files=5):
    files = sorted(Path(sessions_dir).glob("*/*/*/rollout-*.jsonl"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[:max_files]:
        last = None
        try:
            for line in open(f, encoding="utf-8"):
                if "rate_limits" not in line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rl = (e.get("payload") or {}).get("rate_limits")
                if isinstance(rl, dict):
                    last = rl
        except OSError:
            continue
        if last:
            return {"windows": codex_windows_from_rl(last), "plan": last.get("plan_type"),
                    "as_of": int(f.stat().st_mtime)}
    return {"error": "no rate_limits in recent sessions"}


def fetch_account(account, opencode_path=None):
    prov = account["provider"]
    src = account.get("source") or {}
    try:
        if prov == "claude" and src.get("type") == "statusline":
            p = Path(src.get("path", "~/.claude/rbtv-runtime/plan-usage.json")).expanduser()
            return parse_claude_statusline(json.loads(p.read_text(encoding="utf-8")))
        if prov == "codex" and src.get("type") == "codex-local":
            return parse_codex_sessions(Path(src.get("path", "~/.codex/sessions")).expanduser())
        if src.get("type") == "kimi-local":
            cred = Path(src.get("path", "~/.kimi/credentials/kimi-code.json")).expanduser()
            state = "logged in" if cred.is_file() else "not logged in"
            return {"note": f"{state} ({CONSOLE_URLS['kimi']}) · usage not exposed"}
        key = resolve_key(account, opencode_path)
        if prov in ("google", "sakana"):
            state = "key present" if key else "no credential"
            return {"note": f"{state} · console-only ({CONSOLE_URLS[prov]})"}
        if not key:
            return {"error": "no credential"}
        if prov == "zai":
            return parse_zai(get_json("https://api.z.ai/api/monitor/usage/quota/limit",
                                      {"Authorization": key}))
        if prov == "deepseek":
            return parse_deepseek(get_json("https://api.deepseek.com/user/balance",
                                           {"Authorization": f"Bearer {key}"}))
        if prov == "kimi":  # API-key account: documented Moonshot balance endpoint
            for base in ("https://api.moonshot.ai", "https://api.moonshot.cn"):
                try:
                    return parse_moonshot(get_json(base + "/v1/users/me/balance",
                                                   {"Authorization": f"Bearer {key}"}))
                except Exception:  # noqa: BLE001 — try the other region host
                    continue
            return {"error": "balance endpoint unreachable"}
        return {"error": f"no usage source for provider '{prov}'"}
    except FileNotFoundError:
        return {"error": "no data file yet"}
    except Exception as e:  # noqa: BLE001 — never leak request details, class name only
        return {"error": type(e).__name__}


def poll_providers(args):
    accounts = load_accounts(config_path(args.config))
    out = {"ts": int(time.time()), "accounts": []}
    for a in accounts:
        out["accounts"].append({"provider": a["provider"], "name": a.get("name", "main"),
                                "in_use": bool(a.get("in_use")), "data": fetch_account(a)})
    cf = cache_file()
    cf.parent.mkdir(parents=True, exist_ok=True)
    tmp = cf.with_suffix(".tmp")
    tmp.write_text(json.dumps(out), encoding="utf-8")
    tmp.replace(cf)
    return out


def load_cache():
    try:
        return json.loads(cache_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def spawn_background_poll(args):
    argv = [sys.executable, str(Path(__file__).resolve()), "--poll-providers"]
    if args.config:
        argv += ["--config", args.config]
    subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


# ---------- tmux ----------

def tmux_lines(*a):
    r = subprocess.run(["tmux", *a], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def current_session():
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return None
    out = tmux_lines("display-message", "-p", "-t", pane, "#{session_name}")
    return out[0] if out else None


def roster_map(package):
    out = {}
    if not package:
        return out
    try:
        text = (Path(package) / "coordination" / "workers.md").read_text(encoding="utf-8")
    except OSError:
        return out
    for m in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*yes\s*\|\s*(%\d+)\s*\|", text, re.M):
        out[m.group(2)] = m.group(1)
    return out


BUSY_GLYPHS = r"[⠀-⣿✳✻✽✶✢]"  # agent TUIs write these into their pane title while WORKING


def is_busy(title):
    return bool(re.search(BUSY_GLYPHS, title or ""))


def clean_title(title):
    t = re.sub(BUSY_GLYPHS, "", title or "").strip()
    return (t[:18] + "~") if len(t) > 19 else (t or "?")


def session_tree(session, roster):
    """[{name, active, panes: [name, ...]}], nwin, npane — [] when the session is unknown."""
    wins = []
    for ln in tmux_lines("list-windows", "-t", session, "-F",
                         "#{window_index}\t#{window_name}\t#{window_active}"):
        idx, name, active = ln.split("\t")
        wins.append({"idx": idx, "name": name, "active": active == "1", "panes": []})
    by_idx = {w["idx"]: w for w in wins}
    for ln in tmux_lines("list-panes", "-s", "-t", session, "-F",
                         "#{window_index}\t#{pane_id}\t#{pane_title}"):
        idx, pid, title = ln.split("\t", 2)
        if idx in by_idx:
            name = roster.get(pid) or clean_title(title)
            if is_busy(title):
                name += "+"  # working indicator — the seat's TUI reports it is busy/thinking
            by_idx[idx]["panes"].append(name)
    return wins, len(wins), sum(len(w["panes"]) for w in wins)


# ---------- rendering ----------

def visible_len(s):
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def pad_to(s, width):
    return s + " " * max(0, width - visible_len(s))


def bar(pct, width):
    filled = max(0, min(width, round(pct / 100 * width)))
    color = GREEN if pct < 60 else (YELLOW if pct < 85 else RED)
    return f"{color}{'█' * filled}{DIM}{'░' * (width - filled)}{OFF}"


def account_label(acc, multi):
    name = acc.get("name", "main")
    base = acc["provider"] if not multi else f"{acc['provider']}:{name}"
    return (f"{BOLD}{base}{OFF}" if acc.get("in_use") else f"{DIM}{base}{OFF}"), len(base)


def usage_cells(cache):
    """(bar_cells, note_bits): bar cell = (label, label_vis, pct, suffix); notes are text."""
    cells, notes = [], []
    if not cache:
        return cells, ["providers: no data yet (first poll pending)"]
    multi = {}
    for a in cache.get("accounts", []):
        multi[a["provider"]] = multi.get(a["provider"], 0) + 1
    now_ts = datetime.now().timestamp()
    for a in cache.get("accounts", []):
        d = a.get("data") or {}
        label, lvis = account_label(a, multi[a["provider"]] > 1)
        plain = a["provider"] if multi[a["provider"]] == 1 else f"{a['provider']}:{a.get('name')}"
        star = f"{BOLD}{plain}{OFF}" if a.get("in_use") else plain
        if d.get("windows"):
            stale = d.get("as_of") and now_ts - d["as_of"] > 5400
            for w in d["windows"]:
                suffix = f"as of {fmt_epoch(d['as_of'])}" if stale else ""
                cells.append((f"{label} {w['label']}", lvis + 1 + len(w["label"]),
                              w["pct"], suffix))
        elif d.get("balance") is not None:
            cur = {"USD": "$", "CNY": "¥"}.get(d.get("currency"), d.get("currency") or "")
            notes.append(f"{star} {cur}{d['balance']} left")
        elif d.get("note"):
            notes.append(f"{star}: {d['note']}")
        elif d.get("error"):
            notes.append(f"{star}: {d['error']}")
    return cells, notes


def flow(tokens, width, max_lines):
    lines, cur = [], ""
    for t in tokens:
        cand = t if not cur else f"{cur}   {t}"
        if visible_len(cand) <= width or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = t
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        dropped = len(lines) - max_lines
        lines = lines[:max_lines]
        lines[-1] += f" {DIM}(+{dropped} more){OFF}"
    return lines


def window_tokens(wins):
    out = []
    for w in wins:
        star = "*" if w["active"] else ""
        if len(w["panes"]) <= 1:
            busy = "+" if (w["panes"] and w["panes"][0].endswith("+")) else ""
            out.append(f"{star}{w['name']}{busy}")
        else:
            out.append(f"{star}{w['name']}[{' '.join(w['panes'])}]")
    return out




LEGEND = (f"{DIM}+ working · ~ name cut · * active window · "
          f"bold account = in use{OFF}")


def window_grid(wins, width, max_rows, dashes=False):
    """Windows as ASCII columns: window name as header, its panes stacked beneath.
    Fills banks left-to-right; reports what it cannot fit rather than hiding it."""
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
        need = 1 + (1 if dashes else 0) + depth + (1 if lines else 0)
        if lines and len(lines) + need > max_rows:
            break
        if lines:
            lines.append("")
        lines.append("".join(pad_to(f"{BOLD}{h}{OFF}", w + 2) for h, _p, w in bank))
        if dashes:
            lines.append("".join(pad_to("-" * w, w + 2) for _h, _p, w in bank))
        for r in range(depth):
            if len(lines) >= max_rows and r < depth - 1:
                pass
            lines.append("".join(pad_to(p[r] if r < len(p) else "", w + 2)
                                 for _h, p, w in bank))
        lines = lines[:max_rows]
        shown += len(bank)
    if shown < len(cols):
        note = f"{DIM}(+{len(cols) - shown} more windows){OFF}"
        if lines and len(lines) >= max_rows:
            lines[-1] = pad_to(lines[-1], max(0, width - visible_len(note) - 1)) + note
        else:
            lines.append(note)
    return lines


def choose_layout(cols, rows):
    if cols < 70 and rows < 18:
        return "tiny"
    if cols < 70:
        return "narrow"
    if rows < 16:
        return "strip"
    return "full"


def render_bar_cell(cell, label_w, bar_w, with_suffix=True):
    label, _lv, pct, suffix = cell
    s = f"{pad_to(label, label_w)} {bar(pct, bar_w)} {pct:3.0f}%"
    if with_suffix and suffix:
        s += f" {DIM}{suffix}{OFF}"
    return s


def render_full(session, wins, nwin, npane, cells, notes, cache, cols, rows):
    out = [f"{BOLD}teamview{OFF} · session {BOLD}{session}{OFF} · {nwin} windows / "
           f"{npane} panes · {datetime.now().strftime('%H:%M:%S')}", ""]
    age = ""
    if cache and cache.get("ts"):
        m = int((datetime.now().timestamp() - cache["ts"]) // 60)
        age = f"  {DIM}(providers polled {m}m ago){OFF}"
    out.append(f"{BOLD}PLAN LIMITS{OFF}{age}")
    label_w = max([c[1] for c in cells], default=10) + 1
    bar_w = max(16, min(40, cols - label_w - 30))
    for c in cells:
        out.append("  " + render_bar_cell(c, label_w, bar_w))
    for n in notes:
        out.append(f"  {DIM}{n}{OFF}")
    out.append("")
    out.append(f"{BOLD}WINDOWS{OFF} {DIM}(panes beneath){OFF}")
    grid_budget = rows - len(out) - 4
    out.extend("  " + l for l in window_grid(wins, cols - 2, grid_budget, dashes=True))
    out.append("")
    out.append(LEGEND)
    return out[:rows - 1]


def render_strip(session, wins, nwin, npane, cells, notes, cols, rows):
    head = (f"{BOLD}{session}{OFF} · {nwin}w/{npane}p · {datetime.now().strftime('%H:%M:%S')}")
    budget = max(3, rows - 1)
    # bars fold into as many columns as height demands and width allows
    label_w = max([c[1] for c in cells], default=10)
    for ncols in (1, 2, 3):
        bar_w = 22 if ncols == 1 else 14
        cell_w = label_w + bar_w + 8 + (14 if ncols == 1 else 0)
        need_rows = math.ceil(len(cells) / ncols) if cells else 0
        left_w = ncols * (cell_w + 2)
        if need_rows <= budget - 2 and left_w <= cols - 42:
            break
    grid_rows = math.ceil(len(cells) / ncols) if cells else 0
    left = [head]
    for r in range(grid_rows):
        row_cells = [render_bar_cell(cells[r + grid_rows * c], label_w, bar_w,
                                     with_suffix=(ncols == 1))
                     for c in range(ncols) if r + grid_rows * c < len(cells)]
        left.append("  ".join(pad_to(s, cell_w) for s in row_cells))
    # width from head + bars only — the notes footer is truncated to fit, never widens the block
    lw = min(max((visible_len(l) for l in left), default=0), cols - 42)
    if notes:
        left.append(f"{DIM}{' · '.join(notes)[:max(0, lw - 1)]}{OFF}")
    right_w = cols - lw - 3
    right = window_grid(wins, right_w, budget - 1)
    right.append(LEGEND)
    out = []
    for i in range(min(budget, max(len(left), len(right)))):
        lseg = left[i] if i < len(left) else ""
        rseg = right[i] if i < len(right) else ""
        out.append(f"{pad_to(lseg, lw)}{DIM}|{OFF} {rseg}")
    return out


def render_narrow(session, wins, nwin, npane, cells, notes, cols, rows):
    out = [f"{BOLD}{session}{OFF} {nwin}w/{npane}p {datetime.now().strftime('%H:%M')}"]
    label_w = max([c[1] for c in cells], default=8)
    bar_w = max(6, min(14, cols - label_w - 8))
    for c in cells:
        out.append(render_bar_cell(c, label_w, bar_w, with_suffix=False))
    for n in notes:
        out.append(f"{DIM}{n[:cols]}{OFF}")
    out.extend(flow(window_tokens(wins), cols, max(1, rows - len(out) - 1)))
    return out[:rows - 1]


def render_tiny(session, wins, nwin, npane, cells, notes, cols, rows):
    out = [f"{BOLD}{session[:cols - 12]}{OFF} {nwin}w/{npane}p"]
    toks = [f"{re.sub(chr(27) + r'\[[0-9;]*m', '', c[0])} {c[2]:.0f}%" for c in cells]
    toks += [re.sub(r"\s+", " ", n) for n in notes]
    out.extend(flow(toks, cols, max(1, (rows - 1) // 2)))
    out.extend(flow(window_tokens(wins), cols, max(1, rows - len(out) - 1)))
    return out[:rows - 1]


def render(args, session):
    cols = args.width or int(subprocess.run(["tput", "cols"], capture_output=True,
                                            text=True).stdout or 200)
    rows = args.height or int(subprocess.run(["tput", "lines"], capture_output=True,
                                             text=True).stdout or 45)
    roster = roster_map(args.package)
    wins, nwin, npane = session_tree(session, roster)
    if not wins:
        return [f"no such tmux session: {session}",
                "sessions: " + " ".join(tmux_lines("list-sessions", "-F", "#{session_name}"))]
    cache = load_cache()
    cells, notes = usage_cells(cache)
    layout = choose_layout(cols, rows)
    if layout == "full":
        return render_full(session, wins, nwin, npane, cells, notes, cache, cols, rows)
    if layout == "strip":
        return render_strip(session, wins, nwin, npane, cells, notes, cols, rows)
    if layout == "narrow":
        return render_narrow(session, wins, nwin, npane, cells, notes, cols, rows)
    return render_tiny(session, wins, nwin, npane, cells, notes, cols, rows)


# ---------- selftest ----------

def cmd_selftest():
    import tempfile
    failures = []

    def check(name, cond):
        print(("ok  " if cond else "FAIL") + f"  {name}")
        if not cond:
            failures.append(name)

    z = parse_zai({"data": {"level": "lite", "limits": [
        {"type": "TIME_LIMIT", "percentage": 0},
        {"type": "TOKENS_LIMIT", "unit": 3, "number": 5, "percentage": 9,
         "nextResetTime": 1784888042847},
        {"type": "TOKENS_LIMIT", "unit": 6, "number": 1, "percentage": 13,
         "nextResetTime": 1785450703998}]}})
    check("zai parser: 5h+7d windows, tier, TIME_LIMIT skipped",
          [w["label"] for w in z["windows"]] == ["5h", "7d"] and z["plan"] == "lite"
          and z["windows"][0]["resets_at"] == 1784888042)
    d = parse_deepseek({"is_available": True, "balance_infos": [
        {"currency": "USD", "total_balance": "9.26"}]})
    check("deepseek parser: balance+currency", d["balance"] == "9.26" and d["currency"] == "USD")
    m = parse_moonshot({"data": {"available_balance": 12.5}})
    check("moonshot parser: balance", m["balance"] == "12.5" and m["currency"] == "CNY")
    c = parse_claude_statusline({"ts": 1, "rate_limits": {
        "five_hour": {"used_percentage": 51, "resets_at": 2},
        "seven_day": {"used_percentage": 19}, "seven_day_opus": {"used_percentage": 40}}})
    check("claude parser: window labels incl. model-specific",
          sorted(w["label"] for w in c["windows"]) == ["5h", "7d", "7d opus"])
    cw = codex_windows_from_rl({"primary": {"used_percent": 3.0, "window_minutes": 10080,
                                            "resets_at": 5}, "secondary": None})
    check("codex windows: 10080min -> 7d", cw == [{"label": "7d", "pct": 3.0, "resets_at": 5}])

    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        (home / ".claude").mkdir()
        (home / ".codex" / "sessions").mkdir(parents=True)
        (home / ".kimi" / "credentials").mkdir(parents=True)
        oc = home / "auth.json"
        oc.write_text(json.dumps({"deepseek": {"key": "k1"}, "zai-coding-plan": {"key": "k2"}}))
        (home / ".claude-work").mkdir()
        acc = load_accounts(home / "nonexistent.json", home=home, opencode_path=oc)
        provs = sorted(a["provider"] for a in acc)
        check("discovery: claude+codex+kimi+opencode providers found",
              provs == ["claude", "claude", "codex", "deepseek", "kimi", "zai"])
        extra = next((a for a in acc if a["provider"] == "claude" and a["name"] == "work"), None)
        check("discovery: extra ~/.claude-<tag> account dir found with tagged statusline path",
              extra is not None and extra["source"]["path"].endswith("plan-usage-work.json"))
        check("discovery: harness-backed accounts marked in use",
              all(a["in_use"] for a in acc))
        cfg = home / "teamview.json"
        cfg.write_text(json.dumps({"accounts": [
            {"provider": "zai", "name": "main", "source": {"type": "opencode"}},
            {"provider": "zai", "name": "alt", "source": {"type": "env", "var": "X_ALT"}}]}))
        acc = load_accounts(cfg, home=home, opencode_path=oc)
        check("config: multi-account per provider; env account NOT in use",
              len(acc) == 2 and acc[0]["in_use"] and not acc[1]["in_use"])
        key = resolve_key({"provider": "zai", "source": {"type": "opencode"}}, opencode_path=oc)
        check("key resolution: opencode store_key mapping (zai -> zai-coding-plan)", key == "k2")

    check("layout: full / strip / narrow / tiny by pane size",
          (choose_layout(220, 50), choose_layout(280, 8),
           choose_layout(55, 40), choose_layout(60, 12))
          == ("full", "strip", "narrow", "tiny"))

    fake_cache = {"ts": int(time.time()), "accounts": [
        {"provider": "claude", "name": "main", "in_use": True,
         "data": {"windows": [{"label": "5h", "pct": 51, "resets_at": None},
                              {"label": "7d", "pct": 19, "resets_at": None}]}},
        {"provider": "zai", "name": "alt", "in_use": False,
         "data": {"windows": [{"label": "5h", "pct": 9, "resets_at": None}]}},
        {"provider": "deepseek", "name": "main", "in_use": True,
         "data": {"balance": "9.26", "currency": "USD"}},
        {"provider": "sakana", "name": "main", "in_use": True,
         "data": {"note": "key present · console-only (console.sakana.ai)"}}]}
    cells, notes = usage_cells(fake_cache)
    check("cells: one bar per window, money+notes to footer",
          len(cells) == 3 and any("9.26" in n for n in notes)
          and any("sakana" in n for n in notes))
    check("in-use highlight: bold (no star) for in-use, dim for alt",
          "*" not in cells[0][0] and BOLD in cells[0][0] and DIM in cells[2][0])
    wins = [{"idx": "0", "name": "control", "active": True, "panes": ["master", "watcher"]},
            {"idx": "1", "name": "cli", "active": False, "panes": ["cli"]}]
    for layout_fn, dims in ((render_strip, (240, 8)), (render_narrow, (56, 40)),
                            (render_tiny, (58, 12)), ):
        out = layout_fn("sess", wins, 2, 3, cells, notes, *dims)
        joined = "\n".join(out)
        check(f"{layout_fn.__name__}: fits height and carries seats + a provider",
              len(out) <= dims[1] and "master" in joined and "claude" in re.sub(
                  r"\033\[[0-9;]*m", "", joined))
    out = render_full("sess", wins, 2, 3, cells, notes, fake_cache, 120, 40)
    plain = [re.sub(r"\033\[[0-9;]*m", "", l) for l in out]
    hdr = next((i for i, l in enumerate(plain) if "control" in l), None)
    check("render_full: grid — starred active window, panes beneath, no legend, no renews",
          any("PLAN LIMITS" in l for l in plain) and hdr is not None
          and any("master" in l for l in plain[hdr:])
          and any("*control" in l for l in plain)
          and not any("legend:" in l for l in plain)
          and not any("renews" in l for l in plain))
    out = window_grid([{"name": "big", "active": True, "panes": [f"p{i}" for i in range(9)]},
                       {"name": "other", "active": False, "panes": ["x"]}], 30, 5)
    check("window_grid: height-capped with overflow note",
          len(out) <= 6 and any("more windows" in re.sub(r"\033\[[0-9;]*m", "", l)
                                for l in out) is False)  # same-bank cap truncates, no false note

    print(f"\nselftest: {'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s))")
    sys.exit(1 if failures else 0)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(prog="teamview", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", nargs="?", help="tmux session (default: the one you are in)")
    ap.add_argument("--package", default=os.environ.get("RBTV_TEAMVIEW_PACKAGE", ""),
                    help="team-kit run package for pane->agent roster names")
    ap.add_argument("--config", help="accounts config JSON (default ~/.config/rbtv/teamview.json)")
    ap.add_argument("--once", action="store_true", help="print one frame and exit")
    ap.add_argument("--interval", type=int, default=2, help="refresh seconds (default 2)")
    ap.add_argument("--refresh", action="store_true", help="poll providers NOW before rendering")
    ap.add_argument("--provider-ttl", type=int, default=600,
                    help="re-poll providers in background when cache older than SECS (default 600)")
    ap.add_argument("--width", type=int, help="override detected terminal width")
    ap.add_argument("--height", type=int, help="override detected terminal height")
    ap.add_argument("--poll-providers", action="store_true",
                    help="fetch provider usage into the cache and exit (loop-internal mode)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        cmd_selftest()
        return
    if args.poll_providers:
        poll_providers(args)
        print(f"cached: {cache_file()}")
        return

    session = args.session or current_session()
    if not session:
        sessions = tmux_lines("list-sessions", "-F", "#{session_name}")
        print("not inside tmux — pass a session name. sessions: " + " ".join(sessions),
              file=sys.stderr)
        sys.exit(2)

    if args.refresh or not cache_file().exists():
        poll_providers(args)

    def frame():
        cache = load_cache()
        if cache and time.time() - cache.get("ts", 0) > args.provider_ttl:
            spawn_background_poll(args)
        return "\n".join(render(args, session))

    if args.once:
        print(frame())
        return
    try:
        while True:
            out = frame()
            sys.stdout.write("\033[H\033[2J" + out + "\n")
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
