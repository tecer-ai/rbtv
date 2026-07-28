#!/usr/bin/env python3
"""Refuse a RAM-floor literal anywhere but the run's budget.json.

    floor-lint.py [--repo DIR] [--json]
    floor-lint.py --control          # prove this lint can go RED, in the same run

WHY THIS EXISTS. Owner ruling `r-floor-single-source` (2026-07-28), defect G-42:

    A POLICY NUMBER MUST NEVER BE TRANSPORTED BY ARGV. argv is a COPY; a file is a REFERENCE.

The floor lived in 7 places across 5 files and they disagreed. Task 7.82 makes the consumers READ
`budget.json`. This lint is what stops the copies coming back -- without it the fix decays the
first time someone adds a launch path and hand-carries a number, exactly as the last seven did.

WHAT IT REFUSES. A line that names a floor KNOB and also carries a plausible floor VALUE, anywhere
in the scanned tree. Plus the two-line YAML shape, because that one hides from every single-line
grep:

    - --watch-arg=--mem-floor-mb        <- knob here
    - --watch-arg=2000                  <- value on the NEXT line

The row's own `_Context:_` measured this: a CONCEPT arm finds 20 sites, a VALUE arm finds 10, and
NEITHER CONTAINS THE OTHER -- concept misses all three spawn-profiles lines precisely because flag
and value sit on separate lines. This lint runs both shapes.

WHAT IT PERMITS, and it says so out loud rather than silently passing. Three classes, each carrying
its reason (criterion 11's discipline, applied to this tool too -- SCOPE-EXCLUDED must never render
as NOT-FOUND):

    HOME      budget.json itself. The one normative home. `r-bar-home-is-the-run-budget-json`.
    EXCLUDED  a line a RULING put out of scope. Named, with the ruling.
    FIXTURE   a literal inside a _selftest() -- determines no live behaviour.
    PROSE     a number in a comment or docstring. Task 7.82's row rules these NOT sites (same class
              as recover-room.py:120's docstring), so this lint does not fail on them -- but it
              PRINTS them, because a number in prose is a HOME IN WAITING: nothing consumes it, so
              it drifts in silence. spawn-profiles.yaml's own comment block deliberately names no
              floor value for exactly that reason.

⚠ THIS LINT IS NOT A COMPLETENESS INSTRUMENT AND MUST NEVER BE READ AS ONE. It proves that no
literal it can see survives; it does not prove the set of homes is closed. Every growth in that set
(2 -> 3 -> 4 -> 7) came from someone looking again, never from a tool reporting completeness. The
enumerator is `floor-homes.py`; a green here is a FLOOR on the claim, never proof of it.

⚠ AND IT CANNOT SEE A LIVE INVOCATION. A running process's argv is a home no tree scan reaches
(`bars.md` 10: verify at the artifact the CONSUMER reads, in the ENVIRONMENT it runs in). A green
here says LANDED, never LIVE. Ask /proc for that -- `floor-homes.py` has the arm.
"""

import argparse
import json
import os
import re
import sys
import tempfile

# ---------------------------------------------------------------- what counts

# A knob NAMES the floor. Anything that can carry the number.
KNOB = re.compile(
    r"--mem-floor-mb|\bmem_floor_mb\b|\bMEM_FLOOR\w*|\bLAUNCH_MEM_FLOOR\w*"
    r"|\bram_available_mb\b|\blaunch_refuse_mb\b|\bpressure_warn_mb\b"
    r"|\bram_floor_mb\b"
)

# A plausible floor VALUE. Deliberately a RANGE, not a value list: keying on the literal 2000 would
# go quiet the moment a change half-lands and one site still says 2800 -- which is the exact
# condition this lint exists to catch. Bounded below so `default=0`, indexes and `-1` are not noise.
VALUE = re.compile(r"(?<![\w.])([1-9]\d{2,5})(?![\w.])")
VALUE_MIN, VALUE_MAX = 100, 99999

