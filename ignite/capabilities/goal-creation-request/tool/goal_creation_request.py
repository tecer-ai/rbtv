#!/usr/bin/env python3
"""goal_creation_request — THE ENTRY: a goal-creation request arrives here, is validated against
the landed request schema, and is discharged as three ordered acts — create -> arm -> launch.

Core-build task **7.211** (design id `E16`) of run-3's `no-row-builds-the-entry` pass. This file
exists because the wave that consumes the entry was designed on the premise that the entry already
existed, and the disk refuted it: every consumer reached for a thing no row built. This is that row.

WHAT THIS FILE IS, AND WHAT IT IS NOT
-------------------------------------
It is ONE component with ONE output pair `{handler-path, call-site-path}`. The three acts are what
it ORCHESTRATES, not three jobs — splitting them would produce more than one row declaring the
entry's existence, which the pass's end-state forbids.

**It is NOT hosted in `chat-bridge`, deliberately.** `chat-bridge.js:11-12` states its own bound
verbatim: *"It holds NO spawn/queue capability (chat-bridge-spec.md Behavior #5)"*. Hosting the
entry there would change a designed bound of another component. The entry is its own capability
instead, following the shape its five siblings already use.

THE ONE LOCATION COMPUTER — WHY THIS FILE IMPORTS RATHER THAN COMPUTES
----------------------------------------------------------------------
The arming marker's location is computed by `edge-runner-job.arm_path()` and by nothing else. This
file IMPORTS it. A second computation of that location — here, to save an import — would be two
readers free to disagree about which packages are armed, and a disagreement about ARMING is the C4
failure itself. `arm_path()`'s own docstring says the same thing from the other side.

THE RULED NAME
--------------
The creation act invokes **`scaffold-seats`**, the ruled name, resolved on PATH. It never invokes
the script path `materialize-seats.py` behind it, and it never hand-rolls a spawn: `d-materialize-term`
and `p-the-scaffold-seats-fix-is-NOT-a-text-alignment` bind — invoke the ruled name, do not align
text to whatever a call site happens to say.

⚠ ARMING DOES NOT GENERALISE FROM THIS FILE. This handler is the first production writer of an
arming marker, for the path it builds and for nothing else (`decisions.md#p-E16-carries-the-durable-
arming-writer-itself-and-that-does-NOT-generalise-arming`). A goal created by any OTHER path stays
BORN INERT, and this file's existence closes no general arming issue.

THE REFUSAL ARM (task **7.206**, design id `E11`, arm **a**)
------------------------------------------------------------
The refusal is raised HERE, at the entry — the refusing site and the site that answers the requester
are the same file, so ONE observable carries the whole criterion and no propagation question arises.
A refusal therefore names three things at the requester's surface, never a bare status: the MEMBER of
E3's closed reject set that matched, the field or shape it rejects, and what held instead.

The thirteen members and their `S -> P -> V` class-stop report order are the landed schema's
(§6.1, §6.2) and are CONSUMED here, never forked: this file adds no fourteenth member and re-orders
nothing. Where §6.2 stops evaluation at the first class in which any member matched, this validator
RETURNS there — it does not evaluate a later class and then filter, because `V2`/`V3` reach the
filesystem and "evaluated but suppressed" is not what the schema says.

⚠ `goal-kind` IS VALIDATED AND DELIBERATELY NOT PERSISTED. The request schema declares the field
and states explicitly that it does NOT say where the kind is stored, because choosing a carrier is
a structural convention and owner-gated. `goal.md` frontmatter carries no such field and the
creation verb has no flag for it. So this handler checks the value and stops there; inventing a
carrier would be a convention nobody ruled. Named in the result as `kind-carrier: NONE`.
"""

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --------------------------------------------------------------- the schema

