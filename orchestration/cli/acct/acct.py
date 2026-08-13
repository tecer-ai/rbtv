#!/usr/bin/env python3
"""acct — every AI provider account on this box: park logins in named slots, switch between
them without re-logging-in, and read each account's plan limits.

  acct                              every provider's slots (* = active)
  acct <provider> ls
  acct <provider> add <name>        snapshot the CURRENT login into slot <name>
  acct <provider> use <name>        park the live tokens, then activate <name>
  acct <provider> rm <name> --force delete a slot (costs that account a re-login)
  acct usage [--posh]               plan limits for every account with readable usage
  acct <provider> usage [all|<name>] [--posh]

A slot is a snapshot of that harness's credential files, at
`{workspace}/.rbtv/config/acct/<provider>/<name>.json` (mode 600, gitignored). Which slot is
ACTIVE is DERIVED from the live login's own account id — never a marker file, which drifts.

Tokens ROTATE — `use` writes the live credentials back to the outgoing slot before swapping,
so a slot never holds a superseded refresh token. Switching affects NEW sessions only: a
running harness holds its token in memory and writes its own back on refresh.

acct NEVER refreshes a token: an expired stored token is REPORTED as expired, never rendered
as an empty or zero window. Keys and tokens are never printed; each credential is sent only
to its own provider's documented endpoint (`acct providers` lists them).
"""
import argparse
import base64
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HOME = Path.home()
TIMEOUT = 10
BOLD, DIM, OFF = "\033[1m", "\033[2m", "\033[0m"
CYAN, GREEN, YELLOW, RED = "\033[36m", "\033[32m", "\033[33m", "\033[31m"


def workspace_root():
    """The workspace this CLI is installed into — the nearest ancestor holding `rbtv.json`."""
    if env := os.environ.get("RBTV_WORKSPACE"):
        return Path(env)
    for p in Path(__file__).resolve().parents:
        if (p / "rbtv.json").exists():
            return p
    sys.exit("cannot resolve the workspace root (no rbtv.json above this script) — set RBTV_WORKSPACE")


def dig(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def jwt_claim(token, name):
    """One claim out of a JWT payload — identity only, never verified and never printed."""
    try:
        seg = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))).get(name)
    except Exception:  # noqa: BLE001 — a non-JWT credential simply has no claim
        return None


# ---------- providers ----------
#
# `locations` IS the slot format: label -> (file, json-key or None). None means the WHOLE
# file is the slot's payload; a key means only that key of that file moves, leaving the rest
# (claude keeps project history in ~/.claude.json) untouched. claude's two labels are the
# shape its slots have always had, so the existing slot files stay valid unchanged.
PROVIDERS = {
    "claude": {
        "locations": {"credentials": ("~/.claude/.credentials.json", None),
                      "oauthAccount": ("~/.claude.json", "oauthAccount")},
        "ident": lambda s: dig(s, "oauthAccount", "accountUuid"),
        "who": lambda s: dig(s, "oauthAccount", "emailAddress"),
        "expires": lambda s: dig(s, "credentials", "claudeAiOauth", "refreshTokenExpiresAt"),
    },
    "codex": {
        "locations": {"auth": ("~/.codex/auth.json", None)},
        "ident": lambda s: dig(s, "auth", "tokens", "account_id"),
        "who": lambda s: jwt_claim(dig(s, "auth", "tokens", "id_token"), "email"),
        "expires": lambda s: None,
    },
    "kimi": {
        "locations": {"cred": ("~/.kimi/credentials/kimi-code.json", None)},
        "ident": lambda s: jwt_claim(dig(s, "cred", "access_token"), "sub"),
        "who": lambda s: jwt_claim(dig(s, "cred", "access_token"), "sub"),
        "expires": lambda s: None,
    },
}

# Providers whose usage is readable but whose credential is a single API key in a shared
# store (opencode's auth.json): one key each, so there is nothing to switch between — usage
# only. Add a PROVIDERS row above the day a second key exists.
OPENCODE_STORE_KEYS = {"zai": "zai-coding-plan", "deepseek": "deepseek", "sakana": "sakana",
                       "google": "google", "kimi": "moonshot", "xai": "xai"}
CONSOLE_URLS = {"google": "aistudio.google.com", "sakana": "console.sakana.ai",
                "kimi": "kimi.com", "xai": "grok.com/?_s=usage"}
CLAUDE_WINDOW_LABELS = {"five_hour": "5h", "seven_day": "7d"}
USAGE_PROVIDERS = ("claude", "codex", "zai", "deepseek", "kimi", "google", "sakana", "xai")
COMMANDS = {"ls", "list", "add", "use", "rm", "usage", "providers", "doctor"}