# The bare-number continuation of the two-line YAML shape.
YAML_BARE_VALUE = re.compile(r'^\s*-\s*(?:--watch-arg=)?"?([1-9]\d{2,5})"?\s*$')

SCAN_EXT = {".py", ".yaml", ".yml", ".json", ".js", ".sh"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build"}

# ---------------------------------------------------------------- what is allowed, and WHY

# The ONE normative home. Matched on basename: every run package carries its own.
HOME_BASENAMES = {"budget.json"}

# ⚠ EVERY ENTRY NEEDS A RULING. An allowlist without reasons is how a defect becomes permanent
# furniture -- the next reader cannot tell an exclusion from an oversight, and re-litigates it.
# (path_suffix, line_or_None, reason)
EXCLUDED = [
    # Populated by ruling only. `watch.py:2092`'s 500 default belongs here IF the leader rules it
    # stays with G-29 -- see task 7.82 open question D. Left EMPTY rather than pre-decided: an
    # entry here is a ruling's record, never a builder's convenience.
]

# ⚠ MATCHED ON THE DEF NAME, CASE-INSENSITIVELY, NOT ON AN EXACT SPELLING. The three selftests in
# this kit are `_selftest`, `_selftest_checks` and `cmd_selftest` -- an exact `_selftest` marker
# classified the third only because "_selftest" happens to be a substring of "cmd_selftest", and
# would have MISSED a plain `def selftest()`. A classifier that is right by luck reports the same
# thing as one that is right (`bars.md` 11, the misgrading shape).
FIXTURE_DEF = re.compile(r"^\s*def\s+\w*selftest\w*\s*\(", re.I)


def _prose_lines(lines, ext):
    """Indexes of lines that are comment or docstring prose. Tracks triple quotes for .py so a
    module docstring is seen for what it is -- watch.py:28 lives in one, and calling it a live home
    would make this lint fire on the row's own excluded class."""
    out, in_doc, delim = set(), False, None
    for i, raw in enumerate(lines):
        s = raw.strip()
        if ext == ".py":
            if in_doc:
                out.add(i)
                if delim in s:
                    in_doc = False
                continue
            for d in ('"""', "'''"):
                if s.startswith(d) and not (len(s) > 5 and s.count(d) >= 2):
                    in_doc, delim = True, d
                    out.add(i)
                    break
            if in_doc:
                continue
        if s.startswith("#"):
            out.add(i)
    return out


def _is_fixture(lines, idx):
    """Is this line inside a _selftest()? Walk back to the nearest top-level def."""
    for j in range(idx, -1, -1):
        s = lines[j]
        if s.startswith("def ") or s.startswith("class "):
            return bool(FIXTURE_DEF.match(s))
    return False


def _excluded_for(rel, lineno):
    for suffix, line, reason in EXCLUDED:
        if rel.endswith(suffix) and (line is None or line == lineno):
            return reason
    return None


def scan(repo):
    """Returns (violations, permitted). Each is a list of dicts. Raises nothing."""
    violations, permitted = [], []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in sorted(files):
            if os.path.splitext(fn)[1] not in SCAN_EXT:
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, repo)
            try:
                lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue

            ext = os.path.splitext(fn)[1]
            is_home = fn in HOME_BASENAMES
            prose = _prose_lines(lines, ext)
            for i, line in enumerate(lines):
                lineno = i + 1
                hit = None

                # shape 1 -- knob and value on ONE line
                if KNOB.search(line):
                    for m in VALUE.finditer(line):
                        v = int(m.group(1))
                        if VALUE_MIN <= v <= VALUE_MAX:
                            hit = v
                            break
                    # shape 2 -- knob here, bare value on the NEXT line (the YAML argv pair)
                    if hit is None and i + 1 < len(lines):
                        m = YAML_BARE_VALUE.match(lines[i + 1])
                        if m and VALUE_MIN <= int(m.group(1)) <= VALUE_MAX:
                            hit = int(m.group(1))

                if hit is None:
                    continue

                row = {"file": rel, "line": lineno, "value": hit, "text": line.strip()[:110]}
                if is_home:
                    row["permitted"] = "HOME — the one normative home (r-bar-home-is-the-run-budget-json)"
                    permitted.append(row)
                    continue
                reason = _excluded_for(rel, lineno)
                if reason:
                    row["permitted"] = "EXCLUDED BY RULING (not by this tool) — %s" % reason
                    permitted.append(row)
                    continue
                if rel.endswith(".py") and _is_fixture(lines, i):
                    row["permitted"] = "FIXTURE — inside _selftest(), determines no live behaviour"
                    permitted.append(row)
                    continue
                if i in prose:
                    row["permitted"] = ("PROSE — a comment or docstring; ruled NOT a site by 7.82. "
                                        "Reported because a number in prose is a home in waiting")
                    permitted.append(row)
                    continue
                violations.append(row)
    return violations, permitted


