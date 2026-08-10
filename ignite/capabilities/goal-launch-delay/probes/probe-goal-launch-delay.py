#!/usr/bin/env python3
"""probe-goal-launch-delay.py — the daemon half of the delay knob, proven against a COPY.

NOTHING HERE TOUCHES THE LIVE CONFIG OR THE LIVE DAEMON. Every act runs under `tempfile` on a
byte-copy of `ignite/config/spawn-profiles.yaml`, and the restart is a STUB script the module is
pointed at (`mod.DAEMON_OPERATOR`), so no unit is ever driven. That substitution is what makes the
`apply` path runnable at all outside a fire — the real one restarts the daemon running this probe.

  1. THE HAPPY PATH LANDS — a staged `{"delay-seconds": N}` rewrites the operand in the COPY, and
     re-reading the copy answers N. Read from the FILE, never from the returned record: a record
     that echoed its input would satisfy a check that read it back.
  2. THE RESTART IS INVOKED, AND IT IS THE LAST ACT — the stub records its argv AND snapshots the
     config as it stood WHEN IT RAN. That snapshot must already carry the new value. This is the
     one check that discriminates "edit then restart" from "restart then edit", and the ordering is
     the whole reason the module writes with `os.replace` before calling out.
  3. A REFUSAL LEAVES THE FILE BYTE-IDENTICAL — over-ceiling, non-integer, and wrong-shape payloads
     each refuse, each leave a readable `.outcome.json` in `refused/`, and the config's sha256 is
     unchanged from before the fire. No restart is invoked for a fire that accepted nothing.
  4. THE SURGICAL-EDIT CONTROL — an accepted edit changes EXACTLY ONE LINE of a 1300-line document
     whose comments are its documentation. Anything else means the line-precise edit became a
     rewrite, which is the failure this module exists to avoid.
  5. THE INSERT ARM — with the `--delay-seconds` pair deleted from the copy, `show` reports the
     tool default and names it as such, and `apply` INSERTS the pair rather than refusing. Both
     halves of "absent" are exercised, because absent-and-600 and explicit-600 are the same
     effective value reached two different ways.
  6. THE MUTANT — the ceiling is widened in a copy of the module source and check 3's over-ceiling
     case is re-run. It MUST now be accepted. A mutant that stays refused means check 3 is scoring
     nothing (it would pass against a validator that refused everything), and this probe then exits
     2 INOPERATIVE rather than reporting a pass it did not earn.
  7. THE REGISTERED ARGV ITSELF — the argv `config/spawn-profiles.yaml` declares for
     `tools: goal-launch-delay`, read out of that file and run as a SUBPROCESS with only the
     live-state operands substituted. Added after checks 1-6 were all green and the FIRST LIVE FIRE
     still died on `error: unrecognized arguments: --config` (a root-level option the entry spells
     after the verb): every other check calls `apply()` as a function, which is the one surface the
     daemon never touches.
  8. THE SELF-REPORT REACHES THE OWNER'S THREAD, AND IT PRECEDES THE RESTART — `request
     --chat-thread` stages the id and a token the ferry could not route refuses at request time;
     `apply` on a threaded request appends EXACTLY ONE `to: owner` row, parsed back the way
     `bus-ferry.js` parses it (fields BY KEY) and carrying the BRACKETED token; the restart stub's
     snapshot of the bus already holds that row, which is what discriminates report-then-restart
     from restart-then-report; a request with NO token appends nothing at all; and a REFUSED
     request with a token reports its refusal, because "your change did not happen, and here is
     why" is the answer the owner is owed most.
"""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tool" / "goal_launch_delay.py"
LIVE_CONFIG = Path(__file__).resolve().parents[3] / "config" / "spawn-profiles.yaml"
LIVE_PROFILES = LIVE_CONFIG   # same document for this capability: it edits the config it is registered in

failures: list[str] = []
inoperative: list[str] = []


def registered_argv(entry):
    """The argv the LIVE `config/spawn-profiles.yaml` declares for one `tools:` entry.

    Read from the config rather than retyped here: a retyped copy proves the probe author's memory
    of the entry, which is the very thing that was wrong."""
    import re as _re
    lines = LIVE_PROFILES.read_text(encoding="utf-8").splitlines()
    at = next((i for i, ln in enumerate(lines) if ln.rstrip() == f"  {entry}:"), None)
    if at is None:
        return None
    out, seen_argv = [], False
    for ln in lines[at + 1:]:
        if ln.strip() and not ln.startswith("    ") and not ln.lstrip().startswith("#"):
            break
        if ln.rstrip() == "    argv:":
            seen_argv = True
            continue
        s = ln.strip()
        if seen_argv and s.startswith("- "):
            out.append(s[2:].strip().strip('"').strip("'"))
        elif seen_argv and s and not s.startswith("#"):
            break
    return out or None


