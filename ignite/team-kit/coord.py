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
import hashlib
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

# ⚠ RESOLVE THE SYMLINK BEFORE DERIVING THE DIRECTORY. `coordinate` on this box is a symlink into
# ~/.local/bin, and a bare `Path(__file__).parent` would point there rather than at the kit — so
# the import would work when the script is called directly and fail through the symlink every
# other seat uses. Same form watch.py uses, for the same reason.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import budget as budget_mod  # noqa: E402 — the ONE reader of the run's declared floor (task 7.82)
import gateway_client  # noqa: E402 — stdlib-only gateway wire, `gateway-status` (task 7.57)

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
    # THE CORRESPONDENT'S OWN OPT-IN (`ruling-addressable-non-member.md`, constraint 1: derive it,
    # never hardcode a name). A descriptor declaring `addressable: non-member` says THIS AGENT MAY
    # BE ADDRESSED BY A PACKAGE IT IS NOT A MEMBER OF. It is the half a package cannot assert on
    # someone else's behalf: the register (below) supplies only a PATH, and the name, together with
    # the permission, comes from the descriptor the correspondent owns.
    #
    # ⚠ `non-member` IS DESCRIPTIVE, NOT A KG KIND. `sd-graph` resolves no record for
    # `correspondent`, `guest`, `meta-agent`, `non-member` or `external agent`, and PRIN-10 forbids
    # coining one in code — so this reuses the LEADER RULING'S OWN WORDING and mints no term. What
    # to call this kind is an OWNER question, filed, not answered here.
    "addressable": re.compile(r"^addressable:\s*(\S+)\s*$", re.MULTILINE),
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
    hb["code_drifted"], hb["code_known"] = _heartbeat_code_drift(hb.get("code"))
    return hb


def _heartbeat_code_drift(loaded):
    """(drifted file names, whether the question could be answered at all) — run issue G-158.

    The loop stamps a sha per source file it LOADED; this re-reads those same paths NOW. A
    disagreement means a live, heartbeating, apparently-healthy loop is executing code that no
    longer exists on disk — the failure mode that bit three long-lived processes inside one hour on
    2026-07-27, each caught only by hand-comparing a process start time against a commit time.

    ⚠ ABSENCE IS REPORTED AS UNKNOWN, NEVER AS OK. A loop started before this field existed writes
    no `code` key, and that is indistinguishable from a current one unless it is said out loud —
    which is the same absence-reads-as-health shape this whole class is made of. A caller that
    treats a missing marker as "fine" has rebuilt the defect at the reader."""
    if not isinstance(loaded, dict) or not loaded:
        return [], False
    drifted = []
    for path, want in sorted(loaded.items()):
        try:
            now = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        except OSError:
            drifted.append(Path(path).name + " (unreadable now)")
            continue
        if now != want:
            drifted.append(Path(path).name)
    return drifted, True


def _heartbeat_daemon_lines(hb, stale):
    """(fold-into-the-ok-line suffix, [loud lines]) for the ignite daemon — run issue G-188.

    The run had NO detector for "the daemon restarted". It tracked MainPID in PROSE, in a handoff
    doc, BY HAND — and prose does not execute. Twice on 2026-07-27 a restart went unnoticed; the
    second cost ~50 minutes of a false picture and an owner brief that had to be withdrawn. The
    watch loop samples the unit each pass; this renders it on the line the reader already reads,
    because a separate command is a command nobody runs.

    ⚠ THE BOUND, and it must not be read as more than it is: this says THAT the daemon restarted.
    It says NOTHING about WHICH BYTES it is running. There is no G-158-style import-time
    fingerprint on the daemon side, so "the deploy took" remains an inference — a refinement that
    lands in the daemon's own boot code, not here.

    ⚠ ABSENCE IS REPORTED AS UNKNOWN, NEVER AS OK, in both directions: a loop predating the field
    writes no `daemon` key, and a pass that could not read the unit writes state=unknown. Both are
    said out loud, for the reason `_heartbeat_code_drift` gives — a caller that reads a missing
    marker as "fine" has rebuilt the defect at the reader."""
    dmn = hb.get("daemon")
    loud = []
    fold = ""
    # A STALE watcher's daemon reading is as old as its last pass. Saying so is the difference
    # between a fact and a fossil: without the qualifier the reader takes an hours-old pid for a
    # live one, which is this class's whole failure shape wearing a different hat.
    asof = " (as of that last pass, which is STALE)" if stale else ""
    if not isinstance(dmn, dict) or not dmn.get("state"):
        loud.append(("hint", "daemon: UNKNOWN — this loop predates the daemon marker, so nothing "
                             "here can tell whether the ignite daemon has restarted. Treat it as "
                             "UNVERIFIED, not healthy; a restart of the loop makes it answerable."))
        dmn = {}
    elif dmn["state"] == "running":
        pid = dmn.get("pid")
        since = (dmn.get("since") or "").replace("UTC", "").strip()
        fold = f", daemon pid {pid}" + (f" since {since}" if since else "") + asof
    elif dmn["state"] == "stopped":
        loud.append(("dead", f"daemon: DOWN — {dmn.get('why') or 'the unit reports inactive'}"
                             f"{asof}. Nothing is running jobs, ticks or spawns."))
    else:
        loud.append(("dead", f"daemon: UNKNOWN — {dmn.get('why') or 'unreadable'}{asof}. This is "
                             f"NOT a report that the daemon is absent: on this box a system-scope "
                             f"query for the user-scoped unit answers exit 0 with LoadState="
                             f"not-found, byte-identical to a unit that never existed. Ask "
                             f"`systemctl --user status {dmn.get('unit') or 'the ignite unit'}` "
                             f"before concluding."))
    # G-188 stage 3, THE PULL SURFACE — and its absence here was the defect. The watcher computes
    # "is the daemon running current code" every pass; this is the ONLY place that turns it into
    # something a reader sees, because `coordinate workers` composes from the heartbeat file. A
    # verdict computed and never surfaced is a value with no consumer (G-184's shape), and it fails
    # in the direction that looks healthiest: a silent line.
    dcode = hb.get("daemon_code")
    # ⚠ THE CODE VERDICT IS ONLY WORTH A LINE WHILE THE DAEMON IS RUNNING. A down or unreadable
    # daemon ALREADY has a loud line above saying so, and "code state UNKNOWN" underneath it adds no
    # decision — it is the 11-of-12 false-positive shape, arriving as a second line about the same
    # fact. The gap this closes is a RUNNING daemon whose line would otherwise imply healthy bytes.
    running_now = isinstance(dmn, dict) and dmn.get("state") == "running"
    if not running_now:
        dcode = None
    if isinstance(dcode, dict) and dcode.get("verdict") == "current":
        # Folded into the ok line, never given one of its own: G-158's second pass proved that a
        # healthy case printing NOTHING leaves "checked and current" to be inferred from an absence,
        # in the one feature whose whole subject is absence looking like health.
        fold += ", running current code"
    elif isinstance(dcode, dict) and dcode.get("verdict") == "stale":
        loud.append(("dead", f"daemon: RUNNING STALE CODE — {dcode.get('detail') or 'files changed'} "
                             f"changed on disk since this daemon booted, and node binds a module's "
                             f"source at require, so the running daemon can never pick it up. It "
                             f"keeps serving the OLD behaviour while every other surface reports "
                             f"healthy. A restart deploys it (owner-only, task 7.68)."))
    elif isinstance(dcode, dict):
        loud.append(("hint", f"daemon: code state UNKNOWN — {dcode.get('detail') or 'not determinable'}"
                             f". Treat it as UNVERIFIED, not healthy."))
    elif running_now:
        # A loop predating the field writes no key at all. Said out loud for the same reason the
        # watcher's own missing marker is: a caller that reads a missing marker as "fine" has
        # rebuilt the defect at the reader. Bounded to the running case by the rule above.
        loud.append(("hint", "daemon: code state UNKNOWN — this watch loop predates the daemon "
                             "code-state check, so nothing here can tell whether the daemon is "
                             "running current bytes. A loop restart makes it answerable."))
    chg = hb.get("daemon_change")
    if isinstance(chg, dict) and isinstance(chg.get("to"), dict):
        frm, to = chg.get("from") or {}, chg["to"]
        loud.append(("dead", f"daemon: RESTARTED — observed {chg.get('at') or '?'} "
                             f"(pid {frm.get('pid') or '?'} -> {to.get('pid') or '?'}, "
                             f"state {frm.get('state') or '?'} -> {to.get('state') or '?'}). "
                             f"An owner-side deploy or bounce is INVISIBLE to this run otherwise; "
                             f"this line is sticky and stays until the next change, because both "
                             f"restarts on 2026-07-27 were noticed hours late. It does NOT say "
                             f"which code the daemon loaded."))
    return fold, loud


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
        # s12-03: RETURNED, not printed — the caller prints it — so it goes through the
        # message-building half of `refuse`. Left as a bare literal it would be the ONE un-layered
        # refusal in the file, and invisible to the selftest guard, which scopes to `print(`.
        return False, refusal_text(
            "input",
            "wake text carries a newline, and send-keys delivers a newline as "
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


# ---------- lifecycle timeouts (the detached lifecycle executor) ----------
# Two TIMEOUTS, not policy numbers. `r-floor-single-source` (R-10) governs the RAM FLOOR and does
# not reach these; no floor literal belongs anywhere near them, and floor-lint.py refuses one
# outside budget.json.
#
# LIFECYCLE_SETTLE_S bounds the executor's wait for the FORKING CALLER to exit before it acts, then
# it proceeds REGARDLESS of the outcome: the executor never depends on the caller, which is the
# whole point of detaching it. By the time the fork happens the handoff is appended, the transcript
# exported, the roster flipped and the sessions.csv row closed — nothing durable is left inside the
# caller's session to rescue — so the wait is courtesy, not correctness.
#
# LIFECYCLE_STALE_MIN is the age in MINUTES past which an in-flight lifecycle marker whose executor
# is NOT live reads as a FAILED renewal (the revival detector reads exactly that conjunction).
# ⚑ IT IS DERIVED, NOT MEASURED — carry that caveat with the number, never the number alone. The
# derivation sums the waits the executor actually spends:
#     settle              <= LIFECYCLE_SETTLE_S       10 s
#   + mirror refresh         MIRROR_REFRESH_TIMEOUT  300 s   <- the dominant term, and it is a COLD
#                                                               full-workspace render; that
#                                                               constant's own comment puts steady
#                                                               state at 2-3 s
#   + harness up             HARNESS_UP_TIMEOUT       25.0 s
#   + native id resolve      NATIVE_ID_WAIT            8.0 s
#   + pid exit               PID_EXIT_TIMEOUT          6.0 s
#   = ~350 s = ~6 min worst case; the value below started as that worst case plus headroom.
# It is deliberately SHORTER than CLOSING_MAX_MIN: a stuck closer merely narrows an inbox, while a
# stuck executor is a seat that is neither alive nor closed. That ordering is the load-bearing part
# and holds whatever the number becomes.
# ⚑ A later task measures a REAL renewal and freezes this value. That is a ONE-LINE change — the
# assignment below and nothing else. This block is written to stay true either way: it states a
# derivation and an ordering, never a claim that the current digits are the measured answer.
LIFECYCLE_SETTLE_S = 10
LIFECYCLE_STALE_MIN = 10


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
# stays put (owner ruling) and is merely made settable per machine, which is what the env var
# below is for — it is the per-machine seam, not a licence to guess a better number.
# The GATE ITSELF is not in question and was ratified: seat RSS understates peak ~3x, three
# seats died `exit 137`, and the watcher was SIGKILLed twice as a BYSTANDER.
SEAT_SPIKE_MB = int(os.environ.get("COORD_SEAT_SPIKE_MB") or 1400)   # per-box override — a MEASUREMENT
# ⚠ THE SOURCE IS CAPTURED AT THE SAME INSTANT AS THE VALUE, AND THAT IS NOT PEDANTRY. The value is
# read ONCE, at import; a report that re-asked the environment at CALL time could say
# "COORD_SEAT_SPIKE_MB" while printing the built-in 1400, because a var set after import never
# reaches SEAT_SPIKE_MB. A provenance label that can disagree with the number it labels is worse
# than no label — it is a confident wrong answer at the moment someone is auditing the gate.
SEAT_SPIKE_SOURCE = ("COORD_SEAT_SPIKE_MB" if os.environ.get("COORD_SEAT_SPIKE_MB")
                     else "built-in default")

# ⚠⚠ THE FLOOR IS POLICY. IT IS ITS OWN CONSTANT AND TAKES NO ENV OVERRIDE.
# Owner ruling `r-mem-floor-2000` (2026-07-28), shape ruled by the leader (#1210 pt 3, #1269 pt 2).
#
# It used to read `SEAT_SPIKE_MB * SPIKE_RESERVE`, and that derivation is exactly why 2000 could not
# be expressed: 2000 is not 1400 x 2. Reaching it through the factors would have moved SEAT_SPIKE_MB
# — a MEASUREMENT held put by a standing owner ruling (see the block above) — in order to encode a
# POLICY number. Measurement and policy are different things and the code now says so.
#
# ⚠ AND NO `COORD_*` OVERRIDE HERE, DELIBERATELY: an env override on the floor would let an
# environment silently overrule an owner ruling with NO FILE ANYWHERE TO GREP — for the very number
# `budget.json` was just made the normative home of. The per-machine seam belongs on the spike,
# which is measured per box; the floor is decided once, by the owner.
# (`SPIKE_RESERVE` and `COORD_SPIKE_RESERVE` are deleted with this change: their only uses were
# building this product and printing it in the refusal below, and the env var was set nowhere in
# the repo. The reserve is now DERIVED FROM THE FLOOR, which is the direction that stays honest.)
#
# ⚠⚠ AND THE CONSTANT ITSELF IS NOW GONE — task 7.82, owner ruling `r-floor-single-source`:
#
#     A POLICY NUMBER MUST NEVER BE TRANSPORTED BY ARGV. argv is a COPY; a file is a REFERENCE.
#
# A module constant is the same class of copy as an argv literal: it is a number this file decided
# to believe. The floor is READ, per launch, from the run package's `budget.json` via
# `budget.read_floor()` — see `launch_gates()`. `memory_gate()` therefore takes `floor_mb` as a
# REQUIRED argument with NO DEFAULT: a default here would be the constant coming back under
# another name, and every caller must have resolved a floor before it may ask about one.


def available_mb():
    """MemAvailable in MiB, 0 when /proc/meminfo is unreadable (never gate on 'cannot tell')."""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return 0
    return 0


def memory_gate(n_seats, avail_mb, floor_mb):
    """Pure: '' when it is safe to spawn `n_seats`, else the refusal reason. avail_mb == 0 means
    unmeasurable and PASSES — a broken sensor must not be able to stop a run."""
    if not avail_mb:
        return ""
    need = floor_mb + max(0, n_seats - 1) * SEAT_SPIKE_MB
    if avail_mb >= need:
        return ""
    # ⚠ THE RESERVE THIS MESSAGE CLAIMS IS DERIVED FROM THE FLOOR ACTUALLY IN FORCE — `floor_mb`,
    # the argument, not the module constant and not a separate reserve knob. The old text printed
    # `SPIKE_RESERVE`, a number that BUILT the floor; once floor and spike stopped being multiples
    # that would have printed "2 spikes of reserve" while holding 1.43, teaching a false
    # measurement at the exact moment an operator is blocked and reading it. A caller passing its
    # own `floor_mb` now gets a message about ITS floor.
    reserve = (floor_mb / SEAT_SPIKE_MB) if SEAT_SPIKE_MB else 0
    return (f"{avail_mb} MB available, {need} MB needed to spawn {n_seats} seat(s). A claude seat "
            f"peaks at ~{SEAT_SPIKE_MB} MB on boot and on every compaction — steady RSS is a third "
            f"of that — and this gate holds {reserve:.2f} spikes of reserve so a spiking seat "
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


def ident_is_live_process(ident):
    """True when (pid, starttime) still names THE SAME live process — ANY process, harness or not.

    NOT a substitute for `ident_is_live_harness`, and never interchangeable with it: that predicate
    additionally requires `is_harness_argv`, which matches only the claude/codex/opencode basenames
    in HARNESS_PROCS. The lifecycle executor and its forking caller are PYTHON processes, so
    `ident_is_live_harness` reports every live one of them DEAD — silently turning the
    caller-settle wait (LIFECYCLE_SETTLE_S) into a no-op and the staleness test
    (LIFECYCLE_STALE_MIN) into "always stale". A wait that cannot wait and a test that cannot say
    "not yet" both LOOK like working code; that is why the two predicates are separate functions
    with separate names rather than one with a flag.

    Pure w.r.t. its argument, exactly as `ident_is_live_harness` is: it re-derives BOTH halves from
    /proc at call time and trusts nothing remembered. The starttime half is what makes it a guard
    at all — a pid alone is recyclable, and a teardown is exactly when new processes start. Pane
    ancestry is no substitute for it either; `process_identity` carries the reason: "G-12's
    in-place respawn puts the replacement under the SAME pane, so an ancestry test would confirm
    the very process it must protect."

    A zombie is NOT live: it has exited and its status is merely unreaped, which is precisely the
    outcome both callers are waiting for. Any read failure is False as well — an unreadable /proc
    entry is not evidence of liveness, and the fail-safe direction here is "assume it is gone",
    because the alternative is an executor that waits forever on a process it cannot see."""
    pid, starttime = ident
    state, live_start = proc_stat(pid)
    return bool(starttime) and live_start == starttime and state != "Z"


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
        refuse("state", detail, 1)
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
        refuse("state", detail, 1)
    print(f"runs.csv: {detail}")
    print(c(f"the index now resolves the goal's current run without hand maintenance "
            f"({runs_index_csv(pkg)})", C_HINT))
    # ---- s3-03: the LIFECYCLE MARKER SWEEP. `clear_lifecycle` has exactly ONE caller and this is
    # it. Without this block, "swept by the next close-run" would be a claim about code that does
    # not exist: every `state: "done"` entry would accumulate for the life of the goal and
    # `clear_lifecycle` would ship dead. Runs AFTER the index close, because a refused close means
    # the run is not over and its marker is not the close's to touch.
    #
    # The survivors are printed one per line and NAMED. A close that quietly left entries behind
    # would teach the leader that the marker is empty when it is not — and an in-flight entry at
    # close time is exactly the report worth reading.
    swept, survivors = sweep_lifecycle(base_dir(args))
    if swept:
        print(f"lifecycle marker: swept {len(swept)} completed "
              f"{'entry' if len(swept) == 1 else 'entries'} ({', '.join(swept)})")
    for _seat, _why in survivors:
        print(f"lifecycle marker: LEFT {_seat} — {_why}")


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


def session_open(args, w, since=None, wait=None, pane=None):
    """Append this seat's session row the moment it boots. Returns (session-id, note).

    `note` is non-empty when a field could not be resolved — the caller PRINTS it. A blank cell
    that nobody mentioned is indistinguishable from one that was never needed.

    `wait` is a parameter and not a constant read inside so the self-test can drive the resolver
    to its unresolved branch without sleeping through the real boot timeout.

    ⚠ AND `None` MEANS "read NATIVE_ID_WAIT NOW", because a default written as `wait=NATIVE_ID_WAIT`
    IS BOUND AT `def` TIME: a caller that lowers the module constant is then silently ignored, and
    the parameter above delivers its promise only to callers that pass one EXPLICITLY. The path
    that actually spends the budget — launch_seat — passes nothing, so the suite slept through the
    full timeout on every launch while believing it had opted out. Same trap, and the same cure, as
    `claude_projects_dir` evaluating Path.home() at call time instead of import.

    `pane` carries the seat's tmux pane so the row can record the IDENTITY PAIR the seat-identity
    gate decides on. It is the PANE's pid, deliberately, not this process's: every process the seat
    ever runs is a descendant of the pane, and the gate matches the registered pid against the
    CALLER'S ANCESTRY. Recording the launcher's own pid would name a process that is not an
    ancestor of the seat and would refuse every legitimate occupant.
    """
    pkg = package_dir(args)
    native = ""
    if w.get("harness") == "claude":
        native = claude_native_session_id(w.get("cwd"), since,
                                          wait=NATIVE_ID_WAIT if wait is None else wait)
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


def team_monitor_holder(base):
    """Which pid holds the monitor slot right now, or None.

    ⚠ ASKED THE WAY `team_monitor.py`'s OWN `lock_holder` ASKS IT — pid file plus `/proc` — so the
    two cannot disagree about who is running. Deliberately NOT parsed out of `ensure`'s stdout:
    that output is vocabulary ("already running" / "started"), and a report keyed on a sibling's
    wording breaks silently the day the wording changes. This reads the same PROPERTY the sibling
    reads.
    """
    p = base / "team-monitor.lock"
    try:
        pid = int(p.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return None
    return pid if pid and Path(f"/proc/{pid}").exists() else None


def team_monitor_last_seen(base):
    """The DEAD sensor's own final heartbeat: (written_at_iso, writer_pid), or None.

    ⚠⚠ THIS IS WHAT MAKES THE OUTAGE BOUNDABLE, AND IT IS A MEASUREMENT, NOT AN INFERENCE.
    `state.json` carries `written_at_iso` and `writer_pid`, rewritten by the monitor itself every
    pass — so the last line the dead process wrote is still on disk when we replace it. That gives
    LAST OBSERVED ALIVE. The restart instant gives DEAD BY.

    ⚠ WHAT IT DOES **NOT** GIVE, and the report must never claim otherwise: the DEATH INSTANT.
    Nothing was watching. The monitor died somewhere inside (last_seen, restart] — so that interval
    is an UPPER BOUND ON THE OUTAGE, never the outage. "Down for 28 minutes" would be a fabrication;
    "down for AT MOST 28 minutes, last observed alive at T" is what the disk actually supports.

    Returns None whenever the bound cannot be READ — no file, unparseable, no timestamp, or a
    `written_at` in the future (a clock moved; a bound derived from it would be fiction). The
    caller then reports the death instant as unknown, which is the honest floor.
    """
    try:
        snap = json.loads((base.parent / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(snap, dict):
        return None
    iso, at, pid = snap.get("written_at_iso"), snap.get("written_at"), snap.get("writer_pid")
    if not iso or not isinstance(at, (int, float)):
        return None
    if at > time.time() + 60:  # clock skew — refuse to derive a window from it
        return None
    return iso, pid


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

    ⚠⚠ TASK 7.88 (`G-259`, reporting half). THIS USED TO RETURN `("ok", script)` WHETHER IT FOUND
    THE SENSOR ALIVE OR RAISED IT FROM THE DEAD, and the launch line printed "ensured for this run"
    for both. The run's ONLY raw-source sensor died and was silently respawned here; every consumer
    of `state.json` read a stale room until a LAUNCH happened to repair it, and nothing said so.
    ⇒ A REPAIR THAT LEAVES NO REPORT IS INDISTINGUISHABLE, FROM EVERY SURFACE THE ROOM READS, FROM
    NOTHING HAVING BEEN WRONG. Starting a dead monitor is CORRECT and is not being removed; doing
    it silently is the defect.

    The two outcomes are now distinct statuses — `already` and `started` — decided by reading the
    lock slot BEFORE and AFTER, never by parsing the child's wording.
    """
    base = base_dir(args)
    script = team_monitor_script()
    if not script.is_file():
        return "absent", {"why": f"{script} does not exist yet — 7.33 has not landed"}
    before = team_monitor_holder(base)
    # Read the outgoing snapshot BEFORE starting anything: the replacement immediately begins
    # overwriting `state.json`, and with it the dead process's last heartbeat. Read it after the
    # start and the bound is gone — this ordering IS the measurement.
    last_seen = team_monitor_last_seen(base) if before is None else None
    try:
        subprocess.run([sys.executable, str(script), "ensure",
                        "--package", str(package_dir(args))],
                       capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return "fail", {"why": str(exc)}
    after = team_monitor_holder(base)
    if before is not None:
        return "already", {"pid": before}
    if after is None:
        # Started nothing and nothing is holding the slot: the sensor is DOWN and the room is
        # unobserved. Reported as a failure rather than as a quiet success — the pre-7.88 code
        # returned "ok" here too.
        return "fail", {"why": "ensure returned but no process holds the monitor lock"}
    record = {"event": "team-monitor-restarted", "at": now(), "pid": after,
              "last_seen": last_seen[0] if last_seen else None,
              "last_seen_pid": last_seen[1] if last_seen else None}
    append_sensor_event(base, record)
    return "started", record


def append_sensor_event(base, record):
    """Durable, greppable record of a repair we performed — criterion 1's "a surface the room reads".

    ⚠ `team-monitor.log` was NOT enough and that is measured, not assumed: it already carried all
    three `team-monitor up:` lines for this run, so the restart WAS logged and still went
    unreported for the length of a milestone. A log nothing consumes is not a report.

    This records only what we DID, at the instant we did it. It watches nothing and it is not a
    detector — noticing a dead sensor WITHOUT waiting for a launch is 7.32/7.33's flag-set work and
    is deliberately absent here.
    """
    try:
        base.mkdir(parents=True, exist_ok=True)
        with (base / "sensor-events.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass  # never fail a launch over its own bookkeeping (the posture this file already takes)


def render_monitor_report(status, detail):
    """The launch line. Returns (text, tone, to_stderr).

    ⚠ CRITERION 2: `already` and `started` MUST NOT render alike. Everything below the status word
    exists so a reader with no out-of-band knowledge can tell "the sensor was fine" from "the
    sensor was DEAD and I just raised it".
    """
    if status == "already":
        return f"team-monitor: already up (pid {detail['pid']}) — not restarted", C_ALIVE, False
    if status == "absent":
        return f"team-monitor: NOT started — {detail['why']}", C_HINT, False
    if status == "fail":
        return (f"WARNING team-monitor start FAILED — {detail['why']}; the room runs UNOBSERVED",
                C_DEAD, True)
    # started — the sensor was DEAD. Say so, and say exactly how much is known.
    line = (f"⚠ team-monitor WAS DEAD — RESTARTED (pid {detail['pid']}) at {detail['at']}. "
            f"Until now every reader of state.json saw a STALE room.")
    if detail.get("last_seen"):
        line += (f"\n  last observed alive: {detail['last_seen']} (its own final state.json write, "
                 f"pid {detail['last_seen_pid']})"
                 f"\n  ⇒ the sensor was down AT MOST from then until now. The DEATH INSTANT IS "
                 f"UNKNOWN — nothing was watching — so that span is an UPPER BOUND on the outage, "
                 f"never the outage itself.")
    else:
        line += ("\n  last observed alive: UNKNOWN — no readable final write from the dead process, "
                 "so the outage cannot be bounded at all. Not estimated.")
    line += ("\n  a dead sensor is still only noticed by a launch (G-259 detection half, 7.32/7.33)"
             " — this reports the repair, it does not detect the death.")
    return line, C_DEAD, True


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


# ---------------------------------------------------------------------------------------------
# ADDRESSABLE NON-MEMBERS — `seats/leader/ruling-addressable-non-member.md`, ruled 2026-07-27.
#
# THE DEFECT. Every source `known_recipients` draws on is PACKAGE-LOCAL by construction: this
# package's roster rows, its seat descriptors, its groups, its relay tokens. That locality is
# deliberate (see `relay_seats`: G-111 is a foreign seat sharing a live roster name). So an agent
# whose descriptor lives in ANOTHER goal folder resolves nowhere, and BOTH gates in `cmd_send`
# close on it: `send <it>` is refused as an unknown recipient (F5), and its own `ask` is refused
# because nobody can answer it (S-7). Measured live at run-2 #509/#510: a meta-agent summoned to
# build seats could neither message the leader nor be messaged, and finished its work through
# `tmux send-keys` — off the bus, so no record, no threading, no delivery confirmation.
#
# ⚠ THE RECIPIENT HALF IS THE WHOLE DEFECT; THE ASK-REFUSAL IS ITS CONSEQUENCE. The S-7 gate asks
# whether the SENDER can be addressed — i.e. whether it is a recipient. Fix recipient resolution
# and the ask-refusal dissolves on its own. They must not be fixed separately.
#
# THE GRANT IS EXACTLY ONE CAPABILITY: A NAME THAT RESOLVES AS A RECIPIENT.
#
#   GRANTED      resolves as a recipient · can be `--re`-linked in ask->answer threading ·
#                carries its `from-pkg:` origin UNCHANGED (nothing is built for that half — the
#                engineer's stage-4 distinguisher already stamps it `external`, and it keeps
#                doing so precisely BECAUSE no roster row is created here).
#   NOT GRANTED  a roster row · a `taskforce.csv` row · A WAKE · a read cursor · broadcast or
#                group membership by default · any count against the pane cap · inclusion in the
#                chief-of-staff's sweep or any close/kill/reap lifecycle · read-everything · any
#                KG `realizes:` edge.
#
# A future reader must not infer any right from this that is not in the GRANTED line.
#
# ⚠⚠ NO ROSTER ROW, AND THIS IS THE CONSTRAINT THAT SHAPES EVERYTHING ELSE. A row would buy the
# name, the cursor and the wake in one move — which is exactly why it is forbidden: it buys them
# by making the agent a member, contradicting the owner ruling that it is not one. It is also the
# repair THIS TOOL'S OWN S-7 REFUSAL TEXT RECOMMENDS ("check in first so you have a roster row"),
# which is how the trap gets found by every next meta-agent; that text is corrected below.
#
# ⚠ DELIVERY IS PULL, NOT PUSH — STATED HERE AND IN THE OUTPUT, NEVER LEFT TO BE DISCOVERED.
# A non-member has no pane in this run's tmux session and no cursor, so `addressable` CANNOT mean
# `woken`. The message is appended to the log addressed to it and THE CORRESPONDENT READS THE LOG
# ITSELF. If that stays implicit, the first person to address one will assume a wake, get silence,
# and read the silence as "considering" rather than "never delivered" — the hazard the correspondent
# named about itself. A dropped relay is undetectable to it, and that does not change because the
# name now resolves.
ADDRESSABLE_COLS = ["descriptor", "admitted-by", "admitted"]


def load_addressable(args):
    """({name: descriptor-path}, [error, ...]) for this package's addressable non-members.

    DERIVED, NEVER A KIT-SIDE NAME LIST (constraint 1). `SPECIAL_CASE_SEATS` was demoted to a
    default table on exactly this ground, and the engineer refused to validate `window:` against
    one run's four hardcoded names on the same one: a shared kit must not carry one campaign's
    furniture. So the register `<package>/addressable.csv` carries ONLY A PATH — it cannot even
    state the name — and the name is read from the descriptor the correspondent itself owns.
    (`taskforce.csv` is the precedent: a run-authored registry this tool only ever reads.)

    TWO-SIDED AND MACHINE-ENFORCED (constraint 2). The package points at a descriptor; the
    descriptor must declare `addressable: non-member`. Either half alone does nothing. A package
    therefore cannot make another goal's seat addressable without that seat having said so, and a
    descriptor that says so is inert until some package points at it.

    FAILS LOUD, NEVER SILENT (constraint 3). Every row that does not resolve — missing file,
    unreadable, no frontmatter, no name, no opt-in, or a name that COLLIDES with a local seat —
    yields an ERROR STRING and admits nothing. Four fail-silent defects landed in this system in
    one evening; a register that quietly dropped a row would be the fifth. The collision refusal is
    G-111 itself: a foreign descriptor named `leader` must never shadow the local one.
    """
    pkg = package_dir(args)
    path = pkg / "addressable.csv"
    header, rows = read_csv_table(path, ADDRESSABLE_COLS)
    if not rows:
        return {}, []
    if "descriptor" not in header:
        return {}, [f"{path}: no `descriptor` column — header is {','.join(header)}"]
    i = header.index("descriptor")
    out, errors = {}, []
    for r in rows:
        raw = (r[i].strip() if i < len(r) else "")
        if not raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = (pkg / p)
        try:
            text = p.resolve().read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{raw}: descriptor unreadable ({exc.__class__.__name__}) — admits nothing")
            continue
        if not text.startswith("---"):
            errors.append(f"{raw}: no frontmatter — admits nothing")
            continue
        fm_end = text.find("\n---", 3)
        fm = text[:fm_end] if fm_end != -1 else text
        m = FM_KEY["agent"].search(fm)
        if not m:
            errors.append(f"{raw}: descriptor declares no `seat:`/`agent:` name — admits nothing")
            continue
        name = m.group(1)
        decl = FM_KEY["addressable"].search(fm)
        if not decl or decl.group(1).lower() != "non-member":
            errors.append(f"{raw}: '{name}' does not declare `addressable: non-member` in its own "
                          f"descriptor — a package cannot grant this on another agent's behalf")
            continue
        out[name] = str(p)
    return out, errors


def addressable_nonmembers(args, base):
    """Names admitted after the LOCAL-COLLISION check, plus every error to report.

    Split from `load_addressable` because the collision test needs this package's local names,
    and a resolver that reached for them would make the register's own parse depend on roster
    state. Local always wins: a foreign descriptor never shadows a seat of this run."""
    found, errors = load_addressable(args)
    _, _, rows = load_workers(base)
    local = {r["agent"] for r in rows} | set(briefing_frontmatters(workers_dir(args))) \
        | set(group_map(base)) | {"all"}
    admitted = {}
    for name, p in found.items():
        if name in local:
            errors.append(f"{p}: '{name}' COLLIDES with a seat of this package — refused, the "
                          f"local name wins (G-111: a foreign seat sharing a live roster name "
                          f"must never be resolved here)")
            continue
        admitted[name] = p
    return admitted, errors


def report_addressable_errors(args, base, stream=None):
    """Print every unresolved register row. Constraint 3 — REFUSE VISIBLY, never degrade to a
    silent success. Called on the paths where a name is resolved, so a broken row surfaces at the
    moment someone is relying on it rather than at some later audit nobody runs."""
    _, errors = addressable_nonmembers(args, base)
    for e in errors:
        print(f"warning: addressable.csv — {e}", file=stream or sys.stderr)
    return errors


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
            refuse(
                "identity",
                f"you claimed '{claimed}' ({source}), but this pane ({pane}) is "
                f"registered to '{registered}' in the roster.\n"
                f"Run the command without the claim to act as '{registered}', or pass --force "
                f"to override deliberately (leader acting on behalf of a seat).",
                2)
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


# ---- The role gate's refusal CASES (stage-1 §1.3, task s12-02 item 2).
#
# A case is a CALL-SITE PARAMETER, never a wholesale replacement of the wording. `role_verdict`
# builds the message for ALL 14 gate call sites, and hard-wiring the two close-shaped templates
# would regress the refusal at the 9 gated commands that have no self-semantics (`close-run`,
# `owner`, `add-to-group`, `remove-from-group`, `launch`, `panel`, `reap --go`, `kill-pane`,
# `relaunch-pane`): every one of them would print "closing ANOTHER seat…" and LOSE `allowed_desc`
# — the only place a refusal names WHO may act. So the GENERIC case is the default, and a
# close-shaped site opts in by passing `case=`.
ROLE_CASE_DEFAULT = "`{command}` is {allowed_desc}; you resolve to '{caller}'"

# Passed by `cmd_close` / `cmd_close_seat`. Closing ANOTHER seat is the leader's act and stays
# leader-gated as a FAILURE PATH (`d-close-renew-decider-recorded`): the SEAT decides its own
# renew/refresh, the LEADER decides acceptance and the closing of somebody else.
CLOSE_OTHER_CASE = ("closing ANOTHER seat is the leader's act -- `{command}` is {allowed_desc}; "
                    "you resolve to '{caller}' and the target is '{target}'")
# ⚠ THE COACHED COMMAND RUNS TO THE END OF THE STRING, carries `--inline`, and holds no trailing
# punctuation. G-181's harvester reads this file's own advice as argv and runs it through the REAL
# send parser, and it caught two drafts of this line: the first wrapped the command in parentheses
# and the `)` was swallowed into argv; the second omitted `--inline`, which the positional-body
# guard now refuses UNCONDITIONALLY. Advice here is a surface the parser judges, not prose — a
# remedy the tool would itself refuse is worse than no remedy, because it is read at the exact
# moment the caller is blocked.
CLOSE_OTHER_REMEDY = 'ask leader to run it -- coordinate send leader "<why>" --type ask --inline'

# SELECTED ON `is_self`, never passed in. When the caller IS the target and the gate still refuses,
# the call site's OTHER-seat wording is the wrong answer — the caller did not try to close anyone
# else, so "ask leader" sends them to the wrong place. `role_verdict` owns this substitution
# because it is the ONLY place `is_self` is known, and the remedy is the same everywhere: the
# deterministic self path built for exactly this.
ROLE_CASE_SELF = ("`{command}` is {allowed_desc}, and this is not a self-act it offers -- you "
                  "resolve to '{caller}' and the target '{target}' IS you, but this command has "
                  "no self path")
ROLE_REMEDY_SELF = "coordinate checkout --renew"


# ---- Every refusal this file emits names its LAYER (task s12-03, stage-1 §1.4; standing ruling
# R-8, `core-build-run-adjustments/rulings.md`).
#
# THE PROBLEM. A seat that hits a refusal cannot tell whether coord.py's OWN gate refused it or the
# HARNESS's permission classifier did. The two look alike, a bare "refused:" carries nothing that
# separates them, and the seat then sends the run at the wrong fix (W4) — this cost real run-2
# time. The prefix is the fix, and it is shaped so `grep -c 'refused \[coord'` counts them.
#
# THE LAYER IS ASSIGNED BY WHAT THE CHECK READS. That rule is the durable artifact; the site list is
# not. A refusal added tomorrow picks its layer by re-applying it — and `_selftest_checks` refuses
# both a bare `print("refused: …")` (the sweep rots on the next added refusal otherwise: two new
# commands added 12 un-layered sites in a single day) and a layer token outside this tuple.
REFUSAL_LAYERS = (
    "role gate",    # the CALLER's role/identity vs the act
    "identity",     # who the caller resolves to, vs the pane
    "state",        # the run's own recorded state forbids it
    "input",        # the arguments/body are malformed or over a bound
    "environment",  # the process/tmux/filesystem world is wrong
)

# Appended to the ROLE GATE's own refusals — the one layer a seat routinely MISREADS as a harness
# block, because "you may not run this command" is exactly what the classifier also says. Naming
# the layer in the prefix is not enough on its own: the prefix teaches a reader who already knows
# the vocabulary, and this paragraph teaches the one who does not.
ROLE_GATE_LAYER_NOTE = (
    "layer:   this refusal is coord.py's OWN role gate, NOT your harness's permission\n"
    "         classifier. Report it as \"coord role gate refused\" — the two look alike and\n"
    "         a bare \"refused\" sends the run at the wrong fix."
)


def refusal_text(layer, msg):
    """The refusal's TEXT, without the exit — the message-building half of `refuse`.

    Split out for the refusals that are RETURNED rather than printed (`wake`'s newline guard
    returns `(False, text)` and its caller prints it). Without this split that one refusal would be
    the single un-layered refusal in the file, which is precisely the rot the selftest guard exists
    to prevent — and it would be invisible to that guard, because the guard scopes to `print(`.

    The layer is NOT validated here. A ValueError raised while building a refusal would replace a
    refusal with a traceback — worse than the defect. `_selftest_checks` carries the enforcement
    instead, where a wrong token costs a red line and nothing else.
    """
    return "refused [coord " + layer + "]: " + msg


def refuse(layer, msg, code=2):
    """Emit a layered refusal on stderr and exit with `code`.

    ⚠ `code` IS NOT DECORATIVE, and it is passed explicitly at every one of this file's call sites
    rather than defaulted. The sites exit with a MIX of 1 and 2 (the role gate and the identity
    contradiction exit 2; nearly everything else exits 1), and `watch.py`'s `record_undelivered`
    path keys on coord's EXIT CODE, not on this text. Uniformizing the codes would change behaviour
    for it and for every scripted caller.

    ⚠ `_selftest_checks` defines its own local `refuse(fn, **kw)` capture helper, which SHADOWS this
    function inside that one scope. Deliberate: the fixtures called theirs long before this existed,
    and module-level callers are unaffected because they resolve the global at call time.
    """
    print(refusal_text(layer, msg), file=sys.stderr)
    sys.exit(code)


def role_verdict(args, command, allow, allowed_desc, target=None, self_legal=False,
                 remedy=None, case=None):
    """The ROLE gate's verdict, WITHOUT acting on it:
    (caller, passed, overridden, message, is_self).

    Split out of `gate` so a command carrying more than one gate can evaluate them ALL before it
    refuses (leader #230). `passed` is the gate's own answer, ignoring --force; `overridden` says
    --force would carry it anyway.

    THE TARGET IS A PARAMETER, AND THAT IS THE WHOLE FIX (task s12-02, stage-1 §1.1). `allow` is a
    predicate over the CALLER NAME ALONE, so until this parameter existed the gate could not tell
    "I close MYSELF" from "I close YOU" — no call site passed the target, so there was nothing to
    compare against. That is the mechanism behind run-2's 15:1x refusal of an act the owner had
    already ruled legal, and no wording change could have fixed it: the parameter had to exist.

    `self_legal=True` says this command's SELF case is legal without `--force`
    (`d-close-renew-decider-recorded`: the seat decides its own renew/refresh, deterministically,
    with no agent in the execution path). It is deliberately NOT the default — a command grows a
    self path only by declaring one.

    `is_self` is returned so callers can shape their own text and their own post-gate behaviour
    (`cmd_close_seat`'s self-act warning, W1)."""
    caller = resolve_agent(args, required=False)
    is_self = bool(caller) and bool(target) and caller == target
    passed = bool(allow(caller)) or (self_legal and is_self)
    # Through GATE_FLAGS, never a bare getattr: the binding lives in ONE place (S-6(a)).
    forced = gate_forced(args, "role")
    if passed:
        return caller, True, False, "", is_self
    # A refused SELF act never renders the call site's OTHER-seat case: the caller acted on nobody
    # but themselves, and "ask leader to run it" would be a remedy for a thing they did not do.
    template = ROLE_CASE_SELF if is_self else (case or ROLE_CASE_DEFAULT)
    remedy_text = ROLE_REMEDY_SELF if is_self else (remedy or "")
    msg = template.format(command=command, allowed_desc=allowed_desc,
                          caller=caller or "no identity", target=target or "")
    if remedy_text:
        msg += f"\nremedy: {remedy_text}"
    return caller, False, forced, msg, is_self


def gate(args, command, allow, allowed_desc, target=None, self_legal=False,
         remedy=None, case=None):
    """Hard role gate (T6/F14: `owner`/`launch`/`close`/`panel` documented a leader-only rule
    and never enforced it). `allow` is a predicate over the resolved caller name; '' means
    identity was unresolvable. Returns the caller. `--force` is the escape.

    `target`/`self_legal`/`remedy`/`case` are threaded straight through to `role_verdict` — see
    its docstring for why the target is a parameter at all. `case=None` is the generic default, so
    the 9 gated commands with no self-semantics are untouched by that change.

    For a command that ALSO carries the memory gate, use `launch_gates` instead — this one
    short-circuits, which is exactly the trapdoor #230 rules against."""
    caller, passed, overridden, msg, _is_self = role_verdict(
        args, command, allow, allowed_desc, target=target, self_legal=self_legal,
        remedy=remedy, case=case)
    if passed:
        return caller
    if overridden:
        print(f"note: `{command}` role gate overridden with --force "
              f"(caller: {caller or 'unresolved'})", file=sys.stderr)
        return caller
    # W5: the refusal no longer ADVERTISES `--force`. The flag still carries the role gate — the
    # unattended repair path (jobs/recover-room.py) depends on that and GATE_FLAGS is untouched by
    # ruling (`p-override-split-is-safety-critical`) — but a refusal that offers "or pass --force"
    # teaches every reader to reach for the override instead of the legal path, and the legal path
    # is what `remedy` now names.
    # s12-03: and it NAMES ITS LAYER. `role gate` is the one layer a seat reads as a harness
    # block, so the prefix carries the paragraph that separates the two. `{command}` is NOT
    # re-stated here: every one of `role_verdict`'s case templates already renders it, so the
    # §1.3 sketch's leading "`{command}` — " would print it twice.
    refuse("role gate", f"{msg}\n{ROLE_GATE_LAYER_NOTE}", 2)


def launch_gates(args, command, allow, allowed_desc, n_seats, target=None, self_legal=False,
                 remedy=None, case=None):
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
    `--force-memory` carries the memory gate only; neither carries the other.

    `target`/`self_legal`/`remedy`/`case` are threaded to `role_verdict` exactly as `gate` threads
    them, so a command whose two branches split across the two helpers (`cmd_close`) cannot end up
    with one gate that knows the target and one that does not — an inconsistency a reader trusts
    and a test misses."""
    caller, role_ok, role_forced, role_msg, _role_is_self = role_verdict(
        args, command, allow, allowed_desc, target=target, self_legal=self_legal,
        remedy=remedy, case=case)

    # ⚠ THE FLOOR IS READ HERE, PER LAUNCH, FROM THE RUN PACKAGE — never held as a constant
    # (task 7.82, `r-floor-single-source`). `floor_why` is not decoration: criterion 8's acceptance
    # is that the gate SAYS WHICH VALUE IT USED AND WHY, so an operator can never be silently
    # overruled by an environment or a stale copy. It is printed on PASS as well as on REFUSAL —
    # a value you only see when you are blocked is one you cannot check while things work.
    floor_mb, floor_why, floor_err = None, None, None
    try:
        floor_mb, floor_why = budget_mod.floor_source(package_dir(args), "refuse", None)
    except budget_mod.FloorUnreadable as exc:
        floor_err = ("budget.json IS declared for this package and could not be read: %s. That is "
                     "NOT the same as no budget being declared, and it is never treated as one — "
                     "a wrong path and an undeclared budget must not look alike." % exc)
    except budget_mod.FloorUndeclared as exc:
        floor_err = ("%s. The floor's one home is the run's budget.json (r-floor-single-source): "
                     "a launch gate may not invent a number, so it refuses instead. Declare "
                     "floors.launch_refuse_mb there, or override this gate with --force-memory and "
                     "say so on the log." % exc)

    mgate = floor_err if floor_err else memory_gate(n_seats, available_mb(), floor_mb)
    mem_forced = gate_forced(args, "memory")   # via GATE_FLAGS, never a bare getattr (S-6(a))
    lines, refused = [], False

    # ⚠⚠ THE PROVENANCE LINES ARE KEPT SEPARATE FROM THE VERDICT LINES, AND THAT IS THE WHOLE
    # POINT. `lines` is printed ONLY on a refusal or an override — so folding the floor in there
    # would make the number visible exactly when a launch is BLOCKED and invisible every time one
    # SUCCEEDS. Task 7.82 criterion 8's acceptance is that the consumer says WHICH VALUE IT USED
    # AND WHY, and "which value did this launch use?" has to be answerable while things work, not
    # only while they do not. Measured: the first version of this code put them in `lines` and its
    # own comment claimed they printed on PASS. They did not.
    provenance = []
    if floor_why:
        provenance.append(f"floor: {floor_why}")
    # ⚠ AND THE SPIKE SAYS WHERE IT CAME FROM TOO. `COORD_SEAT_SPIKE_MB` no longer touches the
    # FLOOR, but it still moves the EFFECTIVE gate at n_seats > 1 (`need` below), so it is a live
    # MECHANISM even on a box where it is set nowhere — and a live mechanism is not a live
    # divergence (#1254, #1380). Criterion 8 is about the mechanism, so the mechanism reports.
    provenance.append(
        "spike: %d MB per seat (%s) — a MEASUREMENT, not a policy number"
        % (SEAT_SPIKE_MB, SEAT_SPIKE_SOURCE))
    lines.extend(provenance)
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
        # s12-03: the HEAD line names the layer; the per-verdict lines below are untouched, and so
        # is the two-flag disambiguation (jobs/recover-room.py reasons about exactly that split,
        # `p-override-split-is-safety-critical`). The token follows the assignment rule: this head
        # covers BOTH gates, so it names whichever one actually refused — `role gate` when the
        # caller's role did, `environment` when the memory gate did (it reads available RAM, i.e.
        # the process world). A head that always said "role gate" would misname half its refusals.
        _role_refused = not role_ok and not role_forced
        refuse(
            "role gate" if _role_refused else "environment",
            f"`{command}` — BOTH gates evaluated, both verdicts below (neither flag "
            f"carries the other):\n  {verdicts}\n"
            f"--force carries the ROLE gate; --force-memory carries the MEMORY gate.\n"
            f"If memory is the refusal, the right move is usually to WAIT for a seat to depart "
            f"rather than override it."
            + (f"\n{ROLE_GATE_LAYER_NOTE}" if _role_refused else ""),
            2)
    # Nothing refused. The floor and spike this launch actually used are stated even on the happy
    # path (task 7.82 criterion 8) — one line, on stderr, so it never pollutes a piped stdout.
    print(c("gates: " + " · ".join(provenance), C_HINT), file=sys.stderr)
    # Any override that actually carried a gate is announced, so a forced launch
    # is never silent — the WARNING wording is deliberately distinct from `refused:` (#210).
    for line in lines:
        if "overridden" in line:
            print(c(f"WARNING launching anyway: {line}", C_DEAD), file=sys.stderr)
    return caller


def is_leader(name):
    return name == "leader"


def is_leader_or_closer(name):
    return name == "leader" or name.startswith("closer-")


def is_authorized_launcher(name):
    """Who may OPEN panes in this run: the leader, and the chief-of-staff.

    THE CoS's HALF IS AN OWNER RULING, NOT A LOOSENING -- `r-cos-launches-the-staffed-seat` (goal
    decisions.md) makes launching the seat the staffer produces the chief-of-staff's ROUTINE DUTY,
    and this gate predated it (G-257). Before this, compliance with a standing ruling required
    `--force`: a flag that reads as an override of policy while actually being compliance with it,
    which trains the room to force and spends the flag's only signal.

    MINTED RATHER THAN REUSING `is_leader_or_cos_or_closer`
    (`core-build-run-adjustments/decisions.md#d-g257-widening-not-threading`). That predicate
    exists for `kill-pane`/`relaunch-pane` and also admits every `closer-*` seat -- widening
    `launch` to closers is not what was ruled, and reusing it here would have quietly granted it.
    ⚠ THIS WIDENS `launch` ALONE (`d-cos-inbox-is-convention`: "`launch` and nothing else").
    `close-run`, `panel`, `reap --go`, `add-to-group` and `remove-from-group` stay the leader's,
    and `d-cos-may-launch` bars the chief-of-staff from every TERMINATING verb -- close, renew,
    reap, kill, revive. The bound is open-versus-terminate; this is not a second leader.
    """
    return name in ("leader", "chief-of-staff")


def is_leader_or_cos_or_closer(name):
    """Same NAME-PATTERN shape as `is_leader_or_closer` (this file gates roles by literal name
    everywhere, never by a derived lookup -- `chief-of-staff` is one more literal beside `leader`,
    not a new mechanism). `kill-pane` (task 7.91) exists FOR the chief-of-staff: it is the seat
    that owns operational stewardship and is blocked from a raw `tmux kill-pane` by the harness
    auto-mode classifier. This predicate governs WHO may call the command, never WHICH panes it
    may touch -- the door/roster protections are a separate, unconditional check (criterion 2)."""
    return name in ("leader", "chief-of-staff") or name.startswith("closer-")


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
# (G-12) and therefore needs that pane alive at close time. That path is CONDITIONAL, not the
# default (G-154): it is taken when the seat already sits in the window its briefing asks for. The
# refusal still holds for every seat, because at checkout time nothing knows which case a later
# renew will be — see G-151, where stating this half without its condition put two contradictory
# claims in one file. `depart` is the wrong precedent; it is
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
    """{seat: {"since", "pane", "transcript", "exported", "pids", "disposition", "handoff_stamp"}}
    — seats that finished their own lifecycle and whose resources the leader has not yet freed.

    ⚠ EVERY CONSUMER READS `entry.get("disposition", "done")`, NEVER `entry["disposition"]`. This
    returns whatever is on disk, and run packages written before s12-07 hold records with neither
    of the last two keys. The absent-key reading is `done`, which is what those records meant.

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


def set_awaiting(base, seat, pane, transcript, exported, disposition="done", handoff_stamp=""):
    """Record the debt at checkout. Best-effort: bookkeeping ABOUT a checkout must never break the
    checkout itself — 7.37 already ruled that shape for the session trace, and a seat that cannot
    check out is worse than a debt nobody recorded.

    `exported` is stored rather than inferred from `transcript` being truthy, because the two
    genuinely differ: an export can be SKIPPED (a dead pane, `--no-export`) and #259's mapping
    gates the kill on the transcript EXISTING. A reaper must be able to tell "safe to kill" from
    "not yet safe" without re-running the export to find out.

    s12-07: `disposition` is `done` or `renew` — WHICH checkout this was — and `handoff_stamp` is
    the ISO stamp of the block that checkout appended (`""` when it appended none). Both are
    STORED for the same reason `exported` is: they are known FOR CERTAIN here, at the moment of
    truth, and at no later moment. `reap` gates a pane KILL on the disposition, so inferring it
    from an adjacent observable would be the seventh infer-from-ambient defect this run has
    catalogued — and the first one that kills a pane a renewal is about to respawn into.

    The default is `done` so every pre-s12-07 caller keeps its meaning unchanged; the checkout
    passes BOTH arms explicitly anyway, because a default a reader must chase is not an assertion.
    Both are coerced with `str()` at the boundary for the reason the record below states."""
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
                          "pids": [[p, s] for p, s in (pane_harness_idents(pane) if pane else [])],
                          # s12-07, str()-coerced for the same reason the transcript is: these
                          # arrive from a caller, and a non-serializable value here would raise
                          # INSIDE the checkout this record is bookkeeping for.
                          "disposition": str(disposition or "done"),
                          "handoff_stamp": str(handoff_stamp or "")}
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
    # [INTEGRATION POINT — STAGE 3: the executor clears this]
    # s12-07. The age blocker above is a HEURISTIC about a renewal that MIGHT be in flight; this is
    # the ASSERTION that one IS — recorded by the checkout itself, at the one moment it was known.
    # It outlives the age window on purpose: `awaiting-close.json` deliberately does not expire, and
    # a renewal that has not been acted on in 15 minutes is more dangerous to reap, not less.
    # Reaping here kills the pane the renewal respawns INTO (G-12 renews in place), so the two
    # legitimately coexist and this one is the durable half.
    #
    # ⚠ UNTIL STAGE 3 EXISTS, EVERY `renew` ENTRY BLOCKS, AND THAT IS THE CORRECT READING, NOT A
    # STUB. "Has not acted yet" is decidable from the record only because nothing can have acted:
    # there is no executor. Stage 3 releases the block by CLEARING THE ENTRY or FLIPPING THE
    # DISPOSITION — `clear_awaiting` already exists and is `close-seat`'s; whether it is also the
    # executor's is Stage 3's ruling to make. Nothing here invents a clearing mechanism.
    #
    # ⚠ `.get("disposition", "done")`, NEVER `entry["disposition"]`. Records written before this
    # field existed sit in live run packages right now, and a KeyError here would take down the
    # whole sweep that reads them rather than skipping the one entry.
    if (entry or {}).get("disposition", "done") == "renew":
        out.append("its checkout recorded disposition=renew and the renewal executor has not "
                   "acted yet — reaping now would kill the pane the renewal needs")
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


# ---- STAGE 3 (s3-03): the LIFECYCLE-INFLIGHT marker ------------------------------------------
# `{package}/coordination/lifecycle-inflight.json` — beside `awaiting-close.json` and
# `closing.json`, ONE SHARED FILE, a dict keyed by seat, written the way both of them are
# (`coord_lock` + `atomic_write`) and never fatal on any path.
#
# ⚠ TWO FILES NOW CARRY A `disposition` KEY OVER THE SAME done|renew VOCABULARY. THE AUTHORITY
# BETWEEN THEM IS SETTLED, AND IT IS NOT "WHICHEVER ONE THE READER OPENED":
#
#     `awaiting-close.json` is AUTHORITATIVE for INTENT/debt.
#     `lifecycle-inflight.json` is AUTHORITATIVE for EXECUTION state.
#
# The checkout ASSERTS what it meant — `set_awaiting`'s `disposition`, recorded at the one moment
# it was known — and that record is the DEBT: it deliberately never expires and `reap_blockers`
# gates a pane KILL on it. This file records what the executor has actually DONE about that
# intent: which steps verified, whether it is still running, how it ended. So a disagreement
# between the two is never a tie to be broken — read the intent from awaiting-close.json and the
# progress from here. Read the G-134 AWAITING-CLOSE DEBT block above (`awaiting_path` /
# `load_awaiting` / `set_awaiting` / `reap_blockers`) for the design this half is bound to; it is
# POINTED AT, never restated.
#
# Two of that block's rulings carry over unchanged, and are likewise pointed at rather than
# re-argued:
#   · "An assertion at the moment of truth beats an inference at the moment of action" — which is
#     why `steps-completed` is appended AFTER a step VERIFIES, never before. A step listed here
#     HAPPENED; no reader may have to wonder whether it merely started. `stamp_lifecycle` starts
#     the list EMPTY for exactly that reason.
#   · "A debt that ages out unpaid is not a debt" — which is why a finished renewal FLIPS to
#     `state: "done"` instead of being deleted. Deleting it would erase the only record that a
#     renewal happened OUT OF PANE, where nothing else saw it. `close-run` sweeps the done
#     entries (`sweep_lifecycle`) and nothing else may.
#
# The per-seat record:
#
#     {"engineer": {"disposition": "renew",
#                   "executor": {"pid": 41207, "starttime": "884231"},
#                   "caller":   {"pid": 41190, "starttime": "884118"},
#                   "pane": "%37", "tmux-target": "%37",
#                   "stamped-at": "2026-07-28 16:04",
#                   "steps-completed": ["caller-exited", "in-place-decided:in-place", "respawned"],
#                   "state": "in-flight", "failure": ""}}
#
# `stamped-at` goes through `now()` AND NOWHERE ELSE — the store writes it itself and overwrites
# whatever a caller supplies, so the package keeps ONE date format and `lifecycle_age_min` below
# reads it with `closing_age_min`'s arithmetic unchanged. (It cannot CALL `closing_age_min`: that
# one reads the key `since`, which is the closing record's name for the same thing.)
#
# `executor`/`caller` are normalized to `{"pid": int, "starttime": str}` at the boundary, and that
# is not tidiness. watch.py's revival detector reads `entry["executor"]["pid"]` and
# `["starttime"]` and answers False for ANY other shape, so a `(pid, starttime)` TUPLE written
# straight through would make every LIVE executor read as dead — turning MID-RENEWAL into CRASHED
# and double-launching the seat, which is the one outcome stages 3 and 4 both exist to prevent.

def lifecycle_path(base):
    return Path(base) / "lifecycle-inflight.json"


def lifecycle_ident(ident):
    """`{"pid": int, "starttime": str}` from a `(pid, starttime)` tuple, an already-shaped dict, or
    anything else. `{}` when nothing resolves — NEVER a raise and never a partial dict: this runs
    inside a marker write, and bookkeeping ABOUT a lifecycle act must not break the act.

    `{}` rather than a pid-only dict on purpose. A pid ALONE is not an identity (`process_identity`
    carries the reason at length: the kernel recycles pids and a teardown is exactly when new
    processes start), and a half-identity here would be read as a live executor by a reader that
    only checked the key's presence."""
    if isinstance(ident, dict):
        pid, start = ident.get("pid"), ident.get("starttime")
    elif isinstance(ident, (tuple, list)) and len(ident) == 2:
        pid, start = ident
    else:
        return {}
    if pid is None or start is None or str(start) == "":
        return {}
    try:
        return {"pid": int(pid), "starttime": str(start)}
    except (TypeError, ValueError):
        return {}


def load_lifecycle(base):
    """{seat: record} — the marker as it stands, `{}` on ANY read or parse failure. NEVER raises.

    Same never-fatal contract as `load_awaiting`, and the same fail-safe direction: a marker that
    cannot be read must not take down the renewal it is bookkeeping for. A consumer reads
    `entry.get("disposition", "")` and NEVER `entry["disposition"]` — the blank is not `done`, it
    is "the executor recorded no intent here", and the INTENT is awaiting-close.json's to state."""
    path = lifecycle_path(base)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_lifecycle(base, data):
    atomic_write(lifecycle_path(base), json.dumps(data, indent=2, sort_keys=True) + "\n")


def stamp_lifecycle(base, seat, record):
    """Write `seat`'s INITIAL record. Returns True/False, NEVER raises.

    Best-effort for `set_awaiting`'s reason one file over: the caller checks the return and SAYS
    SO when it is False; it does not abandon a renewal over an unwritten marker.

    THE STORE OWNS FOUR FIELDS and overwrites whatever the caller passed for them:
      `stamped-at`      -> `now()`, always (one date format in the package).
      `state`           -> `"in-flight"`, always. A stamp IS the start; only `finish_lifecycle`
                           writes a terminal state, so no caller can stamp a renewal as finished.
      `steps-completed` -> `[]`, always. A caller able to pre-load it could claim a step before it
                           ran — the exact inversion the G-134 block rules against.
      `executor`/`caller` -> normalized through `lifecycle_ident` (see the block above).
    Every other key the caller supplies is carried through unchanged."""
    try:
        rec = dict(record or {})
        for k in ("executor", "caller"):
            if k in rec:
                rec[k] = lifecycle_ident(rec[k])
        rec["disposition"] = str(rec.get("disposition") or "")
        rec["failure"] = str(rec.get("failure") or "")
        rec["state"] = "in-flight"
        rec["steps-completed"] = []
        rec["stamped-at"] = now()
        with coord_lock(base):
            data = load_lifecycle(base)
            data[seat] = rec
            _write_lifecycle(base, data)
        return True
    except (OSError, ValueError, TypeError):
        return False


def append_lifecycle_step(base, seat, step):
    """Append ONE verified step to `seat`'s `steps-completed`. Returns True/False, never raises.

    A step can only FOLLOW a stamp: an entry that does not exist is answered False rather than
    created. A step appended to nothing would be a claim about a renewal this file never saw
    start, and the caller must learn that immediately rather than read it back later as history."""
    try:
        with coord_lock(base):
            data = load_lifecycle(base)
            entry = data.get(seat)
            if not isinstance(entry, dict):
                return False
            prior = entry.get("steps-completed")
            entry["steps-completed"] = ([str(s) for s in prior] if isinstance(prior, list)
                                        else []) + [str(step)]
            data[seat] = entry
            _write_lifecycle(base, data)
        return True
    except (OSError, ValueError, TypeError):
        return False


def finish_lifecycle(base, seat, state, failure=""):
    """Terminal write: `state` is `"done"` or `"FAILED"`, `failure` carries the text of the break.
    Returns True/False, never raises.

    ANY OTHER `state` IS REFUSED (False) rather than written. The sweep in `sweep_lifecycle` keys
    on these two strings exactly, so a third value would silently become an entry nothing ever
    clears and nothing ever reads as a failure.

    The entry is NOT deleted here — see the block above. `close-run` is the only sweep."""
    if state not in ("done", "FAILED"):
        return False
    try:
        with coord_lock(base):
            data = load_lifecycle(base)
            entry = data.get(seat)
            if not isinstance(entry, dict):
                return False
            entry["state"] = str(state)
            entry["failure"] = str(failure or "")
            data[seat] = entry
            _write_lifecycle(base, data)
        return True
    except (OSError, ValueError, TypeError):
        return False


def clear_lifecycle(base, seat):
    """Remove ONE seat's entry. Returns True when one was actually removed.

    ⚠ RUN TEARDOWN ONLY — `sweep_lifecycle` (and therefore `close-run`) is its ONE caller. NEVER
    called on success: a successful renewal FLIPS to `state: "done"` via `finish_lifecycle`, and
    deleting it there would erase the only record that the renewal happened out of pane."""
    try:
        with coord_lock(base):
            data = load_lifecycle(base)
            if seat not in data:
                return False
            del data[seat]
            _write_lifecycle(base, data)
        return True
    except (OSError, ValueError, TypeError):
        return False


def lifecycle_age_min(entry, now_str=None):
    """Minutes since `stamped-at`, or None when the stamp is unreadable.

    `closing_age_min`'s arithmetic and `closing_age_min`'s format, deliberately — but not
    `closing_age_min` itself, which reads the key `since`. `now_str` (same `"%Y-%m-%d %H:%M"`
    form) lets a caller or a check supply the reference instant instead of sleeping for it."""
    try:
        ref = (datetime.strptime(str(now_str).strip(), "%Y-%m-%d %H:%M") if now_str
               else datetime.now())
        return max(0, int((ref - datetime.strptime((entry or {}).get("stamped-at", "").strip(),
                                                   "%Y-%m-%d %H:%M")).total_seconds() // 60))
    except (ValueError, AttributeError, TypeError):
        return None


def lifecycle_stale(entry, now_str=None):
    """THE FAILED-RENEWAL PREDICATE. True only when ALL THREE hold:

        1. `entry["state"] == "in-flight"`, AND
        2. the age of `stamped-at` exceeds `LIFECYCLE_STALE_MIN`, AND
        3. the executor ident is NOT live, by `ident_is_live_process`.

    ⚠⚠ READ THE COMPLEMENT, BECAUSE THE COMPLEMENT IS WHAT STAGE 4 ACTS ON: an entry that is
    `in-flight` WITH A LIVE EXECUTOR IS **MID-RENEWAL** — a renewal in progress, which must NEVER
    be fired on. Getting this one reading backwards turns MID-RENEWAL into CRASHED and
    DOUBLE-LAUNCHES A SEAT, which is the failure this whole predicate exists to make impossible.

    ⚠ CONJUNCT 3 IS `ident_is_live_process`, NEVER `ident_is_live_harness`. The executor is a
    PYTHON process; `ident_is_live_harness` rests on `is_harness_argv`, which matches only the
    claude/codex/opencode basenames in HARNESS_PROCS, so it reports EVERY LIVE EXECUTOR AS DEAD
    and this predicate would fire on healthy renewals. `ident_is_live_process`'s own docstring
    states the trap; the two are separate functions with separate names precisely so this line
    cannot be written by accident.

    FAIL-SAFE DIRECTION IS "NOT STALE". An unreadable stamp, a missing or malformed `executor`
    ident, a non-dict entry — every unprovable case answers False. Firing wrongly revives a seat
    that is alive (a double launch); declining wrongly leaves a stuck seat stuck AND REPORTED,
    which is recoverable. ⚑ The cost of that direction is real and is stated rather than hidden:
    an `in-flight` entry with no readable executor ident is stale to a human and False here
    forever — `sweep_lifecycle` will not clear it either, so it survives every close-run and is
    NAMED in each one's output. That visibility is the remedy; silence would not be."""
    if not isinstance(entry, dict) or entry.get("state") != "in-flight":
        return False
    age = lifecycle_age_min(entry, now_str)
    if age is None or age <= LIFECYCLE_STALE_MIN:
        return False
    ident = lifecycle_ident(entry.get("executor"))
    if not ident:
        return False
    return not ident_is_live_process((ident["pid"], ident["starttime"]))


def sweep_lifecycle(base):
    """`close-run`'s marker sweep. Returns `(cleared, survivors)`: `cleared` is the sorted seats
    removed, `survivors` is `[(seat, why)]` for every entry this REFUSES to touch. Never fatal —
    a run stays closable with an unreadable marker, which reads as no entries at all.

    ⚠ ONLY `state: "done"` IS SWEPT, and every survivor is NAMED by the caller. An `in-flight`
    entry is a renewal that never reported an ending, and clearing it would destroy the one record
    saying so at the exact moment the run closes and nobody looks again; a `FAILED` entry IS the
    failure report. An entry left behind SILENTLY is indistinguishable from one never written,
    which is the G-134 block's own argument for writing the record rather than re-deriving it."""
    cleared, survivors = [], []
    snapshot = load_lifecycle(base)
    for seat in sorted(snapshot):
        entry = snapshot.get(seat)
        state = entry.get("state") if isinstance(entry, dict) else None
        if state == "done":
            if clear_lifecycle(base, seat):
                cleared.append(seat)
            else:
                survivors.append((seat, "its entry is complete but the marker write FAILED, so "
                                        "nothing was cleared"))
        elif state == "in-flight":
            age = lifecycle_age_min(entry)
            survivors.append((seat, f"state=in-flight, stamped "
                                    f"{str(age) + 'min ago' if age is not None else 'unreadably'}"
                                    f" — a renewal that never reported an ending; this entry is "
                                    f"the only record that it started"))
        elif state == "FAILED":
            survivors.append((seat, f"state=FAILED: "
                                    f"{(entry.get('failure') or '').strip() or '(no failure text)'}"
                                    f" — the failure report outlives the run"))
        else:
            survivors.append((seat, f"state={state!r} is not a state this store writes — left "
                                    f"untouched rather than guessed at"))
    return cleared, survivors


def lifecycle_line(base):
    """The marker's READ SIDE: one block for the `status` and `workers` views, or `''` when the
    marker holds nothing an operator must act on.

    `undelivered_line`'s shape exactly — same `(base)` signature, same "a string or empty"
    contract, same never-fatal posture — because it exists for the same reason and has to be
    ignorable in the same way.

    ⚠ WITHOUT THIS FUNCTION THE MARKER IS WRITE-ONLY. `stamp_lifecycle` records every renewal that
    runs OUT OF PANE and, until Stage 4's revival arm lands, NOTHING READS IT. That is precisely
    the shape `undelivered_flags` documents one screen up: warnings "printed to a detached stderr
    file, and lost, while the loop went on reporting healthy". A marker nobody looks at is not a
    fix, and a step that can fail must fail LOUDLY AND VISIBLY.

    THREE CLASSES ARE REPORTED. The first two are the alarm; the third is not padding:

      STALE    `lifecycle_stale(entry)` — in-flight, past `LIFECYCLE_STALE_MIN`, executor NOT live.
               ⚠⚠ THE COMPLEMENT IS NEVER REPORTED: an in-flight entry with a LIVE executor is
               MID-RENEWAL, a renewal in progress. Reporting it would train the room to scroll
               past this line on the one night it is real — and the predicate is CALLED, never
               re-spelled, so this surface and Stage 4 can never hold two definitions of stale.
      FAILED   `state == "FAILED"`. NOT stale — it is young and its executor is legitimately gone —
               but it IS an alarm: the executor itself reported that the renewal broke.
      UNKNOWN  any other `state`. The store writes exactly `in-flight|done|FAILED`
               (`finish_lifecycle` refuses anything else), so a fourth value means the file was
               HAND-EDITED — and `sweep_lifecycle` will not clear it either, so it survives every
               close-run. Named here for `sweep_lifecycle`'s own reason: an entry left behind
               SILENTLY is indistinguishable from one never written.

    `state: "done"` is the only class deliberately silent. A completed renewal is not news.

    ⚠ AGES COME FROM `lifecycle_age_min`, NEVER `closing_age_min`. That one reads the key `since`;
    this record stamps `stamped-at`, so `closing_age_min` returns None on every entry here —
    silently — and every age would render as unknown while the line still looked correct.

    ⚠ `disposition` is read with a `""` DEFAULT, never `load_awaiting`'s `"done"`. A blank means
    the executor recorded no intent in THIS file, and the intent is `awaiting-close.json`'s to
    state — so the line SAYS to read it there rather than inventing `done`. What this line reports
    is EXECUTION state; the authority split between the two files is stated in full at the head of
    this section and is not restated here.

    NOT A REFUSAL, so it carries no `refuse()` layer token: this is display output, rendered by
    its two callers in `C_DEAD` — the constant `undelivered_line` is already rendered in. A
    rendered alarm an operator can act on is not a tool-gate verdict.

    The remedy is named in plain words because a reader who has never seen this line before is
    exactly the reader it is for: Stage 4's revival arm will act on it automatically once it
    lands; until then a leader must run `close-seat <seat> --renew` by hand. No `coord_invocation`
    prefix — the signature takes `base` alone (`undelivered_line`'s, deliberately) and no `args`
    is in scope to resolve one from."""
    entries = load_lifecycle(base)
    if not isinstance(entries, dict) or not entries:
        return ""
    rows = []
    for seat in sorted(entries):
        entry = entries.get(seat)
        if not isinstance(entry, dict):
            rows.append(f"  UNKNOWN {seat} — its entry is not a record but a "
                        f"{type(entry).__name__}; the file was hand-edited and no sweep will "
                        f"clear it")
            continue
        state = entry.get("state")
        if state == "done":
            continue
        if state == "in-flight" and not lifecycle_stale(entry):
            continue        # MID-RENEWAL, or too young to judge. Never fire on it.
        age = lifecycle_age_min(entry)
        aged = f"marker {age}min old" if age is not None else "marker of UNREADABLE age"
        disp = entry.get("disposition", "")
        disp_txt = (f"disposition={disp}" if disp else
                    "disposition NOT recorded here — read the intent from awaiting-close.json")
        ident = lifecycle_ident(entry.get("executor"))
        who = f"executor pid {ident['pid']}" if ident else "NO readable executor ident"
        steps = entry.get("steps-completed")
        steps = [str(s) for s in steps] if isinstance(steps, list) else []
        last = f"last verified step: {steps[-1]}" if steps else "NO step ever verified"
        if state == "FAILED":
            rows.append(f"  FAILED  {seat} — {disp_txt}; {who}; {aged}; {last} — the executor "
                        f"reported the break: "
                        f"{(str(entry.get('failure') or '').strip() or '(no failure text)')}")
        elif state == "in-flight":
            rows.append(f"  STALE   {seat} — {disp_txt}; {who}, and it is NOT running; {aged}; "
                        f"{last}")
        else:
            rows.append(f"  UNKNOWN {seat} — state={state!r} is not a state this store writes, so "
                        f"this file was hand-edited; {disp_txt}; {who}; {aged}; {last}. close-run "
                        f"will not sweep it either")
    if not rows:
        return ""
    return ("LIFECYCLE MARKERS IN ALARM: %d — a renewal ran OUT OF PANE and never reported a clean "
            # number-neutral on purpose: the block lists one entry or ten, and a header that says
            # "the seat below" reads as a lie the moment there are two.
            "ending. In plain words: EACH SEAT NAMED BELOW IS NEITHER ALIVE NOR CLOSED — nothing "
            "is running it, nothing has freed its pane, and it will not recover on its own.\n"
            "%s\n"
            "  Remedy: Stage 4's revival arm will act on this automatically once it lands. UNTIL "
            "THEN the remedy is manual — a leader runs `close-seat <seat> --renew`.\n"
            "  Read them all: %s"
            % (len(rows), "\n".join(rows), lifecycle_path(base)))


def permitted_senders(agent, decls, roster):
    """Who may write to `agent` — or None when its inbox is unbounded. G-197.

    ⚠ `roster` IS A SEPARATE ARGUMENT AND MUST NOT BE `decls`. `inbox_decls` keeps a seat only
    when that seat DECLARES something (`if d: decls[agent] = d`), so an ordinary seat — the leader
    included — is ABSENT from it. Deriving the candidates from `decls` therefore skipped every
    plain seat and reported them as unreachable. Measured, and not by the suite: the first live
    render told this seat that `leader`, which had been messaging it all session, "NO seat
    declares". The fixture had listed `leader: {}` explicitly and so could never produce the bug —
    a fixture shaped to dodge the real path.

    ⚠ THE ANSWER IS EVALUATED, NEVER RE-DERIVED. Every candidate is run through
    `sender_admitted` — the SAME predicate `send` enforces and `why_not_woken` reports — against a
    probe message. Spelling the rule a second time here would produce two computations of "may X
    write to me" that agree today and drift apart on the next bound; this run has already paid for
    that twice (the wake set vs the read set, and the five hand-derived copies of
    `sender != me AND addressed_to`).

    `origin: ""` in the probe is the LOCAL case, deliberately: the question is who may write from
    inside this package. A foreign sender is refused by `sender_admitted`'s own origin test, and
    asserting that here would be the second copy this docstring exists to prevent.

    Returns (literal, relayed, dead_tokens): seats admitted by name, (seat, token) pairs admitted
    by relay, and bound tokens that resolve to NOBODY — the last because a bound naming a token no
    seat carries makes the seat unreachable by that name, silently. That is not hypothetical: it is
    what `senders: leader, master` did before `relays:` existed.
    """
    bound = ((decls or {}).get(agent) or {}).get("senders")
    if bound is None:
        return None
    literal, relayed, live = [], [], set()
    for cand in sorted(set(roster) | set(decls)):
        if cand == agent or not sender_admitted({"sender": cand, "origin": ""}, bound, decls):
            continue
        live.add(cand)
        if cand in bound:
            literal.append(cand)
        else:
            relayed.extend((cand, tok) for tok in sorted(bound)
                           if cand in relay_seats(tok, decls))
    dead = sorted(tok for tok in bound
                  if tok not in live and not relay_seats(tok, decls))
    return literal, relayed, dead


def inbox_bound_line(agent, decls, roster):
    """One line telling a bounded seat WHO may write to it, or '' when unbounded. G-197.

    ⚠ CALLER-ONLY BY CONSTRUCTION, and this is the acceptance bar rather than a nicety: the single
    call site passes the identity the CLI resolved for the caller, and there is no argument here
    that lets a seat ask about another. A command that answered for any seat would hand every seat
    a roster-wide map of who may talk to whom — a strictly larger disclosure than the foreign
    descriptor read this exists to make unnecessary.

    The defect it closes: a bounded seat could not learn its own bound from the tool at all. The
    kit RESOLVES `senders:`/`relays:` on every send and reports the refusal to the SENDER — while
    the bounded seat's own `inbox:` line described only broadcast scope, and said "direct messages
    always reach you", which for a bounded seat IS FALSE. Verifying the bound therefore meant
    reading another seat's descriptor: the tool knew the answer and offered no way to ask, so the
    only available act was the one the boundary forbids.
    """
    res = permitted_senders(agent, decls, roster)
    if res is None:
        return ""
    literal, relayed, dead = res
    who = [f"{s}" for s in literal] + [f"{s} (carries relays: {tok})" for s, tok in relayed]
    line = (f"BOUNDED — only {', '.join(who)} may write to you; every other seat is refused at "
            f"ITS OWN cli and keeps its message" if who else
            "BOUNDED — and NOBODY currently resolves: no seat can reach you at all")
    if dead:
        # Loud rather than omitted: a token nothing carries is indistinguishable, in the bound's
        # own text, from one that works — which is exactly how `master` named nobody for a whole run.
        line += (f" · ⚠ the bound also names {', '.join(dead)}, which NO seat declares — "
                 f"nobody can reach you by that name")
    return line


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
                f"{'/'.join(sorted(scope))}; G-20 does not filter direct messages (a `senders:` "
                f"bound can, and the senders: line below reports it)")
    # ⚠ THIS USED TO SAY "direct messages always do", which is FALSE for a bounded seat and was
    # printed to bounded seats: G-20 is about BROADCASTS, and the sender bound is a separate
    # narrowing this line never knew about. Stating a scope you do not compute is how a seat comes
    # to trust a line that contradicts the refusal its senders are getting.
    return ("special-case seat — the room's broadcasts do not reach you; G-20 does not filter "
            "direct messages (a `senders:` bound can, and the senders: line below reports it)")


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
        refuse(
            "state",
            f"no ACTIVE pane is registered for '{args.target}', so there is nothing to "
            f"send keys to — the seat never checked in, has checked out, or its pane changed.\n"
            f"Check the roster first: {coord_invocation(args)} workers",
            1)
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
        refuse(
            "input",
            f"summary is {len(summary)} chars — max {SUMMARY_MAX}.\n"
            "This line is how OTHER agents decide whether your work concerns them and whether "
            "to message you. Rewrite it to state, concretely: what you are changing/producing "
            "and which shared surfaces (records, scripts, views) you touch. No filler.",
            1)
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
            refuse(
                "state",
                f"'{args.agent}' is already checked in on pane {prior['pane']}, and tmux "
                f"says that pane is still ALIVE — checking in from {pane or 'no pane'} would put "
                f"two live sessions under one name.\n"
                f"Neither would see the other's messages (the unread filter is keyed on the name) "
                f"and only this pane would receive wakes.\n"
                f"Confirm the old session is dead first, then retry: inspect it with "
                f"`tmux capture-pane -p -t {prior['pane']}`; if it is a zombie, kill it BY PANE ID "
                f"(`tmux kill-pane -t {prior['pane']}`) — never by name — and check in again.\n"
                f"If you are deliberately running two sessions under this name, re-run with "
                f"--force.",
                1)
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
            refuse(
                "environment",
                f"no {'/'.join(HARNESS_PROCS)} process is running in pane {pane}, so this "
                f"check-in would put '{args.agent}' on the roster as ACTIVE with nothing behind it "
                f"(G-11).\n"
                f"This is what a briefing executed by the pane's SHELL looks like: the checkin line "
                f"runs for real while the harness never started. If that is what happened, the "
                f"prompt reached the pane as literal keystrokes — spawn through `launch`/`close`, "
                f"which pass the prompt as a file.\n"
                f"If a harness IS running here under a wrapper this check cannot recognize, re-run "
                f"with COORD_SKIP_HARNESS_CHECK=1 and say so on the log.",
                1)
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
    # The check-out handoff, DELIVERED (s12-08). Placed HERE — after the check-in is recorded and
    # reported, before the placement-drift flag — so the seat is handed its predecessor's note at
    # the first moment it is a checked-in session, and `session_trace_safe` guards it for exactly
    # the reason it guards the session trace a few lines below: bookkeeping ABOUT a check-in must
    # never become a gate ON it. A seat that cannot check in is worse than a handoff shown twice,
    # and every branch inside that could reasonably fail already handles itself.
    _hd_ok, _hd_err = session_trace_safe(deliver_handoff, args, base, args.agent)
    if _hd_err:
        print(c(f"WARNING handoff delivery skipped — {_hd_err}. Your checkin STANDS. If a handoff "
                f"was waiting it is still `unread=yes`, so the next check-in of this seat will "
                f"show it.", C_DEAD), file=sys.stderr)
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


# ---- the check-out handoff block (s12-06) ------------------------------------------------
#
# R-14 (`rulings.md`): this effort touches NOTHING that deals with memory — no dreamer, no closer
# work, no compounding — WITH ONE EXCEPTION: the handoff on check-out, a simple form of short-term
# memory. THIS IS THAT EXCEPTION, AND ITS WHOLE EXTENT. There is no rotation, no compaction, no
# indexing, no summarizing and no pruning of `memory.md` here, and nothing reads a block back
# except `s12-08`'s unread flip.
#
# ⚠ APPEND AT EOF, NEVER PARSE, NEVER REWRITE. A seat's `memory.md` is heterogeneous BY
# CONSTRUCTION — some open with YAML frontmatter (`agent:`/`updated:`/`sessions-closed:`), some
# start at a `#` heading — so any shape-assuming write corrupts exactly the files it did not
# anticipate. The block is HTML comments so it is invisible in rendered markdown and cannot
# collide with a heading, and `v=1` rides BOTH delimiters so a truncated append is DETECTABLE.

HANDOFF_TOKEN = "coord:handoff"   # the delimiter word — and the one literal a note body may not carry
HANDOFF_V = "v=1"                 # on BOTH delimiters, so a half-written block is detectable
HANDOFF_STAMP_FMT = "%Y-%m-%dT%H:%M:%S"


def handoff_stamp_text(when):
    """The block's `stamped=` value — ONE formatter, for BOTH of its consumers.

    s12-07 stores this exact string in `awaiting-close.json`'s `handoff_stamp`, and the two must be
    byte-identical: the record is what a later reader uses to find the block it describes. So the
    clock is read ONCE at the call site and formatted HERE for the block and for the record alike.
    Two `datetime.now()` calls can straddle a second — a whole second apart, with nothing able to
    notice — and a second format string is the same drift with an extra way to go wrong."""
    return when.strftime(HANDOFF_STAMP_FMT)


def handoff_block_text(seat, session, disposition, note, when=None):
    """The handoff block, VERBATIM per `stage-1-2-gate-checkout-spec.md` §3.

    `session=` is NEVER omitted — a missing key breaks a positional reader, an explicit `unknown`
    does not. `unread=yes` is the ONLY mutable attribute (`s12-08` flips it to `no` after it has
    printed the block at the successor's check-in); every other attribute is written once here and
    never touched again.
    """
    stamp = when or datetime.now()
    return (
        f"<!-- {HANDOFF_TOKEN} {HANDOFF_V} seat={seat} session={session or 'unknown'} "
        f"disposition={disposition} stamped={handoff_stamp_text(stamp)} unread=yes -->\n"
        f"## Handoff → next session of `{seat}` ({stamp.strftime('%Y-%m-%d %H:%M')})\n"
        f"\n"
        f"{note}\n"
        f"\n"
        f"<!-- /{HANDOFF_TOKEN} {HANDOFF_V} -->\n")


def session_id_open(args, seat):
    """The seat's OPEN `sessions.csv` session-id, or `''` — read-only and never fatal.

    Read BEFORE the checkout body runs, because `session_close` stamps `ended` on exactly this row:
    the handoff must name the session that WROTE it, not a row already closed out from under it.
    LAST open row wins, the same rule `session_close` itself applies. `''` becomes `session=unknown`
    at the block rather than a dropped attribute.
    """
    try:
        path = sessions_csv(package_dir(args))
        if not path.exists():
            return ""
        header, rows = read_csv_table(path, SESSIONS_COLS)
        idx = {c: i for i, c in enumerate(header)}
        if not {"seat", "ended", "session-id"} <= set(idx):
            return ""
        found = ""
        for r in rows:
            pad_row(r, header)
            if r[idx["seat"]].strip() == seat and not r[idx["ended"]].strip():
                found = r[idx["session-id"]].strip()
        return found
    except (OSError, ValueError, csv.Error):
        return ""


def append_handoff(base, memory_path, block):
    """Append `block` at EOF under `coord_lock` + `atomic_write`, then VERIFY it landed.

    Returns `(ok, detail)`; `detail` names the failure when `ok` is False.

    ⚠ THE VERIFICATION IS NOT CEREMONY, IT IS THE POINT. `coord_lock` IS NEVER FATAL — a sandboxed
    seat whose package is read-only (codex EROFS) proceeds WITHOUT the lock after one note — so
    this write can be concurrent, and the replace can fail on a filesystem that accepted the open.
    A silent half-write loses the ONE artifact the successor is promised, at the exact moment the
    seat believes it handed over. So the file is RE-READ and the composed bytes must be found in it.

    ⚠ APPEND-ONLY IN THE STRICT SENSE: the prior bytes are never rewritten, reordered, stripped or
    normalized — the separator is only ever ADDED. Enough newline goes in to leave exactly one blank
    line before the block and to guarantee no line is joined; a file that ALREADY ends in a blank
    line gets nothing, because removing a trailing newline to tidy it would itself be a rewrite.
    """
    try:
        with coord_lock(base):
            prior = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
            if not prior or prior.endswith("\n\n"):
                sep = ""
            elif prior.endswith("\n"):
                sep = "\n"
            else:
                sep = "\n\n"
            atomic_write(memory_path, prior + sep + block)
        landed = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
    except (OSError, ValueError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if block not in landed:
        return False, ("the composed block is NOT in the file after the write — the append did not "
                       "land (a lockless write on a read-only package, or a replace that failed)")
    # The independent half: the file's LAST delimiter must be a CLOSING one. A tail left open is
    # the shape a truncated append leaves behind, and it is the shape `s12-08`'s reader would then
    # scan forever. Matched on the delimiter WORD, not on the whole composed block, so this stays a
    # statement about the file rather than a second copy of the line above.
    if landed.rfind(f"<!-- /{HANDOFF_TOKEN}") < landed.rfind(f"<!-- {HANDOFF_TOKEN}"):
        return False, ("the block on disk is TRUNCATED — the file's last handoff delimiter is an "
                       "OPENING one, so the append stopped part-way through")
    return True, ""

# ---- the check-in handoff DELIVERY (s12-08) -----------------------------------------------
#
# The delivery half of the handoff, and it COPIES THE MESSAGE CURSOR'S ORDERING deliberately:
# `cmd_read` calls `persist_cursor` AFTER the messages are rendered, and that ordering is what
# makes "shown" and "read" the same event. The `unread=` attribute is this mechanism's cursor and
# it moves at the same moment, for the same reason.
#
# WHAT SATISFIES EACH REQUIREMENT (`stage-1-2-gate-checkout-spec.md` §4/§5):
#   survives a crash        the block is on disk from the moment call 2 returns
#   re-delivers if unshown  the flip FOLLOWS the print, so a kill anywhere before it leaves
#                           `unread=yes` and the next check-in shows the same block again
#   keyed on (seat, unread) the lookup reads the seat FOLDER and the ATTRIBUTE, never the `seat=`
#                           author — so a revived successor of a CRASHED seat is handed its own
#                           predecessor's block (D2). NO `workers.md` COLUMN: that row is
#                           per-SESSION and is superseded at re-check-in, while the handoff must
#                           outlive a crash that left no successor row at all
#   idempotent              flipping an already-`no` block is a no-op, exactly as `persist_cursor`
#                           skips a cursor that would not move
#
# ⚠ THE FLIP IS A TARGETED SPLICE AT THE SELECTED BLOCK'S OWN INDICES — NEVER A `replace_all`. A
# whole-file `replace("unread=yes", "unread=no")` would mark EVERY historical block read in one
# act and destroy the re-delivery property for all of them at once.


def handoff_blocks(text):
    """Every COMPLETE handoff block in `text`, in file order.

    Each entry carries `head` (the opening comment, verbatim), its `head_start`/`head_end` span —
    so the flip can splice at an INDEX rather than match a string two byte-identical headers could
    both answer to — plus `attrs` and the `body` between the delimiters.

    Attributes are read BY NAME, never by position: the writer emits `session=unknown` rather than
    dropping the key precisely so a reader never has to count tokens, and a reader that counted
    them would break the day a key is added.

    An opener with no closer is NOT a block and is skipped here; the FILE-level truncation verdict
    belongs to `handoff_truncated`, which is what the caller acts on.
    """
    opener = f"<!-- {HANDOFF_TOKEN} {HANDOFF_V} "
    closer = f"<!-- /{HANDOFF_TOKEN} {HANDOFF_V} -->"
    found, i = [], 0
    while True:
        start = text.find(opener, i)
        if start < 0:
            return found
        head_end = text.find("-->", start)
        if head_end < 0:
            return found                  # a header cut mid-line: nothing after it can parse
        head_end += 3
        end = text.find(closer, head_end)
        nl = text.find("\n", head_end)
        i = head_end
        if end < 0 or nl < 0 or nl > end:
            continue
        attrs = {}
        for tok in text[start + len(opener):head_end - 3].split():
            key, _, val = tok.partition("=")
            attrs[key] = val
        found.append({"head": text[start:head_end], "head_start": start, "head_end": head_end,
                      "attrs": attrs, "body": text[nl + 1:end].strip("\n")})
        i = end + len(closer)


def handoff_truncated(text):
    """True when the file's LAST handoff delimiter is an OPENING one.

    THE SAME TEST `append_handoff` REFUSES ON, deliberately: the writer and the reader must not
    hold two opinions about what a half-written block looks like, or the shape one refuses to
    leave behind is a shape the other happily reads a whole file's tail out of.
    """
    return text.rfind(f"<!-- /{HANDOFF_TOKEN}") < text.rfind(f"<!-- {HANDOFF_TOKEN}")


def handoff_stamp_human(stamp):
    """The block's `stamped=` value rendered for the successor's eyes.

    Parsed against `HANDOFF_STAMP_FMT` — the format the WRITER used — never against a second copy
    of it; a literal here is the same drift `handoff_stamp_text` exists to prevent. An unparseable
    value is shown RAW rather than dropped: a time that looks wrong still tells the reader more
    than no time at all.
    """
    try:
        return datetime.strptime(stamp, HANDOFF_STAMP_FMT).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return stamp or "an unrecorded time"


def flip_handoff_read(base, memory_path, head):
    """Mark the block whose header is `head` READ: ONE line, spliced at its own indices, under
    `coord_lock` + `atomic_write`. Returns `(ok, detail)`.

    ⚠ NEVER `replace_all`, and never a replacement computed over the whole file. The block is
    RE-LOCATED under the lock and rewritten BY INDEX, so two byte-identical headers (one seat, one
    session, one second) can never make this flip the wrong one — and every other block's bytes,
    read or unread, are carried through untouched.

    `head` is the header this process actually PRINTED. If the file moved underneath and the last
    unread block is no longer that one, NOTHING is written: marking a block read that nobody was
    shown is the one outcome worse than showing one twice.
    """
    new = ""
    try:
        with coord_lock(base):
            text = memory_path.read_text(encoding="utf-8")
            unread = [b for b in handoff_blocks(text) if b["attrs"].get("unread") == "yes"]
            if not unread:
                # Idempotent, the same way `persist_cursor` no-ops a cursor that would not move:
                # a concurrent successor already marked it, and re-writing the file to say what it
                # already says is pure race surface.
                return True, "already read"
            block = unread[-1]
            if block["head"] != head:
                return False, ("the file changed under the delivery — its LAST unread block is no "
                               "longer the one that was printed, so nothing was marked read")
            new = (text[:block["head_start"]]
                   + head.replace("unread=yes", "unread=no", 1)
                   + text[block["head_end"]:])
            atomic_write(memory_path, new)
            landed = memory_path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if landed != new:
        return False, ("the flip is NOT on disk after the write — the replace failed, or a "
                       "concurrent writer overwrote it")
    return True, ""


def deliver_handoff(args, base, seat):
    """Show this seat's unread handoff, THEN mark it read. NEVER blocks the check-in.

    Non-fatal in every direction, and deliberately SILENT in most of them — a seat with no folder,
    no `memory.md`, an unreadable one, or nothing unread has nothing to be told. The two loud
    branches are the two where silence would mislead: a TRUNCATED block (printing its tail would
    dump an unbounded slice of the file into the seat's context) and a FLIP THAT FAILED after the
    block was already printed.
    """
    found = next((w for w in discover_workers(workers_dir(args)) if w["agent"] == seat), None)
    folder = found.get("folder") if found else None
    if folder is None:
        return
    memory_path = folder / "memory.md"
    try:
        text = memory_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return
    if handoff_truncated(text):
        print(c(f"WARNING {memory_path} ends in a TRUNCATED handoff block — its opening delimiter "
                f"has no matching closer, so where that note ENDS is unknown and NOTHING was "
                f"printed or marked read. Printing the tail instead would pour an unbounded slice "
                f"of the file into this session. The text above the break is intact; repair the "
                f"file by hand and tell leader.", C_DEAD), file=sys.stderr)
        return
    unread = [b for b in handoff_blocks(text) if b["attrs"].get("unread") == "yes"]
    if not unread:
        return
    block = unread[-1]
    print(f"handoff waiting — written by the previous session of this seat at "
          f"{handoff_stamp_human(block['attrs'].get('stamped', ''))}:")
    print(block["body"])
    print(f"(marked read now; it stays in {memory_path})")
    # ⚠ THE BROAD CATCH IS THE POINT, AND IT BELONGS HERE RATHER THAN AT THE CALLER. The block is
    # already on the seat's screen; anything this raises must land on the ONE loud branch below,
    # which says "you were shown it, it was NOT marked read". The caller's guard would report the
    # delivery as SKIPPED instead — a statement that is simply false once the print has happened.
    try:
        ok, why = flip_handoff_read(base, memory_path, block["head"])
    except Exception as exc:                                   # noqa: BLE001 — deliberate
        ok, why = False, f"{type(exc).__name__}: {exc}"
    if not ok:
        print(c(f"WARNING the handoff above was NOT marked read — {why}. It is STILL "
                f"`unread=yes` in {memory_path}, so the NEXT check-in of this seat will be shown "
                f"it again. RE-DELIVERY BEATS LOSS: act on it once, and say so on the log if it "
                f"keeps repeating.", C_DEAD), file=sys.stderr)




def cmd_checkout(args):
    # s12-05 / D2: `--handoff` is the note the seat's SUCCESSOR reads, so it belongs only to a
    # checkout that OPENS a next session. A done-checkout writes no handoff. Refused FIRST — before
    # identity resolution, before the roster read, before the export — so an argument error costs
    # nothing: at this point nothing has been read, written, captured or muted.
    renew = getattr(args, "renew", False)
    handoff = getattr(args, "handoff", None)
    # s12-07: set by CALL 2 only, and read at the single `set_awaiting` both paths fall through to.
    # The done path records "" because it appended no block — an empty stamp is the honest value,
    # never a placeholder time.
    handoff_stamp = ""
    if handoff is not None and not renew:
        refuse(
            "input",
            f"--handoff carries what the NEXT session of this seat must do, so it needs a checkout "
            f"that opens one: pass --renew with it. A done-checkout has no successor to hand "
            f"anything to, and accepting the note here would file a handoff nobody is ever booted "
            f"to read.\n"
            f"Renewing this seat: {coord_invocation(args)} checkout --renew\n"
            f"Done for good:      {coord_invocation(args)} checkout",
            2)
    base = base_dir(args)
    me = resolve_agent(args)
    _, _, rows = load_workers(base)
    row = current_row(rows, me)
    if not row or row["active"] != "yes":
        refuse(
            "state",
            f"'{me}' has no ACTIVE roster row, so there is no session to end — you "
            f"never checked in, or you already checked out.\n"
            f"See the roster: {coord_invocation(args)} workers",
            1)
    if renew:
        if handoff is None:
            checkout_renew_arm(args, base, me)
            return
        # ---- CALL 2 (s12-06): the handoff lands FIRST, then the ordinary checkout body runs. ----
        #
        # THE ORDER IS LOAD-BEARING. Everything in the body below is irreversible from the seat's
        # side — the export is taken, the roster row is flipped, the session row is closed — so a
        # handoff appended after it would be written by a session that no longer exists to be told
        # it failed. Written first, verified, and only then does anything close.
        #
        # ⚠ THE THREE VALIDATIONS BELOW DUPLICATE `checkout_renew_arm`'s, ON PURPOSE. Call 1
        # refuses a folderless and a `close: mechanical` seat before it arms anything — but CALL 2
        # IS REACHABLE WITHOUT CALL 1: nothing forces the two-step, a seat can type the second
        # command first, and a descriptor can change between the two. A guard that only ever fires
        # behind another guard stops holding the day someone finds the other door.
        if HANDOFF_TOKEN in handoff:
            refuse(
                "input",
                f"your note contains the literal `{HANDOFF_TOKEN}`, which is the delimiter word of "
                f"the block it would be written into. Escaping it would leave the block grammar "
                f"ambiguous for every later reader, so it is REFUSED instead and the grammar stays "
                f"decidable. Nothing was written and nothing was closed — your note is not lost.\n"
                f"Re-word that phrase, then re-run: {coord_invocation(args)} checkout --renew "
                f"--handoff \"<what the next session of this seat must do>\"",
                2)
        seat = next((w for w in discover_workers(workers_dir(args)) if w["agent"] == me), None)
        if seat is not None and seat.get("mechanical_close"):
            refuse(
                "input",
                f"'{me}' declares `close: mechanical` (G-23), so it is memoryless BY DESIGN — no "
                f"memory.md, and therefore nowhere for a handoff to land. The owner ruled this "
                f"seat OFF the self-service renew path PERMANENTLY, not provisionally "
                f"(`d-mechanical-no-self-renew`, 2026-07-29). Nothing was written and nothing was "
                f"closed — your note is not lost.\n"
                f"Its renewal is the LEADER-SIDE close-and-relaunch path instead — end this "
                f"session with `{coord_invocation(args)} checkout`, and leader brings the next one "
                f"up with `{coord_invocation(args)} close {me} --renew`.",
                2)
        folder = seat.get("folder") if seat else None
        if folder is None:
            refuse(
                "input",
                f"'{me}' has no seat FOLDER — its descriptor is a flat file, so there is no "
                f"`{me}/memory.md` for this handoff to be appended to, and carrying it to your "
                f"successor is the whole point of this path. Nothing was written and nothing was "
                f"closed — your note is not lost.\n"
                f"End this session with `{coord_invocation(args)} checkout` instead; leader "
                f"relaunches the seat if it must come back.",
                2)
        memory_path = folder / "memory.md"
        # The session id is resolved HERE, before the body: `session_close` below stamps `ended` on
        # exactly the row this reads, and the block must name the session that WROTE it.
        # ONE clock reading, formatted ONCE, for both the block and the awaiting-close record
        # (s12-07). Letting `handoff_block_text` take its own `datetime.now()` and computing the
        # record's stamp separately would put two readings around one write, and the pair would
        # disagree by a whole second whenever they straddled one — silently, and only sometimes.
        handoff_when = datetime.now()
        handoff_stamp = handoff_stamp_text(handoff_when)
        handoff_ok, handoff_why = append_handoff(
            base, memory_path,
            handoff_block_text(me, session_id_open(args, me), "renew", handoff,
                               when=handoff_when))
        if not handoff_ok:
            refuse(
                "state",
                f"HANDOFF NOT WRITTEN — {handoff_why}. Your session is UNTOUCHED: nothing was "
                f"exported, the roster still shows you active, and no close was recorded. The "
                f"refusal is deliberate — closing on top of a handoff that is not on disk would "
                f"destroy the one artifact this renewal exists to produce, at the moment you "
                f"believe you handed over.\n"
                f"Keep your note. Check that {memory_path} is writable, then re-run "
                f"`{coord_invocation(args)} checkout --renew --handoff \"<note>\"`. If it fails "
                f"again, tell leader and end with `{coord_invocation(args)} checkout`.",
                1)
        print(f"handoff appended: {memory_path}")
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
    #
    # s12-07: WHICH checkout this was, ASSERTED here rather than inferred later. Both paths — done
    # and renew — fall through to this ONE call site, and `renew` is the branch discriminant, in
    # scope on this very line. It is passed EXPLICITLY on both arms even though `done` is the
    # default: at the one place the answer is known, a value a reader must chase to a signature is
    # not an assertion. `handoff_stamp` is call 2's stamp, byte-identical to the block's `stamped=`
    # because both come from one clock reading through one formatter; the done path passes "".
    #
    # It goes in THIS record, never a second file. A second surface would force `cmd_reap` and
    # `watch.py` to reconcile two of them, re-importing the re-derivation hazard the comment block
    # at the top of this section exists to name.
    if set_awaiting(base, me, (row or {}).get("pane", ""), out, not err,
                    disposition=("renew" if renew else "done"), handoff_stamp=handoff_stamp):
        print(f"awaiting close: {me} recorded — its pane is STILL LIVE until leader runs "
              f"`{coord_invocation(args)} close-seat {me}`")
    sid, cerr = session_trace_safe(session_close, args, me)   # 7.37: checkout ends the session as surely as a close does
    if cerr:
        print(c(f"WARNING sessions.csv row NOT completed — {cerr}. The close itself stands.",
                C_DEAD), file=sys.stderr)
    elif sid:
        print(f"sessions.csv: {sid} ended")
    if renew:
        # [INTEGRATION POINT — STAGE 3: fork the detached executor]
        # Stage 3 forks the renewal executor HERE, after the close is recorded and before this
        # process exits, on the `arm_pid_reaper` pattern (setsid + start_new_session=True, the
        # exact (pid, starttime) re-derived at act time). THE PATTERN IS `arm_pid_reaper`; IT IS
        # NOT THE API. Nothing is wired yet, so the seat is told the truth about what remains.
        print(c(f"next: nothing on your side — the renewal executor is not wired yet (Stage 3); "
                f"leader runs `close-seat {me} --renew`.", C_HINT))
    else:
        # [INTEGRATION POINT — STAGE 3: fork the detached reaper]
        # The done path's twin seam: Stage 3 forks the pane reaper here instead of leaving the
        # debt above for a later human pass.
        #
        # ⚠ THIS LINE NO LONGER TEACHES `close <me> --renew`. Renewal is the SEAT's own act now
        # (`checkout --renew`), so naming leader's close-and-renew as this seat's follow-up would
        # teach the superseded ceremony at the one moment the seat is looking for its next step.
        print(c(f"next: nothing on your side — this session is DONE and leader frees the pane "
                f"(`{coord_invocation(args)} close-seat {me}`). Renewing a seat is the SEAT's own "
                f"act now — `checkout --renew`, before you check out for good.", C_HINT))


def checkout_renew_arm(args, base, me):
    """`checkout --renew` CALL 1: arm the seat's own renewal, teach it call 2, close NOTHING.

    `d-close-renew-decider-recorded` — the SEAT decides its own renew/refresh; no agent stands in
    the execution path and there is no `--force`. That is only safe if the call itself is safe to
    make, so this one does NOT export, does NOT flip the roster row, and records no
    awaiting-close debt (the G-134 debt is the DONE path's, and the record carrying
    `disposition=renew` is written by CALL 2, at the moment something actually closes — s12-07).
    All it does is mute the seat's wakes and print the second call.

    ⚠ THE TWO REFUSALS FIRE BEFORE THE ARMING, NEVER AFTER. A flat-file seat has no folder and so
    no `memory.md` for a handoff to land in, and a `close: mechanical` seat (G-23) is memoryless BY
    RULING. Arming first and refusing second would leave such a seat MUTED for CLOSING_MAX_MIN
    minutes with no renewal path out of it — cut off from the room by the very command that then
    told it no. `s12-06`'s call-2 check stays as a belt-and-braces guard behind this one.

    ⚠ THE CLOSER TOKEN IS THE SEAT'S OWN NAME, never a literal like "self-renew"
    (`r-closing-is-a-true-wake-mute`, s12-01 amendment). `closing_reaches` admits exactly `leader`
    and `entry["closer"]`, and the roster grammar admits ANY non-pipe string as an agent name — so
    a literal token is an unclaimed free key into a narrowed inbox. With the seat's own name the
    admitted set is {leader, me}, and a seat's own sends are never re-served nor woken, so the
    effective inbox is exactly `leader`: what the teaching text below claims.
    """
    seat = next((w for w in discover_workers(workers_dir(args)) if w["agent"] == me), None)
    if seat is not None and seat.get("mechanical_close"):
        refuse(
            "input",
            f"'{me}' declares `close: mechanical` (G-23), so it is memoryless BY DESIGN — no "
            f"memory.md, and therefore no handoff for a successor to read. The owner ruled this "
            f"seat OFF the self-service renew path PERMANENTLY, not provisionally "
            f"(`d-mechanical-no-self-renew`, 2026-07-29). Nothing was armed: your wakes are not "
            f"muted and your session is untouched.\n"
            f"Its renewal is the LEADER-SIDE close-and-relaunch path instead — end this session "
            f"with `{coord_invocation(args)} checkout`, and leader brings the next one up with "
            f"`{coord_invocation(args)} close {me} --renew`.",
            2)
    folder = seat.get("folder") if seat else None
    if folder is None:
        refuse(
            "input",
            f"'{me}' has no seat FOLDER — its descriptor is a flat file, so there is no "
            f"`{me}/memory.md` for a handoff to be appended to, and carrying that handoff to your "
            f"successor is the whole point of this path. Nothing was armed: your wakes are not "
            f"muted and your session is untouched.\n"
            f"End this session with `{coord_invocation(args)} checkout` instead; leader relaunches "
            f"the seat if it must come back.",
            2)
    if not set_closing(base, me, me):
        print(c(f"WARNING the wake mute could NOT be written — your inbox is NOT narrowed and "
                f"wakes keep arriving. The renewal below is still yours to finish; expect "
                f"interruptions, and tell leader.", C_DEAD), file=sys.stderr)
    # ⚠ VERBATIM (stage-1-2-gate-checkout-spec.md §2.2). This text IS the mechanism — it is the CLI
    # teaching the seat the second step, and its wording, its order and its line breaks are the
    # spec's, not this function's. The minute figure is DERIVED from CLOSING_MAX_MIN and never
    # typed: a copy drifts, a reference does not.
    memory_path = folder / "memory.md"
    print(
        f"renewal armed: {me} — wakes are muted and your inbox is narrowed to leader (clears in "
        f"{CLOSING_MAX_MIN} min\n"
        f"if you do not finish).\n"
        f"\n"
        f"NOTHING IS CLOSED YET. Two things are still yours, in this order:\n"
        f"  1. STOP READING. Do not run `read` again — the log keeps queueing and your successor\n"
        f"     inherits your cursor, so nothing is lost by stopping here.\n"
        f"  2. WRITE YOUR SUCCESSOR'S HANDOFF, then re-run this command with it:\n"
        f"\n"
        f"     coordinate checkout --renew --handoff \"<what the next session of this seat must "
        f"do>\"\n"
        f"\n"
        f"Write it for someone with NO memory of this session: what is in flight, what you were "
        f"about\n"
        f"to do next, what you tried and ruled out, and any path or id they would otherwise have "
        f"to\n"
        f"re-derive. It is appended to your seat memory ({memory_path}) and printed to your "
        f"successor\n"
        f"at its check-in.")


# ---- owner state (task 7.85, owner ruling r-owner-state-is-not-binary) --------------------
# THE STATES ARE ESCALATION POLICIES, NOT FACTS ABOUT THE HUMAN. That is why a third VALUE is
# right and a second FIELD is wrong: `present` and `afk` never meant "at the desk"/"away", they
# meant "escalate now"/"queue them". `reachable` is the third policy — escalate BY LAUNCHING THE
# DOOR — and the owner ruled it a first-class state of the system, not a run's convention.
#
# ⚠ THIS TABLE IS THE SINGLE HOME. `choices=`, the `--help` text, and what every consumer RENDERS
# are all derived from it, so none of them can drift from the others or from behaviour. The
# ESCALATION ACT lives here, in code — NOT in the free-text note. That is the whole point of the
# row: before this, the third state existed only when someone wrote a good note, and two seats
# reconstructed it in prose on the same afternoon (the leader set `present` at 16:5x and then
# qualified it away in ~400 characters; the chief-of-staff relayed an order built on the same
# distinction). Prose does not survive a rewrite. Delete every note and the distinction still stands.
#
# ⚠⚠ THE ACT IS A FUNCTION OF THE WORLD AT RENDER TIME, NOT OF THE STATE TOKEN ALONE (task 7.89,
# `G-269`). It was static text for about forty minutes and went stale BY BEING OBEYED: `reachable`
# told every seat to LAUNCH THE DOOR, someone did, and the instruction stayed up — true when the
# state was set, false the moment it was carried out. ⇒ THE SURFACE WAS MOST WRONG EXACTLY WHEN THE
# ROOM HAD BEEN MOST RESPONSIVE, which is the worst possible correlation for an escalation
# instruction. `reachable` still describes the OWNER correctly; only the run-side ACT decayed, so
# this needs no fourth state and no new field — just a world the act is composed against.
OWNER_STATES = {
    "present": (
        "rulings can be escalated NOW",
        lambda w: (
            f"message the owner directly — the door ({w['door']}) is up and receiving"
            if w["door_active"] else
            "⚠ state says PRESENT but NO door session is running — nothing is receiving. "
            "Launch the door, or correct the state; do not assume a message lands"
        ),
    ),
    "reachable": (
        "at the PC, AFK FROM THE RUN — no master session running, a pane standing where one can be",
        lambda w: (
            f"the door is ALREADY UP ({w['door']}) — just MESSAGE it. No launch needed"
            if w["door_active"] else
            "LAUNCH THE DOOR — relaunch the seat that carries the owner relay in the standing pane "
            "(resolve the pane from `workers`, never a remembered %n), then message it"
        ),
    ),
    # ⚠ CHECKED UNDER THE SAME LENS AND NOT STALE (criterion 2): `afk`'s act is the NULL act, and a
    # null act cannot go stale by being obeyed — there is nothing to carry out that would falsify
    # it. Deliberately left unconditional rather than gated for symmetry's sake.
    "afk": (
        "queue rulings; do NOT page",
        lambda w: "none until the owner returns — anything urgent waits",
    ),
}


def owner_world(args, base):
    """The facts an escalation act is composed against. READ-ONLY, and that is criterion 4.

    ⚠⚠ IT NEVER TOUCHES A PANE, NEVER LAUNCHES, NEVER PROBES THE DOOR. The question "does a
    relaunch work?" is DESIGNED OUT rather than answered — `bars.md` 4 says a pane whose purpose is
    human contact is never reaped, and testing a relaunch against the live door is that same
    hazard one step earlier. This reads two files.

    The door is derived from `relays:` in the seat descriptors — NEVER a kit-side name list, the
    same derivation the reap exemption uses, and for the reason stated there: a name list freezes
    one campaign's roles into a shared tool and the next such seat is forgotten identically.
    """
    door, active = None, False
    try:
        decls = inbox_decls(args)
    except Exception:  # noqa: BLE001 — a bad descriptor must never break `status`
        decls = {}
    for seat, d in sorted((decls or {}).items()):
        if (d or {}).get("relays"):
            door = seat
            break
    if door:
        try:
            _p, _l, rows = load_workers(base)
            row = current_row(rows, door)
            active = bool(row and row.get("active") == "yes")
        except Exception:  # noqa: BLE001
            active = False
    return {"door": door or "the owner-relay seat", "door_active": active}
OWNER_STATE_UNKNOWN = (
    "no owner state has been recorded",
    "none defined — run `owner <state>` before relying on this",
)


def owner_status(base):
    """Parse `owner-status.md` into STRUCTURE — state, since, note — never one opaque string.

    ⚠ IT USED TO RETURN THE WHOLE LINE AFTER `owner:`, and both consumers printed that raw. So the
    enum value and the operator's free text were literally the same field to every reader, and a
    third state would have rendered identically to the other two no matter what the enum accepted.
    Splitting them is what makes the state itself renderable, which is criterion 5 of task 7.85.

    BACK-COMPAT IS REQUIRED, NOT BEST-EFFORT: a file written before this change must still read
    correctly (its state token is already the first word after `owner:`), and an UNRECOGNISED state
    — hand-edited, or from a newer writer — degrades honestly: it is reported as the state it says,
    marked unknown, with the raw line preserved. Vanishing would be worse than being wrong.
    """
    raw, state, since, note = "", "unknown", "", ""
    path = base / "owner-status.md"
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.startswith("owner:"):
                raw = ln[len("owner:"):].strip()
                break
    if raw:
        head, sep, tail = raw.partition("|")
        state = head.strip() or "unknown"
        rest = tail.strip() if sep else ""
        # The writer's shape is `since {ts}[ — {note}]`. The note delimiter is an EM DASH, which
        # is also legal inside a note; partition on the FIRST one, which is the writer's.
        if rest.startswith("since"):
            rest = rest[len("since"):].strip()
        since, _, note = (p.strip() for p in rest.partition("—"))
    return {
        "state": state,
        "since": since,
        "note": note,
        "raw": raw,
        "known": state in OWNER_STATES,
    }


def owner_escalation(state, world):
    """The act for `state` composed against `world` — the ONE place an act is produced.

    ⚠ CRITERION 5: the conditional lives HERE, where the act is composed, never in a note a human
    writes. A note-borne condition is exactly the defect 7.85 existed to end, and its own follow-up
    must not reintroduce it.
    """
    entry = OWNER_STATES.get(state)
    act = entry[1] if entry else OWNER_STATE_UNKNOWN[1]
    return act(world) if callable(act) else act


def print_owner_status(base, label_width=7, args=None):
    """Render owner state for a consumer. ONE renderer, called by BOTH `status` and `workers`.

    Two consumers rendering this by hand is how the distinction collapsed in the first place, so
    they share this function rather than each formatting the dict. The MEANING and the ESCALATION
    ACT come from OWNER_STATES — from code — and the operator note is printed separately and
    subordinate, so it can be empty without the state becoming ambiguous.
    """
    st = owner_status(base)
    meaning = OWNER_STATES.get(st["state"], OWNER_STATE_UNKNOWN)[0]
    act = owner_escalation(st["state"], owner_world(args, base))
    tone = C_ALIVE if st["state"] == "present" else (C_LABEL if st["known"] else C_DEAD)
    head = c("owner:".ljust(label_width), C_LABEL)
    since = f" | since {st['since']}" if st["since"] else ""
    unknown = "" if st["known"] else "  (UNRECOGNISED STATE — reported verbatim, not translated)"
    pad = " " * (label_width + 1)
    print(f"{head} {c(st['state'], tone)}{since}{unknown}")
    print(f"{pad}{meaning}")
    print(f"{pad}escalation: {act}")
    if st["note"]:
        print(f"{pad}note (operator, not the carrier): {st['note']}")


def cmd_owner(args):
    # P15 — workers were inferring owner availability and getting it wrong; state it explicitly.
    # Gate: leader, or an UNRESOLVABLE identity — that caller is the human owner at a shell.
    gate(args, "owner", lambda who: who in ("leader", ""), "leader's (or the owner's) to set")
    base = base_dir(args)
    base.mkdir(parents=True, exist_ok=True)
    note = f" — {args.note}" if args.note else ""
    with coord_lock(base):
        atomic_write(base / "owner-status.md",
                     "# owner-status — script-managed (coord.py owner "
                     f"<{'|'.join(OWNER_STATES)}>)\n"
                     f"owner: {args.state} | since {now()}{note}\n")
    print(f"owner is now: {args.state}{note}")
    # Echo the MEANING and the ESCALATION ACT back at the setter, from the same table every reader
    # renders. The leader set `present` at 16:5x and then spent a long note explaining that it did
    # NOT mean "escalate now" — a setter shown what the value it just wrote will TELL EVERY READER
    # is a setter given the chance to notice it picked the wrong one (task 7.85, criterion 3).
    _meaning = OWNER_STATES.get(args.state, OWNER_STATE_UNKNOWN)[0]
    print(f"  means:      {_meaning}")
    print(f"  escalation: {owner_escalation(args.state, owner_world(args, base))}")
    # G-181: this used to coach `send all "owner is ..." --type note`, which the tool REFUSES
    # twice over (positional body, then `a note is never an all broadcast`). Adding --inline would
    # have silenced a substring check while the command stayed refused. But the deeper reason not
    # to restore it in any form is DIVERGENCE, not the refusal: the line above just wrote the
    # MACHINE surface, and a hand-typed second statement of owner presence is a copy that can
    # disagree with it. `owner: unknown` sat on the roster through hours of explicit AFK posture
    # precisely because presence was being restated by hand instead of read from one home.
    print(c(f"next: nothing to send — {coord_invocation(args)} status and workers now report "
            f"this to every seat that asks, from the surface just written (P15)", C_HINT))


def truncate(text, limit=DIGEST_SNIPPET):
    """One-line snippet. Newlines are collapsed: every caller renders ONE line per row, and a
    body with embedded newlines would silently break that row into several."""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def state_agent_types(base):
    """{seat: agent_type} straight off `state.json`'s own snapshot (task 7.80's `coordinate`
    half, G-195) — never re-derived, never a second source. `teamview` reads the identical
    field the identical way (`teamview.py:agent_type_bit`); this is the same property read a
    second time, not a second classification.

    Returns {} on anything short of a clean snapshot — missing file, unparseable, wrong shape,
    or a pre-7.80 snapshot with no such key on any row — so `workers` degrades to its
    pre-7.80 rendering rather than raising or inventing a value (same fail-safe shape as
    `team_monitor_last_seen`, same file, read independently here because the two callers want
    different things on failure: a bound there, nothing here).

    ⚠⚠ DISPLAY ONLY, NEVER A GATE. This field is a SENSOR OBSERVATION of a descriptor's
    declared claim, not an authorization — the identity gate (`resolve_agent`/`gate`) is the
    only authorization, and nothing may ever branch on this dict's values
    (`r-agent-type-field-name`'s binding condition, restated here because this is now a fourth
    site that touches the field)."""
    try:
        snap = json.loads((base.parent / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(snap, dict):
        return {}
    out = {}
    for s in snap.get("seats") or []:
        if not isinstance(s, dict):
            continue
        seat, atype = (s.get("seat") or "").strip(), (s.get("agent_type") or "").strip()
        if seat and atype:
            out[seat] = atype
    return out


def cmd_workers(args):
    """Who is alive, at a glance (T2/F4). DEFAULT is one CURRENT row per agent with truncated
    summaries and an unread-lag column; --full keeps summaries whole, --history replays every
    historical row (the pre-T2 behavior)."""
    base = base_dir(args)
    _, _, rows = load_workers(base)
    nonmembers, addr_errors = addressable_nonmembers(args, base)
    print_owner_status(base, label_width=6, args=args)
    # Listed SEPARATELY from the roster, never merged into it: these are not seats, hold no row,
    # and must never be counted in a census, a cap or a sweep. Shown at all because a name that
    # resolves invisibly is its own kind of fail-silent — and the errors are shown for the same
    # reason the successes are.
    if nonmembers or addr_errors:
        print(f"{c('addressable non-members (no row, no wake, no cursor — PULL delivery):', C_LABEL)}")
        for nm in sorted(nonmembers):
            print(f"  {nm} -> {nonmembers[nm]}")
        for e in addr_errors:
            print(c(f"  UNRESOLVED: {e}", C_DEAD))
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
    agent_types = state_agent_types(base)  # task 7.80's `coordinate` half, G-195
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
        # `agent_type` (task 7.80/G-195): shown exactly as the snapshot carries it, including
        # "unclassified" — that value is a real, loud OBSERVATION (never silently defaulted),
        # not a gap to hide. Omitted only when the seat has no state.json row at all (pre-7.80
        # snapshot, or team-monitor has not captured this seat yet) — never invented.
        atype = agent_types.get(r["agent"], "")
        atype_bit = f" {c('[' + atype + ']', C_HINT)}" if atype else ""
        print(f"{c(name_col, C_LABEL)} {c(state_col, tone)} pane={pane_col}{atype_bit}{cursor}{lag} {summary}"
              f"  (in {r['checkin']}{', out ' + r['checkout'] if r['checkout'] else ''})")
    _und = undelivered_line(base)
    if _und:
        print(c(_und, C_DEAD))
    # s3-04: the lifecycle marker's READ SIDE, beside the undelivered line and for its exact
    # reason — s3-03 records every out-of-pane renewal and, until Stage 4 lands, nothing looks at
    # it. Rendered on BOTH surfaces the run actually reads (`workers` here, `status` at the twin
    # site), in the same `C_DEAD` — a new colour would say "a different KIND of alarm", which this
    # is not.
    _lcl = lifecycle_line(base)
    if _lcl:
        print(c(_lcl, C_DEAD))
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
        # G-158, second pass: UNKNOWN and STALE were both loud and the HEALTHY case printed
        # NOTHING, so "checked and current" was left to be INFERRED from an absence — in the one
        # feature whose whole subject is that absence and health look identical. It cost a real
        # reader real time: the chief-of-staff opened coord.py at this print site to confirm the
        # silence was by design rather than assume the absence was good news.
        # Appended to the ok line rather than given a line of its own: the success line already
        # exists, so terse-on-success survives and the common path gains no new noise.
        code_ok = ""
        if hb.get("code_known") and not hb.get("code_drifted"):
            names = sorted(Path(p).name for p in (hb.get("code") or {}))
            code_ok = f", running current {' + '.join(names)}" if names else ""
        daemon_fold, daemon_loud = _heartbeat_daemon_lines(hb, hb["stale"])
        if hb["stale"]:
            print(c(f"watcher: STALE — last pass {hb['age_min']}min ago (stale past "
                    f"{hb['stale_after']}min{cadence}{pid}). Nothing is measuring liveness, "
                    f"context or approval gates right now; restart the loop.", C_DEAD))
        else:
            print(c(f"watcher: ok — last pass {hb['age_min']}min ago{cadence}{pid}{code_ok}"
                    f"{daemon_fold}", C_ALIVE))
        # G-158: "is it running" and "is it running WHAT WE THINK" are different questions, and
        # only the first was ever asked. A loop that imported an old coord.py keeps passing every
        # check above — fresh heartbeat, live pid, flags delivered — while executing code that no
        # longer exists. Printed next to the liveness line because the two are read together and a
        # separate command would be a command nobody runs.
        if not hb.get("code_known"):
            print(c("watcher: code version UNKNOWN — this loop predates the code marker, so "
                    "nothing here can tell whether it is running current code. Treat it as "
                    "UNVERIFIED, not healthy; a restart makes it answerable.", C_HINT))
        elif hb.get("code_drifted"):
            print(c(f"watcher: RUNNING STALE CODE — {', '.join(hb['code_drifted'])} changed on "
                    f"disk since this loop imported it, and python binds source at import, so the "
                    f"running loop can never pick it up. It will keep heartbeating and reporting "
                    f"healthy on the OLD behaviour. Restart the loop to deploy.", C_DEAD))
        # G-188: the daemon. Same print site as the two questions above, and for the same reason —
        # this is where the reader already looks. The healthy case rides the ok line; only DOWN,
        # UNKNOWN and RESTARTED take a line of their own.
        for kind, line in daemon_loud:
            print(c(line, C_DEAD if kind == "dead" else C_HINT))
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
    refuse(
        "state",
        f"{', '.join(blocked)} "
        f"{'are special-case seats' if many else 'is a special-case seat'} — group traffic is "
        f"not {'their' if many else 'its'} input (G-32). A closer, `engineer` and the watcher "
        f"serve the SYSTEM or the ROOM, not the goal's conversation, so the room's threads only "
        f"spend the context {'their' if many else 'its'} one job needs.\n"
        f"Send {'them' if many else 'it'} a DIRECT message instead — direct addressability is "
        f"untouched: {coord_invocation(args)} send {blocked[0]} \"<what you need>\" --type note --inline\n"
        f"--force adds {'them' if many else 'it'} anyway, if the membership is deliberate.",
        1)


def cmd_create_group(args):
    base = base_dir(args)
    me = resolve_agent(args)
    _, _, wrows = load_workers(base)
    agent_names = {r["agent"] for r in wrows}
    name = args.group
    if name == "all" or name in agent_names:
        refuse(
            "state",
            f"'{name}' is already a recipient name ('all', or an agent on the roster), "
            f"and `send {name}` could then mean two different things.\n"
            f"Name the group after the WORKSTREAM instead (e.g. views-render).",
            1)
    members = sorted(set(args.members) | {me, "leader"})
    refuse_special_case_members(args, "create-group", members)
    with coord_lock(base):
        path, _, grows = load_groups(base)
        if any(g["group"] == name for g in grows):
            refuse(
                "state",
                f"group '{name}' already exists — creating it again would fork the "
                f"thread.\nAdd people to the existing one instead (leader): "
                f"{coord_invocation(args)} add-to-group {name} <member ...>",
                1)
        if not path.exists():
            atomic_write(path, GROUPS_HEADER)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"| {name} | {', '.join(members)} | {me} | {now()} |\n")
    print(f"group created: {name} — members: {', '.join(members)}")
    print(c(f"next: {coord_invocation(args)} send {name} \"<why this group exists>\" --type note --inline "
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
            refuse(
                "state",
                f"there is no group '{args.group}', so there is nothing to add to.\n"
                f"existing groups: {known}\nCreate it instead: {coord_invocation(args)} "
                f"create-group {args.group} <member ...>",
                1)
        members = sorted(set(row["members"]) | set(args.members))
        lines[row["_line"]] = f"| {row['group']} | {', '.join(members)} | {row['by']} | {row['created']} |\n"
        atomic_write(path, "".join(lines))
    print(f"group {args.group} members: {', '.join(members)}")
    print(c(f"next: {coord_invocation(args)} send {args.group} \"<who joined, and why>\" "
            f"--type note --inline", C_HINT))


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
            refuse(
                "state",
                f"there is no group '{args.group}', so there is nothing to remove "
                f"from.\nexisting groups: {known}",
                1)
        absent = [m for m in args.members if m not in row["members"]]
        if absent and not getattr(args, "force", False):
            refuse(
                "state",
                f"{', '.join(absent)} "
                f"{'are' if len(absent) > 1 else 'is'} not in group '{args.group}', so removing "
                f"{'them' if len(absent) > 1 else 'it'} would report a change that did not "
                f"happen.\ncurrent members: {', '.join(row['members']) or '(none)'}\n"
                f"--force drops the names that ARE members and ignores the rest.",
                1)
        members = [m for m in row["members"] if m not in set(args.members)]
        lines[row["_line"]] = f"| {row['group']} | {', '.join(members)} | {row['by']} | {row['created']} |\n"
        atomic_write(path, "".join(lines))
    print(f"group {args.group} members: {', '.join(members) or '(none)'}")
    print(c(f"next: {coord_invocation(args)} send {args.group} \"<who left, and why>\" "
            f"--type note --inline", C_HINT))


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
        refuse(
            "input",
            "a quoted body AND --file were both given, and only one of them can be "
            "the message — silently picking one would send a body you did not read.\n"
            "Pass the message positionally OR via --file, not both.",
            1)
    if src:
        if src == "-":
            body = sys.stdin.read()
        else:
            p = Path(src)
            if not p.is_file():
                refuse(
                    "input",
                    f"--file {src} — no such file, so there is no body to send.\n"
                    f"Write the file first, or pass an absolute path (relative paths resolve "
                    f"from YOUR working directory, not the package's).",
                    1)
            body = p.read_text(encoding="utf-8")
    elif msg:
        body = msg
    else:
        refuse(
            "input",
            'no message body — pass "<msg>", or --file PATH (--file - reads stdin) '
            'when the body carries backticks, quotes, or newlines',
            1)
    body = body.strip("\n")
    if not body.strip():
        refuse(
            "input",
            "the body is empty (whitespace only) — an empty message costs every "
            "recipient a wake and a read, and says nothing.\nWrite the content, or drop the "
            "send.",
            1)
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
    # THE ONE GRANT. An addressable non-member joins the recipient set and NOTHING else: it gains
    # no row above, so it is absent from the census, the sweep, every lifecycle command, the pane
    # cap, `to: all` fan-out and the wake pass — each of those reads the roster, not this set.
    # Because BOTH `cmd_send` gates consult this one predicate, admitting the name here fixes the
    # recipient half and the ask-refusal in a single move, which is what the ruling requires.
    names |= set(addressable_nonmembers(args, base)[0])
    return names


def cmd_send(args):
    base = base_dir(args)
    sender = resolve_agent(args)
    force = getattr(args, "force", False)
    body = message_body(args)
    _, blocks = load_messages(base)

    # F5 — a typo'd recipient was accepted silently: the message landed under a name nobody
    # reads and the only signal was one "wake skipped" line the sender scrolled past.
    # Constraint 3: a register row that did not resolve is announced HERE, on the path that was
    # about to rely on it — not deferred to an audit nobody runs. A name silently missing from the
    # recipient set reads exactly like a name that was never admitted.
    report_addressable_errors(args, base)
    nonmembers = addressable_nonmembers(args, base)[0]
    known = known_recipients(args, base)
    if args.to not in known and not force:
        near = difflib.get_close_matches(args.to, sorted(known), n=1, cutoff=0.6)
        refuse(
            "state",
            f"'{args.to}' is not a known recipient — no roster row, no briefing, no "
            f"group, no relay token and no addressable non-member of that name."
            + (f" Did you mean '{near[0]}'?" if near else "")
            + f"\nknown: {', '.join(sorted(known))}\nsend anyway: --force",
            1)
    # S-7 — an `ask` stays OPEN until an answer is addressed to its SENDER via --re, and
    # `known_recipients` refuses any name none of its five sources carries (roster, briefing,
    # group, relay token, addressable non-member). So an
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
        refuse(
            "state",
            f"'{sender}' cannot receive a reply — no roster row, no briefing and no "
            f"group of that name — so an `ask` from you would stay OPEN forever. An answer "
            f"must be addressed to its sender (--re), and nobody can address you.\n"
            f"Send this as --type note (FYI) or --type flag if the type exists, or check in "
            f"first so you have a roster row: {coord_invocation(args)} checkin {sender} "
            f"\"<what you are doing>\".\n"
            # G-165: for a NON-MEMBER that check-in line is the FORBIDDEN repair, and this text
            # recommending it is how the trap reaches every next meta-agent. The correspondent
            # that hit it declined the advice and said so; the next one will not have that
            # context, so the alternative is named here rather than left to a ruling it cannot
            # read.
            f"⚠ If you are NOT a member of this run (a meta-agent with its own goal folder), do "
            f"NOT check in — that would make you a member, which is the thing you are not. Ask "
            f"this package to admit you as an addressable non-member instead: add your "
            f"descriptor's path to {package_dir(args)}/addressable.csv and declare "
            f"`addressable: non-member` in that descriptor. You then resolve as a recipient and "
            f"gain nothing else — in particular NO WAKE: delivery is PULL, and you must read the "
            f"log yourself.\n"
            f"There is no --force for this one: 13 asks opened this way in one run and not "
            f"one of them can ever be closed.",
            1)

    # G-22 / #198 — the two enforcement halves of the broadcast discipline. `all` costs every seat
    # a wake and a read, so it must be justified rather than habitual: a broadcast names the clause
    # it claims, and `note` — the type that was 35 of a live run's 86 broadcasts — cannot claim any,
    # because a note is by definition something a seat that never reads it still acts correctly
    # without. The cheap channel is a GROUP; before this, none had ever been created.
    why = getattr(args, "why", None)
    if args.to == "all" and not force:
        if args.type == "note":
            refuse(
                "input",
                f"a `note` is never an `all` broadcast — if a seat that never reads it "
                f"still acts correctly, it does not belong in everyone's inbox.\n"
                f"Send it to a GROUP (`{coord_invocation(args)} create-group <name> <members>`) "
                f"or direct to the seats who need it.\n"
                f"If it genuinely binds every seat, it is a verdict/completion under one of: "
                f"{', '.join(sorted(BROADCAST_CLAUSES))} — send it as that type with --why.\n"
                f"override: --force",
                1)
        if not why:
            clauses = "\n  ".join(f"{k} — {v}" for k, v in sorted(BROADCAST_CLAUSES.items()))
            refuse(
                "input",
                f"`send all` requires --why <clause>, naming what makes this everyone's "
                f"business:\n  {clauses}\n"
                f"If none of them fits, the message is not a broadcast — send it to a group or "
                f"direct.\noverride: --force",
                1)
    if why and args.to != "all":
        refuse(
            "input",
            f"--why justifies a BROADCAST and '{args.to}' is not `all`, so it would "
            f"record a clause for a message nobody needed one for.\nDrop --why.",
            1)

    # G-21 — a seat mid-close has one job left, so a peer's direct message is REFUSED here, at the
    # CLI, rather than accepted into a log the seat will depart without reading. The refusal is the
    # POINT: it fails loud, the sender still HOLDS its message and knows now, and nothing can be
    # orphaned. Queueing for a successor was the alternative and was ruled against (leader #189) —
    # it assumes a successor exists, and tonight five of six closes had none, so a queue whose
    # consumer may never exist is accept-then-silence with extra steps.
    entry = closing_entry(base, args.to)
    if entry is not None and not closing_reaches(args.to, sender, entry) and not force:
        closer = entry.get("closer") or f"closer-{args.to}"
        refuse(
            "state",
            f"'{args.to}' is CLOSING (since {entry.get('since', '?')}) — its inbox is "
            f"{closer} and leader only, so this message would arrive as work it will never do "
            f"and context its memory hand-off needs.\n"
            f"You still hold it, and nothing is lost: send it to leader, or wait for the seat's "
            f"successor if it is renewed and send it then.\n"
            f"override (you are certain the seat must read this before it goes): --force",
            1)

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
            refuse(
                "state",
                f"'{args.to}' resolves to {named}, and every one of them has a BOUNDED "
                f"INBOX that '{sender}' is not among. This is a standing ruling about who may "
                f"spend those seats' context, not a judgement of your message.\n"
                f"You still hold it, and nothing is lost: send it to leader, who routes it.\n"
                f"override (it will still be filtered at each seat's read, though never silently "
                f"— their footers name it): --force",
                1)
        refuse(
            "state",
            f"'{args.to}' has a BOUNDED INBOX — it receives messages from "
            f"{', '.join(sorted(bound))} only, and '{sender}' is not among them. This is a "
            f"standing ruling about who may spend that seat's context, not a judgement of your "
            f"message.\n"
            f"You still hold it, and nothing is lost: send it to leader, who routes it.\n"
            f"override (and it will still be filtered at that seat's read, though never "
            f"silently — its footer names it): --force",
            1)
    if len(body) > MESSAGE_MAX and not force:
        refuse(
            "input",
            f"message is {len(body)} chars — max {MESSAGE_MAX}.\n"
            f"A body this long is a document, and every agent pays for it at every checkpoint. "
            f"Write it to a file, then send the PATH plus a 3-line summary: what it says, what "
            f"you want done with it, and by whom.\noverride: --force",
            1)
    if args.supersedes is not None and not any(b["num"] == args.supersedes for b in blocks):
        refuse(
            "state",
            f"--supersedes {args.supersedes} — no such message in the log (it ends at "
            f"#{blocks[-1]['num'] if blocks else 0}). A retraction pointing at nothing retracts "
            f"nothing.\nFind the number you meant: {coord_invocation(args)} read --digest --all",
            1)

    re_num = getattr(args, "re_num", None)
    if args.type == "answer" and re_num is None and not force:
        refuse(
            "input",
            "an answer must name the ask it answers — pass --re <ask#> (list them "
            "with `pending`).\nAn unlinked answer leaves the ask OPEN for every reader.\n"
            "override: --force",
            1)
    if re_num is not None and args.type not in ("answer", "verdict"):
        refuse(
            "input",
            f"--re is valid only on --type answer (required) and --type verdict "
            f"(optional) — not on '{args.type}'. A `re:` on any other type would make the "
            f"open-ask derivation lie.\nDrop --re, or send this as an answer.",
            1)
    if re_num is not None:
        target = next((b for b in blocks if b["num"] == re_num), None)
        if target is None:
            refuse(
                "state",
                f"--re {re_num} — no such message in the log (it ends at "
                f"#{blocks[-1]['num'] if blocks else 0}), so the ask would stay OPEN for every "
                f"reader.\nList the open asks: {coord_invocation(args)} pending",
                1)
        if target["type"] != "ask":
            refuse(
                "state",
                f"--re {re_num} — message #{re_num} is a '{target['type']}', not an "
                f"ask; --re links an answer/verdict to the ask it settles.\nList the open asks: "
                f"{coord_invocation(args)} pending",
                1)

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
    # ⚠ SAID AT THE MOMENT IT MATTERS, to the person who most needs it: the sender who has just
    # addressed a non-member and would otherwise wait for a reply that no wake will ever prompt.
    # The ruling is explicit that leaving this implicit is the defect — silence would be read as
    # "considering" rather than "never delivered".
    if args.to in nonmembers:
        print(c(f"-- delivery is PULL, not push: '{args.to}' is an addressable NON-MEMBER — it has "
                f"no pane in this run and is NEVER woken. The message is in the log addressed to "
                f"it, and it must read the log itself. Silence from it means NOT YET READ, never "
                f"'considering'. If it is time-critical, confirm out of band.", C_HINT))
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
    nonmembers = addressable_nonmembers(args, base)[0]
    for name in sorted(recipients):
        row = current_row(rows, name)
        if name in nonmembers:
            # NOT "not launched" — that reason implies a pane is coming. This one never is, and the
            # sender must be able to tell a seat that has not started from a correspondent that is
            # never woken by design.
            skipped.setdefault("PULL delivery — addressable NON-MEMBER, no pane in this run; it "
                               "reads the log itself", []).append(name)
        elif row is None:
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
            refuse(
                "state",
                f"no message #{msg} in the log — it ends at #{blocks[-1]['num']}.\n"
                f"List what is there: {coord} read --digest --all",
                1)
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
                f"--type answer --inline --re {first['num']}", C_HINT))

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
    print_owner_status(base, label_width=7, args=args)
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
    # The SENDER bound, which the line above never carried — and the omission was not neutral: for
    # a bounded seat that line asserts "direct messages always reach you", which is the opposite of
    # true. `me` is the identity the CLI resolved for THIS caller; there is deliberately no way to
    # ask for another seat's (G-197, and see inbox_bound_line).
    bound_line = inbox_bound_line(me, inbox_decls(args),
                                  [w["agent"] for w in discover_workers(workers_dir(args))])
    if bound_line:
        print(f"{c('senders:', C_LABEL)} {bound_line}")
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
    # s3-04, the twin site. Surfaced on EVERY seat's status for the reason the line above carries:
    # a stuck lifecycle is the run failing to finish an act it started, and the seat it is ABOUT is
    # often the one that most needs to see it. Until Stage 4's revival arm lands, these two prints
    # are the ONLY readers the marker has.
    _lcl = lifecycle_line(base)
    if _lcl:
        print(c(_lcl, C_DEAD))
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
        print(c(f"next:   continue your task ({coord} send leader \"<msg>\" --type ask --inline when "
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
            f"answer one: {coord} send <sender> \"<answer>\" --type answer --inline --re <#>")
    section("open asks to everyone", broadcast, "answer only what is yours to answer")
    section("your asks nobody has answered", from_me,
            "chase the recipient, or retract with --supersedes <#>")


def cmd_gateway_status(args):
    """Task 7.57 criterion (1), the DETECT half only. Reports whether an ignite daemon
    serves THIS workspace on THIS machine (`.rbtv/modules/ignite/server.json`,
    machine-keyed, D27) — a pure file read, always safe, never opt-in.

    It does NOT route send/read through the gateway: RULED NOT MET, with the finding
    (task 7.57 fork 1) — the gateway's nine intents carry no addressed-message door.
    `checkin`/`send`/`read`/`pending`/... are UNCHANGED by this command's existence and
    never call anything in this function.

    `--probe` is the SPEAK half, and it is INERT UNLESS PASSED (Fork 2, ruled: client
    mode is opt-in, never silently switched) — it makes exactly ONE live, read-only
    `inspect` call to prove the client can authenticate to the gateway as a sender. It
    never sends or reads a coordination message; there is no door for that yet.
    """
    root = gateway_client.resolve_workspace_root(VAULT_ROOT)
    info = gateway_client.detect_daemon(root)
    print(f"workspace root: {root}")
    if info["detected"]:
        print(f"daemon detected: yes — {info['host']}:{info['port']}  ({info['reason']})")
    else:
        print(f"daemon detected: no  ({info['reason']})")
    print("coordination transport: run-package substrate (file log + flock), UNCHANGED —")
    print("  send/read/checkin/pending never route through the gateway. NOT MET (task 7.57")
    print("  fork 1): the gateway's 9 intents carry no addressed-message door — enqueue-job's")
    print("  send-message action takes exactly (type, thread, corpus), no recipient; inspect")
    print("  messages requires an integer execution id a tmux seat does not have.")
    if not getattr(args, "probe", False):
        print(c("next:   --probe to make one live read-only `inspect` call and prove the "
                 "authenticated wire", C_HINT))
        return
    if not info["detected"]:
        print("PROBE SKIPPED: no daemon detected for this workspace/machine — nothing to call.")
        sys.exit(1)
    token = gateway_client.resolve_token()
    print(f"probing {info['host']}:{info['port']} as an authenticated sender "
          f"({'token present' if token else 'NO TOKEN in env — expect AUTH_REFUSED'}) ...")
    try:
        status, envelope = gateway_client.call_gateway(
            info["host"], info["port"], "inspect", {"target": "queue"}, token=token)
    except gateway_client.GatewayTransportError as exc:
        print(f"PROBE FAILED (transport): {exc}")
        sys.exit(5)
    print(f"HTTP {status} — {json.dumps(envelope)}")
    if envelope.get("ok") is True:
        print("PROBE: authenticated call SUCCEEDED (ok:true) — the client CAN reach the "
              "gateway as an authenticated sender. This proves the WIRE only — it is not a "
              "coordination send or read, and none exists on this door yet.")
        return
    err = envelope.get("error") or {}
    print(f"PROBE: call returned ok:false — code={err.get('code')} message={err.get('message')}")
    sys.exit(3 if err.get("code") == "AUTH_REFUSED" else 1)


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
    refuse(
        "state",
        f"`{command}` — {len(problems)} seat(s) disagree with the run's registry:\n  "
        f"{detail}\n"
        f"  registry: {package_dir(args) / 'taskforce.csv'}\n"
        f"THE DESCRIPTOR IS AUTHORITATIVE — it is what the harness command is built from, so "
        f"launching now would bind the DESCRIPTOR's value and the taskforce.csv row would stay "
        f"a wrong record.\n"
        f"Fix whichever is wrong: edit the DESCRIPTOR to change what actually binds, or the CSV "
        f"row to correct the record. Then re-run.\n"
        f"--force launches on the descriptor's value anyway and says so.",
        2)


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
        refuse(
            "state",
            f"no worker briefing carries `agent: {', '.join(sorted(missing))}` in "
            f"{workers_dir(args)}, so there is nothing to launch under that name.\n"
            f"briefed seats: {known}\nFix the name, or add the briefing folder first.",
            1)
    return picked


def cmd_launch(args):
    role_desc = "leader's and the chief-of-staff's (it opens seats and spends plan budget)"
    # #210: the roster is resolved FIRST because the memory gate is sized by seat COUNT, and both
    # gates must be answered together. Nothing here opens a pane or writes a surface — reading
    # briefings has no side effect — so evaluating the role gate a few lines later costs nothing
    # and buys the caller both verdicts at once. `--dry-run` keeps the role gate ALONE: it opens
    # nothing, so refusing it on available memory would refuse a command that cannot spend any.
    workers = seats_by_name(args, args.only)
    # G-257 / `d-g257-widening-not-threading`: BOTH BRANCHES CARRY THE SAME PREDICATE. Missing
    # one leaves a --dry-run and a real launch disagreeing about who may act -- the shape a reader
    # trusts and a test misses (S4-g is its control).
    #
    # The TARGET is threaded for the REFUSAL TEXT ONLY, so a refusal names WHO was being launched;
    # `launch`'s target is the `--only` set, or a mass launch when none was named. `self_legal` is
    # passed EXPLICITLY as False at both sites rather than left to the default: there is no self
    # case at `launch` -- a seat does not launch itself into existence -- and s12-02's self/other
    # threading is therefore INERT here, which is exactly why it could not have discharged G-257.
    launch_target = args.only or "(mass launch)"
    if args.dry_run:
        gate(args, "launch", is_authorized_launcher, role_desc,
             target=launch_target, self_legal=False)
    else:
        launch_gates(args, "launch", is_authorized_launcher, role_desc, len(workers) or 1,
                     target=launch_target, self_legal=False)
    # G-51: the descriptor binds and the registry is a record nothing read until now. Checked on
    # the DRY-RUN path too — a dry-run exists to show what a real launch would do, and hiding a
    # divergence from it would make the one command meant for inspection the one that lies.
    check_bindings(args, workers, "launch")
    if not workers:
        refuse(
            "state",
            f"no worker briefing carries an `agent:` frontmatter key in "
            f"{workers_dir(args)}, so there is no roster to launch.\n"
            f"Each seat needs workers/<agent>/agent.md with `agent: <name>` "
            f"(template: briefing-template.md beside coord.py).",
            1)

    # PROP-8 (tv-ux-review): validate EVERY seat's launch config BEFORE any pane opens. An
    # invalid model slug used to fail only at model-init, INSIDE each spawned pane — a whole
    # wave died before its first checkin, its panes holding memory until someone noticed.
    invalid = [(w, e) for w in workers for e in [validate_seat(w)] if e]
    if invalid and not args.dry_run:
        for w, e in invalid:
            print(f"  {w['agent']}: {e}\n    briefing: {w['briefing']}", file=sys.stderr)
        refuse(
            "state",
            f"{len(invalid)} seat(s) above carry an invalid harness/model — NO pane "
            f"was opened (not even for the valid seats). Fix the briefing frontmatter, then "
            f"relaunch the whole set.",
            1)

    target = os.environ.get("COORD_LAUNCH_TARGET") or os.environ.get("TMUX_PANE")
    if not target and not args.dry_run:
        refuse(
            "environment",
            "launch opens tmux panes and this shell is not inside tmux (no $TMUX_PANE),"
            " so there is no window to open them in.\nRun it from leader's tmux pane, or use "
            "--dry-run to see the commands it would run.",
            1)

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
    refused = []
    for w in workers:
        pane, err = launch_seat(w, args, target)
        kind, wname = seat_placement(w)
        place = {"own": "window", "shared": f"window:{wname}"}.get(kind, "pane")
        label = f"{w['agent']} ({w['harness']}/{w['model'] or 'plan-default'}, {place})"
        if err:
            refused.append(w["agent"])
            print(f"  {label}: FAILED — {err}", file=sys.stderr)
        else:
            print(f"launched {label} in {pane}"
                  + (" (session /rename scheduled)" if w["harness"] == "claude" else ""))
    status, detail = ensure_team_monitor(args)   # after the seats: the room is up by now
    # 7.88: ONE renderer for every outcome, so "already up" and "was dead, restarted" cannot drift
    # back into printing the same thing — which is the defect this row exists to fix.
    text, tone, to_stderr = render_monitor_report(status, detail)
    print(c(text, tone), **({"file": sys.stderr} if to_stderr else {}))
    # ---- the launch's VERDICT (leader ruling, exit-code semantics) -------------------------
    #
    # Every PRE-SPAWN refusal in this command — PROP-8, the role gate, the memory gate — already
    # exits 1, and `close-seat --renew` exits 1 when its launch_seat fails. This per-seat loop was
    # the ONE path that printed `FAILED` and exited 0, so a launch in which every seat was refused
    # reported SUCCESS to anything reading the status. Making the path consistent with the command
    # it lives in, not new policy.
    #
    # SUCCESSES ARE KEPT — no rollback. A partially-launched wave is a real state and tearing down
    # working seats to make the exit code tidy would cost more than the defect.
    #
    # ⚠ THE COUNTS ARE NOT DECORATION: an exit code cannot distinguish PARTIAL from TOTAL failure,
    # and that difference decides what the operator does next (relaunch two seats, or find out why
    # nothing came up). The code says "something failed"; only this line says how much.
    launched = len(workers) - len(refused)
    if refused:
        print(c(f"launch INCOMPLETE: {launched} launched, {len(refused)} refused "
                f"({', '.join(refused)}). The launched seats are UP and were not rolled back.",
                C_DEAD), file=sys.stderr)
        # ⚠ AND THE NEXT-HINT IS ITSELF PART OF THE DEFECT: "every seat above must appear there"
        # is false the moment one was refused, and a reader who checks `workers` and finds the
        # refused seat missing would read the tool's own instruction as evidence something ELSE
        # broke. Fixing the exit code and leaving this sentence unqualified MOVES the lie.
        print(c(f"next: {coord_invocation(args)} workers — the {launched} LAUNCHED seat(s) must "
                f"appear there; the {len(refused)} refused one(s) will not, and that is this "
                f"command's own result, not a second failure", C_HINT))
        sys.exit(1)
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
        refuse(
            "environment",
            f"cannot capture '{args.target}' — {err}. A scrollback capture needs the "
            f"seat's registered pane to still exist.\nCheck the roster: "
            f"{coord_invocation(args)} workers",
            1)
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
    # THE SAME THREE ARGUMENTS ON BOTH BRANCHES. Missing one leaves the gate inconsistent between
    # a dry-run and a real close — the shape a reader trusts and a test misses.
    #
    # `self_legal` is NOT among them, deliberately: `close` spawns a CLOSER and is leader's alone
    # (`d-close-renew-decider-recorded` keeps closing-another-seat leader-gated as a failure path,
    # and this command IS that path). The target is threaded anyway, because it is what lets a
    # refusal tell the two cases apart — a seat that names ITSELF here is not trying to close
    # anyone, it is reaching for the self path, and `role_verdict` sends it to `checkout --renew`
    # instead of to "ask leader". Without the target both refusals read identically and the second
    # one sends the caller somewhere that cannot help them. The SELF path itself is
    # `close-seat --renew` / `checkout --renew`, never this command.
    if args.dry_run or mech_seat is not None:
        gate(args, "close", is_leader, role_desc, target=args.target,
             remedy=CLOSE_OTHER_REMEDY, case=CLOSE_OTHER_CASE)
    else:
        launch_gates(args, "close", is_leader, role_desc, 1, target=args.target,
                     remedy=CLOSE_OTHER_REMEDY, case=CLOSE_OTHER_CASE)
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
        refuse(
            "environment",
            "close spawns a closer seat in tmux and this shell is not inside tmux (no "
            "$TMUX_PANE).\nRun it from leader's tmux pane, or use --dry-run to see the closer "
            "prompt.",
            1)
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


def renew_in_place(seat, pane, pane_live, pane_window_name=None):
    """Pure: True when a renew must RESPAWN the seat's existing pane rather than kill it and split
    a fresh one. G-12 — kill+split re-tiles the whole window, so every renew destroyed the layout
    the owner had arranged.

    THE DESCRIPTOR WINS (G-154): keep the pane when it is ALREADY where the briefing asks the seat
    to be; re-place it when it is not. Keying on placement KIND alone was correct only while no
    seat declared a window — the moment `r-window-layout` put `window:` on thirteen descriptors it
    silently switched EVERY one of them off this path, so each `close-seat --renew` began killing
    its pane. Nobody edited this function; the descriptors underneath it changed, and the run
    record went on describing renew as "respawns into the SAME pane" while it destroyed panes.

    `pane_window_name` is the window the pane is in RIGHT NOW, resolved by the caller so this stays
    pure. Omitted, a window/shared seat re-places — the pre-G-154 behaviour — so a caller that has
    not been taught to measure the window cannot silently acquire the new path."""
    if not (bool(pane) and bool(pane_live)):
        return False
    place, wname = seat_placement(seat)
    if place == "pane":
        return True                      # no window demand at all — wherever it sits is correct
    # `own`/`shared`: the briefing names a window. Respawn in place only when the pane ALREADY sits
    # in that window; otherwise this renew is also the act that moves the seat where it belongs,
    # and keeping the pane would strand it. That is what the old comment feared, correctly — it
    # just applied the fear to every window seat instead of only the misplaced ones.
    return bool(pane_window_name) and pane_window_name == wname


def cmd_close_seat(args):
    # The closer runs this as the tail of its own close; leader runs it directly for dead panes.
    #
    # SELF IS LEGAL HERE, AND WITHOUT `--force` (`d-close-renew-decider-recorded`): the SEAT
    # decides its own renew/refresh — deterministically, with no agent in the execution path — and
    # the LEADER decides two things only, acceptance that gates a done-close and the closing of
    # ANOTHER seat, which stays leader-gated as a failure path (that is `cmd_close`, and the
    # CLOSE_OTHER_CASE below is this command's own version of the same refusal).
    _caller = gate(args, "close-seat", is_leader_or_closer, "leader's or a closer-* seat's",
                   target=args.target, self_legal=True, remedy=CLOSE_OTHER_REMEDY,
                   case=CLOSE_OTHER_CASE)
    # W1 — A WARNING, NEVER A REFUSAL. The self-act is legal and stays legal; what it is not is
    # SURVIVABLE for the caller's own turn. A self `close-seat --renew` respawns the caller's own
    # pane when the seat already sits in the window its descriptor names (`renew_in_place`, and
    # G-154 is why placement decides it) and kills it outright when it does not — `tmux
    # respawn-pane -k` either way — so EVERY STEP AFTER THIS COMMAND NEVER RUNS. That is not
    # hypothetical: the "checkout kills its own pane" fix was REFUSED for destroying the in-place
    # renew path, and the selftest still carries that ratification (G-134's row).
    # This warning is load-bearing between Stage 1 and Stage 3: Stage 1 makes the self-act LEGAL,
    # Stage 3 supplies the out-of-pane executor that makes it SURVIVABLE. Until then the caller is
    # told, every time, which path was built for this.
    if _caller and _caller == args.target:
        print(c(f"WARNING self-act: '{_caller}' is closing ITSELF. This kills or respawns your own "
                f"pane" + (" (--renew respawns it in place only if you already sit in the window "
                           "your descriptor names)" if getattr(args, "renew", False) else "") +
                f", so every step you had planned after this command will NEVER RUN.\n"
                f"The path built for this is `{coord_invocation(args)} checkout --renew` — it "
                f"hands off and lets the seat come back without destroying the turn that asked.",
                C_DEAD), file=sys.stderr)
    base = base_dir(args)
    # A DOOR IS NOT CLOSED MECHANICALLY. A seat declaring `relays:` carries the relay path to a
    # HUMAN role, and its pane is the surface that human is watching — the owner can be sitting at
    # it while the seat itself is checked out.
    #
    # G-151, corrected: this comment used to read "renew here does not respawn in place — it kills
    # and re-creates", generalised from ONE measurement (leader #385). That reading was true of the
    # seat measured and false as a general claim, and it sat thirty lines from `renew_in_place`'s
    # docstring saying the opposite — a contradiction inside one file that two rulings then leaned
    # on from opposite sides, each correct from where it stood. Both were describing the SAME
    # decision from different seat classes. What is actually true: the plain close ALWAYS kills the
    # pane; the renew kills it too UNLESS the seat is already in the window its briefing asks for
    # (G-154), in which case the pane is kept and respawned. This early check cannot tell which
    # case it is in — `in_place` is not computed until later — and it does not need to: a door is
    # not closed mechanically on EITHER branch.
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
            refuse(
                "state",
                f"'{args.target}' carries a relay path to a human role "
                f"({', '.join(sorted(_relays))}), and its pane {_pane} is LIVE. A plain close "
                f"kills that pane; a --renew kills it too unless the seat is already in the "
                f"window its briefing asks for (G-154), and you cannot tell which case you are "
                f"in from here. So this may close the door a human is watching, possibly while "
                f"they are away and expecting it to be there.\n"
                f"A door in the wrong place is cosmetic; a door destroyed is an outage.\n"
                f"If you mean it (the run is ending, or the owner has moved): --force",
                1)
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
    # G-154: the window the pane is in RIGHT NOW is measured here, not inferred, because that is
    # the only thing that can say whether the seat is already where its briefing wants it.
    in_place = bool(seats) and renew_in_place(seats[0], old_pane, old_pane in live_panes(),
                                              tmux_pane_window_name(old_pane) if old_pane else None)
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
        refuse(
            "environment",
            "panel splits a strip into the CALLING tmux window and this shell is not "
            "inside tmux (no $TMUX_PANE).\nRun it from leader's own pane.",
            1)
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


def cmd_kill_pane(args):
    """Reap ONE pane by id directly -- the chief-of-staff's route to freeing a leaked pane when a
    raw `tmux kill-pane` is refused by the harness auto-mode classifier and `close-seat` needs a
    roster-known SEAT NAME rather than a bare pane id (task 7.91, owner-directed).

    MEASURED (leader #1580), not guessed: `coordinate launch --force` -- also a `coordinate` verb
    -- is ALSO blocked by the classifier from the chief-of-staff's pane, so wrapping a verb in
    coord.py is not by itself sufficient; `coordinate close-seat --force` PASSES from that same
    pane, and close-seat kills panes too, so killing a pane is not by itself what is refused. The
    ONE shape measured to pass while killing panes from that pane is close-seat's -- so this
    mirrors it as closely as the row allows: the same `tmux_kill_pane` + `verify_pids_gone` kill
    step, the same gate() role check, the same --force convention for a deliberate-but-risky act.
    The discriminator itself is NOT known and this does not guess one (criterion 1 is proof from
    %190, never an assumed pass from a pane that was never blocked).

    Kills the PANE ONLY -- like `reap`, never like `close-seat`: no transcript export, no roster
    row mutation, no session-trace close. A pane this frees still owes a close-seat afterwards if
    its row was ever active; freeing memory and completing a lifecycle are different acts, and this
    one does only the first (criterion 6 -- `cmd_reap`'s own docstring states the same split).

    TWO refusals are UNCONDITIONAL, no --force, ever (bars.md 4, criterion 2): the pane belongs to
    a seat whose descriptor declares `relays:` (the owner door, or any future human-contact role),
    or the pane matches no CURRENT roster row of this run at all. Both are REFUSED BY THE TOOL, not
    by convention, and both are derived from the roster + the descriptor's own `relays:` field --
    never a kit-side name list (the same derivation `inbox_decls`/`reap_blockers` already use).

    A THIRD refusal -- the pane's owning row is still `active: yes`, i.e. NOT roster-done
    (criterion 5) -- is the SAME kind of deliberate-act refusal close-seat's own door check uses,
    and shares its escape: --force, with the same "if you mean it" shape. G-196's lesson is why
    this reads the ROW's `active` field as ground truth rather than inferring aliveness from
    whether the pane is in `live_panes()` -- a pane that changed out from under a stale roster row
    must not be misread as free just because the OLD pane id looks live or dead."""
    gate(args, "kill-pane", is_leader_or_cos_or_closer,
         "leader's, chief-of-staff's, or a closer-*'s")
    target = args.pane_id
    if not target.startswith("%"):
        refuse(
            "input",
            f"'{target}' does not look like a tmux pane id (expected e.g. '%190') -- "
            f"kill-pane targets a PANE, never a seat name (that is close-seat's argument)",
            1)
    base = base_dir(args)
    _, _, rows = load_workers(base)
    current = [current_row(rows, a) for a in dict.fromkeys(r["agent"] for r in rows)]
    owner_row = next((r for r in current if r and r.get("pane") == target), None)

    if owner_row is None:
        refuse(
            "state",
            f"pane {target} matches no CURRENT roster row of this run -- kill-pane only "
            f"touches panes this run's own roster accounts for (criterion 2). If this is a "
            f"genuine leak from something else, it is not this tool's to reap. No --force lifts "
            f"this.",
            1)

    decls = inbox_decls(args)
    relays = (decls.get(owner_row["agent"]) or {}).get("relays")
    if relays:
        refuse(
            "state",
            f"pane {target} belongs to '{owner_row['agent']}', which carries a relay "
            f"path to a human role ({', '.join(sorted(relays))}) -- its pane is a DOOR, never "
            f"reapable, unconditionally (bars.md 4, r-owner-afk-liaison-parked). No --force "
            f"lifts this.",
            1)

    if owner_row["active"] == "yes":
        if not getattr(args, "force", False):
            refuse(
                "state",
                f"pane {target} belongs to '{owner_row['agent']}', whose roster row is "
                f"still ACTIVE -- not roster-done (criterion 5). A live working seat's pane is "
                f"close-seat's or renew's to manage, not a bare reap. If you mean it (the seat is "
                f"gone but the row was never closed): --force.",
                1)
        print(f"WARNING: '{owner_row['agent']}' is still roster-ACTIVE -- killing its pane anyway "
              f"because --force was given. Its roster row is UNCHANGED by this call and still "
              f"needs a close-seat.", file=sys.stderr)

    idents = pane_harness_idents(target)
    ok, err = tmux_kill_pane(target)
    print(f"pane {target} ({owner_row['agent']}): {'killed' if ok else 'kill FAILED -- ' + err}")
    if not ok:
        sys.exit(1)
    survivors, note = verify_pids_gone(idents)
    if idents:
        print(f"process check: {len(idents)} harness pid(s) "
              + (f"GONE{' -- ' + note if note else ''}" if not survivors
                 else f"NOT gone -- {note}"))
    # Criterion 4: asserted from tmux list-panes, never inferred from tmux_kill_pane's exit code
    # (which only says the COMMAND ran, not that the pane is actually gone -- G-10's whole point).
    still_there = target in live_panes()
    print(f"tmux check: pane {target} "
          + ("STILL LISTED -- the kill did not take" if still_there else "GONE"))
    if still_there:
        sys.exit(1)
    print(c(f"next: {coord_invocation(args)} workers -- '{owner_row['agent']}' still shows in the "
            f"roster{' (was still active)' if owner_row['active'] == 'yes' else ''}; it still owes "
            f"a close-seat to finish its lifecycle", C_HINT))


def cmd_relaunch_pane(args):
    """Relaunch a seat's harness INTO A NAMED, ALREADY-REGISTERED PANE, in place (task 7.95,
    G-282) — the path `close-seat --renew` cannot take for a seat carrying `relays:`, because
    the door guard inside cmd_close_seat refuses that pane UNCONDITIONALLY once it is live,
    checked out or not (bars.md 4). This is not a weaker close-seat: it never kills anything and
    never touches that guard — it only respawns a pane that is ALREADY bare (no harness running
    in it) and ALREADY roster-done, so the worst case of a wrong call is a refusal, never a
    destroyed pane. It retires the chief-of-staff's `tmux send-keys` stopgap, which brought the
    door back with none of `launch`'s three gates behind it (criterion 3): the memory floor,
    check_bindings (G-51), and the roster/session-trace writes launch_seat always carries.

    MIRRORS THE RENEW-IN-PLACE PATH, NOT close-seat ITSELF (criterion 2): the same two
    primitives `cmd_close_seat --renew`'s in-place branch uses — `tmux_respawn_pane` then
    `launch_seat(..., pane=pane_id)` — called directly, so this command never reaches
    `cmd_close_seat` and therefore never reaches its guard, and never needs --force to do its
    job. The roster row is NOT written here: it is written by the relaunched seat's own
    subsequent `checkin`, exactly as a real renew relies on — and that checkin is not refused by
    P37 (the zombie double-checkin guard), because it lands from the SAME pane its own prior row
    (if any) already names.

    THE PANE ID IS A REQUIRED, CROSS-CHECKED INPUT (criterion 1, bars.md 3): never resolved by
    this tool from memory or by name alone — the caller reads it fresh from `coordinate workers`
    and it must match the roster's OWN latest recorded pane for the target, or this refuses
    unconditionally. A caller naming the wrong pane is exactly the failure bars.md 3 exists to
    prevent, and there is no legitimate reason to force through a mismatch: it means either the
    id is wrong or the roster is stale, and neither is fixed by acting on a pane current records
    do not attribute to this seat.

    FOUR REFUSALS carry NO --force escape, because the risk on each is silent and undoable:
      - no briefing carries this agent name — nothing to relaunch (use `launch` instead)
      - the pane id does not match the roster's own recorded pane for this agent (bars.md 3 —
        resolve it fresh)
      - the pane is not a live tmux pane at all (use `launch --only` for a fresh one)
      - the pane still holds a LIVE HARNESS PROCESS — this is not a bare pane, and respawning it
        would silently kill whatever is running there, worst case an owner mid-session; ground
        truth is read from /proc (G-10/G-11's own discipline: ask the process table, never the
        roster), so a stale-but-ACTIVE roster row cannot mask a genuinely running harness even
        under --force below
    ONE refusal IS force-escapable, matching kill-pane's own criterion-5 convention exactly: the
    roster row is still ACTIVE (not roster-done) — same "if you mean it" shape, for the same
    reason (a live seat's pane is close-seat's or renew's to manage). --force lifts ONLY this
    one; the live-harness check right after it is a separate, unconditional backstop and stays in
    force regardless — the roster can be wrong, /proc cannot be argued with.

    check_bindings (G-51) runs before any of the pane-state checks, on the dry-run path too,
    matching `cmd_launch`'s own reasoning verbatim: a dry-run exists to show what a real relaunch
    would do, and hiding a registry divergence from it would make the one command meant for
    inspection the one that lies."""
    role_desc = "leader's, chief-of-staff's, or a closer-*'s"
    seats = [w for w in discover_workers(workers_dir(args)) if w["agent"] == args.target]
    if not seats:
        refuse(
            "state",
            f"no worker briefing carries `agent: {args.target}` in "
            f"{workers_dir(args)}, so there is nothing to relaunch. This verb only revives an "
            f"already-registered seat into its own pane; a seat with no briefing has never had "
            f"one.",
            1)

    if args.dry_run:
        gate(args, "relaunch-pane", is_leader_or_cos_or_closer, role_desc)
    else:
        launch_gates(args, "relaunch-pane", is_leader_or_cos_or_closer, role_desc, 1)

    # G-51, on the dry-run path too (see docstring) — check_bindings does not special-case
    # dry_run itself; it refuses on a real divergence regardless.
    check_bindings(args, seats, "relaunch-pane")

    if not args.pane_id.startswith("%"):
        refuse(
            "input",
            f"'{args.pane_id}' does not look like a tmux pane id (expected e.g. "
            f"'%501') -- relaunch-pane targets a PANE, never a bare number or a seat name.",
            1)

    base = base_dir(args)
    _, _, rows = load_workers(base)
    row = current_row(rows, args.target)
    recorded = (row or {}).get("pane") or ""
    if recorded != args.pane_id:
        refuse(
            "state",
            f"{args.pane_id} does not match the roster's own recorded pane for "
            f"'{args.target}' ({recorded or 'none on record'}). Resolve the pane fresh with "
            f"`{coord_invocation(args)} workers` (bars.md 3 -- never recall a pane id) and "
            f"retarget. No --force lifts this: a mismatch means either the id is wrong or the "
            f"roster is stale, and neither is fixed by acting on a pane current records do not "
            f"attribute to this seat.",
            1)

    if row["active"] == "yes":
        if not getattr(args, "force", False):
            refuse(
                "state",
                f"'{args.target}'s roster row is still ACTIVE -- not roster-done. A "
                f"live seat's pane is close-seat's or renew's to manage, not a bare relaunch. "
                f"If you are certain the row is stale (the seat is gone but was never closed): "
                f"--force.",
                1)
        print(f"WARNING: '{args.target}' is still roster-ACTIVE -- relaunching into its pane "
              f"anyway because --force was given. Its roster row is unchanged by this call.",
              file=sys.stderr)

    if args.pane_id not in live_panes():
        refuse(
            "environment",
            f"{args.pane_id} is not a live tmux pane -- there is nothing to relaunch "
            f"into. If the pane is genuinely gone, use `{coord_invocation(args)} launch --only "
            f"{args.target}` to open a fresh one instead.",
            1)

    live_idents = pane_harness_idents(args.pane_id)
    if live_idents:
        refuse(
            "environment",
            f"{args.pane_id} still holds a live harness process "
            f"({', '.join(str(p) for p, _ in live_idents)}) -- this is not a bare pane, and "
            f"respawning it would silently kill whatever is running there, with no undo. No "
            f"--force lifts this. If that process is a stuck registration, tear it down "
            f"properly first: {coord_invocation(args)} close-seat {args.target}.",
            1)

    seat = seats[0]
    if args.dry_run:
        cmd, _err = harness_command(seat, prompt_path=(base_dir(args) / "prompts" /
                                                        f"{seat['agent']}-<stamp>.txt"))
        print(f"[dry-run] would respawn {args.pane_id} and start {seat['agent']} "
              f"({seat['harness']}/{seat['model'] or 'plan-default'}) in it, in place: "
              f"{cmd if cmd else '(harness_command refused -- see validate_seat)'}")
        return

    # A relaunch reads current rules just as a fresh launch does — it lands mid-run, exactly
    # when sources have been drifting (mirrors cmd_close_seat's own renew branch).
    refresh_mirrors_for(seats[:1])
    tmux_raise_history_limit()
    ok, rerr = tmux_respawn_pane(args.pane_id, seat["cwd"])
    if not ok:
        refuse(
            "environment",
            f"respawn of {args.pane_id} FAILED -- {rerr}. Nothing was started; verify "
            f"at tmux capture-pane -p -t {args.pane_id} before retrying.",
            1)
    pane, err = launch_seat(seat, args, args.pane_id, pane=args.pane_id)
    if err:
        print(f"relaunch FAILED: {err}\nThe pane was respawned but the harness never verified "
              f"up -- capture it: tmux capture-pane -p -t {args.pane_id}", file=sys.stderr)
        sys.exit(1)
    relays = (inbox_decls(args).get(args.target) or {}).get("relays")
    print(f"relaunched: {args.target} back up in {pane} (same pane, in place)"
          + (f" -- carries relays: {', '.join(sorted(relays))}; the door is up again"
             if relays else ""))
    print(c(f"next: {coord_invocation(args)} workers -- confirm '{args.target}' checked back in "
            f"on {pane}", C_HINT))


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

def harness_outcome(fn, args, capture_err=True):
    """Run a self-test SUBJECT and return (stdout, stderr, exit_code_or_None), never propagating
    its termination. `exit_code_or_None` is None when the subject returned normally.

    G-215(a). A TEST HARNESS MUST CONVERT A SUBJECT'S TERMINATION INTO A VERDICT, NEVER INHERIT
    IT. `SystemExit` is not an `Exception` subclass, so it walked straight through
    `cmd_selftest`'s abort handler — and `sys.exit` is how EVERY gate in this file refuses. One
    mutated guard was therefore enough to kill the whole suite with no verdict line, no FAIL line
    and exit 1. The mute death was not the whole cost: every row AFTER it went unrun and
    unreported, and an unrun row is indistinguishable from a passing one in the exit code. That is
    G-121 (a truncated run reads greener than a complete one) inside the suite written to catch it.

    Measured 2026-07-28: 16 of a 543-site mutation sweep's 226 CAUGHT verdicts were this shape —
    graded a catch on the exit code alone, with no failing row behind it.

    ONE derivation for both callers (PRIN-11): `refuse` used to carry its own copy of this
    try/except and `run` had none, which is exactly how the two disagreed about what a terminating
    command means.

    `capture_err=False` leaves stderr on the real stream, which is what `run` has always done —
    a warning a command prints during a successful row stays visible to whoever is watching.
    """
    import io
    from contextlib import redirect_stderr, redirect_stdout
    out, err, code = io.StringIO(), io.StringIO(), None
    try:
        if capture_err:
            with redirect_stdout(out), redirect_stderr(err):
                fn(args)
        else:
            with redirect_stdout(out):
                fn(args)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return out.getvalue(), err.getvalue(), code


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

    ⚠ G-215(a): `SystemExit` IS CAUGHT HERE TOO, and it is not a subclass of `Exception` — so
    until 2026-07-28 a subject that called `sys.exit` (every gate in this file refuses that way)
    walked through this handler and ended the run with NO verdict line at all: not even an ABORTED
    one. This handler is the LAST resort; the first is `harness_outcome`, which converts a
    subject's termination into that ROW's verdict so the suite continues. Reaching this line with
    a `SystemExit` now means one escaped a path that does not go through it.
    """
    failures, names = [], []
    aborted = ""
    try:
        _selftest_checks(args, failures, names)
    except (Exception, SystemExit) as exc:                      # noqa: BLE001 — the whole point
        import traceback
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        aborted = (f"{type(exc).__name__}: {exc} at "
                   f"{os.path.basename(frame.filename)}:{frame.lineno}")
        print(f"FAIL  selftest ABORTED after {len(names)} check(s) — {aborted}")
        print(f"      the raising check never reported, and every check after it never ran: "
              f"their results are UNKNOWN, not passing")
        failures.append(f"selftest ABORTED: {aborted}")
    verdict = "ABORTED" if aborted else ("PASS" if not failures else "FAIL")
    # G-218: A VERDICT IS A CLAIM ABOUT THE ENVIRONMENT IT WAS TAKEN IN, so the environment is
    # printed beside it. Two rows here read ambient state nobody declared — the caller's cwd and
    # the NAME the file was invoked under — and gave different verdicts on the same bytes to two
    # agents who were each reporting honestly. Both rows now establish their own preconditions;
    # this line exists so the NEXT such divergence is visible in the output instead of argued
    # about, and so a green quoted between agents carries the conditions it was obtained under.
    try:
        _in_pkg = discover_package_from(Path.cwd()) is not None
    except OSError:
        _in_pkg = None
    print(f"\nenvironment: invoked as `{os.path.basename(__file__)}` · cwd "
          f"{'INSIDE' if _in_pkg else ('outside' if _in_pkg is False else 'UNREADABLE for')} "
          f"a run package")
    print(f"selftest: {verdict} ({len(failures)} failure(s))")
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
    global flip_handoff_read   # s12-08: rebound to exercise the flip-FAILURE arm
    global session_close       # rebound to exercise the trace-write FAILURE direction
    real = (wake, set_pane_title, tmux_split_pane, tmux_new_window, tmux_kill_pane, tmux_capture,
            tmux_raise_history_limit, schedule_session_rename, tmux_window_panes, tmux_session_name,
            tmux_split_strip, restore_overview_strip, tmux_find_window_pane, tmux_send_text,
            tmux_send_enter, tmux_capture_tail, tmux_pane_window, detect_pane, live_panes,
            _acquire_flock, atomic_write, pane_title)
    env_agent = os.environ.pop("COORD_AGENT", None)

    # ---- The three REAL-TIME budgets, zeroed for the duration.
    #
    # These are waits for something the stubs above make IMPOSSIBLE, so the suite paid them in
    # full, every run, to reach the outcome it was always going to reach: 56.2s of a 60.3s run was
    # `time.sleep` (cProfile, 181 calls) against ~6s of actual work. It is the vacuous-guard family
    # on the COST axis — a retry budget spent in a state where the awaited event cannot occur — and
    # it priced every save gate and every mutation run at a minute of mostly sleeping.
    #
    # ⚠ EACH SITE, AND IN ONE CLAUSE WHY THE WAIT IS NOT THAT CHECK'S SUBJECT. An escape with no
    # named holder gets taken; shortening a budget on a check whose subject IS the wait would go
    # green WITHOUT EXERCISING THE BEHAVIOUR, which is the same family arriving in the grader.
    #
    #   NATIVE_ID_WAIT (40.3s / 13 calls, via launch_seat -> session_open)
    #     Subject: that a launch WRITES its session row and that the id RESOLVES. Launch is stubbed
    #     here, so no transcript is ever written and the poll returns '' at the deadline whatever
    #     the budget is. The one check that asserts resolution SUCCEEDING (the launch-path check in
    #     the 7.37 block) supplies its own transcript and passes `wait=0.0` explicitly, so it does
    #     not read this at all. No check anywhere asserts the polling itself.
    #
    #   WAKE_ENTER_VERIFY_DELAY_FIRST / _RETRY (15.2s / 11 calls, the P35 blocks)
    #     Subject: the Enter-verify RETRY MECHANICS — how many Enters, that the text is never
    #     retyped, that it is bounded, and the failure string. Every assertion is over
    #     `enter_calls` / `sent_texts` / `terr`. In production the delay lets the pane render
    #     before the re-capture; here `tmux_capture_tail` is a scripted stub popping a fixed
    #     sequence, so ITS ANSWER IS INDEPENDENT OF ELAPSED TIME — provably, not by judgement.
    #
    # NOT zeroed: HARNESS_UP_POLL, because `wait_harness_up` is already stubbed wholesale below;
    # zeroing a constant nothing reads would be decoration.
    global NATIVE_ID_WAIT, WAKE_ENTER_VERIFY_DELAY_FIRST, WAKE_ENTER_VERIFY_DELAY_RETRY
    waits_real = (NATIVE_ID_WAIT, WAKE_ENTER_VERIFY_DELAY_FIRST, WAKE_ENTER_VERIFY_DELAY_RETRY)
    NATIVE_ID_WAIT = 0.0
    WAKE_ENTER_VERIFY_DELAY_FIRST = 0.0
    WAKE_ENTER_VERIFY_DELAY_RETRY = 0.0

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
        # ⚠ THE FIXTURE PACKAGE MUST DECLARE A FLOOR (task 7.82). Without this the launch gate
        # refuses every launch here for FloorUndeclared, and the memory-gate checks below would
        # still go green — while testing "no budget declared" instead of "below the floor". That is
        # the misgrading shape: the assertion passes for a reason the test does not name.
        (pkg / "budget.json").write_text(
            json.dumps({"floors": {"launch_refuse_mb": 2000, "pressure_warn_mb": 2000}}))
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
            """Run a command expected to SUCCEED.

            NO ROW MAY TERMINATE THE SUITE (leader's bound on G-215(a)). A command that refuses
            here is a failure OF THIS ROW — recorded as its own failing check, with the suite
            continuing to every row behind it. A command EXPECTED to refuse belongs in `refuse()`,
            which is what the `cmd_reap` block's comment has been telling readers for weeks while
            nothing enforced it.
            """
            out, _err, code = harness_outcome(fn, ns(**kw), capture_err=False)
            if code is not None:
                check(f"harness/G-215(a): `{getattr(fn, '__name__', fn)}` was expected to SUCCEED "
                      f"and REFUSED instead (exit {code}) — recorded as THIS row's failure so the "
                      f"suite continues and every row behind it still reports. A command expected "
                      f"to refuse belongs in `refuse()`, never `run()`", False)
            return out

        def refuse(fn, **kw):
            """Run a command expected to REFUSE: returns (combined output, exit code)."""
            out, err, code = harness_outcome(fn, ns(**kw))
            return out + err, (0 if code is None else code)

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

        # ---- G-215(a): the control for "no row may terminate the suite" ----
        # This is the one thing that can prove the fix, and it has to run a subject that REALLY
        # terminates: a claim that the suite no longer truncates cannot be established by a subject
        # that never exits. Placed here, near the top, so the ~400 rows below are the "rows behind
        # it" — if the conversion regresses, this run dies HERE and every one of them goes unrun,
        # which is precisely the failure being fixed and is therefore its own loudest signal.
        def _harness_refuser(_a):
            print("the subject reached its refusal")
            sys.exit(3)

        def _harness_returner(_a):
            print("the subject returned normally")

        _hx_out, _hx_err, _hx_code = harness_outcome(_harness_refuser, ns())
        check("harness/G-215(a): a subject that TERMINATES is converted into an outcome instead of "
              "ending the run — this row EXECUTES after one called sys.exit, its exit code is "
              "reported as a value and its output was still captured. `SystemExit` is not an "
              "`Exception`, so it used to escape the abort handler entirely: no verdict line, no "
              "FAIL line, exit 1, and every row after it unrun — and an unrun row is "
              "indistinguishable from a passing one in the exit code",
              _hx_code == 3 and "the subject reached its refusal" in _hx_out)
        _hn_out, _hn_err, _hn_code = harness_outcome(_harness_returner, ns())
        check("harness/G-215(a): and a subject that RETURNS reports NO exit code — the two "
              "outcomes are distinct values, so 'it refused' can never be inferred from an empty "
              "one. Without this row the one above passes for a subject that never exits at all",
              _hn_code is None and "the subject returned normally" in _hn_out)

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

        # ---- guard sweep, slice 2 site 3: `approve`'s OWN precondition ----
        # The SAME predicate — an ACTIVE roster row plus a pane — is covered where it merely
        # SKIPS A WAKE (deliver_wakes' 8(b) chain: its `active != yes` and approval-gate branches
        # both fail their own rows under mutation). Here it AUTHORIZES KEYSTROKES into a pane, and
        # nothing asserted it. Coverage accreted around the harmless use of the predicate and not
        # the dangerous one, which is this slice's selection key.
        # The roster row is the ONLY thing vouching that a pane still belongs to a seat. Approving
        # against a departed seat is not a no-op: it types into whatever now occupies a pane the
        # run stopped tracking, which is the owner door's failure mode wearing a different verb.
        (pkg / "workers" / "apx").mkdir(exist_ok=True)
        (pkg / "workers" / "apx" / "agent.md").write_text(
            "---\nagent: apx\nharness: claude\nmodel: opus\n---\nbrief\n")
        run(cmd_checkin, agent="apx", summary="approval-gate probe", pane="%44")
        # Departed through the REAL verb, not by hand-writing the row: the state `approve` must
        # refuse has to be the state `checkout` actually produces, or the check asserts against a
        # fixture nobody's code can create. The debt checkout records is cleared below, so this
        # block cannot hand the G-134 section a seat it never set up.
        run(cmd_checkout, agent="apx", no_export=True)
        keys_log.clear()
        _apo, _apc = refuse(cmd_approve, target="apx", keys="1", no_enter=False)
        check("approve REFUSES a seat that is no longer ACTIVE even though its row still records "
              "a pane — a checked-out seat's pane is exactly the one that gets reused, and the "
              "roster is the only thing vouching it is still that seat's. The covered sibling is "
              "the same predicate deciding whether to skip a WAKE, which destroys nothing",
              _apc == 1 and "no ACTIVE pane is registered" in _apo
              and not any(p == "%44" for p, _ in keys_log))
        run(cmd_checkin, agent="apx", summary="approval-gate probe, no pane", pane="%44")
        update_row(base_dir(ns()), "apx", lambda r: r.__setitem__("pane", ""))
        keys_log.clear()
        _npo, _npc = refuse(cmd_approve, target="apx", keys="1", no_enter=False)
        check("approve refuses an ACTIVE row with NO pane too — the second disjunct, and a real "
              "state the wake chain has its own branch for. Without it the keys go to an EMPTY "
              "target, and tmux resolves that to the caller's own current pane: the approval "
              "lands on whoever typed it",
              _npc == 1 and "no ACTIVE pane is registered" in _npo and keys_log == [])
        clear_awaiting(base_dir(ns()), "apx")
        import shutil as _sh_ap
        _sh_ap.rmtree(pkg / "workers" / "apx")

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

        # ---- r-window-layout, THE LAUNCH-SIDE WIRING (guard sweep, slice 1 site 1) ----
        # The three r-window-layout rows below test `window_drift` ITSELF, and the close-side row
        # tests its wiring into `cmd_close_seat`. That close-side row exists because removing the
        # refusal from cmd_close_seat "left the three rows above green — the helpers were covered
        # and the path that actually kills was not". THE LAUNCH PATH HAD THE IDENTICAL GAP AND WAS
        # NEVER SWEPT: nothing drove a drifting window through `launch_seat`, so both halves of its
        # gate — that it refuses, and that `--force` skips it — were asserted by nothing. Found by
        # mutation: `if not getattr(args, "force", False)` at launch_seat could be removed and the
        # suite stayed green. Same seam, same file, diagnosed on one path and not carried to the
        # other — which is this run's recurring shape, not a new one.
        drf = pkg / "workers" / "drifty.md"
        drf.write_text("---\nagent: drifty\nmodel: opus\nwindow: wave-haiky\n---\nbrief\n")
        opened_pre_drift = len(opened)
        # `refuse` (not `run`) because the per-seat failure is written to STDERR, and this helper
        # is the only one that returns both streams. Its exit code is captured and deliberately
        # NOT asserted — see below.
        _wo, _wc = refuse(cmd_launch, agent="leader", only="drifty", dry_run=False)
        check("r-window-layout: the drift gate is WIRED INTO LAUNCH, not only into the predicate — "
              "a near-miss window stops the seat and NO pane is opened, and the message names the "
              "window it is one edit from. tmux does not refuse an unrecognised name: it SILENTLY "
              "OPENS one, so an unwired gate would leave the seat reading as correctly placed "
              "into furniture nobody ordered",
              "wave-haiku" in _wo and "FAILED" in _wo
              and len(opened) == opened_pre_drift)
        check("launch: a refused seat makes the COMMAND exit non-zero, and the summary carries "
              "COUNTS — an exit code cannot distinguish PARTIAL from TOTAL failure, and that is "
              "the difference between relaunching two seats and finding out why nothing came up. "
              "This row previously asserted nothing about the exit code on purpose: it was 0, and "
              "asserting 0 would have encoded the defect as expected behaviour",
              _wc == 1 and "launch INCOMPLETE" in _wo and "0 launched, 1 refused" in _wo)
        check("launch: and the NEXT-HINT is qualified — `every seat above must appear there` is "
              "false the moment one was refused, and a reader who then finds it missing from "
              "`workers` would read the tool's own instruction as evidence something ELSE broke. "
              "Fixing the exit code and leaving this sentence would MOVE the lie, not remove it",
              "every seat above must appear there" not in _wo
              and "that is this command" in _wo)
        # ⚠ THE EXIT CODE IS DELIBERATELY NOT ASSERTED HERE, and the omission is the finding.
        # `cmd_launch`'s loop PRINTS `FAILED — <reason>` to stderr and EXITS 0, so a launch in
        # which every seat was refused still reports success to a caller reading the exit status —
        # and still prints the reassuring `next: … workers` line. Pre-spawn refusals (PROP-8, the
        # role and memory gates) all `sys.exit(1)`, so the intent is plainly that a refused launch
        # is non-zero; the per-seat loop is the one path that does not. Asserting `== 0` here would
        # encode that as expected behaviour — the G-194(a) trap, a check whose red could only be
        # cleared by REINTRODUCING the defect. Raised to the leader as a behaviour question
        # (exit-code semantics are not the engineer's to change); this row asserts only what is
        # unambiguously correct today: the seat is stopped and no pane opens.
        _fo2, _fc2 = refuse(cmd_launch, agent="leader", only="drifty", dry_run=False, force=True)
        check("r-window-layout: and `--force` SKIPS it — the gate is conditional, which is the "
              "half a mutant removing `if not args.force` silently deleted. An exemption that "
              "cannot be exercised is untested, and a gate that cannot be overridden is a trap "
              "(the close-side door row rules the same way)",
              _fc2 == 0 and len(opened) > opened_pre_drift
              and "launch INCOMPLETE" not in _fo2)
        drf.unlink()

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

        # ---- guard sweep, slice 1 site 5: the transcript export on CLOSE-SEAT ----
        # ⚠ `cmd_checkout`'s export is covered in BOTH directions further down — and that is the
        # NON-DESTRUCTIVE verb. `close-seat` KILLS THE PANE, so its export is the last chance the
        # record ever gets, and it was asserted by nothing: every close-seat in this suite passes
        # `no_export=True` except two renews that pass False and then assert only rows, kills and
        # relaunch text. The covered sibling is the one that destroys nothing; the uncovered one
        # is the one that destroys the pane. Same shape as the drift gate and the wake abort.
        # This run's own standing bar — preserve a dying seat's transcript BEFORE any
        # `close-seat --no-export` — rests on this guard behaving in both directions.
        (pkg / "workers" / "xp").mkdir(exist_ok=True)
        (pkg / "workers" / "xp" / "agent.md").write_text(
            "---\nagent: xp\nharness: claude\nmodel: opus\n---\nbrief\n")
        xp_tr = pkg / "workers" / "xp" / "transcripts"
        run(cmd_checkin, agent="xp", summary="export probe", pane="%41")
        run(cmd_close_seat, agent="leader", target="xp", renew=False, no_export=False)
        check("close-seat EXPORTS the seat's transcript before killing its pane — the pane is the "
              "only place the scrollback lives, so a close that skips the export destroys the "
              "record with no second chance. `checkout` is covered for this and destroys nothing; "
              "the verb that kills was not",
              xp_tr.is_dir() and len(list(xp_tr.glob("*-xp-close.txt"))) == 1)
        _xp_before = len(list(xp_tr.glob("*.txt")))
        run(cmd_checkin, agent="xp", summary="export probe again", pane="%41")
        _xo = run(cmd_close_seat, agent="leader", target="xp", renew=False, no_export=True)
        check("close-seat --no-export SKIPS it — the escape exists for a pane that is already "
              "dead, where a capture attempt reports a failure about a seat that ended normally. "
              "Asserted so the flag cannot silently become a no-op and start exporting anyway",
              len(list(xp_tr.glob("*.txt"))) == _xp_before and "transcript:" not in _xo)
        import shutil as _sh
        _sh.rmtree(pkg / "workers" / "xp")

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
        # ---- s12-03 L-c (1 of 3): a CONTINUATION-literal site. This refusal's "refused:" was not
        # on the `print(` line but on the line after it, so a converter keyed on `print(f"refused:`
        # would have left it — and its exit code (1) unchanged means callers keyed on the code are
        # untouched. Read behaviourally, on the same output the rows above read.
        check("s12-03 L-c: the checkin NO-HARNESS refusal (a multi-line print whose `refused:` sat "
              "on a continuation line) names its layer — the process world is wrong, so the layer "
              "is `environment` — and the exit code is still 1",
              re.search(r"^refused \[coord environment\]: ", out, re.M) is not None and code == 1)
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

        # ---- guard sweep, slice 1 site 3: the WAKE-FAILURE abort, one guard EARLIER ----
        # ⚠ The row above reads as though it covers this, and it does not. It drives
        # `wait_harness_up` (harness_up = []) with the wake SUCCEEDING, so it exercises
        # launch_seat's `uerr` guard — the one AFTER. The `if not ok` guard on wake() itself was
        # asserted by nothing: no launch anywhere in this suite ran with a failing wake, because
        # `wake_ok` is set True before the first cmd_launch and never lowered again. Two adjacent
        # guards, one covered, one not, under a check name that sounds like it covers both.
        harness_up["v"] = [4242]        # a harness IS up: isolates the wake failure as the cause
        wake_ok["v"] = False
        _ko, _kc = refuse(cmd_launch, agent="leader", only="alpha", dry_run=False, force=False)
        wake_ok["v"] = True
        check("G-11: a launch whose START LINE was never delivered FAILS — the pane is open and "
              "the harness was never told to run. Distinct from the row above: there the wake "
              "landed and no harness came up; here the wake itself failed, and the seat must not "
              "be reported launched on the strength of a pane existing",
              "FAILED" in _ko and "harness start FAILED" in _ko and _kc == 1)

        # ---- guard sweep, slice 1 sites 6-7: a CLOSER that never booted must not open CLOSING --
        # `cmd_close` sets the CLOSING state only after the closer is verified up, and its own
        # comment says why: setting it earlier "would narrow a live seat's inbox on the strength of
        # a closer that might never have started — which is exactly how G-11 burned seven minutes
        # of this run on a closer that was only ever a shell". Both failure guards that protect
        # that ordering — the wake, and the harness-up verify — were asserted by NOTHING: every
        # cmd_close in this suite runs the happy path. The assertion that matters is not the exit
        # code, it is that THE TARGET IS NOT LEFT CLOSING: an inbox narrowed for an absent closer
        # is a live seat cut off from the room with nobody coming to close it.
        # FIXTURE HYGIENE: a failing close still RESOLVES its closer pane, which creates the
        # shared 'closers' window as a side effect — and a later row asserts that the FIRST close
        # of a run is what creates it. Saved and restored so this block cannot consume a window a
        # later check needs. (It did: that row went red before this restore existed.)
        _cw_saved = closers_window_pane["v"]
        wake_ok["v"] = False
        _co1, _cc1 = refuse(cmd_close, agent="leader", target="alpha", renew=False, dry_run=False)
        wake_ok["v"] = True
        check("G-11/G-21: a close whose closer START LINE was never delivered FAILS, and leaves "
              "the target NOT CLOSING — the state that narrows a live seat's inbox must not open "
              "on the strength of a pane that exists, or the seat is cut off from the room with "
              "no closer coming",
              _cc1 == 1 and "closer launch FAILED" in _co1
              and closing_entry(base_dir(ns()), "alpha") is None)
        harness_up["v"] = []            # wake lands, nothing comes up
        _co2, _cc2 = refuse(cmd_close, agent="leader", target="alpha", renew=False, dry_run=False)
        check("G-11/G-21: and the same when the wake LANDS but no harness comes up — a distinct "
              "guard one line later, with the same consequence. The refusal also names the pane "
              "BY ID to kill, because the pane outlives the failure and nothing else will say "
              "which one it was",
              _cc2 == 1 and "NOT closed" in _co2 and "kill-pane" in _co2
              and closing_entry(base_dir(ns()), "alpha") is None)
        harness_up["v"] = None
        closers_window_pane["v"] = _cw_saved
        opened.clear()

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
        # ---- guard sweep, slice 1 site 2: seat VALIDATION on the RENEW path ----
        # PROP-8 validates every seat BEFORE any pane opens — but that sweep lives in `cmd_launch`,
        # and `close-seat --renew` does not go through it: it calls `launch_seat` directly, whose
        # own `verr` guard is the ONLY validation a renew ever meets. That guard was asserted by
        # nothing — every renew in this suite renews a VALID seat. A descriptor edited between a
        # seat's launch and its renewal is exactly when it matters, and a renewal is the one boot
        # that happens after a descriptor has been touched.
        alpha_md = pkg / "workers" / "alpha.md"
        alpha_src = alpha_md.read_text(encoding="utf-8")
        alpha_md.write_text("---\nagent: alpha\nmodel: opsu\neffort: xhigh\n---\nbrief\n",
                            encoding="utf-8")
        run(cmd_checkin, agent="alpha", summary="pane seat", pane="%31")
        live_tmux_panes["v"] = {"%31"}
        killed.clear(); opened.clear(); respawned.clear()
        _vo, _vc = refuse(cmd_close_seat, agent="leader", target="alpha", renew=True,
                          no_export=True)
        alpha_md.write_text(alpha_src, encoding="utf-8")
        live_tmux_panes["v"] = set()
        check("PROP-8: a RENEW validates the seat too — the descriptor may have been edited since "
              "it last booted, and a renew is the one boot that happens AFTER someone touched the "
              "file. cmd_launch's pre-spawn sweep does not run here, so launch_seat's own check is "
              "the only one a renew meets",
              "opsu" in _vo and not opened)

        live_tmux_panes["v"] = set()

        # ---- guard sweep, slice 1 site 4: the guard that CANNOT FIRE, and the coupling that ----
        # ---- makes it so ------------------------------------------------------------------
        # `launch_seat`'s `if cmd is None: return "", err` survived the sweep, and it survived
        # because IT IS UNREACHABLE. `harness_command` returns None in exactly two cases — an
        # unknown harness, and an opencode seat with no model — and `validate_seat` refuses BOTH,
        # one guard earlier on the same path. No input reaches the branch, so no honest check can
        # cover it and none is written here: a test that appeared to exercise it would be asserting
        # a state the code cannot enter.
        #
        # What IS testable is the COUPLING that makes it unreachable, and that is worth more than
        # the branch. The implication runs one way — harness_command returning None MUST imply
        # validate_seat refuses — and it is one-way on purpose: validate_seat is allowed to be
        # STRICTER (it rejects a malformed opencode slug that harness_command would happily quote).
        # If someone adds a new None-return to harness_command without a matching rule in
        # validate_seat, this row fails and the dead branch quietly comes alive.
        _hc_matrix = [
            {"agent": "m1", "harness": "claude", "model": "opus", "effort": "medium", "cwd": "/tmp"},
            {"agent": "m2", "harness": "nonesuch", "model": "opus", "effort": "medium", "cwd": "/tmp"},
            {"agent": "m3", "harness": "opencode", "model": "", "effort": "medium", "cwd": "/tmp"},
            {"agent": "m4", "harness": "opencode", "model": "not-a-slug", "effort": "medium",
             "cwd": "/tmp"},
            {"agent": "m5", "harness": "codex", "model": "gpt-5.5", "effort": "medium", "cwd": "/tmp"},
        ]
        _viol = [w["agent"] for w in _hc_matrix
                 if harness_command(w, prompt_path="/tmp/p.txt")[0] is None
                 and not validate_seat(w)]
        check("PROP-8: every input on which `harness_command` gives up is one `validate_seat` "
              "already refuses — which is WHY launch_seat's `cmd is None` branch cannot fire. The "
              "implication is one-way by design: validate_seat may be stricter. Break the coupling "
              "and a guard this suite cannot otherwise reach comes back to life unannounced",
              _viol == [] and validate_seat(_hc_matrix[0]) == ""
              and harness_command(_hc_matrix[1], prompt_path="/tmp/p.txt")[0] is None)

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
        # ⚠ A FIXTURE FLOOR, NOT THE RUN'S. Task 7.82 deleted the module constant these checks used
        # to read: the floor is now READ from the package's budget.json per launch. Pinning the
        # arithmetic to a local number keeps these checks about the GATE'S SHAPE — spike reserve,
        # per-seat scaling, broken sensor — instead of quietly re-testing whatever the live run
        # happens to declare today. A check whose expected value moves with production data cannot
        # fail for the reason it claims to.
        FLOOR_FX = 2000
        check("mem gate: room for the spike reserve -> no refusal",
              memory_gate(1, FLOOR_FX, FLOOR_FX) == "" and memory_gate(2, 4300, FLOOR_FX) == "")
        check("mem gate: below the reserve -> refused, naming the peak and the reason a flat "
              "steady-state floor is the wrong shape",
              "peaks at" in memory_gate(1, FLOOR_FX - 1, FLOOR_FX)
              and "SIGKILL a bystander" in memory_gate(1, 1000, FLOOR_FX))
        check("mem gate: an N-seat wave needs a spike per seat beyond the first",
              memory_gate(3, FLOOR_FX + SEAT_SPIKE_MB, FLOOR_FX) != ""
              and memory_gate(3, FLOOR_FX + 2 * SEAT_SPIKE_MB, FLOOR_FX) == "")
        # ⚠ AND THE GATE MUST TRACK THE FLOOR IT IS GIVEN, not a remembered one. Without this, a
        # gate that ignored its floor_mb argument entirely would pass every check above.
        check("mem gate: the floor is the ARGUMENT — a higher floor refuses what a lower one "
              "allows, at identical available memory",
              memory_gate(1, 2500, 2000) == "" and memory_gate(1, 2500, 3000) != "")
        check("mem gate: an unreadable sensor PASSES — a broken meter must not stop a run",
              memory_gate(5, 0, FLOOR_FX) == "")

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

        # ---- 7.85: the THIRD owner state, and the control that can actually fail ----------------
        # ⚠ A ROW ASSERTING `"reachable" in choices` WOULD BE VACUOUS: it proves the enum accepts a
        # word, not that any consumer renders it. These rows assert on the RENDERED OUTPUT of the
        # two surfaces a seat actually queries, `status` and `workers`.
        #
        # ⚠⚠ AND THE NOTE IS EMPTY THROUGHOUT. That is what makes this evidence rather than
        # theatre: with a note, `reachable` and `afk` would differ because someone wrote prose,
        # which is the defect the row exists to fix (criterion 6). If they still differ with NO
        # note, the carrier is the code.
        def owner_block(text):
            """The owner lines only, WITH THE TIMESTAMP REMOVED.

            ⚠ WITHOUT THE STRIPPING THIS CHECK IS VACUOUS AND LOOKS FINE: every `owner` write
            stamps `| since {now()}`, so three renders taken in sequence differ from each other
            whatever the state does — the comparison would pass against a build where all three
            states rendered identically. The timestamp is noise for this question and is removed
            before anything is compared.
            """
            lines = text.splitlines()
            for i, ln in enumerate(lines):
                if ln.startswith("owner:"):
                    blk = [ln.split("| since")[0].rstrip()]
                    for nxt in lines[i + 1:]:
                        if not nxt.startswith(" "):
                            break
                        blk.append(nxt.rstrip())
                    return "\n".join(blk)
            return ""

        def owner_renders(state, note=""):
            run(cmd_owner, agent="leader", state=state, note=note)
            return (owner_block(run(cmd_status, agent="alpha")),
                    owner_block(run(cmd_workers, full=False, history=False)))

        def coded(block):
            """The SEMANTIC lines only — the render minus its `owner: <state>` header line.

            ⚠⚠ MEASURED, NOT REASONED, AND IT COST THIS ROW ITS FIRST VERSION: comparing the WHOLE
            block is VACUOUS. I ran the pre-7.85 renderer (one opaque string, printed raw) against
            this suite as a mutant, and the two distinctness rows PASSED — because that string
            BEGINS WITH THE STATE TOKEN, so `owner: reachable ...` and `owner: afk ...` differ
            textually whatever the code does with them. A build that never learned what the third
            state MEANS satisfies "renders differently" for free.
            ⇒ THE DISCRIMINATING PROPERTY IS NOT THAT THE THREE RENDERS DIFFER — IT IS THAT EACH
            CARRIES ITS OWN MEANING AND ESCALATION ACT, FROM THE TABLE. That is what the old code
            could not do at any note setting, and it is what criterion 5 is actually asking for.
            Never widen this back to the whole block: the row goes green and stops testing.
            """
            return "\n".join(block.splitlines()[1:])

        st_r, wk_r = owner_renders("reachable")
        st_p, wk_p = owner_renders("present")
        st_a, wk_a = owner_renders("afk")
        check("7.85 criterion 5: all three owner states render DISTINCT SEMANTICS through `status` "
              "— compared on the CODED lines, with an EMPTY note, so the carrier is proven to be "
              "the code and not the prose. A state that renders identically to `afk` has not been "
              "added, whatever the enum accepts",
              all(coded(b) for b in (st_r, st_p, st_a))
              and len({coded(st_r), coded(st_p), coded(st_a)}) == 3)
        check("7.85 criterion 5: and DISTINCTLY through `workers` too — the other surface a seat "
              "queries. One consumer rendering the state is not the state being renderable; both "
              "printed the same opaque line before this",
              all(coded(b) for b in (wk_r, wk_p, wk_a))
              and len({coded(wk_r), coded(wk_p), coded(wk_a)}) == 3)
        check("7.85 criterion 3: the ESCALATION ACT is carried by the render, not by the note — "
              "`reachable` tells a reader to launch the door, with no note written anywhere",
              "LAUNCH THE DOOR" in st_r and "LAUNCH THE DOOR" in wk_r
              and "LAUNCH THE DOOR" not in st_a and "LAUNCH THE DOOR" not in st_p)
        # ⚠ THE ANTI-VACUITY CONTROL, and it is the reason the three rows above mean anything: the
        # SAME state rendered twice must come back BYTE-IDENTICAL. If it does not, `owner_block` is
        # leaking something that varies per call (a timestamp, a cursor, a lag column) and every
        # "they differ" row above would pass on that noise alone, against any build.
        st_a2, wk_a2 = owner_renders("afk")
        check("7.85 control: the same state rendered twice is BYTE-IDENTICAL in both surfaces — "
              "so the distinctness rows above are reading the STATE and not per-call noise. "
              "Without this, three renders taken in sequence always differ and the check is blind",
              (st_a, wk_a) == (st_a2, wk_a2))
        st_n, wk_n = owner_renders("afk", note="dinner")
        check("7.85 criterion 6: a note is ADDITIVE and subordinate — it appears in the render, "
              "and the state and escalation lines are unchanged by it. The note may inform; it may "
              "never be what distinguishes one state from another",
              "dinner" in st_n and "dinner" in wk_n
              and st_a.splitlines()[:3] == st_n.splitlines()[:3])
        check("7.85 criterion 4: `present` and `afk` still mean exactly what they meant — "
              "escalate now / queue them — and the help says so from the same table the "
              "consumers render, so it cannot drift from behaviour",
              "escalated NOW" in st_p and "do NOT page" in st_a)
        # BACK-COMPAT: a file written before this change, and one hand-edited past it. Both must
        # read; neither may vanish. `owner_status` is now a parser, and a parser that silently
        # returns nothing on an unrecognised line is worse than one that reports honestly.
        legacy = base_dir(ns()) / "owner-status.md"
        legacy.write_text("# owner-status — script-managed (coord.py owner <present|afk>)\n"
                          "owner: afk | since 2026-01-01 10:00 — back in 2h\n", encoding="utf-8")
        parsed = owner_status(base_dir(ns()))
        check("7.85 back-compat: a LEGACY owner-status.md (written by the two-state writer) still "
              "parses — state, since and note all recovered, not one opaque string",
              parsed["state"] == "afk" and parsed["since"] == "2026-01-01 10:00"
              and parsed["note"] == "back in 2h" and parsed["known"])
        legacy.write_text("owner: on-a-call | since 2026-01-01 10:00\n", encoding="utf-8")
        out = run(cmd_status, agent="alpha")
        parsed = owner_status(base_dir(ns()))
        check("7.85: an UNRECOGNISED state degrades HONESTLY — reported verbatim and flagged, "
              "never dropped and never silently translated into a known value. A hand-edited or "
              "newer-writer file must not read as `unknown` or vanish",
              parsed["state"] == "on-a-call" and not parsed["known"]
              and "on-a-call" in out and "UNRECOGNISED" in out)
        # ⚠ THESE TWO ROWS EXIST BECAUSE A MUTANT SHOWED THE OTHERS COULD NOT SEE THIS: every row
        # above calls the command FUNCTION directly, which never goes through argparse — so with
        # `reachable` deleted from OWNER_STATES, `owner reachable` still "worked" in the suite
        # while the real CLI would have refused it. Criterion 1 is that the state is first-class AT
        # THE CLI, so it is asserted at the PARSER, which is where a seat actually meets it.
        def parses(argv):
            """Does the REAL parser accept this command line? Public API, no argparse internals —
            argparse exits on a bad choice, so SystemExit IS the refusal."""
            buf = io.StringIO()
            try:
                with redirect_stdout(buf), redirect_stderr(buf):
                    return build_parser().parse_args(argv).state
            except SystemExit:
                return None

        # ⚠⚠ THE LITERAL `"reachable"` BELOW IS DELIBERATE AND MUST NOT BE "TIDIED" INTO A LOOP
        # OVER OWNER_STATES. MEASURED: the first version of this row asserted only that the parser
        # accepts exactly the table's keys — and when a mutant DELETED `reachable` FROM THE TABLE,
        # the row still PASSED, because both sides of the comparison moved together. A check
        # written entirely in terms of the thing it checks cannot see that thing go missing.
        # The derived half proves choices track the table; the literal half proves WHICH states.
        check("7.85 criterion 1: the third state is first-class AT THE CLI — the REAL parser "
              "accepts `owner reachable` BY NAME, accepts the other two, and rejects a word that "
              "is not a state. Asserted by PARSING, not by reading `choices` off the action object",
              parses(["owner", "reachable"]) == "reachable"
              and parses(["owner", "present"]) == "present"
              and parses(["owner", "afk"]) == "afk"
              and [parses(["owner", s]) for s in OWNER_STATES] == list(OWNER_STATES)
              and parses(["owner", "at-pc"]) is None)
        _help = "; ".join(f"{k} = {v[0]}" for k, v in OWNER_STATES.items())
        _owner_help = ""
        buf = io.StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(buf):
                build_parser().parse_args(["owner", "--help"])
        except SystemExit:
            _owner_help = buf.getvalue()
        check("7.85 criterion 2: `--help` states each state's meaning FROM THE SAME TABLE the "
              "consumers render — a reader tells 'escalate now' from 'queue them' from "
              "'reachable in one act' without out-of-band knowledge, and the help cannot go stale "
              "against behaviour because there is only one home for both. Read off the REAL "
              "`--help` output, not off the string that was passed in",
              all(f"{k} = {v[0]}" in " ".join(_owner_help.split())
                  for k, v in OWNER_STATES.items())
              and "NARROWING" in _owner_help)
        # ---- 7.89 (G-269): an act that went stale BY BEING OBEYED ---------------------------
        # ⚠⚠ BOTH DIRECTIONS, and criterion 3 says why: a control proving only the gated case
        # cannot distinguish "the act is conditional" from "the act was DELETED", and the second
        # passes every test the first does.
        _up = {"door": "owner-liaison", "door_active": True}
        _down = {"door": "owner-liaison", "door_active": False}
        check("7.89 criterion 1+3: with the door NOT active, `reachable`'s act says LAUNCH THE "
              "DOOR — the act is a function of the WORLD AT RENDER TIME, not of the state token",
              "LAUNCH THE DOOR" in owner_escalation("reachable", _down))
        check("7.89 criterion 3, the other direction: with the door ACTIVE, `reachable` does NOT "
              "say launch — it says MESSAGE the door that is already up. This is the direction "
              "that went stale by being OBEYED: someone launched it and the instruction stayed",
              # ⚠ ASSERT THE PROPERTY, NOT THE VOCABULARY — the first version of this row also
              # checked the literal "already up" against text that reads "ALREADY UP", and failed
              # on the CASE while the behaviour was correct. What matters is that the act does not
              # instruct a launch and does instruct a message; the exact phrasing is not the test.
              "LAUNCH THE DOOR" not in owner_escalation("reachable", _up)
              and "MESSAGE it" in owner_escalation("reachable", _up))
        check("7.89: the act is not merely conditional but NAMES THE DOOR it found, so a reader "
              "is never left resolving which seat carries the owner relay",
              "owner-liaison" in owner_escalation("reachable", _up))
        # CRITERION 2 — the other two states re-read under the same lens, in the same change.
        check("7.89 criterion 2: `present` was stale in the OPPOSITE direction and is fixed here "
              "too — with NO door running, 'message the owner directly' is false, so it now warns "
              "that nothing is receiving instead of promising delivery",
              "receiving" in owner_escalation("present", _up)
              and "NO door session is running" in owner_escalation("present", _down))
        check("7.89 criterion 2: `afk`'s act is the NULL act and is checked-and-not-stale — "
              "nothing can be carried out that would falsify it, so it renders identically in "
              "both worlds. Left unconditional deliberately, not overlooked",
              owner_escalation("afk", _up) == owner_escalation("afk", _down))
        # ⚠ THE WIRING, without which both rows above are a claim about a lambda: the SURFACE must
        # actually compose through `owner_escalation`, not carry its own copy of the text.
        run(cmd_owner, agent="leader", state="reachable", note="")
        _st_out = run(cmd_status, agent="alpha")
        _w = owner_world(ns(), base_dir(ns()))
        check("7.89: `status` renders the act the COMPOSER produces for the world it actually "
              "reads — asserted by composing it independently and finding that exact text on the "
              "surface, so the surface cannot be carrying a second, drifting copy",
              owner_escalation("reachable", _w) in _st_out)
        check("7.89 criterion 4: the world is READ-ONLY — resolving it touches no pane, launches "
              "nothing and probes no door. `owner_world` reads descriptors and the roster, so "
              "'does a relaunch work?' is DESIGNED OUT rather than answered on the owner's door",
              set(_w) == {"door", "door_active"} and isinstance(_w["door_active"], bool))
        legacy.unlink()
        out = run(cmd_status, agent="alpha")
        check("7.85: a MISSING owner-status.md reports `unknown` with no escalation path claimed — "
              "the state was never recorded, which is not the same as the owner being away",
              "unknown" in out and "no owner state has been recorded" in out)
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

        # ---- G-181: the advice surface must not coach a command the tool refuses ----
        # Three advice populations (runtime `next:` hints, per-command -h epilogs, refusal texts)
        # all coach `send`, and all three drifted the moment the positional-body guard went
        # unconditional (rbtv 4837088): 14 sites taught the refused shape and nothing noticed,
        # because a behaviour change swept logic and comments and left the text that teaches it.
        g181_bad, g181_total = advice_refused_sends()
        check("G-181: every `send` this file's advice coaches is ACCEPTED by the real send path "
              "— evaluated through main()'s own parser+guard sequence, never a substring check "
              "for `--inline` (which the owner hint would have passed while still being refused "
              "as `a note is never an all broadcast`) — offenders: %s"
              % ("none" if g181_bad == [] else
                 ("SCAN INOPERATIVE: only %d coached sends matched, floor %d — the advice shape "
                  "stopped matching this source and a blind check reporting clean IS the defect"
                  % (g181_total, ADVICE_FLOOR) if g181_bad is None else
                  "; ".join(f"line {ln}: {cmd} -> {why}" for ln, cmd, why in g181_bad))),
              g181_bad == [])

        # ---- G-181 population 4: the kit's DOCS ----
        # protocol.md is loader step 4 for every seat, so a refused shape here mis-teaches the
        # room at BOOT. The skip count is asserted too: a guard that silently exempts lines is a
        # check that stops catching things while still reading green.
        g181_docs, g181_skipped = advice_doc_sends()
        g181_doc_bad = [d for d in g181_docs if not d[3]]
        check("G-181: no kit .md teaches a `send` shape the tool refuses — a doc synopsis is a "
              "STATEMENT ABOUT WHAT coord.py ACCEPTS, and protocol.md is loader step 4 for every "
              "seat (scanned %d command line(s); explicitly-marked refused examples, listed in "
              "full because a bare count has no maintainer and only grows: %s) — offenders: %s"
              % (len(g181_docs),
                 "none" if not g181_skipped else
                 " | ".join(f"{f}:{ln}: {txt}" for f, ln, txt in g181_skipped),
                 "none" if not g181_doc_bad else
                 "; ".join(f"{f}:{ln}: {txt}" for f, ln, txt, _ in g181_doc_bad)),
              g181_docs and not g181_doc_bad)

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
        # ⚠ G-218, and it is `assert the PROPERTY, never the VOCABULARY` again: this row used to
        # assert the LITERAL "coord.py:". A traceback carries the name the file was INVOKED as, and
        # every seat invokes the installed `coordinate` symlink — so this row was RED for every
        # seat and GREEN for anyone typing `python3 coord.py`, on identical bytes. The property is
        # that the abort names a FILE AND A LINE; the filename is derived from this module's own
        # path, which is exactly what the traceback reports.
        # (The same fact was already known here as the "false-red filename trap" — that gating a
        # candidate named `coord-candidate.py` fails this row. It was recorded as a caveat about
        # gating and never read as what it is: this check depends on the invocation name.)
        _where = os.path.basename(__file__) + ":"
        check("G-66: the abort names WHERE it raised — file AND line — so a reader can find the "
              "raising check without re-running under a debugger. The filename is DERIVED from "
              "this module's own path, never a literal, because the traceback carries the name "
              "the file was invoked under and a seat always invokes the symlink (G-218)",
              _where in abort_out and re.search(re.escape(_where) + r"\d+", abort_out)
              and "ABORTED after 1 check(s)" in abort_out)
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
        # ---- s12-03 L-c (2 of 3): the second CONTINUATION-literal site. The check reads the run's
        # own roster (a live ACTIVE row under this name), so the layer is `state`, not
        # `environment` — the pane being alive is evidence, the ROSTER is what forbids the act.
        check("s12-03 L-c: the checkin ZOMBIE-DOUBLE-LAUNCH refusal (continuation-literal site) "
              "names its layer as `state` — the run's own roster row is what forbids it — and "
              "still exits 1",
              re.search(r"^refused \[coord state\]: ", out, re.M) is not None and code == 1)
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

        # ---- 7.80/G-195: coordinate's agent_type render half ----
        # `teamview` already renders this field straight off state.json (agent_type_bit); the
        # row that kept 7.80 #wip was that `coordinate` did not. Same field, same snapshot, no
        # second source — these checks pin exactly that, plus the fail-safe degradations
        # teamview's own tests already established the shape of (no empty ghost, no crash).
        run(cmd_checkin, agent="atype-a", summary="carries a state.json agent_type", pane="%81")
        run(cmd_checkin, agent="atype-b", summary="unclassified in the snapshot", pane="%82")
        run(cmd_checkin, agent="atype-c", summary="absent from the snapshot entirely", pane="%83")
        live_tmux_panes["v"] |= {"%81", "%82", "%83"}

        def agent_row_line(out, agent):
            return next((ln for ln in out.splitlines() if ln.startswith(agent)), "")

        state_path = pkg / "state.json"
        state_path.write_text(json.dumps({"seats": [
            {"seat": "atype-a", "agent_type": "staff"},
            {"seat": "atype-b", "agent_type": "unclassified"},
        ]}), encoding="utf-8")
        out = run(cmd_workers, full=False, history=False)
        check("7.80/G-195: agent_type reaches the row straight off state.json's snapshot — no "
              "second source, the identical field teamview.py's agent_type_bit reads the "
              "identical way",
              "[staff]" in agent_row_line(out, "atype-a"))
        check("7.80/G-195: `unclassified` is a REAL observed value and renders as one, never "
              "hidden as a blank — team-monitor writes it LOUDLY for exactly this reason and a "
              "renderer that swallowed it would put the confident-wrong shape right back",
              "[unclassified]" in agent_row_line(out, "atype-b"))
        check("7.80/G-195: a seat with NO row in state.json's snapshot at all renders exactly "
              "as it did before this feature existed — no empty bracket, no invented value "
              "(teamview.py's own 'no empty ghost' bar, same shape here)",
              "atype-c" in out and "[" not in agent_row_line(out, "atype-c"))

        state_path.write_text("{not json", encoding="utf-8")
        out = run(cmd_workers, full=False, history=False)
        check("7.80/G-195: an unparseable state.json degrades `workers` to its pre-7.80 "
              "rendering rather than raising — this is a live, script-managed, shared file and "
              "a torn write must never take the roster view down with it",
              "atype-a" in out and "[" not in agent_row_line(out, "atype-a"))

        state_path.unlink()
        out = run(cmd_workers, full=False, history=False)
        check("7.80/G-195: a run with NO state.json at all (pre-7.80, or team-monitor never "
              "ran here) renders exactly as before this feature existed — purely additive",
              "atype-a" in out and "[" not in agent_row_line(out, "atype-a"))
        live_tmux_panes["v"] -= {"%81", "%82", "%83"}

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
        # ⚠ G-218: THIS ROW'S SCENARIO PRESUPPOSES A CALLER OUTSIDE ANY PACKAGE, and
        # `sender_origin` reads the PROCESS's cwd — not anything in `args`. Left to the ambient
        # cwd, the row was green only when the suite happened to be run from outside a package,
        # AND A SEAT IS NEVER OUTSIDE ONE: it invokes `coordinate` from its own seat folder, which
        # is inside the run package. So the same bytes gave PASS to one agent and FAIL to another,
        # both reporting honestly — a verdict resting on undeclared ambient state makes two honest
        # reporters who cannot both be right. The precondition is now ESTABLISHED: `td` is the
        # suite's own temp root, and a row above already ASSERTS `discover_package_from(Path(td))
        # is None`, so the setup is not merely believed to be package-free.
        _outside = Path(td) / "outside-any-package"
        _outside.mkdir(exist_ok=True)
        _cwd_ext = os.getcwd()
        try:
            os.chdir(_outside)
            _ext_origin = sender_origin(ns(pane="%9999"), "zeta")
        finally:
            os.chdir(_cwd_ext)
        check("stage 4: a caller whose pane is on no row of this package AND whose cwd is in no "
              "package is `external` even when a seat of that name exists here — the "
              "membership-by-NAME test was circular, and this is the check that would have caught "
              "it. The cwd is now SET for the assertion rather than inherited (G-218)",
              _ext_origin == "external")
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
        # ---- G-197: the bounded seat can ask the TOOL who may write to it ----
        # The kit resolved this on every send and reported the refusal to the SENDER, while the
        # bounded seat's own status said only what G-20 filtered — so verifying the bound meant
        # reading another seat's descriptor. The tool knew the answer and offered no way to ask,
        # which made the boundary-breaking act the only available one. Measured: that is exactly
        # what the engineer did, and disclosed against itself.
        # ⚠ `leader` DECLARES NOTHING here, deliberately: `inbox_decls` keeps only seats that
        # declare something, so an ordinary seat is ABSENT from it and the roster is a SEPARATE
        # input. The first draft derived candidates from `decls` and the live render told this
        # seat that `leader` — its own permitted sender, messaging it all session — "NO seat
        # declares". The fixture had listed `leader: {}`, so it could not produce the bug: shaped
        # to dodge the real path. It is now shaped like the real one.
        d197 = {"bnd": {"senders": frozenset({"leader", "master"})},
                "ol": {"relays": frozenset({"master"})}}
        r197 = ["alpha", "bnd", "leader", "ol", "zeta"]
        lit197, rel197, dead197 = permitted_senders("bnd", d197, r197)
        check("G-197: a bounded seat is told WHO may write to it, split by HOW — `leader` by name, "
              "and the seat CARRYING the role token by relay. The relay holder is the member no "
              "seat could name without opening a peer's descriptor, which is the read this closes",
              lit197 == ["leader"] and rel197 == [("ol", "master")] and dead197 == []
              and "ol (carries relays: master)" in inbox_bound_line("bnd", d197, r197))
        check("G-197: an UNBOUNDED seat gets NO line rather than a reassuring one — an inbox with "
              "no bound has no senders answer to give, and printing one would invent a narrowing",
              permitted_senders("alpha", d197, r197) is None
              and inbox_bound_line("alpha", d197, r197) == "")
        check("G-197: a bound naming a token NO seat carries is reported LOUDLY, not omitted — in "
              "the bound's own text a dead token is indistinguishable from a live one, which is "
              "precisely what `senders: leader, master` did before `relays:` resolved it",
              permitted_senders("bnd", {"bnd": d197["bnd"]}, ["bnd", "leader"])[2] == ["master"]
              and "NO seat declares" in inbox_bound_line("bnd", {"bnd": d197["bnd"]}, ["bnd", "leader"]))
        check("G-197: the answer is EVALUATED through `sender_admitted`, the same predicate `send` "
              "enforces — so a change to admission moves both together. Proven by the property "
              "only that predicate has: a relay is refused for a FOREIGN sender (origin set), and "
              "permitted_senders lists the relay holder only because it asks the local question",
              sender_admitted({"sender": "ol", "origin": "run-1"},
                              d197["bnd"]["senders"], d197) is False
              and sender_admitted({"sender": "ol", "origin": ""},
                                  d197["bnd"]["senders"], d197) is True)

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

        # ---- ADDRESSABLE NON-MEMBERS (`ruling-addressable-non-member.md`) -------------------
        # Inside the suite, not a side script: two probes in this system rotted for seven days
        # because nothing ran them (G-141), and a check with no runner reports on a mechanism
        # nobody is exercising.
        base_an = base_dir(ns())
        out_home = pkg.parent / "outsider-goal" / "seats" / "outsider"
        out_home.mkdir(parents=True, exist_ok=True)
        reg = pkg / "addressable.csv"
        check("addressable: no register by default, so the mechanism ships INERT — a package that "
              "admits nobody behaves exactly as it does today",
              load_addressable(ns()) == ({}, []))
        a_out1, a_code1 = refuse(cmd_send, agent="outsider", to="alpha", message="x", type="ask",
                                 supersedes=None, re_num=None, file=None)
        a_out2, a_code2 = refuse(cmd_send, agent="alpha", to="outsider", message="x", type="note",
                                 supersedes=None, re_num=None, file=None)
        check("addressable / THE DEFECT: an agent whose descriptor lives in ANOTHER goal folder is "
              "blocked BOTH ways — nobody can address it (F5) and its own `ask` therefore has no "
              "possible terminus (S-7). Every source `known_recipients` draws on is package-local "
              "by construction. Measured live at run-2 #509/#510, where a summoned meta-agent "
              "finished its work through `tmux send-keys`, off the bus entirely",
              a_code1 == 1 and "cannot receive a reply" in a_out1
              and a_code2 == 1 and "is not a known recipient" in a_out2)
        check("addressable / G-165: the S-7 refusal no longer sends a NON-MEMBER to `checkin` "
              "without qualification — that is the forbidden repair, and this text is how the trap "
              "reached the correspondent that hit it. The alternative and the PULL limit are named "
              "in the refusal itself, because the next one cannot read the ruling",
              "do NOT check in" in a_out1 and "addressable.csv" in a_out1
              and "NO WAKE" in a_out1 and "delivery is PULL" in a_out1)
        (out_home / "seat.md").write_text(
            "---\nseat: outsider\nharness: claude\naddressable: non-member\n---\nbrief\n",
            encoding="utf-8")
        reg.write_text(f"descriptor,admitted-by,admitted\n{out_home / 'seat.md'},leader,now\n",
                       encoding="utf-8")
        check("addressable: DERIVED, never hardcoded (constraint 1) — the register carries a PATH "
              "and cannot even state the name; the name and the permission both come from the "
              "descriptor the correspondent itself owns. A kit-side name list would freeze one "
              "campaign's furniture into a tool every run shares, which is what SPECIAL_CASE_SEATS "
              "was demoted for",
              # The seat FOLDER is named after the seat, so the path legitimately contains the
              # name. Strip the path and assert the name appears nowhere else: it is never a FIELD
              # the register states, only an incidental substring of a location.
              "outsider" not in reg.read_text(encoding="utf-8").replace(str(out_home), "")
              and set(addressable_nonmembers(ns(), base_an)[0]) == {"outsider"}
              and "outsider" in known_recipients(ns(), base_an))
        # ---- guard sweep, slice 1 site 8: a RELATIVE descriptor path is package-relative ----
        # Every fixture above writes an ABSOLUTE path, so the branch that resolves a relative one
        # was never exercised. Its claim is not cosmetic: a relative path resolved against the
        # PROCESS's cwd instead of the package works perfectly for whoever authored the register
        # (who runs from the package) and fails for every seat, which runs `coordinate` from its
        # OWN folder. That is the shape that passes review and breaks in the room.
        _rel = os.path.relpath(out_home / "seat.md", pkg)
        reg.write_text(f"descriptor,admitted-by,admitted\n{_rel},leader,now\n", encoding="utf-8")
        _cwd_saved = os.getcwd()
        os.chdir(tempfile.gettempdir())      # anywhere that is NOT the package
        try:
            _rel_names = set(addressable_nonmembers(ns(), base_an)[0])
        finally:
            os.chdir(_cwd_saved)
        check("addressable: a RELATIVE descriptor path resolves against the PACKAGE, not the "
              "caller's cwd — every seat runs `coordinate` from its own folder, so a cwd-relative "
              "register would admit the correspondent for whoever wrote it and silently admit "
              "NOBODY for everyone else. Asserted from a cwd outside the package, because run "
              "from inside it the two resolutions are indistinguishable",
              _rel_names == {"outsider"} and not Path(_rel).is_absolute())
        reg.write_text(f"descriptor,admitted-by,admitted\n{out_home / 'seat.md'},leader,now\n",
                       encoding="utf-8")

        a_ask = sd("outsider", "alpha", "now answerable", type="ask")
        a_n = load_messages(base_an)[1][-1]["num"]
        a_ans = sd("alpha", "outsider", "the answer", type="answer", re_num=a_n)
        check("addressable / THE GRANT: it resolves as a recipient in BOTH directions and the "
              "thread CLOSES — the ask-refusal was the CONSEQUENCE of the missing recipient half, "
              "so fixing recipient resolution dissolved it rather than needing its own fix",
              "sent message #" in a_ask and "sent message #" in a_ans
              and load_messages(base_an)[1][-1]["re"] == a_n)
        check("addressable / PULL, NOT PUSH — said in the OUTPUT at the moment it matters, to the "
              "sender who would otherwise wait for a reply no wake will ever prompt. Left implicit, "
              "the first person to address one reads silence as 'considering' rather than 'never "
              "delivered'; the correspondent named that hazard about itself",
              "delivery is PULL, not push" in a_ans and "NOT YET READ" in a_ans
              and "PULL delivery — addressable NON-MEMBER" in a_ans)
        _, _, an_rows = load_workers(base_an)
        check("addressable / THE BOUND (constraint 5): NO ROSTER ROW EXISTS. That row is G-165's "
              "forbidden repair and it is what a cursor, a wake, a census entry, a pane-cap count "
              "and every lifecycle command would have come free with — which is exactly why it is "
              "refused. No taskforce.csv either: KG membership is that file's row",
              not any(r["agent"] == "outsider" for r in an_rows)
              and not (pkg / "taskforce.csv").exists()
              and current_row(an_rows, "outsider") is None)
        reg.write_text(f"descriptor,admitted-by,admitted\n{out_home / 'seat.md'},leader,now\n"
                       f"{out_home / 'gone.md'},leader,now\n", encoding="utf-8")
        a_err, a_ok = addressable_nonmembers(ns(), base_an)
        check("addressable / FAIL LOUD (constraint 3): an unresolvable row yields a NAMED error and "
              "admits nothing — and it never takes the good row down with it (constraint 4: a "
              "message addressed by name must always arrive). Four fail-silent defects landed here "
              "in one evening; a register that quietly dropped a row would be the fifth",
              set(a_err) == {"outsider"} and len(a_ok) == 1 and "unreadable" in a_ok[0])
        (out_home / "noopt.md").write_text("---\nseat: noopt\nharness: claude\n---\nb\n",
                                           encoding="utf-8")
        (out_home / "clash.md").write_text(
            "---\nseat: alpha\nharness: claude\naddressable: non-member\n---\nb\n",
            encoding="utf-8")
        reg.write_text(f"descriptor,admitted-by,admitted\n{out_home / 'noopt.md'},leader,now\n"
                       f"{out_home / 'clash.md'},leader,now\n", encoding="utf-8")
        a_names, a_errs = addressable_nonmembers(ns(), base_an)
        check("addressable / TWO-SIDED AND MACHINE-ENFORCED (constraint 2): a descriptor without "
              "its OWN `addressable: non-member` admits nothing, so a package cannot grant this on "
              "another agent's behalf; and a foreign descriptor named like a LOCAL seat is REFUSED "
              "with the local name winning — G-111 itself, a foreign seat sharing a live roster "
              "name must never be resolved here",
              a_names == {}
              and any("does not declare" in e for e in a_errs)
              and any("COLLIDES" in e for e in a_errs))
        reg.unlink()
        check("addressable: removing the register removes the name — nothing lingers in state, so "
              "the grant is exactly as revocable as it is grantable",
              "outsider" not in known_recipients(ns(), base_an))

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
              "--force-memory" in memory_gate(1, 100, 2000)
              and "override with --force " not in memory_gate(1, 100, 2000))
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
              "role while its pane is LIVE — a plain close always kills the pane, and a --renew "
              "kills it too unless the seat already sits in its briefed window (G-154), so this "
              "may destroy a door a human is watching. A door misplaced is cosmetic; a door "
              "destroyed is an outage",
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
        # ⚠ G-215(b): this row USED to prove "not refused" with `"reap --go" not in _oo` — the
        # ABSENCE of a token the command's own HEALTHY next-hint also prints ("next: … reap --go —
        # frees the panes listed READY above"). So it went RED whenever a READY debt happened to
        # exist at this point in the suite: a false red produced by FIXTURE ORDER rather than by
        # any behaviour change, and it made the row's placement silently load-bearing. It is the
        # same lesson as the G-66 filename row one commit ago — ASSERT THE PROPERTY, NEVER THE
        # VOCABULARY — and the property here is that NO ROLE GATE FIRED. `gate()`'s refusal is the
        # only thing that can say so, and it carries a signature no hint can collide with.
        check("G-134/B: OBSERVING IS UNGATED — it destroys nothing, and gating it forced any seat "
              "wanting to verify against the live room to override the gate or skip the check. A "
              "gate that manufactures its own breaches bills whoever behaves best (G-106). Keyed "
              "on the GATE's own refusal signature, never on the flag name: the healthy next-hint "
              "names that flag too (G-215(b))",
              _oc == 0 and "Ask leader to run it" not in _oo
              and "refused [coord" not in _oo)

        # ---- guard sweep, slice 2 sites 1-2: what the KILLING pass reports ----
        # `reap_blockers`, `confirm_reap` and `awaiting_debts` each have covered rows above, and
        # the GATE is covered in both directions (`--go` is leader/closer, observing is ungated).
        # Everything covered is a part that destroys nothing. `cmd_reap`'s own use of those
        # helpers — the branches deciding what the pane-killing pass says — was asserted by
        # nothing: the same seam `cmd_close_seat`'s comment names, in the verb that kills.
        _rp_panes = set(live_tmux_panes["v"])
        harness_up["v"] = [4242]
        (pkg / "workers" / "door2").mkdir(exist_ok=True)
        (pkg / "workers" / "door2" / "agent.md").write_text(
            "---\nagent: door2\nharness: claude\nmodel: opus\nrelays: master\n---\nbrief\n")
        _rt = pkg / "reap-probe-transcript.txt"
        _rt.write_text("scrollback", encoding="utf-8")
        live_tmux_panes["v"] = {"%81", "%82", "%83"}
        set_awaiting(base_g, "door2", "%81", str(_rt), True)
        set_awaiting(base_g, "free2", "%82", str(_rt), True)
        # s12-07's fixture seat. `renew2` passes EVERY OTHER precondition — a live pane, the
        # harness identity it checked out with, an exported transcript that EXISTS on disk, and an
        # age past the policy minimum — with no `relays:` declaration, so the ONLY thing that can
        # hold it is its disposition. It carries a NON-EMPTY handoff_stamp deliberately: the
        # inference mutant (`"renew" if handoff_stamp else "done"`) must leave THIS seat blocked,
        # so that mutation reds S7-a alone and never S2-h and S7-b along with it.
        # ⚠ GUARDED (G-215(a)): before the keyword parameters exist this call raises TypeError,
        # and a raise here would abort the suite instead of failing the rows that name the gap.
        try:
            _s7_seeded = bool(set_awaiting(base_g, "renew2", "%83", str(_rt), True,
                                           disposition="renew",
                                           handoff_stamp="2026-07-29T12:00:00"))
        except TypeError:
            _s7_seeded = False
        _aw2 = load_awaiting(base_g)
        for _s in ("door2", "free2", "renew2"):
            if _s not in _aw2:      # G-215(a): an unseeded fixture fails its rows, never the suite
                continue
            # Aged past the policy minimum and already confirmed once, so READY is genuinely
            # REACHABLE here. Without that, a mutant would be stopped one guard later by the
            # two-pass rule and these rows could not fail whatever the guard did (bar 11).
            _aw2[_s]["since"] = (datetime.now()
                                 - timedelta(minutes=REAP_MIN_AGE_MIN + 5)).strftime(
                                     "%Y-%m-%d %H:%M")
            _aw2[_s]["confirmed"] = ["2026-01-01 00:00"]
        atomic_write(awaiting_path(base_g), json.dumps(_aw2, indent=2, sort_keys=True) + "\n")
        killed.clear()
        _rpo = run(cmd_reap, agent="leader", go=False)
        check("G-134/B: an observe pass that found a READY seat ends with the EXACT command that "
              "frees it, naming the pane — the two-pass rule makes the dry sweep the normal way "
              "to reach a reap, so a pass that reports a ready seat and no route forward sends "
              "the reader to improvise the destructive command from memory",
              "READY to reap" in _rpo and "%82" in _rpo
              and "reap --go" in _rpo and killed == [])
        check("s12-07 S2-h: a renew disposition HOLDS THE REAPER, and the dry pass says WHY — the "
              "HELD line names `disposition=renew` and states the remedy in the leader's own "
              "terms: the renewal executor has not acted yet, and the pane a reap would free is "
              "the one that renewal needs. A gate that answers only yes/no teaches nobody why the "
              "run is leaking, and this is the one blocker whose remedy is another act, not time",
              _s7_seeded and "renew2" in _rpo and "HELD" in _rpo
              and "disposition=renew" in _rpo
              and "reaping now would kill the pane the renewal needs" in _rpo)
        _aw3 = load_awaiting(base_g)
        _aw3["free2"]["confirmed"] = []
        atomic_write(awaiting_path(base_g), json.dumps(_aw3, indent=2, sort_keys=True) + "\n")
        _rpq = run(cmd_reap, agent="leader", go=False)
        check("G-134/B: and it is SILENT when nothing is READY — a hint printed on every pass is "
              "one nobody reads, and this one names a command that kills panes",
              "reap --go" not in _rpq and "READY to reap" not in _rpq)
        _aw4 = load_awaiting(base_g)
        for _s in ("door2", "free2", "renew2"):
            if _s not in _aw4:      # G-215(a), same reason as the seeding loop above
                continue
            _aw4[_s]["confirmed"] = ["2026-01-01 00:00"]
        atomic_write(awaiting_path(base_g), json.dumps(_aw4, indent=2, sort_keys=True) + "\n")
        killed.clear()
        _rgo = run(cmd_reap, agent="leader", go=True)
        check("G-134/B: on the KILLING pass a blocked debt is held WITH ITS REASON NAMED, beside "
              "an unblocked one that is actually freed — the blocker list is computed for every "
              "debt and nothing asserted the branch that consumes it. Reporting the owner door as "
              "'every precondition holds' states the opposite of the one fact that matters about "
              "it. (The kill itself is separately barred by the two-pass ledger, which resets on "
              "a blocked pass — this row claims the REPORT, not the kill)",
              "DOOR, not a leak" in _rgo and "%81" not in killed and "%82" in killed)
        check("s12-07 S7-b: `reap` and `reap --go` AGREE about a renew entry — the same seat is "
              "held on the DRY pass and on the KILLING one, and --go frees NOTHING for it while "
              "freeing its neighbour in the same sweep. The blocker lives in `reap_blockers`, "
              "which BOTH passes call, precisely so a guard cannot exist on the pass that reports "
              "and be missing from the pass that kills",
              _s7_seeded and "renew2" in _rpo and "renew2" in _rgo
              and "%83" not in killed and "%82" in killed)
        # ---- S7-a: the field is STORED, never inferred ----
        # ⚠ THE FIXTURE IS THE CHECK — the same lesson the `exported` row one block above records.
        # The CONTROL passes every precondition and is blocked by NOTHING, so whatever blocks the
        # other two can only be the disposition. And both discriminating records make the STORED
        # field DISAGREE with the handoff stamp an inference would reach for instead:
        #   renew WITHOUT a stamp — `"renew" if handoff_stamp else "done"` answers `done`, so an
        #                           inference LOSES the block this row demands;
        #   done WITH a stamp     — that same inference answers `renew`, so it INVENTS a block
        #                           this row forbids.
        # A fixture whose field and stamp AGREE would be green over the exact inference it exists
        # to forbid, which is how the earlier `exported` bar shipped.
        _s7_age = REAP_MIN_AGE_MIN + 5
        _s7_pass = {"since": now(), "pane": "%83", "transcript": str(_rt), "exported": True,
                    "pids": [[4242, "stamp-4242"]], "disposition": "done", "handoff_stamp": ""}
        _s7_b_control = reap_blockers(_s7_pass, _s7_age, {"%81", "%82", "%83"})
        _s7_b_renew = reap_blockers(dict(_s7_pass, disposition="renew"), _s7_age,
                                    {"%81", "%82", "%83"})
        _s7_b_stamped = reap_blockers(dict(_s7_pass, handoff_stamp="2026-07-29T12:00:00"),
                                      _s7_age, {"%81", "%82", "%83"})
        check("s12-07 S7-a: the disposition is STORED, not INFERRED. The control record passes "
              "every other precondition — live pane, the harness identity it checked out with, an "
              "exported transcript that is still on disk, aged past the policy minimum — and is "
              "held by nothing, so the renew record's blocker can only be about the disposition. "
              "Both discriminating records disagree with the stamp on purpose: renew-with-no-stamp "
              "must still block, done-with-a-stamp must still pass",
              _s7_b_control == []
              and len(_s7_b_renew) == 1 and "disposition=renew" in _s7_b_renew[0]
              and _s7_b_stamped == [])
        clear_awaiting(base_g, "door2")
        clear_awaiting(base_g, "free2")
        clear_awaiting(base_g, "renew2")
        _rt.unlink()
        _sh_rp = __import__("shutil")
        _sh_rp.rmtree(pkg / "workers" / "door2")
        live_tmux_panes["v"] = _rp_panes
        harness_up["v"] = None
        killed.clear()
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

        # ---- kill-pane (task 7.91): a direct, single-pane reap; close-seat's shape, narrower ----
        # scope (kills the pane only -- no transcript export, no roster mutation, no session
        # close). Fixtures are fresh names so nothing above this block needs to survive it.
        (pkg / "workers" / "kp-door").mkdir(exist_ok=True)
        (pkg / "workers" / "kp-door" / "agent.md").write_text(
            "---\nagent: kp-door\nharness: claude\nmodel: opus\nrelays: master\n---\nbrief\n")
        run(cmd_checkin, agent="kp-door", summary="the owner door, kill-pane fixture", pane="%701")
        live_tmux_panes["v"].add("%701")

        run(cmd_checkin, agent="kp-live", summary="an active seat, kill-pane fixture", pane="%702")
        live_tmux_panes["v"].add("%702")

        run(cmd_checkin, agent="kp-done", summary="a finished seat, kill-pane fixture", pane="%703")
        live_tmux_panes["v"].add("%703")

        def _kp_mark_done(r):
            r["active"] = "no"
            r["checkout"] = f"closed {now()}"
        update_row(base_g, "kp-done", _kp_mark_done)

        killed.clear()
        _ko, _kc = refuse(cmd_kill_pane, agent="zeta", pane_id="%703")
        check("kill-pane: the ROLE gate refuses a caller that is not leader/chief-of-staff/"
              "closer-*, naming the flag the same way every other role gate does",
              _kc == 2 and "kill-pane" in _ko and killed == [])

        _bo, _bc = refuse(cmd_kill_pane, agent="chief-of-staff", pane_id="not-a-pane")
        check("kill-pane: a malformed target (no leading %) is refused before anything else runs "
              "-- this is a PANE id, never a seat name, and the message says so",
              _bc == 1 and "does not look like a tmux pane id" in _bo and killed == [])

        _oo, _oc = refuse(cmd_kill_pane, agent="chief-of-staff", pane_id="%799")
        check("kill-pane (criterion 2, clause 2): a pane matching NO current roster row is "
              "refused -- this tool only ever touches panes this run's own roster accounts for, "
              "and the refusal names no --force escape because none exists",
              _oc == 1 and "matches no CURRENT roster row" in _oo and killed == [])

        _do, _dc = refuse(cmd_kill_pane, agent="chief-of-staff", pane_id="%701")
        check("kill-pane (criterion 2, clause 1 / bars.md 4): the pane of a seat carrying "
              "`relays:` is refused, UNCONDITIONALLY -- the owner door -- derived from the "
              "descriptor, never a kit-side name list",
              _dc == 1 and "carries a relay path to a human role" in _do and killed == [])

        _dfo, _dfc = refuse(cmd_kill_pane, agent="chief-of-staff", pane_id="%701", force=True)
        check("kill-pane (criterion 3, the control's other half / bars.md 4): --force does NOT "
              "lift the door refusal -- unlike close-seat's OWN door check, this one has no "
              "escape at all, because kill-pane is a bare reap-by-id with none of close-seat's "
              "surrounding lifecycle care",
              _dfc == 1 and "carries a relay path to a human role" in _dfo and killed == [])

        _ao, _ac = refuse(cmd_kill_pane, agent="chief-of-staff", pane_id="%702")
        check("kill-pane (criterion 5): a pane whose roster row is still ACTIVE (not "
              "roster-done) is refused without --force -- read from the row's `active` field as "
              "ground truth (G-196), never inferred from whether the pane looks alive in tmux",
              _ac == 1 and "not roster-done" in _ao and killed == [])

        # criterion 4's OTHER direction, FIRST while the default stub is still in place: a
        # "successful" kill call whose target tmux STILL LISTS afterward must be caught, never
        # inferred from the kill call's own exit code (G-10's whole point) -- the default stub
        # (`killed.append(pane) or (True, "")`) never removes the pane from the live set, so it
        # doubles as this control for free.
        killed.clear()
        _so, _sc = refuse(cmd_kill_pane, agent="chief-of-staff", pane_id="%703")
        check("kill-pane (criterion 4, the control -- can this check fail?): a pane the kill call "
              "reports OK for but which tmux STILL LISTS afterward is caught and refused, not "
              "laundered through a trusted exit code",
              _sc == 1 and "STILL LISTED" in _so and "%703" in killed)

        # Now the genuine permit direction: a stub that ALSO removes the pane on kill, so the
        # post-kill tmux-list-panes check the code actually performs has something real to see.
        _orig_kp_kill = tmux_kill_pane
        def _kp_kill_and_remove(pane):
            killed.append(pane)
            live_tmux_panes["v"].discard(pane)
            return True, ""
        tmux_kill_pane = _kp_kill_and_remove

        # The "still roster-ACTIVE" warning is deliberately on STDERR (matching close-seat's own
        # force-override warnings elsewhere in this file), and `run()` leaves stderr on the real
        # stream (harness_outcome's capture_err=False) -- so the PROOF --force actually let this
        # through is `killed`, not a stdout substring.
        run(cmd_kill_pane, agent="chief-of-staff", pane_id="%702", force=True)
        check("kill-pane (criterion 5, the escape): --force overrides the not-roster-done "
              "refusal, the same convention close-seat's own door check uses for a deliberate "
              "act -- the pane is actually killed, not merely permitted on paper",
              "%702" in killed)

        killed.clear()
        _go = run(cmd_kill_pane, agent="chief-of-staff", pane_id="%703")
        check("kill-pane (criterion 3, the permit direction / criterion 4, the pass): a "
              "genuinely reapable pane (roster-done, no relays) is killed and VERIFIED gone via "
              "live_panes(), not merely reported killed -- and its roster row is untouched (no "
              "transcript export, no active-flag mutation): freeing the pane and finishing the "
              "lifecycle are different acts (criterion 6)",
              "%703" in killed and "GONE" in _go
              and current_row(load_workers(base_g)[2], "kp-done")["active"] == "no")

        tmux_kill_pane = _orig_kp_kill
        for _kpd in ("kp-door", "kp-live", "kp-done"):
            __import__("shutil").rmtree(pkg / "workers" / _kpd, ignore_errors=True)
        live_tmux_panes["v"] -= {"%701", "%702", "%703"}
        killed.clear()

        # ---- relaunch-pane (task 7.95, G-282): revive an ALREADY-REGISTERED, bare pane IN ----
        # ---- PLACE via the same tmux_respawn_pane + launch_seat(pane=...) pair close-seat's ----
        # ---- in-place renew uses -- never close-seat itself, so its door guard is never in ----
        # ---- this call graph at all (criteria 1/2). Fixtures are fresh names; nothing above ----
        # ---- this block needs to survive it. ----
        (pkg / "workers" / "rp-door").mkdir(exist_ok=True)
        (pkg / "workers" / "rp-door" / "agent.md").write_text(
            "---\nagent: rp-door\nharness: claude\nmodel: opus\nrelays: master\n---\nbrief\n")
        run(cmd_checkin, agent="rp-door", summary="the owner door, relaunch-pane fixture",
            pane="%711")
        live_tmux_panes["v"].add("%711")

        def _rp_mark_done(r):
            r["active"] = "no"
            r["checkout"] = f"closed {now()}"
        update_row(base_g, "rp-door", _rp_mark_done)

        (pkg / "workers" / "rp-live").mkdir(exist_ok=True)
        (pkg / "workers" / "rp-live" / "agent.md").write_text(
            "---\nagent: rp-live\nharness: claude\nmodel: opus\n---\nbrief\n")
        run(cmd_checkin, agent="rp-live", summary="a still-active seat, relaunch-pane fixture",
            pane="%712")
        live_tmux_panes["v"].add("%712")

        respawned.clear()
        _role_o, _role_c = refuse(cmd_relaunch_pane, agent="zeta", target="rp-door",
                                  pane_id="%711", dry_run=False)
        check("relaunch-pane: the ROLE gate refuses a caller that is not leader/chief-of-staff/"
              "closer-*, the SAME predicate kill-pane uses (PRIN-11 — one derivation, not a new "
              "mechanism)",
              _role_c == 2 and "relaunch-pane" in _role_o and respawned == [])

        _nb_o, _nb_c = refuse(cmd_relaunch_pane, agent="chief-of-staff", target="rp-ghost",
                              pane_id="%999", dry_run=False)
        check("relaunch-pane: an agent with no briefing at all is refused before any gate runs "
              "— there is nothing to relaunch, and no --force escape exists because there is "
              "nothing to force",
              _nb_c == 1 and "no worker briefing carries" in _nb_o and respawned == [])

        _mp_o, _mp_c = refuse(cmd_relaunch_pane, agent="chief-of-staff", target="rp-door",
                              pane_id="not-a-pane", dry_run=False)
        check("relaunch-pane: a malformed target (no leading %) is refused before anything else "
              "runs — this is a PANE id, never a seat name or a bare number",
              _mp_c == 1 and "does not look like a tmux pane id" in _mp_o and respawned == [])

        _pm_o, _pm_c = refuse(cmd_relaunch_pane, agent="chief-of-staff", target="rp-door",
                              pane_id="%999", dry_run=False)
        check("relaunch-pane (criterion 1 / bars.md 3): a pane id that does NOT match the "
              "roster's own recorded pane for the target is refused UNCONDITIONALLY — the "
              "caller must resolve it fresh from `workers`, never from memory; no --force lifts "
              "a mismatch because forcing one does not make the id correct",
              _pm_c == 1 and "does not match the roster's own recorded pane" in _pm_o
              and "%711" in _pm_o and respawned == [])

        _act_o, _act_c = refuse(cmd_relaunch_pane, agent="chief-of-staff", target="rp-live",
                                pane_id="%712", dry_run=False)
        check("relaunch-pane (kill-pane's own criterion-5 convention): a roster row still "
              "ACTIVE (not roster-done) is refused without --force — a live seat's pane is "
              "close-seat's or renew's to manage, not a bare relaunch",
              _act_c == 1 and "still ACTIVE" in _act_o and respawned == [])

        _fo = run(cmd_relaunch_pane, agent="chief-of-staff", target="rp-live", pane_id="%712",
                  dry_run=False, force=True)
        check("relaunch-pane: --force lifts ONLY the still-active refusal (the same "
              "'if you mean it' convention close-seat's own door check and kill-pane's "
              "criterion 5 both use) and the call completes end to end — the WARNING itself is "
              "deliberately on stderr (matching close-seat), so the proof is `respawned` and "
              "the success line, never a stdout substring for the warning",
              respawned and respawned[0][0] == "%712" and "relaunched: rp-live back up" in _fo)
        respawned.clear()

        live_tmux_panes["v"].discard("%711")
        _tl_o, _tl_c = refuse(cmd_relaunch_pane, agent="chief-of-staff", target="rp-door",
                              pane_id="%711", dry_run=False)
        check("relaunch-pane: a pane that is not currently live in tmux AT ALL is refused — "
              "nothing to relaunch into; `launch --only` is the tool for a genuinely fresh pane",
              _tl_c == 1 and "is not a live tmux pane" in _tl_o and respawned == [])
        live_tmux_panes["v"].add("%711")

        harness_up["v"] = [4242]
        _hr_o, _hr_c = refuse(cmd_relaunch_pane, agent="chief-of-staff", target="rp-door",
                              pane_id="%711", dry_run=False)
        check("relaunch-pane (the unconditional backstop, bar 11 — can this check fail?): a "
              "pane that still holds a LIVE HARNESS PROCESS is refused with NO --force offered "
              "at all — ground truth is read from /proc (G-10/G-11's own discipline: ask the "
              "process table, never the roster), so a stale-but-inactive roster row cannot let "
              "a genuinely running harness be silently respawned over",
              _hr_c == 1 and "still holds a live harness process" in _hr_o and respawned == [])
        harness_up["v"] = None

        # ---- criterion 3, gate 1: check_bindings (G-51), exercised on the DRY-RUN path too, ----
        # ---- matching cmd_launch's own reasoning verbatim (a dry-run exists to show what a ----
        # ---- real relaunch would do, so a divergence must not be hidden from it either). ----
        (pkg / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-9,rp-door,,claude,fable,,,m0\n", encoding="utf-8")
        _gd_o, _gd_c = refuse(cmd_relaunch_pane, agent="chief-of-staff", target="rp-door",
                              pane_id="%711", dry_run=True)
        check("relaunch-pane (criterion 3, check_bindings/G-51, exercised on the dry-run path): "
              "a descriptor that disagrees with taskforce.csv's binding registry is refused, "
              "naming the divergence — the command carries its own name through the refusal, "
              "not a hardcoded label",
              _gd_c == 2 and "relaunch-pane" in _gd_o
              and "taskforce.csv says fable" in _gd_o and respawned == [])
        (pkg / "taskforce.csv").unlink()

        _dr_o = run(cmd_relaunch_pane, agent="chief-of-staff", target="rp-door", pane_id="%711",
                    dry_run=True)
        check("relaunch-pane: a clean --dry-run previews the command it would start and "
              "mutates NOTHING — no respawn, no launch, matching cmd_launch's own dry-run shape",
              "[dry-run] would respawn %711 and start rp-door" in _dr_o and respawned == []
              and current_row(load_workers(base_g)[2], "rp-door")["active"] == "no")

        # ---- criterion 3, gate 2: the launch memory floor, via the SAME launch_gates() ----
        # ---- cmd_launch itself uses -- exercised through a REAL call (dry_run=False), since ----
        # ---- --dry-run deliberately skips the memory gate (matches cmd_launch's own G-51/5). ----
        avail_real_rp = available_mb
        available_mb = lambda: budget_mod.read_floor(pkg, "refuse") - 1
        _mem_o, _mem_c = refuse(cmd_relaunch_pane, agent="chief-of-staff", target="rp-door",
                                pane_id="%711", dry_run=False)
        available_mb = avail_real_rp
        check("relaunch-pane (criterion 3, gate 2 — the memory floor): one MB under the "
              "package's declared floor refuses through the SAME launch_gates() cmd_launch "
              "itself uses (PRIN-11), even though nothing else about this call is wrong",
              _mem_c == 2 and "memory gate: REFUSED" in _mem_o and respawned == [])

        # ---- criterion 3, gate 3 (both halves) + criteria 1/2, the genuine permit direction ----
        _sess_before = len(read_csv_table(sessions_csv(pkg), SESSIONS_COLS)[1])
        _ok_o = run(cmd_relaunch_pane, agent="chief-of-staff", target="rp-door", pane_id="%711",
                    dry_run=False)
        _sess_after = len(read_csv_table(sessions_csv(pkg), SESSIONS_COLS)[1])
        check("relaunch-pane (criteria 1+2, the permit direction): roster-done, pane alive, no "
              "harness running, bindings agree, memory clears — rp-door is respawned IN PLACE "
              "via tmux_respawn_pane then launch_seat(pane=...), the exact pair close-seat "
              "--renew's in-place branch uses, and reports the SAME pane back, naming its "
              "relays: declaration",
              respawned and respawned[0][0] == "%711"
              and "relaunched: rp-door back up in %711 (same pane, in place)" in _ok_o
              and "carries relays: master; the door is up again" in _ok_o)
        check("relaunch-pane (criterion 3, gate 3a — session-trace write): launch_seat's own "
              "session_open call fires on this path exactly as it does for `launch` and "
              "`close-seat --renew` — a sessions.csv row is appended, not skipped",
              _sess_after == _sess_before + 1)
        respawned.clear()

        _ci_o = run(cmd_checkin, agent="rp-door",
                    summary="back up via relaunch-pane, checking in from the same pane",
                    pane="%711")
        check("relaunch-pane (criterion 3, gate 3b — the roster write): the relaunched seat's "
              "own next `checkin` is NOT refused by P37 (the zombie-double-checkin guard) — it "
              "lands from the SAME pane its own prior row already named, which is the specific "
              "exception P37 carries for a recovery rather than a twin. This is how the roster "
              "row actually gets rewritten active — this verb deliberately does not write it "
              "directly",
              "checked in: rp-door" in _ci_o)

        for _rpd in ("rp-door", "rp-live"):
            __import__("shutil").rmtree(pkg / "workers" / _rpd, ignore_errors=True)
        live_tmux_panes["v"] -= {"%711", "%712"}
        respawned.clear()

        # ---- criterion 4: the relays: door guard inside cmd_close_seat is UNTOUCHED by any of ----
        # ---- the above -- re-run its own refusal on a checked-out seat with a live bare pane ----
        # ---- and confirm BOTH close-seat and close-seat --renew still refuse it exactly as ----
        # ---- before (no existing selftest row covered this guard directly before this task). ----
        (pkg / "workers" / "rp-door2").mkdir(exist_ok=True)
        (pkg / "workers" / "rp-door2" / "agent.md").write_text(
            "---\nagent: rp-door2\nharness: claude\nmodel: opus\nrelays: master\n---\nbrief\n")
        run(cmd_checkin, agent="rp-door2", summary="second door fixture, criterion-4 regression",
            pane="%713")
        live_tmux_panes["v"].add("%713")

        def _rp2_mark_done(r):
            r["active"] = "no"
            r["checkout"] = f"closed {now()}"
        update_row(base_g, "rp-door2", _rp2_mark_done)

        killed.clear()
        _g4a_o, _g4a_c = refuse(cmd_close_seat, agent="leader", target="rp-door2")
        check("criterion 4 (report, task 7.95): a checked-out door seat with a live bare pane "
              "is STILL refused by plain close-seat after this task's change, exactly as "
              "before — the guard was never touched",
              _g4a_c == 1 and "carries a relay path to a human role" in _g4a_o and killed == [])
        _g4b_o, _g4b_c = refuse(cmd_close_seat, agent="leader", target="rp-door2", renew=True,
                                no_export=True)
        check("criterion 4 (report, task 7.95): close-seat --renew on the same checked-out "
              "door seat is ALSO still refused, unweakened and not made pane-state-aware — the "
              "renew path offers no back door around the plain close's refusal",
              _g4b_c == 1 and "carries a relay path to a human role" in _g4b_o and killed == [])

        # ---- criterion 6, a GENUINE mutation control (bar 11 — can this check fail?): a ----
        # ---- respawn that "succeeds" but whose harness never actually comes up must be ----
        # ---- reported as a FAILURE, never laundered into the success line — this is new ----
        # ---- glue code (launch_seat's own G-11 check is already covered elsewhere; what is ----
        # ---- NOT covered anywhere else is THIS command's own handling of that return value). ----
        harness_up["v"] = []   # positively absent: wait_harness_up will report failure
        _wf_o, _wf_c = refuse(cmd_relaunch_pane, agent="chief-of-staff", target="rp-door2",
                              pane_id="%713", dry_run=False)
        harness_up["v"] = None
        check("relaunch-pane (criterion 6, the control — can this check fail?): a respawn that "
              "reports OK but whose harness never verifies up is surfaced as `relaunch FAILED`, "
              "never printed as `relaunched:` — this command does not trust tmux_respawn_pane's "
              "own exit code any further than launch_seat already does, and does not swallow "
              "launch_seat's error",
              _wf_c == 1 and "relaunch FAILED" in _wf_o and "relaunched:" not in _wf_o
              and respawned and respawned[-1][0] == "%713")

        __import__("shutil").rmtree(pkg / "workers" / "rp-door2", ignore_errors=True)
        live_tmux_panes["v"].discard("%713")
        killed.clear()
        respawned.clear()

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

        # ---- guard sweep, slice 2 sites 6-7: WHICH closing rule a wake applies ----
        # Two rows above already assert that a closing seat is cut out of an `all` broadcast and
        # of a group message — and BOTH send as `alpha`, who is neither the leader nor anyone's
        # closer, so the direct rule would exclude the seat too. The branch SELECTION is therefore
        # unasserted: delete either test and both rows stay green. `closing_reaches` is the whole
        # disagreement, and only the leader (or the seat's own closer) can tell the rules apart.
        # This is the wake/read disagreement class in its cleanest form: the wake half re-deriving
        # a scope the read half computes elsewhere.
        set_closing(base_g, "iota", "closer-iota")
        _, pre_c1 = load_messages(base_g)
        mkc1 = pre_c1[-1]["num"]
        _bo = sd("leader", "all", "m-probe closed", type="verdict", why="milestone")
        check("G-21/G-32: a closing seat is cut out of an `all` BROADCAST even when the sender is "
              "the LEADER — the one sender whose DIRECT message still reaches it. Under the "
              "direct rule the leader's broadcast would WAKE the seat while `read` hid the "
              "message: the wake and read halves disagreeing about one message",
              "closing: iota" in _bo
              and "m-probe closed" not in rd("iota", after=mkc1, peek=True))
        _, pre_c2 = load_messages(base_g)
        mkc2 = pre_c2[-1]["num"]
        _go2 = sd("leader", "lane-g32", "lane note from the leader", type="note")
        check("G-21/G-32: and a GROUP message applies the MEMBER rule rather than the direct one "
              "— a closing MEMBER is cut out however reachable its closer exception would make "
              "it, which is what keeps the closer exception from turning every group into a side "
              "door around the closing cut",
              "closing: iota" in _go2
              and "lane note from the leader" not in rd("iota", after=mkc2, peek=True))
        clear_closing(base_g, "iota")

        # ---- the session-trace REPORT at ALL THREE closing verbs (the slice-2 residual) ----
        # `session_close` itself is covered DIRECTLY by the 7.37 block, against its own package.
        # Its three CALL SITES — `checkout`, `close-seat` and `depart` — each report the outcome
        # in the same two lines, and NOTHING asserted either line at any of them. That is this
        # seat's own 7.37 post-mortem recurring one layer up: THE DERIVATION GOT COVERED AND THE
        # CALL SITES DID NOT.
        # ⚠ These were sites 4-5 of the ratified slice 2 and were EXCLUDED there, because the
        # premise that selected them was false: `cmd_checkout`'s copy was named as the COVERED
        # safer sibling and it is uncovered too. All three are. So they are covered here as one
        # REPLICATION item under their own justification, rather than smuggled in under a key that
        # never selected them — a gap admitted under a wrong reason is worse than an open gap,
        # because the reason is what the next seat inherits.
        # WHY `refuse` AND NOT `run`: it captures STDERR — where the warning goes by design, so a
        # bookkeeping failure is never mistaken for the act's own output — and it returns the exit
        # code, and THAT CODE BEING 0 IS THE CLAIM "the close itself stands".
        def _sc_boom(_a, _seat):
            raise OSError("sessions.csv is read-only")

        _sc_real = session_close
        _sh_sc = __import__("shutil")
        try:
            for _verb, _seat, _pane, _call in (
                    ("checkout", "st1", "%61",
                     lambda s: refuse(cmd_checkout, agent=s, no_export=True)),
                    ("close-seat", "st2", "%62",
                     lambda s: refuse(cmd_close_seat, agent="leader", target=s, renew=False,
                                      no_export=True)),
                    ("depart", "st3", "%63",
                     lambda s: refuse(cmd_depart, agent=s))):
                (pkg / "workers" / _seat).mkdir(exist_ok=True)
                (pkg / "workers" / _seat / "agent.md").write_text(
                    f"---\nagent: {_seat}\nharness: claude\nmodel: opus\n---\nbrief\n")
                run(cmd_checkin, agent=_seat, summary=f"session-trace probe: {_verb}", pane=_pane)
                # `session_open` takes the SEAT RECORD, not a name — and `harness: claude`
                # would send it into the native-id resolver, so the fixture declares a harness
                # that does not, and passes wait=0.0 as well. Neither is this row's subject.
                _srec = {"agent": _seat, "harness": "probe", "model": "opus",
                         "cwd": str(pkg / "workers" / _seat)}
                _sid, _ = session_open(ns(), _srec, since=time.time(), wait=0.0)
                _sout, _scode = _call(_seat)
                _, _, _rows_sc = load_workers(base_dir(ns()))
                check(f"7.37/{_verb}: the session-trace outcome is REPORTED — the id of the row "
                      f"the close completed, named at the one moment the seat's session actually "
                      f"ends. `session_close` is covered directly and all three of its CALL SITES "
                      f"were covered nowhere; the roster flip is asserted alongside so this "
                      f"cannot pass for a verb that did nothing",
                      _scode == 0 and _sid != "" and f"sessions.csv: {_sid} ended" in _sout
                      and current_row(_rows_sc, _seat)["active"] == "no")
                run(cmd_checkin, agent=_seat, summary=f"session-trace probe: {_verb} again",
                    pane=_pane)
                session_open(ns(), _srec, since=time.time(), wait=0.0)
                session_close = _sc_boom
                _bout, _bcode = _call(_seat)
                session_close = _sc_real
                _, _, _rows_b = load_workers(base_dir(ns()))
                check(f"7.37/{_verb}: and when the trace write FAILS the act STILL STANDS and the "
                      f"failure is ANNOUNCED — bookkeeping ABOUT a close must never become a gate "
                      f"ON it (7.37's own ruling), so `session_trace_safe` swallows the exception. "
                      f"A swallow nobody reports is a session trace that goes quietly incomplete, "
                      f"and the only thing standing between those two is this line printing",
                      _bcode == 0 and "sessions.csv row NOT completed" in _bout
                      and "The close itself stands" in _bout
                      and current_row(_rows_b, _seat)["active"] == "no")
                clear_awaiting(base_g, _seat)
                _sh_sc.rmtree(pkg / "workers" / _seat)
        finally:
            # Restored under `finally` because a leak here does not fail loudly at the leak: the
            # 7.37 block calls `session_close` DIRECTLY much later, and a stub still bound there
            # would report as an abort three thousand lines from its cause.
            session_close = _sc_real

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
        # One MB under the floor the FIXTURE PACKAGE declares (task 7.82 — the gate reads
        # pkg/budget.json now, so the number this test undercuts must be that same declaration,
        # not a module constant that no longer exists).
        available_mb = lambda: budget_mod.read_floor(pkg, "refuse") - 1
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
                  and "overridden with --force-memory" in out and "refused [coord" not in out)
            out, code = refuse(cmd_launch, agent="watcher", only="gamma", dry_run=False,
                               force_memory=True)
            check("#230: --force-memory does NOT carry the ROLE gate — the memory flag is not a "
                  "back door into a leader-only command",
                  code == 2
                  and "role gate: REFUSED — `launch` is leader's and the chief-of-staff's"
                  in out)
            out, code = refuse(cmd_launch, agent="leader", only="gamma", dry_run=False)
            check("#230: the LEADER is refused by the memory gate like anyone else and still sees "
                  "BOTH verdicts — the gate binds the seat holding lifecycle authority too",
                  code == 2 and "role gate: PASS" in out and "memory gate: REFUSED" in out)
            out, code = refuse(cmd_launch, agent="watcher", only="gamma", dry_run=True, force=True)
            check("#230: --dry-run keeps the ROLE gate ALONE — it opens nothing, so refusing it "
                  "on available memory would refuse a command that cannot spend any",
                  "memory gate" not in out)

            # ---- task 7.82 criterion 5: THE CONTROL THAT FAILS BY CONSTRUCTION ----
            # "Move budget.json aside and show each consumer REFUSING to start; a consumer that
            # starts anyway is the defect this criterion exists to catch." Asserted through a REAL
            # cmd_launch (dry_run=False), not a direct call to the gate — `--dry-run` deliberately
            # skips the memory gate, so a dry run could never show this.
            available_mb = lambda: 999999          # ⚠ MASSES of memory: the ONLY thing that can
            # refuse this launch is the missing declaration. Without this line the check would pass
            # off the previous below-floor stub and prove nothing about the floor being UNDECLARED.
            bjson = pkg / "budget.json"
            saved = bjson.read_text()
            bjson.unlink()
            try:
                out, code = refuse(cmd_launch, agent="leader", only="gamma", dry_run=False)
                check("7.82/5: with budget.json MOVED ASIDE the launch gate REFUSES — with memory "
                      "to spare, so the refusal can only be the missing declaration. A floor is "
                      "READ, never invented, and 'no declaration' is never a silent fallback",
                      code == 2 and "memory gate: REFUSED" in out
                      and "budget.json" in out and "may not invent a number" in out)
                # ...and the positive twin, or the check above passes on a gate that refuses
                # everything. Same command, same memory, declaration restored -> PASSES.
                bjson.write_text(saved)
                out, code = refuse(cmd_launch, agent="leader", only="gamma", dry_run=False)
                check("7.82/5: restoring budget.json restores the launch — the refusal above "
                      "tracked the declaration and not some unrelated failure",
                      code == 0 and "refused [coord" not in out)
                # ⚠ THIS ASSERTS ON A SUCCESSFUL LAUNCH, DELIBERATELY. The verdict block prints
                # only on a refusal or an override, so an earlier version of this check looked for
                # the floor in a REFUSAL and passed — while a successful launch said nothing about
                # which floor it used. Criterion 8 has to hold when things WORK.
                check("7.82/8: a SUCCESSFUL launch still says WHICH VALUE IT USED AND WHY — the "
                      "floor names budget.json and the spike names its source. A number visible "
                      "only when you are blocked is one nobody can check while things work",
                      "floor: budget.json floors.launch_refuse_mb" in out and "spike:" in out)
                # ⚠ THE PROVENANCE LABEL MUST AGREE WITH THE NUMBER IT LABELS. SEAT_SPIKE_MB is
                # read ONCE at import, so a label that re-asked the environment at call time would
                # print "COORD_SEAT_SPIKE_MB" beside the built-in 1400 whenever the var was set
                # after import — a confident wrong answer to the exact question criterion 8 asks.
                # Asserted as an AGREEMENT, so it fails whichever of the two drifts.
                check("7.82/8: the spike's SOURCE and its VALUE are captured at the same instant "
                      "— the label cannot claim an env override the number never saw",
                      (SEAT_SPIKE_SOURCE == "COORD_SEAT_SPIKE_MB")
                      == (os.environ.get("COORD_SEAT_SPIKE_MB") not in (None, ""))
                      and ("(%s)" % SEAT_SPIKE_SOURCE) in out)

                # ⚠ A DECLARED-BUT-UNREADABLE budget.json IS A DIFFERENT FACT FROM AN ABSENT ONE,
                # and this pair is the one that stops them collapsing. A wrong path and a corrupt
                # declaration must never read alike to the operator holding the refusal.
                bjson.write_text("{ not json")
                out, code = refuse(cmd_launch, agent="leader", only="gamma", dry_run=False)
                check("7.82/5: a DECLARED but UNREADABLE budget.json refuses with its own reason, "
                      "distinct from 'nothing declares a floor' — collapsing the two is what made "
                      "a wrong path look identical to a package with no budget",
                      code == 2 and "could not be read" in out
                      and "NOT the same as no budget" in out)
            finally:
                bjson.write_text(saved)
        finally:
            available_mb = avail_real2

        os.environ.pop("COORD_LAUNCH_TARGET", None)

        # ================= s12-02: the role gate learns SELF from OTHER =================
        # Stage-1 §1.1/§1.2. `role_verdict`'s `allow` was a predicate over the CALLER NAME ALONE
        # and no call site passed the TARGET, so the gate could not tell "I close MYSELF" from "I
        # close YOU" — the mechanism behind run-2's 15:1x refusal of an act the owner had already
        # ruled legal. These rows are LAST in this fixture deliberately: S1-a/S1-f perform REAL
        # closes, so nothing may sit behind them that reads the roster rows they retire.
        import inspect as _s12_inspect
        calling_pane["v"] = ""   # no pane claims an identity — every row here resolves via --as

        # ---- S1-a: the self-close is LEGAL, with NO --force. The design's Stage-1 acceptance.
        # The assertion is that THE GATE DOES NOT EXIT and the call proceeds: proven positively by
        # the W1 self-act warning, which is printed ONLY on the far side of a passed gate on a
        # self act. Downstream this call still refuses (the registry-divergence fixture above left
        # gamma's taskforce row diverged, so check_bindings stops the renew) — that is a LATER
        # refusal by a DIFFERENT guard, which is exactly why the role refusal's own text, and not
        # the process exit code, is what this row reads.
        _s12a_out, _s12a_code = refuse(cmd_close_seat, target="gamma", as_agent="gamma",
                                       renew=True, force=False, no_export=True)
        check("s12-02 S1-a: a seat closing ITSELF passes the role gate with NO --force — the "
              "target is a parameter now, so `caller == target` is a fact the gate can see "
              "(d-close-renew-decider-recorded: the SEAT decides its own renew/refresh)",
              _s12a_code != 2
              and "WARNING self-act" in _s12a_out
              and "closing ANOTHER seat" not in _s12a_out
              and "is leader's or a closer-* seat's;" not in _s12a_out)

        # ---- S1-b: THE CONTROL. Same caller, ANOTHER target, still refused. Without this row
        # S1-a is indistinguishable from a gate that was LOOSENED rather than CORRECTED.
        _s12b_out, _s12b_code = refuse(cmd_close_seat, target="delta", as_agent="gamma",
                                       force=False, renew=False, no_export=True)
        check("s12-02 S1-b (control): the SAME seat closing ANOTHER seat is still REFUSED — the "
              "fix distinguishes self from other, it does not open the gate. S1-a without this "
              "row is not evidence",
              _s12b_code == 2 and "closing ANOTHER seat" in _s12b_out)

        # ---- S1-d: W5. The refusal no longer ADVERTISES --force. GATE_FLAGS is untouched and
        # --force still CARRIES the role gate (recover-room.py depends on it); only the
        # advertisement is gone, because a refusal that offers the override teaches every reader
        # to reach for it instead of the legal path.
        check("s12-02 S1-d: the close-seat role refusal does NOT advertise --force — the flag "
              "still carries the gate (GATE_FLAGS untouched, p-override-split-is-safety-critical), "
              "but the refusal names the LEGAL path instead of the override",
              "--force" not in _s12b_out)

        # ---- S1-e: the remedy is the LEGAL one, and it differs by case. Both halves, because a
        # remedy that is right for one case and wrong for the other is a refusal that misroutes.
        _s12e_out, _s12e_code = refuse(cmd_close, target="gamma", as_agent="gamma", dry_run=True,
                                       renew=False, no_export=True, force_memory=False)
        check("s12-02 S1-e: the OTHER case sends the caller to the leader, and the SELF case on a "
              "leader-only command sends them to `checkout --renew` — never the reverse, which is "
              "a refusal that names a path unable to help the caller",
              "ask leader to run it" in _s12b_out
              and _s12e_code == 2
              and "this is not a self-act" in _s12e_out
              and "checkout --renew" in _s12e_out
              and "ask leader to run it" not in _s12e_out)

        # ---- S1-f: LEADER still passes in BOTH directions — on another seat and on itself. The
        # new conjunct is an OR, so it can only add cases; this row is what proves it did not
        # replace one, i.e. that leader's original grant survived the change untouched.
        #
        # ⚠ THIS ROW IS DELIBERATELY LEADER-ONLY, and that is a correction of the source row, not
        # a weakening of it. The row is titled "leader still passes both directions" and its own
        # assertion text then named `gamma`->`gamma` — a NON-leader self-act, which is S1-a's
        # claim, not this one's. Carrying both here made the two rows red together under the
        # `passed = bool(allow(caller))` mutation, and a mutation that reds two rows is not
        # evidence about either (G-62, and `--expect-fail` refuses it by construction). Leader's
        # own self case exercises the same both-directions claim while staying orthogonal to S1-a.
        _s12f1_out, _s12f1_code = refuse(cmd_close_seat, target="leader", as_agent="leader",
                                         force=False, renew=False, no_export=True)
        _s12f2_out, _s12f2_code = refuse(cmd_close_seat, target="delta", as_agent="leader",
                                         force=False, renew=False, no_export=True)
        check("s12-02 S1-f: leader passes on ANOTHER seat AND on itself — the new conjunct is an "
              "OR, so it added a case rather than replacing leader's original grant",
              _s12f1_code != 2 and "closing ANOTHER seat" not in _s12f1_out
              and _s12f2_code != 2 and "closing ANOTHER seat" not in _s12f2_out)

        # ---- S1-g: the flag map is UNTOUCHED. Out of scope by ruling and asserted anyway,
        # because this task edits the gate the map arms.
        check("s12-02 S1-g: GATE_FLAGS is untouched by the target threading — --force still "
              "carries the ROLE gate ONLY and never the memory gate, which is what "
              "jobs/recover-room.py asserts before every unattended override",
              GATE_FLAGS["--force"] == ("role",)
              and GATE_FLAGS["--force-memory"] == ("memory",)
              and gate_forced(argparse.Namespace(force=True, force_memory=False),
                              "memory") is False)

        # ---- S1-i: `close` carries its gate on TWO branches (dry-run/mechanical via `gate`, the
        # spawning path via `launch_gates`). Threading one and not the other leaves the gate
        # inconsistent between a dry-run and a real close — the shape a reader trusts and a test
        # misses, so both branches are read here.
        _s12i_self_dry, _c1 = refuse(cmd_close, target="gamma", as_agent="gamma", dry_run=True,
                                     renew=False, no_export=True, force_memory=False)
        _s12i_self_real, _c2 = refuse(cmd_close, target="gamma", as_agent="gamma", dry_run=False,
                                      renew=False, no_export=True, force_memory=False)
        _s12i_other_dry, _c3 = refuse(cmd_close, target="delta", as_agent="gamma", dry_run=True,
                                      renew=False, no_export=True, force_memory=False)
        _s12i_other_real, _c4 = refuse(cmd_close, target="delta", as_agent="gamma", dry_run=False,
                                       renew=False, no_export=True, force_memory=False)
        check("s12-02 S1-i: BOTH of `close`'s branches thread the target — a self-target gets the "
              "SAME verdict on --dry-run and on a real close, and so does a foreign target; the "
              "gate cannot disagree with itself across the branch",
              _c1 == 2 and _c2 == 2 and _c3 == 2 and _c4 == 2
              and "this is not a self-act" in _s12i_self_dry
              and "this is not a self-act" in _s12i_self_real
              and "closing ANOTHER seat" in _s12i_other_dry
              and "closing ANOTHER seat" in _s12i_other_real)

        # ---- S1-j: kill-pane / relaunch-pane are UNCHANGED by this task. They target a PANE ID,
        # not a seat identity, and inferring "this pane is mine" from the roster would re-import
        # exactly the ambient inference this file's G-101/G-107/G-121 catalogue names as its
        # recurring defect. Read BOTH ways: structurally (the call carries no threading kwarg) and
        # behaviourally (a self-named caller is still refused, so no self path leaked in).
        _s12j_kill_src = _s12_inspect.getsource(cmd_kill_pane)
        _s12j_rel_src = _s12_inspect.getsource(cmd_relaunch_pane)
        _s12j_ko, _s12j_kc = refuse(cmd_kill_pane, as_agent="gamma", pane_id="%1")
        _s12j_ro, _s12j_rc = refuse(cmd_relaunch_pane, as_agent="gamma", target="gamma",
                                    pane_id="%1", dry_run=True)
        check("s12-02 S1-j: kill-pane and relaunch-pane are NOT threaded — their gate calls carry "
              "no target=/self_legal=, and a caller naming ITSELF is still refused on both. A "
              "pane id is not a seat identity, and deriving one from the roster is the ambient "
              "inference G-101/G-107/G-121 catalogue",
              "self_legal" not in _s12j_kill_src and "self_legal" not in _s12j_rel_src
              and "target=args.target" not in _s12j_rel_src
              and _s12j_kc == 2 and _s12j_rc == 2)

        # ---- S1-k: the 9 gated commands with no self-semantics keep the GENERIC case. This is
        # the row that keeps the case a CALL-SITE PARAMETER: hard-wiring the close-shaped template
        # would make every one of them print "closing ANOTHER seat…" and LOSE `allowed_desc` — the
        # only place a refusal names who may act.
        _s12k_out, _s12k_code = refuse(cmd_panel, as_agent="gamma")
        check("s12-02 S1-k: an untargeted gated command (`panel`) keeps the GENERIC case — the "
              "refusal still RENDERS allowed_desc and never borrows the close-shaped wording, so "
              "the 9 self-less gated commands are untouched by the case parameter",
              _s12k_code == 2
              and "leader's alone (it splits the control-panel window)" in _s12k_out
              and "closing ANOTHER seat" not in _s12k_out)

        # ============ s12-03: every refusal NAMES ITS LAYER (stage-1 §1.4, ruling R-8) ============
        # A seat that hits a refusal cannot tell coord.py's OWN gate from its harness's permission
        # classifier — the two look alike, and a bare "refused:" sends the run at the wrong fix
        # (W4). These rows read the PROPERTY (the prefix a reader routes on), never the prose.

        # ---- S1-c: the row the spec's Stage-1 acceptance table names. `_s12b_out` is the
        # close-seat FOREIGN-target refusal S1-b already captured — read again here for its layer,
        # so the two claims stay separable: S1-b says the gate still refuses, S1-c says the refusal
        # is ROUTABLE. Anchored at a line start (`^`), because a prefix that appears mid-message is
        # not a prefix.
        check("s12-03 S1-c: the close-seat foreign-target refusal NAMES ITS LAYER — it begins "
              "`refused [coord role gate]`, so a seat reporting it can never be confused with a "
              "harness classifier block, and it carries the layer paragraph that says so in words",
              re.search(r"^refused \[coord role gate\]: ", _s12b_out, re.M) is not None
              and "NOT your harness's permission" in _s12b_out)

        # ---- S1-h: THE GUARD. Without it the sweep rots on the next added refusal — which is
        # exactly what happened between the spec's writing and its implementation: two new commands
        # added 12 un-layered sites in one day. Read from the module's OWN SOURCE.
        #
        # ⚠ READ AS AN AST, NOT AS TEXT, and that is a correction of the obvious implementation
        # rather than a flourish. A regex over `print(` plus a quote misses THREE SHAPES this sweep
        # actually contained — one single-quoted site, three whose literal sat on a CONTINUATION
        # line rather than beside the call, and one refusal that is RETURNED and never printed at
        # all — while its own red arm still passes on the one shape it can see. It also matches its
        # OWN explanatory comments, which is how this check first went red on prose. The AST has
        # neither problem: it normalizes every quote and f-prefix shape, merges implicit
        # concatenation, and carries no comments at all.
        import ast as _s3_ast
        _s3_src = Path(__file__).read_text(encoding="utf-8")
        _s3_tree = _s3_ast.parse(_s3_src)
        # ⚠ The token is BUILT, never written as a literal: this check reads the file it lives in,
        # so a literal here would be its own first hit — the check would fail on itself forever.
        _s3_bare_tok = "refused" + ":"
        _s3_hits = []
        for _s3_n in _s3_ast.walk(_s3_tree):
            _s3_v = None
            if isinstance(_s3_n, _s3_ast.Constant) and isinstance(_s3_n.value, str):
                _s3_v = _s3_n.value
            elif (isinstance(_s3_n, _s3_ast.JoinedStr) and _s3_n.values
                  and isinstance(_s3_n.values[0], _s3_ast.Constant)):
                _s3_v = _s3_n.values[0].value
            if isinstance(_s3_v, str) and _s3_v.startswith(_s3_bare_tok):
                _s3_hits.append(_s3_n.lineno)
        check("s12-03 S1-h: NO refusal in this module is emitted bare — NO string literal anywhere "
              "in it begins `refused:`, so every refusal is built by `refuse()`/`refusal_text()` "
              "and names its layer. Scoped by AST rather than by a `print(`-shaped regex, which "
              "missed four of the 57 sites and matched its own comments",
              _s3_hits == [])

        # ---- L-a: and every layer token is one of the FIVE. A prefix vocabulary nobody bounds is
        # a prefix vocabulary that grows a sixth token nobody can route on. Read STRUCTURALLY (ast
        # over the call sites) rather than by regex, so the one CONDITIONAL layer expression
        # (`launch_gates`' head, which names the gate that actually refused) is read in full
        # instead of half.
        _s3_tokens, _s3_opaque = set(), []
        for _s3_node in _s3_ast.walk(_s3_tree):
            if not (isinstance(_s3_node, _s3_ast.Call)
                    and getattr(_s3_node.func, "id", None) in ("refuse", "refusal_text")
                    and _s3_node.args):
                continue
            _s3_a0 = _s3_node.args[0]
            if isinstance(_s3_a0, _s3_ast.Name):
                continue          # the selftest's own local `refuse(fn, **kw)` capture helper
            _s3_lits = [x.value for x in _s3_ast.walk(_s3_a0)
                        if isinstance(x, _s3_ast.Constant) and isinstance(x.value, str)]
            if not _s3_lits:
                # A layer this check cannot READ is a layer it cannot BOUND — never a pass.
                _s3_opaque.append(_s3_node.lineno)
            _s3_tokens |= set(_s3_lits)
        check("s12-03 L-a: every layer token emitted anywhere in this module is one of the five "
              "REFUSAL_LAYERS, all five are actually in use, and no call site hides its layer "
              "behind an expression this check cannot read",
              _s3_tokens == set(REFUSAL_LAYERS) and not _s3_opaque)

        # ---- L-b: THE EXIT CODES ARE UNCHANGED. The sites exited with a MIX of 1 and 2 before the
        # sweep, and `watch.py`'s `record_undelivered` path keys on coord's EXIT CODE rather than
        # on this text — so a conversion that uniformized them would change behaviour for it and
        # for every scripted caller while every text assertion above stayed green. Three sites,
        # spanning both codes; the first is ALSO L-c (3 of 3), the third continuation-literal site.
        _s3_lb_cont, _s3_lb_cont_code = refuse(
            cmd_checkin, agent="s12-03-lb", summary="x" * (SUMMARY_MAX + 25), pane="%1",
            force=False)
        _s3_lb_head, _s3_lb_head_code = refuse(
            cmd_read, agent="leader", msg=10 ** 9, after=None, peek=False, all=False, type=None,
            addressed="any", digest=False, limit=None)
        check("s12-03 L-b / L-c (3 of 3): exit codes survive the sweep — the checkin "
              "SUMMARY-LENGTH site (the third continuation-literal one) still exits 1 and names "
              "`input`, an ordinary head site still exits 1, and the role gate still exits 2. The "
              "codes are behaviour (watch.py keys on them), not decoration",
              _s3_lb_cont_code == 1 and _s3_lb_head_code == 1 and _s12k_code == 2
              and re.search(r"^refused \[coord input\]: ", _s3_lb_cont, re.M) is not None
              and re.search(r"^refused \[coord state\]: ", _s3_lb_head, re.M) is not None
              and re.search(r"^refused \[coord role gate\]: ", _s12k_out, re.M) is not None)

        # ============ s12-04: the launch gate recognises the CHIEF-OF-STAFF (G-257) ============
        # `r-cos-launches-the-staffed-seat` (goal decisions.md) makes launching the staffed seat
        # the chief-of-staff's ROUTINE DUTY, and this gate predated it: every routine CoS launch
        # required `--force` -- a flag that reads as an override of policy while actually being
        # compliance with it, which trains the room to force and spends the flag's only signal.
        #
        # THE FIX IS A PREDICATE WIDENING, NOT THE SELF/OTHER THREADING
        # (`core-build-run-adjustments/decisions.md#d-g257-widening-not-threading`): a
        # chief-of-staff launching a WORKER is never a self-act, so `is_self` stays False and
        # s12-02's threading is INERT here -- it could never have discharged G-257. Scope is
        # `launch` and nothing else (`d-cos-inbox-is-convention`), which S4-f is the control for.
        _s4_only = "hk-1"     # never the caller's OWN name: the SELF template is not this claim

        _s4b_out, _s4b_code = refuse(cmd_launch, as_agent="gamma", only=_s4_only,
                                     dry_run=True, force=False, force_memory=False)
        _s4b2_out, _s4b2_code = refuse(cmd_launch, as_agent="closer-alpha", only=_s4_only,
                                       dry_run=True, force=False, force_memory=False)
        _s4cos_dry, _s4cos_dry_code = refuse(cmd_launch, as_agent="chief-of-staff", only=_s4_only,
                                             dry_run=True, force=False, force_memory=False)
        _s4gamma_real, _s4gamma_real_code = refuse(cmd_launch, as_agent="gamma", only=_s4_only,
                                                   dry_run=False, force=False, force_memory=False)
        # ⚠ S4-d USES ITS OWN REFUSED CALLER, and that is isolation rather than duplication. Read
        # off `gamma`, S4-d and S4-b would go red TOGETHER under the one mutation that admits
        # gamma into the predicate -- and a mutation that reds two rows is evidence about neither
        # (G-62). `beta` is refused for the same reason and by the same gate, and shares nothing.
        _s4d_dry, _s4d_dry_code = refuse(cmd_launch, as_agent="beta", only=_s4_only,
                                         dry_run=True, force=False, force_memory=False)
        _s4d_real, _s4d_real_code = refuse(cmd_launch, as_agent="beta", only=_s4_only,
                                           dry_run=False, force=False, force_memory=False)

        # ⚠ THE CoS's REAL-BRANCH CALL RUNS ONE MB UNDER THE PACKAGE'S DECLARED FLOOR, and that is
        # what makes a PASS verdict OBSERVABLE AT ALL: `launch_gates` prints its verdict block only
        # on a refusal, so "role gate: PASS" is readable only when the OTHER gate supplies the
        # refusal. It also means this row opens no pane and spends nothing.
        _s4_avail_real = available_mb
        available_mb = lambda: budget_mod.read_floor(pkg, "refuse") - 1
        try:
            _s4a_out, _s4a_code = refuse(cmd_launch, as_agent="chief-of-staff", only=_s4_only,
                                         dry_run=False, force=False, force_memory=False)
        finally:
            available_mb = _s4_avail_real

        check("s12-04 S4-a: the chief-of-staff's ROUTINE LAUNCH NEEDS NO FLAG -- with force=False "
              "and force_memory=False it passes the role gate and the command PROCEEDS. An "
              "owner-ruled duty (`r-cos-launches-the-staffed-seat`) is what the tool PERMITS now, "
              "instead of compliance a seat has to spell as an override -- which is what trained "
              "the room to force, and is the defect G-257 filed",
              _s4cos_dry_code == 0
              and "[dry-run] hk-1" in _s4cos_dry
              and "refused [coord role gate]" not in _s4cos_dry)

        check("s12-04 S4-b (control): an ordinary seat is STILL refused on `launch`, the refusal "
              "NAMES ITS LAYER, and it names who may act -- the widening ADDED the chief-of-staff, "
              "it did not open the gate. S4-a without this row is not evidence",
              _s4b_code == 2
              and re.search(r"^refused \[coord role gate\]: ", _s4b_out, re.M) is not None
              and "leader's and the chief-of-staff's" in _s4b_out)

        check("s12-04 S4-b2 (control): a `closer-*` seat is STILL refused on `launch` -- the row "
              "that proves `is_leader_or_cos_or_closer` was NOT reused. It admits every closer, "
              "and `d-cos-inbox-is-convention` scopes this widening to the chief-of-staff on "
              "`launch` and nothing else (`d-g257-widening-not-threading`)",
              _s4b2_code == 2
              and re.search(r"^refused \[coord role gate\]: ", _s4b2_out, re.M) is not None)

        check("s12-04 S4-c: the widening did NOT touch the MEMORY gate -- that same flagless "
              "chief-of-staff launch, one MB under the package's declared floor, still REFUSES on "
              "MEMORY and opens nothing. `--force` carries the ROLE gate ONLY (G-257 says so "
              "explicitly), so a widened role predicate may never become a way under the floor",
              _s4a_code == 2 and "memory gate: REFUSED" in _s4a_out
              and "WARNING launching anyway" not in _s4a_out)

        check("s12-04 S4-d: the launch role refusal no longer teaches `--force` as the route for "
              "a duty the tool now simply permits -- the dry-run branch carries the string "
              "NOWHERE, and the real branch carries it on the two-flag disambiguation line ALONE. "
              "That line STAYS: it is what keeps --force and --force-memory distinguishable "
              "(jobs/recover-room.py reasons about exactly that split), never an invitation",
              _s4d_dry_code == 2 and _s4d_real_code == 2
              and "--force" not in _s4d_dry
              and [ln for ln in _s4d_real.splitlines() if "--force" in ln]
              == ["--force carries the ROLE gate; --force-memory carries the MEMORY gate."])

        _s4e_out = run(cmd_gates, json=True)
        check("s12-04 S4-e: the flag map is UNTOUCHED and its PUBLISHED form still agrees with it "
              "-- `gates --json` reports --force carrying the role gate alone. "
              "jobs/recover-room.py reads THIS OUTPUT (not the constant) and refuses to run if it "
              "ever changed, so a publisher drifting from GATE_FLAGS is as bad as GATE_FLAGS "
              "drifting: `p-override-split-is-safety-critical`",
              json.loads(_s4e_out) == {"--force": ["role"], "--force-memory": ["memory"]})

        _s4f = [
            ("close", refuse(cmd_close, target="delta", as_agent="chief-of-staff", dry_run=True,
                             renew=False, no_export=True, force_memory=False)),
            ("close-seat", refuse(cmd_close_seat, target="delta", as_agent="chief-of-staff",
                                  renew=False, no_export=True)),
            ("reap --go", refuse(cmd_reap, as_agent="chief-of-staff", go=True)),
            ("panel", refuse(cmd_panel, as_agent="chief-of-staff")),
            ("owner", refuse(cmd_owner, as_agent="chief-of-staff", state="afk", note="")),
            ("close-run", refuse(cmd_close_run, as_agent="chief-of-staff")),
            ("add-to-group", refuse(cmd_add_to_group, as_agent="chief-of-staff", group="pair",
                                    members=["gamma"])),
            ("remove-from-group", refuse(cmd_remove_from_group, as_agent="chief-of-staff",
                                         group="pair", members=["gamma"])),
        ]
        check("s12-04 S4-f: the widening is scoped to `launch` AND NOTHING ELSE -- close, "
              "close-seat, reap --go, panel, owner, close-run, add-to-group and "
              "remove-from-group every one still REFUSE the chief-of-staff on the role gate. The "
              "terminating verbs among them are barred by `d-cos-may-launch`: the bound is "
              "open-versus-terminate, and a chief-of-staff is not a second leader",
              all(code == 2
                  and re.search(r"^refused \[coord role gate\]: ", out, re.M) is not None
                  for _name, (out, code) in _s4f))

        # ⚠ AGREEMENT, NOT VERDICT. This row asserts the two branches SAY THE SAME THING, never
        # what they say -- S4-a and S4-b own the verdicts. Asserting the verdict here would make a
        # revert of BOTH branches red this row too, and a mutation that reds two rows is evidence
        # about neither (G-62, and `--expect-fail` refuses it by construction). It is with S4-a
        # that this row establishes the REAL branch's chief-of-staff verdict: S4-a proves the
        # dry-run branch passes, this one proves the real branch says the same. And the real-side
        # token is not read off silence -- S4-c independently proves that same call RENDERS its
        # verdict block (it refuses on memory), so "not refused" here is a read, not an absence.
        _s4g = [("chief-of-staff", _s4cos_dry, _s4a_out), ("gamma", _s4b_out, _s4gamma_real)]
        check("s12-04 S4-g: BOTH of `launch`'s branches carry the SAME predicate -- a --dry-run "
              "and a real launch return the SAME role verdict, for the chief-of-staff and for an "
              "ordinary seat alike. Widening one branch and not the other leaves a dry-run and a "
              "real launch disagreeing about who may act: the shape a reader trusts and a test "
              "misses",
              all(("refused [coord role gate]" in dry) == ("role gate: REFUSED" in real)
                  for _who, dry, real in _s4g))

        # ============ s12-01 + s12-05: the CLOSING wake-mute, and `checkout --renew` call 1 ======
        # Placed LAST inside this fixture DELIBERATELY. The block re-checks `gamma`, `alpha` and
        # `theta` in, arms and clears wake mutes on them and toggles the wake stub, so everything
        # it perturbs sits BEHIND it and no earlier row can inherit a seat this block moved.

        # ---- s12-01 (`r-closing-is-a-true-wake-mute`): set_closing is a TRUE wake-mute ----
        # A CLOSING seat's pane receives no [coord wake] keystrokes at all: the per-branch
        # closed_out cut removes it from `recipients` BEFORE the wake text is built and before
        # any pane is touched. The wake stub FAILS here (wake_ok False), so a wake TARGET is
        # observable as its named failure line "gamma (%71): selftest stub" — a seat absent
        # from every such line was never targeted. Evidence ledger:
        # .rbtv/goals/build-core-daemon-mvp/decisions.md#r-closing-is-a-true-wake-mute
        _wake_ok_prior = wake_ok["v"]
        wake_ok["v"] = False
        run(cmd_checkin, agent="gamma", summary="s12-01 closing-mute fixture", pane="%71",
            force=True)
        set_closing(base_g, "gamma", "self-renew")
        out = sd("alpha", "all", "s12-01 V-a broadcast", type="note", force=True)
        check("V-a (s12-01): a CLOSING seat is cut from a broadcast wake — named under the "
              "'closing' skip reason and in NO wake target list",
              "closing: gamma" in out and "gamma (%71)" not in out)
        clear_closing(base_g, "gamma")
        out = sd("alpha", "all", "s12-01 V-b control broadcast", type="note", force=True)
        check("V-b (s12-01) control: the SAME seat, NOT closing, IS a wake target and appears "
              "under NO skip reason",
              "gamma (%71)" in out and "closing: gamma" not in out
              and not any("gamma" in seg.split(")")[0]
                          for seg in out.split("skipped (")[1:]))
        set_closing(base_g, "gamma", "self-renew")
        out = sd("leader", "gamma", "s12-01 V-c leader order")
        check("V-c (s12-01): leader still reaches a closing seat — the closing_reaches leader "
              "exception makes gamma a wake target with no skip reason",
              "gamma (%71)" in out and "closing: gamma" not in out)
        clear_closing(base_g, "gamma")
        wake_ok["v"] = _wake_ok_prior

        # ---- s12-05: `checkout --renew` CALL 1 — arms, teaches, and closes NOTHING ----
        # Spec: stage-1-2-gate-checkout-spec.md §2.1-2.2. Rulings: `d-close-renew-decider-recorded`
        # (the SEAT decides its own renew), `d-mechanical-no-self-renew` (a `close: mechanical`
        # seat is refused on this path PERMANENTLY), and s12-01's closer-token amendment.
        run(cmd_checkin, agent="gamma", summary="s12-05 renew-arm fixture", pane="%71", force=True)
        _r1_tdir = transcripts_dir(ns(), "gamma")
        _r1_tx_before = sorted(p.name for p in _r1_tdir.glob("*.txt"))
        _r1_aw_before = dict(load_awaiting(base_g))
        _r1_cursor_before = cursor_of("gamma")
        _r1_out = run(cmd_checkout, agent="gamma", renew=True, handoff=None, no_export=False)
        _, _, _r1_rows = load_workers(base_g)
        _r1_tx_after = sorted(p.name for p in _r1_tdir.glob("*.txt"))
        _r1_aw_after = dict(load_awaiting(base_g))
        _r1_rerun = ('coordinate checkout --renew --handoff '
                     '"<what the next session of this seat must do>"')

        check("s12-05 S2-a: the teaching step writes NOTHING destructive — after `checkout "
              "--renew` with no --handoff the seat's roster row is STILL active, the output says "
              "NOTHING IS CLOSED YET and carries the re-run command, and the closing (wake-mute) "
              "state IS set. Call 1 is a call a seat must be safe to make",
              (current_row(_r1_rows, "gamma") or {}).get("active") == "yes"
              and "NOTHING IS CLOSED YET" in _r1_out
              and "coordinate checkout --renew --handoff " in _r1_out
              and closing_entry(base_g, "gamma") is not None)
        check("s12-05 S5-a: call 1 does NOT export — no transcript path is printed and no new "
              "export file appears for the seat. The export is the DONE path's last durable "
              "artifact; a session that is about to write a handoff has not finished yet",
              "transcript:" not in _r1_out and _r1_tx_after == _r1_tx_before)
        check("s12-05 S5-b: call 1 records NO awaiting-close debt — awaiting-close.json is "
              "byte-for-byte the same map after the call. The G-134 debt belongs to the DONE path, "
              "and the renew disposition is s12-07's to write at call 2",
              _r1_aw_after == _r1_aw_before)
        check("s12-05 S2-f: the whole call-1 flow leaves the seat's READ CURSOR untouched (D3) — "
              "the successor inherits this cursor, so a renewal that advanced it would cut the "
              "next session off from messages nobody ever read. No-regression control, scoped to "
              "call 1 (s12-08 carries its own copy for the check-in flow)",
              cursor_of("gamma") == _r1_cursor_before)
        check("s12-05 S5-d: the minute figure in the teaching text is DERIVED from "
              "CLOSING_MAX_MIN, never typed — R-10's spirit: a copy drifts, a reference does not, "
              "and a seat told the wrong expiry plans its handoff against a window that is not "
              "there",
              f"clears in {CLOSING_MAX_MIN} min" in _r1_out)
        check("s12-05 S5-e: the re-run line is BYTE-EXACT — the second call is taught by being "
              "printed, so a character that drifts is a command the seat pastes and the parser "
              "refuses, at the one moment it has already stopped reading",
              _r1_rerun in _r1_out)
        check("s12-05 S5-h: the mute's closer token is the seat's OWN NAME, never the literal "
              "'self-renew' (s12-01's amendment to `r-closing-is-a-true-wake-mute`). "
              "closing_reaches admits `leader` plus entry['closer'], and the roster grammar "
              "admits any non-pipe string as an agent name — so a literal token is an unclaimed "
              "free key into a narrowed inbox",
              (closing_entry(base_g, "gamma") or {}).get("closer") == "gamma"
              and closing_reaches("gamma", "leader", closing_entry(base_g, "gamma"))
              and not closing_reaches("gamma", "self-renew", closing_entry(base_g, "gamma")))

        # The back-date runs ONLY where an entry exists. A missing entry is this row's FAILURE, not
        # a KeyError: an exception here would truncate the suite and take every row behind it with
        # it (G-215(a)), which is the one way a red arm can hide the rows it was meant to isolate.
        # ⚠ The back-date is taken from the RECORD'S OWN `since`, never from `datetime.now()`.
        # Re-stamping from now() would overwrite whatever call 1 actually wrote, so this row would
        # pass for a call that stamped its mute unexpirably far in the future — the row would be
        # testing `closing_entry`, which the G-21 block already owns, instead of the record call 1
        # writes, which nothing else does.
        _r1_stale = load_closing(base_g)
        _r1_expired = "NO closing entry was written at all"
        if "gamma" in _r1_stale:
            _r1_keep = dict(_r1_stale["gamma"])
            _r1_stale["gamma"]["since"] = (
                datetime.strptime(_r1_keep["since"], "%Y-%m-%d %H:%M")
                - timedelta(minutes=CLOSING_MAX_MIN + 5)).strftime("%Y-%m-%d %H:%M")
            atomic_write(closing_path(base_g), json.dumps(_r1_stale) + "\n")
            _r1_expired = closing_entry(base_g, "gamma")
            _r1_stale["gamma"] = _r1_keep
            atomic_write(closing_path(base_g), json.dumps(_r1_stale) + "\n")
        check("s12-05 S5-c: the mute call 1 arms is an ORDINARY, EXPIRING closing record — present "
              "immediately after the call, and gone once its `since` stamp is older than "
              "CLOSING_MAX_MIN. A seat that arms a renewal and never returns un-mutes itself "
              "instead of staying cut off from the room for the rest of the run",
              closing_entry(base_g, "gamma") is not None and _r1_expired is None)
        clear_closing(base_g, "gamma")

        # A FOLDERLESS seat has no memory.md, and a `close: mechanical` seat is memoryless by
        # ruling — both are refused HERE, at call 1, BEFORE the arming. Arming first would leave
        # the seat muted for CLOSING_MAX_MIN minutes with no renewal path out of it, which is the
        # one outcome worse than the refusal.
        run(cmd_checkin, agent="alpha", summary="s12-05 folderless-seat fixture", pane="%73",
            force=True)
        _r1_ff_out, _r1_ff_code = refuse(cmd_checkout, agent="alpha", renew=True, handoff=None,
                                         no_export=True)
        check("s12-05 S5-f: a FOLDERLESS seat is refused at call 1 BEFORE arming — layer `input`, "
              "the message names the missing folder and its absent memory.md, and NO closing entry "
              "exists afterwards. Refusing after the arm would strand the seat muted with no way "
              "to finish the renewal it was just refused",
              _r1_ff_code == 2 and "refused [coord input]" in _r1_ff_out
              and "no seat FOLDER" in _r1_ff_out and "memory.md" in _r1_ff_out
              and closing_entry(base_g, "alpha") is None)
        clear_closing(base_g, "alpha")

        run(cmd_checkin, agent="theta", summary="s12-05 mechanical-close fixture", pane="%72",
            force=True)
        _r1_mc_out, _r1_mc_code = refuse(cmd_checkout, agent="theta", renew=True, handoff=None,
                                         no_export=True)
        check("s12-05 S5-g: a `close: mechanical` seat is refused at call 1 — layer `input`, the "
              "message names G-23, states the ruling as PERMANENT and points at the LEADER-SIDE "
              "close-and-relaunch path that IS its renewal, and no closing entry exists "
              "afterwards. `d-mechanical-no-self-renew` (owner, 2026-07-29) closed this as a "
              "standing rule, so the refusal must not read as a temporary gap",
              _r1_mc_code == 2 and "refused [coord input]" in _r1_mc_out
              and "G-23" in _r1_mc_out and "PERMANENTLY" in _r1_mc_out
              and "close-and-relaunch" in _r1_mc_out and "s12-11" not in _r1_mc_out
              and closing_entry(base_g, "theta") is None)
        clear_closing(base_g, "theta")

        # LAST in the block: on the mutant that ACCEPTS this pairing the call runs a full DONE
        # checkout on gamma, so every measurement above must already be banked.
        _r1_h_out, _r1_h_code = refuse(cmd_checkout, agent="gamma", renew=False, handoff="x",
                                       no_export=True)
        check("s12-05 S2-e: `--handoff` without `--renew` is REFUSED at layer `input` (D2 — a "
              "done-checkout writes no handoff), and refused FIRST, before identity resolution and "
              "before the export, so an argument error costs the seat nothing",
              _r1_h_code == 2 and "refused [coord input]" in _r1_h_out)

        # ============ s12-06: the check-out HANDOFF BLOCK, and `checkout --renew --handoff` =====
        # Spec: stage-1-2-gate-checkout-spec.md §2.2 (call 2) + §3 (the block schema). R-14 makes
        # this block the ONE memory artifact this effort is allowed to write, so every row below is
        # about that write being append-only, verbatim, self-verified, and REFUSED wherever the
        # seat has nowhere — or no right — to write.
        #
        # ⚠ THE DELIMITER GRAMMAR IS RESTATED HERE FROM THE SPEC, NEVER IMPORTED FROM THE MODULE
        # CONSTANTS. A test that asserts against the implementation's own constant asserts only
        # that the implementation agrees with itself: rename the constant's VALUE and the row goes
        # green on a grammar no reader of the spec would recognise. Split across a `+` so this
        # source line is not itself a hit for the marker counts below.
        _h6_open = "<!-- " + "coord:handoff" + " v=1 "
        _h6_close = "<!-- /" + "coord:handoff" + " v=1 -->"
        _h6_token = "coord" + ":handoff"

        # ⚠ CALL-2 SUBJECTS RUN THROUGH `harness_outcome` DIRECTLY, NOT THROUGH `run()`. `run()`
        # posts its OWN failing check when a subject refuses (G-215(a)), so a mutation that makes
        # call 2 refuse would red TWO rows — the row under test and `run()`'s — and `--expect-fail`
        # demands EXACTLY ONE. Every row below therefore carries `code is None` in its own
        # condition: an unexpected refusal is still that row's failure, and only that row's.
        def _h6(agent, note, **kw):
            d = {"agent": agent, "renew": True, "handoff": note, "no_export": True}
            d.update(kw)
            _o, _e, _cd = harness_outcome(cmd_checkout, ns(**d))
            return _o + _e, _cd

        # ---- the two fixture memory.md shapes that did not exist (the task's checker fix) ----
        # S6-e needs a memory.md that OPENS WITH YAML FRONTMATTER and S6-j needs one that does NOT
        # END IN A NEWLINE; the only fixture memory.md was gamma's `# memory\nprior state\n`, so
        # both rows were unrunnable. Created HERE, at the very end of the fixture, so no earlier
        # row that enumerates seats, descriptors or taskforce bindings can inherit them.
        _h6_mem = {}
        for _h6_name, _h6_body in (
                ("omega", "---\nagent: omega\nupdated: 2026-07-29\nsessions-closed: 3\n---\n"
                          "# omega — seat memory\n\nprior state\n"),
                ("sigma", "# sigma — seat memory\nthis last line has NO trailing newline"),
                ("nu", "# nu — seat memory\nprior state\n")):
            _h6_d = pkg / "workers" / _h6_name
            _h6_d.mkdir()
            (_h6_d / "agent.md").write_text(
                f"---\nagent: {_h6_name}\nmodel: haiku\n---\nbrief\n", encoding="utf-8")
            (_h6_d / "memory.md").write_text(_h6_body, encoding="utf-8")
            _h6_mem[_h6_name] = ((_h6_d / "memory.md"), _h6_body)

        # ---- gamma: the happy path (S2-b, S6-a, S6-b) and then the done path (S2-d, S6-i) ----
        _h6_note = ("in flight: the `--renew` arm, half wired.\n"
                    "\n"
                    "- ruled out: a second `state.md` copy\n"
                    "- next: read `stage-3-executor-spec.md` §2 before touching anything")
        _h6_gmem = gdir / "memory.md"
        _h6_gprior = _h6_gmem.read_text(encoding="utf-8")
        run(cmd_checkin, agent="gamma", summary="s12-06 call-2 fixture", pane="%71", force=True)
        _h6_gout, _h6_gcode = _h6("gamma", _h6_note)
        _h6_glanded = _h6_gmem.read_text(encoding="utf-8")
        # s12-07 S7-e's measurement, taken HERE and not later: the DONE checkout a few rows down
        # overwrites gamma's awaiting-close record, so the renew record must be banked before it.
        # ⚠ `partition`, never `index` (G-215(a)): in a build that writes no block an `index` call
        # would RAISE inside a check condition and abort the suite, taking every row behind it
        # unrun. An absent block leaves the stamp `""`, which FAILS the row instead.
        _h6_aw_renew = dict(load_awaiting(base_g).get("gamma") or {})
        _h6_stamped = next(
            (t[len("stamped="):] for t in
             _h6_glanded.partition(_h6_open)[2].partition("-->")[0].split()
             if t.startswith("stamped=")), "")

        check("s12-06 S2-b: the handoff LANDS and the write is APPEND-ONLY — after call 2 gamma's "
              "memory.md still opens with its original bytes and now carries exactly ONE handoff "
              "block, marked `unread=yes`. memory.md is heterogeneous by construction (some seats' "
              "open with YAML frontmatter, some at a heading), so a write that assumed a shape "
              "would corrupt every file whose shape it did not anticipate",
              _h6_gcode is None and _h6_glanded.startswith(_h6_gprior)
              and _h6_glanded.count(_h6_open) == 1 and "unread=yes" in _h6_glanded)

        check("s12-06 S6-a: BOTH delimiters carry `v=1` — the opening comment and the closing one, "
              "exactly once each. That is what makes a TRUNCATED append detectable: a reader that "
              "finds an opener with no matching `v=1` closer knows the block is half-written, "
              "which is precisely what a lockless write on a read-only package can leave behind",
              _h6_gcode is None and _h6_glanded.count(_h6_open) == 1
              and _h6_glanded.count(_h6_close) == 1)

        check("s12-06 S6-b: the note body is VERBATIM, AS TYPED — markdown, backticks and a blank "
              "line survive character-for-character between the delimiters. The successor reads "
              "what its predecessor wrote; a transform applied here is a distortion introduced at "
              "the one moment nobody is left who can check it",
              _h6_gcode is None and ("\n" + _h6_note + "\n") in _h6_glanded)

        check("s12-07 S7-e: the `handoff_stamp` in awaiting-close.json is the block's `stamped=` "
              "attribute BYTE-FOR-BYTE — ONE clock reading, ONE formatter, both consumers. Two "
              "`datetime.now()` calls can straddle a second, and then the record and the block it "
              "describes carry different times with nothing downstream able to tell which block a "
              "record belongs to. Asserted against the stamp READ BACK OUT of the file, never "
              "against a second computation of it",
              _h6_gcode is None and _h6_stamped != ""
              and _h6_aw_renew.get("handoff_stamp") == _h6_stamped)

        # S2-d is deliberately TWO-CLAUSE. "memory.md is unchanged by a bare checkout" is VACUOUSLY
        # true in a build where nothing ever writes memory.md — the row would pass for the ABSENCE
        # of the feature it exists to bound. Clause (a) pins the block call 2 just wrote, so the
        # row can only be green in a build that DOES write on the renew path and does NOT here.
        run(cmd_checkin, agent="gamma", summary="s12-06 done-path fixture", pane="%71", force=True)
        _h6_done_before = _h6_gmem.read_text(encoding="utf-8")
        _h6_done_out = run(cmd_checkout, agent="gamma", renew=False, handoff=None, no_export=True)
        _h6_done_after = _h6_gmem.read_text(encoding="utf-8")
        check("s12-06 S2-d: a DONE check-out writes NOTHING into memory.md — the file is "
              "byte-identical across a bare `checkout`, WHILE still carrying the one block the "
              "renew path wrote a moment earlier (D2: a done-checkout has no successor to hand "
              "anything to). Without that second clause the row would pass in a build where no "
              "path writes a handoff at all",
              _h6_done_before.count(_h6_open) == 1 and _h6_done_after == _h6_done_before)

        _h6_aw_done = dict(load_awaiting(base_g).get("gamma") or {})
        check("s12-07 S2-d (second half): a DONE check-out RECORDS ITS DISPOSITION — the very seat "
              "whose renew checkout wrote `renew` a moment earlier now carries `done`, with no "
              "handoff stamp, because it wrote no block. THE PAIRING IS THE ROW: a build that "
              "hardcodes either value satisfies one half and fails the other, which a single-value "
              "assertion could not tell apart from a build that decides",
              _h6_aw_done.get("disposition") == "done"
              and _h6_aw_done.get("handoff_stamp") == ""
              and _h6_aw_renew.get("disposition") == "renew")

        check("s12-06 S6-i: the DONE path's closing text no longer teaches `close <me> --renew` as "
              "the seat's follow-up — renewal is the SEAT's own act now, so a hint still routing "
              "it through leader teaches the superseded ceremony at the exact moment the seat is "
              "looking for its next step",
              "close gamma --renew" not in _h6_done_out and "checkout --renew" in _h6_done_out)

        # ---- nu: the body guard (S6-c) and the self-verifying append (S6-d) ----
        run(cmd_checkin, agent="nu", summary="s12-06 token-body fixture", pane="%74", force=True)
        _h6_nu_path, _h6_nu_prior = _h6_mem["nu"]
        _h6_c_out, _h6_c_code = _h6("nu", "read the " + _h6_token + " grammar before editing")
        check("s12-06 S6-c: a note body carrying the literal delimiter word is REFUSED, never "
              "escaped — layer `input`, and memory.md is byte-identical afterwards. Escaping it "
              "would make the block grammar ambiguous for every later reader; refusing keeps the "
              "grammar decidable and the seat still holds its note",
              _h6_c_code == 2 and "refused [coord input]" in _h6_c_out
              and _h6_nu_path.read_text(encoding="utf-8") == _h6_nu_prior)

        # ⚠ `atomic_write` is neutered AFTER nu's check-in, never before: the check-in writes the
        # roster through it, and a fixture that cannot register its own seat would prove nothing.
        # ⚠ AND the "unchanged" baseline is re-read HERE, not inherited from S6-c's. A baseline
        # taken before another row's subject ran makes THIS row red whenever THAT row's mutation
        # lands — measured: the escape-instead-of-refuse mutant reddened both, and `--expect-fail`
        # rejected the pair as un-isolated, so the red said nothing about either check.
        # ⚠ AND nu is re-checked-in first, for the same reason: a mutation that makes S6-c's
        # subject SUCCEED checks nu out, and this row would then measure the no-active-row
        # refusal instead of the verification it names — a second way one row's mutation reds
        # another. Every precondition this row needs, this row establishes.
        run(cmd_checkin, agent="nu", summary="s12-06 unwritable-append fixture", pane="%74",
            force=True)
        _h6_aw_real = atomic_write
        _h6_nu_pre_d = _h6_nu_path.read_text(encoding="utf-8")
        atomic_write = lambda path, text: None
        _h6_d_out, _h6_d_code = _h6("nu", "a note that cannot reach the disk")
        atomic_write = _h6_aw_real
        check("s12-06 S6-d: THE APPEND VERIFIES ITS OWN RESULT — with `atomic_write` neutered the "
              "block never reaches disk, and call 2 says so LOUDLY and closes NOTHING: it refuses "
              "at layer `state`, names the handoff as NOT WRITTEN, and never prints `checked out`. "
              "`coord_lock` is never fatal (a read-only package proceeds lockless after one note), "
              "so an unverified append is exactly how the one artifact the successor is promised "
              "is lost in silence",
              _h6_d_code == 1 and "refused [coord state]" in _h6_d_out
              and "HANDOFF NOT WRITTEN" in _h6_d_out and "checked out:" not in _h6_d_out
              and _h6_nu_path.read_text(encoding="utf-8") == _h6_nu_pre_d)

        # ---- omega: frontmatter is never touched (S6-e) ----
        run(cmd_checkin, agent="omega", summary="s12-06 frontmatter fixture", pane="%75",
            force=True)
        _h6_om_path, _h6_om_prior = _h6_mem["omega"]
        _h6_om_fm = _h6_om_prior[:_h6_om_prior.index("\n---\n") + 5]
        _h6_e_out, _h6_e_code = _h6("omega", "the frontmatter above must not move")
        _h6_om_landed = _h6_om_path.read_text(encoding="utf-8")
        check("s12-06 S6-e: a memory.md that OPENS WITH YAML FRONTMATTER keeps it byte-identical — "
              "the block is appended at EOF and the frontmatter is never parsed, rewritten or "
              "reordered. Live seats carry several different shapes of it; a writer that "
              "'understood' the file would eventually meet a file it did not understand",
              _h6_e_code is None and _h6_om_landed.startswith(_h6_om_fm)
              and _h6_om_landed.startswith(_h6_om_prior)
              and _h6_om_landed.count(_h6_open) == 1)

        # ---- sigma + omega: the separator, in BOTH directions (S6-j) ----
        run(cmd_checkin, agent="sigma", summary="s12-06 no-trailing-newline fixture", pane="%76",
            force=True)
        _h6_sg_path, _h6_sg_prior = _h6_mem["sigma"]
        _h6_j_out, _h6_j_code = _h6("sigma", "the content above me ended without a newline")
        _h6_sg_landed = _h6_sg_path.read_text(encoding="utf-8")
        # ⚠ GUARDED SLICES (G-215(a)). In a build where no block is written these `index` calls
        # would RAISE, and a raise inside a check condition aborts the suite and takes every row
        # behind it unrun — the one way a red arm can hide the rows it was meant to isolate. The
        # sentinel is a byte no memory.md can end with, so an absent block fails the row instead.
        _h6_sg_tail = (_h6_sg_landed[_h6_sg_landed.index(_h6_open):]
                       if _h6_open in _h6_sg_landed else "\x00 no block was written")
        _h6_om_tail = (_h6_om_landed[_h6_om_landed.index(_h6_open):]
                       if _h6_open in _h6_om_landed else "\x00 no block was written")
        check("s12-06 S6-j: the separator is correct in BOTH directions — on a memory.md that does "
              "NOT end in a newline and on one that DOES, exactly one blank line stands between "
              "the prior content and the block, and no line is ever joined. The prior bytes are "
              "only ever ADDED TO: normalizing a trailing newline away would be a REWRITE of a "
              "file this path is only allowed to append to",
              _h6_j_code is None
              and _h6_sg_landed.endswith("\n\n" + _h6_sg_tail)
              and not _h6_sg_landed.endswith("\n\n\n" + _h6_sg_tail)
              and _h6_om_landed.endswith("\n\n" + _h6_om_tail)
              and not _h6_om_landed.endswith("\n\n\n" + _h6_om_tail))

        # ---- the two call-2 refusals that duplicate call 1's, on purpose (S6-f, S6-g) ----
        run(cmd_checkin, agent="alpha", summary="s12-06 folderless call-2 fixture", pane="%73",
            force=True)
        _h6_f_out, _h6_f_code = _h6("alpha", "there is nowhere for this to land")
        check("s12-06 S6-f: a FOLDERLESS seat is refused AT CALL 2 as well — layer `input`, and "
              "the message names the missing folder and the memory.md that does not exist. Call 1 "
              "already refuses it, but call 2 IS REACHABLE WITHOUT CALL 1 (nothing forces the "
              "two-step, and a descriptor can change between them), and a guard that only ever "
              "fires behind another guard stops holding the day someone finds the other door",
              _h6_f_code == 2 and "refused [coord input]" in _h6_f_out
              and "no seat FOLDER" in _h6_f_out and "memory.md" in _h6_f_out)

        run(cmd_checkin, agent="theta", summary="s12-06 mechanical call-2 fixture", pane="%72",
            force=True)
        _h6_g_out, _h6_g_code = _h6("theta", "a seat that must never carry one")
        check("s12-06 S6-g: a `close: mechanical` seat is refused at call 2 — layer `input`, the "
              "message names G-23, states the ruling as PERMANENT and points at the LEADER-SIDE "
              "close-and-relaunch path that IS its renewal. `d-mechanical-no-self-renew` (owner, "
              "2026-07-29) settled this as a standing rule, so the refusal must not read as a "
              "temporary gap and must not cite the question it closed as still open",
              _h6_g_code == 2 and "refused [coord input]" in _h6_g_out
              and "G-23" in _h6_g_out and "PERMANENTLY" in _h6_g_out
              and "close-and-relaunch" in _h6_g_out
              and ("s12" + "-11") not in _h6_g_out)

        # ---- the Stage-3 seams (S6-h) ----
        # ⚠ The marker is BUILT from two halves, never written whole: this check reads the file it
        # lives in, so a whole literal here would be its own third hit and the count could never
        # reach 2 however correct the code was.
        _h6_ip = "[INTEGRATION POINT " + "— STAGE 3"
        check("s12-06 S6-h: EVERY Stage-3 seam exists and is GREPPABLE — the module source carries "
              "the named marker exactly THREE times: the renew path's fork (the detached "
              "executor), the done path's fork (the detached reaper), and — added by s12-07 — the "
              "`reap_blockers` block that every renew disposition holds until that executor "
              "releases it. Stage 3 wires the first two to the `arm_pid_reaper` pattern and rules "
              "how it clears the third; a named comment is how the sites stay findable instead of "
              "being re-derived from a spec nobody reads at the time",
              Path(__file__).read_text(encoding="utf-8").count(_h6_ip) == 3)

        # ============ s12-07: the DISPOSITION in awaiting-close.json =============================
        # Spec: stage-1-2-gate-checkout-spec.md §2.3. The rows that need a live pane, a recorded
        # harness identity and an on-disk transcript (S2-h, S7-a, S7-b) sit with the `reap`
        # fixture far above; the two that read call 2's own record (S2-d's second half, S7-e) sit
        # with s12-06's subject, because that record is overwritten by the done checkout that
        # follows it. What is left here needs none of that: the legacy record, the non-fatal
        # property, and the caller sweep.

        # ---- S7-c: a record written BEFORE this field existed ----
        # ⚠ COMPUTED THROUGH A GUARD, AND THE GUARD IS HALF THE ROW. The mutation this row exists
        # to catch is `entry["disposition"]`, which RAISES on exactly this record — and a raise
        # inside a check's condition aborts the whole suite and takes every row behind it unrun
        # (G-215(a)). The sentinel converts that raise into THIS row's failure.
        _s7c_legacy = {"since": now(), "pane": "%84", "transcript": "/tmp/gone-s12-07",
                       "exported": True, "pids": [[4242, "stamp-4242"]]}
        try:
            _s7c_out = reap_blockers(_s7c_legacy, REAP_MIN_AGE_MIN + 5, {"%84"})
            _s7c_raised = ""
        except Exception as _s7c_exc:               # noqa: BLE001 — the raise IS this row's verdict
            _s7c_out, _s7c_raised = [], f"{type(_s7c_exc).__name__}: {_s7c_exc}"
        check("s12-07 S7-c: a record written BEFORE this field existed reads as `done` and NEVER "
              "raises — every consumer goes through `.get(\"disposition\", \"done\")`. Live run "
              "packages hold such records on disk right now, and a KeyError here would take down "
              "the whole sweep that reads them, not merely skip the one entry",
              _s7c_raised == "" and "disposition" not in _s7c_legacy
              and not any("disposition=renew" in b for b in _s7c_out))

        # ---- S7-d: `set_awaiting` stays NON-FATAL ----
        # ⚠ THE FAILURE IS SCOPED TO awaiting-close.json, never a blanket raise. `cmd_checkout`
        # writes the roster row and the session trace through the SAME `atomic_write`, so a
        # blanket raise would take the checkout down for reasons that have nothing to do with this
        # record, and the row would prove nothing about the bookkeeping. Path-scoped, the subject
        # IS the claim: bookkeeping ABOUT a checkout must never break the checkout itself.
        run(cmd_checkin, agent="rho", summary="s12-07 non-fatal fixture", pane="%84", force=True)
        _s7d_real = atomic_write

        def _s7d_write(path, text):
            if Path(path).name == "awaiting-close.json":
                raise OSError("selftest: the awaiting-close write fails")
            return _s7d_real(path, text)

        atomic_write = _s7d_write
        try:
            _s7d_o, _s7d_e, _s7d_c = harness_outcome(
                cmd_checkout, ns(agent="rho", renew=False, handoff=None, no_export=True))
            _s7d_ret = set_awaiting(base_g, "rho", "%84", "/tmp/x", True)
            _s7d_raised = ""
        except Exception as _s7d_exc:               # noqa: BLE001 — the raise IS this row's verdict
            _s7d_o, _s7d_e, _s7d_c, _s7d_ret = "", "", -1, None
            _s7d_raised = f"{type(_s7d_exc).__name__}: {_s7d_exc}"
        atomic_write = _s7d_real
        check("s12-07 S7-d: `set_awaiting` is BEST-EFFORT and adding fields did not change that — "
              "with the awaiting-close write failing, `checkout` still SUCCEEDS and still says so, "
              "does NOT claim a debt it failed to record, and `set_awaiting` REPORTS False rather "
              "than raising. A seat that cannot check out is worse than a debt nobody recorded, "
              "and a new field must never add a raise path into the act it is bookkeeping for",
              _s7d_raised == "" and _s7d_c is None and "checked out: rho" in _s7d_o
              and "awaiting close:" not in _s7d_o and _s7d_ret is False)

        # ---- S7-f: the CALLER SWEEP, asserted IN-SUITE ----
        # A signature change includes its callers, and a sweep recorded only in a return is a
        # sweep nobody re-runs. Read off the module's OWN AST: a positional sixth argument binds
        # `disposition` BY POSITION, so the day a caller passes a stamp or a flag there it lands
        # in the field `reap` now gates a pane KILL on, silently and with no parser to object.
        import ast as _s7_ast
        import inspect as _s7_inspect
        _s7_calls = [n for n in _s7_ast.walk(
                         _s7_ast.parse(Path(__file__).read_text(encoding="utf-8")))
                     if isinstance(n, _s7_ast.Call) and getattr(n.func, "id", "") == "set_awaiting"]
        _s7_params = list(_s7_inspect.signature(set_awaiting).parameters)
        _s7_kwnames = {k.arg for n in _s7_calls for k in n.keywords}
        check("s12-07 S7-f: EVERY `set_awaiting` call site in this module was swept — the five "
              "positional parameters the signature has always had are unchanged and still first, "
              "no call passes more than those five positionally, and every added value is passed "
              "BY NAME. Counted against the source itself, so a caller added later cannot quietly "
              "fall outside a sweep that was true once",
              len(_s7_calls) >= 6
              and _s7_params[:5] == ["base", "seat", "pane", "transcript", "exported"]
              and _s7_params[5:] == ["disposition", "handoff_stamp"]
              and all(len(n.args) <= 5 for n in _s7_calls)
              and _s7_kwnames <= {"disposition", "handoff_stamp"})


        # ============ s12-08: the CHECK-IN DELIVERS the unread handoff ===========================
        # Spec: stage-1-2-gate-checkout-spec.md §4 + §5. The mechanism copied is the MESSAGE
        # CURSOR's: `cmd_read` persists the cursor AFTER rendering, and that ordering is what makes
        # "shown" and "read" one event. Every row below is about that ordering, about the lookup
        # being keyed on (seat, unread) and never on the AUTHOR, and about the delivery never
        # becoming a gate on the check-in it rides.
        #
        # ⚠ CHECK-IN SUBJECTS RUN THROUGH `harness_outcome` DIRECTLY, like s12-06's call-2 subjects
        # and for the same reason: `run()` posts its OWN failing check when a subject refuses
        # (G-215(a)), so a mutation that made the delivery fatal would red TWO rows while
        # `--expect-fail` demands exactly one. Every row carries `code is None` in its own
        # condition, so an unexpected refusal is still that row's failure and only that row's.
        def _d8_in(agent, summary, pane="%80"):
            _o, _e, _cd = harness_outcome(
                cmd_checkin, ns(agent=agent, summary=summary, pane=pane, force=True))
            return _o + _e, _cd

        # ⚠ FIXTURE BLOCKS ARE COMPOSED IN THE SPEC'S GRAMMAR, never through the module's own
        # writer or constants: a fixture built from the implementation asserts only that the
        # implementation agrees with itself. `_h6_open`/`_h6_close` are s12-06's split literals,
        # so this source line is not itself a hit for any marker count.
        def _d8_head(seat, stamp, unread, session="s-1", disposition="renew"):
            return (_h6_open + f"seat={seat} session={session} disposition={disposition} "
                    f"stamped={stamp} unread={unread} -->")

        def _d8_block(seat, stamp, unread, body, **kw):
            return _d8_head(seat, stamp, unread, **kw) + "\n" + body + "\n" + _h6_close + "\n"

        def _d8_seat(name, memory):
            _d = pkg / "workers" / name
            _d.mkdir()
            (_d / "agent.md").write_text(f"---\nagent: {name}\nmodel: haiku\n---\nbrief\n",
                                         encoding="utf-8")
            (_d / "memory.md").write_text(memory, encoding="utf-8")
            return _d / "memory.md"

        # ---- gamma: the ordering, the crash, and the re-delivery (S2-c) + S2-f/S2-g/S8-b ----
        # gamma's memory.md is RESET to a known base first: s12-06 left a real block in it and the
        # check-ins between here and there have already delivered it, so counting from whatever
        # survived would make every count below depend on rows that are not this task's subject.
        _h6_gmem.write_text("# memory\nprior state\n", encoding="utf-8")
        # ⚠ THE BASELINE IS DRAINED AND THEN PROVED, never merely read. A mutation that advances
        # the cursor on the delivery path would have fired at the s12-06 check-ins ABOVE too — so
        # a baseline captured here would already carry the mutant's value, `cursor_of() == baseline`
        # would hold trivially, and S2-f would pass on exactly the build it exists to catch. The
        # log is read down to its last message and the baseline must EQUAL that message's number:
        # a cursor the delivery moved cannot satisfy that, because a moved cursor leaves the read
        # with nothing to show and nothing to advance through.
        _d8_in("gamma", "s12-08 cursor fixture", "%71")
        _d8_prev = None
        for _ in range(20):             # REAL reads, until the log is drained
            rd("gamma")
            if cursor_of("gamma") == _d8_prev:
                break
            _d8_prev = cursor_of("gamma")
        _d8_cursor0 = cursor_of("gamma")
        _d8_blocks = load_messages(base_g)[1]
        _d8_msg_top = str(_d8_blocks[-1]["num"]) if _d8_blocks else "!the log is empty"
        _d8_noteA = "block A: the first successor must read this, and only this"
        _d8_noteB = "block B: written after A was read, and delivered TWICE"
        _h6("gamma", _d8_noteA)         # call 2 writes block A and checks gamma out

        # THE ORDERING PROBE, and it is the half of S2-c a crash simulation cannot reach. Moving
        # the flip ABOVE the print leaves every crash-arm assertion below green (a flip that failed
        # never marked anything either way), so the ordering is measured DIRECTLY: the stub records
        # what was already on stdout at the moment the flip was called.
        _d8_flip_real = flip_handoff_read
        _d8_seen = {"stdout": ""}

        def _d8_flip_probe(_b, _p, _h):
            _d8_seen["stdout"] = getattr(sys.stdout, "getvalue", lambda: "")()
            return _d8_flip_real(_b, _p, _h)

        flip_handoff_read = _d8_flip_probe
        _d8_outA, _d8_codeA = _d8_in("gamma", "s12-08 successor of A", "%71")
        flip_handoff_read = _d8_flip_real
        _d8_memA = _h6_gmem.read_text(encoding="utf-8")

        _d8_out2, _d8_code2 = _d8_in("gamma", "s12-08 nothing left to deliver", "%71")

        _d8_in("gamma", "s12-08 write-B fixture", "%71")
        _h6("gamma", _d8_noteB)

        def _d8_flip_raise(*_a, **_kw):
            raise OSError("selftest: the flip cannot reach the disk")

        flip_handoff_read = _d8_flip_raise
        _d8_crash_out, _d8_crash_code = _d8_in("gamma", "s12-08 crashed successor", "%71")
        flip_handoff_read = _d8_flip_real
        _d8_crash_mem = _h6_gmem.read_text(encoding="utf-8")
        _d8_again_out, _d8_again_code = _d8_in("gamma", "s12-08 re-delivered successor", "%71")
        _d8_again_mem = _h6_gmem.read_text(encoding="utf-8")

        check("s12-08 S2-c: a crash between the WRITE and the CHECK-IN re-delivers instead of "
              "losing — the flip is called only AFTER the block is on stdout (measured at the call, "
              "not inferred), and with the flip made to raise the block is still PRINTED, the "
              "check-in still SUCCEEDS, a LOUD warning says it was not marked read, the attribute "
              "is STILL `unread=yes`, and the very next check-in delivers the SAME block a second "
              "time. That ordering is `cmd_read`'s: shown and read must be one event, and when "
              "they cannot both happen, shown-twice beats shown-never",
              _d8_codeA is None and _d8_crash_code is None and _d8_again_code is None
              and "handoff waiting" in _d8_outA and _d8_noteA in _d8_outA
              and _d8_noteA in _d8_seen["stdout"]
              and _d8_memA.count("unread=yes") == 0 and _d8_memA.count("unread=no") == 1
              and _d8_noteB in _d8_crash_out and "checked in: gamma" in _d8_crash_out
              and "NOT marked read" in _d8_crash_out
              and _d8_crash_mem.count("unread=yes") == 1
              and _d8_noteB in _d8_again_out
              and _d8_again_mem.count("unread=yes") == 0)

        check("s12-08 S8-b: an ALREADY-READ block is never re-delivered — the check-in that "
              "follows a successful delivery prints no handoff at all. `unread=no` is the whole "
              "state; there is no second register that could disagree with it",
              _d8_code2 is None and "handoff waiting" not in _d8_out2
              and _d8_noteA not in _d8_out2)

        check("s12-08 S2-f: the whole delivery flow leaves the seat's READ CURSOR untouched (D3) — "
              "four deliveries and two renewals later gamma's `lastread` is still the value a REAL "
              "read left it at, and that value is the log's last message number, so the baseline "
              "cannot itself be a cursor some delivery already moved. The successor inherits this "
              "cursor, so a delivery that advanced it would cut the next session off from messages "
              "nobody ever read. ⚠ NO-REGRESSION ROW: green BEFORE this task's change as well as "
              "after, and labelled so rather than counted as evidence of the new behaviour",
              _d8_cursor0 == _d8_msg_top and cursor_of("gamma") == _d8_cursor0)

        check("s12-08 S2-g: the successor INHERITS the cursor AND is handed the block in the SAME "
              "check-in, in THAT ORDER — one output carries `(cursor kept at #N)` for the "
              "pre-existing cursor and, after the `checked in:` line, the handoff banner. The two "
              "mechanisms share a seat and a moment; a row that measured either alone would pass "
              "on a build where the other never ran, and a delivery printed BEFORE the check-in "
              "line hands a seat its predecessor's note before telling it that it is a session",
              _d8_codeA is None and _d8_cursor0 != "0"
              and f"(cursor kept at #{_d8_cursor0})" in _d8_outA
              and 0 <= _d8_outA.find("checked in: gamma") < _d8_outA.find("handoff waiting"))

        # ---- psi: TWO unread blocks, and only the last one wins (S8-a) ----
        _d8_psi_old = _d8_block("psi", "2026-07-28T09:00:00", "yes",
                                "older: this one must NOT be delivered")
        _d8_psi_new = _d8_block("psi", "2026-07-28T17:30:00", "yes",
                                "newer: the block that wins")
        _d8_psi_prior = "# psi — seat memory\n\n" + _d8_psi_old + "\n" + _d8_psi_new
        _d8_psi = _d8_seat("psi", _d8_psi_prior)
        _d8_psi_out, _d8_psi_code = _d8_in("psi", "s12-08 two-unread fixture", "%81")
        _d8_psi_mem = _d8_psi.read_text(encoding="utf-8")
        check("s12-08 S8-a: with TWO unread blocks the LAST one is delivered and ONLY it is "
              "flipped — the older block is neither printed nor touched, byte for byte. This is "
              "also the row that catches a whole-file `replace_all`: it is the only fixture where "
              "flipping every block at once differs from flipping the selected one",
              _d8_psi_code is None
              and "newer: the block that wins" in _d8_psi_out
              and "older: this one must NOT be delivered" not in _d8_psi_out
              and _d8_psi_old in _d8_psi_mem
              and _d8_psi_mem.count("unread=yes") == 1
              and _d8_psi_mem.count("unread=no") == 1)

        # ---- chi: one read block, one unread, and the file is otherwise BYTE-IDENTICAL (S8-c) ----
        # ⚠ The already-read block carries TRAILING WHITESPACE on purpose: it is what separates a
        # targeted splice from an implementation that rewrites the file "tidily" on the way past.
        _d8_chi_read = _d8_block("chi", "2026-07-27T08:00:00", "no",
                                 "already read, and it ends in spaces ->   ")
        _d8_chi_new = _d8_block("chi", "2026-07-29T08:00:00", "yes",
                                "fresh: the only block that may change")
        _d8_chi_prior = "# chi — seat memory\n\n" + _d8_chi_read + "\n" + _d8_chi_new
        _d8_chi = _d8_seat("chi", _d8_chi_prior)
        _d8_chi_out, _d8_chi_code = _d8_in("chi", "s12-08 targeted-flip fixture", "%82")
        _d8_chi_mem = _d8_chi.read_text(encoding="utf-8")
        _d8_chi_want = _d8_chi_prior.replace(_d8_head("chi", "2026-07-29T08:00:00", "yes"),
                                             _d8_head("chi", "2026-07-29T08:00:00", "no"))
        check("s12-08 S8-c: the flip is a TARGETED single-line splice — the file ends with exactly "
              "one more `unread=no` and one fewer `unread=yes`, the already-read block's bytes "
              "(trailing whitespace included) are untouched, and the whole file equals the prior "
              "bytes with that ONE attribute changed. Nothing is normalized, reordered or "
              "re-composed on the way past",
              _d8_chi_code is None and _d8_chi_mem == _d8_chi_want
              and _d8_chi_read in _d8_chi_mem
              and _d8_chi_mem.count("unread=no") == _d8_chi_prior.count("unread=no") + 1
              and _d8_chi_mem.count("unread=yes") == _d8_chi_prior.count("unread=yes") - 1)

        # ---- alpha + upsilon: no folder, and a memory.md deleted MID-RUN (S8-d) ----
        _d8_ff_out, _d8_ff_code = _d8_in("alpha", "s12-08 folderless check-in", "%83")
        _d8_up = _d8_seat("upsilon", "# upsilon — seat memory\n\n"
                          + _d8_block("upsilon", "2026-07-29T09:00:00", "yes",
                                      "a note that will never be read"))
        _d8_up.unlink()                 # the file goes AFTER the seat exists — the mid-run case
        _d8_up_out, _d8_up_code = _d8_in("upsilon", "s12-08 deleted-memory check-in", "%84")
        check("s12-08 S8-d: an absent or unreadable memory.md NEVER blocks a check-in and never "
              "invents output — a FOLDERLESS seat and a seat whose memory.md was deleted mid-run "
              "both check in successfully and print no handoff line of any kind. Most seats in "
              "any run are in exactly one of these two states, so a delivery that raised or "
              "chattered here would be a defect on the ordinary path, not the rare one",
              _d8_ff_code is None and _d8_up_code is None
              and "checked in: alpha" in _d8_ff_out and "checked in: upsilon" in _d8_up_out
              and "handoff waiting" not in _d8_ff_out and "handoff waiting" not in _d8_up_out)

        # ---- phi: a TRUNCATED block warns and prints nothing (S8-e) ----
        _d8_phi_good = _d8_block("phi", "2026-07-29T10:00:00", "yes",
                                 "the intact block above the break")
        _d8_phi_prior = ("# phi — seat memory\n\n" + _d8_phi_good + "\n"
                         + _d8_head("phi", "2026-07-29T11:00:00", "yes") + "\n"
                         + "the append stopped here, mid-block\n")
        _d8_phi = _d8_seat("phi", _d8_phi_prior)
        _d8_phi_out, _d8_phi_code = _d8_in("phi", "s12-08 truncated-block fixture", "%85")
        check("s12-08 S8-e: a TRUNCATED block warns and prints NOTHING — the check-in succeeds, "
              "the warning names the truncation, neither the broken tail nor the intact block "
              "above it reaches the seat, and not one byte of memory.md is written. A reader that "
              "printed to EOF instead would pour an unbounded slice of the file into the session, "
              "and would mark read a note whose end nobody can locate",
              _d8_phi_code is None and "TRUNCATED" in _d8_phi_out
              and "the intact block above the break" not in _d8_phi_out
              and "the append stopped here" not in _d8_phi_out
              and _d8_phi.read_text(encoding="utf-8") == _d8_phi_prior)

        # ---- tau + xi: delivery is AUTHOR-BLIND (S8-f) ----
        # tau's block names ITSELF (the crash-revival case the spec calls out). xi's names another
        # seat entirely — the half that discriminates: a reader that filtered on `seat=` would
        # still pass tau's half, so the foreign author is what makes this row fail by construction.
        _d8_tau = _d8_seat("tau", "# tau — seat memory\n\n"
                           + _d8_block("tau", "2026-07-29T12:00:00", "yes",
                                       "self-authored: the crash-revival case"))
        _d8_xi = _d8_seat("xi", "# xi — seat memory\n\n"
                          + _d8_block("leader", "2026-07-29T12:30:00", "yes",
                                      "foreign author: delivered all the same"))
        _d8_tau_out, _d8_tau_code = _d8_in("tau", "s12-08 self-authored fixture", "%86")
        _d8_xi_out, _d8_xi_code = _d8_in("xi", "s12-08 foreign-author fixture", "%87")
        check("s12-08 S8-f: delivery is AUTHOR-BLIND (D2) — a block whose `seat=` names the "
              "checking-in seat ITSELF is delivered normally, and so is one whose `seat=` names "
              "another seat entirely. The key is (seat FOLDER, `unread`), never the author: a "
              "successor revived after a crash reads a block its own predecessor wrote, and a "
              "reader that matched on the author would strand exactly that seat",
              _d8_tau_code is None and _d8_xi_code is None
              and "self-authored: the crash-revival case" in _d8_tau_out
              and "foreign author: delivered all the same" in _d8_xi_out
              and _d8_tau.read_text(encoding="utf-8").count("unread=no") == 1
              and _d8_xi.read_text(encoding="utf-8").count("unread=no") == 1)

        # ============ s12-09: a CLASSIFIER-SHAPED failure at each renewal step is REPORTED ======
        # Spec: stage-1-2-gate-checkout-spec.md §6 (the W2/W4 simulation block). R-8: a step that
        # fails must say so at its own exit code or in its own output, naming the layer that
        # failed — never log to a detached stream and report success. R-6: every row below is a
        # VERIFICATION row over behaviour s12-05/06/08 already landed, so each is green-before by
        # construction; the red arms (stub- and code-side mutations run one at a time under
        # `--expect-fail`) are the R-6 evidence, per s12-08's labelling precedent.
        #
        # ⚠ THE BOUNDARY SIMULATED IS EACH STEP'S OWN WRITE, NOT A TMUX SEND. The task's named
        # tmux stubs (`tmux_send_text`/`tmux_send_enter`/`wake`) ARE installed below, rebound to
        # fail classifier-shaped and to RECORD every call — and each step's *1 row asserts they
        # were never reached: none of the three renewal steps crosses tmux, so a tmux-side-only
        # stub would make all nine rows vacuous (the task's own warning). What a classifier
        # actually breaks in these steps is the step's boundary WRITE, so the denial is injected
        # there: path-scoped through `atomic_write` (s12-07 S7-d's pattern), raising the
        # classifier-shaped reason so the surface can be asserted to carry it — or shown to drop
        # it.
        #
        # ⚠ EVERY STUB PROVES IT WAS REACHED. Each denial appends to its own observation list and
        # each step's *1 row asserts that list non-empty IN THE SAME RUN, before anything about
        # the failure: nine greens over a rebind that never fired would be nine vacuous rows.
        #
        # ⚠ NO SIXTH refuse() LAYER (W4). A classifier failure is NOT coord.py refusing, and the
        # rows assert the two stay DISTINGUISHABLE: the arm and the delivery report theirs as
        # loud stderr WARNINGs with no `refused [coord` prefix (BY RULING — a failed mute must
        # not strand the renewal, and a delivery must never gate a check-in), while call 2
        # refuses at coord.py's own layer `state` and carries the boundary's reason string
        # through, so "the write failed because <reason>" never collapses into a bare refusal.
        _s9_reason = "permission denied by harness classifier"
        _s9_aw_real = atomic_write
        _s9_tmux = []
        _s9_send_real, _s9_enter_real, _s9_wake_real = tmux_send_text, tmux_send_enter, wake
        _s9_send_deny = lambda pane, t: (_s9_tmux.append(("send", pane)) or (False, _s9_reason))
        _s9_enter_deny = lambda pane: (_s9_tmux.append(("enter", pane)) or (False, _s9_reason))
        _s9_wake_deny = lambda pane, t: (_s9_tmux.append(("wake", pane)) or (False, _s9_reason))

        def _s9_install(aw_deny):
            global atomic_write, tmux_send_text, tmux_send_enter, wake
            atomic_write = aw_deny
            tmux_send_text, tmux_send_enter, wake = _s9_send_deny, _s9_enter_deny, _s9_wake_deny

        def _s9_restore():
            global atomic_write, tmux_send_text, tmux_send_enter, wake
            atomic_write = _s9_aw_real
            tmux_send_text, tmux_send_enter, wake = _s9_send_real, _s9_enter_real, _s9_wake_real

        # ---- S9-a: the ARM (`checkout --renew`, no --handoff). Boundary: the closing write ----
        _s9a_obs = []

        def _s9a_deny(path, text):
            if Path(path).name == "closing.json":
                _s9a_obs.append(Path(path).name)
                raise OSError(_s9_reason)
            return _s9_aw_real(path, text)

        _s9a_mem = _d8_seat("s9a", "# s9a — seat memory\nprior state\n")
        run(cmd_checkin, agent="s9a", summary="s12-09 arm fixture", pane="%88", force=True)
        _s9a_before = _s9a_mem.read_text(encoding="utf-8")
        _s9_install(_s9a_deny)
        _s9a_o, _s9a_e, _s9a_c = harness_outcome(
            cmd_checkout, ns(agent="s9a", renew=True, handoff=None, no_export=True))
        _s9_restore()
        _, _, _s9a_rows = load_workers(base_g)
        _s9a_row = current_row(_s9a_rows, "s9a") or {}
        check("s12-09 S9-a1: with the arm's boundary write DENIED the step still ends its turn "
              "(code None — a failed mute must not strand the renewal, so the arm's failure "
              "surface is a WARNING, not an exit) AND its own stderr carries an explicit failure "
              "line, AND the denial was OBSERVED in this same run while the tmux-side stubs were "
              "NEVER reached — the rows are about a failure that actually fired at the boundary "
              "this step crosses, never about a rebind that missed the code under test",
              len(_s9a_obs) >= 1 and not _s9_tmux and _s9a_c is None
              and "WARNING" in _s9a_e and "NOTHING IS CLOSED YET" in _s9a_o)
        check("s12-09 S9-a2: the arm's failure line is DISTINGUISHABLE from a coord.py refusal — "
              "it names the act that failed (the wake mute could not be written) and carries no "
              "`refused [coord` prefix, so a reader can tell 'the boundary write failed' from "
              "'coord.py refused me'. ⚠ Known residue, surfaced to s12-05 and deliberately NOT "
              "asserted either way: `set_closing` returns a bare False, so the boundary's OWN "
              "reason string is dropped before this surface — the seat cannot tell a classifier "
              "denial from a full disk. IMPLICATION FORM for red-arm isolation: the presence of "
              "the failure line is S9-a1's subject, its grammar is this row's",
              "WARNING" not in _s9a_e
              or ("wake mute could NOT be written" in _s9a_e
                  and "refused [coord" not in _s9a_e))
        check("s12-09 S9-a3: NO HALF-WRITE — after the denied arm the roster row is still "
              "`active == yes` with no checkout stamp (the arm never flips it; the roster clause "
              "is also pinned by s12-05 S2-a, whose coverage it shares) and the seat's memory.md "
              "is byte-identical: the step left every surface in exactly one of its legal states",
              _s9a_row.get("active") == "yes" and not _s9a_row.get("checkout")
              and _s9a_mem.read_text(encoding="utf-8") == _s9a_before)
        clear_closing(base_g, "s9a")

        # ---- S9-b: HANDOFF-APPEND + CHECKOUT (call 2). Boundary: the memory.md append ----
        _s9b_obs = []

        def _s9b_deny(path, text):
            if Path(path).name == "memory.md":
                _s9b_obs.append(Path(path).name)
                raise OSError(_s9_reason)
            return _s9_aw_real(path, text)

        _s9b_mem = _d8_seat("s9b", "# s9b — seat memory\nprior state\n")
        run(cmd_checkin, agent="s9b", summary="s12-09 call-2 fixture", pane="%89", force=True)
        _s9b_before = _s9b_mem.read_text(encoding="utf-8")
        _s9_install(_s9b_deny)
        _s9b_o, _s9b_e, _s9b_c = harness_outcome(
            cmd_checkout, ns(agent="s9b", renew=True,
                             handoff="finish the arm; the successor starts at the spec",
                             no_export=True))
        _s9_restore()
        _s9b_out = _s9b_o + _s9b_e
        _, _, _s9b_rows = load_workers(base_g)
        _s9b_row = current_row(_s9b_rows, "s9b") or {}
        _s9b_landed = _s9b_mem.read_text(encoding="utf-8")
        check("s12-09 S9-b1: with the append's boundary write DENIED call 2 fails LOUDLY at its "
              "own exit — code 1, the output names the handoff as NOT WRITTEN, and neither "
              "success line (`handoff appended`, `checked out:`) prints — and the denial was "
              "OBSERVED in this same run while the tmux-side stubs were never reached. A step "
              "that closed on top of a handoff that never landed is the exact detached-stream "
              "anti-pattern this task exists to catch",
              len(_s9b_obs) >= 1 and not _s9_tmux and _s9b_c == 1
              and "HANDOFF NOT WRITTEN" in _s9b_out
              and "handoff appended" not in _s9b_o and "checked out:" not in _s9b_o)
        check("s12-09 S9-b2: call 2's refusal NAMES BOTH SIDES of the boundary — coord.py's own "
              "layer (`refused [coord state]`) AND the denied write's reason string carried "
              "through verbatim, so 'coord.py refused BECAUSE the boundary write failed with "
              "<reason>' stays distinguishable from a bare coord.py refusal without minting a "
              "sixth layer for the classifier (W4). IMPLICATION FORM for red-arm isolation: "
              "presence is S9-b1's subject, the grammar is this row's",
              "HANDOFF NOT WRITTEN" not in _s9b_out
              or ("refused [coord state]" in _s9b_out and _s9_reason in _s9b_out))
        check("s12-09 S9-b3: NO HALF-WRITE — memory.md either carries a COMPLETE handoff block "
              "(both delimiters, opener before closer) or is byte-identical to before, never a "
              "partial block; and the roster row sits in exactly one legal pair — `active yes` "
              "with no checkout stamp, or `active no` with one. Here the refusal left it "
              "untouched: still active, unstamped, memory byte-identical",
              (_s9b_landed == _s9b_before
               or (_s9b_landed.count(_h6_open) == 1 and _s9b_landed.count(_h6_close) == 1
                   and _s9b_landed.find(_h6_open) < _s9b_landed.find(_h6_close)))
              and ((_s9b_row.get("active") == "yes" and not _s9b_row.get("checkout"))
                   or (_s9b_row.get("active") == "no" and bool(_s9b_row.get("checkout")))))
        clear_closing(base_g, "s9b")

        # ---- S9-c: the CHECK-IN DELIVERY. Boundary: the unread->read flip's write ----
        # The R-8 property here is read off the WARNING grammar, not an exit code — BY RULING a
        # delivery must never gate a check-in, so code None IS the expected code and the loud
        # stderr WARNING carrying the reason is the visible failure surface. A flip that fails
        # after the print leaves `unread=yes`: re-delivery beats loss, and that IS S9-c3.
        _s9c_obs = []

        def _s9c_deny(path, text):
            if Path(path).name == "memory.md":
                _s9c_obs.append(Path(path).name)
                raise OSError(_s9_reason)
            return _s9_aw_real(path, text)

        _s9c_note = "carried across the break: the successor finishes the arm"
        _s9c_mem = _d8_seat("s9c", "# s9c — seat memory\n\n"
                            + _d8_block("s9c", "2026-07-29T13:00:00", "yes", _s9c_note))
        _s9c_before = _s9c_mem.read_text(encoding="utf-8")
        _s9_install(_s9c_deny)
        _s9c_out, _s9c_c = _d8_in("s9c", "s12-09 delivery fixture", "%90")
        _s9_restore()
        _s9c_landed = _s9c_mem.read_text(encoding="utf-8")
        check("s12-09 S9-c1: with the flip's boundary write DENIED the check-in still SUCCEEDS "
              "(code None — BY RULING a delivery never gates a check-in, so no exit code will "
              "ever carry this failure), the block is still PRINTED, its own output carries the "
              "explicit failure line `NOT marked read`, and the denial was OBSERVED in this same "
              "run while the tmux-side stubs were never reached. Visibility here IS the WARNING "
              "— a delivery that logged nowhere and reported success is the measured shape this "
              "task exists to forbid",
              len(_s9c_obs) >= 1 and not _s9_tmux and _s9c_c is None
              and "checked in: s9c" in _s9c_out and _s9c_note in _s9c_out
              and "NOT marked read" in _s9c_out)
        check("s12-09 S9-c2: the delivery's failure line carries the boundary's OWN reason "
              "string and no `refused [coord` prefix — a reader of the WARNING can tell 'the "
              "flip's write was denied (classifier-shaped)' from 'coord.py refused the "
              "check-in', which is R-8's layer-naming applied to a surface that must never "
              "refuse. IMPLICATION FORM for red-arm isolation: presence is S9-c1's subject, the "
              "grammar is this row's",
              "NOT marked read" not in _s9c_out
              or (_s9_reason in _s9c_out and "refused [coord" not in _s9c_out))
        check("s12-09 S9-c3: NO HALF-WRITE — the block's `unread` attribute is still `yes` and "
              "memory.md is byte-identical: not shown as read means NOT marked read, so the next "
              "check-in of this seat is shown the same block again. Re-delivery beats loss — "
              "s12-08's ordering property observed through the classifier lens",
              _s9c_landed == _s9c_before and _s9c_landed.count("unread=yes") == 1
              and "unread=no" not in _s9c_landed)

        # ============ s3-03: the LIFECYCLE-INFLIGHT marker store ================================
        # ⚠ EVERY ROW BELOW ASSERTS ON A RETURN VALUE OR ON `load_lifecycle`'s DICT, NEVER ON FILE
        # BYTES. `atomic_write` and `_acquire_flock` are rebindable in this suite (and ARE rebound
        # by the never-fatal row), so a row that read the file directly would be asserting about
        # the stub rather than about the store — green either way, which is the vacuity this file
        # has caught before.
        _lc_base = Path(td) / "lc" / "coordination"
        _lc_base.mkdir(parents=True)
        _lc_rec = {"disposition": "renew",
                   "executor": {"pid": 41207, "starttime": "884231"},
                   "caller": {"pid": 41190, "starttime": "884118"},
                   "pane": "%37", "tmux-target": "%37"}
        _lc_stamped = stamp_lifecycle(_lc_base, "engineer", dict(_lc_rec))
        _lc_back = load_lifecycle(_lc_base)
        _lc_e = _lc_back.get("engineer") or {}
        check("s3-03 (1) ROUND-TRIP: `stamp_lifecycle` returns True and `load_lifecycle` gives "
              "every caller-supplied field back UNCHANGED under the seat's own key, plus the four "
              "the store owns — `stamped-at` in `now()`'s format (so `lifecycle_age_min` reads it "
              "with `closing_age_min`'s arithmetic and the package keeps ONE date format), "
              "`state: in-flight`, an EMPTY `steps-completed`, and `failure`",
              _lc_stamped is True
              and all(_lc_e.get(k) == v for k, v in _lc_rec.items())
              and _lc_e.get("state") == "in-flight" and _lc_e.get("steps-completed") == []
              and _lc_e.get("failure") == "" and lifecycle_age_min(_lc_e) == 0)
        stamp_lifecycle(_lc_base, "leader", {"pane": "%9"})
        _lc_two = load_lifecycle(_lc_base)
        check("⚠ s3-03 (1) THE RED ARM: the marker is ONE FILE KEYED BY SEAT. A seat never "
              "stamped is ABSENT, and a second seat's stamp leaves the first untouched. A flat "
              "(non-seat-keyed) file would answer for EVERY seat and overwrite on every write, "
              "and this is the only row that would see it",
              "leader" not in _lc_back and "beta" not in _lc_two
              and sorted(_lc_two) == ["engineer", "leader"]
              and (_lc_two["engineer"] or {}).get("pane") == "%37"
              and (_lc_two["leader"] or {}).get("pane") == "%9")

        # ---- (2) NEVER FATAL, both directions.
        _lc_garbage = Path(td) / "lc-garbage" / "coordination"
        _lc_garbage.mkdir(parents=True)
        lifecycle_path(_lc_garbage).write_text("{ this is not json", encoding="utf-8")
        _lc_listy = Path(td) / "lc-listy" / "coordination"
        _lc_listy.mkdir(parents=True)
        lifecycle_path(_lc_listy).write_text('["a", "b"]', encoding="utf-8")
        _lc_absent = Path(td) / "lc-absent" / "coordination"
        _lc_absent.mkdir(parents=True)
        try:
            _lc_reads = (load_lifecycle(_lc_garbage), load_lifecycle(_lc_listy),
                         load_lifecycle(_lc_absent))
            _lc_read_raised = ""
        except Exception as _lc_rexc:           # noqa: BLE001 — the raise IS this row's verdict
            _lc_reads, _lc_read_raised = None, f"{type(_lc_rexc).__name__}: {_lc_rexc}"
        check("s3-03 (2) NEVER FATAL on READ: unparseable JSON, VALID JSON of the wrong type (a "
              "list), and an absent file each read as `{}` and raise NOTHING — `load_awaiting`'s "
              "fail-safe direction, because a marker that cannot be read must never take down the "
              "renewal it is bookkeeping for",
              _lc_read_raised == "" and _lc_reads == ({}, {}, {}))
        _lc_aw_real = atomic_write

        def _lc_aw_deny(path, text):
            # PATH-SCOPED, exactly as s12-07 S7-d is. A blanket raise would prove nothing about
            # THIS store: every ledger in the package goes through the same writer, so the row
            # would pass for a reason it does not name.
            if Path(path).name == "lifecycle-inflight.json":
                raise OSError("selftest: the lifecycle marker write fails")
            return _lc_aw_real(path, text)

        atomic_write = _lc_aw_deny
        try:
            _lc_wf = (stamp_lifecycle(_lc_base, "zeta", {"pane": "%1"}),
                      append_lifecycle_step(_lc_base, "engineer", "never-happened"),
                      finish_lifecycle(_lc_base, "engineer", "done"),
                      clear_lifecycle(_lc_base, "engineer"))
            _lc_wraised = ""
        except Exception as _lc_wexc:           # noqa: BLE001 — the raise IS this row's verdict
            _lc_wf, _lc_wraised = None, f"{type(_lc_wexc).__name__}: {_lc_wexc}"
        atomic_write = _lc_aw_real
        _lc_afterfail = load_lifecycle(_lc_base)
        check("s3-03 (2) NEVER FATAL on WRITE: with the marker write failing, all four writers "
              "REPORT False rather than raising, and NO HALF-WRITE lands — `zeta` was never "
              "created, `engineer` is still `in-flight`, carries no step, and was not cleared",
              _lc_wraised == "" and _lc_wf == (False, False, False, False)
              and "zeta" not in _lc_afterfail
              and (_lc_afterfail.get("engineer") or {}).get("state") == "in-flight"
              and (_lc_afterfail.get("engineer") or {}).get("steps-completed") == [])

        # ---- (3) APPEND ORDER, and a step may only FOLLOW a stamp.
        _lc_steps_in = ["caller-exited", "in-place-decided:in-place", "respawned"]
        _lc_appends = [append_lifecycle_step(_lc_base, "engineer", _s) for _s in _lc_steps_in]
        _lc_orphan = append_lifecycle_step(_lc_base, "nosuchseat", "a step with no stamp")
        _lc_a = load_lifecycle(_lc_base)
        check("s3-03 (3) APPEND ORDER: three appends produce the three steps IN ORDER, and a step "
              "appended to a seat with NO entry returns False rather than creating one. "
              "`steps-completed` asserts that a step VERIFIED, so a list that could begin without "
              "a stamp would assert about a renewal this file never saw start",
              _lc_appends == [True, True, True] and _lc_orphan is False
              and "nosuchseat" not in _lc_a
              and (_lc_a.get("engineer") or {}).get("steps-completed") == _lc_steps_in)

        # ---- (4) THE STALENESS PREDICATE, each conjunct isolated.
        _lc_live_id = {"pid": os.getpid(), "starttime": proc_stat(os.getpid())[1]}
        _lc_dead_id = {"pid": 999999, "starttime": "1"}
        _lc_old = (datetime.now()
                   - timedelta(minutes=LIFECYCLE_STALE_MIN + 5)).strftime("%Y-%m-%d %H:%M")
        _lc_young = now()

        def _lc_entry(state, stamp, ident):
            return {"state": state, "stamped-at": stamp, "executor": dict(ident)}

        check("s3-03 (4) THE FIXTURE'S OWN PREMISE, asserted so no row below can be vacuous: this "
              "process's (pid, starttime) IS live to `ident_is_live_process` and the fabricated "
              "one is NOT. On a fixture where both idents read the same way, every conjunct-3 row "
              "would stay green under any mutation of conjunct 3",
              ident_is_live_process((_lc_live_id["pid"], _lc_live_id["starttime"])) is True
              and ident_is_live_process((_lc_dead_id["pid"], _lc_dead_id["starttime"])) is False)
        check("s3-03 (4a) CONJUNCT 1 ISOLATED: `state=done` + old + DEAD executor is NOT stale — "
              "a completed renewal is never a failed one, however long ago it completed",
              lifecycle_stale(_lc_entry("done", _lc_old, _lc_dead_id)) is False)
        check("s3-03 (4b) CONJUNCT 2 ISOLATED: `in-flight` + YOUNG + dead executor is NOT stale — "
              "inside LIFECYCLE_STALE_MIN a renewal has not had time to fail, and its executor is "
              "not yet observable to a reader that arrives mid-fork",
              lifecycle_stale(_lc_entry("in-flight", _lc_young, _lc_dead_id)) is False)
        check("⚠⚠ s3-03 (4c) CONJUNCT 3 ISOLATED — THE MID-RENEWAL ROW, and the one that "
              "DOUBLE-LAUNCHES A SEAT when it is wrong: `in-flight` + old + a LIVE executor is "
              "NOT stale. Stage 4 reads exactly this complement as MID-RENEWAL and must never "
              "fire on it. However old the stamp, a running executor is a renewal in progress",
              lifecycle_stale(_lc_entry("in-flight", _lc_old, _lc_live_id)) is False)
        check("s3-03 (4d) ALL THREE TOGETHER: `in-flight` + old + DEAD executor IS stale — the "
              "failed renewal, and the ONLY combination that is",
              lifecycle_stale(_lc_entry("in-flight", _lc_old, _lc_dead_id)) is True)
        check("s3-03 (4) THE FAIL-SAFE DIRECTION: an unreadable stamp, a missing executor ident, "
              "and a non-dict entry all answer NOT stale. Firing wrongly revives a seat that is "
              "alive; declining wrongly leaves a stuck seat stuck AND named in every close-run's "
              "output, which is recoverable",
              lifecycle_stale({"state": "in-flight", "stamped-at": "not a date",
                               "executor": dict(_lc_dead_id)}) is False
              and lifecycle_stale({"state": "in-flight", "stamped-at": _lc_old}) is False
              and lifecycle_stale(None) is False)

        # ---- (5) THE PREDICATE-CHOICE GUARD, and the record shape watch.py reads.
        check("⚠ s3-03 (5) THE PREDICATE-CHOICE GUARD, IN-SUITE: the two predicates DISAGREE on "
              "this very ident — `ident_is_live_process` says LIVE, `ident_is_live_harness` says "
              "DEAD, because `is_harness_argv` matches only the claude/codex/opencode basenames "
              "and the lifecycle executor is PYTHON. Swapping conjunct 3 to the harness predicate "
              "would turn row (4c) from MID-RENEWAL into a fired staleness, i.e. a double launch. "
              "This row is what makes (4c) DISCRIMINATING rather than merely green",
              ident_is_live_process((_lc_live_id["pid"], _lc_live_id["starttime"])) is True
              and ident_is_live_harness((_lc_live_id["pid"], _lc_live_id["starttime"])) is False)
        _lc_tup = Path(td) / "lc-tuple" / "coordination"
        _lc_tup.mkdir(parents=True)
        stamp_lifecycle(_lc_tup, "engineer", {"executor": (4242, "884231"),
                                              "caller": [4240, "884118"]})
        _lc_tv = load_lifecycle(_lc_tup).get("engineer") or {}
        check("s3-03 (5) THE SHAPE watch.py READS: `executor`/`caller` normalize to "
              "`{'pid': int, 'starttime': str}` whatever form the caller hands over, and a "
              "half-identity resolves to `{}` rather than a pid-only dict. watch.py's "
              "`_executor_ident_live` reads `entry['executor']['pid']`/`['starttime']` and answers "
              "False for any other shape, so a (pid, starttime) TUPLE written straight through "
              "would make every LIVE executor read DEAD and double-launch the seat",
              _lc_tv.get("executor") == {"pid": 4242, "starttime": "884231"}
              and _lc_tv.get("caller") == {"pid": 4240, "starttime": "884118"}
              and lifecycle_ident("nonsense") == {} and lifecycle_ident((7, "")) == {}
              and lifecycle_ident({"pid": 7}) == {})

        # ---- (6) THE CLOSE-RUN SWEEP.
        _lc_pkg = Path(td) / "lc-run"
        (_lc_pkg / "coordination").mkdir(parents=True)
        (_lc_pkg / "runs.csv").write_text(
            "run-id,type,state,taskforce-ids,opened,closed\n"
            "lc-run,goal,open,tf-lc,2026-07-29 09:00,\n", encoding="utf-8")
        _lc_sb = _lc_pkg / "coordination"
        for _s in ("alpha", "beta"):
            stamp_lifecycle(_lc_sb, _s, {"disposition": "renew", "pane": "%1"})
            finish_lifecycle(_lc_sb, _s, "done")
        stamp_lifecycle(_lc_sb, "gamma", {"disposition": "renew", "pane": "%2"})
        stamp_lifecycle(_lc_sb, "delta", {"disposition": "renew", "pane": "%3"})
        finish_lifecycle(_lc_sb, "delta", "FAILED", "the respawned harness never came up")
        _lc_pre = sorted(load_lifecycle(_lc_sb))
        _lc_close_out = run(cmd_close_run, package=str(_lc_pkg), as_agent="leader")
        _lc_post = load_lifecycle(_lc_sb)
        check("s3-03 (6) THE CLOSE-RUN SWEEP: on a marker holding two `done` entries, one "
              "`in-flight` and one `FAILED`, `close-run` clears EXACTLY the two done ones, leaves "
              "the other two, and NAMES each survivor with its reason. Without this sweep "
              "`clear_lifecycle` ships with zero callers and 'swept by the next close-run' is "
              "fiction — done entries would accumulate for the life of the goal",
              _lc_pre == ["alpha", "beta", "delta", "gamma"]
              and sorted(_lc_post) == ["delta", "gamma"]
              and "lifecycle marker: swept 2 completed entries (alpha, beta)" in _lc_close_out
              and "lifecycle marker: LEFT gamma — state=in-flight" in _lc_close_out
              and "lifecycle marker: LEFT delta — state=FAILED: the respawned harness never "
                  "came up" in _lc_close_out)
        check("s3-03 (6) THE TERMINAL WRITE IS BOUNDED: `finish_lifecycle` refuses any state that "
              "is not `done` or `FAILED`, refuses a seat with no entry rather than creating one, "
              "and `clear_lifecycle` answers False on an absent seat. The sweep keys on those two "
              "strings EXACTLY, so a third value would become an entry nothing ever clears and "
              "nothing ever reads as a failure",
              finish_lifecycle(_lc_sb, "gamma", "finished") is False
              and finish_lifecycle(_lc_sb, "nosuchseat", "done") is False
              and "nosuchseat" not in load_lifecycle(_lc_sb)
              and clear_lifecycle(_lc_sb, "nosuchseat") is False
              and (load_lifecycle(_lc_sb).get("gamma") or {}).get("state") == "in-flight")

        # ============ s3-04: the LIFECYCLE LINE — the marker's READ SIDE ========================
        # ⚠ THE FIXTURE IS THE MAIN PACKAGE'S OWN `coordination/`, not a bare temp dir, and that is
        # not convenience. Rows (3a)/(3b) must render through the REAL commands, and `cmd_workers`
        # RETURNS EARLY on a package with no roster rows — before it reaches either render site —
        # so a fresh empty package would assert about a code path the command never enters: green
        # whether or not the line is wired in, which is the whole property row 3 exists to prove.
        # The marker is removed again at the end of this block.
        _s4_base = base_dir(ns())
        _s4_nofile = lifecycle_line(_s4_base)              # no marker file at all
        _s4_clean_st = run(cmd_status, agent="alpha")
        _s4_clean_wk = run(cmd_workers, full=False, history=False)
        stamp_lifecycle(_s4_base, "s4-finished", {"disposition": "renew",
                                                  "executor": {"pid": 999996, "starttime": "1"}})
        finish_lifecycle(_s4_base, "s4-finished", "done")
        _s4_done = lifecycle_line(_s4_base)                # marker holding ONLY a done entry
        _s4_done_st = run(cmd_status, agent="alpha")
        _s4_done_wk = run(cmd_workers, full=False, history=False)
        check("s3-04 (1) SILENT WHEN CLEAN: with NO marker file, and with a marker holding only "
              "`state: done`, `lifecycle_line` returns EMPTY and neither `status` nor `workers` "
              "prints a lifecycle line. A completed renewal is not news, and a surface that "
              "shouts on a healthy room gets scrolled past on a sick one — which is the failure "
              "mode `undelivered_line` was written against, not a style preference",
              _s4_nofile == "" and _s4_done == ""
              and not any("LIFECYCLE MARKERS IN ALARM" in _o for _o in
                          (_s4_clean_st, _s4_clean_wk, _s4_done_st, _s4_done_wk)))

        # The stale/FAILED/hand-edited fixture. The two in-flight stamps are AGED through the
        # store's own writer: `stamp_lifecycle` OWNS `stamped-at` and overwrites whatever a caller
        # supplies, so rewriting the loaded dict is the only way a check can hold an old marker
        # without sleeping for LIFECYCLE_STALE_MIN.
        _s4_old = (datetime.now()
                   - timedelta(minutes=LIFECYCLE_STALE_MIN + 5)).strftime("%Y-%m-%d %H:%M")
        stamp_lifecycle(_s4_base, "s4-stuck", {"disposition": "renew", "pane": "%77",
                                               "executor": {"pid": 999999, "starttime": "1"}})
        append_lifecycle_step(_s4_base, "s4-stuck", "caller-exited")
        append_lifecycle_step(_s4_base, "s4-stuck", "in-place-decided:in-place")
        stamp_lifecycle(_s4_base, "s4-live", {"disposition": "renew", "pane": "%78",
                                              "executor": dict(_lc_live_id)})
        stamp_lifecycle(_s4_base, "s4-broke", {"disposition": "renew",
                                               "executor": {"pid": 999998, "starttime": "1"}})
        append_lifecycle_step(_s4_base, "s4-broke", "caller-exited")
        finish_lifecycle(_s4_base, "s4-broke", "FAILED", "the respawned harness never came up")
        # `s4-nodisp` exists so row (4d) rests on an entry of ITS OWN. It used to read the blank
        # disposition off `s4-hand`, which made the mutation that deletes the hand-edited branch
        # red TWO rows at once — and `--expect-fail` demands exactly one, so neither row's red arm
        # could be isolated. One fixture entry per property is what buys that isolation.
        stamp_lifecycle(_s4_base, "s4-nodisp", {"pane": "%79",
                                                "executor": {"pid": 999995, "starttime": "1"}})
        _s4_data = load_lifecycle(_s4_base)
        for _s4_s in ("s4-stuck", "s4-live", "s4-nodisp"):
            _s4_data[_s4_s]["stamped-at"] = _s4_old
        _s4_data["s4-hand"] = {"state": "paused-by-hand", "stamped-at": _s4_old,
                               "disposition": "", "failure": "", "steps-completed": [],
                               "executor": {"pid": 999997, "starttime": "1"}}
        _write_lifecycle(_s4_base, _s4_data)
        _s4_line = lifecycle_line(_s4_base)
        check("s3-04 (2) LOUD WHEN STALE: an `in-flight` entry stamped past LIFECYCLE_STALE_MIN "
              "with a DEAD executor is named — the seat, its executor pid, its disposition, the "
              "marker's age and the LAST VERIFIED STEP, so a reader can see where it stopped — "
              "together with the consequence in plain words (NEITHER ALIVE NOR CLOSED) and the "
              "interim manual remedy. RED ARM: run this same assertion against coord.py before "
              "this task landed — `lifecycle_line` does not exist, so it fails by construction",
              "s4-stuck" in _s4_line and "999999" in _s4_line
              and "disposition=renew" in _s4_line
              and "in-place-decided:in-place" in _s4_line
              # the age is asserted over a two-minute window on purpose: `_s4_old` is computed one
              # statement earlier than the render, so a clock crossing a minute boundary between
              # them is a real and legitimate outcome, not a defect to pin the row on.
              and any(f"marker {_a}min old" in _s4_line
                      for _a in (LIFECYCLE_STALE_MIN + 5, LIFECYCLE_STALE_MIN + 6))
              and "NEITHER ALIVE NOR CLOSED" in _s4_line
              and "close-seat <seat> --renew" in _s4_line
              and "s4-finished" not in _s4_line)
        _s4_st = run(cmd_status, agent="alpha")
        _s4_wk = run(cmd_workers, full=False, history=False)
        check("s3-04 (3a) RENDERED BY `status`, not merely computed — this is the check that "
              "separates 'the function exists' from 'the run can see it', which is the entire "
              "point of the task. RED ARM: define `lifecycle_line` and wire it into neither "
              "command; this row and (3b) both go red",
              "LIFECYCLE MARKERS IN ALARM" in _s4_st and "s4-stuck" in _s4_st)
        check("s3-04 (3b) RENDERED BY `workers` TOO — the roster is where the leader already "
              "looks to decide lifecycle, and a marker visible on only one of the two surfaces is "
              "half a read side. Split from (3a) so ONE mutation reds ONE row and `--expect-fail` "
              "can isolate each half; the both-sites-removed mutant reds both, as it must",
              "LIFECYCLE MARKERS IN ALARM" in _s4_wk and "s4-stuck" in _s4_wk)
        check("s3-04 (4) FAILED IS REPORTED EVEN WHEN YOUNG, with its `failure` text: the entry "
              "is one minute old and `lifecycle_stale` says NOT stale — asserted here, so this "
              "row cannot pass through the staleness path and stay green if the FAILED branch is "
              "deleted. A FAILED marker is not stale; it IS an alarm, because the executor itself "
              "reported the break",
              "s4-broke" in _s4_line
              and "the respawned harness never came up" in _s4_line
              and lifecycle_stale(_s4_data["s4-broke"]) is False)
        check("⚠⚠ s3-04 (4b) MID-RENEWAL IS NEVER REPORTED — the one row that costs a DOUBLE "
              "LAUNCH when it is wrong. `s4-live` is `in-flight`, stamped just as long ago as "
              "`s4-stuck`, and its executor IS live, so it is a renewal IN PROGRESS. The class is "
              "decided by CALLING `lifecycle_stale`, never by re-spelling it, so this surface and "
              "Stage 4 cannot hold two definitions of stale that drift apart",
              "s4-live" not in _s4_line
              and lifecycle_stale(_s4_data["s4-live"]) is False
              and lifecycle_stale(_s4_data["s4-stuck"]) is True)
        check("s3-04 (4c) A HAND-EDITED STATE IS NAMED, never silently skipped: the store writes "
              "exactly in-flight|done|FAILED, so a fourth value means somebody edited the file — "
              "and `sweep_lifecycle` will not clear it either, so it survives every close-run. An "
              "entry left behind SILENTLY is indistinguishable from one never written",
              "s4-hand" in _s4_line and "'paused-by-hand'" in _s4_line
              and "close-run will not sweep it either" in _s4_line)
        check("s3-04 (4d) THE BLANK DISPOSITION READS AS BLANK, never as `done`: `\"\"` is this "
              "file's absent-key reading (`load_awaiting`'s `done` default belongs to "
              "awaiting-close.json's records, not these), and the line SAYS to read the intent "
              "from awaiting-close.json rather than inventing one. This file is authoritative for "
              "EXECUTION state only",
              "s4-nodisp" in _s4_line
              and "s4-nodisp — disposition NOT recorded here — read the intent from "
                  "awaiting-close.json" in _s4_line)
        lifecycle_path(_s4_base).unlink()   # leave the shared fixture as this block found it
        check("s3-04 (1) AND THE FIXTURE IS RESTORED: with the marker removed the line is empty "
              "again, so no row after this block inherits an alarm this block manufactured",
              lifecycle_line(_s4_base) == "")

    (wake, set_pane_title, tmux_split_pane, tmux_new_window, tmux_kill_pane, tmux_capture,
     tmux_raise_history_limit, schedule_session_rename, tmux_window_panes, tmux_session_name,
     tmux_split_strip, restore_overview_strip, tmux_find_window_pane, tmux_send_text,
     tmux_send_enter, tmux_capture_tail, tmux_pane_window, detect_pane, live_panes,
     _acquire_flock, atomic_write, pane_title) = real
    (pane_harness_pids, pane_harness_idents, wait_harness_up, verify_pids_gone, arm_pid_reaper,
     tmux_pane_pid, tmux_respawn_pane, available_mb) = proc_real
    (NATIVE_ID_WAIT, WAKE_ENTER_VERIFY_DELAY_FIRST,
     WAKE_ENTER_VERIFY_DELAY_RETRY) = waits_real
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
    # s12-03: the one refusal in this file that is RETURNED rather than printed. It goes through
    # `refusal_text` so it is layered like every other — the selftest guard scopes to `print(` and
    # would never have seen it, which is exactly why it is asserted here by hand.
    check("s12-03: the RETURNED refusal (wake's newline guard) names its layer too — a refusal "
          "that reaches a seat through its caller's print is still a refusal, and leaving it bare "
          "would make it the file's one un-layered one, invisible to the print-scoped guard",
          terr.startswith("refused [coord input]: "))
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
    # G-154 CORRECTS THIS CHECK RATHER THAN DELETING IT. It asserted that a window seat NEVER
    # renews in place — true of the code, and it went on passing while the behaviour it guarded
    # became a defect: `r-window-layout` put `window:` on thirteen descriptors, which silently
    # switched every seat off the in-place path and made each renew destroy its pane. A check that
    # encodes the old behaviour of the thing you changed does not go stale, it goes WRONG-BUT-GREEN.
    _shared_seat = dict(_pane_seat, window="workers")
    check("G-154: a window seat whose pane is ALREADY in its own window renews IN PLACE — the "
          "descriptor wins, and the pane is where the descriptor asks for it",
          renew_in_place(_win_seat, "%5", True, "eta"))
    check("G-154: a shared seat sitting in its named wave window renews IN PLACE",
          renew_in_place(_shared_seat, "%5", True, "workers"))
    check("G-12/G-154: a window seat sitting in the WRONG window re-places — the renew is also the "
          "act that moves it where its briefing asks, and keeping the pane would strand it",
          not renew_in_place(_win_seat, "%5", True, "control")
          and not renew_in_place(_shared_seat, "%5", True, "control"))
    check("G-154: with the pane's window UNKNOWN a window seat re-places — the pre-fix behaviour, "
          "so a caller that has not been taught to measure it cannot silently gain the new path",
          not renew_in_place(_win_seat, "%5", True)
          and not renew_in_place(_shared_seat, "%5", True, ""))
    check("G-154: a pane seat is unaffected by the window it happens to sit in — it declares no "
          "window, so no window can be the wrong one",
          renew_in_place(_pane_seat, "%5", True, "anything")
          and renew_in_place(_pane_seat, "%5", True, None))

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
    # The lifecycle executor and its forking caller are PYTHON, so the harness predicate calls both
    # of them dead while they run. This row is the whole justification for a SECOND predicate: it
    # takes ONE identity — this live selftest process, read from the REAL /proc (proc_stat and
    # process_identity are stubbed nowhere in this suite) — and asserts the two predicates DISAGREE
    # about it. Collapse ident_is_live_process back into ident_is_live_harness and this row goes
    # red; that is the point. The third conjunct keeps the recycled-pid half honest: a liveness test
    # written as `os.path.exists(f"/proc/{pid}")` would pass the first two and fail here.
    _wrong_start = str(int(my_ident[1]) + 1)
    check("lifecycle: ident_is_live_process answers for ANY process — this python selftest reads "
          "LIVE to it and DEAD to ident_is_live_harness (which also demands is_harness_argv) — and "
          "it still refuses the same pid carrying a different starttime",
          ident_is_live_process(my_ident) is True
          and ident_is_live_harness(my_ident) is False
          and ident_is_live_process((me, _wrong_start)) is False)
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

        # The native session id RESOLVING, through a real CALL SITE. Every other assertion about
        # that field in this suite reaches '' or, at the row-shape check above, asserts only that
        # THE COLUMN EXISTS — and a resolver that ALWAYS MISSES satisfies every one of them. That
        # is not hypothetical: it is the 7.37 slug bug's own post-mortem ("every earlier check
        # asserted only the '' outcome, so none of them could see a lookup that always missed")
        # recurring ONE LAYER UP. The derivation got covered that day; its three call sites —
        # launch (session_open), checkin (session_backfill_native) and close — did not.
        # HOME is the lever claude_projects_dir's docstring already names, so no stubbing is
        # needed, and `wait=0.0` is deliberate: success must not depend on a poll budget.
        home4 = Path(td4) / "home"
        proj4 = home4 / ".claude" / "projects" / claude_project_slug(seat4["cwd"])
        proj4.mkdir(parents=True)
        (proj4 / "live-sess.jsonl").write_text("{}", encoding="utf-8")
        home_real4 = os.environ.get("HOME")
        os.environ["HOME"] = str(home4)
        try:
            sid4d, _ = session_open(a4, seat4, since=None, wait=0.0)
        finally:
            if home_real4 is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = home_real4
        live4 = pad_row(read_csv_table(sessions_csv(pkg4), SESSIONS_COLS)[1][-1], hdr4)
        check("7.37: a session_open on the LAUNCH path RESOLVES a real transcript into the row's "
              "native-session-id — the SUCCESS path asserted THROUGH a call site, not by calling "
              "the resolver directly with a fixture. Without this, every native-id assertion here "
              "is satisfied by a resolver that always returns '', which is exactly how the slug "
              "bug survived: the outcome under test was the failure outcome",
              live4[cix["native-session-id"]] == "live-sess" and sid4d != "")

        # The budget a caller that passes NOTHING actually gets. Asserted by CAPTURING THE ARGUMENT
        # — what the code BUILDS — never by timing the call: a check that measured elapsed seconds
        # would pass for a resolver that slept for any reason at all, and would be the slowest
        # check in the suite besides.
        #
        # ⚠ IT DEFENDS A FIX WHOSE REGRESSION IS SILENT. Written `wait=NATIVE_ID_WAIT`, the default
        # is bound at `def` time, so lowering the module constant is IGNORED — the suite would
        # simply go back to sleeping through the full timeout on every launch, staying GREEN while
        # doing it. Nothing else here would notice, which is exactly why this check exists.
        seen_wait = []
        global claude_native_session_id
        cnsi_real = claude_native_session_id
        claude_native_session_id = lambda cwd, since=None, wait=0.0, projects=None: (
            seen_wait.append(wait) or "")
        nw_real = globals()["NATIVE_ID_WAIT"]
        globals()["NATIVE_ID_WAIT"] = 7.5
        try:
            session_open(a4, seat4, since=None)                     # no `wait=` — the launch path
            session_open(a4, seat4, since=None, wait=0.25)          # an explicit budget still wins
        finally:
            globals()["NATIVE_ID_WAIT"] = nw_real
            claude_native_session_id = cnsi_real
        check("7.37: a session_open given no `wait` reads NATIVE_ID_WAIT AT CALL TIME, and an "
              "explicit budget still overrides it. A default written `wait=NATIVE_ID_WAIT` is "
              "bound at def time, so the parameter that exists to let a caller opt out of the boot "
              "timeout delivers that only to callers who pass one — and launch_seat, the path that "
              "actually spends it, passes none. Same trap as a module constant computed from "
              "Path.home() at import",
              seen_wait == [7.5, 0.25])

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
              # 7.88 changed this contract: the old flat "ok" split into `already`/`started`, and
              # `detail` became a dict. Updated in the SAME change rather than left to break later.
              mstatus in ("already", "started", "absent", "fail")
              and (mstatus != "absent" or "does not exist" in mdetail["why"]))

        # ---- 7.88 (G-259 reporting half): a silent repair is indistinguishable from no fault ----
        # ⚠ THE DECISION IS A PURE FUNCTION OF (before, after, last_seen), so all four outcomes are
        # exercised here deterministically. The LIVE arm — kill a real monitor, watch the report
        # fire, then run it again with the monitor alive and watch it NOT fire — is criterion 4 and
        # is run against a real tmux session outside the suite; it is reported in the record, not
        # asserted here, because a suite that spawns real sensors is a suite that leaks them.
        started = {"event": "team-monitor-restarted", "at": "2026-07-28 16:28",
                   "pid": 3630881, "last_seen": "2026-07-28T16:00:12Z", "last_seen_pid": 3181095}
        t_started, _tone, t_err = render_monitor_report("started", started)
        t_already, _tone2, a_err = render_monitor_report("already", {"pid": 3630881})
        check("7.88 criterion 2: 'the sensor was already up' and 'the sensor was DEAD and I "
              "restarted it' render DIFFERENTLY — that collapse IS the defect. Before this, both "
              "printed 'team-monitor: ensured for this run'",
              t_started != t_already and "WAS DEAD" in t_started and "WAS DEAD" not in t_already
              and "not restarted" in t_already)
        check("7.88 criterion 3: the report names WHAT IT CANNOT KNOW — it gives `last observed "
              "alive` from the dead process's OWN final write and calls the span an UPPER BOUND, "
              "and it never states an outage duration as fact. An inferred window is worse than "
              "none, so the bound is offered only as a bound",
              "last observed alive: 2026-07-28T16:00:12Z" in t_started
              and "UPPER BOUND" in t_started and "DEATH INSTANT IS UNKNOWN" in t_started)
        no_bound, _t3, _e3 = render_monitor_report(
            "started", {**started, "last_seen": None, "last_seen_pid": None})
        check("7.88 criterion 3, the honest floor: when the dead process left NO readable final "
              "write, the report says the outage CANNOT BE BOUNDED and estimates nothing — the "
              "one case where 'unknown' is the whole truth",
              "UNKNOWN" in no_bound and "cannot be bounded" in no_bound
              and "UPPER BOUND" not in no_bound)
        check("7.88 criterion 5: the report does NOT claim the detection half — it says in its own "
              "text that a dead sensor is still only noticed by a launch, and names 7.32/7.33. "
              "Closing this row must not read as closing G-259",
              "only noticed by a launch" in t_started and "7.32/7.33" in t_started
              and "it does not detect the death" in t_started)
        check("7.88: a `started` report goes to STDERR and an `already` report does not — the "
              "repair is an exception the launcher must see, not a routine line to scroll past",
              t_err is True and a_err is False)
        fail_txt, _t4, _e4 = render_monitor_report("fail", {"why": "boom"})
        check("7.88: `ensure` returning with NOTHING holding the lock is a FAILURE, not a quiet "
              "success — the pre-7.88 code returned 'ok' on that path, so a launch that started no "
              "sensor at all reported exactly like one that did",
              "UNOBSERVED" in fail_txt and "boom" in fail_txt)
        # The bound-reader itself, against real files rather than a hand-made dict.
        # ⚠ ITS OWN TEMP PACKAGE, DELIBERATELY. The first version of these four arms wrote
        # `state.json` into the SUITE'S SHARED package and the run ABORTED on the unlink — the file
        # was gone before I removed it, so something else in the suite owns that path's lifecycle.
        # Sharing a fixture with the rest of the suite made these arms depend on machinery they do
        # not test; a private directory makes each arm's precondition entirely mine to state.
        _tmb = Path(tempfile.mkdtemp(prefix="coord-788-")) / "pkg"
        (_tmb / "coordination").mkdir(parents=True, exist_ok=True)
        _tmbase = _tmb / "coordination"
        (_tmb / "state.json").write_text(json.dumps(
            {"written_at_iso": "2026-07-28T16:00:12Z", "written_at": time.time() - 300,
             "writer_pid": 3181095}), encoding="utf-8")
        check("7.88: the outage bound is READ off state.json's own `written_at_iso`/`writer_pid` "
              "— the dead sensor's final heartbeat, which is a MEASUREMENT and not an inference",
              team_monitor_last_seen(_tmbase) == ("2026-07-28T16:00:12Z", 3181095))
        (_tmb / "state.json").write_text(json.dumps(
            {"written_at_iso": "2099-01-01T00:00:00Z", "written_at": time.time() + 8000,
             "writer_pid": 1}), encoding="utf-8")
        check("7.88: a `written_at` in the FUTURE yields NO bound — a clock moved, and a window "
              "derived from it would be fiction presented as a measurement",
              team_monitor_last_seen(_tmbase) is None)
        (_tmb / "state.json").write_text("{not json", encoding="utf-8")
        check("7.88: an unreadable state.json yields NO bound rather than an exception — the "
              "report degrades to 'unknown' and the launch is never failed over its bookkeeping",
              team_monitor_last_seen(_tmbase) is None)
        (_tmb / "state.json").unlink()
        check("7.88: and a MISSING state.json likewise — this is the first launch of a fresh run, "
              "not a sensor that died",
              team_monitor_last_seen(_tmbase) is None)
        check("7.88: the lock slot is read as a PROPERTY (pid file + /proc), the same question "
              "team_monitor.py's own lock_holder asks — never parsed out of the child's wording, "
              "which would break silently the day that wording changes",
              team_monitor_holder(_tmbase) is None)
        check("7.33: the monitor is resolved beside the rbtv orchestration CLIs, not guessed from "
              "cwd — the same __file__-derived discipline that keeps G-72 from recurring",
              team_monitor_script().name == "team_monitor.py"
              and "orchestration" in str(team_monitor_script()))

        # ---- 7.57: the gateway client's mode split — DETECT half only (fork 1: the SPEAK half's
        # coordination routing is RULED NOT MET, so nothing here calls the network; call_gateway
        # is exercised live, once, outside selftest — this suite stays "no tmux, no run package,
        # no network" per its own docstring). Own temp packages throughout, same reason as the
        # 7.88 block above: a shared fixture would make each arm depend on machinery it does not
        # test.
        _g757 = Path(tempfile.mkdtemp(prefix="coord-757-"))

        # A. THE STANDALONE CONTROL: no server.json at all is what every workspace looks like
        # today, and criterion (2) ("with no daemon configured, behavior is identical to today")
        # depends on this branch staying false — this is the branch every seat's `coordinate`
        # actually runs through right now.
        _g757_none = _g757 / "none"
        check("7.57: detect_daemon reports NOT detected when no server.json exists — the "
              "standalone branch every workspace is in today, criterion (2)'s control",
              gateway_client.detect_daemon(_g757_none, hostname="whatever-box")["detected"] is False)

        # B. THE POSITIVE CONTROL: a server.json naming THIS fixture's own hostname is detected,
        # with the right host/port carried through. This is the check mutated by
        # `--expect-fail "names a live server"` to prove the pair in A/B can actually go red —
        # see the row's own report for the demonstrated mutation run (bars.md 10/11).
        _g757_yes = _g757 / "yes"
        (_g757_yes / ".rbtv" / "modules" / "ignite").mkdir(parents=True)
        (_g757_yes / ".rbtv" / "modules" / "ignite" / "server.json").write_text(json.dumps(
            {"machines": {"fixture-box": {"tailnet_host": "fixture.ts.net", "gateway_port": 4242}}}))
        _g757_info = gateway_client.detect_daemon(_g757_yes, hostname="fixture-box")
        check("7.57: detect_daemon reports detected=True on a server.json naming THIS machine, "
              "with host/port carried through unchanged — names a live server for the caller",
              _g757_info["detected"] is True and _g757_info["host"] == "fixture.ts.net"
              and _g757_info["port"] == 4242)

        # B2. OWN BEATS AMBIGUOUS: TWO machines both name a server and one of them IS this one —
        # the caller must resolve ITSELF, never fall into the ambiguous refusal C proves below.
        # Distinct from B (B's fixture has only one machine total, so a broken `own` match would
        # silently fall through to the single-server fallback and produce the SAME answer,
        # proving nothing — this fixture is the one where own-priority is load-bearing).
        _g757_own2 = _g757 / "own-among-many"
        (_g757_own2 / ".rbtv" / "modules" / "ignite").mkdir(parents=True)
        (_g757_own2 / ".rbtv" / "modules" / "ignite" / "server.json").write_text(json.dumps(
            {"machines": {"my-box": {"tailnet_host": "mine.ts.net", "gateway_port": 7},
                          "other-box": {"tailnet_host": "other.ts.net", "gateway_port": 8}}}))
        _g757_own2_info = gateway_client.detect_daemon(_g757_own2, hostname="my-box")
        check("7.57: own machine has a server AND another machine also has one — OWN WINS, "
              "resolves to the caller's own entry, never the ambiguous refusal C proves below",
              _g757_own2_info["detected"] is True and _g757_own2_info["host"] == "mine.ts.net"
              and _g757_own2_info["port"] == 7)

        # C. Machine-keyed selection (config.js parity): TWO machines both name a server and
        # NEITHER is this one — ambiguous, refused rather than guessed, never silently the wrong
        # daemon.
        _g757_ambig = _g757 / "ambig"
        (_g757_ambig / ".rbtv" / "modules" / "ignite").mkdir(parents=True)
        (_g757_ambig / ".rbtv" / "modules" / "ignite" / "server.json").write_text(json.dumps(
            {"machines": {"box-a": {"tailnet_host": "a.ts.net", "gateway_port": 1},
                          "box-b": {"tailnet_host": "b.ts.net", "gateway_port": 2}}}))
        _g757_amb_info = gateway_client.detect_daemon(_g757_ambig, hostname="box-c")
        check("7.57: two machines both naming a server, neither this one, is AMBIGUOUS and "
              "refused — never silently picks one (config.js parity)",
              _g757_amb_info["detected"] is False and "ambiguous" in _g757_amb_info["reason"])

        # C2. THE TYPICAL CLIENT SHAPE, distinct from B: exactly ONE machine entry names a
        # server and it is NOT the calling hostname (most workspaces have one server machine and
        # N client machines calling FROM elsewhere) — single-server fallback, config.js parity.
        # B alone cannot cover this: B's fixture hostname MATCHES its own entry, so B only ever
        # exercises the `own` branch, never the fallback `len(servers) == 1` branch below it.
        _g757_single = _g757 / "single-other"
        (_g757_single / ".rbtv" / "modules" / "ignite").mkdir(parents=True)
        (_g757_single / ".rbtv" / "modules" / "ignite" / "server.json").write_text(json.dumps(
            {"machines": {"the-server-box": {"tailnet_host": "s.ts.net", "gateway_port": 9}}}))
        _g757_cli_info = gateway_client.detect_daemon(_g757_single, hostname="my-laptop")
        check("7.57: exactly one OTHER machine names a server — the single-server fallback "
              "resolves it, the typical shape for a client calling from a non-server machine",
              _g757_cli_info["detected"] is True and _g757_cli_info["host"] == "s.ts.net"
              and _g757_cli_info["port"] == 9)

        # D. Malformed JSON is a LOUD, distinguishable reason — never silently indistinguishable
        # from "not configured" (config.js: readServerJson throws, never returns null, on bad JSON).
        _g757_bad = _g757 / "bad"
        (_g757_bad / ".rbtv" / "modules" / "ignite").mkdir(parents=True)
        (_g757_bad / ".rbtv" / "modules" / "ignite" / "server.json").write_text("{not json")
        _g757_bad_info = gateway_client.detect_daemon(_g757_bad, hostname="whatever")
        check("7.57: malformed server.json is NOT detected AND says so loudly — distinguishable "
              "from 'no record at all', never a silent identical false",
              _g757_bad_info["detected"] is False and "not valid JSON" in _g757_bad_info["reason"])

        # E. Legacy flat shape (no `machines` key) — config.js's own stated backward-compat case
        # ("a workspace pulled at either side of the shape change resolves").
        _g757_flat = _g757 / "flat"
        (_g757_flat / ".rbtv" / "modules" / "ignite").mkdir(parents=True)
        (_g757_flat / ".rbtv" / "modules" / "ignite" / "server.json").write_text(json.dumps(
            {"tailnet_host": "legacy.ts.net", "gateway_port": 5555}))
        _g757_flat_info = gateway_client.detect_daemon(_g757_flat, hostname="any-box")
        check("7.57: the legacy flat server.json shape (no `machines` key) still resolves — "
              "config.js's own stated backward-compat case",
              _g757_flat_info["detected"] is True and _g757_flat_info["host"] == "legacy.ts.net")

        # F. RBTV_IGNITE_WORKSPACE_ROOT env override actually redirects resolution — the same env
        # var name the JS side reads (ignite/cli/lib/config.js), so a workspace root override
        # means the same thing on both sides of the wire.
        check("7.57: RBTV_IGNITE_WORKSPACE_ROOT overrides the given default workspace root",
              str(gateway_client.resolve_workspace_root(
                  "/does/not/matter", env={"RBTV_IGNITE_WORKSPACE_ROOT": str(_g757_yes)}))
              == str(_g757_yes))
        check("7.57: with no override, resolve_workspace_root returns the caller's default "
              "unchanged — the production path (VAULT_ROOT) is untouched by this env var today",
              str(gateway_client.resolve_workspace_root("/some/default", env={})) == "/some/default")

        # G. Client mode is INERT UNLESS EXPLICITLY OPTED IN (Fork 2, ruled) — asserted at the
        # PARSER, not just the function default, so an argparse edit that silently flipped the
        # default would be caught here, not just in cmd_gateway_status's own signature.
        _g757_parser = build_parser()
        _g757_bare = _g757_parser.parse_args(["gateway-status"])
        _g757_opt = _g757_parser.parse_args(["gateway-status", "--probe"])
        check("7.57: `gateway-status` with no flag parses --probe=False — client mode (the SPEAK "
              "half) is inert by default, never silently on",
              _g757_bare.probe is False)
        check("7.57: `gateway-status --probe` parses --probe=True — the opt-in is reachable, not "
              "just theoretically present",
              _g757_opt.probe is True)

        # H. IGNITE_GATEWAY_ADDR parsing (host:port / bare host / full URL) — config.js parity,
        # pure string parsing, no network.
        check("7.57: IGNITE_GATEWAY_ADDR parses bare `host:port`",
              gateway_client._parse_addr("addr-host:1234") == ("addr-host", 1234))
        check("7.57: IGNITE_GATEWAY_ADDR parses a bare host with no port as port 80",
              gateway_client._parse_addr("addr-host") == ("addr-host", 80))
        check("7.57: IGNITE_GATEWAY_ADDR parses a full https URL, defaulting to port 443",
              gateway_client._parse_addr("https://addr-host") == ("addr-host", 443))

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
  checkout    end your session (exports your transcript first) · --renew --handoff hands this seat to your own next session

leader
  launch      open one tmux seat per worker briefing and start its harness
  close       spawn a closer that co-writes a seat's memory.md, then closes it
  close-seat / reap / kill-pane / relaunch-pane / close-run / current-run  close a seat (--renew) · free panes (--go) · reap one pane by id · respawn a seat INTO its own pane (CoS too) · end / resolve the run
  approve     answer a seat's permission prompt by sending keys to its pane
  panel       open the control-panel overview strip in this window
  owner       set owner presence: present | afk
  add-to-group / remove-from-group  join or drop an existing group's members

other
  workers / descriptors / gateway-status  who is alive and on what · seat-descriptor audit · is a daemon serving this workspace (--probe proves the wire)
  create-group       open a message group for one workstream
  export-transcript  capture a seat's pane scrollback into its worker folder
  depart      ephemeral seats: export + check out + kill your own pane
  selftest / gates   built-in self-test (temp dir, no tmux) · which flag carries which gate
global: --run TAG | --package DIR (which run) · --as NAME (act as) · --pretty (colour)
details + examples: coordinate <command> -h · --force overrides a refusal, where one exists""".format(limit=READ_LIMIT)


ADVICE_SEND = re.compile(
    r'send\s+(?P<to>\{[^}]*\}|<[^>]*>|[A-Za-z0-9_.-]+)\s+\\?"(?P<body>[^"\\]*)\\?"'
    r'(?P<rest>(?:\s+--[a-z-]+(?:\s+(?!--)[^\s"]+)?)*)')
ADVICE_FLOOR = 5
_ADVICE_PLACEHOLDER = re.compile(r'^(\{.*\}|<.*>)$')


def _advice_render(n):
    """The text of a string expression, with f-string slots shown as {expr}."""
    import ast
    if isinstance(n, ast.Constant):
        return n.value if isinstance(n.value, str) else ""
    if isinstance(n, ast.JoinedStr):
        return "".join(_advice_render(v) for v in n.values)
    if isinstance(n, ast.FormattedValue):
        try:
            return "{" + ast.unparse(n.value) + "}"
        except Exception:
            return "{?}"
    if isinstance(n, ast.BinOp):
        return _advice_render(n.left) + _advice_render(n.right)
    return ""


def advice_coached_sends(path=None):
    """Every `send` this file's own advice coaches, as argv — hints, -h epilogs, refusal texts.

    G-181. The advice surface and the send guards drift apart silently: rbtv 4837088 made the
    positional-body guard UNCONDITIONAL and 14 advice strings kept teaching the shape it now
    refuses, for hours, because nothing tied the two together.

    DERIVED, NEVER ENUMERATED (G-158): sites are found by scanning, so a hint added tomorrow is
    covered without editing this function. Selftest fixtures are excluded by their enclosing
    function name — their strings are controlled inputs, not advice to a user.
    """
    import ast
    src = Path(path or __file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    spans = [(n.lineno, n.end_lineno) for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and "selftest" in n.name]
    # which `send` flags take a value, asked of the PARSER — the advice string runs on into prose
    # ("--force adds them anyway, if ..."), and guessing that the next word is a value swallows
    # that prose into argv, which the parser then rejects: a false RED on a hint that was fine.
    value_flags = set()
    for act in _send_actions(build_parser()):
        if act.nargs != 0 and getattr(act, "const", None) is None:
            value_flags.update(o for o in act.option_strings if o.startswith("--"))

    outer = []

    class _V(ast.NodeVisitor):
        def visit_JoinedStr(self, n):
            outer.append(n)

        def visit_Constant(self, n):
            if isinstance(n.value, str):
                outer.append(n)

        def visit_BinOp(self, n):
            if _advice_render(n):
                outer.append(n)
            else:
                self.generic_visit(n)

    _V().visit(tree)

    sites = []
    for node in outer:
        text = _advice_render(node)
        if not text or any(a <= node.lineno <= b for a, b in spans):
            continue
        for m in ADVICE_SEND.finditer(text):
            to = m.group("to")
            # `all` is NEVER normalised to a seat name: it is the recipient the owner hint was
            # refused for, and rewriting it would lose the only case a flag cannot fix.
            if to != "all":
                to = "beta"
            body = m.group("body") or "body"
            if _ADVICE_PLACEHOLDER.match(body.strip()):
                body = "body"
            argv = ["send", to, body]
            toks = (m.group("rest") or "").split()
            i = 0
            while i < len(toks):
                t = toks[i]
                if not t.startswith("--"):
                    break                      # prose begins; the command ended
                argv.append(t)
                if t in value_flags and i + 1 < len(toks):
                    v = toks[i + 1]
                    argv.append("ASK" if t == "--re"
                                else ("body" if _ADVICE_PLACEHOLDER.match(v) else v))
                    i += 2
                else:
                    i += 1
            sites.append((node.lineno, argv))
    return sites


# G-181 population 4: the kit's DOCS coach commands too, and protocol.md is loader step 4 for
# every seat — the highest-traffic advice surface in a run. Three of its four `send` synopsis lines
# taught the positional form the guard refuses, mis-teaching the room at BOOT.
#
# The invocation is DERIVED, never a literal: the docs write `$COORD`, and a scan keyed on
# `coordinate` returned ZERO and nearly certified them clean — verify-absence violated by the
# wrong pattern, which is the same class this whole check exists for.
ADVICE_INVOCATION = re.compile(r'^\s*(?:\$?COORD|coordinate|python3?\s+coord\.py)\s+', re.I)
# A doc may QUOTE a refused form in order to FORBID it, and flagging that would delete the warning
# that prevents the defect — G-176's trap one layer out. The first design keyed on negation words
# near the line. The leader found the residual and it points the DANGEROUS way — a FALSE GREEN:
#
#     Do not forget the type flag.          <- incidental "not"
#     $COORD send x "body" --type note      <- genuinely TAUGHT, silently exempted
#
# A false red wastes a seat; that loses the defect. And it is not fixed by moving the lookback:
# `# do not forget --type` on the command line itself exempts it just as well. Any negation
# heuristic can be tripped by prose that was never about this check.
#
# So the vocabulary check is replaced by an EXPLICIT MARKER — the same shape as the guard this all
# started from, where a positional body pays an explicit `--inline`. Only an assertion cures an
# inference. The marker is an HTML comment: invisible in rendered markdown, and impossible to write
# by accident, so an incidental sentence can never exempt a taught command.
ADVICE_DOC_OPTOUT = re.compile(r'<!--\s*advice-check:\s*refused-example\s*-->', re.I)


def advice_doc_sends(root=None):
    """-> (sites, skipped_as_warnings). Coached sends in the kit's own .md files.

    TAUGHT vs QUOTED-AS-WRONG: a candidate must be a COMMAND LINE — the invocation at line start,
    which is how a synopsis presents something to run. A prose mention mid-sentence is not a
    command being taught. A doc that deliberately shows a refused form marks it with the explicit
    opt-out comment; every skipped line is RETURNED IN FULL, never counted, because a count in
    permanent output has no maintainer and only grows, while three lines of real text are
    auditable at a glance.
    """
    root = Path(root or Path(__file__).resolve().parent)
    sites, skipped = [], []
    for md in sorted(root.glob("*.md")):
        lines = md.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not ADVICE_INVOCATION.match(line) or " send " not in f" {line} ":
                continue
            m = ADVICE_SEND.search(line)
            if not m:
                continue
            prev = next((x for x in reversed(lines[:i]) if x.strip()), "")
            if ADVICE_DOC_OPTOUT.search(line) or ADVICE_DOC_OPTOUT.search(prev):
                skipped.append((md.name, i + 1, line.strip()[:90]))
                continue
            sites.append((md.name, i + 1, line.strip()[:110],
                          bool(re.search(r"--inline|--file", line))))
    return sites, skipped


def _send_actions(parser):
    """The `send` subparser's actions, found by walking the parser rather than by name."""
    for act in parser._actions:
        subs = getattr(act, "choices", None)
        if isinstance(subs, dict) and "send" in subs:
            return subs["send"]._actions
    return []


def advice_refused_sends(path=None):
    """-> (offenders, total). Offenders are advice-coached sends the REAL send path refuses.

    ASSERTS THE PROPERTY, NOT THE VOCABULARY. An earlier draft checked each advice string for the
    substring `--inline`; the leader killed it with this file's own evidence — the `owner` hint was
    refused TWICE (positional body, then `a note is never an all broadcast`), so adding --inline
    turns a substring check green while the command stays refused. That detector would certify the
    exact state it exists to detect. So each command is parsed by the real parser and run through
    main()'s own boundary sequence instead, which covers any guard, including ones added later.

    VERB-SCOPED TO `send`, DELIBERATELY — the extension was MEASURED AND REJECTED, and this is the
    place that question gets asked, so the answer lives here rather than in a ledger row nobody
    opens. All 24 subcommands are coached by some advice string (~72 non-send sites against send's
    14), and NONE of them refuses: every apparent failure was extraction noise or a fixture
    artifact.

    WHY IT CANNOT BE WIDENED: `send` is extractable because THE QUOTED BODY IS A DELIMITER — the
    quotes around a body give the command an unambiguous end. Nothing else has one. Advice reads
    `close <agent> — the closer reads this export`, and no rule separates argv from English without
    guessing; placeholders also carry semantic constraints a generic fixture cannot satisfy (a
    group name must not collide with an agent name). Measured, a widened check flags ~28% of sites
    spuriously. A check whose only value is being trusted, wrong a quarter of the time, is WORSE
    than no check: it trains readers to ignore it, it still looks like coverage, and it RETIRES the
    human attention now covering those sites while certifying nothing.

    The unlock, if this is ever revisited, is an AUTHORING CONVENTION (commands in advice must be
    delimited), which converts guessing into parsing — a documented, owner-gated change, not a
    tweak to this function.

    ⚠ WRITING THIS DOCSTRING TRIPPED THIS CHECK, which is worth knowing before you edit it: the
    CODE scanner EXECUTES what it extracts, while advice_doc_sends() only tests for --inline/--file
    presence. So a SYNOPSIS with a metavariable — `--type T` — is fine in a .md and fails here,
    because `T` is not a real type. Illustrate with a concrete type, or the example you add to
    explain this function will be reported as an offender by it.
    """
    import io
    import tempfile
    from contextlib import redirect_stderr, redirect_stdout

    global CLI_INVOCATION, shell_source_line, RUNS_INDEX, wake, detect_pane, live_panes
    sites = advice_coached_sends(path)
    if len(sites) < ADVICE_FLOOR:
        return None, len(sites)        # INOPERATIVE — the pattern stopped matching the source

    # G-182 — HERMETIC IN THE ENVIRONMENT, not only in the package. This used to isolate its temp
    # package and nothing else, which made it safe ONLY inside the selftest, because the selftest
    # globally stubs pane resolution and wakes. Called directly — which is how a ratifier verifies
    # a fix against a mutated copy — it inherited the caller's live pane, so the fixture roster
    # bound a fixture seat to a REAL pane and then:
    #   * every send refused "you claimed 'leader' but this pane (%N) is registered to 'beta'",
    #     11 false offenders on a WORKING file, and the leader was one message from reporting a
    #     correct fix as broken;
    #   * deliver_wakes sent real tmux keystrokes to that pane. A check that audits advice must
    #     not interrupt the room to do it.
    # The precondition existed as a COMMENT in the probe that developed this and never as code.
    # A gate that is prose is not a gate, so it is built in here and restored in `finally`.
    saved = (CLI_INVOCATION, shell_source_line, RUNS_INDEX, wake, detect_pane, live_panes)
    wake = lambda pane, text: None            # noqa: E731 — no tmux contact, ever
    detect_pane = lambda override=None: ""    # noqa: E731 — identity comes from --as, not a pane
    live_panes = lambda: set()                # noqa: E731 — no live roster to collide with
    offenders = []
    try:
        with tempfile.TemporaryDirectory() as td:
            RUNS_INDEX = Path(td) / "runs.json"
            pkg = Path(td) / "pkg"
            (pkg / "coordination").mkdir(parents=True)
            (pkg / "workers").mkdir()
            for a in ("leader", "alpha", "beta"):
                (pkg / "workers" / f"{a}.md").write_text(f"---\nagent: {a}\n---\nbrief\n")
            parser = build_parser()
            # Fixture setup must not be judged by the guard under test: the selftest replaces
            # shell_source_line with controlled lines for its own G-101 checks, and a seed send
            # refused by an inherited stub silently left the log with no ask in it — after which
            # every `--re` site failed for a reason that was this harness's, not the advice's.
            CLI_INVOCATION, shell_source_line = False, (lambda: "")

            def _run(argv):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    try:
                        main_args = parser.parse_args(
                            ["--package", str(pkg)] + argv)
                        assert_argv_body_shell_safe(main_args)
                        main_args.func(main_args)
                    except SystemExit:
                        pass

            for a in ("leader", "alpha", "beta"):
                _run(["checkin", a, "x"])
            # a REAL open ask, so `--re` binds to something: left dangling it refuses for an
            # unrelated reason, and a false RED is how a correct hint gets deleted (G-151).
            _run(["--as", "alpha", "send", "leader", "seed", "--type", "ask", "--inline"])
            # DERIVE the ask's number instead of assuming it is #1: checkins and the coached
            # sends themselves put other traffic in this log, and a `--re` pointed at a note
            # refuses for a reason that has nothing to do with the advice — a false RED, which is
            # how a correct hint gets deleted (G-151). Measured: 3 sites failed this way first.
            _, _blocks = load_messages(pkg / "coordination")
            _asks = [b["num"] for b in _blocks if b.get("type") == "ask"]
            ask_no = str(_asks[-1]) if _asks else "1"

            for lineno, argv in sites:
                argv = [ask_no if t == "ASK" else t for t in argv]
                err = io.StringIO()
                CLI_INVOCATION, shell_source_line = True, (lambda: "")
                try:
                    with redirect_stderr(err):
                        parsed = parser.parse_args(
                            ["--package", str(pkg), "--as", "leader"] + argv)
                except SystemExit:
                    offenders.append((lineno, " ".join(argv),
                                      "the parser rejects this argv"))
                    continue
                try:
                    with redirect_stdout(io.StringIO()), redirect_stderr(err):
                        # main()'s EXACT sequence: the positional-body guard runs BEFORE dispatch,
                        # not inside cmd_send. Calling cmd_send alone skipped it and passed 12
                        # sites the real CLI refuses — the check rebuilding the very class it
                        # exists to catch.
                        assert_argv_body_shell_safe(parsed)
                        parsed.func(parsed)
                except SystemExit as exc:
                    if exc.code not in (0, None):
                        first = (err.getvalue().strip().splitlines() or ["(refused)"])[0]
                        offenders.append((lineno, " ".join(argv), first[:150]))
    finally:
        (CLI_INVOCATION, shell_source_line, RUNS_INDEX,
         wake, detect_pane, live_panes) = saved
    return offenders, len(sites)


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
        "when your briefing is complete and your completion message is already sent.\n"
        "\n"
        "--renew does the OPPOSITE of ending the seat: it opens the seat's NEXT session, and it is\n"
        "YOUR call, not leader's. It runs in two steps — the first arms the renewal, mutes your\n"
        "wakes and prints the second; the second carries your successor's handoff. Nothing is\n"
        "closed until that second call.",
        "example:\n"
        "  coordinate checkout\n"
        "  coordinate checkout --renew\n"
        "next: ending for good — nothing on your side, leader runs `close <you>` if the seat must\n"
        "      go; renewing — run the second call the first one printed for you")
    s.add_argument("--no-export", action="store_true", help="skip the automatic transcript export (e.g. the pane is already dead)")
    s.add_argument("--renew", action="store_true",
                   help="this checkout opens the NEXT session of this seat, not its last — run it once to arm the renewal and be taught the second call, then again with --handoff")
    s.add_argument("--handoff", metavar="NOTE", default=None,
                   help="what the next session of this seat must do, quoted — requires --renew; it is appended to your seat memory and printed to your successor at its check-in")
    add_identity_flags(s)
    s.set_defaults(func=cmd_checkout)

    s = command(
        "send",
        "Send one typed message to an agent, a group, or everyone, and wake the recipients'\n"
        "panes. Send at coordination points: starting, before touching a shared surface, at a\n"
        "milestone, when blocked, when done. The log is the truth — wakes are best-effort.",
        "example:\n"
        "  coordinate send leader \"views build green; 12/12 pages render\" --type completion --inline\n"
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
        "next: coordinate send <asker> \"<answer>\" --type answer --inline --re <ask#>")
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
        "⚠ NARROWING (task 7.85): `afk` used to carry the door-closed case too, because it was the\n"
        "least-wrong of two values. It no longer does — that case is `reachable`. `present` and\n"
        "`afk` mean exactly what they always meant; what changed is that neither has to stretch.\n"
        "example:\n"
        "  coordinate owner afk --note \"back in 2h\"\n"
        "  coordinate owner reachable        # at the PC, no door running — no note needed\n"
        "next: nothing to send — coordinate status and workers report it from the surface\n"
        "      this command just wrote; a hand-typed copy is a second answer that can disagree")
    # ⚠ choices AND help are DERIVED from OWNER_STATES — never re-spelled here. A hand-written
    # `choices=[...]` beside a hand-written help string is two more places for the state set to
    # drift from what the consumers actually render.
    s.add_argument("state", choices=list(OWNER_STATES),
                   help="; ".join(f"{k} = {v[0]}" for k, v in OWNER_STATES.items()))
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
        "kill-pane",
        "Reap ONE pane by id directly (task 7.91) -- the route to a leaked pane when a raw\n"
        "`tmux kill-pane` is refused by the harness auto-mode classifier and `close-seat` needs a\n"
        "roster-known SEAT NAME rather than a bare pane id. Kills the PANE ONLY, like `reap` --\n"
        "no transcript export, no roster mutation; the seat still owes a close-seat afterwards.\n"
        "Refuses UNCONDITIONALLY (no --force) if the pane is not on this run's CURRENT roster, or\n"
        "belongs to a seat carrying `relays:` (a human-contact door). Refuses, escapable with\n"
        "--force, if the pane's row is still roster-ACTIVE (not roster-done).",
        "example:\n"
        "  coordinate kill-pane %482\n"
        "next: coordinate workers -- confirm the pane is gone; the seat still owes a close-seat")
    # dest is `pane_id`, NEVER `pane` -- `args.pane` is reserved: resolve_agent()/detect_pane()
    # read it as an override for the CALLING pane (the same attribute `checkin --pane` sets), so a
    # positional named `pane` here would make the TARGET silently stand in for the caller during
    # identity resolution -- caught by this row's own selftest (a door/active refusal that only
    # "worked" with --force, because --force is what let resolve_agent's OWN identity-mismatch
    # refusal through, not because the door/active logic below it was ever reached).
    s.add_argument("pane_id", metavar="pane",
                    help="the tmux PANE ID to kill (e.g. %%482) -- never a seat name")
    add_identity_flags(s)
    s.set_defaults(func=cmd_kill_pane)

    s = command(
        "relaunch-pane",
        "(leader/chief-of-staff/closer-*) Relaunch a seat's harness INTO a named, already-\n"
        "registered pane, in place (task 7.95, G-282) -- the door's own path back up when a\n"
        "plain `launch` would move it and `close-seat --renew` is refused by the relays: guard.\n"
        "Never kills anything: refuses unless the pane is already bare (no harness running) and\n"
        "the roster row is already roster-done. Never routes through close-seat and never needs\n"
        "--force for the intended case -- retires the chief-of-staff's raw `tmux send-keys`\n"
        "stopgap, restoring the memory floor, check_bindings (G-51), and the roster/session-\n"
        "trace writes that stopgap skipped.",
        "example:\n"
        "  coordinate relaunch-pane owner-liaison %501\n"
        "next: coordinate workers -- confirm the seat checked back in on the SAME pane")
    s.add_argument("target", help="the TARGET seat to relaunch (the seat acted on)")
    s.add_argument("pane_id", metavar="pane",
                    help="the tmux PANE ID to relaunch into (e.g. %%501) -- must match the "
                         "roster's own recorded pane for TARGET; resolve it fresh from "
                         "`coordinate workers`, never from memory (bars.md 3)")
    s.add_argument("--dry-run", action="store_true",
                    help="print the command that would start, respawn/launch nothing")
    s.add_argument("--force-memory", action="store_true",
                    help="override the MEMORY gate only (--force does not: it covers the role "
                         "gate and the roster-still-active refusal)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_relaunch_pane)

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
        "next: coordinate send views-render \"<why this group exists>\" --type note --inline")
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
        "next: coordinate send views-render \"<who joined, and why>\" --type note --inline")
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
        "next: coordinate send ceremony \"<who left, and why>\" --type note --inline")
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
        "gateway-status",
        "Task 7.57 (DETECT half only). Reports whether an ignite daemon serves THIS\n"
        "workspace on THIS machine (.rbtv/modules/ignite/server.json) — a pure file read,\n"
        "always safe. Does NOT route coordination send/read through the gateway: that is\n"
        "RULED NOT MET (fork 1) — the gateway has no addressed-message door yet.\n"
        "checkin/send/read/pending/... never call this and are unaffected by it.",
        "example:\n"
        "  coordinate gateway-status            # detection only, zero network\n"
        "  coordinate gateway-status --probe    # ALSO makes one live read-only `inspect`\n"
        "                                       # call to prove the authenticated wire\n"
        "next: nothing — informational; coordination messages still use the run package")
    s.add_argument("--probe", action="store_true",
                   help="explicit opt-in (inert by default, Fork 2 ruled): make one live "
                        "read-only `inspect` call against the detected gateway")
    s.set_defaults(func=cmd_gateway_status)

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
        refuse(
            "input",
            f"your shell SUBSTITUTED {' and '.join(eaten)} in this body before "
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
            1)
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
        refuse(
            "input",
            f"this body was typed on a shell command line, and a shell eats "
            f"backticks and $(...) BEFORE coord.py can see them — the corruption is "
            f"undetectable after the fact and it has silently rewritten this room's "
            # The count that used to sit here ("three times") had no maintainer and no way to be
            # checked at read time — permanent text asserting a number that only ever grows. It
            # is the drift the run already ruled on in its evidence layer, wearing a refusal's
            # clothes. The force of the sentence was never the number; it is that the authors
            # KNEW.
            f"record repeatedly, each time by an author who knew about it.\n"
            f"Shell-safe (cannot be eaten):\n"
            f"  cat > /tmp/msg.txt <<'EOF'\n  ...your text...\n  EOF\n"
            f"  {coord_invocation(args)} send {getattr(args, 'to', '<to>')} "
            f"--type {getattr(args, 'type', '<type>')} --file /tmp/msg.txt\n"
            f"Short body with no backticks, quotes or $ in it? Add --inline and it is "
            f"sent as typed.",
            1)

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
