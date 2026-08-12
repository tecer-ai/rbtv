#!/usr/bin/env python3
"""master_profile — the channel master's own control over WHICH HARNESS AND MODEL its next sitting
runs on (issue C-1, owner-ruled 2026-08-10).

WHAT THE KNOB ACTUALLY IS, AND WHERE IT LIVES
---------------------------------------------
⚠ RETARGETED 2026-08-12. Until then the knob was `master_profile` in
`.rbtv/config/chat-bridge-config.json`, read at boot by the chat bridge and selected per SURFACE by
`forward-path.js#profileFor`. The launch-cast unification (owner ruling D2, 2026-08-11) DELETED
that key's readers — the transport stopped naming execution — and this tool was parked on a
refusal naming the correct target rather than half-retargeted. This IS that retarget, and the
refusal is gone with it.

The knob is now the channel master's own CASTING SHEET —
`.rbtv/config/modules/meta/master-agent/bindings/channel-master.json`, the `harness` · `model` ·
`effort` triple of its one seat. The master is cast exactly like every other seat; what makes it
special is only that it is the seat allowed to re-cast ITSELF. `materialize-seats.py --repass`
re-renders `seat.md` from the sheet, and every launch door resolves the cast from that descriptor
(`launch-profiles/catalog.js#castProfileFor`, read fresh per message), so the change lands on the
owner's next word.

The AGENT-FACING unit is still a spawn-profile NAME from `profiles:` in
`ignite/config/spawn-profiles.yaml` — one profile IS one harness+model pair
(`r-seats-only-architecture`), so a name is a complete cast and the requester keeps the one
vocabulary `show` prints. The name is resolved to its pair and validated at BOTH halves: an
unknown or uncastable name does not fail at the sheet, it fails at the SPAWN, one owner message
later, with the sitting already accounted for.

The owner's ruling was explicit: **do not change the system, give the agent a tool to interact with
it in its native place.** So this file writes the same three fields a hand-edit would, through the
same validator `rbtv-bindings set` uses, and nothing else.

EFFORT — A NUMERIC RUNG, AND THE LANE UNDER IT WAS BUILT ON 2026-08-11
----------------------------------------------------------------------
⚠ THIS SECTION REPLACES A REFUSAL. Until 2026-08-11 this docstring carried a measured trace ending
"adding `--effort` here would have written a value nothing reads — a knob that turns and does
nothing". That trace was CORRECT at its HEAD: `forward-path.js` composed `args: {profile, prompt}`,
the `chat-agent` job's schema admitted no `effort`, `ticker.js#launchAgent` read three arg keys, and
`spawn.js` never touched the profile's `effort:` table. Owner ruling `d-0811lp-effort-lane-build-now`
(run exec-0811-live-proofs) ruled the LANE built rather than the knob dropped, explicitly overriding
the "NO daemon caller today — Re-rule at 7.43/7.54" reservation at `internal-api/dispatch.js:405`
and the sibling refusal in `spawn.js` (G-144). Every link in that trace now carries the field.

  · `ticker.js#launchAgent` reads `args.effort` and passes it to `spawnManager.spawn(...)`;
  · `spawn.js#composeArgv` composes it through `resolveEffort()` — the SAME function
    `launch-profiles/resolveProfile` calls, never a second reading of the table.

⚠ THE FIRST TWO LINKS OF THAT TRACE ARE HISTORY. They were the bridge's `master_effort` key and the
job id widened to admit it — the per-SURFACE lane, deleted by D2 the same week it shipped. What
survived is the half below them, and it is the half that matters: the rung reaches `composeArgv`
from the SEAT'S DESCRIPTOR now, on every lane, so the effort this tool writes is honoured whether
the master is reached over chat or spawned by the daemon.

WHAT A RUNG IS (owner ruling `d-0811lp-effort-numeric-per-profile`): an integer 1..N, ordered lowest
to highest reasoning, in the ladder THAT PROFILE declares in `spawn-profiles.yaml` (`effort.rungs`).
N differs per harness — claude 5 (low·medium·high·xhigh·max), codex 3, kimi 2 — so a rung is only
meaningful against a profile, and a request outside that profile's range is REFUSED naming it.

⚠ A PROFILE WITH NO DIAL (`effort: { inert: true }` — `claude-haiku`, `test-sleep`) ACCEPTS a rung
and the sheet stores the word `inert`. It REFUSED one until 2026-08-12 — the "known asymmetry"
`d-effort-refuses-only-where-a-dial-exists` filed as defensible while nothing cast a seat to an
inert profile. Something does: the channel master runs on `claude-haiku` for the warm-session path,
and the refusal made that cast un-makeable through THIS tool — `cast_seat` popped the rung and
`materialize-seats.py#open_binding` then refused the half-declared triple on the standing seat, so
the live sheet had to be hand-written (measured 2026-08-12). The ruling governs both doors now:
refuse only where a dial EXISTS and the level is out of its range. The mirror-image rule is
unchanged: a profile that HAS a dial must be given a rung, because materialize refuses
`effort-missing` on it.

⚠ THE RUNG IS WRITTEN WITH THE PROFILE, ALWAYS — NEVER LEFT OVER FROM THE PREVIOUS ONE. A rung
belongs to the profile it was chosen for: rung 4, chosen on a five-rung claude ladder and left
behind across a switch to codex (top rung 3), would pass every door here and REFUSE AT THE SPAWN,
one owner message later — the exact failure mode the profile-name validation exists to prevent, one
field over. So the switch rewrites the field: a dialled profile takes the rung it was given (and
refuses without one), and an INERT one takes the word `inert` whether a rung was named or not.

⚠ AND ON THE SHEET, THE EFFORT RULES ARE THE SHEET'S — `bindings.cast_seat` IS THE VALIDATOR HERE,
called dry-run by `request` and for real by `apply`, so one function answers "may I?" and performs
"do it". It is STRICTER than the retired bridge-config path in ONE direction: a pair WITH a dial
must name a rung, because materialize refuses `effort-missing` on it. In the other direction the
two agree — a pair with no dial accepts a rung and records it inert. That is why this file no
longer carries its own `validate_effort` — a second effort validator over a file another tool owns
is the drift the ladder reader was already collapsed to avoid.

WHY THIS IS TWO HALVES AND NOT ONE COMMAND
-------------------------------------------
⚠ THE REASON CHANGED WITH THE TARGET, AND IT IS NARROWER NOW. It is NOT that the seat cannot write
the sheet: the bindings tree is in the channel master's `rw-paths` and the seat writes it directly
(`capabilities/bindings` is a one-part capability for exactly that reason). It is the RE-RENDER.
`--repass` rewrites `<goal>/seat.md`, and `spawn.js`'s `rw-paths` resolver refuses any grant
overlapping `.rbtv/goals/` on purpose — a seat may not rewrite its own identity surface. So the
seat can author the cast and cannot make it take, which is the worst of both; the split gives the
authoring to the seat's `request` and the re-render to the daemon's `apply`. Measured and filed as
`i-cast-rerender-blocked` on the master's own issues ledger, 2026-08-11.

The transport is unchanged from its siblings `goal-launch-delay` and `goal-creation-request`:
`fire-tool` argv is STATIC, so no gateway verb can carry a request body to a fired tool and the
payload must travel as a FILE staged in the seat's own folder; `enqueue-job` is the one gateway
verb open to every sender kind including a `bridge` token, so it is the trigger.

⚠ NOTHING IS RESTARTED ANY MORE, AND THE SITTING SURVIVES. The old apply restarted
`rbtv-chat-bridge.service` because the bridge boot-read the value — which killed the very
conversation that asked for the switch. Nothing boot-reads a casting sheet: `spawn.js` reads
`seat.md` per launch (`readFileSync`, never cached), and the warm leg re-resolves the cast on EVERY
owner message and reaps a live session whose conversation now names a different profile
(`live-sessions.js` § REAP ON A PROFILE SWITCH). So the re-render is the last act, the switch takes
effect on the owner's next word, and the thread that requested it is still there to read the report.

THE SELF-REPORT — WHY THE OUTCOME TRAVELS BACK ON THE COORDINATION BUS
----------------------------------------------------------------------
An outcome record in `done/` is durable but SILENT: the sitting that asked for the change ended
with its turn, and the owner is left watching a Slack thread where nothing ever answers (issue
`i-profile-switch-no-feedback`, owner-ruled 2026-08-10 — when the restart also killed that sitting
outright; the sitting survives now, but the silence does not fix itself). So `request` takes the
sitting's own
`--chat-thread <channel>:<ts>` — every sitting is told its thread in the plain form on the first
line of its prompt — and `apply` writes the outcome back into that thread.

⚠ IT POSTS NOTHING ITSELF, AND THAT IS THE WHOLE DESIGN. This tool holds no Slack token and opens
no socket. It appends ONE row to the requesting goal's coordination bus, addressed `to: owner`, with
the BRACKETED `[chat-thread: <id>]` token in the body — and `bridges/chat/bus-ferry.js`'s return leg
carries it into that thread. The bracketed form is the ferry's routing token (the plain form a
prompt carries is deliberately inert), and the return leg is read BEFORE the two contact gates, so
the report travels even on a goal that may not INITIATE contact with the owner. Nothing new was
built for this: the row is appended through `coord.py#append_message`, the one allocator of bus ids.

⚠ THE ROW ALSO CARRIES `[deliver: post]`, AND WITHOUT IT THE REPORT IS NOT A REPORT. A bare
`[chat-thread:]` token means "hand this row to an AGENT on that thread" — the bridge mints a
channel-master sitting from it and posts NOTHING (ruled 2026-08-07, for a SEAT answering the
owner). Measured on this exact path 2026-08-10 12:46:46Z: the switch report minted queue row 361
and the owner was shown nothing. A settled switch is a FACT, already composed here, so it asks to
be POSTED verbatim instead — no agent, no inference, no ~12s spawn pipeline
(`bridges/chat/bus-ferry.js` § `deliverToken`; `live-session-design.md` §3a).

⚠ A REFUSED OUTCOME CARRIES `[deliver: wake]` INSTEAD — post always, wake when agent action is
needed (owner-ruled 2026-08-10). `wake` posts the row verbatim AND mints a sitting with it as the
prompt, so the owner sees the refusal and an agent is standing on the thread that has to answer it.
An ACCEPTED change is a settled fact nobody must act on and stays `post`; only the unfinished job
wakes anybody. The choice is made at the ONE call site in `apply` — the outcome verdict IS the
signal, so no second flag decides it.

⚠ THE REPORT PRECEDES THE RE-RENDER, so it cannot state its exit code — it states what is ABOUT to
happen. That ordering was forced when the last act killed this process; it is kept because the
report is still the courtesy and the change is still the job. The rc stays where it always was:
the outcome record on disk, rewritten once the re-render returns.

⚠ A FAILED APPEND NEVER ABORTS THE APPLY. The switch is the job; the report is the courtesy. A
report that cannot be written is recorded IN the outcome record (`chat-report.error`) and the fire
continues — losing the change to save the message would be exactly backwards.
"""

