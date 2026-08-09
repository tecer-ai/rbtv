#!/usr/bin/env python3
"""probe-goal-type-carrier.py — the goal TYPE survives the request path to the descriptor (7.533).

WHAT THIS EXISTS TO CATCH, and why it is not the defect the row that minted it described.

Row 7.533 was minted on the reading that `goal_cli.py`'s `--type` argparse DEFAULT
(`default="one-shot"`) meant "nothing on the request path can produce a recurring goal". Re-measured
at HEAD, that reading is wrong: the flag carries `choices=list(GOAL_TYPES)`, so the default applies
only when the flag is OMITTED, and the request layer has forwarded `--type request["goal-type"]`
since 58d0e13 (2026-08-01). The carrier EXISTS.

What did NOT exist is any exercise of it. Every probe and every selftest arm in this repo passed
`goal-type: "one-shot"`; `recurring` appeared in no probe, and no check anywhere read the created
goal's OWN descriptor to see which type landed. So the carrier was correct and UNPROVEN — and an
unproven carrier is indistinguishable from a broken one until something drives it. That is the gap
this probe closes: not a missing feature, a missing witness.

THE PROOF IS THE CREATED GOAL'S DESCRIPTOR ON DISK, NEVER THE REQUEST. A check that asserted the
request said `recurring` would pass against a carrier that dropped the value entirely — the request
is the input, and reading the input back proves only that the test wrote it.

  1. RECURRING LANDS — a validated recurring request scaffolds a goal whose own `goal.md` declares
     `type: recurring`. Read from the descriptor, not from the request.
  2. THE DEFAULT IS INTACT (the control) — the existing caller shape that passes NO `--type` still
     produces `one-shot`. Without this, check 1 would also pass if the change had flipped the
     default, i.e. if every goal had silently become recurring.
  3. ONE-SHOT STILL ROUND-TRIPS — an explicit one-shot request lands one-shot, so check 1 is not
     passing for a constant reason (a carrier hard-wired to `recurring` fails here).
  4. HOSTILE INPUT REFUSES TYPED, AT BOTH LAYERS — an unrecognised type is refused by the request
     validator naming member V4, and, independently, by the creation verb itself. Neither falls
     through to a default. The argv-shaped inputs matter because this value BECOMES an argv element
     (`goal_creation_request.py#scaffold_goal`), which the `d-q10-launcher` hostile-row-text
     criterion makes a mandatory review surface.
  5. THE MUTANT — the `--type` forwarding is removed from a copy of the module source and check 1
     is re-run. It MUST go red. A green mutant means checks 1-3 are scoring nothing (a descriptor
     that reads `recurring` because the tool defaulted there would satisfy them all), and this
     probe then exits 2 INOPERATIVE rather than reporting a pass it did not earn.

Nothing here touches a live goals package: every act runs under `tempfile`, and the path driven is
`scaffold_goal` — which invokes `rbtv-goal scaffold` ONLY. It never reaches `scaffold-seats`, so no
seat is materialized, no pane is opened and no agent is ever launched by this probe.
"""

import importlib.util
import re
import sys
import tempfile
import types
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tool" / "goal_creation_request.py"
GOAL_CLI = Path(__file__).resolve().parents[2] / "goals-tree" / "tool" / "goal_cli.py"

FORWARDING = '"--root", str(goals_root), "--type", request["goal-type"],'
MUTANT_FORWARDING = '"--root", str(goals_root),'

failures: list[str] = []
inoperative: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> bool:
    print(f"  {'ok  ' if cond else 'FAIL'} {label}{'' if cond else ': ' + detail}")
    if not cond:
        failures.append(label)
    return cond


def load(src: str | None = None):
    """The module, real or mutated, always under its REAL __file__.

    `scaffold_goal` resolves `goal_cli.py` through `Path(__file__).parents[2]`, so a mutant
    exec'd under any other name would look for the creation verb in the wrong tree and fail for
    a reason that has nothing to do with the mutation.
    """
    if src is None:
        spec = importlib.util.spec_from_file_location("gcr_real", TOOL)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    mod = types.ModuleType("gcr_mutant")
    mod.__file__ = str(TOOL)
    exec(compile(src, str(TOOL), "exec"), mod.__dict__)
    return mod


def request(name: str, gtype: str) -> dict:
    return {"goal-name": name, "goal-type": gtype,
            "goal-contract": "Ship the thing, verified at the edge.",
            "goal-kind": "interactive"}


