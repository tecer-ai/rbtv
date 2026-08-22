#!/usr/bin/env python3
"""goal_creation_request — THE ENTRY: a goal-creation request arrives here, is validated against
the landed request schema, and is discharged as two ordered acts — create -> launch.

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

ARMING IS RETIRED, AND THE CHAIN IS NOW create -> launch
--------------------------------------------------------
This file used to write `coordination/edge-fastpath.json` — the per-package marker that armed the
Python edge-runner's check-out fast path — importing `edge-runner-job.arm_path()` so that the
location had exactly one computer. Both the marker and that engine are GONE
(`1-projects/rbtv-sb-merge-refactor-core-build/build/one-readiness-predicate.md`, owner-ruled
2026-08-11): readiness is recomputed from disk every cadence by the daemon's seeding pass through
`coordinate ready-seats --json`, so nothing is armed per package any more. See § 3 below.

THE RULED NAME
--------------
The creation act invokes **`scaffold-seats`**, the ruled name, resolved on PATH. It never invokes
the script path `materialize-seats.py` behind it, and it never hand-rolls a spawn: `d-materialize-term`
and `p-the-scaffold-seats-fix-is-NOT-a-text-alignment` bind — invoke the ruled name, do not align
text to whatever a call site happens to say.

A GOAL CREATED HERE IS BORN INTO A LANE (task **7.777**, owner-ruled). What decides whether a goal
advances is its LANE ASSIGNMENT (`<goal>/execution-lane`), and since this row landed the request
carries it as a REQUIRED field: creation REFUSES without one, and the DAEMON writes the marker —
in the very process that already writes `goal.md`, through `goal_cli.py scaffold --lane`.

⚠ THE ROUTE IS THE POINT, NOT A CONVENIENCE. The channel master CANNOT write `<goal>/execution-lane`
itself. Its `goals-write` cage grant is resolved as a SPAWN-TIME SNAPSHOT of the goals that had a
live, verified tmux occupant when the sandbox was composed, so a goal created DURING a sitting is
never in that snapshot and the master's write dies on `EROFS`. Routing the lane through the request
means the master needs no folder access at all.

⚠ NO DERIVATION LADDER, DELIBERATELY. `execution-mode` below has a three-tier resolve (request →
goal-kind → workflow default); this field has none. The owner ruled the assignment EXPLICIT: a
requester who does not say which lane runs the goal is REFUSED, never defaulted, because the two
lanes are "the daemon runs this unattended" and "you run it when you type `rbtv run`" and silently
picking one for a requester who did not choose is how a goal ends up in neither.

THE REFUSAL ARM (task **7.206**, design id `E11`, arm **a**)
------------------------------------------------------------
The refusal is raised HERE, at the entry — the refusing site and the site that answers the requester
are the same file, so ONE observable carries the whole criterion and no propagation question arises.
A refusal therefore names three things at the requester's surface, never a bare status: the MEMBER of
E3's closed reject set that matched, the field or shape it rejects, and what held instead.

The sixteen members and their `S -> P -> V` class-stop report order are the landed schema's
(§6.1, §6.2) and are CONSUMED here, never forked: this file mints no member and re-orders nothing.
The fourteenth (`V7`) was AMENDED INTO THE SCHEMA before it was implemented, by the clause the
capability doc now carries — see the REJECT_SET header for where that clause lives and why it lives
there. Where §6.2 stops evaluation at the first class in which any member matched, this validator
RETURNS there — it does not evaluate a later class and then filter, because `V2`/`V3` reach the
filesystem and "evaluated but suppressed" is not what the schema says.

`goal-kind` IS VALIDATED AND NOW PERSISTED — the carrier is `goal.md` FRONTMATTER (owner ruling
`d-owner-batch1` (2), 2026-08-08). The structural convention this file once declined to invent has
been ruled, so the creation verb carries `--kind` and this handler FORWARDS the value it validated
instead of dropping it. Named in the result as `kind-carrier: goal.md frontmatter`.

⚠ The two halves of "optional" are not the same half. In THIS request schema `goal-kind` stays
REQUIRED (§1: four required fields; `P4` refuses an absent one) — a requester asking for a goal
must say which kind it wants. What the ruling made optional is the FRONTMATTER KEY, so that goals
scaffolded before the field existed stay valid and read as `interactive`. Relaxing `P4` on the
strength of the frontmatter default would be reading a ruling about stored goals as a ruling about
incoming requests, and would silently drop a field the requester is answerable for.
"""

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------- the schema

# From the landed request-schema artifact, §1 — ONE field set, both goal kinds, EIGHT fields:
# five required plus three optional. The set is CLOSED: a name outside it is a refusal, never a
# passthrough, because §1's table IS the whole field set.
#
# `execution-lane` joined the REQUIRED half on 2026-08-12 (task 7.777, owner-ruled). It is required
# and not optional for the reason the header states in full: there is no defensible default between
# `daemon` and `console`, so the requester answers or is refused.
REQUIRED_FIELDS = ("goal-name", "goal-type", "goal-contract", "goal-kind", "execution-lane")
# `execution-mode` joined `due-date` here on 2026-08-10 (owner ruling, § the execution-mode
# lifecycle below). OPTIONAL is the whole point: a requester who says nothing gets the WORKFLOW's
# default, resolved from the workflow's own scaffolding — which is a better answer than any
# default this layer could invent, and is why the field was not made required.
#
# ⚠ `launch-profile` IS DELETED FROM THE REQUEST SHAPE (`#d-abolish-profile-names`, 2026-08-12).
# It named the FALLBACK launch profile for seats declaring no cast of their own; the fallback is
# abolished and `rbtv-goal scaffold` no longer has a `--profile` flag to forward it to. A request
# still carrying the field is refused as an unknown field, which is the honest answer: the value
# would have been silently dropped otherwise, and the requester would believe it had chosen
# something. What a seat runs on is its CAST, in the workflow's bindings sheet, and is not a
# goal-creation input at all.
OPTIONAL_FIELDS = ("due-date", "execution-mode")
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# §1.1 — the same expression the creation verb enforces (`goal_cli.py#GOAL_NAME_RE`), not a second
# spelling of it. Kept as a literal here on purpose: importing it would couple the request layer's
# contract to a tool's internals, and the schema names the constraint, not the import.
#
# The anchor is the SYMBOL, not a line number. It read `goal_cli.py:36` until 2026-08-08, by which
# time the definition had moved to line 42 — a citation that drifts silently is worse than none,
# because it still looks precise. Symbol anchors are already this repo's idiom for the same reason
# (`seat-folder.js` cites `goal_cli.py#GOAL_KINDS`).
GOAL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GOAL_TYPES = ("one-shot", "recurring")
# §1.4 — the enum is now closed by CODE as well as by text: `goal_cli.py#GOAL_KINDS` owns it on the
# creation-verb side (it landed there with the `--kind` flag, d-owner-batch1 (2)). This copy stays a
# literal for the same reason GOAL_NAME_RE does — deliberate duplication of a contract constant, not
# drift — so the request layer's schema does not become importable from a tool's internals.
GOAL_KINDS = ("interactive", "non-interactive")
# Named off the tuple rather than re-spelled: `resolve_execution_mode` derives a mode from this
# one member (owner ruling 2026-08-11, task 7.753), and a second literal is a second thing to
# keep in step with the enum. V6 already refuses anything outside GOAL_KINDS, so the value this
# compares against and the value the schema admits are the same object.
NON_INTERACTIVE_KIND = GOAL_KINDS[1]