# From the landed request-schema artifact, §1 — ONE field set, both goal kinds, five fields:
# four required plus one optional. The set is CLOSED: a name outside it is a refusal, never a
# passthrough, because §1's table IS the whole field set.
REQUIRED_FIELDS = ("goal-name", "goal-type", "goal-contract", "goal-kind")
OPTIONAL_FIELDS = ("due-date",)
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# §1.1 — the same expression the creation verb enforces (`goal_cli.py:36`), not a second spelling
# of it. Kept as a literal here on purpose: importing it would couple the request layer's contract
# to a tool's internals, and the schema names the constraint, not the import.
GOAL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GOAL_TYPES = ("one-shot", "recurring")
# §1.4 — closed by TEXT (7.79, 7.136, the definition-of-done), by no code. Stated so a reader does
# not go looking for the enum in a source file that does not carry it.
GOAL_KINDS = ("interactive", "non-interactive")

RULED_LAUNCH_NAME = "scaffold-seats"

# ------------------------------------------- the CLOSED reject set (E3's §6.1)
#
# THIRTEEN members, id -> (member name, the field or shape it rejects). The set is CLOSED: these are
# the members and no others, and growing it requires adding a CLAUSE to the schema's §1 FIRST. This
# file therefore mints nothing — a condition with no member here is a condition this schema ADMITS,
# and inventing a fourteenth member would re-open a closed half nobody reviewed.
REJECT_SET_SOURCE = (".rbtv/goals/build-core-daemon-mvp/runs/run-3/planning/"
                     "briefing-master-request-launch-entry/request-schema-goal-creation.md §6.1")
REJECT_SET = {
    "S1": ("payload-not-a-field-mapping", "shape: the payload as a whole"),
    "S2": ("field-name-not-in-the-five", "shape: the payload's set of field names"),
    "S3": ("field-value-not-a-single-value", "shape: the value of one named field"),
    "P1": ("goal-name-absent", "field goal-name"),
    "P2": ("goal-type-absent", "field goal-type"),
    "P3": ("goal-contract-absent", "field goal-contract"),
    "P4": ("goal-kind-absent", "field goal-kind"),
    "V1": ("goal-name-not-kebab-case", "field goal-name"),
    "V2": ("goal-name-taken-in-resolved-root", "field goal-name"),
    "V3": ("goal-name-declared-by-another-goal", "field goal-name"),
    "V4": ("goal-type-not-in-enum", "field goal-type"),
    "V5": ("goal-contract-empty-after-strip", "field goal-contract"),
    "V6": ("goal-kind-not-in-enum", "field goal-kind"),
}
# §6.2 — the classes are evaluated S -> P -> V and evaluation STOPS at the first class in which any
# member matched; within that class EVERY matching member is reported. The order is the schema's own
# ruling, not this file's preference, and it exists so two implementers report the same MEMBERS
# rather than merely the same verdict.
REJECT_CLASS_ORDER = ("S", "P", "V")

# TWO READINGS THIS FILE TAKES TO MAKE THE MEMBERS DECIDABLE OVER A JSON PAYLOAD, STATED RATHER THAN
# BURIED. §6.1 states its conditions in the schema's prose vocabulary ("the ask resolves to no value,
# or to more than one"); a payload is JSON. Neither reading adds or removes a member.
#
#   (1) S3 is about ARITY, not type. It fires when the ask resolves to NO value (`null`) or to MORE
#       THAN ONE (a list, tuple, dict or set). A wrongly-TYPED scalar is still one value and is NOT
#       S3 — it falls to that field's own value member below.
#   (2) A wrongly-typed scalar fails its field's VALUE member, because a value member is the
#       negation of §1's constraint clause and a value of the wrong type does not satisfy that
#       clause: `5` is not lowercase kebab-case (`V1`), is not one of two literals (`V4`/`V6`), and
#       is not non-empty prose (`V5`). This keeps the pre-existing strictness without minting a
#       member for "wrong type", which §1 states as a Type column and not as a separate clause.
_MULTI_VALUE_TYPES = (list, tuple, dict, set)

# The ONE location computer, reached by file path because the module's filename is hyphenated and
# so is not importable by name.
EDGE_RUNNER_JOB = Path(__file__).resolve().parents[3] / "jobs" / "edge-runner-job.py"


class Refusal(Exception):
    """A refusal with a reason. Never a crash: the caller gets a verdict it can act on."""