def load(path, name="gld"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stub_operator(tmp, target, bus=None):
    """A stand-in for `rbtv-ignite-daemon` that records that it ran, and WHAT THE CONFIG LOOKED
    LIKE when it ran. The snapshot is what proves the ordering; the argv alone would not.

    `bus` adds a second snapshot — the coordination log — which is how check 8 discriminates
    report-then-restart from restart-then-report. Guarded, because on every other check the bus
    file legitimately does not exist and a missing file is not a failure."""
    rec, snap = tmp / "restart.argv", tmp / "restart.snapshot"
    bus_snap = tmp / "restart.bus-snapshot"
    s = tmp / "stub-daemon-operator"
    s.write_text("#!/usr/bin/env bash\n"
                 f'printf "%s\\n" "$*" >> {rec}\n'
                 f'cp {target} {snap}\n'
                 + (f'cp {bus} {bus_snap} 2>/dev/null || true\n' if bus else ""),
                 encoding="utf-8")
    s.chmod(0o755)
    return s, rec, snap


# `## 4774 | from: goal-launch-delay | to: owner | type: note | exec: 2026-08-10a | 2026-08-10 14:23`
#
# READ THE FIELDS BY KEY, NEVER BY POSITION — `bus-ferry.js#parseHeader`'s own discipline, and the
# reason it has it: the bus header grammar is ADDITIVE, `from-pkg:` and `exec:` already sit between
# the fixed fields, and a positional regex reads such a row as malformed and drops it silently.
BUS_HEADER_RE = re.compile(r"^## (\d+) \| (.+)$")


def bus_rows(bus):
    """Every row of a coordination log, keyed exactly as the ferry keys them."""
    if not Path(bus).is_file():
        return []
    rows, cur = [], None
    for line in Path(bus).read_text(encoding="utf-8").split("\n"):
        m = BUS_HEADER_RE.match(line)
        if m:
            fields = {}
            for part in m.group(2).split(" | "):
                i = part.find(": ")
                if i > 0:
                    fields[part[:i]] = part[i + 2:].strip()
            cur = {"id": int(m.group(1)), "fields": fields, "body": []}
            rows.append(cur)
        elif cur is not None:
            cur["body"].append(line)
    for r in rows:
        r["body"] = "\n".join(r["body"]).strip()
    return rows


def stage(inbox, payload, name):
    inbox.mkdir(parents=True, exist_ok=True)
    p = inbox / name
    p.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return p


def check(cond, msg):
    if not cond:
        failures.append(msg)
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")


def main():
    mod = load(TOOL)

    # ── 1, 2, 4 ─────────────────────────────────────────────────────────────────────────────
    print("check 1/2/4 — happy path lands, restart is invoked LAST, exactly one line moved")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        cfg = tmp / "spawn-profiles.yaml"
        shutil.copy2(LIVE_CONFIG, cfg)
        before_lines = cfg.read_text(encoding="utf-8").splitlines()
        inbox = tmp / "inbox"
        stub, rec, snap = stub_operator(tmp, cfg)
        mod.DAEMON_OPERATOR = stub

        stage(inbox, {"delay-seconds": 1234}, "a.json")
        out = mod.apply(inbox, cfg)

        check(out["ok"] is True, "the fire reports ok")
        check(mod.read_value(cfg)["seconds"] == 1234,
              f"re-reading the config file answers 1234 (got {mod.read_value(cfg)['seconds']})")
        check(mod.read_value(cfg)["source"] == "explicit", "and reports it as explicit")

        check(rec.exists() and "restart --service ignite" in rec.read_text(),
              f"the restart was invoked once, as `restart --service ignite` "
              f"({rec.read_text().strip() if rec.exists() else '<never ran>'})")
        check(snap.exists() and '- "1234"' in snap.read_text(),
              "the config AS THE RESTART SAW IT already carried the new value — edit precedes restart")

        after_lines = cfg.read_text(encoding="utf-8").splitlines()
        diff = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
        check(len(before_lines) == len(after_lines) and len(diff) == 1,
              f"exactly one line changed and the line count is unchanged "
              f"(changed={len(diff)}, {len(before_lines)}->{len(after_lines)})")
        check(bool(diff) and after_lines[diff[0]].strip() == '- "1234"',
              f"and it is the operand line ({after_lines[diff[0]].strip() if diff else '<none>'})")

        settled = sorted((inbox / "done").glob("*.outcome.json"))
        check(len(settled) == 1, "one outcome record settled into done/")
        if settled:
            r = json.loads(settled[0].read_text())
            check(r["outcome"] == "ACCEPTED" and r["restart"]["rc"] == 0
                  and r["after"]["seconds"] == 1234,
                  "the outcome record the requester reads names ACCEPTED, the restart, and the after-value")

    # ── 3 ───────────────────────────────────────────────────────────────────────────────────
    print("check 3 — every refusal shape leaves the config byte-identical and no restart fires")
    for label, payload in (("over-ceiling", {"delay-seconds": 86401}),
                           ("non-integer", {"delay-seconds": "600"}),
                           ("fractional", {"delay-seconds": 1.5}),
                           ("wrong-shape", {"delay": 60}),
                           ("unparseable", "{not json")):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg = tmp / "spawn-profiles.yaml"
            shutil.copy2(LIVE_CONFIG, cfg)
            digest = sha(cfg)
            inbox = tmp / "inbox"
            stub, rec, snap = stub_operator(tmp, cfg)
            mod.DAEMON_OPERATOR = stub
            stage(inbox, payload, "a.json")
            out = mod.apply(inbox, cfg)
            recs = sorted((inbox / "refused").glob("*.outcome.json"))
            stated = json.loads(recs[0].read_text())["stated-refusal"] if recs else None
            check(out["ok"] is False and sha(cfg) == digest and not rec.exists() and stated,
                  f"{label}: refused, config sha unchanged, no restart, and the requester can read "
                  f"why — {(stated or '<no record>')[:90]}")

    # ── 5 ───────────────────────────────────────────────────────────────────────────────────
    print("check 5 — with the flag absent, show names the tool default and apply INSERTS the pair")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        cfg = tmp / "spawn-profiles.yaml"
        text = LIVE_CONFIG.read_text(encoding="utf-8")
        stripped = text.replace('      - --delay-seconds\n      - "600"\n', "", 1)
        check(stripped != text, "the fixture removed the shipped --delay-seconds pair")
        cfg.write_text(stripped, encoding="utf-8")

        v = mod.read_value(cfg)
        check(v["seconds"] == mod.TOOL_DEFAULT and v["source"] == "tool-default",
              f"show reports {mod.TOOL_DEFAULT} sourced as tool-default (got {v['seconds']}/{v['source']})")

        inbox = tmp / "inbox"
        stub, rec, snap = stub_operator(tmp, cfg)
        mod.DAEMON_OPERATOR = stub
        stage(inbox, {"delay-seconds": 900}, "a.json")
        out = mod.apply(inbox, cfg)
        v2 = mod.read_value(cfg)
        check(out["ok"] and v2["seconds"] == 900 and v2["source"] == "explicit",
              f"apply inserted the pair and the value now reads explicit 900 "
              f"(got {v2['seconds']}/{v2['source']})")
        lines = cfg.read_text(encoding="utf-8").splitlines()
        check(len(lines) == len(stripped.splitlines()) + 2,
              "exactly two lines were inserted (the flag and its operand)")

    # ── 6 THE MUTANT ────────────────────────────────────────────────────────────────────────
    print("check 6 — the mutant: widen the ceiling and the over-ceiling case MUST be accepted")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src = TOOL.read_text(encoding="utf-8")
        mutant_src = src.replace("MAX_SECONDS = 86400", "MAX_SECONDS = 10**9", 1)
        if mutant_src == src:
            inoperative.append("the mutation target `MAX_SECONDS = 86400` was not found in the tool "
                               "source — the mutant proves nothing and check 3 is unscored")
        else:
            # The mutant is nested deep enough that the module's own
            # `Path(__file__).resolve().parents[N]` derivations still resolve — a mutant that
            # cannot IMPORT is not evidence, it is a crash wearing a red verdict.
            mdir = tmp.joinpath(*[f"x{i}" for i in range(8)])
            mdir.mkdir(parents=True)
            mpath = mdir / "mutant.py"
            mpath.write_text(mutant_src, encoding="utf-8")
            mmod = load(mpath, "gld_mutant")
            cfg = tmp / "spawn-profiles.yaml"
            shutil.copy2(LIVE_CONFIG, cfg)
            inbox = tmp / "inbox"
            stub, rec, snap = stub_operator(tmp, cfg)
            mmod.DAEMON_OPERATOR = stub
            stage(inbox, {"delay-seconds": 86401}, "a.json")
            out = mmod.apply(inbox, cfg)
            if not (out["ok"] and mmod.read_value(cfg)["seconds"] == 86401):
                inoperative.append("the mutant did NOT go green — the over-ceiling refusal in "
                                   "check 3 is not being produced by the ceiling check, so check 3 "
                                   "scores nothing")
            print(f"  ok   the mutant accepted 86401 (ceiling widened) — check 3 is discriminating")

    # ── 7 THE REGISTERED ARGV ITSELF ──────────────────────────────────────────────────────
    #
    # ⚠ THIS ARM EXISTS BECAUSE ITS ABSENCE COST A LIVE FIRE. Every check above calls `apply()` as a
    # PYTHON FUNCTION, which is exactly the surface the daemon never touches: the daemon execs the
    # wrapper with the argv `config/spawn-profiles.yaml` declares. `--config` was a ROOT option and
    # that argv puts it after the verb, so the first real fire died with
    # `error: unrecognized arguments: --config …`, drained nothing, and recorded `failed` — while
    # every function-level check stayed green. A check that cannot see the caller's shape is not
    # checking the caller.
    #
    # So: read THIS capability's own `tools:` entry out of the live config, substitute only the two
    # paths that must not point at live files, and run the wrapper as a SUBPROCESS.
    print("check 7 — the argv the `tools: goal-launch-delay` entry actually declares, run as a subprocess")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        argv = registered_argv("goal-launch-delay")
        if argv is None:
            inoperative.append("the live spawn-profiles.yaml carries no `tools: goal-launch-delay` entry — "
                               "the one surface the daemon uses is unchecked")
        else:
            inbox = tmp / "inbox"
            inbox.mkdir()
            stage(inbox, {"delay-seconds": 777}, "a.json")
            cfg = tmp / "spawn-profiles.yaml"
            shutil.copy2(LIVE_CONFIG, cfg)
            # Substitute ONLY the operands that would point at live state. Every other token —
            # including the interpreter, the script path, the verb, and the flag SPELLINGS and
            # ORDER — is the config's own, byte for byte.
            run_argv = list(argv)
            for i, tok in enumerate(run_argv):
                if i and run_argv[i - 1] == "--inbox":
                    run_argv[i] = str(inbox)
                elif i and run_argv[i - 1] == "--config":
                    run_argv[i] = str(cfg)
            env = dict(os.environ)
            # A unit the user manager has never heard of: `daemon-operator` refuses it (exit 1) and
            # drives NOTHING, so the real restart leg is exercised as far as it can be without
            # touching a live service.
            env["RBTV_IGNITE_UNIT"] = "rbtv-probe-no-such-unit-goal-launch-delay.service"
            r = subprocess.run(run_argv, capture_output=True, text=True, env=env)
            check(r.returncode == 0,
                  f"the registered argv runs clean (exit {r.returncode}) — "
                  f"{(r.stderr.strip().splitlines() or [''])[-1][:120]}")
            check(mod.read_value(cfg)["seconds"] == 777,
                  "and the edit it was fired to make landed in the copy")

    # ── 8 THE SELF-REPORT INTO THE OWNER'S OWN CHAT THREAD ────────────────────────────────
    #
    # ⚠ THE INBOX SHAPE IS PART OF THE FIXTURE. The tool DERIVES the bus from the inbox
    # (`<goal>/settings-requests/<capability>` → `<goal>/coordination`) rather than naming a goal,
    # so a flat temp inbox would prove a path the daemon never takes — and a probe that named the
    # live goal would append to the owner's real bus, which a read-only check may not do.
    print("check 8 — the outcome reports itself into the owner's thread, BEFORE the restart")
    THREAD = "C0PROBEGLD:1754812345.123456"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        inbox = tmp / "goal" / "settings-requests" / "goal-launch-delay"
        bus = tmp / "goal" / "coordination" / "messages.md"
        cfg = tmp / "spawn-profiles.yaml"
        shutil.copy2(LIVE_CONFIG, cfg)
        stub, rec, snap = stub_operator(tmp, cfg, bus=bus)
        mod.DAEMON_OPERATOR = stub

        # `/bin/true` stands in for the `ignite` client: `request` stages BEFORE it enqueues, and
        # what is under test here is the payload, not the queue.
        out = mod.request(inbox, 1234, "/bin/true", chat_thread=THREAD)
        staged = json.loads(Path(out["staged"]).read_text())
        check(staged.get("chat-thread") == THREAD,
              f"request --chat-thread stages the id in the payload (got {staged.get('chat-thread')!r})")
        bad_refused = False
        try:
            mod.request(inbox, 1234, "/bin/true", chat_thread="C0PROBEGLD-1754812345")
        except mod.Refusal:
            bad_refused = True
        check(bad_refused, "a token bus-ferry.js could not route refuses in the sitting that typed it")

        prev = mod.read_value(cfg)["seconds"]
        mod.apply(inbox, cfg)
        rows = bus_rows(bus)
        check(len(rows) == 1, f"exactly ONE bus row was appended (got {len(rows)})")
        if rows:
            f, body = rows[0]["fields"], rows[0]["body"]
            check(f.get("from") == "goal-launch-delay" and f.get("to") == "owner"
                  and f.get("type") == "note",
                  f"and its header carries from/to/type the ferry requires ({f})")
            check(f"[chat-thread: {THREAD}]" in body,
                  "the BRACKETED token is in the body — the plain form does not route")
            check(f"`{prev}s` → `1234s`" in body,
                  f"the body states the change as old → new (`{prev}s` → `1234s`)")
            check("restart:" in body, "and names what happens to the unit")
            check(not any(l.startswith("|") or l.startswith("#") for l in body.split("\n")),
                  "the body is mrkdwn — no pipe tables, no markdown headings")
        check(bus.read_text(encoding="utf-8").endswith("\n"),
              "the log ends with a newline — the ferry's torn-write rule only counts a row that does")
        check((tmp / "restart.bus-snapshot").is_file()
              and THREAD in (tmp / "restart.bus-snapshot").read_text(),
              "the bus AS THE RESTART SAW IT already carried the report — report precedes restart")

    print("check 8b — a request with NO chat thread reports nothing at all")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        inbox = tmp / "goal" / "settings-requests" / "goal-launch-delay"
        bus = tmp / "goal" / "coordination" / "messages.md"
        cfg = tmp / "spawn-profiles.yaml"
        shutil.copy2(LIVE_CONFIG, cfg)
        stub, rec, snap = stub_operator(tmp, cfg, bus=bus)
        mod.DAEMON_OPERATOR = stub
        stage(inbox, {"delay-seconds": 1234}, "a.json")
        out = mod.apply(inbox, cfg)
        check(out["ok"] and not bus.exists(),
              "the retiming landed and no bus row exists — an untokened request is silent, as before")

    print("check 8c — a REFUSED outcome carrying a thread reports its refusal too")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        inbox = tmp / "goal" / "settings-requests" / "goal-launch-delay"
        bus = tmp / "goal" / "coordination" / "messages.md"
        cfg = tmp / "spawn-profiles.yaml"
        shutil.copy2(LIVE_CONFIG, cfg)
        digest = sha(cfg)
        stub, rec, snap = stub_operator(tmp, cfg, bus=bus)
        mod.DAEMON_OPERATOR = stub
        stage(inbox, {"delay-seconds": 86401, "chat-thread": THREAD}, "a.json")
        out = mod.apply(inbox, cfg)
        rows = bus_rows(bus)
        check(out["ok"] is False and sha(cfg) == digest and not rec.exists(),
              "the refusal still refuses — config untouched, no restart")
        check(len(rows) == 1 and "REFUSED" in rows[0]["body"]
              and f"[chat-thread: {THREAD}]" in rows[0]["body"],
              f"and exactly one row reports the refusal into the thread (got {len(rows)} row(s))")

    if inoperative:
        print(f"probe-goal-launch-delay: INOPERATIVE — {inoperative}")
        return 2
    if failures:
        print(f"probe-goal-launch-delay: FAIL — {len(failures)} failure(s): {failures}")
        return 1
    print("probe-goal-launch-delay: PASS — the edit lands, the restart is the last act, every "
          "refusal shape leaves the config byte-identical, the absent-flag insert works, and the "
          "ceiling check is proven discriminating by mutation — the argv the daemon "
          "actually fires runs clean as a subprocess, and a request naming its chat thread reports "
          "its outcome (accepted OR refused) as exactly one ferry-parseable bus row written BEFORE "
          "the restart")
    return 0


class _Tee:
    def __init__(self, real):
        self.real, self.buf = real, []

    def write(self, s):
        self.real.write(s)
        self.buf.append(s)
        return len(s)

    def flush(self):
        self.real.flush()


if __name__ == "__main__":
    tee = _Tee(sys.stdout)
    sys.stdout = tee
    try:
        rc = main()
    finally:
        sys.stdout = tee.real
        Path(__file__).with_suffix(".out").write_text("".join(tee.buf), encoding="utf-8")
    sys.exit(rc)
