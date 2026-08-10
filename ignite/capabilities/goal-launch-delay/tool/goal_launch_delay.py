#!/usr/bin/env python3
"""goal_launch_delay — the channel master's own control over ONE operating parameter of its own:
how long a master-created goal waits before its first workflow job fires (issue C-1, owner-ruled
2026-08-10).

WHAT THE KNOB ACTUALLY IS, AND WHERE IT LIVES
---------------------------------------------
There is no "delay setting" anywhere in this system. The delay is the OPERAND of `--delay-seconds`
in the `tools: goal-creation-request:` argv of `ignite/config/spawn-profiles.yaml`, read by
`goal_creation_request.py#scaffold_and_queue` and turned into the queued job's `--at`. When the flag
is ABSENT from that argv the tool's own argparse default (600) applies — so "absent" and "600" are
the same effective value reached two different ways, and `show` says WHICH of the two is in force
rather than printing a number that hides the difference.

The owner's ruling was explicit about the shape: **do not change the system, give the agent a tool
to interact with it in its native place**. So this file edits those two lines of YAML and nothing
else. It does not introduce a settings file, it does not mirror the value anywhere, and it never
round-trips the YAML through a parser — `spawn-profiles.yaml` is ~1300 lines of load-bearing
COMMENTS, and a dump-and-rewrite would destroy the document that explains the config it holds.

WHY THIS IS TWO HALVES AND NOT ONE COMMAND
-------------------------------------------
Measured, and the measurement is the whole design (same measurement `goal-creation-request` was
built on, re-confirmed for this file): the channel master's cage binds the rbtv repo READ-ONLY —
`touch` inside it answers `Read-only file system` — so a CLI run BY THE SEAT cannot write
`spawn-profiles.yaml`, and no amount of care in this file changes that. The daemon can.

So the transport is split exactly as `goal-creation-request`'s is, for exactly the same two reasons:

  · the PAYLOAD is FILE-STAGED into the requester's own seat folder, because `fire-tool`'s argv is
    STATIC — only `args.workdir` crosses from a queue row — so there is no gateway verb that can
    carry a request body to a fired tool;
  · the TRIGGER is the gateway verb `enqueue-job`, because that is the ONE door open to every
    sender kind including the chat `bridge` token (`register-job`, by contrast, is refused to a
    bridge token by `authz.canRegisterJob`).

`request` is the client half (runs in the cage, writes only inside the seat folder, enqueues).
`apply` is the daemon half (fired unsandboxed by the ticker, edits the YAML, restarts the daemon).
`show` is a READ and runs anywhere — the cage's bind is read-only, not unreadable.

⚠ THE RESTART IS THE LAST ACT, AND THAT ORDERING IS LOAD-BEARING. `spawn-profiles.yaml` is
boot-read (`loadMergedConfig`, no `fs.watch`), so an edit that is not followed by a daemon restart
changes nothing observable. But a fired tool restarting the daemon that fired it is a process asking
to be killed mid-run: `runToolLikeExec` launches through `systemd-run --user`, which creates its own
TRANSIENT UNIT under the user manager rather than a child in `rbtv-ignite.service`'s cgroup — so it
SURVIVES the restart (verified live, this build: the tool's own outcome record was written after the
restart it performed). We do not lean on that anyway: the YAML is written with tmp+`os.replace`
(atomic) and every outcome record is on disk BEFORE the restart is invoked, so even a kill mid-restart
loses nothing but the `restart` field's final value, which then honestly reads `pending`.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# The capability tree is the anchor: <rbtv>/ignite/capabilities/goal-launch-delay/tool/<this file>
_IGNITE = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = _IGNITE / "config" / "spawn-profiles.yaml"
DAEMON_OPERATOR = _IGNITE / "capabilities" / "daemon-operator" / "tool" / "rbtv-ignite-daemon"

# The `tools:` entry whose argv carries the knob. A constant, not a flag: there is exactly one
# entry that queues a master-created goal's first job, and making it selectable would invite a
# request that retimes some OTHER tool's argv.
ENTRY = "goal-creation-request"
FLAG = "--delay-seconds"

# The `tools:` key of THIS capability's own entry — what the fired job's `tool` arg must name.
# Distinct from ENTRY above, and the two are easy to confuse: ENTRY is the argv this tool EDITS,
# ENTRY_TOOL_KEY is the argv the daemon fires to run this tool.
ENTRY_TOOL_KEY = "goal-launch-delay"

# The value the tool's own argparse default supplies when the flag is absent from the argv.
# Duplicated here deliberately (the same call `goal_creation_request.py` makes on the other side),
# so `show` can say "absent — the tool default applies" with the number, instead of printing a
# blank where a reader would supply their own guess.
TOOL_DEFAULT = 600

# The ceiling is a REFUSAL, not a clamp. A request for 10_000_000 is a mistake, and silently
# storing 86400 for it would hide the mistake behind a plausible number. 86400 = one day: past it
# the "10 minutes out" the master's own task-goal names has stopped meaning anything.
MIN_SECONDS = 1
MAX_SECONDS = 86400

DONE_DIR = "done"
REFUSED_DIR = "refused"

JOB_ID = "goal-launch-delay"   # the registered fire-tool job id the client half enqueues


class Refusal(Exception):
    """A refusal names what was rejected and what held instead — never a bare status."""


# ─────────────────────────────────────────────────────────────────── the targeted YAML edit
#
# ⚠ NO YAML LIBRARY, AND THAT IS THE POINT. Round-tripping `spawn-profiles.yaml` through
# `yaml.safe_load`/`dump` would drop every comment in it — and this file's comments ARE its
# documentation (the `tools:` header alone carries the containment warning every future entry
# author must read). So the edit is line-precise: locate the entry's argv block, then rewrite or
# insert exactly the two lines that are the flag and its operand.

def _entry_span(lines):
    """(argv_start, block_end) line indices for the `tools: ENTRY:` argv list.

    Refuses rather than guessing at every step: a wrong span here would edit some other tool's
    command line, which is the one outcome worse than not editing at all.
    """
    tools_at = next((i for i, ln in enumerate(lines) if ln.rstrip("\n") == "tools:"), None)
    if tools_at is None:
        raise Refusal("no root key `tools:` in the config — this is not a spawn-profiles document")

    entry_at = None
    for i in range(tools_at + 1, len(lines)):
        ln = lines[i]
        if ln.rstrip("\n") == f"  {ENTRY}:":
            entry_at = i
            break
        # A root key (column 0, not a comment, not blank) ends the `tools:` section.
        if ln[:1] not in (" ", "#", "\n", ""):
            break
    if entry_at is None:
        raise Refusal(f"the `tools:` section declares no `{ENTRY}:` entry — nothing to retime")

    # The block runs to the next SIBLING entry (2-space indent, not a comment) or the next root key.
    block_end = len(lines)
    for i in range(entry_at + 1, len(lines)):
        ln = lines[i]
        if ln[:1] not in (" ", "#", "\n", "") or re.match(r"^  [^\s#]", ln):
            block_end = i
            break

    argv_at = next((i for i in range(entry_at + 1, block_end)
                    if lines[i].rstrip("\n") == "    argv:"), None)
    if argv_at is None:
        raise Refusal(f"the `{ENTRY}:` entry declares no `argv:` list")
    return argv_at + 1, block_end


def _argv_items(lines, start, end):
    """[(index, indent, value)] for the argv list's own items ONLY.

    Indent-pinned to the FIRST item: sibling keys of `argv:` (`args_allowlist:`) carry `- ` items at
    a DEEPER indent, and treating one of those as an argv operand would edit an allowlist.
    """
    items, indent = [], None
    for i in range(start, end):
        s = lines[i].strip()
        if not s or s.startswith("#"):
            continue
        if not s.startswith("- "):
            break                       # a sibling key of `argv:` — the list is over
        lead = len(lines[i]) - len(lines[i].lstrip(" "))
        if indent is None:
            indent = lead
        elif lead != indent:
            continue                    # deeper `- ` items belong to a nested key, not to argv
        items.append((i, lead, s[2:].strip().strip('"').strip("'")))
    if indent is None:
        raise Refusal(f"the `{ENTRY}:` argv list is empty")
    return items


def read_value(config):
    """The effective delay, and WHERE it comes from. Pure read — safe from inside the cage."""
    lines = Path(config).read_text(encoding="utf-8").splitlines(keepends=True)
    argv_start, block_end = _entry_span(lines)
    items = _argv_items(lines, argv_start, block_end)
    for pos, (idx, _indent, val) in enumerate(items):
        if val == FLAG:
            if pos + 1 >= len(items):
                raise Refusal(f"`{FLAG}` is the LAST argv item — it has no operand, and the fired "
                              f"tool would refuse with `expected one argument`")
            op_idx, _, op_val = items[pos + 1]
            try:
                seconds = int(op_val)
            except ValueError:
                raise Refusal(f"the `{FLAG}` operand on line {op_idx + 1} is `{op_val}`, "
                              f"which is not an integer")
            return {"seconds": seconds, "source": "explicit",
                    "config": str(config), "line": op_idx + 1,
                    "where": f"{config}:{op_idx + 1} — `tools: {ENTRY}:` argv, operand of {FLAG}"}
    return {"seconds": TOOL_DEFAULT, "source": "tool-default",
            "config": str(config), "line": None,
            "where": (f"{FLAG} is ABSENT from the `tools: {ENTRY}:` argv in {config}, so "
                      f"`goal_creation_request.py`'s own argparse default ({TOOL_DEFAULT}) applies")}


def write_value(config, seconds):
    """Set the operand in place. Returns a dict describing exactly which lines moved."""
    config = Path(config)
    text = config.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    argv_start, block_end = _entry_span(lines)
    items = _argv_items(lines, argv_start, block_end)

    positions = [p for p, it in enumerate(items) if it[2] == FLAG]
    if len(positions) > 1:
        raise Refusal(f"the `{ENTRY}:` argv declares `{FLAG}` {len(positions)} times — refusing to "
                      f"guess which one the fired tool honours (argparse takes the LAST). "
                      f"Remove the duplicates by hand first.")

    if positions:
        op_idx, indent, old = items[positions[0] + 1]
        lines[op_idx] = f'{" " * indent}- "{seconds}"\n'
        change = {"action": "updated", "line": op_idx + 1, "previous": old}
    else:
        # Insert AFTER the last argv item: argparse is order-insensitive over optionals, and
        # appending is the only insertion point that cannot split a flag from its operand.
        last_idx, indent, _ = items[-1]
        lines[last_idx + 1:last_idx + 1] = [f'{" " * indent}- {FLAG}\n',
                                            f'{" " * indent}- "{seconds}"\n']
        change = {"action": "inserted", "line": last_idx + 2, "previous": None}

    # tmp + os.replace: the edit is atomically on disk before anything restarts anything, so the
    # ordering promise in this module's docstring is carried by the filesystem, not by a comment.
    tmp = config.with_name(config.name + f".goal-launch-delay.{os.getpid()}.tmp")
    tmp.write_text("".join(lines), encoding="utf-8")
    os.replace(tmp, config)
    change["config"] = str(config)
    change["seconds"] = seconds
    return change


def validate(seconds):
    """The ONE validator. Both halves call it — the client so a typo refuses in the sitting that
    made it, the daemon because a client-side check is not a check (the payload file is written by
    the requester and can be edited after staging)."""
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise Refusal(f"delay-seconds must be an integer, got {type(seconds).__name__} "
                      f"({seconds!r}) — a quoted or fractional value is refused rather than "
                      f"coerced, because the coercion is where a 1.5 becomes a 1")
    if not (MIN_SECONDS <= seconds <= MAX_SECONDS):
        raise Refusal(f"delay-seconds {seconds} is outside [{MIN_SECONDS}, {MAX_SECONDS}] "
                      f"(one day). Refused, NOT clamped: a silently clamped value hides the "
                      f"mistake behind a plausible number.")
    return seconds


# ─────────────────────────────────────────────────────────────────────────── the client half

def request(inbox, seconds, ignite_bin, job_id=JOB_ID, dry_run=False):
    validate(seconds)
    inbox = Path(inbox)
    if inbox.is_symlink():
        raise Refusal(f"{inbox} is a symlink — refusing to stage through one")
    inbox.mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    staged = inbox / name
    out = {"ok": True, "staged": str(staged), "delay-seconds": seconds}
    if dry_run:
        out["staged"] = None
        out["dry-run"] = True
        return out
    staged.write_text(json.dumps({"delay-seconds": seconds}, indent=2) + "\n", encoding="utf-8")

    # The TRIGGER. `enqueue-job` carries no authz gate, so this leg works whichever sender kind the
    # channel master presents. `--at` now: the row fires on the next tick.
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = subprocess.run([ignite_bin, "add-job", "--fn", job_id,
                        "--args-json", json.dumps({"tool": ENTRY_TOOL_KEY}),
                        "--trigger", "scheduled", "--at", at],
                       capture_output=True, text=True)
    out["enqueue"] = {"rc": r.returncode, "at": at,
                      "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    if r.returncode != 0:
        # NOT a refusal of the request: the payload is staged and the next fire of this tool drains
        # it. Saying so is the difference between a recoverable state and a silent drop.
        out["ok"] = False
        out["note"] = (f"the request is STAGED at {staged} but the enqueue failed — it will be "
                       f"applied by the next fire of this tool, or re-run the enqueue by hand")
    return out


# ─────────────────────────────────────────────────────────────────────────── the daemon half

def _outcome(dest, record):
    dest.with_suffix(".outcome.json").write_text(json.dumps(record, indent=2) + "\n",
                                                 encoding="utf-8")


def apply(inbox, config, restart=True, dry_run=False):
    """Drain the staged inbox, apply the LAST accepted value, then restart — in that order.

    ⚠ ONE RESTART PER FIRE, NOT ONE PER REQUEST. Restarting the daemon three times because a
    requester staged three files would take supervision down three times to reach one end state.
    """
    inbox = Path(inbox)
    if not inbox.is_dir():
        raise Refusal(f"the staged inbox {inbox} does not resolve to a directory — nothing to drain")
    # Same escape, same guard, same reason as `goal_creation_request.py#scaffold_and_queue`: the
    # inbox lives inside the REQUESTER's folder, so a pre-created symlink would relocate the
    # daemon's writes outside the cage.
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
            if not isinstance(payload, dict) or set(payload) != {"delay-seconds"}:
                raise Refusal(f"the payload must be exactly {{\"delay-seconds\": <int>}}; "
                              f"got keys {sorted(payload) if isinstance(payload, dict) else type(payload).__name__}")
            seconds = validate(payload["delay-seconds"])
            record["requested"] = seconds
            if not dry_run:
                record["change"] = write_value(config, seconds)
            verdict = "ACCEPTED"
            accepted.append(seconds)
        except Refusal as exc:
            verdict, record["stated-refusal"] = "REFUSED", str(exc)
        except Exception as exc:
            # The whole per-request body is the refusal arm — a directory named `*.json`, an
            # unreadable entry, or a schema-legal non-int all refuse THIS request instead of
            # killing the fire and wedging every later one behind a file that never leaves.
            verdict = "REFUSED"
            record["stated-refusal"] = f"{type(exc).__name__}: {exc}"
        record["outcome"] = verdict
        results.append(_settle(inbox, src, verdict, record, dry_run))

    out = {"ok": all(r["outcome"] == "ACCEPTED" for r in results),
           "drained": len(results), "before": before, "results": results}

    if accepted and not dry_run:
        out["after"] = read_value(config)
        out["restart"] = _restart() if restart else {"skipped": "--no-restart"}
        # Re-stamp every accepted outcome now the restart's verdict is known. The records were
        # already durable BEFORE the restart — this only upgrades `pending` to the real answer.
        for r in results:
            if r["outcome"] == "ACCEPTED" and r.get("moved-to"):
                r["restart"] = out["restart"]
                r["after"] = out["after"]
                _outcome(Path(r["moved-to"]), r)
    return out


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
    # The outcome is written where the REQUESTER can read it — the folder it staged into. An
    # outcome a caged requester cannot read is a silent drop, accepted or refused alike.
    _outcome(dest, record)
    return record


def _restart():
    """Delegated to `daemon-operator`, never re-implemented (PRIN-11, and the same delegation
    `rbtv-ignite-ticker` makes). `RBTV_IGNITE_UNIT` therefore steers this at a throwaway unit
    exactly as it steers that one — which is how the probe proves the flow without restarting the
    live daemon."""
    r = subprocess.run([str(DAEMON_OPERATOR), "restart", "--service", "ignite"],
                       capture_output=True, text=True)
    return {"rc": r.returncode, "cmd": f"{DAEMON_OPERATOR} restart --service ignite",
            "unit": os.environ.get("RBTV_IGNITE_UNIT", "rbtv-ignite.service"),
            "stdout": r.stdout.strip()[-800:], "stderr": r.stderr.strip()[-800:]}


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="rbtv-goal-launch-delay",
        description="read and change how long a master-created goal waits before its first "
                    "workflow job fires — the `--delay-seconds` operand of the "
                    "`tools: goal-creation-request:` argv in spawn-profiles.yaml")
    # ⚠ `--config` HANGS OFF THE VERBS, NOT OFF THE ROOT PARSER, and this is a FIX rather than a
    # style call. It was a root option first, which means argparse only accepts it BEFORE the verb
    # (`… --config X apply`) — while the `tools:` entry, every example in the capability doc, and
    # every hand a reader would write spell it AFTER (`apply --inbox … --config X`). The first live
    # fire died on exactly that: `error: unrecognized arguments: --config …`, the request left
    # un-drained in the inbox, and the `fire-tool` execution recorded `failed`. A shared parent
    # parser keeps ONE definition of the option and admits it in the position callers actually use.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="the spawn-profiles document that carries the knob "
                             "(default: the live one)")
    sub = p.add_subparsers(dest="verb", required=True)

    s = sub.add_parser("show", parents=[common],
                       help="print the delay in force and where it comes from")
    s.add_argument("--json", action="store_true")

    q = sub.add_parser("request", help="[the seat's verb] stage a change and enqueue the daemon "
                                       "job that applies it")
    q.add_argument("seconds", type=int)
    q.add_argument("--inbox", required=True)
    q.add_argument("--ignite-bin", default="ignite")
    q.add_argument("--dry-run", action="store_true")

    a = sub.add_parser("apply", parents=[common],
                       help="[the daemon's verb] drain the inbox, edit the config, restart")
    a.add_argument("--inbox", required=True)
    a.add_argument("--no-restart", action="store_true",
                   help="edit only — the change stays inert until the daemon is restarted")
    a.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)
    try:
        if args.verb == "show":
            v = read_value(args.config)
            if args.json:
                print(json.dumps(v, indent=2))
            else:
                print(f"delay-seconds: {v['seconds']}  ({v['source']})")
                print(f"from: {v['where']}")
                print("boot-read: a change needs an `rbtv-ignite` restart to take effect")
            return 0
        if args.verb == "request":
            out = request(args.inbox, args.seconds, args.ignite_bin, dry_run=args.dry_run)
            print(json.dumps(out, indent=2))
            return 0 if out["ok"] else 1
        out = apply(args.inbox, args.config, restart=not args.no_restart, dry_run=args.dry_run)
        print(json.dumps(out, indent=2))
        return 0 if out["ok"] else 1
    except Refusal as exc:
        print(json.dumps({"ok": False, "refusal": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