# ── `execution-mode`: the OPTIONAL sixth field (owner ruling 2026-08-10) ───────────────────────
#
# The per-goal OWNER-CONTACT policy — registry concept `execution mode`, whose values are
# `interactive | autonomous` with ABSENT reading `autonomous`. Until today no creation path wrote
# `.rbtv/goals/<goal>/execution-mode` at all, so every daemon-created goal was born mode-less and
# the ferry could only read the model's default back. The owner ruled the lifecycle: a workflow
# declares a default, creation WRITES it, and a requester may override per goal.
#
# ⚠ THE VOCABULARY CLASH IS REAL AND IS NOT A TYPO. `goal-kind`'s `interactive` and this axis's
# `interactive` are DIFFERENT AXES that share a word (`concepts/execution-mode.md` § v1 mechanism,
# vocabulary guard; open issue F-96). `goal-kind` is `interactive | non-interactive`; this is
# `interactive | autonomous`. Neither enum may be written in terms of the other.
#
# THE ENUM IS ENFORCED AT TWO SITES, AND THAT IS DELIBERATE (task 7.631, 2026-08-10).
#
#   · `V7` in `validate`, class V — the schema's fourteenth member. It exists because `validate`
#     is the requester's PRE-FLIGHT and performs no act: while the enum was enforced only below,
#     `validate` exited 0 on a payload `handle` then refused (measured, and recorded in the
#     capability doc's reject-set decision), and a caged requester stages on that verdict.
#   · the typed `Refusal` raised by `resolve_execution_mode` BEFORE the scaffold act — the same
#     shape `--kind` has at `goal_cli.py#cmd_scaffold`, and, like it, it leaves no goal directory
#     behind. It STAYS after V7 landed: `scaffold_goal` is reachable as a function and `handle`'s
#     callers may skip `validate`, so the ACTING path keeps its own refusal.
#
# The two answer different questions — "may I send this?" and "may I act on this?" — and both read
# this one constant, so neither can drift to a different enum.
EXECUTION_MODES = ("interactive", "autonomous")
EXECUTION_MODE_DEFAULT = "autonomous"
DECLARED_MODE_RE = re.compile(r"^default-execution-mode:\s*(\S+)\s*$", re.M)
INTERACTIVE_MODALITY = "interactive"

# ── `execution-lane`: the REQUIRED sixth field (task 7.777, owner-ruled 2026-08-12) ────────────
#
# The two lanes, in the vocabulary the registry minted (`concepts/lane-assignment.md`): `daemon` —
# the daemon's watch pass picks the goal up and seeds it unattended; `console` — nothing runs until
# a human types `rbtv run`. The literals are duplicated from `goal_cli.py#LANES` on the SAME terms
# as `GOAL_KINDS` above: a contract constant, deliberately not an import, so the request layer's
# schema does not become reachable through a tool's internals.
#
# ⚠ ENFORCED AT TWO SITES, exactly as `EXECUTION_MODES` is and for the same two reasons: `V8` in
# `validate` answers "may I send this?" for a caged requester staging on a pre-flight verdict, and
# the typed `Refusal` in `resolve_execution_lane` answers "may I act on this?" for the callers that
# reach `scaffold_goal` as a function without going through `validate`. Both read this one constant.
EXECUTION_LANES = ("daemon", "console")

RULED_LAUNCH_NAME = "scaffold-seats"

# ------------------------------------------- the CLOSED reject set (E3's §6.1)
#
# SIXTEEN members, id -> (member name, the field or shape it rejects). The set is CLOSED: these are
# the members and no others, and growing it requires adding a CLAUSE to the schema's §1 FIRST. This
# file therefore mints nothing — a condition with no member here is a condition this schema ADMITS,
# and inventing a member with no clause behind it would re-open a closed half nobody reviewed.
#
# WHERE THE SCHEMA LIVES NOW, AND WHY IT MOVED (task 7.631, 2026-08-10). The set was specified at
#   .rbtv/goals/build-core-daemon-mvp/runs/run-3/planning/briefing-master-request-launch-entry/
#   request-schema-goal-creation.md  — §1 FIVE fields, §6.1 THIRTEEN members
# and that path is inside a run compartment the owner ruled READ-ONLY ARCHAEOLOGY: never migrated,
# never edited (`.rbtv/goals/CLAUDE.md`). The sixth field's clause therefore could not be written
# into it. It was written into the capability's own doc instead — which is what `REJECT_SET_SOURCE`
# names below and what every refusal cites: EIGHT fields, SIXTEEN members — `V7` generated from
# §1.7, and `P5`/`V8` from §1.8 (task 7.777's required `execution-lane`), all three by §6.0's own
# generation rule (one member per presence requirement and one per constraint clause). The path above is left unedited
# and is cited by NO refusal; it is the historical record of §1 as 7.197 landed it and §6.1 as
# 7.198 landed it, and the live clause names it as superseded from the other side.
REJECT_SET_SOURCE = ("ignite/capabilities/goal-creation-request/goal-creation-request.md "
                     "§ The request schema it validates against — THE LIVE CLAUSE")