import argparse
import json
import re
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

_IGNITE = Path(__file__).resolve().parents[3]
DEFAULT_PROFILES = _IGNITE / "config" / "spawn-profiles.yaml"
TEAM_KIT = _IGNITE / "team-kit"      # `coord.py` — the ONE allocator of bus message ids
MATERIALIZE = TEAM_KIT / "materialize-seats.py"      # the ONE re-render, never a second renderer
# The workspace root is the folder that roots `.rbtv/` — <workspace>/3-resources/tools/rbtv/ignite
_WORKSPACE = _IGNITE.parents[3]
DEFAULT_SEAT = "channel-master"
DEFAULT_BINDINGS = (_WORKSPACE / ".rbtv" / "config" / "modules" / "meta" / "master-agent"
                    / "bindings" / f"{DEFAULT_SEAT}.json")
DEFAULT_CATALOG_ROOT = _WORKSPACE / ".rbtv" / "mirror" / "meta"

# ⚠ EVERY ONE OF THOSE IS A DEFAULT FOR A HUMAN AT A TERMINAL, AND THE FIRED ARGV NAMES ALL OF THEM
# EXPLICITLY (`tools: master-profile:` in spawn-profiles.yaml). Same reason the sibling entries
# spell out `--config`: a reader of that entry can see WHICH sheet a fire rewrites and WHICH seat it
# re-renders without opening this script. The `--package` is the exception and is DERIVED from
# `--inbox` rather than defaulted — see `_goal_dir`.