DOC_PROVIDERS = """Providers — what acct can switch, and where each usage figure comes from
(read-only; keys are never printed and are sent ONLY to that provider's own endpoint):

  claude    SWITCHABLE. Usage: GET api.anthropic.com/api/oauth/usage with that account's
            STORED accessToken -> 5h/7d bars plus every model-scoped weekly the plan carries
            (e.g. "7d fable"). A model-scoped weekly is a SUBSET of the plain 7d window, not
            a separate budget: it can be exhausted while 7d still has room.
            ⚠ A PARKED slot's access token lasts ~8h. acct never refreshes it, so a slot
            parked longer than that reports `token expired` — `acct claude use <name>`, run
            one session, and its usage reads live again.
  codex     SWITCHABLE. Usage: LOCAL parse of ~/.codex/sessions rollout files'
            payload.rate_limits. Those files are per-MACHINE, not per-account, so codex
            usage describes whichever account last ran — one row, never per-slot.
  kimi      SWITCHABLE. Subscription OAuth login has no usage endpoint -> console only.
            Opt-in: an sk-kimi key (kimi.com/code/console) polls
            GET api.kimi.com/coding/v1/usages; a Moonshot platform key instead uses the
            documented GET /v1/users/me/balance (api.moonshot.ai|.cn).
  zai       usage only (one key in opencode's store):
            GET api.z.ai/api/monitor/usage/quota/limit -> 5h + weekly bars + plan tier
  deepseek  usage only: GET api.deepseek.com/user/balance -> money balance (no windows)
  google    no usage endpoint for an AI Studio key (verified 2026-07-24) -> console only
  sakana    no balance/usage endpoint (verified 2026-07-24) -> console only
  xai       usage only, console only. The credential is an OAUTH entry in opencode's store
            (access/refresh/expires, no `key`), so presence is read off `access`. No usage
            endpoint for a Grok subscription login (2026-08-13). ⚠ As of that date the
            account has no credits/subscription — a live run returns
            `personal-team-blocked:spending-limit`, so presence here means logged in, NOT
            usable.
"""


def prov_or_die(name):
    if name not in PROVIDERS:
        sys.exit(f"'{name}' has no switchable login (have: {', '.join(PROVIDERS)}). "
                 f"For usage only: acct {name} usage")
    return PROVIDERS[name]


# ---------- slots ----------

def slot_dir(prov):
    """`{workspace}/.rbtv/config/acct/{provider}/` — the CMP-1-ruled credential home. Moved
    here from `.rbtv/env/{provider}-accts/` on 2026-08-07. ⚠ `.rbtv/config/` is NOT ignored
    wholesale (its siblings are listed file by file); `.rbtv/config/acct/` has its OWN
    `.gitignore` directory rule, and that rule is the only thing keeping real refresh tokens
    out of a commit. Never relocate this without moving the rule in the same change."""
    return workspace_root() / ".rbtv" / "config" / "acct" / prov


def slot_path(prov, name):
    return slot_dir(prov) / f"{name}.json"


def slot_names(prov):
    return sorted(p.stem for p in slot_dir(prov).glob("*.json"))


def read_slot(prov, name):
    return json.loads(slot_path(prov, name).read_text(encoding="utf-8"))


def live_snapshot(prov):
    """The live credential set for `prov`, in slot shape — None when not logged in."""
    snap = {}
    for label, (path, key) in PROVIDERS[prov]["locations"].items():
        try:
            data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        snap[label] = data.get(key) if key else data
        if snap[label] is None:
            return None
    return snap


def write_live(prov, snap):
    """Install a slot's payload into the live credential locations. A key location is MERGED
    into the existing file so everything else in it (claude's project history) survives."""
    for label, (path, key) in PROVIDERS[prov]["locations"].items():
        p = Path(path).expanduser()
        if key:
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                doc = {}
            doc[key] = snap[label]
        else:
            doc = snap[label]
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".acct-tmp")
        tmp.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        tmp.chmod(0o600)
        tmp.replace(p)


def save(prov, name):
    """Write the CURRENT live login into slot `name`."""
    snap = live_snapshot(prov)
    if snap is None:
        sys.exit(f"no live {prov} login to save (expected "
                 f"{', '.join(p for p, _k in PROVIDERS[prov]['locations'].values())})")
    d = slot_dir(prov)
    d.mkdir(parents=True, exist_ok=True)
    p = slot_path(prov, name)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(p)


