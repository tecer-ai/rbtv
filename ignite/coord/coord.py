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

Stdlib only; no PATH install. The pane-sensor `team_monitor.py` (`orchestration/team-monitor/`,
successor to the retired `watch.py`) is deleted [T4-R8, del-observers]: a terminal pane is a
viewport, never a heartbeat, and "is it alive" is answered by the supervisor registry (not yet
built), never by a standalone monitor.
"""
import argparse
import csv
import difflib
import functools
import hashlib
import json
import os
import re
import shlex
import signal as signal_mod
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
import ending_store  # noqa: E402 — kit door onto the ONE ending store (spec-state-store §4.1)
import supervisor_door  # noqa: E402 — kit door onto the ONE death stamp (spec-supervisor §3/§4)
import liveness  # noqa: E402 — the ONE liveness surface: is this sitting alive (spec-supervisor §6)

# ⚠ ONE NAMESPACE, ALWAYS NAMED `coord`. `supervisor/`'s six modules `import coord` and read its
# names at call time; running this file directly would execute it a SECOND time under the name
# `coord`, leaving the CLI in `__main__`'s copy and every supervision module bound to the other —
# two namespaces, and every selftest stub landing in the one nobody reads. So a direct run is a
# TRAMPOLINE: re-enter through the import machinery and dispatch there. Nothing below this point
# executes under `__main__`.
if __name__ == "__main__":
    # ⚠ RE-ENTERED BY PATH, NEVER BY NAME. `import coord` would resolve through sys.path and could
    # execute a DIFFERENT coord.py than the one invoked — which is exactly what `save-coord.py`'s
    # gate runs (`python3 <candidate> --help`): by-name re-entry made every candidate test the
    # INSTALLED kit and pass, mutant or not. Loading `__file__` under the name `coord` runs THIS
    # file, once, in the one namespace everything else binds to.
    #
    # ⚠ THE LOADER MUST BE NAMED EXPLICITLY. `spec_from_file_location` with no `loader=` guesses
    # one from `__file__`'s extension — and `__file__` is whatever name invoked this script, which
    # under an extension-less `~/.local/bin/coordinate` symlink has no `.py` suffix. No suffix
    # matches no loader, `spec_from_file_location` returns `None`, and `module_from_spec(None)`
    # dies with `AttributeError: 'NoneType' object has no attribute 'loader'`. Passing a
    # `SourceFileLoader` directly reads and compiles `__file__` as source regardless of the name it
    # was invoked under, while still re-entering BY PATH — the by-name hazard above is unchanged.
    import importlib.util as _ilu
    from importlib.machinery import SourceFileLoader as _SourceFileLoader
    _spec = _ilu.spec_from_file_location(
        "coord", __file__, loader=_SourceFileLoader("coord", __file__)
    )
    _mod = _ilu.module_from_spec(_spec)
    sys.modules["coord"] = _mod
    _spec.loader.exec_module(_mod)
    sys.exit(_mod.main())

try:  # POSIX advisory locking. Absent (or unusable) -> every lock falls back to lockless.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None


VAULT_ROOT = "/home/henri/ht-wkdir/second-brain"
CLAUDE_BIN = os.environ.get("COORD_CLAUDE_BIN", "claude")
CODEX_BIN = os.environ.get("COORD_CODEX_BIN", "codex")
OPENCODE_BIN = os.environ.get("COORD_OPENCODE_BIN", "opencode")
# T1/7.400: every launched seat's tmp writes (harness captures, session state, startup
# extraction) redirect here — off the quota'd usr-quota tmpfs backing `/tmp`, onto `/dev/sda1`.
# Bound into `identity_prefix()`, the one env-prefix door every harness command passes through
# (`harness_command` AND `resume_command` both build from it) — never `TMUX_TMPDIR`, which binds
# a process to one tmux SERVER and is untouched by this (coord.py:5502).
AGENT_TMPDIR = "/home/henri/.cache/agent-tmp"
DEFAULT_EFFORT = "high"
HARNESSES = ("claude", "codex", "opencode")
HARNESS_PROCS = HARNESSES
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
SPECIAL_CASE_SEATS = {"engineer"}
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
# The `watcher` seat's broadcast carve expired WITH the seat (retired 2026-08-13, owner-ruled):
# the deterministic watch layer (team-monitor CMP-20 + goal-watcher-job CMP-21) replaced the
# agentic seat per `d-watcher-deterministic-chain`, and DAG-unblocking is the edge-runner's
# monopoly (CMP-25) — no seat rides broadcasts for it. Do not re-add the name.
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
# P2 — the registry's canonical message types (concepts/message.md): the SOLE vocabulary.
#
# ⚠ CLOSED AT EIGHT (W4 closed it at seven; D2 added the eighth). Each addition past the original
# five has ONE consumer that justifies it:
#   queue-request  ENGINE-INTERNAL. A judged milestone PASS asking for the next wave to be seeded.
#                  Its consumer arrives in W7; until then `_append_message_unlocked` REFUSES it, so
#                  the type exists on every door before anything can write a row nobody drains.
#   escalation     OWNER-DIRECTED. A halt the leader (or the two-strikes judge) could not fix. It
#                  succeeds the `type: verdict` + ESCALATION_MARKER encoding, which is dual-read
#                  for rows already on live buses.
#   stuck          SYSTEM-ROUTED (owner ruling D2, 2026-08-19). An agent — or the watcher — says it
#                  is blocked and does NOT say to whom: the routing table below picks the recipient
#                  (always the `leader`, which escalates to the owner what it cannot solve). Its
#                  consumer EXISTS TODAY and is why the type is not writer-held: a staff chair
#                  spawns a sitting on unread mail, and `stuck` is addressed to the leader.
# The enum is copied at SEVEN sites and they move in ONE change (adv, C39): here, `TYPE_COLOR`
# below, both argparse `--type` sites, `server/heart/heart-store.js`, `server/internal-api/
# dispatch.js`, `runtime/gateway/parse.js`, `chat/forward-path.js`, plus `heart/schema.sql`'s CHECK
# (a table REBUILD — migration 5 `message-types-seven-w4`, then migration 7
# `message-types-eight-stuck`). A partial move recreates the D3 silent class: the row lands in this
# append-only log and the daemon door then refuses it.
MESSAGE_TYPES = ["completion", "ask", "answer", "verdict", "note", "queue-request", "escalation",
                 "stuck"]

# The types this file will not WRITE yet, for want of a consumer. Enforced at
# `_append_message_unlocked` — the one writer — so no verb can route around it.
#
# ⚠ EMPTY SINCE W7, AND THAT IS THE MECHANISM WORKING, NOT A DEAD KNOB. W4 admitted
# `queue-request` at every door (enum, argparse, gateway, store CHECK) while holding the WRITER,
# so the type could never be written into an append-only log before something drained it; W7 built
# that consumer (the engine's queue-request pass + the `queue-requests` read verb below) and empties
# the tuple in the same change, which is the whole contract. Keep the tuple — the next type admitted
# ahead of its consumer re-uses this exact hold; do NOT delete it as unused flexibility.
#
# ⚠ `stuck` IS NOT HELD, decided explicitly rather than by default (D2): it has a consumer TODAY —
# a staff chair spawns a sitting on unread mail, and every `stuck` is addressed to the `leader` —
# so holding the writer would suppress a signal something is already waiting to read.
#
# ⚠ `gateway_send_leg`'s skip-list spells `queue-request` as a LITERAL and is NOT derived from this
# tuple (see its note at the `("completion", "queue-request")` test). The two are independent on
# purpose: this tuple is "nothing may write it yet", that list is "this type does not cross the
# gateway door" — emptying one must not silently open the other.
WRITER_HELD_TYPES = ()

TYPE_COLOR = {"ask": "33", "verdict": "35", "completion": "32", "answer": "36", "note": "2",
              "escalation": "1;31", "queue-request": "2", "stuck": "1;33"}
WORKER_ROW = re.compile(
    r"^\|\s*(?P<agent>[^|]+?)\s*\|\s*(?P<active>yes|no)\s*\|\s*(?P<pane>[^|]*?)\s*"
    r"\|\s*(?P<summary>[^|]*?)\s*\|\s*(?P<checkin>[^|]*?)\s*\|\s*(?P<checkout>[^|]*?)\s*"
    r"\|\s*(?P<lastread>[^|]*?)\s*\|$"
)

# ---- the kit's product files: ten loaded siblings + six imported supervision modules -------
# The ten below hold bodies MOVED VERBATIM out of this file and are loaded INTO this module's
# namespace rather than imported, because that split is TEXTUAL: a moved body keeps reading and
# writing exactly the globals it read before the move. The selftest substitutes ~60 of those names
# at runtime (`global wake, tmux_send_text, atomic_write, RUNS_INDEX, ...` plus the `globals()[...]`
# sites), and a per-module COPY of the namespace leaves every stub unreachable: measured
# 2026-08-24, the suite fell from 913 ok / 128 fail to ABORTED after 23 checks under a copying bind.
SPLIT_MODULES = ("addressing", "outputs", "tmux", "records", "identity", "closeout", "checkout",
                 "messages", "coord_selftest", "cli_main")
# The six modules `spec-component-map` §3 homes in `supervisor/` are REAL MODULES, imported below
# (owner ruling 2026-08-25, "SPLIT_MODULES / coordinate split"). They were measured before they
# moved: 1,505 of the 1,506 cross-module references in this kit are read inside a function body,
# so the module cycle they form with this file resolves at CALL time and plain imports are sound.
# Every name they take from here is spelled `coord.NAME`, and every name this side takes from them
# is spelled `<module>.NAME` — which is also what keeps a selftest stub visible across the seam.
SUPERVISOR_MODULES = ("process", "carrier", "attest", "lifecycle_exec", "launch", "ready")
# The product's load order, unchanged since the move-only split — PRODUCT_SOURCE stays the same
# corpus in the same sequence, so every audit that counts over it keeps meaning what it meant.
PRODUCT_ORDER = ("addressing", "outputs", "tmux", "process", "records", "identity", "carrier",
                 "closeout", "attest", "checkout", "lifecycle_exec", "messages", "launch",
                 "ready", "coord_selftest", "cli_main")
COORD_PY = Path(__file__).resolve()
KIT_DIR = COORD_PY.parent
SUPERVISOR_DIR = KIT_DIR.parent / "supervisor"
# The supervision door — the other half of the entry-point split (owner ruling 2026-08-25).
SUPERVISE_PY = SUPERVISOR_DIR / "supervise.py"
# The supervision half is imported by plain module name, so its folder joins this one on the path.
sys.path.insert(0, str(SUPERVISOR_DIR))


def _split_path(name):
    """Where one product module's file lives. The ONE place the two-folder layout is spelled."""
    return (SUPERVISOR_DIR if name in SUPERVISOR_MODULES else KIT_DIR) / (name + ".py")