REJECT_SET = {
    "S1": ("payload-not-a-field-mapping", "shape: the payload as a whole"),
    # ⚠ The member NAME still says "the five" and is left BYTE-VERBATIM from the schema: a member
    # id-to-name mapping two implementers must report identically is not this file's to reword.
    # The set it checks is `ALL_FIELDS`, which is SIX since `execution-mode` landed — the check
    # message prints the live set, so a reader is never told the wrong one.
    "S2": ("field-name-not-in-the-five", "shape: the payload's set of field names"),
    "S3": ("field-value-not-a-single-value", "shape: the value of one named field"),
    "P1": ("goal-name-absent", "field goal-name"),
    "P2": ("goal-type-absent", "field goal-type"),
    "P3": ("goal-contract-absent", "field goal-contract"),
    "P4": ("goal-kind-absent", "field goal-kind"),
    # The FIFTEENTH, amended in with the required sixth field (task 7.777). A REQUIRED field
    # contributes a presence member, exactly as `P1`..`P4` do — no exception was minted for it.
    "P5": ("execution-lane-absent", "field execution-lane"),
    "V1": ("goal-name-not-kebab-case", "field goal-name"),
    "V2": ("goal-name-taken-in-resolved-root", "field goal-name"),
    "V3": ("goal-name-declared-by-another-goal", "field goal-name"),
    "V4": ("goal-type-not-in-enum", "field goal-type"),
    "V5": ("goal-contract-empty-after-strip", "field goal-contract"),
    "V6": ("goal-kind-not-in-enum", "field goal-kind"),
    # The FOURTEENTH, amended in by the live clause's §1.7 (task 7.631). Optional fields contribute
    # no PRESENCE member — absence is legal — but a constraint clause contributes its negation
    # whatever the field's requiredness, exactly as `V4`/`V6` do. `due-date` is not the precedent:
    # it contributes none because §3.1 records its TYPE as UNRESOLVED (§6.3), and this field's type
    # is two literals.
    "V7": ("execution-mode-not-in-enum", "field execution-mode"),
    # The SIXTEENTH, the negation of the required sixth field's constraint clause (task 7.777) —
    # generated by §6.0's own rule, one member per constraint clause, exactly as `V4`/`V6`/`V7`.
    "V8": ("execution-lane-not-in-enum", "field execution-lane"),
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

class Refusal(Exception):
    """A refusal with a reason. Never a crash: the caller gets a verdict it can act on."""


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
            # Was hardcoded "NONE" while no carrier was ruled. d-owner-batch1 (2) ruled one, so
            # this names it — the requester's surface reports WHERE the kind it supplied went.
            "kind-carrier": "goal.md frontmatter"}


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
                          ("goal-contract", "P3"), ("goal-kind", "P4"),
                          ("execution-lane", "P5")):
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

    # REQUIRED, so it is present by the time class V runs — `P5` already refused an absent one and
    # `S3` an arity-broken one, and each class returns before this point.
    checked.append({"field": "execution-lane", "check": f"V8 · enum {list(EXECUTION_LANES)}"})
    if payload["execution-lane"] not in EXECUTION_LANES:
        refuse("V8", f"{payload['execution-lane']!r} is not exactly one of "
                     f"{list(EXECUTION_LANES)}. This field decides WHO runs the goal — the daemon "
                     "unattended, or a human typing `rbtv run` — and there is no default between "
                     "them, which is why it refuses rather than falling back")

    # `due-date` is optional and its TYPE is unresolved in the schema, which records the gap rather
    # than guessing. So no value of it is rejected here — §6.3's ZERO value members, an empty slice
    # that is a decided closure and not a hole. Naming it as checked is what makes the slice visible.
    checked.append({"field": "due-date",
                    "check": "optional; type UNRESOLVED in the schema — no member rejects any value"})

    # `execution-mode` is OPTIONAL, so it has no presence member — but it does have a constraint
    # clause (§1.7), so it has that clause's negation: `V7`. Checked only when PRESENT and
    # non-null: an absent optional field is legal, and `None` is the requester spelling "unset",
    # which `resolve_execution_mode` reads the same way. Naming the field as checked either way is
    # what stops a reader concluding the value went unexamined.
    checked.append({"field": "execution-mode",
                    "check": f"optional; V7 · enum {list(EXECUTION_MODES)} when present"})
    if payload.get("execution-mode") is not None:
        if payload["execution-mode"] not in EXECUTION_MODES:
            refuse("V7", f"{payload['execution-mode']!r} is not exactly one of "
                         f"{list(EXECUTION_MODES)}. This field carries the per-goal owner-contact "
                         "policy, and a value the control plane cannot read would silently make "
                         "the goal autonomous")

    return _verdict(checked, refusals, "S,P,V")


# ------------------------------------------------- 1b · THE EXECUTION MODE (owner ruling 2026-08-10)

def workflow_default_execution_mode(catalog_root, workflow):
    """The workflow's DEFAULT execution mode: declared, else derived. Returns (mode, source).

    Two rungs, in this order and no other:

      1. DECLARED — `default-execution-mode:` in the workflow definition's frontmatter
         (`<catalog-root>/<component>/workflows/<W>/workflow.md`). The declaration exists for the
         case derivation CANNOT express: a workflow that HAS interactive seats but that the owner
         wants defaulting autonomous. Derivation would say `interactive` there and be wrong, and
         there is no way to say "no, autonomous" in a Modality column.
      2. DERIVED from the manifest — any row whose Modality reads `interactive` -> `interactive`;
         none -> `autonomous`. This is a floor, not a guess: a workflow with an interactive seat
         has a seat whose whole job is talking to the owner, and an autonomous default would gag
         it silently.

    The manifest is resolved by the SAME glob `materialize-seats.py#resolve_added` uses —
    `<catalog-root>/*/workflows/<W>/<W>.csv` — so a workflow this function cannot find is a
    workflow materialization cannot find either. An unresolvable or ambiguous workflow returns the
    model's own default with the reason NAMED, never a silent `autonomous`: the caller writes the
    mode either way (a goal is never born without the file), and the source string is what tells a
    reader afterwards whether the value was resolved or fallen back to.
    """
    if not catalog_root or not workflow:
        return EXECUTION_MODE_DEFAULT, "no workflow named at creation — the model's own default"
    manifests = sorted(Path(catalog_root).glob(f"*/workflows/{workflow}/{workflow}.csv"))
    if len(manifests) != 1:
        return EXECUTION_MODE_DEFAULT, (
            f"{workflow!r} resolves to {len(manifests)} manifests under {catalog_root} — "
            "the model's own default")
    manifest = manifests[0]

    definition = manifest.parent / "workflow.md"
    if definition.is_file():
        head = definition.read_text(encoding="utf-8", errors="replace")
        m = DECLARED_MODE_RE.search(head)
        if m:
            declared = m.group(1)
            if declared not in EXECUTION_MODES:
                raise Refusal(
                    f"{definition}: declares default-execution-mode: {declared!r}, which is not "
                    f"one of {list(EXECUTION_MODES)}. A malformed declaration is refused rather "
                    "than fallen back over — falling back would create goals on a default the "
                    "workflow's own scaffolding says is not its default.")
            return declared, f"declared at {definition}"

    # DERIVED. The Modality column is the manifest's 4th (`Seat/workflow,after,i/o,Modality`);
    # read by NAME through csv.DictReader so a column added left of it never shifts the read.
    with manifest.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    interactive = [r.get("Seat/workflow") for r in rows
                   if (r.get("Modality") or "").strip().lower() == INTERACTIVE_MODALITY]
    if interactive:
        return "interactive", (f"derived from {manifest}: interactive seat(s) "
                               f"{sorted(s for s in interactive if s)}")
    return "autonomous", f"derived from {manifest}: no interactive seat"