def active(prov):
    """The slot matching the login the harness is currently using — DERIVED, never recorded.

    A marker file is a second source of truth that silently drifts out of sync with the real
    credential store; the account id inside the live credentials IS the answer.
    """
    live = live_snapshot(prov)
    ident = PROVIDERS[prov]["ident"](live) if live else None
    if not ident:
        return None
    for n in slot_names(prov):
        if PROVIDERS[prov]["ident"](read_slot(prov, n)) == ident:
            return n
    return None


def cmd_add(prov, name):
    save(prov, name)
    print(f"saved the current {prov} login as '{name}' (now active)")


def cmd_use(prov, name):
    if not slot_path(prov, name).exists():
        sys.exit(f"no such {prov} slot: {name} (have: {', '.join(slot_names(prov)) or 'none'})")
    cur = active(prov)
    if cur == name:
        print(f"'{name}' is already the active {prov} account")
        return
    if cur:
        save(prov, cur)  # tokens rotate — park the live ones before swapping them out
    elif slot_names(prov) and live_snapshot(prov):
        # Overwriting a login held by no slot would lose it: its refresh token exists nowhere else.
        sys.exit(f"the current {prov} login is not saved in any slot — run "
                 f"`acct {prov} add <name>` first")
    write_live(prov, read_slot(prov, name))
    print(f"active {prov} account: {name} — start a NEW session to use it")


def cmd_rm(prov, name, force=False):
    if not slot_path(prov, name).exists():
        sys.exit(f"no such {prov} slot: {name}")
    if active(prov) == name:
        sys.exit(f"'{name}' is the active {prov} account — `use` another slot first")
    # A parked slot is the ONLY copy of that account's refresh token: deleting it costs a re-login.
    if not force:
        sys.exit(f"deleting slot '{name}' loses its login — that account would need a fresh "
                 f"login. Re-run with: acct {prov} rm {name} --force")
    slot_path(prov, name).unlink()
    print(f"removed {prov} slot '{name}'")


def cmd_ls(prov=None):
    """EVERY provider gets a line, including the ones with nothing parked.

    An earlier version printed only providers that HAD slots, so with claude parked and
    codex/kimi merely unparked, bare `acct` listed claude and nothing else — two switchable
    providers that were logged in the whole time simply did not appear, and their silence read
    as "acct does not do those". Absence is a state here, not the lack of one: `no slot saved`
    and `not logged in` are different facts and each has to say itself.
    """
    for p in ([prov] if prov else list(PROVIDERS)):
        names = slot_names(p)
        cur = active(p) if names else None
        for n in names:
            d = read_slot(p, n)
            who = PROVIDERS[p]["who"](d) or "?"
            exp_ms = PROVIDERS[p]["expires"](d)
            tail = ""
            if exp_ms:
                exp = datetime.fromtimestamp(exp_ms / 1000)
                tail = (f"  login valid until {exp:%Y-%m-%d}"
                        + (" STALE" if exp < datetime.now() else ""))
            print(f"{'*' if n == cur else ' '} {p + ':' + n:22} {who:38}{tail}")
        if names and not cur and live_snapshot(p):
            # The dangerous state: a live login held by NO slot. Its refresh token exists
            # nowhere else, and `use` would overwrite it — which is why `use` refuses here.
            print(f"  {'':22} ⚠ the live {p} login is in no slot — `acct {p} add <name>` "
                  f"before switching, or it is lost")
        if not names:
            print(f"  {p:22} " + (f"logged in, no slot saved — run: acct {p} add <name>"
                                  if live_snapshot(p) else "not logged in"))
    if not prov:
        # The usage-only providers have no slot concept at all — ONE key each in opencode's
        # shared store. Saying so beats leaving the reader to infer it from an absence.
        rest = [p for p in USAGE_PROVIDERS if p not in PROVIDERS]
        have = [p for p in rest if opencode_key(p)]
        print(f"  {'usage only':22} {', '.join(have) or 'none'}"
              f" — one key each, nothing to switch between: acct usage")


# ---------- usage: provider fetchers (parsers are pure; network isolated in fetch) ----------

def get_json(url, headers):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def opencode_store(path=None):
    p = Path(path) if path else HOME / ".local" / "share" / "opencode" / "auth.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def opencode_key(provider, path=None):
    """The credential opencode holds for a provider, or None. Entries are `type: api` with a
    `key`, EXCEPT oauth logins (xai) which carry `access`/`refresh`/`expires` and no `key` —
    reading only `key` there reports a live login as `no credential` (measured 2026-08-13)."""
    store_key = OPENCODE_STORE_KEYS.get(provider, provider)
    entry = opencode_store(path).get(store_key) or {}
    return entry.get("key") or entry.get("access")


