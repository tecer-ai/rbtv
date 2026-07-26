#!/usr/bin/env python3
"""teamview — live tmux team-run dashboard: panes with per-agent model/context/activity,
plus plan-limit bars for every AI provider account on the machine.

Run it inside tmux, or from outside: `teamview NAME` / `teamview session NAME` (bare
`teamview` auto-picks the only running session). Layouts adapt to the pane size; provider
data caches under ~/.cache/rbtv/ and re-polls in the background. When a layout cannot show
every window OR every pane within a window at once, the visible set ROTATES every ~10s
(wall-clock derived, so --once shows whichever page is current) instead of permanently
hiding the overflow — or pass --no-rotate for a COMPLETE snapshot instead (every window and
pane at once, best paired with --once; the output can grow taller than the terminal). A
CRITICAL pane — past its own ctx-refresh threshold, >=85% context,
or awaiting approval — is PINNED into every rotation page and never cycles out of view. A
pane stuck at a permission/trust prompt (detected in its captured tail) renders its name RED
with a `?!` marker. With --package, a pane whose context used % has reached ITS OWN seat's
ctx-refresh threshold (from that seat's workers/<agent>/agent.md frontmatter) renders its
ctx cell RED with a trailing `!` — WITHOUT --package this check never runs, so the header
carries a "no --package: thresholds/roster off" cue instead of silently showing a plain
green ctxN% that could read as "confirmed under threshold" rather than "never checked". The
console-only provider group (no readable usage endpoint) word-wraps the same way, so a long
provider list never hard-clips mid-word either. Every cue, rotation footer, and limit/ctx
VALUE degrades GRACEFULLY at narrow widths (shrinks to a shorter but still-complete form,
e.g. a bar drops before its own percent does) instead of a blind mid-word/mid-value clip.
The header also carries a system RAM+CPU readout (available RAM, load average vs core
count; stdlib only, `/proc/meminfo` + `os.getloadavg`), colored green/yellow/red by
pressure so an operator or watcher spots an OOM risk at a glance; it degrades the same
graceful way and vanishes rather than crash on a platform without these readings.
Stdlib only.

Legend (dashboard markers): + working · … text cut · * active window · ctxN% context used
(ctx~ = pane match uncertain; '~' means ONLY that, never truncation) ·
green<60 / yellow<85 / red>=85 = ctx and limit-bar color bands (plain red = high value,
no threshold involved) · Nm/Nh last activity · account = in use ·
name?! = awaiting approval · ctxN%! = past this seat's ctx-refresh threshold ·
name shell = harness exited · ? = empty-title pane.

Reference:  --help-providers  usage source per provider (read-only; keys never printed)
            --help-config     accounts config schema (multi-account)
            --help-security   audit surface: writes, endpoints, never-touches-tmux
            --help-panes      every pane state/marker, cause and remedy
            --audit           resolved accounts -> source -> redacted path -> poll result
            full docs         orchestration/cli/teamview/README.md
"""
import argparse
import difflib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

DOC_PROVIDERS = """Providers and their usage sources (read-only; keys are never printed, and
are sent ONLY to that provider's own documented endpoint):

  claude    per-account OAuth usage endpoint (GET api.anthropic.com/api/oauth/usage with the
            STORED accessToken from that account's {config_dir}/.credentials.json — the same
            call the Claude Code /usage screen makes; read-only, owner-sanctioned 2026-07-24)
            -> 5h/7d bars PLUS every model-scoped weekly window the plan carries (e.g.
            "7d fable"). teamview NEVER refreshes tokens: an idle account's expired token
            falls back to the statusline-persisted rate_limits file (pushed by a Claude Code
            statusline script; path per account, default ~/.claude/rbtv-runtime/
            plan-usage.json) until a real session of that account runs again. Statusline
            recency still decides IN-USE highlighting.
  codex     LOCAL parse of ~/.codex/sessions rollout files' payload.rate_limits -> plan bars
            (fresh only while a codex session runs; staleness shown as "as of", never hidden)
  zai       GET https://api.z.ai/api/monitor/usage/quota/limit (Authorization: <key>, no
            Bearer) -> 5h + weekly used-% bars + plan tier
  deepseek  GET https://api.deepseek.com/user/balance (Bearer) -> money balance (no windows)
  kimi      subscription OAuth login has no usage endpoint -> login state in the console-only
            group. Opt-in: an sk-kimi key (minted at kimi.com/code/console) polls
            GET api.kimi.com/coding/v1/usages -> per-model plan bars (community-verified
            endpoint, not officially documented); a Moonshot platform key instead uses the
            documented GET /v1/users/me/balance (api.moonshot.ai|.cn)
  google    no usage-read endpoint for an AI Studio API key (verified 2026-07-24) ->
            console-only group
  sakana    no balance/usage endpoint (verified 2026-07-24) -> console-only group

A model-scoped weekly like "7d fable" is a SUBSET of the plain "7d" window, not a separate
budget: that model's usage counts against BOTH bars, so the scoped bar can be exhausted
while the overall 7d still has room — a launch decision needs the scoped bar, not just 7d.
"""

DOC_CONFIG = """Accounts config — optional; with no config, accounts are auto-discovered from
the harness credential stores on the machine. Path: ~/.config/rbtv/teamview.json (override
with --config or RBTV_TEAMVIEW_CONFIG). All fields optional except provider; `source.type`
one of opencode | env | file | statusline | codex-local | kimi-local | none. Harness-backed
types are highlighted IN USE (override per account with "in_use": true/false).

  {"accounts": [
     {"provider": "zai",      "name": "main", "source": {"type": "opencode"}},
     {"provider": "zai",      "name": "alt",  "source": {"type": "env", "var": "ZAI_KEY_ALT"}},
     {"provider": "deepseek", "name": "main", "source": {"type": "opencode"}},
     {"provider": "claude",   "name": "main", "source": {"type": "statusline",
                                              "path": "~/.claude/rbtv-runtime/plan-usage.json"}},
     {"provider": "codex",    "name": "main", "source": {"type": "codex-local"}},
     {"provider": "kimi",     "name": "api",  "source": {"type": "env", "var": "MOONSHOT_API_KEY"}}
  ]}

Extra Claude accounts: any ~/.claude-<tag> config dir is auto-discovered as account
claude:<tag> (statusline file plan-usage-<tag>.json; OAuth credentials from that dir).
"""

DOC_SECURITY = """Security / audit surface — what teamview touches (verify with --audit):

WRITES — the ONLY files teamview ever writes:
  {XDG_CACHE_HOME|~/.cache}/rbtv/teamview-providers.json  provider usage cache (+ its .tmp)
It NEVER mutates tmux state: every tmux call is read-only (list-sessions, list-windows,
list-panes, display-message, capture-pane) — no send-keys, no kill, no resize, ever.

NETWORK — the complete endpoint list; each credential is sent ONLY to its own provider:
  api.anthropic.com/api/oauth/usage         claude (stored OAuth token, NEVER refreshed)
  api.z.ai/api/monitor/usage/quota/limit    zai
  api.deepseek.com/user/balance             deepseek
  api.kimi.com/coding/v1/usages | /usage    kimi (opt-in sk-kimi key only)
  api.moonshot.ai|.cn/v1/users/me/balance   kimi (Moonshot platform key only)
All read-only GETs. google/sakana have no usage endpoint and are never contacted.

CREDENTIALS — read-only from the harness stores (opencode auth.json, ~/.claude*/
.credentials.json, env vars, statusline/rollout files). Keys and tokens are NEVER printed:
--audit redacts paths to their basename and shows env-var NAMES only; fetch errors carry
the exception class name only, never the request.
"""

DOC_PANES = """Pane states and markers — every form a pane row can take, and what clears it:

  seat+           WORKING — visible content changed across two samples ~0.6s apart. Work
                  is bursty: a seat flips between + and unmarked as turns start/finish, so
                  a pane can honestly show a recent age (e.g. 'now') without a '+'.
  seat            idle this sample (no marker).
  seat?!  (red)   AWAITING APPROVAL — the pane tail matches a permission/trust prompt.
                  Clears when the prompt is answered in that pane.
  ctxN%           context-window used %, colored green <60 / yellow <85 / red >=85.
  ctxN%!  (red)   past this seat's OWN ctx-refresh threshold (workers/<agent>/agent.md
                  frontmatter) — only checked WITH --package.
  ctx~N%          pane match UNCERTAIN: ctx-monitor could not uniquely map this pane's
                  process to one harness session record, so the value may belong to a
                  sibling pane. Clears when the mapping becomes unambiguous — e.g. the
                  team-kit statusline persists a pid->transcript record for claude panes,
                  or the ambiguous sibling exits. (ctx-monitor --json flag: "ambiguous".)
  name shell (dim) the harness EXITED — a bare shell sits in the pane. Distinct from a
                  live pane whose agent info merely failed to resolve (name + command).
  ?          (dim) a pane with an EMPTY title and no roster name — usually a dead pane;
                  pass --package to resolve roster names.
  … / ~           '…' marks TEXT truncated for width (anywhere); '~' is ONLY the
                  ctx-uncertainty marker above — it never marks truncation.
"""