def resolve_execution_mode(request, catalog_root=None, workflow=None):
    """The mode a goal is BORN with: the request's own value, else a non-interactive goal-kind,
    else the workflow's default (the rung comment below states the precedence in full).

    Returns (mode, source). Raises `Refusal` on a payload value outside the enum — see the
    EXECUTION_MODES header for why this is a refusal HERE rather than a reject-set member.
    """
    if "execution-mode" in request and request["execution-mode"] is not None:
        asked = request["execution-mode"]
        if asked not in EXECUTION_MODES:
            raise Refusal(
                f"execution-mode {asked!r} is not one of {list(EXECUTION_MODES)}. REFUSED before "
                "any act: nothing was created. This field carries the per-goal owner-contact "
                "policy, and a value the control plane cannot read would silently make the goal "
                "autonomous — which is why it refuses instead of falling back to a default.")
        return asked, "the request payload"

    # THE GOAL-KIND RUNG (owner ruling 2026-08-11, task 7.753). Full precedence:
    #   1. the request's own `execution-mode` (above) — an explicit ask ALWAYS wins;
    #   2. `goal-kind: non-interactive` → `autonomous`, OVERRIDING the workflow default;
    #   3. the workflow default (declared, else derived from the manifest).
    #
    # ⚠ ONE-DIRECTIONAL, DELIBERATELY. `goal-kind: interactive` derives NOTHING and falls through
    # to (3): a goal nobody will sit with cannot be born waiting for an owner, but a goal someone
    # MAY sit with is not thereby a goal that must wait — that is the workflow's call, and the
    # manifest is what knows whether a seat is actually interactive. Reading the kind in both
    # directions would let a goal-kind silently overrule a workflow that declares its own default.
    #
    # ⚠ The two `interactive`s are DIFFERENT AXES sharing a word (see the EXECUTION_MODES header,
    # open issue F-96) — which is exactly why only the UNAMBIGUOUS member is read here.
    if request.get("goal-kind") == NON_INTERACTIVE_KIND:
        return "autonomous", f"goal-kind {NON_INTERACTIVE_KIND!r} (overrides the workflow default)"

    mode, source = workflow_default_execution_mode(catalog_root, workflow)
    return mode, f"the workflow default — {source}"


# ------------------------------------------------- 1c · THE EXECUTION LANE (task 7.777)

def resolve_execution_lane(request):
    """The lane a goal is BORN into: the request's own value, and NOTHING else. Returns the lane.

    ⚠ THERE IS NO LADDER HERE, and the flatness is the design. `resolve_execution_mode` above has
    three rungs because every rung has a defensible answer; this field has one, because the two
    lanes differ in WHO runs the goal and no layer below the requester knows that. An absent or
    unreadable value is a `Refusal` raised BEFORE any act — the ACTING-path twin of `P5`/`V8`, kept
    for the same reason `resolve_execution_mode`'s refusal is: `scaffold_goal` is reachable as a
    function and `handle`'s callers may skip `validate`.
    """
    lane = request.get("execution-lane")
    if lane is None:
        raise Refusal(
            "execution-lane is REQUIRED and the request carries none. REFUSED before any act: "
            "nothing was created. Pass 'daemon' if the daemon should run this goal unattended, or "
            f"'console' if a human runs it with `rbtv run`. One of {list(EXECUTION_LANES)} — there "
            "is no default between them, so this refuses rather than choosing for you.")
    if lane not in EXECUTION_LANES:
        raise Refusal(
            f"execution-lane {lane!r} is not one of {list(EXECUTION_LANES)}. REFUSED before any "
            "act: nothing was created. An unreadable lane marker resolves to `console` at every "
            "reader, so accepting this would silently park the goal in a lane the requester did "
            "not ask for.")
    return lane


# --------------------------------------------------------------- 2 · CREATE

def scaffold_goal(request, goals_root, dry_run=False, catalog_root=None, workflow=None):
    """SCAFFOLD — the goal folder and its contract, and NOTHING else.

    The first half of `create()` below, extracted (task C2) because the daemon-executed path needs
    the goal to EXIST without materializing its content: `scaffold-seats` has no create-only mode
    and would launch seats, which a scheduled workflow start is what queues instead. Extracted
    rather than copied — a second spelling of the `--kind` forwarding is exactly the drop
    `d-owner-batch1` (2) ruled a carrier for, and two spellings are two chances to drop it.

    Returns ONE step dict, or the skip record when the goal already resolves.
    """
    goal_cli = (Path(__file__).resolve().parents[2] / "goals-tree" / "tool" / "goal_cli.py")
    goal_dir = Path(goals_root) / request["goal-name"]

    # RESOLVED FIRST, BEFORE THE EXISTS CHECK AND BEFORE ANY WRITE (owner ruling 2026-08-10). A
    # request naming an unreadable mode is refused whatever else is true of the goals root — an
    # act performed on a refused request is the one thing the entry's ordering exists to prevent.
    mode, mode_source = resolve_execution_mode(request, catalog_root, workflow)
    # Same placement, same reason (task 7.777): a request naming no lane, or an unreadable one, is
    # refused before the exists check and before any write.
    lane = resolve_execution_lane(request)

    if goal_dir.exists():
        return {"step": "create-goal", "skipped": f"{goal_dir} already resolves"}

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
        # `--kind` is passed UNCONDITIONALLY, unlike `--due` below: `goal-kind` is a REQUIRED
        # request field (P4 refuses an absent one), so by the time this runs the value is
        # present and validated. Forwarding it is what stops the validated value being dropped
        # on the floor — the whole defect d-owner-batch1 (2) ruled a carrier for.
        cmd = [sys.executable, str(goal_cli), "scaffold", request["goal-name"],
               "--root", str(goals_root), "--type", request["goal-type"],
               "--kind", request["goal-kind"],
               # `--execution-mode` is passed UNCONDITIONALLY for the same reason `--kind` is,
               # arrived at from the other side: the field is OPTIONAL in the request, but the
               # RESOLVED value never is — an omitted field resolves to the workflow's default,
               # so there is always a word to forward. Omitting the flag here would let the
               # creation verb's own `autonomous` default silently overwrite an `interactive`
               # workflow default, which is exactly the drop this ruling closed.
               "--execution-mode", mode,
               # ⚠ THE WRITE THE REQUESTER COULD NOT MAKE (task 7.777). `--lane` is passed
               # UNCONDITIONALLY: the field is REQUIRED and `resolve_execution_lane` above has
               # already refused every payload that could not supply it, so there is always a word
               # to forward. This is the whole reason the lane travels as a request field — the
               # daemon writes `<goal>/execution-lane` inside the same process that writes
               # `goal.md`, so the channel master (whose `goals-write` grant is a spawn-time
               # snapshot that can never contain a goal created during its own sitting) needs no
               # access to the goal folder at all.
               "--lane", lane,
               "--contract", str(contract_file), "--json"]
        if request.get("due-date"):
            cmd += ["--due", request["due-date"]]
        step = _run(cmd, "create-goal", dry_run)
        # NAMED IN THE STEP so the requester's surface reports WHICH mode the goal was born with
        # and WHERE that value came from. A created goal whose mode nobody can attribute is the
        # state this whole lifecycle replaced.
        step["execution-mode"] = mode
        step["execution-mode-source"] = mode_source
        # Stamped beside them for the same reason, one rung shorter: the lane has exactly one
        # source, so it is named and no `-source` key is minted for a question with one answer.
        step["execution-lane"] = lane
        step["execution-lane-source"] = "the request payload (REQUIRED — no default, no derivation)"
        return step
    finally:
        contract_file.unlink(missing_ok=True)