def fmt_epoch(epoch):
    try:
        dt = datetime.fromtimestamp(int(epoch))
    except (TypeError, ValueError, OSError):
        return ""
    return dt.strftime("%H:%M") if dt.date() == datetime.now().date() else dt.strftime("%a %H:%M")


def iso_epoch(ts):
    try:
        return int(datetime.fromisoformat(ts).timestamp())
    except (TypeError, ValueError):
        return None


def parse_zai(d):
    """data.limits[] TOKENS_LIMIT entries — unit3/number5 = 5h window, unit6 = weekly;
    `percentage` = used %, nextResetTime epoch-ms; data.level = tier."""
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
    return {"balance": b.get("total_balance"), "currency": b.get("currency")}


def parse_kimi_code(d):
    """Kimi Code plan usage (community-verified endpoint, not officially documented) —
    tolerant: accepts per-model rows carrying limit/used at top level, .data, or .usages."""
    rows = d.get("usages") or (d.get("data") or {}).get("usages") or d.get("data") or []
    if isinstance(rows, dict):
        rows = [rows]
    windows = []
    for r in rows:
        if not isinstance(r, dict) or not r.get("limit"):
            continue
        used = r.get("used", r.get("limit", 0) - r.get("remaining", 0))
        windows.append({"label": str(r.get("model") or r.get("name") or "plan")[:12],
                        "pct": round(100.0 * used / r["limit"], 1),
                        "resets_at": r.get("reset_at") or r.get("resets_at")})
    if not windows:
        return {"error": "no usage rows"}
    return {"windows": windows[:2]}


def parse_moonshot(d):
    data = d.get("data") or {}
    if data.get("available_balance") is None:
        return {"error": "no available_balance"}
    return {"balance": str(data["available_balance"]), "currency": "CNY"}