KEY = "master_profile"
ENTRY_TOOL_KEY = "master-profile"   # this capability's own `tools:` key
JOB_ID = "master-profile"           # the registered fire-tool job id the client half enqueues

DONE_DIR = "done"
REFUSED_DIR = "refused"


# ── THE CATALOG, THE LADDER READER AND THE WRITE ARE IMPORTED, NEVER RE-IMPLEMENTED ─────────────
#
# `effort_ladder` IS `bindings.profile_effort` — the same function object, not a copy that agrees.
# It was a copy until 2026-08-11, and the copies DISAGREED on identical bytes: this file line-scanned
# a profile block and returned on whichever of `inert` / `rungs:` came FIRST, while the bindings
# capability searched the whole block for `inert` before looking at rungs. A `rungs:` line above an
# `effort: { inert: true }` line read as a FIVE-RUNG LADDER here and as INERT there — for the same
# profile, in the same file, in the same second. Two copies agree on the day they are written; that
# is the only day they are guaranteed to.
#
# ⚠ THE 2026-08-12 RETARGET MADE THE OTHER THREE THE SAME KIND OF FACT. Once this tool's target
# became a CASTING SHEET, `bindings` was no longer a library it borrowed a reader from — it is the
# capability that OWNS the file. So the name→cast resolution (`profile_row`), the castable set
# (`catalog`) and the write itself (`cast_seat`) all come from there too. What this file still owns
# is the TRANSPORT — staging, the fire, the bus report, the re-render — which is the half `bindings`
# has no reason to know about.
#
# The direction is bindings ← master-profile, and it is acyclic: `bindings` imports nothing from
# here, and its ONE cross-tool import (`coord.py#validate_seat`) is function-scoped and lazy, so
# importing it here does not drag `team-kit/` in. Enforced as OBJECT IDENTITY by
# `probes/probe-master-profile.py`, not as value equality — equality is what two drifting copies
# report right up until they drift.
_BINDINGS_TOOL = str(_IGNITE / "capabilities" / "bindings" / "tool")
if _BINDINGS_TOOL not in sys.path:
    sys.path.insert(0, _BINDINGS_TOOL)
from bindings import (                                    # noqa: E402
    Refusal,
    profile_effort as effort_ladder,
    catalog as bindings_catalog,
    profile_row,
    cast_seat,
)

# ⚠ `Refusal` IS IMPORTED, NOT DECLARED — AND THAT IS A FIX, NOT TIDINESS. This file declared its
# own identically-named, identically-worded exception class until 2026-08-12. The moment `cast_seat`
# became this tool's validator, that made the refusals it raises a DIFFERENT TYPE from the ones
# `main` catches: a legitimate "this profile has a 5-rung dial, name one" came back as an unhandled
# traceback with no `{"ok": false, "refusal": …}` envelope, and inside `apply` it fell to the
# catch-all and was recorded as `Refusal: …` — an internal class name in the record where a stated
# reason belongs. Measured on the fixture before it could reach a live fire. One capability pair,
# one refusal type.


def known_profiles(profiles_path=DEFAULT_PROFILES):
    """The names this tool will accept — the CASTABLE profiles, read live off the catalog.

    ⚠ NOT A HARD-CODED ROSTER. The owner-ruled roster changes (four claude models, codex, kimi, the
    opencode set), and a list frozen in this file would refuse a profile that exists or admit one
    that was removed — the second being the failure that reaches the spawn.

    ⚠ AND NOT THE `profiles:` KEY SET EITHER, WHICH IS THE WIDER AND WRONG LIST. This was a line
    scan of that section until 2026-08-12, which admitted every declared name — including ones no
    seat can be cast as (`test-sleep`: `coord.py#validate_seat` rejects its harness) and ones that
    spawn nothing (no `exec:` half). Against the bridge config that only ever cost a spawn; against
    a casting sheet it would write a cast `materialize-seats.py`'s F6 gate refuses, which is a
    refusal at goal-creation for the whole batch. The catalog is the ONE derivation both this tool
    and `rbtv-bindings` enforce, so the names offered here are exactly the names accepted.
    """
    return sorted(r["profile"] for r in bindings_catalog(profiles_path) if r["castable"])