# The kit's PRODUCT FILES in load order, this file first. Every scan that asks "what is this
# module's source" derives its file list from HERE — a scan that walked one directory would go
# silently EMPTY for the supervision half rather than red.
PRODUCT_FILES = (COORD_PY,) + tuple(_split_path(n) for n in PRODUCT_ORDER)

_SPLIT_SOURCES = {}
for _split_name in SPLIT_MODULES:
    _split_src = _split_path(_split_name)
    _split_text = _split_src.read_text(encoding="utf-8")
    _SPLIT_SOURCES[_split_name] = _split_text
    exec(compile(_split_text, str(_split_src), "exec"), globals())

# ⚠ IMPORTED AFTER THE LOAD, NEVER BEFORE. Each of the six `import coord` back, and this module is
# only half-built until the loop above finishes; importing them first would hand them a namespace
# missing every agent-side name. Nothing reads an attribute at import time, on either side — that
# is the property that makes the cycle sound, and it was measured before the move.
import process         # noqa: E402 — process truth (spec-component-map §3)
import carrier         # noqa: E402 — the asserted-identity launch bound
import attest          # noqa: E402 — attest-exit and the session closer
import lifecycle_exec  # noqa: E402 — the daemon's mechanical-remedy executor
import launch          # noqa: E402 — the lane-aware launch composer
import ready           # noqa: E402 — the ready-seat arithmetic and the derived `dead` state

