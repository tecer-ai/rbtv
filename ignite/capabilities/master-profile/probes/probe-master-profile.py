#!/usr/bin/env python3
"""probe-master-profile.py — the daemon half of the master-profile knob, proven against a COPY.

NOTHING HERE TOUCHES THE LIVE CASTING SHEET, THE LIVE GOAL PACKAGE, OR THE LIVE `seat.md`. Every act
runs under `tempfile` on a byte-copy of
`.rbtv/config/modules/meta/master/bindings/channel-master.json`, and the RE-RENDER is a STUB
the module is pointed at (`mod.MATERIALIZE`). The real one rewrites the channel master's own
descriptor, which decides what the owner's next sitting runs — a probe may not move that.

⚠ RETARGETED 2026-08-12, WITH THE TOOL. Every check below used to run against a copy of
`.rbtv/config/chat-bridge-config.json` and a stubbed `rbtv-ignite-daemon restart`. The launch-cast
unification (owner ruling D2, 2026-08-11) deleted that file's readers; the tool now writes the
master's CASTING SHEET and re-renders its `seat.md` from it. Two arms INVERT rather than move, and
both inversions are the point:

  · check 8 asserted the registered argv REFUSED (the tool was parked out of service). It now
    asserts the argv RUNS and LANDS. A capability whose one live surface is asserted to refuse is
    a capability nobody can use.
  · check 10d's `validate_effort` arm is GONE, because the function is. `bindings.cast_seat` is the
    effort validator now — one function for "may I?" and "do it" — so the arm that proved the tool
    consumed the shared ladder reader is re-aimed at `cast_seat` itself.

  1. THE HAPPY PATH LANDS — a staged `{"harness": "claude", "model": "claude-opus-5", "effort": N}` rewrites the
     seat's harness/model/effort in the COPY, and re-reading the FILE answers claude/…. Read from
     the file, never from the record.
  2. THE RE-RENDER IS INVOKED, WITH THE PACKAGE DERIVED FROM THE INBOX, AND IT IS THE LAST ACT —
     the stub records its argv (`--refresh` against `<goal>`, the inbox's own grandparent, never a
     goal named in a flag) AND snapshots the sheet as it stood when it ran, which must already
     carry the new cast. A re-render that preceded the write would render the OLD cast and report
     success.
  3. AN UNKNOWN OR UNCASTABLE PROFILE IS REFUSED AND THE SHEET IS BYTE-IDENTICAL — the refusal
     names the live castable set, and no re-render fires. This is the check the whole capability
     turns on: a bad name does NOT fail when the sheet is written, it fails at the SPAWN, one owner
     message later, with the sitting already accounted for. `test-sleep` is the sharp case — a
     DECLARED profile that `coord.py#validate_seat` rejects, which the old `profiles:`-key-set
     validator would have waved through.
  4. VALIDATION READS THE LIVE ROSTER, NOT A FROZEN LIST — a profile added to a COPY of
     spawn-profiles.yaml is accepted when validated against that copy and refused against a copy
     with it removed. A hard-coded roster passes check 3 and fails here.
  5. AN UNKNOWN SEAT REFUSES RATHER THAN BEING CREATED — a sheet whose `seats` map does not carry
     the named seat is a refusal naming what it does carry. Minting the entry would cast a seat
     nothing materializes.
  6. THE SURGICAL-WRITE CONTROL — every line of the sheet that is not the seat's own casting fields
     survives BYTE FOR BYTE. This arm is not decoration: on 2026-08-12 `bindings._write` dumped
     without `ensure_ascii=False`, so writing three fields also rewrote five lines of hand-authored
     prose (`—` → `\\u2014`) in keys nobody touched. It is a live regression this probe caught only
     because a human diffed the file.
  7. THE MUTANT — the name lookup is neutered in a copy of the module source and check 3 is re-run.
     It MUST now be accepted; otherwise check 3 is scoring nothing and this probe exits 2
     INOPERATIVE rather than reporting a pass it did not earn.
  8. THE REGISTERED ARGV ITSELF — the argv `config/spawn-profiles.yaml` declares for
     `tools: master-profile`, read out of that file and run as a SUBPROCESS with only the
     live-state operands substituted. Added after the twin capability's first live fire died on
     `error: unrecognized arguments: --config` with every function-level check green: the daemon
     execs a command line, and a check that only calls the function never sees it.
  9. THE SELF-REPORT REACHES THE OWNER'S THREAD, AND IT PRECEDES THE RE-RENDER — `request
     --chat-thread` stages the id and a token the ferry could not route refuses at request time;
     `apply` on a threaded request appends EXACTLY ONE `to: owner` row, parsed back the way
     `bus-ferry.js` parses it (fields BY KEY) and carrying the BRACKETED token; the stub's snapshot
     of the bus already holds that row; a request with NO token appends nothing at all; and a
     REFUSED request with a token reports its refusal, because "your switch did not happen, and
     here is why" is the answer the owner is owed most.
 10. THE EFFORT RUNG RIDES WITH THE PROFILE, END TO END, AND THE SHEET'S RULES ARE STRICTER —
     `request --effort` stages the rung; `apply` writes the HARNESS'S OWN LEVEL STRING (never the
     number) into the sheet; a rung outside the TARGET profile's ladder is refused at BOTH halves
     with the range named; a rung valid on one profile and invalid on another proves the range is
     the profile's, not a global ceiling. ⚠ AND THE TWO EFFORT RULES OF THE SHEET: a profile
     WITH a dial and NO rung is REFUSED (materialize refuses `effort-missing`) — that one reverses
     what the retired target did — while a rung on an INERT profile is ACCEPTED and stored as the
     word `inert`, which is owner ruling `d-effort-refuses-only-where-a-dial-exists` and the arm
     that reds if the 2026-08-12 refusal returns. That refusal ALSO popped the field, and
     `open_binding` then refused the half-declared triple on this very seat, so the master's live
     `claude-haiku` cast could not be made through this tool at all.
 11. A RELATIVE `--inbox` IS WORKSPACE-RELATIVE, NEVER CWD-RELATIVE — the half of the 2026-08-12
     misrooting this capability owns. Resolving a relative inbox at the caller's cwd `mkdir -p`'d a
     stray `.rbtv/goals` under the requesting seat's own folder, which `goal_cli`'s root walk-up
     then scaffolded a real goal into. Absolute paths pass through untouched. Proven at the
     FUNCTION and through `main` on the real argv, with the pre-fix `Path(raw)` as the red control.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tool" / "master_profile.py"
LIVE_PROFILES = Path(__file__).resolve().parents[3] / "config" / "spawn-profiles.yaml"
# The live sheet and seat are taken from the TOOL's own resolution (`mod.DEFAULT_BINDINGS` /
# `mod.DEFAULT_SEAT`), not recomputed here: two spellings of the same path is how a probe ends up
# proving a file the tool never reads. Bound at the top of main(), once the module is loaded.
LIVE_SHEET = None
LIVE_SEAT = None

failures: list[str] = []
inoperative: list[str] = []


def registered_argv(entry):
    """The argv the LIVE `config/spawn-profiles.yaml` declares for one `tools:` entry.

    Read from the config rather than retyped here: a retyped copy proves the probe author's memory
    of the entry, which is the very thing that was wrong."""
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


def load(path, name="mp"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stub_materialize(tmp, sheet, bus=None):
    """A stand-in for `materialize-seats.py` that records its argv and snapshots what the state
    looked like WHEN IT RAN. `bus` adds a second snapshot — the coordination log — which is how
    check 9 discriminates report-then-re-render from re-render-then-report. Guarded, because on
    every other check the bus file legitimately does not exist and a missing file is not a failure.

    A PYTHON script, because `_repass` composes `[sys.executable, MATERIALIZE, …]` — a bash stub
    would be handed to the interpreter and die, which is a crash wearing a green verdict."""
    rec, snap = tmp / "repass.argv", tmp / "repass.snapshot"
    bus_snap = tmp / "repass.bus-snapshot"
    s = tmp / "stub-materialize.py"
    s.write_text(
        "import json, shutil, sys, pathlib\n"
        f"pathlib.Path({str(rec)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n"
        f"shutil.copy2({str(sheet)!r}, {str(snap)!r})\n"
        + (f"try: shutil.copy2({str(bus)!r}, {str(bus_snap)!r})\n"
           "except Exception: pass\n" if bus else "")
        + "print(json.dumps({'ok': True, 'stub': True}))\n",
        encoding="utf-8")
    return s, rec, snap


# `## 4774 | from: master-profile | to: owner | type: note | exec: 2026-08-10a | 2026-08-10 14:23`
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


def stage(inbox, payload, name="a.json"):
    inbox.mkdir(parents=True, exist_ok=True)
    p = inbox / name
    p.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return p


def fixture(tmp, sheet_src):
    """The inbox SHAPE is part of the fixture, not a convenience. The tool DERIVES both the bus and
    the `--package` from the inbox (`<goal>/settings-requests/<capability>` → `<goal>`), so a flat
    temp inbox would prove a path the daemon never takes — and a probe that named the live goal
    would append to the owner's real bus and re-render his real seat."""
    goal = tmp / "goal"
    inbox = goal / "settings-requests" / "master-profile"
    bus = goal / "coordination" / "messages.md"
    sheet = tmp / "channel-master.json"
    shutil.copy2(sheet_src, sheet)
    return goal, inbox, bus, sheet