def validate(name, profiles_path=DEFAULT_PROFILES):
    """Resolve a profile NAME to the catalog row that IS its cast. The ONE resolver, called by both
    halves. The client so a typo refuses in the sitting that made it; the daemon because a
    client-side check is not a check (the staged payload is written by the requester and can be
    edited between staging and the fire)."""
    if not isinstance(name, str) or not name.strip():
        raise Refusal(f"{KEY} must be a non-empty string, got {name!r}")
    row = profile_row(name, profiles_path)
    if row is not None and row["castable"]:
        return row
    known = known_profiles(profiles_path)
    if row is not None:
        raise Refusal(f"`{name}` is a declared spawn profile but is NOT castable: "
                      f"{row['not-castable-because']}. A seat may only be cast as a pair "
                      f"`coord.py#validate_seat` accepts — the same predicate materialize's F6 gate "
                      f"runs over the whole batch. Castable names: {', '.join(known)}.")
    raise Refusal(f"`{name}` is not a castable spawn profile. The live castable set is: "
                  f"{', '.join(known)}. Refused HERE because an unknown name does not fail when the "
                  f"sheet is written — it fails at the spawn, one owner message later.")


# ⚠ THERE IS NO `validate_effort` IN THIS FILE ANY MORE, AND ITS ABSENCE IS THE POINT.
#
# It was the three-way rung check (`None` = no dial · `[]` = inert · list = rungs) that guarded a
# write into the bridge config. The 2026-08-12 retarget moved the write onto the casting sheet,
# whose rule is STRICTER in one direction — a pair WITH a dial must carry a rung, because
# materialize refuses `effort-missing` — and identical in the other: a pair with an INERT dial
# accepts any rung and stores `inert` (`d-effort-refuses-only-where-a-dial-exists`). Keeping the
# old checker beside the new file would
# have been a second effort validator over a document this tool does not own — the exact shape of
# drift the ladder-reader collapse above was performed to end, one field over.
#
# `bindings.cast_seat` is the validator now: `request` calls it with `dry_run=True` (validates,
# writes nothing) and `apply` calls it for real. One function answers "may I?" and performs "do it",
# so the two answers cannot disagree. `effort_ladder` survives because `ladders()` below still needs
# to PRINT every ladder — a display, not a gate.


def ladders(profiles_path=DEFAULT_PROFILES):
    """Every profile with what may be asked of it — what `show` prints so nobody has to guess N."""
    out = {}
    for name in known_profiles(profiles_path):
        ladder = effort_ladder(name, profiles_path)
        out[name] = ("no effort block — omit the rung" if ladder is None
                     else "inert (accepts any rung, applies none — G-270)" if ladder == []
                     else f"1..{len(ladder)} ({', '.join(f'{i + 1}={v}' for i, v in enumerate(ladder))})")
    return out


# ⚠ THE REQUESTER IS AN LLM AND ITS INPUT IS PROSE ("switch to opus at high effort", "think
# harder", "max reasoning"). What it needs is not a word→number table — which refuses the phrasing
# nobody anticipated — but the SHAPE of the scale, from which it translates any wording itself.
# Stated once here and printed on both surfaces the requester reads: `show` and `request --help`.
EFFORT_GUIDANCE = (
    "converting a prose effort request into a rung: a rung is a POSITION on the TARGET profile's "
    "ladder, so map the phrasing proportionally onto 1..N — N is that profile's own, and `show` "
    "prints every profile's ladder. minimal/quick/low → 1; medium/normal → the middle rung; "
    "high → just below N on a ladder of 4+ (on a 2- or 3-rung ladder it IS N); "
    "maximum/deepest/think-hardest → N. If the request names NO effort but the target profile HAS a "
    "ladder, you must still pick one — the middle rung is the honest default for an unstated ask — "
    "because a dialled seat with no effort is refused. A profile `show` marks INERT has no dial at "
    "all: pass a rung or omit it, either way the sheet records `inert` and the harness runs "
    "single-mode."
)


# ───────────────────────────────────────────── the cast: read it here, WRITE IT THROUGH `bindings`
#
# ⚠ THE WRITE IS NOT IN THIS FILE. It was a pair of line-precise regex edits into a hand-authored
# JSON config until 2026-08-12 (`_LINE`/`_ELINE`, `write_value`, `write_effort`) — the right shape
# for that document, and the wrong one for this target. A casting sheet is machine-authored,
# `bindings._write` round-trips it at one-space indent, and `bindings.cast_seat` is the function
# that already knew every rule about what may go in it. So the ~110 lines of edit machinery were
# DELETED rather than pointed at a new file: a second writer of a document another capability owns
# is drift with a deadline.
#
# What is left here is the READ, and it is a read the seat can perform from inside its own cage —
# the bindings tree is in the master's `rw-paths`.