# ---- the §3 re-export shim: every supervision public name is still an attribute of `coord` ----
# `spec-component-map` §3 keeps this file "a thin re-export shim ... so external callers
# (`coordinate`, daemon argv, probes) keep working", and two of them read the moved names straight
# off the module object: `planning/materialize-seats.py` imports `validate_seat`, and
# `goals-tree/tool/goal_cli.py` loads this file by path and reads `parse_after_member` /
# `after_member_limbs` off it, refusing loudly when either is absent. DERIVED from each module's
# own namespace, never a hand-written list — a hand-written list is what broke `probe-save-gate`'s
# kit twice, a release late each time.
#
# ⚠ THIS IS FOR CALLERS OUTSIDE THE KIT ONLY. Product code names a supervision symbol through its
# OWNING module (`process.ps_snapshot`), never through the alias, and the selftest rebinds the
# owning module's attribute — an alias is a SNAPSHOT taken here at import and a stub would never
# reach it. Nothing in this kit reads one; keep it that way.
for _sup_mod in (process, carrier, attest, lifecycle_exec, launch, ready):
    for _sup_name, _sup_val in vars(_sup_mod).items():
        if _sup_name.startswith("_") or _sup_name in globals():
            continue
        if isinstance(_sup_val, type(sys)):      # a module the supervision half imported
            continue
        globals()[_sup_name] = _sup_val

# The kit's PRODUCT SOURCE as one text: this file followed by every product file above, in load
# order. The audits and selftest rows that scan "this module's source" are asking about the
# product, and the product is several files — this is the same corpus they read before the split,
# so their counts and their AST walks keep meaning what they meant. Scan TARGET only; no scan's
# logic moved.
PRODUCT_SOURCE = "\n".join(
    [COORD_PY.read_text(encoding="utf-8")]
    + [_SPLIT_SOURCES.get(_n) or _split_path(_n).read_text(encoding="utf-8")
       for _n in PRODUCT_ORDER])