def _edge_runner():
    """The module that owns `arm_path`. Imported, never re-implemented — see the module docstring."""
    if not EDGE_RUNNER_JOB.is_file():
        raise Refusal(
            f"{EDGE_RUNNER_JOB}: the one arming-location computer is not on disk, so this handler "
            "cannot arm anything. It does NOT fall back to computing the location itself: a second "
            "computer is the failure the import exists to prevent."
        )
    spec = importlib.util.spec_from_file_location("edge_runner_job", EDGE_RUNNER_JOB)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----------------------------------------------------------- 1 · VALIDATION

def _stated(refusals):
    """The requester-facing TEXT of a refusal — never a bare status.

    A status says a request was refused. This says WHICH member of the closed set matched, what it
    rejects, and what held instead — which is the difference between a requester who can fix the
    request and one who can only guess at it.
    """
    if not refusals:
        return ""
    cls = refusals[0]["class"]
    head = (f"REFUSED at the entry — {len(refusals)} member(s) of the closed reject set matched in "
            f"class {cls}; evaluation stopped at that class (§6.2). Reject set: {REJECT_SET_SOURCE}.")
    lines = [f"  [{r['member']}] {r['member-name']} — {r['rejects']}: {r['detail']}"
             for r in refusals]
    return "\n".join([head] + lines)


def _verdict(checked, refusals, stage):
    return {"accepted": not refusals,
            "checked": checked,
            "refusals": refusals,
            "stated-refusal": _stated(refusals),
            "refusal-site": "entry" if refusals else None,
            "arm": "a" if refusals else None,
            "reject-set-source": REJECT_SET_SOURCE,
            "classes-evaluated": stage,
            "kind-carrier": "NONE"}