def seat_entry(sheet, seat):
    return json.loads(Path(sheet).read_text(encoding="utf-8"))["seats"][seat]


def check(cond, msg):
    if not cond:
        failures.append(msg)
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")


def main():
    global LIVE_SHEET, LIVE_SEAT
    mod = load(TOOL)
    LIVE_SHEET = Path(mod.DEFAULT_BINDINGS)
    LIVE_SEAT = mod.DEFAULT_SEAT

    if not LIVE_SHEET.is_file():
        inoperative.append(f"the live casting sheet {LIVE_SHEET} does not resolve — this probe "
                           f"copies it as its fixture, and a fabricated one would prove nothing "
                           f"about the shape actually shipped")
        print(f"probe-master-profile: INOPERATIVE — {inoperative}")
        return 2

    CLAUDE = mod.effort_ladder("claude", "claude-opus-5", LIVE_PROFILES)
    CODEX = mod.effort_ladder("codex", "gpt-5.5", LIVE_PROFILES)
    HAIKU = mod.effort_ladder("claude", "claude-haiku-4-5", LIVE_PROFILES)

    # ── 1, 2, 6 ─────────────────────────────────────────────────────────────────────────────
    print("check 1/2/6 — happy path lands, the RE-RENDER is last, every other line survives")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
        before_lines = sheet.read_text(encoding="utf-8").splitlines()
        stub, rec, snap = stub_materialize(tmp, sheet)
        mod.MATERIALIZE = stub

        stage(inbox, {"harness": "claude", "model": "claude-opus-5", "effort": len(CLAUDE)})
        out = mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)

        check(out["ok"] is True, "the fire reports ok")
        got = mod.read_value(sheet, LIVE_SEAT, LIVE_PROFILES)
        check(got["pair"] == "claude/claude-opus-5" and got["harness"] == "claude",
              f"re-reading the sheet FILE answers claude-opus (got {got['pair']}/{got['harness']})")
        check(got["effort"] == CLAUDE[-1] and got["rung"] == len(CLAUDE),
              f"the file carries the harness's own level string, and the rung reads back "
              f"(got {got['effort']!r} = rung {got['rung']})")

        # 2 — the re-render, its argv, and its ordering.
        argv = json.loads(rec.read_text(encoding="utf-8")) if rec.exists() else None
        # --refresh, not plain --repass (task 7.796, d-uniform-descriptor-carriage): the refresh
        # is what materializes the card's exposure loaders + guidance pair beside the descriptor.
        check(argv is not None and "--refresh" in argv and "--repass" not in argv,
              f"the re-render ran with --refresh ({'<never ran>' if argv is None else ' '.join(argv[:4])})")
        check(bool(argv) and argv[argv.index("--package") + 1] == str(goal),
              "and its --package is the inbox's own goal folder — DERIVED, never a named goal")
        check(bool(argv) and argv[argv.index("--seat") + 1] == LIVE_SEAT
              and argv[argv.index("--bindings") + 1] == str(sheet),
              "and it re-renders the SAME seat out of the SAME sheet the write just landed in")
        seen_by_render = json.loads(snap.read_text())["seats"][LIVE_SEAT] if snap.exists() else {}
        check(seen_by_render.get("harness") == "claude"
              and seen_by_render.get("model") == "claude-opus-5"
              and seen_by_render.get("effort") == CLAUDE[-1],
              f"the sheet AS THE RE-RENDER SAW IT already carried the new cast — write precedes "
              f"render (it saw {seen_by_render.get('model')!r}/{seen_by_render.get('effort')!r})")

        # 6 — the surgical control.
        after_lines = sheet.read_text(encoding="utf-8").splitlines()
        moved = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
        casting = {"harness", "model", "effort"}
        offenders = [after_lines[i] for i in moved
                     if not any(f'"{k}"' in after_lines[i] for k in casting)]
        check(len(before_lines) == len(after_lines) and not offenders,
              f"ONLY the seat's own casting lines moved — line count unchanged, "
              f"{len(moved)} changed, {len(offenders)} of them off-target {offenders[:2]}")
        check("\\u" not in sheet.read_text(encoding="utf-8"),
              "and no character was escaped into a `\\uXXXX` sequence — the hand-authored prose is "
              "still readable (the 2026-08-12 ensure_ascii regression)")

        settled = sorted((inbox / "done").glob("*.outcome.json"))
        check(len(settled) == 1 and json.loads(settled[0].read_text())["outcome"] == "ACCEPTED",
              "one ACCEPTED outcome record settled where the requester can read it")

    # ── 3 ───────────────────────────────────────────────────────────────────────────────────
    print("check 3 — an unknown or UNCASTABLE profile refuses, names the live set, writes nothing")
    for label, payload in (("unknown-name", {"harness": "gpt-cli", "model": "gpt-9-ultra"}),
                           ("declared-but-uncastable", {"harness": "sleep", "model": "test-sleep"}),
                           ("empty-name", {"harness": "", "model": ""}),
                           ("non-string", {"harness": 5, "model": 5}),
                           ("wrong-shape", {"master-profile": "claude-opus"})):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
            digest = sha(sheet)
            stub, rec, snap = stub_materialize(tmp, sheet)
            mod.MATERIALIZE = stub
            stage(inbox, payload)
            out = mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
            recs = sorted((inbox / "refused").glob("*.outcome.json"))
            stated = json.loads(recs[0].read_text())["stated-refusal"] if recs else None
            check(out["ok"] is False and sha(sheet) == digest and not rec.exists() and stated,
                  f"{label}: refused, sheet sha unchanged, no re-render, requester-readable — "
                  f"{(stated or '<no record>')[:80]}")
            if label == "unknown-name":
                check(stated is not None and "claude-fable" in stated,
                      "the unknown-name refusal names the live castable set back to the requester")
            if label == "declared-but-uncastable":
                # 7.787: `test-sleep` left `profiles:` for the `jobs:` block, so it is no longer a
                # DECLARED-but-uncastable row — it is not in the catalog at all. The refusal is the
                # unknown-pair one, which is the honest answer: a job's mechanics are unreachable
                # from a cast by construction now, not merely rejected by a predicate.
                check(stated is not None and "not a castable pair" in stated,
                      "and a JOB-block name is simply not a castable pair — a name that used to be a DECLARED "
                      "profile the old `profiles:`-key validator would have waved through")

    # ── 4 ───────────────────────────────────────────────────────────────────────────────────
    print("check 4 — the roster is read live, not frozen in the tool")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        text = LIVE_PROFILES.read_text(encoding="utf-8")
        removed = tmp / "without-sonnet.yaml"
        # 7.787: the roster is `launch-specs:`' KEYS, so renaming a spec means re-keying it — and
        # the argv must move with the key, or `profiles.js#validateSpecKey` refuses the document on
        # the daemon side (this reader would still see it, but the fixture would be one the daemon
        # could not boot, which is not the state under test).
        removed.write_text(text.replace("    claude-sonnet-5:\n", "    claude-sonnet-renamed:\n", 1)
                               .replace('"--model", "claude-sonnet-5"', '"--model", "claude-sonnet-renamed"'),
                           encoding="utf-8")
        accepted_live = False
        try:
            mod.validate("claude", "claude-sonnet-5", LIVE_PROFILES)
            accepted_live = True
        except mod.Refusal:
            pass
        refused_removed = False
        try:
            mod.validate("claude", "claude-sonnet-5", removed)
        except mod.Refusal:
            refused_removed = True
        check(accepted_live and refused_removed,
              "the SAME pair is accepted against the live document and refused against a copy it "
              "was re-keyed out of — the set is read, not hard-coded")

    # ── 5 ───────────────────────────────────────────────────────────────────────────────────
    print("check 5 — an unknown SEAT refuses rather than being created")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
        digest = sha(sheet)
        stub, rec, snap = stub_materialize(tmp, sheet)
        mod.MATERIALIZE = stub

        read_refused = ""
        try:
            mod.read_value(sheet, "no-such-seat", LIVE_PROFILES)
        except mod.Refusal as exc:
            read_refused = str(exc)
        check(LIVE_SEAT in read_refused,
              f"reading an absent seat refuses NAMING the seats the sheet does carry "
              f"({read_refused[:80] or '<no refusal>'})")

        # `apply` RAISES here rather than settling a per-request record, and that is the right
        # shape: the seat is read ONCE, before the drain, so an absent one is not a bad request —
        # it is a fire pointed at a sheet that cannot answer, and there is no request to blame it
        # on. `main` renders it as the `{"ok": false, "refusal": …}` envelope.
        stage(inbox, {"harness": "claude", "model": "claude-opus-5", "effort": len(CLAUDE)})
        apply_refused = ""
        try:
            mod.apply(inbox, sheet, "no-such-seat", profiles_path=LIVE_PROFILES)
        except mod.Refusal as exc:
            apply_refused = str(exc)
        check(bool(apply_refused) and sha(sheet) == digest and not rec.exists(),
              f"and apply refused, wrote nothing, and re-rendered nothing "
              f"({apply_refused[:60] or '<no refusal — it proceeded>'})")

    # ── 7 THE MUTANT ────────────────────────────────────────────────────────────────────────
    print("check 7 — the mutant: neuter the name lookup and the unknown name MUST be accepted")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src = TOOL.read_text(encoding="utf-8")
        target = "    row = spec_row(harness, model, profiles_path)\n"
        mutant_src = src.replace(
            target,
            "    row = spec_row(harness, model, profiles_path) or spec_row('claude', 'claude-haiku-4-5', profiles_path)\n",
            1)
        if mutant_src == src:
            inoperative.append("the mutation target `row = spec_row(harness, model, profiles_path)` was "
                               "not found in the tool source — the mutant proves nothing and "
                               "check 3 is unscored")
        else:
            # The mutant is nested deep enough that the module's own
            # `Path(__file__).resolve().parents[N]` derivations still resolve — a mutant that
            # cannot IMPORT is not evidence, it is a crash wearing a red verdict.
            mdir = tmp.joinpath(*[f"x{i}" for i in range(8)])
            mdir.mkdir(parents=True)
            mpath = mdir / "mutant.py"
            mpath.write_text(mutant_src, encoding="utf-8")
            mmod = load(mpath, "mp_mutant")
            goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
            stub, rec, snap = stub_materialize(tmp, sheet)
            mmod.MATERIALIZE = stub
            stage(inbox, {"harness": "gpt-cli", "model": "gpt-9-ultra"})
            out = mmod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
            landed = seat_entry(sheet, LIVE_SEAT).get("model")
            if not (out["ok"] and landed == "claude-haiku-4-5"):
                inoperative.append(f"the mutant did NOT go green (ok={out['ok']}, model={landed!r}) "
                                   f"— check 3's refusal is not being produced by the name lookup, "
                                   f"so check 3 scores nothing")
            else:
                print("  ok   the mutant accepted gpt-9-ultra — check 3 is discriminating")

    # ── 8 THE REGISTERED ARGV ITSELF ──────────────────────────────────────────────────────
    #
    # ⚠ THIS ARM EXISTS BECAUSE ITS ABSENCE COST A LIVE FIRE. Every check above calls `apply()` as a
    # PYTHON FUNCTION, which is exactly the surface the daemon never touches: the daemon execs the
    # wrapper with the argv `config/spawn-profiles.yaml` declares. `--config` was a ROOT option and
    # that argv puts it after the verb, so the first real fire died with
    # `error: unrecognized arguments: --config …`, drained nothing, and recorded `failed` — while
    # every function-level check stayed green. A check that cannot see the caller's shape is not
    # checking the caller.
    #
    # ⚠ AND IT ASSERTS SUCCESS AGAIN. It was inverted to assert a REFUSAL for one day (2026-08-11,
    # while the tool was parked out of service by D2). An arm asserting that the one surface the
    # daemon fires refuses is an arm that goes green on a broken capability.
    #
    # ⚠ DISCLOSED BOUND: `--no-repass` is APPENDED. The real renderer needs a real goal package
    # (conduct, taskforce, catalogue) and this fixture is a bare inbox, so the subprocess covers
    # every declared token and the drain-and-write, NOT the render. The render's own argv is
    # covered at function level by check 2, against the stub.
    print("check 8 — the argv the `tools: master-profile` entry actually declares, run as a subprocess")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        argv = registered_argv("master-profile")
        if argv is None:
            inoperative.append("the live spawn-profiles.yaml carries no `tools: master-profile` entry — "
                               "the one surface the daemon uses is unchecked")
        else:
            goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
            inbox.mkdir(parents=True, exist_ok=True)
            stage(inbox, {"harness": "claude", "model": "claude-haiku-4-5"})
            # Substitute ONLY the operands that would point at live state. Every other token —
            # including the interpreter, the script path, the verb, and the flag SPELLINGS and
            # ORDER — is the config's own, byte for byte.
            run_argv = list(argv)
            for i, tok in enumerate(run_argv):
                if i and run_argv[i - 1] == "--inbox":
                    run_argv[i] = str(inbox)
                elif i and run_argv[i - 1] == "--bindings":
                    run_argv[i] = str(sheet)
            check(all(f in argv for f in ("--inbox", "--bindings", "--seat", "--catalog-root")),
                  f"the entry declares every operand the fire needs (got "
                  f"{[t for t in argv if t.startswith('--')]})")
            r = subprocess.run(run_argv + ["--no-repass"], capture_output=True, text=True,
                               env=dict(os.environ))
            check(r.returncode == 0,
                  f"the registered argv RUNS CLEAN (exit {r.returncode}) — "
                  f"{(r.stderr.strip().splitlines() or [''])[-1][:120]}")
            check(seat_entry(sheet, LIVE_SEAT)["model"] == "claude-haiku-4-5",
                  f"and its edit LANDED in the sheet it was fired at "
                  f"(model={seat_entry(sheet, LIVE_SEAT)['model']!r})")

    # ── 9 THE SELF-REPORT INTO THE OWNER'S OWN CHAT THREAD ────────────────────────────────
    print("check 9 — the outcome reports itself into the owner's thread, BEFORE the re-render")
    THREAD = "C0PROBEMP:1754812345.123456"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
        stub, rec, snap = stub_materialize(tmp, sheet, bus=bus)
        mod.MATERIALIZE = stub

        # `/bin/true` stands in for the `ignite` client: `request` stages BEFORE it enqueues, and
        # what is under test here is the payload, not the queue.
        out = mod.request(inbox, "claude", "claude-opus-5", "/bin/true", profiles_path=LIVE_PROFILES,
                          chat_thread=THREAD, effort=len(CLAUDE), bindings=sheet, seat=LIVE_SEAT)
        staged = json.loads(Path(out["staged"]).read_text())
        check(staged.get("chat-thread") == THREAD,
              f"request --chat-thread stages the id in the payload (got {staged.get('chat-thread')!r})")
        bad_refused = False
        try:
            mod.request(inbox, "claude", "claude-opus-5", "/bin/true", profiles_path=LIVE_PROFILES,
                        chat_thread="C0PROBEMP-1754812345", effort=len(CLAUDE),
                        bindings=sheet, seat=LIVE_SEAT)
        except mod.Refusal:
            bad_refused = True
        check(bad_refused, "a token bus-ferry.js could not route refuses in the sitting that typed it")

        prev = mod.read_value(sheet, LIVE_SEAT, LIVE_PROFILES)["pair"]
        mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
        rows = bus_rows(bus)
        check(len(rows) == 1, f"exactly ONE bus row was appended (got {len(rows)})")
        if rows:
            f, body = rows[0]["fields"], rows[0]["body"]
            check(f.get("from") == "master-profile" and f.get("to") == "owner"
                  and f.get("type") == "note",
                  f"and its header carries from/to/type the ferry requires ({f})")
            check(f"[chat-thread: {THREAD}]" in body,
                  "the BRACKETED token is in the body — the plain form does not route")
            check("[deliver: post]" in body,
                  "an ACCEPTED outcome asks to be POSTED verbatim — nothing to act on")
            check(f"`{prev}` → `claude/claude-opus-5`" in body,
                  f"the body states the change as old → new (`{prev}` → `claude/claude-opus-5`)")
            check("NEXT message" in body and "restarted" in body,
                  "and tells the owner the switch lands on his next message with nothing restarted "
                  "— the retired body promised a bridge restart that no longer happens")
            check(not any(l.startswith("|") or l.startswith("#") for l in body.split("\n")),
                  "the body is mrkdwn — no pipe tables, no markdown headings")
        check(bus.read_text(encoding="utf-8").endswith("\n"),
              "the log ends with a newline — the ferry's torn-write rule only counts a row that does")
        check((tmp / "repass.bus-snapshot").is_file()
              and THREAD in (tmp / "repass.bus-snapshot").read_text(),
              "the bus AS THE RE-RENDER SAW IT already carried the report — report precedes render")

    print("check 9b — a request with NO chat thread reports nothing at all")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
        stub, rec, snap = stub_materialize(tmp, sheet, bus=bus)
        mod.MATERIALIZE = stub
        stage(inbox, {"harness": "claude", "model": "claude-opus-5", "effort": len(CLAUDE)})
        out = mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
        check(out["ok"] and not bus.exists(),
              "the switch landed and no bus row exists — an untokened request is silent, as before")

    print("check 9c — a REFUSED outcome carrying a thread reports its refusal too")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
        digest = sha(sheet)
        stub, rec, snap = stub_materialize(tmp, sheet, bus=bus)
        mod.MATERIALIZE = stub
        stage(inbox, {"harness": "gpt-cli", "model": "gpt-9-ultra", "chat-thread": THREAD})
        out = mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
        rows = bus_rows(bus)
        check(out["ok"] is False and sha(sheet) == digest and not rec.exists(),
              "the refusal still refuses — sheet untouched, no re-render")
        check(len(rows) == 1 and "REFUSED" in rows[0]["body"]
              and f"[chat-thread: {THREAD}]" in rows[0]["body"],
              f"and exactly one row reports the refusal into the thread (got {len(rows)} row(s))")
        check(bool(rows) and "[deliver: wake]" in rows[0]["body"],
              "and a REFUSED outcome asks to WAKE an agent — the refusal needs follow-up "
              "(owner ruling 2026-08-10: post always, wake when agent action is needed)")

    # ── 10 THE EFFORT RUNG ────────────────────────────────────────────────────────────────
    #
    # ⚠ EVERY ASSERTION READS THE FILE, NEVER THE RECORD. `apply`'s return value is the tool's own
    # account of what it did; `materialize-seats.py` reads the FILE. Check 1 draws that line for
    # the cast and this leg holds it for the rung.
    print("check 10 — the effort RUNG: staged, stored as the harness's own string, range-checked "
          "against the profile it is FOR")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
        stub, rec, snap = stub_materialize(tmp, sheet, bus=bus)
        mod.MATERIALIZE = stub

        # (a) the ladders come off the LIVE spawn-profiles document, not a list retyped here — the
        #     same discipline check 4 applies to the profile roster, and for the same reason.
        check(isinstance(CLAUDE, list) and len(CLAUDE) >= 4 and HAIKU == [],
              f"the live ladders are read per profile (claude={CLAUDE}, haiku inert={HAIKU == []})")

        # (b) staged, then applied — and read back OFF THE FILE, as a STRING not a number.
        out = mod.request(inbox, "claude", "claude-opus-5", "/bin/true", profiles_path=LIVE_PROFILES,
                          effort=len(CLAUDE), bindings=sheet, seat=LIVE_SEAT)
        staged = json.loads(Path(out["staged"]).read_text())
        check(staged.get("effort") == len(CLAUDE),
              f"request --effort stages the RUNG NUMBER in the payload (got {staged.get('effort')!r})")
        mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
        entry = seat_entry(sheet, LIVE_SEAT)
        check(entry.get("effort") == CLAUDE[-1] and entry.get("model") == "claude-opus-5",
              f"the SHEET carries the harness's own LEVEL STRING beside the model, never the number "
              f"({entry.get('model')!r}, {entry.get('effort')!r})")

        # (c) THE RANGE IS THE PROFILE'S, NOT A CEILING. The SAME rung that just succeeded on
        #     claude is refused on codex — which is the whole content of the numeric-rung ruling.
        #     A global ceiling passes (b) and fails here.
        over = len(CODEX) + 1
        codex_refused = claude_ok = False
        try:
            mod.request(inbox, "codex", "gpt-5.5", "/bin/true", profiles_path=LIVE_PROFILES,
                        effort=over, bindings=sheet, seat=LIVE_SEAT)
        except mod.Refusal as exc:
            codex_refused = f"1..{len(CODEX)}" in str(exc)
        try:
            mod.request(inbox, "claude", "claude-opus-5", "/bin/true", profiles_path=LIVE_PROFILES,
                        effort=over, bindings=sheet, seat=LIVE_SEAT, dry_run=True)
            claude_ok = True
        except mod.Refusal:
            pass
        check(codex_refused and claude_ok,
              f"rung {over} is refused on codex NAMING 1..{len(CODEX)} and accepted on claude — "
              f"the range belongs to the profile")

        # (d) THE SHEET'S TWO EFFORT RULES. The first is the LIVE MASTER'S OWN CAST: this seat runs
        #     on `claude-haiku` for the warm-session path, and until 2026-08-12 this tool REFUSED
        #     that rung and POPPED the field, after which `open_binding` refused the half-declared
        #     triple — so the cast in force could not be made by the CLI that owns it and the sheet
        #     was hand-written. Owner ruling `d-effort-refuses-only-where-a-dial-exists`: accept,
        #     and record `inert`. The whole triple must land, which is what the last clause checks.
        stage(inbox, {"harness": "claude", "model": "claude-haiku-4-5", "effort": 3})
        out = mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
        entry = seat_entry(sheet, LIVE_SEAT)
        check(out["ok"] is True and entry.get("effort") == "inert"
              and entry.get("model") == "claude-haiku-4-5" and entry.get("harness") == "claude",
              f"a rung on an INERT profile is ACCEPTED and stored as `inert`, with the whole "
              f"harness·model·effort triple present so a STANDING seat materializes "
              f"({entry.get('harness')!r}, {entry.get('model')!r}, {entry.get('effort')!r})")

        stage(inbox, {"harness": "claude", "model": "claude-opus-5"})
        out = mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
        stated = (out["results"][-1] or {}).get("stated-refusal", "")
        check(out["ok"] is False and "effort-missing" in stated,
              f"and a DIALLED profile with NO rung is REFUSED naming what materialize would say "
              f"({stated[:70]})")

    print("check 10b — a REFUSED EFFORT rides the same [deliver: wake] outcome path as a refused name")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
        digest = sha(sheet)
        stub, rec, snap = stub_materialize(tmp, sheet, bus=bus)
        mod.MATERIALIZE = stub
        stage(inbox, {"harness": "codex", "model": "gpt-5.5", "effort": len(CODEX) + 1,
                      "chat-thread": THREAD})
        out = mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
        rows = bus_rows(bus)
        check(out["ok"] is False and sha(sheet) == digest and not rec.exists(),
              "an out-of-range rung refuses the WHOLE request — sheet byte-identical, no re-render")
        check(len(rows) == 1 and "[deliver: wake]" in rows[0]["body"]
              and "REFUSED" in rows[0]["body"],
              f"and it wakes an agent on the thread through the ONE outcome mapping (got {len(rows)} row(s))")

    # ── 10d ONE VALIDATOR AND ONE LADDER READER, PINNED BY OBJECT IDENTITY ────────────────
    #
    # ⚠ VALUE EQUALITY IS THE VACUOUS VERSION OF THIS CHECK. Two copies of the ladder reader agree
    # on the day they are written and drift silently after — and these two DID: until 2026-08-11
    # this tool line-scanned a profile block returning on whichever of `inert` / `rungs:` came
    # first, while the bindings capability searched the whole block for `inert` before looking at
    # rungs. A `rungs:` line above an `effort: { inert: true }` line read as a five-rung ladder here
    # and as INERT there, on the same bytes in the same second. A check comparing their OUTPUTS
    # would have been green for weeks. So: same object, or nothing.
    #
    # ⚠ THE SET GREW ON 2026-08-12. `cast_seat` (the write AND the effort validator), `catalog` and
    # `profile_row` are imported for the same reason the ladder reader was — the sheet is a file the
    # BINDINGS capability owns, and a second opinion about what may go in it is drift with a
    # deadline. `Refusal` is on the list because the two classes being distinct made every refusal
    # `cast_seat` raised escape `main`'s handler as a traceback.
    print("check 10d — the catalog, the write, the ladder reader and the refusal type ARE the "
          "bindings capability's own objects")
    bindings_mod = sys.modules.get("bindings")
    # The path is spelled independently ON PURPOSE here, unlike LIVE_SHEET above: the question is
    # whether the module the tool imported is the bindings TOOL, and a path taken from the tool's
    # own resolution could not tell. A `bindings` shadowed from anywhere else on sys.path would
    # satisfy the identity assertions below while pointing at the wrong file.
    want = Path(__file__).resolve().parents[3] / "capabilities" / "bindings" / "tool" / "bindings.py"
    check(bindings_mod is not None
          and Path(bindings_mod.__file__).resolve() == want,
          f"the tool imported the bindings TOOL itself "
          f"({getattr(bindings_mod, '__file__', None)})")
    for name, theirs in (("effort_ladder", "spec_effort"), ("cast_seat", "cast_seat"),
                         ("bindings_catalog", "catalog"), ("spec_row", "spec_row"),
                         ("Refusal", "Refusal")):
        check(bindings_mod is not None
              and getattr(mod, name, None) is getattr(bindings_mod, theirs, object()),
              f"master_profile.{name} IS bindings.{theirs} — one object, not two that agree")

    # THE MUTATION CONTROL. Without it the identity assertions could be matching names nothing
    # calls: `apply` might hold a private writer and the aliases be decoration.
    # ⚠ THE PATCH GOES ON `mod.cast_seat`, NOT ON `bindings_mod.cast_seat`, and that is not a
    # weakening. `from bindings import cast_seat` binds the OBJECT, so rebinding the source module's
    # attribute cannot reach a consumer that already imported it — the mutation would fail to
    # propagate and report RED for the binding style rather than for any defect. Patching the global
    # the consumer actually resolves asks the real question: does `apply` route through the imported
    # writer, or around it?
    real = mod.cast_seat
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        goal, inbox, bus, sheet = fixture(tmp, LIVE_SHEET)
        stub, rec, snap = stub_materialize(tmp, sheet)
        mod.MATERIALIZE = stub
        seen = {}
        try:
            def spy(*a, **k):
                seen["called"] = True
                return real(*a, **k)
            mod.cast_seat = spy
            stage(inbox, {"harness": "claude", "model": "claude-opus-5", "effort": len(CLAUDE)})
            mod.apply(inbox, sheet, LIVE_SEAT, profiles_path=LIVE_PROFILES)
        finally:
            mod.cast_seat = real
        check(seen.get("called") is True and seat_entry(sheet, LIVE_SEAT)["model"] == "claude-opus-5",
              "apply's write goes THROUGH that object — replacing it is observed on a real fire, "
              "so the alias is the writer and not decoration")
    check(mod.cast_seat is bindings_mod.cast_seat,
          "...and the writer is restored, so nothing below runs on a patched module")

    # ── 10c THE PROSE→RUNG GUIDANCE ───────────────────────────────────────────────────────
    #
    # The requester is an LLM handed effort in prose. The scheme is only usable if the explanation
    # of it is on the surfaces that requester actually reads — `show` and `request --help` — so
    # this asserts the text is on BOTH, not merely defined in the module.
    print("check 10c — the prose→rung guidance reaches both surfaces the requester reads")
    # ⚠ WHITESPACE IS NORMALISED ON BOTH SIDES, and that is not a loosened assertion. Both surfaces
    # re-wrap the text — `show` through `textwrap.fill`, `request --help` through argparse's own
    # formatter — so the marker is routinely split across a line break. Matching the raw bytes was
    # asserting a WRAP POINT: it went red on 2026-08-12 for no reason but a longer `--effort` help
    # string above it shifting the column the phrase happened to land on. The question this arm asks
    # is whether the guidance REACHES the surface, and a line break is not an answer to it.
    flat = lambda s: " ".join(s.split())
    marker = flat("converting a prose effort request into a rung")
    seen = {}
    for name, argv in (("show", ["show", "--bindings", str(LIVE_SHEET),
                                 "--profiles", str(LIVE_PROFILES)]),
                       ("request --help", ["request", "--help"])):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.suppress(SystemExit):
            mod.main(argv)
        seen[name] = marker in flat(buf.getvalue())
    check(all(seen.values()) and marker in flat(mod.EFFORT_GUIDANCE),
          f"the guidance prints on show and on request --help (got {seen}) — stated once in "
          f"EFFORT_GUIDANCE, never retyped per surface")

    # ── 11 A RELATIVE `--inbox` IS WORKSPACE-RELATIVE, NEVER CWD-RELATIVE ─────────────────
    #
    # ⚠ THIS ARM IS THE HALF OF A LIVE INCIDENT, AND ITS TWIN LIVES IN goals-tree. On 2026-08-12
    # the channel master staged a request with a RELATIVE `--inbox` from a sitting whose cwd was
    # its own seat folder. `request` resolved it there and `mkdir -p`'d `.rbtv/goals/…` UNDER THE
    # SEAT; `goal_cli.resolve_goals_root`'s child scan then matched that stray tree from every seat
    # cwd beneath it, and the seat's next `scaffold` created a real goal inside it, where nothing
    # enumerates it. `_anchor_inbox` closes this half: relative → `_WORKSPACE`, absolute → through.
    # (The other half — the walk-up ORDER — is scored by
    # `capabilities/goals-tree/probes/probe-goals-root-walkup.py`.)
    #
    # ⚠ THE FUNCTION ARMS ALONE WOULD BE VACUOUS, AND THAT IS WHY (b) AND ITS MUTANT EXIST. Every
    # other check in this file calls `apply`/`request` as PYTHON FUNCTIONS with ABSOLUTE fixture
    # paths — the anchoring happens in `main`, on `args.inbox`, which none of them reach. A pure
    # `_anchor_inbox("x") == _WORKSPACE / "x"` assertion would stay green if `main` stopped calling
    # it. So (b) drives the REAL argv through `main` and reads what the callee was handed, and its
    # mutant neuters `_anchor_inbox` to the pre-fix `Path` and requires the SAME argv to hand over
    # a cwd-relative path.
    #
    # Nothing is created anywhere: `main`'s callees are spied and refuse before any write, and the
    # anchored path is only ever COMPARED — never opened.
    print("check 11 — a relative --inbox anchors on the WORKSPACE, an absolute one passes through")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td).resolve()
        ws = Path(mod._WORKSPACE).resolve()

        # (a) the function itself, evaluated from a cwd that is NOT the workspace.
        prior = Path.cwd()
        try:
            os.chdir(tmp)
            rel = Path(mod._anchor_inbox("settings-requests/master-profile")).resolve()
            absolute = tmp / "somewhere" / "inbox"
            through = Path(mod._anchor_inbox(str(absolute)))
        finally:
            os.chdir(prior)
        check(rel == (ws / "settings-requests" / "master-profile").resolve(),
              f"a relative --inbox resolves under the WORKSPACE root, not the cwd (got {rel})")
        check(tmp not in rel.parents and rel != tmp,
              f"and NOTHING about it is cwd-derived — {tmp} is not on the resolved path")
        check(through == absolute,
              f"an ABSOLUTE --inbox is handed through byte for byte (got {through}) — the daemon's "
              f"fired argv and this file's own tmp fixtures must not be rewritten")

        # (b) THE WIRING, through `main`, on the argv shape the caller actually types. Both verbs,
        #     because the fix touched two call sites and one of them is easy to miss.
        real_apply, real_request = mod.apply, mod.request
        seen = {}

        def spy(key):
            def f(inbox, *a, **k):
                seen[key] = Path(inbox)
                raise mod.Refusal("probe spy — nothing was done")
            return f

        for verb, argv in (("apply", ["apply", "--inbox", "rel/inbox", "--no-repass"]),
                           # 7.787: `request` takes TWO positionals now — harness and model.
                           # The retired single-name form made argparse SystemExit(2) inside the
                           # redirect, which surfaced as a silent INOPERATIVE with no line saying so.
                           ("request", ["request", "claude", "claude-opus-5", "--inbox", "rel/inbox",
                                        "--effort", str(len(CLAUDE)), "--dry-run"])):
            try:
                mod.apply, mod.request = spy("apply"), spy("request")
                os.chdir(tmp)
                with contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    mod.main(argv)
            finally:
                os.chdir(prior)
                mod.apply, mod.request = real_apply, real_request
            check(seen.get(verb) == ws / "rel" / "inbox",
                  f"main's `{verb}` verb hands its callee the WORKSPACE-anchored inbox "
                  f"(got {seen.get(verb)})")

        # (c) THE MUTANT — the pre-fix behaviour is `Path(raw)`, and it MUST re-produce the
        #     cwd-relative path row (b) just refused. Patched on `mod._anchor_inbox` because that
        #     is the global `main` resolves; if this does not go through, row (b) is scoring
        #     nothing and the whole leg is unproven rather than green.
        real_anchor = mod._anchor_inbox
        seen.clear()
        try:
            mod._anchor_inbox = lambda raw: Path(raw)
            mod.apply = spy("apply")
            os.chdir(tmp)
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                mod.main(["apply", "--inbox", "rel/inbox", "--no-repass"])
        finally:
            os.chdir(prior)
            mod._anchor_inbox, mod.apply, mod.request = real_anchor, real_apply, real_request
        if (tmp / seen.get("apply", Path("."))).resolve() != (tmp / "rel" / "inbox") \
                or seen.get("apply") == ws / "rel" / "inbox":
            inoperative.append(f"the pre-fix `Path(raw)` did NOT produce a cwd-relative inbox "
                               f"(got {seen.get('apply')!r}) — check 11(b) is not being produced "
                               f"by `_anchor_inbox`, so it scores nothing")
        else:
            print("  ok   the mutant handed over a cwd-relative inbox — check 11(b) discriminates")
        check(mod._anchor_inbox is real_anchor and mod.apply is real_apply,
              "...and the anchor and both callees are restored, so nothing below runs patched")

    if inoperative:
        print(f"probe-master-profile: INOPERATIVE — {inoperative}")
        return 2
    if failures:
        print(f"probe-master-profile: FAIL — {len(failures)} failure(s): {failures}")
        return 1
    print("probe-master-profile: PASS — the cast lands in the sheet, the seat's RE-RENDER is the "
          "last act with its package derived from the inbox, unknown AND uncastable names refuse "
          "against the LIVE catalog leaving the sheet byte-identical, an unknown seat refuses "
          "rather than being created, every non-casting line of the hand-authored sheet survives "
          "unescaped, and the name lookup is proven discriminating by mutation — the argv the "
          "daemon actually fires runs clean as a subprocess AND lands its edit, and a request "
          "naming its chat thread reports its outcome (accepted OR refused) as exactly one "
          "ferry-parseable bus row written BEFORE the re-render, and a relative --inbox anchors "
          "on the WORKSPACE rather than the caller's cwd while an absolute one passes through")
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