def read_value(bindings=DEFAULT_BINDINGS, seat=DEFAULT_SEAT, profiles_path=DEFAULT_PROFILES):
    """The cast in force, reported in BOTH vocabularies. Pure read — safe from inside the cage.

    The sheet stores `harness`/`model`/`effort` — the harness's own strings, which is what
    `materialize-seats.py` renders and what a launch door reads. The requester speaks in profile
    NAMES and RUNG NUMBERS. Both are returned, mapped through the same catalog `validate` resolves
    against, so `show` can print what is in force in the words `request` will accept back.

    An UNRECOGNISED cast is reported, never refused: a sheet hand-edited to a pair no profile
    declares is exactly the state a reader most needs to see spelled out, and refusing to read it
    would leave `show` unable to explain why the next spawn fails.
    """
    bindings = Path(bindings)
    doc = json.loads(bindings.read_text(encoding="utf-8"))
    entry = (doc.get("seats") or {}).get(seat)
    if entry is None:
        raise Refusal(f"{bindings} carries no seat `{seat}` — its seats are: "
                      f"{', '.join(sorted((doc.get('seats') or {}))) or '(none)'}. This tool reads "
                      f"and writes ONE seat of an existing sheet; it never mints either.")
    harness, model, effort = entry.get("harness"), entry.get("model"), entry.get("effort")
    row = next((r for r in bindings_catalog(profiles_path)
                if r["harness"] == harness and r["model"] == model), None)
    profile = row["profile"] if row else None
    ladder = list(row["effort-levels"]) if row else []
    rung = ladder.index(effort) + 1 if effort in ladder else None

    if profile is None:
        where = (f"{bindings} — seat `{seat}`. ⚠ its cast `{harness}/{model}` matches NO profile in "
                 f"{profiles_path}, so the next spawn of this seat REFUSES "
                 f"(`catalog.js#E_UNCAST_SEAT`). Request a castable name to repair it.")
    else:
        where = (f"{bindings} — the `harness`/`model`/`effort` of seat `{seat}`, rendered into "
                 f"{seat}'s `seat.md` by `materialize-seats.py --repass` and resolved at every "
                 f"launch door by `launch-profiles/catalog.js#castProfileFor`. Read per launch, "
                 f"never boot-cached: a change lands on the owner's next message.")
    return {"profile": profile, "harness": harness, "model": model, "effort": effort,
            "rung": rung, "bindings": str(bindings), "seat": seat, "where": where}



# ────────────────────────────────────── the self-report back into the owner's own chat thread
#
# ⚠ THIS REGEX MIRRORS `bus-ferry.js`'s CHAT_THREAD_RE, ANCHORED. The ferry routes on
# `[A-Z][A-Z0-9_]{2,}:\d+\.\d+` and NOTHING ELSE — a bare channel id (a GOAL conversation's shape)
# is deliberately outside it, because routing into a goal channel is a different leg. A token this
# tool accepted but the ferry would not route is a report staged into silence, so the shape is
# checked HERE, in the sitting that typed it, and again at the fire.
CHAT_THREAD_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,}:\d+\.\d+$")

# The `from:` this tool signs its bus rows with. The capability's own key, not a seat name: no seat
# wrote this row, the daemon-side half of this tool did, and the owner reads it as `from <this>`.
REPORT_SENDER = ENTRY_TOOL_KEY


def validate_chat_thread(thread):
    """The ONE thread-id validator, called by both halves — same reason `validate` is."""
    if not isinstance(thread, str) or not CHAT_THREAD_RE.match(thread):
        raise Refusal(f"--chat-thread must be `<channel>:<ts>` — a Slack channel id then a colon "
                      f"then the thread timestamp (e.g. C0ABCDEFG:1754812345.123456); got "
                      f"{thread!r}. Refused HERE because bus-ferry.js routes on exactly this shape "
                      f"and silently ignores anything else — an accepted-but-unroutable token is a "
                      f"report nobody ever receives.")
    return thread


def _anchor_inbox(raw):
    """A RELATIVE `--inbox` is WORKSPACE-relative, never cwd-relative. The seat that
    stages a request runs with cwd inside its own seat folder; resolving there
    `mkdir -p`'d a nested `.rbtv/goals` tree under the seat (measured 2026-08-12 —
    `goal_cli`'s root walk-up then scaffolded a real goal into it). Absolute paths
    (the daemon's fired argv, the probes' tmp fixtures) pass through untouched."""
    p = Path(raw).expanduser()
    return p if p.is_absolute() else _WORKSPACE / p


def _goal_dir(inbox):
    """The goal folder the request was STAGED IN.

    DERIVED, never named: the inbox is `<goal>/settings-requests/<capability>`, so its grandparent
    IS the requesting goal's folder. Naming `_channel-master` here would hard-code one workspace's
    goal into a repo whose components must be general — and would point a probe's fire at the live
    package. TWO consumers: the bus the outcome is reported on, and the `--package` the re-render
    runs against. They are the same folder by construction, so they are derived once.
    """
    return Path(inbox).resolve().parents[1]


def _bus_dir(inbox):
    """The coordination bus of the goal the request was staged in — `<goal>/coordination`, the one
    the ferry enumerates for it."""
    return _goal_dir(inbox) / "coordination"


def report_to_thread(inbox, thread, body, deliver="post"):
    """Append ONE `to: owner` row carrying the bracketed token. NEVER raises — see the module
    docstring: the switch must not be lost to save the message.

    The append goes through `coord.py#append_message`, which owns the header grammar, the id
    allocation and the package lock (two concurrent senders once claimed one id). Imported in
    process rather than shelled out: a body carrying backticks — and this one does — is a quoting
    hazard on a command line and none at all through a function call.
    """
    try:
        if str(TEAM_KIT) not in sys.path:
            sys.path.insert(0, str(TEAM_KIT))
        from coord import append_message
        base = _bus_dir(inbox)
        base.mkdir(parents=True, exist_ok=True)
        n = append_message(base, REPORT_SENDER, "owner", "note",
                           f"{body}\n\n[chat-thread: {thread}] [deliver: {deliver}]")
        return {"appended": n, "bus": str(base / "messages.md"), "chat-thread": thread}
    except Exception as exc:
        return {"appended": None, "chat-thread": thread,
                "error": f"{type(exc).__name__}: {exc}",
                "note": "the change itself was applied — only the owner-facing report failed"}