def validate(payload, goals_root=None):
    """Validate a request field by field, NAMING every field checked and every MEMBER that matched.

    Returns `{accepted, checked, refusals, stated-refusal, refusal-site, arm, classes-evaluated,
    kind-carrier}`. `checked` is one point: a validator that reports only a verdict cannot be
    distinguished from one that checked nothing and guessed right. The member ids are the other: a
    refusal that names no member cannot be told apart from a refusal invented at the call site.

    THE THREE CLASSES ARE STAGED, AND EACH STAGE RETURNS. §6.2 stops evaluation at the first class
    in which any member matched — evaluating a later class and filtering it out afterwards is a
    different act, and for `V2`/`V3` it is a different act that touches the filesystem.
    """
    checked = []
    refusals = []

    def refuse(member, detail):
        name, rejects = REJECT_SET[member]
        refusals.append({"member": member, "class": member[0], "member-name": name,
                         "rejects": rejects, "detail": detail})

    # ================================================================== class S
    # --- S1 · the payload must resolve to name->value pairs, or no field can be looked up
    checked.append({"field": "<payload>", "check": "S1 · resolves to a field mapping"})
    if not isinstance(payload, dict):
        refuse("S1", f"payload resolved to {type(payload).__name__}, which cannot be looked up "
                     "by name")
        return _verdict(checked, refusals, "S")

    # --- S2 · the field set is CLOSED. Every offending name is reported, not just the first.
    checked.append({"field": "<field-names>", "check": f"S2 · closed set {list(ALL_FIELDS)}"})
    unknown = [k for k in payload if k not in ALL_FIELDS]
    if unknown:
        refuse("S2", f"field name(s) not in the five: {sorted(unknown)}")

    # --- S3 · ARITY, per reading (1) above: no value, or more than one. Each of the four is named
    # as checked whether or not it is present — a `checked` list that silently omitted an absent
    # field would read as "not applicable" when the truth is "absent".
    for field in REQUIRED_FIELDS:
        if field not in payload:
            continue
        checked.append({"field": field, "check": "S3 · resolves to exactly one value"})
        value = payload[field]
        if value is None:
            refuse("S3", f"'{field}': the ask resolves to NO value (null)")
        elif isinstance(value, _MULTI_VALUE_TYPES):
            refuse("S3", f"'{field}': the ask resolves to more than one value "
                         f"({type(value).__name__})")

    if refusals:
        return _verdict(checked, refusals, "S")

    # ================================================================== class P
    for field, member in (("goal-name", "P1"), ("goal-type", "P2"),
                          ("goal-contract", "P3"), ("goal-kind", "P4")):
        checked.append({"field": field, "check": f"{member} · present"})
        if field not in payload:
            refuse(member, "the field name is not among the payload's names")

    if refusals:
        return _verdict(checked, refusals, "S,P")

    # ================================================================== class V
    # Reached only when every required field is present and single-valued, so each value member
    # below has a value to test.
    value = payload["goal-name"]
    checked.append({"field": "goal-name", "check": f"V1 · matches {GOAL_NAME_RE.pattern}"})
    if not isinstance(value, str) or not GOAL_NAME_RE.match(value):
        refuse("V1", f"{value!r} is not lowercase kebab-case ({GOAL_NAME_RE.pattern})")
    elif goals_root is not None:
        # V2 and V3 — the only two members that reach outside the payload, both relative to the
        # goals root the caller aims at, a caller AIM and never a request field. Skipped, not
        # faked, when no root is supplied: a uniqueness verdict with no root to be unique IN is
        # not a verdict, and reporting one would be worse than reporting none.
        checked.append({"field": "goal-name", "check": "V2 · free in the resolved goals root"})
        root = Path(goals_root)
        if (root / value).exists():
            refuse("V2", f"{root / value} already resolves — creation is create-only")
        else:
            checked.append({"field": "goal-name",
                            "check": "V3 · declared by no other goal in that root"})
            for other in sorted(root.glob("*/goal.md")):
                head = other.read_text(encoding="utf-8", errors="replace")[:2000]
                m = re.search(r"^name:\s*(\S+)\s*$", head, re.MULTILINE)
                if m and m.group(1) == value:
                    refuse("V3", f"{other} declares name: {value}")

    checked.append({"field": "goal-type", "check": f"V4 · enum {list(GOAL_TYPES)}"})
    if payload["goal-type"] not in GOAL_TYPES:
        refuse("V4", f"{payload['goal-type']!r} is not exactly one of {list(GOAL_TYPES)}")

    value = payload["goal-contract"]
    checked.append({"field": "goal-contract", "check": "V5 · non-empty after whitespace strip"})
    if not isinstance(value, str) or not value.strip():
        refuse("V5", "a goal is born with its contract — the value is not non-empty prose "
                     f"(got {type(value).__name__} {value!r})")

    checked.append({"field": "goal-kind", "check": f"V6 · enum {list(GOAL_KINDS)}"})
    if payload["goal-kind"] not in GOAL_KINDS:
        refuse("V6", f"{payload['goal-kind']!r} is not exactly one of {list(GOAL_KINDS)}")

    # `due-date` is optional and its TYPE is unresolved in the schema, which records the gap rather
    # than guessing. So no value of it is rejected here — §6.3's ZERO value members, an empty slice
    # that is a decided closure and not a hole. Naming it as checked is what makes the slice visible.
    checked.append({"field": "due-date",
                    "check": "optional; type UNRESOLVED in the schema — no member rejects any value"})

    return _verdict(checked, refusals, "S,P,V")


# --------------------------------------------------------------- 2 · CREATE

