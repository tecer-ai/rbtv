#!/usr/bin/env python3
"""probe-cagespec-mirror.py — the PIN that fails when `cagespec.py` drifts from `cage.js`.

⚠ WHAT THIS REPLACES, AND WHY IT IS BACK. `cagespec.py` is the Python MIRROR of
`server/spawn/cage.js#composeSeatCage`. One check held it against the composer —
`jobs/edge-runner-job.py#check_deriver_mirrors_the_composer` — and it was DELETED with its file.
Nothing replaced it, and cagespec's own docstring has said so ("this mirror is currently unpinned")
since. The gap is not hypothetical: it FIRED. W3's `849b09df` added the grant class
`permissionEditsRo` to the JS composer's template; `cagespec.py` did not know it; an unknown grant
field fails the WHOLE template closed, so every goal-relative token evaluated `undecided` and
`materialize-seats.py` refused `cage-goal-writes-ungranted` for EVERY seat declaring a
`goal-writes` output. It shipped red and nobody noticed until the next agent ran the selftest.

THE DRIFT THIS MUST CATCH, stated exactly: **a grant class known to the JS composer and unknown to
the Python deriver.** So the arms read the LIVE template — `config/spawn-profiles.yaml`'s
`cage.SeatBinds`, the one input `cage.js` substitutes `{grant:FIELD}` out of — rather than a copy,
and hold it against cagespec's own three sets (`DROPPED_GRANTS`, `GOAL_WRITE_GRANT`,
`PERMISSION_EDITS_GRANT`). A class added to the template without a matching cagespec row turns A2
red, and A3 shows the CONSEQUENCE the drift actually had: the whole template undecided.

WHY NOT DRIVE `composeSeatCage` THROUGH NODE, as the deleted check did. That check re-derived every
DROPPED entry through the real composer to prove it lands outside the goal folder. This one is
narrower on purpose: the drift that shipped was a VOCABULARY gap, catchable by reading the live
template, and a probe that boots the node composer buys the drop-table re-derivation at the cost of
a fixture goal tree. Narrow and green beats broad and deleted — the drop-table re-derivation is
noted as unpinned, not silently claimed.

No tmux, no daemon, no network. Run it through the enumerator: `node deploy/probe-suite.js --only
cagespec-mirror`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
OUT = HERE / "probe-cagespec-mirror.out"
PROFILES = KIT.parent / "config" / "spawn-profiles.yaml"

sys.path.insert(0, str(KIT))

lines, failures, inoperative = [], [], []


def check(tag, ok, detail):
    lines.append(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def stop(tag, detail):
    lines.append(f"INOP  {tag}  {detail}")
    inoperative.append(tag)


GRANT_SLOT = re.compile(r"\{grant:([a-zA-Z][a-zA-Z0-9_]*)\}")


def live_seat_binds(text):
    """The `SeatBinds:` list of quoted entries, read off the yaml WITHOUT a yaml dependency.

    cagespec is deliberately dependency-free and this probe stays on its side of that line. The
    block ends at the first line that is not a `- "entry"` item, so a malformed template truncates
    the list instead of swallowing the keys after it — and A1's non-vacuity floor catches that."""
    out, in_block = [], False
    for line in text.split("\n"):
        if not in_block:
            if re.match(r"^\s*SeatBinds:\s*$", line):
                in_block = True
            continue
        if re.match(r"^\s*#", line) or not line.strip():
            continue
        item = re.match(r"^\s*-\s*\"(.+)\"\s*$", line)
        if not item:
            break
        out.append(item.group(1))
    return out


def main():
    if not PROFILES.exists():
        stop("A0", f"the live template is not at {PROFILES}")
        return
    import cagespec

    binds = live_seat_binds(PROFILES.read_text(encoding="utf-8"))
    fields = sorted({f for e in binds for f in GRANT_SLOT.findall(e)})
    known = set(cagespec.DROPPED_GRANTS) | {cagespec.GOAL_WRITE_GRANT,
                                            cagespec.PERMISSION_EDITS_GRANT}

    # ── A1 — NON-VACUITY. A template this probe failed to parse would make A2/A3 pass empty. ──
    check("A1", len(binds) >= 10 and len(fields) >= 5,
          f"read {len(binds)} live SeatBinds entries carrying {len(fields)} grant classes: "
          f"{', '.join(fields)}")

    # ── A2 — THE PIN. Every grant class the JS composer's template names is known to the Python
    # deriver. This is the arm that goes RED on the exact drift `849b09df` shipped. ────────────
    unknown = [f for f in fields if f not in known]
    check("A2", not unknown,
          "every live grant class is modelled by cagespec" if not unknown else
          f"UNKNOWN TO cagespec.py: {', '.join(unknown)} — the template grew and the mirror did "
          f"not; every goal-relative token now evaluates `undecided` and materialize-seats.py "
          f"refuses `cage-goal-writes-ungranted` for every seat declaring an output")

    # ── A3 — THE CONSEQUENCE, measured rather than argued: the live template really composes,
    # and a real goal-relative token really decides. A2 says the vocabulary matches; this says the
    # mirror still WORKS on it — the observable that was red for a day at `849b09df`. ──────────
    spec = cagespec.compose(binds, seat="builder", goal_writes=["notes.md"])
    verdict = cagespec.evaluate(binds, "notes.md", seat="builder", goal_writes=["notes.md"])[0]
    check("A3", spec is not None and verdict == cagespec.WRITABLE,
          f"live template composes {len(spec) if spec else 0} goal-relative entries; a declared "
          f"`goal-writes` output reads `{verdict}` (want `{cagespec.WRITABLE}`)")

    # ── A4 — AND IT STILL FAILS CLOSED. The pin must not be satisfiable by making cagespec
    # permissive: an unknown class is `undecided`, never a guess. ─────────────────────────────
    grown = binds + ["ro-bind-try:{grant:aClassNobodyModelled}"]
    check("A4", cagespec.compose(grown, seat="builder") is None,
          "an unmodelled grant class still returns None (undecided) — the mirror stays fail-closed")

    # ── A5 — cagespec's OWN asserts. The mirror's internal reading is held by its __main__; a
    # pin that ran the vocabulary check while those rotted would be half a pin. ────────────────
    import subprocess
    r = subprocess.run([sys.executable, str(KIT / "cagespec.py")],
                       capture_output=True, text=True, timeout=60)
    check("A5", r.returncode == 0,
          f"`python3 cagespec.py` exit={r.returncode}: {(r.stdout or r.stderr).strip()[:160]}")


try:
    main()
except Exception as exc:                                                    # noqa: BLE001
    stop("harness", f"{exc.__class__.__name__}: {exc}")

body = "\n".join(lines) + "\n"
OUT.write_text(body, encoding="utf-8")
sys.stdout.write(body)
if inoperative:
    print(f"probe-cagespec-mirror: INOPERATIVE ({len(inoperative)} arm(s) could not run)")
    sys.exit(2)
if failures:
    print(f"probe-cagespec-mirror: FAIL ({len(failures)}): {', '.join(failures)}")
    sys.exit(1)
print(f"probe-cagespec-mirror: PASS ({len(lines)} arms)")
sys.exit(0)
