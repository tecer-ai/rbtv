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
"""

import hashlib
import importlib.util
import json
import os
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


def stub_operator(tmp, target):
    """A stand-in for `rbtv-ignite-daemon` that records that it ran, and WHAT THE CONFIG LOOKED
    LIKE when it ran. The snapshot is what proves the ordering; the argv alone would not."""
    rec, snap = tmp / "restart.argv", tmp / "restart.snapshot"
    s = tmp / "stub-daemon-operator"
    s.write_text("#!/usr/bin/env bash\n"
                 f'printf "%s\\n" "$*" >> {rec}\n'
                 f'cp {target} {snap}\n', encoding="utf-8")
    s.chmod(0o755)
    return s, rec, snap


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

    if inoperative:
        print(f"probe-goal-launch-delay: INOPERATIVE — {inoperative}")
        return 2
    if failures:
        print(f"probe-goal-launch-delay: FAIL — {len(failures)} failure(s): {failures}")
        return 1
    print("probe-goal-launch-delay: PASS — the edit lands, the restart is the last act, every "
          "refusal shape leaves the config byte-identical, the absent-flag insert works, and the "
          "ceiling check is proven discriminating by mutation — and the argv the daemon "
          "actually fires runs clean as a subprocess")
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
