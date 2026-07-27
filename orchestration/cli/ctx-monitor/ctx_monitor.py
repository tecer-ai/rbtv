#!/usr/bin/env python3
"""ctx-monitor — per-pane agent context / model / last-activity for a tmux team session.

For every pane of a tmux session (or a single pane, or an explicit cwd+harness with no tmux
at all), report the agent running there: harness, model, context-window used %, and the last
activity time — read from each harness's OWN session record on disk (local files only; no
network, no credentials):

  claude    the pane's claude PID is first resolved through the statusline-persisted map
            ~/.claude/rbtv-runtime/session-pids/<sid>.json (written by team-kit's
            statusline-usage.py; pid -> transcript + model + the payload's EXACT
            context_window block — window size is plan-dependent and unknowable from
            outside, so the record's window always wins) -> last main-chain assistant
            `usage` (input + cache_read + cache_creation vs the window; fallback window
            guess: 200k; 1M for the Claude 5 family and "[1m]" ids; RBTV_CONTEXT_WINDOW
            env overrides); model from
            message.model; activity = transcript mtime. Synthetic/zero-usage entries
            (errors, interruptions) are skipped. Unmapped panes fall back to a cwd
            heuristic (source shown as 'transcript~'): transcripts under
            ~/.claude/projects/<munged-cwd>/ whose first timestamp postdates the pane
            process's start, claimed oldest-first in pane-creation order, one pane each;
            RESUMED sessions (transcript predates the process) get a stable session-start-
            order assignment over the recently-written files instead — sibling order can
            still be wrong there, so EVERY heuristic pick carries ambiguous=True (ctx shown
            as ~N%) until the session's next statusline tick pins it exactly. Transcripts
            the pid map assigns to a LIVE pid other than the pane's (another session in
            the same cwd, possibly outside tmux) are never heuristic candidates.
            MODEL is resolved from the pane process's own argv `--model` FIRST when present
            (the one source that cannot belong to another session); the pid-map/transcript
            model only fills in when argv carries no flag. `model_source` names which it
            was (argv | pidmap | transcript | transcript~); a family-level disagreement
            between argv and the matched transcript proves the transcript is another
            session's and sets ambiguous=True plus `model_conflict`.
  codex     newest rollout under ~/.codex/sessions/ whose session_meta cwd matches the
            pane -> last token_count event (last_token_usage.total_tokens /
            model_context_window); model from the last turn_context; activity = file mtime
  opencode  ~/.local/share/opencode/opencode.db opened READ-ONLY: newest session row for
            the cwd -> model; its last assistant message with non-zero tokens -> context
            tokens (total, else input+output+cache) vs a per-model window map; activity =
            that message's time_updated
  kimi      ~/.kimi/sessions/<md5(cwd)>/<newest-session>/wire.jsonl -> last StatusUpdate
            event (context_tokens / max_context_tokens are explicit); activity = file mtime
  any       fallbacks, in order: an argv `--model` flag on the pane's process; a visible
            "N% context left" style TUI footer (tmux capture-pane; those report REMAINING,
            converted to used)

Relation to the orchestration PostToolUse hook (orchestration/hooks/context-monitor.py):
that hook is Claude-Code-only by construction — Claude pipes it hook stdin and it parses
Claude's transcript format; no other harness ever invokes it. This CLI is the harness-
agnostic twin for observing panes FROM OUTSIDE a session. The hook keeps advising the
conductor in-session; teamview imports this module for its per-pane columns.

Usage:
  ctx_monitor.py [session] [--json]                    # every pane (default: session you are in)
  ctx_monitor.py --pane %3 [--json]                    # one pane
  ctx_monitor.py --cwd DIR --harness claude [--json]   # no tmux: query the records directly
  ctx_monitor.py --selftest

Text output is one row per pane: pane  title  harness  model  ctx%  activity  source.
JSON output is a list of the same records with raw numbers. Stdlib only; no install step.
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SHELLS = {"bash", "zsh", "sh", "fish", "dash"}
# Pane commands recognized as AI harnesses (worth resolving records/argv for). Anything else
# still gets a row, with only the command as its harness.
HARNESSES = {"claude", "codex", "opencode", "kimi", "gemini", "aider", "goose", "amp",
             "crush", "droid", "cursor-agent", "copilot"}

CLAUDE_WINDOW = 200_000  # default; overrides below
# Bare model ALIASES (`claude --model opus`) — an alias always names the CURRENT generation of
# that family, which is the Claude 5 family, so each resolves to the same window as its
# versioned id. Matched on the whole normalized string, never as a substring: "opus-4-8" must
# NOT inherit "opus"'s window. Add an alias here only when its current generation is 1M.
CLAUDE_1M_ALIASES = {"fable", "opus", "sonnet"}
# Versioned/long-context ids, matched as substrings ("opus-5" does not occur inside "opus-4-5").
CLAUDE_1M_PATTERNS = ("[1m]", "fable", "sonnet-5", "opus-5")


def normalize_claude_model(model):
    """Model string reduced to its comparable form: lowercased, `claude-` prefix and any
    date suffix dropped ('claude-opus-5' -> 'opus-5', 'opus' -> 'opus')."""
    m = re.sub(r"^claude-", "", (model or "").strip().lower())
    return re.sub(r"-\d{8}$", "", m)


def model_family(model):
    """Family identity an alias and a full id agree on — 'opus' for both `opus` and
    `claude-opus-5`, 'sonnet' for `claude-sonnet-4-5-20250929`. Used to tell a HARMLESS
    alias/id difference from a real disagreement between two sources."""
    return re.split(r"[-@\[]", normalize_claude_model(model))[0]


def claude_window(model):
    """FALLBACK guess only — a pid-map record's `ctx.window` (the plan's real, per-session
    window straight from the statusline payload) always outranks this. Claude 5 family
    (fable-5, sonnet-5 verified via /context 2026-07-24; opus-5 verified via statusline
    ctx.window payloads 2026-07-27) observed running 1M windows, as does any [1m]
    long-context id; the rest 200k. RBTV_CONTEXT_WINDOW overrides everything
    (same env the orchestration hook honors).

    Bare aliases resolve too (issues.md G-4): `claude --model opus` puts the string "opus"
    — not "claude-opus-5" — on the wire and in argv, and matching only versioned ids scored
    those sessions against 200k while reporting a 1M-family model in the same record."""
    env = os.environ.get("RBTV_CONTEXT_WINDOW", "")
    if env.isdigit() and int(env) > 0:
        return int(env)
    m = (model or "").strip().lower()
    if normalize_claude_model(m) in CLAUDE_1M_ALIASES:
        return 1_000_000
    if any(p in m for p in CLAUDE_1M_PATTERNS):
        return 1_000_000
    return CLAUDE_WINDOW
# opencode context window by model-id substring (first match wins); its DB carries no window.
OPENCODE_WINDOWS = [("deepseek-v4", 262_144), ("deepseek", 131_072), ("glm", 204_800),
                    ("kimi", 262_144), ("gpt", 272_000), ("claude", 200_000)]
OPENCODE_DEFAULT_WINDOW = 200_000

# TUI footers that expose context REMAINING (converted to used% by the caller).
TUI_CTX_REMAINING = [
    re.compile(r"(\d{1,3})\s*%\s*context\s*left", re.I),                 # codex
    re.compile(r"context\s*low\s*\((\d{1,3})\s*%\s*remaining\)", re.I),  # claude low warning
    re.compile(r"until\s*auto-?compact\s*:?\s*(\d{1,3})\s*%", re.I),     # claude verbose
    re.compile(r"(\d{1,3})\s*%\s*(?:context\s*)?remaining", re.I),
]


def munge_cwd(cwd):
    """Claude Code project-dir name for a cwd (every non-alnum char becomes '-')."""
    return re.sub(r"[^A-Za-z0-9]", "-", cwd or "")


def tail_json_lines(path, max_bytes=250_000):
    """Parsed JSON objects from the last max_bytes of a JSONL file (truncated first line
    and malformed lines are skipped)."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            fh.seek(max(0, size - max_bytes))
            text = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def pct(used, window):
    if not window:
        return None
    return round(min(100.0, 100.0 * used / window), 1)