def _report_body(record, repass):
    """Slack mrkdwn, and only mrkdwn: no pipe tables, no `#` headings, no `[](…)` links — the ferry
    delivers a conformant body VERBATIM, and a markdown-ism arrives as literal punctuation."""
    if record["outcome"] == "ACCEPTED":
        change = record.get("change") or {}
        after = change.get("after") or {}
        # NOT an rc — the report precedes the re-render by ruling, so it says what is about to happen.
        line = ("re-rendering this seat's `seat.md` from the sheet now — the last act of this job"
                if repass else
                "SKIPPED (--no-repass) — the sheet is written but `seat.md` still carries the old "
                "cast, which is what a launch actually reads")
        rung = record.get("requested-effort")
        if change.get("effort-inert"):
            # The rung, if one was asked for, is NOT reported as applied: this profile has no dial,
            # so it is accepted and recorded inert (G-270 — stated, never silently dropped).
            effort_line = (f"effort: `{after.get('effort')}` — this model has no effort dial, so "
                           f"any rung is accepted and applies nothing")
        elif rung is None:
            effort_line = "effort: harness default (this pair declares no dial)"
        else:
            effort_line = (f"effort: rung {rung} = `{after.get('effort')}` on "
                           f"`{record['requested']}`'s ladder ({record.get('effort-ladder')})")
        was = record.get("before") or {}
        return (f"*master cast changed* — `{was.get('profile')}` → `{record['requested']}` "
                f"({after.get('harness')}/{after.get('model')})\n"
                f"{effort_line}\n"
                f"apply: {line}\n"
                f"scope: takes effect on your NEXT message — the live session is reaped when its "
                f"conversation names a different profile, and nothing is restarted")
    return (f"*master cast change REFUSED* — still `{(record.get('before') or {}).get('profile')}`\n"
            f"why: {str(record.get('stated-refusal'))[:600]}\n"
            f"apply: none — nothing changed")


# ─────────────────────────────────────────────────────────────────────────── the client half