def parse_oauth_limits(d):
    """Windows from the OAuth usage endpoint's limits[] — includes model-scoped weeklies
    (kind=weekly_scoped, scope.model.display_name e.g. 'Fable')."""
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
        out.append({"label": label, "pct": float(pct), "resets_at": iso_epoch(lim.get("resets_at"))})
    return out


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
    try:
        files = sorted(Path(sessions_dir).glob("*/*/*/rollout-*.jsonl"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return {"error": "no sessions dir"}
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


def claude_usage(creds):
    """Windows for ONE claude account, via its own STORED access token. acct never refreshes
    that token (the harness owns the chain), so an expired one is REPORTED, never rendered as
    an empty window set — an account showing 0% because nobody could read it is the one
    misreading that costs a wrong rotation."""
    oauth = (creds or {}).get("claudeAiOauth") or {}
    tok, exp = oauth.get("accessToken"), oauth.get("expiresAt")
    if not tok:
        return {"error": "no stored token"}
    if exp and exp / 1000 < time.time() + 60:
        return {"error": f"token expired {fmt_epoch(exp / 1000)} — `acct claude use <name>`, "
                         f"run one session, then retry"}
    try:
        wins = parse_oauth_limits(get_json(
            "https://api.anthropic.com/api/oauth/usage",
            {"Authorization": f"Bearer {tok}", "anthropic-beta": "oauth-2025-04-20"}))
    except Exception as e:  # noqa: BLE001 — never leak request details, class name only
        return {"error": type(e).__name__}
    return {"windows": wins, "fresh": True} if wins else {"error": "no windows returned"}


def kimi_usage(key):
    if key and key.startswith("sk-kimi"):
        for path in ("/coding/v1/usages", "/coding/v1/usage"):
            try:
                return parse_kimi_code(get_json("https://api.kimi.com" + path,
                                                {"Authorization": f"Bearer {key}"}))
            except Exception:  # noqa: BLE001 — try the fallback path
                continue
        return {"error": "usages endpoint unreachable"}
    if key:  # Moonshot platform key: documented balance endpoint
        for base in ("https://api.moonshot.ai", "https://api.moonshot.cn"):
            try:
                return parse_moonshot(get_json(base + "/v1/users/me/balance",
                                               {"Authorization": f"Bearer {key}"}))
            except Exception:  # noqa: BLE001 — try the other region host
                continue
        return {"error": "balance endpoint unreachable"}
    state = "logged in" if (HOME / ".kimi" / "credentials" / "kimi-code.json").is_file() \
        else "not logged in"
    return {"note": f"{state} · usage not exposed", "console": CONSOLE_URLS["kimi"]}


def usage_rows(provider=None, which=None):
    """[{provider, account, active, data}] for every account whose usage can be attempted.

    Only CLAUDE is multi-account here, and that is a property of the providers, not a gap:
    it is the one with a per-account usage endpoint. codex parses machine-wide session files;
    the rest hold a single key. Each of those reports ONE row, named by its active slot.
    """
    rows = []
    want = [provider] if provider else list(USAGE_PROVIDERS)
    for prov in want:
        if prov == "claude":
            act = active("claude")
            names = slot_names("claude")
            for n in names:
                if which and which != "all" and which != n:
                    continue
                creds = (live_snapshot("claude") if n == act else read_slot("claude", n))
                rows.append({"provider": prov, "account": n, "active": n == act,
                             "data": claude_usage((creds or {}).get("credentials"))})
            if not act and (not which or which == "all"):
                live = live_snapshot("claude")
                if live:  # a live login no slot holds — name it so `add` is the obvious fix
                    rows.append({"provider": prov, "account": "(unsaved)", "active": True,
                                 "data": claude_usage(live.get("credentials"))})
            continue
        name = (active(prov) or "main") if prov in PROVIDERS else "main"
        if which and which != "all" and which != name:
            continue
        if prov == "codex":
            data = parse_codex_sessions(HOME / ".codex" / "sessions")
        elif prov == "kimi":
            data = kimi_usage(os.environ.get("MOONSHOT_API_KEY") or opencode_key("kimi"))
        elif prov in ("google", "sakana", "xai"):
            state = "key present" if opencode_key(prov) else "no credential"
            data = {"note": f"{state} · console only", "console": CONSOLE_URLS[prov]}
        else:
            key = opencode_key(prov)
            if not key:
                data = {"error": "no credential"}
            elif prov == "zai":
                try:
                    data = parse_zai(get_json("https://api.z.ai/api/monitor/usage/quota/limit",
                                              {"Authorization": key}))
                except Exception as e:  # noqa: BLE001
                    data = {"error": type(e).__name__}
            else:
                try:
                    data = parse_deepseek(get_json("https://api.deepseek.com/user/balance",
                                                   {"Authorization": f"Bearer {key}"}))
                except Exception as e:  # noqa: BLE001
                    data = {"error": type(e).__name__}
        rows.append({"provider": prov, "account": name, "active": True, "data": data})
    # `*` marks the account in use, and ONLY where a provider HAS more than one to choose
    # between — a star every row carries marks nothing. Counted from the provider's own
    # account set, never from the rows SHOWN: `acct claude usage rbtv` filters to one row and
    # must still say that row is the live one.
    for r in rows:
        n = len(slot_names(r["provider"])) if r["provider"] in PROVIDERS else 1
        r["label"] = f"{r['provider']}:{r['account']}" + ("*" if r["active"] and n > 1 else "")
    return rows


# ---------- rendering ----------

def cell_label(row):
    return row.get("label") or f"{row['provider']}:{row['account']}"


def renews(w, data):
    """The one time-fact a rotation decision needs: when this window renews. A LOCAL-parse
    figure (codex) also carries how old the reading is — a fresh-looking bar off a two-day-old
    session file is the misread this suffix exists to prevent."""
    at = f"renews {fmt_epoch(w['resets_at'])}" if w.get("resets_at") else ""
    if data.get("as_of") and not data.get("fresh"):
        at += f"{'  ' if at else ''}(as of {fmt_epoch(data['as_of'])})"
    return at


def plain_lines(rows):
    """One line per window / balance / note / error — uncoloured, pipe-friendly."""
    w = max((len(cell_label(r)) for r in rows), default=10)
    out = []
    for r in rows:
        d, lab = r["data"], cell_label(r).ljust(w)
        if d.get("windows"):
            for win in d["windows"]:
                out.append(f"{lab}  {win['label']:<10} {win['pct']:5.1f}%  {renews(win, d)}".rstrip())
        elif d.get("balance") is not None:
            cur = {"USD": "$", "CNY": "¥"}.get(d.get("currency"), (d.get("currency") or "") + " ")
            out.append(f"{lab}  balance {cur}{d['balance']}")
        elif d.get("note"):
            out.append(f"{lab}  {d['note']}"
                       + (f" ({d['console']})" if d.get("console") else ""))
        else:
            out.append(f"{lab}  ERROR: {d.get('error', '?')}")
    return out


def bar(pct, width):
    filled = max(0, min(width, round(pct / 100 * width)))
    color = GREEN if pct < 60 else (YELLOW if pct < 85 else RED)
    return f"{color}{'█' * filled}{DIM}{'░' * (width - filled)}{OFF}"


def clip(s, width):
    """ANSI-aware hard clip. A posh line longer than the terminal WRAPS, which pushes the
    frame's own top line off screen on the next repaint — so every line is cut to width."""
    if len(re.sub(r"\033\[[0-9;]*m", "", s)) <= width:
        return s
    out, vis = "", 0
    for chunk in re.split(r"(\033\[[0-9;]*m)", s):
        if chunk.startswith("\033"):
            out += chunk
            continue
        out += chunk[:max(0, width - 1 - vis)]
        vis += len(chunk)
        if vis >= width - 1:
            break
    return out + "…" + OFF


def until(epoch, now=None):
    """'in 2h13m' — a countdown moves every frame off the clock alone, so posh stays live
    between polls instead of showing a wall time that never changes."""
    if not epoch:
        return ""
    secs = int(epoch - (time.time() if now is None else now))
    if secs <= 0:
        return "due"
    d, h, m = secs // 86400, secs % 86400 // 3600, secs % 3600 // 60
    return f"in {d}d{h}h" if d else (f"in {h}h{m:02d}m" if h else f"in {m}m")


def posh_lines(rows, cols, polled_at, now=None):
    """The posh frame: one bar per window, the countdown live off the clock."""
    clock = datetime.now().strftime("%H:%M:%S")
    age = int((time.time() if now is None else now) - polled_at)
    head = (f"{BOLD}acct usage{OFF} · {clock} · "
            f"{DIM}polled {age}s ago{OFF}" if age < 90 else
            f"{BOLD}acct usage{OFF} · {clock} · {DIM}polled {age // 60}m ago{OFF}")
    out = [head, ""]
    lab_w = max((len(cell_label(r)) for r in rows), default=16)
    bar_w = max(8, min(34, cols - lab_w - 36))
    for r in rows:
        d = r["data"]
        color = CYAN if r["active"] else DIM
        base = f"{color}{cell_label(r).ljust(lab_w)}{OFF}"   # pad the PLAIN text, then colour
        if d.get("windows"):
            for win in d["windows"]:
                out.append(f"  {base} {win['label']:<9} {bar(win['pct'], bar_w)} "
                           f"{win['pct']:5.1f}%  {DIM}{until(win.get('resets_at'), now)}{OFF}"
                           .rstrip())
        elif d.get("balance") is not None:
            cur = {"USD": "$", "CNY": "¥"}.get(d.get("currency"), (d.get("currency") or "") + " ")
            out.append(f"  {base} {GREEN}balance {cur}{d['balance']}{OFF}")
        elif d.get("note"):
            url = f" {DIM}({d['console']}){OFF}" if d.get("console") else ""
            out.append(f"  {base} {YELLOW}no usage API{OFF} {DIM}· {d['note']}{OFF}{url}")
        else:
            out.append(f"  {base} {RED}{d.get('error', '?')}{OFF}")
    out += ["", f"{DIM}ctrl-c to exit{OFF}"]
    return [clip(l, cols) for l in out]


def run_posh(provider, which, interval):
    polled, rows = 0.0, []
    try:
        while True:
            if time.time() - polled > interval:
                rows, polled = usage_rows(provider, which), time.time()
            cols = shutil.get_terminal_size((100, 40)).columns
            sys.stdout.write("\033[H\033[2J" + "\n".join(posh_lines(rows, cols, polled)))
            sys.stdout.flush()
            time.sleep(1)
    except KeyboardInterrupt:
        sys.stdout.write("\n")


# ---------- doctor ----------

def doctor_lines():
    """Orientation: what is logged in, what acct can switch, what it can read usage for.
    Never prints a key, a token, or a full credential path."""
    out = [f"workspace   {workspace_root()}"]
    for p in PROVIDERS:
        live = live_snapshot(p)
        names = slot_names(p)
        out.append(f"{p:<11} login {'present' if live else 'MISSING'} · "
                   f"{len(names)} slot(s){' ' + ', '.join(names) if names else ''} · "
                   f"active {active(p) or '(none saved — run `acct %s add <name>`)' % p} · "
                   f"slots {slot_dir(p)}")
    for p in USAGE_PROVIDERS:
        if p in PROVIDERS:
            continue
        out.append(f"{p:<11} usage only · key {'present' if opencode_key(p) else 'absent'} "
                   f"(opencode store)")
    return out


# ---------- selftest ----------

def selftest():
    import tempfile
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    # parsers
    ck("zai", parse_zai({"data": {"level": "pro", "limits": [
        {"type": "TOKENS_LIMIT", "unit": 3, "number": 5, "percentage": 12.5,
         "nextResetTime": 1786000000000}]}})["windows"][0] ==
       {"label": "5h", "pct": 12.5, "resets_at": 1786000000})
    ck("zai-empty", "error" in parse_zai({"data": {"limits": []}}))
    ck("deepseek", parse_deepseek({"balance_infos": [{"total_balance": "9.5",
                                                      "currency": "USD"}]})["balance"] == "9.5")
    ck("moonshot", parse_moonshot({"data": {"available_balance": 3}})["currency"] == "CNY")
    ck("kimi-code", parse_kimi_code({"usages": [{"model": "k2", "limit": 100, "used": 25}]})
       ["windows"][0]["pct"] == 25.0)
    ck("oauth-scoped", [w["label"] for w in parse_oauth_limits({"limits": [
        {"kind": "session", "percent": 1}, {"kind": "weekly_all", "percent": 2},
        {"kind": "weekly_scoped", "percent": 3,
         "scope": {"model": {"display_name": "Fable"}}}]})] == ["5h", "7d", "7d fable"])
    ck("statusline", parse_claude_statusline({"rate_limits": {"five_hour":
       {"used_percentage": 7}}})["windows"][0]["label"] == "5h")
    ck("codex-rl", [w["label"] for w in codex_windows_from_rl(
        {"primary": {"used_percent": 5, "window_minutes": 300},
         "secondary": {"used_percent": 9, "window_minutes": 10080}})] == ["5h", "7d"])

    # an EXPIRED stored token must report, never return an empty window set that renders 0%
    exp = claude_usage({"claudeAiOauth": {"accessToken": "x", "expiresAt": 1000}})
    ck("expired-reports", "expired" in exp.get("error", "") and "windows" not in exp)
    ck("no-token-reports", claude_usage({}).get("error") == "no stored token")

    ck("jwt", jwt_claim("a." + base64.urlsafe_b64encode(b'{"sub":"u1"}').decode().rstrip("=")
                        + ".c", "sub") == "u1")
    ck("jwt-garbage", jwt_claim("not-a-jwt", "sub") is None)
    ck("dig", dig({"a": {"b": 1}}, "a", "b") == 1 and dig({"a": 1}, "a", "b") is None)
    ck("until", until(time.time() + 3660).startswith("in 1h") and until(time.time() - 5) == "due")
    ck("clip-short", clip(f"{RED}abc{OFF}", 40) == f"{RED}abc{OFF}")
    ck("clip-ansi-width", len(re.sub(r"\033\[[0-9;]*m", "", clip(f"{RED}{'x' * 90}{OFF}", 20))) == 20)
    # every posh line must fit the frame, or the repaint scrolls its own header off
    _r = [{"provider": "claude", "account": "x", "active": True, "label": "claude:x",
           "data": {"error": "token expired " + "y" * 200}}]
    ck("posh-fits", all(len(re.sub(r"\033\[[0-9;]*m", "", l)) <= 60
                        for l in posh_lines(_r, 60, time.time())))

    # opencode's store holds api entries (`key`) AND oauth ones (`access`, no `key`) — both count
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(json.dumps({"deepseek": {"type": "api", "key": "sk-1"},
                            "xai": {"type": "oauth", "access": "tok", "refresh": "r"}}))
        _store = f.name
    ck("store-api-key", opencode_key("deepseek", _store) == "sk-1")
    ck("store-oauth-access", opencode_key("xai", _store) == "tok")
    ck("store-absent", opencode_key("sakana", _store) is None)
    os.unlink(_store)

    # slot round-trip against a REAL temp provider: save -> ident -> active -> use.
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cred, conf = td / "cred.json", td / "conf.json"
        PROVIDERS["_t"] = {
            "locations": {"credentials": (str(cred), None), "who": (str(conf), "acc")},
            "ident": lambda s: dig(s, "who", "uuid"),
            "who": lambda s: dig(s, "who", "mail"), "expires": lambda s: None}
        os.environ["RBTV_WORKSPACE"] = str(td)
        (td / "rbtv.json").write_text("{}")
        try:
            cred.write_text(json.dumps({"tok": "A"}))
            conf.write_text(json.dumps({"keep": "me", "acc": {"uuid": "u-a", "mail": "a@x"}}))
            save("_t", "a")
            ck("active-a", active("_t") == "a")
            cred.write_text(json.dumps({"tok": "B"}))
            conf.write_text(json.dumps({"keep": "me", "acc": {"uuid": "u-b", "mail": "b@x"}}))
            save("_t", "b")
            ck("active-b", active("_t") == "b")
            cmd_use("_t", "a")
            ck("use-swaps", json.loads(cred.read_text())["tok"] == "A")
            ck("use-keeps-siblings", json.loads(conf.read_text())["keep"] == "me")
            # the outgoing login must be parked, not lost: b's token has to survive the swap
            ck("use-parks-outgoing", read_slot("_t", "b")["credentials"]["tok"] == "B")
            ck("names", slot_names("_t") == ["a", "b"])
            # A provider that is SWITCHABLE but has nothing parked must still print a line.
            # It used to print nothing at all, which read as "not supported" for two
            # providers that were logged in the whole time.
            PROVIDERS["_u"] = dict(PROVIDERS["_t"],
                                   locations={"credentials": (str(cred), None)})
            try:
                import io
                import contextlib
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    cmd_ls()
                out = buf.getvalue()
                ck("ls-names-unparked", "_u" in out and "no slot saved" in out)
                ck("ls-names-parked", "_t:a" in out and "_t:b" in out)
                ck("ls-names-usage-only", "usage only" in out)
            finally:
                del PROVIDERS["_u"]
        finally:
            del PROVIDERS["_t"]
            os.environ.pop("RBTV_WORKSPACE", None)

    print("selftest: " + (f"{len(fails)} FAILED: {', '.join(fails)}" if fails else "all passed"))
    sys.exit(1 if fails else 0)


# ---------- main ----------

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="acct", description=__doc__, add_help=True,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", nargs="*", metavar="[PROVIDER] COMMAND [ARG]",
                    help="ls | add <name> | use <name> | rm <name> --force | "
                         "usage [all|<name>] | providers | doctor")
    ap.add_argument("--posh", action="store_true",
                    help="usage as a live full-screen dashboard with bars and countdowns "
                         "(repaints every second; re-polls every --interval)")
    ap.add_argument("--json", action="store_true", help="machine-readable usage output")
    ap.add_argument("--interval", type=int, default=120,
                    help="--posh provider re-poll seconds (default 120)")
    ap.add_argument("--force", action="store_true", help="confirm `rm` (it costs a re-login)")
    ap.add_argument("--selftest", action="store_true", help="run the offline self-test and exit")
    args = ap.parse_args(argv)

    if args.selftest:
        selftest()
    words = [w for w in args.words if w]
    prov = words.pop(0) if words and (words[0] in PROVIDERS or words[0] in USAGE_PROVIDERS) else None
    cmd = words.pop(0) if words else "ls"
    arg = words.pop(0) if words else None
    # A first word that is neither a provider nor a command is almost always a MISTYPED
    # PROVIDER (`acct nope usage`), and reporting it as an unknown COMMAND sends the reader
    # looking in the wrong half of the grammar. Name both halves and stop.
    if cmd not in COMMANDS:
        sys.exit(f"'{cmd}' is neither a provider nor a command.\n"
                 f"  providers: {', '.join(USAGE_PROVIDERS)}"
                 f"   (switchable: {', '.join(PROVIDERS)})\n"
                 f"  commands:  {', '.join(sorted(COMMANDS))}\n"
                 f"  try:       acct usage   ·   acct {list(PROVIDERS)[0]} ls   ·   acct --help")

    if cmd == "providers":
        print(DOC_PROVIDERS, end="")
    elif cmd == "doctor":
        print("\n".join(doctor_lines()))
    elif cmd == "usage":
        if prov and prov not in USAGE_PROVIDERS:
            sys.exit(f"no usage source for '{prov}' (have: {', '.join(USAGE_PROVIDERS)})")
        if args.posh:
            run_posh(prov, arg, args.interval)
            return
        rows = usage_rows(prov, arg)
        if not rows:
            sys.exit(f"no {prov or ''} account matches '{arg}'".replace("  ", " "))
        print(json.dumps(rows, indent=2) if args.json else "\n".join(plain_lines(rows)))
    elif cmd in ("ls", "list"):
        if prov:
            prov_or_die(prov)
        cmd_ls(prov)
    elif cmd in ("add", "use", "rm"):
        if not prov:
            sys.exit(f"usage: acct <provider> {cmd} <name>   "
                     f"(switchable: {', '.join(PROVIDERS)})")
        prov_or_die(prov)
        if not arg:
            sys.exit(f"usage: acct {prov} {cmd} <name>")
        if cmd == "rm":
            cmd_rm(prov, arg, force=args.force)
        else:
            {"add": cmd_add, "use": cmd_use}[cmd](prov, arg)


if __name__ == "__main__":
    main()