def create(request, goals_root, package, catalog_root, bindings, claude_md, budget_json,
           seat=None, workflow=None, after=None, root=False, dry_run=False):
    """CREATE — the goal, then its working content, through the RULED NAME.

    Two invocations because the system splits them: `rbtv-goal scaffold` mints the goal folder and
    its contract; `scaffold-seats` materializes the working content INTO that folder. There is NO
    create-only mode on the second — it requires `--seat` or `--workflow` plus an explicit
    `--after|--root` — so this act NECESSARILY materializes at least one seat. That is a property
    of the only creation path in the system, not a choice this handler made.

    7.607 E2a: `package` IS THE GOAL DIRECTORY. The run package it used to name is extinguished
    (`decisions.md#d-runs-extinguished`); the goal folder is the package (design-lock item 8).
    """
    # `catalog_root` and `workflow` cross into the scaffold act SOLELY to resolve the execution
    # mode's workflow-level default (owner ruling 2026-08-10). A `--seat` creation names no
    # workflow, so `workflow` is None there and the resolution falls back with its reason named.
    steps = [scaffold_goal(request, goals_root, dry_run,
                           catalog_root=catalog_root, workflow=workflow)]


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
           "--bindings", str(bindings), "--claude-md", str(claude_md),
           # ⚠ 7.607 E2b: `--run-type` is GONE with the run register (design-lock item 8). It
           # named the `type` cell of a `runs.csv` row that is no longer written by anything.
           "--budget-json", str(budget_json), "--json"]
    cmd += ["--seat", seat] if seat else ["--workflow", workflow]
    cmd += ["--root"] if root else ["--after", after]
    steps.append(_run(cmd, "create-package", dry_run))
    return steps


# ------------------------------------------------------------------ 3 · (ARM — RETIRED)
#
# The chain was create -> arm -> launch. The ARM act wrote `coordination/edge-fastpath.json`, the
# per-package marker that armed the check-out fast path of the Python edge-runner.
#
# BOTH ARE GONE (`build/one-readiness-predicate.md`, owner-ruled 2026-08-11). Advancement is no
# longer armed per package and is no longer triggered by the check-out: the daemon's seeding pass
# recomputes readiness from disk every cadence through `coordinate ready-seats --json`, which is the
# ONE predicate. A goal therefore advances because it is ASSIGNED TO A LANE (`<goal>/execution-lane`),
# not because something wrote a marker into it at birth.
#
# ⚠ NOTHING REPLACES THIS STEP HERE. If a newly created goal does not advance, the question is its
# lane assignment, never a missing marker — and binding lane assignment to creation is deliberately
# NOT done yet (that design's § Out of scope).


# --------------------------------------------------------------- 4 · LAUNCH