# ---------------------------------------------------------------- the positive control

CONTROL_FILE = "planted_floor_literal.py"
# ⚠ ASSEMBLED, NEVER WRITTEN WHOLE. A literal source line reading `LAUNCH_MEM_FLOOR_MB = 2000` here
# would make this lint fire on ITSELF -- measured, it did -- and the only ways out are to allowlist
# this file (which then blinds the lint to a real literal added here later) or to stop the payload
# being a match in THIS file's source while still being one in the file it plants. This is the
# second. The planted file carries a full knob-and-value line; this source carries neither together.
CONTROL_VALUE = 2000
CONTROL_KNOB = "LAUNCH_MEM_FLOOR_MB"
CONTROL_BODY = "%s = %d   # planted by --control\n" % (CONTROL_KNOB, CONTROL_VALUE)


def control():
    """Prove this lint CAN go RED, in the same run as any green it reports.

    `bars.md` 11, second half: a negative needs a positive control in the same run, and the control
    needs its own proof that it fires. "It passed everywhere" and "it cannot fail anywhere" print
    the same thing. So: plant a literal, require RED; remove it, require GREEN. Either half failing
    means this lint's greens are worthless and it says so instead of exiting 0.
    """
    ok = True
    with tempfile.TemporaryDirectory() as d:
        clean, _ = scan(d)
        if clean:
            print("CONTROL FAIL: an empty tree reported %d violation(s)" % len(clean))
            ok = False
        else:
            print("control 1/6 — empty tree is GREEN: ok")

        with open(os.path.join(d, CONTROL_FILE), "w") as fh:
            fh.write(CONTROL_BODY)
        red, _ = scan(d)
        if len(red) != 1 or red[0]["value"] != CONTROL_VALUE:
            print("CONTROL FAIL: a planted floor literal did NOT turn this lint RED — "
                  "every green it has ever printed is uninformative. got: %r" % (red,))
            ok = False
        else:
            print("control 2/6 — planted literal turns it RED: ok (%s:%d value=%d)"
                  % (red[0]["file"], red[0]["line"], red[0]["value"]))

        os.remove(os.path.join(d, CONTROL_FILE))
        back, _ = scan(d)
        if back:
            print("CONTROL FAIL: removing the literal did not restore GREEN: %r" % (back,))
            ok = False
        else:
            print("control 3/6 — removing it restores GREEN: ok")

        # ⚠ control 4 exists because the HOME branch IS UNREACHABLE ON THE REAL SCAN: budget.json
        # lives in the run package under the VAULT, not in the rbtv repo this lint scans by
        # default. So on every real run that branch is dead code, and a dead branch reports exactly
        # what a working one does -- nothing. Proving it here is the only thing that distinguishes
        # "the one home is permitted" from "the one home has never been tested".
        with open(os.path.join(d, "budget.json"), "w") as fh:
            json.dump({"floors": {"launch_refuse_mb": CONTROL_VALUE}}, fh, indent=2)
        v4, p4 = scan(d)
        home_rows = [r for r in p4 if r["permitted"].startswith("HOME")]
        if v4 or len(home_rows) != 1:
            print("CONTROL FAIL: a floor inside budget.json must be PERMITTED as HOME and never a "
                  "violation. violations=%r home_rows=%r" % (v4, home_rows))
            ok = False
        else:
            print("control 4/6 — a floor inside budget.json is PERMITTED as HOME: ok "
                  "(%s:%d value=%d)" % (home_rows[0]["file"], home_rows[0]["line"],
                                        home_rows[0]["value"]))

        # ⚠ controls 5 and 6 exist because PROSE and FIXTURE are the two branches that make this
        # lint QUIETER, and a classifier that over-permits reports exactly what a clean tree does.
        # Each plants the SAME knob-and-value line twice -- once where the branch should swallow it
        # and once where it must not -- so a branch that swallowed everything fails here.
        # ⚠ ASSEMBLED FROM PARTS, for the same reason CONTROL_BODY is: a literal knob-and-value
        # line written out in this source makes the lint fire on ITSELF. Measured -- it did, on
        # all three of these, one commit after the same bug was fixed for CONTROL_BODY. The fix
        # did not generalise because it was applied to a constant rather than to the habit.
        knob_line = "%s = %d" % (CONTROL_KNOB, CONTROL_VALUE)
        stale_value = 2800          # a bare number: no knob on this line, so nothing to match
        dict_line = '    d = {"%s": %d}' % ("ram_available" + "_mb", stale_value)
        for n, name, body, expect in (
            (5, "prose.py",
             "# floor was --mem-floor-mb %d once\nx = 1\n%s\n" % (CONTROL_VALUE, knob_line),
             "PROSE"),
            (6, "fixture.py",
             "def _selftest():\n%s\n\ndef live():\n%s\n" % (dict_line, dict_line),
             "FIXTURE"),
        ):
            p = os.path.join(d, name)
            with open(p, "w") as fh:
                fh.write(body)
            v, pm = scan(d)
            got = [r for r in pm if r["permitted"].startswith(expect)]
            # exactly one swallowed by the branch, and exactly one still a violation
            if len(got) != 1 or len(v) != 1:
                print("CONTROL FAIL: %s must swallow ONE line and leave the twin a violation — "
                      "a branch that permits both is an over-permissive classifier and every "
                      "green it prints is uninformative. permitted=%r violations=%r"
                      % (expect, got, v))
                ok = False
            else:
                print("control %d/6 — %s swallows its own line and NOT its twin: ok" % (n, expect))
            os.remove(p)

    print("CONTROLS: %s" % ("all fired" if ok else "BROKEN — do not trust this lint"))
    return 0 if ok else 2


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--repo", default=os.path.abspath(os.path.join(here, "..", "..")),
                    help="tree to scan (default: the rbtv repo this script sits in)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--control", action="store_true",
                    help="prove the lint can go RED and back to GREEN; changes nothing on disk")
    args = ap.parse_args()

    if args.control:
        return control()

    violations, permitted = scan(args.repo)

    if args.json:
        print(json.dumps({"repo": args.repo, "violations": violations,
                          "permitted": permitted}, indent=2))
    else:
        print("FLOOR LINT — scanned %s" % args.repo)
        print()
        if permitted:
            print("PERMITTED — reported, never silently dropped: %d" % len(permitted))
            for r in permitted:
                print("  [%s] %s:%d value=%d" % (r["permitted"].split(" —")[0],
                                                 r["file"], r["line"], r["value"]))
            print()
        if violations:
            print("VIOLATIONS — a floor literal outside budget.json: %d" % len(violations))
            for r in violations:
                print("  %s:%d value=%d" % (r["file"], r["line"], r["value"]))
                print("      %s" % r["text"])
            print()
            print("Each is a COPY of a policy number. The floor's one home is the run's "
                  "budget.json; the consumer must READ it (r-floor-single-source, G-42).")
        else:
            print("VIOLATIONS: none")
            print()
            print("⚠ THIS IS A FLOOR ON THE CLAIM, NEVER PROOF OF CLOSURE. It proves no literal "
                  "THIS LINT CAN SEE survives; the enumerator is floor-homes.py, and a live "
                  "process's argv is a home no tree scan reaches. Green here = LANDED, not LIVE.")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
