#!/usr/bin/env python3
"""teamview — team-run dashboard: panes with per-agent model/context/activity, plus
plan-limit bars for every AI provider account on the machine.

⚠ teamview RENDERS the run's state; it does NOT sense it (settle ledger R24, task 7.34).
`team-monitor` is the run's one raw-source sensor — it reads the tmux panes, harness session
files and /proc, and writes ONE canonical snapshot to {goal}/runs/run-{n}/state.json. This
program reads that file and nothing else, ALWAYS shows the snapshot's age, and renders a stale
snapshot as a visible WARNING rather than as silently-current data. Two lanes stay outside that
boundary and are named where they live: the provider plan-limit bars (they read provider
accounts, not run state) and the box CPU% (state.json's box{} carries no cpu field). See
README.md § "Proving the boundary".

The run package resolves from --package, else by walking UP from the current directory; nothing
resolves to a guess and every failure to read the snapshot renders LOUDLY (an empty dashboard
reads as a quiet room). Layouts adapt to the pane size; provider data caches under
~/.cache/rbtv/ and re-polls in the background. When the terminal is big
enough to hold the limits block AND every window/pane at once, that COMBINED view renders
statically. Only when it is too small does the body CYCLE every ~10s below the constant
first line: the windows/panes view — itself paged into as many views as the height needs —
then the plan-limits view, then the MESSAGES view (the coordination log's last sends off
the snapshot, aligned rows: how long ago · sender→recipient · as much text as the row
holds; the slot exists
only when the snapshot carries a message tail), then back around (wall-clock derived, so
--once shows whichever page is current). Nothing is permanently hidden. --view pins one
body instead: limits (bars only), panes (windows/panes only), messages (last sends only),
or combined (= --no-rotate: everything in one
frame even when it grows taller than the terminal, best paired with --once). The WINDOWS
header carries the run's average dispatch payload ("dispatch ~N tok avg/seat" — the
~tokens a freshly launched seat must read before working: shared boot files plus its own
seat.md/memory.md, computed by the sensor into the snapshot's dispatch_tokens field). A
CRITICAL pane — past its own ctx-refresh threshold, >=85% context, or awaiting approval —
PINS the cycle on its windows page (the limits page waits) and never cycles out of view;
the alarm rollup rides the header of BOTH views so no glance loses it. A
pane stuck at a permission/trust prompt (detected in its captured tail) renders its name RED
with a `?` marker. With --package, a pane whose context used % has reached ITS OWN seat's
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

The legend is NOT on the dashboard — every row there goes to data. Run
`teamview interface-legend` to print the marker key and exit.

Legend (dashboard markers): + working · … text cut · * active window (on a window
header) and * active pane (prefixing a seat name — tmux has one active pane per
window, so several can show; the starred header ranks them) · N% ctx usage
(~N% pane match uncertain; '~' means ONLY that, never truncation; the + … markers
render magenta so they stay legible on dark backgrounds) ·
green<60 / yellow<85 / red≥85 ctx and limit-bar color bands (plain red means high value,
no threshold involved) · Nm/Nh last activity · account in use (a live agent process is
spending it) vs dim account configured (credential present, nothing running) ·
? awaiting approval (red, on the seat name) · N%! past this seat's ctx-refresh
threshold · shell harness exited · ? empty-title pane (dim).

Reference:  --help-providers  usage source per provider (read-only; keys never printed)
            --help-config     accounts config schema (multi-account)
            --help-security   audit surface: writes, endpoints, never-touches-tmux
            --help-panes      every pane state/marker, cause and remedy
            --audit           resolved accounts -> source -> redacted path -> poll result
            full docs         orchestration/cli/teamview/README.md
"""
import argparse
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
            plan-usage.json) until a real session of that account runs again. Which Claude
            ACCOUNT is in use comes from the live processes' own CLAUDE_CONFIG_DIR, never
            from statusline recency (a run whose seats never fire the statusline used to
            read as no Claude account in use at all — issues.md G-17).
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
one of opencode | env | file | statusline | codex-local | kimi-local | none. An account is
highlighted IN USE only while a LIVE agent process on this box spends it (claude resolved
per CLAUDE_CONFIG_DIR, opencode per its --model <provider>/<id> prefix, codex/kimi by
process); an account with a credential and nothing running is CONFIGURED, rendered dim.
Pin either state per account with "in_use": true/false.

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
claude:<tag> (statusline file plan-usage-<tag>.json; OAuth credentials from that dir). Only ONE
Claude account is ever RENDERED — the one in use (or "main" when none is), labelled bare
"claude"; the others are still polled and cached, just not shown.
"""

DOC_SECURITY = """Security / audit surface — what teamview touches (verify with --audit):

WRITES — the ONLY files teamview ever writes:
  {XDG_CACHE_HOME|~/.cache}/rbtv/teamview-providers.json  provider usage cache (+ its .tmp)
TMUX — teamview makes NO tmux call at all (R24). It reads the run's state.json snapshot;
team-monitor is the only component that touches panes. Nothing here can mutate tmux state
because nothing here speaks to tmux.

RUN STATE — read-only from {run-folder}/state.json. teamview never writes that file; the
sensor's single-writer flock is unaffected by any number of readers.

NETWORK — the complete endpoint list; each credential is sent ONLY to its own provider:
  api.anthropic.com/api/oauth/usage         claude (stored OAuth token, NEVER refreshed)
  api.z.ai/api/monitor/usage/quota/limit    zai
  api.deepseek.com/user/balance             deepseek
  api.kimi.com/coding/v1/usages | /usage    kimi (opt-in sk-kimi key only)
  api.moonshot.ai|.cn/v1/users/me/balance   kimi (Moonshot platform key only)
All read-only GETs. google/sakana have no usage endpoint and are never contacted.

PROCESSES — `ps -eo pid=,args=` plus /proc/<pid>/environ for the CLAUDE_CONFIG_DIR of each
live claude process (own-uid reads only), to decide which accounts are IN USE. Read-only:
teamview never signals, starts, or stops a process. No environment value other than
CLAUDE_CONFIG_DIR is inspected, and none is ever printed.

CREDENTIALS — read-only from the harness stores (opencode auth.json, ~/.claude*/
.credentials.json, env vars, statusline/rollout files). Keys and tokens are NEVER printed:
--audit redacts paths to their basename and shows env-var NAMES only; fetch errors carry
the exception class name only, never the request.
"""

DOC_PANES = """Pane states and markers — every form a pane row can take, and what clears it:

  seat+           RECENTLY ACTIVE — this seat's harness wrote to its transcript within 45s
                  of the snapshot's capture. ⚠ R24 changed this signal's instrument: it used
                  to mean "visible content changed across two tmux captures ~0.6s apart".
                  Coarser now, and relabelled rather than silently reused. Work is bursty, so
                  a seat flips between + and unmarked as turns start and finish.
  seat            idle this sample (no marker).
  seat?   (red)   AWAITING APPROVAL — the pane tail matches a permission/trust prompt.
                  Clears when the prompt is answered in that pane.
  N%              context-window used % (ctx usage), colored green <60 / yellow <85 /
                  red >=85.
  N%!     (red)   past this seat's OWN ctx-refresh threshold (workers/<agent>/agent.md
                  frontmatter) — only checked WITH --package.
  ~N% (aka ctx~)  pane match UNCERTAIN: ctx-monitor could not uniquely map this pane's
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
MARK = "\033[95m"  # status markers (+ …): bright magenta — legible on dark bgs, where
#                    DIM vanished; unclaimed by the red/yellow/green/cyan semantics
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


# Process names that spend a provider account, and the provider each one spends. opencode is
# provider-agnostic — its account comes from the `--model <provider>/<id>` prefix in its argv.
AGENT_PROCESSES = {"claude": "claude", "codex": "codex", "kimi": "kimi", "opencode": None}
# opencode's model-prefix vocabulary -> teamview provider (inverse of OPENCODE_STORE_KEYS,
# plus the identity spellings opencode also accepts).
OPENCODE_PROVIDER_ALIASES = {v: k for k, v in OPENCODE_STORE_KEYS.items()}
OPENCODE_PROVIDER_ALIASES.update({k: k for k in OPENCODE_STORE_KEYS})


def ps_processes():
    """[(pid, args)] for every process on the box — one ps call. [] if ps is unavailable."""
    out = []
    try:
        r = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True)
    except OSError:
        return out
    for ln in r.stdout.splitlines():
        parts = ln.strip().split(None, 1)
        if len(parts) == 2:
            out.append((parts[0], parts[1]))
    return out


def claude_account_of(pid, home=None):
    """Which Claude account a live process spends, from CLAUDE_CONFIG_DIR in that process's
    OWN environment: ~/.claude (or unset) -> 'main', ~/.claude-<tag> -> '<tag>'.
    Falls back to 'main' — the meaning of an unset var — when the environment cannot be read
    (no /proc, or a foreign uid); on such a platform a tagged account running alone would be
    attributed to main, which is why the read, not the fallback, is the intended path."""
    try:
        env = Path(f"/proc/{pid}/environ").read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return "main"
    for entry in env.split("\0"):
        if entry.startswith("CLAUDE_CONFIG_DIR="):
            name = Path(entry.split("=", 1)[1].rstrip("/")).name
            if not name.startswith(".claude-"):
                return "main"                      # ~/.claude itself
            return name[len(".claude-"):] or "alt"  # matches discover_accounts' tagging
    return "main"


def opencode_account_of(args):
    """(provider, 'main') for an opencode process, from its `--model <provider>/<id>` argv —
    None when the process names no provider (nothing is marked on inference)."""
    m = re.search(r"(?:--model|-m)[= ]+([\w.-]+)/", args or "")
    prov = OPENCODE_PROVIDER_ALIASES.get(m.group(1).lower()) if m else None
    return (prov, "main") if prov else None


def live_agent_accounts(procs=None, home=None):
    """{(provider, account)} that a LIVE agent process on this box is actually spending.

    IN USE is a fact about running processes, never about stored credentials (issues.md
    G-17): the previous rule marked an account in use whenever its source type was
    harness-backed — i.e. whenever a key or login existed — which lit up six idle providers
    while dimming the two Claude accounts a whole run was burning. An account with a
    credential and no live process is CONFIGURED, not IN USE.

    Machine-wide by design, a superset of the rendered session's panes: an agent spending an
    account from another tmux session, or outside tmux entirely, still spends it."""
    live = set()
    for pid, args in (ps_processes() if procs is None else procs):
        toks = args.split()
        head = os.path.basename(toks[0]) if toks else ""
        if head not in AGENT_PROCESSES:
            continue
        if head == "opencode":
            acct = opencode_account_of(args)
            if acct:
                live.add(acct)
        elif head == "claude":
            live.add(("claude", claude_account_of(pid, home)))
        else:
            live.add((AGENT_PROCESSES[head], "main"))
    return live


def account_in_use(account, live):
    """True when a live process spends THIS account. `live` is the set from
    live_agent_accounts(); an explicit config `in_use` overrides it (the flag survives into
    the cache as `in_use_explicit`, so the renderer honors it too)."""
    if account.get("_in_use_explicit") or account.get("in_use_explicit"):
        return bool(account.get("in_use"))
    return (account["provider"], account.get("name", "main")) in (live or set())


def load_accounts(cfg_path, home=None, opencode_path=None, live=None):
    accounts = None
    if cfg_path.is_file():
        try:
            accounts = json.load(open(cfg_path, encoding="utf-8")).get("accounts")
        except (OSError, json.JSONDecodeError) as e:
            print(f"warning: unreadable config {cfg_path}: {e}", file=sys.stderr)
    if not accounts:
        accounts = discover_accounts(home, opencode_path)
    live = live_agent_accounts(home=home) if live is None else live
    for a in accounts:
        if "in_use" in a:
            a["_in_use_explicit"] = True
        else:
            a["in_use"] = account_in_use(a, live)
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
        # in_use is a LIVE fact and the cache can be minutes old, so the renderer recomputes
        # it every frame; this value is the poll-time reading (--audit / cache readers).
        out["accounts"].append({"provider": a["provider"], "name": a.get("name", "main"),
                                "in_use": bool(a.get("in_use")),
                                "in_use_explicit": bool(a.get("_in_use_explicit")),
                                "data": data})
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


# ---------- the snapshot: teamview's ONLY run-state source (settle ledger R24, task 7.34) ----------
#
# teamview does not sense. `team-monitor` is the run's one raw-source sensor (tmux panes,
# harness session files, /proc RAM and pressure) and writes ONE canonical snapshot to
# {goal}/runs/run-{n}/state.json; teamview RENDERS it. Nobody else reads the panes — PRIN-2
# parity: one source of truth for the facts AND for their treatment.
#
# ⚠ TWO LANES ARE DELIBERATELY OUTSIDE THIS BOUNDARY, AND BOTH ARE NAMED SO A GREP-PROOF CAN
# SCOPE THEM HONESTLY (a grep that passes because someone quietly scoped it is theatre):
#
#   LANE 1 — PROVIDER PLAN-LIMIT BARS. They read PROVIDER ACCOUNTS, not run state, and task
#     7.34's own _Note:_ orders them left exactly as they are ("do not 'purify' them out").
#     Their raw reads: ps_processes (`ps -eo pid=,args=`), claude_account_of
#     (/proc/<pid>/environ, for CLAUDE_CONFIG_DIR only), opencode_store
#     (~/.local/share/opencode/auth.json), claude_oauth_windows / parse_claude_statusline
#     (~/.claude*), codex_windows_from_rl (~/.codex/sessions).
#   LANE 2 — BOX CPU USAGE (cpu_usage_pct, /proc/stat). state.json's box{} carries
#     available_mb/total_mb/swap/load1/5/15/cores/pressure_memory and NO cpu field. Ruled
#     PROVISIONAL by the run-2 leader 2026-07-27 (seats/leader/ruling-734-cpu-cell.md),
#     extending the _Note:_'s own classification to a second named lane: box CPU is telemetry
#     outside the state.json boundary. ⚠ IT IS NOT A FIELD SOMEONE SHOULD "JUST MOVE" INTO
#     box{}: cpu_usage_pct is a BETWEEN-FRAMES delta (teamview frames ~1s) while team-monitor
#     captures every ~20s, so the same label at the sensor's cadence would silently become a
#     20-second average. See the follow-on item; it carries this warning in its own words.
#
# Everything else — panes, seats, models, context %, ctx-refresh thresholds, activity,
# prompt-pending, RAM, liveness, absent roster rows — comes from the snapshot and NOTHING else.

SNAPSHOT_NAME = "state.json"

# team-monitor's DEFAULT_INTERVAL is 20.0s, so 60s is three missed captures — no longer "live".
# A sensor that dies is detected by its consumer, because a snapshot that stops advancing is
# exactly what a dead sensor looks like from outside (team-monitor README § Lifecycle).
SNAPSHOT_STALE_S = 60.0

# The `+` working marker. ⚠ ITS MEANING CHANGED WITH R24 AND THE LEGEND SAYS SO: it used to mean
# "this pane's visible content differed across two captures 0.6s apart" (teamview sampling tmux
# itself); it now means "this seat's harness wrote to its transcript within RECENT_ACTIVITY_S of
# the capture". Coarser, and from a different instrument — relabelled rather than silently reused.
RECENT_ACTIVITY_S = 45.0


def find_package(start=None):
    """The run folder, by walk-up from `start` (default: cwd) — the first ancestor holding a
    `state.json`. None when there is none.

    REUSE, NOT INVENTION: `coordinate` already resolves its run package from a cwd walk-up, and
    every seat's cwd is inside its own run package, so a bare `teamview` keeps working from any
    seat pane. Deliberately NOT a search of `.rbtv/goals/*/runs/*` from an assumed vault root —
    that would be inventing a discovery convention this system does not have (PRIN-7, PRIN-10)."""
    try:
        d = Path(start).resolve() if start else Path.cwd().resolve()
    except OSError:
        return None
    for cand in (d, *d.parents):
        if (cand / SNAPSHOT_NAME).is_file():
            return cand
    return None


def load_snapshot(package):
    """(snapshot, error) — EXACTLY ONE is None; error is human text, never an exception.

    ⚠ EVERY FAILURE MUST BE RETURNED AS TEXT AND RENDERED, never swallowed into an empty frame.
    That is G-153's lesson turned into a contract: teamview's per-seat ctx-refresh marker used to
    read a pre-restructure path, got {} on every KG-shaped package, and FAILED OPEN — a total
    read failure was indistinguishable from 'nobody set a threshold'. A dashboard that renders
    nothing reads as a quiet room."""
    if not package:
        return None, "no run package given and none found by walking up from the current directory"
    path = Path(package) / SNAPSHOT_NAME
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"cannot read {path}: {e.strerror or e}"
    try:
        snap = json.loads(raw)
    except ValueError as e:
        return None, (f"{path} is not valid JSON ({e}) — team-monitor writes tmp+os.replace, so "
                      "a reader never sees a PARTIAL file; this one is corrupt")
    if not isinstance(snap, dict) or "captured_at" not in snap or "seats" not in snap:
        return None, (f"{path} is not a team-monitor snapshot: no captured_at / seats. "
                      "Is team-monitor running? `team-monitor status --package <run-folder>`")
    return snap, None


def snapshot_refusal(package_arg, session_arg, found, snap_session=None):
    """The teaching refusal for an unresolvable snapshot — None when everything resolves.
    Callers print it to stderr and exit 2.

    It PRINTS THE EXACT COMMAND rather than naming a flag: the owner uses teamview
    interactively, and R24 removed the bare-invocation auto-pick this refusal replaces. The
    contract it inherits is `session_error`'s, kept verbatim in spirit — a bogus name once
    rendered an 'empty' frame on STDOUT at exit 0, so a wrapper script recorded success for a
    view that showed nothing."""
    if not found:
        where = f"--package {package_arg}" if package_arg else f"the current directory ({Path.cwd()})"
        return (f"no {SNAPSHOT_NAME} found from {where}.\n"
                f"teamview renders a team-monitor snapshot; it no longer reads tmux directly.\n"
                f"  run it from inside a run folder, or name one:\n"
                f"      teamview --package /path/to/<goal>/runs/run-N\n"
                f"  if the run folder is right but has no {SNAPSHOT_NAME}, the sensor is not "
                f"running:\n"
                f"      team-monitor start --package /path/to/<goal>/runs/run-N")
    if session_arg and snap_session and session_arg != snap_session:
        return (f"this run package's snapshot is for session '{snap_session}', not "
                f"'{session_arg}'.\n"
                f"  render it as it is:   teamview --package {found}\n"
                f"  or point at the run folder whose session is '{session_arg}':\n"
                f"      teamview --package /path/to/<goal>/runs/run-N")
    return None


# ---------- snapshot -> the shapes the renderers already consume ----------

# TWINS of ctx_monitor.short_model / ctx_monitor.fmt_age (../ctx-monitor/ctx_monitor.py:684,:689).
# DUPLICATED ON PURPOSE and declared so: importing the sensor engine is exactly the coupling R24
# exists to cut, and 13 lines of pure string formatting is the cheap side of that trade. Declared
# duplicates get fixed together; undeclared ones drift silently. Change one -> change the other.

def short_model(model):
    m = re.sub(r"^claude-", "", model or "")
    return re.sub(r"-\d{8}$", "", m)[:14]


def fmt_secs(secs):
    """Compact duration, the ctx_monitor.fmt_age spelling minus its 'now' floor — an AGE display
    must not round a real 80-second staleness down to the word 'now'."""
    secs = max(0, int(secs))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m{secs % 60:02d}s"
    if secs < 86400:
        return f"{secs // 3600}h{secs % 3600 // 60:02d}m"
    return f"{secs // 86400}d{secs % 86400 // 3600}h"