# ---------- per-harness record readers (pure local reads; each returns a partial record) ----------

def session_start_epoch(path):
    """Epoch of the first timestamp among a transcript's head lines (None when absent —
    the head may open with summary/snapshot lines that carry no timestamp)."""
    try:
        head = open(path, "rb").read(8192).decode("utf-8", errors="replace")
    except OSError:
        return None
    for line in head.splitlines()[:20]:
        try:
            ts = json.loads(line).get("timestamp")
            if ts:
                return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except (json.JSONDecodeError, ValueError, AttributeError):
            continue
    return None


def pidmap_entries(runtime_root=None):
    """All {pid, transcript, ts} records of the statusline's session-pids map
    (exact pid->session mapping; see team-kit/statusline-usage.py)."""
    d = (Path(runtime_root) if runtime_root
         else Path.home() / ".claude" / "rbtv-runtime") / "session-pids"
    out = []
    try:
        files = list(d.glob("*.json"))
    except OSError:
        return out
    for f in files:
        try:
            o = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if o.get("transcript") and Path(o["transcript"]).is_file():
            out.append(o)
    return out


def claude_pidmap_record(pid, runtime_root=None, entries=None):
    """Full record for a claude pid (newest ts wins); None when unmapped. Carries
    transcript, and — when the statusline payload provided them — the exact model and
    ctx {window, tokens, pct}."""
    best = None
    for o in (entries if entries is not None else pidmap_entries(runtime_root)):
        if str(o.get("pid")) == str(pid) and (best is None or o.get("ts", 0) > best.get("ts", 0)):
            best = o
    return best


TAIL_BYTES = 250_000        # normal read: the pane agent's own last turn is near the end
TAIL_BYTES_WIDE = 8_000_000  # widened read, only when a sub-agent run buried that turn


def last_usage_entry(objs, prefer_model=None):
    """(model, tokens) of the last REAL assistant usage among `objs`, plus whether it had to
    fall back off `prefer_model`. Skips sidechains and the synthetic/zero-usage entries
    Claude writes for errors and interruptions.

    `prefer_model` exists because a sub-agent's turns are appended to its PARENT's
    transcript carrying isSidechain=false, the same sessionId, and the SUB-agent's model —
    so the plain last entry is often another agent's context, not the pane agent's
    (observed 2026-07-27: a fable seat's pane read 427k tokens that belonged to an opus
    sub-agent running inside it). Given the pane's own model, the last entry of THAT model
    family wins."""
    fallback = None
    for obj in reversed(objs):
        if obj.get("isSidechain") is True:
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        u = msg.get("usage")
        if not isinstance(u, dict) or u.get("input_tokens") is None:
            continue
        model = msg.get("model") or ""
        used = (int(u.get("input_tokens") or 0) + int(u.get("cache_read_input_tokens") or 0)
                + int(u.get("cache_creation_input_tokens") or 0))
        if model == "<synthetic>" or used == 0:
            continue
        if prefer_model and model_family(model) != model_family(prefer_model):
            fallback = fallback if fallback is not None else (model, used)
            continue
        return (model, used), False
    return fallback, True


