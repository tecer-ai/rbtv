#!/usr/bin/env python3
"""master_profile — the channel master's own control over WHICH HARNESS AND MODEL its next sitting
runs on (issue C-1, owner-ruled 2026-08-10).

WHAT THE KNOB ACTUALLY IS, AND WHERE IT LIVES
---------------------------------------------
`master_profile` in `.rbtv/config/chat-bridge-config.json`. The chat bridge reads it at boot
(`bridges/chat/config.js`) and `forward-path.js#profileFor` selects it for MASTER (DM) traffic:

    return config.masterProfile || config.sessionProfile;

so an absent or empty `master_profile` silently falls back to `session_profile` — which is why this
tool refuses to CREATE the key rather than inventing one (see `write_value`). The value is a
spawn-profile NAME from `profiles:` in `ignite/config/spawn-profiles.yaml`, and it is validated
against that live list at BOTH halves: a name absent from it does not fail at the bridge, it fails
at the SPAWN, one owner message later, with the sitting already accounted for.

The owner's ruling was explicit: **do not change the system, give the agent a tool to interact with
it in its native place.** So this file edits one line of that JSON and nothing else.

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

  · `bridges/chat/config.js` reads `master_effort`; `forward-path.js#effortFor` pairs it with the
    MASTER profile only and puts it in the enqueue `args`;
  · the job id the bridge names must admit it — a registered `args_schema` is CREATE-ONLY, so the
    old `chat-agent` id could not be widened and a NEW one carrying `"effort": "integer"` was
    registered and pointed at by `session_job_id` (the old id is retired in place, still refusing);
  · `ticker.js#launchAgent` reads `args.effort` and passes it to `spawnManager.spawn(...)`;
  · `spawn.js#composeArgv` composes it through `resolveEffort()` — the SAME function
    `launch-profiles/resolveProfile` calls, never a second reading of the table.

WHAT A RUNG IS (owner ruling `d-0811lp-effort-numeric-per-profile`): an integer 1..N, ordered lowest
to highest reasoning, in the ladder THAT PROFILE declares in `spawn-profiles.yaml` (`effort.rungs`).
N differs per harness — claude 5 (low·medium·high·xhigh·max), codex 3, kimi 2 — so a rung is only
meaningful against a profile, and a request outside that profile's range is REFUSED naming it. A
profile with no dial (`effort: { inert: true }`, e.g. `claude-haiku` and the whole `opencode-*` set)
ACCEPTS any rung and reports it inert (G-270): the dial visibly does nothing there, which is the
honest report rather than a silent drop. Omit the rung and the harness runs its own default.

⚠ THE RUNG IS WRITTEN WITH THE PROFILE, ALWAYS, AND CLEARED WHEN NONE IS GIVEN. `request opus`
without `--effort` REMOVES `master_effort`. That is not tidiness: a rung left behind across a switch
to a shorter-laddered harness (rung 4 on claude, then a switch to codex, whose top is 3) would pass
every door here and REFUSE AT THE SPAWN, one owner message later — the exact failure mode the
profile-name validation exists to prevent, one field over.

WHY THIS IS TWO HALVES AND NOT ONE COMMAND
-------------------------------------------
Identical to its sibling `goal-launch-delay`, and to `goal-creation-request` before it: the channel
master's cage binds `.rbtv/config` READ-ONLY (`touch` answers `Read-only file system`), so the seat
cannot write this file; `fire-tool` argv is STATIC, so no gateway verb can carry a request body to a
fired tool, and the payload must travel as a FILE staged in the seat's own folder; `enqueue-job` is
the one gateway verb open to every sender kind including a `bridge` token, so it is the trigger.

⚠ THE RESTART IS THE LAST ACT. The bridge config is boot-read by `rbtv-chat-bridge.service`, so the
edit is inert until that unit restarts — and the restart kills the very conversation the requesting
sitting is having. Edit first, outcome record on disk second, restart last: a sitting that vanishes
mid-restart still finds its answer written when the next one reads the inbox.

THE SELF-REPORT — WHY THE OUTCOME TRAVELS BACK ON THE COORDINATION BUS
----------------------------------------------------------------------
An outcome record in `done/` is durable but SILENT: the sitting that asked for the change is killed
by the restart, and the owner is left watching a Slack thread where nothing ever answers (issue
`i-profile-switch-no-feedback`, owner-ruled 2026-08-10). So `request` now takes the sitting's own
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

⚠ THE REPORT PRECEDES THE RESTART, so it cannot state the restart's exit code — it states what is
ABOUT to happen. Restart-last is a ruled invariant (above); reporting after it would mean reporting
from inside a killed process. The rc stays where it always was: the outcome record on disk.

⚠ A FAILED APPEND NEVER ABORTS THE APPLY. The switch is the job; the report is the courtesy. A
report that cannot be written is recorded IN the outcome record (`chat-report.error`) and the fire
continues — losing the change to save the message would be exactly backwards.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

_IGNITE = Path(__file__).resolve().parents[3]
DEFAULT_PROFILES = _IGNITE / "config" / "spawn-profiles.yaml"
DAEMON_OPERATOR = _IGNITE / "capabilities" / "daemon-operator" / "tool" / "rbtv-ignite-daemon"
TEAM_KIT = _IGNITE / "team-kit"      # `coord.py` — the ONE allocator of bus message ids
# The workspace root is the folder that roots `.rbtv/` — <workspace>/3-resources/tools/rbtv/ignite
DEFAULT_CONFIG = _IGNITE.parents[3] / ".rbtv" / "config" / "chat-bridge-config.json"

KEY = "master_profile"
ENTRY_TOOL_KEY = "master-profile"   # this capability's own `tools:` key
JOB_ID = "master-profile"           # the registered fire-tool job id the client half enqueues

DONE_DIR = "done"
REFUSED_DIR = "refused"


class Refusal(Exception):
    """A refusal names what was rejected and what held instead — never a bare status."""


def known_profiles(profiles_path=DEFAULT_PROFILES):
    """The live `profiles:` key set, read from the config the daemon boots on.

    ⚠ NOT A HARD-CODED ROSTER. The owner-ruled roster changes (four claude models, codex, kimi, the
    opencode set), and a list frozen in this file would refuse a profile that exists or admit one
    that was removed — the second being the failure that reaches the spawn.

    ponytail: a line scan, not a YAML parse. It reads the two-space keys directly under the
    `profiles:` root key and stops at the next root key. Ceiling: it would miss a profile declared
    with a non-standard indent or a quoted key. Upgrade path if that ever happens: PyYAML is
    already a daemon dependency — but a parse here would be the ONLY reader of this document that
    needs one, for a question a scan answers exactly.
    """
    lines = Path(profiles_path).read_text(encoding="utf-8").splitlines()
    at = next((i for i, ln in enumerate(lines) if ln.rstrip() == "profiles:"), None)
    if at is None:
        raise Refusal(f"{profiles_path} declares no root key `profiles:` — refusing to validate a "
                      f"profile name against a list this file does not carry")
    names = []
    for ln in lines[at + 1:]:
        if ln.strip() and not ln.startswith(" ") and not ln.lstrip().startswith("#"):
            break                       # the next root key ends the section
        m = re.match(r"^  ([A-Za-z0-9][A-Za-z0-9._-]*):\s*$", ln)
        if m:
            names.append(m.group(1))
    if not names:
        raise Refusal(f"the `profiles:` section of {profiles_path} declares no profiles — refusing "
                      f"to validate against an empty list, which would refuse EVERY name")
    return names


def validate(name, profiles_path=DEFAULT_PROFILES):
    """The ONE validator, called by both halves. The client so a typo refuses in the sitting that
    made it; the daemon because a client-side check is not a check (the staged payload is written
    by the requester and can be edited between staging and the fire)."""
    if not isinstance(name, str) or not name.strip():
        raise Refusal(f"{KEY} must be a non-empty string, got {name!r}")
    known = known_profiles(profiles_path)
    if name not in known:
        raise Refusal(f"`{name}` is not a declared spawn profile. The live `profiles:` set is: "
                      f"{', '.join(sorted(known))}. Refused HERE because an unknown name does not "
                      f"fail at the bridge — it fails at the spawn, one owner message later.")
    return name


EFFORT_KEY = "master_effort"

# `rungs: [low, medium, high, xhigh, max]` / `rungs: ["--no-thinking", "--thinking"]`, with an
# optional trailing `# comment`. Same ponytail ceiling as `known_profiles` above and for the same
# reason — see that docstring.
_RUNGS = re.compile(r"^\s*rungs:\s*\[([^\]]*)\]")
_INERT = re.compile(r"^\s*effort:\s*\{\s*inert:\s*true\s*\}")


def effort_ladder(profile, profiles_path=DEFAULT_PROFILES):
    """This profile's ordered rungs. `[]` means an INERT dial; `None` means NO dial at all.

    The distinction is the whole point (G-270): inert ACCEPTS a rung and does nothing with it,
    while a profile declaring no `effort:` block at all cannot translate one and refuses.
    """
    lines = Path(profiles_path).read_text(encoding="utf-8").splitlines()
    at = next((i for i, ln in enumerate(lines) if ln.rstrip() == f"  {profile}:"), None)
    if at is None:
        return None
    for ln in lines[at + 1:]:
        if ln.strip() and not ln.startswith("    ") and not ln.lstrip().startswith("#"):
            break                       # the next profile (or root key) ends this one
        if _INERT.match(ln):
            return []
        m = _RUNGS.match(ln)
        if m:
            return [v.strip().strip('"\'') for v in m.group(1).split(",") if v.strip()]
    return None


def validate_effort(profile, rung, profiles_path=DEFAULT_PROFILES):
    """The ONE effort validator, called by both halves — same reason `validate` is, and one more:
    a rung is only meaningful against a PROFILE, so it is checked against the profile this same
    request is switching TO, never against the one in force."""
    if rung is None:
        return None
    if not isinstance(rung, int) or isinstance(rung, bool) or rung < 1:
        raise Refusal(f"effort must be an integer rung >= 1 (rung 1 = lowest reasoning), got {rung!r}")
    ladder = effort_ladder(profile, profiles_path)
    if ladder is None:
        raise Refusal(f"`{profile}` declares no `effort:` block in {profiles_path}, so it cannot "
                      f"translate a rung. Omit the effort: the harness runs its own default.")
    if ladder == []:
        return rung                     # inert — accepted and reported, never silently dropped
    if rung > len(ladder):
        raise Refusal(f"effort {rung} is outside `{profile}`'s range 1..{len(ladder)} "
                      f"({', '.join(f'{i + 1}={v}' for i, v in enumerate(ladder))}). Every harness "
                      f"declares its OWN ladder, so a rung that is valid on one profile is not on "
                      f"another — refused HERE because out of range does not fail at the bridge, "
                      f"it fails at the spawn, one owner message later.")
    return rung


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
    "maximum/deepest/think-hardest → N. If the request names NO effort, OMIT the rung rather than "
    "guessing one — the harness then runs its own default. A profile with no dial accepts a rung "
    "and reports it inert."
)


# ───────────────────────────────────────────────────────────────── the targeted JSON edit
#
# ⚠ A LINE EDIT, NOT A json.load/json.dump ROUND TRIP. The live file is hand-authored with
# one-space indentation; re-dumping it would rewrite every line of a config an operator reads and
# diffs, turning a one-value change into a whole-file diff. The line edit changes exactly the bytes
# that are the value.

_LINE = re.compile(r'^(\s*"%s"\s*:\s*)"([^"]*)"(\s*,?\s*)$' % KEY)
_ELINE = re.compile(r'^(\s*"%s"\s*:\s*)(-?\d+)(\s*,?\s*)$' % EFFORT_KEY)


def read_value(config=DEFAULT_CONFIG):
    """The value in force and where it comes from. Pure read — safe from inside the cage."""
    config = Path(config)
    lines = config.read_text(encoding="utf-8").splitlines(keepends=True)
    effort, effort_line = None, None
    for i, ln in enumerate(lines):
        e = _ELINE.match(ln.rstrip("\n"))
        if e:
            effort, effort_line = int(e.group(2)), i + 1
    for i, ln in enumerate(lines):
        m = _LINE.match(ln.rstrip("\n"))
        if m:
            return {"profile": m.group(2), "source": "explicit", "config": str(config),
                    "line": i + 1, "effort": effort, "effort-line": effort_line,
                    "where": f"{config}:{i + 1} — the `{KEY}` field, read at boot by "
                             f"bridges/chat/config.js and selected for master (DM) traffic by "
                             f"forward-path.js#profileFor"
                             + (f"; `{EFFORT_KEY}` = rung {effort} at :{effort_line}, paired with it "
                                f"by forward-path.js#effortFor" if effort is not None
                                else f"; no `{EFFORT_KEY}` — the harness runs its own default")}
    # No key: `profileFor` falls through to `session_profile`. Say so with the value, because
    # "absent" alone leaves the reader to guess what the master is actually running on.
    doc = json.loads(config.read_text(encoding="utf-8"))
    return {"profile": doc.get("session_profile"), "source": "session_profile-fallback",
            "config": str(config), "line": None, "effort": effort, "effort-line": effort_line,
            "where": f"`{KEY}` is ABSENT from {config}, so forward-path.js#profileFor "
                     f"(`config.masterProfile || config.sessionProfile`) falls back to "
                     f"`session_profile`"}


def write_value(config, name):
    config = Path(config)
    lines = config.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, ln in enumerate(lines):
        m = _LINE.match(ln.rstrip("\n"))
        if m:
            previous = m.group(2)
            lines[i] = f'{m.group(1)}"{name}"{m.group(3)}\n'
            # tmp + os.replace: atomically on disk before anything restarts anything.
            tmp = config.with_name(config.name + f".master-profile.{os.getpid()}.tmp")
            tmp.write_text("".join(lines), encoding="utf-8")
            os.replace(tmp, config)
            return {"action": "updated", "line": i + 1, "previous": previous,
                    "profile": name, "config": str(config)}
    # ⚠ REFUSE RATHER THAN CREATE THE KEY. An absent `master_profile` is a live configuration
    # choice — master traffic riding `session_profile` deliberately — and minting the key would
    # SPLIT the two surfaces without anyone deciding to. That is an operator's edit, not a
    # requester's, and it is one line of JSON for whoever wants it.
    raise Refusal(f"{config} carries no `{KEY}` field. Master traffic is currently riding "
                  f"`session_profile` by fallback, and creating the key would split the two "
                  f"surfaces apart — a configuration decision, not a value change. Add "
                  f"`\"{KEY}\": \"<profile>\"` to that file by hand first; this tool then owns it.")


def write_effort(config, rung):
    """Set, replace or REMOVE the `master_effort` line. Unlike `write_value` this one may CREATE
    its key — and the asymmetry is not an oversight. An absent `master_profile` is a live
    configuration choice (master traffic riding `session_profile` by fallback), so minting it would
    decide something nobody decided; an absent `master_effort` has no such second meaning — it is
    simply "harness default" — and a knob that can be turned up but never down is worse than none.

    ⚠ THE RESULT IS PARSED BEFORE IT IS COMMITTED. This is a line edit into a hand-authored
    document (same reason as `write_value`), and inserting or deleting a line is where a line edit
    can produce invalid JSON — a trailing comma before `}`. `json.loads` on the composed text is
    the cheapest possible proof that it did not, and it runs before `os.replace` touches anything.
    """
    config = Path(config)
    lines = config.read_text(encoding="utf-8").splitlines(keepends=True)
    previous, at = None, None
    for i, ln in enumerate(lines):
        m = _ELINE.match(ln.rstrip("\n"))
        if m:
            previous, at = int(m.group(2)), i
            break

    if rung is None:
        if at is None:
            return {"action": "absent", "previous": None, "effort": None}
        del lines[at]
        action = "removed"
    elif at is not None:
        lines[at] = f'{_ELINE.match(lines[at].rstrip(chr(10))).group(1)}{rung}{_ELINE.match(lines[at].rstrip(chr(10))).group(3)}\n'
        action = "updated"
    else:
        # Inserted directly BELOW `master_profile`, whose indentation and trailing comma it copies:
        # the two are one setting in two fields and a reader diffs them together.
        host = next((i for i, ln in enumerate(lines) if _LINE.match(ln.rstrip("\n"))), None)
        if host is None:
            raise Refusal(f"{config} carries no `{KEY}` field to pair an effort with — set the "
                          f"profile first (this tool refuses to create that key; see write_value).")
        m = _LINE.match(lines[host].rstrip("\n"))
        indent = m.group(1)[:len(m.group(1)) - len(m.group(1).lstrip())]
        lines.insert(host + 1, f'{indent}"{EFFORT_KEY}": {rung},\n')
        action = "created"

    text = "".join(lines)
    try:
        json.loads(text)
    except Exception as exc:
        raise Refusal(f"the composed {config} is not valid JSON after the `{EFFORT_KEY}` edit "
                      f"({type(exc).__name__}: {exc}) — NOTHING was written")
    tmp = config.with_name(config.name + f".master-effort.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, config)
    return {"action": action, "previous": previous, "effort": rung}


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

RESTART_UNIT = "rbtv-chat-bridge"


def validate_chat_thread(thread):
    """The ONE thread-id validator, called by both halves — same reason `validate` is."""
    if not isinstance(thread, str) or not CHAT_THREAD_RE.match(thread):
        raise Refusal(f"--chat-thread must be `<channel>:<ts>` — a Slack channel id then a colon "
                      f"then the thread timestamp (e.g. C0ABCDEFG:1754812345.123456); got "
                      f"{thread!r}. Refused HERE because bus-ferry.js routes on exactly this shape "
                      f"and silently ignores anything else — an accepted-but-unroutable token is a "
                      f"report nobody ever receives.")
    return thread


def _bus_dir(inbox):
    """The coordination bus of the goal the request was STAGED IN — `<goal>/coordination`.

    DERIVED, never named: the inbox is `<goal>/settings-requests/<capability>`, so its grandparent
    IS the requesting goal's folder, and that goal's bus is the one the ferry enumerates for it.
    Naming `_channel-master` here would hard-code one workspace's goal into a repo whose components
    must be general — and would send a probe's report onto the live bus.
    """
    return Path(inbox).resolve().parents[1] / "coordination"


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


def _report_body(record, restart):
    """Slack mrkdwn, and only mrkdwn: no pipe tables, no `#` headings, no `[](…)` links — the ferry
    delivers a conformant body VERBATIM, and a markdown-ism arrives as literal punctuation."""
    if record["outcome"] == "ACCEPTED":
        change = record.get("change") or {}
        # NOT an rc — the report precedes the restart by ruling, so it says what is about to happen.
        line = (f"restarting `{RESTART_UNIT}` now — the last act of this job, and it ends this sitting"
                if restart else
                f"SKIPPED (--no-restart) — the change stays inert until `{RESTART_UNIT}` restarts")
        eff = record.get("effort-change") or {}
        rung = record.get("requested-effort")
        if rung is None:
            effort_line = "effort: harness default (no rung set)"
        elif record.get("effort-inert"):
            effort_line = (f"effort: rung {rung} recorded, but `{record['requested']}` has NO dial "
                           f"(inert) — it will apply nothing")
        else:
            effort_line = f"effort: rung {rung} of `{record['requested']}`'s ladder ({record.get('effort-ladder')})"
        if eff.get("previous") is not None and eff.get("previous") != rung:
            effort_line += f"  (was rung {eff['previous']})"
        return (f"*master profile changed* — `{change.get('previous')}` → `{record['requested']}`\n"
                f"{effort_line}\n"
                f"restart: {line}\n"
                f"scope: applies to NEW threads only — this thread stays on its current profile")
    return (f"*master profile change REFUSED* — still `{record['before']['profile']}`\n"
            f"why: {str(record.get('stated-refusal'))[:600]}\n"
            f"restart: none — nothing changed")


# ─────────────────────────────────────────────────────────────────────────── the client half

def request(inbox, name, ignite_bin, profiles_path=DEFAULT_PROFILES, job_id=JOB_ID, dry_run=False,
            chat_thread=None, effort=None):
    validate(name, profiles_path)
    validate_effort(name, effort, profiles_path)     # against the TARGET profile, not the one in force
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
    out["warning"] = ("applying this restarts rbtv-chat-bridge, which ENDS the live chat session "
                      "this request was made from. The next owner message opens a new one, on the "
                      "new profile.")
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
    record.setdefault("restart", "pending")
    _outcome(dest, record)
    return record


def _restart():
    """Delegated to `daemon-operator` (PRIN-11) — `RBTV_IGNITE_UNIT` steers it at a throwaway unit
    for the probe, exactly as it does for `rbtv-ignite-ticker`."""
    r = subprocess.run([str(DAEMON_OPERATOR), "restart", "--service", "chat-bridge"],
                       capture_output=True, text=True)
    return {"rc": r.returncode, "cmd": f"{DAEMON_OPERATOR} restart --service chat-bridge",
            "unit": os.environ.get("RBTV_IGNITE_UNIT", "rbtv-chat-bridge.service"),
            "stdout": r.stdout.strip()[-800:], "stderr": r.stderr.strip()[-800:]}


def apply(inbox, config, profiles_path=DEFAULT_PROFILES, restart=True, dry_run=False):
    """Drain, apply, then restart the bridge — in that order, once per fire."""
    inbox = Path(inbox)
    if not inbox.is_dir():
        raise Refusal(f"the staged inbox {inbox} does not resolve to a directory — nothing to drain")
    for candidate in (inbox, inbox / DONE_DIR, inbox / REFUSED_DIR):
        if candidate.is_symlink():
            raise Refusal(f"{candidate} is a symlink, and this verb refuses to drain through one. "
                          f"NOTHING was drained; replace it with a real directory.")

    before = read_value(config)
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
            name = validate(payload["master-profile"], profiles_path)
            record["requested"] = name
            # Client-side validation is not validation: the payload is written by the requester and
            # can be edited between staging and the fire. Re-checked here against the SAME target.
            rung = validate_effort(name, payload.get("effort"), profiles_path)
            ladder = effort_ladder(name, profiles_path)
            record["requested-effort"] = rung
            record["effort-inert"] = ladder == []
            record["effort-ladder"] = (None if not ladder else
                                       ", ".join(f"{i + 1}={v}" for i, v in enumerate(ladder)))
            if not dry_run:
                record["change"] = write_value(config, name)
                # ⚠ THE PAIR IS WRITTEN TOGETHER AND AN OMITTED RUNG CLEARS THE OLD ONE — see the
                # module docstring: a rung outliving its profile refuses at the spawn, not here.
                record["effort-change"] = write_effort(config, rung)
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

    # ── THE SELF-REPORT, AND IT RUNS BEFORE THE RESTART BELOW ────────────────────────────────
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
                                                _report_body(r, restart),
                                                "wake" if r["outcome"] == "REFUSED" else "post")
            if r.get("moved-to"):
                _outcome(Path(r["moved-to"]), r)

    if accepted and not dry_run:
        out["after"] = read_value(config)
        out["restart"] = _restart() if restart else {"skipped": "--no-restart"}
        for r in results:
            if r["outcome"] == "ACCEPTED" and r.get("moved-to"):
                r["restart"] = out["restart"]
                r["after"] = out["after"]
                _outcome(Path(r["moved-to"]), r)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="rbtv-master-profile",
        description="read and change which harness+model — and at which reasoning RUNG — the "
                    "channel master's next sitting runs on: the `master_profile` and "
                    "`master_effort` fields of .rbtv/config/chat-bridge-config.json")
    # ⚠ THE OPTIONS HANG OFF THE VERBS, NOT OFF THE ROOT PARSER — a FIX, not a style call. As root
    # options argparse accepts them only BEFORE the verb, while the `tools:` entry and every
    # documented example spell them after (`apply --inbox … --config X --profiles Y`). The twin
    # capability's first live fire died on exactly that (`error: unrecognized arguments: --config`),
    # leaving the request un-drained and the execution recorded `failed`. Shared parent parsers keep
    # ONE definition of each option and admit it where callers actually put it.
    cfg_opt = argparse.ArgumentParser(add_help=False)
    cfg_opt.add_argument("--config", default=str(DEFAULT_CONFIG),
                         help="the chat-bridge config that carries the knob (default: the live one)")
    prof_opt = argparse.ArgumentParser(add_help=False)
    prof_opt.add_argument("--profiles", default=str(DEFAULT_PROFILES),
                          help="the spawn-profiles document a requested name is validated against")
    sub = p.add_subparsers(dest="verb", required=True)

    s = sub.add_parser("show", parents=[cfg_opt, prof_opt],
                       help="print the profile in force, where it comes from, and the "
                            "names that may be requested")
    s.add_argument("--json", action="store_true")

    q = sub.add_parser("request", parents=[prof_opt],
                       help="[the seat's verb] stage a change and enqueue the daemon "
                            "job that applies it")
    q.add_argument("profile")
    q.add_argument("--effort", type=int, default=None,
                   help="the reasoning RUNG for the NEW profile: an integer 1..N in that profile's "
                        "own ladder, 1 = lowest reasoning. `show` prints every profile's N. OMIT IT "
                        "and the harness default is used — and any rung currently set is CLEARED, "
                        "because a rung is only meaningful against the profile it was chosen "
                        "for. " + EFFORT_GUIDANCE)
    q.add_argument("--inbox", required=True)
    q.add_argument("--ignite-bin", default="ignite")
    q.add_argument("--chat-thread", default=None,
                   help="`<channel>:<ts>` — YOUR OWN chat thread, the plain `chat-thread:` line at "
                        "the top of your prompt. Given it, the daemon reports the outcome back "
                        "into that thread; omitted, the outcome is only the file in done/refused/")
    q.add_argument("--dry-run", action="store_true")

    a = sub.add_parser("apply", parents=[cfg_opt, prof_opt],
                       help="[the daemon's verb] drain the inbox, edit the config, "
                            "restart the bridge")
    a.add_argument("--inbox", required=True)
    a.add_argument("--no-restart", action="store_true")
    a.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)
    try:
        if args.verb == "show":
            v = read_value(args.config)
            v["available"] = sorted(known_profiles(args.profiles))
            v["effort-ladders"] = ladders(args.profiles)
            v["effort-guidance"] = EFFORT_GUIDANCE
            if args.json:
                print(json.dumps(v, indent=2))
            else:
                print(f"master_profile: {v['profile']}  ({v['source']})")
                print(f"master_effort:  {v['effort'] if v['effort'] is not None else 'unset (harness default)'}"
                      f"   [{v['effort-ladders'].get(v['profile'], 'unknown profile')}]")
                print(f"from: {v['where']}")
                print("available (profile — effort rungs you may ask for):")
                for n in v["available"]:
                    print(f"  {n}: {v['effort-ladders'][n]}")
                print(textwrap.fill(EFFORT_GUIDANCE, 96, subsequent_indent="  "))
                print("boot-read: a change needs an `rbtv-chat-bridge` restart to take effect, "
                      "and that restart ends the live chat session")
            return 0
        if args.verb == "request":
            out = request(args.inbox, args.profile, args.ignite_bin, profiles_path=args.profiles,
                          dry_run=args.dry_run, chat_thread=args.chat_thread, effort=args.effort)
            print(json.dumps(out, indent=2))
            return 0 if out["ok"] else 1
        out = apply(args.inbox, args.config, profiles_path=args.profiles,
                    restart=not args.no_restart, dry_run=args.dry_run)
        print(json.dumps(out, indent=2))
        return 0 if out["ok"] else 1
    except Refusal as exc:
        print(json.dumps({"ok": False, "refusal": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