def fmt_age(age_s):
    """Last-activity age for a pane row — ctx_monitor.fmt_age's twin, fed the snapshot's
    precomputed `last_activity_age_s` instead of an absolute stamp."""
    if age_s is None:
        return ""
    secs = max(0, int(age_s))
    if secs < 90:
        return "now"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h{secs % 3600 // 60:02d}m"
    return f"{secs // 86400}d{secs % 86400 // 3600}h"


def snapshot_age_s(snap, now=None):
    """Seconds since the snapshot's CAPTURE.

    ⚠ `captured_at`, NEVER `written_at`. team-monitor stamps captured_at as the FIRST act of a
    capture, before any raw read, and never restamps it; written_at is stamped at serialization.
    A frozen sensor therefore produces a snapshot that visibly AGES — which is the whole thing
    the staleness warning and this age display ride on. Keying on written_at would satisfy
    'carries a timestamp' while defeating staleness detection entirely, and it would LOOK right:
    on a healthy run the two differ by ~0.1s and their ISO strings are usually identical."""
    ts = (snap or {}).get("captured_at")
    if not isinstance(ts, (int, float)) or isinstance(ts, bool):
        return None
    return max(0.0, (time.time() if now is None else now) - ts)


def age_variants(age_s, stale_after=SNAPSHOT_STALE_S):
    """(full, short) snapshot-age forms — NEITHER IS EVER EMPTY, unlike the degradable cues.
    'age is always on screen' is a criterion, so this text is part of the header's BASE and is
    never the thing that gets dropped to make room."""
    if age_s is None:
        return (f"{RED}SNAPSHOT AGE UNKNOWN{OFF}", f"{RED}age?{OFF}")
    a = fmt_secs(age_s)
    if age_s >= stale_after:
        return (f"{RED}{BOLD}STALE SNAPSHOT {a} — sensor may be dead{OFF}",
                f"{RED}{BOLD}STALE {a}{OFF}")
    return (f"{DIM}snap {a} old{OFF}", f"{DIM}snap {a}{OFF}")


def snapshot_stale(snap, now=None, stale_after=SNAPSHOT_STALE_S):
    age = snapshot_age_s(snap, now)
    return age is None or age >= stale_after


# ---------- headless rows: the snapshot's SECOND source (design-760 §1/§4, task 7.74) ----------
#
# A headless session occupies a SEAT but no pane, so the pane tree is blind to it by construction.
# team-monitor joins the daemon's `jobs_log` to the run's `sessions.csv` and writes the result
# into the same snapshot as `headless[]` (plus `headless_unattributed` when that join fails);
# teamview renders it as ONE MORE trailing pseudo-window, the exact shape `roster_absent` already
# uses — same pane cells, same grid, same rotation, every layout for free. A second rendering
# path for a second source is how two blocks of one dashboard come to disagree.
#
# ⚠ SNAPSHOT ONLY, and that is design-760's criterion (1): nothing below opens heart.db, reads
# sessions.csv, or looks at a pane. `started_age_s` IS design-760 §5's `taken_at − started_at`,
# computed ONCE by the writer — like every other age this file renders (see fmt_age, fed the
# sensor's precomputed `last_activity_age_s`). Recomputing it here would put one quantity in two
# homes (PRIN-11) and let the two drift apart.

# A non-terminal row quiet this long renders as a WARNING. A DISPLAY design call, disclosed here
# because design-760 fixes no number: a headless one-shot lives seconds (§5), so a row still
# claiming to run five minutes on is the state worth seeing. Deliberately NOT SNAPSHOT_STALE_S —
# that number means "the sensor may be dead", and equal values would be a coincidence of value,
# never of meaning. A PARAMETER, not an inline constant: the selftest drives other values.
HEADLESS_STALE_S = 300.0


def headless_cell(name, state="", outcome="", age=""):
    """One headless row in the pane-cell shape every layout already renders. The slots are the
    seat row's, REUSED rather than re-specified: `harness` carries the job's state and `model`
    its outcome, so pane_agent_bits renders 'state:outcome' exactly where a seat renders
    'harness:model'. ctx stays None — a headless session has no pane and therefore no context
    reading, and a fabricated 0% would enter the alarm rollup as health."""
    return {"name": name, "active": False, "shell": False, "busy": False, "awaiting": False,
            "harness": state, "model": outcome, "ctx": None, "approx": False,
            "ctx_over": False, "cls": "", "age": age}


def headless_quiet_s(row, taken_at):
    """Seconds since this row last showed life — its transcript's mtime where it has one, else
    the row's own age. None when the snapshot cannot say, which is never read as health."""
    last = row.get("last_activity")
    if isinstance(last, (int, float)) and not isinstance(last, bool) \
            and isinstance(taken_at, (int, float)):
        return max(0.0, taken_at - last)
    age = row.get("started_age_s")
    return age if isinstance(age, (int, float)) and not isinstance(age, bool) else None


def headless_panes(snap, stale_after=HEADLESS_STALE_S):
    """`headless[]` as pane cells: seat + state + age on EVERY row, `outcome` on the terminal
    ones, a quiet non-terminal row RED and labelled `stale`.

    Terminal-ness is read off the PRESENCE of `outcome` — the sensor emits that field on exactly
    the terminal statuses and nowhere else, so teamview needs no copy of the status vocabulary
    (the same reason agent_type_bit refuses to hold a value list).

    ⚠ A ROW WITHOUT A SEAT IS FLAGGED — never dropped, never shown as a session row. `seat` is
    REQUIRED by the row schema and guaranteed at the dispatch door (design-760 §3), so a seatless
    row means that guarantee broke upstream. Both quiet answers are the ones design-760 §4
    forbids: hiding it is the invisibility NEED-3 exists to close, and rendering it as a nameless
    session row is the owner's rider violated. It renders as neither."""
    rows = (snap or {}).get("headless")
    if not isinstance(rows, list):
        return []
    taken = (snap or {}).get("captured_at")
    out = []
    for r in rows:
        seat = (r.get("seat") or "").strip() if isinstance(r, dict) else ""
        if not seat:
            ref = (str(r.get("exec_id"))
                   if isinstance(r, dict) and r.get("exec_id") is not None else "?")
            out.append(headless_cell(f"{RED}MALFORMED ROW exec {ref} — no seat{OFF}"))
            continue
        outcome = r.get("outcome")
        code = outcome.get("exit_code") if isinstance(outcome, dict) else None
        quiet = headless_quiet_s(r, taken)
        out.append(headless_cell(
            f"{RED}{seat} stale{OFF}"
            if (not outcome and quiet is not None and quiet >= stale_after) else seat,
            state=str(r.get("state") or "?"),
            outcome=("" if not outcome else f"exit{code}" if code is not None else "ended"),
            age=fmt_age(r.get("started_age_s")) or "?"))
    return out


def headless_window_name(snap):
    """The headless block's header — and the ONE place `headless_unattributed` renders.

    ⚠ A WARNING, NEVER A ROW (design-760 §4). A `jobs_log` row whose session_id joins no
    dispatch-time record cannot be shown as a session — that is the mis-attribution the incident
    field exists to make impossible — and it cannot be silent either. So it rides the BLOCK'S OWN
    HEADER as a count: unmistakably not a seat, unmissable while the block is on screen."""
    inc = (snap or {}).get("headless_unattributed")
    if not isinstance(inc, dict):
        return "headless"
    n = inc.get("count")
    if not isinstance(n, int) or isinstance(n, bool):
        n = len(inc.get("exec_ids") or inc.get("rows") or [])
    return f"headless {RED}{BOLD}!! {n} UNATTRIBUTED{OFF}" if n else "headless"


def snapshot_tree(snap, now=None):
    """([{idx, name, active, panes:[pane-dict]}], nwin, npane) built ONLY from the snapshot.

    `name` is "INDEX NAME" when the snapshot carries a window name, and the bare INDEX when it
    does not — a snapshot written by a pre-window-name sensor still renders, one field poorer,
    never blank. The index is ALWAYS shown and always leads: it is the tmux target, while the
    name is display-only and drifts independently of what the window holds.

    `active` on a window is tmux's `#{window_active}` — exactly ONE per session. Each pane
    carries its own `active` from `#{pane_active}` — one per WINDOW, so a multi-window frame
    stars several panes and the starred HEADER is what ranks them. The two are kept as
    separate fields and never ANDed here: a renderer that wants "the focused split" ANDs
    them itself, and one that wants "the tab you'd attach to" reads only the header's.

    This closes field (1) of the R24 follow-on. Its field (2), box CPU%, must NOT be merged
    in — see ideas.md for why that one changes meaning at the sensor's cadence.

    `roster_absent` — the GHOSTROW input — renders as its own trailing pseudo-window. Dropping it
    would be the exact failure this run keeps paying for: a seat whose pane left the room would
    render as nothing, and absence would be indistinguishable from health.

    `headless[]` / `headless_unattributed` (design-760) render as one more trailing pseudo-window,
    for the same reason and in the same shape — see the section above. BOTH FIELDS ABSENT INVENTS
    NOTHING: a pre-design-760 snapshot renders byte-for-byte as it always did."""
    order, by_idx = [], {}
    for s in (snap or {}).get("seats") or []:
        idx = str(s.get("window") or "?")
        if idx not in by_idx:
            wname = (s.get("window_name") or "").strip()
            label = f"{idx} {wname}" if wname and wname != idx else idx
            by_idx[idx] = {"idx": idx, "name": label,
                           "active": bool(s.get("window_active")), "panes": []}
            order.append(idx)
        act_age = s.get("last_activity_age_s")
        pct, thr = s.get("ctx_pct"), s.get("ctx_refresh")
        by_idx[idx]["panes"].append({
            "name": s.get("seat") or clean_title(s.get("title")),
            "active": bool(s.get("pane_active")),
            "shell": s.get("liveness") == "shell",
            "busy": isinstance(act_age, (int, float)) and act_age <= RECENT_ACTIVITY_S,
            "awaiting": bool(s.get("prompt_pending")),
            "harness": "" if s.get("liveness") == "shell" else (s.get("harness") or ""),
            "model": short_model(s.get("model")),
            "ctx": pct,
            "approx": bool(s.get("ctx_ambiguous")),
            "ctx_over": thr is not None and pct is not None and pct >= thr,
            "cls": (s.get("agent_type") or "").strip(),
            "age": fmt_age(act_age)})
    wins = [by_idx[i] for i in order]
    absent = (snap or {}).get("roster_absent") or []
    if absent:
        wins.append({"idx": "-", "name": f"{RED}absent{OFF}", "active": False, "panes": [
            {"name": f"{RED}{a.get('seat') or '?'}{OFF}", "active": False,
             "shell": False, "busy": False,
             "awaiting": False, "harness": str(a.get("liveness") or "absent"), "model": "",
             "ctx": None, "approx": False, "ctx_over": False,
             "cls": (a.get("agent_type") or "").strip(),
             "age": str(a.get("reason") or "")[:12]} for a in absent]})
    hpanes = headless_panes(snap)
    if hpanes or (snap or {}).get("headless_unattributed"):
        wins.append({"idx": "-", "name": headless_window_name(snap),
                     "active": False, "panes": hpanes})
    return wins, len(wins), sum(len(w["panes"]) for w in wins)


def snapshot_thresholds(snap):
    """{seat: ctx-refresh %} straight off the snapshot's own seat records.

    THIS IS G-153'S STRUCTURAL CURE: the thresholds used to be re-read from seat descriptors by a
    SECOND path that could drift out of step with the sensor's — and did, silently, for every
    post-restructure package. Taking them from the same snapshot as the ctx% they gate removes
    the second path entirely. An empty result is still NOT 'everyone is fine' — it is 'no
    threshold was ever checked' — so the caller still raises a visible cue on {}."""
    return {s["seat"]: s["ctx_refresh"] for s in (snap or {}).get("seats") or []
            if s.get("seat") and isinstance(s.get("ctx_refresh"), int)}


def box_load(snap):
    """(avail_mb, total_mb, load1, cores, cpu_pct) for system_cell_variants.

    First four from the snapshot's box{} — no /proc read. cpu_pct from THIS process's /proc/stat
    delta: the ruled exempt LANE 2 documented at the top of this section, because box{} carries
    no cpu field and moving it to the sensor's ~20s cadence would change the metric."""
    box = (snap or {}).get("box") or {}
    return (box.get("available_mb"), box.get("total_mb"), box.get("load1"),
            box.get("cores") or os.cpu_count() or 1, cpu_usage_pct())


BUSY_GLYPHS = r"[⠀-⣿✳✻✽✶✢]"  # TUI title spinner glyphs, stripped out of a pane title


def clean_title(title):
    t = re.sub(BUSY_GLYPHS, "", title or "").strip()
    return (t[:18] + f"{MARK}…{OFF}") if len(t) > 19 else (t or "?")




def ctx_str(pct, approx=False, over=False):
    """over: this seat's own ctx-refresh threshold has been reached — always RED, trailing
    '!' (past-threshold marker), regardless of the normal color-band it would otherwise get."""
    color = GREEN if pct < 60 else (YELLOW if pct < 85 else RED)
    bang = "!" if over else ""
    c = RED if over else color
    return f"{c}{'~' if approx else ''}{pct:.0f}%{bang}{OFF}"


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


def agent_type_bit(p):
    """The seat's declared agent type (task 7.80), straight off the snapshot — the sensor's
    `agent_type` field, rendered without a second source.

    ⚠ The key was spelled `class` until 2026-07-28; it is `agent_type` now, for exact parity
    with the registry record it publishes (owner ruling `r-agent-type-field-name`, PRIN-10).

    ⚠ NO VALUE LIST HERE, DELIBERATELY, and this renderer must never grow one. The string
    is displayed exactly as the snapshot carries it; teamview knows no vocabulary and
    validates nothing. The reason is already ruled for the sensor
    (`ruling-780-literals-withdrawn-derive-dont-list.md` RULING 2, and `coord.py:338-345`
    before it): a name list inside a tool every run shares encodes ONE campaign's role
    vocabulary into all of them, and a MANDATE cannot be expressed as a name list.

    ⚠⚠ AND IT IS NOT A PRIVILEGE TOKEN. THIS FIELD IS A SENSOR OBSERVATION OF A DECLARED
    CLAIM AND IS NEVER AN AUTHORIZATION; THE IDENTITY GATE IS THE ONLY AUTHORIZATION. The
    descriptor's declaration is a CLAIM, the snapshot's field is an OBSERVATION of it.
    Nothing here may ever gate a permission on it — displaying is not authorizing. The bar is
    spelled out rather than implied because the 2026-07-28 rename took the field's NAME to
    exact parity with a registry record whose own definition says an agent type "DRIVES SOME
    OF THE AGENT'S PERMISSIONS". It does not do so here, and the old name's difference from
    that record used to make the confusion impossible; this paragraph replaced that defence.
    """
    return f"{DIM}{p['cls']}{OFF}" if p.get("cls") else ""


def pane_star(p):
    """The '*' PREFIX marking tmux's active pane — the one split in this window holding the
    cursor. Every window has exactly one, so a multi-window frame shows several; the window
    header's own '*' is what ranks them (only ONE window is active session-wide, so
    '*header + *pane' together read as 'the focused split you'd land on').

    A PREFIX, not a suffix, and deliberately: the suffix slot already carries '+' (busy) and
    '?' (awaiting approval), and pane_cell_variants shrinks cells from the RIGHT — a suffix
    star would be the first thing dropped on a narrow frame, which is where knowing the
    focus matters most. One column, never dropped."""
    return f"{DIM}*{OFF}" if p.get("active") else ""


def pane_name(p):
    """Seat name with its state marker: RED name? when stuck at a permission/trust prompt
    (AWAITING approval — the pane tail matched a prompt signature), else the plain busy '+'.
    Both forms keep the active-pane '*' prefix — a focused pane is still focused while it
    waits on a prompt, and that combination ('*name?') is precisely the one worth seeing."""
    if p.get("awaiting"):
        return f"{pane_star(p)}{RED}{p['name']}?{OFF}"
    return pane_star(p) + p["name"] + (f"{MARK}+{OFF}" if p["busy"] else "")


def shell_cell(p):
    """Harness exited — a bare shell sits in the pane. The explicit 'shell' tag separates
    this KNOWN state from a live pane whose agent info merely failed to resolve (the two
    previously rendered identically as a dim bare name)."""
    return f"{pane_star(p)}{DIM}{p['name']} shell{OFF}"


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
    very last non-bare variant.

    The seat's AGENT TYPE is carried as its own bit rather than folded into pane_agent_bits(),
    whose three bits are indexed POSITIONALLY just below — a fourth bit in that list would
    silently shift ctx% into the age slot. It drops FIRST of all: an agent type is near-static,
    it is the cheapest thing to lose when the frame narrows, and the safety signals must
    outlive it."""
    if p["shell"]:
        return [shell_cell(p), f"{pane_star(p)}{DIM}{p['name']}{OFF}"]
    name = pane_name(p)
    bits = pane_agent_bits(p)
    idx, hm, ctx, age = 0, None, None, None
    if p.get("harness") or p.get("model"):
        hm, idx = bits[idx], idx + 1
    if p.get("ctx") is not None:
        ctx, idx = bits[idx], idx + 1
    if p.get("age"):
        age = bits[idx]
    cls = agent_type_bit(p)
    variants = []
    for parts in ((name, cls, hm, ctx, age), (name, hm, ctx, age),
                  (name, hm, ctx), (name, ctx), (name,)):
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
    bits = [b for b in [agent_type_bit(p)] if b] + pane_agent_bits(p)
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
    return out + OFF + MARK + "…" + OFF


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


def current_claude_only(accounts):
    """Only ONE Claude account is ever shown: the one in use. Several Claude config dirs can
    exist on a box, but only the account a live session spends is the owner's current plan —
    the rest are noise, and dropping them also collapses the label back to a bare 'claude'
    (account_label only tags when a provider has >1 row). With none in use, 'main' stands in."""
    cl = [a for a in accounts if a["provider"] == "claude"]
    if len(cl) < 2:
        return accounts
    keep = [a for a in cl if a.get("in_use")] or [a for a in cl if a.get("name", "main") == "main"]
    keep = keep[:1] or cl[:1]
    return [a for a in accounts if a["provider"] != "claude" or a is keep[0]]


def usage_cells(cache, live=None):
    """(bar_cells, note_bits, console_bits): bar cell = (label, label_vis, pct, suffix);
    notes = API-backed facts (balances, errors); console_bits = providers whose usage is NOT
    programmatically readable (nested under one 'console only' group by the renderers).

    `live` = the live_agent_accounts() set: when given, IN-USE highlighting is recomputed
    from the processes running RIGHT NOW rather than replayed from the cache, which may be
    minutes old (in-use flips far faster than the provider poll). Omit it to render the
    cache's own poll-time reading."""
    cells, notes, console = [], [], []
    if not cache:
        return cells, ["providers: no data yet (first poll pending)"], console
    accounts = [dict(a, in_use=account_in_use(a, live)) if live is not None else a
                for a in cache.get("accounts", [])]
    accounts = current_claude_only(accounts)
    multi = {}
    for a in accounts:
        multi[a["provider"]] = multi.get(a["provider"], 0) + 1
    now_ts = datetime.now().timestamp()
    for a in accounts:
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


def compact_window_lines(wins, width, max_lines, now=None, extra_slots=0):
    """Narrow/tiny windows block: each window starts its own line ('*name:' then panes),
    wrapping BETWEEN panes so no pane is ever clipped away mid-token. When the full set
    doesn't fit max_lines, ROTATES the visible page of windows every ~10s (same
    wall-clock derivation as window_grid) instead of permanently hiding overflow. A page
    holding a CRITICAL pane (is_critical_pane) is PINNED — shown steadily instead of
    rotating away from it on a timer.

    extra_slots > 0 puts this block into the caller's WHOLE-VIEW cycle: the rotation
    wheel gains that many extra slots after the window pages, and when the wall clock
    lands on one, the function returns that extra slot's 0-based INDEX (an int, not a
    list) — 'not this block's turn' — so the caller renders the matching other view
    (plan limits, messages). A CRITICAL page pins the whole wheel: the extra slots are
    skipped until the pane is dealt with."""
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
    total_slots = len(pages) + extra_slots
    if critical_page_idx is not None:
        page_idx = critical_page_idx  # PIN: hold on the critical page, no time rotation
    elif total_slots <= 1:
        page_idx = 0
    else:
        slot = int((time.time() if now is None else now) // 10) % total_slots
        if slot >= len(pages):
            return slot - len(pages)  # an extra slot's turn — its index picks the view
        page_idx = slot
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
# The ctx keys live in their OWN group, rendered right-aligned on the legend's last line
# (owner-requested): usage %, the ~ uncertainty mark, the ! threshold mark, and the color
# bands all describe the same on-screen number, so they read as one block, set apart from
# the general markers by the horizontal gap.
LEGEND_CTX = (f"{DIM}N%{OFF} ctx usage", f"{RED}~{OFF} uncertain",
              f"{RED}!{OFF} ctx refresh due",
              f"{GREEN}<60{OFF} {YELLOW}<85{OFF} {RED}≥85{OFF} bands")
LEGEND_ITEMS = (
    f"{RED}?{OFF} awaiting approval",
    f"{MARK}+{OFF} working", f"{MARK}…{OFF} text cut",
    f"{DIM}*{OFF} active window (header) / active pane (seat)",
    f"{DIM}Nm/Nh{OFF} last activity", f"{CYAN}account{OFF} in use",
    f"{DIM}account{OFF} configured",
    f"{DIM}shell{OFF} harness exited", f"{DIM}?{OFF} empty-title pane",
)


def legend_lines(width, max_lines=4):
    """The full marker legend: general items WORD-WRAPPED (never hard-clipped) to the
    given width, then the ctx key-group RIGHT-ALIGNED on its own final line — one block,
    set apart by the gap. Ctx keys drop from their tail when even a full line is too
    narrow for the whole group."""
    body = flow(LEGEND_ITEMS, width, max_lines - 1)
    sep = f" {DIM}·{OFF} "
    ctx = shrink_to_fit([sep.join(LEGEND_CTX[:n])
                         for n in range(len(LEGEND_CTX), 0, -1)], max(0, width - LEG_GAP))
    if ctx:
        body.append(" " * LEG_GAP + ctx)  # indented own line — reads as its own block
    return body


LEG_GAP = 8  # spaces between the general-keys block and the ctx block


def interface_legend_lines(width=80):
    """The standalone marker key — `teamview interface-legend`. NO layout renders a legend
    any more (owner ruling 2026-07-28: every dashboard row goes to data), so this command is
    the ONLY place the key exists on screen, and it is built from the SAME LEGEND_ITEMS /
    LEGEND_CTX tuples the renderers mark with. That shared source is the point: a marker
    added to the dashboard cannot silently go undocumented here.

    One item per line rather than the old packed row — this output is not competing for
    dashboard space, so it spends the rows on legibility instead."""
    out = [f"{BOLD}teamview interface-legend{OFF} {DIM}— the dashboard's marker key{OFF}", ""]
    out.append(f"{BOLD}PANE AND WINDOW MARKERS{OFF}")
    out.extend("  " + clip_line(i, max(0, width - 2)) for i in LEGEND_ITEMS)
    out.append("")
    out.append(f"{BOLD}CONTEXT USAGE{OFF}")
    out.extend("  " + clip_line(i, max(0, width - 2)) for i in LEGEND_CTX)
    out.append("")
    out.append(f"{DIM}Cause and remedy for each pane state: teamview --help-panes{OFF}")
    return out


def agent_type_census(panes):
    """['3 staff', '1 worker', '2 unclassified'] — the room's seats GROUPED BY THE VALUE THE
    SNAPSHOT CARRIES, most common first, ties broken alphabetically so the line is stable
    between refreshes.

    ⚠ IT GROUPS, IT DOES NOT CLASSIFY. There is no list of known values here and no notion
    of which value 'counts' as anything — that arithmetic is the consumer's (the room-idle
    aggregate reads the snapshot, not this line), and putting it here would encode one
    campaign's vocabulary into a tool every run shares.

    The absence marker is NOT special-cased: it is simply one of the values counted, which
    is why an incompletely-classified room reads its own incompleteness off this line
    instead of showing a number that looks whole. A room where nothing declares renders
    exactly one term, and that term says so.

    Empty when no pane carries the field at all — a pre-7.80 snapshot renders as it always
    did rather than growing an empty term."""
    counts = {}
    for p in panes:
        c = (p.get("cls") or "").strip()
        if c:
            counts[c] = counts.get(c, 0) + 1
    return [f"{DIM}{n} {c}{OFF}"
            for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def rollup_variants(wins):
    """The persistent alarm-rollup — '13 panes · worst ~94% · 1 red · 0 ?' — rendered
    at EVERY layout size on the windows header line, above the rotating detail. Rotation
    can hide panes; this line is the fixed summary that proves (or disproves) 'nothing is
    alarming' from any single glance (DESIGN item 4: a 93.7%-ctx pane once rotated fully
    out of view). Shell panes count in the total but never in worst/red/?."""
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
        + [f"{rc}{red} red{OFF}", f"{ac}{waiting} ?{OFF}"] + agent_type_census(panes)
    short = [f"{len(panes)}p"] + ([wc] if wc else []) \
        + [f"{rc}{red}r{OFF}", f"{ac}{waiting}?{OFF}"]
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


def window_grid(wins, width, max_rows, dashes=False, now=None, extra_slots=0):
    """Windows as ASCII columns: window name as header, its panes stacked beneath.
    Fills banks left-to-right; when the full set doesn't fit max_rows, ROTATES the
    visible page of banks every ~10s (stateless: derived from wall clock, so the 2s
    refresh loop rotates naturally and --once shows whichever page is current) instead
    of permanently hiding overflow. A SINGLE window with more panes than fit rotates its
    OWN pane list the same way (a 6-pane window in a 1-pane-tall slot previously looked
    like a dead 1-seat window with no hint 5 more existed). CRITICAL panes/windows (see
    is_critical_pane) are PINNED — never rotated out; a page containing one is shown
    steadily instead of cycling away from it on a timer.

    extra_slots > 0 puts this grid into the caller's WHOLE-VIEW cycle: the rotation
    wheel gains that many extra slots after the window pages, and when the wall clock
    lands on one, the function returns that extra slot's 0-based INDEX (an int, not a
    list) — 'not this block's turn' — so the caller renders the matching other view
    (plan limits, messages). A CRITICAL page pins the whole wheel: the extra slots are
    skipped until the pane is dealt with."""
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
    total_slots = len(pages) + extra_slots
    if critical_page_idx is not None:
        page_idx = critical_page_idx  # PIN: hold on the critical page, no time rotation
    elif total_slots <= 1:
        page_idx = 0
    else:
        slot = int((time.time() if now is None else now) // 10) % total_slots
        if slot >= len(pages):
            return slot - len(pages)  # an extra slot's turn — its index picks the view
        page_idx = slot
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


def snapshot_messages(snap):
    """The sensor's coordination-log tail ({total, tail:[...]}) off the snapshot — R24: the
    log itself is a raw source and team-monitor is its reader; teamview renders only what the
    snapshot carries. None when the snapshot predates the field or the sensor found no log."""
    m = (snap or {}).get("messages")
    return m if isinstance(m, dict) and isinstance(m.get("tail"), list) else None


def extra_view_names(cells, notes, console, snap):
    """The whole-view cycle's extra slots after the window pages, in wheel order. The
    messages slot exists only when the snapshot actually carries a message tail — an old
    sensor or a log-less run must not buy a 10s blank page."""
    names = ["limits"] if (cells or notes or console) else []
    msgs = snapshot_messages(snap)
    if msgs and msgs["tail"]:
        names.append("messages")
    return names


def messages_body(snap, width, max_lines, now=None):
    """The MESSAGES page body: the last coordination sends in log order (newest LAST, like
    the log itself), one ALIGNED row each — how long ago · sender→recipient · as much of
    the text as the row can hold (the age and route columns are padded to the block's own
    widest, so the text starts on one straight edge). Overflow drops the OLDEST rows with
    a count note, never the newest. A snapshot with no messages field renders a LOUD
    explanation, not an empty page (G-153's lesson)."""
    msgs = snapshot_messages(snap)
    if msgs is None:
        return [f"{YELLOW}no message data in snapshot — sensor predates the messages "
                f"field or found no coordination/messages.md{OFF}"[:width + 20]]
    if not msgs["tail"]:
        return [f"{DIM}message log is empty{OFF}"]
    t = time.time() if now is None else now
    rows = []
    for e in msgs["tail"]:
        age = (fmt_age(t - e["sent_epoch"]) if e.get("sent_epoch") else "") or "?"
        route = f"{BOLD}{e.get('from', '?')}{OFF} {DIM}→{OFF} {e.get('to', '?')}"
        rows.append((age, route, (e.get("text") or "").strip()))
    age_w = max(len(a) for a, _r, _x in rows)
    route_w = max(visible_len(r) for _a, r, _x in rows)
    lines = []
    for age, route, text in rows:
        room = max(12, width - age_w - route_w - 4)  # the text NEVER loses its whole column
        if len(text) > room:
            text = text[:room - 1] + f"{MARK}…{OFF}"
        lines.append(f"{DIM}{age:>{age_w}}{OFF}  {pad_to(route, route_w)}  {text}")
    if 0 < max_lines < len(lines):
        keep = max(1, max_lines - 1)  # the note takes a row only when there is a spare one
        dropped = len(lines) - keep
        note = f"{DIM}(+{dropped} older not shown){OFF}"
        lines = lines[-keep:]
        if max_lines > 1:
            lines.insert(0, note)
        else:
            lines[0] = clip_line(f"{note} {lines[0]}", width)
    return lines


def messages_hdr_count(snap):
    """' (last N of T)' for the MESSAGES header — '' when the counts are unavailable."""
    msgs = snapshot_messages(snap)
    if not msgs or not msgs["tail"]:
        return ""
    return f" {DIM}(last {len(msgs['tail'])} of {msgs.get('total') or '?'}){OFF}"


def fmt_tok(n):
    """Compact ~token count: 850, 46k, 1.2M."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{round(n / 1000)}k"
    return str(n)


def dispatch_cue(snap, avail):
    """The average dispatch payload — the ~tokens a freshly launched seat must read before
    working (shared boot files + its own seat.md/memory.md), computed by the sensor and
    rendered on the WINDOWS header (it describes the seats, not the plan bars). Degrades
    gracefully and to '' when the snapshot lacks the field — absence renders as nothing
    rather than a fake 0."""
    d = (snap or {}).get("dispatch_tokens") or {}
    avg = d.get("avg_tokens")
    if avg is None or avail <= 2:
        return ""
    # the VALUE renders bright (CYAN, like the in-use account labels) — a fully-DIM cue
    # proved invisible on a dark terminal ("I can't see the token counter", owner 2026-07-28)
    variants = (f"{DIM}dispatch{OFF} {CYAN}~{fmt_tok(avg)} tok{OFF} {DIM}avg/seat{OFF}",
                f"{DIM}disp{OFF} {CYAN}~{fmt_tok(avg)} tok{OFF}",
                f"{CYAN}disp~{fmt_tok(avg)}{OFF}")
    fit = shrink_to_fit(variants, avail - 3)
    return f" · {fit}" if fit else ""


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


def limits_body(cells, notes, console, width, max_lines, style="wide"):
    """The PLAN LIMITS page body for the whole-view cycle — bars + notes + console at the
    layout's own detail level ('wide' folds bar cells into columns when one-per-line is
    too tall; 'narrow' drops suffixes; 'tiny' is label+percent only, keeping the urgency
    color band), capped to max_lines with a (+N more) note instead of silent loss."""
    lines = []
    if style == "tiny":
        for c in cells:
            color = GREEN if c[2] < 60 else (YELLOW if c[2] < 85 else RED)
            lines.append(f"{c[0]}: {color}{c[2]:.0f}%{OFF}")
        toks = [re.sub(r"\s+", " ", n) for n in notes]
        if console:
            toks.append("no-API: " + " ".join(
                re.sub(r"\033\[[0-9;]*m", "", c).split(" ")[0] for c in console))
        if toks:
            lines.extend(flow(toks, width, max(1, max_lines - len(lines))))
    elif style == "narrow":
        label_w = max([c[1] for c in cells], default=8)
        bar_w = max(6, min(14, width - label_w - 8))
        lines = [render_bar_cell(c, label_w, bar_w, with_suffix=False) for c in cells]
        lines += [n[:width] for n in notes]
        lines += console_lines(console, width, max_lines=2)
    else:
        label_w = max([c[1] for c in cells], default=10)
        ncols, bar_w, cell_w = 1, 22, 0
        for ncols in (1, 2, 3, 4):
            bar_w = 22 if ncols == 1 else 14
            cell_w = label_w + bar_w + 8 + 15  # same suffix budget as render_strip
            if (math.ceil(len(cells) / ncols) <= max(1, max_lines - 1)
                    and ncols * (cell_w + 2) <= width):
                break
        grid_rows = math.ceil(len(cells) / ncols) if cells else 0
        for r in range(grid_rows):
            row_cells = [render_bar_cell(cells[r + grid_rows * c], label_w, bar_w)
                         for c in range(ncols) if r + grid_rows * c < len(cells)]
            while len(row_cells) > 1 and visible_len(
                    "  ".join(pad_to(s, cell_w) for s in row_cells)) > width:
                row_cells = row_cells[:-1]
            if len(row_cells) > 1:
                row = "  ".join(pad_to(s, cell_w) for s in row_cells)
            else:
                row = row_cells[0] if row_cells else ""
                if visible_len(row) > width:
                    row = shrink_to_fit(bar_cell_variants(cells[r], label_w, bar_w),
                                        width) or clip_line(row, width)
            lines.append(row)
        if notes:
            lines.append(fit_join(notes, " · ", width))
        lines.extend(console_lines(console, width))
    if max_lines > 0 and len(lines) > max_lines:
        dropped = len(lines) - max_lines
        lines = lines[:max_lines]
        lines[-1] = clip_line(lines[-1] + f" {DIM}(+{dropped} more){OFF}", width)
    return lines


def render_full(session, wins, nwin, npane, cells, notes, console, cache, cols, rows,
                cue=False, now=None, cycle=True, phase=None, snap=None):
    # ⚠ THE SNAPSHOT AGE RIDES THE BASE, and when the base no longer fits it is the SESSION LABEL
    # that gives way, never the age. Every other element of this header degrades to "" under
    # pressure; the age must not, because 'age is always on screen' is a criterion of this task —
    # a STALE warning that disappears exactly when the terminal is small is the silence it exists
    # to break. shrink_to_fit picks the widest form that fits, so the age's own short spelling is
    # the last thing to go and it never vanishes.
    age_full, age_short = age_variants(snapshot_age_s(snap, now))
    clock = datetime.now().strftime("%H:%M:%S")
    base = shrink_to_fit((
        f"{BOLD}teamview{OFF} · session {BOLD}{session}{OFF} · {nwin} windows / "
        f"{npane} panes · {clock} · {age_full}",
        f"{BOLD}teamview{OFF} · {BOLD}{session}{OFF} · {nwin}w / {npane}p · {clock} · {age_full}",
        f"{BOLD}{session}{OFF} · {nwin}w / {npane}p · {clock} · {age_short}",
        f"{BOLD}{session}{OFF} · {nwin}w/{npane}p · {age_short}",
        age_short,
    ), cols) or age_short
    head = base + package_cue(cue, cols - visible_len(base))
    head += sys_cue(cols - visible_len(head), snap)
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
    if cycle:
        # Whole-view cycle: below the constant header line, the body alternates between
        # the windows pages (as many as the grid needs) and ONE plan-limits page —
        # windows p1 … pN, limits, back to p1. The alarm rollup rides BOTH phase headers,
        # so no glance loses it (DESIGN-4).
        # phase pins ONE view (--view limits / --view panes): no alternation, the other
        # view is never rendered. phase=None keeps the timed cycle.
        # No marker legend on ANY frame — every row goes to data. The key moved OFF the
        # dashboard entirely, to `teamview interface-legend` (owner ruling 2026-07-28,
        # reversing the earlier decision that put a mini legend on the small layouts).
        body_budget = max(1, rows - len(out) - 3)
        extras = extra_view_names(cells, notes, console, snap)
        if phase in ("limits", "messages"):
            grid, which = None, phase
        else:
            grid = window_grid(wins, cols - 2, body_budget, dashes=True, now=now,
                               extra_slots=0 if phase == "panes" else len(extras))
            which = extras[grid] if isinstance(grid, int) else None
        if which == "messages":
            mhdr = f"{BOLD}MESSAGES{OFF}{messages_hdr_count(snap)}"
            out.append(mhdr + rollup_suffix(wins, cols - visible_len(mhdr)))
            out.extend("  " + l for l in messages_body(snap, cols - 2, body_budget, now))
            return out[:rows - 1]
        if which == "limits":
            lhdr = f"{BOLD}PLAN LIMITS{OFF}{age}"
            out.append(lhdr + rollup_suffix(wins, cols - visible_len(lhdr)))
            out.extend("  " + l for l in
                       limits_body(cells, notes, console, cols - 2, body_budget))
            return out[:rows - 1]
        else:
            whdr = f"{BOLD}WINDOWS{OFF} {DIM}(panes beneath){OFF}"
            whdr += dispatch_cue(snap, cols - visible_len(whdr))
            out.append(whdr + rollup_suffix(wins, cols - visible_len(whdr)))
            out.extend("  " + l for l in grid)
        return out[:rows - 1]
    out.append(f"{BOLD}PLAN LIMITS{OFF}{age}")
    label_w = max([c[1] for c in cells], default=10) + 1
    bar_w = max(16, min(40, cols - label_w - 30))
    for c in cells:
        out.append("  " + render_bar_cell(c, label_w, bar_w))
    for n in notes:
        out.append("  " + n)
    out.extend("  " + l for l in console_lines(console, cols - 2))
    out.append("")
    whdr = f"{BOLD}WINDOWS{OFF} {DIM}(panes beneath){OFF}"
    whdr += dispatch_cue(snap, cols - visible_len(whdr))
    out.append(whdr + rollup_suffix(wins, cols - visible_len(whdr)))
    grid_budget = rows - len(out) - 1
    out.extend("  " + l for l in window_grid(wins, cols - 2, grid_budget, dashes=True))
    if snapshot_messages(snap):
        out.append("")
        out.append(f"{BOLD}MESSAGES{OFF}{messages_hdr_count(snap)}")
        out.extend("  " + l for l in
                   messages_body(snap, cols - 2, max(1, rows - len(out) - 1), now))
    return out[:rows - 1]


_PREV_CPU_SAMPLE = {"v": None}  # (idle_ticks, total_ticks) of the previous frame


def cpu_usage_pct():
    """System CPU usage % since the PREVIOUS call — a /proc/stat busy/total tick delta,
    the same computation top makes between refreshes, so each frame's reading averages
    over the frame interval. None on the first call (no delta yet) and off-Linux."""
    try:
        vals = [int(x) for x in
                Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)  # idle + iowait
        total = sum(vals)
    except (OSError, ValueError, IndexError):
        return None
    prev, _PREV_CPU_SAMPLE["v"] = _PREV_CPU_SAMPLE["v"], (idle, total)
    if not prev or total <= prev[1]:
        return None
    dtotal = total - prev[1]
    return round(100.0 * (dtotal - (idle - prev[0])) / dtotal, 1)




def system_cell_variants(avail_mb, total_mb, load1, cores, cpu_pct=None):
    """Full -> short -> RAM-only text for the system-resource cell: RAM as used-% plus
    the GB still AVAILABLE to new work (MemAvailable — top's tiny 'free' column excludes
    reclaimable page cache and reads misleadingly low), CPU as usage % when a /proc/stat
    delta exists (load-vs-cores fallback on the first frame / off-Linux). Colored by
    PRESSURE — red when available RAM < ~500MB, cpu% >= 90, or load1 >= cores; yellow at
    the halfway warning band; else green — an operator AND watcher see resource pressure
    at a glance (this run hit an OOM cascade). A pure function of the 5 fields, so it's
    testable without touching the OS. [] when neither RAM nor CPU data is available."""
    ram_full = ram_short = cpu = None
    if avail_mb is not None:
        color = RED if avail_mb < 500 else (YELLOW if avail_mb < 1500 else GREEN)
        free_gb = (avail_mb * 10 // 1024) / 10  # one decimal, rounded DOWN (never overstate)
        if total_mb:
            used_pct = round(100.0 * (total_mb - avail_mb) / total_mb)
            ram_full = f"{color}RAM {used_pct}% ({free_gb}GB free){OFF}"
        else:
            ram_full = f"{color}RAM {free_gb}GB free{OFF}"
        ram_short = f"{color}{free_gb}GB free{OFF}"
    saturated = load1 is not None and load1 >= cores  # queueing pressure cpu% can't see
    if cpu_pct is not None:
        color = (RED if cpu_pct >= 90 or saturated
                 else (YELLOW if cpu_pct >= 70 else GREEN))
        cpu = f"{color}CPU {cpu_pct:.0f}%{OFF}"
    elif load1 is not None:
        color = RED if saturated else (YELLOW if load1 >= cores * 0.75 else GREEN)
        cpu = f"{color}CPU {load1:.1f}/{cores}{OFF}"
    variants = []
    for parts in ((ram_full, cpu), (ram_short, cpu), (ram_short,)):
        v = "  ".join(x for x in parts if x)
        if v and (not variants or variants[-1] != v):
            variants.append(v)
    return variants


def sys_cue(avail, snap=None):
    """The system-resource cell, shrunk to whatever room is available (same graceful
    degradation as package_cue) — "" when it doesn't fit or neither reading is available,
    never a mid-value clip. RAM/load/cores come from the snapshot's box{}; only the CPU% is
    read live (the ruled exempt lane — see the snapshot section header)."""
    if avail <= 2:
        return ""
    variants = system_cell_variants(*box_load(snap))
    fit = shrink_to_fit(variants, avail - 2) if variants else ""
    return f"  {fit}" if fit else ""


# ⚠ THE OLD "no --package" CUE IS RETIRED, NOT TOMBSTONED. It warned that thresholds and roster
# names were never loaded because --package was omitted. Under R24 that state CANNOT OCCUR: a
# package always resolves or main refuses at exit 2, and thresholds now come off the snapshot
# itself. A cue for an unreachable state is a lie a future reader would take as live.
#
# RED, not yellow, and the distinction is the whole point: the surviving cue is a DEFECT signal —
# the run asked for threshold checking and silently is not getting it (G-153).
NO_THRESHOLD_CUE_VARIANTS = (
    f"{RED}ctx thresholds NOT loaded — none checked{OFF}",
    f"{RED}no ctx thresholds loaded{OFF}",
    f"{RED}no-thr!{OFF}",
)

CUE_VARIANTS_BY_REASON = {"no-thresholds": NO_THRESHOLD_CUE_VARIANTS}


def package_cue(cue, avail):
    """The degraded-thresholds cue, shrunk to whatever room is actually available — never emitted
    at a length that would need clip_line's blind mid-word cut ('...roster~' was the reported
    bug); "" (no cue at all) only when even the shortest form doesn't fit.

    `cue` is falsy (no cue) or a reason key naming a degradation. UNLIKE the snapshot-age text
    this one MAY degrade to "" — it reports a policy gap, not the freshness of the data on
    screen."""
    variants = CUE_VARIANTS_BY_REASON.get(cue)
    if not variants or avail <= 2:
        return ""
    fit = shrink_to_fit(variants, avail - 2)
    return f"  {fit}" if fit else ""


def session_line(session, nwin, npane, cols=999, cue=False, snap=None, now=None):
    """cue: no seat in the snapshot declares a ctx-refresh threshold, so a bare ctxN%
    could read as 'confirmed under threshold' when it is really 'no threshold was ever checked'
    (an operator made a wrong renewal call on exactly this silent gap).

    ⚠ THE SNAPSHOT AGE IS PART OF THE BASE, NOT A CUE, IN BOTH THE FULL AND THE SHORT FORM.
    package_cue and sys_cue degrade to "" when they do not fit — that is correct for them and
    would be a defect here, because 'age is always on screen' is a criterion of this task and a
    STALE warning that vanishes at narrow widths is precisely the silence it exists to break."""
    age_full, age_short = age_variants(snapshot_age_s(snap, now))
    base = (f"{BOLD}{session}{OFF} · {nwin} windows · {npane} panes · "
            f"{datetime.now().strftime('%H:%M:%S')} · {age_full}")
    s = base + package_cue(cue, cols - visible_len(base))
    s += sys_cue(cols - visible_len(s), snap)
    if visible_len(s) <= cols:
        return s
    short_base = (f"{BOLD}{session[:max(4, cols - 22 - visible_len(age_short))]}{OFF} · "
                  f"{nwin}w · {npane}p · {age_short}")
    s2 = short_base + package_cue(cue, cols - visible_len(short_base))
    return s2 + sys_cue(cols - visible_len(s2), snap)


# The two table titles — one own line, bold+underlined, so each block's SCOPE is unmistakable
# and the session-stats line above is never mistaken for a table header.
LIMITS_HDR = f"{BOLD}{UL}PLAN LIMITS{OFF}"
WINDOWS_HDR = f"{BOLD}{UL}WINDOWS · PANES{OFF}"
MESSAGES_HDR = f"{BOLD}{UL}MESSAGES{OFF}"


def render_strip(session, wins, nwin, npane, cells, notes, console, cols, rows,
                 cue=False, now=None, cycle=True, phase=None, snap=None):
    if cycle:
        # Whole-view cycle (see render_full): the old side-by-side split becomes one
        # full-width view at a time — windows pages, then the limits page, repeating.
        # phase pins ONE view; see render_full.
        out = [session_line(session, nwin, npane, cols, cue, snap, now)]
        budget = max(1, rows - 2)  # session line + phase header (no legend — see render_full)
        extras = extra_view_names(cells, notes, console, snap)
        if phase in ("limits", "messages"):
            grid, which = None, phase
        else:
            grid = window_grid(wins, cols, budget, now=now,
                               extra_slots=0 if phase == "panes" else len(extras))
            which = extras[grid] if isinstance(grid, int) else None
        if which == "messages":
            mhdr = MESSAGES_HDR + messages_hdr_count(snap)
            out.append(mhdr + rollup_suffix(wins, cols - visible_len(mhdr)))
            out.extend(messages_body(snap, cols, budget, now))
            return out[:rows]
        if which == "limits":
            out.append(LIMITS_HDR + rollup_suffix(wins, cols - visible_len(LIMITS_HDR)))
            out.extend(limits_body(cells, notes, console, cols, budget))
            return out[:rows]
        else:
            hdr = WINDOWS_HDR + dispatch_cue(snap, cols - visible_len(WINDOWS_HDR))
            hdr += rollup_suffix(wins, cols - visible_len(hdr))
            out.append(hdr)
            out.extend(grid)
        return out[:rows]
    budget = max(2, rows - 2)  # rows 0-1 are the session line + the two-table header row
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
        left.append(fit_join(notes, " · ", max(0, lw - 1)))
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
    hdr_row += dispatch_cue(snap, cols - visible_len(hdr_row))
    hdr_row += rollup_suffix(wins, cols - visible_len(hdr_row))
    out = [session_line(session, nwin, npane, cols, cue, snap, now), hdr_row]
    for i in range(budget):
        lseg = left[i] if i < len(left) else ""
        rseg = right[i] if i < len(right) else ""
        if not lseg and not rseg:
            break
        out.append(f"{pad_to(lseg, lw)}{DIM}|{OFF} {rseg}")
    if snapshot_messages(snap):
        out.append(MESSAGES_HDR + messages_hdr_count(snap))
        out.extend(messages_body(snap, cols, max(1, rows - len(out) - 1), now))
    return out[:rows]


def cycle_compact(session, wins, nwin, npane, cells, notes, console, cols, rows,
                  cue, now, style, phase=None, snap=None):
    """The narrow/tiny whole-view cycle frame: constant session line, then either a
    windows page (compact_window_lines' turn) or the limits page. No legend on any frame
    — see render_full. phase pins ONE view instead of alternating; see render_full."""
    out = [session_line(session, nwin, npane, cols, cue, snap, now)]
    budget = max(1, rows - 3)  # session line + phase header + the rows-1 cap
    extras = extra_view_names(cells, notes, console, snap)
    if phase in ("limits", "messages"):
        grid, which = None, phase
    else:
        grid = compact_window_lines(wins, cols, budget, now=now,
                                    extra_slots=0 if phase == "panes" else len(extras))
        which = extras[grid] if isinstance(grid, int) else None
    if which == "messages":
        mhdr = (MESSAGES_HDR if style == "narrow" else f"{BOLD}{UL}MSGS{OFF}") \
            + messages_hdr_count(snap)
        out.append(mhdr + rollup_suffix(wins, cols - visible_len(mhdr)))
        out.extend(messages_body(snap, cols, budget + 1, now))
        return out[:rows - 1]
    if which == "limits":
        lhdr = LIMITS_HDR if style == "narrow" else f"{BOLD}{UL}LIMITS{OFF}"
        out.append(lhdr + rollup_suffix(wins, cols - visible_len(lhdr)))
        out.extend(limits_body(cells, notes, console, cols, budget + 1, style=style))
        return out[:rows - 1]
    else:
        whdr = WINDOWS_HDR if style == "narrow" else f"{BOLD}{UL}WINDOWS{OFF}"
        whdr += dispatch_cue(snap, cols - visible_len(whdr))
        out.append(whdr + rollup_suffix(wins, cols - visible_len(whdr)))
        out.extend(grid)
    return out[:rows - 1]


def render_narrow(session, wins, nwin, npane, cells, notes, console, cols, rows,
                  cue=False, now=None, cycle=True, phase=None, snap=None):
    if cycle:
        return cycle_compact(session, wins, nwin, npane, cells, notes, console, cols,
                             rows, cue, now, "narrow", phase, snap)
    out = [session_line(session, nwin, npane, cols, cue, snap, now), LIMITS_HDR]
    label_w = max([c[1] for c in cells], default=8)
    bar_w = max(6, min(14, cols - label_w - 8))
    for c in cells:
        out.append(render_bar_cell(c, label_w, bar_w, with_suffix=False))
    for n in notes:
        out.append(n[:cols])
    out.extend(console_lines(console, cols, max_lines=2))
    whdr = WINDOWS_HDR + dispatch_cue(snap, cols - visible_len(WINDOWS_HDR))
    out.append(whdr + rollup_suffix(wins, cols - visible_len(whdr)))
    out.extend(compact_window_lines(wins, cols, max(1, rows - len(out) - 1)))
    if snapshot_messages(snap):
        out.append(MESSAGES_HDR + messages_hdr_count(snap))
        out.extend(messages_body(snap, cols, max(1, rows - len(out) - 1), now))
    return out[:rows - 1]


def render_tiny(session, wins, nwin, npane, cells, notes, console, cols, rows,
                cue=False, now=None, cycle=True, phase=None, snap=None):
    """LIMITS: one label + percent PER LINE (never 2-up flowed) — at this width a flowed
    pair sits close enough that a label can misread as paired with its NEIGHBOR's percent
    (observed: 'claude:main 5h' read against a different window's value). One entry per
    line makes each label unambiguously own its own number."""
    if cycle:
        return cycle_compact(session, wins, nwin, npane, cells, notes, console, cols,
                             rows, cue, now, "tiny", phase, snap)
    out = [session_line(session, nwin, npane, cols, cue, snap, now), f"{BOLD}{UL}LIMITS{OFF}"]
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
    thdr += dispatch_cue(snap, cols - visible_len(thdr))
    out.append(thdr + rollup_suffix(wins, cols - visible_len(thdr)))
    out.extend(compact_window_lines(wins, cols, max(1, rows - len(out) - 1)))
    if snapshot_messages(snap):
        out.append(f"{BOLD}{UL}MSGS{OFF}" + messages_hdr_count(snap))
        out.extend(messages_body(snap, cols, max(1, rows - len(out) - 1), now))
    return out[:rows - 1]


def combined_fits(combined_lines, rows, cells=(), wins=()):
    """AUTO view: does the COMPLETE combined frame (limits block + every window and pane,
    what --no-rotate renders) actually fit the measured frame? The cycle exists ONLY to
    survive a frame too small to show everything at once — when everything fits, cycling
    hides half the dashboard for 10s at a time for no reason.

    TWO conditions, because height alone proved insufficient (verified live at 100x9: the
    frame was short enough, and the strip layout's column fold had silently dropped 5 of 8
    plan-limit bars — a --no-rotate-path defect that auto-selection would have promoted to
    the DEFAULT view, showing an operator a limits block missing most of its bars with no
    note). So: (1) it must be no taller than the frame, keeping the one spare row every
    renderer's own `rows - 1` cap reserves; (2) every bar label and every window name must
    be VISIBLY PRESENT in it. Failing either falls back to the cycle — the status quo, and
    the safe direction: rotation always says what it is hiding, silent dropping does not.

    BOTH SIDES of the presence test are SGR-STRIPPED. A cell label carries color (CYAN for
    the account in use, DIM for configured), so comparing a raw label against a stripped
    body never matched: condition (2) failed for EVERY live frame and auto-combined was
    dead on arrival at any size (reported live at 280x83, rendering windows-only). The
    critical-pane pin was NOT the cause — it only picks a page inside a CYCLING grid, and
    a combined frame renders every pane regardless, so a pin cannot suppress the limits
    block once this returns True."""
    if len(combined_lines) > max(1, rows - 1):
        return False
    strip = lambda s: re.sub(r"\033\[[0-9;]*m", "", s)  # noqa: E731
    body = strip("\n".join(combined_lines))
    return (all(strip(c[0]) in body for c in cells)
            and all(strip(w["name"]) in body for w in wins))


def render(args, package, now=None):
    """One frame from ONE re-read of the snapshot. The snapshot is re-read every frame — that is
    what makes the age advance and the STALE warning fire while teamview keeps running."""
    cols = args.width or int(subprocess.run(["tput", "cols"], capture_output=True,
                                            text=True).stdout or 200)
    rows = args.height or int(subprocess.run(["tput", "lines"], capture_output=True,
                                             text=True).stdout or 45)
    snap, err = load_snapshot(package)
    if err:
        # FAIL LOUD, never an empty frame: a dashboard that renders nothing reads as a quiet
        # room. The error is the frame (G-153's lesson as a contract).
        return [f"{RED}{BOLD}TEAMVIEW: NO SNAPSHOT{OFF}", f"{RED}{err}{OFF}"]
    session = snap.get("session") or "?"
    thresholds = snapshot_thresholds(snap)
    wins, nwin, npane = snapshot_tree(snap, now)
    if not wins:
        return [f"{RED}{BOLD}TEAMVIEW: SNAPSHOT HAS NO PANES{OFF}",
                f"{RED}{Path(package) / SNAPSHOT_NAME} captured "
                f"{fmt_secs(snapshot_age_s(snap, now) or 0)} ago and lists zero panes — "
                f"is the tmux session '{session}' still alive?{OFF}",
                f"{RED}session_alive: {snap.get('session_alive')!r}{OFF}"]
    cache = load_cache()
    cells, notes, console = usage_cells(cache, live=live_agent_accounts())
    layout = choose_layout(cols, rows)
    # G-153: a package WAS given and still yielded no threshold — say so, loudly. Absence has to be
    # audible here or it reads as health: every pane renders a plain ctxN% and an operator takes
    # green for "confirmed under threshold" when it means "never checked" (the exact wrong-renewal
    # call the no-package cue was added for). It fires equally when no seat happens to declare a
    # `ctx-refresh:` — deliberate, because that state is ALSO "no threshold is being checked", and
    # a cue that stays quiet whenever it cannot tell a stale path from an empty policy is the
    # fail-open this fixes.
    # R24: a package always resolves now (main refuses otherwise), so the surviving case is the
    # one that matters — a snapshot carrying ZERO ctx-refresh thresholds.
    cue = "no-thresholds" if not thresholds else False
    # --no-rotate / --view combined: LAYOUT is still chosen from the real terminal shape,
    # but the whole-view cycle is disabled (both blocks render in ONE combined frame) and
    # every internal row/line budget (and the final row cap) is lifted so every window and
    # every pane renders — a COMPLETE snapshot, taller than the terminal if it must be,
    # instead of cycling pages a single --once frame can never show you the rest of.
    def frame(render_rows, cyc, phase=None):
        kw = dict(cue=cue, now=now, cycle=cyc, phase=phase, snap=snap)
        if layout == "full":
            return render_full(session, wins, nwin, npane, cells, notes, console, cache,
                               cols, render_rows, **kw)
        if layout == "strip":
            return render_strip(session, wins, nwin, npane, cells, notes, console, cols,
                                render_rows, **kw)
        if layout == "narrow":
            return render_narrow(session, wins, nwin, npane, cells, notes, console, cols,
                                 render_rows, **kw)
        return render_tiny(session, wins, nwin, npane, cells, notes, console, cols,
                           render_rows, **kw)

    view = "combined" if getattr(args, "no_rotate", False) else getattr(args, "view", "auto")
    if view == "combined":
        out = frame(10 ** 6, False)
    elif view in ("limits", "panes", "messages"):
        # single-view modes: one view, pinned — no alternation with the others
        out = frame(rows, True, phase=view)
    else:
        # AUTO: cycle ONLY when the frame is too small to hold everything at once.
        # Derived from the measured frame every render, so a resize switches modes by
        # itself. The probe frame must not CONSUME the between-frames CPU delta — restore
        # the previous /proc/stat sample so the frame we actually print computes its own.
        prev_cpu = _PREV_CPU_SAMPLE["v"]
        combined = frame(10 ** 6, False)
        if combined_fits(combined, rows, cells, wins):
            out = combined
        else:
            _PREV_CPU_SAMPLE["v"] = prev_cpu
            out = frame(rows, True)
    return [clip_line(l, cols) for l in out]


# ---------- selftest ----------

def cmd_selftest():
    import ast
    import tempfile
    failures = []

    def check(name, cond):
        print(("ok  " if cond else "FAIL") + f"  {name}")
        if not cond:
            failures.append(name)

    strip_sgr = lambda s: re.sub(r"\033\[[0-9;]*m", "", s)  # noqa: E731

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
    accs = [{"provider": "claude", "name": "main"}, {"provider": "claude", "name": "tecer",
                                                     "in_use": True},
            {"provider": "codex", "name": "main"}]
    kept = current_claude_only(accs)
    lbl, _lv = account_label([a for a in kept if a["provider"] == "claude"][0],
                             sum(1 for a in kept if a["provider"] == "claude") > 1)
    check("claude accounts: only the in-use one, labelled bare 'claude'",
          [(a["provider"], a["name"]) for a in kept] == [("claude", "tecer"), ("codex", "main")]
          and re.sub(r"\033\[[0-9;]*m", "", lbl) == "claude")
    check("claude accounts: none in use -> main stands in",
          [a["name"] for a in current_claude_only([dict(a, in_use=False) for a in accs])
           if a["provider"] == "claude"] == ["main"])
    cw = codex_windows_from_rl({"primary": {"used_percent": 3.0, "window_minutes": 10080,
                                            "resets_at": 5}, "secondary": None})
    check("codex windows: 10080min -> 7d", cw == [{"label": "7d", "pct": 3.0, "resets_at": 5}])
    # R24: `busy` and `awaiting` no longer come from teamview sampling tmux — they are read off
    # the snapshot. `awaiting` maps EXACTLY (team_monitor.prompt_pending, same prompt patterns,
    # computed at the sensor). `busy` DOES NOT: it used to mean "visible content changed across
    # two captures 0.6s apart" and now means "the harness wrote to its transcript within
    # RECENT_ACTIVITY_S of the capture" — a coarser signal from a different instrument. It is
    # RELABELLED in the legend rather than silently reused, which is what these two checks pin.
    bw, _n, _p = snapshot_tree({"seats": [
        {"seat": "fresh", "window": "1", "last_activity_age_s": 3.0},
        {"seat": "idle", "window": "1", "last_activity_age_s": RECENT_ACTIVITY_S + 1},
        {"seat": "never", "window": "1", "last_activity_age_s": None},
        {"seat": "stuck", "window": "1", "last_activity_age_s": 1.0, "prompt_pending": True}]})
    by_name = {q["name"]: q for q in bw[0]["panes"]}
    check("snapshot_tree: `+` working marker = recent transcript activity, not a tmux diff",
          by_name["fresh"]["busy"] and not by_name["idle"]["busy"]
          and not by_name["never"]["busy"])
    check("snapshot_tree: awaiting comes from the snapshot's prompt_pending, nothing else",
          by_name["stuck"]["awaiting"] and not by_name["fresh"]["awaiting"])

    # G-17: IN USE is derived from live processes, never from "a credential exists".
    # pids are deliberately nonexistent: /proc read fails -> the documented 'main' fallback
    fake_procs = [("9990001", "claude --model fable --effort high do a thing"),
                  ("9990002", "opencode run -m deepseek/deepseek-v4-pro do a thing"),
                  ("9990003", "-bash"), ("9990004", "python3 /home/x/teamview --once"),
                  ("9990005", "opencode run do a thing")]  # no --model: provider unknowable
    live = live_agent_accounts(procs=fake_procs)
    check("live accounts: claude (default config dir) + opencode provider prefix only (G-17)",
          live == {("claude", "main"), ("deepseek", "main")})
    check("live accounts: no live process -> nothing in use, whatever credentials exist",
          live_agent_accounts(procs=[("1", "-bash"), ("2", "sshd: henri")]) == set())
    check("live accounts: codex/kimi processes map to their provider",
          live_agent_accounts(procs=[("1", "codex --search"), ("2", "kimi")])
          == {("codex", "main"), ("kimi", "main")})
    check("opencode provider aliases: store key and identity spelling both resolve",
          (opencode_account_of("opencode run -m zai-coding-plan/glm-4.6"),
           opencode_account_of("opencode -m moonshot/kimi-k2"),
           opencode_account_of("opencode run -m deepseek/deepseek-v4"),
           opencode_account_of("opencode run"))
          == (("zai", "main"), ("kimi", "main"), ("deepseek", "main"), None))
    check("account_in_use: live wins; explicit config flag overrides in both directions",
          account_in_use({"provider": "claude", "name": "main"}, live)
          and not account_in_use({"provider": "claude", "name": "tecer"}, live)
          and not account_in_use({"provider": "zai", "name": "main"}, live)
          and account_in_use({"provider": "zai", "name": "main", "in_use": True,
                              "_in_use_explicit": True}, live)
          and not account_in_use({"provider": "claude", "name": "main", "in_use": False,
                                  "in_use_explicit": True}, live))

    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        (home / ".claude").mkdir()
        (home / ".codex" / "sessions").mkdir(parents=True)
        (home / ".kimi" / "credentials").mkdir(parents=True)
        oc = home / "auth.json"
        oc.write_text(json.dumps({"deepseek": {"key": "k1"}, "zai-coding-plan": {"key": "k2"}}))
        (home / ".claude-work").mkdir()
        acc = load_accounts(home / "nonexistent.json", home=home, opencode_path=oc,
                            live={("claude", "main"), ("zai", "main")})
        provs = sorted(a["provider"] for a in acc)
        check("discovery: claude+codex+kimi+opencode providers found",
              provs == ["claude", "claude", "codex", "deepseek", "kimi", "zai"])
        extra = next((a for a in acc if a["provider"] == "claude" and a["name"] == "work"), None)
        check("discovery: extra ~/.claude-<tag> account dir found with tagged statusline path",
              extra is not None and extra["source"]["path"].endswith("plan-usage-work.json"))
        # G-17 regression: a discovered credential is CONFIGURED, not in use. Only the
        # accounts a live process spends light up — claude:work and codex/deepseek/kimi
        # all have stores here and none is running.
        by_key = {(a["provider"], a["name"]): a["in_use"] for a in acc}
        check("discovery: only accounts with a LIVE process are in use (G-17)",
              by_key[("claude", "main")] and by_key[("zai", "main")]
              and not any(v for k, v in by_key.items()
                          if k not in {("claude", "main"), ("zai", "main")}))
        cfg = home / "teamview.json"
        cfg.write_text(json.dumps({"accounts": [
            {"provider": "zai", "name": "main", "source": {"type": "opencode"}},
            {"provider": "zai", "name": "alt", "source": {"type": "env", "var": "X_ALT"}}]}))
        acc = load_accounts(cfg, home=home, opencode_path=oc, live={("zai", "main")})
        check("config: multi-account per provider; the idle sibling is NOT in use",
              len(acc) == 2 and acc[0]["in_use"] and not acc[1]["in_use"])
        key = resolve_key({"provider": "zai", "source": {"type": "opencode"}}, opencode_path=oc)
        check("key resolution: opencode store_key mapping (zai -> zai-coding-plan)", key == "k2")

    check("reference docs live behind their flags, off the -h path",
          "api/oauth/usage" in DOC_PROVIDERS and '"accounts"' in DOC_CONFIG
          and "opencode | env | file" in DOC_CONFIG and "api.z.ai" in DOC_PROVIDERS
          and all(s not in __doc__ for s in ("api.z.ai", '"accounts"')))
    check("legend: every marker discoverable from -h (fresh-eyes gap fix)",
          all(s in __doc__ for s in ("text cut", "active window", "pane match uncertain",
                                     "last activity", "account in use", "awaiting approval",
                                     "ctx-refresh threshold", "shell", "empty-title")))
    narrow_legend = [re.sub(r"\033\[[0-9;]*m", "", l) for l in legend_lines(80)]
    check("legend_lines: word-wraps at a narrow width instead of hard-clipping mid-word "
          "(the '...ctx~ = pane ma~' bug — every line fits, none end in a clip_line '~')",
          all(len(l) <= 80 for l in narrow_legend)
          and all(clip_line(l, 80) == l for l in narrow_legend)
          and "~ uncertain" in " ".join(narrow_legend))
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
    # R24 discovery: package-rooted, never tmux-rooted.
    with tempfile.TemporaryDirectory() as td:
        run = Path(td).resolve() / "goal" / "runs" / "run-9"
        (run / "seats" / "s1").mkdir(parents=True)
        (run / SNAPSHOT_NAME).write_text('{"captured_at": 1, "seats": []}', encoding="utf-8")
        check("find_package: walks UP from a seat folder to the run folder holding state.json",
              find_package(run / "seats" / "s1") == run and find_package(run) == run)
        check("find_package: None when no ancestor carries a snapshot (never a silent guess)",
              find_package(Path(td).resolve()) is None)
    # Regression (op-ux-1, dispatch #127-B), R24 form: the surviving degradation is a snapshot
    # carrying zero ctx-refresh thresholds. A bare frame showed plain green ctxN% with no cue that
    # nothing was being checked — a tester made a WRONG renewal call reading "green" as "confirmed
    # under threshold" when it really meant "never checked". The header cue closes that gap, and
    # must survive the narrow-fallback branch of session_line, not just the wide one.
    check("session_line: the zero-thresholds cue is shown ONLY when there is a degradation, and "
          "survives the narrow fallback",
          "ctx thresholds NOT loaded" in strip_sgr(session_line("s", 1, 1, 999, "no-thresholds"))
          and "ctx thresholds" not in strip_sgr(session_line("s", 1, 1, 999, False))
          and "no-thr!" in strip_sgr(session_line("s", 1, 1, 40, "no-thresholds")))
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
    pc = re.sub(r"\033\[[0-9;]*m", "", pane_cell(P("leader", busy=True)))
    check("pane_cell: seat+ harness:model ctxN% age", pc == "leader+ claude:opus-4-8 46% 2m")
    check("pane_cell/pane_compact: awaiting-approval renders RED name? (overrides busy '+')",
          RED + "stuck?" + OFF in pane_cell(P("stuck", busy=True, awaiting=True))
          and RED + "stuck?" + OFF in pane_compact(P("stuck", awaiting=True)))
    check("ctx_str: past-threshold renders RED ctxN%! regardless of the normal color band",
          re.sub(r"\033\[[0-9;]*m", "", ctx_str(30, over=True)) == "30%!"
          and ctx_str(30, over=True).startswith(RED)
          and re.sub(r"\033\[[0-9;]*m", "", ctx_str(30, over=False)) == "30%")
    check("pane_cell: ctx_over renders the past-threshold ctxN%! marker",
          "42%!" in re.sub(r"\033\[[0-9;]*m", "", pane_cell(P("seat", ctx=42.0, ctx_over=True))))
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
          all("42%!" in v for v in pcv[:-1]) and pcv[-1] == pane_name(crit_p))
    check("pane_cell_fit: degrades to a shorter complete variant instead of mid-value "
          "clipping — ctx% survives at a width that still fits 'name ctx42%!'",
          "42%!" in pane_cell_fit(crit_p, 20) and visible_len(pane_cell_fit(crit_p, 20)) <= 20)
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
        calm_wins_w = [{"idx": str(i), "name": f"win{i}", "active": i == 0,
                        "panes": [P(f"seat{i}a"), P(f"seat{i}b", ctx=42.0)]}
                       for i in range(4)]
        for layout_fn, h in ((render_strip, 8), (render_narrow, 30), (render_tiny, 12)):
            for fixture, nv in ((many_wins, 0), (calm_wins_w, 10)):
                out = layout_fn("improve-teamview", fixture, 4, 8, many_cells,
                                ["deepseek $8.63 left"], [], w, h, now=nv)
                plain = [re.sub(r"\033\[[0-9;]*m", "", l) for l in out]
                check(f"{layout_fn.__name__} at {w}w now={nv}: no line exceeds the "
                      "requested width on either cycle phase (no cue/footer/value "
                      "overflow reaching the outer blind clip)",
                      all(len(l) <= w for l in plain))
    # G-153's STRUCTURAL CURE. The defect was a SECOND path: thresholds were re-read from seat
    # descriptors on a hardcoded layout while the ctx% they gate came from the sensor, so the two
    # could drift — and did, silently, on every post-restructure package. Both now come off the
    # SAME snapshot record, so there is no second path left to drift. The descriptor reader and
    # its layout table are DELETED, not merely bypassed: a reader kept "just in case" is a second
    # path that a future change re-wires.
    thr_snap = {"seats": [
        {"seat": "engineer-2", "ctx_refresh": 50}, {"seat": "no-thr", "ctx_refresh": None},
        {"seat": "", "ctx_refresh": 55},                 # never checked in -> not a threshold
        {"seat": "bad", "ctx_refresh": "50"}]}           # wrong type -> refused, not coerced
    check("snapshot_thresholds: thresholds come off the SAME record as the ctx% they gate — "
          "absent/unnamed/mistyped entries carry NO threshold rather than a guessed one",
          snapshot_thresholds(thr_snap) == {"engineer-2": 50}
          and snapshot_thresholds({}) == {} and snapshot_thresholds(None) == {})
    check("G-153 cure: a seat's ctx_over marker is computed from that seat's OWN snapshot "
          "ctx_refresh, so a threshold can no longer be read from a stale second path",
          [q["ctx_over"] for q in snapshot_tree({"seats": [
              {"seat": "over", "window": "1", "ctx_pct": 52.0, "ctx_refresh": 50},
              {"seat": "under", "window": "1", "ctx_pct": 41.0, "ctx_refresh": 50},
              {"seat": "nothr", "window": "1", "ctx_pct": 99.0}]})[0][0]["panes"]]
          == [True, False, False])
    # The other half of G-153, and the half that makes the first OBSERVABLE: absence must be LOUD.
    # A snapshot that carries zero thresholds renders every pane's plain green ctxN%, which an
    # operator reads as "confirmed under threshold" when it means "never checked".
    plain_cue = lambda c, w=999: re.sub(r"\033\[[0-9;]*m", "", package_cue(c, w))
    check("G-153: zero ctx-refresh thresholds raises a RED cue, and never renders silent",
          "ctx thresholds NOT loaded" in plain_cue("no-thresholds")
          and plain_cue(False) == ""
          and "no-thr!" in plain_cue("no-thresholds", 12))   # survives the narrowest fold too
    check("the retired no-package cue is GONE, not merely unused — an unknown reason key is "
          "silent rather than falling back to stale wording",
          plain_cue(True) == "" and plain_cue("some-future-reason") == "")
    check("pane_cell: shell pane -> dim name + explicit 'shell' tag; no-info pane -> harness only",
          re.sub(r"\033\[[0-9;]*m", "", pane_cell(P("gone", shell=True))) == "gone shell"
          and re.sub(r"\033\[[0-9;]*m", "", pane_cell(
              P("ov", harness="python3", model="", ctx=None, age=""))) == "ov python3")
    check("pane_compact: parenthesized agent info",
          re.sub(r"\033\[[0-9;]*m", "", pane_compact(P("leader")))
          == "leader(claude:opus-4-8 46% 2m)")
    check("ctx color bands: green<60, yellow<85, red",
          GREEN in ctx_str(45) and YELLOW in ctx_str(70) and RED in ctx_str(90))
    check("uncertain pane match renders ~N%",
          "~46%" in re.sub(r"\033\[[0-9;]*m", "", pane_cell(P("m", approx=True))))
    wins = [{"idx": "0", "name": "control", "active": True,
             "panes": [P("leader", busy=True),
                       P("watcher", harness="opencode", model="deepseek-v4-pro", ctx=91.0,
                         age="5m")]},
            {"idx": "1", "name": "cli", "active": False, "panes": [P("cli", shell=True)]}]
    calm_wins = [{"idx": "0", "name": "control", "active": True,
                  "panes": [P("leader", busy=True),
                            P("watcher", harness="opencode", model="deepseek-v4-pro",
                              ctx=51.0, age="5m")]},
                 {"idx": "1", "name": "cli", "active": False,
                  "panes": [P("cli", shell=True)]}]
    for layout_fn, dims in ((render_strip, (240, 8)), (render_narrow, (56, 40)),
                            (render_tiny, (58, 12)), ):
        outw = layout_fn("sess", wins, 2, 3, cells, notes, console, *dims, now=0)
        outl = layout_fn("sess", calm_wins, 2, 3, cells, notes, console, *dims, now=10)
        jw = re.sub(r"\033\[[0-9;]*m", "", "\n".join(outw))
        jl = re.sub(r"\033\[[0-9;]*m", "", "\n".join(outl))
        check(f"{layout_fn.__name__}: fits height on both phases; windows phase carries "
              "seats + agent info, limits phase carries provider info",
              len(outw) <= dims[1] and len(outl) <= dims[1] and "leader" in jw
              and "claude" in jw and "46%" in jw and "9.26" in jl)
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
        "sess", calm_wins, 2, 3, [("claude:main 5h", 14, 45.0, "renews 18:39")], [], [],
        60, 12, now=10)]
    check("render_tiny: a known plan-usage value (45%) renders EXACTLY at 60x12, one "
          "label+percent per line (no neighbor-pair bleed)",
          "claude:main 5h: 45%" in tiny_out
          and not any(l.startswith("claude:main 5h:") and "45%" not in l for l in tiny_out))
    out = render_full("sess", wins, 2, 3, cells, notes, console, fake_cache, 160, 40,
                      now=0)
    plain = [re.sub(r"\033\[[0-9;]*m", "", l) for l in out]
    hdr = next((i for i, l in enumerate(plain) if "control" in l), None)
    check("render_full windows phase: grid — starred active window, panes with agent "
          "info beneath, no limits block sharing the frame",
          hdr is not None
          and any("leader+ claude:opus-4-8 46% 2m" in l for l in plain[hdr:])
          and any("*control" in l for l in plain)
          and not any("PLAN LIMITS" in l for l in plain)
          and not any("legend:" in l for l in plain))
    lim_full = [re.sub(r"\033\[[0-9;]*m", "", l) for l in render_full(
        "sess", calm_wins, 2, 3, cells, notes, console, fake_cache, 160, 40, now=10)]
    check("render_full limits phase: the next cycle slot renders the PLAN LIMITS page — "
          "windows grid absent, alarm rollup still on the phase header",
          any("PLAN LIMITS" in l for l in lim_full)
          and not any("control" in l for l in lim_full)
          and any("worst" in l for l in lim_full))
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
    # Whole-view cycle: with extra_slots=1 the rotation wheel gains a limits slot AFTER
    # the window pages — windows p1..pN, then None (the caller's limits turn), then back.
    check("whole-view cycle: window_grid with extra_slots=1 yields every window page, "
          "then the extra slot's index on its turn, then repeats",
          isinstance(window_grid(rot_wins, 40, 4, now=0, extra_slots=1), list)
          and isinstance(window_grid(rot_wins, 40, 4, now=20, extra_slots=1), list)
          and window_grid(rot_wins, 40, 4, now=30, extra_slots=1) == 0
          and plain(window_grid(rot_wins, 40, 4, now=40, extra_slots=1))
          == plain(window_grid(rot_wins, 40, 4, now=0, extra_slots=1)))
    check("whole-view cycle: compact_window_lines honors the same extra slot",
          isinstance(compact_window_lines(rot_wins, 40, 1, now=0, extra_slots=1), list)
          and compact_window_lines(rot_wins, 40, 1, now=30, extra_slots=1) == 0)
    check("whole-view cycle: even a single fitting windows page alternates with the "
          "extra slot",
          isinstance(window_grid(fit_wins, 80, 10, now=0, extra_slots=1), list)
          and window_grid(fit_wins, 80, 10, now=10, extra_slots=1) == 0)
    check("whole-view cycle: TWO extra slots take their turns IN ORDER after the window "
          "pages (limits then messages), 0 then 1, then the wheel repeats",
          window_grid(fit_wins, 80, 10, now=10, extra_slots=2) == 0
          and window_grid(fit_wins, 80, 10, now=20, extra_slots=2) == 1
          and isinstance(window_grid(fit_wins, 80, 10, now=30, extra_slots=2), list)
          and compact_window_lines(fit_wins, 80, 10, now=10, extra_slots=2) == 0
          and compact_window_lines(fit_wins, 80, 10, now=20, extra_slots=2) == 1)
    s0 = render_strip("sess", fit_wins, 1, 1, cells, notes, console, 220, 10, now=0)
    s1 = render_strip("sess", fit_wins, 1, 1, cells, notes, console, 220, 10, now=10)
    s2 = render_strip("sess", fit_wins, 1, 1, cells, notes, console, 220, 10, now=20)
    p0, p1 = plain(s0), plain(s1)
    check("whole-view cycle: strip alternates a full-width WINDOWS page and a full-width "
          "PLAN LIMITS page, deterministically repeating",
          any("WINDOWS" in l for l in p0) and not any("PLAN LIMITS" in l for l in p0)
          and any("PLAN LIMITS" in l for l in p1)
          and not any("WINDOWS · PANES" in l for l in p1)
          and plain(s2)[1:] == p0[1:])
    check("whole-view cycle: the first line stays constant across both phases — the "
          "cycle phase is no input to it (only the clock and the live sys cue move)",
          p0[0].startswith("sess · 1 windows · 1 panes")
          and p1[0].startswith("sess · 1 windows · 1 panes"))
    crit_cycle = [{"idx": "0", "name": "w", "active": True,
                   "panes": [P("stuck", awaiting=True)]}]
    pinned_frames = [plain(render_strip("sess", crit_cycle, 1, 1, cells, notes, console,
                                        220, 10, now=n)) for n in (0, 10, 20)]
    check("whole-view cycle: a critical pane PINS the cycle on its windows page — the "
          "limits page waits, no frame ever hides the critical pane",
          all(any("stuck" in l for l in f) for f in pinned_frames)
          and not any(any("PLAN LIMITS" in l for l in f) for f in pinned_frames))
    combined = plain(render_strip("sess", fit_wins, 1, 1, cells, notes, console,
                                  220, 10 ** 6, cycle=False))
    check("--no-rotate: cycle disabled -> ONE combined frame carries PLAN LIMITS and "
          "the windows block together",
          any("PLAN LIMITS" in l for l in combined)
          and any("WINDOWS" in l for l in combined))

    # Owner request 2026-07-28: (a) a MESSAGES page joins the whole-view cycle — the
    # coordination log's last sends (how long ago · sender→recipient · first 70 chars),
    # rendered R24-style off the snapshot's `messages` field, never off the log itself;
    # (b) the WINDOWS header carries the sensor's average dispatch payload
    # (`dispatch_tokens.avg_tokens` — what every seat must read regardless of its prompt
    # or agent type).
    msg_snap = {"captured_at": 1000.0,
                "messages": {"total": 42, "tail": [
                    {"n": 41, "from": "leader", "to": "engineer", "type": "note",
                     "sent": "2026-07-28 10:00", "sent_epoch": 400.0, "text": "A" * 100},
                    {"n": 42, "from": "chief-of-staff", "to": "leader", "type": "verdict",
                     "sent": "2026-07-28 10:05", "sent_epoch": 700.0, "text": "short"}]},
                "dispatch_tokens": {"avg_tokens": 46200, "shared_tokens": 9000, "seats": 4}}
    mb = plain(messages_body(msg_snap, 200, 10, now=1000.0))
    check("messages_body: one ALIGNED row per send — age · sender → recipient · text, "
          "log order (newest last), text on one straight edge",
          len(mb) == 2 and "leader → engineer" in mb[0]
          and "chief-of-staff → leader" in mb[1]
          and mb[1].strip().startswith("5m") and "short" in mb[1]
          and mb[0].index("A" * 5) == mb[1].index("short"))
    check("messages_body: the text fills the row's remaining width (not a fixed 70) and "
          "cuts with the … marker only when the row runs out",
          "A" * 100 in mb[0]
          and (lambda n: "A" * 49 + "…" in n[0] and "A" * 50 not in n[0])(
              plain(messages_body(msg_snap, 80, 10, now=1000.0))))
    check("messages_body: overflow drops the OLDEST rows with a count note, never the "
          "newest — down to a 1-row budget, where the note shares the newest row's line",
          (lambda o: len(o) == 2 and "+3 older not shown" in o[0] and "short" in o[1])(
              plain(messages_body(dict(msg_snap, messages={"total": 42, "tail":
                    msg_snap["messages"]["tail"] * 2}), 200, 2, now=1000.0)))
          and (lambda o: len(o) == 1 and "+1 older" in o[0] and "short" in o[0])(
              plain(messages_body(msg_snap, 200, 1, now=1000.0))))
    check("messages_body: a snapshot without the field renders a LOUD explanation, "
          "not an empty page",
          any("no message data" in l for l in plain(messages_body({}, 200, 5))))
    m0, m1, m2, m3 = (plain(render_strip("sess", fit_wins, 1, 1, cells, notes, console,
                                         220, 10, now=n, snap=msg_snap))
                      for n in (0, 10, 20, 30))
    check("whole-view cycle: with a message tail in the snapshot the wheel runs windows "
          "-> PLAN LIMITS -> MESSAGES -> back to windows",
          any("WINDOWS" in l for l in m0) and any("PLAN LIMITS" in l for l in m1)
          and any("MESSAGES (last 2 of 42)" in l for l in m2)
          and any("leader → engineer" in l for l in m2)
          and m3[1:] == m0[1:])
    check("whole-view cycle: NO messages slot when the snapshot carries no tail — an old "
          "sensor must not buy a blank 10s page",
          not any(any("MESSAGES" in l for l in
                      plain(render_strip("sess", fit_wins, 1, 1, cells, notes, console,
                                         220, 10, now=n)))
                  for n in (0, 10, 20, 30)))
    check("--view messages: pinned — every tick shows the messages page, never the others",
          all(any("MESSAGES" in l for l in f) and not any("WINDOWS" in l for l in f)
              and not any("PLAN LIMITS" in l for l in f)
              for f in (plain(render_strip("sess", fit_wins, 1, 1, cells, notes, console,
                                           220, 10, now=n, phase="messages",
                                           snap=msg_snap)) for n in (0, 10, 20))))
    combined_m = plain(render_strip("sess", fit_wins, 1, 1, cells, notes, console,
                                    220, 10 ** 6, cycle=False, snap=msg_snap))
    check("--no-rotate: the combined frame carries the MESSAGES block too",
          any("MESSAGES" in l for l in combined_m)
          and any("chief-of-staff → leader" in l for l in combined_m))
    check("dispatch tokens: the WINDOWS header carries the snapshot's average dispatch "
          "payload, and its absence renders as NOTHING rather than a fake 0",
          any("dispatch ~46k tok avg/seat" in l for l in m0)
          and not any("disp" in l for l in
                      plain(render_strip("sess", fit_wins, 1, 1, cells, notes, console,
                                         220, 10, now=0))))
    check("dispatch cue: degrades to shorter forms at narrow room, never a mid-value clip",
          dispatch_cue(msg_snap, 14).endswith(f"disp~46k{OFF}")
          and dispatch_cue(msg_snap, 2) == "")
    # Regression (live crash 2026-07-24): a real full-screen frame can leave grid_budget at
    # 0 or negative once the provider bars eat the height (rows - len(out) - 4), and rotation
    # with an over-budget page produced an empty `lines` list that lines[-1] then indexed
    # into -> IndexError, crashing every wave's live teamview mid-run. Must never raise for
    # ANY max_rows/max_lines, including 0 and negative.
    for budget in (0, -1, -5):
        try:
            window_grid(rot_wins, 1, budget)
            compact_window_lines(rot_wins, 40, budget)
            window_grid(rot_wins, 1, budget, extra_slots=1)
            compact_window_lines(rot_wins, 40, budget, extra_slots=1)
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

    # Owner item A, REVERSED 2026-07-28: the marker legend no longer renders on ANY frame,
    # at ANY size, on EITHER phase — every dashboard row goes to data, and the key lives
    # only behind `teamview interface-legend`. The old check pinned "legend on the windows
    # phase, absent on the limits phase"; this one pins absence everywhere, so the legend
    # cannot creep back onto a layout unnoticed. 'approval' and 'ctx usage' are legend-only
    # strings — the alarm rollup says '0 ?' and a pane cell says a bare 'N%'.
    lf_win = plain(render_full("sess", wins, 2, 3, cells, notes, console, fake_cache,
                               160, 40, now=0))
    lf_lim = plain(render_full("sess", calm_wins, 2, 3, cells, notes, console, fake_cache,
                               160, 40, now=10))
    check("itemA(rev): render_full — NO marker legend on either phase, and the PLAN LIMITS "
          "phase still renders its bars",
          any("PLAN LIMITS" in l for l in lf_lim)
          and not any("approval" in l for l in lf_win + lf_lim)
          and not any("ctx usage" in l for l in lf_win + lf_lim))
    for layout_fn, dims in ((render_strip, (240, 8)), (render_narrow, (56, 40)),
                            (render_tiny, (58, 12))):
        mw = plain(layout_fn("sess", wins, 2, 3, cells, notes, console, *dims, now=0))
        ml = plain(layout_fn("sess", calm_wins, 2, 3, cells, notes, console, *dims,
                             now=10))
        check(f"itemA(rev): {layout_fn.__name__} — NO legend on either phase; the limits "
              "bars keep their own notes and the frame still fits its height",
              any("LIMITS" in l for l in ml)
              and not any("approval" in l for l in mw + ml)
              and len(ml) <= dims[1] and len(mw) <= dims[1])

    # Owner item B: the ~10s cycle exists only to survive a frame too small for everything.
    # A frame big enough gets the COMBINED view statically (auto), decided from the
    # MEASURED size every render — the same combined frame --no-rotate forces.
    comb_lines = render_strip("sess", fit_wins, 1, 1, cells, notes, console,
                              220, 10 ** 6, cycle=False)
    check("itemB: combined_fits — True when the frame has room for every combined line "
          "(plus the one spare row every renderer reserves), False when it does not",
          combined_fits(comb_lines, len(comb_lines) + 1) is True
          and combined_fits(comb_lines, len(comb_lines)) is False
          and combined_fits(comb_lines, 4) is False
          and combined_fits([], 1) is True)
    # Height alone is NOT enough (verified live at 100x9): a short-enough combined frame
    # can still have dropped bars in the strip layout's column fold. Auto must refuse a
    # frame that is missing content and fall back to the cycle, which at least SAYS what
    # it is hiding.
    # The exact live shape (100 cols, the box's real 8 bars): the strip fold drops 5 of
    # them with no note, in a frame only 6 lines tall.
    # Labels are PRODUCTION-SHAPED: colorized exactly as usage_cells emits them (CYAN in
    # use / DIM configured). A plain-label fixture here is what let the SGR defect below
    # ship — it was width-realistic but not color-realistic, so it could not fail.
    live_cells = [(f"{CYAN if i < 3 else DIM}{l.split(' ')[0]}{OFF} "
                   + l.split(" ", 1)[1], len(l), 40.0, "renews Sat 03:00")
                  for i, l in enumerate(
                      ("claude:main 5h", "claude:main 7d", "claude:main 7d fable",
                       "claude:tecer 5h", "claude:tecer 7d", "codex 7d", "zai 5h",
                       "zai 7d"))]
    lossy = render_strip("sess", fit_wins, 1, 1, live_cells, [], [], 100, 10 ** 6,
                         cycle=False)
    intact = render_strip("sess", fit_wins, 1, 1, live_cells, [], [], 140, 10 ** 6,
                          cycle=False)
    check("itemB: combined_fits REFUSES a short-enough combined frame that silently "
          "dropped bars — every cell label and window name must be VISIBLY present "
          "(live 100x9: 5 of 8 bars gone from a 6-line frame)",
          not all(c[0] in "\n".join(plain(lossy)) for c in live_cells)
          and combined_fits(lossy, 40, live_cells, fit_wins) is False
          and combined_fits(lossy, 40) is True  # height-only would have ACCEPTED it
          and combined_fits(intact, len(intact) + 1, live_cells, fit_wins) is True)
    # Regression (owner, live at 280x83): a cell LABEL carries SGR color, so comparing the
    # raw label against an SGR-stripped body never matched — condition (2) failed on every
    # live frame and auto-combined never engaged at ANY size. Both sides must be stripped.
    check("itemB: combined_fits matches COLORIZED labels (CYAN in-use / DIM configured) — "
          "the live shape; a raw-vs-stripped comparison made auto-combined dead on arrival",
          any("\033[" in c[0] for c in live_cells)  # the fixture is genuinely colorized
          and combined_fits(intact, len(intact) + 1, live_cells, fit_wins) is True)
    # Owner report at 280x83: a CRITICAL pane must NOT suppress the combined view. The pin
    # exists so a critical pane is never CYCLED OUT OF VIEW; a combined frame renders every
    # pane (the critical one included) plus the limits, so the pin has nothing to protect.
    crit_big_wins = [{"idx": "0", "name": "defect-fix", "active": True,
                      "panes": [P("defect-fix", awaiting=True)]},
                     {"idx": "1", "name": "talk", "active": False, "panes": [P("liaison")]}]
    crit_big = render_full("sess", crit_big_wins, 2, 2, live_cells, [], [], fake_cache,
                           280, 10 ** 6, cycle=False)
    crit_big_p = plain(crit_big)
    check("itemB: a CRITICAL pane on a BIG frame still selects the COMBINED view — both "
          "PLAN LIMITS and WINDOWS present, the critical pane visible with its ? marker "
          "(the pin only holds a page while CYCLING)",
          combined_fits(crit_big, 83, live_cells, crit_big_wins) is True
          and any("PLAN LIMITS" in l for l in crit_big_p)
          and any("WINDOWS" in l for l in crit_big_p)
          and any("defect-fix?" in l for l in crit_big_p)
          and all(re.sub(r"\033\[[0-9;]*m", "", c[0]) in "\n".join(crit_big_p)
                  for c in live_cells))
    big = plain(comb_lines)
    small = plain(render_strip("sess", fit_wins, 1, 1, cells, notes, console,
                               220, 10, now=0))
    check("itemB: a fitting frame shows BOTH blocks at once (what auto selects), while "
          "the too-small frame still shows exactly one view per ~10s phase",
          combined_fits(comb_lines, len(comb_lines) + 1)
          and any("PLAN LIMITS" in l for l in big) and any("WINDOWS" in l for l in big)
          and any("WINDOWS" in l for l in small)
          and not any("PLAN LIMITS" in l for l in small))

    # Owner item C: --view pins ONE body — no alternation at any tick, at every layout.
    for layout_fn, dims in ((render_strip, (240, 8)), (render_narrow, (56, 40)),
                            (render_tiny, (58, 12))):
        lim = [plain(layout_fn("sess", fit_wins, 1, 1, cells, notes, console, *dims,
                               now=n, phase="limits")) for n in (0, 10, 20, 30)]
        pan = [plain(layout_fn("sess", fit_wins, 1, 1, cells, notes, console, *dims,
                               now=n, phase="panes")) for n in (0, 10, 20, 30)]
        check(f"itemC: {layout_fn.__name__} --view limits — LIMITS only at EVERY tick, "
              "never a windows grid, never the pane legend",
              all(any("LIMITS" in l for l in f) for f in lim)
              and not any(any("WINDOWS" in l for l in f) for f in lim)
              and not any(any("approval" in l for l in f) for f in lim)
              and all(len(f) <= dims[1] for f in lim))
        check(f"itemC: {layout_fn.__name__} --view panes — windows/panes only at EVERY "
              "tick, never the limits block",
              all(any("WINDOWS" in l for l in f) for f in pan)
              and not any(any("PLAN LIMITS" in l for l in f) for f in pan)
              and all(any("x" in l for l in f) for f in pan)
              and all(len(f) <= dims[1] for f in pan))
    vf_lim = [plain(render_full("sess", fit_wins, 1, 1, cells, notes, console, fake_cache,
                                160, 40, now=n, phase="limits")) for n in (0, 10, 20)]
    vf_pan = [plain(render_full("sess", fit_wins, 1, 1, cells, notes, console, fake_cache,
                                160, 40, now=n, phase="panes")) for n in (0, 10, 20)]
    check("itemC: render_full --view limits/panes pin their own body at every tick",
          all(any("PLAN LIMITS" in l for l in f) and not any("WINDOWS" in l for l in f)
              for f in vf_lim)
          and all(any("WINDOWS" in l for l in f)
                  and not any("PLAN LIMITS" in l for l in f) for f in vf_pan))
    ap_view = argparse.ArgumentParser()
    ap_view.add_argument("--view", choices=("auto", "limits", "panes", "combined"),
                         default="auto")
    check("itemC: --view parses limits/panes/combined and defaults to auto (current "
          "behavior preserved when the flag is never passed)",
          ap_view.parse_args([]).view == "auto"
          and ap_view.parse_args(["--view", "limits"]).view == "limits"
          and ap_view.parse_args(["--view", "panes"]).view == "panes"
          and ap_view.parse_args(["--view", "combined"]).view == "combined")

    # Fix D (owner-approved item #172): system RAM+CPU readout, colored by pressure so an
    # operator AND watcher see resource pressure at a glance (this run hit an OOM cascade).
    check("system_cell_variants: RED when avail RAM < 500MB, cpu% >= 90, or load1 >= "
          "cores (saturation reddens even a modest cpu%)",
          RED in system_cell_variants(200, 8000, 1.0, 4)[0]
          and RED in system_cell_variants(4000, 8000, 4.0, 4)[0]
          and RED in system_cell_variants(4000, 8000, 1.0, 4, cpu_pct=95.0)[0]
          and RED in system_cell_variants(4000, 8000, 4.5, 4, cpu_pct=50.0)[0])
    check("system_cell_variants: YELLOW at the halfway warning band (500-1500MB avail, "
          "cpu% >= 70, or load1 >= 75% of cores)",
          YELLOW in system_cell_variants(1000, 8000, 1.0, 4)[0]
          and YELLOW in system_cell_variants(4000, 8000, 3.0, 4)[0]
          and YELLOW in system_cell_variants(4000, 8000, 1.0, 4, cpu_pct=75.0)[0])
    check("system_cell_variants: GREEN when RAM and CPU are both comfortable",
          GREEN in system_cell_variants(4000, 8000, 1.0, 4)
          [0] and GREEN in system_cell_variants(4000, 8000, 1.0, 4, cpu_pct=20.0)[0])
    check("system_cell_variants: [] when neither RAM nor CPU reading is available on "
          "this platform (decorative info must never crash or blank-render the header)",
          system_cell_variants(None, None, None, 4) == [])
    check("system_cell_variants: degrades to RAM-only when no CPU reading exists, "
          "never drops RAM data just because CPU data is missing",
          system_cell_variants(4000, 8000, None, 4) != []
          and all("CPU" not in v for v in system_cell_variants(4000, 8000, None, 4)))
    check("system_cell_variants: cpu% preferred, load-vs-cores only as first-frame "
          "fallback; RAM rendered as used-% + GB available (one decimal, rounded DOWN)",
          "CPU 34%" in system_cell_variants(4000, 8000, 1.0, 4, cpu_pct=34.2)[0]
          and "CPU 1.0/4" in system_cell_variants(4000, 8000, 1.0, 4)[0]
          and "RAM 50% (3.9GB free)" in system_cell_variants(4000, 8000, 1.0, 4)[0])
    sysv = system_cell_variants(200, 8000, 1.0, 4)
    check("system_cell_variants: graceful shrink full -> short -> RAM-only — detail "
          "thins out but the RAM value itself is NEVER dropped while any variant remains",
          "RAM 98% (0.1GB free)" in sysv[0] and "CPU 1.0/4" in sysv[0]
          and "0.1GB free" in sysv[1] and "CPU 1.0/4" in sysv[1]
          and "0.1GB free" in sysv[-1] and "CPU" not in sysv[-1])
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
    sweep_calm = [{"idx": str(i), "name": f"win{i}", "active": i == 0,
                   "panes": [P(f"seat{i}a"), P(f"seat{i}b", ctx=42.0)]}
                  for i in range(4)]
    for w in (70, 80):
        for fixture, nv in ((sweep_wins, 0), (sweep_calm, 10)):
            out_full = render_full("improve-teamview", fixture, 4, 8, sweep_cells,
                                   ["deepseek $8.63 left"], [], fake_cache, w, 30, now=nv)
            plain_full = [re.sub(r"\033\[[0-9;]*m", "", l) for l in out_full]
            check(f"render_full at {w}w now={nv}: header line (carrying the live system "
                  "RAM/CPU cue) never exceeds the requested width on either cycle phase",
                  all(len(l) <= w for l in plain_full))

    # ---- UX backlog items 2,4,5,6,7,8,9,10 (findings run tv-ux-review; fixed 2026-07-26) ----
    hot_cells = [("claude:main 5h", 14, 97.0, ""), ("zai 7d", 6, 12.0, "")]
    tiny_hot = render_tiny("sess", calm_wins, 2, 3, hot_cells, [], [], 60, 12, now=10)
    hot_line = next((l for l in tiny_hot if "97%" in strip_sgr(l)), "")
    cool_line = next((l for l in tiny_hot if "12%" in strip_sgr(l)), "")
    check("item2: render_tiny at 60x12 keeps the urgency color band on LIMITS rows — a "
          "97% row carries RED SGR, a 12% row GREEN (the verified false all-clear)",
          RED in hot_line and GREEN in cool_line)
    for layout_fn, dims in ((render_strip, (220, 10)), (render_narrow, (70, 40)),
                            (render_tiny, (60, 12))):
        out_l = layout_fn("sess", wins, 2, 3, hot_cells, [], [], *dims, now=0)
        check(f"item2(rev): {layout_fn.__name__} emits NO legend line at all — the mini "
              "legend is GONE from the small layouts (reversed 2026-07-28); frames still "
              "respect their width",
              "approval" not in strip_sgr("\n".join(out_l))
              and all(visible_len(l) <= dims[0] for l in out_l))
    fl2 = strip_sgr(" ".join(legend_lines(70, max_lines=2)))
    check("legend_lines: drop priority — under a 2-line cap at 70 cols the alarm keys "
          "survive and tail items drop; no line exceeds width. Still pinned because "
          "interface_legend_lines marks from the SAME tuples",
          "awaiting approval" in fl2 and "empty-title" not in fl2
          and all(len(strip_sgr(l)) <= 70 for l in legend_lines(70, max_lines=2)))
    ilg = [strip_sgr(l) for l in interface_legend_lines(100)]
    check("interface-legend: the standalone key carries EVERY marker the renderers use — "
          "it is the only on-screen key now, so a gap here is a gap everywhere",
          all(strip_sgr(i) in "\n".join(ilg) for i in LEGEND_ITEMS + LEGEND_CTX)
          and any("--help-panes" in l for l in ilg))

    roll_wins = [{"idx": "0", "name": "w0", "active": True,
                  "panes": [P("calm", ctx=30.0), P("hot", ctx=94.0, approx=True),
                            P("stuck", awaiting=True, ctx=91.0)]}]
    check("item4: rollup line — pane total, worst ctx (keeping its ~), red count, "
          "? count",
          strip_sgr(rollup_variants(roll_wins)[0]) == "3 panes · worst ~94% · 2 red · 1 ?")
    full_o = render_full("sess", roll_wins, 1, 3, hot_cells, [], [], fake_cache, 220, 50,
                         now=0)
    strip_o = render_strip("sess", roll_wins, 1, 3, hot_cells, [], [], 220, 10, now=0)
    narrow_o = render_narrow("sess", roll_wins, 1, 3, hot_cells, [], [], 70, 40, now=0)
    tiny_o = render_tiny("sess", roll_wins, 1, 3, hot_cells, [], [], 60, 12, now=0)
    check("item4: the alarm rollup renders at EVERY layout size (full 220x50, strip "
          "220x10, narrow 70x40, tiny 60x12) above the rotating windows detail",
          all(any(("2 red" in strip_sgr(l) or "2r" in strip_sgr(l)) for l in o)
              for o in (full_o, strip_o, narrow_o, tiny_o)))

    check("item5: color-band thresholds documented — a legend ctx key AND -h carry the "
          "green<60 / yellow<85 / red≥85 numbers",
          any("<60" in strip_sgr(i) and "≥85" in strip_sgr(i) for i in LEGEND_CTX)
          and "green<60" in __doc__ and "red≥85" in __doc__)

    check("item6: '…' is the ONE text-cut glyph — clip_line and clean_title never emit "
          "'~' (reserved for ctx-match uncertainty), and the legend says so",
          strip_sgr(clip_line("x" * 50, 10)).endswith("…")
          and "~" not in clip_line("x" * 50, 10)
          and strip_sgr(clean_title("a-very-long-pane-title-here")).endswith("…")
          and any("text cut" in strip_sgr(i) for i in LEGEND_ITEMS))

    # R24 STRENGTHENED this guarantee rather than restating it: it used to be "every tmux call is
    # read-only", which is a promise about HOW teamview calls tmux. It is now "teamview makes no
    # tmux call at all", which is a promise there is nothing to get wrong. The check pins the new,
    # stronger claim AND that the weaker wording is gone — a doc that still promised read-only
    # tmux calls would be describing code that no longer exists.
    check("item7: --help-security states the write-set, EVERY endpoint, the run-state read, and "
          "the STRONGER R24 guarantee (no tmux call at all, not merely read-only ones)",
          all(s in DOC_SECURITY for s in ("teamview-providers.json", "api.anthropic.com",
              "api.z.ai", "api.deepseek.com", "api.kimi.com", "api.moonshot",
              "NO tmux call at all", "state.json"))
          and "NEVER mutates tmux" not in DOC_SECURITY)
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
          all(s in DOC_PANES for s in ("~N%", "Clears when", "shell", "EMPTY title",
                                       "RECENTLY ACTIVE", "ambiguous"))
          # the `+` marker's INSTRUMENT changed in R24; the doc must say so, not just describe
          # the new behaviour as if it had always been this way
          and "R24 changed this signal's instrument" in DOC_PANES)
    check("item8: pane_compact and pane_cell_variants carry the explicit 'shell' tag too",
          "gone shell" in strip_sgr(pane_compact(P("gone", shell=True)))
          and "gone shell" in strip_sgr(pane_cell_variants(P("gone", shell=True))[0]))

    # item9, R24 form: the refusal that replaces the tmux session lookup. It must PRINT THE EXACT
    # COMMAND, not merely name a flag — the owner uses teamview interactively and R24 removed the
    # bare-invocation auto-pick this refusal stands in for. It inherits session_error's contract:
    # stderr + exit 2, never an "empty" frame on stdout at exit 0 (a wrapper once recorded success
    # for a view that showed nothing).
    no_pkg = snapshot_refusal(None, None, None)
    check("item9: no snapshot -> teaching refusal carrying a RUNNABLE command for BOTH causes "
          "(wrong directory, and sensor not started), never a bare flag name",
          "teamview --package /path/to/<goal>/runs/run-N" in no_pkg
          and "team-monitor start --package /path/to/<goal>/runs/run-N" in no_pkg
          and SNAPSHOT_NAME in no_pkg)
    check("item9: a positional NAME that disagrees with the snapshot's OWN session refuses and "
          "names both; agreement (and no name at all) resolves to None",
          "'other', not 'kg-views'" in snapshot_refusal(None, "kg-views", Path("/p"), "other")
          and snapshot_refusal(None, "kg-views", Path("/p"), "kg-views") is None
          and snapshot_refusal(None, None, Path("/p"), "other") is None)
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
    calm_roll = [{"idx": "0", "name": "w0", "active": True,
                  "panes": [P("calm", ctx=30.0)]}]
    hedged = "\n".join(render_full("sess", calm_roll, 1, 1, stale_cells, [], [],
                                   fake_cache, 220, 50, now=10))
    unhedged = "\n".join(render_full("sess", calm_roll, 1, 1,
                                     [("claude:main 5h", 14, 10.0, "renews 23:00")],
                                     [], [], fake_cache, 220, 50, now=10))
    check("item10: full-layout limits header hedges 'providers polled Nm ago' when any "
          "bar carries its own older 'as of' stamp — and only then",
          "some bars older" in hedged and "some bars older" not in unhedged)
    check("item10: --help-providers explains a model-scoped weekly ('7d fable') as a "
          "SUBSET of the plain 7d window",
          "SUBSET" in DOC_PROVIDERS and "7d fable" in DOC_PROVIDERS)

    # ================= R24 (task 7.34): teamview renders the snapshot, it no longer takes one ===
    #
    # ⚠ THE FIXTURES BELOW ARE BUILT TO FAIL A WRONG IMPLEMENTATION, not to exercise the right
    # one (p-green-harness-over-a-broken-mechanism). A hand-authored snapshot that merely SAYS it
    # is old exercises the formatter, never staleness detection — so the STALE fixture carries a
    # captured_at 10 minutes back and a written_at of NOW. On a renderer keyed to written_at
    # every staleness check below goes green while the feature is dead; keyed to captured_at
    # they fire. That single field is the difference between a probe and a decoration.
    NOW = 1_800_000_000.0
    def snap_at(age_s, seats=None, **extra):
        """A snapshot captured `age_s` ago but WRITTEN this instant — the discriminating shape."""
        return {"schema": "team-monitor/1", "captured_at": NOW - age_s,
                "captured_at_iso": "(iso)", "written_at": NOW, "written_at_iso": "(iso)",
                "session": "kg-views", "session_alive": True,
                "box": {"available_mb": 4000, "total_mb": 8000, "load1": 1.0, "cores": 4},
                "seats": seats if seats is not None else [
                    {"seat": "leader", "pane": "%1", "window": "1", "harness": "claude",
                     "model": "claude-opus-5", "ctx_pct": 30.0, "ctx_refresh": 50,
                     "last_activity_age_s": 5.0, "liveness": "live"}],
                "roster_absent": [], **extra}

    fresh, stale = snap_at(3), snap_at(600)
    check("R24: snapshot age is measured from captured_at — a snapshot CAPTURED 10 min ago but "
          "WRITTEN this instant is 600s old, NOT fresh (a written_at-keyed reader reports ~0)",
          round(snapshot_age_s(fresh, NOW)) == 3 and round(snapshot_age_s(stale, NOW)) == 600)
    check("R24: written_at is never consulted — deleting it changes no age reading",
          snapshot_age_s({k: v for k, v in stale.items()
                          if k not in ("written_at", "written_at_iso")}, NOW)
          == snapshot_age_s(stale, NOW))
    check("R24: staleness fires on the CAPTURE clock at the documented threshold, and a missing "
          "captured_at is treated as STALE (unknown is never assumed healthy)",
          not snapshot_stale(fresh, NOW) and snapshot_stale(stale, NOW)
          and snapshot_stale(snap_at(SNAPSHOT_STALE_S + 1), NOW)
          and not snapshot_stale(snap_at(SNAPSHOT_STALE_S - 1), NOW)
          and snapshot_stale({"seats": []}, NOW) and snapshot_stale({"captured_at": "x"}, NOW))
    check("R24: a stale snapshot renders the word WARNING-loudly (STALE + RED + the age), a "
          "fresh one does not — and BOTH forms carry it, so it survives every fold",
          all("STALE" in strip_sgr(v) and "10m00s" in strip_sgr(v)
              and RED in v for v in age_variants(snapshot_age_s(stale, NOW)))
          and not any("STALE" in strip_sgr(v)
                      for v in age_variants(snapshot_age_s(fresh, NOW))))

    # AGE IS ALWAYS ON SCREEN — a criterion, at EVERY layout and EVERY width. The cues around it
    # are allowed to degrade to ""; this is not. A staleness warning that vanishes precisely when
    # the terminal is small is the silence it exists to break.
    r24_wins, r24_nw, r24_np = snapshot_tree(stale, NOW)
    age_missing = []
    for fn, needs_cache in ((render_full, True), (render_strip, False),
                            (render_narrow, False), (render_tiny, False)):
        for w, h in ((220, 50), (120, 24), (80, 20), (70, 12), (60, 12), (40, 10)):
            for cyc in (True, False):
                args_ = ([ "kg-views", r24_wins, r24_nw, r24_np, cells, [], []]
                         + ([fake_cache] if needs_cache else []) + [w, h])
                lines = fn(*args_, cue=False, now=NOW, cycle=cyc, snap=stale)
                body = strip_sgr("\n".join(clip_line(l, w) for l in lines))
                if "STALE" not in body:
                    age_missing.append((fn.__name__, w, h, cyc))
    check("R24: the STALE snapshot warning survives EVERY layout x width x cycle phase "
          "(full/strip/narrow/tiny, 220w down to 40w) — it is base text, never a droppable cue",
          not age_missing)
    age_missing_fresh = []
    for fn, needs_cache in ((render_full, True), (render_strip, False),
                            (render_narrow, False), (render_tiny, False)):
        for w, h in ((220, 50), (80, 20), (40, 10)):
            args_ = (["kg-views", r24_wins, r24_nw, r24_np, cells, [], []]
                     + ([fake_cache] if needs_cache else []) + [w, h])
            body = strip_sgr("\n".join(clip_line(l, w) for l in
                                       fn(*args_, cue=False, now=NOW, snap=fresh)))
            if "snap 3s" not in body:
                age_missing_fresh.append((fn.__name__, w))
    check("R24: a HEALTHY snapshot's age is on screen too, at every layout and width — the "
          "display is unconditional, not a warning that only appears once it is too late",
          not age_missing_fresh)

    # FAIL LOUD. G-153's lesson as a contract: a total read failure must never be
    # indistinguishable from a quiet room. Each of these must RENDER, never blank.
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        miss, e_miss = load_snapshot(d)
        (d / SNAPSHOT_NAME).write_text("{not json", encoding="utf-8")
        bad, e_bad = load_snapshot(d)
        (d / SNAPSHOT_NAME).write_text('{"hello": 1}', encoding="utf-8")
        wrong, e_wrong = load_snapshot(d)
        (d / SNAPSHOT_NAME).write_text(json.dumps(fresh), encoding="utf-8")
        good, e_good = load_snapshot(d)
        check("R24 fail-loud: missing / unparseable / wrong-shaped state.json each return a "
              "NAMED error and no snapshot; a real one returns the snapshot and no error",
              (miss, bad, wrong) == (None, None, None) and good is not None
              and e_good is None
              and all(e and SNAPSHOT_NAME in e for e in (e_miss, e_bad, e_wrong))
              and "not valid JSON" in e_bad and "captured_at" in e_wrong)
        check("R24 fail-loud: load_snapshot never raises and never returns a HALF answer — "
              "exactly one of (snapshot, error) is None in all four cases",
              all((s is None) != (e is None)
                  for s, e in ((miss, e_miss), (bad, e_bad), (wrong, e_wrong), (good, e_good))))

        class A:  # the argparse shape render() consumes
            width, height, package, no_rotate, view = 80, 24, str(d), False, "auto"
        (d / SNAPSHOT_NAME).write_text("{not json", encoding="utf-8")
        loud = strip_sgr("\n".join(render(A(), str(d), now=NOW)))
        check("R24 fail-loud: render() on a corrupt snapshot returns a VISIBLE error frame — "
              "never an empty dashboard, which reads as a quiet room",
              "NO SNAPSHOT" in loud and "not valid JSON" in loud and len(loud.strip()) > 40)
        (d / SNAPSHOT_NAME).write_text(json.dumps(snap_at(3, seats=[])), encoding="utf-8")
        empty = strip_sgr("\n".join(render(A(), str(d), now=NOW)))
        check("R24 fail-loud: a snapshot listing ZERO panes renders as a stated condition with "
              "session_alive, not as a blank frame (absence must be audible)",
              "SNAPSHOT HAS NO PANES" in empty and "session_alive" in empty)

    # ⚠ THE SNAPSHOT IS RE-READ EVERY FRAME, and this is the check that pins it. The live loop
    # calls render() per frame; if the load were hoisted OUT of render(), every frame would show
    # the age of the FIRST read — a dead sensor would render forever-fresh and the STALE warning
    # could never fire while teamview stayed up. That is precisely the defect 7.34 exists to
    # prevent, and it would live in the one code path --once never exercises. Verified against a
    # frozen snapshot in a real running loop (ages advanced 50s -> 55s -> STALE 1m00s -> 1m05s
    # -> 1m10s, crossing the threshold mid-loop); this is the deterministic form of that proof.
    with tempfile.TemporaryDirectory() as td2:
        d2 = Path(td2)

        class B:
            width, height, package, no_rotate, view = 200, 30, str(d2), True, "combined"

        (d2 / SNAPSHOT_NAME).write_text(json.dumps(snap_at(3)), encoding="utf-8")
        f1 = strip_sgr("\n".join(render(B(), str(d2), now=NOW)))
        (d2 / SNAPSHOT_NAME).write_text(json.dumps(snap_at(900)), encoding="utf-8")
        f2 = strip_sgr("\n".join(render(B(), str(d2), now=NOW)))
        check("R24: render() RE-READS state.json every frame — replacing the file between two "
              "calls flips a fresh frame to a STALE one, so a frozen sensor cannot render "
              "forever-fresh while teamview stays up",
              "snap 3s" in f1 and "STALE" not in f1 and "STALE" in f2 and "15m00s" in f2)

    # roster_absent — the GHOSTROW input. A roster row whose pane left the room must be VISIBLE;
    # dropping it would render a vanished seat as nothing, which is the failure this run keeps
    # paying for: absence indistinguishable from health.
    ghost = snap_at(3, roster_absent=[{"seat": "vanished", "pane": "%9", "liveness": "absent",
                                       "reason": "pane gone"}])
    g_wins, g_nw, g_np = snapshot_tree(ghost, NOW)
    check("R24: roster_absent renders as its own trailing pseudo-window and counts toward the "
          "pane total — a seat whose pane left the room is never silently dropped",
          g_nw == 2 and g_np == 2
          and "vanished" in strip_sgr(g_wins[-1]["panes"][0]["name"])
          and "absent" in strip_sgr(g_wins[-1]["name"]))
    check("R24: no roster_absent rows -> no pseudo-window invented",
          snapshot_tree(fresh, NOW)[1] == 1)

    # design-760 §1/§4 (task 7.74) — headless[] and headless_unattributed. A headless session
    # holds a seat and no pane, so every pane read above is blind to it; these pin that the
    # snapshot's second source reaches the screen with its fields intact, that an unjoinable row
    # is LOUD rather than a nameless session row, and that a snapshot without either key renders
    # exactly as it did before the field existed.
    h_rows = [{"seat": "drain-1", "session_id": "s1", "exec_id": 11, "job_id": "j1",
               "state": "running", "started_at": "(iso)", "started_age_s": 240.0,
               "last_activity": NOW - 33.0, "outcome": None, "pid": 4242, "log_path": "/l/1"},
              {"seat": "drain-2", "session_id": "s2", "exec_id": 12, "job_id": "j1",
               "state": "done", "started_at": "(iso)", "started_age_s": 3600.0,
               "last_activity": NOW - 1800.0, "pid": 99, "log_path": "/l/2",
               "outcome": {"exit_code": 0, "status": "done", "ended_at": "(iso)",
                           "completion_msg_id": "m7"}},
              {"seat": "drain-3", "session_id": "s3", "exec_id": 13, "job_id": "j2",
               "state": "running", "started_at": "(iso)", "started_age_s": 900.0,
               "last_activity": NOW - 900.0, "outcome": None, "pid": 7, "log_path": ""}]
    h_snap = snap_at(3, headless=h_rows)
    h_wins, h_nw, h_np = snapshot_tree(h_snap, NOW)
    h_block = h_wins[-1]
    hp = h_block["panes"]
    check("760: headless[] renders as its own trailing pseudo-window and counts toward the pane "
          "total — a session with a seat and no pane is never invisible",
          h_nw == 2 and h_np == 4 and strip_sgr(h_block["name"]) == "headless" and len(hp) == 3)
    check("760 §5: EVERY headless row carries seat + state + age, and the age is the snapshot's "
          "own taken_at-started_at (started_age_s), not a second derivation",
          [strip_sgr(p["name"]) for p in hp] == ["drain-1", "drain-2", "drain-3 stale"]
          and [p["harness"] for p in hp] == ["running", "done", "running"]
          and [p["age"] for p in hp] == [fmt_age(240.0), fmt_age(3600.0), fmt_age(900.0)]
          and all(p["age"] for p in hp))
    check("760 §5: outcome renders on TERMINAL rows only — read off the presence of the sensor's "
          "`outcome` field, so teamview holds no copy of the status vocabulary",
          [p["model"] for p in hp] == ["", "exit0", ""])
    check("760 §1: a quiet NON-terminal row is a WARNING (red + the word stale); a terminal row "
          "idle far longer is history, not an alarm, and stays plain",
          RED in hp[2]["name"] and "stale" in strip_sgr(hp[2]["name"])
          and RED not in hp[0]["name"] and RED not in hp[1]["name"]
          and headless_quiet_s(h_rows[2], h_snap["captured_at"]) >= HEADLESS_STALE_S)
    check("760: the stale marker is threshold-driven, not hardcoded to one row — raising the "
          "threshold past the quiet row clears it, lowering it past a live row fires it "
          "(a marker that cannot move is a decoration)",
          RED not in headless_panes(h_snap, stale_after=10_000.0)[2]["name"]
          and RED in headless_panes(h_snap, stale_after=1.0)[0]["name"])
    check("760: a headless row is a session, NOT a context reading — no ctx%, no agent-type "
          "term, never a pinned-critical pane; a fabricated 0% would enter the rollup as health",
          all(p["ctx"] is None and p["cls"] == "" and not is_critical_pane(p) for p in hp))

    # C-3 RED ARM. `seat` is REQUIRED by design-760 §3 and guaranteed at the dispatch door, so a
    # seatless row means that guarantee broke upstream. The two answers design-760 §4 forbids are
    # exactly the two a careless renderer gives: drop it, or show it as a nameless session row.
    mal = headless_panes(snap_at(3, headless=[
        {"session_id": "s9", "exec_id": 91, "state": "running", "started_age_s": 5.0},
        {"seat": "   ", "exec_id": 92, "state": "running", "started_age_s": 5.0},
        "not-a-row"]), NOW)
    check("760 §4 RED ARM: a malformed headless row (no seat / blank seat / not a mapping) is "
          "FLAGGED and counted — never dropped, and never rendered as a nameless session row",
          len(mal) == 3
          and all("MALFORMED" in strip_sgr(p["name"]) and RED in p["name"] for p in mal)
          and "exec 91" in strip_sgr(mal[0]["name"]) and "exec ?" in strip_sgr(mal[2]["name"]))
    check("760 §4 RED ARM control: the same rows WITH a seat render plainly — the flag tracks the "
          "missing field, not the code path (a flag that always fires proves nothing)",
          not any("MALFORMED" in strip_sgr(p["name"]) for p in hp))

    # §4's incident field: LOUD, and never a row. It rides the block's own header.
    u_snap = snap_at(3, headless=h_rows[:1], headless_unattributed={
        "count": 2, "exec_ids": [77, 78],
        "rows": [{"exec_id": 77, "session_id": "sx", "reason": "no dispatch-time row"},
                 {"exec_id": 78, "session_id": "sy", "reason": "no dispatch-time row"}]})
    u_wins, _u_nw, u_np = snapshot_tree(u_snap, NOW)
    u_block = u_wins[-1]
    check("760 §4: headless_unattributed renders as a WARNING on the block header — the count is "
          "loud and RED, and it is NEVER a row: the pane total is unchanged by the incident",
          "UNATTRIBUTED" in strip_sgr(u_block["name"]) and "2" in strip_sgr(u_block["name"])
          and RED in u_block["name"] and len(u_block["panes"]) == 1 and u_np == 2
          and not any("UNATTRIBUTED" in strip_sgr(p["name"]) for p in u_block["panes"]))
    check("760 §4: the incident surfaces even when the join left NO renderable row at all — the "
          "block appears with the warning and no session rows (an empty headless[] must not "
          "swallow the reason it is empty)",
          "UNATTRIBUTED" in strip_sgr(snapshot_tree(
              snap_at(3, headless=[], headless_unattributed={"count": 1, "exec_ids": [5]}),
              NOW)[0][-1]["name"]))
    check("760 §4: a count-less incident payload still renders a count from its own rows — a "
          "warning that degrades to a bare label would read as a formatting quirk",
          "1" in strip_sgr(headless_window_name(
              {"headless_unattributed": {"exec_ids": [5]}})))

    # Criterion (3): BOTH FIELDS ABSENT -> UNCHANGED, and criterion (2) at the FRAME, not just in
    # a return value. Both sweep every layout x width, and the ORACLE for the second one is the
    # roster_absent block that has shipped since R24: design-760 §1 says headless[] renders
    # "exactly as seats[] does", so the claim under test is EQUIVALENCE WITH THAT PRECEDENT, not
    # omnipresence. Measured here and stated rather than papered over: at strip/80x20 the grid has
    # room for ONE bank, and the trailing pseudo-window — absent or headless, identically — does
    # not make the frame. Asserting "always visible" would have been a check written to pass.
    check("760: a snapshot carrying NEITHER key invents no pseudo-window and no pane",
          snapshot_tree(fresh, NOW)[1] == 1 and headless_panes(fresh) == []
          and headless_window_name(fresh) == "headless")
    base_wins, base_nw, base_np = snapshot_tree(fresh, NOW)

    def frame_text(fn, needs_cache, wins_, npane_, snap_, w, h):
        lines = fn(*(["kg-views", wins_, len(wins_), npane_, cells, [], []]
                     + ([fake_cache] if needs_cache else []) + [w, h]),
                   cue=False, now=NOW, cycle=False, snap=snap_)
        return strip_sgr("\n".join(clip_line(l, w) for l in lines))

    LAYOUTS = ((render_full, True), (render_strip, False),
               (render_narrow, False), (render_tiny, False))
    # 60x12 is deliberately NOT in this sweep and the omission is not a convenience: at that size
    # the full layout PAGINATES the two windows, and render_full's non-cycle path calls
    # window_grid WITHOUT `now`, so which page renders is wall-clock dependent. An assertion there
    # would pass or fail by the second. The state itself is covered by the rotation check below.
    SIZES = ((220, 50), (120, 24), (80, 20))
    leaked, hl_gap, hl_seen = [], [], 0
    for fn, needs_cache in LAYOUTS:
        for w, h in SIZES + ((60, 12),):
            if any(t in frame_text(fn, needs_cache, base_wins, base_np, fresh, w, h)
                   for t in ("headless", "UNATTRIBUTED")):
                leaked.append((fn.__name__, w, h))
            if (w, h) not in SIZES:
                continue
            shown = "UNATTRIBUTED" in frame_text(fn, needs_cache, u_wins, u_np, u_snap, w, h)
            hl_seen += bool(shown)
            if shown != ("vanished" in frame_text(fn, needs_cache, g_wins, g_np, ghost, w, h)):
                hl_gap.append((fn.__name__, w, h))
    check("760: with both keys absent NO layout at any width grows a headless block — a snapshot "
          "that predates the field renders as it always did, and does not crash",
          not leaked)
    check("760 §4: the unattributed warning reaches the RENDERED frame wherever the established "
          "roster_absent block reaches it, at every layout x width — same grid, same fate, no "
          "special pleading (and it does reach most of them, so the equivalence is not vacuous)",
          not hl_gap and hl_seen >= len(LAYOUTS) * len(SIZES) - 1)
    cramped = [strip_sgr("\n".join(window_grid(u_wins, 58, 3, dashes=True, now=NOW + t)))
               for t in (0, 10, 20)]
    check("760 §4: where the grid must PAGINATE the block away (the 60-col full frame), the "
          "warning is ROTATED, not lost — it returns on its own page like any other window",
          any("UNATTRIBUTED" in c for c in cramped)
          and any("UNATTRIBUTED" not in c for c in cramped))

    # The snapshot's own field mapping, pinned so a sensor-side rename cannot pass silently.
    mapped = snapshot_tree(snap_at(3, seats=[
        {"seat": "eng", "window": "2", "harness": "claude", "model": "claude-opus-5",
         "ctx_pct": 91.0, "ctx_ambiguous": True, "ctx_refresh": 50,
         "last_activity_age_s": 200.0, "liveness": "live"},
        {"seat": "", "title": "✳ btm", "window": "2", "harness": "btm",
         "liveness": "no-harness"},
        {"seat": "gone", "window": "2", "harness": "bash", "liveness": "shell"}]), NOW)[0][0]
    m = mapped["panes"]
    check("R24: seat->pane mapping — seat name, short model, ctx%/ambiguous/over, age, and the "
          "shell tag all come off the snapshot record and nothing else",
          m[0]["name"] == "eng" and m[0]["model"] == "opus-5" and m[0]["ctx"] == 91.0
          and m[0]["approx"] and m[0]["ctx_over"] and m[0]["age"] == "3m"
          and m[2]["shell"] and not m[0]["shell"] and m[2]["harness"] == "")
    check("R24: a pane whose occupant has not checked in falls back to its cleaned TITLE — a "
          "launched-but-silent harness is a real state, reported as one and never guessed",
          m[1]["name"] == "btm" and not m[1]["shell"])
    check("R24 follow-on(1): a snapshot with NO window_name/active fields still renders — "
          "header falls back to the bare INDEX and nothing is starred (a pre-follow-on "
          "sensor degrades by one field, it never blanks or crashes)",
          mapped["idx"] == "2" and mapped["name"] == "2" and mapped["active"] is False
          and all(p["active"] is False for p in mapped["panes"]))

    # R24 follow-on(1), CLOSED: window_name + window_active + pane_active come off the
    # snapshot. The two active flags are DISTINCT facts — one active window per session,
    # one active pane per window — so this pins that a second window also stars a pane
    # while only ONE window header is starred. Collapsing them into a single flag is the
    # failure this check exists to catch.
    act = snapshot_tree(snap_at(0, seats=[
        {"seat": "leader", "window": "2", "window_name": "control", "window_active": True,
         "pane_active": True, "harness": "claude", "liveness": "live"},
        {"seat": "cos", "window": "2", "window_name": "control", "window_active": True,
         "pane_active": False, "harness": "claude", "liveness": "live"},
        {"seat": "eng", "window": "3", "window_name": "workers", "window_active": False,
         "pane_active": True, "harness": "claude", "liveness": "live"}]), NOW)[0]
    check("R24 follow-on(1): window_name labels the header 'INDEX NAME', window_active "
          "stars exactly ONE header, pane_active stars one pane PER window",
          [w["name"] for w in act] == ["2 control", "3 workers"]
          and [w["active"] for w in act] == [True, False]
          and [[p["active"] for p in w["panes"]] for w in act] == [[True, False], [True]])
    check("R24 follow-on(1): the '*' reaches the rendered cell as a PREFIX and survives the "
          "narrowest variant — it must not be the first thing a shrinking cell drops",
          strip_sgr(pane_cell(act[0]["panes"][0])).startswith("*leader")
          and not strip_sgr(pane_cell(act[0]["panes"][1])).startswith("*")
          and all(strip_sgr(v).startswith("*")
                  for v in pane_cell_variants(act[0]["panes"][0]))
          and strip_sgr(pane_compact(act[1]["panes"][0])).startswith("*eng"))

    # box{} feeds the system cell; only CPU% is read live (the ruled exempt lane).
    bl = box_load(fresh)
    check("R24: RAM / load / cores come from the snapshot's box{} — no /proc read for any of "
          "them; an absent box{} degrades to None rather than falling back to a live read",
          bl[:4] == (4000, 8000, 1.0, 4)
          and box_load({"box": {}})[:3] == (None, None, None)
          and box_load(None)[:3] == (None, None, None))
    check("R24: the system cell still renders from snapshot-sourced values alone (RAM present "
          "even with no CPU reading at all)",
          "RAM 50% (3.9GB free)" in system_cell_variants(*(bl[:4] + (None,)))[0])

    # ⚠ LEADER BAR (ruling-734-cpu-cell.md): THE PROOF MUST NAME BOTH EXEMPT LANES. A check that
    # passes because someone scoped it, WITHOUT SAYING WHAT WAS SCOPED OUT, is theatre.
    #
    # ⚠ AND IT IS AN AST WALK, NOT A GREP, BECAUSE A GREP CANNOT DO THIS HONESTLY. Written as a
    # text scan it matched this file's own PROSE — the module docstring's "/proc/meminfo", the
    # --help-security text, box_load's own docstring, and the source of this very check. A proof
    # that counts the words describing a read as a read is not a proof. The AST sees CODE ONLY:
    # docstrings and comments are not Constant nodes in an expression position here. The plain
    # grep a human can run by hand is documented in README.md § "Proving the boundary"; this is
    # the machine-checkable form of the same claim.
    tree = ast.parse(Path(__file__).resolve().read_text(encoding="utf-8"))
    owner_of, skip = {}, set()

    def descend(node, owner):
        """Innermost enclosing def wins. `skip` collects the string nodes that are DOCUMENTATION
        rather than code: every docstring, and the DOC_* help texts — this file DESCRIBES the
        reads it makes, at length, and counting a description as a read is what made the text
        scan useless."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if ast.get_docstring(node, clean=False) is not None and isinstance(
                    node.body[0], ast.Expr):
                skip.add(id(node.body[0].value))
            owner = getattr(node, "name", owner)
        if isinstance(node, ast.Assign) and any(
                isinstance(tg, ast.Name) and tg.id.startswith("DOC_") for tg in node.targets):
            for s in ast.walk(node.value):
                skip.add(id(s))
        for child in ast.iter_child_nodes(node):
            owner_of[id(child)] = owner
            descend(child, owner)

    owner_of[id(tree)] = "<module>"
    descend(tree, "<module>")
    docstrings = skip
    PROVIDER_LANE = {"ps_processes", "claude_account_of", "opencode_store", "discover_accounts",
                     "claude_oauth_windows", "parse_claude_statusline", "codex_windows_from_rl",
                     "fetch_account", "resolve_key", "audit_lines"}
    BOX_CPU_LANE = {"cpu_usage_pct"}
    SELFTEST = {"cmd_selftest"}          # this proof's own fixtures are not production reads
    raw = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        v = node.value
        if "/proc/" in v or v == "tmux" or "/proc" == v:
            raw.append((node.lineno, owner_of.get(id(node), "<module>")))
    leaks = [r for r in raw if r[1] not in PROVIDER_LANE | BOX_CPU_LANE | SELFTEST]
    check("R24 CRITERION 1: NO raw-source read remains in executable code outside the two NAMED "
          "exempt lanes — provider plan-limit bars (task 7.34's own _Note:_) and box CPU% "
          f"(leader ruling, PROVISIONAL). Unaccounted: {leaks}",
          not leaks)
    check("R24: both exempt lanes are still REALLY present — this is an exemption list, not a "
          "blanket, so it must go stale LOUDLY if either lane's reads move or vanish",
          any(o in PROVIDER_LANE for _n, o in raw) and any(o in BOX_CPU_LANE for _n, o in raw))
    check("R24: no `tmux` process is invoked from production code anywhere — team-monitor is "
          "the run's ONE raw-source sensor, and teamview is now purely its reader",
          not [n for n, o in raw if o not in SELFTEST
               and any(isinstance(x, ast.Constant) and x.value == "tmux"
                       for x in ast.walk(tree) if getattr(x, "lineno", None) == n)])
    imported = {a.name.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.Import) for a in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module}
    check("R24: the ctx-monitor engine is no longer imported by path — importlib is gone from "
          "the import set and the module name appears in no executable expression",
          "importlib" not in imported
          and not [1 for node in ast.walk(tree)
                   if isinstance(node, ast.Constant) and isinstance(node.value, str)
                   and id(node) not in docstrings and "ctx_monitor" in node.value
                   and owner_of.get(id(node)) not in SELFTEST])   # this check names it itself

    # ---- the seat's agent type, rendered from the snapshot alone (task 7.80) ----
    csnap = {"seats": [
        {"seat": "a", "pane": "%1", "window": "1", "agent_type": "zzz-invented-type",
         "harness": "claude", "model": "opus", "ctx_pct": 10.0, "liveness": "live"},
        {"seat": "b", "pane": "%2", "window": "1", "agent_type": "zzz-invented-type",
         "harness": "claude", "model": "opus", "ctx_pct": 20.0, "liveness": "live"},
        {"seat": "c", "pane": "%3", "window": "1", "agent_type": "unclassified",
         "harness": "claude", "model": "opus", "ctx_pct": 30.0, "liveness": "live"}],
        "roster_absent": [{"seat": "g", "pane": "%9", "agent_type": "ghost-type",
                           "liveness": "absent", "reason": "gone"}]}
    cwins, _, _ = snapshot_tree(csnap)
    cpanes = [p for w in cwins for p in w["panes"]]
    check("7.80: agent_type reaches the pane record straight off the snapshot — no second source",
          [p["cls"] for p in cpanes] == ["zzz-invented-type", "zzz-invented-type",
                                         "unclassified", "ghost-type"])
    check("7.80: an INVENTED value renders verbatim — teamview holds no value list and "
          "validates nothing (this fails the moment someone adds one)",
          "zzz-invented-type" in strip_sgr(pane_cell_variants(cpanes[0])[0])
          and "zzz-invented-type" in strip_sgr(pane_compact(cpanes[0])))
    census = strip_sgr(" · ".join(agent_type_census(cpanes)))
    check("7.80: the rollup census GROUPS BY OBSERVED VALUE, most common first — it does not "
          "classify, so no vocabulary is encoded here either",
          census == "2 zzz-invented-type · 1 ghost-type · 1 unclassified")
    check("7.80: the absence marker is NOT special-cased — it is counted as one of the values, "
          "which is how an incompletely-classified room reports its own incompleteness",
          "1 unclassified" in census)
    check("7.80: agent_type DROPS FIRST as the cell narrows — the ctx% safety signal outlives it",
          "zzz-invented-type" not in strip_sgr(pane_cell_variants(cpanes[0])[1])
          and "10%" in strip_sgr(pane_cell_variants(cpanes[0])[1]))
    check("7.80: a snapshot with NO agent_type field renders exactly as before — no empty "
          "term in the census, no stray separator in the cell",
          agent_type_census([{"name": "x"}]) == []
          and "  " not in strip_sgr(pane_cell_variants(
              {"name": "x", "cls": "", "shell": False, "busy": False, "awaiting": False,
               "active": False, "harness": "claude", "model": "opus", "ctx": 5.0,
               "age": "1m"})[0]))
    # ⚠ THE RENAME'S OWN REGRESSION CHECK (2026-07-28, `r-agent-type-field-name`). A snapshot
    # carrying the WITHDRAWN `class` key must render as if the field were ABSENT — the key was
    # renamed, NOT aliased. Without this, renaming the reads and the fixtures together would
    # pass on the pre-rename code too: the harness would be supplying both sides of the
    # assertion. This check asserts the NEW behaviour against the OLD spelling, so it can only
    # pass if the rename actually happened, and it FAILS on any back-compat shim reading both.
    lsnap = {"seats": [{"seat": "a", "pane": "%1", "window": "1", "class": "staff",
                        "harness": "claude", "model": "opus", "ctx_pct": 10.0,
                        "liveness": "live"}]}
    lpanes = [p for w in snapshot_tree(lsnap)[0] for p in w["panes"]]
    check("7.80: a snapshot on the WITHDRAWN `class` key reads as ABSENT, never rendered — "
          "renamed, NEVER aliased (r-agent-type-field-name)",
          [p["cls"] for p in lpanes] == [""] and agent_type_census(lpanes) == []
          and "staff" not in strip_sgr(pane_cell_variants(lpanes[0])[0]))

    print(f"\nselftest: {'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s))")
    sys.exit(1 if failures else 0)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(prog="teamview", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", nargs="*",
                    help="tmux session — NAME or 'session NAME' (default: the session you "
                         "are in; outside tmux, the only running session). The single "
                         "token 'interface-legend' instead prints the dashboard's marker "
                         "key and exits — the key is NOT rendered on the dashboard")
    ap.add_argument("--package", default=os.environ.get("RBTV_TEAMVIEW_PACKAGE", ""),
                    help="team-kit run package for pane->agent roster names")
    ap.add_argument("--config", help="accounts config JSON (default ~/.config/rbtv/teamview.json)")
    ap.add_argument("--once", action="store_true", help="print one frame and exit")
    ap.add_argument("--no-rotate", action="store_true",
                    help="disable rotation: show EVERY window/pane in one COMPLETE "
                         "snapshot (best with --once; output can grow taller than the "
                         "terminal) — same as --view combined")
    ap.add_argument("--view", choices=("auto", "limits", "panes", "messages", "combined"),
                    default="auto",
                    help="which body to show (default auto: ONE combined frame when the "
                         "terminal fits limits+every pane, else the ~10s cycle) — limits: "
                         "plan-limit bars only · panes: windows/panes only · messages: "
                         "the coordination log's last sends only · combined: "
                         "everything at once (= --no-rotate)")
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

    # `teamview interface-legend` — a positional SUBCOMMAND. Intercepted here, ahead of
    # package discovery, so it prints from ANYWHERE including outside a run package, where
    # the dashboard itself refuses with exit 2. Reading the key must never depend on having
    # a live run. It touches no snapshot, no cache, no network.
    if [t.lower() for t in (args.session or []) if t] == ["interface-legend"]:
        width = args.width or shutil.get_terminal_size((100, 45)).columns
        for line in interface_legend_lines(width):
            print(line)
        return

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

    # R24 DISCOVERY — package-rooted, never tmux-rooted. --package wins; otherwise walk up from
    # cwd (the convention `coordinate` already uses, and every seat's cwd is inside its own run
    # package). A positional NAME is matched against the SNAPSHOT'S OWN `session` field, so
    # `teamview <name>` still means something without asking tmux anything.
    package = args.package or find_package()
    name_toks = [t for t in (args.session or []) if t]
    if len(name_toks) > 1 and name_toks[0] == "session":
        name_toks = name_toks[1:]
    wanted = name_toks[0] if name_toks else None
    probe, _probe_err = load_snapshot(package) if package else (None, None)
    err = snapshot_refusal(args.package, wanted, package,
                           (probe or {}).get("session"))
    if err:
        print(err, file=sys.stderr)
        sys.exit(2)

    if args.refresh or not cache_file().exists():
        poll_providers(args)

    def frame():
        cache = load_cache()
        if cache and time.time() - cache.get("ts", 0) > args.provider_ttl:
            spawn_background_poll(args)
        return "\n".join(render(args, package))

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