def parse_claude_transcript(f, prefer_model=None):
    """Record for the transcript's last assistant usage — the pane agent's own when
    `prefer_model` names it (see last_usage_entry). A sub-agent run can push the pane
    agent's last turn out of the normal tail, so a miss re-reads a much larger tail once
    before settling for another agent's entry."""
    hit, unmatched = last_usage_entry(tail_json_lines(f, TAIL_BYTES), prefer_model)
    if prefer_model and unmatched and os.path.getsize(f) > TAIL_BYTES:
        wide, wide_unmatched = last_usage_entry(tail_json_lines(f, TAIL_BYTES_WIDE),
                                                prefer_model)
        if wide is not None and not wide_unmatched:
            hit, unmatched = wide, False
    if hit is None:
        return {"file": str(f)}
    model, used = hit
    window = claude_window(model)
    return {"model": model, "model_source": "transcript", "ctx_pct": pct(used, window),
            "ctx_tokens": used, "window": window, "as_of": int(f.stat().st_mtime),
            "source": "transcript", "file": str(f)}


def claude_info(cwd, projects_root=None, after=None, exclude=(), pid=None,
                runtime_root=None, prefer_model=None):
    """Source order: the pid map (statusline-persisted, EXACT) -> start-time pairing
    (`after` = the pane process's start epoch; only transcripts started after it qualify,
    claimed oldest-first via `exclude`) -> stable session-start-order assignment (resumed
    sessions predate their process, so time pairing cannot bind them; start order at least
    keeps claims STABLE across frames instead of churning with mtime). Heuristic picks are
    marked source 'transcript~', and `ambiguous: True` when more than one candidate
    existed — the pid map resolves it exactly as soon as that session's statusline next
    fires."""
    if pid:
        mapped = claude_pidmap_record(pid, runtime_root)
        if mapped:
            rec = parse_claude_transcript(Path(mapped["transcript"]),
                                          prefer_model or mapped.get("model"))
            if mapped.get("model"):
                rec["model"], rec["model_source"] = mapped["model"], "pidmap"
            ctx = mapped.get("ctx") or {}
            if ctx.get("window"):  # the plan's REAL window (statusline payload) beats guesses
                rec["window"], rec["window_exact"] = int(ctx["window"]), True
                tokens = rec.get("ctx_tokens") or ctx.get("tokens")
                rec["ctx_tokens"] = tokens
                rec["ctx_pct"] = (pct(tokens, rec["window"]) if tokens
                                  else (float(ctx["pct"]) if ctx.get("pct") is not None
                                        else rec.get("ctx_pct")))
            return rec
    root = Path(projects_root) if projects_root else Path.home() / ".claude" / "projects"
    proj = root / munge_cwd(cwd)
    try:
        files = sorted(proj.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return {}
    files = [f for f in files if str(f) not in exclude]
    if not files:
        return {}
    f = None
    started = [(session_start_epoch(p), p) for p in files]
    if after:
        cands = [(s, p) for s, p in started if s and s >= after - 5]
        if cands:
            f = min(cands)[1]  # oldest-starting session that postdates the process
    if f is None:
        # resumed / unknown-start: stable assignment by session start order, over the
        # RECENTLY-WRITTEN files only (a live session's transcript stays fresh; ancient
        # dead transcripts must not enter the pool)
        now = time.time()
        recent = [(s, p) for s, p in started if now - p.stat().st_mtime <= 3600]
        if recent:
            f = min((s if s is not None else float("inf"), p) for s, p in recent)[1]
        else:
            f = files[0]  # nothing recent: newest by mtime
    rec = parse_claude_transcript(f, prefer_model)
    if rec.get("source"):
        rec["source"] = "transcript~"  # heuristic pick — not pid-verified
        rec["model_source"] = "transcript~"
        # A heuristic pick is a GUESS about which session this pane owns, even when only one
        # candidate existed (the pane may own none of them — issues.md G-16 reported a
        # single-candidate pick as `ambiguous: false` while naming another seat's model).
        # Certainty comes from the pid map, never from candidate scarcity.
        rec["ambiguous"] = True
    return rec


def codex_info(cwd, sessions_root=None):
    root = Path(sessions_root) if sessions_root else Path.home() / ".codex" / "sessions"
    try:
        files = sorted(root.glob("*/*/*/rollout-*.jsonl"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return {}
    for f in files[:10]:
        try:
            head = open(f, "rb").read(4096).decode("utf-8", errors="replace")
        except OSError:
            continue
        if json.dumps(cwd)[1:-1] not in head:  # session_meta payload carries "cwd":"<path>"
            continue
        model, used, window = "", None, None
        for obj in tail_json_lines(f):
            pay = obj.get("payload") or {}
            info = pay.get("info") if pay.get("type") == "token_count" else None
            if isinstance(info, dict):
                lt = info.get("last_token_usage") or info.get("total_token_usage") or {}
                if lt.get("total_tokens") is not None and info.get("model_context_window"):
                    used, window = int(lt["total_tokens"]), int(info["model_context_window"])
            if "turn_context" in (obj.get("type"), pay.get("type")) and pay.get("model"):
                model = pay["model"]
        if used is not None or model:
            return {"model": model, "ctx_pct": pct(used, window) if used is not None else None,
                    "ctx_tokens": used, "window": window,
                    "as_of": int(f.stat().st_mtime), "source": "rollout"}
    return {}


def opencode_window(model_id):
    m = (model_id or "").lower()
    for key, win in OPENCODE_WINDOWS:
        if key in m:
            return win
    return OPENCODE_DEFAULT_WINDOW


def opencode_info(cwd, db_path=None):
    db_file = Path(db_path) if db_path else (Path.home() / ".local" / "share" / "opencode"
                                             / "opencode.db")
    if not db_file.is_file():
        return {}
    try:
        db = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        try:
            row = db.execute(
                "SELECT id, model, time_updated FROM session WHERE directory = ? "
                "ORDER BY time_updated DESC LIMIT 1", (cwd,)).fetchone()
            if not row:
                return {}
            sid, model_json, ts = row
            try:
                model = (json.loads(model_json) or {}).get("id", "")
            except (json.JSONDecodeError, TypeError):
                model = ""
            out = {"model": model, "as_of": int(ts / 1000) if ts else None, "source": "db"}
            for data, mts in db.execute(
                    "SELECT data, time_updated FROM message WHERE session_id = ? "
                    "ORDER BY time_updated DESC LIMIT 50", (sid,)):
                try:
                    o = json.loads(data)
                except json.JSONDecodeError:
                    continue
                tok = o.get("tokens") or {}
                cache = tok.get("cache") or {}
                used = tok.get("total") or (int(tok.get("input") or 0)
                                            + int(tok.get("output") or 0)
                                            + int(cache.get("read") or 0)
                                            + int(cache.get("write") or 0))
                if o.get("role") == "assistant" and used:
                    window = opencode_window(o.get("modelID") or model)
                    out.update({"ctx_pct": pct(used, window), "ctx_tokens": used,
                                "window": window,
                                "as_of": int(mts / 1000) if mts else out["as_of"]})
                    break
            return out
        finally:
            db.close()
    except sqlite3.Error:
        return {}


def kimi_info(cwd, sessions_root=None):
    root = Path(sessions_root) if sessions_root else Path.home() / ".kimi" / "sessions"
    proj = root / hashlib.md5((cwd or "").encode("utf-8")).hexdigest()
    try:
        wires = sorted(proj.glob("*/wire.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return {}
    for f in wires[:3]:
        for obj in reversed(tail_json_lines(f)):
            msg = obj.get("message") or {}
            pay = msg.get("payload") or {}
            if msg.get("type") == "StatusUpdate" and pay.get("max_context_tokens"):
                used, window = int(pay.get("context_tokens") or 0), int(pay["max_context_tokens"])
                return {"model": "", "ctx_pct": pct(used, window), "ctx_tokens": used,
                        "window": window, "as_of": int(f.stat().st_mtime), "source": "wire"}
    return {}


# ---------- generic fallbacks ----------

def ps_args_table():
    """pid -> (ppid, args) for every process — one ps call, shared across panes."""
    out = {}
    r = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        parts = ln.split(None, 2)
        if len(parts) >= 2:
            out[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else "")
    return out


def pane_agent_proc(pane_pid, cmd, procs):
    """(pid, argv) of the pane's foreground harness: the pane root process or its nearest
    descendant whose executable name matches tmux's pane_current_command."""
    kids = {}
    for pid, (ppid, _a) in procs.items():
        kids.setdefault(ppid, []).append(pid)
    queue = [str(pane_pid)]
    while queue:
        pid = queue.pop(0)
        args = procs.get(pid, ("", ""))[1]
        heads = [os.path.basename(t) for t in args.split()[:2]]
        if any(h == cmd for h in heads):
            return pid, args
        queue.extend(kids.get(pid, []))
    return None, ""


def proc_starts():
    """pid -> process start epoch (one ps call; drives same-cwd transcript pairing)."""
    now = time.time()
    out = {}
    r = subprocess.run(["ps", "-eo", "pid=,etimes="], capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        parts = ln.split()
        if len(parts) == 2 and parts[1].isdigit():
            out[parts[0]] = now - int(parts[1])
    return out


def argv_model(args):
    m = re.search(r"(?:--model|-m)[= ]+(\S+)", args or "")
    return m.group(1).rsplit("/", 1)[-1] if m else ""  # opencode passes provider/model


def parse_tui_ctx(text):
    """Context used% from a visible 'N% context left' style footer (None when absent)."""
    best = None
    for rx in TUI_CTX_REMAINING:
        for m in rx.finditer(text or ""):
            best = m  # keep the LAST match — footers sit at the bottom
        if best:
            remaining = max(0, min(100, int(best.group(1))))
            return float(100 - remaining)
    return None


def capture_pane(pane_id):
    r = subprocess.run(["tmux", "capture-pane", "-p", "-t", pane_id],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


READERS = {"claude": claude_info, "codex": codex_info,
           "opencode": opencode_info, "kimi": kimi_info}


def apply_argv_model(rec, amodel):
    """Let the pane's OWN process argv decide the model (issues.md G-16).

    A transcript can belong to another session — with no `session-pids` record the pane ->
    transcript match is a guess, and a wrong guess reported a fable seat as opus while
    claiming `ambiguous: false`. `--model` in the pane process's argv is the one source that
    CANNOT be another session's, so it outranks every record-derived model. When the two
    disagree by family the matched transcript is provably not this pane's: keep the numbers
    (they are all there is) but mark them ambiguous and record what the transcript claimed.
    The window is re-derived from the authoritative model unless it came from the statusline
    payload — a record must never carry a model and a window that describe different models
    (the G-4 symptom)."""
    if not amodel:
        return rec
    tmodel = rec.get("model") or ""
    rec["model"], rec["model_source"] = amodel, "argv"
    if tmodel and model_family(tmodel) != model_family(amodel):
        rec["model_conflict"] = tmodel
        rec["ambiguous"] = True
    if not rec.get("window_exact"):
        rec["window"] = claude_window(amodel)
        if rec.get("ctx_tokens"):
            rec["ctx_pct"] = pct(rec["ctx_tokens"], rec["window"])
    return rec


def agent_info(harness, cwd, pane_id=None, pane_pid=None, procs=None,
               after=None, exclude=()):
    """Full record for one agent: the pane process's own argv --model (authoritative for
    claude), the harness record, then a TUI scrape. `after`/`exclude` feed claude's same-cwd
    transcript disambiguation."""
    rec = {"harness": harness, "model": "", "model_source": "", "ctx_pct": None,
           "ctx_tokens": None, "window": None, "as_of": None, "source": "", "file": "",
           "ambiguous": False}
    if harness == "claude":
        apid, aargs = None, ""
        if pane_pid:
            apid, aargs = pane_agent_proc(pane_pid, "claude",
                                          procs if procs is not None else ps_args_table())
        amodel = argv_model(aargs)  # resolved FIRST: it also picks the pane agent's own
        #                             usage entry out of a transcript shared with sub-agents
        rec.update({k: v for k, v in claude_info(cwd, after=after, exclude=exclude,
                                                 pid=apid or pane_pid,
                                                 prefer_model=amodel).items()
                    if v not in (None, "")})
        apply_argv_model(rec, amodel)
    elif harness in READERS:
        rec.update({k: v for k, v in READERS[harness](cwd).items() if v not in (None, "")})
    if not rec["model"] and pane_pid and harness in HARNESSES:
        _pid, args = pane_agent_proc(pane_pid, harness,
                                     procs if procs is not None else ps_args_table())
        rec["model"] = argv_model(args)
        if rec["model"] and not rec["source"]:
            rec["source"] = "argv"
    if rec["ctx_pct"] is None and pane_id and harness in HARNESSES:
        tui = parse_tui_ctx(capture_pane(pane_id))
        if tui is not None:
            rec.update({"ctx_pct": tui, "source": rec["source"] or "tui"})
    return rec


# ---------- tmux enumeration ----------

def tmux_lines(*a):
    r = subprocess.run(["tmux", *a], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def current_session():
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return None
    out = tmux_lines("display-message", "-p", "-t", pane, "#{session_name}")
    return out[0] if out else None


def list_panes(session=None, pane=None):
    """[{pane_id, window, title, cmd, pid, cwd}] for a session (or one pane)."""
    fmt = ("#{pane_id}\t#{window_index}\t#{pane_pid}\t#{pane_current_command}"
           "\t#{pane_current_path}\t#{pane_title}")
    args = (["display-message", "-p", "-t", pane, fmt] if pane
            else ["list-panes", "-s", "-t", session, "-F", fmt])
    out = []
    for ln in tmux_lines(*args):
        parts = ln.split("\t", 5)
        if len(parts) < 6:
            continue
        pid_, win, ppid, cmd, cwd, title = parts
        out.append({"pane_id": pid_, "window": win, "pid": ppid, "cmd": cmd,
                    "cwd": cwd, "title": title})
    return out


def pane_records(session=None, pane=None):
    """One full record per pane — the module-level API teamview consumes. Panes are
    processed in creation order (numeric pane id) so same-cwd claude panes claim their
    transcripts oldest-first; output keeps tmux listing order."""
    panes = list_panes(session, pane)
    any_harness = any(p["cmd"] in HARNESSES for p in panes)
    procs = ps_args_table() if any_harness else {}
    has_claude = any(p["cmd"] == "claude" for p in panes)
    starts = proc_starts() if has_claude else {}
    pmap = pidmap_entries() if has_claude else []
    claimed, results = set(), {}

    def pane_num(p):
        try:
            return int(p["pane_id"].lstrip("%"))
        except ValueError:
            return 1 << 30
    for p in sorted(panes, key=pane_num):
        rec = {"pane_id": p["pane_id"], "window": p["window"], "title": p["title"],
               "harness": "" if p["cmd"] in SHELLS else p["cmd"], "shell": p["cmd"] in SHELLS,
               "model": "", "model_source": "", "model_conflict": "", "ctx_pct": None,
               "ctx_tokens": None, "window_tokens": None,
               "as_of": None, "source": "", "ambiguous": False}
        if p["cmd"] in HARNESSES:
            after, exclude = None, claimed
            if p["cmd"] == "claude":
                apid, _args = pane_agent_proc(p["pid"], "claude", procs)
                after = starts.get(apid or p["pid"])
                # a transcript mapped to a LIVE pid other than this pane's belongs to
                # another session (possibly outside tmux) — never a heuristic candidate
                foreign = {e["transcript"] for e in pmap
                           if str(e.get("pid")) != str(apid or p["pid"])
                           and str(e.get("pid")) in procs}
                exclude = claimed | foreign
            info = agent_info(p["cmd"], p["cwd"], p["pane_id"], p["pid"], procs,
                              after=after, exclude=exclude)
            if info.get("file"):
                claimed.add(info["file"])
            rec.update({"model": info["model"], "model_source": info.get("model_source", ""),
                        "model_conflict": info.get("model_conflict", ""),
                        "ctx_pct": info["ctx_pct"],
                        "ctx_tokens": info["ctx_tokens"], "window_tokens": info["window"],
                        "as_of": info["as_of"], "source": info["source"],
                        "ambiguous": bool(info.get("ambiguous"))})
        results[p["pane_id"]] = rec
    return [results[p["pane_id"]] for p in panes]


# ---------- output ----------

def short_model(model):
    m = re.sub(r"^claude-", "", model or "")
    return re.sub(r"-\d{8}$", "", m)[:14]


def fmt_age(as_of, now=None):
    if not as_of:
        return ""
    secs = max(0, (now if now is not None else time.time()) - as_of)
    if secs < 90:
        return "now"
    if secs < 3600:
        return f"{int(secs // 60)}m"
    if secs < 86400:
        return f"{int(secs // 3600)}h{int(secs % 3600 // 60):02d}m"
    return f"{int(secs // 86400)}d{int(secs % 86400 // 3600)}h"


def render_rows(records):
    hdr = ("pane", "win", "title", "harness", "model", "ctx", "activity", "source")
    rows = [hdr]
    for r in records:
        ctx = f"{r['ctx_pct']:.0f}%" if r["ctx_pct"] is not None else "-"
        if r.get("ctx_tokens") and r.get("window_tokens"):
            ctx += f" ({r['ctx_tokens'] // 1000}k/{r['window_tokens'] // 1000}k)"
        if ctx != "-" and r.get("ambiguous"):
            ctx = "~" + ctx  # pane-transcript match uncertain until its statusline fires
        rows.append((r["pane_id"], r["window"], (r["title"] or "")[:24],
                     r["harness"] or "-", short_model(r["model"]) or "-", ctx,
                     fmt_age(r["as_of"]) or "-", r["source"] or "-"))
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(hdr))]
    return [ "  ".join(str(c).ljust(w) for c, w in zip(row, widths)).rstrip()
             for row in rows]


# ---------- selftest ----------

def cmd_selftest():
    import tempfile
    failures = []

    def check(name, cond):
        print(("ok  " if cond else "FAIL") + f"  {name}")
        if not cond:
            failures.append(name)

    check("munge: non-alnum -> dashes",
          munge_cwd("/home/x/a.b_c d") == "-home-x-a-b-c-d")
    check("argv model: --model / -m / provider-path / absent",
          (argv_model("claude --model opus --effort high"), argv_model("codex -m gpt-5"),
           argv_model("opencode --model deepseek/deepseek-v4-pro"), argv_model("claude"))
          == ("opus", "gpt-5", "deepseek-v4-pro", ""))
    check("tui ctx: codex 'context left' converts remaining->used; absent -> None",
          parse_tui_ctx("stuff\n72% context left\n") == 28.0
          and parse_tui_ctx("Context low (9% remaining)") == 91.0
          and parse_tui_ctx("nothing here") is None)
    check("age: now / minutes / hours / days",
          (fmt_age(1000, now=1050), fmt_age(1000, now=1000 + 300),
           fmt_age(1000, now=1000 + 7300), fmt_age(1000, now=1000 + 90000), fmt_age(None))
          == ("now", "5m", "2h01m", "1d1h", ""))
    check("model shortening", (short_model("claude-opus-4-8"),
                               short_model("claude-sonnet-4-5-20250929"))
          == ("opus-4-8", "sonnet-4-5"))

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cwd = "/work/agent-a"
        proj = td / "projects" / munge_cwd(cwd)
        proj.mkdir(parents=True)
        lines = [
            {"type": "assistant", "isSidechain": True,
             "message": {"model": "claude-x", "usage": {"input_tokens": 999_999}}},
            {"type": "assistant",
             "message": {"model": "claude-opus-4-8",
                         "usage": {"input_tokens": 2, "cache_read_input_tokens": 88_000,
                                   "cache_creation_input_tokens": 4_000}}},
            {"type": "progress"},
        ]
        (proj / "s1.jsonl").write_text("\n".join(json.dumps(l) for l in lines))
        c = claude_info(cwd, projects_root=td / "projects")
        check("claude: last main-chain usage, sidechain skipped, 200k window",
              c.get("model") == "claude-opus-4-8" and c.get("ctx_tokens") == 92_002
              and c.get("ctx_pct") == 46.0 and c.get("source") == "transcript~")
        check("claude: a SINGLE-candidate heuristic pick is still a guess -> ambiguous (G-16)",
              c.get("ambiguous") is True and c.get("model_source") == "transcript~")
        # A sub-agent's turns land in the PARENT's transcript with isSidechain=false and the
        # sub-agent's own model: without prefer_model the pane reads the sub-agent's context.
        sub = proj / "sub.jsonl"
        sub.write_text("\n".join(json.dumps(l) for l in [
            {"type": "assistant", "message": {"model": "claude-fable-5",
                                              "usage": {"input_tokens": 40_000}}},
            {"type": "assistant", "message": {"model": "claude-opus-5",
                                              "usage": {"input_tokens": 900_000}}}]))
        check("claude: prefer_model picks the PANE agent's own turn out of a transcript "
              "shared with a sub-agent on another model",
              parse_claude_transcript(sub)["ctx_tokens"] == 900_000
              and parse_claude_transcript(sub, "fable")["ctx_tokens"] == 40_000
              and parse_claude_transcript(sub, "claude-fable-5")["ctx_tokens"] == 40_000
              and parse_claude_transcript(sub, "opus")["ctx_tokens"] == 900_000)
        check("claude: prefer_model with NO matching turn falls back, flagged unmatched",
              parse_claude_transcript(sub, "sonnet")["ctx_tokens"] == 900_000
              and last_usage_entry([json.loads(l) for l in sub.read_text().splitlines()],
                                   "sonnet")[1] is True)
        sub.unlink()
        check("claude: unknown cwd -> {}", claude_info("/nope", projects_root=td / "projects") == {})
        (proj / "s1.jsonl").write_text((proj / "s1.jsonl").read_text() + "\n" + json.dumps(
            {"type": "assistant", "message": {"model": "<synthetic>",
                                              "usage": {"input_tokens": 0}}}))
        check("claude: trailing synthetic/zero-usage entry skipped",
              claude_info(cwd, projects_root=td / "projects").get("ctx_tokens") == 92_002)

        # same-cwd disambiguation: two sessions, started at t=100 and t=200; the newer one
        # has the fresher mtime. A pane started at t=90 claims the OLDEST postdating
        # transcript; a sibling with it excluded gets the next; a pane started at t=150
        # skips straight to the second; no start info -> newest mtime.
        def mk_transcript(name, start_epoch, tokens):
            p = proj / name
            iso = datetime.fromtimestamp(start_epoch).astimezone().isoformat()
            p.write_text("\n".join(json.dumps(l) for l in [
                {"type": "user", "timestamp": iso},
                {"type": "assistant", "message": {"model": "claude-opus-4-8",
                                                  "usage": {"input_tokens": tokens}}}]))
            return p
        (proj / "s1.jsonl").unlink()
        t1 = mk_transcript("t1.jsonl", 1000, 111)
        t2 = mk_transcript("t2.jsonl", 5000, 222)
        os.utime(t1, (6000, 6000)), os.utime(t2, (7000, 7000))
        check("claude same-cwd: oldest postdating start wins; exclude claims; late start skips",
              claude_info(cwd, projects_root=td / "projects", after=900)["ctx_tokens"] == 111
              and claude_info(cwd, projects_root=td / "projects", after=900,
                              exclude={str(t1)})["ctx_tokens"] == 222
              and claude_info(cwd, projects_root=td / "projects", after=3000)["ctx_tokens"] == 222
              and claude_info(cwd, projects_root=td / "projects")["ctx_tokens"] == 222)
        check("claude resumed session, no recent writes -> newest-mtime fallback + ambiguous",
              claude_info(cwd, projects_root=td / "projects", after=99_000)["ctx_tokens"] == 222
              and claude_info(cwd, projects_root=td / "projects",
                              after=99_000).get("ambiguous") is True)
        now = time.time()
        os.utime(t1, (now - 100, now - 100)), os.utime(t2, (now - 50, now - 50))
        check("claude resumed session, recent writes -> STABLE session-start-order claims",
              claude_info(cwd, projects_root=td / "projects", after=99_000)["ctx_tokens"] == 111
              and claude_info(cwd, projects_root=td / "projects", after=99_000,
                              exclude={str(t1)})["ctx_tokens"] == 222)
        os.utime(t1, (6000, 6000)), os.utime(t2, (7000, 7000))

        pids = td / "rt" / "session-pids"
        pids.mkdir(parents=True)
        (pids / "sid-a.json").write_text(json.dumps(
            {"pid": 77, "transcript": str(t1), "ts": 5}))
        (pids / "sid-b.json").write_text(json.dumps(
            {"pid": 77, "transcript": str(t2), "ts": 9, "model": "claude-sonnet-5",
             "ctx": {"window": 1_000_000, "tokens": None, "pct": 13}}))
        m = claude_info(cwd, projects_root=td / "projects", after=99_000, pid=77,
                        runtime_root=td / "rt")
        check("claude pid map: exact transcript beats every heuristic; newest ts wins",
              m.get("ctx_tokens") == 222 and m.get("source") == "transcript"
              and claude_info(cwd, projects_root=td / "projects", pid=1,
                              runtime_root=td / "rt").get("source") == "transcript~")
        check("claude pid map: record's REAL window + model override transcript guesses",
              m.get("window") == 1_000_000 and m.get("model") == "claude-sonnet-5"
              and m.get("ctx_pct") == round(100 * 222 / 1_000_000, 1))
        (pids / "sid-gone.json").write_text(json.dumps(
            {"pid": 78, "transcript": str(td / "nope.jsonl"), "ts": 1}))
        ents = pidmap_entries(td / "rt")
        check("pid map entries: missing-transcript records dropped; live ones listed",
              {e["pid"] for e in ents} == {77}
              and claude_pidmap_record(77, entries=ents)["transcript"] == str(t2))

        cx = td / "codex" / "2026" / "07" / "24"
        cx.mkdir(parents=True)
        (cx / "rollout-1.jsonl").write_text("\n".join(json.dumps(l) for l in [
            {"type": "session_meta", "payload": {"cwd": cwd}},
            {"type": "turn_context", "payload": {"cwd": cwd, "model": "gpt-5.1-codex"}},
            {"type": "event_msg", "payload": {"type": "token_count", "info": {
                "last_token_usage": {"total_tokens": 31_108},
                "model_context_window": 258_400}}},
        ]))
        k = codex_info(cwd, sessions_root=td / "codex")
        check("codex: cwd-matched rollout -> model + ctx from window",
              k.get("model") == "gpt-5.1-codex" and k.get("ctx_pct") == 12.0
              and k.get("source") == "rollout")
        check("codex: other cwd -> {}", codex_info("/nope", sessions_root=td / "codex") == {})

        db_path = td / "oc.db"
        db = sqlite3.connect(db_path)
        db.execute("CREATE TABLE session (id TEXT, directory TEXT, model TEXT, time_updated INT)")
        db.execute("CREATE TABLE message (id TEXT, session_id TEXT, time_updated INT, data TEXT)")
        db.execute("INSERT INTO session VALUES ('s1', ?, ?, 2000)",
                   (cwd, json.dumps({"id": "deepseek-v4-pro"})))
        db.execute("INSERT INTO message VALUES ('m2', 's1', 2000, ?)",
                   (json.dumps({"role": "assistant", "tokens": {
                       "input": 0, "output": 0, "cache": {"read": 0, "write": 0}}}),))
        db.execute("INSERT INTO message VALUES ('m1', 's1', 1500, ?)",
                   (json.dumps({"role": "assistant", "modelID": "deepseek-v4-pro",
                                "tokens": {"total": 169_417, "input": 184, "output": 257,
                                           "cache": {"read": 168_960, "write": 0}}}),))
        db.commit()
        db.close()
        oc = opencode_info(cwd, db_path=db_path)
        check("opencode: newest session's last non-zero-token assistant msg -> ctx",
              oc.get("model") == "deepseek-v4-pro" and oc.get("ctx_tokens") == 169_417
              and oc.get("ctx_pct") == round(100 * 169_417 / 262_144, 1)
              and oc.get("source") == "db")

        kd = td / "kimi" / hashlib.md5(cwd.encode()).hexdigest() / "sess-1"
        kd.mkdir(parents=True)
        (kd / "wire.jsonl").write_text("\n".join(json.dumps(l) for l in [
            {"message": {"type": "TurnBegin", "payload": {}}},
            {"message": {"type": "StatusUpdate", "payload": {
                "context_tokens": 21_198, "max_context_tokens": 262_144}}},
        ]))
        km = kimi_info(cwd, sessions_root=td / "kimi")
        check("kimi: StatusUpdate context_tokens/max -> ctx",
              km.get("ctx_pct") == round(100 * 21_198 / 262_144, 1)
              and km.get("source") == "wire")

    procs = {"10": ("1", "bash"), "20": ("10", "claude --model opus x"),
             "30": ("10", "python3 something.py")}
    check("pane argv walk: descendant matching pane_current_command",
          pane_agent_proc("10", "claude", procs) == ("20", "claude --model opus x")
          and pane_agent_proc("10", "codex", procs) == (None, ""))
    check("windows: opencode model map first-match + default",
          (opencode_window("deepseek-v4-pro"), opencode_window("deepseek-chat"),
           opencode_window("mystery")) == (262_144, 131_072, OPENCODE_DEFAULT_WINDOW))
    check("windows: claude 200k default; 5-family/[1m] -> 1M",
          (claude_window("claude-opus-4-8"), claude_window("claude-fable-5"),
           claude_window("claude-sonnet-5"), claude_window("claude-sonnet-4-5[1m]"))
          == (200_000, 1_000_000, 1_000_000, 1_000_000))
    # G-4: `claude --model opus` puts a BARE alias on the wire; matching only versioned ids
    # scored those sessions against 200k. Bare aliases resolve, versioned 200k ids still do.
    check("windows: BARE aliases resolve (G-4); versioned 200k ids unaffected",
          (claude_window("opus"), claude_window("sonnet"), claude_window("fable"),
           claude_window("claude-opus"), claude_window("OPUS"))
          == (1_000_000,) * 5
          and (claude_window("opus-4-8"), claude_window("claude-opus-4-8"),
               claude_window("claude-sonnet-4-5-20250929"), claude_window("haiku"),
               claude_window("")) == (200_000,) * 5)
    check("model_family: alias and full id agree; different families do not",
          (model_family("opus"), model_family("claude-opus-5"),
           model_family("claude-sonnet-4-5-20250929"), model_family("fable"))
          == ("opus", "opus", "sonnet", "fable")
          and model_family("fable") != model_family("claude-opus-5"))
    # G-16: argv beats a transcript-derived model, re-derives the window to match it, and a
    # family disagreement proves the matched transcript belongs to another session.
    conflict = apply_argv_model({"model": "claude-opus-5", "model_source": "transcript~",
                                 "ctx_tokens": 400_000, "ctx_pct": 200.0, "window": 200_000,
                                 "ambiguous": False}, "fable")
    agree = apply_argv_model({"model": "claude-opus-5", "model_source": "transcript~",
                              "ctx_tokens": 100_000, "window": 200_000, "ambiguous": False},
                             "opus")
    exact = apply_argv_model({"model": "claude-sonnet-5", "model_source": "pidmap",
                              "ctx_tokens": 100_000, "window": 1_000_000,
                              "window_exact": True, "ambiguous": False}, "sonnet")
    check("argv model: outranks transcript, window re-derived, conflict -> ambiguous (G-16)",
          (conflict["model"], conflict["model_source"], conflict["window"],
           conflict["ambiguous"], conflict["model_conflict"])
          == ("fable", "argv", 1_000_000, True, "claude-opus-5")
          and conflict["ctx_pct"] == 40.0)
    check("argv model: same family is no conflict; statusline window never overwritten",
          (agree["ambiguous"], agree["window"], "model_conflict" in agree)
          == (False, 1_000_000, False)
          and (exact["window"], exact["ambiguous"], exact["model"]) == (1_000_000, False, "sonnet")
          and apply_argv_model({"model": "claude-opus-5", "model_source": "transcript"},
                               "")["model_source"] == "transcript")

    recs = [{"pane_id": "%1", "window": "0", "title": "master", "harness": "claude",
             "model": "claude-opus-4-8", "ctx_pct": 46.0, "ctx_tokens": 92_002,
             "window_tokens": 200_000, "as_of": int(time.time()) - 120, "source": "transcript"}]
    rows = render_rows(recs)
    check("render: table carries model, ctx tokens, age",
          "opus-4-8" in rows[1] and "46% (92k/200k)" in rows[1] and "2m" in rows[1])

    print(f"\nselftest: {'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s))")
    sys.exit(1 if failures else 0)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(prog="ctx-monitor", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", nargs="?", help="tmux session (default: the one you are in)")
    ap.add_argument("--pane", help="report a single tmux pane id (e.g. %%3)")
    ap.add_argument("--cwd", help="no-tmux mode: resolve records for this working directory")
    ap.add_argument("--harness", help="no-tmux mode: harness to resolve (claude/codex/...)")
    ap.add_argument("--json", action="store_true", help="machine output")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        cmd_selftest()
        return
    if args.cwd or args.harness:
        if not (args.cwd and args.harness):
            print("--cwd and --harness go together", file=sys.stderr)
            sys.exit(2)
        rec = agent_info(args.harness, args.cwd)
        rec.update({"pane_id": "-", "window": "-", "title": "-", "shell": False,
                    "window_tokens": rec.pop("window", None)})
        records = [rec]
    else:
        session = args.session or (None if args.pane else current_session())
        if not session and not args.pane:
            print("not inside tmux — pass a session name or --pane/--cwd", file=sys.stderr)
            sys.exit(2)
        records = pane_records(session, args.pane)
    if args.json:
        print(json.dumps(records, indent=1))
    else:
        print("\n".join(render_rows(records)))


if __name__ == "__main__":
    main()