def launch(package, only=None, dry_run=False):
    """LAUNCH — through the goal's own coordination CLI, which is the ONLY writer of a session row.

    `sessions.csv` is born HERE and not at creation: the creation path omits it deliberately, so
    the ruled goal-folder shape completes at this act. Its absence BEFORE this act is expected and
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


# ------------------------------------------------- 5 · SCAFFOLD (task C2; the QUEUE half deleted 7.778)

# The two subdirs the drain moves a request into. A processed request MUST leave the inbox: the
# tool is fired by a queue row and would otherwise re-process every request on every fire, where
# `V2`/`V3` (goal-name uniqueness) would refuse each one forever — a growing pile of refusals about
# work that already succeeded.
DONE_DIR = "done"
REFUSED_DIR = "refused"

# ── 7.607 E2a — `FRESH_RUN_ID` AND THE RUN-1 PACKAGE COMPOSITION ARE DELETED ───────────────────
#
# The package a fresh goal is born with is THE GOAL DIRECTORY ITSELF (design-lock item 8: "package
# = goal folder"). What died with the constant, stated because a reader of the old comment will
# come looking for it:
#
#   · the ordinal. `d-owner-planning-entry-0808` (3) had the scaffold act create `runs/run-1/` and
#     register it `state=open`. There is no ordinal to mint and no register to write into.
#   · the WHOLE-TOKEN constraint. The old comment's argument was that whole-token templating
#     "deliberately cannot compose `runs/run-N`", so a row queued at birth had to carry a
#     pre-composed path. The goal dir is composable from the goal name, and since 7.778 no row is
#     queued at birth at all, so the constraint has no subject on either side.
#   · ⚠ THE DEADLOCK (inventory #73). `scaffold_and_queue` never wrote an open row itself, but the
#     act it invoked did — `scaffold-seats` appended `state=open` to the goal's register, and the
#     start row this verb queued then met the one-live-run gate holding that very row. The gate is
#     already lease-founded (E1) and the register is gone, so the deadlock has no carrier left on
#     either side. THIS FILE WRITES NO OPEN ROW ANYWHERE, and none may be added.

# ── 7.778 — THE `start-workflow` DOOR THIS VERB USED TO ARM IS DELETED (owner-ruled 2026-08-12) ──
#
# This verb used to end by minting a `<goal>-workflow-start` job (`register-job`) and queueing it
# `--delay-seconds` out (`add-job`), which fired `workflow_launcher.py` to open the goal's room and
# launch its entry seat. All of it is GONE, and so is `workflow_launcher.py` itself.
#
# WHAT OPENS THE ENTRY SEAT NOW: the LANE. A goal is born with `<goal>/execution-lane` (task 7.777,
# above), and the daemon's watch pass reads that marker every cadence and seeds the goals assigned
# to `daemon` — one readiness predicate recomputed from disk, rather than a one-shot row planted at
# birth that had to guess how long to wait. A `console` goal opens when a human types `rbtv run`.
#
# ⚠ WHAT IS **NOT** DELETED: the `start-workflow` ACTION TYPE. It is a generic dispatch category
# with live consumers (`server/ticker/one-live-run.js`, `server/ticker/goal-channel-start.js` — one
# of them a run-start safety gate). This row deleted the DOOR that armed it from goal creation,
# never the category.


def scaffold_and_queue(inbox, goals_root, workflow, catalog_root, bindings,
                       claude_md, budget_json,
                       ignite_bin="ignite", dry_run=False):
    """SCAFFOLD — the daemon-executed half of a caged requester's ask (task C2).

    ⚠ THE NAME STILL SAYS `and-queue` AND IT NO LONGER QUEUES ANYTHING (7.778). The verb name is
    the tool's CLI contract and the `tools:` key in `config/spawn-profiles.yaml` that fires it, so
    renaming it is a separate act with its own call sites; what it DOES is stated here.

    THE MEASUREMENT THIS SHAPE IS BUILT ON (evidence/c2/, probe-c2.js, 2026-08-08). Under the
    SHIPPED seat cage a channel-master-shaped service seat CANNOT create a goal directory
    (`mkdir: Read-only file system`, proven by the target's absent bytes read from OUTSIDE the
    cage) but CAN write inside its own seat folder. At the gateway, `register-job` is REFUSED to a
    `bridge` token and allowed to `owner`/`agent`, while `enqueue-job` is allowed to ALL THREE
    kinds — it carries no authz gate at all.

    So the transport is split, and neither half is a preference:
      · the PAYLOAD is FILE-STAGED into the requester's own seat folder, because `fire-tool`'s argv
        is static (only `workdir` crosses from a queue row) and there is no gateway verb that
        carries a request body to a fired tool;
      · the TRIGGER is the gateway verb `enqueue-job`, because that is the one door open to every
        sender kind — the wire therefore works even if the channel master presents a bridge token.

    This function is the daemon side of that split: it drains the staged inbox, and for each
    accepted request it scaffolds the goal — the write the requester could not make, INCLUDING the
    goal's lane marker (task 7.777). It QUEUES NOTHING and LAUNCHES NOTHING: the workflow-start row
    it used to plant is deleted (7.778, § above) and `launch()` is the entry's other act, which
    stays out of this path deliberately. What advances the goal from here is its LANE.

    ⚑ VALIDATION STRICTLY PRECEDES THE SCAFFOLD. A malformed or refused payload must leave no goal
    directory behind, so parse and `validate()` both run before `scaffold_goal` is reached.
    """
    inbox = Path(inbox)
    results = []
    if not inbox.is_dir():
        raise Refusal(f"the staged inbox {inbox} does not resolve to a directory — nothing to drain")

    # ⚠ THE INBOX AND ITS SETTLE TARGETS MUST BE REAL DIRECTORIES, AND THIS GUARD IS HERE BECAUSE
    # THE ESCAPE WAS MEASURED (C2 review, 2026-08-08). The inbox lives INSIDE the requester's own
    # seat folder — that is the whole transport — so the requester can pre-create `done/` or
    # `refused/` as a SYMLINK. `mkdir(exist_ok=True)` ACCEPTS a symlink-to-directory (`is_dir()`
    # follows it) and `Path.replace` follows it too, so the daemon then writes the staged request
    # AND its `.refusal.json` wherever the link points, with the DAEMON's uid and outside the cage:
    # requester-chosen content at a requester-chosen absolute path. Refused for the WHOLE fire and
    # not per request — a symlinked settle target is tampering with the transport, not a bad ask.
    # Residual, stated rather than left to be found: this is a check, so a requester that swaps the
    # directory for a symlink between here and the move still wins that race. Closing it needs
    # dir-fd-relative moves; the check is what stops the standing, un-raced case.
    for candidate in (inbox, inbox / DONE_DIR, inbox / REFUSED_DIR):
        if candidate.is_symlink():
            raise Refusal(
                f"{candidate} is a symlink, and this verb refuses to drain through one. The "
                "requester owns this folder, so a symlinked inbox or settle target relocates every "
                "write made here outside the cage. NOTHING was drained; replace it with a real "
                "directory.")

    def settle(src, verdict, record):
        """Move the request out of the inbox and record where it went."""
        record["request-file"] = str(src)
        record["outcome"] = verdict
        if dry_run:
            record["moved-to"] = None
            return record
        dest_dir = inbox / (DONE_DIR if verdict == "ACCEPTED" else REFUSED_DIR)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        if dest.exists():
            # A colliding settled name is NOT a reason to raise: the requester chooses these names
            # and a plain retry of a refused request re-stages the same one. Uniquify — clobbering
            # would destroy the earlier refusal record the requester is meant to read, and raising
            # would leave the request in the inbox for the next fire to trip over again.
            dest = dest_dir / f"{src.name}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
        src.replace(dest)
        record["moved-to"] = str(dest)
        if verdict != "ACCEPTED":
            # The refusal is written where the requester can read it — the same folder it staged
            # into. A refusal a caged requester cannot see is a silent drop.
            dest.with_suffix(".refusal.json").write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return record

    # ⚠ THE REFUSAL ARM IS THE WHOLE PER-REQUEST BODY, NOT THE READ, AND THAT IS A FIX RATHER THAN
    # A PREFERENCE (C2 review, 2026-08-08). `main()` already states the property this loop is
    # supposed to have — "an unreadable file refuses that ONE request instead of killing the whole
    # fire" — but only `JSONDecodeError`/`UnicodeDecodeError` was caught, and THREE
    # requester-reachable inputs raised straight past it, each measured:
    #   · a DIRECTORY named `*.json` (the requester can `mkdir` in its own seat folder)
    #     -> `IsADirectoryError` at the read;
    #   · an unreadable, dangling or looping entry -> another `OSError` at the same read;
    #   · a schema-LEGAL non-string `due-date` — §6.3 gives it ZERO value members on purpose —
    #     which reaches subprocess argv as a non-str -> `TypeError`, well past validation.
    # Every one killed the fire with a traceback, and because the offender never left the inbox it
    # killed EVERY LATER FIRE TOO: one `mkdir` permanently denies the surface, and every request
    # sorted after it is never processed. What may refuse ONE request is decided by the BLAST
    # RADIUS, never by the exception class someone anticipated — so the catch is broad and the
    # settle is the same one the designed arms use, which is what gets the offender OUT of the
    # inbox and puts a readable refusal beside it.
    for src in sorted(inbox.glob("*.json")):
        payload = None
        try:
            payload = json.loads(src.read_text(encoding="utf-8"))

            verdict = validate(payload, goals_root=goals_root)
            if not verdict["accepted"]:
                # 7.550 (owner ruling `d-owner-seven-smalls-0808`, knowingly against the presented
                # recommendation): a V2 refusal — the name is TAKEN — DISCLOSES the state of the
                # directory it collided with, on the same keys the R8b failure arm below uses. An
                # operator reading a bare "already resolves" cannot tell a HEALTHY goal from an
                # ORPHAN a failed fire left behind, and the two need opposite actions (pick another
                # name / clean up and retry).
                #
                # THE SIGNAL IS `seats/`, and it is read off THIS FILE'S OWN CREATION PATH: `create`
                # scaffolds the goal folder and then NECESSARILY materializes at least one seat
                # ("There is NO create-only mode on the second"), so a goal dir holding no seat is
                # one that never got past its first step. NOT a run package — the run layer is
                # extinguished (`decisions.md#d-runs-extinguished`) and a goal's content sits
                # directly under the goal folder now. Deliberately a count and nothing more: this
                # is a disclosure, not an orphan-detection feature.
                taken = payload.get("goal-name") if isinstance(payload, dict) else None
                hit = (Path(goals_root) / taken) if (
                    goals_root is not None and isinstance(taken, str)
                    and any(r["member"] == "V2" for r in verdict["refusals"])) else None
                results.append(settle(src, "REFUSED", {
                    "stated-refusal": verdict["stated-refusal"],
                    "refusal-site": verdict["refusal-site"],
                    "refusals": verdict["refusals"],
                    "classes-evaluated": verdict["classes-evaluated"],
                    "scaffolded": False,
                    **({"goal-name": taken,
                        "goal-dir": str(hit),
                        "goal-exists": hit.is_dir(),
                        "goal-seats": len(list((hit / "seats").iterdir()))
                                      if (hit / "seats").is_dir() else 0}
                       if hit is not None else {}),
                }))
                continue

            goal = payload["goal-name"]
            goal_dir = Path(goals_root) / goal
            # 7.607 E2a — THE PACKAGE IS THE GOAL DIRECTORY (design-lock item 8). No ordinal, no
            # compartment, and NO OPEN ROW: this verb writes none, and the act it invokes has no
            # register left to append to. That is the deadlock site (#73) ceasing to exist rather
            # than being worked around — the queued start now meets a lease-founded gate that reads
            # live evidence, and a fresh goal has no room, so its start ADMITS.
            package = goal_dir

            steps = create(payload, goals_root, package, catalog_root, bindings,
                           claude_md, budget_json,
                           workflow=workflow, root=True, dry_run=dry_run)

            # NO ROW IS QUEUED HERE ANY MORE (7.778). The `register-job` + `add-job` pair that
            # minted `<goal>-workflow-start` and scheduled it `--delay-seconds` out is DELETED with
            # the door it armed; the goal's lane marker (written by the scaffold above) is what the
            # daemon's watch pass reads to seed it.
            #
            # Room selfheal is NOT armed here any more (retire-health, 2026-08-20): the
            # per-goal reconciliation loop (engine/reconcile.js, D1/D15) detects a dead or
            # empty room on every pass and shells `jobs/recover-room.py` itself. No
            # per-goal job to register, so nothing to arm at creation.

            failed = [s for s in steps if s.get("rc", 0) != 0]
            results.append(settle(src, "REFUSED" if failed else "ACCEPTED", {
                "goal-name": goal,
                "goal-dir": str(goal_dir),
                "goal-exists": goal_dir.is_dir(),
                # The package is disclosed on the SAME terms as the goal dir — and it now IS the
                # goal dir. Kept as its own pair of keys rather than folded into `goal-dir`: a
                # consumer reading the record should see WHAT WAS PASSED as `--package`, and a
                # record that silently stops naming it hides the very field a partial state is
                # diagnosed from.
                "package": str(package),
                "package-exists": package.is_dir(),
                "workflow": workflow,
                "steps": steps,
                "scaffolded": any(s.get("step") == "create-goal" and s.get("rc", 0) == 0
                                  for s in steps),
                "stated-refusal": (f"{failed[0]['step']} failed (rc={failed[0]['rc']}): "
                                   f"{(failed[0].get('stderr') or failed[0].get('stdout') or '').strip()[-800:]}")
                                  if failed else None,
            }))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            results.append(settle(src, "REFUSED", {
                "stated-refusal": f"the staged request is not readable JSON: {exc}. "
                                  "Nothing was created: the payload is parsed before any act.",
                "refusal-site": "scaffold-and-queue · parse",
                "scaffolded": False,
            }))
        except Exception as exc:
            # The goal dir is named when it CAN be named, so an orphan left by a mid-request failure
            # is findable from this record rather than only from the goals root. `scaffolded` is
            # `null`, not `false`: this arm cannot know how far the request got, and reporting a
            # confident `false` over an unknown is how an orphan becomes invisible.
            name = payload.get("goal-name") if isinstance(payload, dict) else None
            named = isinstance(name, str) and bool(GOAL_NAME_RE.match(name))
            results.append(settle(src, "REFUSED", {
                "stated-refusal": f"the staged request could not be processed: "
                                  f"{type(exc).__name__}: {exc}. The fire continued: this refusal "
                                  "is scoped to THIS request, and the goal directory below (when "
                                  "named) is where to look for a partial scaffold.",
                "refusal-site": "scaffold-and-queue · unhandled",
                "goal-name": name if named else None,
                "goal-dir": str(Path(goals_root) / name) if named else None,
                "goal-exists": (Path(goals_root) / name).is_dir() if named else None,
                "scaffolded": None,
            }))

    accepted = [r for r in results if r["outcome"] == "ACCEPTED"]
    return {
        "outcome": "ACCEPTED" if results and len(accepted) == len(results) else
                   ("EMPTY" if not results else "REFUSED"),
        "inbox": str(inbox),
        "drained": len(results),
        "accepted": len(accepted),
        "refused": len(results) - len(accepted),
        "requests": results,
    }


def _run(cmd, step, dry_run):
    if dry_run:
        return {"step": step, "dry-run": True, "argv": cmd}
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {"step": step, "argv": cmd, "rc": proc.returncode,
            "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}


# ----------------------------------------------------------------- the entry

def handle(request, goals_root, package, catalog_root, bindings, claude_md, budget_json,
           seat=None, workflow=None, after=None, root=False,
           do_launch=True, dry_run=False):
    """The entry: validate, then create -> launch, in that order and once.

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
        request, goals_root, package, catalog_root, bindings, claude_md, budget_json,
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
        result["acts"]["launch"] = {"step": "launch", "performed": False,
                                    "why": "the create act failed"}
        return result

    # The ARM act stood here and is RETIRED (§ 3 above). The chain is create -> launch. The
    # fail-closed guard above is UNCHANGED and still load-bearing: a later act never runs on an
    # earlier act's failure.
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
        description="The goal-creation request entry: validate a request, then create -> launch.")
    sub = p.add_subparsers(dest="verb", required=True)

    v = sub.add_parser("validate", help="validate a request payload; perform no act")
    v.add_argument("request", help="JSON file carrying the request payload, or - for stdin")
    v.add_argument("--goals-root", help="goals root the uniqueness checks resolve against")

    h = sub.add_parser("handle", help="validate, then create -> launch")
    h.add_argument("request", help="JSON file carrying the request payload, or - for stdin")
    h.add_argument("--goals-root", required=True)
    h.add_argument("--package", required=True,
                   help="absolute package path — since 7.607 this IS the goal folder "
                        "(<goals-root>/<goal>/); the runs/run-N compartment is extinguished")
    h.add_argument("--catalog-root", required=True)
    h.add_argument("--bindings", required=True)
    h.add_argument("--claude-md", required=True)
    h.add_argument("--budget-json", required=True)
    g = h.add_mutually_exclusive_group(required=True)
    g.add_argument("--seat")
    g.add_argument("--workflow")
    i = h.add_mutually_exclusive_group(required=True)
    i.add_argument("--after")
    i.add_argument("--root", action="store_true")
    h.add_argument("--no-launch", action="store_true",
                   help="perform create only; the launch act is withheld by the caller")
    h.add_argument("--dry-run", action="store_true")

    # Task C2 — the DAEMON-EXECUTED verb. It takes an inbox DIRECTORY, never a single request
    # path: `fire-tool`'s argv is static, so one fixed argument must serve every request, and a
    # drained directory is the only shape that does. See scaffold_and_queue's docstring for the
    # measurements that settled this.
    q = sub.add_parser("scaffold-and-queue",
                       help="drain a staged request inbox: scaffold each goal into its declared "
                            "lane (the name's `-and-queue` half is historical — 7.778 deleted the "
                            "workflow-start row this verb used to plant)")
    q.add_argument("--inbox", required=True,
                   help="directory the requester stages request JSON into (its own seat folder)")
    q.add_argument("--goals-root", required=True)
    q.add_argument("--workflow", required=True,
                   help="the workflow the created goal is materialized with (`scaffold-seats "
                        "--workflow`). Since 7.778 it starts nothing by itself — the goal's LANE "
                        "does")
    # ⚠ THE BASE INPUTS OF A CREATED RUN PACKAGE, ALL REQUIRED, NONE DEFAULTED (task C5E).
    # `scaffold-seats` REFUSES `create-inputs-missing` without the last two and states why:
    # "this command never invents run conventions and never defaults a floor". Those base texts are
    # the goal-generic STARTER SET the owner authored and approved for exactly this path
    # (`d-owner-starter-set-approved-0808`), shipped at `ignite/team-kit/starter-set/`. They are
    # named as PATHS here rather than resolved relative to this file: a default would make this tool
    # the author of a run's constitution, which is the one thing that refusal exists to prevent.
    q.add_argument("--catalog-root", required=True,
                   help="component catalog root the workflow's seat definitions resolve from — the "
                        "SHARED PARENT of the components, since catalog resolution is catalog-root-wide")
    q.add_argument("--bindings", required=True,
                   help="goal-generic per-seat bindings JSON for this workflow's manifest seats")
    q.add_argument("--claude-md", required=True,
                   help="caller-supplied CLAUDE.md base text for the created goal package")
    q.add_argument("--budget-json", required=True,
                   help="caller-supplied budget.json for the created goal package (a PATH, never a value)")
    q.add_argument("--ignite-bin", default="ignite",
                   help="the door's binary; a daemon-fired exec has no ~/.local/bin on PATH. "
                        "UNUSED since 7.778 deleted the two gateway calls this verb made — kept so "
                        "the shipped `tools:` argv keeps parsing")
    q.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)
    try:
        # `scaffold-and-queue` reads its payloads FROM THE INBOX, one per request, and each read is
        # inside the drain's own refusal arm — so an unreadable file refuses that ONE request
        # instead of killing the whole fire. It therefore takes no `request` argument and must not
        # go through the single-payload read below.
        if args.verb == "scaffold-and-queue":
            out = scaffold_and_queue(args.inbox, args.goals_root, args.workflow,
                                     args.catalog_root, args.bindings,
                                     args.claude_md, args.budget_json,
                                     ignite_bin=args.ignite_bin, dry_run=args.dry_run)
            print(json.dumps(out, indent=2))
            for req in out["requests"]:
                if req["outcome"] != "ACCEPTED":
                    print(f"{req['request-file']}: {req.get('stated-refusal')}", file=sys.stderr)
            return 0 if out["outcome"] in ("ACCEPTED", "EMPTY") else 1

        payload = json.loads(sys.stdin.read() if args.request == "-"
                             else Path(args.request).read_text(encoding="utf-8"))
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
                     args.claude_md, args.budget_json,
                     seat=args.seat, workflow=args.workflow, after=args.after, root=args.root,
                     do_launch=not args.no_launch, dry_run=args.dry_run)
        print(json.dumps(out, indent=2))
        if out.get("stated-refusal"):
            print(out["stated-refusal"], file=sys.stderr)
        return 0 if out["outcome"] == "ACCEPTED" else 1
    except Refusal as exc:
        print(json.dumps({"ok": False, "refusal": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