def declared_type(goal_dir: Path) -> str | None:
    """The type the CREATED goal declares about itself. None when it declares none."""
    gm = goal_dir / "goal.md"
    if not gm.is_file():
        return None
    m = re.search(r"^type:\s*(\S+)\s*$", gm.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def scaffold(mod, root: Path, name: str, gtype: str) -> tuple[dict, str | None]:
    step = mod.scaffold_goal(request(name, gtype), str(root))
    return step, declared_type(root / name)


def main() -> int:
    mod = load()

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        root = tmp / ".rbtv" / "goals"
        root.mkdir(parents=True)

        print("1. a recurring request lands a recurring DESCRIPTOR")
        verdict = mod.validate(request("rec-goal", "recurring"), goals_root=str(root))
        check("the validator ACCEPTS a recurring request",
              verdict.get("accepted") is True, str(verdict.get("refusals")))
        step, got = scaffold(mod, root, "rec-goal", "recurring")
        check("scaffold_goal exits 0 for a recurring request", step.get("rc") == 0, str(step))
        recurring_landed = check(
            "the CREATED goal's own descriptor declares type: recurring",
            got == "recurring", f"descriptor declares {got!r}")

        print("2. the control — an existing caller that names NO type still gets one-shot")
        # The pre-existing caller shape, invoked exactly as it was before this row: the creation
        # verb with no `--type` at all. This is the before/after comparison that proves the
        # carrier is ADDITIVE — if the default had been flipped, check 1 would still pass and
        # only this arm would catch it.
        import subprocess
        contract = tmp / "c.md"
        contract.write_text("Ship it.\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(GOAL_CLI), "--root", str(root), "scaffold", "default-goal",
             "--contract", str(contract)],
            capture_output=True, text=True)
        got_default = declared_type(root / "default-goal")
        check("a caller passing no --type still produces one-shot",
              proc.returncode == 0 and got_default == "one-shot",
              f"rc={proc.returncode} descriptor declares {got_default!r}")

        print("3. an explicit one-shot request still round-trips as one-shot")
        step, got_one = scaffold(mod, root, "one-goal", "one-shot")
        check("the CREATED goal's own descriptor declares type: one-shot",
              step.get("rc") == 0 and got_one == "one-shot",
              f"descriptor declares {got_one!r}")

        print("4. hostile input refuses TYPED, at both layers, never through a default")
        # Argv-shaped and case-variant inputs. `recurring` differing only in case is the one most
        # likely to be waved through by a lenient comparison, and a value opening with `-` is the
        # one that would be read as a FLAG were it ever to reach the argv it is destined for.
        for hostile in ("recurring; rm -rf /", "--json", "-r", "RECURRING", "recurring ", ""):
            v = mod.validate(request("hostile-goal", hostile), goals_root=str(root))
            members = [r.get("member") for r in v.get("refusals") or []]
            check(f"request layer refuses {hostile!r} naming a member",
                  v.get("accepted") is False and ("V4" in members or "P2" in members),
                  f"accepted={v.get('accepted')} members={members}")

        # The SECOND layer, proven independently: were validation ever bypassed, the creation verb
        # itself must still refuse rather than fall back to its argparse default.
        import argparse as _ap
        gspec = importlib.util.spec_from_file_location("gc_real", GOAL_CLI)
        gc = importlib.util.module_from_spec(gspec)
        gspec.loader.exec_module(gc)
        try:
            gc.cmd_scaffold(_ap.Namespace(
                root=str(root), json=False, dry_run=False, goal_name="bypass-goal",
                type="recurring; rm -rf /", due=None, contract=str(contract)))
            check("the creation verb refuses an unrecognised type", False, "did not refuse")
        except gc.Refusal as exc:
            check("the creation verb refuses an unrecognised type",
                  "must be one of" in str(exc), str(exc))
        check("the refused type created NO goal folder",
              not (root / "bypass-goal").exists())

        print("5. the mutant — the --type forwarding removed; check 1 MUST go red")
        src = TOOL.read_text(encoding="utf-8")
        if FORWARDING not in src:
            inoperative.append("the forwarding anchor was not found in the module source — the "
                               "mutation would be a silent no-op and checks 1-3 would score "
                               "nothing")
        else:
            mutant = load(src.replace(FORWARDING, MUTANT_FORWARDING, 1))
            mroot = tmp / "mutant" / ".rbtv" / "goals"
            mroot.mkdir(parents=True)
            mstep, mgot = scaffold(mutant, mroot, "rec-goal", "recurring")
            print(f"     mutant descriptor declares {mgot!r} (rc={mstep.get('rc')})")
            if mgot == "recurring":
                inoperative.append("the mutant STILL produced a recurring descriptor — checks 1-3 "
                                   "cannot distinguish a working carrier from a dropped one")
            else:
                print("  ok   the mutant drops the type and lands one-shot — checks 1-3 discriminate")
            # The mutant must fail for the RIGHT reason: the goal is still created, it just
            # carries the wrong type. A mutant that crashed would also be "not recurring".
            if mstep.get("rc") != 0:
                inoperative.append(f"the mutant did not scaffold at all (rc={mstep.get('rc')}) — "
                                   "its red is a crash, not a dropped type")
            if not recurring_landed:
                inoperative.append("check 1 was already red, so the mutant proves nothing")

    print()
    if inoperative:
        for item in inoperative:
            print(f"INOPERATIVE: {item}")
        print("probe-goal-type-carrier: INOPERATIVE — not a pass")
        return 2
    if failures:
        print(f"probe-goal-type-carrier: FAIL — {len(failures)} failure(s): {failures}")
        return 1
    print("probe-goal-type-carrier: PASS — the type carrier is proven end-to-end, "
          "the default is intact, and hostile types refuse typed at both layers")
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
        (Path(__file__).with_suffix(".out")).write_text("".join(tee.buf), encoding="utf-8")
    sys.exit(rc)