def create(request, goals_root, package, catalog_root, bindings, conduct, claude_md, budget_json,
           seat=None, workflow=None, after=None, root=False, dry_run=False):
    """CREATE — the goal, then its run package, through the RULED NAME.

    Two invocations because the system splits them: `rbtv-goal scaffold` mints the goal folder and
    its contract; `scaffold-seats` materializes the run package. There is NO create-only mode on
    the second — it requires `--seat` or `--workflow` plus an explicit `--after|--root` — so this
    act NECESSARILY materializes at least one seat. That is a property of the only creation path in
    the system, not a choice this handler made.
    """
    goal_cli = (Path(__file__).resolve().parents[2] / "goals-tree" / "tool" / "goal_cli.py")
    goal_dir = Path(goals_root) / request["goal-name"]
    steps = []

    if not goal_dir.exists():
        # ⚠ THE CONTRACT GOES TO A TEMP FILE, AND NOTHING IS WRITTEN UNDER --dry-run. Measured, on
        # this row's own first exercise: an earlier draft staged the contract at
        # `package.parent.parent` and created that directory with `mkdir(parents=True)` BEFORE
        # testing `dry_run` — which is the goal directory itself. The dry run therefore CREATED the
        # goal, and the next run refused it as already existing. A dry run that writes makes the
        # one command meant for inspection the one that lies.
        with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8",
                                         delete=False) as fh:
            fh.write(request["goal-contract"])
            contract_file = Path(fh.name)
        try:
            cmd = [sys.executable, str(goal_cli), "scaffold", request["goal-name"],
                   "--root", str(goals_root), "--type", request["goal-type"],
                   "--contract", str(contract_file), "--json"]
            if request.get("due-date"):
                cmd += ["--due", request["due-date"]]
            steps.append(_run(cmd, "create-goal", dry_run))
        finally:
            contract_file.unlink(missing_ok=True)
    else:
        steps.append({"step": "create-goal", "skipped": f"{goal_dir} already resolves"})

    # THE RULED NAME. Resolved on PATH as the name — never the script path behind it.
    ruled = shutil.which(RULED_LAUNCH_NAME)
    if not ruled:
        raise Refusal(
            f"the ruled name '{RULED_LAUNCH_NAME}' does not resolve on PATH. This handler does NOT "
            "fall back to the script path behind it and does NOT rename anything: an absent ruled "
            "name is a sequencing fault to route, not a text alignment to perform."
        )
    if not (seat or workflow) or not (after or root):
        raise Refusal(
            "the creation path requires --seat or --workflow AND an explicit --after or --root. "
            "An omitted insertion point can NEVER default to root."
        )
    cmd = [RULED_LAUNCH_NAME, "--package", str(package), "--catalog-root", str(catalog_root),
           "--bindings", str(bindings), "--conduct", str(conduct), "--claude-md", str(claude_md),
           "--budget-json", str(budget_json), "--run-type", "fresh", "--json"]
    cmd += ["--seat", seat] if seat else ["--workflow", workflow]
    cmd += ["--root"] if root else ["--after", after]
    steps.append(_run(cmd, "create-package", dry_run))
    return steps


# ------------------------------------------------------------------ 3 · ARM