TIMEOUT = 10
BOLD, DIM, OFF = "\033[1m", "\033[2m", "\033[0m"
CYAN, UL = "\033[36m", "\033[4m"
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
                    "source": {"type": "statusline", "config_dir": str(home / ".claude"),
                               "path": str(home / ".claude" / "rbtv-runtime" / "plan-usage.json")}})
    # extra Claude accounts: one config dir per account (CLAUDE_CONFIG_DIR=~/.claude-<tag>);
    # the statusline script persists each account's windows to plan-usage-<tag>.json
    for extra in sorted(home.glob(".claude-*")):
        if extra.is_dir():
            tag = extra.name[len(".claude-"):] or "alt"
            acc.append({"provider": "claude", "name": tag,
                        "source": {"type": "statusline", "config_dir": str(extra),
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
# A statusline (Claude) account counts as IN USE only if a session wrote its usage file within
# this window — multiple Claude accounts are all statusline-backed, so recency, not source
# type, is what distinguishes the account actually being used.
CLAUDE_ACTIVE_SECS = 600


def claude_in_use(data, now=None):
    as_of = (data or {}).get("as_of")
    if not as_of:
        return False
    now = now if now is not None else time.time()
    return (now - as_of) <= CLAUDE_ACTIVE_SECS


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
        if "in_use" in a:
            a["_in_use_explicit"] = True
        else:  # harness-backed sources are what the harnesses actually read
            a["in_use"] = src.get("type") in HARNESS_BACKED
    return accounts


def missing_config_warning(cfg_arg):
    """stderr warning when an EXPLICIT --config path does not exist (auto-discovery still
    proceeds) — None when no --config was given or the file exists. Previously a mistyped
    --config fell back to auto-discovery SILENTLY, indistinguishable from a working one."""
    if cfg_arg and not Path(cfg_arg).expanduser().is_file():
        return (f"warning: --config {cfg_arg} not found — falling back to account "
                "auto-discovery (see --help-config for the schema and default path)")
    return None


def redact_path(p):
    """Basename only, '…/' prefix — --audit must show WHICH file backs an account without
    ever printing a full filesystem path (or, anywhere, a key/token)."""
    return f"…/{Path(p).name}" if p else ""


def audit_lines(accounts, cache):
    """One line per resolved account: 'provider:name -> source-kind -> redacted path ->
    last poll result' — the auditor surface (--audit). Pure function of the account list +
    cache: no network, no key resolution, nothing secret ever enters the output."""
    by_key = {(c.get("provider"), c.get("name", "main")): c.get("data") or {}
              for c in (cache or {}).get("accounts", [])}
    out = []
    for a in accounts:
        src = a.get("source") or {}
        kind = src.get("type") or "none"
        loc = redact_path(src.get("path") or src.get("config_dir"))
        if not loc and src.get("var"):
            loc = f"${src['var']}"  # the env var's NAME, never its value
        d = by_key.get((a["provider"], a.get("name", "main")))
        if d is None:
            result = "not polled yet"
        elif d.get("windows"):
            result = f"ok ({len(d['windows'])} windows)"
        elif d.get("balance") is not None:
            result = "ok (balance)"
        elif d.get("note"):
            result = "console-only"
        else:
            result = f"error: {d.get('error', '?')}"
        out.append(f"{a['provider']}:{a.get('name', 'main')} -> {kind} -> "
                   f"{loc or '-'} -> {result}")
    return out


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


def parse_kimi_code(d):
    """Kimi Code plan usage — GET api.kimi.com/coding/v1/usages with an sk-kimi key (minted in
    the Kimi Code Console; the subscription OAuth token cannot call it). Community-verified
    endpoint (not in official docs) — parser is tolerant: accepts a list of per-model rows
    carrying limit/used (top-level, data, or usages)."""
    rows = d.get("usages") or (d.get("data") or {}).get("usages") or d.get("data") or []
    if isinstance(rows, dict):
        rows = [rows]
    windows = []
    for r in rows:
        if not isinstance(r, dict) or not r.get("limit"):
            continue
        used = r.get("used", r.get("limit", 0) - r.get("remaining", 0))
        label = str(r.get("model") or r.get("name") or "plan")[:12]
        reset = r.get("reset_at") or r.get("resets_at")
        windows.append({"label": label, "pct": round(100.0 * used / r["limit"], 1),
                        "resets_at": reset})
    if not windows:
        return {"error": "no usage rows"}
    return {"windows": windows[:2]}


def parse_moonshot(d):
    data = d.get("data") or {}
    if data.get("available_balance") is None:
        return {"error": "no available_balance"}
    return {"balance": str(data["available_balance"]), "currency": "CNY"}


def iso_epoch(ts):
    try:
        return int(datetime.fromisoformat(ts).timestamp())
    except (TypeError, ValueError):
        return None


def parse_oauth_limits(d):
    """Windows from the OAuth usage endpoint's limits[] — includes model-scoped weeklies
    (kind=weekly_scoped, scope.model.display_name e.g. 'Fable') the statusline never sees."""
    out = []
    for lim in d.get("limits") or []:
        pct, kind = lim.get("percent"), lim.get("kind")
        if pct is None:
            continue
        if kind == "session":
            label = "5h"
        elif kind == "weekly_all":
            label = "7d"
        elif kind == "weekly_scoped":
            scope = ((lim.get("scope") or {}).get("model") or {}).get("display_name")
            label = f"7d {(scope or 'scoped').lower()}"
        else:
            label = kind or "?"
        out.append({"label": label, "pct": float(pct),
                    "resets_at": iso_epoch(lim.get("resets_at"))})
    return out


def claude_oauth_windows(config_dir=None):
    """Live per-account windows via the account's STORED OAuth access token — read-only,
    never refreshed (owner ruling 2026-07-24: teamview must not touch the token chain; an
    idle account's expired token simply falls back to the statusline file until a real
    session of that account runs and Claude Code refreshes it). [] on any failure."""
    cred = Path(config_dir or "~/.claude").expanduser() / ".credentials.json"
    try:
        oauth = json.loads(cred.read_text(encoding="utf-8")).get("claudeAiOauth") or {}
    except (OSError, json.JSONDecodeError):
        return []
    tok, exp = oauth.get("accessToken"), oauth.get("expiresAt")
    if not tok or (exp and exp / 1000 < time.time() + 60):  # expired: don't even call
        return []
    try:
        return parse_oauth_limits(get_json(
            "https://api.anthropic.com/api/oauth/usage",
            {"Authorization": f"Bearer {tok}", "anthropic-beta": "oauth-2025-04-20"}))
    except Exception:  # noqa: BLE001 — endpoint/token trouble just means fallback
        return []


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
            try:
                sl = parse_claude_statusline(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                sl = {"error": "no data file yet"}
            oauth = claude_oauth_windows(src.get("config_dir"))
            if oauth:  # complete window set, fetched NOW ("fresh" suppresses as-of staleness);
                out = {"windows": oauth, "fresh": True}  # statusline as_of still marks in-use
                if sl.get("as_of"):
                    out["as_of"] = sl["as_of"]
                return out
            return sl
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
        if prov == "kimi" and key.startswith("sk-kimi"):
            # Kimi Code Console key -> plan usage endpoint (community-verified; opt-in key)
            for path in ("/coding/v1/usages", "/coding/v1/usage"):
                try:
                    return parse_kimi_code(get_json("https://api.kimi.com" + path,
                                                    {"Authorization": f"Bearer {key}"}))
                except Exception:  # noqa: BLE001 — try the fallback path
                    continue
            return {"error": "usages endpoint unreachable"}
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
        data = fetch_account(a)
        in_use = bool(a.get("in_use"))
        if (a["provider"] == "claude" and (a.get("source") or {}).get("type") == "statusline"
                and not a.get("_in_use_explicit")):
            in_use = claude_in_use(data)  # recency decides between multiple Claude accounts
        out["accounts"].append({"provider": a["provider"], "name": a.get("name", "main"),
                                "in_use": in_use, "data": data})
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


def resolve_session(tokens, current, sessions):
    """Positional tokens -> session name. Accepts `NAME`, the spoken form `session NAME`,
    or nothing — which means the session teamview runs inside, else (from OUTSIDE tmux)
    the only running session. None when nothing resolves (caller lists the candidates)."""
    toks = [t for t in tokens or [] if t]
    if len(toks) > 1 and toks[0] == "session":
        toks = toks[1:]
    if toks:
        return toks[0]
    if current:
        return current
    if len(sessions) == 1:
        return sessions[0]
    return None


def session_error(session, sessions):
    """The teaching refusal for an unresolved/unknown session — None when `session` is a
    live tmux session. Callers print it to stderr and exit 2: a bogus name previously
    rendered an 'empty' frame on STDOUT with exit 0, so a wrapper script recorded success
    for a view that showed nothing."""
    if session and session in sessions:
        return None
    if not sessions:
        return ("no tmux sessions are running" if session
                else "not inside tmux and no tmux sessions are running")
    if not session:
        return (f"not inside tmux and {len(sessions)} sessions are running — pick one: "
                "teamview <session>. sessions: " + " ".join(sessions))
    close = difflib.get_close_matches(session, sessions, n=1)
    hint = f" — did you mean '{close[0]}'?" if close else ""
    return (f"no such tmux session: {session}{hint}\n"
            "sessions: " + " ".join(sessions))


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


def ctx_refresh_thresholds(package):
    """{agent-name: threshold%} read from every workers/<agent>/agent.md frontmatter's
    `ctx-refresh:` key (integer percent). An agent with no such key carries no threshold —
    default is none, never enforced. [] package -> {}."""
    out = {}
    if not package:
        return out
    try:
        agent_dirs = sorted((Path(package) / "workers").iterdir())
    except OSError:
        return out
    for d in agent_dirs:
        try:
            text = (d / "agent.md").read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        fm = text[:end] if end != -1 else text
        name = re.search(r"^agent:\s*(\S+)", fm, re.M)
        thr = re.search(r"^ctx-refresh:\s*(\d+)", fm, re.M)
        if name and thr:
            out[name.group(1)] = int(thr.group(1))
    return out


BUSY_GLYPHS = r"[⠀-⣿✳✻✽✶✢]"  # TUI title spinner glyphs — they PERSIST frozen when a turn ends,
SHELLS = {"bash", "zsh", "sh", "fish", "dash"}  # pane_current_command = shell -> harness exited
# so a still frame cannot tell working from idle (a frozen ✳ is not activity). The honest,
# harness-agnostic signal is CHANGE: a pane whose visible content differs across two samples a
# fraction of a second apart is actively rendering (spinner cycling / tokens streaming / tool
# output) — i.e. working. An idle pane's content is static between samples.
BUSY_SAMPLE_GAP = 0.6  # seconds between the two activity samples


def pane_signature(pane):
    r = subprocess.run(["tmux", "capture-pane", "-p", "-t", pane],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    return "\n".join(r.stdout.splitlines()[-8:])


# Permission/trust prompt signatures a stuck seat's pane tail shows — claude's numbered
# Yes/No dialogs ("Do you want to ... ❯ 1. Yes ... Esc to cancel"), codex's "Action
# Required", and generic trust-this-folder/workspace prompts. Matched against the SAME
# two-sample capture busy_panes already takes — no extra tmux call.
PROMPT_PATTERNS = tuple(re.compile(p, re.I | re.M) for p in (
    r"do you want to",
    r"do you trust",
    r"esc to cancel",
    r"action required",
    r"^\s*[❯>]?\s*1\.\s*yes\b",
))


def is_awaiting_approval(text):
    return any(p.search(text) for p in PROMPT_PATTERNS)


def busy_panes(pids, gap=BUSY_SAMPLE_GAP):
    """(working, awaiting) pane-id sets from the SAME two-sample capture: working = visible
    content changed across the two samples -> actively rendering; awaiting = the latest
    sample's tail matches a permission/trust prompt signature -> stuck waiting on approval."""
    if not pids:
        return set(), set()
    a = {pid: pane_signature(pid) for pid in pids}
    time.sleep(gap)
    b = {pid: pane_signature(pid) for pid in pids}
    working = {pid for pid in pids if a.get(pid) and a[pid] != b.get(pid)}
    awaiting = {pid for pid in pids if is_awaiting_approval(b.get(pid, ""))}
    return working, awaiting


def clean_title(title):
    t = re.sub(BUSY_GLYPHS, "", title or "").strip()
    return (t[:18] + "…") if len(t) > 19 else (t or "?")


_CTX_MOD = "unset"


def ctx_module():
    """The sibling ctx-monitor engine (../ctx-monitor/ctx_monitor.py), imported by path;
    None when absent — pane rows then degrade to names + pane command."""
    global _CTX_MOD
    if _CTX_MOD == "unset":
        path = Path(__file__).resolve().parent.parent / "ctx-monitor" / "ctx_monitor.py"
        try:
            spec = importlib.util.spec_from_file_location("ctx_monitor", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _CTX_MOD = mod
        except Exception:  # noqa: BLE001 — a broken/absent engine must never kill a frame
            _CTX_MOD = None
    return _CTX_MOD


def session_tree(session, roster, thresholds=None):
    """[{name, active, panes: [pane-dict, ...]}], nwin, npane — [] when the session is
    unknown. Each pane dict: name/shell/busy plus the agent in it (harness, model, ctx
    used %, last-activity age) resolved by ctx-monitor; ctx_over marks a pane whose ctx%
    has reached its seat's own ctx-refresh threshold (from `thresholds`, per-agent %)."""
    thresholds = thresholds or {}
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
    working, awaiting = busy_panes([pid for _i, pid, cmd, _t in rows if cmd not in SHELLS])
    cm, recs = ctx_module(), {}
    if cm:
        try:
            recs = {r["pane_id"]: r for r in cm.pane_records(session)}
        except Exception:  # noqa: BLE001 — pane info is best-effort decoration
            recs = {}
    for idx, pid, cmd, title in rows:
        r = recs.get(pid, {})
        name = roster.get(pid) or clean_title(title)
        pct = r.get("ctx_pct")
        thr = thresholds.get(name)
        by_idx[idx]["panes"].append({
            "name": name,
            "shell": cmd in SHELLS, "busy": pid in working, "awaiting": pid in awaiting,
            "harness": "" if cmd in SHELLS else cmd,
            "model": cm.short_model(r.get("model", "")) if cm else "",
            "ctx": pct, "approx": bool(r.get("ambiguous")),
            "ctx_over": thr is not None and pct is not None and pct >= thr,
            "age": cm.fmt_age(r.get("as_of")) if cm else ""})
    return wins, len(wins), sum(len(w["panes"]) for w in wins)


def ctx_str(pct, approx=False, over=False):
    """over: this seat's own ctx-refresh threshold has been reached — always RED, trailing
    '!' (past-threshold marker), regardless of the normal color-band it would otherwise get."""
    color = GREEN if pct < 60 else (YELLOW if pct < 85 else RED)
    bang = "!" if over else ""
    return f"{RED if over else color}ctx{'~' if approx else ''}{pct:.0f}%{bang}{OFF}"


def pane_agent_bits(p):
    """harness:model + ctxN% + age — the agent-info suffix shared by both pane styles."""
    bits = []
    hm = p.get("harness") or ""
    if p.get("model"):
        hm += f":{p['model']}"
    if hm:
        bits.append(f"{DIM}{hm}{OFF}")
    if p.get("ctx") is not None:
        bits.append(ctx_str(p["ctx"], p.get("approx", False), p.get("ctx_over", False)))
    if p.get("age"):
        bits.append(f"{DIM}{p['age']}{OFF}")
    return bits


def pane_name(p):
    """Seat name with its state marker: RED name?! when stuck at a permission/trust prompt
    (AWAITING approval — the pane tail matched a prompt signature), else the plain busy '+'."""
    if p.get("awaiting"):
        return f"{RED}{p['name']}?!{OFF}"
    return p["name"] + ("+" if p["busy"] else "")


def shell_cell(p):
    """Harness exited — a bare shell sits in the pane. The explicit 'shell' tag separates
    this KNOWN state from a live pane whose agent info merely failed to resolve (the two
    previously rendered identically as a dim bare name)."""
    return f"{DIM}{p['name']} shell{OFF}"


def pane_cell(p):
    """Wide layouts (full/strip grid): 'seat+ harness:model ctxN% age' on one line."""
    if p["shell"]:
        return shell_cell(p)
    return " ".join([pane_name(p)] + pane_agent_bits(p))


def pane_cell_variants(p):
    """pane_cell()'s content from full detail down to bare name — lets a column that would
    otherwise overflow the frame width shrink GRACEFULLY instead of getting hard-clipped
    mid-value downstream (observed: 'ctx42~' losing its own % sign and color reset). Age
    drops first, then harness:model; ctx% — the DESIGN-4 safety signal — survives until the
    very last non-bare variant."""
    if p["shell"]:
        return [shell_cell(p), f"{DIM}{p['name']}{OFF}"]
    name = pane_name(p)
    bits = pane_agent_bits(p)
    idx, hm, ctx, age = 0, None, None, None
    if p.get("harness") or p.get("model"):
        hm, idx = bits[idx], idx + 1
    if p.get("ctx") is not None:
        ctx, idx = bits[idx], idx + 1
    if p.get("age"):
        age = bits[idx]
    variants = []
    for parts in ((name, hm, ctx, age), (name, hm, ctx), (name, ctx), (name,)):
        v = " ".join(x for x in parts if x)
        if not variants or variants[-1] != v:
            variants.append(v)
    return variants


def pane_cell_fit(p, max_w):
    variants = pane_cell_variants(p)
    return shrink_to_fit(variants, max_w) or variants[-1]


def pane_compact(p):
    """Compact layouts (narrow/tiny flow): 'seat+(harness:model ctxN% age)'."""
    if p["shell"]:
        return shell_cell(p)
    name = pane_name(p)
    bits = pane_agent_bits(p)
    return f"{name}({' '.join(bits)})" if bits else name


# ---------- rendering ----------

def visible_len(s):
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def clip_line(s, width):
    """ANSI-aware hard clip: a rendered line longer than the pane wraps in the terminal and
    breaks the exact-height frame contract, so it is cut to width with a '…' marker ('…' is
    the ONE text-truncation glyph everywhere; '~' is reserved for ctx-match uncertainty)."""
    if visible_len(s) <= width:
        return s
    out, vis = "", 0
    for chunk in re.split(r"(\033\[[0-9;]*m)", s):
        if chunk.startswith("\033"):
            out += chunk
            continue
        take = max(0, width - 1 - vis)
        out += chunk[:take]
        vis += min(len(chunk), take)
        if vis >= width - 1:
            break
    return out + OFF + "…"


def pad_to(s, width):
    return s + " " * max(0, width - visible_len(s))


def shrink_to_fit(variants, width):
    """variants: strings from most to least detailed. Returns the first that FITS width —
    graceful degradation instead of relying on clip_line's blind mid-word/mid-value cut.
    "" (never a signal) only when even the shortest variant doesn't fit."""
    for v in variants:
        if visible_len(v) <= width:
            return v
    return ""


def fit_join(items, sep, width):
    """Join `items` with `sep`; if that overflows width, drop items from the END (never
    mid-word) and append a '(+N)' count — used for note/balance lists that would otherwise
    hard-clip mid-word at narrow widths."""
    joined = sep.join(items)
    if not items or visible_len(joined) <= width:
        return joined
    kept = list(items)
    while kept:
        kept.pop()
        dropped = len(items) - len(kept)
        tail = f" {DIM}(+{dropped}){OFF}"
        candidate = (sep.join(kept) + tail) if kept else f"{DIM}(+{dropped}){OFF}"
        if visible_len(candidate) <= width:
            return candidate
    return ""


def range_note_variants(label, start, end, total, pinned=False):
    """Full -> short -> tiny text for a contiguous 'N-M/T' overflow note (windows or panes),
    picked by shrink_to_fit against whatever width is actually available."""
    tag = " · pinned" if pinned else ""
    return [
        f"{DIM}({label} {start}-{end}/{total} - rotating{tag}){OFF}",
        f"{DIM}({start}-{end}/{total}{tag}){OFF}",
        f"{DIM}+{total - (end - start + 1)}{OFF}",
    ]


def count_note_variants(shown, total, pinned=True):
    """Full -> short -> tiny text for a NON-contiguous 'K/T shown' note (pinning broke the
    simple range), picked by shrink_to_fit."""
    tag = "pinned+rotating" if pinned else "rotating"
    return [
        f"{DIM}({shown}/{total} shown - {tag}){OFF}",
        f"{DIM}({shown}/{total}){OFF}",
        f"{DIM}+{total - shown}{OFF}",
    ]


def bar(pct, width):
    filled = max(0, min(width, round(pct / 100 * width)))
    color = GREEN if pct < 60 else (YELLOW if pct < 85 else RED)
    return f"{color}{'█' * filled}{DIM}{'░' * (width - filled)}{OFF}"


def account_label(acc, multi):
    name = acc.get("name", "main")
    base = acc["provider"] if not multi else f"{acc['provider']}:{name}"
    return (f"{CYAN}{base}{OFF}" if acc.get("in_use") else f"{DIM}{base}{OFF}"), len(base)


def usage_cells(cache):
    """(bar_cells, note_bits, console_bits): bar cell = (label, label_vis, pct, suffix);
    notes = API-backed facts (balances, errors); console_bits = providers whose usage is NOT
    programmatically readable (nested under one 'console only' group by the renderers)."""
    cells, notes, console = [], [], []
    if not cache:
        return cells, ["providers: no data yet (first poll pending)"], console
    multi = {}
    for a in cache.get("accounts", []):
        multi[a["provider"]] = multi.get(a["provider"], 0) + 1
    now_ts = datetime.now().timestamp()
    for a in cache.get("accounts", []):
        d = a.get("data") or {}
        label, lvis = account_label(a, multi[a["provider"]] > 1)
        plain = a["provider"] if multi[a["provider"]] == 1 else f"{a['provider']}:{a.get('name')}"
        star = f"{CYAN}{plain}{OFF}" if a.get("in_use") else plain
        if d.get("windows"):
            stale = (not d.get("fresh")) and d.get("as_of") and now_ts - d["as_of"] > 5400
            for w in d["windows"]:
                suffix = (f"as of {fmt_epoch(d['as_of'])}" if stale
                          else (f"renews {fmt_epoch(w['resets_at'])}"
                                if w.get("resets_at") else ""))
                cells.append((f"{label} {w['label']}", lvis + 1 + len(w["label"]),
                              w["pct"], suffix))
        elif d.get("balance") is not None:
            cur = {"USD": "$", "CNY": "¥"}.get(d.get("currency"), d.get("currency") or "")
            notes.append(f"{star} {cur}{d['balance']} left")
        elif d.get("note"):
            url = CONSOLE_URLS.get(a["provider"], "")
            state = "logged in" if "logged in" in d["note"] else (
                "key present" if "key present" in d["note"] else "no credential")
            console.append(f"{star} {DIM}({state}{'; ' + url if url else ''}){OFF}")
        elif d.get("error"):
            notes.append(f"{star}: {d['error']}")
    return cells, notes, console


def console_line(console):
    """The nested console-only group, visually set apart: 'no usage API > provider (state)'.
    Single un-wrapped line — safe only where the caller already guarantees it fits (narrow
    fallback forms); wide/full layouts use console_lines() instead so a long provider list
    never hard-clips mid-word."""
    if not console:
        return ""
    return f"{YELLOW}no usage API{OFF} {DIM}>{OFF} " + f" {DIM}·{OFF} ".join(console)


def console_lines(console, width, max_lines=3):
    """console_line's content, WORD-WRAPPED to width (never hard-clipped mid-word) — each
    provider entry is an atomic token, same wrap mechanics as legend_lines()."""
    if not console:
        return []
    return flow([f"{YELLOW}no usage API{OFF} {DIM}>{OFF}"] + list(console), width, max_lines)


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
        tail = f" {DIM}(+{dropped} more){OFF}"
        # width-safe: shed whole trailing tokens until the note fits — never let the
        # suffix push the line past width into the outer clip's mid-word cut
        while "   " in lines[-1] and visible_len(lines[-1] + tail) > width:
            lines[-1] = lines[-1].rsplit("   ", 1)[0]
        lines[-1] += tail
    return lines


def compact_window_lines(wins, width, max_lines, now=None):
    """Narrow/tiny windows block: each window starts its own line ('*name:' then panes),
    wrapping BETWEEN panes so no pane is ever clipped away mid-token. When the full set
    doesn't fit max_lines, ROTATES the visible page of windows every ~10s (same
    wall-clock derivation as window_grid) instead of permanently hiding overflow. A page
    holding a CRITICAL pane (is_critical_pane) is PINNED — shown steadily instead of
    rotating away from it on a timer."""
    chunks, chunk_critical = [], []
    for w in wins:
        star = "*" if w["active"] else ""
        toks = [pane_compact(p) for p in w["panes"]]
        chunks.append(flow([f"{star}{w['name']}:"] + toks, width, 99) if toks
                      else [f"{star}{w['name']}"])
        chunk_critical.append(any(is_critical_pane(p) for p in w["panes"]))

    pages, page, page_lines, page_nwin, page_crit = [], [], 0, 0, False
    for c, crit in zip(chunks, chunk_critical):
        need = len(c)
        if page and page_lines + need > max_lines:
            pages.append((page, page_nwin, page_crit))
            page, page_lines, page_nwin, page_crit = [], 0, 0, False
        page.append(c)
        page_lines += need
        page_nwin += 1
        page_crit = page_crit or crit
    if page:
        pages.append((page, page_nwin, page_crit))
    if not pages:
        return []

    critical_page_idx = next((i for i, (_p, _n, crit) in enumerate(pages) if crit), None)
    if len(pages) == 1:
        page_idx = 0
    elif critical_page_idx is not None:
        page_idx = critical_page_idx  # PIN: hold on the critical page, no time rotation
    else:
        page_idx = int((time.time() if now is None else now) // 10) % len(pages)
    page_chunks, _, _ = pages[page_idx]
    lines = [l for c in page_chunks for l in c]
    if len(pages) > 1:
        start = sum(n for _c, n, _cr in pages[:page_idx]) + 1
        end = start + pages[page_idx][1] - 1
        variants = range_note_variants("windows", start, end, len(chunks),
                                       pinned=critical_page_idx is not None)
        if lines and len(lines) >= max_lines:
            lines = lines[:max(1, max_lines)]
            note = shrink_to_fit(variants, width)
            if note:
                lines[-1] = note
        else:
            note = shrink_to_fit(variants, width)
            if note:
                lines.append(note)
    elif len(lines) > max_lines:
        dropped = len(lines) - max_lines
        lines = lines[:max_lines]
        lines[-1] += f" {DIM}(+{dropped} more){OFF}"
    return lines




# Individual marker explanations — flowed (wrapped) to the frame's own width at render time
# instead of joined into one long line, so a narrow pane never hard-clips the legend mid-word
# (clip_line's '~' cut previously ate everything past ~80 cols, e.g. "...ctx~ = pane ma~").
# ALARM items lead: flow() drops overflow from the END, so the keys an operator most
# needs (approval, threshold, the color bands) are the LAST dropped, never the first
# (the run verified the old order shed exactly those keys first at <=70 cols).
LEGEND_ITEMS = (
    f"{RED}name?!{OFF} = awaiting approval",
    f"{RED}ctxN%!{OFF} = past this seat's ctx-refresh threshold",
    f"{GREEN}green{OFF}<60 {YELLOW}yellow{OFF}<85 {RED}red{OFF}>=85 = ctx/bar color bands",
    f"{DIM}+{OFF} working", f"{DIM}…{OFF} text cut", f"{DIM}*{OFF} active window",
    f"{DIM}ctxN%{OFF} = context used (ctx~ = pane match uncertain)",
    f"{DIM}Nm/Nh{OFF} = last activity", f"{CYAN}account{OFF} = in use",
    f"{DIM}name shell{OFF} = harness exited", f"{DIM}?{OFF} = empty-title pane",
)


def legend_lines(width, max_lines=4):
    """The full marker legend, WORD-WRAPPED (never hard-clipped) to the given width — every
    item always shows complete, just on however many lines it takes."""
    return flow(LEGEND_ITEMS, width, max_lines)


# Alarm keys FIRST — items drop from the END as width shrinks, so the alarm vocabulary
# (the keys a small view exists to surface) is the LAST thing lost, never the first.
MINI_LEGEND_ITEMS = (
    f"{RED}?!{OFF}=approval", f"{RED}ctx%!{OFF}=threshold",
    f"{RED}red{OFF}>=85 {YELLOW}yel{OFF}>=60",
    f"{DIM}+{OFF}=working", f"{DIM}…{OFF}=cut", f"{DIM}~{OFF}=ctx uncertain",
)


def mini_legend(width):
    """ONE legend line for the sub-full layouts (strip/narrow/tiny previously rendered no
    legend at all — an operator at a small size had NO on-screen key for the alarm markers).
    Degrades by dropping trailing items (alarm keys survive longest); '' when even the
    alarm keys alone don't fit."""
    variants = [f" {DIM}·{OFF} ".join(MINI_LEGEND_ITEMS[:n])
                for n in range(len(MINI_LEGEND_ITEMS), 0, -1)]
    return shrink_to_fit(variants, width)


def rollup_variants(wins):
    """The persistent alarm-rollup — '13 panes · worst ctx94%~ · 1 red · 0 ?!' — rendered
    at EVERY layout size on the windows header line, above the rotating detail. Rotation
    can hide panes; this line is the fixed summary that proves (or disproves) 'nothing is
    alarming' from any single glance (DESIGN item 4: a 93.7%-ctx pane once rotated fully
    out of view). Shell panes count in the total but never in worst/red/?!."""
    panes = [p for w in wins for p in w["panes"]]
    live = [p for p in panes if not p.get("shell")]
    ctxs = [p for p in live if p.get("ctx") is not None]
    worst = max(ctxs, key=lambda p: p["ctx"]) if ctxs else None
    red = sum(1 for p in live if p.get("ctx_over")
              or (p.get("ctx") is not None and p["ctx"] >= 85))
    waiting = sum(1 for p in live if p.get("awaiting"))
    wc = (ctx_str(worst["ctx"], worst.get("approx", False), worst.get("ctx_over", False))
          if worst else "")
    rc, ac = (RED if red else DIM), (RED if waiting else DIM)
    full = [f"{len(panes)} panes"] + ([f"worst {wc}"] if wc else []) \
        + [f"{rc}{red} red{OFF}", f"{ac}{waiting} ?!{OFF}"]
    short = [f"{len(panes)}p"] + ([wc] if wc else []) \
        + [f"{rc}{red}r{OFF}", f"{ac}{waiting}?!{OFF}"]
    return [" · ".join(full), " ".join(short)]


def rollup_suffix(wins, avail):
    """The rollup shrunk to the room left on a header line — never mid-value clipped;
    '' only when even the short form doesn't fit."""
    if avail <= 2:
        return ""
    fit = shrink_to_fit(rollup_variants(wins), avail - 2)
    return f"  {fit}" if fit else ""


def rotate_page(total, budget, now=None):
    """(start, end, n_pages, page_idx) 1-indexed for a list of `total` items shown `budget`
    at a time, rotating every ~10s (stateless: int(now//10) % n_pages). n_pages == 1 when
    everything already fits -> caller should show no indicator."""
    if budget <= 0 or total <= budget:
        return 1, total, 1, 0
    n_pages = math.ceil(total / budget)
    idx = int((time.time() if now is None else now) // 10) % n_pages
    start = idx * budget
    end = min(total, start + budget)
    return start + 1, end, n_pages, idx


def is_critical_pane(p):
    """A pane needing an operator's attention RIGHT NOW: past its own ctx-refresh
    threshold, near the hard context ceiling regardless of --package, or stuck awaiting a
    permission prompt. Critical panes are PINNED into every rotation page — rotation must
    never be the reason an operator misses one (DESIGN-4, owner-approved: the run's only
    could-not-do-my-job was a 93.7%-ctx pane hidden by rotation)."""
    if p.get("shell"):
        return False
    return bool(p.get("ctx_over") or p.get("awaiting")
                or (p.get("ctx") is not None and p["ctx"] >= 85))


def pin_indices(base_indices, critical_idx, budget):
    """base_indices: the 0-based indices a plain rotation page would show. Ensures every
    index in critical_idx is present, evicting non-critical slots (last-first) to make
    room. Returns (final_indices sorted, contiguous) — contiguous is True only when
    nothing had to change, so the caller can keep its nicer 'N-M/T' range note."""
    if not critical_idx:
        return list(base_indices), True
    idx_set, changed = list(base_indices), False
    for c in critical_idx:
        if c in idx_set:
            continue
        evict_pos = next((p for p in range(len(idx_set) - 1, -1, -1)
                          if idx_set[p] not in critical_idx), None)
        if evict_pos is not None:
            idx_set[evict_pos] = c
            changed = True
        elif len(idx_set) < budget:
            idx_set.append(c)
            changed = True
    return sorted(set(idx_set)), not changed


def window_grid(wins, width, max_rows, dashes=False, now=None):
    """Windows as ASCII columns: window name as header, its panes stacked beneath.
    Fills banks left-to-right; when the full set doesn't fit max_rows, ROTATES the
    visible page of banks every ~10s (stateless: derived from wall clock, so the 2s
    refresh loop rotates naturally and --once shows whichever page is current) instead
    of permanently hiding overflow. A SINGLE window with more panes than fit rotates its
    OWN pane list the same way (a 6-pane window in a 1-pane-tall slot previously looked
    like a dead 1-seat window with no hint 5 more existed). CRITICAL panes/windows (see
    is_critical_pane) are PINNED — never rotated out; a page containing one is shown
    steadily instead of cycling away from it on a timer."""
    pane_row_budget = max(1, max_rows - (2 if dashes else 1))
    cell_budget = max(6, width - 2)  # a single column can never exceed the frame width
    cols = []
    for w in wins:
        header = ("*" if w["active"] else "") + w["name"]
        wp = w["panes"]
        pstart, pend, pn_pages, _ = rotate_page(len(wp), pane_row_budget, now)
        critical_idx = [i for i, p in enumerate(wp) if is_critical_pane(p)]
        final_idx, contiguous = pin_indices(list(range(pstart - 1, pend)), critical_idx,
                                            pane_row_budget)
        visible = [wp[i] for i in final_idx] if wp else wp
        panes = [pane_cell_fit(p, cell_budget) for p in visible] or ["-"]
        if pn_pages > 1 or not contiguous:
            room = max(0, cell_budget - visible_len(panes[-1]) - 2)
            note = shrink_to_fit(range_note_variants("panes", pstart, pend, len(wp)), room) \
                if contiguous else shrink_to_fit(count_note_variants(len(visible), len(wp)), room)
            if note:
                panes[-1] += f"  {note}"
        colw = max([visible_len(header)] + [visible_len(p) for p in panes])
        cols.append((header, panes, colw, bool(critical_idx)))
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

    def bank_rows(b):
        return 1 + (1 if dashes else 0) + max(len(p) for _h, p, _w, _c in b)

    def bank_critical(b):
        return any(c for _h, _p, _w, c in b)

    pages, page, page_rows, page_nwin = [], [], 0, 0
    for b in banks:
        need = bank_rows(b) + (1 if page else 0)
        if page and page_rows + need > max_rows:
            pages.append((page, page_nwin))
            page, page_rows, page_nwin = [], 0, 0
            need = bank_rows(b)
        page.append(b)
        page_rows += need
        page_nwin += len(b)
    if page:
        pages.append((page, page_nwin))
    if not pages:
        return []

    critical_page_idx = next((i for i, (pg, _n) in enumerate(pages)
                              if any(bank_critical(b) for b in pg)), None)
    if len(pages) == 1:
        page_idx = 0
    elif critical_page_idx is not None:
        page_idx = critical_page_idx  # PIN: hold on the critical page, no time rotation
    else:
        page_idx = int((time.time() if now is None else now) // 10) % len(pages)
    page_banks, _ = pages[page_idx]

    lines = []
    for bank in page_banks:
        depth = max(len(p) for _h, p, _w, _c in bank)
        if lines:
            lines.append("")
        lines.append("".join(pad_to(f"{BOLD}{UL}{h}{OFF}", w + 2) for h, _p, w, _c in bank))
        if dashes:
            lines.append("".join(pad_to("-" * w, w + 2) for _h, _p, w, _c in bank))
        for r in range(depth):
            lines.append("".join(pad_to(p[r] if r < len(p) else "", w + 2)
                                 for _h, p, w, _c in bank))
    lines = lines[:max_rows]
    if len(pages) > 1:
        start = sum(n for _b, n in pages[:page_idx]) + 1
        end = start + pages[page_idx][1] - 1
        variants = range_note_variants("windows", start, end, len(cols),
                                       pinned=critical_page_idx is not None)
        if lines and len(lines) >= max_rows:
            room = max(0, width - visible_len(lines[-1]) - 1)
            note = shrink_to_fit(variants, room)
            if note:
                lines[-1] = pad_to(lines[-1], max(0, width - visible_len(note) - 1)) + note
        else:
            note = shrink_to_fit(variants, width)
            if note:
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


def bar_cell_variants(cell, label_w, max_bar_w):
    """render_bar_cell content from full detail down to label+percent only — the percent
    (the safety-critical value) is NEVER dropped, only the suffix and bar shrink. Used when
    a PLAN LIMITS row has collapsed to a single column but even that overflows its budget,
    so the row never gets blind mid-value clip_line'd (the reported 'claude:main 5h ████~'
    bug — losing the percent entirely)."""
    variants = []
    for bw, suf in ((max_bar_w, True), (max_bar_w, False),
                    (max(4, max_bar_w // 2), False), (0, False)):
        v = render_bar_cell(cell, label_w, bw, with_suffix=suf)
        if not variants or variants[-1] != v:
            variants.append(v)
    return variants


def render_full(session, wins, nwin, npane, cells, notes, console, cache, cols, rows,
                no_package=False):
    base = (f"{BOLD}teamview{OFF} · session {BOLD}{session}{OFF} · {nwin} windows / "
           f"{npane} panes · {datetime.now().strftime('%H:%M:%S')}")
    head = base + package_cue(no_package, cols - visible_len(base))
    head += sys_cue(cols - visible_len(head))
    out = [head, ""]
    age = ""
    if cache and cache.get("ts"):
        m = int((datetime.now().timestamp() - cache["ts"]) // 60)
        # 'polled Nm ago' is the CACHE's age; a local-parse bar (codex) can be far older.
        # Hedge the header whenever any bar carries its own stale 'as of' stamp, so the
        # fresh-sounding poll age never over-claims those bars' freshness.
        hedge = (" — some bars older, see per-bar 'as of'"
                 if any(c[3].startswith("as of") for c in cells) else "")
        age = f"  {DIM}(providers polled {m}m ago{hedge}){OFF}"
    out.append(f"{BOLD}PLAN LIMITS{OFF}{age}")
    label_w = max([c[1] for c in cells], default=10) + 1
    bar_w = max(16, min(40, cols - label_w - 30))
    for c in cells:
        out.append("  " + render_bar_cell(c, label_w, bar_w))
    for n in notes:
        out.append(f"  {DIM}{n}{OFF}")
    out.extend("  " + l for l in console_lines(console, cols - 2))
    out.append("")
    whdr = f"{BOLD}WINDOWS{OFF} {DIM}(panes beneath){OFF}"
    out.append(whdr + rollup_suffix(wins, cols - visible_len(whdr)))
    grid_budget = rows - len(out) - 4
    out.extend("  " + l for l in window_grid(wins, cols - 2, grid_budget, dashes=True))
    out.append("")
    out.extend(legend_lines(cols))
    return out[:rows - 1]


def system_load():
    """Live (avail_mb, total_mb, load1, cores) — read-only, stdlib only (Linux
    /proc/meminfo + os.getloadavg). Any field is None when unavailable on this platform;
    never raises — decorative info must never crash a frame."""
    avail_mb = total_mb = load1 = None
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition(":")
            if k in ("MemAvailable", "MemTotal"):
                info[k] = int(v.strip().split()[0]) // 1024  # kB -> MB
        avail_mb, total_mb = info.get("MemAvailable"), info.get("MemTotal")
    except (OSError, ValueError, IndexError):
        pass
    try:
        load1 = os.getloadavg()[0]
    except (OSError, AttributeError):
        pass
    return avail_mb, total_mb, load1, os.cpu_count() or 1


def system_cell_variants(avail_mb, total_mb, load1, cores):
    """Full -> short -> RAM-only text for the system-resource cell, colored by PRESSURE
    (red when available RAM < ~500MB or load1 >= cores; yellow at the halfway warning band;
    else green) — an operator AND watcher see resource pressure at a glance (this run hit
    an OOM cascade). A pure function of the 4 fields, so it's testable without touching the
    OS. [] when neither RAM nor CPU data is available on this platform."""
    ram_full = ram_short = cpu = None
    if avail_mb is not None:
        color = RED if avail_mb < 500 else (YELLOW if avail_mb < 1500 else GREEN)
        ram_full = (f"{color}RAM {avail_mb}MB/{total_mb}MB{OFF}" if total_mb
                    else f"{color}RAM {avail_mb}MB{OFF}")
        ram_short = f"{color}{avail_mb}MB{OFF}"
    if load1 is not None:
        color = RED if load1 >= cores else (YELLOW if load1 >= cores * 0.75 else GREEN)
        cpu = f"{color}CPU {load1:.1f}/{cores}{OFF}"
    variants = []
    for parts in ((ram_full, cpu), (ram_short, cpu), (ram_short,)):
        v = "  ".join(x for x in parts if x)
        if v and (not variants or variants[-1] != v):
            variants.append(v)
    return variants


def sys_cue(avail):
    """The system-resource cell, shrunk to whatever room is available (same graceful
    degradation as package_cue) — "" when it doesn't fit or the platform has neither
    reading, never a mid-value clip."""
    if avail <= 2:
        return ""
    variants = system_cell_variants(*system_load())
    fit = shrink_to_fit(variants, avail - 2) if variants else ""
    return f"  {fit}" if fit else ""


NO_PACKAGE_CUE_VARIANTS = (
    f"{YELLOW}no --package: thresholds/roster off{OFF}",
    f"{YELLOW}no --package{OFF}",
    f"{YELLOW}no-pkg{OFF}",
)


def package_cue(no_package, avail):
    """The no-package cue, shrunk to whatever room is actually available — never emitted at
    a length that would need clip_line's blind mid-word cut ('...roster~' was the reported
    bug); "" (no cue at all) only when even the shortest form doesn't fit."""
    if not no_package or avail <= 2:
        return ""
    fit = shrink_to_fit(NO_PACKAGE_CUE_VARIANTS, avail - 2)
    return f"  {fit}" if fit else ""


def session_line(session, nwin, npane, cols=999, no_package=False):
    """no_package: --package was never given, so ctx-refresh thresholds and roster names
    never loaded — a bare ctxN% could otherwise read as 'confirmed under threshold' when
    it is really 'no threshold was ever checked' (an operator made a wrong renewal call on
    exactly this silent gap)."""
    base = (f"{BOLD}{session}{OFF} · {nwin} windows · {npane} panes · "
           f"{datetime.now().strftime('%H:%M:%S')}")
    s = base + package_cue(no_package, cols - visible_len(base))
    s += sys_cue(cols - visible_len(s))
    if visible_len(s) <= cols:
        return s
    short_base = f"{BOLD}{session[:max(4, cols - 22)]}{OFF} · {nwin}w · {npane}p"
    s2 = short_base + package_cue(no_package, cols - visible_len(short_base))
    return s2 + sys_cue(cols - visible_len(s2))


# The two table titles — one own line, bold+underlined, so each block's SCOPE is unmistakable
# and the session-stats line above is never mistaken for a table header.
LIMITS_HDR = f"{BOLD}{UL}PLAN LIMITS{OFF}"
WINDOWS_HDR = f"{BOLD}{UL}WINDOWS · PANES{OFF}"


def render_strip(session, wins, nwin, npane, cells, notes, console, cols, rows,
                 no_package=False):
    budget = max(2, rows - 3)  # rows 0-1 are the session line + the two-table header row;
    # one more row is reserved for the mini legend appended below
    label_w = max([c[1] for c in cells], default=10)
    for ncols in (1, 2, 3):
        bar_w = 22 if ncols == 1 else 14
        cell_w = label_w + bar_w + 8 + 15  # renew/as-of suffix stays in every fold
        need_rows = math.ceil(len(cells) / ncols) if cells else 0
        left_w = ncols * (cell_w + 2)
        if need_rows <= budget - 1 and left_w <= cols - 42:
            break
    grid_rows = math.ceil(len(cells) / ncols) if cells else 0
    row_budget = max(1, cols - 42)  # the ncols pick above is an ESTIMATE (cell_w budgets a
    # fixed +15 for the suffix, which a long "renews Wed 13:59" can exceed) — drop trailing
    # columns from a row that overflows it instead of letting the outer clip_line cut into a
    # bar's percent mid-value (the reported "claude:tecer 5h    ~" bug).
    left = []
    for r in range(grid_rows):
        row_cells = [render_bar_cell(cells[r + grid_rows * c], label_w, bar_w)
                     for c in range(ncols) if r + grid_rows * c < len(cells)]
        while len(row_cells) > 1 and visible_len(
                "  ".join(pad_to(s, cell_w) for s in row_cells)) > row_budget:
            row_cells = row_cells[:-1]
        if len(row_cells) > 1:
            row = "  ".join(pad_to(s, cell_w) for s in row_cells)
        else:
            # a single cell padded to the (possibly oversized, multi-column) cell_w can
            # STILL overflow row_budget on its own — bound it directly rather than let the
            # outer clip_line cut it wherever the combined left+right line happens to end
            row = row_cells[0] if row_cells else ""
            if visible_len(row) > row_budget and r < len(cells):
                row = shrink_to_fit(bar_cell_variants(cells[r], label_w, bar_w),
                                    row_budget) or row
            if visible_len(row) > row_budget:
                row = clip_line(row, row_budget)
        left.append(row)
    lw = min(max([visible_len(l) for l in left] + [len("PLAN LIMITS")], default=11), cols - 42)
    if notes:
        left.append(f"{DIM}{fit_join(notes, ' · ', max(0, lw - 1))}{OFF}")
    if console:
        cl = console_line(console)
        if visible_len(cl) > lw:
            names = [re.sub(r"\033\[[0-9;]*m", "", c).split(" ")[0] for c in console]
            prefix = f"{YELLOW}no usage API{OFF} {DIM}>{OFF} "
            cl = prefix + fit_join(names, ", ", max(0, lw - visible_len(prefix)))
            if visible_len(cl) > lw:  # even the compact form doesn't fit — names only, no
                cl = clip_line(cl, lw)  # numeric value is ever at stake on this line
        left.append(cl)
    right_w = cols - lw - 3
    right = window_grid(wins, right_w, budget)
    hdr_row = f"{pad_to(LIMITS_HDR, lw)}{DIM}|{OFF} {WINDOWS_HDR}"
    hdr_row += rollup_suffix(wins, cols - visible_len(hdr_row))
    out = [session_line(session, nwin, npane, cols, no_package), hdr_row]
    for i in range(budget):
        lseg = left[i] if i < len(left) else ""
        rseg = right[i] if i < len(right) else ""
        if not lseg and not rseg:
            break
        out.append(f"{pad_to(lseg, lw)}{DIM}|{OFF} {rseg}")
    leg = mini_legend(cols)
    if leg:
        out.append(leg)
    return out[:rows]


def render_narrow(session, wins, nwin, npane, cells, notes, console, cols, rows,
                  no_package=False):
    out = [session_line(session, nwin, npane, cols, no_package), LIMITS_HDR]
    label_w = max([c[1] for c in cells], default=8)
    bar_w = max(6, min(14, cols - label_w - 8))
    for c in cells:
        out.append(render_bar_cell(c, label_w, bar_w, with_suffix=False))
    for n in notes:
        out.append(f"{DIM}{n[:cols]}{OFF}")
    out.extend(console_lines(console, cols, max_lines=2))
    out.append(WINDOWS_HDR + rollup_suffix(wins, cols - visible_len(WINDOWS_HDR)))
    out.extend(compact_window_lines(wins, cols, max(1, rows - len(out) - 2)))
    leg = mini_legend(cols)
    if leg:
        out.append(leg)
    return out[:rows - 1]


def render_tiny(session, wins, nwin, npane, cells, notes, console, cols, rows,
                no_package=False):
    """LIMITS: one label + percent PER LINE (never 2-up flowed) — at this width a flowed
    pair sits close enough that a label can misread as paired with its NEIGHBOR's percent
    (observed: 'claude:main 5h' read against a different window's value). One entry per
    line makes each label unambiguously own its own number."""
    out = [session_line(session, nwin, npane, cols, no_package), f"{BOLD}{UL}LIMITS{OFF}"]
    limit_budget = max(1, (rows - 3) // 2)
    # The percent keeps its urgency color band even at this size — color costs ZERO
    # columns, and a bare '97%' rendered identically to '12%' was a verified false
    # all-clear (the glance view was structurally unable to show a red limit).
    limit_lines = []
    for c in cells:
        color = GREEN if c[2] < 60 else (YELLOW if c[2] < 85 else RED)
        limit_lines.append(f"{c[0]}: {color}{c[2]:.0f}%{OFF}")
    if len(limit_lines) > limit_budget:
        dropped = len(limit_lines) - limit_budget
        limit_lines = limit_lines[:limit_budget]
        limit_lines[-1] += f" {DIM}(+{dropped} more){OFF}"
    out.extend(limit_lines)
    note_toks = [re.sub(r"\s+", " ", n) for n in notes]
    if console:
        note_toks.append("no-API: " + " ".join(
            re.sub(r"\033\[[0-9;]*m", "", c).split(" ")[0] for c in console))
    out.extend(flow(note_toks, cols, max(1, rows - len(out) - 3)))
    thdr = f"{BOLD}{UL}WINDOWS{OFF}"
    out.append(thdr + rollup_suffix(wins, cols - visible_len(thdr)))
    out.extend(compact_window_lines(wins, cols, max(1, rows - len(out) - 2)))
    leg = mini_legend(cols)
    if leg:
        out.append(leg)
    return out[:rows - 1]


def render(args, session):
    cols = args.width or int(subprocess.run(["tput", "cols"], capture_output=True,
                                            text=True).stdout or 200)
    rows = args.height or int(subprocess.run(["tput", "lines"], capture_output=True,
                                             text=True).stdout or 45)
    roster = roster_map(args.package)
    thresholds = ctx_refresh_thresholds(args.package)
    wins, nwin, npane = session_tree(session, roster, thresholds)
    if not wins:
        return [f"no such tmux session: {session}",
                "sessions: " + " ".join(tmux_lines("list-sessions", "-F", "#{session_name}"))]
    cache = load_cache()
    cells, notes, console = usage_cells(cache)
    layout = choose_layout(cols, rows)
    no_package = not args.package
    # --no-rotate: LAYOUT is still chosen from the real terminal shape, but every internal
    # row/line budget (and the final row cap) is lifted so every window and every pane
    # renders — a COMPLETE snapshot, taller than the terminal if it must be, instead of
    # rotating pages a single --once frame can never show you the rest of.
    render_rows = 10 ** 6 if getattr(args, "no_rotate", False) else rows
    if layout == "full":
        out = render_full(session, wins, nwin, npane, cells, notes, console, cache, cols,
                          render_rows, no_package)
    elif layout == "strip":
        out = render_strip(session, wins, nwin, npane, cells, notes, console, cols,
                           render_rows, no_package)
    elif layout == "narrow":
        out = render_narrow(session, wins, nwin, npane, cells, notes, console, cols,
                            render_rows, no_package)
    else:
        out = render_tiny(session, wins, nwin, npane, cells, notes, console, cols,
                          render_rows, no_package)
    return [clip_line(l, cols) for l in out]


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
    k = parse_kimi_code({"usages": [{"model": "kimi-for-coding", "limit": 200, "used": 30,
                                     "reset_at": 7}]})
    check("kimi-code parser: pct from limit/used",
          k["windows"][0]["pct"] == 15.0 and k["windows"][0]["resets_at"] == 7)
    check("kimi-code parser: empty -> error", parse_kimi_code({}).get("error") == "no usage rows")
    c = parse_claude_statusline({"ts": 1, "rate_limits": {
        "five_hour": {"used_percentage": 51, "resets_at": 2},
        "seven_day": {"used_percentage": 19}, "seven_day_opus": {"used_percentage": 40}}})
    check("claude parser: window labels incl. model-specific",
          sorted(w["label"] for w in c["windows"]) == ["5h", "7d", "7d opus"])
    o = parse_oauth_limits({"limits": [
        {"kind": "session", "percent": 7, "resets_at": "2026-07-24T18:40:00+00:00"},
        {"kind": "weekly_all", "percent": 39, "resets_at": "2026-07-25T03:00:00+00:00"},
        {"kind": "weekly_scoped", "percent": 54, "resets_at": "2026-07-25T03:00:00+00:00",
         "scope": {"model": {"id": None, "display_name": "Fable"}, "surface": None}},
        {"kind": "mystery", "percent": None}]})
    check("oauth parser: 5h/7d/scoped-model labels, epoch resets, null-pct skipped",
          [w["label"] for w in o] == ["5h", "7d", "7d fable"]
          and o[2]["pct"] == 54.0 and isinstance(o[0]["resets_at"], int))
    cw = codex_windows_from_rl({"primary": {"used_percent": 3.0, "window_minutes": 10080,
                                            "resets_at": 5}, "secondary": None})
    check("codex windows: 10080min -> 7d", cw == [{"label": "7d", "pct": 3.0, "resets_at": 5}])
    global pane_signature
    real_sig = pane_signature
    sig_seq = {"%a": iter(["x", "x"]), "%b": iter(["one", "two"])}  # %a static, %b changing
    pane_signature = lambda pid: next(sig_seq[pid])
    working, awaiting = busy_panes(["%a", "%b"], gap=0)
    pane_signature = real_sig
    check("busy_panes: changed content -> working; static -> idle",
          working == {"%b"} and awaiting == set())
    check("busy_panes: empty input -> empty", busy_panes([], gap=0) == (set(), set()))

    claude_prompt = ("Do you want to make this edit to foo.py?\n"
                      " ❯ 1. Yes\n   2. Yes, allow all edits during this session\n"
                      "   3. No, and tell Claude what to do differently (esc)")
    codex_prompt = "Action Required: approve command execution before I can continue"
    trust_prompt = "Do you trust the files in this folder?"
    normal_tail = "streaming tokens... building response...\n$ "
    check("is_awaiting_approval: detects claude/codex/trust prompt signatures, "
          "not normal output",
          is_awaiting_approval(claude_prompt) and is_awaiting_approval(codex_prompt)
          and is_awaiting_approval(trust_prompt) and not is_awaiting_approval(normal_tail))

    real_sig2 = pane_signature
    sig_seq2 = {"%a": iter(["x", "x"]), "%b": iter([claude_prompt, claude_prompt])}
    pane_signature = lambda pid: next(sig_seq2[pid])
    working2, awaiting2 = busy_panes(["%a", "%b"], gap=0)
    pane_signature = real_sig2
    check("busy_panes: awaiting-approval detected from the latest sample, same capture",
          awaiting2 == {"%b"} and working2 == set())

    check("claude in-use: recent statusline write -> in use; stale/absent -> not",
          claude_in_use({"as_of": 1000}, now=1300) and not claude_in_use({"as_of": 1000}, now=1000 + CLAUDE_ACTIVE_SECS + 1)
          and not claude_in_use({"error": "no data file yet"}, now=1300))

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

    check("reference docs live behind their flags, off the -h path",
          "api/oauth/usage" in DOC_PROVIDERS and '"accounts"' in DOC_CONFIG
          and "opencode | env | file" in DOC_CONFIG and "api.z.ai" in DOC_PROVIDERS
          and all(s not in __doc__ for s in ("api.z.ai", '"accounts"')))
    check("legend: every marker discoverable from -h (fresh-eyes gap fix)",
          all(s in __doc__ for s in ("text cut", "active window", "pane match uncertain",
                                     "last activity", "= in use", "awaiting approval",
                                     "ctx-refresh threshold", "shell", "empty-title")))
    narrow_legend = [re.sub(r"\033\[[0-9;]*m", "", l) for l in legend_lines(80)]
    check("legend_lines: word-wraps at a narrow width instead of hard-clipping mid-word "
          "(the '...ctx~ = pane ma~' bug — every line fits, none end in a clip_line '~')",
          all(len(l) <= 80 for l in narrow_legend)
          and all(clip_line(l, 80) == l for l in narrow_legend)
          and "pane match uncertain" in " ".join(narrow_legend))
    full_legend_plain = " ".join(re.sub(r"\033\[[0-9;]*m", "", l) for l in legend_lines(500))
    check("legend_lines: no marker item dropped when everything fits on one wide line",
          all(re.sub(r"\033\[[0-9;]*m", "", item) in full_legend_plain
              for item in LEGEND_ITEMS))
    fake_console = [f"{CYAN}sakana{OFF} {DIM}(key present; console.sakana.ai){OFF}",
                    f"{CYAN}google{OFF} {DIM}(key present; aistudio.google.com){OFF}",
                    f"{CYAN}kimi{OFF} {DIM}(logged in; kimi.com){OFF}"]
    narrow_console = [re.sub(r"\033\[[0-9;]*m", "", l) for l in console_lines(fake_console, 68)]
    check("console_lines: word-wraps provider entries at a narrow width instead of "
          "hard-clipping mid-word (the '...google (ke~' bug at 70x40)",
          all(len(l) <= 68 for l in narrow_console)
          and "google (key present; aistudio.google.com)" in " ".join(narrow_console)
          and "sakana (key present; console.sakana.ai)" in " ".join(narrow_console)
          and "kimi (logged in; kimi.com)" in " ".join(narrow_console))
    check("console_lines: [] for no console providers; console_line unaffected (still used "
          "by render_strip's own narrow fallback)",
          console_lines([], 80) == [] and "no usage API" in console_line(fake_console))
    check("session resolution: NAME / 'session NAME' / inside-tmux / lone outside session",
          (resolve_session(["kg"], None, ["a", "b"]),
           resolve_session(["session", "kg"], None, ["a"]),
           resolve_session([], "cur", ["a", "b"]),
           resolve_session([], None, ["only"]),
           resolve_session([], None, ["a", "b"]),
           resolve_session(["session"], None, ["a"]))
          == ("kg", "kg", "cur", "only", None, "session"))
    # Regression (op-ux-1, dispatch #127-B): the ctx-refresh threshold '!' marker only fires
    # WITH --package, but a bare frame showed plain green ctxN% with no cue that thresholds
    # were never loaded — a tester made a WRONG renewal call reading "green" as "confirmed
    # under threshold" when it really meant "never checked". A visible header cue closes the
    # silent-false-negative gap.
    check("session_line: no-package cue shown ONLY when --package was never given",
          "no --package" in re.sub(r"\033\[[0-9;]*m", "", session_line("s", 1, 1, 999, True))
          and "no --package" not in re.sub(r"\033\[[0-9;]*m", "",
                                           session_line("s", 1, 1, 999, False))
          and "no --package" in re.sub(r"\033\[[0-9;]*m", "",
                                       session_line("s", 1, 1, 30, True)))  # survives the
                                       # narrow-fallback branch too, not just the wide one
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
    cells, notes, console = usage_cells(fake_cache)
    check("cells: one bar per window, money to notes, console-only nested apart",
          len(cells) == 3 and any("9.26" in n for n in notes)
          and not any("sakana" in n for n in notes)
          and any("sakana" in c for c in console)
          and "no usage API" in console_line(console))
    check("in-use highlight: cyan (no star) for in-use, dim for alt",
          "*" not in cells[0][0] and CYAN in cells[0][0] and DIM in cells[2][0])
    fresh = usage_cells({"ts": int(time.time()), "accounts": [
        {"provider": "claude", "name": "main", "in_use": True,
         "data": {"windows": [{"label": "7d fable", "pct": 54, "resets_at": None}],
                  "fresh": True, "as_of": int(time.time()) - 90000}}]})[0]
    check("oauth-fresh windows: old statusline as_of does NOT mark them 'as of' stale",
          len(fresh) == 1 and "as of" not in fresh[0][3])

    def P(name, busy=False, shell=False, harness="claude", model="opus-4-8",
          ctx=46.0, age="2m", approx=False, awaiting=False, ctx_over=False):
        return {"name": name, "busy": busy, "shell": shell, "harness": harness,
                "model": model, "ctx": ctx, "age": age, "approx": approx,
                "awaiting": awaiting, "ctx_over": ctx_over}
    pc = re.sub(r"\033\[[0-9;]*m", "", pane_cell(P("master", busy=True)))
    check("pane_cell: seat+ harness:model ctxN% age", pc == "master+ claude:opus-4-8 ctx46% 2m")
    check("pane_cell/pane_compact: awaiting-approval renders RED name?! (overrides busy '+')",
          RED + "stuck?!" + OFF in pane_cell(P("stuck", busy=True, awaiting=True))
          and RED + "stuck?!" + OFF in pane_compact(P("stuck", awaiting=True)))
    check("ctx_str: past-threshold renders RED ctxN%! regardless of the normal color band",
          re.sub(r"\033\[[0-9;]*m", "", ctx_str(30, over=True)) == "ctx30%!"
          and ctx_str(30, over=True).startswith(RED)
          and re.sub(r"\033\[[0-9;]*m", "", ctx_str(30, over=False)) == "ctx30%")
    check("pane_cell: ctx_over renders the past-threshold ctxN%! marker",
          "ctx42%!" in re.sub(r"\033\[[0-9;]*m", "", pane_cell(P("seat", ctx=42.0, ctx_over=True))))
    # dispatch #164-A (checker-verified FINDING-3): "no --package" clipped to a lone tilde
    # at 70w, the rotation footer clipped to '(windo~' at 80 and VANISHED at 80x14, and
    # limit/ctx values clipped mid-value ('claude:main 5h ████~' losing the %; 'ctx42%~'
    # losing the past-threshold '!'). Every cue/footer/value must degrade GRACEFULLY
    # (shrink to a shorter but still-complete form) instead of relying on clip_line's blind
    # mid-word/mid-value cut.
    crit_p = P("scientist", ctx=42.0, ctx_over=True, age="9m")
    pcv = pane_cell_variants(crit_p)
    check("pane_cell_variants: ctx% (+ its past-threshold '!') NEVER drops — age/harness "
          "shrink first, the DESIGN-4 safety signal survives to the last non-bare variant",
          all("ctx42%!" in v for v in pcv[:-1]) and pcv[-1] == pane_name(crit_p))
    check("pane_cell_fit: degrades to a shorter complete variant instead of mid-value "
          "clipping — ctx% survives at a width that still fits 'name ctx42%!'",
          "ctx42%!" in pane_cell_fit(crit_p, 20) and visible_len(pane_cell_fit(crit_p, 20)) <= 20)
    check("pane_cell_fit: an impossibly tight width still returns something COMPLETE "
          "(the bare name), never a mid-value clip",
          pane_cell_fit(crit_p, 3) == pane_name(crit_p))
    bcv = bar_cell_variants(("claude:main 5h", 14, 25.0, "renews 23:40"), 14, 22)
    check("bar_cell_variants: the percent NEVER drops — only the bar/suffix shrink",
          all("25%" in v for v in bcv))
    for w in (60, 70, 80):
        many_wins = [{"idx": str(i), "name": f"win{i}", "active": i == 0,
                     "panes": [P(f"seat{i}a"), P(f"seat{i}b", ctx=42.0, ctx_over=True)]}
                    for i in range(4)]
        many_cells = [(f"claude:main {lbl}", 14, pct, "renews Sat 03:00")
                     for lbl, pct in (("5h", 25.0), ("7d", 51.0), ("7d fable", 66.0))]
        for layout_fn, h in ((render_strip, 8), (render_narrow, 30), (render_tiny, 12)):
            out = layout_fn("improve-teamview", many_wins, 4, 8, many_cells,
                            ["deepseek $8.63 left"], [], w, h)
            plain = [re.sub(r"\033\[[0-9;]*m", "", l) for l in out]
            check(f"{layout_fn.__name__} at {w}w: no line exceeds the requested width "
                  "(no cue/footer/value overflow reaching the outer blind clip)",
                  all(len(l) <= w for l in plain))
    tmp_pkg = tempfile.mkdtemp()
    try:
        (Path(tmp_pkg) / "workers" / "toolsmith-tv").mkdir(parents=True)
        (Path(tmp_pkg) / "workers" / "toolsmith-tv" / "agent.md").write_text(
            "---\nagent: toolsmith-tv\nharness: claude\nctx-refresh: 50\n---\nbody\n",
            encoding="utf-8")
        (Path(tmp_pkg) / "workers" / "scientist").mkdir(parents=True)
        (Path(tmp_pkg) / "workers" / "scientist" / "agent.md").write_text(
            "---\nagent: scientist\nharness: claude\n---\nno ctx-refresh key here\n",
            encoding="utf-8")
        thr = ctx_refresh_thresholds(tmp_pkg)
        check("ctx_refresh_thresholds: reads per-agent ctx-refresh from a temp package "
              "fixture; absent key -> no threshold; no package -> {}",
              thr == {"toolsmith-tv": 50} and "scientist" not in thr
              and ctx_refresh_thresholds("") == {} and ctx_refresh_thresholds(None) == {})
    finally:
        shutil.rmtree(tmp_pkg, ignore_errors=True)
    check("pane_cell: shell pane -> dim name + explicit 'shell' tag; no-info pane -> harness only",
          re.sub(r"\033\[[0-9;]*m", "", pane_cell(P("gone", shell=True))) == "gone shell"
          and re.sub(r"\033\[[0-9;]*m", "", pane_cell(
              P("ov", harness="python3", model="", ctx=None, age=""))) == "ov python3")
    check("pane_compact: parenthesized agent info",
          re.sub(r"\033\[[0-9;]*m", "", pane_compact(P("master")))
          == "master(claude:opus-4-8 ctx46% 2m)")
    check("ctx color bands: green<60, yellow<85, red",
          GREEN in ctx_str(45) and YELLOW in ctx_str(70) and RED in ctx_str(90))
    check("uncertain pane match renders ctx~N%",
          "ctx~46%" in re.sub(r"\033\[[0-9;]*m", "", pane_cell(P("m", approx=True))))
    wins = [{"idx": "0", "name": "control", "active": True,
             "panes": [P("master", busy=True),
                       P("watcher", harness="opencode", model="deepseek-v4-pro", ctx=91.0,
                         age="5m")]},
            {"idx": "1", "name": "cli", "active": False, "panes": [P("cli", shell=True)]}]
    for layout_fn, dims in ((render_strip, (240, 8)), (render_narrow, (56, 40)),
                            (render_tiny, (58, 12)), ):
        out = layout_fn("sess", wins, 2, 3, cells, notes, console, *dims)
        joined = re.sub(r"\033\[[0-9;]*m", "", "\n".join(out))
        check(f"{layout_fn.__name__}: fits height, carries seats + provider + agent info",
              len(out) <= dims[1] and "master" in joined and "claude" in joined
              and "ctx46%" in joined and "deepseek" in joined)
    # Regression (hk-ux-1, dispatch #95, CRITICAL): reported "claude:main 5h" showing 1%
    # instead of the correct 45% at 60x12. Could not reproduce a formatting/truncation bug
    # after extensive width/value sweeps — the pipeline reads `pct` verbatim end to end, no
    # scaling or truncation touches it. Most likely explanation: a genuine 5h rate-limit
    # window reset between the tester's own sequential steps (their own T3 finding showed
    # "renews 18:39"; the dispatch landed at 19:24, ~45min after that reset time). Shipped
    # regardless: LIMITS now renders ONE label+percent per line (never flowed 2-up) so a
    # label can never visually run into a NEIGHBOR pair's value at this width — the likelier
    # root cause of "corruption" given the tester's own "misalignment" wording. This check
    # locks the exact known value in at the exact reported size.
    tiny_out = [re.sub(r"\033\[[0-9;]*m", "", l) for l in render_tiny(
        "sess", wins, 2, 3, [("claude:main 5h", 14, 45.0, "renews 18:39")], [], [], 60, 12)]
    check("render_tiny: a known plan-usage value (45%) renders EXACTLY at 60x12, one "
          "label+percent per line (no neighbor-pair bleed)",
          "claude:main 5h: 45%" in tiny_out
          and not any(l.startswith("claude:main 5h:") and "45%" not in l for l in tiny_out))
    out = render_full("sess", wins, 2, 3, cells, notes, console, fake_cache, 160, 40)
    plain = [re.sub(r"\033\[[0-9;]*m", "", l) for l in out]
    hdr = next((i for i, l in enumerate(plain) if "control" in l), None)
    check("render_full: grid — starred active window, panes with agent info beneath",
          any("PLAN LIMITS" in l for l in plain) and hdr is not None
          and any("master+ claude:opus-4-8 ctx46% 2m" in l for l in plain[hdr:])
          and any("*control" in l for l in plain)
          and not any("legend:" in l for l in plain))
    out = window_grid([{"name": "big", "active": True,
                        "panes": [P(f"p{i}", model="", ctx=None, age="") for i in range(9)]},
                       {"name": "other", "active": False, "panes": [P("x")]}], 44, 5)
    check("window_grid: height-capped with overflow note",
          len(out) <= 6 and any("more windows" in re.sub(r"\033\[[0-9;]*m", "", l)
                                for l in out) is False)  # same-bank cap truncates, no false note

    def plain(lines):
        return [re.sub(r"\033\[[0-9;]*m", "", l) for l in lines]
    rot_wins = [{"name": f"w{i}", "active": False, "panes": [P(f"w{i}p")]} for i in range(3)]
    g0 = plain(window_grid(rot_wins, 40, 4, now=0))
    g1 = plain(window_grid(rot_wins, 40, 4, now=10))
    g2 = plain(window_grid(rot_wins, 40, 4, now=20))
    g3 = plain(window_grid(rot_wins, 40, 4, now=30))
    check("window_grid: rotation shows a different bank per ~10s tick, deterministic + "
          "position indicator",
          any("w0" in l for l in g0) and not any("w1" in l for l in g0)
          and any("w1" in l for l in g1) and not any("w2" in l for l in g1)
          and any("w2" in l for l in g2) and not any("w0" in l for l in g2)
          and g3 == g0 and any("rotating" in l for l in g0))
    # Regression (op-ux-3 + sn-ux-1/2/3, dispatch #127-A, SEVERE): a SINGLE window with 6
    # panes rendered as if it had just 1 seat with NO indicator that 5 more were hidden —
    # operators could believe alive seats had died. Root cause: the bank/page rotation only
    # covered dropping whole WINDOWS; a single window's own over-tall pane list silently
    # truncated with no note (this predates Task 1 — the ORIGINAL pre-rotation code had the
    # same gap). Fix: each window's own pane list rotates too via rotate_page(), independent
    # of window/bank-level rotation.
    many_pane_win = [{"idx": "0", "name": "w", "active": True,
                      "panes": [P(f"s{i}") for i in range(6)]}]
    pg0 = plain(window_grid(many_pane_win, 200, 3, dashes=True, now=0))
    pg1 = plain(window_grid(many_pane_win, 200, 3, dashes=True, now=30))
    pg2 = plain(window_grid(many_pane_win, 200, 3, dashes=True, now=60))
    check("window_grid: a single window with MORE PANES than fit rotates its own pane "
          "list too, with an indicator (a 6-seat window must never render as if it had 1)",
          any("s0" in l for l in pg0) and not any("s3" in l for l in pg0)
          and any("s3" in l for l in pg1) and not any("s0" in l for l in pg1)
          and pg2 == pg0 and any("panes 1-1/6 - rotating" in l for l in pg0))
    # DESIGN-4 (owner-approved, dispatch #164-B): the run's only could-not-do-my-job was a
    # 93.7%-ctx pane hidden by rotation. A CRITICAL pane (past its own threshold, >=85% ctx,
    # or awaiting approval) must never rotate out of view.
    crit_pane_win = [{"idx": "0", "name": "w", "active": True,
                      "panes": [P(f"s{i}") for i in range(4)]
                      + [P("critical93", ctx=93.7)] + [P("s5")]}]
    crit_pg = [plain(window_grid(crit_pane_win, 200, 3, dashes=True, now=n))
              for n in (0, 10, 20, 30, 40, 50)]
    check("window_grid: a pane at >=85% ctx is PINNED — visible at EVERY rotation tick, "
          "never hidden",
          all(any("critical93" in l for l in pg) for pg in crit_pg))
    crit_win_set = [{"idx": str(i), "name": f"w{i}", "active": False,
                     "panes": [P(f"s{i}")]} for i in range(4)]
    crit_win_set[2]["panes"] = [P("stuck", awaiting=True)]
    crit_wg = [plain(window_grid(crit_win_set, 40, 4, dashes=True, now=n))
              for n in (0, 10, 20, 30, 40)]
    check("window_grid: a WHOLE WINDOW holding an awaiting-approval pane is PINNED — its "
          "bank/page never rotates away, tagged 'pinned' in the note",
          all(any("w2" in l for l in wg) for wg in crit_wg)
          and all(any("pinned" in l for l in wg) for wg in crit_wg))
    crit_cw = [plain(compact_window_lines(crit_win_set, 40, 1, now=n))
              for n in (0, 10, 20, 30)]
    check("compact_window_lines: a window holding a ctx_over/awaiting pane is PINNED the "
          "same way in narrow/tiny layouts",
          all(any("pinned" in l for l in cw) for cw in crit_cw)
          and len({tuple(cw) for cw in crit_cw}) == 1)  # same page every tick, never rotates
    cw0 = plain(compact_window_lines(rot_wins, 40, 1, now=0))
    cw1 = plain(compact_window_lines(rot_wins, 40, 1, now=10))
    cw2 = plain(compact_window_lines(rot_wins, 40, 1, now=20))
    cw3 = plain(compact_window_lines(rot_wins, 40, 1, now=30))
    check("compact_window_lines: rotation cycles a different page per ~10s tick, "
          "deterministic + full-cycle repeat",
          cw0 != cw1 and cw1 != cw2 and cw0 != cw2 and cw3 == cw0
          and any("rotating" in l for l in cw0))
    fit_wins = [{"name": "a", "active": True, "panes": [P("x")]}]
    check("window rotation: no position note when everything already fits",
          not any("rotating" in l for l in plain(window_grid(fit_wins, 80, 10)))
          and not any("rotating" in l
                     for l in plain(compact_window_lines(fit_wins, 80, 10))))
    # Regression (live crash 2026-07-24): a real full-screen frame can leave grid_budget at
    # 0 or negative once the provider bars eat the height (rows - len(out) - 4), and rotation
    # with an over-budget page produced an empty `lines` list that lines[-1] then indexed
    # into -> IndexError, crashing every wave's live teamview mid-run. Must never raise for
    # ANY max_rows/max_lines, including 0 and negative.
    for budget in (0, -1, -5):
        try:
            window_grid(rot_wins, 1, budget)
            compact_window_lines(rot_wins, 40, budget)
            ok = True
        except Exception:  # noqa: BLE001 — the check itself asserts "never raises"
            ok = False
        check(f"window_grid/compact_window_lines: never raise at max_rows/max_lines={budget} "
              "(overflow + zero/negative budget)", ok)

    # DESIGN-1 (owner-approved, dispatch #164-C): rotation means a single --once frame can
    # never show an operator the rest — --no-rotate gives a COMPLETE snapshot instead.
    ap_test = argparse.ArgumentParser()
    ap_test.add_argument("--no-rotate", action="store_true")
    check("--no-rotate: argparse flag parses to args.no_rotate=True",
          ap_test.parse_args(["--no-rotate"]).no_rotate is True
          and ap_test.parse_args([]).no_rotate is False)
    many_wins_c = [{"idx": str(i), "name": f"cw{i}", "active": i == 0, "panes": [P(f"cs{i}")]}
                  for i in range(8)]
    rotating = plain(window_grid(many_wins_c, 200, 3, dashes=True, now=0))
    complete = plain(window_grid(many_wins_c, 200, 10 ** 6, dashes=True, now=0))  # render()
    # passes this huge budget under --no-rotate — the exact mechanism, not a re-implementation
    rotating_joined, complete_joined = " ".join(rotating), " ".join(complete)
    check("--no-rotate semantics: a huge row budget (what render() passes under the flag) "
          "shows EVERY window, vs a normal budget which hides some (checked by presence, "
          "not the note's exact wording — the note itself may shrink at narrow widths)",
          not all(f"cw{i}" in rotating_joined for i in range(8))
          and all(f"cw{i}" in complete_joined for i in range(8)))
    rotating_c = plain(compact_window_lines(many_wins_c, 40, 3, now=0))
    complete_c = plain(compact_window_lines(many_wins_c, 40, 10 ** 6, now=0))
    check("--no-rotate semantics: compact_window_lines (narrow/tiny) shows EVERY window too",
          not all(f"cw{i}" in " ".join(rotating_c) for i in range(8))
          and all(f"cw{i}" in " ".join(complete_c) for i in range(8)))

    # Fix D (owner-approved item #172): system RAM+CPU readout, colored by pressure so an
    # operator AND watcher see resource pressure at a glance (this run hit an OOM cascade).
    check("system_cell_variants: RED when avail RAM < 500MB or load1 >= cores",
          RED in system_cell_variants(200, 8000, 1.0, 4)[0]
          and RED in system_cell_variants(4000, 8000, 4.0, 4)[0])
    check("system_cell_variants: YELLOW at the halfway warning band (500-1500MB avail, "
          "or load1 >= 75% of cores)",
          YELLOW in system_cell_variants(1000, 8000, 1.0, 4)[0]
          and YELLOW in system_cell_variants(4000, 8000, 3.0, 4)[0])
    check("system_cell_variants: GREEN when RAM and CPU are both comfortable",
          GREEN in system_cell_variants(4000, 8000, 1.0, 4)[0])
    check("system_cell_variants: [] when neither RAM nor CPU reading is available on "
          "this platform (decorative info must never crash or blank-render the header)",
          system_cell_variants(None, None, None, 4) == [])
    check("system_cell_variants: degrades to RAM-only when load avg is unavailable, "
          "never drops RAM data just because CPU data is missing",
          system_cell_variants(4000, 8000, None, 4) != []
          and all("CPU" not in v for v in system_cell_variants(4000, 8000, None, 4)))
    sysv = system_cell_variants(200, 8000, 1.0, 4)
    check("system_cell_variants: graceful shrink full -> short -> RAM-only — detail "
          "thins out but the RAM value itself is NEVER dropped while any variant remains",
          "RAM 200MB/8000MB" in sysv[0] and "CPU 1.0/4" in sysv[0]
          and "200MB" in sysv[1] and "CPU 1.0/4" in sysv[1]
          and "200MB" in sysv[-1] and "CPU" not in sysv[-1])
    for avail in (2, 5, 12, 20, 200):
        fit = shrink_to_fit(sysv, avail - 2) if avail > 2 else ""
        check(f"sys_cue shrink at avail={avail}: the fitted variant never exceeds its "
              "budget (picks the widest one that DOES fit, or '' when none fit)",
              fit == "" or visible_len(fit) <= avail - 2)
    check("sys_cue: never crashes on the live host and always fits the room given, at "
          "every width down to 0 (possibly '' when a reading is genuinely unavailable)",
          all(visible_len(sys_cue(w)) <= w for w in (0, 1, 2, 3, 5, 10, 40)))
    sweep_wins = [{"idx": str(i), "name": f"win{i}", "active": i == 0,
                  "panes": [P(f"seat{i}a"), P(f"seat{i}b", ctx=42.0, ctx_over=True)]}
                 for i in range(4)]
    sweep_cells = [(f"claude:main {lbl}", 14, pct, "renews Sat 03:00")
                  for lbl, pct in (("5h", 25.0), ("7d", 51.0), ("7d fable", 66.0))]
    # render_full is only reachable at cols >= 70 (choose_layout, line ~1132) — 60w always
    # routes to narrow/tiny instead, so it is excluded here (same reachability boundary
    # Fix A's own strip/narrow/tiny sweep above respects).
    for w in (70, 80):
        out_full = render_full("improve-teamview", sweep_wins, 4, 8, sweep_cells,
                               ["deepseek $8.63 left"], [], fake_cache, w, 30)
        plain_full = [re.sub(r"\033\[[0-9;]*m", "", l) for l in out_full]
        check(f"render_full at {w}w: header line (now carrying the live system RAM/CPU "
              "cue) never exceeds the requested width",
              all(len(l) <= w for l in plain_full))

    # ---- UX backlog items 2,4,5,6,7,8,9,10 (findings run tv-ux-review; fixed 2026-07-26) ----
    strip_sgr = lambda s: re.sub(r"\033\[[0-9;]*m", "", s)  # noqa: E731
    hot_cells = [("claude:main 5h", 14, 97.0, ""), ("zai 7d", 6, 12.0, "")]
    tiny_hot = render_tiny("sess", wins, 2, 3, hot_cells, [], [], 60, 12)
    hot_line = next((l for l in tiny_hot if "97%" in strip_sgr(l)), "")
    cool_line = next((l for l in tiny_hot if "12%" in strip_sgr(l)), "")
    check("item2: render_tiny at 60x12 keeps the urgency color band on LIMITS rows — a "
          "97% row carries RED SGR, a 12% row GREEN (the verified false all-clear)",
          RED in hot_line and GREEN in cool_line)
    for layout_fn, dims in ((render_strip, (220, 10)), (render_narrow, (70, 40)),
                            (render_tiny, (60, 12))):
        out_l = layout_fn("sess", wins, 2, 3, hot_cells, [], [], *dims)
        check(f"item2: {layout_fn.__name__} emits the one-line mini legend with the alarm "
              "keys (previously NO legend rendered below full size)",
              "?!=approval" in strip_sgr("\n".join(out_l))
              and all(visible_len(l) <= dims[0] for l in out_l))
    ml30 = strip_sgr(mini_legend(30))
    check("item2: mini legend drops TAIL items as width shrinks — alarm keys are the "
          "last thing lost, never the first",
          ml30.startswith("?!=approval") and "working" not in ml30)
    fl2 = strip_sgr(" ".join(legend_lines(70, max_lines=2)))
    check("item2: full-legend drop priority INVERTED — under a 2-line cap at 70 cols "
          "the alarm keys survive and tail items drop (was the reverse); the (+N more) "
          "note never pushes a line past width",
          "awaiting approval" in fl2 and "empty-title" not in fl2
          and all(len(strip_sgr(l)) <= 70 for l in legend_lines(70, max_lines=2)))

    roll_wins = [{"idx": "0", "name": "w0", "active": True,
                  "panes": [P("calm", ctx=30.0), P("hot", ctx=94.0, approx=True),
                            P("stuck", awaiting=True, ctx=91.0)]}]
    check("item4: rollup line — pane total, worst ctx (keeping its ~), red count, "
          "?! count",
          strip_sgr(rollup_variants(roll_wins)[0]) == "3 panes · worst ctx~94% · 2 red · 1 ?!")
    full_o = render_full("sess", roll_wins, 1, 3, hot_cells, [], [], fake_cache, 220, 50)
    strip_o = render_strip("sess", roll_wins, 1, 3, hot_cells, [], [], 220, 10)
    narrow_o = render_narrow("sess", roll_wins, 1, 3, hot_cells, [], [], 70, 40)
    tiny_o = render_tiny("sess", roll_wins, 1, 3, hot_cells, [], [], 60, 12)
    check("item4: the alarm rollup renders at EVERY layout size (full 220x50, strip "
          "220x10, narrow 70x40, tiny 60x12) above the rotating windows detail",
          all(any(("2 red" in strip_sgr(l) or "2r" in strip_sgr(l)) for l in o)
              for o in (full_o, strip_o, narrow_o, tiny_o)))

    check("item5: color-band thresholds documented — a legend item AND -h carry the "
          "green<60 / yellow<85 / red>=85 numbers",
          any("<60" in strip_sgr(i) and ">=85" in strip_sgr(i) for i in LEGEND_ITEMS)
          and "green<60" in __doc__ and "red>=85" in __doc__)

    check("item6: '…' is the ONE text-cut glyph — clip_line and clean_title never emit "
          "'~' (reserved for ctx-match uncertainty), and the legend says so",
          clip_line("x" * 50, 10).endswith("…") and "~" not in clip_line("x" * 50, 10)
          and clean_title("a-very-long-pane-title-here").endswith("…")
          and any("text cut" in strip_sgr(i) for i in LEGEND_ITEMS))

    check("item7: --help-security states the write-set, EVERY endpoint, and the "
          "never-touches-tmux guarantee",
          all(s in DOC_SECURITY for s in ("teamview-providers.json", "api.anthropic.com",
              "api.z.ai", "api.deepseek.com", "api.kimi.com", "api.moonshot",
              "NEVER mutates tmux", "no send-keys")))
    aud_acc = [{"provider": "claude", "name": "main",
                "source": {"type": "statusline",
                           "path": "/home/x/.claude/rbtv-runtime/plan-usage.json"}},
               {"provider": "zai", "name": "alt", "source": {"type": "env", "var": "ZAI_ALT"}}]
    aud = audit_lines(aud_acc, {"accounts": [
        {"provider": "claude", "name": "main", "data": {"windows": [1, 2]}}]})
    check("item7: --audit lines — provider:name -> source kind -> BASENAME-redacted path "
          "-> last poll result; env vars by NAME; a full path never appears",
          aud[0] == "claude:main -> statusline -> …/plan-usage.json -> ok (2 windows)"
          and aud[1] == "zai:alt -> env -> $ZAI_ALT -> not polled yet"
          and not any("/home/x" in l for l in aud))
    check("item7: an explicit --config path that does not exist WARNS instead of "
          "silently falling back to auto-discovery; no --config -> no warning",
          "auto-discovery" in (missing_config_warning("/nope/teamview.json") or "")
          and missing_config_warning("") is None and missing_config_warning(None) is None)

    check("item8: --help-panes documents every pane state — ctx~ cause AND what clears "
          "it, the shell tag, the '?' empty-title placeholder, '+' vs age",
          all(s in DOC_PANES for s in ("ctx~", "Clears when", "shell", "EMPTY title",
                                       "WORKING", "ambiguous")))
    check("item8: pane_compact and pane_cell_variants carry the explicit 'shell' tag too",
          "gone shell" in strip_sgr(pane_compact(P("gone", shell=True)))
          and "gone shell" in strip_sgr(pane_cell_variants(P("gone", shell=True))[0]))

    check("item9: unknown session -> teaching refusal (stderr + exit 2 in main): names "
          "the bad session, suggests the closest match, lists the live set; valid -> None",
          session_error("kg-viewz", ["kg-views", "other"]).startswith(
              "no such tmux session: kg-viewz — did you mean 'kg-views'?")
          and "sessions: kg-views other" in session_error("kg-viewz", ["kg-views", "other"])
          and session_error("kg-views", ["kg-views", "other"]) is None
          and "no tmux sessions" in session_error("x", []))
    h = subprocess.run([sys.executable, str(Path(__file__).resolve()), "-h"],
                       capture_output=True, text=True,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"}).stdout
    h_flat = " ".join(h.split())
    check("item9: --selftest carries a real help line in -h (was empty)",
          "self-test suite" in h_flat)
    check("item10: -h vocabulary — --interval says display-only repaint (does NOT "
          "re-poll); --refresh notes the codex exception and the --once pairing",
          "display refresh seconds" in h_flat and "NOT re-poll" in h_flat
          and "codex excepted" in h_flat and "pair with --once" in h_flat)
    stale_cells = [("codex 7d", 8, 40.0, "as of Wed 09:00"),
                   ("claude:main 5h", 14, 10.0, "renews 23:00")]
    hedged = "\n".join(render_full("sess", roll_wins, 1, 3, stale_cells, [], [],
                                   fake_cache, 220, 50))
    unhedged = "\n".join(render_full("sess", roll_wins, 1, 3,
                                     [("claude:main 5h", 14, 10.0, "renews 23:00")],
                                     [], [], fake_cache, 220, 50))
    check("item10: full-layout header hedges 'providers polled Nm ago' when any bar "
          "carries its own older 'as of' stamp — and only then",
          "some bars older" in hedged and "some bars older" not in unhedged)
    check("item10: --help-providers explains a model-scoped weekly ('7d fable') as a "
          "SUBSET of the plain 7d window",
          "SUBSET" in DOC_PROVIDERS and "7d fable" in DOC_PROVIDERS)

    print(f"\nselftest: {'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s))")
    sys.exit(1 if failures else 0)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(prog="teamview", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", nargs="*",
                    help="tmux session — NAME or 'session NAME' (default: the session you "
                         "are in; outside tmux, the only running session)")
    ap.add_argument("--package", default=os.environ.get("RBTV_TEAMVIEW_PACKAGE", ""),
                    help="team-kit run package for pane->agent roster names")
    ap.add_argument("--config", help="accounts config JSON (default ~/.config/rbtv/teamview.json)")
    ap.add_argument("--once", action="store_true", help="print one frame and exit")
    ap.add_argument("--no-rotate", action="store_true",
                    help="disable rotation: show EVERY window/pane in one COMPLETE "
                         "snapshot (best with --once; output can grow taller than the "
                         "terminal)")
    ap.add_argument("--interval", type=int, default=2,
                    help="display refresh seconds (default 2) — repaint cadence only, does "
                         "NOT re-poll providers (that is --refresh / --provider-ttl)")
    ap.add_argument("--refresh", action="store_true",
                    help="poll providers NOW before rendering (codex excepted: its usage is "
                         "a local session-file parse with no endpoint to re-poll); without "
                         "--once this then enters the live loop — pair with --once for a "
                         "one-shot fresh frame")
    ap.add_argument("--provider-ttl", type=int, default=600,
                    help="re-poll providers in background when cache older than SECS (default 600)")
    ap.add_argument("--width", type=int, help="override detected terminal width")
    ap.add_argument("--height", type=int, help="override detected terminal height")
    ap.add_argument("--poll-providers", action="store_true",
                    help="fetch provider usage into the cache and exit (loop-internal mode)")
    ap.add_argument("--help-providers", action="store_true",
                    help="show each provider's usage source and exit")
    ap.add_argument("--help-config", action="store_true",
                    help="show the accounts config schema and exit")
    ap.add_argument("--help-security", action="store_true",
                    help="show the audit surface — every file written, every endpoint "
                         "contacted, and the never-touches-tmux guarantee — and exit")
    ap.add_argument("--help-panes", action="store_true",
                    help="show every pane state/marker, its cause and what clears it, "
                         "and exit")
    ap.add_argument("--audit", action="store_true",
                    help="dump the resolved accounts (provider:name -> source kind -> "
                         "redacted path -> last poll result) and exit; never prints a key, "
                         "token, or full path")
    ap.add_argument("--selftest", action="store_true",
                    help="run the built-in offline self-test suite (pure Python — no tmux, "
                         "no network, no writes outside temp dirs) and exit 0/1")
    args = ap.parse_args()

    docs = {"help_providers": DOC_PROVIDERS, "help_config": DOC_CONFIG,
            "help_security": DOC_SECURITY, "help_panes": DOC_PANES}
    for attr, doc in docs.items():
        if getattr(args, attr):
            print(doc, end="")
            return

    if args.selftest:
        cmd_selftest()
        return

    warn = missing_config_warning(args.config)
    if warn:
        print(warn, file=sys.stderr)

    if args.audit:
        for line in audit_lines(load_accounts(config_path(args.config)), load_cache()):
            print(line)
        return
    if args.poll_providers:
        poll_providers(args)
        print(f"cached: {cache_file()}")
        return

    sessions = tmux_lines("list-sessions", "-F", "#{session_name}")
    session = resolve_session(args.session, current_session(), sessions)
    err = session_error(session, sessions)
    if err:
        print(err, file=sys.stderr)
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
            # no trailing newline: a full-height frame must fill the pane EXACTLY, or the extra
            # newline scrolls the top line (the session-stats line) off the pane.
            sys.stdout.write("\033[H\033[2J" + frame())
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