def request(inbox, name, ignite_bin, profiles_path=DEFAULT_PROFILES, job_id=JOB_ID, dry_run=False,
            chat_thread=None, effort=None, bindings=DEFAULT_BINDINGS, seat=DEFAULT_SEAT):
    row = validate(name, profiles_path)
    # THE FULL WRITE, WITH THE WRITE TURNED OFF. Not a lighter client-side approximation of the
    # daemon's check — literally the same call `apply` makes, `dry_run=True`. A rung the sheet would
    # refuse therefore refuses HERE, in the sitting that typed it, instead of at a fire the owner is
    # no longer watching. The seat can run it because the bindings tree is in its `rw-paths`.
    cast_seat(bindings, seat, row["harness"], row["model"], effort, profiles_path, dry_run=True)
    if chat_thread is not None:
        validate_chat_thread(chat_thread)
    inbox = Path(inbox)
    if inbox.is_symlink():
        raise Refusal(f"{inbox} is a symlink — refusing to stage through one")
    inbox.mkdir(parents=True, exist_ok=True)
    staged = inbox / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    payload = {"master-profile": name}
    if effort is not None:
        payload["effort"] = effort
    if chat_thread:
        payload["chat-thread"] = chat_thread
    out = {"ok": True, "staged": str(staged), **payload}
    if dry_run:
        out["staged"] = None
        out["dry-run"] = True
        return out
    staged.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = subprocess.run([ignite_bin, "add-job", "--fn", job_id,
                        "--args-json", json.dumps({"tool": ENTRY_TOOL_KEY}),
                        "--trigger", "scheduled", "--at", at],
                       capture_output=True, text=True)
    out["enqueue"] = {"rc": r.returncode, "at": at,
                      "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    if r.returncode != 0:
        out["ok"] = False
        out["note"] = (f"the request is STAGED at {staged} but the enqueue failed — it will be "
                       f"applied by the next fire of this tool, or re-run the enqueue by hand")
    # ⚠ THIS FIELD IS READ ALOUD TO THE OWNER. It said "applying this restarts rbtv-chat-bridge,
    # which ENDS the live chat session this request was made from" until 2026-08-12 — true of the
    # retired bridge-config target, false of this one, and the kind of false a requesting agent
    # repeats verbatim into Slack as a warning about a cost nobody is paying.
    out["note"] = ("nothing is restarted and this session survives. The daemon writes the cast and "
                   "re-renders this seat's descriptor; the switch takes effect on the owner's NEXT "
                   "message, when the live session is reaped for naming a different profile. The "
                   "outcome lands in done/ or refused/ either way.")
    return out


# ─────────────────────────────────────────────────────────────────────────── the daemon half

def _outcome(dest, record):
    dest.with_suffix(".outcome.json").write_text(json.dumps(record, indent=2) + "\n",
                                                 encoding="utf-8")


def _settle(inbox, src, verdict, record, dry_run):
    if dry_run:
        record["moved-to"] = None
        return record
    dest_dir = inbox / (DONE_DIR if verdict == "ACCEPTED" else REFUSED_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        dest = dest_dir / f"{src.name}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    src.replace(dest)
    record["moved-to"] = str(dest)
    record.setdefault("repass", "pending")
    _outcome(dest, record)
    return record


def _repass(package, seat, catalog_root, bindings):
    """Re-render the seat's descriptor from the sheet. Delegated to `materialize-seats.py`
    (PRIN-11) — the ONE renderer of a seat.md, the same one goal creation runs.

    ⚠ THIS IS WHY THERE IS A DAEMON HALF AT ALL. `--repass` writes `<package>/seat.md`, and a
    seat's own cage refuses every `rw-paths` grant overlapping `.rbtv/goals/` (`spawn.js` — a seat
    may not rewrite its own identity surface). The requesting sitting can author the cast and
    cannot make it take; this side makes it take.

    `--root` marks the materialized row a DAG root, as the seat already is. On a `--repass` of an
    existing standing seat no taskforce row is appended (measured: `taskforce_rows_appended: 0`) —
    the flag is required because an omitted insertion point never defaults to root, not because
    anything is being inserted.
    """
    cmd = [sys.executable, str(MATERIALIZE), "--package", str(package), "--seat", str(seat),
           "--catalog-root", str(catalog_root), "--bindings", str(bindings),
           "--repass", "--root", "--json"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return {"rc": r.returncode, "cmd": " ".join(cmd),
            "descriptor": str(Path(package) / "seat.md"),
            "stdout": r.stdout.strip()[-800:], "stderr": r.stderr.strip()[-800:]}


def apply(inbox, bindings=DEFAULT_BINDINGS, seat=DEFAULT_SEAT, catalog_root=DEFAULT_CATALOG_ROOT,
          profiles_path=DEFAULT_PROFILES, repass=True, dry_run=False):
    """Drain, write the cast, then re-render the descriptor — in that order, once per fire."""
    inbox = Path(inbox)
    if not inbox.is_dir():
        raise Refusal(f"the staged inbox {inbox} does not resolve to a directory — nothing to drain")
    for candidate in (inbox, inbox / DONE_DIR, inbox / REFUSED_DIR):
        if candidate.is_symlink():
            raise Refusal(f"{candidate} is a symlink, and this verb refuses to drain through one. "
                          f"NOTHING was drained; replace it with a real directory.")

    before = read_value(bindings, seat, profiles_path)
    results, accepted = [], []
    for src in sorted(p for p in inbox.iterdir() if p.name.endswith(".json")):
        record = {"request-file": str(src), "before": before}
        try:
            payload = json.loads(src.read_text(encoding="utf-8"))
            if (not isinstance(payload, dict) or "master-profile" not in payload
                    or not set(payload) <= {"master-profile", "chat-thread", "effort"}):
                raise Refusal(f"the payload must be {{\"master-profile\": \"<name>\"}} with an "
                              f"optional \"effort\": <rung> and an optional "
                              f"\"chat-thread\": \"<channel>:<ts>\"; "
                              f"got keys {sorted(payload) if isinstance(payload, dict) else type(payload).__name__}")
            # READ BEFORE THE VALUE IS VALIDATED, so a REFUSED request still knows where to report
            # itself. A malformed token refuses the request instead of being reported into nowhere.
            if payload.get("chat-thread") is not None:
                record["chat-thread"] = validate_chat_thread(payload["chat-thread"])
            row = validate(payload["master-profile"], profiles_path)
            name = row["profile"]
            record["requested"] = name
            rung = payload.get("effort")
            ladder = row["effort-levels"]
            record["requested-effort"] = rung
            record["effort-ladder"] = (None if not ladder else
                                       ", ".join(f"{i + 1}={v}" for i, v in enumerate(ladder)))
            # Client-side validation is not validation: the payload is written by the requester and
            # can be edited between staging and the fire. This IS the client's call re-run with the
            # write switched on — same function, same rules, so an "it passed at `request`" can
            # never mean something different here.
            #
            # ⚠ THE TRIPLE IS WRITTEN TOGETHER AND AN OMITTED RUNG CLEARS THE OLD ONE — see the
            # module docstring: a rung outliving its profile refuses at the spawn, not here.
            record["change"] = cast_seat(bindings, seat, row["harness"], row["model"], rung,
                                         profiles_path, dry_run=dry_run)
            verdict = "ACCEPTED"
            accepted.append(name)
        except Refusal as exc:
            verdict, record["stated-refusal"] = "REFUSED", str(exc)
        except Exception as exc:
            verdict = "REFUSED"
            record["stated-refusal"] = f"{type(exc).__name__}: {exc}"
        record["outcome"] = verdict
        results.append(_settle(inbox, src, verdict, record, dry_run))

    out = {"ok": all(r["outcome"] == "ACCEPTED" for r in results),
           "drained": len(results), "before": before, "results": results}

    # ── THE SELF-REPORT, AND IT RUNS BEFORE THE RE-RENDER BELOW ──────────────────────────────
    # ACCEPTED and REFUSED alike: "your switch did not happen, and here is why" is the answer the
    # owner is owed most. Only a request that NAMED a thread reports; the rest are silent exactly
    # as before, so nothing a previous caller staged acquires a new behaviour.
    if not dry_run:
        for r in results:
            if not r.get("chat-thread"):
                continue
            # post always; wake when agent action is needed (owner ruling 2026-08-10). A
            # settled change is a fact nobody has to act on and is POSTED verbatim; a REFUSAL
            # is an unfinished job, so it WAKES an agent on the thread that asked for it.
            r["chat-report"] = report_to_thread(inbox, r["chat-thread"],
                                                _report_body(r, repass),
                                                "wake" if r["outcome"] == "REFUSED" else "post")
            if r.get("moved-to"):
                _outcome(Path(r["moved-to"]), r)

    if accepted and not dry_run:
        out["after"] = read_value(bindings, seat, profiles_path)
        # The package is the goal the request was staged in — never a name typed into this argv.
        out["repass"] = (_repass(_goal_dir(inbox), seat, catalog_root, bindings) if repass
                         else {"skipped": "--no-repass"})
        for r in results:
            if r["outcome"] == "ACCEPTED" and r.get("moved-to"):
                r["repass"] = out["repass"]
                r["after"] = out["after"]
                _outcome(Path(r["moved-to"]), r)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="rbtv-master-profile",
        description="read and change which harness+model — and at which reasoning RUNG — the "
                    "channel master's next sitting runs on: the harness/model/effort triple of its "
                    "seat in .rbtv/config/modules/meta/master-agent/bindings/channel-master.json")
    # ⚠ THE OPTIONS HANG OFF THE VERBS, NOT OFF THE ROOT PARSER — a FIX, not a style call. As root
    # options argparse accepts them only BEFORE the verb, while the `tools:` entry and every
    # documented example spell them after (`apply --inbox … --bindings X --profiles Y`). The twin
    # capability's first live fire died on exactly that (`error: unrecognized arguments: --config`),
    # leaving the request un-drained and the execution recorded `failed`. Shared parent parsers keep
    # ONE definition of each option and admit it where callers actually put it.
    sheet_opt = argparse.ArgumentParser(add_help=False)
    sheet_opt.add_argument("--bindings", default=str(DEFAULT_BINDINGS),
                           help="the casting sheet that carries the knob (default: the live one)")
    sheet_opt.add_argument("--seat", default=DEFAULT_SEAT,
                           help="which seat of that sheet is the master (default: %(default)s)")
    prof_opt = argparse.ArgumentParser(add_help=False)
    prof_opt.add_argument("--profiles", default=str(DEFAULT_PROFILES),
                          help="the spawn-profiles document a requested name is validated against")
    sub = p.add_subparsers(dest="verb", required=True)

    s = sub.add_parser("show", parents=[sheet_opt, prof_opt],
                       help="print the cast in force, where it comes from, and the "
                            "names that may be requested")
    s.add_argument("--json", action="store_true")

    q = sub.add_parser("request", parents=[sheet_opt, prof_opt],
                       help="[the seat's verb] stage a change and enqueue the daemon "
                            "job that applies it")
    q.add_argument("profile")
    q.add_argument("--effort", type=int, default=None,
                   help="the reasoning RUNG for the NEW profile: an integer 1..N in that profile's "
                        "own ladder, 1 = lowest reasoning. `show` prints every profile's N. REQUIRED "
                        "when the profile HAS a dial and refused when it has none — the sheet stores "
                        "the harness's own level string, and materialize refuses a dialled seat with "
                        "no effort. Omitting it on a dial-less profile clears any rung currently set, "
                        "because a rung is only meaningful against the profile it was chosen "
                        "for. " + EFFORT_GUIDANCE)
    q.add_argument("--inbox", required=True)
    q.add_argument("--ignite-bin", default="ignite")
    q.add_argument("--chat-thread", default=None,
                   help="`<channel>:<ts>` — YOUR OWN chat thread, the plain `chat-thread:` line at "
                        "the top of your prompt. Given it, the daemon reports the outcome back "
                        "into that thread; omitted, the outcome is only the file in done/refused/")
    q.add_argument("--dry-run", action="store_true")

    a = sub.add_parser("apply", parents=[sheet_opt, prof_opt],
                       help="[the daemon's verb] drain the inbox, write the cast, "
                            "re-render the seat descriptor")
    a.add_argument("--inbox", required=True)
    a.add_argument("--catalog-root", default=str(DEFAULT_CATALOG_ROOT),
                   help="the component catalog the re-render reads the seat definition from")
    a.add_argument("--no-repass", action="store_true")
    a.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)
    try:
        if args.verb == "show":
            v = read_value(args.bindings, args.seat, args.profiles)
            v["available"] = known_profiles(args.profiles)
            v["effort-ladders"] = ladders(args.profiles)
            v["effort-guidance"] = EFFORT_GUIDANCE
            if args.json:
                print(json.dumps(v, indent=2))
            else:
                print(f"cast:   {v['harness']}/{v['model']}"
                      f"  (profile `{v['profile'] or 'UNKNOWN — matches no declared profile'}`)")
                effort = f"{v['effort']} (rung {v['rung']})" if v["rung"] else (
                    v["effort"] or "none (harness default)")
                print(f"effort: {effort}"
                      f"   [{v['effort-ladders'].get(v['profile'], 'no ladder — unknown profile')}]")
                print(f"from: {v['where']}")
                print("available (profile — effort rungs you may ask for):")
                for n in v["available"]:
                    print(f"  {n}: {v['effort-ladders'][n]}")
                print(textwrap.fill(EFFORT_GUIDANCE, 96, subsequent_indent="  "))
                print("takes effect on the NEXT message — nothing is boot-read and nothing is "
                      "restarted, so requesting a change no longer ends your chat session")
            return 0
        if args.verb == "request":
            out = request(_anchor_inbox(args.inbox), args.profile, args.ignite_bin, profiles_path=args.profiles,
                          dry_run=args.dry_run, chat_thread=args.chat_thread, effort=args.effort,
                          bindings=args.bindings, seat=args.seat)
            print(json.dumps(out, indent=2))
            return 0 if out["ok"] else 1
        out = apply(_anchor_inbox(args.inbox), args.bindings, args.seat, args.catalog_root,
                    profiles_path=args.profiles, repass=not args.no_repass, dry_run=args.dry_run)
        print(json.dumps(out, indent=2))
        return 0 if out["ok"] else 1
    except Refusal as exc:
        print(json.dumps({"ok": False, "refusal": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