def arm(package, job_id, profile, note=None, dry_run=False):
    """ARM — write the marker at the location `edge-runner-job.arm_path()` computes, then read the
    result back through the fastpath's OWN reader.

    The read-back is the point. A marker that is present but that its reader rejects is not a
    partial success: absent, unreadable and unparseable all fail closed and are indistinguishable
    from each other at the door, and that indistinguishability IS the criterion.
    """
    mod = _edge_runner()
    path = mod.arm_path(package)          # THE one computer. Never recomputed here.
    payload = {"job-id": job_id, "profile": profile}
    if note:
        payload["note"] = note
    if dry_run:
        return {"step": "arm", "dry-run": True, "arm-path": str(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    accepted, why = mod.fastpath_arm(package)
    return {"step": "arm", "arm-path": str(path), "written": True,
            "accepted-by-fastpath-reader": accepted is not None,
            "reader-said": why if accepted is None else "armed",
            "arm-read-back": accepted}


# --------------------------------------------------------------- 4 · LAUNCH

def launch(package, only=None, dry_run=False):
    """LAUNCH — through the run's own coordination CLI, which is the ONLY writer of a session row.

    `sessions.csv` is born HERE and not at creation: the creation path omits it deliberately, so
    the ruled run-folder shape completes at this act. Its absence BEFORE this act is expected and
    is not a defect; its absence AFTER one is.

    This handler INVOKES the launcher; it does not reimplement it, and it opens no pane itself. The
    role gate on that command is the launcher's, and it stays the launcher's.
    """
    cmd = ["coordinate", "--package", str(package), "launch"]
    if only:
        cmd += ["--only", only]
    if dry_run:
        cmd += ["--dry-run"]
    return _run(cmd, "launch", dry_run=False)


def _run(cmd, step, dry_run):
    if dry_run:
        return {"step": step, "dry-run": True, "argv": cmd}
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {"step": step, "argv": cmd, "rc": proc.returncode,
            "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}


# ----------------------------------------------------------------- the entry

def handle(request, goals_root, package, catalog_root, bindings, conduct, claude_md, budget_json,
           job_id, profile, seat=None, workflow=None, after=None, root=False, note=None,
           do_launch=True, dry_run=False):
    """The entry: validate, then create -> arm -> launch, in that order and once.

    A refused request performs NO act. That ordering is the whole reason validation is a separate
    step rather than a check inside the create act.
    """
    verdict = validate(request, goals_root=goals_root)
    result = {"validation": verdict, "acts": {}}
    if not verdict["accepted"]:
        # THE REFUSAL IS STATED AT THE SURFACE THAT ANSWERS THE REQUESTER, not merely recorded
        # inside the verdict. This is the whole of arm `a`: the refusing site and the responding
        # site are the same file, so the requester sees the matched member by name — a bare
        # "REFUSED" is a status, and a status the requester cannot act on is what this arm exists
        # to replace.
        result["refusal-site"] = "entry"
        result["arm"] = "a"
        result["stated-refusal"] = verdict["stated-refusal"]
        result["members-matched"] = [r["member"] for r in verdict["refusals"]]
        result["outcome"] = "REFUSED — no act performed\n" + verdict["stated-refusal"]
        return result
    result["acts"]["create"] = create(
        request, goals_root, package, catalog_root, bindings, conduct, claude_md, budget_json,
        seat=seat, workflow=workflow, after=after, root=root, dry_run=dry_run)

    # ⚠ THE CHAIN FAILS CLOSED, AND THIS GUARD IS HERE BECAUSE ITS ABSENCE WAS MEASURED. On this
    # row's own first real exercise the create act's second step returned rc=1 (a refused bindings
    # key) — and an earlier draft armed the package anyway and reported the whole run ACCEPTED. An
    # arming marker on a package that was never created is worse than no marker: the door reads it,
    # believes the package, and advances something that does not exist. A later act NEVER runs on
    # an earlier act's failure, and the outcome NEVER reads ACCEPTED when a step returned non-zero.
    failed = [s for s in result["acts"]["create"] if s.get("rc") not in (0, None)]
    if failed:
        result["outcome"] = ("FAILED at create — later acts NOT performed. "
                             f"{len(failed)} step(s) returned non-zero: "
                             + ", ".join(f"{s['step']} rc={s['rc']}" for s in failed))
        result["acts"]["arm"] = {"step": "arm", "performed": False,
                                 "why": "the create act failed; arming an uncreated package is refused"}
        result["acts"]["launch"] = {"step": "launch", "performed": False,
                                    "why": "the create act failed"}
        return result

    result["acts"]["arm"] = arm(package, job_id, profile, note=note, dry_run=dry_run)
    if not dry_run and not result["acts"]["arm"].get("accepted-by-fastpath-reader"):
        # Written-but-rejected is a FAILURE, not a partial success: absent, unreadable and
        # unparseable all fail closed at the door and are indistinguishable from each other there.
        result["outcome"] = ("FAILED at arm — the marker was written but the fastpath's own reader "
                             "REJECTED it: " + str(result["acts"]["arm"].get("reader-said")))
        result["acts"]["launch"] = {"step": "launch", "performed": False, "why": "the arm act failed"}
        return result
    if do_launch:
        result["acts"]["launch"] = launch(package, only=seat, dry_run=dry_run)
        # THE LANE IS NAMED IN THE RESULT AND NEVER IN THE ARGV. It is computed from the argument
        # the entry already received: it reaches no argv, gates nothing, refuses nothing and adds
        # no flag. It exists because the entry's own output otherwise cannot say WHICH lane it just
        # asked for — the two are told apart only by the ABSENCE of `--only`. The staged lane asks
        # by forwarding a BARE launch and selecting nothing; naming the workflow's seats in the
        # argv instead would be the entry selecting seats, which is exactly what it is barred from.
        result["acts"]["launch"]["launch-lane"] = (
            "named-seat" if seat is not None else "staged-workflow")
        # THE LAUNCH ARM GATES THE OUTCOME TOO, and it is asserted at the ARTIFACT rather than at
        # the return code. A launch can exit 0 having opened a pane whose harness then died, and
        # `sessions.csv` is written only AFTER the harness is verified up — so the trace row, not
        # the exit status, is what distinguishes a launch that happened from one that reported
        # happening. An entry whose create and arm are proven and whose launch never ran is exactly
        # the artifact that passes every gate and then dies.
        rc = result["acts"]["launch"].get("rc")
        trace = Path(package) / "sessions.csv"
        row = trace.is_file() and len(trace.read_text(encoding="utf-8").splitlines()) > 1
        result["acts"]["launch"]["sessions-csv"] = str(trace)
        result["acts"]["launch"]["session-row-present"] = bool(row)
        if rc not in (0, None) or not row:
            result["outcome"] = (
                f"FAILED at launch — rc={rc}, session row present={bool(row)}. The run folder's "
                "ruled shape completes at THIS act, so a package without a session row is not "
                "launched, whatever the command returned.")
            return result
    else:
        result["acts"]["launch"] = {"step": "launch", "performed": False,
                                    "why": "--no-launch: the caller withheld the launch act"}
    result["outcome"] = "ACCEPTED"
    return result


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="rbtv-goal-request",
        description="The goal-creation request entry: validate a request, then create -> arm -> launch.")
    sub = p.add_subparsers(dest="verb", required=True)

    v = sub.add_parser("validate", help="validate a request payload; perform no act")
    v.add_argument("request", help="JSON file carrying the request payload, or - for stdin")
    v.add_argument("--goals-root", help="goals root the uniqueness checks resolve against")

    h = sub.add_parser("handle", help="validate, then create -> arm -> launch")
    h.add_argument("request", help="JSON file carrying the request payload, or - for stdin")
    h.add_argument("--goals-root", required=True)
    h.add_argument("--package", required=True, help="absolute run-package path (runs/run-N)")
    h.add_argument("--catalog-root", required=True)
    h.add_argument("--bindings", required=True)
    h.add_argument("--conduct", required=True)
    h.add_argument("--claude-md", required=True)
    h.add_argument("--budget-json", required=True)
    h.add_argument("--job-id", required=True, help="the arming marker's job-id")
    h.add_argument("--profile", required=True, help="the arming marker's spawn profile")
    h.add_argument("--note", help="free text written into the arming marker")
    g = h.add_mutually_exclusive_group(required=True)
    g.add_argument("--seat")
    g.add_argument("--workflow")
    i = h.add_mutually_exclusive_group(required=True)
    i.add_argument("--after")
    i.add_argument("--root", action="store_true")
    h.add_argument("--no-launch", action="store_true",
                   help="perform create and arm only; the launch act is withheld by the caller")
    h.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)
    payload = json.loads(sys.stdin.read() if args.request == "-"
                         else Path(args.request).read_text(encoding="utf-8"))
    try:
        if args.verb == "validate":
            out = validate(payload, goals_root=args.goals_root)
            print(json.dumps(out, indent=2))
            # The stated refusal ALSO goes to stderr, as text. The JSON carries it for a machine
            # caller; a human requester reading a terminal is answered here, and answering only in
            # a field of a JSON blob is how a stated refusal becomes a bare status in practice.
            if not out["accepted"]:
                print(out["stated-refusal"], file=sys.stderr)
            return 0 if out["accepted"] else 1
        out = handle(payload, args.goals_root, args.package, args.catalog_root, args.bindings,
                     args.conduct, args.claude_md, args.budget_json, args.job_id, args.profile,
                     seat=args.seat, workflow=args.workflow, after=args.after, root=args.root,
                     note=args.note, do_launch=not args.no_launch, dry_run=args.dry_run)
        print(json.dumps(out, indent=2))
        if out.get("stated-refusal"):
            print(out["stated-refusal"], file=sys.stderr)
        return 0 if out["outcome"] == "ACCEPTED" else 1
    except Refusal as exc:
        print(json.dumps({"ok": False, "refusal": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
