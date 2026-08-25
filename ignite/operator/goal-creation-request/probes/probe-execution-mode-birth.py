#!/usr/bin/env python3
"""probe-execution-mode-birth.py — a created goal is BORN with its execution mode (owner ruling 2026-08-10).

WHAT THIS EXISTS TO CATCH.

`.rbtv/goals/<goal>/execution-mode` is gate 2 of all agent-INITIATED owner contact — the per-goal
owner-contact policy, registry concept `execution mode`, values `interactive | autonomous`, ABSENT
reading `autonomous`. Until 2026-08-10 NO creation path wrote it. Every daemon-created goal was
therefore born mode-less, and because absent reads `autonomous` the failure was SILENT and looked
exactly like a deliberate choice: a goal whose interviewer seat was built to ask the owner
questions could not reach them, and nothing anywhere recorded that nobody had decided.

The owner ruled the lifecycle: a workflow declares a default in its own scaffolding, goal creation
RESOLVES and WRITES it, and a requester may override it per goal. This probe drives the creation
half.

  1. THE RESOLVED DEFAULT LANDS — a request that names NO mode, created against the real `planning`
     workflow, produces a goal whose own `execution-mode` file reads `interactive`, because that
     workflow DECLARES `default-execution-mode: interactive`. Read from the created goal's file on
     disk, never from the request: a check that asserted the request said `interactive` would pass
     against a carrier that dropped the value entirely.
  2. AN EXPLICIT PAYLOAD VALUE WINS — the same workflow, the same declared `interactive` default,
     a request carrying `execution-mode: autonomous`: the goal is born `autonomous`. Without this,
     check 1 also passes for a carrier hard-wired to `interactive`.
  3. AN INVALID VALUE REFUSES AT BOTH SITES, AND CREATES NOTHING — `execution-mode: "sometimes"`
     raises a typed `Refusal` naming the enum, BEFORE any act, leaving no goal directory; and
     `validate` refuses the same payload naming member `V7`, the schema's fourteenth (task 7.631).
     This is the arm that matters most at the argv surface: the value becomes an argv element, and
     a bad one that fell through to a default would produce a goal silently gagged. The `validate`
     half is here because the two verbs USED TO DISAGREE — `validate` exited 0 on exactly these
     payloads while `handle` refused them, and a caged requester stages on `validate`'s verdict.
     Carried with its own positive controls: both legal modes and an ABSENT one must be ACCEPTED,
     or the arm passes against a validator that refuses every value it sees.
  4. DERIVATION, BOTH WAYS — a synthetic catalog root whose workflow declares NOTHING: a manifest
     with an `interactive`-Modality row derives `interactive`; one with none derives `autonomous`.
     Two arms, not one: a deriver hard-wired to either answer passes the other arm's opposite.
  5. THE CONTROL — the creation verb invoked with NO `--execution-mode` at all still writes the
     file, reading `autonomous`. This is what makes check 1 discriminating: had the verb's own
     default been flipped to `interactive`, check 1 would pass while meaning nothing.
  6. THE MUTANT (widen-don't-delete: the forwarding is REMOVED from a copy of the module source,
     the module is otherwise untouched) — check 1 is re-run and MUST go red. A green mutant means
     checks 1 and 4 are scoring nothing, because the creation verb's own `autonomous` default
     would be producing whatever they read; the probe then exits 2 INOPERATIVE rather than
     reporting a pass it did not earn.
  7. THE GOAL-KIND RUNG (owner ruling 2026-08-11, task 7.753) — a goal nobody will sit with was
     still born `interactive` whenever its workflow declared that default, so its seats waited on
     an owner who was never coming. Three arms, because the rung is PRECEDENCE, not a mapping:
     `goal-kind: non-interactive` with no requested mode overrides the declared `interactive`;
     an explicitly requested `interactive` still beats the kind; and an `interactive` kind derives
     NOTHING — it falls through to the workflow, deliberately one-directional. Two of the three
     would pass against a hard-wire; only all three pin the order.

Nothing here touches a live goals package: every act runs under `tempfile`, and the path driven is
`scaffold_goal`, which invokes `rbtv-goal scaffold` ONLY. It never reaches `scaffold-seats`, so no
seat is materialized, no pane is opened, and no agent is ever launched by this probe.      The one live
path it READS is the workspace's own `3-resources/tools/rbtv/meta` catalog root — read-only, and the point:
checks 1 and 2 must resolve the default from the workflow's REAL scaffolding, not from a fixture
this probe wrote to agree with itself.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tool" / "goal_creation_request.py"
GOAL_CLI = Path(__file__).resolve().parents[2] / "goals-tree" / "tool" / "goal_cli.py"
# Check 8's subject: the control plane's own execution-mode reader, required as the real module.
BUS_FERRY = Path(__file__).resolve().parents[3] / "chat" / "bus-ferry.js"

REAL_WORKFLOW = "plan-console"


def catalog_root() -> Path | None:
    """The workspace's component catalog root, found by WALKING UP for `rbtv.json`.

    Never a path relative to this repo's own depth: the repo is installed at a workspace-chosen
    location (this module's General rule), so counting parents would encode one instance's layout
    and read the wrong folder — or nothing — on the next. Returns None when no workspace roots
    this checkout, which the caller reports INOPERATIVE rather than passing over.
    """
    for parent in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        if (parent / "rbtv.json").is_file():
            try:
                data = json.loads((parent / "rbtv.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            rel = str((data or {}).get("rbtv_path") or "").strip()
            if not rel:
                return None
            root = Path(rel)
            if not root.is_absolute():
                root = parent / root
            return root / "meta"
    return None


CATALOG_ROOT = catalog_root()

FORWARDING = '"--execution-mode", mode,'

failures: list[str] = []
inoperative: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> bool:
    print(f"  {'ok  ' if cond else 'FAIL'} {label}{'' if cond else ': ' + detail}")
    if not cond:
        failures.append(label)
    return cond


def load(src: str | None = None):
    """The module, real or mutated, always under its REAL __file__.

    `scaffold_goal` resolves `goal_cli.py` through `Path(__file__).parents[2]`, so a mutant exec'd
    under any other name would look for the creation verb in the wrong tree and fail for a reason
    that has nothing to do with the mutation.
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


def request(name: str, mode: str | None = None, kind: str = "interactive") -> dict:
    # `execution-lane` is REQUIRED since 7.777; `console` because this probe measures the MODE
    # axis and the lane axis must not colour it (they are different axes — F-96's neighbour).
    req = {"goal-name": name, "goal-type": "one-shot",
           "goal-contract": "Ship the thing, verified at the edge.",
           "goal-kind": kind, "execution-lane": "console"}
    if mode is not None:
        req["execution-mode"] = mode
    return req


def born_mode(goal_dir: Path) -> str | None:
    """The mode the CREATED goal declares about itself. None when it declares none.

    Read with the SAME grammar the ferry reads it with — the whole file, trimmed — so a file this
    probe calls `interactive` is a file the control plane calls `interactive` too. A read that
    matched a substring would pass on a file whose second line negated its first.
    """
    path = goal_dir / "execution-mode"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def synthetic_catalog(base: Path, modality: str) -> Path:
    """A catalog root whose workflow DECLARES NOTHING — so only derivation can answer.

    `workflow.md` is written WITHOUT a `default-execution-mode:` key on purpose: with one, rung 1
    would answer and the derivation under test would never run.
    """
    root = base / f"cat-{modality or 'none'}"
    wf = root / "synth-comp" / "workflows" / "synth-flow"
    wf.mkdir(parents=True)
    (wf / "workflow.md").write_text(
        "---\nname: synth-flow\n---\n\n# synth-flow\n\nNo declared default, on purpose.\n",
        encoding="utf-8")
    (wf / "synth-flow.csv").write_text(
        "Seat/workflow,after,i/o,Modality\n"
        f"synth-first,,\"in: seed; out: draft\",{modality}\n"
        "synth-second,synth-first,\"in: draft; out: result\",agentic\n",
        encoding="utf-8")
    return root


def main() -> int:
    mod = load()

    if CATALOG_ROOT is None or not (CATALOG_ROOT / REAL_WORKFLOW / "workflows" / REAL_WORKFLOW /
                                    f"{REAL_WORKFLOW}.csv").is_file():
        inoperative.append(
            f"the real catalog root {CATALOG_ROOT} carries no {REAL_WORKFLOW} manifest — checks 1 "
            "and 2 would resolve against nothing and fall back to the model default, which is a "
            "pass for the wrong reason")
        print(f"INOPERATIVE: {inoperative[-1]}")
        return 2

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        root = tmp / ".rbtv" / "goals"
        root.mkdir(parents=True)

        print("1. a request naming NO mode is born with the WORKFLOW's declared default")
        declared, source = mod.workflow_default_execution_mode(str(CATALOG_ROOT), REAL_WORKFLOW)
        print(f"     resolved {declared!r} — {source}")
        check(f"the real {REAL_WORKFLOW} workflow declares/derives 'interactive'",
              declared == "interactive", f"resolved {declared!r} from {source}")
        step = mod.scaffold_goal(request("mode-default-goal"), str(root),
                                 catalog_root=str(CATALOG_ROOT), workflow=REAL_WORKFLOW)
        got = born_mode(root / "mode-default-goal")
        default_landed = check(
            "the CREATED goal's own execution-mode file reads 'interactive'",
            step.get("rc") == 0 and got == "interactive",
            f"rc={step.get('rc')} file reads {got!r}")
        check("the step names the mode AND where it came from",
              step.get("execution-mode") == "interactive"
              and "declared" in (step.get("execution-mode-source") or ""),
              str(step.get("execution-mode-source")))

        print("2. an explicit payload value WINS over the workflow default")
        step = mod.scaffold_goal(request("mode-explicit-goal", "autonomous"), str(root),
                                 catalog_root=str(CATALOG_ROOT), workflow=REAL_WORKFLOW)
        got = born_mode(root / "mode-explicit-goal")
        check("an explicit 'autonomous' beats the declared 'interactive'",
              step.get("rc") == 0 and got == "autonomous",
              f"rc={step.get('rc')} file reads {got!r}")
        check("the step attributes it to the request payload",
              step.get("execution-mode-source") == "the request payload",
              str(step.get("execution-mode-source")))

        print("3. an invalid value REFUSES, names the enum, and creates nothing")
        # Argv-shaped and case-variant inputs. This value BECOMES an argv element, so a value
        # opening with `-` is the one that would be read as a FLAG had it ever reached argv, and a
        # case variant is the one a lenient comparison waves through.
        for hostile in ("sometimes", "INTERACTIVE", "interactive ", "--json", "-i", "",
                        "autonomous; rm -rf /"):
            name = "mode-hostile-goal"
            try:
                mod.scaffold_goal(request(name, hostile), str(root),
                                  catalog_root=str(CATALOG_ROOT), workflow=REAL_WORKFLOW)
                check(f"{hostile!r} refuses", False, "did not refuse")
            except mod.Refusal as exc:
                check(f"{hostile!r} refuses, naming the enum",
                      "is not one of" in str(exc) and "interactive" in str(exc), str(exc)[:120])
            check(f"{hostile!r} left NO goal folder behind", not (root / name).exists())
            # The PRE-FLIGHT arm (task 7.631). `validate` performs no act, so before `V7` it
            # exited 0 on exactly these payloads while `handle` refused them — and a caged
            # requester stages on `validate`'s verdict. The two verbs must agree.
            out = mod.validate(request(name, hostile))
            members = [r.get("member") for r in out.get("refusals", [])]
            check(f"{hostile!r} is REFUSED by validate too, naming V7",
                  not out.get("accepted") and members == ["V7"],
                  f"accepted={out.get('accepted')} members={members}")

        # The positive control for the arm above: a LEGAL mode must still be accepted, or the
        # check would pass against a validator that refuses every execution-mode it sees.
        for legal in ("interactive", "autonomous"):
            out = mod.validate(request("mode-legal-goal", legal))
            check(f"validate ACCEPTS the legal mode {legal!r}", out.get("accepted"),
                  str(out.get("refusals")))
        # …and an ABSENT optional field is legal, which is what makes the field optional at all.
        out = mod.validate(request("mode-absent-goal"))
        check("validate ACCEPTS a request naming no mode at all", out.get("accepted"),
              str(out.get("refusals")))
        check("validate NAMES execution-mode among the fields it checked",
              any(c.get("field") == "execution-mode" for c in out.get("checked", [])),
              str(out.get("checked")))

        print("4. with NO declaration, the default is DERIVED from the manifest — both ways")
        cats: dict[str, Path] = {}  # kept for check 7c, which needs the no-interactive-seat one
        for modality, expect in (("interactive", "interactive"), ("agentic", "autonomous")):
            cat = cats[modality] = synthetic_catalog(tmp, modality)
            derived, source = mod.workflow_default_execution_mode(str(cat), "synth-flow")
            check(f"a manifest whose seat is {modality!r} derives {expect!r}",
                  derived == expect, f"derived {derived!r} from {source}")
            check("the source names DERIVATION, not a declaration",
                  derived == expect and source.startswith("derived from"), source)
            step = mod.scaffold_goal(request(f"derive-{modality}-goal"), str(root),
                                     catalog_root=str(cat), workflow="synth-flow")
            got = born_mode(root / f"derive-{modality}-goal")
            check(f"a goal created against it is born {expect!r}",
                  step.get("rc") == 0 and got == expect,
                  f"rc={step.get('rc')} file reads {got!r}")

        print("5. the control — the creation verb with NO --execution-mode still writes the file")
        # The pre-existing caller shape, invoked exactly as it was before this ruling. If the
        # verb's own default had been flipped to `interactive`, check 1 would still pass and only
        # this arm would catch it.
        contract = tmp / "c.md"
        contract.write_text("Ship it.\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(GOAL_CLI), "--root", str(root), "scaffold", "control-goal",
             "--contract", str(contract), "--lane", "console"],
            capture_output=True, text=True)
        got_control = born_mode(root / "control-goal")
        check("a caller passing no --execution-mode gets the file, reading 'autonomous'",
              proc.returncode == 0 and got_control == "autonomous",
              f"rc={proc.returncode} file reads {got_control!r}")

        print("7. the goal-kind rung — non-interactive is born autonomous, one-directionally")
        # a. THE RUNG. Same real `planning` workflow as check 1, which DECLARES `interactive`, and
        #    no mode in the request — so the only thing that can produce `autonomous` here is the
        #    kind. Read from the file on disk for check 1's reason: a step dict that said
        #    `autonomous` while the goal was written `interactive` is the exact defect.
        step = mod.scaffold_goal(request("kind-nonint-goal", kind="non-interactive"), str(root),
                                 catalog_root=str(CATALOG_ROOT), workflow=REAL_WORKFLOW)
        got = born_mode(root / "kind-nonint-goal")
        check("a non-interactive goal-kind is born 'autonomous', OVERRIDING the declared "
              "'interactive' workflow default",
              step.get("rc") == 0 and got == "autonomous",
              f"rc={step.get('rc')} file reads {got!r}")
        check("the step attributes the mode to the goal-kind, not to the workflow",
              "goal-kind" in (step.get("execution-mode-source") or ""),
              str(step.get("execution-mode-source")))

        # b. THE EXPLICIT ASK STILL WINS. Without this the rung would be a hard-wire: a request
        #    that deliberately asks for owner contact on a non-interactive goal must get it.
        step = mod.scaffold_goal(request("kind-nonint-explicit-goal", "interactive",
                                         kind="non-interactive"), str(root),
                                 catalog_root=str(CATALOG_ROOT), workflow=REAL_WORKFLOW)
        got = born_mode(root / "kind-nonint-explicit-goal")
        check("an explicit 'interactive' beats the non-interactive goal-kind (rung 1 > rung 2)",
              step.get("rc") == 0 and got == "interactive"
              and step.get("execution-mode-source") == "the request payload",
              f"rc={step.get('rc')} file reads {got!r} source={step.get('execution-mode-source')!r}")

        # c. ONE-DIRECTIONAL. An `interactive` goal-kind derives NOTHING — it falls through to the
        #    workflow, which here DERIVES `autonomous` from a manifest with no interactive seat.
        #    Read against the synthetic no-interactive-seat catalog rather than `planning`, whose
        #    declared `interactive` would agree with a kind-driven answer by coincidence and score
        #    nothing.
        step = mod.scaffold_goal(request("kind-int-goal", kind="interactive"), str(root),
                                 catalog_root=str(cats["agentic"]), workflow="synth-flow")
        got = born_mode(root / "kind-int-goal")
        check("an INTERACTIVE goal-kind derives nothing and still takes the workflow's answer",
              step.get("rc") == 0 and got == "autonomous"
              and (step.get("execution-mode-source") or "").startswith("the workflow default"),
              f"rc={step.get('rc')} file reads {got!r} source={step.get('execution-mode-source')!r}")

        print("8. the FERRY SEAM — the control plane's own reader, on the goals just created")
        # The rung above is only worth anything if the surface that ENFORCES owner contact agrees
        # with it. `bus-ferry.js#goalExecutionMode` is that surface (gate 2 of agent-initiated
        # owner contact), and until now NO probe drove it against a goal the creation path
        # actually made — both sides were guarded, the seam between them was not. Driven as the
        # REAL exported function over the REAL goal directories written above, never a re-read of
        # the file with this probe's own grammar, which would only prove the probe agrees with
        # itself.
        node = shutil.which("node")
        if node is None:
            inoperative.append("no `node` on PATH — the ferry seam could not be driven, and the "
                               "goal-kind rung is unproven at the surface that enforces it")
        else:
            reader = (
                "const f=require(process.argv[1]);"
                "console.log(JSON.stringify(process.argv.slice(3).map("
                "(g)=>f.goalExecutionMode(process.argv[2],g))));"
            )
            subjects = ["kind-nonint-goal", "mode-default-goal"]
            proc = subprocess.run(
                [node, "-e", reader, str(BUS_FERRY), str(tmp), *subjects],
                capture_output=True, text=True)
            modes = None
            if proc.returncode == 0:
                try:
                    modes = dict(zip(subjects, json.loads(proc.stdout.strip())))
                except ValueError:
                    modes = None
            print(f"     ferry reads {modes} (rc={proc.returncode})")
            if modes is None:
                inoperative.append(f"the ferry reader did not answer (rc={proc.returncode}): "
                                   f"{(proc.stderr or proc.stdout)[:200]}")
            else:
                check("the ferry reads the flow-born NON-INTERACTIVE goal as 'autonomous'",
                      modes.get("kind-nonint-goal") == "autonomous", str(modes))
                # The control: without it the arm passes against a ferry hard-wired to
                # `autonomous`, which is the pre-2026-08-10 defect the mode file exists to close.
                check("…and still reads the interactive-workflow goal as 'interactive' (control)",
                      modes.get("mode-default-goal") == "interactive", str(modes))

        print("6. the mutant — the --execution-mode forwarding removed; check 1 MUST go red")
        src = TOOL.read_text(encoding="utf-8")
        if src.count(FORWARDING) != 1:
            inoperative.append(
                f"the forwarding anchor {FORWARDING!r} appears {src.count(FORWARDING)} times in "
                "the module source — the mutation would be a silent no-op or ambiguous, and "
                "checks 1 and 4 would score nothing")
        else:
            mutant = load(src.replace(FORWARDING, "", 1))
            mroot = tmp / "mutant" / ".rbtv" / "goals"
            mroot.mkdir(parents=True)
            mstep = mutant.scaffold_goal(request("mode-default-goal"), str(mroot),
                                         catalog_root=str(CATALOG_ROOT), workflow=REAL_WORKFLOW)
            mgot = born_mode(mroot / "mode-default-goal")
            print(f"     mutant goal is born {mgot!r} (rc={mstep.get('rc')})")
            if mgot == "interactive":
                inoperative.append(
                    "the mutant STILL produced an 'interactive' goal — checks 1 and 4 cannot "
                    "distinguish a working carrier from a dropped one")
            else:
                print("  ok   the mutant drops the mode and falls to 'autonomous' — check 1 "
                      "discriminates")
            # The mutant must fail for the RIGHT reason: the goal is still created, it just
            # carries the wrong mode. A mutant that crashed would also be "not interactive".
            if mstep.get("rc") != 0:
                inoperative.append(f"the mutant did not scaffold at all (rc={mstep.get('rc')}) — "
                                   "its red is a crash, not a dropped mode")
            if not default_landed:
                inoperative.append("check 1 was already red, so the mutant proves nothing")

    print()
    if inoperative:
        for item in inoperative:
            print(f"INOPERATIVE: {item}")
        print("probe-execution-mode-birth: INOPERATIVE — not a pass")
        return 2
    if failures:
        print(f"probe-execution-mode-birth: FAIL — {len(failures)} failure(s): {failures}")
        return 1
    print("probe-execution-mode-birth: PASS — a created goal is born with its execution mode: the "
          "workflow's declared default lands, an explicit request value wins, an invalid one "
          "refuses creating nothing, derivation answers both ways, a non-interactive goal-kind "
          "overrides the workflow default one-directionally, and the verb's own default is intact")
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
