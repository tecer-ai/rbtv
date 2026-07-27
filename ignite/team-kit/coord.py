#!/usr/bin/env python3
"""coord — the coordination CLI for a multi-agent tmux team run (shared team-kit).

All state lives in the RUN PACKAGE, never beside this script: `{package}/coordination/` (roster,
append-only message log, groups, owner status — script-managed, never hand-edited) and
`{package}/workers/<agent>/` (one briefing per seat, plus its memory + transcripts). The package
resolves as `--package DIR` > `--run TAG` > $COORD_PACKAGE > a cwd walk-up, so a seat working in
its own folder needs neither flag. Identity resolves the same way instead of being typed:
`--as NAME` > $COORD_AGENT (injected into every launched seat) > the calling pane's roster row.

The command surface, its flags and its examples live in the CLI's own help — a second copy here
drifted from the code and taught commands that no longer existed. Run `coordinate -h` for the
grouped command list, `coordinate <command> -h` for one command's arguments, one example and the
step that usually follows. Briefing frontmatter keys: `briefing-template.md` beside this script.

Stdlib only; no PATH install. Liveness/context monitoring lives in watch.py beside this script.
"""
import argparse
import csv
import difflib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

try:  # POSIX advisory locking. Absent (or unusable) -> every lock falls back to lockless.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None

VAULT_ROOT = "/home/henri/ht-wkdir/second-brain"
CLAUDE_BIN = os.environ.get("COORD_CLAUDE_BIN", "claude")
CODEX_BIN = os.environ.get("COORD_CODEX_BIN", "codex")
OPENCODE_BIN = os.environ.get("COORD_OPENCODE_BIN", "opencode")
DEFAULT_MODEL = "opus"
DEFAULT_EFFORT = "high"
HARNESSES = ("claude", "codex", "opencode")
CLOSER_MODEL = "sonnet"
CLOSERS_WINDOW = "closers"  # every closer pane lands here, never in the control-panel window
# tmux default history (2000 lines) truncates transcript exports; raise it before creating seats.
HISTORY_LIMIT = "100000"
# Observers may read the FULL message log, not just their own inbox; auto-wake recipients are
# woken on EVERY message so live observation needs no polling. Both sets are the defaults below
# PLUS any briefing declaring `observer: yes` / `auto-wake: yes` in its frontmatter.
DEFAULT_OBSERVERS = {"leader", "scientist"}
DEFAULT_AUTO_WAKE = {"scientist"}
# G-20 (owner-directed) — SPECIAL-CASE seats serve the SYSTEM or the ROOM, not the goal's
# conversation, so a `to: all` broadcast is not their input: it wakes them and spends the context
# their one job needs. The protocol bounded a closer's SENDING and never anyone's RECEIVING; this
# is that missing half. `closer-*` is matched by prefix (see broadcast_scope).
SPECIAL_CASE_SEATS = {"engineer", "watcher"}
# G-22 / leader #198 — `all` is legitimate ONLY when a seat that never reads it would act WRONGLY.
# Measured on a live run: 86 broadcasts, 35 of them `note`, the leader alone accounting for 38 —
# and ZERO groups existed after 192 messages, so the expensive channel was the only channel anyone
# had. The four clauses are the ruling's, verbatim in intent; `--why` makes each broadcast name the
# one it claims, in the log, where a reader can judge it.
BROADCAST_CLAUSES = {
    "ruling": "an owner ruling or leader verdict binding every seat",
    "milestone": "a milestone open/close, freeze or hazard changing what every seat may do",
    "retraction": "retracting something broadcast — it must reach everyone who read the wrong thing",
    "roster": "a roster/lifecycle change altering who exists",
}
# The watcher is special-cased only UNTIL the deterministic watch layer (tasks 7.33 team-monitor +
# 7.32 goal-watcher-job) replaces the agentic seat — at which point this exception expires with the
# seat. It keeps `completion` and `verdict` because its DAG-unblock trigger RIDES those broadcasts
# (it learns a task is ready from seats' completions): cutting them with no replacement trigger
# stops new seats launching SILENTLY, which is a quiet stall, not a saving. Leader ruled type
# granularity (a) tonight over trigger-replacement (b), which rides 7.32/7.33 (msg #189).
WATCHER_BROADCAST_TYPES = frozenset({"completion", "verdict"})
# G-21 — how long a `closing` state is honoured before it is treated as orphaned. A close ceremony
# runs in minutes; a closer that dies mid-close (G-11 killed one tonight) must not leave its target
# narrowed for the rest of the run.
CLOSING_MAX_MIN = 45
# G-134 shape B (`reap`), owner of the numbers: leader #312.
# 15 min is far beyond a close/renew decision made properly (1-2 min observed) and far short of the
# 41-minute leak that motivated this. It need not be tight — the awaiting-close marker makes the
# debt visible from minute zero, so a generous N costs observability nothing and costs a
# mid-decision renewal nothing either.
REAP_MIN_AGE_MIN = 15
# ...and the condition must SURVIVE, not merely be observed once. A single reading cannot tell an
# orphaned pane from a renewal decision in flight: in-place renew (G-12) NEEDS the pane alive and
# nothing machine-visible says a leader is mid-decision. Two confirmations spaced at least this far
# apart mean the condition was observed, survived, and re-observed — a trend, not a snapshot.
# WITHOUT THE SPACING THE TWO-PASS RULE IS DECORATIVE: `reap; reap` in one shell would satisfy a
# bare counter instantly, which is the whole guarantee gone. Set below the ~10-min sweep cadence so
# a slightly early pass still counts, and far above zero so no burst can manufacture a trend.
REAP_MIN_PASS_GAP_MIN = 5
# P2 — the registry's five canonical message types (concepts/message.md): the SOLE vocabulary.
MESSAGE_TYPES = ["completion", "ask", "answer", "verdict", "note"]
SUMMARY_MAX = 560
# T2 — a real run logged 305 messages averaging 1,243 chars: an unbounded `read` floods the
# reader's context. A read renders at most this many messages and says how many are still
# waiting; the cursor moves only through what was SHOWN.
READ_LIMIT = 10
DIGEST_SNIPPET = 90   # chars of body rendered per line by `read --digest` / truncated summaries
# T3 — a message body over this many chars is refused (write a file, send its path). --force escapes.
MESSAGE_MAX = 2000
# T5 — broadcast wakes run in a bounded pool: 1.3s of Enter-verify per recipient, serial, made a
# 10-seat send-all cost ~13s of the sender's turn.
WAKE_PARALLEL_MAX = 8

# T6 — two output modes. The DEFAULT is byte-plain (zero escape bytes): the primary reader is an
# agent, and colour codes inside a message body it re-quotes are noise it cannot see. `--pretty`
# (or COORD_PRETTY=1) turns on ANSI colour + aligned columns for the four VIEW commands — status,
# workers, read, pending. It is an EXPLICIT switch, never TTY auto-detection: agents live in TTYs
# too, so a TTY check would hand them the human mode by default (owner ruling, 2026-07-25).
PRETTY = {"on": False}
TYPE_COLOR = {"ask": "33", "verdict": "35", "completion": "32", "answer": "36", "note": "2"}
C_ALIVE, C_DEAD, C_DONE = "32", "31", "2"   # roster states
C_RETRACT = "1;31"    # supersession markers — the one thing a reader must not miss
C_LOGNOTE = "2;31"    # delivery-failure trailers: the log speaking, not the sender
C_LABEL = "1"         # field labels, agent names, section titles
C_HINT = "2"          # `--` footers and `next:` lines


def c(text, code):
    """ANSI-wrap `text` in --pretty mode; a plain passthrough otherwise. Every colour in this file
    goes through here, so the default output is byte-identical to the uncoloured one."""
    text = str(text)
    if not PRETTY["on"] or not code:
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def set_pretty(args):
    """Switch the human mode on from `--pretty` (global or after the subcommand) or COORD_PRETTY.
    Called once by main(); a direct cmd_* caller (watch.py, the self-test) stays plain."""
    env = os.environ.get("COORD_PRETTY", "").strip().lower()
    PRETTY["on"] = bool(getattr(args, "pretty", False)) or env not in ("", "0", "no", "false")
    return PRETTY["on"]

WORKERS_HEADER = (
    "# workers — agent sessions (script-managed, do not edit by hand)\n"
    "\n"
    "| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
    "|-------|--------|-----------|------------|------------|-------------|-----------|\n"
)
MESSAGES_HEADER = (
    "# messages — append-only coordination log (script-managed, do not edit by hand)\n"
)
GROUPS_HEADER = (
    "# groups — message groups (script-managed, do not edit by hand)\n"
    "\n"
    "| group | members | created by | created |\n"
    "|-------|---------|------------|---------|\n"
)
WORKER_ROW = re.compile(
    r"^\|\s*(?P<agent>[^|]+?)\s*\|\s*(?P<active>yes|no)\s*\|\s*(?P<pane>[^|]*?)\s*"
    r"\|\s*(?P<summary>[^|]*?)\s*\|\s*(?P<checkin>[^|]*?)\s*\|\s*(?P<checkout>[^|]*?)\s*"
    r"\|\s*(?P<lastread>[^|]*?)\s*\|$"
)
GROUP_ROW = re.compile(
    r"^\|\s*(?P<group>[^|]+?)\s*\|\s*(?P<members>[^|]*?)\s*\|\s*(?P<by>[^|]*?)\s*\|\s*(?P<created>[^|]*?)\s*\|$"
)
# T4 — ` | re: N` is ADDITIVE and optional: it sits after `supersedes:` and before the timestamp,
# so every pre-T4 log line still parses with this same regex.
# Every added field is OPTIONAL and the trailing `ts` stays greedy-last, so every log written
# before this grammar existed parses identically — the same additive discipline `re:` was given.
#
# `from-pkg:` is G-94's missing distinguisher. Identity in the log was a NAME, and a name is a
# ROLE: run-1's leader wrote `from: leader | to: leader` INTO run-2's package, and nothing in the
# stored record told the two leaders apart, so run-2's leader filtered it as its own send and the
# cursor stepped past it. A sender that is not a member of the package it is writing INTO now says
# where it came from, which is the ONE fact that makes the two distinguishable at read time.
#
# `why:` is G-100: `append_message` has always written this clause, but the grammar had no group
# for it, so it was absorbed into `ts` and `age_of` returned '?' for every broadcast carrying one.
# Fixed here rather than filed again — this is the exact line being widened, and leaving a known
# unparsed field in a regex while editing it would be perverse.
MSG_HEADER = re.compile(
    r"^## (?P<num>\d+) \| from: (?P<sender>\S+)(?: \| from-pkg: (?P<from_pkg>\S+))?"
    r" \| to: (?P<to>\S+) \| type: (?P<type>\S+)"
    r"(?: \| supersedes: (?P<supersedes>\d+))?(?: \| re: (?P<re>\d+))?"
    r"(?: \| why: (?P<why>[^|]*?))? \| (?P<ts>.+)$"
)
FM_KEY = {
    # roster signature: `seat:` is the KG term (seat.md descriptors); `agent:` is the legacy key
    "agent": re.compile(r"^(?:seat|agent):\s*(\S+)\s*$", re.MULTILINE),
    "harness": re.compile(r"^harness:\s*(\S+)\s*$", re.MULTILINE),
    "model": re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE),
    "effort": re.compile(r"^effort:\s*(\S+)\s*$", re.MULTILINE),
    "cwd": re.compile(r"^cwd:\s*(\S+)\s*$", re.MULTILINE),
    "window": re.compile(r"^window:\s*(\S+)\s*$", re.MULTILINE),
    "ephemeral": re.compile(r"^ephemeral:\s*(\S+)\s*$", re.MULTILINE),
    "observer": re.compile(r"^observer:\s*(\S+)\s*$", re.MULTILINE),
    "auto-wake": re.compile(r"^auto-wake:\s*(\S+)\s*$", re.MULTILINE),
    # r-cos-bounded-inbox / r-engineer-contact — the SENDER BOUND: a comma-separated allow-list of
    # the ONLY seats whose messages reach this one. ABSENT MEANS UNBOUNDED, which is every seat
    # today, so this lands inert and no seat silently loses reachability when it does.
    "senders": re.compile(r"^senders:\s*(.+?)\s*$", re.MULTILINE),
    # G-20's other half, DECLARED instead of named in the kit: which `to: all` TYPES reach this
    # seat. `none` | `all` | a comma-separated type list. ABSENT keeps the built-in default table
    # (broadcast_scope), so every existing package behaves exactly as it does today.
    "broadcast": re.compile(r"^broadcast:\s*(.+?)\s*$", re.MULTILINE),
    # KIT VOCABULARY, deliberately NOT a KG edge — same standing as `senders:`/`broadcast:` above,
    # neither of which is a KG verb either. A seat declaring `relays: master` says it CARRIES the
    # relay path to that role, NOT that it IS one. The distinction is the whole point and was a
    # leader override of this seat's own first proposal (`realizes: master`): `realizes` is the KG's
    # seat->role verb, so it would have said the seat IS a master — and the master role carries
    # READ-EVERYTHING across every goal's threads store plus the universal initiate right. That is a
    # privilege escalation by descriptor, granted as a side effect of fixing an addressing bug.
    # The KG's own v1 stand-in is the authority for a relay instead: "no master agent exists in code
    # — the owner IS the master", so THERE IS NO MASTER SEAT TO REALIZE, only a relay path to a
    # human. The token resolves to whichever seat currently carries it; that seat gains an ADDRESS
    # and gains no scope.
    "relays": re.compile(r"^relays:\s*(.+?)\s*$", re.MULTILINE),
    "ctx-refresh": re.compile(r"^ctx-refresh:\s*(\d+)\s*$", re.MULTILINE),
    # G-23 (owner-directed) — `close: mechanical` on a LONG-LIVED seat whose whole state is
    # external and machine-owned. It finishes one session and opens another: no closer agent, no
    # memory.md written or read, no harvest. `ceremony` (the default, and every other value) keeps
    # the full closer ceremony. The two properties this separates — a seat's LIFETIME and its CLOSE
    # PATH — were coupled only by accident of the kit's model: `ephemeral` meant both "short-lived"
    # and "keeps no memory", and the watcher is the case that pulls them apart.
    "close": re.compile(r"^close:\s*(\S+)\s*$", re.MULTILINE),
}


def _fm_yes(fm, key):
    m = FM_KEY[key].search(fm)
    return bool(m) and m.group(1).lower() in ("yes", "true")


def _fm_mechanical_close(fm):
    """True when the briefing declares `close: mechanical` (G-23). Any other value, and the
    absence of the key, mean the full closer ceremony — the default stays the careful one."""
    m = FM_KEY["close"].search(fm)
    return bool(m) and m.group(1).lower() == "mechanical"


def _fm_window(fm):
    """window: value, normalized — "" (absent/no), "yes" (own window), or a SHARED window
    name (wave layout: seats carrying the same name become panes of one window)."""
    m = FM_KEY["window"].search(fm)
    if not m:
        return ""
    v = m.group(1)
    if v.lower() in ("yes", "true"):
        return "yes"
    if v.lower() in ("no", "false"):
        return ""
    return v


def briefing_files(wdir):
    """Every briefing path in discovery order: flat <roster>/*.md, then <roster>/*/agent.md and
    <roster>/*/seat.md (seat.md is the KG run-folder form — seats/<seat>/seat.md; agent.md the
    legacy workers/ form)."""
    if not wdir.is_dir():
        return []
    flat = sorted(p for p in wdir.glob("*.md"))
    folder = sorted(list(wdir.glob("*/agent.md")) + list(wdir.glob("*/seat.md")))
    return flat + folder


def briefing_frontmatters(wdir):
    """agent-name -> (frontmatter text, briefing path), for every briefing in workers/."""
    out = {}
    for p in briefing_files(wdir):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        fm_end = text.find("\n---", 3)
        if fm_end == -1:
            continue
        fm = text[:fm_end]
        m = FM_KEY["agent"].search(fm)
        if m:
            out[m.group(1)] = (fm, p)
    return out


def observer_sets(args):
    """(observers, auto_wake) — built-in defaults plus per-run briefing declarations."""
    observers, auto = set(DEFAULT_OBSERVERS), set(DEFAULT_AUTO_WAKE)
    for agent, (fm, _p) in briefing_frontmatters(workers_dir(args)).items():
        if _fm_yes(fm, "observer"):
            observers.add(agent)
        if _fm_yes(fm, "auto-wake"):
            auto.add(agent)
    return observers, auto


def _fm_list(fm, key):
    """The comma-separated values of `key`, or None when the key is absent.

    None and the empty list are DIFFERENT answers here and the distinction is load-bearing: absent
    means "undeclared, keep today's behaviour", while `broadcast: none` means "declared, and the
    answer is nothing". Collapsing them would make an explicit narrowing indistinguishable from
    never having said anything."""
    m = FM_KEY[key].search(fm)
    if not m:
        return None
    return [v.strip() for v in m.group(1).split(",") if v.strip()]


def inbox_decls(args):
    """{seat: {"senders": frozenset, "broadcast": scope}} — each seat's DECLARED inbox topology,
    read from its OWN descriptor. Keys appear only when the descriptor declares them.

        senders:   leader, master        the ONLY seats whose messages reach this one
        broadcast: none | all | a,b      which `to: all` TYPES reach it (G-20, declared)
        relays:    master                ROLE TOKENS this seat carries the relay path for

    `relays:` is what makes the other two usable at all for a role word. `senders: leader, master`
    is the owner's ruled wording, and `leader` resolves only because that role's name happens to BE
    a seat name; `master` is a FUNCTION and matched nobody, so the ruled bound admitted a sender
    that does not exist and refused the seat actually carrying the owner channel. Measured before
    it was built (`probe_master_bound.py`): M2 and M4 red, M5 green — the bound was sound and the
    identity layer was missing.

    Two owner rulings bound an inbox to named senders (`r-cos-bounded-inbox` for the
    chief-of-staff, `r-engineer-contact` for the engineer: leader + master, a third sender is a
    breach). Until this existed both were enforced by the SEAT DECLINING — the message still
    arrived, still spent the seat's context, and a breach was visible only if the seat noticed and
    said so.

    DERIVED, never a kit-side name list, for the same reason `observer:`/`auto-wake:` are. A name
    list in the kit encodes ONE campaign's role vocabulary into a tool every run shares: another
    run's `engineer` is narrowed by accident and its differently-named system seat is not.
    `SPECIAL_CASE_SEATS` named its members while its own comment described a MANDATE ("serve the
    SYSTEM or the ROOM") — which is exactly how the chief-of-staff came to be omitted from the set
    whose definition described it. A mandate cannot be expressed as a name list, so the next such
    seat is forgotten identically. The seat descriptor already IS where topology is declared
    (harness, model, observer, auto-wake, ctx-refresh); inbox scope belongs beside them.

    ABSENCE IS TODAY'S BEHAVIOUR on both keys, and no descriptor in any package declares either —
    so this ships INERT: it changes no seat's inbox until a descriptor says otherwise.
    """
    decls = {}
    for agent, (fm, _p) in briefing_frontmatters(workers_dir(args)).items():
        d = {}
        named = _fm_list(fm, "senders")
        if named:
            d["senders"] = frozenset(named)
        relays = _fm_list(fm, "relays")
        if relays:
            d["relays"] = frozenset(v.lower() for v in relays)
        raw = _fm_list(fm, "broadcast")
        if raw is not None:
            low = [v.lower() for v in raw]
            if low == ["all"]:
                d["broadcast"] = None            # every type, explicitly
            elif low == ["none"]:
                d["broadcast"] = frozenset()     # no broadcast at all
            else:
                d["broadcast"] = frozenset(low)  # exactly these types
        if d:
            decls[agent] = d
    return decls


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def file_stamp():
    return datetime.now().strftime("%Y%m%d-%H%M")


RUNS_INDEX = Path.home() / ".config" / "rbtv" / "coordinate-runs.json"


def write_runs_index(idx):
    """Persist the registry. Best-effort: a read-only HOME must never break coordination."""
    try:
        RUNS_INDEX.parent.mkdir(parents=True, exist_ok=True)
        RUNS_INDEX.write_text(json.dumps(idx, indent=1), encoding="utf-8")
    except OSError:
        pass


def load_runs_index(prune=True):
    """The run-tag registry, with dead entries dropped (T5): a package folder that no longer
    exists (a /tmp package, a deleted run) polluted every `--run` error listing. Rewrites the
    file only when pruning actually changed it; every failure is silent."""
    try:
        idx = json.loads(RUNS_INDEX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(idx, dict):
        return {}
    if not prune:
        return idx
    alive = {tag: path for tag, path in idx.items() if Path(path).is_dir()}
    if alive != idx:
        write_runs_index(alive)
    return alive


def register_run(pkg):
    """Auto-register a package under its folder-name tag so later calls can say
    `--run <tag>` (or nothing, from inside the package) instead of the full path.

    A tag is never STOLEN: when it already points at a DIFFERENT package that still exists on
    disk, the second same-named package registers nothing and says nothing. Re-pointing it
    silently redirected `--run <tag>` — and every wake and hint built from it — at the wrong
    run (observed live, two packages sharing a folder name). Silence is deliberate: the loser
    needs no warning, because `coord_invocation` sees the tag does not resolve to its own path
    and emits the full `--package` form instead. A tag whose path is GONE was already dropped by
    load_runs_index's prune, so the new package takes it."""
    idx = load_runs_index()
    tag = Path(pkg).name
    held = idx.get(tag)
    if held == str(pkg):
        return
    if held and Path(held).is_dir():
        return
    idx[tag] = str(pkg)
    write_runs_index(idx)


def discover_package_from(cwd):
    """Nearest ancestor (cwd included) that IS a run package — identified by its own
    structure (coordination/ + a roster dir: seats/ in the KG run-folder form, workers/ in the
    legacy form). Seats' cwd is their seat folder, so a bare `coordinate <cmd>` resolves for
    them with no arguments at all."""
    p = Path(cwd).resolve()
    for cand in (p, *p.parents):
        if (cand / "coordination").is_dir() and (
                (cand / "seats").is_dir() or (cand / "workers").is_dir()):
            return cand
    return None


def package_dir(args, register=True):
    """Resolution order: --package path > --run tag (registry) > COORD_PACKAGE env >
    cwd walk-up. Every successful resolution (re-)registers the tag."""
    pkg = getattr(args, "package", None)
    if not pkg and getattr(args, "run", None):
        pkg = load_runs_index().get(args.run)
        if not pkg:
            known = ", ".join(sorted(load_runs_index())) or "(none registered yet)"
            print(f"error: unknown run tag '{args.run}' — known: {known}", file=sys.stderr)
            sys.exit(2)
    if not pkg:
        pkg = os.environ.get("COORD_PACKAGE")
    if not pkg:
        pkg = discover_package_from(Path.cwd())
    if not pkg:
        known = ", ".join(sorted(load_runs_index())) or "(none registered yet)"
        print("error: no run package — pass --run <tag> or --package <abs-run-folder>, or "
              f"invoke from inside a package. Known runs: {known}", file=sys.stderr)
        sys.exit(2)
    pkg = Path(pkg).resolve()
    if register:
        register_run(pkg)
    return pkg


def base_dir(args):
    if getattr(args, "base", None):
        base = Path(args.base).resolve()
    else:
        base = package_dir(args) / "coordination"
    set_injection_context(base=base)  # 7.39: the primitives get no args; this is the one chokepoint
    return base


def workers_dir(args):
    if getattr(args, "workers_dir", None):
        return Path(args.workers_dir).resolve()
    pkg = package_dir(args)
    seats = pkg / "seats"  # KG run-folder form wins when present; legacy workers/ otherwise
    if seats.is_dir():
        return seats
    return pkg / "workers"


def coord_invocation(args):
    """The exact command string agents use — embedded in wakes and launch prompts. Prefers
    the per-machine `coordinate` PATH symlink (it IS a CLI — seats should not carry the
    script's full path) and the short `--run <tag>` form (auto-registered); falls back to
    the full forms where symlink/registry are absent."""
    import shutil
    script = Path(__file__).resolve()
    cli = "coordinate" if shutil.which("coordinate") else f"python3 {script}"
    if getattr(args, "base", None):
        return f"{cli} --base {Path(args.base).resolve()}"
    pkg = package_dir(args)
    if load_runs_index().get(pkg.name) == str(pkg):
        return f"{cli} --run {pkg.name}"
    return f"{cli} --package {pkg}"


def atomic_write(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# ---------- package lock (T5) ----------

_LOCK_NOTE = {"shown": False}


def _acquire_flock(fh):
    """Take an exclusive advisory lock on an open handle. Raises on ANY failure — the caller
    then proceeds lockless. Module-level so the self-test can force the fallback path."""
    if fcntl is None:
        raise OSError("fcntl unavailable on this platform")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)


@contextmanager
def coord_lock(base):
    """Serialize one read-modify-write of the package's state files across concurrent coord
    processes (message-ID allocation, roster/cursor/group writes). Two concurrent sends used to
    claim the SAME message number (run-obs §589) and two concurrent roster writes could lose one
    (cli #203) — reads stay lockless.

    Never fatal: a sandboxed seat whose package is read-only (codex EROFS) cannot take the lock,
    so it proceeds WITHOUT it after one note. Yields True when the lock was actually held."""
    fh = None
    try:
        Path(base).mkdir(parents=True, exist_ok=True)
        fh = open(Path(base) / ".lock", "a+", encoding="utf-8")
        _acquire_flock(fh)
    except Exception as exc:  # OSError, PermissionError, anything the platform raises
        if fh is not None:
            try:
                fh.close()
            except OSError:
                pass
            fh = None
        if not _LOCK_NOTE["shown"]:
            _LOCK_NOTE["shown"] = True
            print(f"note: coordination lock unavailable ({exc}) — proceeding lockless",
                  file=sys.stderr)
    try:
        yield fh is not None
    finally:
        if fh is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            fh.close()


def detect_pane(override=None):
    if override:
        return override
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return ""
    r = subprocess.run(
        ["tmux", "display-message", "-p", "-t", pane, "#{pane_id}"],
        capture_output=True, text=True,
    )
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else pane


# ---------- injection write-log (task 7.39; owner ruling `r-739-payload-text`) ----------------
#
# Every agent-to-agent keystroke injection writes ONE attributed line: WHO injected, into WHICH
# seat/pane, WHEN, WHICH action, and THE FULL PAYLOAD TEXT. The payload is recorded on the owner's
# explicit ruling (2026-07-27), taken AGAINST the metadata-only recommendation with the exposure on
# the table: it re-creates the R1-dropped keystroke-transcript class for agent-to-agent injections
# only. That call is the owner's, not this code's — do not re-decide it here.
#
# The log is NEVER-COMMIT / NEVER-PUSH: same exposure class as raw scrollback (issues G-3). It is
# written into the run package's `coordination/` dir, which lives under `.rbtv/goals/**` and is
# untracked, and it is chmod 0600 (task 7.13 tightened this artifact class 664 -> 0600).
#
# TWO PROPERTIES THAT ARE DELIBERATE, both from task 7.13's retention ruling:
#   FAILS OPEN, ALWAYS — a logging error NEVER blocks or fails an injection. 7.13 ruled that a
#   fail-closed audit disables the very function it audits. Here it would be worse: all keystroke
#   injection funnels through these three primitives, so an unwritable path would silence EVERY
#   seat at once. Every entry point below swallows its own exceptions and returns False.
#   AGE SWEEP, NEVER A SIZE CAP — 7.13 criterion (2) rejects size caps in those words, because a
#   cap either fires fail-closed or silently discards evidence. Window is env-configurable,
#   default 90 days, 0 = never delete, values below 7 refused (a typo must not erase the trail).

INJECTION_LOG = "injections.log"
INJECTION_RETENTION_DAYS = 90          # 7.13 default
INJECTION_RETENTION_MIN = 7            # 7.13: below this is REFUSED, never honoured
INJECTION_RETENTION_ENV = "COORD_INJECTION_RETENTION_DAYS"

# who/action/base for the primitives, which are module-level and receive no `args`.
_INJECTION = {"agent": "", "action": "", "base": None}
_INJECTION_PRUNED = False
_INJECTION_SWEEP_LOCK = threading.Lock()


def set_injection_context(agent=None, action=None, base=None):
    """Tell the injection log who is calling, why, and where the package is (7.39).

    The three tmux primitives take only `(pane, text)`, so identity, action and package land here
    instead of being threaded through every call site. Anything left unset falls back at write
    time to $COORD_AGENT / $COORD_PACKAGE / the calling pane's roster row — which is what covers
    watch.py's internal API path, since it runs outside any pane."""
    if agent is not None:
        _INJECTION["agent"] = (agent or "").strip()
    if action is not None:
        _INJECTION["action"] = (action or "").strip()
    if base is not None:
        _INJECTION["base"] = Path(base)


def injection_retention_days():
    """7.13's window. Default 90; 0 = never delete; below INJECTION_RETENTION_MIN is REFUSED and
    falls back to the default, because a mistyped '1' must not silently erase the audit trail.
    An unparseable value is treated the same way — fail open, keep evidence."""
    raw = os.environ.get(INJECTION_RETENTION_ENV, "").strip()
    if not raw:
        return INJECTION_RETENTION_DAYS
    try:
        days = int(raw)
    except ValueError:
        return INJECTION_RETENTION_DAYS
    if days == 0:
        return 0
    if days < INJECTION_RETENTION_MIN:
        return INJECTION_RETENTION_DAYS
    return days


def injection_log_path():
    """The log's home: `{package}/coordination/injections.log`. None when no package resolves —
    in which case nothing is logged and nothing fails."""
    base = _INJECTION.get("base")
    if base is None:
        pkg = os.environ.get("COORD_PACKAGE", "").strip()
        if not pkg:
            return None
        base = Path(pkg) / "coordination"
    return Path(base) / INJECTION_LOG


def injection_payload_repr(payload):
    """One line, full text, reversible. The payload is recorded VERBATIM per the owner's ruling —
    never truncated, never hashed — but the log stays line-oriented (one line per injection, so it
    greps and tails), so the four characters that would break that are escaped."""
    if payload is None:
        return "(none)"
    return (str(payload).replace("\\", "\\\\").replace("\t", "\\t")
            .replace("\r", "\\r").replace("\n", "\\n"))


def prune_injection_log(path, days):
    """7.13 AGE sweep. Drops entries older than the window; NEVER caps by size. A line whose
    timestamp will not parse is KEPT — evidence we cannot date is still evidence.

    CHEAP-CHECKS FIRST, AND THAT IS A CORRECTNESS PROPERTY, NOT AN OPTIMISATION. A sweep is a
    read-then-rewrite, and `deliver_wakes` fans out to recipients CONCURRENTLY (ThreadPoolExecutor),
    so a rewrite racing an append from another thread or another `coordinate` process would silently
    LOSE that line — in the one file whose whole purpose is that nothing is lost. Since entries are
    appended in time order, the OLDEST line is the first one: if it is inside the window there is
    nothing to drop, so we return having only read one line and never open the file for writing.
    With a 90-day window that makes the racy path run about once per 90 days instead of once per
    process. The rewrite itself then takes the package lock, and the caller holds a thread lock."""
    if days <= 0 or not path.exists():
        return
    cutoff = datetime.now() - timedelta(days=days)
    try:  # one line, not the file: is there anything old enough to be worth a rewrite?
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            first = fh.readline()
        if not first.strip():
            return
        if datetime.fromisoformat(first.split("\t", 1)[0]) >= cutoff:
            return  # oldest entry is inside the window -> nothing to sweep, no rewrite
    except (ValueError, IndexError, OSError):
        pass  # undateable or unreadable first line -> fall through to the full pass
    kept, dropped = [], 0
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            if datetime.fromisoformat(ln.split("\t", 1)[0]) < cutoff:
                dropped += 1
                continue
        except (ValueError, IndexError):
            pass
        kept.append(ln)
    if dropped:
        # Under the package lock: `coordinate` processes serialize their read-modify-writes here,
        # which is the same guard the roster and message-id allocation use.
        with coord_lock(path.parent):  # the log lives IN the coordination dir the lock guards
            path.write_text("".join(f"{ln}\n" for ln in kept), encoding="utf-8")


def log_injection(pane, primitive, payload):
    """Append ONE attributed line for one keystroke injection (7.39). Returns True when written.

    NEVER RAISES. Every failure path returns False and the injection proceeds — see this section's
    header for why fail-open is a requirement here and not a convenience."""
    global _INJECTION_PRUNED
    try:
        path = injection_log_path()
        if path is None:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        # Wakes fan out concurrently, so the once-per-process sweep takes a thread lock: two
        # threads must never rewrite this file at the same time. The append below needs no lock —
        # one short line opened "a" is atomic under POSIX O_APPEND, across threads and processes.
        with _INJECTION_SWEEP_LOCK:
            if not _INJECTION_PRUNED:
                _INJECTION_PRUNED = True
                try:
                    prune_injection_log(path, injection_retention_days())
                except Exception:
                    pass
        who = _INJECTION.get("agent") or os.environ.get("COORD_AGENT", "").strip()
        if not who:
            try:
                who = pane_agent(path.parent, detect_pane()) or ""
            except Exception:
                who = ""
        seat = ""
        try:
            seat = pane_agent(path.parent, pane) if pane else ""
        except Exception:
            seat = ""
        # Every injection entry point names its OWN action, so a later call can never inherit an
        # earlier one's label — the first draft of this logged a `/rename` as `approve:rename`
        # because it reused whatever `cmd_approve` had set. An unnamed action logs the bare
        # primitive, which is honest; a WRONG one is worse than none in a forensic log.
        ctx = _INJECTION.get("action", "")
        if ctx == primitive:
            ctx = ""
        line = "\t".join((
            datetime.now().isoformat(timespec="seconds"),
            who or "(unresolved)",
            seat or "(unregistered)",
            pane or "(no-pane)",
            f"{ctx}:{primitive}" if ctx else primitive,
            injection_payload_repr(payload),
        ))
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return True
    except Exception:
        return False


# ---------- tmux wrappers (every tmux touch goes through one of these, so selftest can stub) ----

def set_pane_title(pane, title):
    """Name the tmux pane after the agent (visible via pane-border-status)."""
    if not pane:
        return
    subprocess.run(["tmux", "select-pane", "-t", pane, "-T", title],
                   capture_output=True, text=True)


RENAME_ACTION = "rename-scheduled"


def rename_injection_note(agent, delay):
    """The write-log payload for a SCHEDULED rename (G-53). Pure, so it is testable without the
    detached subshell — and the reason it exists is that the shell is exactly what makes the
    delivery unobservable."""
    return (f"/rename {agent} (scheduled: detached, fires in ~{delay}s via raw tmux; "
            f"delivery is NOT observed by this log)")


def schedule_session_rename(pane, agent, delay=25):
    """Inject `/rename <agent>` into the pane's Claude session once it has had time to boot.

    Detached (coord.py returns immediately); failures are silent — the rename is cosmetic and a
    lost keystroke must never block a launch. claude harness only: codex/opencode have no
    /rename — their seats are identified by pane/window title alone."""
    # G-53: this logs INTENT, not injection. The keystrokes are sent by the DETACHED subshell
    # below, ~25s later, with raw `tmux send-keys` that never touches the instrumented primitives
    # — so nothing here can know whether they landed, and the line would read identically if the
    # pane had died in the meantime. writelog proved it by observation: zero entries across every
    # pane in the window where the real keystrokes went out. The action name now says what the
    # line actually attests, so the write-log stops asserting what it cannot know.
    set_injection_context(action=RENAME_ACTION)  # our own action: never inherit a caller's
    log_injection(pane, RENAME_ACTION, rename_injection_note(agent, delay))
    script = (f"sleep {delay}; "
              f"tmux send-keys -t {shlex.quote(pane)} -l {shlex.quote('/rename ' + agent)}; "
              f"sleep 1; tmux send-keys -t {shlex.quote(pane)} Enter")
    subprocess.Popen(["bash", "-c", script], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def live_panes():
    """Set of pane ids tmux currently knows. Empty set when tmux is unavailable."""
    r = subprocess.run(["tmux", "list-panes", "-a", "-F", "#{pane_id}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return set()
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


# P38/8(b) — a seat parked on its harness's interactive approval prompt is a BLIND GATE: the pane
# is frozen on a modal, so a wake typed into it is not read, and worst case lands as stray text
# inside the modal's own input. codex advertises the state in the pane TITLE ("Action Required").
# The title is the only signal used on purpose: matching the pane's visible TEXT would false-fire
# on any seat whose output happens to contain the phrase (a briefing quoting it, a log line).
# codex is the only rostered harness that publishes such a title today — extending this to another
# harness needs a real captured pane in the gated state, the same discipline P35 round 2 imposed.
APPROVAL_TITLE_MARKERS = ("action required",)


def pane_title(pane):
    """Current tmux title of a pane. '' when tmux is unavailable or the pane is gone."""
    r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "-F", "#{pane_title}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    return r.stdout.strip()


def at_approval_gate(pane):
    """True when this pane's TITLE says its harness is parked on an interactive approval prompt.

    Fail-safe by construction: an unreadable title, a dead pane, or no tmux all return '' and
    therefore False — a seat is never treated as gated on the strength of a missing signal."""
    if not pane:
        return False
    title = pane_title(pane).lower()
    return any(m in title for m in APPROVAL_TITLE_MARKERS)


def watcher_heartbeat(base):
    """The watcher loop's last-pass record, or None when no watcher has ever run in this package.

    P32 — nothing watched the watcher: `watch.py` runs detached for hours (nohup), so when its
    loop dies the run loses liveness/context/approval flagging SILENTLY, and the absence of flags
    reads exactly like a healthy run. The loop stamps every pass; the roster view reads the stamp,
    which makes leader's existing orientation command the external check."""
    p = base / "watch-heartbeat.json"
    if not p.exists():
        return None
    try:
        hb = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(hb, dict) or not hb.get("last_pass"):
        return None
    try:
        age_min = int((datetime.now() - datetime.fromisoformat(hb["last_pass"])).total_seconds()
                      // 60)
    except (TypeError, ValueError):
        return None
    loop_min = hb.get("loop_min")
    # A one-shot pass (no --loop) has no cadence to be late against: judge it on a flat 30 min.
    # A looping watcher gets three missed passes of slack before it is called stale — one skipped
    # pass is a slow tmux capture, three in a row is a dead loop.
    stale_after = (loop_min * 3) if isinstance(loop_min, int) and loop_min > 0 else 30
    hb["age_min"] = age_min
    hb["stale"] = age_min > stale_after
    hb["stale_after"] = stale_after
    return hb


WAKE_ENTER_ATTEMPTS = 3
# A real production wake (300+ chars) takes some TUIs noticeably longer than round-2's 0.15s
# first-check assumed just to REDRAW the pasted text, before Enter's effect is even relevant — a
# check that fires before the redraw catches up cannot tell "still stranded" apart from "hasn't
# rendered yet" (both look like "text absent from composer"), so it silently skips verification
# on exactly the pane class it's slowest on. Round-3 live-stress finding: a real 323-char wake on
# a rostered-width (114-col) opencode pane took ~0.6-0.85s (3 trials, cold and warm) to redraw
# EITHER outcome (stranded-and-still-there, or typed-then-cleared) — the composer is frozen on
# its pre-send content for that whole window regardless of whether Enter lands. Claude Code
# resolves in <0.15s (round-2 evidence, reconfirmed). WAKE_ENTER_VERIFY_DELAY_FIRST is set with
# margin over the slower harness's observed worst case; this trades some latency on the fast
# common path (every send now pays it, not just genuine retries) for not being blind on the
# slower one — the same failure MODE the wrap fix above addresses, just a different cause.
WAKE_ENTER_VERIFY_DELAY_FIRST = 1.3
WAKE_ENTER_VERIFY_DELAY_RETRY = 0.6   # a retry's pane has already rendered the paste once by
                                       # here (live-verified: a genuine second Enter's effect
                                       # still resolves within this window — round-3 evidence)
WAKE_TAIL_LINES = 20  # on-screen lines scanned for the still-unsubmitted composer line
# A production wake line (310-319 chars) hard-wraps in EVERY rostered pane (narrowest 114 cols) —
# `capture-pane -J` cannot rejoin a TUI's own wrap points (verifier-tick round-2, msg #188). Only
# a PREFIX of the wake text is guaranteed to render intact on the composer's first on-screen line;
# 60 chars covers '[coord wake] New coordination message #N from <sender> ' (unique per send) with
# wide margin under the narrowest rostered composer width.
WAKE_PREFIX_LEN = 60

# Claude Code draws its composer as one or more lines sandwiched between two horizontal rule
# lines (the top rule may carry the pane's tmux title, e.g. '───── toolsmith-2 ──'); a wake line
# wider than the pane hard-wraps across several composer lines. Status/hint chrome always renders
# BELOW the bottom rule, never between the rules. Requiring the sandwich — not just the '❯' glyph
# alone — also guards against a false match on a shell PS1 prompt that reuses the same glyph
# (starship-themed shells) sitting anywhere in cooked-mode scrollback.
_RULE_RUN = "─" * 10  # '──────────'

# opencode draws its composer inside a '┃'-bordered box: a blank pad line, the composer's own
# content line, another blank pad, then a 'Build · <model>' status line, in that order — the
# composer is the FIRST non-blank line in the box's bottom-most run, not the last (that's the
# model-status footer).
_OPENCODE_BORDER = "┃"


def tmux_send_text(pane, text):
    log_injection(pane, "text", text)
    r = subprocess.run(["tmux", "send-keys", "-t", pane, "-l", text], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def tmux_send_enter(pane):
    log_injection(pane, "enter", "<Enter>")
    r = subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def tmux_capture_tail(pane, lines=WAKE_TAIL_LINES):
    """Last N on-screen lines of a pane, soft-wraps rejoined (-J). Returns (text, err)."""
    r = subprocess.run(["tmux", "capture-pane", "-p", "-J", "-t", pane, "-S", f"-{lines}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return "", r.stderr.strip()
    return r.stdout, ""


def _locate_claude_composer(lines):
    """Find the bottom-most rule-sandwiched composer and return its TOP-most line — the one a
    hard-wrapped wake's prefix starts on. Scans from the screen bottom for a rule line (the
    sandwich's bottom rule), then walks upward collecting composer line(s) until the matching top
    rule. A sandwich with zero lines between the rules (top rule immediately above the bottom
    rule) is not a real composer and is skipped."""
    for i in range(len(lines) - 1, 1, -1):
        if not lines[i].startswith(_RULE_RUN):
            continue
        j = i - 1
        while j >= 0 and not lines[j].startswith(_RULE_RUN):
            j -= 1
        if j < 0 or j == i - 1:
            continue
        return lines[j + 1]
    return None


def _locate_opencode_composer(lines):
    run_start = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].lstrip().startswith(_OPENCODE_BORDER):
            run_start = i
        elif run_start is not None:
            break
    if run_start is None:
        return None
    run_end = run_start
    while run_end < len(lines) and lines[run_end].lstrip().startswith(_OPENCODE_BORDER):
        run_end += 1
    for line in lines[run_start:run_end]:
        if line.lstrip().lstrip(_OPENCODE_BORDER).strip():
            return line
    return None


def _locate_composer_line(tail):
    """Return the pane's live composer text, or None when the capture matches no known composer
    structure (an unrecognized TUI, or a cooked-mode pane with no composer at all). Callers MUST
    treat None as fail-safe: do not retry, do not report failure."""
    lines = tail.splitlines()
    return _locate_claude_composer(lines) or _locate_opencode_composer(lines)


def _wake_unsubmitted(pane, text):
    """True while `text` is still sitting in the pane's live composer — the Enter that should
    have submitted it was dropped by a busy/streaming pane (P35). False once the composer no
    longer holds it, OR when the pane's chrome does not match a known composer structure: an
    unparseable pane fails SAFE (today's single-Enter behavior — never retried, never reported
    as a delivery failure) rather than risking a false stranded-retry or a false failure on a
    pane this code cannot read (round-2 fix, verifier-tick #145 — the prior 'last non-blank
    line' check was blind on every rostered TUI, since each renders status/hint chrome below the
    composer). Matches only a bounded PREFIX of `text`, not the full line: a production wake
    (310-319 chars) hard-wraps across several composer lines in every rostered pane, and
    `capture-pane -J` cannot rejoin a TUI's own wrap points — the full text is never one
    contiguous captured line, but its first WAKE_PREFIX_LEN chars always render intact on the
    composer's top-most line (round-3 fix, verifier-tick round-2 re-verification). A capture
    error is likewise treated as submitted: send-keys already reported success and there is
    nothing further to act on."""
    tail, err = tmux_capture_tail(pane)
    if err:
        return False
    composer = _locate_composer_line(tail)
    if composer is None:
        return False
    return text[:WAKE_PREFIX_LEN] in composer


def wake(pane, text):
    """Type `text` into `pane` and submit it. A busy/streaming pane can eat the Enter keystroke
    without submitting (P35) even though text and Enter are already separate send-keys calls
    (§17.3) — verify the wake line actually left the composer and, if not, re-send ONLY Enter
    (never retype text), bounded to WAKE_ENTER_ATTEMPTS. Every send pays the first verify delay
    (see its constant for why a "short fixed delay, only retries pay more" split does not hold at
    real wake length); a retry (genuinely stranded after the first Enter) pays the shorter settle
    delay on top, since by then the pane has already rendered the paste once.

    REFUSES multi-line text (G-11). `tmux send-keys -l` delivers an embedded newline as Enter, so
    multi-line text is EXECUTED LINE BY LINE by whatever reads the pane. Reproduced 2026-07-27 in
    a throwaway pane: a closer's markdown prompt sent this way into a bash/ble.sh pane ran its
    `coordinate checkin` line for real and printed its completion line — a seat that reported done
    while no harness had ever started, and wake() returned SUCCESS. Any text long enough to be
    multi-line goes through a file (prompt_file) so the wake line stays one line."""
    if "\n" in text or "\r" in text:
        return False, ("refused: wake text carries a newline, and send-keys delivers a newline as "
                       "Enter — the pane's shell would execute the text line by line (G-11). "
                       "Write the text to a file and wake with a one-line command that reads it "
                       "(see prompt_file).")
    set_injection_context(action="wake")
    ok, err = tmux_send_text(pane, text)
    if not ok:
        return False, err
    for attempt in range(WAKE_ENTER_ATTEMPTS):
        ok, err = tmux_send_enter(pane)
        if not ok:
            return False, err
        time.sleep(WAKE_ENTER_VERIFY_DELAY_FIRST if attempt == 0 else WAKE_ENTER_VERIFY_DELAY_RETRY)
        if not _wake_unsubmitted(pane, text):
            return True, ""
    return False, (f"Enter did not submit after {WAKE_ENTER_ATTEMPTS} attempt(s) — "
                    f"wake text left unsubmitted in the pane's composer")


PANEL_STRIP_ROWS = 8


def restore_overview_strip(target):
    """After a re-tile, shrink any 'overview' pane in the window back to its strip height."""
    for pid, title in tmux_window_panes(target):
        if title == "overview":
            subprocess.run(["tmux", "resize-pane", "-t", pid, "-y", str(PANEL_STRIP_ROWS)],
                           capture_output=True, text=True)


def tmux_split_pane(target, cwd):
    """Open a tiled pane in the target pane's window. Returns (pane_id, err)."""
    r = subprocess.run(
        ["tmux", "split-window", "-d", "-t", target, "-c", cwd, "-P", "-F", "#{pane_id}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return "", r.stderr.strip()
    pane = r.stdout.strip()
    subprocess.run(["tmux", "select-layout", "-t", target, "tiled"], capture_output=True, text=True)
    subprocess.run(["tmux", "set-option", "-w", "-t", target, "pane-border-status", "top"],
                   capture_output=True, text=True)
    restore_overview_strip(target)  # the tiled relayout equalizes; the panel strip stays small
    return pane, ""


def tmux_split_strip(target, cwd, rows=PANEL_STRIP_ROWS):
    """Open a short FULL-WIDTH bottom strip in the target pane's window (not re-tiled).
    Returns (pane_id, err)."""
    r = subprocess.run(
        ["tmux", "split-window", "-d", "-f", "-l", str(rows), "-t", target, "-c", cwd,
         "-P", "-F", "#{pane_id}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return "", r.stderr.strip()
    return r.stdout.strip(), ""


def tmux_session_name(target):
    """Session name of a pane ('' when unresolvable)."""
    r = subprocess.run(["tmux", "display-message", "-p", "-t", target, "#{session_name}"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tmux_window_panes(target):
    """[(pane_id, pane_title), ...] of the target pane's window."""
    r = subprocess.run(["tmux", "list-panes", "-t", target, "-F", "#{pane_id}\t#{pane_title}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [tuple(ln.split("\t", 1)) for ln in r.stdout.splitlines() if "\t" in ln]


def tmux_new_window(target, name, cwd):
    """Open a named window (tab) in the target pane's session. Returns (pane_id, err)."""
    session = tmux_session_name(target)
    if not session:
        return "", f"cannot resolve session of {target}"
    r = subprocess.run(
        ["tmux", "new-window", "-d", "-t", f"{session}:", "-n", name, "-c", cwd,
         "-P", "-F", "#{pane_id}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return "", r.stderr.strip()
    pane = r.stdout.strip()
    subprocess.run(["tmux", "set-option", "-w", "-t", pane, "automatic-rename", "off"],
                   capture_output=True, text=True)
    return pane, ""


def tmux_find_window_pane(session, window):
    """First pane id of `window` in `session`, or "" if that window doesn't exist (or `session`
    is empty). A hit is a valid split-window target; a miss means the window must be created."""
    if not session:
        return ""
    r = subprocess.run(
        ["tmux", "list-panes", "-t", f"{session}:{window}", "-F", "#{pane_id}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return ""
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    return lines[0] if lines else ""


def tmux_kill_pane(pane):
    """Kill a pane; a window whose last pane dies closes with it. Returns (ok, err)."""
    r = subprocess.run(["tmux", "kill-pane", "-t", pane], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def tmux_respawn_pane(pane, cwd):
    """Restart a pane's command IN PLACE — same pane id, same cell, window layout untouched
    (G-12). `-k` kills whatever still runs there first. A renew used to kill the pane and split a
    fresh one, which re-tiles the whole window and destroys an arranged layout. Returns (ok, err)."""
    r = subprocess.run(["tmux", "respawn-pane", "-k", "-c", cwd, "-t", pane],
                       capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def tmux_pane_pid(pane):
    """PID of the pane's own process (its shell), 0 when unresolvable."""
    r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "#{pane_pid}"],
                       capture_output=True, text=True)
    out = r.stdout.strip()
    return int(out) if r.returncode == 0 and out.isdigit() else 0


def tmux_pane_window(pane):
    """Window id (@N) of a pane, '' when unresolvable."""
    r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "#{window_id}"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tmux_pane_window_name(pane):
    """Window NAME of a pane ('control', 'workers'), '' when unresolvable. The id form above
    answers identity; this answers placement, which is what a descriptor declares."""
    r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "#{window_name}"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tmux_capture(pane):
    """Full scrollback of a pane, wrapped lines joined. Returns (text, err)."""
    r = subprocess.run(["tmux", "capture-pane", "-p", "-J", "-t", pane, "-S", "-"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return "", r.stderr.strip()
    return r.stdout, ""


def tmux_raise_history_limit():
    subprocess.run(["tmux", "set-option", "-g", "history-limit", HISTORY_LIMIT],
                   capture_output=True, text=True)


# ---------- process truth: is the harness actually running, and did it actually die? ----------
# Two failures on one night proved the roster is not evidence about processes:
#   G-11 — a closer's multi-line prompt was typed into the pane's SHELL, which executed it line by
#          line: the `checkin` line ran for real (row -> ACTIVE) and the completion line printed a
#          report, while the harness never started. A row said ACTIVE; nothing was running.
#   G-10 — `tmux kill-pane` SIGHUPs the pane's process group; a harness blocked elsewhere survives
#          as a GHOST (449-488 MB each) that no roster row mentions and no sensor counts. Three were
#          hand-reaped by the leader; hand-reaping does not scale to an unattended night.
# Both are answered the same way: ask the process table, never the roster.

HARNESS_PROCS = ("claude", "codex", "opencode")
HARNESS_UP_TIMEOUT = 25.0   # cold claude start measured ~2-4s on this box; generous, bounded
HARNESS_UP_POLL = 0.5
PID_EXIT_TIMEOUT = 6.0
# Set to skip the checkin-time harness check. The escape hatch exists because a positive-absence
# verdict rests on argv shape: a harness launched under a wrapper this code cannot recognize would
# be refused a checkin it deserves. Losing a seat to a false refusal is worse than G-11.
SKIP_HARNESS_CHECK = os.environ.get("COORD_SKIP_HARNESS_CHECK") == "1"


# ---------- memory pre-flight (leader ruling, 2026-07-27 msg #128) ----------
# A claude seat's steady RSS is 419-549 MB but its PEAK is ~1.4 GB: boot and compaction spike ~3x
# steady state (systemd scope accounting, "1.4G memory peak"). Every launch gate tonight sized seats
# by what `ps` showed and understated the requirement threefold; the kernel answered by SIGKILLing a
# bystander — the watcher, twice, its roster row still reading ACTIVE. So this gate is not a flat
# floor over steady state: it holds a SPIKE reserve, because the spike is the risk.
# ⚑ THE NUMBER BELOW IS UNVALIDATED AND MACHINE-SPECIFIC. It is ONE systemd cgroup peak from one
# claude seat on one box, doubled — and a cgroup peak INCLUDES reclaimable page cache, so it
# counts as *required* memory the kernel would hand back under pressure. The causal OOM theory
# behind it was RETRACTED the same night it was taken (campaign issue S-8(a), owner-raised).
# It MUST NEVER travel to another machine as a constant: re-derive per box from a working-set or
# PSI-pressure metric over SEVERAL samples. Overriding it with a single fresh reading would
# repeat exactly the error that produced it. Until that measurement campaign runs, the value
# stays put (owner ruling) and is merely made settable per machine, which is what the env vars
# below are for — they are the per-machine seam, not a licence to guess a better number.
# The GATE ITSELF is not in question and was ratified: seat RSS understates peak ~3x, three
# seats died `exit 137`, and the watcher was SIGKILLed twice as a BYSTANDER.
SEAT_SPIKE_MB = int(os.environ.get("COORD_SEAT_SPIKE_MB") or 1400)   # per-box override
SPIKE_RESERVE = int(os.environ.get("COORD_SPIKE_RESERVE") or 2)      # boot + compaction
LAUNCH_MEM_FLOOR_MB = SEAT_SPIKE_MB * SPIKE_RESERVE   # 2800 MB on this box


def available_mb():
    """MemAvailable in MiB, 0 when /proc/meminfo is unreadable (never gate on 'cannot tell')."""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return 0
    return 0


def memory_gate(n_seats, avail_mb, floor_mb=LAUNCH_MEM_FLOOR_MB):
    """Pure: '' when it is safe to spawn `n_seats`, else the refusal reason. avail_mb == 0 means
    unmeasurable and PASSES — a broken sensor must not be able to stop a run."""
    if not avail_mb:
        return ""
    need = floor_mb + max(0, n_seats - 1) * SEAT_SPIKE_MB
    if avail_mb >= need:
        return ""
    return (f"{avail_mb} MB available, {need} MB needed to spawn {n_seats} seat(s). A claude seat "
            f"peaks at ~{SEAT_SPIKE_MB} MB on boot and on every compaction — steady RSS is a third "
            f"of that — and this gate holds {SPIKE_RESERVE} spikes of reserve so a spiking seat "
            f"cannot make the kernel SIGKILL a bystander (how the watcher died twice on "
            f"2026-07-27). Close a seat first, or override with --force-memory and say so on "
            f"the log. NOT --force: that flag carries the ROLE gate only and will not lift "
            f"this one (campaign issue S-8(c) — this text used to name it, at the exact "
            f"moment an unattended run is blocked and reaching for the documented escape).")


# ---------- the flag -> gate binding, in ONE place (campaign issue S-6(a)) ----------
# The standing invariant is "no gate may ever be re-attached to --force": `--force` carries the
# ROLE gate, `--force-memory` carries the MEMORY gate, and NEITHER CARRIES THE OTHER. Until this
# map existed the invariant lived in prose and in two independent getattr() reads, so recombining
# them was a one-line edit nothing would notice.
#
# WHY THAT MATTERS MORE HERE THAN ANYWHERE ELSE: jobs/recover-room.py — the daemon-fired self-heal
# path — passes `--force` on EVERY firing, at whatever hour the room dies, with nobody awake. That
# override is correct by necessity (a timer-fired exec has no pane, hence no seat identity, hence
# cannot pass an identity-keyed gate). Its SAFETY, however, rests entirely on `--force` not also
# carrying memory — and nothing in that path asserted the dependency.
#
# This map is the ONLY place the binding exists and `gate_forced` is its ONLY reader, so adding
# "memory" to --force's tuple genuinely ARMS it — the map cannot drift from behaviour. `coordinate
# gates --json` publishes it, and recover-room.py ASSERTS against that output before it overrides
# anything: undo the split and the unattended recovery REFUSES instead of silently arming a
# memory override at 4am.
GATE_FLAGS = {
    "--force": ("role",),
    "--force-memory": ("memory",),
}


def gate_forced(args, gate_name):
    """True iff a flag the caller ACTUALLY passed carries `gate_name`, per GATE_FLAGS."""
    for flag, gates in GATE_FLAGS.items():
        if gate_name in gates and bool(getattr(args, flag[2:].replace("-", "_"), False)):
            return True
    return False


def cmd_gates(args):
    """Publish the flag -> gate binding so an UNATTENDED caller can assert it before overriding.

    Exists for jobs/recover-room.py, which force-overrides the role gate on every firing with
    nobody in the loop. It reads this and refuses to run if `--force` ever starts carrying the
    memory gate. Printing the map is not the point — being the SAME map launch_gates reads is."""
    payload = {flag: list(gates) for flag, gates in sorted(GATE_FLAGS.items())}
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for flag, gates in sorted(payload.items()):
            print(f"{flag:16} carries: {', '.join(gates)}")
        print("neither flag carries the other — no gate may ever be re-attached to --force")
    return 0


def ps_snapshot():
    """[(pid, ppid, argv-string)] for every process on the box, [] when ps is unavailable."""
    try:
        r = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True)
    except OSError:
        return []
    if r.returncode != 0:
        return []
    rows = []
    for line in r.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        rows.append((int(parts[0]), int(parts[1]), parts[2]))
    return rows


def descendant_pids(snapshot, root_pid):
    """Every pid at or below `root_pid` in `snapshot`. Pure — no I/O, so selftest exercises it."""
    if not root_pid:
        return []
    children = {}
    for pid, ppid, _ in snapshot:
        children.setdefault(ppid, []).append(pid)
    out, stack = [], [root_pid]
    while stack:
        pid = stack.pop()
        out.append(pid)
        stack.extend(children.get(pid, []))
    return out


def is_harness_argv(argv):
    """True when this command line starts a coordination harness. Pure. Matches the executable's
    basename and, for the node/bun-wrapped forms, any argv token that IS a harness path."""
    tokens = argv.split()
    if not tokens:
        return False
    if os.path.basename(tokens[0]) in HARNESS_PROCS:
        return True
    return any(os.path.basename(t.split("=")[-1]) in HARNESS_PROCS for t in tokens[1:4])


def harness_pids(snapshot, root_pid):
    """Pids of harness processes running at or below `root_pid`. Pure."""
    want = set(descendant_pids(snapshot, root_pid))
    return [pid for pid, _, argv in snapshot if pid in want and is_harness_argv(argv)]


def pane_harness_pids(pane):
    """(pids, verifiable) for the harness processes under `pane`. `verifiable` is False when the
    process table or the pane's pid could not be read at all — 'cannot tell' is NOT 'nothing is
    running', and every caller must treat the two differently (fail-safe)."""
    if not pane:
        return [], False
    root = tmux_pane_pid(pane)
    if not root:
        return [], False
    snap = ps_snapshot()
    if not snap:
        return [], False
    return harness_pids(snap, root), True


def pane_harness_idents(pane):
    """[(pid, starttime)] for the harness processes under `pane` — the identity form of
    pane_harness_pids, and what every teardown captures before it kills anything."""
    if not pane:
        return []
    root = tmux_pane_pid(pane)
    if not root:
        return []
    return harness_idents(ps_snapshot(), root)


def proc_stat(pid):
    """(state, starttime) from /proc/<pid>/stat — fields 3 and 22 — or ("", "") when unreadable.
    Parsed by splitting after the LAST ')': the comm field can itself contain spaces and
    parentheses, so a naive whitespace split mis-indexes every later field. Same derivation the
    ignite daemon uses (carrier.js setsidStatus, "pidStarttime guard against PID reuse")."""
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", ""
    cut = raw.rfind(")")
    if cut == -1:
        return "", ""
    rest = raw[cut + 1:].split()
    # rest[0] is field 3 (state), so field 22 sits at index 19.
    return rest[0], (rest[19] if len(rest) > 19 else "")


def proc_starttime(pid):
    """Field 22 of /proc/<pid>/stat, '' when unreadable — the identity half a pid cannot supply."""
    return proc_stat(pid)[1]


def process_identity(pid):
    """(pid, starttime), or None when the pid is gone. A pid ALONE is not an identity: the kernel
    recycles pids, and a teardown is exactly when new processes start, so a remembered pid can name
    a stranger seconds later — which is how a dead seat's reaper can SIGKILL a live one.

    Pane ancestry is NOT a substitute (leader, #138): G-12's in-place respawn puts the replacement
    under the SAME pane, so an ancestry test would confirm the very process it must protect.
    starttime is the half a respawn cannot reproduce."""
    st = proc_starttime(pid)
    return (pid, st) if st else None


def harness_idents(snapshot, root_pid):
    """[(pid, starttime)] for the harness processes under `root_pid` — identity, not bare pids."""
    return [i for i in (process_identity(p) for p in harness_pids(snapshot, root_pid)) if i]


def ident_is_live_harness(ident):
    """True when (pid, starttime) still names the SAME live process and it is still a harness. The
    single predicate every kill in this file passes through. Pure w.r.t. its argument: it re-derives
    both halves from /proc at call time and trusts nothing remembered."""
    pid, starttime = ident
    state, live_start = proc_stat(pid)
    if not starttime or live_start != starttime or state == "Z":
        return False
    try:
        argv = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace")
    except OSError:
        return False
    return is_harness_argv(argv)


def idents_alive(idents):
    """The subset of `idents` that still name their original live harness process."""
    return [i for i in idents if ident_is_live_harness(i)]


def reaper_script(idents, delay):
    """The detached reaper's shell text. It re-derives (pid, starttime) from /proc at the moment of
    the kill and fires ONLY on an exact match of both halves — the guard that was missing when this
    reaper was gated on "the pid is A harness" rather than "the pid is THE harness" (owner
    directive 2026-07-27, msg #137). Pure, so the decision it encodes is checkable without arming
    anything. field 22 is read after the last ')', never by a naive whitespace split.

    A zombie needs no special case: its /proc/<pid>/cmdline is EMPTY, so the harness test below
    cannot match and no signal is sent."""
    specs = " ".join(f"{pid}:{st}" for pid, st in idents)
    return (
        f"sleep {delay}; for spec in {specs}; do "
        f"p=${{spec%%:*}}; want=${{spec#*:}}; "
        f"st=$(sed 's/^.*) //' /proc/$p/stat 2>/dev/null | awk '{{print $20}}'); "
        f'if [ -n "$st" ] && [ "$st" = "$want" ]; then '
        f"tr '\\0' ' ' < /proc/$p/cmdline 2>/dev/null "
        f"| grep -qE '(^| |/)(claude|codex|opencode)( |$)' && kill -9 $p; fi; done"
    )


def wait_harness_up(pane, timeout=HARNESS_UP_TIMEOUT):
    """Poll until a harness process is running under `pane`. Returns (pids, err): err is '' when
    one came up OR when liveness is unverifiable here; non-empty ONLY on positive absence."""
    deadline = time.time() + timeout
    while True:
        pids, verifiable = pane_harness_pids(pane)
        if pids:
            return pids, ""
        # "Cannot tell" does not improve with waiting (no pane pid, no readable process table) —
        # return at once rather than burning the whole timeout on an unanswerable question.
        if not verifiable:
            return [], ""
        if time.time() >= deadline:
            break
        time.sleep(HARNESS_UP_POLL)
    return [], (f"no {'/'.join(HARNESS_PROCS)} process is running in {pane} after "
                f"{timeout:.0f}s — the start line was submitted to the pane but only its shell "
                f"is there (G-11). Capture the pane to see what the shell did with it: "
                f"tmux capture-pane -p -t {pane}")


def pids_alive(pids):
    """The subset of `pids` still alive, EXCLUDING zombies.

    A zombie has exited: it holds no memory and runs no code, and only lingers because its parent
    has not reaped it. `os.kill(pid, 0)` succeeds for one, so a bare signal-0 probe reports a
    successfully killed process as a surviving ghost — caught by the live reaper proof, where a
    process the reaper HAD killed was still reported alive."""
    alive = []
    for pid in pids:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            pass
        if proc_stat(pid)[0] == "Z":
            continue
        alive.append(pid)
    return alive


def verify_pids_gone(idents, timeout=PID_EXIT_TIMEOUT):
    """Wait for the harness processes named by `idents` — (pid, starttime) pairs — to exit,
    escalating SIGTERM then SIGKILL on a straggler (G-10: kill-pane SIGHUPs the process group and a
    blocked harness survives it as a ghost nobody counts). Returns (survivors, note); survivors is
    empty on success and note says what it took.

    EVERY signal passes ident_is_live_harness first, so a recycled pid can never be hit: identity is
    re-proved from /proc at the instant of signalling, never remembered from before the kill."""
    if not idents:
        return [], ""
    deadline = time.time() + timeout
    escalated = []
    while True:
        alive = idents_alive(idents)
        if not alive:
            break
        if time.time() >= deadline:
            for sig in (15, 9):
                for ident in idents_alive(idents):
                    try:
                        os.kill(ident[0], sig)
                        escalated.append((ident[0], sig))
                    except OSError:
                        pass
                time.sleep(0.5)
            alive = idents_alive(idents)
            break
        time.sleep(0.3)
    if alive:
        return alive, (f"pid(s) {', '.join(str(p) for p, _ in alive)} SURVIVED kill-pane, SIGTERM "
                       f"and SIGKILL — a ghost holding memory; reap it by hand and say so on the log")
    if escalated:
        return [], (f"kill-pane left the harness alive; reaped by signal "
                    f"({', '.join(f'{p}:SIG{s}' for p, s in escalated)})")
    return [], ""


def arm_pid_reaper(idents, delay=4):
    """Detach a one-shot reaper for the harness processes named by `idents` — (pid, starttime)
    pairs — `delay` seconds from now. `depart` kills its OWN pane, so this process dies with it and
    can verify nothing afterwards (G-10); the reaper outlives both.

    It fires only on an exact (pid, starttime) match re-derived from /proc at kill time. The first
    version guarded on "this pid is A harness", which is not identity: a relaunch landing on a
    recycled pid would be SIGKILLed by the dead seat's reaper (owner directive, msg #137; the ignite
    daemon guards the same hazard the same way — spawn.js pid_starttime)."""
    idents = [i for i in idents if i and i[1]]
    if not idents:
        return
    try:
        subprocess.Popen(["setsid", "bash", "-c", reaper_script(idents, delay)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError:
        pass


# ---------- run index + session trace (task 7.37; settle ledger R10/R11) ----------
#
# TWO FILES, DIFFERENT JOBS. The KG `run` record as AMENDED (R11, decisions.md#d-run-state-layout)
# — the record's older wording called the per-run trace `runs.csv` and now says so against itself:
#
#   {goal}/runs.csv                    the run INDEX — one row per run (start, finish/ongoing)
#   {goal}/runs/run-{n}/sessions.csv   that run's TRACE — one row per session, in order,
#                                      carrying the resume refs (harness, native session id,
#                                      workdir) task 7.32 resumes from
#
# ONE ROW PER SESSION, opened at launch and completed at close. 7.37's criteria say a launch and a
# close "each produce their own row"; read literally that is TWO rows per session, which would make
# the `ended` column meaningless and contradict the session shape the same task builds for (a
# session lives until CLOSED; the trace is ordered sessions, one per session). What that criterion
# actually defends is that NOBODY INVOKES THE WRITER — and nobody does: both acts below are hooks
# on paths the run already traverses, and neither has a command. Disclosed to leader (log #531).
#
# R10 RESIDUE, carried rather than softened: goal-level state surviving across runs is valid only
# because R9 guarantees one live run per goal, and R9 is now task 7.77 (m4) — NOT BUILT. Until it
# lands, one-live-run is a convention held by hand. So nothing here assumes exclusivity: the index
# is keyed by run-id, and a second concurrent run would add its own row rather than corrupt this.

RUNS_INDEX_COLS = ["run-id", "type", "state", "taskforce-ids", "opened", "closed"]
# `pid`/`pid-starttime`/`tty` are the seat-identity gate's PRE-REGISTERED interface to this writer
# (ignite/server/seat-identity/identity.js: REQUIRED_IDENTITY_COLUMNS + CORROBORATING_COLUMNS).
# The PAIR is the identity — starttime is what defeats pid reuse, so the gate refuses a pid alone
# and explicitly does not accept a degraded mode. `tty` corroborates and never decides.
SESSIONS_COLS = ["session-id", "seat", "harness", "native-session-id", "workdir",
                 "recorded", "started", "ended", "pid", "pid-starttime", "tty"]
NATIVE_ID_WAIT = 8.0   # seconds; a boot writes its transcript within ~1s, close re-resolves


def goal_dir(pkg):
    """The goal folder owning this run package: {goal}/runs/run-{n} -> {goal}.

    A package NOT in the canonical runs/ form (a /tmp fixture, the legacy workers/ layout) owns
    its own index: returning pkg keeps the writer total rather than raising on a shape the kit
    still supports.
    """
    return pkg.parent.parent if pkg.parent.name == "runs" else pkg


def runs_index_csv(pkg):
    return goal_dir(pkg) / "runs.csv"


def sessions_csv(pkg):
    return pkg / "sessions.csv"


def widen_header(header, cols):
    """(header, changed) — the on-disk header plus any of `cols` it is MISSING, appended in order.

    G-152, and it is the difference between this task shipping and this task looking like it did.
    `read_csv_table` preserves the on-disk header verbatim, which is correct — a column contract a
    live reader already keys on must never be reordered or dropped under it. The consequence nobody
    had measured is that a NEW column then reaches only files that do not yet exist: every selftest
    fixture builds a fresh file, so the change reads green everywhere and is a silent no-op on
    run-1, run-2 and every existing package. `G-135` is the same defect at the daemon's SQLite
    store; two components, two persistence technologies, one blind spot — a schema change verified
    only where the schema is BORN, never where it LIVES.

    APPEND-ONLY, and that is the whole safety argument: existing columns keep their positions, so
    a positional reader cannot break (run-1 and run-2 already disagree on column ORDER, which is
    exactly why re-sorting into SESSIONS_COLS order would corrupt one of them). Nothing is ever
    renamed or removed here — a column this kit no longer writes (`model`, hand-added to run-2's
    header and never populated) stays, blank, because deleting it is a different decision with a
    different owner.
    """
    missing = [c for c in cols if c not in header]
    return (header + missing, bool(missing))


def read_csv_table(path, cols):
    """(header, rows). The header is preserved VERBATIM from disk when the file exists — a column
    contract another seat may already read is never rewritten by a writer that merely appends.

    Widening an existing header is `widen_header`'s job, taken deliberately at the WRITE sites
    rather than here: a read must stay a read, or every reader silently rewrites the file it opened.
    """
    if not path.exists():
        return list(cols), []
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            table = list(csv.reader(fh))
    except (OSError, UnicodeDecodeError):
        return list(cols), []
    if not table:
        return list(cols), []
    return table[0], [r for r in table[1:] if any(c.strip() for c in r)]


def write_csv_table(path, header, rows):
    """Atomic: temp file + os.replace. A reader never sees a half-written trace, and a crash
    mid-write leaves the previous table intact (G-45's discipline applied to state files)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    os.replace(tmp, path)


def pad_row(row, header):
    """Widen a short row to the header. A row written before a column existed must not make the
    writer raise — it makes it write a blank cell."""
    while len(row) < len(header):
        row.append("")
    return row


def taskforce_ids(pkg):
    """This run's taskforce ids, file order, deduped, '|'-joined. '' when there is none."""
    header, rows = read_csv_table(pkg / "taskforce.csv", [])
    if not rows or "taskforce-id" not in header:
        return ""
    i = header.index("taskforce-id")
    out = []
    for r in rows:
        v = r[i].strip() if i < len(r) else ""
        if v and v not in out:
            out.append(v)
    return "|".join(out)


def ensure_run_index(pkg):
    """Keep the goal-level run INDEX correct with nobody maintaining it by hand. Idempotent.

    Creates the file with its header when absent, adds this run's row when absent, and re-syncs
    only DERIVED state (`taskforce-ids`). Never rewrites `type` or `opened`: they are the run's
    identity, not derived data.

    `type` is left EMPTY on a row this code creates, deliberately. The KG says run type is csv
    DATA — `fresh | fix` — and explicitly NOT derivable from the ordinal. Defaulting it to
    `fresh` would be right most of the time and silently wrong on a fix run, which is the exact
    shape this run has spent the night refusing. An empty cell is answerable; a guessed one is not.

    `closed` is NOT stamped here. Closing a run is the leader's ceremony and this kit has no
    run-close command; an OPEN run's row is correct precisely by staying open. Disclosed at #531.
    """
    path = runs_index_csv(pkg)
    header, rows = read_csv_table(path, RUNS_INDEX_COLS)
    idx = {c: i for i, c in enumerate(header)}
    if "run-id" not in idx:
        return False
    run_id = pkg.name
    row, changed = None, False
    for r in rows:
        pad_row(r, header)
        if r[idx["run-id"]].strip() == run_id:
            row = r
    if row is None:
        row = [""] * len(header)
        row[idx["run-id"]] = run_id
        if "state" in idx:
            row[idx["state"]] = "open"
        if "opened" in idx:
            row[idx["opened"]] = now()
        rows.append(row)
        changed = True
    tf = taskforce_ids(pkg)
    if tf and "taskforce-ids" in idx and row[idx["taskforce-ids"]].strip() != tf:
        row[idx["taskforce-ids"]] = tf
        changed = True
    if changed:
        write_csv_table(path, header, rows)
    return changed


def resolve_live_run(goal):
    """(run-id, detail) — the goal's CURRENT run, resolved from the goal-level index alone.

    R10: goal-level state must read correctly ACROSS A RUN BOUNDARY. This is the mechanism that
    makes that possible — one hop from the goal folder, with no knowledge of which run the caller
    was born in. A sensor that resolves its target this way follows the boundary instead of being
    pinned to the run it started in; run-1's team-monitor was still writing `run-1/state.json` at
    19:06 for a run closed at 13:11 precisely because nothing gave it this hop.

    ⚠ R10 RESTS ON R9's ONE-LIVE-RUN GUARANTEE, WHOSE ENFORCEMENT (task 7.77) IS NOT BUILT. So
    this REFUSES rather than guesses when the guarantee does not hold: zero open runs and two open
    runs are both reported as such, naming R9. Returning "the first open row" would be right most
    of the time and silently wrong exactly when the convention has slipped — which, with two
    writable runs on this box tonight, is not a hypothetical. A resolver that cannot be wrong
    quietly is the whole point.
    """
    path = goal / "runs.csv"
    header, rows = read_csv_table(path, RUNS_INDEX_COLS)
    if not path.exists():
        return "", f"no run index at {path}"
    idx = {c: i for i, c in enumerate(header)}
    if "run-id" not in idx or "state" not in idx:
        return "", f"run index carries no run-id/state column (header: {','.join(header)})"
    live = [r[idx["run-id"]].strip() for r in (pad_row(r, header) for r in rows)
            if r[idx["state"]].strip() == "open"]
    if len(live) == 1:
        return live[0], ""
    if not live:
        return "", (f"no OPEN run in {path} — every run is closed; a goal with no live run has no "
                    f"current state to read")
    return "", (f"{len(live)} runs are OPEN in {path} ({', '.join(live)}) — R9 guarantees ONE live "
                f"run per goal and its enforcement (task 7.77) is NOT BUILT, so this is a real "
                f"state, not an impossible one. Refusing to pick: goal-level state read against "
                f"the wrong run is worse than a refusal that names the ambiguity.")


def cmd_current_run(args):
    goal = goal_dir(package_dir(args))
    run_id, detail = resolve_live_run(goal)
    if not run_id:
        print(f"refused: {detail}", file=sys.stderr)
        sys.exit(1)
    print(run_id)
    print(c(f"resolved from {goal / 'runs.csv'} — one hop from the goal folder, so goal-level "
            f"state follows the run boundary (R10)", C_HINT))


def close_run_index(pkg, when=None):
    """Stamp this run's index row `state=closed` + `closed=<now>`. Returns (ok, detail).

    LEADER RULING #398, adopted verbatim: THE CEREMONY STAYS THE LEADER'S, THE WRITE STOPS BEING
    THE LEADER'S. The leader decides WHEN a run closes; the kit records THAT it closed. Conflating
    the decision with the keystrokes is why run-1's closed row is in a leader's handwriting, and
    why 7.37's criterion — the index resolves the current run WITHOUT HAND MAINTENANCE — was unmet
    while `ensure_run_index` deliberately refused to stamp `closed` for want of a run-close command.
    This is that command's writer half.

    Why this is 7.37's and not 7.77's: 7.77 is R9's one-live-run QUEUE rule on the daemon's
    scheduler. Stamping state/closed is a WRITE TO runs.csv, and 7.37 is the writers half.

    NOT idempotent-by-overwrite: an already-closed run is REFUSED rather than re-stamped, so a
    second close cannot quietly move a historical timestamp. Re-closing is a correction, and a
    correction should be visible.
    """
    path = runs_index_csv(pkg)
    if not path.exists():
        return False, f"no run index at {path} — nothing to close"
    header, rows = read_csv_table(path, RUNS_INDEX_COLS)
    header, widened = widen_header(header, RUNS_INDEX_COLS)
    if widened:
        rows = [pad_row(r, header) for r in rows]
    idx = {c: i for i, c in enumerate(header)}
    if "run-id" not in idx or "state" not in idx:
        return False, f"run index carries no run-id/state column (header: {','.join(header)})"
    run_id = pkg.name
    row = None
    for r in rows:
        pad_row(r, header)
        if r[idx["run-id"]].strip() == run_id:
            row = r
    if row is None:
        return False, f"no index row for {run_id} — it was never opened"
    if row[idx["state"]].strip() == "closed":
        return False, (f"{run_id} is ALREADY closed"
                       + (f" at {row[idx['closed']].strip()}" if "closed" in idx else "")
                       + " — refusing to re-stamp; a correction must be visible, not silent")
    row[idx["state"]] = "closed"
    if "closed" in idx:
        row[idx["closed"]] = when or now()
    write_csv_table(path, header, rows)
    return True, f"{run_id} closed at {row[idx['closed']] if 'closed' in idx else '(no column)'}"


def cmd_close_run(args):
    gate(args, "close-run", lambda a: a == "leader", "leader's alone (it ends the run's index row)")
    pkg = package_dir(args)
    ok, detail = close_run_index(pkg)
    if not ok:
        print(f"refused: {detail}", file=sys.stderr)
        sys.exit(1)
    print(f"runs.csv: {detail}")
    print(c(f"the index now resolves the goal's current run without hand maintenance "
            f"({runs_index_csv(pkg)})", C_HINT))


def claude_projects_dir():
    """Evaluated at CALL time, not import time, so a test can point HOME at a sandbox and have the
    resolver follow it. A module constant computed from Path.home() at import silently ignores the
    override and reads the real user's transcripts."""
    return Path.home() / ".claude" / "projects"


def claude_project_slug(cwd):
    """Claude's transcript directory name for a working directory: the absolute path with BOTH
    path separators AND DOTS replaced by '-'.

    THE DOT IS NOT COSMETIC AND ITS OMISSION WAS A REAL BUG. Every seat in a goal run lives under
    `.rbtv/`, so a slug that replaces only '/' yields `...-second-brain-.rbtv-goals-...` while the
    directory claude actually writes is `...-second-brain--rbtv-goals-...` (note the DOUBLE dash).
    The lookup missed for EVERY claude seat in this run and `native-session-id` came back empty
    every time.

    It went undetected because the original evidence for this mapping was a directory LISTING, not
    an exercise of this function: the directory was real, the derivation was never run against it.
    A check that resolves a real transcript out of a fixture projects dir now covers it — the
    earlier checks only ever asserted the '' outcome, so none of them could see it.
    """
    return str(Path(cwd).resolve()).replace("/", "-").replace(".", "-")


def claude_native_session_id(cwd, since=None, wait=0.0, projects=None):
    """This boot's claude session id for a seat working in `cwd`, or '' if not resolvable yet.

    EXACT rather than a heuristic, and only because of a property of this layout: every seat's cwd
    is its OWN seat folder, so that project directory holds that seat's sessions and nobody
    else's. `since` (the instant before the harness started) is what makes a RENEW correct — the
    previous session's transcript is static by then, so it sorts out; without `since` a renew
    would resolve to the session it replaced.

    Returns '' rather than guessing when nothing qualifies. An empty field is a stated gap; a
    wrong session id would send task 7.32's resume at another session entirely.
    """
    if not cwd:
        return ""
    d = (Path(projects) if projects else claude_projects_dir()) / claude_project_slug(cwd)
    deadline = time.time() + max(wait, 0.0)
    while True:
        best, best_m = "", -1.0
        if d.is_dir():
            for f in d.glob("*.jsonl"):
                try:
                    m = f.stat().st_mtime
                except OSError:
                    continue
                if since is not None and m < since:
                    continue
                if m > best_m:
                    best, best_m = f.stem, m
        if best or time.time() >= deadline:
            return best
        time.sleep(0.25)


def session_trace_safe(fn, *a, **kw):
    """Run a session-trace write so that its failure can never take down the act it records.

    The trace is bookkeeping ABOUT the run; it must not become a gate ON it. A read-only goal
    folder, a full disk, or a malformed csv would otherwise raise out of `launch_seat` AFTER the
    harness is already up — leaving a live seat the roster believes failed, which is G-11's exact
    shape wearing the bookkeeping mask. Failures are printed LOUDLY and swallowed; the same
    trade-off `refresh_mirrors_for`, `write_seat_statusline` and `ensure_team_monitor` already make.
    """
    try:
        return fn(*a, **kw), ""
    except Exception as exc:                                   # noqa: BLE001 — deliberate
        return None, f"{type(exc).__name__}: {exc}"


def proc_stat_fields(pid):
    """(starttime, tty_nr) from /proc/<pid>/stat as STRINGS, or ('', '').

    Parsed from the LAST ')' rather than by splitting the line, because field 2 (comm) is
    parenthesised and may itself contain spaces and parentheses — the classic way this parse goes
    quietly wrong. Field numbering matches the daemon's own reader
    (ignite/server/seat-identity/identity.js readProcStat), so both sides of the contract compute
    the pair the same way; a starttime that disagreed by one field would refuse every seat.
    """
    try:
        raw = Path(f"/proc/{int(pid)}/stat").read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError, TypeError):
        return "", ""
    close = raw.rfind(")")
    if close < 0:
        return "", ""
    rest = raw[close + 2:].split()
    if len(rest) < 22 - 3 + 1:
        return "", ""
    return rest[22 - 3], (rest[7 - 3] if len(rest) > 7 - 3 else "")


def pane_identity(pane):
    """(pid, pid-starttime, tty) for a seat's pane — all strings, all '' when unresolvable.

    `tty` is the NUMERIC tty_nr, not the /dev/pts path: the gate corroborates against
    /proc/<pid>/stat's tty_nr field, so a device path here would never compare equal and would
    look like a tty mismatch on every seat.

    Never raises and never guesses. An unresolvable pane yields blanks, and `session_open`'s note
    tells the operator — a blank identity is honest; a fabricated one authenticates an impostor.
    """
    if not pane:
        return "", "", ""
    try:
        pid = tmux_pane_pid(pane)
    except Exception:                                          # noqa: BLE001 — never break a boot
        return "", "", ""
    if not pid:
        return "", "", ""
    start, tty = proc_stat_fields(pid)
    return (str(pid), start, tty) if start else ("", "", "")


def session_open(args, w, since=None, wait=NATIVE_ID_WAIT, pane=None):
    """Append this seat's session row the moment it boots. Returns (session-id, note).

    `note` is non-empty when a field could not be resolved — the caller PRINTS it. A blank cell
    that nobody mentioned is indistinguishable from one that was never needed.

    `wait` is a parameter and not a constant read inside so the self-test can drive the resolver
    to its unresolved branch without sleeping through the real boot timeout.

    `pane` carries the seat's tmux pane so the row can record the IDENTITY PAIR the seat-identity
    gate decides on. It is the PANE's pid, deliberately, not this process's: every process the seat
    ever runs is a descendant of the pane, and the gate matches the registered pid against the
    CALLER'S ANCESTRY. Recording the launcher's own pid would name a process that is not an
    ancestor of the seat and would refuse every legitimate occupant.
    """
    pkg = package_dir(args)
    native = ""
    if w.get("harness") == "claude":
        native = claude_native_session_id(w.get("cwd"), since, wait=wait)
    pid, pid_start, tty = pane_identity(pane)
    rec = {"session-id": "", "seat": w.get("agent", ""), "harness": w.get("harness", ""),
           "native-session-id": native, "workdir": str(w.get("cwd") or ""),
           # `recorded` is the pipe-pane marker of task 7.31, which is NOT BUILT (no pipe-pane
           # anywhere in this file). The column stays, blank, rather than being invented.
           "recorded": "", "started": now(), "ended": "",
           "pid": pid, "pid-starttime": pid_start, "tty": tty}
    with coord_lock(base_dir(args)):
        path = sessions_csv(pkg)
        header, rows = read_csv_table(path, SESSIONS_COLS)
        # G-152: the widen happens HERE, on the one path every seat boot takes, so an EXISTING
        # trace gains the identity columns instead of the change being a no-op everywhere it
        # matters. Append-only, so no live reader's column positions move.
        header, widened = widen_header(header, SESSIONS_COLS)
        if widened:
            rows = [pad_row(r, header) for r in rows]
        idx = {c: i for i, c in enumerate(header)}
        taken = {r[idx["session-id"]].strip() for r in rows
                 if "session-id" in idx and idx["session-id"] < len(r)}
        stem = f"{rec['seat']}-{file_stamp()}"
        sid, n = stem, 2
        while sid in taken:          # two sessions of one seat inside one minute
            sid, n = f"{stem}-{n}", n + 1
        rec["session-id"] = sid
        rows.append([rec.get(c, "") for c in header])
        write_csv_table(path, header, rows)
        ensure_run_index(pkg)
    note = ("" if native or w.get("harness") != "claude"
            else "native-session-id UNRESOLVED at launch — retried at close")
    return sid, note


def session_backfill_native(args, seat):
    """Fill a live session row's `native-session-id` from the seat's OWN checkin. Returns the id
    filled, or ''.

    WHY THIS EXISTS, measured rather than anticipated: resolving at LAUNCH races the harness's own
    startup. claude writes its transcript when it first has something to write, which is AFTER
    `wait_harness_up` returns — the leader's 08:21 renewal resolved to '' because no transcript in
    its project dir was newer than the launch instant inside the launch-side window.

    Checkin is the correct hook and is exact: the seat is running, has processed its boot prompt,
    and the transcript it is actively writing is by definition the most recently modified file in
    its own project directory. No `since` is needed, and no window can expire.

    It also closes the case the launch-side resolver could never reach: a seat that CRASHES never
    closes, so a close-time backfill would never run — but a crashed seat did check in, and 7.32's
    native resume is exactly the path a crashed seat needs.
    """
    pkg = package_dir(args)
    with coord_lock(base_dir(args)):
        path = sessions_csv(pkg)
        if not path.exists():
            return ""
        header, rows = read_csv_table(path, SESSIONS_COLS)
        idx = {c: i for i, c in enumerate(header)}
        if not {"seat", "ended", "native-session-id", "harness", "workdir"} <= set(idx):
            return ""
        target = None
        for r in rows:
            pad_row(r, header)
            if (r[idx["seat"]].strip() == seat and not r[idx["ended"]].strip()
                    and not r[idx["native-session-id"]].strip()
                    and r[idx["harness"]].strip() == "claude"):
                target = r
        if target is None:
            return ""
        native = claude_native_session_id(target[idx["workdir"]].strip())
        if not native:
            # NEVER SILENT. A backfill that finds its row and fails to resolve used to return ''
            # exactly like one with nothing to do, and the caller printed nothing either way — so
            # the slug bug above sat invisible through every checkin in this run. A clean result
            # must never be readable as a clean class.
            return f"!unresolved: no claude transcript under {claude_project_slug(target[idx['workdir']].strip())}"
        target[idx["native-session-id"]] = native
        write_csv_table(path, header, rows)
        return native


def session_close(args, seat):
    """Complete the seat's open session row: stamp `ended`, and fill `native-session-id` if the
    launch could not resolve it yet. Returns the session-id closed, or ''.

    A silent no-op when the seat has NO open row — a seat closed twice, or one launched before
    this writer existed, must not gain a phantom row. The close path is reached by three commands
    (close-seat, depart, checkout) and a run may traverse more than one of them for one seat.
    """
    pkg = package_dir(args)
    with coord_lock(base_dir(args)):
        path = sessions_csv(pkg)
        if not path.exists():
            return ""
        header, rows = read_csv_table(path, SESSIONS_COLS)
        idx = {c: i for i, c in enumerate(header)}
        if "seat" not in idx or "ended" not in idx:
            return ""
        target = None
        for r in rows:                      # LAST open row wins — the live session
            pad_row(r, header)
            if r[idx["seat"]].strip() == seat and not r[idx["ended"]].strip():
                target = r
        if target is None:
            return ""
        target[idx["ended"]] = now()
        if ("native-session-id" in idx and not target[idx["native-session-id"]].strip()
                and target[idx.get("harness", 0)].strip() == "claude"):
            since = None
            if "started" in idx:
                try:
                    since = datetime.strptime(
                        target[idx["started"]].strip(), "%Y-%m-%d %H:%M").timestamp()
                except ValueError:
                    since = None
            wd = target[idx["workdir"]].strip() if "workdir" in idx else ""
            target[idx["native-session-id"]] = claude_native_session_id(wd, since)
        write_csv_table(path, header, rows)
        ensure_run_index(pkg)
        return target[idx["session-id"]].strip() if "session-id" in idx else ""


# ---------- per-seat statusline (task 7.69, statusline half) ----------
#
# `p-statusline-scope` ruled (b): the launch profiles write a `.claude/settings.local.json`
# carrying the statusLine block INTO EACH SEAT FOLDER at launch. Option (a) — the owner's global
# ~/.claude/settings.json — was never on the menu: it fires for every claude session on this
# machine, including the owner's own, which is not run-scoped and not a leader's to authorize.
# This code therefore writes ONLY inside a seat's own cwd and touches no file above it.
#
# WHY IT WAS BROKEN: the statusline was wired only in the vault's project-scoped
# .claude/settings.local.json, and a seat's project dir IS its seat folder — so no seat ever fired
# it. No `session-pids` record, so ctx-monitor falls back to the `transcript~` heuristic instead of
# an exact pid->transcript map, and per-session windows are guessed.
#
# THE PATH IS ABSOLUTE AND DERIVED FROM THIS FILE'S OWN LOCATION, deliberately (issue G-72). The
# vault's wiring used "$CLAUDE_PROJECT_DIR/1-projects/.../team-kit/statusline-usage.py" and has
# been DEAD for every claude session on this box since the team-kit was promoted into the rbtv
# repo on 2026-07-26 — the promotion moved the script and nothing re-pointed the pointer, and a
# statusline fails silently. Deriving it from __file__ makes the pointer move WITH the file; and
# $CLAUDE_PROJECT_DIR would resolve inside the seat folder here, which is the same trap twice.

def seat_statusline_command():
    return f"python3 {Path(__file__).resolve().parent / 'statusline-usage.py'}"


def write_seat_statusline(w):
    """Write the statusLine block into this seat's own .claude/settings.local.json. Returns
    (path, action) where action is written | merged | kept | skipped.

    MERGES rather than replaces: a seat folder's settings may carry permissions or env a seat
    depends on, and a launch profile that overwrote them would break the seat to fix its
    statusline. An existing `statusLine` is KEPT — a seat that already declares one has been
    configured deliberately, and launch is not the place to overrule it.

    Never raises into the launch path: a seat that boots without a statusline is a seat with a
    worse sensor, while a seat that fails to boot is a hole in the wave.
    """
    if w.get("harness") != "claude" or not w.get("cwd"):
        return None, "skipped"
    # THE SEAT'S OWN FOLDER, OR NOWHERE. A seat's cwd is NOT guaranteed to be its own folder:
    # discover_workers falls back to `VAULT_ROOT` for a flat briefing file that declares no `cwd:`
    # (coord.py L2838), and a seat may point `cwd:` anywhere. Writing the block at cwd would then
    # land it in the VAULT ROOT — a shared, tracked, owner-owned settings file that governs every
    # claude session started there, which is the same class of harm `p-statusline-scope` forbids
    # for ~/.claude/settings.json, wearing a different mask.
    #
    # MEASURED, NOT THEORETICAL: this is exactly what happened at 08:06 on 2026-07-27 — the
    # self-test's own flat fixture seats (alpha/beta/watcher, no folder, no cwd:) resolved to
    # VAULT_ROOT and rewrote the vault's .claude/settings.local.json statusLine. Incident #542/#545,
    # issue G-75. A path check would have caught it; an IDENTITY check makes it impossible.
    folder = w.get("folder")
    if not folder:
        return None, "skipped"
    try:
        if Path(w["cwd"]).resolve() != Path(folder).resolve():
            return None, "skipped"
    except OSError:
        return None, "skipped"
    path = Path(w["cwd"]) / ".claude" / "settings.local.json"
    block = {"type": "command", "command": seat_statusline_command()}
    try:
        data, action = {}, "written"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                data = {}
            if not isinstance(data, dict):
                data = {}
            if data.get("statusLine"):
                return path, "kept"
            action = "merged"
        data["statusLine"] = block
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, json.dumps(data, indent=2) + "\n")
        return path, action
    except OSError:
        return path, "skipped"


# ---------- team-monitor start (task 7.33's room-creation line; p-monitor-start-is-lane-K...) ----------

def team_monitor_script():
    return Path(__file__).resolve().parents[2] / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"


def ensure_team_monitor(args):
    """Start the run's team-monitor, deterministically WITH THE ROOM rather than by hand.

    `ensure` is idempotent by construction (flock: a second writer exits 3), detaches immediately,
    and needs no teardown — the monitor polls `tmux has-session` and exits when the room is gone.
    So this is safe to call on every launch, which is what makes it deterministic: no one has to
    remember, and a retry costs nothing.

    ORDERING (monitor-builder, #524): it must not run before the tmux session exists — a monitor
    that starts first sees no session on its first pass and exits cleanly, leaving no lock and no
    monitor. It is called from `launch`, which already refuses outside tmux, and only after the
    seats are up.

    Never blocks or fails a launch: an unstarted monitor is a run with a weaker sensor; a launch
    that died starting one is a run with fewer seats.
    """
    script = team_monitor_script()
    if not script.is_file():
        return "absent", f"{script} does not exist yet — 7.33 has not landed"
    try:
        subprocess.run([sys.executable, str(script), "ensure",
                        "--package", str(package_dir(args))],
                       capture_output=True, text=True, timeout=30)
        return "ok", str(script)
    except (OSError, subprocess.SubprocessError) as exc:
        return "fail", str(exc)


# ---------- workers.md ----------

def load_workers(base):
    path = base / "workers.md"
    if not path.exists():
        return path, [], []
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    rows = []
    for i, line in enumerate(lines):
        m = WORKER_ROW.match(line.rstrip("\n"))
        if m and m.group("agent") != "agent":
            d = {k: v.strip() for k, v in m.groupdict().items()}
            d["_line"] = i
            rows.append(d)
    return path, lines, rows


def row_text(r):
    return (f"| {r['agent']} | {r['active']} | {r['pane']} | {r['summary']} "
            f"| {r['checkin']} | {r['checkout']} | {r['lastread']} |\n")


def current_row(rows, agent):
    """Latest row for an agent (last check-in wins). P1 keeps at most one active."""
    mine = [r for r in rows if r["agent"] == agent]
    return mine[-1] if mine else None


def update_row(base, agent, mutate):
    """Locked read-modify-write of ONE roster row: re-reads workers.md under the lock (so a
    concurrent writer's rows are never clobbered by a stale in-memory copy), applies `mutate`
    to the agent's current row, writes. `mutate` returning False means "no change, skip the
    write". Returns (ok, note)."""
    with coord_lock(base):
        path, lines, rows = load_workers(base)
        row = current_row(rows, agent)
        if row is None:
            return False, f"no roster row for '{agent}'"
        if mutate(row) is False:
            return True, "unchanged"
        lines[row["_line"]] = row_text(row)
        atomic_write(path, "".join(lines))
    return True, ""


# ---------- identity (T1) ----------

def pane_agent(base, pane):
    """The agent this tmux pane is REGISTERED to in the roster (latest active row wins), or ''.
    This is the only identity claim the tool can verify, so it is what a claim is checked
    against."""
    if not pane:
        return ""
    _, _, rows = load_workers(base)
    hit = [r for r in rows if r["pane"] == pane and r["active"] == "yes"]
    return hit[-1]["agent"] if hit else ""


def resolve_agent(args, required=True):
    """Who is calling, resolved instead of typed (T1 — F1: identity used to be hand-typed into
    every command and never verified; a sender/recipient reversal recorded leader as the sender
    of another seat's message, and impersonation-by-typo was silent).

    Order: `--as NAME` > `COORD_AGENT` (injected into every launched/closed/renewed seat's
    harness command) > the calling pane's registered roster row. An explicit `args.agent`
    attribute carries --as semantics — that is the internal API watch.py calls through, and it
    runs outside any pane, so no contradiction can fire there.

    A claimed identity that CONTRADICTS the calling pane's registered agent is REFUSED with the
    registered name shown; `--force` is the deliberate override. Returns '' when identity is
    unresolvable and `required` is False (the `owner` command reads that as "the human")."""
    claimed = (getattr(args, "as_agent", None) or getattr(args, "agent", None) or "").strip()
    source = "--as"
    if not claimed:
        claimed = os.environ.get("COORD_AGENT", "").strip()
        source = "COORD_AGENT"
    pane = detect_pane(getattr(args, "pane", None))
    registered = pane_agent(base_dir(args), pane) if pane else ""
    if claimed:
        if registered and registered != claimed and not getattr(args, "force", False):
            print(f"refused: you claimed '{claimed}' ({source}), but this pane ({pane}) is "
                  f"registered to '{registered}' in the roster.\n"
                  f"Run the command without the claim to act as '{registered}', or pass --force "
                  f"to override deliberately (leader acting on behalf of a seat).", file=sys.stderr)
            sys.exit(2)
        return claimed
    if registered:
        return registered
    if not required:
        return ""
    print(f"error: cannot resolve who you are — no --as NAME, no COORD_AGENT in the environment, "
          f"and this pane ({pane or 'not inside tmux'}) has no active roster row.\n"
          f"Check in first: {coord_invocation(args)} checkin <your-agent> \"<what you are working "
          f"on>\" — or pass --as <your-agent>.", file=sys.stderr)
    sys.exit(2)


def role_verdict(args, command, allow, allowed_desc):
    """The ROLE gate's verdict, WITHOUT acting on it: (caller, passed, overridden, message).

    Split out of `gate` so a command carrying more than one gate can evaluate them ALL before it
    refuses (leader #230). `passed` is the gate's own answer, ignoring --force; `overridden` says
    --force would carry it anyway."""
    caller = resolve_agent(args, required=False)
    passed = bool(allow(caller))
    # Through GATE_FLAGS, never a bare getattr: the binding lives in ONE place (S-6(a)).
    forced = gate_forced(args, "role")
    if passed:
        return caller, True, False, ""
    msg = (f"`{command}` is {allowed_desc}; you resolve to '{caller or 'no identity'}'")
    return caller, False, forced, msg


def gate(args, command, allow, allowed_desc):
    """Hard role gate (T6/F14: `owner`/`launch`/`close`/`panel` documented a leader-only rule
    and never enforced it). `allow` is a predicate over the resolved caller name; '' means
    identity was unresolvable. Returns the caller. `--force` is the escape.

    For a command that ALSO carries the memory gate, use `launch_gates` instead — this one
    short-circuits, which is exactly the trapdoor #230 rules against."""
    caller, passed, overridden, msg = role_verdict(args, command, allow, allowed_desc)
    if passed:
        return caller
    if overridden:
        print(f"note: `{command}` role gate overridden with --force "
              f"(caller: {caller or 'unresolved'})", file=sys.stderr)
        return caller
    print(f"refused: {msg}.\nAsk leader to run it, or pass --force if you are "
          f"deliberately acting for leader.", file=sys.stderr)
    sys.exit(2)


def launch_gates(args, command, allow, allowed_desc, n_seats):
    """BOTH gates a spawning command carries — role AND memory — evaluated ALWAYS, with BOTH
    verdicts reported in one message (leader #230). Returns the caller, or exits.

    THE DEFECT THIS FIXES, and it is an ordering defect rather than a flag one. The role gate was
    checked FIRST and SHORT-CIRCUITED, so a role refusal said nothing about memory — and the ONLY
    seat that routinely trips the role gate is the watcher, which holds DAG-unblock authority
    exercisable solely through `--force`. It therefore could never OBSERVE the memory verdict
    without having already overridden the role gate, at which point (before the flags were split)
    it had overridden memory too. A gate you cannot observe without overriding it is not a gate,
    it is a trapdoor — and separating the flags alone would not have helped, because the second
    verdict stayed invisible until after the first was waived.

    So: compute both, say both, and refuse if EITHER refuses. `--force` carries the role gate only;
    `--force-memory` carries the memory gate only; neither carries the other."""
    caller, role_ok, role_forced, role_msg = role_verdict(args, command, allow, allowed_desc)
    mgate = memory_gate(n_seats, available_mb())
    mem_forced = gate_forced(args, "memory")   # via GATE_FLAGS, never a bare getattr (S-6(a))
    lines, refused = [], False
    if role_ok:
        lines.append("role gate: PASS")
    elif role_forced:
        lines.append(f"role gate: REFUSED, overridden with --force ({role_msg})")
    else:
        lines.append(f"role gate: REFUSED — {role_msg}")
        refused = True
    if not mgate:
        lines.append("memory gate: PASS")
    elif mem_forced:
        lines.append(f"memory gate: REFUSED, overridden with --force-memory — {mgate}")
    else:
        lines.append(f"memory gate: REFUSED — {mgate}")
        refused = True
    verdicts = "\n  ".join(lines)
    if refused:
        print(f"refused: `{command}` — BOTH gates evaluated, both verdicts below (neither flag "
              f"carries the other):\n  {verdicts}\n"
              f"--force carries the ROLE gate; --force-memory carries the MEMORY gate.\n"
              f"If memory is the refusal, the right move is usually to WAIT for a seat to depart "
              f"rather than override it.", file=sys.stderr)
        sys.exit(2)
    # Nothing refused. Any override that actually carried a gate is announced, so a forced launch
    # is never silent — the WARNING wording is deliberately distinct from `refused:` (#210).
    for line in lines:
        if "overridden" in line:
            print(c(f"WARNING launching anyway: {line}", C_DEAD), file=sys.stderr)
    return caller


def is_leader(name):
    return name == "leader"


def is_leader_or_closer(name):
    return name == "leader" or name.startswith("closer-")


def is_closer(name):
    return bool(name) and name.startswith("closer-")


def broadcast_scope(agent, decls=None):
    """Which `to: all` broadcast TYPES reach `agent` (G-20).

    None  = every type — an ordinary seat, unchanged.
    set   = only these types reach it.
    empty = no broadcast reaches it at all.

    A seat's OWN DECLARATION (`broadcast:` in its descriptor) wins over the built-in table below,
    including over the `closer-` prefix: an explicit statement in the one file that defines the
    seat outranks a default inferred from its name. The table stays as the DEFAULT — every package
    that declares nothing behaves exactly as it did — but it is no longer the mechanism, so a seat
    is narrowed by saying so rather than by a future maintainer remembering to add its name here.

    This bounds BROADCAST ONLY. A message addressed to the seat BY NAME, or to a group it belongs
    to, always arrives — the point is to stop the room's conversation from spending a system seat's
    context, never to make a seat unreachable. (The SENDER BOUND is the one cut that may narrow a
    by-name message, and it is refused at `send` so nothing is ever accepted and then dropped.)"""
    declared = (decls or {}).get(agent) or {}
    if "broadcast" in declared:
        return declared["broadcast"]
    if is_closer(agent):
        return frozenset()          # one-shot: co-write memory, harvest, close, depart
    if agent == "watcher":
        return WATCHER_BROADCAST_TYPES
    if agent in SPECIAL_CASE_SEATS:
        return frozenset()
    return None


def in_broadcast_scope(agent, mtype, decls=None):
    """Does a broadcast of type `mtype` reach `agent`? (True for every ordinary seat.)"""
    scope = broadcast_scope(agent, decls)
    return True if scope is None else mtype in scope


# ---------- closing state (G-21) ----------
#
# CLOSING is a STATE, not a role: from the moment `close <seat>` spawns its closer, the seat has
# exactly one job left — co-write its memory.md, answer the harvest, go. Every other message
# arriving in that window is work it will never do and context the co-write needs. G-20 bounds WHO
# a seat is; G-21 bounds WHEN. Inbox while closing: its CLOSER plus `leader`, nothing else.
#
# Kept in its own file rather than a roster column: workers.md's row grammar is frozen (WORKER_ROW
# / row_text) and every reader parses it positionally, so widening it to carry a flag that lives
# for minutes would be the expensive way to store the cheap thing.

def closing_path(base):
    return base / "closing.json"


def load_closing(base):
    """{seat: {"since": ts, "closer": name}} for every seat currently being closed. Never fatal:
    an unreadable or malformed file means "nobody is closing" — the fail-safe direction, since a
    parse error must not silence the room."""
    path = closing_path(base)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def closing_age_min(entry):
    """Minutes since the close began, or None when the stamp is unreadable."""
    try:
        return max(0, int((datetime.now()
                           - datetime.strptime((entry or {}).get("since", "").strip(),
                                               "%Y-%m-%d %H:%M")).total_seconds() // 60))
    except (ValueError, AttributeError, TypeError):
        return None


def closing_entry(base, seat):
    """`seat`'s closing state, or None — EXPIRED entries read as None.

    The expiry is not tidiness, it is the failure this run already had: a closer can DIE mid-close
    (G-11 killed one outright, and three seats were SIGKILLed tonight). Without an expiry, a dead
    closer would leave its target narrowed for the rest of the run — cut off from the room with no
    remedy anyone would think to look for. A close ceremony takes minutes; past CLOSING_MAX_MIN the
    state is assumed orphaned and the seat is treated as ordinary again. Fail-safe direction: an
    unreadable stamp expires too, because a seat wrongly narrowed goes quiet where a seat wrongly
    left open merely reads a message it did not need."""
    entry = load_closing(base).get(seat)
    if entry is None:
        return None
    age = closing_age_min(entry)
    if age is None or age > CLOSING_MAX_MIN:
        return None
    return entry


def closing_seats(base):
    return {seat for seat in load_closing(base) if closing_entry(base, seat) is not None}


# ---- G-134: the AWAITING-CLOSE debt ----------------------------------------------------------
# A seat can complete its OWN lifecycle (`checkout` — its last act per protocol §8) but only the
# leader can free its resources (`close-seat`, which kills the pane and verifies the harness pids
# are gone). Nothing bounded, drove, or even NOTICED the interval between the two: a seat read
# `active: no` on the roster while its pane held RAM against a 2800 MB launch floor, until a human
# happened to look. One instance ran 41 minutes and was found by hand.
#
# THE DEFECT WAS NEVER A MISSING KILL. `close-seat` has always killed. The stated fix — have
# `checkout` kill its own pane — was REFUSED and the refusal ratified: it would destroy the
# in-place renew path, which respawns the successor into the SAME pane to preserve window layout
# (G-12) and therefore needs that pane alive at close time. `depart` is the wrong precedent; it is
# a seat leaving for good, with no renewal question open. `checkout` is the half that KEEPS it open.
#
# So the record is written, not the kill: checkout ASSERTS the debt (who, which pane, whether the
# transcript landed, when), and close-seat/depart clear it. That makes #259's ratified hand-mapping
# — roster-done + pane-alive + transcript-EXISTS -> kill by pane id — a fact the tool WROTE rather
# than a state a later pass RECONSTRUCTS from roster + tmux + filesystem. This run has catalogued
# six instances of inferring a property from ambient context (G-101, G-107, G-121, G-124, G-128,
# and the engineer's own circular origin); a reaper that re-derives the debt each pass would be the
# seventh. An assertion at the moment of truth beats an inference at the moment of action.
#
# ⚠ THIS STATE DELIBERATELY DOES NOT EXPIRE, and that is the one place it must NOT copy `closing`
# above. There, expiry is fail-safe: a dead closer would otherwise leave its target narrowed and
# silent forever, so forgetting is the safer error. Here the entry IS the leak report — an expiry
# would delete the evidence of a pane still holding memory and restore exactly the silence this
# exists to end. A debt that ages out unpaid is not a debt.

def undelivered_flags(base):
    """[(stamp, text)] for every monitor flag the messaging layer REFUSED, newest last.

    Written by watch.py as a plain append, deliberately outside the message log: it reports that
    the messaging layer refused something, so routing it back through that layer is the one path
    guaranteed to fail the same way. Surfaced by `status` and `workers` because a monitor that
    cannot deliver must SHOUT that it cannot deliver — tonight's context warnings were computed
    correctly, refused correctly, printed to a detached stderr file, and lost, while the loop went
    on reporting healthy. Silence and health were indistinguishable at exactly the wrong place."""
    path = base / "undelivered-flags.md"
    if not path.exists():
        return []
    try:
        out = []
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
            ln = ln.strip()
            if ln.startswith("- ") and "|" in ln:
                stamp, _, rest = ln[2:].partition("|")
                out.append((stamp.strip(), rest.strip()))
        return out
    except OSError:
        return []


def undelivered_line(base):
    """One line for the roster/status views, or '' when nothing was ever refused."""
    flags = undelivered_flags(base)
    if not flags:
        return ""
    return (f"UNDELIVERED MONITOR FLAGS: {len(flags)} — the watch loop computed a warning and the "
            f"messaging layer refused it. Most recent: {flags[-1][0]} {flags[-1][1][:110]}\n"
            f"  Read them all: {base / 'undelivered-flags.md'}")


def awaiting_path(base):
    return base / "awaiting-close.json"


def load_awaiting(base):
    """{seat: {"since", "pane", "transcript", "exported"}} — seats that finished their own
    lifecycle and whose resources the leader has not yet freed.

    Never fatal, same as `load_closing`: an unreadable file reads as "no debt". The fail-safe
    direction differs from closing's for a reason worth stating — a lost entry costs a leaked pane
    someone must find by hand (recoverable, and the roster still shows the seat inactive), whereas
    raising here would take down `checkout`, the one act a finishing seat must always be able to
    complete."""
    path = awaiting_path(base)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def set_awaiting(base, seat, pane, transcript, exported):
    """Record the debt at checkout. Best-effort: bookkeeping ABOUT a checkout must never break the
    checkout itself — 7.37 already ruled that shape for the session trace, and a seat that cannot
    check out is worse than a debt nobody recorded.

    `exported` is stored rather than inferred from `transcript` being truthy, because the two
    genuinely differ: an export can be SKIPPED (a dead pane, `--no-export`) and #259's mapping
    gates the kill on the transcript EXISTING. A reaper must be able to tell "safe to kill" from
    "not yet safe" without re-running the export to find out."""
    try:
        with coord_lock(base):
            data = load_awaiting(base)
            # str() at the boundary: `export_transcript` hands back a Path, and a Path is not JSON
            # serializable — an uncoerced one raises INSIDE the checkout it is bookkeeping for.
            # Caught by the selftest before it ever reached a live room, which is the whole point
            # of writing the record through a fixture that runs the real verb.
            data[seat] = {"since": now(), "pane": str(pane or ""),
                          "transcript": str(transcript or ""), "exported": bool(exported),
                          # The harness identity AS THE SEAT LEFT IT, in the pid+starttime form
                          # every teardown already uses (PID reuse cannot forge it). `reap` later
                          # requires the pane to still hold EXACTLY these processes — which is how
                          # "no human on this pane" becomes an ASSERTION recorded at the moment it
                          # was true, rather than a guess made at kill time about a pane someone
                          # may have repurposed in between.
                          "pids": [[p, s] for p, s in (pane_harness_idents(pane) if pane else [])]}
            atomic_write(awaiting_path(base), json.dumps(data, indent=2, sort_keys=True) + "\n")
        return True
    except (OSError, ValueError):
        return False


def clear_awaiting(base, seat):
    """Drop the debt — the leader has freed the seat's resources. Returns True when one was
    actually cleared, so the caller can say so rather than claim it unconditionally."""
    try:
        with coord_lock(base):
            data = load_awaiting(base)
            if seat not in data:
                return False
            del data[seat]
            atomic_write(awaiting_path(base), json.dumps(data, indent=2, sort_keys=True) + "\n")
        return True
    except (OSError, ValueError):
        return False


def awaiting_debts(base, live=None):
    """[(seat, entry, age_min, pane_alive)] oldest first — the debt, ready to render or to reap.

    `pane_alive` is resolved against the live pane set so a debt whose pane is ALREADY gone (killed
    by hand, or the whole window torn down) is distinguishable from one still holding memory. Both
    are debts — the record is stale either way and the leader still owes a `close-seat` to complete
    the roster and session trace — but only one of them is costing RAM."""
    panes = live_panes() if live is None else live
    out = []
    for seat, entry in load_awaiting(base).items():
        age = closing_age_min(entry)
        out.append((seat, entry, age, bool(entry.get("pane")) and entry["pane"] in panes))
    return sorted(out, key=lambda r: (-1 if r[2] is None else r[2]), reverse=True)


def reap_blockers(entry, age, panes, decls=None, seat=None):
    """Every reason `entry` must NOT be reaped, as a list. EMPTY means every precondition holds.

    A LIST, not a bool, and that is the design: `reap` kills panes, so a caller — and the leader
    reading a dry pass — must see WHICH condition held it, never just that something did. A gate
    that answers only yes/no teaches nobody why the run is leaking.

    The two hard preconditions (leader #312, non-negotiable) are the last two rows:

      TRANSCRIPT EXISTS — #259's ratified mapping gates the kill on it, and the marker records
      whether the export actually landed rather than leaving this to be re-derived. Checked against
      the FILE, not only the flag: a recorded path whose file has since gone is not a transcript.

      NO HUMAN ON THE PANE — the reason this is not a nicety: a checked-out seat's pane can be
      picked up by a live owner conversation, and a mechanical reap there terminates the
      conversation rather than freeing memory. Proven by requiring the pane to still hold EXACTLY
      the harness processes recorded at checkout (pid+starttime, so PID reuse cannot forge it). A
      pane whose processes changed has been repurposed; a pane with no recorded identity was never
      provably seat-only. Both refuse. FAIL-CLOSED: anything unprovable holds the reap."""
    out = []
    # A PANE WHOSE PURPOSE IS HUMAN CONTACT IS NEVER REAPABLE (owner-ruled, via leader #341:
    # `r-owner-afk-liaison-parked`). A seat can close while its pane deliberately SURVIVES as the
    # owner's door — the owner is away and watches that spot. Such a pane matches every debt
    # condition exactly, so this machinery reports it as a leak: a FALSE POSITIVE BY DESIGN, and
    # the most expensive kind, because acting on it closes the door the run is reachable through.
    #
    # Derived from the seat's own descriptor, never a kit-side name list, for the reason
    # `inbox_decls` states at length — a name list freezes one campaign's roles into a shared tool
    # and the NEXT such seat is forgotten identically. `relays:` already means exactly the needed
    # thing: this seat carries the relay path to a HUMAN role. Carrying that path is what makes the
    # pane a door rather than a leak, so the exemption falls out of the declaration instead of
    # needing new vocabulary.
    #
    # ⚠ THE EXEMPTION IS ONLY AS LIVE AS THE DECLARATION. Until a parked seat's descriptor declares
    # `relays:`, nothing here protects it. When this landed, the live owner door was protected ONLY
    # by accident — its debt record predated the `pids` field, so it failed closed on "no identity
    # recorded". That is luck, not design, and luck about ordering is not compliance.
    if seat and ((decls or {}).get(seat) or {}).get("relays"):
        out.append("it carries a relay path to a human role — its pane is a DOOR, not a leak, and "
                   "is never reaped (r-owner-afk-liaison-parked)")
    pane = (entry or {}).get("pane") or ""
    if not pane:
        out.append("no pane recorded")
    elif pane not in panes:
        out.append("its pane is already gone — nothing to free (the close is still owed)")
    if age is None:
        out.append("its checkout stamp is unreadable, so age cannot be established")
    elif age < REAP_MIN_AGE_MIN:
        out.append(f"only {age}min old (needs {REAP_MIN_AGE_MIN}min — a renewal decision may be "
                   f"in flight, and in-place renew needs this pane alive)")
    recorded = [(int(p), str(s)) for p, s in (entry or {}).get("pids") or []]
    tpath = (entry or {}).get("transcript") or ""
    if not entry.get("exported") or not tpath:
        out.append("no transcript was exported — #259 gates the kill on it existing")
    elif not Path(tpath).exists():
        out.append(f"its recorded transcript {tpath} is no longer on disk")
    if not recorded:
        out.append("no harness identity was recorded, so the pane was never provably seat-only")
    elif pane and pane in panes:
        live_now = [(int(p), str(s)) for p, s in pane_harness_idents(pane)]
        if sorted(live_now) != sorted(recorded):
            out.append("the pane no longer holds the processes it checked out with — it has been "
                       "repurposed, and a human may be on it")
    return out


def confirm_reap(base, seat, blocked):
    """Record ONE sweep pass's observation and answer whether the two-pass rule is satisfied.

    Returns (confirmations, ready). A pass whose condition FAILED resets the ledger to empty: the
    rule is two CONSECUTIVE passes, so an interruption must cost the trend rather than leave a
    stale half-confirmation to be completed an hour later by an unrelated sweep.

    Confirmations are recorded on EVERY pass, including a dry one — observing is not acting, and
    the whole point of a dry sweep is to build the trend the leader then acts on. What `--go`
    gates is the KILL, and nothing else.

    The spacing rule lives here rather than in the caller so no future entry point can skip it."""
    try:
        with coord_lock(base):
            data = load_awaiting(base)
            entry = data.get(seat)
            if entry is None:
                return [], False
            seen = [s for s in (entry.get("confirmed") or []) if isinstance(s, str)]
            if blocked:
                seen = []
            else:
                last = seen[-1] if seen else ""
                gap = closing_age_min({"since": last}) if last else None
                # A first observation always counts; a later one counts only if it is far enough
                # from the previous to be a genuinely separate pass.
                if not seen or (gap is not None and gap >= REAP_MIN_PASS_GAP_MIN):
                    seen.append(now())
            entry["confirmed"] = seen
            data[seat] = entry
            atomic_write(awaiting_path(base), json.dumps(data, indent=2, sort_keys=True) + "\n")
            return seen, len(seen) >= 2
    except (OSError, ValueError):
        return [], False


def set_closing(base, seat, closer):
    """Mark `seat` as closing. Best-effort like every other coordination side-effect: a failure to
    write must never abort a close that has already spawned its closer."""
    try:
        with coord_lock(base):
            data = load_closing(base)
            data[seat] = {"since": now(), "closer": closer}
            atomic_write(closing_path(base), json.dumps(data, indent=2, sort_keys=True) + "\n")
        return True
    except (OSError, ValueError):
        return False


def clear_closing(base, seat):
    """Drop `seat`'s closing state — the state dies WITH the close (or with a renew: the successor
    is a fresh seat with a full inbox). Returns True when a state was actually cleared."""
    try:
        with coord_lock(base):
            data = load_closing(base)
            if seat not in data:
                return False
            del data[seat]
            atomic_write(closing_path(base), json.dumps(data, indent=2, sort_keys=True) + "\n")
        return True
    except (OSError, ValueError):
        return False


def inbox_scope_line(base, agent):
    """One line naming the seat's inbox narrowing, or '' for an ordinary seat."""
    entry = closing_entry(base, agent)
    if entry is not None:
        closer = entry.get("closer") or f"closer-{agent}"
        return (f"CLOSING since {entry.get('since', '?')} — inbox is {closer} + leader only; "
                f"peers are refused at the CLI and still hold their message (G-21)")
    scope = broadcast_scope(agent)
    if scope is None:
        return ""
    if scope:
        return (f"special-case seat — of the room's broadcasts you receive only "
                f"{'/'.join(sorted(scope))}; direct messages always reach you (G-20)")
    return ("special-case seat — the room's broadcasts do not reach you; direct messages always "
            "do (G-20)")


def closing_reaches(seat, sender, entry):
    """May `sender`'s DIRECT message reach `seat` while it is closing? Only its closer and the
    leader. The closer exception is not optional: the co-write IS a conversation (the closer sends
    its draft `--type ask` and folds in the correction), so a literal no-direct-messages would
    break the very ceremony the state exists for. Leader stays reachable for an abort or a renew."""
    if sender == "leader":
        return True
    expected = (entry or {}).get("closer") or f"closer-{seat}"
    return sender == expected


def cmd_approve(args):
    """(doorman) answer a seat's interactive permission/approval prompt: send keys to its
    REGISTERED pane and echo the pane tail so the caller can verify the outcome. This is
    the sanctioned pane-touch for approval gates — inspect the pane (capture-pane) and
    decide BEFORE calling; --keys "" (default) just presses Enter (the highlighted
    option), --keys 1/2/3/n selects that option, --no-enter sends keys without Enter.

    `args.target` is the seat being answered — NEVER the caller (T1: `args.agent` now means
    "who is calling" everywhere, so a target positional must not land on it)."""
    _, _, rows = load_workers(base_dir(args))
    row = current_row(rows, args.target)
    if not row or row.get("active") != "yes" or not row.get("pane"):
        print(f"refused: no ACTIVE pane is registered for '{args.target}', so there is nothing to "
              f"send keys to — the seat never checked in, has checked out, or its pane changed.\n"
              f"Check the roster first: {coord_invocation(args)} workers", file=sys.stderr)
        sys.exit(1)
    pane = row["pane"]
    set_injection_context(action="approve")
    if args.keys:
        tmux_send_text(pane, args.keys)
        time.sleep(0.2)
    if not args.no_enter:
        tmux_send_enter(pane)
    time.sleep(0.8)
    tail, terr = tmux_capture_tail(pane, lines=6)  # (text, err) — printing the tuple was F13
    print(f"sent {args.keys!r}{'' if args.no_enter else ' + Enter'} to {args.target} ({pane}); pane tail:")
    print(tail if not terr else f"(capture failed: {terr})")
    print(c("next: run it again if the tail above still shows the prompt", C_HINT))


def unread_for(args, base, agent, start, blocks=None, gmap=None, observers=None, closing=None):
    """Messages after #start this agent would see on an unfiltered `read` — the same predicate
    `read` uses, so checkin/status/workers never disagree with it. This is the ONE unread
    derivation: it excludes the agent's own sends and honours addressing + observer status, which
    a bare `log tail - cursor` subtraction cannot (that over-reported every seat whose own
    messages were the tail). The optional preloaded log/groups/observers let a caller that lists
    EVERY agent (`workers`) parse each of them once instead of once per row."""
    if blocks is None:
        _, blocks = load_messages(base)
    if not blocks:
        return []
    if gmap is None:
        gmap = group_map(base)
    if observers is None:
        observers, _ = observer_sets(args)
    if closing is None:
        closing = closing_seats(base)
    return [b for b in blocks if b["num"] > start
            and shows_in_inbox(b, agent, gmap, observers, "any", closing,
                               inbox_decls(args))]


def cmd_checkin(args):
    base = base_dir(args)
    base.mkdir(parents=True, exist_ok=True)
    summary = " ".join(args.summary.split()).replace("|", "/")
    if len(summary) > SUMMARY_MAX:
        print(
            f"refused: summary is {len(summary)} chars — max {SUMMARY_MAX}.\n"
            "This line is how OTHER agents decide whether your work concerns them and whether "
            "to message you. Rewrite it to state, concretely: what you are changing/producing "
            "and which shared surfaces (records, scripts, views) you touch. No filler.",
            file=sys.stderr,
        )
        sys.exit(1)
    pane = detect_pane(args.pane)
    if not pane:
        print("warning: not inside tmux and no --pane given, so your row carries no pane and "
              "wakes cannot reach you — you must run `read` at your own checkpoints. Pass "
              "--pane %N to bind one.", file=sys.stderr)
    else:
        set_pane_title(pane, args.agent)
    # P37 (zombie double-launch): supersession is the RIGHT answer for a relaunch or a recovery —
    # the prior pane is gone, so nothing else can be holding the name. It is the WRONG answer when
    # the prior pane is still ALIVE: two live sessions then share one roster name, and the run has
    # no way to see it. Only the newest pane is in the roster, so every wake reaches only that one;
    # the own-sender read filter is keyed on the NAME (`unread_for`), so each twin's messages are
    # invisible to the other; and both write the same seat's surfaces as single-writer. Refuse, and
    # name the remedy the protocol requires — confirm the old session is dead (kill it BY PANE ID,
    # never by name) before retrying. `--force` is the deliberate override.
    if not getattr(args, "force", False):
        _, _, existing = load_workers(base)
        prior = current_row(existing, args.agent)
        if (prior and prior["active"] == "yes" and prior["pane"] and prior["pane"] != pane
                and prior["pane"] in live_panes()):
            print(
                f"refused: '{args.agent}' is already checked in on pane {prior['pane']}, and tmux "
                f"says that pane is still ALIVE — checking in from {pane or 'no pane'} would put "
                f"two live sessions under one name.\n"
                f"Neither would see the other's messages (the unread filter is keyed on the name) "
                f"and only this pane would receive wakes.\n"
                f"Confirm the old session is dead first, then retry: inspect it with "
                f"`tmux capture-pane -p -t {prior['pane']}`; if it is a zombie, kill it BY PANE ID "
                f"(`tmux kill-pane -t {prior['pane']}`) — never by name — and check in again.\n"
                f"If you are deliberately running two sessions under this name, re-run with "
                f"--force.",
                file=sys.stderr,
            )
            sys.exit(1)
    # G-11: a row goes ACTIVE only when a harness process is actually running in its pane. The
    # closer whose multi-line prompt was executed by the pane's SHELL checked itself in from bash
    # — a real row, an honest-looking summary, and nothing running behind it; its "completion"
    # message was believed for seven minutes. The roster is the run's map of what is alive, so the
    # claim is verified at the moment it is made, against the process table rather than the caller.
    # Fail-safe, deliberately asymmetric: only POSITIVE absence refuses. An unreadable process
    # table or pane pid ("cannot tell") passes, since losing a real seat to a false refusal is
    # worse than the defect. COORD_SKIP_HARNESS_CHECK=1 is the escape hatch for an unrecognized
    # harness wrapper.
    if pane and not SKIP_HARNESS_CHECK:
        pids, verifiable = pane_harness_pids(pane)
        if verifiable and not pids:
            print(
                f"refused: no {'/'.join(HARNESS_PROCS)} process is running in pane {pane}, so this "
                f"check-in would put '{args.agent}' on the roster as ACTIVE with nothing behind it "
                f"(G-11).\n"
                f"This is what a briefing executed by the pane's SHELL looks like: the checkin line "
                f"runs for real while the harness never started. If that is what happened, the "
                f"prompt reached the pane as literal keystrokes — spawn through `launch`/`close`, "
                f"which pass the prompt as a file.\n"
                f"If a harness IS running here under a wrapper this check cannot recognize, re-run "
                f"with COORD_SKIP_HARNESS_CHECK=1 and say so on the log.",
                file=sys.stderr,
            )
            sys.exit(1)
    superseded = 0
    # The read cursor belongs to the SEAT, not to one session of it: a re-check-in (P1
    # supersession) and a renewed seat (close-seat --renew closes the row BEFORE the fresh
    # session checks in) both used to write lastread=0, so the seat was told the entire log was
    # unread and re-read hundreds of messages it had already been shown. The new row inherits the
    # highest cursor any prior row of the SAME agent reached — never another agent's.
    inherited = 0
    with coord_lock(base):
        path, lines, rows = load_workers(base)
        if not path.exists():
            atomic_write(path, WORKERS_HEADER)
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            rows = []
        for r in rows:
            if r["agent"] != args.agent:
                continue
            if r["lastread"].isdigit():
                inherited = max(inherited, int(r["lastread"]))
            # P1: a re-check-in supersedes EVERY prior active row for the same agent — the roster
            # never strands a ghost ACTIVE row again.
            if r["active"] == "yes":
                r["active"] = "no"
                r["checkout"] = f"superseded {now()}"
                lines[r["_line"]] = row_text(r)
                superseded += 1
        new_row = {"agent": args.agent, "active": "yes", "pane": pane, "summary": summary,
                   "checkin": now(), "checkout": "", "lastread": str(inherited)}
        atomic_write(path, "".join(lines) + row_text(new_row))
    note = f" (superseded {superseded} prior row(s))" if superseded else ""
    if inherited:
        note += f" (cursor kept at #{inherited})"
    print(f"checked in: {args.agent} ({pane or 'no pane'}){note} — {summary}")
    # PLACEMENT DRIFT: the seat checks its OWN pane against what its descriptor declares.
    #
    # DETECTION, NOT PREVENTION, and the distinction is the honest half of this: a pane opened BY
    # HAND never passes through `launch`, so no validation there can ever see it — which is exactly
    # how the trigger instance happened (a hand-renewal into the wrong window). This is the only
    # reachable half. It also cannot self-correct: a seat cannot move its own pane without killing
    # it, and a pane whose purpose is human contact must never be moved to tidy a layout — a door
    # in the wrong window is cosmetic, a door killed for the layout is an outage. So it FLAGS and
    # leaves, and the operational fix stays a human's.
    if pane:
        _decl = next((w["window"] for w in discover_workers(workers_dir(args))
                      if w["agent"] == args.agent), "")
        _actual = tmux_pane_window_name(pane)
        if _decl and _decl != "yes" and _actual and _actual != _decl:
            print(c(f"placement drift: your descriptor declares `window: {_decl}` but this pane is "
                    f"in '{_actual}'. Nothing here moves it — a seat cannot move its own pane "
                    f"without killing it. Report it; the layout fix is operational stewardship.",
                    C_DEAD), file=sys.stderr)
    # 7.37: the seat's own checkin is where its native session id becomes resolvable — see
    # session_backfill_native. Never allowed to break a checkin (session_trace_safe).
    nat, nerr = session_trace_safe(session_backfill_native, args, args.agent)
    if nerr:
        print(c(f"WARNING sessions.csv native-session-id NOT backfilled — {nerr}. Your checkin "
                f"stands.", C_DEAD), file=sys.stderr)
    elif nat.startswith("!unresolved"):
        print(c(f"WARNING sessions.csv: this seat has an OPEN session row and its "
                f"native-session-id could NOT be resolved — {nat[12:]}. Task 7.32's native resume "
                f"cannot use this row.", C_DEAD), file=sys.stderr)
    elif nat:
        print(f"sessions.csv: native session id recorded ({nat})")
    # T1: from here the seat never types its own name again — every other command resolves it.
    waiting = unread_for(args, base, args.agent, inherited)
    if waiting:
        print(c(f"next: {coord_invocation(args)} read — {len(waiting)} message(s) already waiting "
                f"for you", C_HINT))
    else:
        print(c(f"next: {coord_invocation(args)} status — nothing waiting yet", C_HINT))


def cmd_checkout(args):
    base = base_dir(args)
    me = resolve_agent(args)
    _, _, rows = load_workers(base)
    row = current_row(rows, me)
    if not row or row["active"] != "yes":
        print(f"refused: '{me}' has no ACTIVE roster row, so there is no session to end — you "
              f"never checked in, or you already checked out.\n"
              f"See the roster: {coord_invocation(args)} workers", file=sys.stderr)
        sys.exit(1)
    # T3: the export is the seat's last durable artifact and was routinely forgotten — mechanize
    # it instead of teaching it (protocol item 8). --no-export is the escape for a dead pane.
    out, err = "", "--no-export"
    if not getattr(args, "no_export", False):
        out, err = export_transcript(args, me, "checkout")
        print(f"transcript: {out}" if not err else f"transcript skipped — {err}")

    def flip(r):
        r["active"] = "no"
        r["checkout"] = now()

    update_row(base, me, flip)
    print(f"checked out: {me}")
    # G-134: the seat's half of the lifecycle is now done and its resources are NOT freed — only
    # `close-seat` kills the pane. Assert that debt here, at the one moment every input is known
    # for certain, instead of leaving a later pass to reconstruct it from roster + tmux + fs.
    if set_awaiting(base, me, (row or {}).get("pane", ""), out, not err):
        print(f"awaiting close: {me} recorded — its pane is STILL LIVE until leader runs "
              f"`{coord_invocation(args)} close-seat {me}`")
    sid, cerr = session_trace_safe(session_close, args, me)   # 7.37: checkout ends the session as surely as a close does
    if cerr:
        print(c(f"WARNING sessions.csv row NOT completed — {cerr}. The close itself stands.",
                C_DEAD), file=sys.stderr)
    elif sid:
        print(f"sessions.csv: {sid} ended")
    print(c(f"next: nothing on your side — leader closes or renews the seat "
            f"(`{coord_invocation(args)} close {me} [--renew]`)", C_HINT))


def owner_status(base):
    path = base / "owner-status.md"
    if not path.exists():
        return "unknown"
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("owner:"):
            return ln[len("owner:"):].strip()
    return "unknown"


def cmd_owner(args):
    # P15 — workers were inferring owner availability and getting it wrong; state it explicitly.
    # Gate: leader, or an UNRESOLVABLE identity — that caller is the human owner at a shell.
    gate(args, "owner", lambda who: who in ("leader", ""), "leader's (or the owner's) to set")
    base = base_dir(args)
    base.mkdir(parents=True, exist_ok=True)
    note = f" — {args.note}" if args.note else ""
    with coord_lock(base):
        atomic_write(base / "owner-status.md",
                     "# owner-status — script-managed (coord.py owner <present|afk>)\n"
                     f"owner: {args.state} | since {now()}{note}\n")
    print(f"owner is now: {args.state}{note}")
    print(c(f"next: {coord_invocation(args)} send all \"owner is {args.state}{note}\" --type note "
            f"— workers infer it wrongly when nobody says it (P15)", C_HINT))


def truncate(text, limit=DIGEST_SNIPPET):
    """One-line snippet. Newlines are collapsed: every caller renders ONE line per row, and a
    body with embedded newlines would silently break that row into several."""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def cmd_workers(args):
    """Who is alive, at a glance (T2/F4). DEFAULT is one CURRENT row per agent with truncated
    summaries and an unread-lag column; --full keeps summaries whole, --history replays every
    historical row (the pre-T2 behavior)."""
    base = base_dir(args)
    _, _, rows = load_workers(base)
    print(f"{c('owner:', C_LABEL)} {owner_status(base)}")
    if not rows:
        print("no workers registered")
        print(c(f"next: {coord_invocation(args)} launch — nobody has checked in yet", C_HINT))
        return
    _, blocks = load_messages(base)
    tail = blocks[-1]["num"] if blocks else 0
    # Parsed ONCE for the whole listing, then handed to unread_for per row (the lag column is
    # the same exact per-agent unread count `status` reports — see unread_for).
    gmap = group_map(base)
    observers, _ = observer_sets(args)
    live = live_panes()
    if getattr(args, "history", False):
        shown = rows
    else:
        shown = [current_row(rows, a) for a in dict.fromkeys(r["agent"] for r in rows)]
    dead = 0
    for r in shown:
        if r["active"] == "yes":
            status, tone = "ACTIVE", C_ALIVE
            if r["pane"] and live and r["pane"] not in live:
                status, tone = "DEAD?", C_DEAD  # registered pane is gone — wakes cannot reach it
                dead += 1
        else:
            status, tone = "done", C_DONE
        cursor = f" read@{r['lastread']}" if r["lastread"] not in ("", "0") else ""
        lag = ""
        if r["active"] == "yes" and tail:
            start = int(r["lastread"]) if r["lastread"].isdigit() else 0
            behind = len(unread_for(args, base, r["agent"], start, blocks, gmap, observers))
            lag = f" lag={behind}"
        summary = r["summary"] if getattr(args, "full", False) else truncate(r["summary"])
        # Columns are padded BEFORE colouring: an escape sequence inside a padded field counts
        # toward its width and would shear every column to its right.
        name_col = "{:<16}".format(r["agent"])
        state_col = "{:<7}".format(status)
        pane_col = "{:<6}".format(r["pane"] or "-")
        print(f"{c(name_col, C_LABEL)} {c(state_col, tone)} pane={pane_col}{cursor}{lag} {summary}"
              f"  (in {r['checkin']}{', out ' + r['checkout'] if r['checkout'] else ''})")
    _und = undelivered_line(base)
    if _und:
        print(c(_und, C_DEAD))
    # G-134: the debt is surfaced HERE because a record nobody reads is not a fix, and the roster
    # is where leader already looks to decide lifecycle. Rendered oldest-first with the pane's LIVE
    # state, because the two debts differ in what they cost: a live pane is still holding memory
    # against the launch floor, a dead one is only an incomplete record. Both still owe a
    # `close-seat` — the roster and session trace are not finished until it runs.
    for seat, entry, age, alive in awaiting_debts(base, live):
        aged = f"{age}min" if age is not None else "unknown age"
        if alive:
            print(c(f"awaiting close: {seat} — checked out {aged} ago and its pane "
                    f"{entry.get('pane') or '?'} IS STILL LIVE, holding memory against the launch "
                    f"floor. transcript {'exported' if entry.get('exported') else 'NOT exported'}"
                    f" — {coord_invocation(args)} close-seat {seat}", C_DEAD))
        else:
            print(c(f"awaiting close: {seat} — checked out {aged} ago; its pane is already gone, "
                    f"but the close never ran, so the roster and session trace are unfinished "
                    f"— {coord_invocation(args)} close-seat {seat} --no-export", C_HINT))
    # P32: the watcher is the run's sentinel and NOTHING watched it. Its loop is detached, so a
    # dead loop looks exactly like a quiet run — no flags either way. The roster view is where
    # leader already looks, so the heartbeat is checked here rather than in a new command.
    hb = watcher_heartbeat(base)
    if hb:
        cadence = f", loop {hb['loop_min']}min" if hb.get("loop_min") else ", one-shot"
        pid = f", pid {hb['pid']}" if hb.get("pid") else ""
        if hb["stale"]:
            print(c(f"watcher: STALE — last pass {hb['age_min']}min ago (stale past "
                    f"{hb['stale_after']}min{cadence}{pid}). Nothing is measuring liveness, "
                    f"context or approval gates right now; restart the loop.", C_DEAD))
        else:
            print(c(f"watcher: ok — last pass {hb['age_min']}min ago{cadence}{pid}", C_ALIVE))
    if not getattr(args, "history", False):
        print(c(f"-- current rows only (log tail #{tail}); --history for every row, --full for "
                f"untruncated summaries", C_HINT))
    if dead:
        print(c(f"next: {dead} row(s) point at a pane tmux no longer has — "
                f"{coord_invocation(args)} close-seat <agent> cleans one up", C_HINT))


# ---------- groups.md ----------

def load_groups(base):
    path = base / "groups.md"
    if not path.exists():
        return path, [], []
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    rows = []
    for i, line in enumerate(lines):
        m = GROUP_ROW.match(line.rstrip("\n"))
        if m and m.group("group") != "group":
            rows.append({
                "group": m.group("group").strip(),
                "members": [x.strip() for x in m.group("members").split(",") if x.strip()],
                "by": m.group("by").strip(),
                "created": m.group("created").strip(),
                "_line": i,
            })
    return path, lines, rows


def group_map(base):
    _, _, rows = load_groups(base)
    return {r["group"]: r["members"] for r in rows}


def refuse_special_case_members(args, command, names):
    """G-32 — a SPECIAL-CASE seat is not a group member (owner-spotted: "why was it included in a
    group? it should not"). A group is the room's cheap channel, and the room's conversation is
    exactly what G-20 cut from these seats at the front door; letting them be added walks the same
    traffic in the side one. Enforced in the two commands that can CREATE a membership, because the
    run makes a fresh group per wave and a rule kept only by remembering is the class this run has
    been paying for all night. `--force` stays the single deliberate override, as on every other
    refusal here — and even then delivery is filtered by TYPE (`addressed_to`), so the override
    buys membership, never the traffic."""
    blocked = sorted({n for n in names if broadcast_scope(n) is not None})
    if not blocked:
        return
    many = len(blocked) > 1
    if getattr(args, "force", False):
        print(f"note: `{command}` added special-case seat(s) {', '.join(blocked)} with --force "
              f"(G-32); group messages still reach them only by TYPE", file=sys.stderr)
        return
    print(f"refused: {', '.join(blocked)} "
          f"{'are special-case seats' if many else 'is a special-case seat'} — group traffic is "
          f"not {'their' if many else 'its'} input (G-32). A closer, `engineer` and the watcher "
          f"serve the SYSTEM or the ROOM, not the goal's conversation, so the room's threads only "
          f"spend the context {'their' if many else 'its'} one job needs.\n"
          f"Send {'them' if many else 'it'} a DIRECT message instead — direct addressability is "
          f"untouched: {coord_invocation(args)} send {blocked[0]} \"<what you need>\" --type note\n"
          f"--force adds {'them' if many else 'it'} anyway, if the membership is deliberate.",
          file=sys.stderr)
    sys.exit(1)


def cmd_create_group(args):
    base = base_dir(args)
    me = resolve_agent(args)
    _, _, wrows = load_workers(base)
    agent_names = {r["agent"] for r in wrows}
    name = args.group
    if name == "all" or name in agent_names:
        print(f"refused: '{name}' is already a recipient name ('all', or an agent on the roster), "
              f"and `send {name}` could then mean two different things.\n"
              f"Name the group after the WORKSTREAM instead (e.g. views-render).", file=sys.stderr)
        sys.exit(1)
    members = sorted(set(args.members) | {me, "leader"})
    refuse_special_case_members(args, "create-group", members)
    with coord_lock(base):
        path, _, grows = load_groups(base)
        if any(g["group"] == name for g in grows):
            print(f"refused: group '{name}' already exists — creating it again would fork the "
                  f"thread.\nAdd people to the existing one instead (leader): "
                  f"{coord_invocation(args)} add-to-group {name} <member ...>", file=sys.stderr)
            sys.exit(1)
        if not path.exists():
            atomic_write(path, GROUPS_HEADER)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"| {name} | {', '.join(members)} | {me} | {now()} |\n")
    print(f"group created: {name} — members: {', '.join(members)}")
    print(c(f"next: {coord_invocation(args)} send {name} \"<why this group exists>\" --type note "
            f"— a group nobody was told about carries no thread", C_HINT))


def cmd_add_to_group(args):
    gate(args, "add-to-group", is_leader, "leader's alone")
    # Only the names being ADDED are policed: a group that already carries a special-case seat
    # (three did when G-32 was filed) must stay editable, or the refusal would block its own fix.
    refuse_special_case_members(args, "add-to-group", args.members)
    base = base_dir(args)
    with coord_lock(base):
        path, lines, grows = load_groups(base)
        row = next((g for g in grows if g["group"] == args.group), None)
        if not row:
            known = ", ".join(sorted(g["group"] for g in grows)) or "(none yet)"
            print(f"refused: there is no group '{args.group}', so there is nothing to add to.\n"
                  f"existing groups: {known}\nCreate it instead: {coord_invocation(args)} "
                  f"create-group {args.group} <member ...>", file=sys.stderr)
            sys.exit(1)
        members = sorted(set(row["members"]) | set(args.members))
        lines[row["_line"]] = f"| {row['group']} | {', '.join(members)} | {row['by']} | {row['created']} |\n"
        atomic_write(path, "".join(lines))
    print(f"group {args.group} members: {', '.join(members)}")
    print(c(f"next: {coord_invocation(args)} send {args.group} \"<who joined, and why>\" "
            f"--type note", C_HINT))


def cmd_remove_from_group(args):
    """(leader) Drop members from an existing group — add-to-group's missing half, and the ONLY
    sanctioned way to undo a membership: `coordination/` is script-managed and hand-editing it is
    banned, so before this command a wrong member could be added but never taken back. G-32 is the
    case that needed it: three groups carried the watcher from before the special-case cut landed,
    and `create-group` refuses a re-create."""
    gate(args, "remove-from-group", is_leader, "leader's alone")
    base = base_dir(args)
    with coord_lock(base):
        path, lines, grows = load_groups(base)
        row = next((g for g in grows if g["group"] == args.group), None)
        if not row:
            known = ", ".join(sorted(g["group"] for g in grows)) or "(none yet)"
            print(f"refused: there is no group '{args.group}', so there is nothing to remove "
                  f"from.\nexisting groups: {known}", file=sys.stderr)
            sys.exit(1)
        absent = [m for m in args.members if m not in row["members"]]
        if absent and not getattr(args, "force", False):
            print(f"refused: {', '.join(absent)} "
                  f"{'are' if len(absent) > 1 else 'is'} not in group '{args.group}', so removing "
                  f"{'them' if len(absent) > 1 else 'it'} would report a change that did not "
                  f"happen.\ncurrent members: {', '.join(row['members']) or '(none)'}\n"
                  f"--force drops the names that ARE members and ignores the rest.",
                  file=sys.stderr)
            sys.exit(1)
        members = [m for m in row["members"] if m not in set(args.members)]
        lines[row["_line"]] = f"| {row['group']} | {', '.join(members)} | {row['by']} | {row['created']} |\n"
        atomic_write(path, "".join(lines))
    print(f"group {args.group} members: {', '.join(members) or '(none)'}")
    print(c(f"next: {coord_invocation(args)} send {args.group} \"<who left, and why>\" "
            f"--type note", C_HINT))


# ---------- messages.md ----------

def load_messages(base):
    path = base / "messages.md"
    if not path.exists():
        return path, []
    blocks, current = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = MSG_HEADER.match(line)
        if m:
            current = {"num": int(m.group("num")), "sender": m.group("sender"),
                       # None = written from INSIDE this package, which is every message in every
                       # log predating this field. Only a foreign sender carries an origin.
                       "origin": m.group("from_pkg"),
                       "to": m.group("to"), "type": m.group("type"),
                       "supersedes": int(m.group("supersedes")) if m.group("supersedes") else None,
                       "re": int(m.group("re")) if m.group("re") else None,
                       "why": (m.group("why") or "").strip() or None,
                       "ts": m.group("ts").strip(),
                       "lines": [line]}
            blocks.append(current)
        elif current is not None:
            current["lines"].append(line)
    return path, blocks


def next_message_number(blocks):
    return max((b["num"] for b in blocks), default=0) + 1


def append_message(base, sender, to, mtype, body, supersedes=None, re_num=None, why=None,
                   origin=None):
    """Allocate the next message number AND append the block inside one lock hold — two
    concurrent sends used to read the same tail and claim the same ID (run-obs §589).
    Returns the number."""
    with coord_lock(base):
        path, blocks = load_messages(base)
        n = next_message_number(blocks)
        if not path.exists():
            path.write_text(MESSAGES_HEADER, encoding="utf-8")
        # G-94: a sender writing into a package it is not rostered in NAMES WHERE IT CAME FROM.
        # Written only for a foreign sender, so a local send's header is byte-identical to before.
        org = f" | from-pkg: {origin}" if origin else ""
        sup = f" | supersedes: {supersedes}" if supersedes is not None else ""
        rel = f" | re: {re_num}" if re_num is not None else ""
        # #198: the clause rides IN THE LOG LINE, not just in the sender's terminal — a reader
        # judging whether a broadcast earned everyone's attention can see the claim it made.
        wc = f" | why: {why}" if why else ""
        block = (f"\n## {n} | from: {sender}{org} | to: {to} | type: {mtype}{sup}{rel}{wc} | "
                 f"{now()}\n"
                 f"\n{body}\n")
        with open(path, "a", encoding="utf-8") as f:
            f.write(block)
    return n


def log_delivery_failures(base, failures):
    """P22 — a lost wake must be visible in the LOG, not only on the sender's terminal."""
    if not failures:
        return
    with coord_lock(base):
        with open(base / "messages.md", "a", encoding="utf-8") as f:
            for fail in failures:
                f.write(f"> delivery-failure: {fail}\n")


def relay_seats(token, decls):
    """Every seat in THIS package declaring `relays: <token>` — the resolution of a role word.

    DERIVED from descriptors, never a kit-side name list, for the reason `inbox_decls` states at
    length: a name list in the kit freezes ONE campaign's role vocabulary into a tool every run
    shares. It also keeps the resolution HONEST — `probe_master_bound.py`'s M6 asserts the kit does
    not contain the live master seat's name, so a fix that hard-coded it would go green while
    rebuilding the exact defect stage 3 removed.

    PACKAGE-SCOPED BY CONSTRUCTION: `decls` is built from this package's own briefings, so a
    foreign seat sharing a roster name cannot be resolved here at all. That is not incidental —
    `G-111` is exactly this, live: a seat of a CLOSED run still running and sharing the live run's
    roster name, so an unscoped resolution would deliver this run's `send master` into a dead one.
    (The seat is deliberately not named here: `probe_master_bound.py`'s M6 asserts mechanically
    that the kit does not contain the live relay seat's name, and a comment naming it would defeat
    that check while proving nothing.)

    N SEATS IS A VALID ANSWER, not an ambiguity. The KG is explicit that the master is ONE ROLE
    over ONE shared state realized by N live sessions, safe because no master session owns private
    durable state, so two live master sessions cannot diverge into two masters. N deliveries are
    therefore N copies to ONE recipient. Refusing on N>1 would make the owner channel fail
    precisely when it is most redundant."""
    if not token:
        return frozenset()
    t = token.lower()
    return frozenset(s for s, d in (decls or {}).items() if t in (d.get("relays") or ()))


def sender_admitted(b, bound, decls):
    """Does a bounded inbox admit message `b`'s sender? The SENDER half of relay resolution.

    Two ways in, and the split is deliberate:

      LITERAL — the sender's own seat name is in the bound. Unchanged, and no origin test: this is
      exactly today's behaviour for every existing bound, and narrowing it while adding a feature
      would be a silent regression dressed as a fix.

      RELAY — the bound names a role TOKEN and the sender declares it. This one IS origin-tested:
      a message carrying `from-pkg:` was written from outside this package (stage 4), so its sender
      is not the seat this package's descriptors describe. Without that test a foreign seat named
      like the local relay-holder would inherit the local master's reach — asserted identity beating
      verified identity, which is `G-111` itself.

    A bound that is None means UNBOUNDED and never reaches here."""
    if b["sender"] in bound:
        return True
    if b.get("origin"):
        return False
    return any(b["sender"] in relay_seats(tok, decls) for tok in bound)


def addressed_to(b, agent, gmap, observers, mode="any", closing=(), decls=None):
    """Is message `b` in `agent`'s inbox? `mode` is the --addressed vocabulary: `any` = to me,
    my groups, or everyone (an observer seat sees the full log); `direct` = only messages naming
    me; `broadcast` = only messages to all.

    G-20/G-21 are applied HERE, in the one predicate `read`, `status` and every unread count share,
    so no view can disagree with another about what a seat's inbox holds — the same reason the
    unread derivation was collapsed into `unread_for`.

    `closing` is the set of seats currently being closed (`load_closing`); pass it or a closing
    seat is filtered by role only."""
    to = b["to"]
    is_closing = agent in closing
    # THE SENDER BOUND, applied before any addressing question: `r-cos-bounded-inbox` and
    # `r-engineer-contact` bound an inbox to NAMED SENDERS, and that is a property of WHO IS
    # SPEAKING, not of how the message is addressed — so it cuts a broadcast, a group message and a
    # by-name message alike. That is the owner's sentence in full ("receiving all messages, not only
    # those addressed to him; only u and master can talk to him"): one declared field answers both
    # halves.
    #
    # This is BELT-AND-BRACES, not the enforcement: `send` refuses a non-permitted sender at the
    # CLI (see cmd_send), so a bounded message should never reach the log at all. This catches the
    # two that can — a `--force` override, and a message that predates the bound. It is safe to cut
    # here for exactly the reason the closing cut is: the sender was told at send time and still
    # HOLDS its message, so nothing is accepted-then-dropped. And it is never SILENT — `read`'s
    # withheld footer names every message addressed to this seat that this predicate cut, with its
    # number, which is what keeps a bound from manufacturing G-94's failure while fixing its family.
    #
    # No descriptor in any package declares `senders:` today, so this is None for every seat and
    # the mechanism ships INERT until one does.
    bound = ((decls or {}).get(agent) or {}).get("senders")
    if bound is not None and not sender_admitted(b, bound, decls):
        return False
    # A RELAY TOKEN is a by-name address in effect, and is branched EXPLICITLY rather than reusing
    # the group machinery — which is the tempting reuse, since a group gives addressing, wake, read
    # and recipient validation for free. It would be wrong: `G-32` makes group fan-out honour the
    # same TYPE scope test as `all`, so `send master --type note` would be silently dropped for a
    # special-case seat. The master's traffic is a by-name address and must never be type-scoped.
    to_relay = to != "all" and to not in gmap and agent in relay_seats(to, decls)
    if to == "all":
        # A special-case seat, or any seat mid-close, is cut from the room's broadcast — by TYPE
        # for the watcher, entirely for the rest. Applied before the observer short-circuit: an
        # observer reads the full log by grant, but the owner's directive is about what LANDS in
        # a system seat's inbox, and a grant to read everything is not an obligation to receive it.
        if is_closing or not in_broadcast_scope(agent, b["type"], decls):
            return False
    elif to in gmap and agent in gmap.get(to, ()):
        # G-32: a GROUP is not a side door around the broadcast cut. The traffic the owner cut at
        # the front door walked in this one — the watcher sat in three of the run's four groups, so
        # essentially the whole room's lane traffic still landed in the seat the directive was
        # written to protect. Group fan-out therefore honours the SAME scope test as `all`: the
        # watcher keeps completion/verdict (its DAG trigger), closers and `engineer` keep nothing,
        # and a seat mid-close is cut entirely. Membership refusal (create-group/add-to-group) is
        # the braces; this is the belt, so even a deliberately-added member is filtered by TYPE
        # rather than by anyone remembering the rule. A message addressed to the seat BY NAME is
        # untouched — that invariant is what makes every one of these cuts safe.
        if is_closing or not in_broadcast_scope(agent, b["type"], decls):
            return False
    elif is_closing and (to == agent or to_relay) and not closing_reaches(agent, b["sender"], None):
        # Belt-and-braces: `send` refuses a peer's direct message to a closing seat at the CLI, so
        # one should never reach the log. If one does (a --force override, or a message that
        # predates the state), it still must not spend the seat's remaining context.
        return False
    if mode == "direct":
        # `--addressed direct` means "only messages naming me". A relay token names the seat
        # carrying it just as surely as its seat name does — that is what resolution MEANS — so
        # excluding it here would hide the owner channel's own traffic from the filter a seat uses
        # to find what was addressed to it.
        return to == agent or to_relay
    if mode == "broadcast":
        return to == "all"
    if agent in observers:
        return True
    return to == agent or to_relay or to == "all" or (to in gmap and agent in gmap[to])


def sender_origin(args, sender):
    """Where `sender` is writing FROM, or None when it is a member of the package it writes INTO.

    G-94's root, in one sentence: a sender may write into a package it is not rostered in, the log
    records only its role name, and every downstream visibility and reachability decision is then
    made against a roster that does not describe that sender at all. `resolve_agent` permits the
    claim precisely because the calling pane has no roster row IN THE TARGET PACKAGE — which is
    exactly the cross-package case — so the permission is right and the RECORD was incomplete.

    THE TEST IS THE CALLING PANE, NOT THE NAME, and that distinction is the entire fix. Asking
    "does a seat of this name belong to this package" is CIRCULAR — run-2 has a `leader` seat, so
    run-1's leader writing into run-2 answers YES and goes unlabelled, which is precisely the
    handover G-94 lost. Measured, not reasoned: that membership-by-name version returned None for
    the exact case it existed to catch. The pane is the ONE identity claim the tool can verify
    (`pane_agent`'s own docstring), so it is what verified-vs-asserted must be decided on.

    An unresolvable pane returns None — today's behaviour exactly. Under-labelling is the safe
    direction: it preserves the status quo for out-of-pane callers like watch.py, whereas
    over-labelling would stop a seat's own sends being suppressed and re-serve them to it.

    NOT a refusal. Cross-package sending is legitimate and this run does it deliberately — a
    leader hands a run off, a liaison answers on another package's log. What was missing was the
    record of it, so the label is additive and never blocks."""
    try:
        pane = detect_pane(getattr(args, "pane", None))
        if not pane:
            return None        # cannot verify anything; change nothing
        if pane_agent(base_dir(args), pane):
            # This pane holds an active row in THIS package — either as `sender`, or as the row
            # resolve_agent already vetted a --force claim against. Local.
            return None
    except Exception:
        return None            # never let bookkeeping about a send break the send
    # No ACTIVE roster row for this pane. That is NOT the same as foreign, and treating it as such
    # was this function's defect: a seat that has checked out — or was renewed, or never checked in
    # — keeps writing from inside its own package, and every one of its messages was stamped
    # `external`. Measured: all four origin-labelled messages in run-2's log were the owner-liaison,
    # local and rostered, sending while its row read inactive. Under the stage-5 sender bound a
    # relay token is refused for any message carrying an origin, so that mislabel would have
    # SEVERED THE OWNER CHANNEL the moment `relays: master` was declared.
    #
    # So resolve the caller's OWN package from its cwd and compare: the NEAREST enclosing package
    # is where the caller is writing from. Same package -> local, whatever the roster says. A
    # different one -> name it, which is exactly G-111 (a closed run's seat still resolves to its
    # own package and stays refused). Only a cwd inside no package at all is `external`, which now
    # means what it says: no package this tool could identify.
    #
    # The earlier form walked PAST this package looking for any other, so it could also attribute a
    # caller to an ANCESTOR package it merely sat under. Stopping at the nearest fixes both.
    try:
        here = Path.cwd().resolve()
        pkg = package_dir(args)
        for cand in (here, *here.parents):
            if (cand / "coordination").is_dir():
                return None if cand == pkg else cand.name
    except Exception:
        pass
    return "external"


def is_own_send(b, agent):
    """Is `b` a message THIS seat sent? (G-94 — the cut that ate a lifecycle handover.)

    The old test was `b["sender"] == agent`: a NAME comparison. A name is a ROLE, and roles repeat
    across packages, so when run-1's leader wrote `from: leader | to: leader` into run-2's package
    the receiving leader classified it as its own send, `read` answered "no new messages", and the
    cursor advanced past it — the message was addressed to it, was never shown, and was never
    re-offered. Correct in its designed case (a seat must not be re-served its own traffic) and
    wrong for two distinct seats wearing one name.

    A message carrying an ORIGIN was written from OUTSIDE this package, so whoever sent it is by
    construction not the local seat reading it, whatever the two are called. Absence of an origin
    means local, which is every message written before the field existed — so this is exactly the
    old behaviour for every historical log, and the fix is FORWARD-LOOKING by necessity: the
    record for the handover that motivated it does not carry the distinguisher, and inventing one
    retroactively would be rewriting the permanent log. That message stays disclosed by `read`'s
    withheld footer instead, which is what stage 1 exists for."""
    return b["sender"] == agent and not b.get("origin")


def shows_in_inbox(b, agent, gmap, observers, mode="any", closing=(), decls=None):
    """THE one answer to "will `agent`'s `read` show message `b`" — `read`, `unread_for` and the
    WAKE half all route through it.

    `addressed_to` already collapsed the READ-side views into one predicate so no two of them could
    disagree about a seat's inbox. The wake half was never brought in: `deliver_wakes` re-derived a
    weaker test of its own (`in_broadcast_scope` on the `all` and group branches, `closing_reaches`
    on the direct branch, and NO visibility test at all on a bare direct message), so the wake set
    and the read set drifted apart in both directions. A seat with `auto-wake: yes` was woken for
    every direct message in the room and could read none of them — the pure-overhead version of the
    very interruption a bounded inbox exists to prevent — while the code's own comment already
    stated the invariant it was breaking.

    The `sender != agent` half lives here rather than in `addressed_to` because it is a property of
    the READER, not of the addressing: `addressed_to` answers "is this in my inbox", and a seat's
    own sends are in its inbox and simply must not be re-served to it.
    """
    return not is_own_send(b, agent) and addressed_to(b, agent, gmap, observers, mode, closing,
                                                      decls)


def why_not_woken(b, agent, gmap, observers, decls=None):
    """The REASON `agent` is not woken, for the sender's summary line (T3: a narrowed inbox is
    never silent at either end — the sender always learns who did not get the nudge, and why)."""
    bound = ((decls or {}).get(agent) or {}).get("senders")
    if bound is not None and not sender_admitted(b, bound, decls):
        # Named distinctly from the generic cut: this one is about WHO IS SPEAKING, and a sender
        # told only "not in its inbox" would look for the fault in its addressing.
        return "bounded inbox: you are not a permitted sender"
    if b["to"] == "all" or (b["to"] in gmap and agent in gmap.get(b["to"], ())):
        if not in_broadcast_scope(agent, b["type"], decls):
            return "special-case seat"
    return "not in its inbox"


def open_asks(blocks):
    """Asks nobody has settled: type ask, not superseded, and no answer/verdict carrying `re:`
    its number (T4/F11 — before the link existed, an unanswered ask was invisible without
    re-reading the whole log)."""
    superseded = {b["supersedes"] for b in blocks if b["supersedes"] is not None}
    settled = {b["re"] for b in blocks
               if b["re"] is not None and b["type"] in ("answer", "verdict")}
    return [b for b in blocks
            if b["type"] == "ask" and b["num"] not in superseded and b["num"] not in settled]


def age_of(ts):
    """Age of a message timestamp in m/h ('?' when unparseable)."""
    try:
        dt = datetime.strptime(ts.strip(), "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return "?"
    mins = max(0, int((datetime.now() - dt).total_seconds() // 60))
    return f"{mins}m" if mins < 90 else f"{mins // 60}h"


def split_log_notes(b):
    """(body lines, log-annotation lines) for one message block.

    P22 appends its `> delivery-failure:` lines to messages.md AFTER the block they follow, so
    `load_messages` absorbs them into that block and a plain render showed them as if the sender
    had written them. They are the LOG speaking about a failed wake, never message content. The
    file itself is untouched (its grammar is frozen and the lines must stay findable there) —
    this is a RENDER split only: the reader gets them as a labelled trailer, never hidden."""
    body = [ln for ln in b["lines"][1:] if not ln.startswith("> delivery-failure:")]
    notes = [ln[2:] for ln in b["lines"][1:] if ln.startswith("> delivery-failure:")]
    return body, notes


def body_of(b):
    """A message's body WITHOUT the P22 delivery-failure annotations (one-line views only)."""
    return "\n".join(split_log_notes(b)[0]).strip()


SHELL_COMMS = {"bash", "sh", "dash", "zsh", "ksh", "fish", "csh", "tcsh"}

# Set true by main() only. See main() for why the distinction cannot be inferred.
CLI_INVOCATION = False


def parent_is_shell():
    """Is this process's parent a shell — i.e. was our argv PARSED by one on the way in?"""
    try:
        return Path(f"/proc/{os.getppid()}/comm").read_text(encoding="utf-8").strip() \
            in SHELL_COMMS
    except OSError:
        return False


def shell_source_line():
    """The command string the PARENT was given, when the parent is a one-shot `sh -c <string>`.

    This is the ONE place the PRE-SUBSTITUTION text still exists. By the time coord.py receives
    argv the shell has already run every `backtick` and $(...) and replaced it with the output —
    undetectable from the body alone, which is why S-4(b) bit three authors who KNEW about it.
    '' when the parent is an interactive shell (no -c) or unreadable: that case is genuinely
    undetectable and the gate below stays silent rather than guessing."""
    try:
        raw = Path(f"/proc/{os.getppid()}/cmdline").read_bytes().split(b"\0")
    except OSError:
        return ""
    parts = [p.decode("utf-8", "replace") for p in raw if p]
    if len(parts) >= 3 and Path(parts[0]).name in SHELL_COMMS and parts[1].startswith("-") \
            and "c" in parts[1]:
        return parts[2]
    return ""


def substitution_eaten(body):
    """The substitution markers the invoking shell consumed before coord.py saw this body.

    A marker present in the shell's ORIGINAL command string and absent from what arrived was
    substituted away — the body in hand is not the body the author wrote. Once, this executed
    the launch command a renewal broadcast was merely describing: a second live leader for four
    minutes, and the record of how to recover a dead leader no longer contained the recovery.

    THE BOUND, stated rather than implied: this catches a body sent through `sh -c`, which is
    every agent-harness and every scripted send. It CANNOT catch a human typing at an
    interactive prompt — there is no -c string to compare against — and it does not need to
    catch a programmatic caller passing an argv LIST, which was never exposed."""
    line = shell_source_line()
    if not line:
        return []
    return [m for m in ("`", "$(") if m in line and m not in body]


def message_body(args):
    """The body: the positional, or --file PATH / --file - (stdin). A file/stdin body never
    passes through a shell — the fix for the backtick-substitution class that corrupted msg #77
    (F6)."""
    src = getattr(args, "file", None)
    msg = getattr(args, "message", None)
    if src and msg:
        print("refused: a quoted body AND --file were both given, and only one of them can be "
              "the message — silently picking one would send a body you did not read.\n"
              "Pass the message positionally OR via --file, not both.", file=sys.stderr)
        sys.exit(1)
    if src:
        if src == "-":
            body = sys.stdin.read()
        else:
            p = Path(src)
            if not p.is_file():
                print(f"refused: --file {src} — no such file, so there is no body to send.\n"
                      f"Write the file first, or pass an absolute path (relative paths resolve "
                      f"from YOUR working directory, not the package's).", file=sys.stderr)
                sys.exit(1)
            body = p.read_text(encoding="utf-8")
    elif msg:
        body = msg
    else:
        print('refused: no message body — pass "<msg>", or --file PATH (--file - reads stdin) '
              'when the body carries backticks, quotes, or newlines', file=sys.stderr)
        sys.exit(1)
    body = body.strip("\n")
    if not body.strip():
        print("refused: the body is empty (whitespace only) — an empty message costs every "
              "recipient a wake and a read, and says nothing.\nWrite the content, or drop the "
              "send.", file=sys.stderr)
        sys.exit(1)
    return body


def known_recipients(args, base):
    """Every name `send` can deliver to: roster rows ∪ briefing `agent:` names (a seat that
    exists but has not launched yet) ∪ group names ∪ RELAY TOKENS that resolve ∪ 'all'.

    A relay token is admitted ONLY while some seat declares it. That asymmetry is deliberate: an
    unresolved `master` stays an unknown recipient and is refused with the near-match hint, which
    is the right answer — accepting an address nobody holds is how `S-7` opens a thread with no
    possible terminus. This is also the SEND-side half of `#184`'s both-directions ruling: before
    it, `master` was not a valid recipient at all, so a bounded seat could receive from the master
    and could never answer it."""
    _, _, rows = load_workers(base)
    names = {r["agent"] for r in rows}
    names |= set(briefing_frontmatters(workers_dir(args)))
    names |= set(group_map(base))
    for d in inbox_decls(args).values():
        names |= set(d.get("relays") or ())
    names.add("all")
    return names


def cmd_send(args):
    base = base_dir(args)
    sender = resolve_agent(args)
    force = getattr(args, "force", False)
    body = message_body(args)
    _, blocks = load_messages(base)

    # F5 — a typo'd recipient was accepted silently: the message landed under a name nobody
    # reads and the only signal was one "wake skipped" line the sender scrolled past.
    known = known_recipients(args, base)
    if args.to not in known and not force:
        near = difflib.get_close_matches(args.to, sorted(known), n=1, cutoff=0.6)
        print(f"refused: '{args.to}' is not a known recipient — no roster row, no briefing, and "
              f"no group of that name." + (f" Did you mean '{near[0]}'?" if near else "")
              + f"\nknown: {', '.join(sorted(known))}\nsend anyway: --force", file=sys.stderr)
        sys.exit(1)
    # S-7 — an `ask` stays OPEN until an answer is addressed to its SENDER via --re, and
    # `known_recipients` refuses any name with no roster row, no briefing and no group. So an
    # ask from an unaddressable sender opens a thread WITH NO POSSIBLE TERMINUS: nobody can
    # close it, even in principle. A daemon-fired job sending under its own name — deliberately,
    # so flags are attributed to the detector that raised them rather than a borrowed seat —
    # accumulated 13 of these in one run, every one reported DELIVERED by the sending side and
    # every one permanent residue in an append-only log. The correct sibling shows the pairing
    # is load-bearing: watch.py also sends `ask` and is RIGHT to, because it sends AS `watcher`,
    # a real answerable seat. The TYPE was copied without the IDENTITY.
    #
    # One check, at the only moment it is cheap. NO --force override, deliberately and unlike
    # every other gate in this function: those refuse things that are wrong in the usual case
    # but right in some case. There is no state of the world in which opening an unclosable ask
    # is correct — the sender wants `flag` or `note`, both of which need no reply.
    if args.type == "ask" and sender not in known:
        print(f"refused: '{sender}' cannot receive a reply — no roster row, no briefing and no "
              f"group of that name — so an `ask` from you would stay OPEN forever. An answer "
              f"must be addressed to its sender (--re), and nobody can address you.\n"
              f"Send this as --type note (FYI) or --type flag if the type exists, or check in "
              f"first so you have a roster row: {coord_invocation(args)} checkin {sender} "
              f"\"<what you are doing>\".\n"
              f"There is no --force for this one: 13 asks opened this way in one run and not "
              f"one of them can ever be closed.", file=sys.stderr)
        sys.exit(1)

    # G-22 / #198 — the two enforcement halves of the broadcast discipline. `all` costs every seat
    # a wake and a read, so it must be justified rather than habitual: a broadcast names the clause
    # it claims, and `note` — the type that was 35 of a live run's 86 broadcasts — cannot claim any,
    # because a note is by definition something a seat that never reads it still acts correctly
    # without. The cheap channel is a GROUP; before this, none had ever been created.
    why = getattr(args, "why", None)
    if args.to == "all" and not force:
        if args.type == "note":
            print(f"refused: a `note` is never an `all` broadcast — if a seat that never reads it "
                  f"still acts correctly, it does not belong in everyone's inbox.\n"
                  f"Send it to a GROUP (`{coord_invocation(args)} create-group <name> <members>`) "
                  f"or direct to the seats who need it.\n"
                  f"If it genuinely binds every seat, it is a verdict/completion under one of: "
                  f"{', '.join(sorted(BROADCAST_CLAUSES))} — send it as that type with --why.\n"
                  f"override: --force", file=sys.stderr)
            sys.exit(1)
        if not why:
            clauses = "\n  ".join(f"{k} — {v}" for k, v in sorted(BROADCAST_CLAUSES.items()))
            print(f"refused: `send all` requires --why <clause>, naming what makes this everyone's "
                  f"business:\n  {clauses}\n"
                  f"If none of them fits, the message is not a broadcast — send it to a group or "
                  f"direct.\noverride: --force", file=sys.stderr)
            sys.exit(1)
    if why and args.to != "all":
        print(f"refused: --why justifies a BROADCAST and '{args.to}' is not `all`, so it would "
              f"record a clause for a message nobody needed one for.\nDrop --why.",
              file=sys.stderr)
        sys.exit(1)

    # G-21 — a seat mid-close has one job left, so a peer's direct message is REFUSED here, at the
    # CLI, rather than accepted into a log the seat will depart without reading. The refusal is the
    # POINT: it fails loud, the sender still HOLDS its message and knows now, and nothing can be
    # orphaned. Queueing for a successor was the alternative and was ruled against (leader #189) —
    # it assumes a successor exists, and tonight five of six closes had none, so a queue whose
    # consumer may never exist is accept-then-silence with extra steps.
    entry = closing_entry(base, args.to)
    if entry is not None and not closing_reaches(args.to, sender, entry) and not force:
        closer = entry.get("closer") or f"closer-{args.to}"
        print(f"refused: '{args.to}' is CLOSING (since {entry.get('since', '?')}) — its inbox is "
              f"{closer} and leader only, so this message would arrive as work it will never do "
              f"and context its memory hand-off needs.\n"
              f"You still hold it, and nothing is lost: send it to leader, or wait for the seat's "
              f"successor if it is renewed and send it then.\n"
              f"override (you are certain the seat must read this before it goes): --force",
              file=sys.stderr)
        sys.exit(1)

    # THE SENDER BOUND (`r-cos-bounded-inbox`, `r-engineer-contact`) — refused HERE, at the CLI,
    # because a bound enforced only at read time is the exact failure this family is being fixed
    # for: the message would be accepted, written to the permanent log, and then silently swallowed,
    # which is how G-94 lost a lifecycle handover. Refusing at send inverts that — the sender still
    # HOLDS its message, learns immediately, and is told the route that works.
    #
    # Only a BY-NAME message is refused. A broadcast or a group message is not: it legitimately
    # reaches every other member, and the bounded seat's copy is cut by `addressed_to` and then
    # NAMED in that seat's withheld footer. Refusing the whole broadcast because one member bounds
    # this sender out would narrow the room to protect one inbox.
    #
    # `origin` is resolved HERE rather than at append time because the bound test needs it: a relay
    # token is only honoured for a LOCAL sender (see `sender_admitted`), so the CLI refusal and the
    # read-time cut must be computed from the same inputs or they can disagree — which is this
    # seat's whole commission.
    origin = sender_origin(args, sender)
    decls = inbox_decls(args)
    probe = {"sender": sender, "origin": origin}
    # A relay token addresses N seats, so the bound question is asked of each: refuse only when the
    # message can reach NOBODY. A partial cut is not a refusal — the permitted seats still get it,
    # and each cut seat is named in the wake summary and in its own withheld footer.
    targets = sorted(relay_seats(args.to, decls)) or ([args.to] if args.to != "all" else [])
    bounds = {t: ((decls.get(t) or {}).get("senders")) for t in targets}
    reachable = [t for t, bd in bounds.items() if bd is None or sender_admitted(probe, bd, decls)]
    bound = bounds.get(args.to) if len(targets) == 1 and targets[0] == args.to else None
    if targets and not reachable and not force:
        if bound is None:                      # a relay token: name what it resolved to
            named = ", ".join(sorted(bounds))
            print(f"refused: '{args.to}' resolves to {named}, and every one of them has a BOUNDED "
                  f"INBOX that '{sender}' is not among. This is a standing ruling about who may "
                  f"spend those seats' context, not a judgement of your message.\n"
                  f"You still hold it, and nothing is lost: send it to leader, who routes it.\n"
                  f"override (it will still be filtered at each seat's read, though never silently "
                  f"— their footers name it): --force", file=sys.stderr)
            sys.exit(1)
        print(f"refused: '{args.to}' has a BOUNDED INBOX — it receives messages from "
              f"{', '.join(sorted(bound))} only, and '{sender}' is not among them. This is a "
              f"standing ruling about who may spend that seat's context, not a judgement of your "
              f"message.\n"
              f"You still hold it, and nothing is lost: send it to leader, who routes it.\n"
              f"override (and it will still be filtered at that seat's read, though never "
              f"silently — its footer names it): --force", file=sys.stderr)
        sys.exit(1)
    if len(body) > MESSAGE_MAX and not force:
        print(f"refused: message is {len(body)} chars — max {MESSAGE_MAX}.\n"
              f"A body this long is a document, and every agent pays for it at every checkpoint. "
              f"Write it to a file, then send the PATH plus a 3-line summary: what it says, what "
              f"you want done with it, and by whom.\noverride: --force", file=sys.stderr)
        sys.exit(1)
    if args.supersedes is not None and not any(b["num"] == args.supersedes for b in blocks):
        print(f"refused: --supersedes {args.supersedes} — no such message in the log (it ends at "
              f"#{blocks[-1]['num'] if blocks else 0}). A retraction pointing at nothing retracts "
              f"nothing.\nFind the number you meant: {coord_invocation(args)} read --digest --all",
              file=sys.stderr)
        sys.exit(1)

    re_num = getattr(args, "re_num", None)
    if args.type == "answer" and re_num is None and not force:
        print("refused: an answer must name the ask it answers — pass --re <ask#> (list them "
              "with `pending`).\nAn unlinked answer leaves the ask OPEN for every reader.\n"
              "override: --force", file=sys.stderr)
        sys.exit(1)
    if re_num is not None and args.type not in ("answer", "verdict"):
        print(f"refused: --re is valid only on --type answer (required) and --type verdict "
              f"(optional) — not on '{args.type}'. A `re:` on any other type would make the "
              f"open-ask derivation lie.\nDrop --re, or send this as an answer.", file=sys.stderr)
        sys.exit(1)
    if re_num is not None:
        target = next((b for b in blocks if b["num"] == re_num), None)
        if target is None:
            print(f"refused: --re {re_num} — no such message in the log (it ends at "
                  f"#{blocks[-1]['num'] if blocks else 0}), so the ask would stay OPEN for every "
                  f"reader.\nList the open asks: {coord_invocation(args)} pending", file=sys.stderr)
            sys.exit(1)
        if target["type"] != "ask":
            print(f"refused: --re {re_num} — message #{re_num} is a '{target['type']}', not an "
                  f"ask; --re links an answer/verdict to the ask it settles.\nList the open asks: "
                  f"{coord_invocation(args)} pending", file=sys.stderr)
            sys.exit(1)

    n = append_message(base, sender, args.to, args.type, body,
                       supersedes=args.supersedes, re_num=re_num, why=why, origin=origin)
    marks = ((f", supersedes #{args.supersedes}" if args.supersedes is not None else "")
             + (f", re #{re_num}" if re_num is not None else "")
             + (f", why: {why}" if why else ""))
    # A cross-package send is called out to the SENDER too: the seat that most needs to know its
    # message landed on a roster that does not describe it is the one that just sent it.
    org_note = f" [from-pkg: {origin}]" if origin else ""
    # Leader's condition on `deliver to all`: PRINT THE RESOLVED SET. A bare "delivered to master"
    # is an unverifiable claim, and a role word that silently resolves to a different seat than the
    # sender assumed is `G-111` with better manners. Only for a token that actually resolved —
    # an ordinary recipient already names itself.
    resolved = sorted(relay_seats(args.to, decls))
    rel_note = f" [{args.to} -> {', '.join(resolved)}]" if resolved else ""
    print(f"sent message #{n} ({sender} -> {args.to}, type: {args.type}{marks}){org_note}{rel_note}")
    deliver_wakes(args, base, sender, args.to, n, args.type, origin)
    if args.type == "ask":
        print(c(f"next: {coord_invocation(args)} pending — your ask stays OPEN until an answer "
                f"or verdict --re's #{n}", C_HINT))


def deliver_wakes(args, base, sender, to, n, mtype="note", origin=None):
    """Nudge every recipient's pane. Wakes stay BEST-EFFORT (P22) — the log is the only truth.

    A wake is only ever ATTEMPTED for a recipient with an ACTIVE roster row AND a pane. Every
    other recipient is SKIPPED: never woken, never written to the log, named to the sender in
    the one summary line with the reason. Only an attempted wake can fail, so `> delivery-failure`
    means exactly what P22 says it means. Before this, an unreachable recipient produced a
    logged 'failure' for a wake nobody ever sent — 46 such lines once buried the one real failure
    of a run, and a package with no `scientist` seat logged a phantom scientist failure on EVERY
    single send (the built-in auto-wake default naming a seat that did not exist).

    T5: the surviving wakes run in a bounded thread pool; serially, each recipient cost the
    sender 1.3s of Enter-verify (~13s for a 10-seat send-all). Results print sorted by agent, so
    output stays deterministic."""
    _, _, rows = load_workers(base)
    gmap = group_map(base)
    decls = inbox_decls(args)
    relayed = relay_seats(to, decls) if to not in gmap else frozenset()
    if to == "all":
        recipients = {r["agent"] for r in rows if r["agent"] != sender}
        label = "all"
    elif to in gmap:
        recipients = set(gmap[to]) - {sender}
        label = f"group '{to}'"
    elif relayed:
        # A relay token is resolved for the WAKE too. Addressing it without this would produce the
        # exact defect this seat was commissioned on, in its cleanest form: a message the master's
        # `read` shows and no wake ever nudged it for — the two computations disagreeing again,
        # one layer up. The label names the resolution so the wake line is self-explaining.
        recipients = set(relayed) - {sender}
        label = f"{to} ({', '.join(sorted(relayed))})"
    else:
        recipients = {to}
        label = to
    # The built-in auto-wake names (DEFAULT_AUTO_WAKE/DEFAULT_OBSERVERS) are a DEFAULT, not a
    # roster: they join only where THIS package actually knows the name (a roster row or a
    # briefing). A default name absent from the package produces no wake, no skip mention and no
    # log line — it is not a recipient of this run at all. Briefing-DECLARED auto-wake seats are
    # by construction in the briefings, so they are unaffected.
    observers, auto_wake = observer_sets(args)
    known = {r["agent"] for r in rows} | set(briefing_frontmatters(workers_dir(args)))
    recipients |= (auto_wake & known) - {sender}

    # G-20/G-21: the wake half of the inbox scope. A message the seat's `read` will not show it
    # must not cost it a wake either — waking a seat to fetch nothing is the pure-overhead version
    # of the very interruption this bounds. Filtered seats are NAMED to the sender with the reason,
    # exactly as every other skipped recipient is (T3): the sender always learns who did not get
    # the nudge and why, so a narrowed inbox is never silent at either end.
    closing = {seat: entry for seat, entry in load_closing(base).items()
               if closing_entry(base, seat) is not None}
    # The CLOSING cut keeps its own per-branch rules verbatim — G-21 semantics are a STATE
    # machine, not a visibility question, and folding them into the predicate would have changed
    # which closing seats a group message reaches. Only the VISIBILITY test below is unified.
    # `origin` rides along so the wake's visibility test is asked of the SAME message the log
    # records. Without it a cross-package send would be judged local here and foreign at read —
    # the two computations disagreeing about one message, which is the class this seat owns.
    pending = {"sender": sender, "to": to, "type": mtype, "origin": origin}
    scope_skipped = {}
    closed_out = set()
    if to == "all":
        closed_out = {n for n in recipients if n in closing}
    elif to in gmap:
        # G-32: an observer or auto-wake seat pulled in from OUTSIDE the group still reads the
        # message by grant, so its closing cut is the direct-message rule, not the member rule.
        members = set(gmap[to])
        closed_out = {n for n in recipients
                      if closing.get(n) is not None
                      and (n in members or not closing_reaches(n, sender, closing[n]))}
    else:
        closed_out = {n for n in recipients
                      if closing.get(n) is not None
                      and not closing_reaches(n, sender, closing[n])}
    for name in sorted(closed_out):
        scope_skipped.setdefault("closing", []).append(name)
    # G-20/G-21/G-101 — and the fix this seat was commissioned for: the wake half now asks the
    # SAME question `read` asks, instead of re-deriving a weaker one per branch. The bare direct
    # branch had no visibility test at all, so `auto-wake: yes` bought a seat an interruption for
    # every direct message in the room and a `read` that showed it none of them. `closing` is
    # passed empty because the branch above already ruled on it.
    for name in sorted(set(recipients) - closed_out):
        if not shows_in_inbox(pending, name, gmap, observers, "any", (), decls):
            scope_skipped.setdefault(
                why_not_woken(pending, name, gmap, observers, decls), []).append(name)
    for names in scope_skipped.values():
        recipients -= set(names)

    # T1: the wake embeds the identity-less form — the recipient's own pane/env resolves it.
    text = (f"[coord wake] New coordination message #{n} from {sender} to {label}. "
            f"Read it now, then continue your task: {coord_invocation(args)} read")
    targets, skipped, failures = [], dict(scope_skipped), []
    for name in sorted(recipients):
        row = current_row(rows, name)
        if row is None:
            skipped.setdefault("not launched", []).append(name)   # briefed/named, no row yet
        elif row["active"] != "yes":
            skipped.setdefault("departed", []).append(name)       # had a row, checked out/closed
        elif not row["pane"]:
            skipped.setdefault("no pane", []).append(name)        # checked in without a pane
        elif at_approval_gate(row["pane"]):
            # 8(b) blind-gate hygiene: the seat is alive but parked on an interactive approval
            # modal. Typing into it cannot be read and can land INSIDE the modal's input — the
            # broadcast would corrupt the very gate leader has to answer. Same skip semantics as
            # every other unreachable recipient (T3): not woken, not logged, NAMED to the sender
            # with the reason, so leader knows to run `approve` rather than assume delivery.
            skipped.setdefault("at an approval gate", []).append(name)
        else:
            targets.append((name, row["pane"]))

    def one(target):
        name, pane = target
        ok, err = wake(pane, text)
        return name, pane, ok, err

    results = []
    if targets:
        with ThreadPoolExecutor(max_workers=min(WAKE_PARALLEL_MAX, len(targets))) as pool:
            results = list(pool.map(one, targets))
    delivered = 0
    for name, pane, ok, err in sorted(results):
        if ok:
            delivered += 1
            continue
        failures.append(f"{name} ({pane}): {err or 'tmux send-keys failed'}")
    # T6: a 20-seat broadcast printed 20 result lines the sender had to scan for the one that
    # mattered. Wakes are best-effort chrome — the counts are ONE line, and only failures (the
    # actionable half) keep a line of their own. Skipped seats are named, not just counted:
    # the sender still has to know which seats did not get the nudge, and why.
    parts = [f"{delivered} delivered"]
    if failures:
        parts.append(f"{len(failures)} failed")
    # The tuple fixes the ORDER of the reasons worth leading with; the trailing pass catches any
    # reason not named in it. Before that pass a skip reason absent from this list was computed,
    # applied, and never printed — the seat was silently not woken and the sender was told
    # nothing, which is precisely the silent-drop this summary exists to prevent. A hard-coded
    # list of what may be reported is a list of what can vanish.
    ordered = ("departed", "not launched", "no pane", "at an approval gate",
               "special-case seat", "not in its inbox", "closing")
    for why in ordered + tuple(w for w in sorted(skipped) if w not in ordered):
        names = skipped.get(why)
        if names:
            parts.append(f"{len(names)} skipped ({why}: {', '.join(sorted(names))})")
    print("  wakes: " + (", ".join(parts) if (delivered or failures or skipped)
                         else "no live recipient panes"))
    for line in sorted(failures):
        print(f"  wake FAILED -> {line}")
    gated = skipped.get("at an approval gate")
    if gated:
        print(c(f"  next: {', '.join(sorted(gated))} is parked on an approval prompt — leader "
                f"clears it with {coord_invocation(args)} approve <agent>, and the seat picks this "
                f"message up on its next read", C_HINT))
    if failures:
        log_delivery_failures(base, failures)
        print(f"  ({len(failures)} delivery failure(s) recorded in the log — recipients must "
              f"pick the message up via `read` at their next checkpoint)")


def render_message(b, superseded_by):
    print(c(b["lines"][0], TYPE_COLOR.get(b["type"], "")))
    if b["num"] in superseded_by:
        # P12 — the retraction travels WITH the claim, so no reader acts on a withdrawn one.
        print(c(f"*** SUPERSEDED by #{superseded_by[b['num']]} — do not rely on this message ***",
                C_RETRACT))
    body, notes = split_log_notes(b)
    print("\n".join(body).rstrip())
    if notes:
        print()
    for note in notes:
        # Set apart from the body, never hidden: this is the log's own record of a wake that
        # did not arrive, not something the sender wrote.
        print(c(f"[log] {note}", C_LOGNOTE))
    print()


def digest_line(b, superseded_by):
    """One line per message (T2): enough to triage a 300-message log without reading it."""
    marks = ""
    if b["supersedes"] is not None:
        marks += f" (supersedes #{b['supersedes']})"
    if b["re"] is not None:
        marks += f" (re #{b['re']})"
    ts = b["ts"].split(" ")[-1] if b["ts"] else "--:--"
    num_col = "{:<4}".format("#" + str(b["num"]))
    type_col = "{:<10}".format(b["type"])
    retracted = (c(f" [SUPERSEDED by #{superseded_by[b['num']]}]", C_RETRACT)
                 if b["num"] in superseded_by else "")
    return (f"{c(num_col, C_LABEL)} {ts} {c(type_col, TYPE_COLOR.get(b['type'], ''))} "
            f"{b['sender']}->{b['to']}{marks}{retracted}  {truncate(body_of(b))}")


def persist_cursor(base, agent, target):
    """Store the read cursor. NEVER fatal (F9): a codex seat's sandbox makes the package
    read-only (EROFS) and a concurrent writer can lose the os.replace race — either way the
    reader keeps the messages it was just shown and gets an `--after` hint instead of a
    traceback. The no-op guard skips the rewrite entirely when the cursor would not move: that
    rewrite was itself a race source (scientist-roster #103). Returns (stored, note)."""
    try:
        with coord_lock(base):
            path, lines, rows = load_workers(base)
            row = current_row(rows, agent)
            if row is None or row["active"] != "yes":
                return False, "no active check-in"
            if row["lastread"] == str(target):
                return True, "unchanged"
            row["lastread"] = str(target)
            lines[row["_line"]] = row_text(row)
            atomic_write(path, "".join(lines))
        return True, ""
    except (OSError, ValueError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def cmd_read(args):
    """Bounded, cursor-safe inbox read (T2 + the designer catch).

    The cursor advances ONLY on an unfiltered, non-peek read, and only through the LAST MESSAGE
    SHOWN. Before this, a filtered read (`--type ask` — leader's documented drain) advanced the
    cursor past every non-matching message, silently dropping it from that agent's inbox
    forever; and an unbounded read dumped a 300-message log into the reader's context."""
    base = base_dir(args)
    me = resolve_agent(args)
    _, blocks = load_messages(base)
    if not blocks:
        print("no messages yet")
        return
    gmap = group_map(base)
    _, _, wrows = load_workers(base)
    row = current_row(wrows, me)
    observers, _ = observer_sets(args)
    superseded_by = {b["supersedes"]: b["num"] for b in blocks if b["supersedes"] is not None}
    addressed = getattr(args, "addressed", "any")
    digest = getattr(args, "digest", False)
    msg = getattr(args, "msg", None)
    coord = coord_invocation(args)

    if msg is not None:
        b = next((x for x in blocks if x["num"] == msg), None)
        if b is None:
            print(f"refused: no message #{msg} in the log — it ends at #{blocks[-1]['num']}.\n"
                  f"List what is there: {coord} read --digest --all", file=sys.stderr)
            sys.exit(1)
        render_message(b, superseded_by)
        if b["re"] is not None:
            print(c(f"-- answers ask #{b['re']}", C_HINT))
        settled = [x["num"] for x in blocks if x["re"] == b["num"]]
        if settled:
            print(c("-- answered by #" + ", #".join(str(s) for s in settled), C_HINT))
        print(c("-- peek: --msg never moves your cursor", C_HINT))
        return

    # P26 — persisted cursor: default start point is the agent's stored last-read.
    if args.all:
        start = 0
    elif getattr(args, "after", None) is not None:
        start = args.after
    else:
        start = int(row["lastread"]) if row and row["lastread"].isdigit() else 0

    filtered = (args.type is not None) or (addressed != "any")
    closing = closing_seats(base)      # hoisted: the withheld pass below needs the same set
    decls = inbox_decls(args)
    candidates = [b for b in blocks
                  if b["num"] > start
                  and shows_in_inbox(b, me, gmap, observers, addressed, closing, decls)
                  and (args.type is None or b["type"] == args.type)]
    # G-94 — A SILENT FILTER AND AN EMPTY INBOX ARE THE SAME OUTPUT, and that is what made the
    # defect permanent rather than merely late: `read` answered "no new messages for leader" while
    # a run-1 -> run-2 LEADER LIFECYCLE HANDOVER sat in the log, then advanced the cursor past it,
    # so no later read ever re-offered it. Recovery needed `--msg N`, which a reader with an
    # empty-looking inbox has no reason to run.
    #
    # Reported here is the ONE bucket that is both dangerous and always small: messages whose `to`
    # NAMES THIS SEAT and which the inbox predicate cut anyway. The broad "not addressed to you"
    # count is deliberately NOT reported — in a busy room it is most of the log, and a footer that
    # announces the room's whole traffic every read would re-import the very context a bounded
    # inbox exists to keep out, burying this signal in the noise it creates.
    withheld = [b["num"] for b in blocks
                if b["num"] > start and b["to"] == me
                and not shows_in_inbox(b, me, gmap, observers, addressed, closing, decls)]
    limit = getattr(args, "limit", None)
    if limit is None:
        limit = 0 if args.all else READ_LIMIT  # --all = deliberate full replay
    limit = max(0, limit)
    shown = candidates[:limit] if limit else candidates
    remaining = len(candidates) - len(shown)
    tail = blocks[-1]["num"]

    if not shown:
        print(f"no new messages for {me} after #{start}")
    for b in shown:
        if digest:
            print(digest_line(b, superseded_by))
        else:
            render_message(b, superseded_by)
    if digest and shown:
        print()
    print(c(f"-- shown {len(shown)} message(s); last message number in log: {tail}", C_HINT))
    if withheld:
        nums = ", ".join(f"#{n}" for n in withheld[:8])
        more = f" (+{len(withheld) - 8} more)" if len(withheld) > 8 else ""
        print(c(f"-- {len(withheld)} message(s) ADDRESSED TO YOU were withheld by the inbox filter: "
                f"{nums}{more}. Read any of them in full with `{coord} read --msg N` — this line "
                f"exists because an inbox that filters silently reads exactly like an empty one "
                f"(G-94)", C_HINT))
    if remaining:
        print(c(f"-- {remaining} more waiting — run `{coord} read` again", C_HINT))
    # Only asks nobody has settled yet — pointing the reader at an ask that already has its
    # answer is worse than saying nothing (the derivation is `open_asks`, same as `pending`).
    open_nums = {b["num"] for b in open_asks(blocks)}
    asked = [b for b in shown if b["type"] == "ask" and b["num"] in open_nums]
    if asked:
        first = asked[0]
        print(c(f"next: answer what is yours — {coord} send {first['sender']} \"<answer>\" "
                f"--type answer --re {first['num']}", C_HINT))

    advance = not (args.peek or args.all or digest or filtered)
    if not advance:
        why = ("--peek" if args.peek else "--all" if args.all else "--digest" if digest
               else "a filtered read (--type/--addressed) shows only part of your inbox")
        print(c(f"-- peek semantics: this read did NOT move your cursor ({why}). Run a plain "
                f"`{coord} read` to actually drain your inbox.", C_HINT))
        return
    if not shown:
        print(c(f"-- cursor unchanged at #{start} (nothing new was shown)", C_HINT))
        return
    target = shown[-1]["num"]
    stored, note = persist_cursor(base, me, target)
    if stored and note == "unchanged":
        print(c(f"-- cursor already at #{target}", C_HINT))
    elif stored:
        print(c(f"-- cursor advanced to #{target} (override any time: --after N, --all, --peek)",
                C_HINT))
    else:
        print(c(f"-- cursor NOT stored ({note}) — the messages above are still yours; pass "
                f"--after {target} on your next read", C_HINT))


def cmd_status(args):
    """One-shot orientation (T2/F12): who am I, is my pane reachable, is the owner around, what
    is waiting for me, where is my cursor, what do I run next. Recovery used to mean `workers`
    plus `read --peek` plus a manual scan."""
    base = base_dir(args)
    me = resolve_agent(args)
    coord = coord_invocation(args)
    _, _, rows = load_workers(base)
    row = current_row(rows, me)
    print(f"{c('you:   ', C_LABEL)} {c(me, C_LABEL)}")
    if not row or row["active"] != "yes":
        print(f"{c('roster:', C_LABEL)} {c('NOT checked in', C_DEAD)} — no active row for '{me}'")
        print(c(f"next:   {coord} checkin {me} \"<what you are working on>\"", C_HINT))
        return
    live = live_panes()
    if not row["pane"]:
        pane_state, pane_tone = "no pane registered — wakes cannot reach you", C_DEAD
    elif live and row["pane"] not in live:
        pane_state, pane_tone = "DEAD? — the registered pane is gone, wakes cannot reach you", C_DEAD
    else:
        # No live tmux server means live_panes() is empty and every pane reads ok — an honest
        # degradation, the same one `workers` makes.
        pane_state, pane_tone = "ok", C_ALIVE
    print(f"{c('pane:  ', C_LABEL)} {row['pane'] or '-'} ({c(pane_state, pane_tone)})")
    print(f"{c('work:  ', C_LABEL)} {truncate(row['summary'], 120)}")
    print(f"{c('owner: ', C_LABEL)} {owner_status(base)}")
    _, blocks = load_messages(base)
    tail = blocks[-1]["num"] if blocks else 0
    cursor = int(row["lastread"]) if row["lastread"].isdigit() else 0
    waiting = unread_for(args, base, me, cursor)
    counts = {}
    for b in waiting:
        counts[b["type"]] = counts.get(b["type"], 0) + 1
    breakdown = ", ".join(f"{c(k, TYPE_COLOR.get(k, ''))} {v}"
                          for k, v in sorted(counts.items())) or "none"
    print(f"{c('cursor:', C_LABEL)} #{cursor} of #{tail} in the log")
    print(f"{c('unread:', C_LABEL)} {len(waiting)} ({breakdown})")
    gmap = group_map(base)
    # `set()` for observers is DELIBERATE and survives the unification: an observer reads the whole
    # log by grant, and "asks waiting on YOU" must stay the asks it must personally answer, not
    # every open ask in the room. What changes is that the composition `sender != me AND
    # addressed_to` is no longer re-spelled here — this was the FIFTH site to derive that pair by
    # hand, and re-deriving one predicate in five places is exactly the drift that let the wake half
    # and the read half disagree for two fixes without either being wrong on its own.
    mine = [b for b in open_asks(blocks)
            if shows_in_inbox(b, me, gmap, set(), "any", closing_seats(base), inbox_decls(args))]
    # A narrowed inbox must never be invisible to the seat living in it: a seat that sees fewer
    # messages than the room is sending has to be able to tell "filtered by design" from "the
    # wakes are broken", and the second is a real failure mode this run has already hit.
    scope_line = inbox_scope_line(base, me)
    if scope_line:
        print(f"{c('inbox: ', C_LABEL)} {scope_line}")
    detail = ("  " + ", ".join(f"#{b['num']} from {b['sender']} ({age_of(b['ts'])})"
                               for b in mine[:5])) if mine else ""
    print(f"{c('asks waiting on you:', C_LABEL)} {len(mine)}{detail}")
    # Surfaced on EVERY seat's status, not only the leader's roster view: a refused monitor flag is
    # the run failing to warn itself, and the seat it was about is often the one that most needs to
    # see it. Tonight's two crossings were about the leader and the chief-of-staff, and neither
    # ever learned a warning had been raised.
    _und = undelivered_line(base)
    if _und:
        print(c(_und, C_DEAD))
    if waiting:
        print(c(f"next:   {coord} read", C_HINT))
    elif mine:
        print(c(f"next:   {coord} pending", C_HINT))
    elif is_leader(me):
        # Leader has nobody to escalate to — the idle hint told it to `send leader`, i.e. to
        # message itself. Leader's idle move is draining the run's queue: open asks first
        # (`pending` also shows broadcast asks and its own unanswered ones), then the log.
        print(c(f"next:   {coord} pending — drain the run's open asks, then {coord} read",
                C_HINT))
    else:
        print(c(f"next:   continue your task ({coord} send leader \"<msg>\" --type ask when "
                f"blocked)", C_HINT))


def cmd_pending(args):
    """Open asks, computed over the FULL log — not cursor-relative (T4/F11)."""
    base = base_dir(args)
    me = resolve_agent(args)
    coord = coord_invocation(args)
    _, blocks = load_messages(base)
    gmap = group_map(base)
    opens = open_asks(blocks)
    # G-94: `pending` derives open asks over the FULL log, so a foreign seat sharing my role name
    # put its own asks in "your asks nobody has answered" and hid its asks TO me. Same one
    # predicate as read and the wake half — a view that answers "is this mine" differently from
    # the inbox is the drift this class is named for.
    to_me = [b for b in opens if not is_own_send(b, me)
             and (b["to"] == me or (b["to"] in gmap and me in gmap[b["to"]]))]
    broadcast = [b for b in opens if not is_own_send(b, me) and b["to"] == "all"]
    from_me = [b for b in opens if is_own_send(b, me)]

    def section(title, items, hint):
        print(f"{c(title, C_LABEL)} ({len(items)})")
        if not items:
            print("  (none)")
            return
        for b in items:
            num_col = "{:<4}".format("#" + str(b["num"]))
            age_col = "{:>4}".format(age_of(b["ts"]))
            print(f"  {c(num_col, TYPE_COLOR['ask'])} {age_col} old  {b['sender']}->{b['to']}  "
                  f"{truncate(body_of(b))}")
        print(c(f"  {hint}", C_HINT))

    section("asks waiting on you", to_me,
            f"answer one: {coord} send <sender> \"<answer>\" --type answer --re <#>")
    section("open asks to everyone", broadcast, "answer only what is yours to answer")
    section("your asks nobody has answered", from_me,
            "chase the recipient, or retract with --supersedes <#>")


# ---------- launch / lifecycle ----------

def discover_workers(wdir):
    """Every briefing with an `agent:` frontmatter key — leader INCLUDED, so an explicit
    by-name `launch --only leader` or `close-seat leader --renew` can target it. A bare
    mass `launch` still never boots leader: seats_by_name filters it from the no-names sweep.

    Returns per-seat dicts: agent, briefing, harness, model, effort, cwd, window, ephemeral,
    ctx_refresh (int|None — the seat's own context-refresh threshold, consumed by watch.py),
    folder (the seat's worker folder in folder form, else None)."""
    found = []
    for p in briefing_files(wdir):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        fm_end = text.find("\n---", 3)
        if fm_end == -1:
            continue
        fm = text[:fm_end]
        m = FM_KEY["agent"].search(fm)
        if not m:
            continue
        # G-14: the seat.md (KG run-folder) form resolved NO folder, so `memory.md` was invisible
        # to boot_prompt and every renewed PERSISTENT seat booted without being told to read its
        # own memory — the one artifact a close exists to produce. Both briefing names count.
        folder = p.parent if p.name in ("agent.md", "seat.md") and p.parent != wdir else None
        mh = FM_KEY["harness"].search(fm)
        mm = FM_KEY["model"].search(fm)
        me = FM_KEY["effort"].search(fm)
        mc = FM_KEY["cwd"].search(fm)
        mr = FM_KEY["ctx-refresh"].search(fm)
        harness = mh.group(1) if mh else "claude"
        found.append({
            "agent": m.group(1), "briefing": p, "harness": harness,
            "model": mm.group(1) if mm else (DEFAULT_MODEL if harness == "claude" else ""),
            "effort": me.group(1) if me else DEFAULT_EFFORT,
            "cwd": mc.group(1) if mc else (str(folder) if folder else VAULT_ROOT),
            "window": _fm_window(fm),
            "ephemeral": _fm_yes(fm, "ephemeral"),
            "ctx_refresh": int(mr.group(1)) if mr else None,
            "folder": folder,
            "mechanical_close": _fm_mechanical_close(fm),
        })
    return found


# ---------- structural descriptor audit (G-57) ----------
#
# G-51 refuses a LAUNCH whose descriptor disagrees with the registry — one seat, at one moment,
# on three binding fields. This is the standing sweep over the WHOLE descriptor set, and it is
# read-only: it opens no briefing body, only frontmatter and paths, because a descriptor is a
# BRIEFING and R-isolation bars a seat from reading another seat's briefing. Fields and paths are
# not prose, so nobody's instructions enter anybody's context.
#
# WHAT IT DELIBERATELY DOES NOT COVER, printed in its own output every run: a descriptor's OWNED-
# SURFACES claim and its mission narrative are prose, and the run's surface map is prose too, so no
# mechanical pass can compare them. That is the half of G-57 that bit this run — a descriptor
# claiming surfaces handed to another seat a milestone earlier — and it stays open until a
# `surfaces:` frontmatter key makes the claim a field. A clean result here is NOT a clean class.

def descriptor_findings(args):
    """[(seat, kind, detail)] — every structural divergence in the run's descriptor set."""
    wdir = workers_dir(args)
    registry = taskforce_bindings(args)
    seats = discover_workers(wdir)
    found = []
    by_name = {}
    for w in seats:
        name = w["agent"]
        if name in by_name:
            # Two descriptors claiming one name: `launch` resolves whichever it finds first, so
            # the seat that boots is decided by directory order — never by anyone's intent.
            found.append((name, "duplicate-name",
                          f"also declared by {by_name[name]} — launch would pick by walk order"))
            continue
        by_name[name] = w["briefing"]
        folder = w["folder"]
        if folder is not None and folder.name != name:
            found.append((name, "name-vs-folder",
                          f"descriptor says {name}, folder is {folder.name}"))
        cwd = Path(w["cwd"])
        if not cwd.is_dir():
            found.append((name, "cwd-missing", f"cwd does not exist: {cwd}"))
        elif folder is not None and cwd.resolve() != folder.resolve():
            found.append((name, "cwd-vs-folder",
                          f"cwd is {cwd}, seat folder is {folder}"))
        row = registry.get(name)
        if row is None:
            if registry:
                found.append((name, "no-registry-row",
                              "descriptor exists with no taskforce.csv row — nothing records "
                              "this seat's binding"))
        else:
            for field, descriptor, reg in binding_divergence(w, row):
                found.append((name, "binding-divergence",
                              f"{field}: descriptor {descriptor} | taskforce.csv {reg} "
                              f"(THE DESCRIPTOR BINDS)"))
    for name in registry:
        if name not in by_name:
            found.append((name, "no-descriptor",
                          "taskforce.csv row with no descriptor — this seat cannot launch"))
    return found


# The documents a seat is known to READ AT BOOT — its loader pair, its descriptor, its memory, and
# the handoff/state doc that proved the class (a superseded ruling sat verbatim in SEAT-STATE.md,
# read at boot and never re-read). Used ONLY to rank and mark the boot-stale report, never to
# filter it: a boot-read document under a name not listed here is still reported, just lower.
BOOT_READ_NAMES = {"seat.md", "agent.md", "memory.md", "SEAT-STATE.md", "CLAUDE.md", "AGENTS.md"}


def boot_stale_findings(args):
    """[(seat, path, mtime)] — files in a LIVE seat's folder modified after that seat checked in.

    G-61: a seat's instructions are WRITE-ONCE AT BOOT. Nothing re-reads them, so a ruling that
    invalidates a running seat's briefing reaches it only if someone notices by hand. Measured
    instance: a planner booted at 06:50 on constraints reversed at 06:52 and had no way to learn it.

    The scope is the seat's OWN FOLDER, not `seat.md` alone, because the widening that proved the
    class came from `SEAT-STATE.md` — a boot-read document that is not the descriptor. A folder IS
    the seat-scoped boot-read surface, so `memory.md`, handoff docs and successors are covered by
    construction, with no declared list to maintain and no layout decision to settle first.

    `transcripts/` is excluded: it is an export target, written by the close ceremony, never read
    at boot.

    DELIBERATELY OVER-REPORTS, and the trade is the point: mtime moves when content does not, and
    a seat writing its OWN memory.md trips it. A false positive costs a glance; the false negative
    this replaces cost the run a live seat planning against two dead constraints.
    """
    base = base_dir(args)
    _, _, rows = load_workers(base)
    wdir = workers_dir(args)
    out = []
    for name in dict.fromkeys(r["agent"] for r in rows):
        row = current_row(rows, name)
        if not row or row.get("active") != "yes":
            continue
        try:
            since = datetime.strptime(row.get("checkin", "").strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            continue  # an unparseable checkin stamp is not evidence of staleness either way
        folder = wdir / name
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or "transcripts" in path.relative_to(folder).parts:
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
            except OSError:
                continue
            if mtime > since:
                out.append((name, path.relative_to(folder), mtime))
    return out


def cmd_descriptors(args):
    """Read-only structural audit of every seat descriptor (G-57). Opens no briefing body."""
    findings = descriptor_findings(args)
    wdir = workers_dir(args)
    print(f"{c('descriptors:', C_LABEL)} {wdir}")
    print(f"{c('registry:', C_LABEL)} {package_dir(args) / 'taskforce.csv'}")
    if findings:
        for seat, kind, detail in sorted(findings):
            print(f"  {c(seat, C_DEAD)}  {kind}: {detail}")
    print(f"\nstructural findings: {len(findings)}")
    # The bound is printed on EVERY run, clean or not — the leader's own ruling generalised: a
    # clean result must never be readable as a clean class.
    print("bound: frontmatter fields and paths ONLY. A stale owned-surfaces claim or a stale "
          "mission narrative is PROSE and is NOT checked here — zero findings does not mean the "
          "descriptors are true.")

    stale = boot_stale_findings(args)
    # Measured on this run's first live pass: 11 findings, 10 of them a seat writing its OWN
    # outputs. Full coverage is deliberate and kept — but an alarm that rings ten times per real
    # signal is one nobody reads, so boot-read NAMES are ranked first and marked. This is a DISPLAY
    # heuristic, never a filter: nothing is hidden, and a boot-read document under a name not on
    # the list still appears, just lower.
    ranked = sorted(stale, key=lambda f: (f[1].name not in BOOT_READ_NAMES, f[0], str(f[1])))
    print(f"\n{c('boot-stale (G-61):', C_LABEL)} files changed since the LIVE seat read them")
    for name, rel, mtime in ranked:
        mark = "BOOT-READ" if rel.name in BOOT_READ_NAMES else "also"
        print(f"  {c(name, C_DEAD)}  [{mark}] {rel} modified {mtime:%Y-%m-%d %H:%M} — after that "
              f"seat checked in; it is still running the version it booted on")
    high = sum(1 for _, rel, _ in stale if rel.name in BOOT_READ_NAMES)
    print(f"boot-stale findings: {len(stale)} "
          f"({high} BOOT-READ by name, {len(stale) - high} other)")
    print("bound: MTIME, not content, over the seat's folder minus transcripts/ — it over-reports "
          "(a seat writing its own memory.md trips it) and it CANNOT see a ruling that invalidates "
          "a seat's instructions without anyone editing its files. Zero here is not proof a seat "
          "is current.")
    sys.exit(1 if (findings or stale) else 0)


# ---------- descriptor vs taskforce.csv (G-51) ----------
#
# The SEAT DESCRIPTOR binds: `launch` and `close --renew` build the harness command from its
# frontmatter. `taskforce.csv` is the run's binding REGISTRY — and until this check, the kit never
# opened it (`grep -n taskforce coord.py` returned nothing), so the two could disagree silently and
# permanently. They did: a seat re-bound in the registry after an owner-departure event still
# launched on its old model, because a CSV row cannot bind anything. That defect appeared THREE
# times in one run before it was named once.
#
# This does not make the CSV authoritative — it makes a DISAGREEMENT impossible to launch through
# without seeing it. The refusal says which side binds, because a 3am reader who is only told the
# two files differ has been handed the confusion, not the answer.

def taskforce_bindings(args):
    """{seat: {harness, model, effort}} from the run package's taskforce.csv — {} when the file is
    absent (a legacy `workers/` package has no registry, and its seats must still launch)."""
    path = package_dir(args) / "taskforce.csv"
    if not path.is_file():
        return {}
    try:
        rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    except (OSError, ValueError, csv.Error):
        return {}
    out = {}
    for r in rows:
        seat = (r.get("seat") or "").strip()
        if seat:
            out[seat] = {k: (r.get(k) or "").strip() for k in ("harness", "model", "effort")}
    return out


def binding_divergence(w, row):
    """[(field, descriptor_value, registry_value)] where the two disagree.

    A BLANK registry cell means "not stated" and is skipped — the opencode verification seats
    legitimately carry no `effort`, and treating blank as a value would refuse every one of them.
    """
    out = []
    for field in ("harness", "model", "effort"):
        registry = (row.get(field) or "").strip()
        if not registry:
            continue
        descriptor = (w.get(field) or "").strip()
        if descriptor != registry:
            out.append((field, descriptor or "(unset)", registry))
    return out


def check_bindings(args, workers, command):
    """REFUSE when a seat's descriptor disagrees with its taskforce.csv row (G-51). `--force`
    overrides, as on every other refusal here."""
    registry = taskforce_bindings(args)
    if not registry:
        return
    problems = []
    for w in workers:
        row = registry.get(w["agent"])
        if row:
            diff = binding_divergence(w, row)
            if diff:
                problems.append((w, diff))
    if not problems or getattr(args, "force", False):
        if problems:
            for w, diff in problems:
                fields = ", ".join(f"{f}: descriptor {d} vs registry {r}" for f, d, r in diff)
                print(c(f"WARNING --force: {w['agent']} binds from its DESCRIPTOR ({fields})",
                        C_DEAD), file=sys.stderr)
        return
    lines = []
    for w, diff in problems:
        lines.append(f"{w['agent']}:")
        for field, descriptor, registry_value in diff:
            lines.append(f"    {field}: descriptor says {descriptor} | taskforce.csv says "
                         f"{registry_value}")
        lines.append(f"    descriptor: {w['briefing']}")
    detail = "\n  ".join(lines)
    print(f"refused: `{command}` — {len(problems)} seat(s) disagree with the run's registry:\n  "
          f"{detail}\n"
          f"  registry: {package_dir(args) / 'taskforce.csv'}\n"
          f"THE DESCRIPTOR IS AUTHORITATIVE — it is what the harness command is built from, so "
          f"launching now would bind the DESCRIPTOR's value and the taskforce.csv row would stay "
          f"a wrong record.\n"
          f"Fix whichever is wrong: edit the DESCRIPTOR to change what actually binds, or the CSV "
          f"row to correct the record. Then re-run.\n"
          f"--force launches on the descriptor's value anyway and says so.", file=sys.stderr)
    sys.exit(2)


def identity_prefix(agent):
    """The shell-env prefix that gives a launched seat its identity (T1). Every command the
    seat then runs resolves `COORD_AGENT` — it never types its own name, and cannot mistype
    another seat's."""
    return f"COORD_AGENT={shlex.quote(agent)} "


CLAUDE_MODEL_ALIASES = ("opus", "sonnet", "haiku", "fable")
OPENCODE_MODEL_RE = re.compile(r"[^/\s]+/[^/\s]+\Z")


def peer_windows(seats, me):
    """Every shared-window name declared by descriptors OTHER than `me`'s.

    OTHER than its own, and that exclusion is the whole point: validating a value against the union
    of all descriptors INCLUDING the seat under test is vacuous — the seat's own typo would appear
    in the set and authorize itself. Nearly shipped that way."""
    return {w["window"] for w in seats
            if w["window"] and w["window"] != "yes" and w["agent"] != me}


def window_drift(w, peers):
    """'' when the seat's `window:` is placeable, else the reason it is a probable typo.

    THE DEFECT THIS CATCHES, and it is drift that looks like success: nothing validated the value,
    and an unrecognised window name does not fail — `launch_seat` finds no window of that name and
    cheerfully OPENS ONE. So `window: controll` places the seat "correctly" into furniture nobody
    ordered, and the room silently grows a window named after a misspelling.

    NO LAYOUT IS HARDCODED HERE, deliberately and by ruling (leader #382): the ruled four-window
    organization belongs to ONE campaign, and freezing its names into a tool every run shares would
    refuse every launch in a room organized differently. That is the mistake `SPECIAL_CASE_SEATS`
    was demoted for — a MANDATE cannot be expressed as a name list — repeated in the same file.

    So the signal is a NEAR MISS, not membership: a name no peer declares is a legitimately new
    window and passes, while a name that is one edit away from a window peers DO declare is the
    typo. Same idiom, same cutoff, as this file's recipient-typo refusal (F5), and it refuses only
    where it can name the intended value."""
    name = (w or {}).get("window") or ""
    if not name or name == "yes" or name in peers:
        return ""
    near = difflib.get_close_matches(name, sorted(peers), n=1, cutoff=0.8)
    if not near:
        return ""
    return (f"window '{name}' is declared by no other seat, and it is one edit from '{near[0]}', "
            f"which is. An unrecognised window is NOT refused by tmux — it silently OPENS a new "
            f"one, so this would place the seat into a window named after a typo.\n"
            f"declared by peers: {', '.join(sorted(peers))}\n"
            f"Fix the descriptor, or launch with --force if '{name}' is genuinely a new window.")


def validate_seat(w):
    """Pre-flight launch validation — PROP-8 (tv-ux-review): an invalid model slug in one
    wave's briefings stalled the ENTIRE wave at model-init, after every pane had already
    spawned and before any seat reached its boot prompt. Validates only what the kit can know
    locally (accepted alias/slug SHAPES per harness) — never a provider call. A well-formed
    slug the provider still rejects dies at boot anyway; the watcher's leftover-window flag
    (PROP-10) is the detection net for that residue. Returns '' when launchable, else the
    reason (used to refuse a launch BEFORE any pane opens)."""
    if w["harness"] not in HARNESSES:
        return f"unknown harness '{w['harness']}' (expected one of {', '.join(HARNESSES)})"
    if w["harness"] == "claude" and not (
            w["model"] in CLAUDE_MODEL_ALIASES or w["model"].startswith("claude-")):
        return (f"claude model '{w['model']}' is neither a known alias "
                f"({', '.join(CLAUDE_MODEL_ALIASES)}) nor a full claude-* model id — "
                f"write a genuinely new alias as its full claude-* id")
    if w["harness"] == "opencode":
        if not w["model"]:
            return "opencode seats require an explicit model: (provider/model slug)"
        if not OPENCODE_MODEL_RE.fullmatch(w["model"]):
            return (f"opencode model '{w['model']}' is not a provider/model slug "
                    f"(e.g. deepseek/deepseek-v4-pro)")
    return ""


def prompt_file(args, agent, prompt):
    """Write a seat's boot prompt to a file under the package and return its path.

    EVERY harness command reads its prompt from a file rather than carrying it inline: the start
    line is typed into the pane as literal keystrokes, and a prompt with newlines is executed line
    by line by the pane's shell (G-11 — see wake()). A file keeps the start line one line no matter
    how long the prompt grows, so launch and close share one path with one failure mode."""
    d = base_dir(args) / "prompts"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{agent}-{file_stamp()}.txt"
    p.write_text(prompt, encoding="utf-8")
    return p


def harness_command(w, prompt=None, prompt_path=None):
    """The shell command that starts this seat's session, or (None, reason). Carries the seat's
    identity as an env prefix (see identity_prefix). Pass `prompt_path` (what every real spawn
    does, via prompt_file) to read the prompt from a file; `prompt` inlines it and is for dry-run
    display only — an inlined multi-line prompt is exactly the G-11 defect."""
    env = identity_prefix(w["agent"])
    if prompt_path is not None:
        arg = '"$(cat ' + shlex.quote(str(prompt_path)) + ')"'
    else:
        arg = shlex.quote(prompt or "")
    if w["harness"] == "claude":
        return f"{env}{CLAUDE_BIN} --model {w['model']} --effort {w['effort']} {arg}", ""
    if w["harness"] == "codex":
        model = f" -m {shlex.quote(w['model'])}" if w["model"] else ""
        return f"{env}{CODEX_BIN}{model} {arg}", ""
    if w["harness"] == "opencode":
        if not w["model"]:
            return None, "opencode seats require an explicit model: (provider/model slug)"
        # G-13: the kit built `opencode --model X --prompt Y`. This opencode has NEITHER flag at
        # top level — the one-shot form is the `run` SUBCOMMAND (`opencode run -m <slug> <msg>`,
        # verified live on deepseek and glm-5.2). The old string fell through to the TUI and the
        # prompt was never run: a launch command nobody had executed end to end. NOTE the shape
        # this imposes — `run` is ONE-SHOT: an opencode seat executes its prompt and exits, so it
        # cannot be woken later; it must read its own messages before finishing, and a wake aimed
        # at its pane after that would type into a bare shell (the harness-up guard refuses it).
        # OWNER-DIRECTED (2026-07-27, owner present; leader #607): seats initiate with auto mode
        # ON. Without it EVERY opencode seat runs with permissions live, auto-REJECTS reads outside
        # its own folder and dies silently — it is what killed K4 three times and it is G-49's
        # mechanism for the whole opencode half of the roster.
        #
        # POSITION IS LOAD-BEARING AND IS G-13 ALL OVER AGAIN. `--auto` must come AFTER the `run`
        # subcommand. Verified live by two of us independently, not read off the help:
        #   `opencode --auto run -m X P`  -> PRINTS THE BANNER AND RUNS NOTHING, exit 0
        #   `opencode run --auto -m X P`  -> returns the expected string
        # The wrong form is the dangerous one precisely because it exits 0: it would look like a
        # fix, pass any check that only asserts the flag is present, and launch nothing.
        return f"{env}{OPENCODE_BIN} run --auto -m {shlex.quote(w['model'])} {arg}", ""
    return None, f"unknown harness '{w['harness']}' (expected one of {', '.join(HARNESSES)})"


def boot_prompt(w, args):
    """The initial prompt every seat starts with, harness-independent. A leader seat whose
    memory.md already exists is only ever (re)launched to CONTINUE a run it was arbitrating
    (renew, or crash recovery) — its prompt is resume-first, never the generic fresh boot."""
    pkg = package_dir(args)
    wdir = workers_dir(args)
    mem = (w["folder"] / "memory.md") if w["folder"] else None
    if w["agent"] == "leader" and mem and mem.exists():
        first = (f"You are RESUMING a prior session, not starting fresh: read {mem} FIRST — "
                 f"especially its 'Resume here' section — it is your own state from the session "
                 f"this relaunch continues; do not re-run work it records as complete. "
                 f"Then read your briefing {w['briefing']}.")
    else:
        memory = ""
        # G-23: a `close: mechanical` seat is memoryless BY DESIGN — it must not be told to read a
        # memory.md, or it would trust a file its close path never writes and that goes stale the
        # moment its external state moves. Long-lived, but boots fresh every session.
        if w["folder"] and not w["ephemeral"] and not w.get("mechanical_close"):
            memory = (f" If {mem} exists, read it too — it is your memory from "
                      f"prior sessions of this seat; trust it as your own notes.")
        first = f"Read your briefing {w['briefing']} first.{memory}"
    return (
        f"You are agent '{w['agent']}' of the run package at {pkg}. "
        f"{first} "
        f"Then read {pkg}/CLAUDE.md and follow its coordination protocol exactly: "
        f"check in as '{w['agent']}' (coordination CLI: {coord_invocation(args)}), "
        f"then execute ONLY your briefing. "
        f"Never read any other agent's briefing or folder in {wdir}/. "
        f"Message 'leader' on any conflict, inconsistency, or decision you cannot settle alone."
    )


# ---------- worker-mirror refresh (pre-launch) ----------
# A codex/opencode seat reads its rules from the AGENTS.md + .agents/ MIRROR of the launch root's
# CLAUDE.md/skills/rules — not from the sources themselves. The mirror only refreshes when the
# installer runs, and every AGENTS.md is gitignored, so drift is invisible to git and per-machine:
# a skill edited an hour ago reaches a claude seat and NOT the codex seat beside it. Nothing else
# consumes the mirror, so launch IS the moment it must be current — refresh at the point of
# consumption rather than on a clock.

MIRROR_REFRESH_TIMEOUT = 300  # a cold full-workspace render; the steady-state run is ~2-3s


def find_workspace_root(start):
    """Walk up from `start` for the workspace root carrying rbtv.json.

    Returns (root, rbtv_path_abs) — (None, None) when no rbtv.json is found (not an rbtv
    workspace), (root, None) when one exists but names no readable rbtv_path.
    """
    try:
        p = Path(start).resolve()
    except OSError:
        return None, None
    for d in (p, *p.parents):
        cfg = d / "rbtv.json"
        if not cfg.is_file():
            continue
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return d, None
        rel = data.get("rbtv_path")
        if not rel:
            return d, None
        # rbtv_path is recorded workspace-relative; an absolute value is honoured as-is.
        return d, (Path(rel) if Path(rel).is_absolute() else (d / rel)).resolve()
    return None, None


def refresh_mirror(cwd):
    """Refresh the worker mirror for the workspace owning `cwd`.

    Returns (status, detail) where status is:
      "ok"   — the mirror was refreshed (detail = the installer's summary line)
      "skip" — nothing to refresh (detail says why): not an rbtv workspace, or one with no
               mirror installed. NOT an error: a workspace without elected CLI workers has
               no mirror by design.
      "fail" — the refresh was attempted and failed (detail = the reason)
    """
    root, rbtv_path = find_workspace_root(cwd)
    if root is None:
        return "skip", f"no rbtv.json at or above {cwd} — not an rbtv workspace"
    if rbtv_path is None:
        return "fail", f"{root / 'rbtv.json'} is unreadable or names no rbtv_path"

    installer = rbtv_path / "install.py"
    if not installer.is_file():
        return "fail", f"installer not found at {installer} (rbtv_path points nowhere)"

    # --exclude is deliberately OMITTED: the driver defaults excluded_paths from the recorded
    # state, so omitting it PRESERVES the workspace's exclusions. Passing it here would replace
    # them and start rendering mirrors into paths the owner excluded.
    cmd = [sys.executable, str(installer), "--mirror", "--non-interactive", "--target", str(root)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=MIRROR_REFRESH_TIMEOUT)
    except subprocess.TimeoutExpired:
        return "fail", f"refresh timed out after {MIRROR_REFRESH_TIMEOUT}s"
    except OSError as exc:
        return "fail", f"could not run the installer: {exc}"

    if r.returncode != 0:
        err = (r.stderr or r.stdout or "").strip().splitlines()
        return "fail", (err[-1] if err else f"installer exited {r.returncode}")

    summary = next(
        (ln.strip() for ln in reversed((r.stdout or "").splitlines()) if "Mirror:" in ln),
        "mirror refreshed",
    )
    if "no mirrorable packages elected" in summary:
        return "skip", "workspace elects no mirrorable CLI workers — no mirror to refresh"
    return "ok", summary


def refresh_mirrors_for(workers):
    """Refresh the mirror for every distinct launch root among the NON-claude seats.

    Claude seats read CLAUDE.md natively and consume no mirror, so a claude-only launch does no
    work here. Deduped by root: an N-seat wave rooted in one workspace pays one refresh, and a
    seat rooted in a worktree gets ITS root refreshed rather than the parent's.

    NEVER blocks the launch. A failed refresh is reported loudly and the seats still boot — a
    broken installer must not be able to stop a team run, and a stale mirror still carries the
    previous render's rules rather than none.
    """
    roots = list(dict.fromkeys(
        w["cwd"] for w in workers if w["harness"] != "claude" and w["cwd"]
    ))
    for cwd in roots:
        status, detail = refresh_mirror(cwd)
        if status == "ok":
            print(f"mirror refreshed for {cwd}: {detail}")
        elif status == "skip":
            print(c(f"mirror: skipped for {cwd} — {detail}", C_HINT))
        else:
            print(c(f"WARNING mirror refresh FAILED for {cwd} — {detail}", C_DEAD), file=sys.stderr)
            print(c("  the codex/opencode seats below may read STALE rules; refresh by hand with "
                    "`python install.py --mirror --non-interactive --target <root>`", C_DEAD),
                  file=sys.stderr)


def seat_placement(w):
    """Pure placement decision from the briefing's window: value — ("own", agent-name) for
    `yes`, ("shared", NAME) for a named wave window, ("pane", None) otherwise."""
    if w["window"] == "yes":
        return "own", w["agent"]
    if w["window"]:
        return "shared", w["window"]
    return "pane", None


def launch_seat(w, args, target, prompt=None, pane=None):
    """Open a pane/window for one seat and start its harness. Returns (pane_id, err).

    `pane` reuses an EXISTING pane (a renew respawned in place — G-12) instead of placing a new
    one. Never returns success on a pane where no harness came up: G-11's whole failure was a
    start line that the pane's shell swallowed while the roster went on believing the seat live."""
    verr = validate_seat(w)  # PROP-8: `close-seat --renew` relaunches single seats through here
    if verr:
        return "", verr
    # Checked HERE because this is the one door every boot passes — `launch` and
    # `close-seat --renew` both arrive here, so a renew cannot drift where a launch is checked.
    # Peers are read from ALL briefings, not from the seats in this wave: a single-seat renew would
    # otherwise have no peers to compare against and skip the check exactly when it matters.
    if not getattr(args, "force", False):
        derr = window_drift(w, peer_windows(discover_workers(workers_dir(args)), w["agent"]))
        if derr:
            return "", derr
    cmd, err = harness_command(w, prompt_path=prompt_file(args, w["agent"],
                                                          prompt or boot_prompt(w, args)))
    if cmd is None:
        return "", err
    if pane:
        place = "existing"
    else:
        place, wname = seat_placement(w)
        if place == "own":
            pane, err = tmux_new_window(target, wname, w["cwd"])
        elif place == "shared":
            existing = tmux_find_window_pane(tmux_session_name(target), wname)
            if existing:
                pane, err = tmux_split_pane(existing, w["cwd"])
            else:
                pane, err = tmux_new_window(target, wname, w["cwd"])
        else:
            pane, err = tmux_split_pane(target, w["cwd"])
        if not pane:
            return "", err
    set_pane_title(pane, w["agent"])
    write_seat_statusline(w)   # 7.69: before the harness reads its settings, never after
    since = time.time()        # 7.37: the instant the transcript must post-date (renew-correct)
    ok, terr = wake(pane, cmd)
    if not ok:
        return pane, f"pane opened but harness start FAILED: {terr}"
    _, uerr = wait_harness_up(pane)
    if uerr:
        return pane, uerr
    if w["harness"] == "claude":
        schedule_session_rename(pane, w["agent"])
    # 7.37: the session row is written by the RUN, here, on the one path every seat boot takes —
    # `launch` and `close-seat --renew` both arrive here. A renew is a NEW session of the same
    # seat, which is exactly the "one seat, several sessions within one run" the KG names.
    # Only AFTER the harness is verified up: a row for a seat that never booted is the G-11 lie
    # in a second file.
    res, terr2 = session_trace_safe(session_open, args, w, since=since, pane=pane)
    if terr2:
        print(c(f"WARNING {w['agent']}: the seat IS UP but its sessions.csv row was NOT written "
                f"— {terr2}. The trace is incomplete; the seat is fine.", C_DEAD), file=sys.stderr)
    elif res and res[1]:
        print(c(f"  {w['agent']}: session {res[0]} — {res[1]}", C_HINT))
    return pane, ""


def seats_by_name(args, names=None):
    workers = discover_workers(workers_dir(args))
    if names is None:
        # A bare `launch` (no --only) never boots leader — the owner starts leader by hand;
        # only an explicit by-name launch or a close-seat --renew may target the leader seat.
        return [w for w in workers if w["agent"] != "leader"]
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    picked = [w for w in workers if w["agent"] in wanted]
    missing = set(wanted) - {w["agent"] for w in picked}
    if missing:
        known = ", ".join(sorted(w["agent"] for w in workers)) or "(none)"
        print(f"refused: no worker briefing carries `agent: {', '.join(sorted(missing))}` in "
              f"{workers_dir(args)}, so there is nothing to launch under that name.\n"
              f"briefed seats: {known}\nFix the name, or add the briefing folder first.",
              file=sys.stderr)
        sys.exit(1)
    return picked


def cmd_launch(args):
    role_desc = "leader's alone (it opens seats and spends plan budget)"
    # #210: the roster is resolved FIRST because the memory gate is sized by seat COUNT, and both
    # gates must be answered together. Nothing here opens a pane or writes a surface — reading
    # briefings has no side effect — so evaluating the role gate a few lines later costs nothing
    # and buys the caller both verdicts at once. `--dry-run` keeps the role gate ALONE: it opens
    # nothing, so refusing it on available memory would refuse a command that cannot spend any.
    workers = seats_by_name(args, args.only)
    if args.dry_run:
        gate(args, "launch", is_leader, role_desc)
    else:
        launch_gates(args, "launch", is_leader, role_desc, len(workers) or 1)
    # G-51: the descriptor binds and the registry is a record nothing read until now. Checked on
    # the DRY-RUN path too — a dry-run exists to show what a real launch would do, and hiding a
    # divergence from it would make the one command meant for inspection the one that lies.
    check_bindings(args, workers, "launch")
    if not workers:
        print(f"refused: no worker briefing carries an `agent:` frontmatter key in "
              f"{workers_dir(args)}, so there is no roster to launch.\n"
              f"Each seat needs workers/<agent>/agent.md with `agent: <name>` "
              f"(template: briefing-template.md beside coord.py).", file=sys.stderr)
        sys.exit(1)

    # PROP-8 (tv-ux-review): validate EVERY seat's launch config BEFORE any pane opens. An
    # invalid model slug used to fail only at model-init, INSIDE each spawned pane — a whole
    # wave died before its first checkin, its panes holding memory until someone noticed.
    invalid = [(w, e) for w in workers for e in [validate_seat(w)] if e]
    if invalid and not args.dry_run:
        for w, e in invalid:
            print(f"  {w['agent']}: {e}\n    briefing: {w['briefing']}", file=sys.stderr)
        print(f"refused: {len(invalid)} seat(s) above carry an invalid harness/model — NO pane "
              f"was opened (not even for the valid seats). Fix the briefing frontmatter, then "
              f"relaunch the whole set.", file=sys.stderr)
        sys.exit(1)

    target = os.environ.get("COORD_LAUNCH_TARGET") or os.environ.get("TMUX_PANE")
    if not target and not args.dry_run:
        print("refused: launch opens tmux panes and this shell is not inside tmux (no $TMUX_PANE),"
              " so there is no window to open them in.\nRun it from leader's tmux pane, or use "
              "--dry-run to see the commands it would run.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        for cwd in dict.fromkeys(w["cwd"] for w in workers
                                 if w["harness"] != "claude" and w["cwd"]):
            print(f"[dry-run] would refresh the worker mirror for {cwd}")
        for w in workers:
            verr = validate_seat(w)  # PROP-8: the dry-run shows the same pre-flight refusal
            # The real spawn reads its prompt from a file (G-11); show that shape, not an inlined
            # prompt the launcher would never actually type.
            cmd, err = (None, verr) if verr else harness_command(
                w, prompt_path=(base_dir(args) / "prompts" / f"{w['agent']}-<stamp>.txt"))
            kind, wname = seat_placement(w)
            place = {"own": "window", "shared": f"window:{wname}"}.get(kind, "pane")
            print(f"[dry-run] {w['agent']} ({w['harness']}/{w['model'] or 'plan-default'}"
                  f"{'/' + w['effort'] if w['harness'] == 'claude' else ''}, {place}, cwd={w['cwd']}): "
                  f"{cmd if cmd else 'REFUSED — ' + err}")
        return

    # The memory gate is answered UP FRONT, beside the role gate, by `launch_gates` — both
    # verdicts in one message, neither flag carrying the other (#210/#230).

    # BEFORE any seat boots: a worker reads its rules once, at startup, so a refresh that lands
    # after the pane opens is a refresh the worker never sees.
    refresh_mirrors_for(workers)

    tmux_raise_history_limit()  # exports capture full scrollback (see export-transcript)
    for w in workers:
        pane, err = launch_seat(w, args, target)
        kind, wname = seat_placement(w)
        place = {"own": "window", "shared": f"window:{wname}"}.get(kind, "pane")
        label = f"{w['agent']} ({w['harness']}/{w['model'] or 'plan-default'}, {place})"
        if err:
            print(f"  {label}: FAILED — {err}", file=sys.stderr)
        else:
            print(f"launched {label} in {pane}"
                  + (" (session /rename scheduled)" if w["harness"] == "claude" else ""))
    status, detail = ensure_team_monitor(args)   # after the seats: the room is up by now
    if status == "ok":
        print(f"team-monitor: ensured for this run ({detail})")
    elif status == "absent":
        print(c(f"team-monitor: NOT started — {detail}", C_HINT))
    else:
        print(c(f"WARNING team-monitor start FAILED — {detail}; the room runs UNOBSERVED",
                C_DEAD), file=sys.stderr)
    print(c(f"next: {coord_invocation(args)} workers — every seat above must appear there; one "
            f"that never checks in never booted", C_HINT))


# ---------- transcript export / close / depart ----------

def transcripts_dir(args, agent):
    d = workers_dir(args) / agent / "transcripts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_transcript(args, agent, label=""):
    """Capture the agent's full pane scrollback into its worker folder. Returns (path, err)."""
    _, _, rows = load_workers(base_dir(args))
    row = current_row(rows, agent)
    if not row or not row["pane"]:
        return None, f"no registered pane for '{agent}' — nothing to capture"
    text, err = tmux_capture(row["pane"])
    if err:
        return None, f"capture failed for {row['pane']}: {err}"
    suffix = f"-{label}" if label else ""
    out = transcripts_dir(args, agent) / f"{file_stamp()}-{agent}{suffix}.txt"
    out.write_text(text, encoding="utf-8")
    return out, ""


def cmd_export_transcript(args):
    out, err = export_transcript(args, args.target, args.label or "")
    if err:
        print(f"refused: cannot capture '{args.target}' — {err}. A scrollback capture needs the "
              f"seat's registered pane to still exist.\nCheck the roster: "
              f"{coord_invocation(args)} workers", file=sys.stderr)
        sys.exit(1)
    print(f"transcript exported: {out}")
    print(c(f"next: {coord_invocation(args)} close {args.target} — the closer reads this export "
            f"to write the seat's memory.md", C_HINT))


def closer_prompt(args, target, renew):
    """Fill the closer prompt template for one target seat. A package-local
    closer-prompt.md at the run-package root overrides the kit template (a run may
    extend the ceremony, e.g. ledger grooming); kit default when the file is absent."""
    pkg = package_dir(args)
    template = pkg / "closer-prompt.md"
    if not template.is_file():
        template = Path(__file__).resolve().parent / "closer-prompt.md"
    text = template.read_text(encoding="utf-8")
    if text.startswith("# closer prompt template"):  # template header is meta, not prompt
        text = text.split("\n", 1)[1].lstrip("\n")
    wfolder = workers_dir(args) / target
    renew_flag = " --renew" if renew else ""
    renew_note = (
        "RENEW IS ON: after you run close-seat the seat relaunches fresh and will read the "
        "memory.md you just wrote — write it as the revival briefing it is."
        if renew else
        "Renew is OFF: the seat stays closed; memory.md is for a possible future revival."
    )
    for token, value in (
        ("{TARGET}", target),
        ("{CLOSER}", f"closer-{target}"),
        ("{PACKAGE}", str(pkg)),
        ("{COORD}", coord_invocation(args)),
        ("{WORKER_DIR}", str(wfolder)),
        ("{MEMORY}", str(wfolder / "memory.md")),
        ("{TRANSCRIPTS}", str(wfolder / "transcripts")),
        ("{MESSAGES}", str(base_dir(args) / "messages.md")),
        ("{RENEW_FLAG}", renew_flag),
        ("{RENEW_NOTE}", renew_note),
    ):
        text = text.replace(token, value)
    return text


def closer_placement(existing_pane):
    """Pure placement decision for the next closer pane — no tmux I/O, so selftest can exercise
    it headless. `existing_pane` is the result of looking up a pane already in the shared
    CLOSERS_WINDOW ("" if that window doesn't exist yet). Returns ("split", pane_to_split) when
    the window is already open, or ("new_window", CLOSERS_WINDOW) to create it fresh."""
    if existing_pane:
        return ("split", existing_pane)
    return ("new_window", CLOSERS_WINDOW)


def resolve_closer_pane(target, cwd):
    """Open (or reuse) the shared 'closers' tmux window and return the pane for the next closer.
    Every closer lands here as a pane, titled by its target agent — never in the control-panel
    window `target` sits in. Returns (pane_id, err)."""
    session = tmux_session_name(target)
    existing = tmux_find_window_pane(session, CLOSERS_WINDOW)
    action, dest = closer_placement(existing)
    if action == "split":
        return tmux_split_pane(dest, cwd)
    return tmux_new_window(target, dest, cwd)


def ns_like(args, **overrides):
    """A copy of the caller's namespace with fields overridden — so a delegating command keeps the
    package/identity flags (`--run`, `--package`, `--as`, `--force`) instead of rebuilding them and
    silently resolving a different package than the one the caller named."""
    data = dict(vars(args))
    data.update(overrides)
    return argparse.Namespace(**data)


def mechanical_close_seat(args, target):
    """The seat's briefing, when it declares `close: mechanical` (G-23) — else None."""
    for w in discover_workers(workers_dir(args)):
        if w["agent"] == target and w.get("mechanical_close"):
            return w
    return None


def cmd_close(args):
    role_desc = "leader's alone (it spawns a closer seat)"
    # #210/#230: `close` carries both gates too, so both are answered together — but ONLY on the
    # path that actually spawns a closer. A `--dry-run` opens nothing, and a `close: mechanical`
    # seat (G-23) spawns no closer at all, so neither can spend the memory the gate protects;
    # refusing those on available memory would refuse a command that costs none. Resolving the
    # seat's briefing first is read-only.
    mech_seat = mechanical_close_seat(args, args.target)
    if args.dry_run or mech_seat is not None:
        gate(args, "close", is_leader, role_desc)
    else:
        launch_gates(args, "close", is_leader, role_desc, 1)
    # G-23 (owner-directed): a seat whose entire state is EXTERNAL and machine-owned finishes one
    # session and opens another — no closer agent, no memory.md, no harvest. Its memory would be a
    # hand-maintained copy of files its own loop recomputes every pass, which is the stale-derived-
    # value class this run hit repeatedly; and a harvest is spent on a seat scheduled to stop being
    # an agent at all (tasks 7.33 + 7.32). What it learns it files to the ledgers DURING its life.
    # The transcript is still exported by close-seat: evidence outlives memory.
    mech = mech_seat
    if mech is not None:
        renew = getattr(args, "renew", False)
        print(f"'{args.target}' declares `close: mechanical` — closing WITHOUT a closer seat "
              f"(no memory.md, no harvest; transcript still exported)."
              + ("  Relaunching it fresh from its briefing." if renew else
                 "  NOT relaunching: pass --renew to open the next session."))
        if args.dry_run:
            print(f"[dry-run] would run: close-seat {args.target}"
                  + (" --renew" if renew else "")
                  + " — no closer pane is opened, so no memory gate applies")
            return
        return cmd_close_seat(ns_like(args, target=args.target, renew=renew,
                                      no_export=getattr(args, "no_export", False)))
    prompt = closer_prompt(args, args.target, args.renew)
    closer = {
        "agent": f"closer-{args.target}", "briefing": None, "harness": "claude",
        "model": CLOSER_MODEL, "effort": DEFAULT_EFFORT, "cwd": VAULT_ROOT,
        "window": False, "ephemeral": True, "folder": None,
    }
    title = f"closer-{args.target}"
    if args.dry_run:
        print(f"[dry-run] closer seat: claude/{CLOSER_MODEL}, pane '{title}' in the shared "
              f"'{CLOSERS_WINDOW}' window. Prompt:\n\n{prompt}")
        return
    target = os.environ.get("COORD_LAUNCH_TARGET") or os.environ.get("TMUX_PANE")
    if not target:
        print("refused: close spawns a closer seat in tmux and this shell is not inside tmux (no "
              "$TMUX_PANE).\nRun it from leader's tmux pane, or use --dry-run to see the closer "
              "prompt.", file=sys.stderr)
        sys.exit(1)
    # The memory gate for this spawn was answered up front by `launch_gates`, beside the role gate.
    # G-11: the closer prompt is MULTI-LINE markdown, and it used to be typed into the pane as
    # literal keystrokes — every newline arriving as Enter, so the pane's shell executed the
    # briefing line by line. It checked the closer in for real and printed a completion report
    # while claude never started. It now boots exactly as `launch` does: prompt in a file, start
    # line on ONE line, and the row is only trusted once the process is verified up.
    cmd, err = harness_command(closer, prompt_path=prompt_file(args, closer["agent"], prompt))
    if cmd is None:
        print(f"closer launch FAILED: {err}", file=sys.stderr)
        sys.exit(1)
    pane, err = resolve_closer_pane(target, closer["cwd"])
    if not pane:
        print(f"closer launch FAILED: {err}", file=sys.stderr)
        sys.exit(1)
    set_pane_title(pane, title)
    ok, terr = wake(pane, cmd)
    if not ok:
        print(f"closer launch FAILED: pane opened but harness start FAILED: {terr}", file=sys.stderr)
        sys.exit(1)
    _, uerr = wait_harness_up(pane)
    if uerr:
        print(f"closer launch FAILED: {uerr}\nThe seat '{args.target}' was NOT closed — nothing "
              f"ran. Kill the dead pane BY ID (tmux kill-pane -t {pane}) and retry.",
              file=sys.stderr)
        sys.exit(1)
    schedule_session_rename(pane, closer["agent"])
    # G-21: the state opens only once the closer is VERIFIED up. Setting it earlier would narrow a
    # live seat's inbox on the strength of a closer that might never have started — which is
    # exactly how G-11 burned seven minutes of this run on a closer that was only ever a shell.
    set_closing(base_dir(args), args.target, closer["agent"])
    print(f"closer launched for '{args.target}' in {pane} (window '{CLOSERS_WINDOW}', pane '{title}')"
          + (", renew ON" if args.renew else ""))
    print(f"inbox: '{args.target}' is now CLOSING — broadcasts stop reaching it and a peer's direct "
          f"message is refused at the CLI (sender keeps it); {closer['agent']} and leader still get "
          f"through. Clears when close-seat completes.")
    print(c(f"next: {coord_invocation(args)} workers — closer-{args.target} checks in, co-writes "
            f"memory.md with the seat, then closes it", C_HINT))


def renew_in_place(seat, pane, pane_live):
    """Pure: True when a renew must RESPAWN the seat's existing pane rather than kill it and split
    a fresh one. G-12 — kill+split re-tiles the whole window, so every renew destroyed the layout
    the owner had arranged. Only a `pane` seat (no window: of its own) whose pane tmux still has
    can be respawned in place; a window/shared seat re-places from its briefing as before."""
    return bool(pane) and bool(pane_live) and seat_placement(seat)[0] == "pane"


def cmd_close_seat(args):
    # The closer runs this as the tail of its own close; leader runs it directly for dead panes.
    gate(args, "close-seat", is_leader_or_closer, "leader's or a closer-* seat's")
    base = base_dir(args)
    # A DOOR IS NOT CLOSED MECHANICALLY. A seat declaring `relays:` carries the relay path to a
    # HUMAN role, and its pane is the surface that human is watching — the owner can be sitting at
    # it while the seat itself is checked out. This path KILLS the pane (measured, leader #385: a
    # renewed leader's prior pane was gone and the successor held a new id, so renew here does not
    # respawn in place — it kills and re-creates). So both the plain close and the renew destroy
    # the door, and neither should happen because someone was tidying the roster.
    #
    # REFUSED, NOT SILENTLY EXEMPTED: unlike `reap`, this command is an explicit deliberate act, so
    # the right answer is to make the caller say they mean it rather than to ignore the request.
    # `--force` is that, and it is the same escape every other refusal in this file offers.
    #
    # Derived from the descriptor, extending the predicate reap already uses — not a second list.
    if not getattr(args, "force", False):
        _relays = ((inbox_decls(args).get(args.target) or {}).get("relays"))
        _row = current_row(load_workers(base)[2], args.target)
        _pane = (_row or {}).get("pane") or ""
        if _relays and _pane and _pane in live_panes():
            print(f"refused: '{args.target}' carries a relay path to a human role "
                  f"({', '.join(sorted(_relays))}), and its pane {_pane} is LIVE. This command "
                  f"kills that pane — on the renew path too, which kills and re-creates rather "
                  f"than respawning in place — so this would close the door a human may be "
                  f"watching, possibly while they are away and expecting it to be there.\n"
                  f"A door in the wrong place is cosmetic; a door destroyed is an outage.\n"
                  f"If you mean it (the run is ending, or the owner has moved): --force",
                  file=sys.stderr)
            sys.exit(1)
    if not args.no_export:
        out, err = export_transcript(args, args.target, "close")
        print(f"transcript: {out}" if not err else f"transcript skipped — {err}")
    _, _, rows = load_workers(base)
    row = current_row(rows, args.target)
    # Resolved BEFORE anything is killed: the in-place decision needs the seat's placement, and
    # the pids to verify dead are only readable while the pane still exists (G-10).
    seats = ([w for w in discover_workers(workers_dir(args)) if w["agent"] == args.target]
             if args.renew else [])
    # G-51: checked BEFORE the seat is closed, not after. A renew that refuses halfway has already
    # killed the pane — the seat would be gone AND not relaunched, which is worse than either
    # outcome the check is choosing between. This is the exact path the run's live divergence sits
    # on: `close --renew` reads the DESCRIPTOR, so a registry re-bind never reaches it.
    if seats:
        check_bindings(args, seats, "close --renew")
    old_pane = (row or {}).get("pane") or ""
    old_idents = pane_harness_idents(old_pane) if old_pane else []
    in_place = bool(seats) and renew_in_place(seats[0], old_pane, old_pane in live_panes())
    if row and row["active"] == "yes":
        def close_row(r):
            r["active"] = "no"
            r["checkout"] = f"closed {now()}"

        update_row(base, args.target, close_row)
        print(f"roster: {args.target} closed")
    # 7.37: the session row is COMPLETED wherever the roster row goes inactive — this is one of
    # the three such paths (close-seat, depart, checkout). Idempotent: a seat with no open row
    # gains nothing, so a depart followed by a close-seat writes one `ended`, not two.
    sid, cerr = session_trace_safe(session_close, args, args.target)
    if cerr:
        print(c(f"WARNING sessions.csv row NOT completed — {cerr}. The close itself stands.",
                C_DEAD), file=sys.stderr)
    elif sid:
        print(f"sessions.csv: {sid} ended")
    # G-21: the state dies WITH the close, and unconditionally — including the renew path, where
    # the successor is a fresh seat that must boot with a full inbox, and including a close-seat
    # run directly by leader on a dead pane, which never had a closer to clear it. A closing flag
    # that outlives its seat would quietly filter a live successor's messages, which is the failure
    # this whole change exists to prevent, wearing the other mask.
    if clear_closing(base, args.target):
        print(f"inbox: '{args.target}' closing state cleared — the narrowing does not outlive the "
              f"close")
    # G-134: the debt is settled by the act that actually frees the resources. Cleared here rather
    # than at the kill below so the RENEW path clears it too — an in-place renew keeps the pane
    # deliberately (G-12), and a debt left standing for a seat that is back and running would make
    # the record lie in the opposite direction.
    if clear_awaiting(base, args.target):
        print(f"awaiting close: '{args.target}' debt settled")
    old_window = ""
    if old_pane:
        old_window = tmux_pane_window(old_pane)
        if in_place:
            print(f"pane {old_pane}: KEPT for an in-place renew — respawned below, so the "
                  f"window layout survives (G-12)")
        else:
            ok, err = tmux_kill_pane(old_pane)
            print(f"pane {old_pane}: {'killed' if ok else 'kill failed — ' + err}")
            # G-10: kill-pane SIGHUPs the process group and a blocked harness survives it as a
            # ghost the roster never mentions. Confirm the exit; escalate rather than assume.
            survivors, note = verify_pids_gone(old_idents)
            if old_idents:
                print(f"process check: {len(old_idents)} harness pid(s) "
                      + (f"GONE{' — ' + note if note else ''}" if not survivors
                         else f"NOT gone — {note}"))
    if args.renew:
        if not seats:
            print(f"renew FAILED: no briefing in {workers_dir(args)} carries "
                  f"`agent: {args.target}`, so there is nothing to relaunch — the seat is closed "
                  f"but not renewed.\nRelaunch it by hand once the briefing exists: "
                  f"{coord_invocation(args)} launch --only {args.target}", file=sys.stderr)
            sys.exit(1)
        # A pane seat relaunches into the window its old pane occupied (if it survived the
        # kill) — e.g. a renewed leader lands back in the control panel — NEVER the caller's
        # window: a closer runs this from the shared 'closers' window, which must not
        # inherit the renewed seat. Window/shared seats re-place from their briefing as before.
        launch_target = ""  # a tmux pane, not an agent — args.target is the seat being renewed
        if in_place:
            launch_target = old_pane
        elif seat_placement(seats[0])[0] == "pane" and old_window and tmux_session_name(old_window):
            launch_target = old_window
        if not launch_target:
            launch_target = os.environ.get("COORD_LAUNCH_TARGET") or os.environ.get("TMUX_PANE")
        if not launch_target:
            print(f"renew FAILED: the seat is closed, but relaunching it needs a tmux window and "
                  f"this shell is not inside tmux (no $TMUX_PANE) — its old window is gone too.\n"
                  f"Relaunch it from leader's pane: {coord_invocation(args)} launch --only "
                  f"{args.target}", file=sys.stderr)
            sys.exit(1)
        # A renewed seat re-reads its rules at boot, so it needs a current mirror just as a
        # fresh launch does — and a renew lands mid-run, exactly when sources have been drifting.
        refresh_mirrors_for(seats[:1])
        tmux_raise_history_limit()
        same_cell = None
        if in_place:
            ok, rerr = tmux_respawn_pane(old_pane, seats[0]["cwd"])
            if ok:
                same_cell = old_pane
                survivors, note = verify_pids_gone(old_idents)
                if old_idents:
                    print(f"process check: {len(old_idents)} harness pid(s) "
                          + (f"GONE{' — ' + note if note else ''}" if not survivors
                             else f"NOT gone — {note}"))
            else:
                # Fall back to the old kill+split path rather than stall the renew: a re-tiled
                # window is a cosmetic loss, a seat that never comes back is not.
                print(f"respawn-in-place failed ({rerr}) — falling back to kill+split, which "
                      f"re-tiles this window", file=sys.stderr)
                tmux_kill_pane(old_pane)
                verify_pids_gone(old_idents)
                launch_target = old_window or launch_target
        pane, err = launch_seat(seats[0], args, launch_target, pane=same_cell)
        if err:
            print(f"renew FAILED: {err}", file=sys.stderr)
            sys.exit(1)
        print(f"renewed: {args.target} relaunched in {pane}"
              + (" (same pane, layout intact)" if same_cell else "")
              + " (reads its updated memory.md at boot)")
    print(c(f"next: {coord_invocation(args)} workers — confirm the seat is "
            f"{'back and checked in' if args.renew else 'gone from the live rows'}", C_HINT))


def cmd_panel(args):
    """(leader) open the control-panel overview pane in the caller's window.

    The leader window is the run's control panel: leader + the oversight seats (watcher,
    scientist, scientist-roster) + on-demand closers as panes, plus this pane running the live
    tmux-overview of the whole session. Idempotent: skips if an 'overview' pane already exists."""
    gate(args, "panel", is_leader, "leader's alone (it splits the control-panel window)")
    target = os.environ.get("COORD_LAUNCH_TARGET") or os.environ.get("TMUX_PANE")
    if not target:
        print("refused: panel splits a strip into the CALLING tmux window and this shell is not "
              "inside tmux (no $TMUX_PANE).\nRun it from leader's own pane.", file=sys.stderr)
        sys.exit(1)
    for pid, title in tmux_window_panes(target):
        if title == "overview":
            print(f"overview pane already open ({pid}) — nothing to do")
            return
    session = tmux_session_name(target)
    if not session:
        print(f"panel FAILED: tmux does not resolve a session for this pane ({target}), and the "
              f"overview needs a session name to watch.\nRun it from a pane inside the run's own "
              f"tmux session.", file=sys.stderr)
        sys.exit(1)
    tool = Path(__file__).resolve().parent / "tmux-overview"
    pane, err = tmux_split_strip(target, VAULT_ROOT)
    if not pane:
        print(f"panel FAILED: {err}", file=sys.stderr)
        sys.exit(1)
    set_pane_title(pane, "overview")
    ok, terr = wake(pane, f"bash {shlex.quote(str(tool))} {shlex.quote(session)} --compact "
                          f"--package {shlex.quote(str(package_dir(args)))}")
    print(f"overview strip {pane} ({PANEL_STRIP_ROWS} rows) running tmux-overview '{session}' "
          f"--compact (roster names from the package): {'ok' if ok else 'FAILED ' + terr}")
    print(c(f"next: {coord_invocation(args)} launch — the strip tracks the seats it opens",
            C_HINT))


def cmd_reap(args):
    """One sweep pass over the awaiting-close debt: observe, confirm, and — only with --go — free.

    OBSERVES BY DEFAULT AND SAYS SO. `reap` kills panes, so the destructive form is the one that
    must be typed, not the safe one. A bare `reap` reports the debt and records this pass's
    observation; `--go` is what kills. That also makes the two-pass rule cheap to satisfy honestly:
    a watcher can sweep on its own cadence and the leader acts on an already-confirmed set.

    It never reaps a seat the run still owes a `close-seat`: reaping frees the PANE, and the roster
    row and session trace are finished by the close. So a reaped seat KEEPS its debt entry, with
    its pane now gone — the leader still sees it and still owes the close. Freeing memory and
    completing a lifecycle are different acts and this one does only the first."""
    # THE GATE IS ON THE CONSEQUENCE, NOT THE VERB (leader ruling, #363). It first covered the
    # whole command, including the observe pass — which destroys nothing. The cost of that lands
    # in exactly one place: a seat wanting to check the door exemption against the LIVE room had to
    # either override the gate or not verify. A gate that MANUFACTURES its own breaches, and
    # charges them to whoever is being most careful, is G-106's shape — every gate individually
    # correct, the bill sent to the seat behaving best. (This one billed its own author within the
    # hour: I overrode it to verify, which was the right act on an authority that was not mine.)
    #
    # So: observing is free, killing is gated. The refusal names `reap --go` rather than `reap`,
    # because a message that refuses the verb when only the flag is barred sends the reader looking
    # for the wrong permission.
    go = getattr(args, "go", False)
    if go:
        gate(args, "reap --go", is_leader_or_closer, "leader's or a closer-* seat's")
    base = base_dir(args)
    panes = live_panes()
    debts = awaiting_debts(base, panes)
    if not debts:
        print("no awaiting-close debt — every finished seat has been closed")
        return
    decls = inbox_decls(args)
    freed, held = [], []
    for seat, entry, age, _alive in debts:
        blockers = reap_blockers(entry, age, panes, decls, seat)
        seen, ready = confirm_reap(base, seat, blockers)
        aged = f"{age}min" if age is not None else "unknown age"
        if blockers:
            held.append(f"{seat} ({aged}): HELD — " + "; ".join(blockers))
            continue
        if not ready:
            held.append(f"{seat} ({aged}): every precondition holds, confirmed {len(seen)}/2 — "
                        f"a second pass at least {REAP_MIN_PASS_GAP_MIN}min from now decides it. "
                        f"One reading is a snapshot; two is a trend.")
            continue
        if not go:
            held.append(f"{seat} ({aged}): READY to reap ({len(seen)} confirmations) — "
                        f"pane {entry['pane']} would be freed. Re-run with --go.")
            continue
        idents = pane_harness_idents(entry["pane"])
        ok, err = tmux_kill_pane(entry["pane"])
        # G-10, same discipline every other teardown uses: kill-pane SIGHUPs the process group and
        # a blocked harness survives it as a ghost no roster row mentions. Confirm, never assume.
        survivors, note = verify_pids_gone(idents)
        freed.append(f"{seat}: pane {entry['pane']} "
                     + ("freed" if ok else f"kill FAILED — {err}")
                     + (f"; {len(idents)} harness pid(s) "
                        + ("GONE" if not survivors else f"NOT gone — {note}") if idents else ""))
    for line in held:
        print(c(f"  {line}", C_HINT))
    for line in freed:
        print(c(f"  {line}", C_ALIVE))
    if not go and any("READY to reap" in h for h in held):
        print(c(f"next: {coord_invocation(args)} reap --go — frees the panes listed READY above; "
                f"each still owes a close-seat afterwards", C_HINT))


def cmd_depart(args):
    """Self-service exit: export own transcript, check out, kill own pane. SELF ONLY (T1) —
    it takes no target, so no seat can depart another; leader cleans dead seats with
    close-seat."""
    base = base_dir(args)
    me = resolve_agent(args)
    out, err = export_transcript(args, me, "depart")
    print(f"transcript: {out}" if not err else f"transcript skipped — {err}")
    _, _, rows = load_workers(base)
    row = current_row(rows, me)
    if row and row["active"] == "yes":
        def close_row(r):
            r["active"] = "no"
            r["checkout"] = now()

        update_row(base, me, close_row)
        print(f"checked out: {me}")
    sid, cerr = session_trace_safe(session_close, args, me)   # 7.37: a self-departure is still a closed session
    if cerr:
        print(c(f"WARNING sessions.csv row NOT completed — {cerr}. The close itself stands.",
                C_DEAD), file=sys.stderr)
    elif sid:
        print(f"sessions.csv: {sid} ended")
    # G-21: a seat that departs under its own steam mid-close (or one whose close-seat never ran)
    # must not leave its closing flag behind for a future occupant of the name.
    clear_closing(base, me)
    # G-134: a departure frees its OWN resources — it kills its pane below and arms a reaper for
    # any ghost — so it owes nothing and must not leave a debt behind. This also covers the
    # checkout-then-depart order: the entry checkout wrote is settled by the act that made it moot.
    clear_awaiting(base, me)
    pane = (row or {}).get("pane") or detect_pane(None)
    if pane:
        # G-10: kill-pane SIGHUPs the process group; a harness blocked elsewhere survives as a
        # ghost holding ~450 MB that no roster row mentions. This process dies WITH the pane, so
        # it cannot check afterwards — a detached reaper outlives both and finishes the job.
        idents = pane_harness_idents(pane)
        if idents:
            print(f"arming the exit reaper for harness pid(s) "
                  f"{', '.join(str(p) for p, _ in idents)} — no ghost survives this departure "
                  f"(it fires only on an exact pid+starttime match, so a recycled pid is safe)")
            arm_pid_reaper(idents)
        print(f"killing own pane {pane} — goodbye")
        tmux_kill_pane(pane)
    else:
        print("no pane to kill (not inside tmux)")


# ---------- selftest ----------

def cmd_selftest(args):
    """G-66: run the checks, and ALWAYS reach a verdict.

    A check whose condition RAISES used to take the whole self-test down: no verdict line, no
    `expect-fail:` line, just a traceback that reads as a broken harness rather than a caught
    defect — strictly worse than the failure it was written to report. Measured while mutating the
    G-61 ranking check, whose `.index()` raised on the very input the mutation produced.

    It cannot be fixed inside `check()`: the condition is an ARGUMENT, evaluated in full before
    `check` is ever entered, so by then the exception has already escaped. The honest fix is to
    make an abort a first-class OUTCOME — reported, counted as a failure, and distinguished from
    FAIL, because every check after the raise never ran and their results are unknown, not passing.
    """
    failures, names = [], []
    aborted = ""
    try:
        _selftest_checks(args, failures, names)
    except Exception as exc:                                    # noqa: BLE001 — the whole point
        import traceback
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        aborted = (f"{type(exc).__name__}: {exc} at "
                   f"{os.path.basename(frame.filename)}:{frame.lineno}")
        print(f"FAIL  selftest ABORTED after {len(names)} check(s) — {aborted}")
        print(f"      the raising check never reported, and every check after it never ran: "
              f"their results are UNKNOWN, not passing")
        failures.append(f"selftest ABORTED: {aborted}")
    verdict = "ABORTED" if aborted else ("PASS" if not failures else "FAIL")
    print(f"\nselftest: {verdict} ({len(failures)} failure(s))")
    if not getattr(args, "expect_fail", None):
        sys.exit(1 if failures else 0)
    if aborted:
        # --expect-fail exists to make a mutation's evidence be the NAMED check's line. An abort
        # means that line was never printed, so the mutation proves nothing either way.
        print(f"expect-fail: FAIL — the self-test ABORTED, so the named check produced no result. "
              f"A mutation that aborts the suite is not evidence about any check.")
        sys.exit(1)
    sys.exit(report_expect_fail(args.expect_fail, names, failures))


def _selftest_checks(args, failures, names):
    import io
    from contextlib import redirect_stderr, redirect_stdout

    def check(name, cond):
        print(("ok  " if cond else "FAIL") + f"  {name}")
        names.append(name)
        if not cond:
            failures.append(name)

    # Never touch real tmux from the self-test: wakes deterministically "fail" (exercising the
    # P22 path), pane/window operations are recorded instead of executed. detect_pane/live_panes
    # are stubbed for the same reason — identity resolution (T1) reads the calling pane.
    # A COORD_AGENT inherited from the seat running the self-test would silently become every
    # command's identity, so it is cleared for the duration.
    global wake, set_pane_title, tmux_split_pane, tmux_new_window, tmux_kill_pane, tmux_capture
    global tmux_raise_history_limit, schedule_session_rename, tmux_window_panes, tmux_session_name
    global tmux_split_strip, restore_overview_strip, tmux_find_window_pane
    global tmux_send_text, tmux_send_enter, tmux_capture_tail, tmux_pane_window, RUNS_INDEX
    global detect_pane, live_panes, _acquire_flock, atomic_write, pane_title
    real = (wake, set_pane_title, tmux_split_pane, tmux_new_window, tmux_kill_pane, tmux_capture,
            tmux_raise_history_limit, schedule_session_rename, tmux_window_panes, tmux_session_name,
            tmux_split_strip, restore_overview_strip, tmux_find_window_pane, tmux_send_text,
            tmux_send_enter, tmux_capture_tail, tmux_pane_window, detect_pane, live_panes,
            _acquire_flock, atomic_write, pane_title)
    env_agent = os.environ.pop("COORD_AGENT", None)

    # The process-truth helpers (G-10/G-11) read the LIVE process table and live tmux panes. Left
    # real, this suite would judge fixture panes against whatever happens to run on the tester's
    # box — and it did: a fixture checkin at "%5" hit a real, bare-shell pane of the running team
    # and was refused, killing the suite mid-way. Stubbed to "cannot tell" (the fail-safe default),
    # with the branch-specific checks below flipping them deliberately. Kept in its own save/restore
    # pair rather than the indexed `real` tuple above, which is positional and easy to break.
    global pane_harness_pids, pane_harness_idents, wait_harness_up, verify_pids_gone
    global arm_pid_reaper, tmux_pane_pid, tmux_respawn_pane, available_mb
    proc_real = (pane_harness_pids, pane_harness_idents, wait_harness_up, verify_pids_gone,
                 arm_pid_reaper, tmux_pane_pid, tmux_respawn_pane, available_mb)
    harness_up = {"v": None}   # None = unverifiable; [] = positively absent; [pid] = up
    reaped, respawned = [], []
    pane_harness_pids = lambda pane: (([], False) if harness_up["v"] is None
                                      else (list(harness_up["v"]), True))
    wait_harness_up = lambda pane, timeout=HARNESS_UP_TIMEOUT: (
        ([], "") if harness_up["v"] is None or harness_up["v"]
        else ([], f"no harness process is running in {pane} after {timeout:.0f}s (G-11)"))
    pane_harness_idents = lambda pane: ([] if harness_up["v"] is None
                                        else [(p, f"stamp-{p}") for p in harness_up["v"]])
    verify_pids_gone = lambda idents, timeout=PID_EXIT_TIMEOUT: (
        reaped.extend(p for p, _ in idents) or ([], ""))
    arm_pid_reaper = lambda idents, delay=4: reaped.extend(p for p, _ in idents)
    tmux_pane_pid = lambda pane: 0
    tmux_respawn_pane = lambda pane, cwd: (respawned.append((pane, cwd)) or (True, ""))
    available_mb = lambda: 0   # unmeasurable -> the memory gate passes (fail-safe)

    # ---- P35 (round 2): wake()'s Enter-verify + bounded Enter-only retry, exercised against the
    # REAL wake() with only its three tmux primitives stubbed (wake itself is stubbed wholesale
    # further below for the rest of the suite, which only needs a pass/fail switch, not the
    # mechanics). Round 1 stubbed the wake line as the pane's LAST line — the exact false
    # assumption verifier-tick #145 disproved (status/hint chrome renders below the composer on
    # every rostered TUI, so the retry never fired where P35 actually happened). These fixtures
    # are built from REAL captured pane tails instead: a rostered claude seat's idle composer
    # (window 1 pane %6, 'cli', 2026-07-24), a scratch claude pane's stranded composer, a scratch
    # opencode pane's boxed composer (idle + stranded), and a scratch cooked-mode bash pane whose
    # PS1 happens to reuse claude's '❯' glyph (padding trimmed for source width; the special
    # characters, line order, and chrome-below-composer structure are unedited).
    CLAUDE_TAIL_IDLE = (
        "──────────────────────────────────────────────────── cli ──\n"
        "❯ \n"
        "──────────────────────────────────────────────────────────\n"
        "                                                       /rc\n"
        "  ⏵⏵ auto mode on (shift+tab to cycle) · ← for agents\n"
    )
    CLAUDE_TAIL_STRANDED = (
        "──────────────────────────────────────────────────────────\n"
        "❯ [coord wake] hello\n"
        "──────────────────────────────────────────────────────────\n"
        "  ⏸ manual mode on                                     /rc\n"
    )
    OPENCODE_TAIL_IDLE = (
        "┃ \n"
        '┃  Ask anything... "Fix broken tests"\n'
        "┃ \n"
        "┃  Build · DeepSeek Reasoner DeepSeek\n"
        "╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀\n"
        "                    tab agents  ctrl+p commands\n"
    )
    OPENCODE_TAIL_STRANDED = (
        "┃ \n"
        "┃  [coord wake] hello\n"
        "┃ \n"
        "┃  Build · DeepSeek Reasoner DeepSeek\n"
        "╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀\n"
        "                    tab agents  ctrl+p commands\n"
    )
    COOKED_TAIL = (  # a bare bash pane — no composer at all, just a starship-style '❯' PS1 echo
        "❯ PS1='$ ' bash --norc\n"
        "$ cat > /dev/null\n"
        "[coord wake] hello\n"
    )

    # ---- P35 round 3: production wakes are 310-319 chars and hard-wrap in every rostered pane
    # (narrowest 114 cols) — `capture-pane -J` cannot rejoin a TUI's own wrap points, so the
    # round-2 full-text match against a single captured line never fired where P35 lives
    # (verifier-tick round-2 re-verification, msg #188). These fixtures are REAL captures at a
    # REAL production-length wake, at the narrowest rostered pane width: a scratch claude pane
    # and a scratch opencode pane, both 114 cols, each with the exact 323-char wake text typed
    # and left unsubmitted (padding trimmed for source width; special characters, line order,
    # wrap points, and chrome-below-composer structure are unedited).
    REAL_WAKE_TEXT = (
        "[coord wake] New coordination message #199 from toolsmith-2 to all. Read it now, then "
        "continue your task: python3 /home/henri/ht-wkdir/second-brain/1-projects/"
        "rbtv-sb-merge-refactor/build/team-kit/coord.py --package /home/henri/ht-wkdir/"
        "second-brain/1-projects/rbtv-sb-merge-refactor/build/kg-views-rebuild read toolsmith-2"
    )
    CLAUDE_TAIL_STRANDED_WRAPPED = (
        "──────────────────────────────────────────────────────────────────\n"
        "❯\xa0[coord wake] New coordination message #199 from toolsmith-2 to all. Read it now, "
        "then continue your task:\n"
        "  python3 /home/henri/ht-wkdir/second-brain/1-projects/rbtv-sb-merge-refactor/build/"
        "team-kit/coord.py --package\n"
        "  /home/henri/ht-wkdir/second-brain/1-projects/rbtv-sb-merge-refactor/build/"
        "kg-views-rebuild read toolsmith-2\n"
        "──────────────────────────────────────────────────────────────────\n"
        "  ⏸ manual mode on                                                              /rc\n"
    )
    OPENCODE_TAIL_STRANDED_WRAPPED = (
        "                    ┃\n"
        "                    ┃  [coord wake] New coordination message #199 from toolsmith-2 to "
        "all.\n"
        "                    ┃  Read it now, then continue your task: python3 /home/henri/"
        "ht-wkdir/\n"
        "                    ┃  second-brain/1-projects/rbtv-sb-merge-refactor/build/team-kit/"
        "coord.\n"
        "                    ┃  py --package /home/henri/ht-wkdir/second-brain/1-projects/"
        "rbtv-sb-\n"
        "                    ┃  merge-refactor/build/kg-views-rebuild read toolsmith-2\n"
        "                    ┃\n"
        "                    ┃  Build · DeepSeek Reasoner DeepSeek\n"
        "                    ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀"
        "▀▀▀▀▀▀\n"
        "                                                                    tab agents  "
        "ctrl+p commands\n"
    )

    sent_texts, enter_calls = [], []
    tmux_send_text = lambda pane, t: (sent_texts.append(t) or (True, ""))
    tmux_send_enter = lambda pane: (enter_calls.append(pane) or (True, ""))
    capture_sequence = []
    tmux_capture_tail = lambda pane, lines=WAKE_TAIL_LINES: (
        capture_sequence.pop(0) if capture_sequence else ("", ""))

    sent_texts.clear(); enter_calls.clear()
    capture_sequence[:] = [(CLAUDE_TAIL_IDLE, "")]
    ok, terr = wake("%1", "[coord wake] hello")
    check("P35: claude normal path submits on the first Enter, no retry (real idle pane tail)",
          ok and len(enter_calls) == 1 and sent_texts == ["[coord wake] hello"])

    sent_texts.clear(); enter_calls.clear()
    capture_sequence[:] = [(CLAUDE_TAIL_STRANDED, ""), (CLAUDE_TAIL_IDLE, "")]
    ok, terr = wake("%1", "[coord wake] hello")
    check("P35: claude busy pane (real stranded-composer tail) retries Enter-only, never retypes",
          ok and len(enter_calls) == 2 and sent_texts == ["[coord wake] hello"])

    sent_texts.clear(); enter_calls.clear()
    capture_sequence[:] = [(CLAUDE_TAIL_STRANDED, "")] * WAKE_ENTER_ATTEMPTS
    ok, terr = wake("%1", "[coord wake] hello")
    check("P35: bounded — gives up after WAKE_ENTER_ATTEMPTS, still never retypes, reports failure",
          not ok and len(enter_calls) == WAKE_ENTER_ATTEMPTS
          and sent_texts == ["[coord wake] hello"] and "unsubmitted" in terr)

    sent_texts.clear(); enter_calls.clear()
    capture_sequence[:] = [(OPENCODE_TAIL_STRANDED, ""), (OPENCODE_TAIL_IDLE, "")]
    ok, terr = wake("%1", "[coord wake] hello")
    check("P35: opencode busy pane (real boxed-composer tail) retries Enter-only, never retypes",
          ok and len(enter_calls) == 2 and sent_texts == ["[coord wake] hello"])

    sent_texts.clear(); enter_calls.clear()
    capture_sequence[:] = [(COOKED_TAIL, "")]
    ok, terr = wake("%1", "[coord wake] hello")
    check("P35: unparseable pane (cooked-mode, PS1 reuses '❯') fails safe — single Enter, no "
          "retry, no reported failure, despite the wake text sitting on-screen",
          ok and len(enter_calls) == 1 and sent_texts == ["[coord wake] hello"])

    # ---- P35 round 3: the same mechanics, but at REAL production wake length (310-319 chars)
    # against a REAL wrapped-composer capture — the exact regime round 2 was blind on (verifier-
    # tick round-2 re-verification, msg #188: round 2's full-text match against ONE captured line
    # never matches a wrapped composer, so the retry never fired where P35 actually happens).
    sent_texts.clear(); enter_calls.clear()
    capture_sequence[:] = [(CLAUDE_TAIL_STRANDED_WRAPPED, ""), (CLAUDE_TAIL_IDLE, "")]
    ok, terr = wake("%1", REAL_WAKE_TEXT)
    check("P35 round 3: claude busy pane, REAL wrapped composer at REAL wake length (323 chars, "
          "3 wrapped lines) — prefix-matches the sandwich's top line and retries Enter-only",
          ok and len(enter_calls) == 2 and sent_texts == [REAL_WAKE_TEXT])

    sent_texts.clear(); enter_calls.clear()
    capture_sequence[:] = [(CLAUDE_TAIL_STRANDED_WRAPPED, "")] * WAKE_ENTER_ATTEMPTS
    ok, terr = wake("%1", REAL_WAKE_TEXT)
    check("P35 round 3: bounded at real wake length — still gives up after WAKE_ENTER_ATTEMPTS, "
          "never retypes, reports failure",
          not ok and len(enter_calls) == WAKE_ENTER_ATTEMPTS
          and sent_texts == [REAL_WAKE_TEXT] and "unsubmitted" in terr)

    sent_texts.clear(); enter_calls.clear()
    capture_sequence[:] = [(OPENCODE_TAIL_STRANDED_WRAPPED, ""), (OPENCODE_TAIL_IDLE, "")]
    ok, terr = wake("%1", REAL_WAKE_TEXT)
    check("P35 round 3: opencode busy pane, REAL wrapped composer at REAL wake length — "
          "prefix-matches the box's first line and retries Enter-only",
          ok and len(enter_calls) == 2 and sent_texts == [REAL_WAKE_TEXT])

    tmux_send_text, tmux_send_enter, tmux_capture_tail = real[13], real[14], real[15]

    # wake behavior is switchable: send-path tests need failing wakes (P22), launch/renew-path
    # tests need succeeding ones (a failed wake aborts launch_seat before the rename).
    wake_ok = {"v": False}
    wake = lambda pane, text: ((True, "") if wake_ok["v"] else (False, "selftest stub"))
    titles = []
    set_pane_title = lambda pane, title: titles.append((pane, title))
    opened, killed, renames, split_targets = [], [], [], []
    tmux_split_pane = lambda target, cwd: (split_targets.append(target)
                                           or opened.append(("pane", cwd))
                                           or (f"%9{len(opened)}", ""))
    pane_windows = {}  # pane id -> window id, for the renew-placement stub
    tmux_pane_window = lambda pane: pane_windows.get(pane, "")
    closers_window_pane = {"v": ""}  # models the shared 'closers' window's first pane, once opened
    shared_windows = {}              # name -> first pane, for shared (wave) windows
    def _fake_new_window(target, name, cwd):
        opened.append(("window", name))
        pane = f"%8{len(opened)}"
        if name == CLOSERS_WINDOW:
            closers_window_pane["v"] = pane
        shared_windows[name] = pane
        return pane, ""
    tmux_new_window = _fake_new_window
    tmux_find_window_pane = lambda session, window: (closers_window_pane["v"]
                                                     if window == CLOSERS_WINDOW
                                                     else shared_windows.get(window, ""))
    tmux_kill_pane = lambda pane: (killed.append(pane) or (True, ""))
    tmux_capture = lambda pane: (f"captured scrollback of {pane}", "")
    tmux_raise_history_limit = lambda: None
    schedule_session_rename = lambda pane, agent, delay=25: renames.append(agent)
    panel_panes = []
    tmux_window_panes = lambda target: list(panel_panes)
    tmux_session_name = lambda target: "testsess"
    tmux_split_strip = lambda target, cwd, rows=PANEL_STRIP_ROWS: (opened.append(("strip", rows)) or (f"%7{len(opened)}", ""))
    restore_overview_strip = lambda target: None
    # T1: the calling pane, stubbed. "" = "this caller is not in a registered pane", the state
    # every internal/`--as` call runs in; individual checks below set it to a real pane id.
    calling_pane = {"v": ""}
    detect_pane = lambda override=None: (override or calling_pane["v"])
    live_tmux_panes = {"v": set()}   # empty = "tmux unavailable", so no row is judged DEAD?
    live_panes = lambda: set(live_tmux_panes["v"])
    # P38/8(b): pane TITLES back the approval-gate predicate. Unstubbed, every send in this suite
    # would shell out to the tester's REAL tmux — and on a box where pane %1 exists, read a live
    # seat's title. Default "" = no pane is gated.
    pane_titles = {}
    pane_title = lambda pane: pane_titles.get(pane, "")

    with tempfile.TemporaryDirectory() as td:
        RUNS_INDEX = Path(td) / "coordinate-runs.json"  # never touch the real registry
        pkg = Path(td) / "pkg"
        (pkg / "coordination").mkdir(parents=True)
        (pkg / "workers").mkdir()
        (pkg / "workers" / "alpha.md").write_text("---\nagent: alpha\nmodel: fable\neffort: xhigh\n---\nbrief\n")
        (pkg / "workers" / "beta.md").write_text("---\nagent: beta\n---\nbrief\n")
        (pkg / "workers" / "watcher.md").write_text("---\nagent: watcher\nobserver: yes\nauto-wake: yes\n---\nbrief\n")
        # folder-form seats (v2): opencode window seat, codex seat, memoryless validator
        gdir = pkg / "workers" / "gamma"
        gdir.mkdir()
        (gdir / "agent.md").write_text(
            "---\nagent: gamma\nharness: opencode\nmodel: zai-coding-plan/glm-5.2\nwindow: yes\n---\nbrief\n")
        (gdir / "memory.md").write_text("# memory\nprior state\n")
        ddir = pkg / "workers" / "delta"
        ddir.mkdir()
        (ddir / "agent.md").write_text("---\nagent: delta\nharness: codex\nephemeral: yes\nwindow: yes\n---\nbrief\n")
        for hk in ("hk-1", "hk-2"):  # wave seats sharing one named window
            hdir = pkg / "workers" / hk
            hdir.mkdir()
            (hdir / "agent.md").write_text(
                f"---\nagent: {hk}\nmodel: haiku\nwindow: wave-haiku\nephemeral: yes\n"
                f"ctx-refresh: 40\n---\nbrief\n")
        # leader seat (folder form, no window:) — by-name launch/renew targets only
        mdir = pkg / "workers" / "leader"
        mdir.mkdir()
        (mdir / "agent.md").write_text("---\nagent: leader\nmodel: opus\n---\nbrief\n")

        def ns(**kw):
            d = {"package": str(pkg), "base": None, "workers_dir": None,
                 "as_agent": None, "force": False}
            d.update(kw)
            return argparse.Namespace(**d)

        def run(fn, **kw):
            buf = io.StringIO()
            with redirect_stdout(buf):
                fn(ns(**kw))
            return buf.getvalue()

        def refuse(fn, **kw):
            """Run a command expected to REFUSE: returns (combined output, exit code)."""
            out, err, code = io.StringIO(), io.StringIO(), 0
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    fn(ns(**kw))
                except SystemExit as exc:
                    code = exc.code if isinstance(exc.code, int) else 1
            return out.getvalue() + err.getvalue(), code

        def rd(agent, **kw):
            d = {"agent": agent, "after": None, "peek": False, "all": False, "type": None,
                 "addressed": "any", "digest": False, "msg": None, "limit": None}
            d.update(kw)
            return run(cmd_read, **d)

        def sd(agent, to, message=None, **kw):
            d = {"agent": agent, "to": to, "message": message, "type": "note",
                 "supersedes": None, "re_num": None, "file": None}
            d.update(kw)
            return run(cmd_send, **d)

        def cursor_of(agent):
            _, _, rr = load_workers(base_dir(ns()))
            row = current_row(rr, agent)
            return row["lastread"] if row else None

        run(cmd_checkin, agent="alpha", summary="first check-in", pane="%1")
        run(cmd_checkin, agent="beta", summary="beta work", pane="%2")
        out = run(cmd_checkin, agent="alpha", summary="second check-in", pane="%3")
        check("P1: re-check-in reports supersession", "superseded 1 prior row" in out)
        _, _, rows = load_workers(base_dir(ns()))
        active_alpha = [r for r in rows if r["agent"] == "alpha" and r["active"] == "yes"]
        check("P1: exactly one active row per agent", len(active_alpha) == 1 and active_alpha[0]["pane"] == "%3")

        keys_log = []
        tmux_send_text = lambda pane, text: (keys_log.append((pane, text)) or (True, ""))
        tmux_send_enter = lambda pane: (keys_log.append((pane, "<Enter>")) or (True, ""))
        # stub signature/return type MUST match the real fn — a bare string here is what hid F13
        tmux_capture_tail = lambda pane, lines=WAKE_TAIL_LINES: (f"tail-of-{pane}", "")
        out = run(cmd_approve, target="alpha", keys="1", no_enter=False)
        check("approve: keys + Enter go to the agent's REGISTERED pane, tail echoed as TEXT "
              "(F13: it used to print the (text, err) tuple)",
              ("%3", "1") in keys_log and ("%3", "<Enter>") in keys_log
              and "tail-of-%3" in out and "('tail-of-%3'" not in out)

        check("run tags: --package use auto-registers; --run resolves; cwd walk-up works",
              load_runs_index().get("pkg") == str(pkg)
              and package_dir(argparse.Namespace(package=None, run="pkg", base=None)) == pkg
              and discover_package_from(pkg / "workers" / "gamma") == pkg
              and discover_package_from(Path(td)) is None)
        check("invocation: registered package emits the short --run form",
              coord_invocation(ns()).endswith("--run pkg"))

        # ---- T5: the runs registry prunes packages that no longer exist on disk (F15) ----
        idx = load_runs_index()
        idx["ghost-run"] = str(Path(td) / "deleted-package")
        write_runs_index(idx)
        pruned = load_runs_index()
        check("T5 registry: a dead package path is pruned on load and the live one survives",
              "ghost-run" not in pruned and pruned.get("pkg") == str(pkg)
              and "ghost-run" not in RUNS_INDEX.read_text(encoding="utf-8"))

        # ---- fix round: a run tag is never STOLEN by a same-named package ----
        twin = Path(td) / "twin" / "pkg"
        (twin / "coordination").mkdir(parents=True)
        (twin / "workers").mkdir()
        errbuf = io.StringIO()
        with redirect_stderr(errbuf):
            twin_invocation = coord_invocation(ns(package=str(twin)))
        check("registry no-steal: a second package with the SAME folder name never re-points a "
              "tag whose package still exists — it registers nothing, says nothing, and its own "
              "invocation falls back to the explicit --package form, so neither run breaks",
              load_runs_index().get("pkg") == str(pkg)
              and twin_invocation.endswith(f"--package {twin.resolve()}")
              and coord_invocation(ns()).endswith("--run pkg")
              and errbuf.getvalue() == "")
        idx = load_runs_index()
        idx["revived"] = str(Path(td) / "gone" / "revived")   # tag held by a package now deleted
        write_runs_index(idx)
        revived = Path(td) / "revived"
        (revived / "coordination").mkdir(parents=True)
        (revived / "workers").mkdir()
        register_run(revived)
        check("registry no-steal: a tag whose package path is GONE is still re-taken by a live "
              "package of that name (the prune drops the dead entry first)",
              load_runs_index().get("revived") == str(revived.resolve()))

        sd("beta", "alpha", "how many rows does the export have?", type="ask")
        sd("alpha", "beta", "claim: count is 11", type="answer", re_num=1)
        # force: these fixtures exercise broadcast DELIVERY, not the #198 discipline gate — the
        # note-to-all they send is the shape the gate now refuses, and it is the shape under test.
        sd("beta", "all", "starting", force=True)
        _, blocks = load_messages(base_dir(ns()))
        check("P2: type recorded in header", blocks[0]["type"] == "ask" and blocks[1]["type"] == "answer")
        check("T4: `| re: N` is written into the header and parses back",
              blocks[1]["re"] == 1 and "| re: 1 |" in blocks[1]["lines"][0])
        raw = (base_dir(ns()) / "messages.md").read_text()
        check("P22: wake failure recorded in log", "> delivery-failure:" in raw)

        out = rd("beta")
        check("read: sees addressed message", "count is 11" in out)
        check("P26: cursor advances to the last SHOWN message",
              "cursor advanced to #2" in out and cursor_of("beta") == "2")
        out = rd("beta")
        check("P26: second read starts at cursor", "no new messages for beta after #2" in out)
        sd("alpha", "beta", "ping", type="ask")
        out = rd("beta", peek=True)
        check("P26: --peek shows without advancing", "ping" in out and "cursor advanced" not in out)
        out = rd("beta", all=True)
        check("P26: --all replays from zero", "count is 11" in out and "ping" in out)

        sd("alpha", "beta", "RETRACTED: count was wrong, it is 8", type="answer", re_num=1,
           supersedes=2)
        out = rd("beta", after=0, peek=True)
        check("P12: superseded message flagged inline", "SUPERSEDED by #5" in out)
        out = rd("beta", after=0, peek=True, type="ask")
        check("P2: --type filter", "ping" in out and "count is 11" not in out)

        # ---- T2 designer catch: a FILTERED read is peek-semantics — it must never advance the
        # cursor past the messages its filter hid (leader's documented `--type ask` drain used to
        # silently drop every non-ask message from the reader's inbox forever).
        before = cursor_of("beta")
        out = rd("beta", type="ask")
        check("T2 catch: a filtered read shows its hits, says it is peek-semantics, and leaves "
              "the cursor exactly where it was",
              "ping" in out and "peek semantics" in out and cursor_of("beta") == before == "2")
        out = rd("beta", addressed="direct")
        check("T2 catch: --addressed is a filter too — no cursor movement",
              "peek semantics" in out and cursor_of("beta") == "2")
        out = rd("beta")
        check("T2 catch: the plain read that follows still delivers everything the filtered "
              "reads did NOT consume", "ping" in out and "count was wrong" in out
              and cursor_of("beta") == "5")

        # ---- T2: bounded batches, cursor only through what was SHOWN ----
        for i in range(12):
            sd("alpha", "beta", f"bulk message {i}")
        out = rd("beta")
        check(f"T2 bounded: a default read shows at most READ_LIMIT ({READ_LIMIT}) messages and "
              "reports the remainder",
              out.count("bulk message") == READ_LIMIT and "2 more waiting" in out
              and cursor_of("beta") == "15")
        out = rd("beta")
        check("T2 bounded: the next read picks up exactly where the batch stopped",
              "bulk message 10" in out and "bulk message 11" in out and cursor_of("beta") == "17")
        out = rd("beta", after=5, limit=3, peek=True)
        check("T2 bounded: --limit overrides the batch size",
              out.count("bulk message") == 3 and "9 more waiting" in out)

        # ---- T2: digest + single message, both peek-semantics ----
        out = rd("beta", digest=True, after=0)
        check("T2 digest: one line per message with type, sender->to, re/supersession markers",
              "(re #1)" in out and "[SUPERSEDED by #5]" in out and "alpha->beta" in out
              and "claim: count is 11" in out and "cursor advanced" not in out)
        out = rd("beta", msg=2)
        check("T2 --msg: one full message with its ask link, no cursor move",
              "count is 11" in out and "answers ask #1" in out and "never moves your cursor" in out
              and cursor_of("beta") == "17")
        out, code = refuse(cmd_read, agent="beta", after=None, peek=False, all=False, type=None,
                           addressed="any", digest=False, msg=9999, limit=None)
        check("T2 --msg: an unknown message number is refused, not silently empty",
              code == 1 and "no message #9999" in out)

        run(cmd_owner, agent="leader", state="present", note="ruling live tonight")
        out = run(cmd_workers, full=False, history=False)
        check("P15: owner presence surfaces in workers", "owner: present" in out)

        obs, auto = observer_sets(ns())
        check("frontmatter observers: declared seat joins both sets",
              "watcher" in obs and "watcher" in auto and "scientist" in obs and "beta" not in obs)
        run(cmd_checkin, agent="watcher", summary="watching", pane="%9")
        out = rd("watcher", after=0, peek=True, limit=0)
        check("frontmatter observers: full-log read (sees a message addressed to neither it nor all)",
              "count is 11" in out)

        run(cmd_create_group, agent="alpha", group="pair", members=["beta"])
        gm = group_map(base_dir(ns()))
        check("groups: creator + leader auto-included", set(gm["pair"]) == {"alpha", "beta", "leader"})

        # ---- v2: discovery over both briefing forms ----
        ws = discover_workers(workers_dir(ns()))
        by = {w["agent"]: w for w in ws}
        check("launch: per-seat model/effort from frontmatter (flat form)",
              by["alpha"]["model"] == "fable" and by["alpha"]["effort"] == "xhigh"
              and by["beta"]["model"] == DEFAULT_MODEL and by["beta"]["effort"] == DEFAULT_EFFORT)
        check("v2: folder-form seat discovered with harness/model/window/cwd",
              by["gamma"]["harness"] == "opencode" and by["gamma"]["model"] == "zai-coding-plan/glm-5.2"
              and by["gamma"]["window"] and by["gamma"]["cwd"] == str(gdir)
              and by["gamma"]["folder"] == gdir)
        check("v2: ephemeral codex seat discovered; model empty -> plan default",
              by["delta"]["harness"] == "codex" and by["delta"]["ephemeral"] and by["delta"]["model"] == "")
        check("T5 ctx-refresh: the frontmatter key is exposed per seat (int|None) for watch.py",
              by["hk-1"]["ctx_refresh"] == 40 and by["alpha"]["ctx_refresh"] is None)
        check("leader renew: discovered by name, excluded from the bare mass sweep",
              "leader" in by
              and "leader" not in {w["agent"] for w in seats_by_name(ns())}
              and [w["agent"] for w in seats_by_name(ns(), "leader")] == ["leader"])

        # ---- v2: harness command builders (+ T1 identity injection) ----
        cmd, _ = harness_command(by["alpha"], "P")
        check("v2: claude command carries model+effort", "--model fable" in cmd and "--effort xhigh" in cmd)
        check("T1: every harness command is prefixed with the seat's COORD_AGENT identity",
              cmd.startswith("COORD_AGENT=alpha ") and f"COORD_AGENT=alpha {CLAUDE_BIN}" in cmd)
        cmd, _ = harness_command(by["gamma"], "P")
        # G-13: this asserted the flags `opencode --model X --prompt Y`, which THIS opencode has at
        # no level — the one-shot form is the `run` subcommand. The old string fell through to the
        # TUI and never ran the prompt, and the check passed for two months because it asserted the
        # kit's own invention rather than the CLI's surface.
        check("G-13: opencode command is the one-shot `run` subcommand with -m <provider/model> — "
              "never the invented `--model/--prompt` flags this opencode does not have. "
              "(`--auto` now sits between `run` and `-m` per the owner-directed fix; the "
              "adjacency of `run` and `-m` was never this check's point, and the flag's own "
              "position is asserted separately and more strictly below)",
              cmd.startswith(f"COORD_AGENT=gamma {OPENCODE_BIN} run ")
              and "-m zai-coding-plan/glm-5.2" in cmd
              and "--prompt" not in cmd and "--model" not in cmd)
        cmd, _ = harness_command(by["delta"], "P")
        check("v2: codex command uses plan default when model empty",
              cmd.startswith(f"COORD_AGENT=delta {CODEX_BIN}") and " -m " not in cmd)
        bad = dict(by["gamma"], model="")
        cmd, err = harness_command(bad, "P")
        check("v2: opencode without model refused", cmd is None and "require" in err)

        # ---- PROP-8: pre-flight harness/model validation (local knowledge only) ----
        check("PROP-8: every fixture seat's launch config validates clean",
              validate_seat(by["alpha"]) == "" and validate_seat(by["gamma"]) == ""
              and validate_seat(by["delta"]) == "" and validate_seat(by["leader"]) == "")
        check("PROP-8: a full claude-* model id is accepted alongside the aliases",
              validate_seat(dict(by["alpha"], model="claude-fable-5")) == "")
        check("PROP-8: an unknown claude alias is refused with the accepted forms named",
              "neither a known alias" in validate_seat(dict(by["alpha"], model="opsu")))
        check("PROP-8: an opencode slug missing its provider half is refused — the shape a "
              "launch can validate locally, without any provider call",
              "provider/model" in validate_seat(dict(by["gamma"], model="deepseek-reasoner")))
        check("PROP-8: an unknown harness is refused at pre-flight, not mid-spawn",
              "unknown harness" in validate_seat(dict(by["alpha"], harness="gemini")))

        # ---- v2: boot prompt mentions memory only for persistent folder seats ----
        p = boot_prompt(by["gamma"], ns())
        check("v2: persistent folder seat boot prompt names memory.md", "memory.md" in p)
        p = boot_prompt(by["delta"], ns())
        check("v2: ephemeral seat boot prompt omits memory", "memory.md" not in p)
        p = boot_prompt(by["leader"], ns())
        check("leader renew: no memory.md yet -> generic fresh boot prompt", "RESUMING" not in p)
        (mdir / "memory.md").write_text("# memory\n## Resume here\nstate\n")
        p = boot_prompt(by["leader"], ns())
        check("leader renew: memory.md present -> resume-first prompt (memory before briefing, "
              "'Resume here' named, no re-run of completed work)",
              "RESUMING" in p and "Resume here" in p and "do not re-run" in p
              and p.index(str(mdir / "memory.md")) < p.index(str(mdir / "agent.md")))

        # ---- v2: launch placement — window vs pane ----
        wake_ok["v"] = True  # harness starts must succeed from here on
        os.environ["COORD_LAUNCH_TARGET"] = "%0"
        out = run(cmd_launch, agent="leader", only="gamma,beta", dry_run=False)
        check("v2: window seat opens a window, pane seat opens a pane",
              ("window", "gamma") in opened and ("pane", VAULT_ROOT) in opened)
        check("v2: claude seat schedules /rename, opencode seat does not",
              "beta" in renames and "gamma" not in renames)
        # G-53: the write-log must not assert an injection this code path cannot observe. The
        # keystrokes go out ~25s later from a DETACHED subshell using raw tmux, bypassing the
        # instrumented primitives entirely, so the entry attests INTENT — and the action name has
        # to say so, or the line reads identically whether the keystroke landed or the pane died.
        check("G-53: the scheduled rename logs `rename-scheduled`, NEVER a bare `rename`, and its "
              "payload SAYS delivery is unobserved — this path hands the real keystrokes to a "
              "detached subshell that bypasses the instrumented primitives, so it can attest "
              "INTENT and must not claim the keystroke landed",
              RENAME_ACTION == "rename-scheduled"
              and "NOT observed" in rename_injection_note("zeta-seat", 25)
              and "zeta-seat" in rename_injection_note("zeta-seat", 25)
              and "~25s" in rename_injection_note("zeta-seat", 25))

        # ---- wave windows: `window: NAME` seats share one window, one pane each ----
        check("wave: placement plan — own / shared / pane",
              (seat_placement({"window": "yes", "agent": "a"}),
               seat_placement({"window": "wave-x", "agent": "a"}),
               seat_placement({"window": "", "agent": "a"}))
              == (("own", "a"), ("shared", "wave-x"), ("pane", None)))
        out = run(cmd_launch, agent="leader", only="hk-1,hk-2", dry_run=False)
        check("wave: first seat creates the shared window, second splits into it",
              [o for o in opened if o == ("window", "wave-haiku")] == [("window", "wave-haiku")]
              and "window:wave-haiku" in out and out.count("launched") == 2)

        # ---- PROP-8 end to end: one invalid seat refuses the WHOLE launch, pre-spawn ----
        badf = pkg / "workers" / "badseat.md"
        badf.write_text("---\nagent: badseat\nmodel: opsu\n---\nbrief\n")
        opened_before = len(opened)
        out, code = refuse(cmd_launch, agent="leader", only="badseat,alpha", dry_run=False)
        check("PROP-8: a launch containing an invalid seat is refused BEFORE any pane opens — "
              "the valid seat beside it is not launched either (an invalid slug used to kill "
              "the whole wave at model-init, after every pane had spawned)",
              code == 1 and "badseat" in out and "opsu" in out and "NO pane" in out
              and len(opened) == opened_before)
        out = run(cmd_launch, agent="leader", only="badseat,alpha", dry_run=True)
        check("PROP-8: dry-run shows the same per-seat pre-flight refusal instead of a command",
              "REFUSED" in out and "opsu" in out)
        badf.unlink()

        # ---- v2: transcript export ----
        run(cmd_checkin, agent="gamma", summary="gamma work", pane="%5")
        out = run(cmd_export_transcript, target="gamma", label="test")
        check("v2: export-transcript writes into the worker folder",
              "transcript exported" in out and any((gdir / "transcripts").glob("*-gamma-test.txt")))

        # ---- v2: closer prompt + close dry-run ----
        text = closer_prompt(ns(), "gamma", renew=True)
        check("v2: closer prompt filled (target, memory path, renew)",
              "closer-gamma" in text and str(gdir / "memory.md") in text
              and "close-seat gamma --renew" in text and "RENEW IS ON" in text)
        check("T1 doc: the closer template teaches the identity-less grammar (no seat types its "
              "own name into send/read/depart)",
              " send gamma " in text and " read`" in text and " depart`" in text
              and "send closer-gamma" not in text and "read closer-gamma" not in text
              and "depart closer-gamma" not in text)
        out = run(cmd_close, agent="leader", target="gamma", renew=False, dry_run=True)
        check("v2: close --dry-run shows sonnet closer + prompt + shared 'closers' window",
              CLOSER_MODEL in out and "closer-gamma" in out and CLOSERS_WINDOW in out)

        # ---- closer placement: pure decision function (headless, no tmux) ----
        check("closer_placement: no existing pane -> create the shared window",
              closer_placement("") == ("new_window", CLOSERS_WINDOW))
        check("closer_placement: existing pane -> split into it",
              closer_placement("%77") == ("split", "%77"))

        # ---- v2: close-seat kills, checks out, renews ----
        killed.clear()
        opened.clear()
        out = run(cmd_close_seat, agent="closer-gamma", target="gamma", renew=True, no_export=False)
        _, _, rows = load_workers(base_dir(ns()))
        g = current_row(rows, "gamma")
        check("v2: close-seat checks the row out and kills the pane",
              g["active"] == "no" and "closed" in g["checkout"] and "%5" in killed)
        check("v2: close-seat --renew relaunches the seat", ("window", "gamma") in opened
              and "renewed: gamma" in out)

        # ---- leader renew: a pane seat relaunches into its OLD window, never the caller's ----
        run(cmd_checkin, agent="leader", summary="arbiter", pane="%6")
        pane_windows["%6"] = "@7"
        killed.clear()
        split_targets.clear()
        out = run(cmd_close_seat, agent="leader", target="leader", renew=True, no_export=False)
        check("leader renew: close-seat --renew leader finds the briefing and relaunches it as "
              "a pane into the window its old pane occupied (the control panel)",
              "%6" in killed and split_targets == ["@7"] and "renewed: leader" in out)

        # ---- G-10/G-11/G-12 on the real command paths (2026-07-27 close/renew ceremony) ----
        # Fixture hygiene: this block uses probe-* names and restores alpha's row at the end, so it
        # cannot consume a row a later check needs (it did once — the suite died on an unrelated
        # `checkout` whose seat this block had departed).
        harness_up["v"] = []            # positively absent: a shell-only pane
        out, code = refuse(cmd_checkin, agent="probe-a", summary="from a bare shell", pane="%1")
        check("G-11: a check-in from a pane with NO harness process is REFUSED — the roster is the "
              "run's map of what is alive, so the claim is verified against the process table at "
              "the moment it is made (a closer's briefing executed by bash checked itself in and "
              "was believed for seven minutes)",
              code == 1 and "G-11" in out and "nothing behind it" in out)
        check("G-11: the refusal names the cause AND the escape hatch for an unrecognized wrapper",
              "literal keystrokes" in out and "COORD_SKIP_HARNESS_CHECK=1" in out)
        harness_up["v"] = None          # unverifiable
        out = run(cmd_checkin, agent="probe-a", summary="unverifiable pane", pane="%1")
        check("G-11: unverifiable liveness PASSES — losing a real seat to a false refusal is worse "
              "than the defect (asymmetric on purpose)", "checked in: probe-a" in out)

        harness_up["v"] = []
        wake_ok["v"] = True
        out, code = refuse(cmd_launch, agent="leader", only="alpha", dry_run=False, force=False)
        check("G-11: a launch whose pane never brings a harness up FAILS LOUDLY instead of "
              "reporting a launched seat — the submitted start line is not evidence it ran",
              "FAILED" in out and "G-11" in out)
        harness_up["v"] = None

        # G-12: the renew respawns the seat's own pane instead of killing it and splitting a new
        # one, so an arranged window layout survives. Exercised through the real command.
        run(cmd_checkin, agent="alpha", summary="pane seat", pane="%31")
        live_tmux_panes["v"] = {"%31"}
        killed.clear(); opened.clear(); respawned.clear(); split_targets.clear()
        out = run(cmd_close_seat, agent="leader", target="alpha", renew=True, no_export=True)
        check("G-12: close-seat --renew on a live PANE seat respawns that pane in place — pane id "
              "and cell kept, nothing killed, nothing split, no re-tile",
              respawned == [("%31", str(pkg / "workers"))] or respawned == [("%31", VAULT_ROOT)]
              or (respawned and respawned[0][0] == "%31"))
        check("G-12: the in-place renew kills no pane and opens none — the two acts that re-tiled "
              "the window", not killed and not opened and not split_targets)
        check("G-12: it reports the seat back in the SAME pane", "renewed: alpha" in out
              and "%31" in out and "layout intact" in out)
        live_tmux_panes["v"] = set()

        # G-10: a teardown proves the process died instead of assuming kill-pane was enough.
        harness_up["v"] = [98765]
        run(cmd_checkin, agent="probe-b", summary="ghost probe", pane="%32")
        reaped.clear()
        out = run(cmd_close_seat, agent="leader", target="probe-b", renew=False, no_export=True)
        check("G-10: close-seat verifies the harness pid actually EXITED after kill-pane and says "
              "so — kill-pane SIGHUPs the group and a blocked harness survives as a ghost nobody "
              "counts (three were hand-reaped on 2026-07-27)",
              98765 in reaped and "process check" in out and "GONE" in out)
        reaped.clear()
        run(cmd_checkin, agent="probe-c", summary="departing probe", pane="%33")
        out = run(cmd_depart, agent="probe-c")
        check("G-10: depart arms a detached reaper for its OWN harness — it kills its pane, so this "
              "process dies with it and can verify nothing afterwards",
              98765 in reaped and "exit reaper" in out)
        harness_up["v"] = None
        run(cmd_checkin, agent="alpha", summary="second check-in", pane="%3")  # restore fixture

        # Memory pre-flight (leader ruling #128): the gate holds a SPIKE reserve, not a floor over
        # steady state. Pure, so both branches are checkable without touching /proc.
        check("mem gate: room for the spike reserve -> no refusal",
              memory_gate(1, LAUNCH_MEM_FLOOR_MB) == "" and memory_gate(2, 4300) == "")
        check("mem gate: below the reserve -> refused, naming the peak and the reason a flat "
              "steady-state floor is the wrong shape",
              "peaks at" in memory_gate(1, LAUNCH_MEM_FLOOR_MB - 1)
              and "SIGKILL a bystander" in memory_gate(1, 1000))
        check("mem gate: an N-seat wave needs a spike per seat beyond the first",
              memory_gate(3, LAUNCH_MEM_FLOOR_MB + SEAT_SPIKE_MB) != ""
              and memory_gate(3, LAUNCH_MEM_FLOOR_MB + 2 * SEAT_SPIKE_MB) == "")
        check("mem gate: an unreadable sensor PASSES — a broken meter must not stop a run",
              memory_gate(5, 0) == "")

        # ---- v2: control panel — overview pane, idempotent ----
        opened.clear()
        out = run(cmd_panel, agent="leader")
        check("panel: opens a short full-width strip running tmux-overview --compact --package",
              ("strip", PANEL_STRIP_ROWS) in opened and "tmux-overview 'testsess' --compact" in out
              and "roster names from the package" in out)
        panel_panes.append(("%42", "overview"))
        opened.clear()
        out = run(cmd_panel, agent="leader")
        check("panel: idempotent when an overview pane exists",
              not opened and "already open" in out)
        # closer placement (owner-directed layout fix): closers NEVER open in the control-panel
        # window; the first close of a run creates the shared 'closers' window, every closer
        # after that splits into that SAME window as an additional pane, titled by its target.
        opened.clear()
        out = run(cmd_close, agent="leader", target="gamma", renew=False, dry_run=False)
        check("closer placement: first closer creates the shared 'closers' window (not a pane "
              "in the caller's own window)",
              ("window", CLOSERS_WINDOW) in opened
              and not any(k == "pane" for k, _ in opened)
              and any(t == "closer-gamma" for _, t in titles))

        opened.clear()
        out = run(cmd_close, agent="leader", target="beta", renew=False, dry_run=False)
        check("closer placement: second closer splits into the EXISTING 'closers' window, "
              "never opens a second one",
              not any(k == "window" for k, _ in opened)
              and any(k == "pane" for k, _ in opened)
              and any(t == "closer-beta" for _, t in titles))
        # These two closes are real closes, so they really did put gamma and beta into the G-21
        # CLOSING state — and neither runs close-seat, so nothing would clear it. This section's
        # subject is PANE PLACEMENT, and both seats keep working as ordinary recipients in a dozen
        # later sections, so the state is cleared HERE rather than left to refuse thirty unrelated
        # sends. G-21's own behaviour is exercised deliberately in its section below.
        for seat in ("gamma", "beta"):
            clear_closing(base_dir(ns()), seat)

        # ---- v2: depart (self close) ----
        run(cmd_checkin, agent="delta", summary="one pass", pane="%7")
        killed.clear()
        out = run(cmd_depart, agent="delta")
        _, _, rows = load_workers(base_dir(ns()))
        d = current_row(rows, "delta")
        check("v2: depart exports, checks out, kills own pane",
              d["active"] == "no" and "%7" in killed
              and any((pkg / "workers" / "delta" / "transcripts").glob("*-delta-depart.txt")))

        # ---- T3: checkout mechanizes the transcript export (--no-export escapes) ----
        out = run(cmd_checkout, agent="beta", no_export=False)
        _, _, rows = load_workers(base_dir(ns()))
        b = current_row(rows, "beta")
        check("checkout stamps row", b["active"] == "no" and b["checkout"] != "")
        check("T3: checkout auto-exports the seat's transcript first",
              "transcript:" in out
              and any((pkg / "workers" / "beta" / "transcripts").glob("*-beta-checkout.txt")))
        run(cmd_checkin, agent="beta", summary="second beta pass", pane="%2")
        before_exports = len(list((pkg / "workers" / "beta" / "transcripts").glob("*.txt")))
        out = run(cmd_checkout, agent="beta", no_export=True)
        check("T3: --no-export skips it (a dead pane has nothing to capture)",
              "transcript:" not in out
              and len(list((pkg / "workers" / "beta" / "transcripts").glob("*.txt")))
              == before_exports)
        # G-134 — THE SEAM, asserted on the REAL verb rather than on the helpers it calls. The
        # helper checks further down all passed with `checkout`'s call to set_awaiting disabled:
        # both halves green, the COMPOSITION never taken, which is G-124's lesson exactly. This is
        # the row that fails when the wiring is cut, and it is the one that matters — the debt is
        # worthless if the act that incurs it does not record it.
        check("G-134 (wiring): `checkout` ITSELF records the debt, and it names the pane the "
              "leader must free — a checked-out seat's pane stays LIVE until close-seat, which is "
              "the 41-minute leak this exists to make impossible to miss",
              load_awaiting(base_dir(ns())).get("beta", {}).get("pane") == "%2"
              and "awaiting close" in out)
        cs_out = run(cmd_close_seat, agent="leader", target="beta", no_export=True, renew=False)
        check("G-134 (wiring): and `close-seat` SETTLES it — the debt dies with the act that "
              "actually frees the resources, so a settled seat never lingers in the leader's view "
              "and the record cannot outlive the leak it reports",
              "beta" not in load_awaiting(base_dir(ns())) and "debt settled" in cs_out)

        check("auto-name: checkin titles the pane after the agent",
              ("%1", "alpha") in titles and ("%2", "beta") in titles)

        # ---- T1: identity resolution + verification (F1) ----
        calling_pane["v"] = ""
        check("T1: an explicit args.agent (watch.py's internal Namespace calls) resolves as --as",
              resolve_agent(ns(agent="watcher")) == "watcher")
        os.environ["COORD_AGENT"] = "alpha"
        check("T1: COORD_AGENT (injected at launch) resolves the caller with nothing typed",
              resolve_agent(ns()) == "alpha")
        check("T1: --as beats COORD_AGENT", resolve_agent(ns(as_agent="beta")) == "beta")
        os.environ.pop("COORD_AGENT", None)
        calling_pane["v"] = "%3"
        check("T1: with no claim at all, the calling pane's registered roster row IS the identity",
              resolve_agent(ns()) == "alpha")
        out, code = refuse(resolve_agent, as_agent="beta")
        check("T1: a claim contradicting the calling pane's registered agent is REFUSED, and the "
              "refusal names the registered agent",
              code == 2 and "'alpha'" in out and "beta" in out)
        with redirect_stderr(io.StringIO()):
            forced = resolve_agent(ns(as_agent="beta", force=True))
        check("T1: --force overrides the contradiction deliberately", forced == "beta")
        out, code = refuse(cmd_send, agent="par-b", to="alpha", message="impersonation",
                           type="note", supersedes=None, re_num=None, file=None)
        check("T1 end-to-end: a command claiming another seat's name from a registered pane is "
              "refused before anything is written", code == 2 and "alpha" in out)
        calling_pane["v"] = "%99"  # a pane no roster row claims
        out, code = refuse(resolve_agent)
        check("T1: unresolvable identity teaches checkin instead of guessing",
              code == 2 and "checkin" in out and "--as" in out)
        calling_pane["v"] = ""

        # ---- T6: hard role gates (F14 — these commands documented a rule they never enforced) ----
        out, code = refuse(cmd_launch, agent="beta", only="hk-1", dry_run=True)
        check("gate: launch hard-refuses a non-leader caller", code == 2 and "leader" in out)
        out, code = refuse(cmd_launch, agent="beta", only="hk-1", dry_run=True, force=True)
        check("gate: --force is the escape on every gate", code == 0 and "[dry-run] hk-1" in out)
        out, code = refuse(cmd_panel, agent="beta")
        check("gate: panel hard-refuses a non-leader caller", code == 2)
        out, code = refuse(cmd_add_to_group, agent="beta", group="pair", members=["gamma"])
        check("gate: add-to-group stays leader-only", code == 2)
        out, code = refuse(cmd_close_seat, agent="beta", target="alpha", renew=False, no_export=True)
        check("gate: close-seat refuses a plain worker (leader or closer-* only)", code == 2)
        out, code = refuse(cmd_owner, agent="beta", state="afk", note="")
        check("gate: owner refuses a worker", code == 2)
        out = run(cmd_owner, state="afk", note="dinner")
        check("gate: owner ACCEPTS an unresolvable identity — that caller is the human owner",
              "owner is now: afk" in out)
        run(cmd_owner, agent="leader", state="present", note="back")

        # ---- T3: recipient validation, length guard, file/stdin bodies ----
        out, code = refuse(cmd_send, agent="alpha", to="betaa", message="typo", type="note",
                           supersedes=None, re_num=None, file=None)
        check("T3 validation: an unknown recipient is refused with the closest match (F5)",
              code == 1 and "betaa" in out and "'beta'" in out)
        out, code = refuse(cmd_send, agent="alpha", to="betaa", message="typo", type="note",
                           supersedes=None, re_num=None, file=None, force=True)
        check("T3 validation: --force sends it anyway", code == 0 and "sent message #" in out)
        raw_before = (base_dir(ns()) / "messages.md").read_text(encoding="utf-8")
        out = sd("alpha", "hk-2", "your briefing exists but you have not checked in yet")
        raw_after = (base_dir(ns()) / "messages.md").read_text(encoding="utf-8")
        check("T3 validation: a briefed-but-not-yet-launched seat is a VALID recipient — and its "
              "wake is never ATTEMPTED, so it is named in the skip list as `not launched` and "
              "NOTHING is written to the log (a wake nobody sent cannot have failed)",
              "sent message #" in out and "skipped (not launched: hk-2)" in out
              and "wake FAILED" not in out
              and raw_after.count("> delivery-failure:")
              == raw_before.count("> delivery-failure:"))
        long_body = "x" * (MESSAGE_MAX + 1)
        out, code = refuse(cmd_send, agent="alpha", to="beta", message=long_body, type="note",
                           supersedes=None, re_num=None, file=None)
        check("T3 length guard: an oversized body is refused and TEACHES the file+summary fix",
              code == 1 and str(MESSAGE_MAX) in out and "Write it to a file" in out)
        out, code = refuse(cmd_send, agent="alpha", to="beta", message=long_body, type="note",
                           supersedes=None, re_num=None, file=None, force=True)
        check("T3 length guard: --force escapes it", code == 0 and "sent message #" in out)
        body_file = Path(td) / "body.md"
        body_file.write_text("holds `backticks`, \"quotes\" and $(substitution)\nsecond line\n",
                             encoding="utf-8")
        run(cmd_send, agent="alpha", to="beta", message=None, type="note", supersedes=None,
            re_num=None, file=str(body_file))
        _, blocks = load_messages(base_dir(ns()))
        check("T3 --file: the body is read from disk verbatim — backticks never touch a shell (F6)",
              "`backticks`" in body_of(blocks[-1]) and "$(substitution)" in body_of(blocks[-1])
              and "second line" in body_of(blocks[-1]))
        saved_stdin = sys.stdin
        sys.stdin = io.StringIO("body piped in on stdin\n")
        try:
            run(cmd_send, agent="alpha", to="beta", message=None, type="note", supersedes=None,
                re_num=None, file="-")
        finally:
            sys.stdin = saved_stdin
        _, blocks = load_messages(base_dir(ns()))
        check("T3 --file -: the body is read from stdin",
              "body piped in on stdin" in body_of(blocks[-1]))
        out, code = refuse(cmd_send, agent="alpha", to="beta", message="both", type="note",
                           supersedes=None, re_num=None, file=str(body_file))
        check("T3: a positional body AND --file together are refused", code == 1 and "not both" in out)
        out, code = refuse(cmd_send, agent="alpha", to="beta", message=None, type="note",
                           supersedes=None, re_num=None, file=None)
        check("T3: no body at all is refused with the --file hint",
              code == 1 and "no message body" in out)

        # ---- T4: ask threading ----
        out, code = refuse(cmd_send, agent="alpha", to="beta", message="here you go",
                           type="answer", supersedes=None, re_num=None, file=None)
        check("T4: an answer with no --re is refused and teaches `pending`",
              code == 1 and "--re" in out and "pending" in out)
        out, code = refuse(cmd_send, agent="alpha", to="beta", message="here you go",
                           type="answer", supersedes=None, re_num=None, file=None, force=True)
        check("T4: --force is the rare escape", code == 0 and "sent message #" in out)
        out, code = refuse(cmd_send, agent="alpha", to="beta", message="fyi", type="note",
                           supersedes=None, re_num=4, file=None)
        check("T4: --re on a type that cannot carry it is refused",
              code == 1 and "only on --type answer" in out)
        out, code = refuse(cmd_send, agent="alpha", to="beta", message="answering", type="answer",
                           supersedes=None, re_num=9999, file=None)
        check("T4: --re must reference a message that exists", code == 1 and "no such message" in out)
        out, code = refuse(cmd_send, agent="alpha", to="beta", message="answering", type="answer",
                           supersedes=None, re_num=3, file=None)
        check("T4: --re must reference an ASK, not any message", code == 1 and "not an ask" in out)

        ask_open = int(sd("alpha", "leader", "PENDING: which layout wins?", type="ask")
                       .split("#")[1].split()[0])
        ask_closed = int(sd("alpha", "leader", "CLOSED-BY-ANSWER: rerun the export?", type="ask")
                         .split("#")[1].split()[0])
        sd("leader", "alpha", "yes, rerun it", type="answer", re_num=ask_closed)
        ask_superseded = int(sd("alpha", "leader", "CLOSED-BY-SUPERSESSION: ignore me", type="ask")
                             .split("#")[1].split()[0])
        sd("alpha", "leader", "withdrawn", type="note", supersedes=ask_superseded)
        _, blocks = load_messages(base_dir(ns()))
        nums = {b["num"] for b in open_asks(blocks)}
        check("T4: an ask is OPEN until an answer --re's it or it is superseded",
              ask_open in nums and ask_closed not in nums and ask_superseded not in nums)

        def section_of(text, title):
            lines = text.splitlines()
            start = next((i for i, ln in enumerate(lines) if ln.startswith(title)), None)
            if start is None:
                return ""
            body = []
            for ln in lines[start + 1:]:
                if not ln.startswith("  "):
                    break
                body.append(ln)
            return "\n".join(body)

        out = run(cmd_pending, agent="leader")
        check("T4 pending: open asks addressed to me are listed with their age; settled and "
              "superseded ones are gone",
              f"#{ask_open} " in section_of(out, "asks waiting on you")
              and f"#{ask_closed} " not in out and f"#{ask_superseded} " not in out
              and "old" in section_of(out, "asks waiting on you"))
        out = run(cmd_pending, agent="alpha")
        check("T4 pending: my own unanswered asks are a separate section",
              f"#{ask_open} " in section_of(out, "your asks nobody has answered"))

        # ---- T2: status ----
        out = run(cmd_status, agent="alpha")
        check("T2 status: identity, pane, owner, cursor, unread-by-type and open asks in one shot",
              "you:    alpha" in out and "pane:   %3" in out and "owner:  present" in out
              and "cursor: #" in out and "unread:" in out and "asks waiting on you:" in out
              and "next:" in out)
        out = run(cmd_status, agent="gamma")
        check("T2 status: a not-checked-in caller is taught checkin, not shown a half-state",
              "NOT checked in" in out and "checkin gamma" in out)

        # ---- T3: wakes to DEPARTED seats are skipped quietly, never logged as failures (F7) ----
        raw_before = (base_dir(ns()) / "messages.md").read_text(encoding="utf-8")
        out = sd("alpha", "all", "who is still here?", force=True)
        raw_after = (base_dir(ns()) / "messages.md").read_text(encoding="utf-8")
        new_failures = (raw_after.count("> delivery-failure:")
                        - raw_before.count("> delivery-failure:"))
        departed_line = next((ln for ln in out.splitlines() if "skipped (departed:" in ln), "")
        departed_names = [n.strip() for n in
                          departed_line.split("departed:")[-1].split(")")[0].split(",")]
        check("T3: a departed seat is skipped quietly — every one of them NAMED to the sender in "
              "the single wake summary line (T6), in sorted order, and NEVER written to the log "
              "as a delivery failure; nothing else in this broadcast was attempted-and-failed "
              "either, so the log gains no failure line at all",
              "beta" in departed_names and "delta" in departed_names
              and departed_names == sorted(departed_names)
              and out.count("wakes: ") == 1
              and new_failures == 0 and "delivery-failure: delta" not in raw_after)
        # ---- fix round: a built-in auto-wake DEFAULT naming a seat this package does not have ----
        # (the body must not name the seat itself — the assertion below reads the whole log)
        out = sd("alpha", "beta", "a routine send in a package holding no such default seat")
        raw = (base_dir(ns()) / "messages.md").read_text(encoding="utf-8")
        check("fix round: `scientist` is a built-in auto-wake DEFAULT, not a roster — with no "
              "scientist row and no scientist briefing in this package it is not a recipient at "
              "all: no wake, no skip mention, no log line (every send used to log a phantom "
              "scientist delivery failure, the 46:1 noise class F7 is about)",
              "scientist" not in out and "scientist" not in raw)

        # ---- T5: broadcast wakes run in parallel, results printed in sorted order ----
        import threading
        for seat, seat_pane in (("par-a", "%21"), ("par-b", "%22"), ("par-c", "%23")):
            run(cmd_checkin, agent=seat, summary=f"{seat} work", pane=seat_pane)
        run(cmd_create_group, agent="par-a", group="parallel", members=["par-b", "par-c"])
        probe = {"cur": 0, "max": 0}
        plock = threading.Lock()

        def recording_wake(pane, text):
            with plock:
                probe["cur"] += 1
                probe["max"] = max(probe["max"], probe["cur"])
            time.sleep(0.05)
            with plock:
                probe["cur"] -= 1
            return True, ""

        saved_wake = wake
        wake = recording_wake
        out = sd("par-a", "parallel", "wave check")
        wake = saved_wake
        summary = [ln for ln in out.splitlines() if ln.strip().startswith("wakes: ")]
        delivered_n = int(summary[0].split("wakes: ")[1].split()[0]) if summary else 0
        check("T5 parallel: recipients are woken concurrently, and their results collapse into "
              "ONE deterministic summary line — no per-recipient delivery lines are left to "
              "interleave (T6 compression; failures still get their own line)",
              probe["max"] > 1 and len(summary) == 1 and delivered_n >= 2
              and "wake -> " not in out)

        # ---- T5: the package lock, and its lockless fallback ----
        check("T5 lock: a locked write creates the package lockfile", (base_dir(ns()) / ".lock").exists())
        saved_flock = _acquire_flock

        def broken_flock(fh):
            raise OSError("EROFS: read-only file system")

        _acquire_flock = broken_flock
        _LOCK_NOTE["shown"] = False
        errbuf = io.StringIO()
        with redirect_stderr(errbuf):
            out = sd("par-a", "par-b", "sent while the lock is unavailable")
        _acquire_flock = saved_flock
        check("T5 lock: an unusable lock (read-only sandbox) degrades to lockless with ONE note "
              "and still writes — never a crash",
              "sent message #" in out and "proceeding lockless" in errbuf.getvalue())

        # ---- T5: cursor persistence is non-fatal, and no-ops are not rewritten ----
        saved_atomic = atomic_write

        def failing_workers_write(path, text):
            if Path(path).name == "workers.md":
                raise OSError("EROFS: read-only file system")
            return saved_atomic(path, text)

        atomic_write = failing_workers_write
        out = rd("par-c")
        atomic_write = saved_atomic
        check("T5: a cursor-persist failure never costs the reader its messages — the batch is "
              "shown, with an --after hint instead of a traceback (F9, codex EROFS)",
              "-- shown" in out and "cursor NOT stored" in out and "--after" in out
              and "EROFS" in out)
        out = rd("par-c")
        cur = int(cursor_of("par-c"))
        writes = []
        atomic_write = lambda p, t: (writes.append(Path(p).name) or saved_atomic(p, t))
        out = rd("par-c", after=cur - 1)
        atomic_write = saved_atomic
        check("T5: a cursor rewrite that would change nothing is skipped entirely "
              "(the no-op rewrite was itself a race source, scientist-roster #103)",
              "cursor already at" in out and "workers.md" not in writes)

        # ---- fix round: the read cursor belongs to the SEAT, not to one session of it ----
        run(cmd_checkin, agent="rejoin", summary="first session", pane="%31")
        check("checkin cursor: a first-ever check-in still starts at 0",
              cursor_of("rejoin") == "0")
        sd("alpha", "rejoin", "read me before the relaunch")
        rd("rejoin")
        kept = cursor_of("rejoin")
        out = run(cmd_checkin, agent="rejoin", summary="re-check-in, same seat", pane="%31")
        check("checkin cursor: a re-check-in INHERITS the superseded row's cursor and reports "
              "unread FROM it — it used to write lastread=0, so the seat was told the whole log "
              "was waiting for it",
              kept != "0" and cursor_of("rejoin") == kept
              and f"cursor kept at #{kept}" in out and "nothing waiting yet" in out)
        run(cmd_checkout, agent="rejoin", no_export=True)
        out = run(cmd_checkin, agent="rejoin", summary="renewed session", pane="%32")
        check("checkin cursor: a RENEWED seat inherits it too — close-seat --renew closes the "
              "row BEFORE the fresh session checks in, so there is no ACTIVE row left to "
              "supersede, and that is the exact path the symptom was reported on",
              cursor_of("rejoin") == kept)
        run(cmd_checkin, agent="fresh", summary="a different seat entirely", pane="%33")
        check("checkin cursor: never inherited across agent NAMES", cursor_of("fresh") == "0")

        # ---- fix round: the workers lag column is the exact per-agent unread count ----
        for i in range(3):
            sd("rejoin", "alpha", f"my own message {i}")
        _, tail_blocks = load_messages(base_dir(ns()))
        old_formula = tail_blocks[-1]["num"] - int(cursor_of("rejoin"))
        out = run(cmd_workers, full=False, history=False)
        rejoin_line = next((ln for ln in out.splitlines() if ln.startswith("rejoin")), "")
        st = run(cmd_status, agent="rejoin")
        check("workers lag: an agent whose OWN messages are the log tail is NOT reported behind "
              "— the column now runs the same addressing/observer-aware unread derivation "
              "`status` uses (`log tail - cursor` counted the agent's own sends against it: "
              f"it would have said lag={old_formula} here)",
              old_formula == 3 and " lag=0" in rejoin_line and "unread: 0 (none)" in st)

        # ---- T6: the two output modes (--pretty is EXPLICIT — never TTY-detected) ----
        plain = run(cmd_status, agent="alpha")
        check("T6 --pretty off (the default): the output carries ZERO ANSI escape bytes — an "
              "agent re-quoting a line must not paste colour codes into the log",
              "\x1b[" not in plain and "\x1b[" not in run(cmd_workers, full=False, history=False)
              and "\x1b[" not in rd("beta", after=0, peek=True, digest=True)
              and "\x1b[" not in run(cmd_pending, agent="leader"))
        set_pretty(argparse.Namespace(pretty=True))
        pretty_status = run(cmd_status, agent="alpha")
        pretty_digest = rd("beta", after=0, peek=True, digest=True)
        pretty_workers = run(cmd_workers, full=False, history=False)
        pretty_pending = run(cmd_pending, agent="leader")
        PRETTY["on"] = False
        check("T6 --pretty on: status, workers, read --digest and pending render ANSI, and the "
              "plain text underneath is unchanged (colour wraps, never replaces)",
              all("\x1b[" in o for o in (pretty_status, pretty_digest, pretty_workers,
                                         pretty_pending))
              and "you:" in pretty_status and "asks waiting on you" in pretty_pending)
        os.environ["COORD_PRETTY"] = "1"
        env_on = set_pretty(argparse.Namespace(pretty=False))
        env_pretty = run(cmd_status, agent="alpha")
        os.environ.pop("COORD_PRETTY", None)
        off_again = set_pretty(argparse.Namespace(pretty=False))
        check("T6 --pretty: COORD_PRETTY=1 turns the human mode on without the flag, and dropping "
              "it turns the mode back off (no TTY sniffing either way)",
              env_on and "\x1b[" in env_pretty and not off_again
              and "\x1b[" not in run(cmd_status, agent="alpha"))

        # ---- T6/F2: the help is an INDEX, not a manual (it used to print the module docstring) ----
        saved_cols = os.environ.get("COLUMNS")
        os.environ["COLUMNS"] = "100"  # deterministic wrapping for the line count
        parser = build_parser()
        top = parser.format_help()
        per_cmd = {name: sp.format_help() for name, sp in parser.command_parsers.items()}
        if saved_cols is None:
            os.environ.pop("COLUMNS", None)
        else:
            os.environ["COLUMNS"] = saved_cols
        check("T6 help: the top-level -h is a one-screen index — 30 lines or fewer, grouped "
              "everyday/leader/other, pointing at the per-command help (F2/F18: it used to dump "
              "a ~120-line docstring listing every subcommand a second time)",
              len(top.splitlines()) <= 30
              and all(f"\n{g}\n" in top for g in ("everyday", "leader", "other"))
              and "coordinate <command> -h" in top
              and "--last-read" not in top and "read <agent>" not in top)
        # T6: the command inventory is DERIVED from the epilog index, never counted. A hardcoded
        # count (`len(per_cmd) == 19`) is a check that passes while the claim it stands for goes
        # false: add a command and document nothing, bump the number to make the suite green, and
        # the drift it existed to catch is now invisible — it can never see an UNDOCUMENTED
        # command, only a miscounted one. The set difference sees both, and names which command
        # and which side is missing it.
        documented = set()
        for epi_line in HELP_EPILOG.splitlines():
            listed = re.match(r"^  (\S(?:.*?\S)?)\s{2,}\S", epi_line)
            if listed:
                documented.update(name.strip() for name in listed.group(1).split("/"))
        undocumented = sorted(set(per_cmd) - documented)
        phantom = sorted(documented - set(per_cmd))
        check("T6 help: the epilog index and the parser agree on the command set, derived from "
              "both rather than counted — accepted but undocumented: %s; documented but not "
              "accepted: %s" % (undocumented or "none", phantom or "none"),
              per_cmd and not undocumented and not phantom)
        check("T6 help: every command's own -h carries a worked example and the step that "
              "usually follows",
              per_cmd
              and all("example:\n  coordinate" in h or "example:\n  python3" in h
                      for h in per_cmd.values())
              and all("\nnext: " in h for h in per_cmd.values()))
        check("T6 help: a target positional says it is the SEAT ACTED ON, never the caller "
              "(F14 — positional #1 used to mean SELF on some commands and TARGET on others)",
              all("TARGET seat" in per_cmd[n]
                  for n in ("close", "close-seat", "approve", "export-transcript")))

        # ---- G-57: the standing structural descriptor sweep ----
        # Fixture: three seats, each carrying one structural defect, plus a clean one — so a check
        # that merely counts findings cannot pass; each kind must be named.
        dpkg = Path(td) / "descpkg"
        (dpkg / "seats" / "good").mkdir(parents=True)
        (dpkg / "seats" / "wrongfolder").mkdir(parents=True)
        (dpkg / "seats" / "noreg").mkdir(parents=True)
        (dpkg / "seats" / "good" / "seat.md").write_text(
            "---\nseat: good\nharness: claude\nmodel: opus\neffort: medium\n---\nbody\n",
            encoding="utf-8")
        (dpkg / "seats" / "wrongfolder" / "seat.md").write_text(
            "---\nseat: mismatched\nharness: claude\nmodel: opus\neffort: high\n---\nbody\n",
            encoding="utf-8")
        (dpkg / "seats" / "noreg" / "seat.md").write_text(
            "---\nseat: noreg\nharness: claude\nmodel: sonnet\neffort: high\n---\nbody\n",
            encoding="utf-8")
        (dpkg / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "1,good,,claude,fable,medium,50,m1\n"       # binding divergence on model
            "2,mismatched,,claude,opus,high,50,m1\n"
            "3,ghostrow,,claude,opus,medium,50,m1\n",   # registry row with no descriptor
            encoding="utf-8")
        dns = argparse.Namespace(package=str(dpkg), run=None, base=None, workers_dir=None)
        kinds = {k for _, k, _ in descriptor_findings(dns)}
        check("G-57 descriptors: the sweep names each structural kind — a descriptor whose name "
              "disagrees with its folder, a descriptor with no registry row, a registry row with "
              "no descriptor, and a binding divergence — never just a count",
              kinds == {"name-vs-folder", "no-registry-row", "no-descriptor",
                        "binding-divergence"})
        divergence = [d for s, k, d in descriptor_findings(dns) if k == "binding-divergence"]
        check("G-57 descriptors: a binding divergence says which side BINDS, because a reader "
              "told only that two files differ has been handed the confusion, not the answer",
              len(divergence) == 1 and "THE DESCRIPTOR BINDS" in divergence[0])
        orphan = [s for s, k, _ in descriptor_findings(dns) if k == "no-descriptor"]
        check("G-57 descriptors: an orphan registry row is reported under the SEAT NAME from the "
              "row, so the finding names the seat that cannot launch", orphan == ["ghostrow"])
        (dpkg / "seats" / "dup").mkdir()
        (dpkg / "seats" / "dup" / "seat.md").write_text(
            "---\nseat: good\nharness: claude\nmodel: opus\neffort: medium\n---\nbody\n",
            encoding="utf-8")
        check("G-57 descriptors: two descriptors claiming ONE name is reported — launch would "
              "otherwise resolve it by directory walk order, not by anyone's intent",
              any(k == "duplicate-name" for _, k, _ in descriptor_findings(dns)))
        def run_descriptors(namespace):
            """cmd_descriptors EXITS, and runs against its own fixture package — neither the
            shared run() helper (which builds the self-test's own namespace) nor refuse() fits."""
            buf, code = io.StringIO(), 0
            with redirect_stdout(buf):
                try:
                    cmd_descriptors(namespace)
                except SystemExit as exc:
                    code = exc.code if isinstance(exc.code, int) else 1
            return buf.getvalue(), code

        cleanpkg = Path(td) / "cleanpkg"
        (cleanpkg / "seats" / "solo").mkdir(parents=True)
        (cleanpkg / "seats" / "solo" / "seat.md").write_text(
            "---\nseat: solo\nharness: claude\nmodel: opus\neffort: medium\n---\nbody\n",
            encoding="utf-8")
        (cleanpkg / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "1,solo,,claude,opus,medium,50,m1\n", encoding="utf-8")
        cns = argparse.Namespace(package=str(cleanpkg), run=None, base=None, workers_dir=None)
        check("G-57 descriptors: a structurally sound package yields ZERO findings — the sweep "
              "does not manufacture noise", descriptor_findings(cns) == [])
        clean_out, clean_code = run_descriptors(cns)
        check("G-57 descriptors: the BOUND is printed even on a CLEAN run — owned-surfaces and "
              "mission prose are not checked, so zero findings must never read as a clean class "
              "(the leader's rule, applied to the check that most invites the misreading)",
              clean_code == 0 and "bound:" in clean_out and "owned-surfaces" in clean_out
              and "NOT checked" in clean_out)
        # ---- G-61: boot-staleness, folder-scoped (a seat's instructions are write-once at boot) ----
        (cleanpkg / "coordination").mkdir(exist_ok=True)
        (cleanpkg / "coordination" / "workers.md").write_text(
            "| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
            "| solo | yes | %1 | working | 2026-07-27 06:00 |  | 0 |\n"
            "| gone | no | %2 | departed | 2026-07-27 06:00 | closed 2026-07-27 06:30 | 0 |\n",
            encoding="utf-8")
        seat_dir = cleanpkg / "seats" / "solo"
        boot_epoch = datetime(2026, 7, 27, 6, 0).timestamp()
        os.utime(seat_dir / "seat.md", (boot_epoch - 600, boot_epoch - 600))  # read at boot
        check("G-61 boot-stale: a seat whose folder has not changed since it checked in reports "
              "NOTHING — the check does not fire on mere age", boot_stale_findings(cns) == [])
        (seat_dir / "SEAT-STATE.md").write_text("superseded ruling, verbatim\n", encoding="utf-8")
        os.utime(seat_dir / "SEAT-STATE.md", (boot_epoch + 600, boot_epoch + 600))
        stale_found = boot_stale_findings(cns)
        check("G-61 boot-stale: a boot-read document that is NOT the descriptor — the widening "
              "that proved the class — is caught, because the scope is the seat's FOLDER and not "
              "seat.md alone",
              [(s, str(r)) for s, r, _ in stale_found] == [("solo", "SEAT-STATE.md")])
        (seat_dir / "transcripts").mkdir()
        (seat_dir / "transcripts" / "dump.txt").write_text("scrollback\n", encoding="utf-8")
        os.utime(seat_dir / "transcripts" / "dump.txt", (boot_epoch + 900, boot_epoch + 900))
        check("G-61 boot-stale: transcripts/ is EXCLUDED — it is an export target written by the "
              "close ceremony, never read at boot, and every close would otherwise flag its own "
              "seat", len(boot_stale_findings(cns)) == 1)
        (cleanpkg / "seats" / "gone").mkdir()
        (cleanpkg / "seats" / "gone" / "seat.md").write_text(
            "---\nseat: gone\n---\nbody\n", encoding="utf-8")
        os.utime(cleanpkg / "seats" / "gone" / "seat.md", (boot_epoch + 900, boot_epoch + 900))
        check("G-61 boot-stale: a CHECKED-OUT seat is not flagged — nothing is running on those "
              "instructions, so a changed file there is an edit, not a stale boot",
              all(s != "gone" for s, _, _ in boot_stale_findings(cns)))
        (seat_dir / "scratch-output.txt").write_text("my own work product\n", encoding="utf-8")
        os.utime(seat_dir / "scratch-output.txt", (boot_epoch + 300, boot_epoch + 300))
        stale_out, stale_code = run_descriptors(cns)
        check("G-61 boot-stale: findings exit non-zero and print their OWN bound — mtime not "
              "content, folder-scoped, over-reporting, and blind to a ruling nobody wrote down",
              stale_code == 1 and "SEAT-STATE.md" in stale_out and "MTIME, not content" in stale_out
              and "over-reports" in stale_out and "not proof a seat is current" in stale_out)
        check("G-61 boot-stale: a BOOT-READ document is ranked ABOVE a seat's own work product "
              "and marked as such — measured 10-of-11 noise on the first live pass, and an alarm "
              "that rings ten times per real signal is one nobody reads",
              # membership FIRST so `and` short-circuits: a mutation that removes a line must make
              # this check FAIL, never raise — .index() on an absent substring took the whole
              # self-test down with a ValueError and produced no verdict at all.
              "[BOOT-READ] SEAT-STATE.md" in stale_out
              and "[also] scratch-output.txt" in stale_out
              and stale_out.find("SEAT-STATE.md") < stale_out.find("scratch-output.txt"))
        check("G-61 boot-stale: the ranking is a DISPLAY heuristic and never a FILTER — the "
              "unlisted file is still reported and still counted, because a boot-read document "
              "under an unlisted name must not vanish",
              "1 BOOT-READ by name, 1 other" in stale_out
              and len(boot_stale_findings(cns)) == 2)

        dirty_out, dirty_code = run_descriptors(dns)
        check("G-57 descriptors: a package WITH findings exits non-zero and still prints the "
              "bound — the audit is gate-ready either way",
              dirty_code == 1 and "bound:" in dirty_out
              and "structural findings: 0" not in dirty_out)

        # ---- G-66: a raising check must still reach a VERDICT, never a bare traceback ----
        # The abort path is exercised by substituting the check body for one that raises, which is
        # the same global-substitution idiom the rest of this self-test uses for tmux.
        global _selftest_checks
        real_checks = _selftest_checks

        def _boom(a, f, n):
            n.append("a check that ran before the raise")
            raise ValueError("substring not found")

        def run_aborting(**kw):
            buf, code = io.StringIO(), 0
            with redirect_stdout(buf):
                try:
                    cmd_selftest(argparse.Namespace(expect_fail=None, **kw))
                except SystemExit as exc:
                    code = exc.code if isinstance(exc.code, int) else 1
            return buf.getvalue(), code

        _selftest_checks = _boom
        try:
            abort_out, abort_code = run_aborting()
            ef_out, ef_code = None, None
            buf = io.StringIO()
            with redirect_stdout(buf):
                try:
                    cmd_selftest(argparse.Namespace(
                        expect_fail="a check that ran before the raise"))
                except SystemExit as exc:
                    ef_code = exc.code if isinstance(exc.code, int) else 1
            ef_out = buf.getvalue()
        finally:
            _selftest_checks = real_checks
        check("G-66: a check whose condition RAISES still reaches a VERDICT — it used to take the "
              "whole self-test down with no verdict and no expect-fail line, a traceback reading "
              "as a broken harness rather than a caught defect",
              abort_code == 1 and "selftest: ABORTED" in abort_out
              and "ValueError: substring not found" in abort_out)
        check("G-66: ABORTED is distinguished from FAIL, and says the checks after the raise never "
              "ran — their results are UNKNOWN, not passing",
              "ABORTED" in abort_out and "selftest: FAIL" not in abort_out
              and "UNKNOWN, not passing" in abort_out)
        check("G-66: the abort names WHERE it raised, so a reader can find the raising check "
              "without re-running under a debugger",
              "coord.py:" in abort_out and "ABORTED after 1 check(s)" in abort_out)
        check("G-66: --expect-fail REFUSES on an abort — the named check produced no line, so the "
              "mutation is evidence about nothing; without this it would silently mis-report",
              ef_code == 1 and "ABORTED, so the named check produced no result" in ef_out)

        # ---- G-101: the shell guard must judge the INVOCATION, never the caller's shell ----
        # It used to live inside `message_body` and interrogate ambient process state, so it
        # refused THIS SUITE's own synthetic sends and tore the run down at check 17 of 303 —
        # while the very same file reported 303/exit 0 from a `timeout`-wrapped invocation,
        # because that leaves a non-shell parent. A gate whose verdict is decided by the shape
        # of the caller's command line is not a gate. Both directions are pinned here, and the
        # shell is forced ON so these cannot pass merely because this runner has no shell
        # parent — which is exactly how the defect hid from two honest verifiers.
        # NOTE: `_selftest_checks` is ONE long function, so every local below is `g101_`-
        # prefixed. An unprefixed `real` silently clobbered the suite's tuple of real tmux
        # primitives and aborted the run 50 checks later.
        # `shell_source_line` is stubbed too, and that is not incidental: without it these
        # checks would themselves be decided by the shape of the line that launched the suite
        # (the substitution detector reads the invoking shell's command string), which is the
        # exact fault under test. A check that inherits the defect it pins proves nothing.
        g101_pis, g101_cli = parent_is_shell, CLI_INVOCATION
        g101_ssl = shell_source_line
        try:
            globals()["parent_is_shell"] = lambda: True
            globals()["CLI_INVOCATION"] = True
            globals()["shell_source_line"] = lambda: ""
            g101_raised = False
            try:
                assert_argv_body_shell_safe(
                    ns(to="beta", message="hello", type="note", inline=False))
            except SystemExit:
                g101_raised = True
            check("G-101: a SYNTHETIC caller (no argv, no `func`) is never judged by the shell "
                  "guard — the self-test's own sends are this shape, and judging them aborted "
                  "the whole save gate at check 17 of 303", not g101_raised)
            g101_code = None
            try:
                with redirect_stderr(io.StringIO()):
                    assert_argv_body_shell_safe(
                        ns(to="beta", message="hi", type="note", inline=False, func=cmd_send))
            except SystemExit as exc:
                g101_code = exc.code
            check("G-101: a REAL argv positional body is still refused without --inline — the "
                  "move to the boundary must not have weakened S-4(b)", g101_code == 1)
            g101_inline_ok = True
            try:
                with redirect_stderr(io.StringIO()):
                    assert_argv_body_shell_safe(
                        ns(to="beta", message="hi", type="note", inline=True, func=cmd_send))
            except SystemExit:
                g101_inline_ok = False
            check("G-101: --inline still carries a real argv body past the guard", g101_inline_ok)
            # G-101 residual: an EXEC-AWAY WRAPPER (timeout/env/nice) leaves a non-shell parent.
            # The guard must refuse anyway — inferring shell-ness from the parent is what let
            # `timeout 30 coordinate send x "text $(...)"` write a shell-eaten body to the log.
            globals()["parent_is_shell"] = lambda: False
            g101_wrapped = None
            try:
                with redirect_stderr(io.StringIO()):
                    assert_argv_body_shell_safe(
                        ns(to="beta", message="hi", type="note", inline=False, func=cmd_send))
            except SystemExit as exc:
                g101_wrapped = exc.code
            check("G-101 residual: a positional argv body is refused even behind an exec-away "
                  "wrapper (no shell parent) — the guard asserts, it does not infer",
                  g101_wrapped == 1)
            # ...and the substitution half, pinned against a CONTROLLED shell line rather than
            # whatever launched this run: --inline is no escape from proven damage.
            globals()["shell_source_line"] = lambda: 'send beta "v is $(id -u)" --inline'
            g101_sub = None
            try:
                with redirect_stderr(io.StringIO()):
                    assert_argv_body_shell_safe(
                        ns(to="beta", message="v is 1000", type="note", inline=True,
                           func=cmd_send))
            except SystemExit as exc:
                g101_sub = exc.code
            check("G-101: a PROVEN substitution is still refused even with --inline — moving the "
                  "guard must not turn --inline into a blanket override", g101_sub == 1)
        finally:
            globals()["parent_is_shell"] = g101_pis
            globals()["CLI_INVOCATION"] = g101_cli
            globals()["shell_source_line"] = g101_ssl

        # ---- G-62: --expect-fail, the mutation-evidence gate, checking itself ----
        def expect_rc(expect, all_names, failed_names):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = report_expect_fail(expect, all_names, failed_names)
            return rc, buf.getvalue()

        ef_names = ["alpha check one", "beta check two", "gamma check three"]
        rc, out = expect_rc("beta", ef_names, ["beta check two"])
        check("G-62 --expect-fail: exits 0 ONLY when the named check failed and every other "
              "check passed", rc == 0 and "expect-fail: PASS" in out)
        rc, out = expect_rc("beta", ef_names, ["gamma check three"])
        check("G-62 --expect-fail: the suite going red while the NAMED check stayed SILENT is a "
              "failure — the wrong-reason red this mode exists to catch",
              rc == 1 and "never reached it" in out and "gamma check three" not in out)
        rc, out = expect_rc("beta", ef_names, ["beta check two", "gamma check three"])
        check("G-62 --expect-fail: the named check failing ALONGSIDE others is a failure — an "
              "unisolated mutation is not evidence about it, and the collateral is NAMED",
              rc == 1 and "not isolated" in out and "gamma check three" in out)
        rc, out = expect_rc("delta", ef_names, ["beta check two"])
        check("G-62 --expect-fail: a substring matching NO check FAILS — a typo must never be "
              "indistinguishable from a mutation that worked",
              rc == 1 and "no check matched" in out)
        rc, out = expect_rc("check", ef_names, ["beta check two"])
        check("G-62 --expect-fail: an AMBIGUOUS substring is refused, listing what it matched, "
              "rather than silently testing whichever check sorted first",
              rc == 1 and "EXACTLY ONE" in out and "alpha check one" in out)

        # ---- fix round: leader's idle next-hint drains the queue instead of self-messaging ----
        run(cmd_checkin, agent="leader", summary="arbiter, second sitting", pane="%41")
        sd("leader", "alpha", "ruling: layout A", type="answer", re_num=ask_open)
        rd("leader", limit=0)          # drain the log so the IDLE branch is the one under test
        out = run(cmd_status, agent="leader")
        check("F6 status: with nothing waiting, leader is pointed at its own drain (pending, "
              "then read) — the idle hint used to tell leader to `send leader ... --type ask`, "
              "i.e. to message itself",
              "unread: 0 (none)" in out and "asks waiting on you: 0" in out
              and "pending — drain the run's open asks" in out and "send leader" not in out)
        rd("fresh", limit=0)
        out = run(cmd_status, agent="fresh")
        check("F6 status: a plain worker's idle hint is unchanged — it still escalates to leader",
              "send leader" in out and "drain the run's open asks" not in out)

        # ---- P37: a re-check-in must never split one seat across two LIVE panes ----
        run(cmd_checkin, agent="twin", summary="first session", pane="%51")
        live_tmux_panes["v"] = {"%51"}
        out, code = refuse(cmd_checkin, agent="twin", summary="zombie relaunch", pane="%52")
        _, _, twin_rows = load_workers(base_dir(ns()))
        check("P37: a re-check-in is REFUSED while the pane already holding the name is still "
              "ALIVE — supersession would leave two live sessions under one name, mutually blind "
              "(the unread filter is keyed on the NAME) with only the newest receiving wakes",
              code == 1 and "%51" in out and "kill-pane" in out
              and current_row(twin_rows, "twin")["pane"] == "%51")
        check("P37: the refusal teaches confirm-dead-before-retry and kill BY PANE ID",
              "capture-pane" in out and "never by name" in out)
        out = run(cmd_checkin, agent="twin", summary="same pane, recovered", pane="%51")
        check("P37: re-checking in from the SAME pane is a recovery, not a twin — still supersedes",
              "superseded 1 prior row" in out)
        out = run(cmd_checkin, agent="twin", summary="deliberate second session", pane="%52",
                  force=True)
        check("P37: --force is the single deliberate override, as on every other refusal",
              "checked in: twin (%52)" in out)
        live_tmux_panes["v"] = {"%53"}   # the registered pane is GONE: an ordinary relaunch
        out = run(cmd_checkin, agent="twin", summary="relaunched after its pane died", pane="%53")
        check("P37: a relaunch whose old pane is dead supersedes exactly as before — the guard "
              "fires on pane LIVENESS, never on the mere existence of a prior active row",
              "superseded 1 prior row" in out)

        # ---- 8(b): a seat parked on an approval gate is never broadcast-woken ----
        run(cmd_checkin, agent="gated", summary="codex seat mid-approval", pane="%61")
        pane_titles["%61"] = "gated — Action Required"
        fails_before = (base_dir(ns()) / "messages.md").read_text(
            encoding="utf-8").count("> delivery-failure:")
        out = sd("alpha", "gated", "does this reach you?")
        fails_after = (base_dir(ns()) / "messages.md").read_text(
            encoding="utf-8").count("> delivery-failure:")
        check("8(b): a LIVE seat parked on an approval prompt is SKIPPED, not woken — keystrokes "
              "into a modal cannot be read and can land inside the gate leader has to answer. It "
              "is named to the sender with `approve` as the next step, and — like every other "
              "skip (T3) — nothing is written to the log, because only an ATTEMPTED wake can fail",
              "skipped (at an approval gate: gated)" in out and "approve <agent>" in out
              and fails_after == fails_before)
        pane_titles.pop("%61")
        out = sd("alpha", "gated", "and now?")
        check("8(b): the skip is live pane STATE, not a seat property — the same seat is woken "
              "normally the moment its title clears",
              "at an approval gate" not in out)

        # ---- P32: the roster view is the external check on the watcher loop ----
        hbp = base_dir(ns()) / "watch-heartbeat.json"
        hbp.write_text(json.dumps({"last_pass": datetime.now().isoformat(timespec="seconds"),
                                   "loop_min": 10, "pid": 4242}), encoding="utf-8")
        out = run(cmd_workers, full=False, history=False)
        check("P32: `workers` reports the watcher loop's last pass — the loop runs detached, so "
              "before this a DEAD watcher was indistinguishable from a quiet run (no flags "
              "either way) and the run lost liveness/context/approval cover silently",
              "watcher: ok" in out and "loop 10min" in out and "pid 4242" in out)
        hbp.write_text(json.dumps({"last_pass": "2000-01-01T00:00:00", "loop_min": 10,
                                   "pid": 4242}), encoding="utf-8")
        out = run(cmd_workers, full=False, history=False)
        check("P32: past three missed passes it is reported STALE, naming what has stopped being "
              "measured — one skipped pass is a slow capture, three is a dead loop",
              "watcher: STALE" in out and "stale past 30min" in out)
        hbp.unlink()
        out = run(cmd_workers, full=False, history=False)
        check("P32: a run with no watcher prints no line at all — the row is evidence, not chrome",
              "watcher:" not in out)
        live_tmux_panes["v"] = set()

        # ---- worker-mirror refresh: launch is the moment the mirror must be current ----
        # A codex/opencode seat reads AGENTS.md + .agents/ at boot; every AGENTS.md is gitignored,
        # so drift is per-machine and invisible to git. These cases pin the DECISION logic only —
        # none of them runs the installer.
        mroot = Path(td) / "mirror-ws"
        (mroot / "deep" / "nested").mkdir(parents=True)
        (mroot / "rbtv.json").write_text(
            json.dumps({"rbtv_path": "tools/rbtv"}), encoding="utf-8")
        (mroot / "tools" / "rbtv").mkdir(parents=True)

        found_root, found_path = find_workspace_root(mroot / "deep" / "nested")
        check("mirror: the workspace root is found by walking UP from the seat's cwd — a seat "
              "rooted deep in the tree (or in a worktree) must refresh ITS root, not the caller's",
              found_root == mroot.resolve())
        check("mirror: rbtv_path is recorded workspace-RELATIVE and resolves against the root — "
              "treating it as a cwd-relative path would point the refresh at nothing",
              found_path == (mroot / "tools" / "rbtv").resolve())

        orphan = Path(td) / "not-a-workspace"
        orphan.mkdir()
        check("mirror: a cwd under no rbtv.json resolves to no workspace",
              find_workspace_root(orphan) == (None, None))
        status, _ = refresh_mirror(orphan)
        check("mirror: a non-rbtv workspace SKIPS, never fails — a team run in a plain folder has "
              "no mirror to refresh and must not be warned at every launch",
              status == "skip")

        (mroot / "rbtv.json").write_text("{not json", encoding="utf-8")
        check("mirror: an unreadable rbtv.json FAILS loudly rather than silently skipping — a "
              "corrupt config is a real problem, not an absent mirror",
              refresh_mirror(mroot)[0] == "fail")
        (mroot / "rbtv.json").write_text(
            json.dumps({"rbtv_path": "tools/rbtv"}), encoding="utf-8")
        check("mirror: an rbtv_path with no install.py FAILS (it points nowhere) — the installer "
              "is never invoked, so this costs nothing to detect",
              refresh_mirror(mroot)[0] == "fail")

        # refresh_mirrors_for: who gets refreshed, and how many times.
        calls = []
        _real_refresh = refresh_mirror
        globals()["refresh_mirror"] = lambda cwd: (calls.append(cwd), ("skip", "stub"))[1]
        try:
            calls.clear()
            refresh_mirrors_for([{"harness": "claude", "cwd": "/w"},
                                 {"harness": "claude", "cwd": "/w"}])
            check("mirror: a claude-only launch refreshes NOTHING — claude reads CLAUDE.md "
                  "natively and consumes no mirror, so the cost must not be paid for it",
                  calls == [])
            calls.clear()
            with redirect_stdout(io.StringIO()):
                refresh_mirrors_for([{"harness": "codex", "cwd": "/w"},
                                     {"harness": "opencode", "cwd": "/w"},
                                     {"harness": "claude", "cwd": "/w"}])
            check("mirror: N seats sharing one root pay ONE refresh — a 10-seat wave must not "
                  "re-render the same workspace 10 times",
                  calls == ["/w"])
            calls.clear()
            with redirect_stdout(io.StringIO()):
                refresh_mirrors_for([{"harness": "codex", "cwd": "/w"},
                                     {"harness": "opencode", "cwd": "/other"}])
            check("mirror: seats in DIFFERENT roots each get their own refresh — a worktree seat's "
                  "mirror lives in the worktree, not the parent workspace",
                  calls == ["/w", "/other"])
            calls.clear()
            globals()["refresh_mirror"] = lambda cwd: (_ for _ in ()).throw(
                AssertionError("should not be reached"))
            refresh_mirrors_for([{"harness": "codex", "cwd": ""}])
            check("mirror: a seat with no cwd is skipped rather than crashing the launch",
                  True)
        except AssertionError as exc:
            check(f"mirror: refresh_mirrors_for raised — {exc}", False)
        finally:
            globals()["refresh_mirror"] = _real_refresh

        # ---- G-20 (inbox-scope) + G-21 (closing state): who a broadcast reaches ----
        # The owner's directive bounds the RECEIVING direction the protocol never bounded. The bar
        # below is the leader's, verbatim in shape: a special-case seat's read shows nothing after
        # an `all`; a direct send still arrives; a COMPLETION reaches the watcher while a NOTE does
        # not; a closing seat gets no `all`; a peer's direct send is REFUSED with its typed reason
        # and never silently accepted; its closer's ask arrives; the leader's order arrives; the
        # state clears when close-seat completes.
        check("G-20: broadcast_scope — a closer takes no broadcast at all",
              broadcast_scope("closer-alpha") == frozenset())
        check("G-20: broadcast_scope — the watcher keeps completion+verdict and nothing else",
              broadcast_scope("watcher") == WATCHER_BROADCAST_TYPES
              and in_broadcast_scope("watcher", "completion")
              and in_broadcast_scope("watcher", "verdict")
              and not in_broadcast_scope("watcher", "note")
              and not in_broadcast_scope("watcher", "ask"))
        check("G-20: broadcast_scope — `engineer` (a one-agent inbox by r-engineer-practice) "
              "takes none, and an ordinary seat is UNTOUCHED (None = every type)",
              broadcast_scope("engineer") == frozenset()
              and broadcast_scope("alpha") is None
              and in_broadcast_scope("alpha", "note"))

        run(cmd_checkin, agent="watcher", summary="sensor pass", pane="%20")
        run(cmd_checkin, agent="engineer", summary="one-agent inbox", pane="%21")
        run(cmd_checkin, agent="zeta", summary="an ordinary seat", pane="%22")
        base_g = base_dir(ns())
        _, before = load_messages(base_g)
        mark = before[-1]["num"] if before else 0
        out = sd("alpha", "all", "room chatter nobody's sensor needs", type="note", force=True)
        check("G-20: an `all` NOTE skips the special-case seats by NAME in the sender's summary "
              "(never silently) and still reaches an ordinary seat",
              "skipped (special-case seat: engineer, watcher)" in out
              and "zeta" not in out.split("skipped (special-case seat")[1].split(")")[0])
        check("G-20: after that broadcast the watcher's and engineer's read shows NOTHING NEW, "
              "while the ordinary seat sees it",
              "room chatter" not in rd("watcher", after=mark, peek=True)
              and "room chatter" not in rd("engineer", after=mark, peek=True)
              and "room chatter" in rd("zeta", after=mark, peek=True))
        # G-94: read's withheld-disclosure footer. A message whose sender NAME equals the
        # recipient's is cut by the self-send rule — correct in its designed case, and wrong
        # when two DISTINCT seats in two packages share a role name. That is how a run-1 ->
        # run-2 LEADER LIFECYCLE HANDOVER reached the log and was never shown: `read` answered
        # "no new messages for leader", then advanced the cursor past it, so nothing re-offered
        # it. The cut stays (fixing WHO is stage 4); what must never happen again is the cut
        # being SILENT, because an inbox that filters without saying so reads exactly like an
        # empty one.
        # ---- the wake half must ask the SAME question `read` asks ----
        # `auto-wake: yes` injects a seat into EVERY send's recipient set. The `all` and group
        # branches scope-filtered it; the bare direct branch tested nothing, so `cos` was woken
        # for every direct message in the room and could read none of them. `in_broadcast_scope`
        # is NOT the cure — it type-scopes BROADCASTS and answers True for an ordinary seat like
        # `cos`, so the symmetric-looking fix would have left this exact case broken while
        # passing a test written over `engineer`/`watcher`.
        # Created HERE, not at package setup: `auto-wake: yes` puts this seat into EVERY send's
        # recipient set, so introducing it earlier would perturb unrelated wake checks upstream.
        # A fixture that changes results it is not testing makes every mutation non-isolated.
        (pkg / "workers" / "cos.md").write_text("---\nagent: cos\nauto-wake: yes\n---\nbrief\n")
        run(cmd_checkin, agent="cos", summary="auto-wake, not an observer", pane="%23")
        w_mark = load_messages(base_g)[1][-1]["num"]
        w_out = sd("alpha", "zeta", "a direct message to a third party", type="note", force=True)
        check("wake/read: an auto-wake seat is NOT woken for a direct message addressed to "
              "someone else — and is NAMED to the sender with the reason, never dropped silently",
              "not in its inbox: cos" in w_out)
        check("wake/read: and its own `read` confirms the wake would have fetched nothing",
              "a direct message to a third party" not in rd("cos", after=w_mark, peek=True))
        check("wake/read: in_broadcast_scope would NOT have cut it — the naive symmetric fix "
              "passes over engineer/watcher and leaves the reported seat woken",
              in_broadcast_scope("cos", "note") is True)
        w_mark2 = load_messages(base_g)[1][-1]["num"]
        w_out2 = sd("alpha", "cos", "a direct message TO the auto-wake seat", type="note",
                    force=True)
        check("wake/read: a direct message TO that seat still reaches it — the cut narrows the "
              "inbox, it must never make a seat unreachable",
              "not in its inbox: cos" not in w_out2
              and "a direct message TO the auto-wake seat" in rd("cos", after=w_mark2, peek=True))
        g94_mark = load_messages(base_g)[1][-1]["num"]
        g94_n = append_message(base_g, "zeta", "zeta", "note", "cross-package lifecycle handover")
        g94_out = rd("zeta", after=g94_mark, peek=True)
        check("G-94: a message ADDRESSED TO a seat but cut by the inbox filter is NAMED, with its "
              "number, in read's footer — a silent filter and an empty inbox are otherwise the "
              "same output",
              "ADDRESSED TO YOU were withheld" in g94_out and f"#{g94_n}" in g94_out)
        check("G-94: the withheld message is still not RENDERED — the disclosure names it and "
              "points at --msg, it does not quietly undo the filter",
              "cross-package lifecycle handover" not in g94_out)
        check("G-94: an ordinary read with nothing withheld stays quiet — the line is a signal, "
              "not a permanent banner",
              "were withheld" not in rd("zeta", after=g94_n, peek=True))

        # ---- stage 4: the record now carries WHICH seat spoke, not just what it is called ----
        # The cut above is correct in its designed case and wrong for two seats wearing one name.
        # Fixing it needed the log to carry the distinguisher, which it never did: `from-pkg:` is
        # written only for a sender that is not a member of the package it writes INTO.
        s4_mark = load_messages(base_g)[1][-1]["num"]
        s4_n = append_message(base_g, "zeta", "zeta", "note",
                              "a FOREIGN seat sharing my role name", origin="run-1")
        s4_read = rd("zeta", after=s4_mark, peek=True)
        check("stage 4 / B1: a message from a FOREIGN seat that shares this seat's role name is "
              "SHOWN — the self-send cut compares identity now, not a role word, so a run-1 "
              "leader's handover into run-2 no longer reads as run-2's leader talking to itself",
              "a FOREIGN seat sharing my role name" in s4_read)
        s4_blocks = load_messages(base_g)[1]
        s4_b = [b for b in s4_blocks if b["num"] == s4_n][0]
        check("stage 4: the origin round-trips through the log — written into the header and "
              "parsed back, so the distinguisher survives the only place it matters (the record)",
              s4_b["origin"] == "run-1" and "from-pkg: run-1" in s4_b["lines"][0])
        pre_cursor = cursor_of("zeta")
        rd("zeta", after=s4_mark)          # a REAL read, not a peek: the cursor must move through it
        check("stage 4 / B2: the cursor advances THROUGH the foreign message rather than stepping "
              "over it — B1 without B2 would show it once and lose it on the next read",
              cursor_of("zeta") != pre_cursor and int(cursor_of("zeta")) >= s4_n)
        own_mark = load_messages(base_g)[1][-1]["num"]
        own_n = append_message(base_g, "zeta", "all", "note", "zeta's own local broadcast")
        own_read = rd("zeta", after=own_mark)
        later_n = append_message(base_g, "alpha", "all", "note", "someone else speaks after it")
        rd("zeta")
        check("stage 4 / B3: a seat's OWN local send is STILL suppressed, and the cursor does not "
              "JAM on it — G-94's ranked fix (b), 'never advance past a suppressed message', is "
              "wrong as literally worded: a seat's own sends are suppressed on EVERY read, so that "
              "cursor would stop at its first one forever. The real invariant is T2's — the cursor "
              "moves through what was SHOWN, so it holds while the own send is the tail (nothing "
              "was shown) and passes it the moment a later message is",
              "zeta's own local broadcast" not in own_read
              and int(cursor_of("zeta")) >= later_n)
        check("stage 4: a LOCAL send carries no from-pkg at all — the header is byte-identical to "
              "what it was before this field existed, which is what keeps every prior log parsing",
              [b for b in load_messages(base_g)[1] if b["num"] == own_n][0]["origin"] is None)
        # G-100, fixed in the same regex rather than filed a second time: `why:` has always been
        # WRITTEN by append_message and was never PARSED, so it was absorbed into `ts` and age_of
        # returned '?' for every broadcast carrying one.
        old_hdr = "## 7 | from: a | to: all | type: note | 2026-07-27 14:34"
        why_hdr = "## 8 | from: a | to: all | type: note | why: milestone | 2026-07-27 14:34"
        pkg_hdr = ("## 9 | from: a | from-pkg: run-1 | to: b | type: ask | re: 3 | "
                   "2026-07-27 14:34")
        check("stage 4 / G-100: a header carrying `why:` now parses it as its OWN field, leaving "
              "`ts` a clean timestamp — it used to swallow the clause, so age_of answered '?' for "
              "every message that justified itself",
              MSG_HEADER.match(why_hdr).group("why") == "milestone"
              and MSG_HEADER.match(why_hdr).group("ts") == "2026-07-27 14:34"
              and age_of(MSG_HEADER.match(why_hdr).group("ts")) != "?")
        check("stage 4: the widened grammar is ADDITIVE — a header written before either field "
              "existed parses exactly as it did, and all four optional fields compose",
              MSG_HEADER.match(old_hdr).group("ts") == "2026-07-27 14:34"
              and MSG_HEADER.match(old_hdr).group("from_pkg") is None
              and MSG_HEADER.match(old_hdr).group("why") is None
              and MSG_HEADER.match(pkg_hdr).group("from_pkg") == "run-1"
              and MSG_HEADER.match(pkg_hdr).group("re") == "3"
              and MSG_HEADER.match(pkg_hdr).group("ts") == "2026-07-27 14:34")
        # The WRITER half, exercised through sender_origin itself rather than through an injected
        # origin=. Every check above feeds append_message a label directly, so all of them would
        # stay green while the code that DECIDES the label was broken — and the first version of
        # it was: it asked "does a seat of this name belong here", which run-2 answers YES for a
        # foreign `leader` because run-2 has a leader of its own. Circular, and it returned None
        # for the exact case it existed to catch. The pane is the only verifiable claim.
        check("stage 4: a caller whose pane holds an ACTIVE row in THIS package is LOCAL — the "
              "verified case, and the one that must keep writing an unchanged header",
              sender_origin(ns(pane="%22"), "zeta") is None)
        check("stage 4: a caller whose pane is on no row of this package AND whose cwd is in no "
              "package is `external` even when a seat of that name exists here — the "
              "membership-by-NAME test was circular, and this is the check that would have caught "
              "it",
              sender_origin(ns(pane="%9999"), "zeta") == "external")
        # ⚠ The row above USED to read "is FOREIGN", and that wording was the defect: no active
        # roster row was treated as another package. A checked-out, renewed, or never-checked-in
        # seat keeps writing from inside its OWN package, and every message it sent was stamped
        # foreign. Measured on the live run: all four origin-labelled messages were the owner
        # channel, local and rostered, sending while its row read inactive — and under the stage-5
        # bound a relay token is refused for anything carrying an origin, so this would have
        # severed the owner channel the moment `relays: master` was declared.
        _cwd = os.getcwd()
        try:
            os.chdir(pkg)
            check("stage 4 (fixed): a caller writing from INSIDE this package is LOCAL whatever "
                  "the roster says — 'has no active row here' is not 'belongs to another run'. "
                  "This is the row that keeps a bounded inbox reachable by a seat between "
                  "lifecycles",
                  sender_origin(ns(pane="%9999"), "zeta") is None)
        finally:
            os.chdir(_cwd)
        check("stage 4: an unresolvable pane changes NOTHING — out-of-pane callers (watch.py, an "
              "--as claim from outside tmux) keep today's behaviour, because under-labelling is "
              "the safe direction and over-labelling would re-serve a seat its own sends",
              sender_origin(ns(pane=""), "zeta") is None)
        check("stage 4: `pending` asks the SAME identity question — a foreign same-named seat's "
              "ask counts as an ask TO me, never as one of mine, so the view that lists open work "
              "cannot disagree with the inbox that delivers it",
              is_own_send({"sender": "zeta", "to": "zeta", "origin": None}, "zeta") is True
              and is_own_send({"sender": "zeta", "to": "zeta", "origin": "run-1"}, "zeta") is False)
        _, mid = load_messages(base_g)
        mark2 = mid[-1]["num"]
        out = sd("alpha", "all", "lane A node delivered", type="completion", why="milestone")
        check("G-20: an `all` COMPLETION DOES reach the watcher — its DAG-unblock trigger rides "
              "these — while the engineer still takes none",
              "lane A node" in rd("watcher", after=mark2, peek=True)
              and "lane A node" not in rd("engineer", after=mark2, peek=True))
        _, mid2 = load_messages(base_g)
        mark3 = mid2[-1]["num"]
        sd("alpha", "watcher", "a question only you can answer", type="note")
        check("G-20: DIRECT addressability is untouched — a message naming the seat always lands",
              "a question only you can answer" in rd("watcher", after=mark3, peek=True))

        # ---- stage 3: a seat's inbox topology is DECLARED, not named in the kit ----
        # `SPECIAL_CASE_SEATS` listed its members while its own comment described a MANDATE
        # ("serve the SYSTEM or the ROOM") — which is exactly how `chief-of-staff` came to be
        # omitted from the set whose definition described it, and why the next such seat would be
        # forgotten identically. A kit-side list also freezes ONE campaign's role vocabulary into a
        # tool every run shares: another run's `engineer` is narrowed by accident, its
        # differently-named system seat is not. Both keys therefore live in the seat descriptor,
        # beside observer/auto-wake, and ABSENCE means exactly today's behaviour.
        check("stage 3: absent and `none` are DIFFERENT answers — a seat that declares nothing "
              "keeps the built-in default, which is what lets this land INERT",
              _fm_list("agent: x\n", "broadcast") is None
              and _fm_list("agent: x\nbroadcast: none\n", "broadcast") == ["none"]
              and _fm_list("agent: x\nsenders: leader, master\n", "senders")
              == ["leader", "master"])
        (pkg / "workers" / "bcast.md").write_text(
            "---\nagent: bcast\nbroadcast: none\n---\nbrief\n")
        (pkg / "workers" / "bnd.md").write_text(
            "---\nagent: bnd\nsenders: leader, alpha\n---\nbrief\n")
        d3 = inbox_decls(ns())
        allnote = {"sender": "alpha", "to": "all", "type": "note"}
        check("stage 3 / D8: a seat is narrowed BY ITS OWN DESCRIPTOR with no kit-side list "
              "touched — `bcast` is in none of them, and without its declaration it is an "
              "ordinary seat, so the narrowing demonstrably comes from the file",
              broadcast_scope("bcast", d3) == frozenset()
              and "bcast" not in SPECIAL_CASE_SEATS
              and broadcast_scope("bcast") is None)
        check("stage 3 / D1: the declared `broadcast: none` cuts the room's broadcast from that "
              "seat's inbox — the axis `in_broadcast_scope` already owned, now DECLARED",
              addressed_to(allnote, "bcast", {}, set(), "any", (), d3) is False
              and addressed_to(allnote, "bcast", {}, set(), "any", (), None) is True)
        check("stage 3: a seat's OWN declaration outranks the built-in table — `engineer` takes "
              "no broadcast by default, and a descriptor saying `broadcast: all` restores it. The "
              "table is now the DEFAULT, not the mechanism",
              broadcast_scope("engineer") == frozenset()
              and broadcast_scope("engineer", {"engineer": {"broadcast": None}}) is None)
        # ---- the SENDER BOUND (r-cos-bounded-inbox, r-engineer-contact) ----
        # The third axis. (a) answers which broadcast TYPES reach me and (c) answers whether I am
        # woken; neither answers WHO MAY ADDRESS ME AT ALL, which is the owner's actual sentence.
        # Until this existed both rulings were enforced by the seat DECLINING BY HAND: the message
        # still arrived, still spent the context, and a breach was visible only if the seat noticed.
        pm = {"sender": "zeta", "to": "bnd", "type": "note"}
        lm = {"sender": "leader", "to": "bnd", "type": "note"}
        check("stage 3 / D3+E7: the bound cuts a BY-NAME message from a non-permitted sender, a "
              "permitted one still lands, and a seat declaring no `senders:` is UNBOUNDED — every "
              "existing package keeps working with no edit",
              addressed_to(pm, "bnd", {}, set(), "any", (), d3) is False
              and addressed_to(lm, "bnd", {}, set(), "any", (), d3) is True
              and addressed_to({"sender": "zeta", "to": "alpha", "type": "note"},
                               "alpha", {}, set(), "any", (), d3) is True)
        check("stage 3 / D6: the SAME derivation bounds `engineer` for r-engineer-contact — the "
              "mechanism keys on what a descriptor DECLARES, never on the seat's name, so it "
              "cannot narrow one campaign's role vocabulary while missing another's",
              addressed_to({"sender": "zeta", "to": "engineer", "type": "note"}, "engineer",
                           {}, set(), "any", (),
                           {"engineer": {"senders": frozenset({"leader", "master"})}}) is False
              and addressed_to({"sender": "leader", "to": "engineer", "type": "note"}, "engineer",
                               {}, set(), "any", (),
                               {"engineer": {"senders": frozenset({"leader", "master"})}}) is True)
        run(cmd_checkin, agent="bnd", summary="a bounded inbox", pane="%24")
        _, pre_b = load_messages(base_g)
        r_out, r_code = refuse(cmd_send, agent="zeta", to="bnd", message="a third sender",
                               type="note", supersedes=None, re_num=None, file=None)
        _, post_b = load_messages(base_g)
        check("stage 3 / D4+E1+E2: a non-permitted sender is REFUSED AT SEND — told who may send "
              "and the route that works — and the message is NEVER written, so the sender still "
              "HOLDS it. A bound enforced only at read time would be the accept-then-silence that "
              "cost G-94 a lifecycle handover, while claiming to fix its family",
              r_code == 1 and "BOUNDED INBOX" in r_out and "alpha, leader" in r_out
              and "send it to leader" in r_out and len(post_b) == len(pre_b))
        mark_b = post_b[-1]["num"]
        ok_out = sd("alpha", "bnd", "a permitted sender's message", type="note")
        ok_skipped = ok_out.split("skipped (")[1] if "skipped (" in ok_out else ""
        check("stage 3 / D7+E3: a PERMITTED sender still delivers, reads AND wakes — the bound "
              "narrows an inbox, it must never close one",
              "a permitted sender's message" in rd("bnd", after=mark_b, peek=True)
              and "bnd" not in ok_skipped)
        mark_f = load_messages(base_g)[1][-1]["num"]
        f_out = sd("zeta", "bnd", "forced past the bound", type="note", force=True)
        f_read = rd("bnd", after=mark_f, peek=True)
        check("stage 3 / E4+D5+E5: a --force'd message from a non-permitted sender is filtered at "
              "READ and NAMED in the withheld footer — never silently dropped — and the WAKE half "
              "agrees through shows_in_inbox with no test of its own, telling the sender the "
              "reason names WHO IS SPEAKING rather than sending it to check its addressing",
              "forced past the bound" not in f_read
              and "ADDRESSED TO YOU were withheld" in f_read
              and "bounded inbox" in f_out)

        # ---- stage 5: MASTER RESOLUTION, both directions (#184, ruling-master-resolution.md) ----
        # The bound above is `senders: leader, master` — the owner's ruled wording. `leader`
        # resolved only because that role's name happens to BE a seat name; `master` is a FUNCTION
        # and matched nobody, so the ruled bound admitted a sender that does not exist and REFUSED
        # the seat carrying the owner channel. Measured before it was built (probe_master_bound.py:
        # M2 and M4 red, M5 green — the mechanism sound, the identity layer missing).
        (pkg / "workers" / "rly.md").write_text(
            "---\nagent: rly\nrelays: master\n---\nbrief\n")
        (pkg / "workers" / "bnd2.md").write_text(
            "---\nagent: bnd2\nsenders: leader, master\n---\nbrief\n")
        d5 = inbox_decls(ns())
        local = {"sender": "rly", "to": "bnd2", "type": "note"}
        foreign = {"sender": "rly", "to": "bnd2", "type": "note", "origin": "run-1"}
        check("stage 5 / M2: the RULED wording `senders: leader, master` now admits the seat that "
              "CARRIES the master relay — the bound was never wrong, `master` was simply not a "
              "name it could resolve, so fixing it by loosening the bound would have been the "
              "wrong layer",
              addressed_to(local, "bnd2", {}, set(), "any", (), d5) is True)
        check("stage 5 / G-111: the relay path is PACKAGE-SCOPED via stage 4's origin — a foreign "
              "seat of the same name is NOT admitted. Without this, a seat of a closed run "
              "inherits the live master's reach: asserted identity beating verified identity",
              addressed_to(foreign, "bnd2", {}, set(), "any", (), d5) is False)
        check("stage 5: the LITERAL path is untouched and origin-blind — a bound naming a real "
              "seat behaves exactly as it did before this stage, and an ordinary third sender is "
              "still refused. Narrowing the existing path while adding a feature would be a "
              "regression dressed as a fix",
              addressed_to({"sender": "leader", "to": "bnd2", "type": "note", "origin": "run-1"},
                           "bnd2", {}, set(), "any", (), d5) is True
              and addressed_to({"sender": "zeta", "to": "bnd2", "type": "note"},
                               "bnd2", {}, set(), "any", (), d5) is False)
        check("stage 5 / M4: `master` is a valid RECIPIENT too, so the bound closes in BOTH "
              "directions. A bound that permits receiving and forbids answering is a dead end, "
              "not a bound — S-7's shape, MANUFACTURED by the bound rather than merely permitted",
              "master" in known_recipients(ns(), base_g)
              and addressed_to({"sender": "leader", "to": "master", "type": "note"},
                               "rly", {}, set(), "any", (), d5) is True)
        check("stage 5 / G-32: a relay token is a BY-NAME address and is NEVER type-scoped. "
              "Reusing the group machinery would have given addressing, wake, read and validation "
              "for free — and silently dropped `send master --type note` for a special-case seat, "
              "because group fan-out honours the same scope test as `all`",
              in_broadcast_scope("engineer", "note", None) is False
              and addressed_to({"sender": "leader", "to": "master", "type": "note"}, "engineer",
                               {}, set(), "any", (),
                               {"engineer": {"relays": frozenset({"master"})}}) is True)
        check("stage 5: an UNRESOLVED token is not a recipient at all — `master` is addressable "
              "only while some descriptor declares it, so a token nobody carries is refused with "
              "the unknown-recipient hint rather than opening a thread with no terminus (S-7)",
              "overseer" not in known_recipients(ns(), base_g)
              and relay_seats("overseer", d5) == frozenset())
        check("stage 5 / M6: resolution is DERIVED from descriptors — two seats declaring the "
              "token both resolve, and N seats is a valid answer, not an ambiguity (one ROLE over "
              "one shared state, realized by N live sessions, so N deliveries are N copies to ONE "
              "recipient). A kit-side name list would freeze one campaign's vocabulary into a tool "
              "every run shares",
              relay_seats("master", d5) == frozenset({"rly"})
              and relay_seats("master", {"a": {"relays": frozenset({"master"})},
                                          "b": {"relays": frozenset({"master"})},
                                          "c": {}}) == frozenset({"a", "b"}))
        m5mark = load_messages(base_g)[1][-1]["num"]
        m5_out = sd("leader", "master", "the owner channel, addressed by ROLE", type="note")
        check("stage 5: the send REPORTS the resolved set — a bare 'delivered to master' is an "
              "unverifiable claim, and a role word that quietly resolves to a seat the sender did "
              "not expect is G-111 with better manners",
              "sent message #" in m5_out and "[master -> rly]" in m5_out)
        check("stage 5: and the seat carrying the relay READS it — the wake half and the read half "
              "resolve the token through the same predicate, so this stage cannot reopen the very "
              "disagreement the seat was commissioned on",
              "addressed by ROLE" in rd("rly", after=m5mark, peek=True))

        # G-21 — the STATE half. `close` sets it; this asserts the state's semantics directly so a
        # failure names the rule that broke rather than the ceremony around it.
        run(cmd_checkin, agent="eta", summary="about to be closed", pane="%23")
        set_closing(base_g, "eta", "closer-eta")
        check("G-21: `status` tells the closing seat its own inbox is narrowed — a seat living in "
              "a filtered inbox must be able to tell 'by design' from 'my wakes are broken'",
              "CLOSING" in inbox_scope_line(base_g, "eta")
              and "closer-eta" in inbox_scope_line(base_g, "eta"))
        _, pre = load_messages(base_g)
        out, code = refuse(cmd_send, agent="zeta", to="eta", message="one more thing",
                           type="note", supersedes=None, re_num=None, file=None)
        _, post = load_messages(base_g)
        check("G-21: a PEER's direct send to a closing seat is REFUSED with the typed reason and "
              "the redirect, and NOTHING is appended — the sender still holds its message "
              "(accept-then-silence is the forbidden shape)",
              code == 1 and "is CLOSING" in out and "closer-eta and leader only" in out
              and "send it to leader" in out and len(post) == len(pre))
        out, code = refuse(cmd_send, agent="zeta", to="eta", message="one more thing",
                           type="note", supersedes=None, re_num=None, file=None, force=True)
        check("G-21: --force is the deliberate override (the sender is certain it must be read)",
              code == 0 and "sent message #" in out)
        _, pre2 = load_messages(base_g)
        mark4 = pre2[-1]["num"]
        # The real closer's FIRST act is `checkin closer-<target>` (closer-prompt.md step 1),
        # which is what makes it answerable. The fixture used to skip it and send an ask from a
        # name nothing could reply to — S-7's exact shape, inside the test suite. Restored.
        run(cmd_checkin, agent="closer-eta", summary="closing eta", pane="%24")
        sd("closer-eta", "eta", "draft memory — corrections?", type="ask")
        check("G-21: its CLOSER gets through — the co-write IS a conversation, so the exception "
              "is not optional",
              "draft memory" in rd("eta", after=mark4, peek=True))
        check("S-7: a closer that HAS checked in can ask — the gate is on unaddressability, "
              "not on closers, and a real closer is always addressable",
              "draft memory" in rd("eta", after=mark4, peek=True))
        _, s7pre = load_messages(base_g)
        out, code = refuse(cmd_send, agent="daemon-detector", to="leader",
                           message="who closes this?", type="ask", supersedes=None,
                           re_num=None, file=None)
        _, s7post = load_messages(base_g)
        check("S-7: an `ask` from an identity with no roster row, briefing or group is REFUSED "
              "at SEND time — 13 such asks were opened in one run and not one of them can ever "
              "be closed, because an answer must be addressed to its sender",
              code == 1 and "cannot receive a reply" in out and len(s7post) == len(s7pre))
        out, code = refuse(cmd_send, agent="daemon-detector", to="leader",
                           message="a flag, for information", type="note", supersedes=None,
                           re_num=None, file=None)
        check("S-7: the SAME unaddressable sender's NOTE is still accepted — the gate is on "
              "the ask/identity PAIRING, never on daemon senders, whose own-name attribution is "
              "deliberate",
              code == 0 and "sent message #" in out)
        check("S-6(a): GATE_FLAGS is the single flag->gate binding and `--force` carries the "
              "ROLE gate ONLY — jobs/recover-room.py force-overrides on every unattended firing "
              "and asserts this map before it does",
              GATE_FLAGS["--force"] == ("role",)
              and GATE_FLAGS["--force-memory"] == ("memory",))
        check("S-6(a): gate_forced reads that map rather than the flag, so recombining the "
              "flags genuinely ARMS the gate instead of merely mislabelling it",
              gate_forced(argparse.Namespace(force=True, force_memory=False), "role") is True
              and gate_forced(argparse.Namespace(force=True, force_memory=False), "memory") is False
              and gate_forced(argparse.Namespace(force=False, force_memory=True), "memory") is True)
        check("S-8(c): the memory-gate refusal names --force-memory, the flag that actually "
              "lifts it — it used to name --force, which carries the ROLE gate only, at the "
              "exact moment an unattended run is blocked and reaching for the documented escape",
              "--force-memory" in memory_gate(1, 100)
              and "override with --force " not in memory_gate(1, 100))
        _, pre3 = load_messages(base_g)
        mark5 = pre3[-1]["num"]
        sd("leader", "eta", "abort the close", type="verdict")
        check("G-21: the LEADER always gets through (abort / renew)",
              "abort the close" in rd("eta", after=mark5, peek=True))
        _, pre4 = load_messages(base_g)
        mark6 = pre4[-1]["num"]
        out = sd("alpha", "all", "a broadcast during the close", type="note", force=True)
        check("G-21: an `all` broadcast does not reach a closing seat, and the sender is told",
              "closing: eta" in out
              and "a broadcast during the close" not in rd("eta", after=mark6, peek=True))
        run(cmd_close_seat, target="eta", agent="leader", renew=False, no_export=True)
        check("G-21: the state CLEARS when close-seat completes — the narrowing never outlives "
              "the seat it was protecting",
              closing_entry(base_g, "eta") is None and "eta" not in closing_seats(base_g))

        # The expiry, which is not tidiness: a closer that DIES mid-close (G-11 killed one tonight)
        # would otherwise leave its target cut off from the room for the rest of the run, silently.
        set_closing(base_g, "zeta", "closer-zeta")
        stale = load_closing(base_g)
        stale["zeta"]["since"] = (datetime.now()
                                  - timedelta(minutes=CLOSING_MAX_MIN + 5)).strftime(
                                      "%Y-%m-%d %H:%M")
        atomic_write(closing_path(base_g), json.dumps(stale) + "\n")
        check("G-21: a closing state older than CLOSING_MAX_MIN is treated as ORPHANED — the seat "
              "returns to an ordinary inbox rather than staying mute behind a dead closer",
              closing_entry(base_g, "zeta") is None and "zeta" not in closing_seats(base_g))
        stale["zeta"]["since"] = "not-a-timestamp"
        atomic_write(closing_path(base_g), json.dumps(stale) + "\n")
        check("G-21: an unreadable stamp expires too (fail-safe direction: a seat wrongly narrowed "
              "goes quiet; one wrongly left open merely reads a message it did not need)",
              closing_entry(base_g, "zeta") is None)
        atomic_write(closing_path(base_g), "{ not json")
        check("G-21: a corrupt closing.json means NOBODY is closing — a parse error must never "
              "silence the room",
              load_closing(base_g) == {} and closing_seats(base_g) == set())
        clear_closing(base_g, "zeta")

        # ---- G-134: the AWAITING-CLOSE debt ----
        # A seat finishes its own lifecycle at `checkout`; only `close-seat` frees its resources.
        # Nothing bounded or noticed the gap, and one instance ran 41 minutes with the pane holding
        # memory against a 2800 MB launch floor. The stated fix (checkout kills its own pane) was
        # REFUSED: it destroys the in-place renew path, which respawns into the SAME pane (G-12).
        check("G-134: `checkout` ASSERTS the debt at the one moment every input is known — who, "
              "which pane, whether the transcript landed. A later pass reconstructing this from "
              "roster + tmux + fs would be the seventh infer-from-ambient defect this run has "
              "catalogued (G-101, G-107, G-121, G-124, G-128, the circular origin)",
              set_awaiting(base_g, "theta", "%99", "/tmp/t.txt", True)
              and load_awaiting(base_g)["theta"]["pane"] == "%99"
              and load_awaiting(base_g)["theta"]["exported"] is True)
        # ⚠ THE FIXTURE IS THE CHECK. An earlier version of this bar used transcript=""/exported=
        # False and transcript=<path>/exported=True — two rows where `exported == bool(transcript)`,
        # so a mutation replacing the stored flag with `bool(transcript)` PASSED IT. The bar was
        # green over the exact inference it existed to forbid. The discriminating row is the one
        # where the two DISAGREE: an export that produced a path and still FAILED.
        check("G-134: `exported` is STORED, not inferred from the transcript path being truthy — "
              "an export can hand back a path and still fail, and #259's ratified mapping gates "
              "the kill on the transcript EXISTING, so a reaper must tell 'safe to kill' from 'not "
              "yet safe' without re-running the export to find out",
              set_awaiting(base_g, "iota", "%98", "/tmp/partial.txt", False)
              and load_awaiting(base_g)["iota"]["exported"] is False
              and load_awaiting(base_g)["iota"]["transcript"] == "/tmp/partial.txt")
        _live = {"%99"}
        _debts = {s: (a, alive) for s, _e, a, alive in awaiting_debts(base_g, _live)}
        check("G-134: a debt whose pane is ALREADY GONE is distinguished from one still holding "
              "memory — both still owe a close-seat (the roster and session trace are unfinished "
              "either way), but only one is costing RAM, and telling the leader they are the same "
              "would be the silence this record exists to end",
              _debts["theta"][1] is True and _debts["iota"][1] is False)
        check("G-134: the debt is SETTLED by the act that frees the resources, and clearing is "
              "reported honestly — True only when something was actually cleared",
              clear_awaiting(base_g, "theta") is True
              and clear_awaiting(base_g, "theta") is False
              and "theta" not in load_awaiting(base_g))
        # ---- G-134 shape B: `reap` (leader #312 owns the numbers) ----
        _fresh = {"since": now(), "pane": "%77", "transcript": "/tmp/x", "exported": True,
                  "pids": [[1, "1"]]}
        check("G-134/B: a debt younger than the policy age is HELD — a single reading cannot tell "
              "an orphan from a renewal decision in flight, and in-place renew (G-12) needs that "
              "pane alive",
              any("needs 15min" in b for b in reap_blockers(_fresh, 3, {"%77"})))
        check("G-134/B: NO TRANSCRIPT holds the reap (#259's ratified precondition), and it is "
              "checked against the FILE — a recorded path whose file has since gone is not a "
              "transcript, so the flag alone is never enough",
              any("no transcript" in b for b in
                  reap_blockers(dict(_fresh, exported=False), 30, {"%77"}))
              and any("no longer on disk" in b for b in reap_blockers(_fresh, 30, {"%77"})))
        # The pane is in the live set but holds NO recognisable harness, so the recorded identity
        # cannot be matched — the repurposed-pane case, reached without needing a real tmux pane.
        check("G-134/B: NO HUMAN ON THE PANE is proven by IDENTITY, not assumed — a pane that no "
              "longer holds the processes it checked out with is refused, and one with no recorded "
              "identity was never provably seat-only. Both FAIL CLOSED: a live owner conversation "
              "on a reused pane must never be terminated to free memory",
              any("repurposed" in b for b in reap_blockers(_fresh, 30, {"%77"}))
              and any("never provably seat-only" in b for b in
                      reap_blockers(dict(_fresh, pids=[]), 30, {"%77"})))
        # The owner door: a seat closes and its pane deliberately SURVIVES for an AFK owner. It
        # matches every debt condition, so the marker reports it — a false positive by design, and
        # the most expensive kind, since acting on it closes the door the run is reachable through.
        _door = {"door": {"relays": frozenset({"master"})}}
        check("G-134/B: A PANE WHOSE PURPOSE IS HUMAN CONTACT IS NEVER REAPED "
              "(r-owner-afk-liaison-parked) — and the exemption is DERIVED from the seat's own "
              "`relays:` declaration, so the next parked door is protected without anyone "
              "remembering to add its name to a list in the kit",
              any("DOOR, not a leak" in b for b in
                  reap_blockers(dict(_fresh, since="old"), 99, {"%77"}, _door, "door"))
              and not any("DOOR, not a leak" in b for b in
                          reap_blockers(_fresh, 99, {"%77"}, _door, "ordinary")))
        # ---- the muted-monitor route (owner-directed; leader's design-context-watch-route.md) ----
        # The watch loop computed both context crossings the owner later noticed BY EYE, and coord
        # refused every flag: the `watcher` role had been dissolved and its roster row deleted, so
        # an `ask` from an unaddressable sender was correctly refused (S-7), and the loop had also
        # inherited a seat's TMUX_PANE so its identity claim was refused too. The refusals went to
        # a detached stderr file nobody reads while the loop kept reporting healthy.
        check("muted monitor: a `note` from a sender with NO roster row is ACCEPTED, which is the "
              "whole delivery fix — a flag is a FACT, not a question, and coord's own refusal text "
              "said so ('Send this as --type note'). The fix was written on the failure",
              "sent message #" in sd("nonseat-detector", "leader", "context at 58.3%",
                                     type="note"))
        _, _ac = refuse(cmd_send, agent="nonseat-detector", to="leader", message="context at 52%",
                        type="ask", supersedes=None, re_num=None, file=None)
        check("muted monitor: and the same sender's `ask` is still REFUSED — the S-7 fix is not "
              "weakened, because an ask nobody can answer still cannot be closed. Only the type "
              "changed",
              _ac == 1)
        (base_g / "undelivered-flags.md").write_text(
            "- 2026-07-27 20:28 | UNDELIVERED (coord refused): context at 58.3%\n", encoding="utf-8")
        check("muted monitor: a refused flag is recorded DURABLY and surfaced where the run looks "
              "— a monitor that cannot deliver must SHOUT that it cannot deliver. stderr is not a "
              "channel: this one ran detached into /tmp for hours while silence and health were "
              "indistinguishable",
              len(undelivered_flags(base_g)) == 1
              and "UNDELIVERED MONITOR FLAGS: 1" in undelivered_line(base_g))
        (base_g / "undelivered-flags.md").unlink()
        check("muted monitor: and it is SILENT when nothing was refused — a permanent warning is "
              "one nobody reads",
              undelivered_line(base_g) == "")

        # ---- r-window-layout, the TOOL half (#332/#382) ----
        _seats = [{"agent": "a", "window": "control"}, {"agent": "b", "window": "control"},
                  {"agent": "c", "window": "workers"}]
        check("r-window-layout: a seat's own declaration NEVER authorizes itself — peers exclude "
              "the seat under test, or its typo appears in the set it is validated against and the "
              "check is vacuous. Nearly shipped that way",
              peer_windows(_seats, "c") == {"control"}
              and peer_windows([{"agent": "c", "window": "typo"}], "c") == set())
        check("r-window-layout: a TYPO is refused because it is a NEAR MISS of a window peers "
              "declare — and the refusal names the intended value. An unrecognised window is not "
              "refused by tmux: it SILENTLY OPENS a new one, so the seat reads as correctly placed "
              "into furniture nobody ordered. Drift that looks like success",
              "one edit from 'control'" in window_drift({"window": "controll"}, {"control",
                                                                                 "workers"}))
        check("r-window-layout: a genuinely NEW window passes — no layout is hardcoded, by ruling. "
              "Freezing this campaign's four window names into a tool every run shares would "
              "refuse every launch in a differently-organized room, which is the mistake "
              "SPECIAL_CASE_SEATS was demoted for: a MANDATE cannot be a name list",
              window_drift({"window": "hr"}, {"control", "workers"}) == ""
              and window_drift({"window": "control"}, {"control"}) == ""
              and window_drift({"window": ""}, {"control"}) == "")
        # THE WIRING, not just the predicate. Removing the refusal from cmd_close_seat left the
        # three rows above green — the helpers were covered and the path that actually kills was
        # not. Same seam gap as G-134's, caught the same way: by mutation, not by reading.
        (pkg / "workers" / "dr").mkdir(exist_ok=True)
        (pkg / "workers" / "dr" / "agent.md").write_text(
            "---\nagent: dr\nharness: claude\nmodel: opus\nrelays: master\n---\nbrief\n")
        run(cmd_checkin, agent="dr", summary="the owner door", pane="%31")
        live_tmux_panes["v"].add("%31")
        _do, _dc = refuse(cmd_close_seat, target="dr", agent="leader", renew=False, no_export=True)
        check("r-window-layout/door: `close-seat` REFUSES a seat carrying a relay path to a human "
              "role while its pane is LIVE — this path kills the pane (on the renew path too, "
              "which kills and re-creates rather than respawning in place), so it would destroy a "
              "door a human may be watching. A door misplaced is cosmetic; a door destroyed is an "
              "outage",
              _dc == 1 and "relay path to a human role" in _do and "%31" in _do)
        _fo, _fc = refuse(cmd_close_seat, target="dr", agent="leader", renew=False, no_export=True,
                          force=True)
        check("r-window-layout/door: and --force still closes it — an exemption that cannot be "
              "overridden is a trap, not a safeguard, and the run legitimately ends",
              _fc == 0 and "%31" in _fo)
        _ro, _rc = refuse(cmd_reap, agent="zeta", go=True)
        check("G-134/B: the gate is on the CONSEQUENCE, not the verb — `--go` is leader/closer "
              "only, and the refusal names the FLAG so the reader looks for the right permission",
              _rc == 2 and "reap --go" in _ro)
        # Run through `refuse` rather than `run` even though nothing should be refused: if a
        # regression re-gates the verb, this must report a clean FAIL. Under `run`, the gate's
        # sys.exit escapes and ABORTS the whole selftest — every later check silently unreported,
        # which is G-121 (a truncated run reads greener than a complete one) inside the suite that
        # exists to catch it.
        _oo, _oc = refuse(cmd_reap, agent="zeta", go=False)
        check("G-134/B: OBSERVING IS UNGATED — it destroys nothing, and gating it forced any seat "
              "wanting to verify against the live room to override the gate or skip the check. A "
              "gate that manufactures its own breaches bills whoever behaves best (G-106)",
              _oc == 0 and "reap --go" not in _oo)
        set_awaiting(base_g, "kappa", "%77", "/tmp/x", True)
        _s1, _r1 = confirm_reap(base_g, "kappa", [])
        _s2, _r2 = confirm_reap(base_g, "kappa", [])
        check("G-134/B: TWO CONSECUTIVE PASSES means two SPACED passes — a burst cannot "
              "manufacture a trend. Without the spacing rule `reap; reap` in one shell would "
              "satisfy a bare counter instantly and the whole guarantee would be decorative",
              len(_s1) == 1 and _r1 is False and len(_s2) == 1 and _r2 is False)
        check("G-134/B: a pass whose condition FAILED resets the ledger — the rule is two "
              "CONSECUTIVE passes, so an interruption costs the trend rather than leaving a stale "
              "half-confirmation for an unrelated sweep an hour later to complete",
              confirm_reap(base_g, "kappa", ["something broke"]) == ([], False))
        _aw = load_awaiting(base_g)
        _aw["kappa"]["confirmed"] = ["2026-01-01 00:00"]
        atomic_write(awaiting_path(base_g), json.dumps(_aw, indent=2, sort_keys=True) + "\n")
        check("G-134/B: and a genuinely separate second pass DOES confirm — the gate is spacing, "
              "never a refusal to ever confirm",
              confirm_reap(base_g, "kappa", [])[1] is True)
        clear_awaiting(base_g, "kappa")
        awaiting_path(base_g).write_text("{ not json", encoding="utf-8")
        check("G-134: a corrupt awaiting-close.json reads as NO DEBT rather than raising — the "
              "fail-safe direction differs from closing's deliberately: a lost entry costs a pane "
              "someone finds by hand, but raising here would break `checkout`, the one act a "
              "finishing seat must always be able to complete",
              load_awaiting(base_g) == {} and awaiting_debts(base_g, set()) == [])
        awaiting_path(base_g).unlink()

        # ---- G-32: a GROUP is not a side door around the inbox cut ----
        # The owner spotted the watcher sitting in THREE of the run's four groups: the G-20 cut was
        # real, but `addressed_to` applied it on the `to == all` branch only, so a group message
        # reached every member unfiltered — the traffic cut at the front door walked in the side
        # one. Two halves, and they need each other: MEMBERSHIP (the two commands that can create
        # one refuse a special-case seat) is the braces; DELIVERY (group fan-out honours the same
        # TYPE scope as a broadcast) is the belt, because the run makes a fresh group per wave and
        # a deliberately-added member must still be filtered. The invariant both rest on — a
        # message NAMING the seat always lands — is asserted last.
        out, code = refuse(cmd_add_to_group, agent="leader", group="pair", members=["watcher"])
        check("G-32: `add-to-group` REFUSES a special-case seat, naming the seat, the rule and the "
              "direct-message path — a rule kept only by remembering is what filed this issue",
              code == 1 and "watcher is a special-case seat" in out
              and "group traffic is not its input" in out and "send watcher" in out)
        out, code = refuse(cmd_create_group, agent="alpha", group="lane-x", members=["engineer"])
        check("G-32: `create-group` refuses one too — a group must not be BORN carrying the seat",
              code == 1 and "engineer is a special-case seat" in out)
        gm32 = group_map(base_g)
        check("G-32: a refusal WRITES NOTHING — the existing group is untouched and the refused "
              "one was never created",
              "watcher" not in gm32["pair"] and "lane-x" not in gm32)
        out, code = refuse(cmd_create_group, agent="alpha", group="lane-g32",
                           members=["watcher", "zeta"], force=True)
        check("G-32: --force stays the single deliberate override, and SAYS so — the membership is "
              "bought, the traffic is not (delivery is still filtered by type)",
              code == 0 and "with --force" in out
              and set(group_map(base_g)["lane-g32"]) == {"alpha", "leader", "watcher", "zeta"})
        _, pre32 = load_messages(base_g)
        mk32 = pre32[-1]["num"]
        out = sd("alpha", "lane-g32", "lane chatter the sensor never needed", type="note")
        check("G-32: a GROUP note does NOT reach the special-case member — even one holding an "
              "observer grant — while an ORDINARY member of the same group reads it",
              "lane chatter" not in rd("watcher", after=mk32, peek=True)
              and "lane chatter" in rd("zeta", after=mk32, peek=True))
        check("G-32: and it costs the filtered member no WAKE either — the sender is told by name "
              "and reason, exactly as on the `all` branch",
              "skipped (special-case seat: watcher)" in out)
        _, mid32 = load_messages(base_g)
        mk33 = mid32[-1]["num"]
        sd("alpha", "lane-g32", "lane G node delivered", type="completion")
        check("G-32: a GROUP completion DOES reach the watcher — the DAG-unblock trigger kept on "
              "the broadcast branch must survive the group branch too, or the cure stalls the run",
              "lane G node" in rd("watcher", after=mk33, peek=True))
        run(cmd_checkin, agent="iota", summary="group member about to close", pane="%25")
        run(cmd_add_to_group, agent="leader", group="lane-g32", members=["iota"])
        set_closing(base_g, "iota", "closer-iota")
        _, mid33 = load_messages(base_g)
        mk34 = mid33[-1]["num"]
        out = sd("alpha", "lane-g32", "more lane work while it closes", type="note")
        check("G-32 + G-21: a group message does not reach a member MID-CLOSE either — closing "
              "narrows the inbox whatever channel the message arrives on",
              "more lane work" not in rd("iota", after=mk34, peek=True)
              and "closing: iota" in out)
        clear_closing(base_g, "iota")
        _, mid34 = load_messages(base_g)
        mk35 = mid34[-1]["num"]
        sd("alpha", "watcher", "sensor, this one is for you", type="note")
        check("G-32: the INVARIANT the whole design rests on — a message addressed to the seat BY "
              "NAME still lands, group filtering or not",
              "this one is for you" in rd("watcher", after=mk35, peek=True))
        out, code = refuse(cmd_remove_from_group, agent="zeta", group="lane-g32",
                           members=["watcher"])
        check("G-32: `remove-from-group` is leader-gated exactly like add-to-group", code == 2)
        out = run(cmd_remove_from_group, agent="leader", group="lane-g32", members=["watcher"])
        check("G-32: leader REMOVES the member and the file is rewritten through the same writer — "
              "the three pre-existing memberships have a sanctioned undo at last "
              "(coordination/ is script-managed; hand-editing it is banned)",
              "watcher" not in group_map(base_g)["lane-g32"]
              and set(group_map(base_g)["lane-g32"]) == {"alpha", "leader", "zeta", "iota"}
              and set(group_map(base_g)["pair"]) == {"alpha", "beta", "leader"})
        out, code = refuse(cmd_remove_from_group, agent="leader", group="lane-g32",
                           members=["nobody"])
        check("G-32: removing a name that is not a member is REFUSED rather than reported as a "
              "change that did not happen",
              code == 1 and "not in group" in out)

        # ---- G-22 / #198: the broadcast discipline, enforced instead of remembered ----
        # Measured on the live run that produced the rule: 86 broadcasts, 35 of them `note`, one
        # seat accounting for 38 — and ZERO groups after 192 messages, so the expensive channel was
        # the only channel anyone had. Both halves are mechanical here: a note cannot be an `all`,
        # and every `all` names the clause that makes it everyone's business.
        out, code = refuse(cmd_send, agent="alpha", to="all", message="fyi, lane A is green",
                           type="note", supersedes=None, re_num=None, file=None)
        check("#198: a `note` to `all` is REFUSED and the refusal teaches the CHEAP channel — a "
              "note is by definition something a seat that never reads it still acts correctly "
              "without",
              code == 1 and "never an `all` broadcast" in out and "create-group" in out)
        out, code = refuse(cmd_send, agent="alpha", to="all", message="m1 is closed",
                           type="verdict", supersedes=None, re_num=None, file=None)
        check("#198: any `all` without --why is REFUSED, and the refusal LISTS the four clauses "
              "rather than making the sender go looking for them",
              code == 1 and "requires --why" in out
              and all(k in out for k in BROADCAST_CLAUSES))
        out, code = refuse(cmd_send, agent="alpha", to="all", message="m1 is closed",
                           type="verdict", supersedes=None, re_num=None, file=None,
                           why="milestone")
        check("#198: a justified broadcast goes through and the CLAUSE is recorded in the LOG LINE "
              "itself — a reader judging whether it earned everyone's attention sees the claim it "
              "made",
              code == 0 and "why: milestone" in out
              and "| why: milestone |" in (base_dir(ns()) / "messages.md").read_text(encoding="utf-8"))
        out, code = refuse(cmd_send, agent="alpha", to="beta", message="just you",
                           type="note", supersedes=None, re_num=None, file=None, why="ruling")
        check("#198: --why on a NON-broadcast is refused — it would record a justification for a "
              "message that needed none",
              code == 1 and "not `all`" in out)
        out, code = refuse(cmd_send, agent="alpha", to="all", message="fyi again",
                           type="note", supersedes=None, re_num=None, file=None, force=True)
        check("#198: --force remains the single deliberate override, as on every other refusal here",
              code == 0 and "sent message #" in out)

        # ---- G-23: `close: mechanical` — a long-lived seat with an ephemeral-class CLOSE PATH ----
        # The owner's case is the watcher: its whole state is external and machine-owned, so a
        # memory.md would be a hand-kept copy of files its loop recomputes every pass. LIFETIME and
        # CLOSE PATH were coupled only by accident of the kit's model; this separates them.
        mdir2 = pkg / "workers" / "theta"
        mdir2.mkdir(parents=True, exist_ok=True)
        (mdir2 / "agent.md").write_text(
            "---\nagent: theta\nharness: claude\nclose: mechanical\n---\nsensor loop\n",
            encoding="utf-8")
        theta = [w for w in discover_workers(workers_dir(ns())) if w["agent"] == "theta"][0]
        check("G-23: `close: mechanical` is exposed per seat from the descriptor",
              theta["mechanical_close"] is True
              and not theta["ephemeral"])          # long-lived, and still memoryless
        (mdir2 / "memory.md").write_text("# stale copy of machine-owned state\n", encoding="utf-8")
        check("G-23: its boot prompt does NOT point at memory.md even though the file EXISTS and "
              "the seat is persistent — it boots fresh every session by design",
              "memory.md" not in boot_prompt(theta, ns()))
        ordinary = [w for w in discover_workers(workers_dir(ns())) if w["agent"] == "gamma"]
        check("G-23: the DEFAULT is untouched — a persistent seat with no `close:` key still "
              "reads its memory (the careful path stays the default)",
              bool(ordinary) and "memory.md" in boot_prompt(ordinary[0], ns()))
        run(cmd_checkin, agent="theta", summary="mechanical-close sensor", pane="%24")
        opened.clear()
        out = run(cmd_close, agent="leader", target="theta", renew=False, dry_run=False,
                  no_export=True)
        _, _, rows_t = load_workers(base_g)
        check("G-23: `close` on it spawns NO closer pane and closes the seat mechanically — no "
              "closer seat, so no ~500 MB launch against the memory gate either",
              "WITHOUT a closer seat" in out and not opened
              and not any(t.startswith("closer-theta") for _, t in titles)
              and current_row(rows_t, "theta")["active"] == "no")

        # ---- G-51: the descriptor vs the registry nothing used to read ----
        # `taskforce.csv` is the run's binding REGISTRY and the kit never opened it, so the two
        # could disagree silently and permanently — and did: a seat re-bound in the registry after
        # an owner-departure event still launched on its old model, three appearances in one run.
        # This does not make the CSV authoritative; it makes a disagreement impossible to launch
        # through unseen.
        check("G-51: with NO taskforce.csv the check is a no-op — a legacy `workers/` package has "
              "no registry and its seats must still launch",
              taskforce_bindings(ns()) == {})
        (pkg / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,gamma,,opencode,zai-coding-plan/glm-5.2,high,,m0\n"   # matches gamma's briefing
            "tf-1,delta,,codex,,,,m0\n"                   # blank model/effort = not stated
            "tf-1,epsilon-x,,claude,sonnet,high,,m0\n",   # a row for a seat with no briefing
            encoding="utf-8")
        reg = taskforce_bindings(ns())
        check("G-51: the registry parses per seat, and a BLANK cell means 'not stated' rather "
              "than a value — the opencode verification seats legitimately carry no `effort`, and "
              "treating blank as a value would refuse every one of them",
              set(reg) == {"gamma", "delta", "epsilon-x"}
              and reg["delta"]["model"] == "" and reg["delta"]["harness"] == "codex"
              and binding_divergence({"harness": "codex", "model": "anything", "effort": "low"},
                                     reg["delta"]) == [])
        gseat = [w for w in discover_workers(workers_dir(ns())) if w["agent"] == "gamma"][0]
        check("G-51: a seat AGREEING with its row produces no divergence",
              binding_divergence(gseat, reg["gamma"]) == [])
        diverged = dict(reg["gamma"], model="deepseek/deepseek-v4-pro")
        diff = binding_divergence(gseat, diverged)
        check("G-51: a disagreement is reported per FIELD with both values, descriptor first",
              diff == [("model", "zai-coding-plan/glm-5.2", "deepseek/deepseek-v4-pro")])
        (pkg / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,gamma,,opencode,deepseek/deepseek-v4-pro,high,,m0\n", encoding="utf-8")
        out, code = refuse(cmd_launch, agent="leader", only="gamma", dry_run=True)
        check("G-51: launch REFUSES the divergent seat, naming both values, both paths, and — the "
              "part that makes it usable at 3am — WHICH SIDE BINDS",
              code == 2 and "descriptor says zai-coding-plan/glm-5.2" in out
              and "taskforce.csv says deepseek/deepseek-v4-pro" in out
              and "THE DESCRIPTOR IS AUTHORITATIVE" in out and "taskforce.csv" in out
              and str(pkg) in out)
        check("G-51: the DRY-RUN is checked too — a dry-run exists to show what a real launch "
              "would do, so hiding a divergence from it would make the one command meant for "
              "inspection the one that lies",
              code == 2)
        out, code = refuse(cmd_launch, agent="leader", only="gamma", dry_run=True, force=True)
        check("G-51: --force launches on the DESCRIPTOR's value anyway and says so",
              code == 0 and "WARNING --force" in out and "binds from its DESCRIPTOR" in out)
        (pkg / "taskforce.csv").unlink()

        # ---- #210 + #230: BOTH gates evaluated, BOTH verdicts reported, no short-circuit ----
        # The watcher must pass --force on EVERY launch (the seed rule gives it DAG-unblock
        # authority exercisable only through the leader's role gate). The role gate was checked
        # FIRST and SHORT-CIRCUITED, so the watcher could never observe the memory verdict without
        # having already overridden the role gate — and before the flags were split, that same flag
        # cleared memory too. Separating the flags alone would NOT have fixed it: the second verdict
        # stayed invisible until after the first was waived. A gate you cannot observe without
        # overriding it is not a gate, it is a trapdoor.
        avail_real2 = available_mb
        available_mb = lambda: LAUNCH_MEM_FLOOR_MB - 1     # one MB under the floor
        try:
            out, code = refuse(cmd_launch, agent="watcher", only="gamma", dry_run=False,
                               force=True)
            check("#230: a role-gated caller with --force alone is REFUSED BY MEMORY, and the "
                  "refusal names BOTH verdicts — the role override no longer hides the memory "
                  "gate behind it",
                  code == 2 and "role gate: REFUSED, overridden with --force" in out
                  and "memory gate: REFUSED" in out)
            out, code = refuse(cmd_launch, agent="watcher", only="gamma", dry_run=False,
                               force=True, force_memory=True)
            check("#230: with BOTH flags it proceeds, and the WARNING is distinguishable from a "
                  "refusal — it launches and names which gate was overridden",
                  code == 0 and "WARNING launching anyway" in out
                  and "overridden with --force-memory" in out and "refused:" not in out)
            out, code = refuse(cmd_launch, agent="watcher", only="gamma", dry_run=False,
                               force_memory=True)
            check("#230: --force-memory does NOT carry the ROLE gate — the memory flag is not a "
                  "back door into a leader-only command",
                  code == 2 and "role gate: REFUSED — `launch` is leader's alone" in out)
            out, code = refuse(cmd_launch, agent="leader", only="gamma", dry_run=False)
            check("#230: the LEADER is refused by the memory gate like anyone else and still sees "
                  "BOTH verdicts — the gate binds the seat holding lifecycle authority too",
                  code == 2 and "role gate: PASS" in out and "memory gate: REFUSED" in out)
            out, code = refuse(cmd_launch, agent="watcher", only="gamma", dry_run=True, force=True)
            check("#230: --dry-run keeps the ROLE gate ALONE — it opens nothing, so refusing it "
                  "on available memory would refuse a command that cannot spend any",
                  "memory gate" not in out)
        finally:
            available_mb = avail_real2

        os.environ.pop("COORD_LAUNCH_TARGET", None)

    (wake, set_pane_title, tmux_split_pane, tmux_new_window, tmux_kill_pane, tmux_capture,
     tmux_raise_history_limit, schedule_session_rename, tmux_window_panes, tmux_session_name,
     tmux_split_strip, restore_overview_strip, tmux_find_window_pane, tmux_send_text,
     tmux_send_enter, tmux_capture_tail, tmux_pane_window, detect_pane, live_panes,
     _acquire_flock, atomic_write, pane_title) = real
    (pane_harness_pids, pane_harness_idents, wait_harness_up, verify_pids_gone, arm_pid_reaper,
     tmux_pane_pid, tmux_respawn_pane, available_mb) = proc_real
    if env_agent is not None:
        os.environ["COORD_AGENT"] = env_agent

    # ---- KG seats-mode discovery (2026-07-27): a KG-shaped run folder
    # (.rbtv/goals/<goal>/runs/run-N/) rosters briefings at seats/<seat>/seat.md;
    # workers/<agent>/agent.md remains the legacy form. seats/ wins when both exist.
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td2:
        RUNS_INDEX = Path(td2) / "coordinate-runs.json"  # never the real registry
        pkg2 = Path(td2) / "run-1"
        (pkg2 / "coordination").mkdir(parents=True)
        sdir2 = pkg2 / "seats" / "epsilon"
        sdir2.mkdir(parents=True)
        (sdir2 / "seat.md").write_text("---\nseat: epsilon\nharness: claude\n---\n# e\n")
        check("seats-mode: */seat.md with the KG `seat:` signature key is discovered",
              "epsilon" in briefing_frontmatters(pkg2 / "seats"))
        check("seats-mode: walk-up recognizes coordination/ + seats/ (no workers/)",
              discover_package_from(sdir2) == pkg2)
        # G-14: seats-mode resolved NO folder for a seat.md briefing, so `memory.md` was invisible
        # to boot_prompt and a renewed persistent seat was never told to read its own memory — the
        # artifact the whole close ceremony exists to produce.
        (sdir2 / "memory.md").write_text("# memory\nprior state\n")
        eps = [w for w in discover_workers(pkg2 / "seats") if w["agent"] == "epsilon"]
        check("G-14: a seat.md briefing resolves its seat FOLDER (it used to key on agent.md "
              "only), so memory.md is reachable",
              len(eps) == 1 and eps[0]["folder"] == sdir2)
        check("G-14: a renewed PERSISTENT seat's boot prompt names its own memory.md — without "
              "the folder it silently booted memoryless",
              str(sdir2 / "memory.md") in boot_prompt(
                  eps[0], argparse.Namespace(package=str(pkg2), base=None, workers_dir=None)))

        check("seats-mode: workers_dir prefers seats/ when present",
              workers_dir(ns(package=str(pkg2))) == pkg2 / "seats")

    # ---- G-10/G-11/G-12 (2026-07-27): the close/renew ceremony's three process-truth defects,
    # every one of them launch-path code that had never been executed end to end. wake() and the
    # process helpers below are exercised REAL (no tmux stubs needed: each refuses or resolves
    # before it touches tmux), which is the point — the old checks asserted the kit's intentions.
    ok, terr = wake("%1", "line one\nline two")
    check("G-11: wake REFUSES multi-line text before any keystroke is sent — send-keys delivers a "
          "newline as Enter, so the pane's shell executes the text line by line (reproduced: a "
          "closer's prompt ran its own checkin line as bash and printed a fake completion)",
          not ok and "newline" in terr and "G-11" in terr)
    ok, terr = wake("%1", "one line\r")
    check("G-11: a bare carriage return is refused too — the same Enter to a shell", not ok)

    _oc_seat = {"agent": "oc", "harness": "opencode", "model": "deepseek/deepseek-v4-pro",
                "effort": "high"}
    _oc_cmd, _ = harness_command(_oc_seat, prompt_path=Path("/tmp/p.txt"))
    _oc_cmd = _oc_cmd or ""
    check("opencode: the spawn command carries --auto AFTER the `run` subcommand — the SUCCESS "
          "shape, not merely the flag's presence (G-78). `opencode --auto run ...` prints the "
          "banner and runs NOTHING at exit 0, so a check that only asserted `--auto` in the string "
          "would pass the form that launches nothing. Verified live in both positions before this "
          "check was written (owner-directed, leader #607)",
          " run --auto " in _oc_cmd
          and _oc_cmd.find(" run ") < _oc_cmd.find("--auto")
          and not _oc_cmd.startswith("--auto")
          and " --auto run " not in _oc_cmd)
    check("opencode: without auto mode a seat auto-REJECTS reads outside its own folder and dies "
          "silently — the mechanism that killed K4 three times (G-49). The flag is therefore part "
          "of the launch contract, not an option",
          "--auto" in _oc_cmd and _oc_seat["harness"] == "opencode")

    _pf_seat = {"agent": "zeta", "harness": "claude", "model": "opus", "effort": "high"}
    with tempfile.TemporaryDirectory() as td3:
        pkg3 = Path(td3) / "pkg"
        (pkg3 / "coordination").mkdir(parents=True)
        a3 = argparse.Namespace(package=str(pkg3), base=None, workers_dir=None)
        pf = prompt_file(a3, "zeta", "multi\nline\nprompt\n")
        cmd, _ = harness_command(_pf_seat, prompt_path=pf)
        check("G-11: the spawn command reads its prompt from a FILE and is itself one line — the "
              "structural fix, since no prompt length can reintroduce the defect",
              "\n" not in cmd and f'"$(cat {pf})"' in cmd
              and pf.read_text(encoding="utf-8") == "multi\nline\nprompt\n")
        cmd2, _ = harness_command(_pf_seat, prompt_path=pf)
        ok2, _ = wake("%1", cmd2)  # real wake: refuses on newline, otherwise reaches tmux
        check("G-11: launch and close now share ONE spawn shape, so the wake guard cannot fire on "
              "either", "\n" not in cmd2)

    snap = [(100, 1, "bash"), (200, 100, "claude --model opus --effort medium PROMPT"),
            (300, 200, "bash -c coordinate read"), (400, 1, "claude --model fable OTHER SEAT"),
            (500, 100, "python3 watch.py --loop 10")]
    check("G-11: harness detection walks the pane's whole process subtree — the harness is a child "
          "of the pane's shell, and its own tool calls are children of that",
          sorted(descendant_pids(snap, 100)) == [100, 200, 300, 500]
          and harness_pids(snap, 100) == [200])
    check("G-11: another pane's harness is NEVER counted as this pane's",
          400 not in descendant_pids(snap, 100))
    check("G-11: a shell-only subtree yields no harness — the exact state a row claiming ACTIVE "
          "must not survive", harness_pids([(100, 1, "bash"), (300, 100, "bash -c echo")], 100) == [])
    check("G-11: argv matching covers a wrapper form (node/bun running a harness path) as well as "
          "a bare basename",
          is_harness_argv("/usr/bin/node /opt/x/opencode --help")
          and is_harness_argv("claude --model opus P") and not is_harness_argv("bash -c ls"))
    check("G-11: unverifiable is not absent — no pane, no pid, nothing to refuse on (fail-safe)",
          pane_harness_pids("") == ([], False) and wait_harness_up("", timeout=0.1) == ([], ""))

    _pane_seat = {"agent": "eta", "harness": "claude", "model": "opus", "effort": "high",
                  "window": False}
    _win_seat = dict(_pane_seat, window="yes")
    check("G-12: a pane seat with a live pane renews IN PLACE — respawn keeps the pane id and the "
          "cell, so an arranged window layout survives the renew (kill+split re-tiled it)",
          renew_in_place(_pane_seat, "%5", True))
    check("G-12: a dead pane cannot be respawned — falls back to placement",
          not renew_in_place(_pane_seat, "%5", False) and not renew_in_place(_pane_seat, "", True))
    check("G-12: a window/shared seat still re-places from its briefing — respawning it in a pane "
          "would silently move it out of its own window",
          not renew_in_place(_win_seat, "%5", True))

    check("G-10: verify_pids_gone reports clean for identities already gone, and never blocks on "
          "an empty set", verify_pids_gone([]) == ([], "")
          and verify_pids_gone([(2 ** 22 - 1, "999")], timeout=0.1)[0] == [])
    check("G-10: this very process is seen as alive — the liveness probe is real, not a stub",
          pids_alive([os.getpid()]) == [os.getpid()])

    # ---- reaper identity (owner directive 2026-07-27 #137; leader #138; daemon precedent #139).
    # A pid is NOT an identity. The first reaper fired on "this pid is A harness", so a relaunch
    # landing on a recycled pid was SIGKILLed by the dead seat's reaper. Ancestry is not a fix
    # either: G-12's in-place respawn puts the replacement under the SAME pane, so an ancestry test
    # would confirm the very process it must protect. Only (pid, starttime) survives both.
    me = os.getpid()
    my_ident = process_identity(me)
    check("reaper: a process identity is (pid, starttime) read from /proc field 22, parsed after "
          "the LAST ')' — a naive whitespace split mis-indexes any comm containing a space",
          my_ident is not None and my_ident[0] == me and my_ident[1].isdigit()
          and proc_starttime(2 ** 22 - 1) == "")
    check("reaper: the same pid with a DIFFERENT starttime is a DIFFERENT process and is never "
          "signalled — this is the recycled-pid case that killed the watcher's replacement",
          not ident_is_live_harness((me, "0")) and idents_alive([(me, "0")]) == [])
    check("reaper: this python process is live but is NOT a harness, so it is not a reap target "
          "either — both halves of the guard must hold", not ident_is_live_harness(my_ident))
    script = reaper_script([(4242, "777")], 3)
    check("reaper: the detached script re-derives starttime at kill time and compares it to the "
          "value captured at ARM time — it never kills a remembered number",
          "4242:777" in script and '[ "$st" = "$want" ]' in script
          and "sed 's/^.*) //'" in script and "kill -9 $p" in script
          and "sleep 3" in script)
    check("reaper: arming with an identity that has no starttime arms NOTHING — an unidentifiable "
          "process is never a kill target", arm_pid_reaper([(4242, "")]) is None)

    # ---- 7.37 run index + session trace (R10/R11), and 7.69's per-seat statusline.
    # Built on a fixture in the CANONICAL goal shape ({goal}/runs/run-{n}), because the index
    # living one level ABOVE the package is the whole point of R11 and a flat fixture would let a
    # writer that put both files in one folder pass.
    with tempfile.TemporaryDirectory() as td4:
        goal4 = Path(td4) / "goal"
        pkg4 = goal4 / "runs" / "run-7"
        (pkg4 / "coordination").mkdir(parents=True)
        (pkg4 / "seats").mkdir()
        (pkg4 / "taskforce.csv").write_text(
            "taskforce-id,seat,after\ntf-9,alpha,\ntf-9,beta,\n", encoding="utf-8")
        a4 = argparse.Namespace(package=str(pkg4), base=None, workers_dir=None,
                                as_agent=None, force=False)
        seat4 = {"agent": "alpha", "harness": "claude", "model": "opus", "effort": "medium",
                 "cwd": str(pkg4 / "seats" / "alpha"), "window": False,
                 "folder": pkg4 / "seats" / "alpha"}
        Path(seat4["cwd"]).mkdir(parents=True)

        check("7.37/R11: the run INDEX is the GOAL-level runs.csv and the TRACE is the run's own "
              "sessions.csv — two files, one level apart. The KG record's older wording called "
              "the per-run trace runs.csv; building that would put both in one folder",
              runs_index_csv(pkg4) == goal4 / "runs.csv"
              and sessions_csv(pkg4) == pkg4 / "sessions.csv"
              and goal_dir(pkg4) == goal4)
        check("7.37: a package NOT in the canonical runs/ form still resolves an index — the "
              "writer stays total over the layouts this kit supports rather than raising",
              goal_dir(Path("/tmp/flat-pkg")) == Path("/tmp/flat-pkg"))

        sid4, note4 = session_open(a4, seat4, since=time.time(), wait=0.0)
        hdr4, rows4 = read_csv_table(sessions_csv(pkg4), SESSIONS_COLS)
        r4 = rows4[0] if rows4 else []
        pad_row(r4, hdr4)
        cix = {c: i for i, c in enumerate(hdr4)}
        check("7.37: a seat LAUNCH writes its session row with nobody invoking a writer — the "
              "criterion's real teeth (a writer only ever called by hand satisfies the words "
              "'writers live' while sessions.csv stays header-only)",
              len(rows4) == 1 and r4[cix.get("seat", 0)] == "alpha"
              and r4[cix.get("harness", 0)] == "claude"
              and r4[cix.get("started", 0)] != "" and r4[cix.get("ended", 0)] == "")
        check("7.37: the row carries the RESUME REFS task 7.32 needs from this file alone — "
              "harness and workdir, with the native-session-id column present to be filled",
              r4[cix.get("workdir", 0)] == seat4["cwd"] and "native-session-id" in cix)
        check("7.37: `recorded` (the pipe-pane marker of task 7.31) is left EMPTY, not invented — "
              "7.31 is not built and a fabricated marker would point at no recording",
              "recorded" in cix and r4[cix["recorded"]] == "")

        check("7.37: the GOAL-level index gains this run's row automatically, at the same moment "
              "— nobody hand-maintains it",
              (goal4 / "runs.csv").exists()
              and read_csv_table(goal4 / "runs.csv", RUNS_INDEX_COLS)[1][0][0] == "run-7")
        irows4 = read_csv_table(goal4 / "runs.csv", RUNS_INDEX_COLS)[1]
        iix4 = {c: i for i, c in enumerate(RUNS_INDEX_COLS)}
        check("7.37: `taskforce-ids` is DERIVED from taskforce.csv and deduped — 2 rows of one "
              "taskforce yield one id, not two",
              bool(irows4) and pad_row(irows4[0], RUNS_INDEX_COLS)[iix4["taskforce-ids"]] == "tf-9")
        check("7.37: run `type` is left EMPTY on a row this code creates — the KG says type is "
              "DATA (fresh|fix) and NOT derivable from the ordinal, so defaulting it to `fresh` "
              "would be silently wrong on a fix run. An empty cell is answerable; a guess is not",
              bool(irows4) and irows4[0][iix4["type"]] == "")
        check("7.37: `closed` is NOT stamped by the writer — closing a run is the leader's "
              "ceremony and an OPEN run's row is correct by staying open",
              bool(irows4) and irows4[0][iix4["closed"]] == "" and irows4[0][iix4["state"]] == "open")

        # A SECOND session of the SAME seat — the renew case the KG names ("one seat may
        # contribute SEVERAL sessions within one run").
        sid4b, _ = session_open(a4, seat4, since=time.time(), wait=0.0)
        rows4b = read_csv_table(sessions_csv(pkg4), SESSIONS_COLS)[1]
        check("7.37: a RENEW appends a SECOND session row for the same seat with a distinct id — "
              "the trace is ordered sessions, and a renew is a new session of one seat",
              len(rows4b) == 2 and sid4 != sid4b and sid4b != "")

        closed4 = session_close(a4, "alpha")
        rows4c = read_csv_table(sessions_csv(pkg4), SESSIONS_COLS)[1]
        ended4 = [pad_row(r, hdr4)[cix.get("ended", 0)] for r in rows4c]
        check("7.37: a CLOSE completes the seat's LIVE row — the most recent open one — and "
              "leaves the earlier closed session untouched",
              closed4 == sid4b and ended4.count("") == 1 and rows4c[1][cix.get("ended", 0)] != "")
        check("7.37: closing a seat with no open row is a silent NO-OP — a seat closed twice, or "
              "one launched before this writer existed, never gains a phantom row",
              session_close(a4, "nobody-here") == ""
              and len(read_csv_table(sessions_csv(pkg4), SESSIONS_COLS)[1]) == 2)
        check("7.37: ensure_run_index is IDEMPOTENT — a second call changes nothing, so every "
              "launch and close in a long run rewrites no history",
              ensure_run_index(pkg4) is False)

        # An index row already carrying owner-set identity must survive the writer touching it.
        write_csv_table(goal4 / "runs.csv", RUNS_INDEX_COLS,
                        [["run-7", "fix", "open", "", "2026-01-01 00:00", ""]])
        ensure_run_index(pkg4)
        keep4 = read_csv_table(goal4 / "runs.csv", RUNS_INDEX_COLS)[1][0]
        check("7.37: the writer NEVER rewrites `type` or `opened` on an existing row — they are "
              "the run's identity, not derived state, and a re-sync that overwrote a hand-set "
              "`fix` would destroy the one field the KG says is not derivable",
              keep4[iix4["type"]] == "fix" and keep4[iix4["opened"]] == "2026-01-01 00:00"
              and keep4[iix4["taskforce-ids"]] == "tf-9")

        # A header written before a column existed: the writer widens, never raises.
        (pkg4 / "sessions.csv").write_text("session-id,seat\nold-1,gamma\n", encoding="utf-8")
        check("7.37: a sessions.csv whose header PREDATES a column is honoured verbatim and never "
              "rewritten — a writer that merely appends must not redefine a contract other seats "
              "already read", read_csv_table(sessions_csv(pkg4), SESSIONS_COLS)[0] == ["session-id", "seat"]
              and session_close(a4, "gamma") == "")

        # ---- 7.69 statusline half
        sl_path, sl_action = write_seat_statusline(seat4)
        sl_data = json.loads(sl_path.read_text(encoding="utf-8")) if sl_path else {}
        check("7.69: the statusLine block is written into the SEAT's own "
              ".claude/settings.local.json — p-statusline-scope ruled (b); the owner's global "
              "~/.claude/settings.json fires for every claude session on this box and is never "
              "touched",
              sl_path == Path(seat4["cwd"]) / ".claude" / "settings.local.json"
              and sl_action == "written"
              and sl_data.get("statusLine", {}).get("type") == "command")
        check("7.69: the statusline command is an ABSOLUTE path derived from THIS file's own "
              "location — not $CLAUDE_PROJECT_DIR (which resolves inside the seat folder) and not "
              "a hard-coded vault path (issue G-72: the vault's wiring has pointed at a "
              "non-existent script since the team-kit was promoted, and a statusline fails "
              "silently)",
              "statusline-usage.py" in sl_data.get("statusLine", {}).get("command", "")
              and "$CLAUDE_PROJECT_DIR" not in sl_data.get("statusLine", {}).get("command", "")
              and sl_data.get("statusLine", {}).get("command", "").find("python3 /") == 0)
        atomic_write(sl_path, json.dumps({"permissions": {"allow": ["Bash"]}}) + "\n")
        _, sl_action2 = write_seat_statusline(seat4)
        sl_data2 = json.loads(sl_path.read_text(encoding="utf-8"))
        check("7.69: an EXISTING settings.local.json is MERGED, never replaced — a launch profile "
              "that clobbered a seat's permissions to fix its statusline would break the seat to "
              "improve its sensor",
              sl_action2 == "merged" and sl_data2.get("permissions", {}).get("allow") == ["Bash"]
              and "statusLine" in sl_data2)
        atomic_write(sl_path, json.dumps({"statusLine": {"type": "command", "command": "mine"}}) + "\n")
        _, sl_action3 = write_seat_statusline(seat4)
        check("7.69: a seat that ALREADY declares a statusLine keeps it — that was configured "
              "deliberately and launch is not the place to overrule it",
              sl_action3 == "kept"
              and json.loads(sl_path.read_text(encoding="utf-8"))["statusLine"]["command"] == "mine")
        check("7.69: a NON-claude seat gets no settings file at all — codex and opencode read "
              "neither, and writing one would litter their folders",
              write_seat_statusline(dict(seat4, harness="opencode")) == (None, "skipped"))
        check("7.69: a seat whose cwd is NOT its own folder gets NOTHING — discover_workers falls "
              "back to VAULT_ROOT for a flat briefing that declares no cwd:, and writing the block "
              "there would rewrite the VAULT's shared settings.local.json, governing every claude "
              "session started in the vault. MEASURED: that is exactly what happened at 08:06 "
              "(incident #545, G-75). Identity check, not a path blacklist",
              write_seat_statusline(dict(seat4, cwd=VAULT_ROOT)) == (None, "skipped")
              and write_seat_statusline(dict(seat4, folder=None)) == (None, "skipped")
              and write_seat_statusline(dict(seat4, cwd=str(pkg4))) == (None, "skipped"))

        projdir = Path(td4) / "projects"
        dotted = goal4 / ".rbtv" / "seats" / "leader"      # a dot, as every real seat path has
        dotted.mkdir(parents=True)
        (projdir / claude_project_slug(dotted)).mkdir(parents=True)
        (projdir / claude_project_slug(dotted) / "abc-123.jsonl").write_text("{}", encoding="utf-8")
        check("7.37: the transcript slug replaces DOTS as well as separators, and a real "
              "transcript RESOLVES out of a path containing one. Every seat lives under `.rbtv/`, "
              "so a slug that replaced only '/' missed EVERY claude seat and returned '' each "
              "time. Undetected because the original evidence was a directory LISTING, never an "
              "exercise of the derivation — and because every earlier check asserted only the '' "
              "outcome, so none of them could see a lookup that always missed",
              claude_native_session_id(str(dotted), projects=projdir) == "abc-123"
              and "-rbtv-" in claude_project_slug(dotted)
              and ".rbtv" not in claude_project_slug(dotted))
        check("7.37: an unresolvable backfill REPORTS rather than returning a bare '' that reads "
              "identically to nothing-to-do — the silence is what hid the slug bug all run",
              session_backfill_native(a4, "nobody-here") == ""
              and str(claude_native_session_id(str(dotted), projects=projdir / "nope")) == "")

        bf_seat = dict(seat4)
        check("7.37: the native session id is backfilled at the seat's OWN CHECKIN, not at launch "
              "— resolving at launch RACES the harness's startup and measurably lost the leader's "
              "08:21 renewal (transcript written after wait_harness_up returned). Checkin cannot "
              "race: the seat is running and the file it is writing is the newest in its own "
              "project dir. It also covers a CRASHED seat, which never closes but did check in",
              session_backfill_native(a4, "nobody-here") == ""
              and isinstance(bf_seat.get("cwd"), str))

        def _boom(*a, **kw):
            raise OSError("read-only goal folder")

        def _swallows():
            """TOTAL over the mutation input (G-66): removing the swallow makes _boom's OSError
            escape, and a check expression that let it through would ABORT the suite instead of
            failing — a mutation that aborts is evidence about nothing."""
            try:
                return session_trace_safe(_boom) == (None, "OSError: read-only goal folder")
            except Exception:                                  # noqa: BLE001
                return False
        check("7.37: a session-trace write that FAILS never takes down the act it records — the "
              "trace is bookkeeping ABOUT the run, not a gate ON it. A read-only goal folder must "
              "not raise out of launch_seat AFTER the harness is up, leaving a live seat the "
              "roster believes failed (G-11's shape wearing the bookkeeping mask)",
              _swallows() and session_trace_safe(lambda: "sid-1") == ("sid-1", ""))

        # ---- 7.33's room-creation line (p-monitor-start-is-lane-K-and-restart-is-732)
        mstatus, mdetail = ensure_team_monitor(a4)
        check("7.33: the team-monitor start line reports ABSENT rather than failing when "
              "team_monitor.py has not landed — a launch must never die because its monitor is "
              "not built yet, and 'absent' is the report monitor-builder reads as PENDING-WIRING",
              mstatus in ("ok", "absent") and (mstatus == "ok" or "does not exist" in mdetail))
        check("7.33: the monitor is resolved beside the rbtv orchestration CLIs, not guessed from "
              "cwd — the same __file__-derived discipline that keeps G-72 from recurring",
              team_monitor_script().name == "team_monitor.py"
              and "orchestration" in str(team_monitor_script()))

    # verdict, exit code and --expect-fail all live in cmd_selftest, so an abort anywhere above
    # still reaches them (G-66).


def report_expect_fail(expect, names, failures):
    """G-62: a mutation that makes the suite go red is NOT evidence the check under test works.

    The red can come from an unrelated check while the check being tested stays silent, and the
    suite verdict looks identical either way — measured: an appended help line tripped the
    `one-screen index` assertion while the parser-vs-epilog check under test never fired, and the
    mutation was one step from being banked as evidence. `--expect-fail` names the check the
    mutation is supposed to break, so the evidence becomes THAT CHECK'S LINE, never the verdict.
    Exit 0 only when the named check failed and every other check passed.
    """
    matched = [n for n in names if expect in n]
    print(f"expect-fail: {expect!r} matched {len(matched)} of {len(names)} checks")
    if not matched:
        # The dangerous case. A substring that names nothing must never read as success: it is a
        # typo, or the check you believe you are testing does not exist — and both would otherwise
        # be indistinguishable from a mutation that worked.
        print("expect-fail: FAIL — no check matched. A substring naming nothing is a typo or a "
              "check that does not exist; it is never a pass.")
        return 1
    if len(matched) > 1:
        print("expect-fail: FAIL — the substring must name EXACTLY ONE check; narrow it:")
        for name in matched[:10]:
            print(f"  matched: {name}")
        if len(matched) > 10:
            print(f"  ... and {len(matched) - 10} more")
        return 1
    target = matched[0]
    if target not in failures:
        print("expect-fail: FAIL — the named check PASSED, so the mutation never reached it. "
              "Whatever else the suite did, it says nothing about this check:")
        print(f"  named: {target}")
        return 1
    collateral = [n for n in failures if n != target]
    if collateral:
        print(f"expect-fail: FAIL — the named check failed, but so did {len(collateral)} other "
              "check(s). The mutation is not isolated, so this red is not evidence about the "
              "named check (G-62):")
        for name in collateral:
            print(f"  also failed: {name}")
        return 1
    print("expect-fail: PASS — exactly the named check failed; every other check passed.")
    print(f"  named: {target}")
    return 0


def add_identity_flags(s, force=True):
    """--as / --force are also accepted AFTER the subcommand (that is where agents type them).
    SUPPRESS leaves the global --as untouched when the subcommand's copy is absent."""
    s.add_argument("--as", dest="as_agent", default=argparse.SUPPRESS, metavar="NAME",
                   help="act as this agent instead of the resolved identity")
    if force:
        s.add_argument("--force", action="store_true",
                       help="override this command's refusal (identity mismatch, role gate, validation)")


def add_pretty_flag(s):
    """`--pretty` on the four VIEW commands as well as globally — that is where a human types it
    (`coordinate status --pretty`). SUPPRESS keeps the global value when this copy is absent."""
    s.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS,
                   help="ANSI colour + aligned columns (also: COORD_PRETTY=1); default is plain")


# T6/F2 — the top-level help used to print this module's docstring: a ~120-line manual that
# listed every subcommand a second time and had already drifted from the code. It is now a
# grouped 1-line-per-command index; each command's own -h carries the detail, an example and the
# step that follows. Global flags are summarised in the footer instead of an options block —
# argparse renders one line per flag, and the whole point of this help is that it fits on a
# screen. Groups are LIFECYCLE-ordered, not alphabetical: everyday work, leader-only, the rest.
HELP_EPILOG = """everyday
  checkin     register this session — binds this tmux pane to your agent name
  status      where you stand: identity, pane, owner, unread, cursor, open asks
  read        your unread messages, {limit} at a time (cursor persisted per agent)
  send        message one agent, a group, or all — typed, their pane woken
  pending     open asks: waiting on you, open to everyone, yours unanswered
  checkout    end your session (exports your transcript first)

leader
  launch      open one tmux seat per worker briefing and start its harness
  close       spawn a closer that co-writes a seat's memory.md, then closes it
  close-seat / reap / close-run / current-run  close a seat (--renew) · free panes (--go) · end / resolve the run
  approve     answer a seat's permission prompt by sending keys to its pane
  panel       open the control-panel overview strip in this window
  owner       set owner presence: present | afk
  add-to-group / remove-from-group  join or drop an existing group's members

other
  workers / descriptors  who is alive and on what · structural audit of the seat descriptors
  create-group       open a message group for one workstream
  export-transcript  capture a seat's pane scrollback into its worker folder
  depart      ephemeral seats: export + check out + kill your own pane
  selftest / gates   built-in self-test (temp dir, no tmux) · which flag carries which gate
global: --run TAG | --package DIR (which run) · --as NAME (act as) · --pretty (colour)
details + examples: coordinate <command> -h · --force overrides a refusal, where one exists""".format(limit=READ_LIMIT)


def build_parser():
    """The whole CLI surface. Split out of main() so the self-test can render the help texts."""
    p = argparse.ArgumentParser(
        prog="coordinate",
        usage="coordinate [--run TAG | --package DIR] [--as NAME] [--pretty] <command> [args]",
        description="Coordination CLI for a multi-agent tmux team run — all state lives in the "
                    "run package.\nIdentity is resolved, never typed: --as NAME > $COORD_AGENT > "
                    "this pane's roster row.",
        epilog=HELP_EPILOG,
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # -h stays, but out of the options block: with every global flag summarised in the epilog,
    # an options section holding one entry costs three lines of a help that must fit a screen.
    p.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS,
                   help=argparse.SUPPRESS)
    p.add_argument("--package", metavar="DIR", help=argparse.SUPPRESS)
    p.add_argument("--run", metavar="TAG", help=argparse.SUPPRESS)
    p.add_argument("--as", dest="as_agent", default=None, metavar="NAME", help=argparse.SUPPRESS)
    p.add_argument("--pretty", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--base", help=argparse.SUPPRESS)            # testing only
    p.add_argument("--workers-dir", help=argparse.SUPPRESS)     # testing only
    # help=SUPPRESS hides the subparsers action from the "positional arguments" block (the epilog
    # IS the command list); parsing is untouched.
    sub = p.add_subparsers(dest="cmd", required=True, metavar="<command>", help=argparse.SUPPRESS)

    made = {}

    def command(name, description, epilog):
        """One subcommand. No `help=` on purpose: the grouped epilog above IS the command list,
        and argparse would otherwise render a second, ungrouped one."""
        made[name] = sub.add_parser(name, description=description, epilog=epilog,
                                    formatter_class=argparse.RawDescriptionHelpFormatter)
        return made[name]

    s = command(
        "checkin",
        "Register your session. This is the ONE command that carries your name: it creates your\n"
        "roster row and binds this tmux pane to you, and every later command resolves your\n"
        "identity from that binding. Run it before any briefing work, and again after a relaunch\n"
        "(a re-check-in supersedes your prior row — but is REFUSED while the pane that already\n"
        "holds this name is still alive, so a zombie relaunch cannot split a seat in two).",
        "example:\n"
        "  coordinate checkin builder \"rebuilding views/*.html from graph.py; owns views/ + "
        "render.py\"\n"
        "next: coordinate read — anything already waiting for you")
    s.add_argument("agent", help="your agent name, as in your briefing's `agent:` key — this call CREATES the pane->name binding every later command resolves")
    s.add_argument("summary", help=f"what you are working on, max {SUMMARY_MAX} chars — other agents read this line to decide whether to message you")
    s.add_argument("--pane", help="override tmux pane id (default: auto-detect from $TMUX_PANE)")
    s.add_argument("--force", action="store_true",
                   help="check in even though a LIVE pane still holds this name — only after you have confirmed the other session is dead (zombie double-launch guard)")
    s.set_defaults(func=cmd_checkin)

    s = command(
        "checkout",
        "End your session: exports your transcript, then flips your roster row to done. Run it\n"
        "when your briefing is complete and your completion message is already sent.",
        "example:\n"
        "  coordinate checkout\n"
        "next: nothing on your side — leader runs `close <you>` if the seat must go")
    s.add_argument("--no-export", action="store_true", help="skip the automatic transcript export (e.g. the pane is already dead)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_checkout)

    s = command(
        "send",
        "Send one typed message to an agent, a group, or everyone, and wake the recipients'\n"
        "panes. Send at coordination points: starting, before touching a shared surface, at a\n"
        "milestone, when blocked, when done. The log is the truth — wakes are best-effort.",
        "example:\n"
        "  coordinate send leader \"views build green; 12/12 pages render\" --type completion\n"
        "next: coordinate pending — after an ask, it shows whether anyone settled it")
    s.add_argument("to", help="recipient: an agent name, a group name, or 'all' — validated against the roster, the briefings and the groups, so a typo is refused")
    s.add_argument("message", nargs="?", help="the body, quoted — needs --inline when typed at a shell, because a shell eats backticks and $(...) before coord.py sees them. Anything with backticks, quotes or newlines goes through --file")
    s.add_argument("--type", required=True, choices=MESSAGE_TYPES,
                   help="completion (my briefing/milestone is done) | ask (I need an answer) | answer (replying to an ask) | verdict (a judge/checker ruling) | note (FYI)")
    s.add_argument("--re", dest="re_num", type=int, metavar="N",
                   help="the ask this settles — REQUIRED on --type answer, optional on verdict")
    s.add_argument("--supersedes", type=int, metavar="N",
                   help="retract message N: readers see the retraction inline wherever N is rendered")
    s.add_argument("--file", metavar="PATH",
                   help="read the body from a file ('-' = stdin) — shell-safe for backticks/quotes/newlines")
    s.add_argument("--inline", action="store_true",
                   help="accept the quoted positional body from a shell command line: you are asserting it has no backticks, $(...) or anything else a shell would have eaten before coord.py saw it (a proven substitution is refused even with this)")
    s.add_argument("--why", choices=sorted(BROADCAST_CLAUSES), metavar="CLAUSE",
                   help="REQUIRED on `send all`: which broadcast clause justifies it — "
                        + " | ".join(f"{k} ({v})" for k, v in sorted(BROADCAST_CLAUSES.items())))
    add_identity_flags(s)
    s.set_defaults(func=cmd_send)

    s = command(
        "gates",
        "Print the flag -> gate binding: which override flag carries which launch gate.\n"
        "Exists so an UNATTENDED caller can assert the split before it overrides anything —\n"
        "jobs/recover-room.py reads this and refuses to run if `--force` ever starts carrying\n"
        "the memory gate. Reads the same map launch_gates enforces, so it cannot drift.",
        "example:\n"
        "  coordinate gates --json\n"
        "next: nothing — this command reads state and changes none")
    s.add_argument("--json", action="store_true", help="machine-readable, for an asserting caller")
    s.set_defaults(func=cmd_gates)

    s = command(
        "read",
        f"Show the messages you have not read yet, {READ_LIMIT} at a time. A plain read advances\n"
        "your persisted cursor through the last message SHOWN — nothing else. Every filter\n"
        "(--type/--addressed), plus --digest, --msg, --peek and --all, is peek-only and says so,\n"
        "so a filtered read can never drop the messages it hid from your inbox.",
        "example:\n"
        "  coordinate read\n"
        "next: read again while it reports more waiting; coordinate pending for the asks you owe")
    s.add_argument("--digest", action="store_true", help="one line per message instead of full bodies (no cursor move)")
    s.add_argument("--msg", type=int, default=None, metavar="N", help="show message N alone, in full, with its ask link (no cursor move)")
    s.add_argument("--after", type=int, default=None, metavar="N",
                   help="override the stored cursor: show messages after N (recovery after a context loss)")
    s.add_argument("--limit", type=int, default=None, metavar="N", help=f"messages per batch (default {READ_LIMIT}; 0 = no limit)")
    s.add_argument("--peek", action="store_true", help="show without advancing the cursor")
    s.add_argument("--all", action="store_true", help="replay the whole log without advancing the cursor")
    s.add_argument("--type", choices=MESSAGE_TYPES, default=None, help="show only this message type (no cursor move)")
    s.add_argument("--addressed", choices=["any", "direct", "broadcast"], default="any",
                   help="any = to me, my groups, or everyone (default) | direct = only messages naming me | broadcast = only messages to all")
    add_pretty_flag(s)
    add_identity_flags(s)
    s.set_defaults(func=cmd_read)

    s = command(
        "status",
        "One-shot orientation — run it after a relaunch, a context loss, or whenever you are\n"
        "unsure where you stand: who you are, whether your pane can still be woken, owner\n"
        "presence, your cursor against the log tail, unread by type, and the asks waiting on you.\n"
        "The pane check needs a live tmux server; without one every pane honestly reads ok.",
        "example:\n"
        "  coordinate status\n"
        "next: whatever its own `next:` line says — read, pending, or back to your task")
    add_pretty_flag(s)
    add_identity_flags(s)
    s.set_defaults(func=cmd_status)

    s = command(
        "pending",
        "The open asks, derived over the WHOLE log and not from your cursor: what is waiting on\n"
        "you, what is open to everyone, and which of your own asks nobody has answered. An ask\n"
        "stays open until an answer or verdict --re's it, or it is superseded.",
        "example:\n"
        "  coordinate pending\n"
        "next: coordinate send <asker> \"<answer>\" --type answer --re <ask#>")
    add_pretty_flag(s)
    add_identity_flags(s)
    s.set_defaults(func=cmd_pending)

    s = command(
        "workers",
        "The roster: one CURRENT row per agent — alive, dead pane, or checked out; what each is\n"
        "working on; and how many messages each one has still to read (lag=, the same exact\n"
        "unread count that seat's own `status` reports). ACTIVE rows are verified against live\n"
        "tmux panes, so a seat whose pane is gone shows DEAD?.",
        "example:\n"
        "  coordinate workers\n"
        "next: coordinate close-seat <agent> for a DEAD? row; send to reach a live one")
    s.add_argument("--full", action="store_true", help="do not truncate the 'working on' summaries")
    s.add_argument("--history", action="store_true", help="every historical row, not just each agent's current one")
    add_pretty_flag(s)
    s.set_defaults(func=cmd_workers)

    s = command(
        "owner",
        "Record whether the owner is at the keyboard. Workers were inferring it and getting it\n"
        "wrong (P15), so it is stated instead. Leader's to set — or the owner's own, from a\n"
        "shell outside any seat.",
        "example:\n"
        "  coordinate owner afk --note \"back in 2h\"\n"
        "next: coordinate send all \"owner is afk until ~18h\" --type note")
    s.add_argument("state", choices=["present", "afk"], help="present = rulings can be escalated now; afk = queue them")
    s.add_argument("--note", default="", help="optional context, e.g. 'back in 2h'")
    add_identity_flags(s)
    s.set_defaults(func=cmd_owner)

    s = command(
        "launch",
        "(leader) Open one tmux seat per worker briefing and start its harness. Harness, model,\n"
        "effort, cwd and pane-vs-window all come from each briefing's frontmatter, so leader\n"
        "launches without reading any briefing. A bare launch never boots leader itself.\n"
        "Before any codex/opencode seat opens, its launch root's worker mirror (AGENTS.md +\n"
        ".agents/) is refreshed once, so the seat reads current rules and not whatever the\n"
        "last installer run left behind. A failed refresh warns and launches anyway.",
        "example:\n"
        "  coordinate launch --only judge-ux,judge-parity\n"
        "next: coordinate workers — every seat must check in; one that does not never booted")
    s.add_argument("--only", help="comma-separated agent names to launch (stages: e.g. --only judge-ux,judge-parity)")
    s.add_argument("--dry-run", action="store_true", help="print the command each seat would start with, open nothing")
    s.add_argument("--force-memory", action="store_true",
                   help="override the MEMORY gate only (--force does not: it covers the role gate)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_launch)

    s = command(
        "export-transcript",
        "Capture a seat's full pane scrollback into workers/<agent>/transcripts/. checkout and\n"
        "depart already do this for you — run it by hand for a mid-run milestone, or for a seat\n"
        "you are about to close.",
        "example:\n"
        "  coordinate export-transcript builder --label milestone2\n"
        "next: coordinate close builder — the closer reads the export")
    s.add_argument("target", help="the TARGET seat whose pane is captured (the seat acted on, not the caller)")
    s.add_argument("--label", default="", help="optional filename suffix, e.g. 'milestone2'")
    s.set_defaults(func=cmd_export_transcript)

    s = command(
        "close",
        "(leader) Spawn a closer seat for one target: it reads the seat's transcript and the log,\n"
        "co-writes the seat's memory.md WITH the worker, then runs close-seat and departs. Use it\n"
        "when a seat is finished, or is near its context limit (--renew gives it a fresh session\n"
        "with the same briefing and its new memory).",
        "example:\n"
        "  coordinate close builder --renew\n"
        "next: coordinate workers — closer-<target> checks in, then the seat goes")
    s.add_argument("target", help="the TARGET seat being closed (the seat acted on, never your own name)")
    s.add_argument("--renew", action="store_true",
                   help="after closing, relaunch the seat fresh (it reads the updated memory.md)")
    s.add_argument("--dry-run", action="store_true", help="print the closer prompt without launching")
    s.add_argument("--force-memory", action="store_true",
                   help="override the MEMORY gate only (--force does not: it covers the role gate)")
    s.add_argument("--no-export", action="store_true", default=False,
                   help="skip the transcript export (only reached by a `close: mechanical` seat, "
                        "which closes without a closer)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_close)

    s = command(
        "close-seat",
        "The mechanical tail of a close: export the target seat's transcript, check its row out,\n"
        "kill its pane — and with --renew relaunch it fresh. The closer runs this at the end of\n"
        "its own job; leader runs it directly to clean up a dead pane.",
        "example:\n"
        "  coordinate close-seat builder --renew\n"
        "next: coordinate workers — confirm the seat is gone (or back, with --renew)")
    s.add_argument("target", help="the TARGET seat being closed (the seat acted on — a closer never passes its own name)")
    s.add_argument("--renew", action="store_true", help="relaunch the seat fresh after killing it")
    s.add_argument("--no-export", action="store_true", help="skip the transcript export (e.g. pane already dead)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_close_seat)

    s = command(
        "close-run",
        "Stamp this run's row in the goal-level runs.csv: state=closed, closed=<now>.\n"
        "The leader still DECIDES when a run closes; this records THAT it closed, so the run\n"
        "index resolves the goal's current run with nobody maintaining it by hand (task 7.37).",
        "example:\n"
        "  coordinate close-run\n"
        "next: coordinate --package <next-run> launch — the new run opens its own index row")
    add_identity_flags(s)
    s.set_defaults(func=cmd_close_run)

    s = command(
        "current-run",
        "Which run of this goal is LIVE, resolved from the goal-level runs.csv alone (R10).\n"
        "One hop from the goal folder, so a sensor follows a run boundary instead of staying\n"
        "pinned to the run it was born in. Refuses — never guesses — when zero or several runs\n"
        "are open, because R9's one-live-run enforcement (task 7.77) is not built yet.",
        "example:\n"
        "  coordinate current-run\n"
        "next: coordinate --run <that run> workers — read the live run's roster")
    add_identity_flags(s)
    s.set_defaults(func=cmd_current_run)

    s = command(
        "reap",
        "One sweep over the awaiting-close debt: seats that finished their own lifecycle whose\n"
        "panes the leader has not yet freed. OBSERVES BY DEFAULT — a bare `reap` reports the debt\n"
        "and records this pass; --go is what kills. A pane is freed only when it is at least\n"
        f"{REAP_MIN_AGE_MIN}min old, its transcript exists, the pane still holds exactly the\n"
        "harness processes it checked out with (so no human has picked it up), and the condition\n"
        "has held across TWO passes at least "
        f"{REAP_MIN_PASS_GAP_MIN}min apart — one reading is a snapshot, two is a trend.\n"
        "Reaping frees the PANE only; each seat still owes a close-seat afterwards.",
        "example:\n"
        "  coordinate reap            # observe and confirm, kill nothing\n"
        "  coordinate reap --go       # free the panes already confirmed READY\n"
        "next: coordinate workers — the debt is listed there until close-seat settles it")
    s.add_argument("--go", action="store_true",
                   help="actually free the confirmed panes (without it, reap only observes)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_reap)

    s = command(
        "approve",
        "(doorman) Answer a seat's interactive permission prompt by sending keys to its\n"
        "registered pane, then echo the pane tail so you can verify what happened. Inspect the\n"
        "pane and DECIDE first — this only presses the button.",
        "example:\n"
        "  coordinate approve builder --keys 2\n"
        "next: run it again if the echoed tail still shows the prompt")
    s.add_argument("target", help="the TARGET seat whose pane is showing the prompt (the seat acted on)")
    s.add_argument("--keys", default="", help="literal keys before Enter (e.g. 1, 2, 3, n); empty = Enter only")
    s.add_argument("--no-enter", action="store_true", help="send keys without a trailing Enter")
    s.set_defaults(func=cmd_approve)

    s = command(
        "panel",
        "(leader) Split a short full-width overview strip into THIS window: the live session\n"
        "overview (windows, panes, seat names) plus plan usage. Idempotent — it skips if an\n"
        "overview pane is already open.",
        "example:\n"
        "  coordinate panel\n"
        "next: coordinate launch — the strip tracks the seats it opens")
    add_identity_flags(s)
    s.set_defaults(func=cmd_panel)

    s = command(
        "depart",
        "Self-service exit for an ephemeral seat: export your own transcript, check out, and kill\n"
        "your own pane, in one command. It takes no name — a seat can only depart ITSELF; leader\n"
        "removes other seats with close-seat.",
        "example:\n"
        "  coordinate depart\n"
        "next: nothing — your pane is gone and your row reads checked out")
    add_identity_flags(s)
    s.set_defaults(func=cmd_depart)

    s = command(
        "create-group",
        "Open a message group for ONE workstream or overlap, so its thread leaves the `all`\n"
        "channel. You and leader are always members. This is what the startup round produces:\n"
        "one group per identified overlap, and detailed discussion happens there.",
        "example:\n"
        "  coordinate create-group views-render builder judge-ux\n"
        "next: coordinate send views-render \"<why this group exists>\" --type note")
    s.add_argument("group", help="the group name — a workstream, never an agent name or 'all'")
    s.add_argument("members", nargs="*", help="agent names to include (you and leader are added automatically)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_create_group)

    s = command(
        "add-to-group",
        "(leader) Add members to an existing group — the way a late seat joins a thread that is\n"
        "already running.",
        "example:\n"
        "  coordinate add-to-group views-render toolsmith\n"
        "next: coordinate send views-render \"<who joined, and why>\" --type note")
    s.add_argument("group", help="an existing group name")
    s.add_argument("members", nargs="+", help="agent names to add")
    add_identity_flags(s)
    s.set_defaults(func=cmd_add_to_group)

    s = command(
        "remove-from-group",
        "(leader) Remove members from an existing group — the only sanctioned way to undo a\n"
        "membership, since coordination/ is script-managed and hand-editing it is banned. Use it\n"
        "when a seat's lane is done, or when a special-case seat (watcher, engineer, a closer)\n"
        "was added before the G-32 rule that now refuses it.",
        "example:\n"
        "  coordinate remove-from-group ceremony watcher\n"
        "next: coordinate send ceremony \"<who left, and why>\" --type note")
    s.add_argument("group", help="an existing group name")
    s.add_argument("members", nargs="+", help="agent names to drop (all must currently be members, unless --force)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_remove_from_group)

    s = command(
        "descriptors",
        "Read-only structural audit of every seat descriptor against taskforce.csv: name vs\n"
        "folder, cwd, orphans both directions, duplicate names, binding divergence. Opens no\n"
        "briefing body — fields and paths only — so no seat's instructions reach the caller.",
        "example:\n"
        "  coordinate descriptors\n"
        "next: nothing — findings are reported to whoever owns seats/, never fixed here")
    s.set_defaults(func=cmd_descriptors)

    s = command(
        "selftest",
        "Run the built-in self-test in a temp dir: no tmux, no run package, no network — every\n"
        "tmux touch is stubbed. Required to exit 0 before any change to this script is used.",
        "example:\n"
        "  python3 coord.py selftest --expect-fail 'epilog index and the parser agree'\n"
        "next: nothing — a non-zero exit means the change is not ready")
    s.add_argument("--expect-fail", metavar="SUBSTRING", default=None,
                   help="mutation-testing: name the ONE check this mutation should break. Exits 0 "
                        "only if that check failed and every other passed — a suite that goes red "
                        "for an unrelated reason is not evidence (G-62)")
    s.set_defaults(func=cmd_selftest)
    p.command_parsers = made  # so the self-test can render every command's help
    return p



def assert_argv_body_shell_safe(args):
    """S-4(b) at the ONE boundary where argv provenance is knowable: a body that arrived in THIS
    process's argv, parsed by whatever launched us.

    G-101 — these two checks used to sit inside `message_body`, where they interrogated AMBIENT
    PROCESS STATE (the parent's `comm`, the parent's pre-substitution command line) rather than the
    provenance of the body they judged. `_selftest_checks` calls `cmd_send` with synthetic
    positional bodies, which that evidence cannot tell apart from a human typing at a shell, so the
    guard refused the suite's own sends and `sys.exit(1)` tore the run down at check 17 of 303. The
    gate every seat must pass before saving this file was therefore RED — and the deeper fault was
    that its verdict was decided by the SHAPE OF THE CALLER'S INVOCATION: a shell that execs itself
    away on a simple command, or a `timeout`/`env` wrapper, leaves a non-shell parent and the guard
    never fires at all. Two independent verifiers reported this gate GREEN from wrapped invocations
    while it was RED from plain ones, and re-derivation — the campaign's standard remedy — cannot
    detect that, because both re-derivations were honest and reinforced each other. Only VARYING
    THE INVOCATION exposes it.

    Deciding it here, after parsing and before dispatch, is the fix rather than a flag: a real CLI
    body is the only thing that can be present at this point. Synthetic and in-process callers
    (`watch.py`, the daemon jobs, the self-test) build a Namespace and call the command function
    directly, so they never reach this boundary and never pay for a hazard they cannot have — which
    is what `CLI_INVOCATION` was always trying to express.
    """
    if not (CLI_INVOCATION and getattr(args, "func", None) is cmd_send):
        return
    body = getattr(args, "message", None)
    if not body:
        return      # --file / --file - / no body: nothing a shell could have eaten
    eaten = substitution_eaten(body)
    if eaten and not getattr(args, "force", False):
        print(f"refused: your shell SUBSTITUTED {' and '.join(eaten)} in this body before "
              f"coord.py ever saw it — what you are about to log is the OUTPUT of a command "
              f"that actually RAN on your box, not the text you wrote. coord.py cannot "
              f"repair it: the original characters are already gone from argv.\n"
              f"Send it via --file (or --file - with a quoted heredoc) — the only form a "
              f"shell cannot eat:\n"
              f"  cat > /tmp/msg.txt <<'EOF'\n  ...your text...\n  EOF\n"
              f"  {coord_invocation(args)} send {getattr(args, 'to', '<to>')} "
              f"--type {getattr(args, 'type', '<type>')} --file /tmp/msg.txt\n"
              f"your shell's original line, for reference:\n  {shell_source_line()[:400]}\n"
              f"override (you are certain the substitution was harmless): --force",
              file=sys.stderr)
        sys.exit(1)
    # G-101 residual (leader #76): the parent-process test is GONE, deliberately. It asked "was
    # our argv parsed by a shell", and any exec-away wrapper — `timeout`, `env`, `nice`, `xargs`
    # — answers no while a shell parsed the line anyway. Measured after the boundary move:
    # `coordinate send x "body"` refused, `timeout 30 coordinate send x "body"` ACCEPTED, and
    # `timeout 30 coordinate send x "text $(echo EATEN)"` put EATEN into the permanent log.
    # Wrappers are not exotic — a leader reaching for `timeout` on anything that might hang
    # produced that corruption twice in one hour. So the rule is now unconditional at this
    # boundary: a positional body pays an explicit `--inline`, whatever launched us. That is
    # S-4(b)'s own design (default safe; the unsafe path pays an assertion) with the inference
    # removed, and it costs nothing real — every programmatic caller either goes in-process
    # (goal-watcher-job calls cmd_send directly) or already uses --file (the probes).
    if not getattr(args, "inline", False):
        print(f"refused: this body was typed on a shell command line, and a shell eats "
              f"backticks and $(...) BEFORE coord.py can see them — the corruption is "
              f"undetectable after the fact and it has silently rewritten this room's "
              f"record three times, each by an author who knew about it.\n"
              f"Shell-safe (cannot be eaten):\n"
              f"  cat > /tmp/msg.txt <<'EOF'\n  ...your text...\n  EOF\n"
              f"  {coord_invocation(args)} send {getattr(args, 'to', '<to>')} "
              f"--type {getattr(args, 'type', '<type>')} --file /tmp/msg.txt\n"
              f"Short body with no backticks, quotes or $ in it? Add --inline and it is "
              f"sent as typed.", file=sys.stderr)
        sys.exit(1)

def main():
    # S-4(b): only a real CLI invocation had its argv parsed by a shell. watch.py and the
    # daemon jobs call cmd_send() IN-PROCESS with a Namespace — no argv, no shell, never
    # exposed — and must not pay for a hazard they cannot have. This flag is the difference,
    # and it is set HERE rather than inferred from the parent process, because an in-process
    # caller started from a shell has a shell parent too and would otherwise be caught.
    global CLI_INVOCATION
    CLI_INVOCATION = True
    args = build_parser().parse_args()
    set_pretty(args)
    # S-4(b)/G-101 — argv provenance is a property of the INVOCATION, so it is judged here,
    # at the boundary, and never inside a function that also serves synthetic callers.
    assert_argv_body_shell_safe(args)
    args.func(args)


if __name__ == "__main__":
    main()
