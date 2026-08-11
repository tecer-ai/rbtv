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

⚠ EFFORT IS NOT ON THIS WIRE, AND THE `--effort` FLAG IS THEREFORE ABSENT BY MEASUREMENT, NOT BY
OVERSIGHT. Traced end to end for this build (2026-08-10):

  · `forward-path.js` composes the session-create enqueue as `args: { profile, prompt }` — no
    effort key, and the `chat-agent` job's registered `args_schema` is
    `{required:{profile}, optional:{prompt, workdir}}`, so a row carrying one would be REFUSED at
    the enqueue door (`register-job` is create-only — the schema cannot be widened in place);
  · `ticker.js#launchAgent` reads exactly `args.profile` / `args.prompt` / `args.workdir` and calls
    `spawnManager.spawn(execId, profileName, sessionMode, prompt, workdir, enqueuedBy, resumeRef)`
    — a seven-parameter signature with no effort parameter at all;
  · the effort TRANSLATION table each profile declares (`effort: {dialect, values, argv}`) is
    consumed only by `launch-profiles/resolveProfile`, and `internal-api/dispatch.js` states its
    own status verbatim: `E_UNKNOWN_EFFORT` is *"raised only inside resolveProfile (the effort
    translation table), which has NO daemon caller today"*. `spawn.js` resolves `exec.argv`
    directly and never appends the effort argv.

So the dial exists in the config vocabulary and is not connected to the master's spawn path. Adding
`--effort` here would have written a value nothing reads — a knob that turns and does nothing, which
is worse than no knob. Wiring it is a daemon change (7.43/7.54), not a tool change.

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


# ───────────────────────────────────────────────────────────────── the targeted JSON edit
#
# ⚠ A LINE EDIT, NOT A json.load/json.dump ROUND TRIP. The live file is hand-authored with
# one-space indentation; re-dumping it would rewrite every line of a config an operator reads and
# diffs, turning a one-value change into a whole-file diff. The line edit changes exactly the bytes
# that are the value.

_LINE = re.compile(r'^(\s*"%s"\s*:\s*)"([^"]*)"(\s*,?\s*)$' % KEY)


def read_value(config=DEFAULT_CONFIG):
    """The value in force and where it comes from. Pure read — safe from inside the cage."""
    config = Path(config)
    lines = config.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, ln in enumerate(lines):
        m = _LINE.match(ln.rstrip("\n"))
        if m:
            return {"profile": m.group(2), "source": "explicit", "config": str(config),
                    "line": i + 1,
                    "where": f"{config}:{i + 1} — the `{KEY}` field, read at boot by "
                             f"bridges/chat/config.js and selected for master (DM) traffic by "
                             f"forward-path.js#profileFor"}
    # No key: `profileFor` falls through to `session_profile`. Say so with the value, because
    # "absent" alone leaves the reader to guess what the master is actually running on.
    doc = json.loads(config.read_text(encoding="utf-8"))
    return {"profile": doc.get("session_profile"), "source": "session_profile-fallback",
            "config": str(config), "line": None,
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
        return (f"*master profile changed* — `{change.get('previous')}` → `{record['requested']}`\n"
                f"restart: {line}\n"
                f"scope: applies to NEW threads only — this thread stays on its current profile")
    return (f"*master profile change REFUSED* — still `{record['before']['profile']}`\n"
            f"why: {str(record.get('stated-refusal'))[:600]}\n"
            f"restart: none — nothing changed")


# ─────────────────────────────────────────────────────────────────────────── the client half

def request(inbox, name, ignite_bin, profiles_path=DEFAULT_PROFILES, job_id=JOB_ID, dry_run=False,
            chat_thread=None):
    validate(name, profiles_path)
    if chat_thread is not None:
        validate_chat_thread(chat_thread)
    inbox = Path(inbox)
    if inbox.is_symlink():
        raise Refusal(f"{inbox} is a symlink — refusing to stage through one")
    inbox.mkdir(parents=True, exist_ok=True)
    staged = inbox / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    payload = {"master-profile": name}
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
                    or not set(payload) <= {"master-profile", "chat-thread"}):
                raise Refusal(f"the payload must be {{\"master-profile\": \"<name>\"}} with an "
                              f"optional \"chat-thread\": \"<channel>:<ts>\"; "
                              f"got keys {sorted(payload) if isinstance(payload, dict) else type(payload).__name__}")
            # READ BEFORE THE VALUE IS VALIDATED, so a REFUSED request still knows where to report
            # itself. A malformed token refuses the request instead of being reported into nowhere.
            if payload.get("chat-thread") is not None:
                record["chat-thread"] = validate_chat_thread(payload["chat-thread"])
            name = validate(payload["master-profile"], profiles_path)
            record["requested"] = name
            if not dry_run:
                record["change"] = write_value(config, name)
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
        description="read and change which harness+model the channel master's next sitting runs "
                    "on — the `master_profile` field of .rbtv/config/chat-bridge-config.json")
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
            if args.json:
                print(json.dumps(v, indent=2))
            else:
                print(f"master_profile: {v['profile']}  ({v['source']})")
                print(f"from: {v['where']}")
                print(f"available: {', '.join(v['available'])}")
                print("boot-read: a change needs an `rbtv-chat-bridge` restart to take effect, "
                      "and that restart ends the live chat session")
            return 0
        if args.verb == "request":
            out = request(args.inbox, args.profile, args.ignite_bin, profiles_path=args.profiles,
                          dry_run=args.dry_run, chat_thread=args.chat_thread)
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
