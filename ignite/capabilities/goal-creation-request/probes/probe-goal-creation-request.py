#!/usr/bin/env python3
"""probe-goal-creation-request.py — the four checks task 7.211 AUTHORS, each with its own mutant.

⚠ THE GREEN ARMS ALONE PROVE NOTHING, AND THAT IS WHY EVERY CHECK CARRIES A MUTANT. "The entry
invokes the ruled name" is also what a checker reading a key the file does not carry would report,
and a control arm that cannot fire is indistinguishable from one that fired and found nothing. The
owner's own authorization of this build makes the red arm a CONDITION, not a courtesy
(`decisions.md#r-goal-launch-build-authorized`).

So each check below runs TWICE: once against the real file (must be GREEN) and once against a
mutated copy in a throwaway tree, where the condition the check exists to catch has been introduced
(must be RED). A check whose mutant stays green has scored nothing, and this probe exits **2
(INOPERATIVE)** rather than 0 — never a pass.

The four checks, and what each catches:

  1. VALIDATION NAMES ITS FIELDS — the validator reports every field it checked, not only a
     verdict. Mutant: a validator that returns the verdict with an empty `checked` list.
  2. THE RULED NAME — the create act invokes `scaffold-seats`. Mutant: the ruled name replaced by
     the script path behind it (`materialize-seats.py`), which is exactly the substitution
     `d-materialize-term` bars and which no naive "does it spawn something" check would catch.
  3. NO BESPOKE SPAWN, WITH A POSITIVE CONTROL — no seat-materialization or harness-launch
     construct other than the ruled name is reachable from the call site. The instrument is proven
     able to return non-zero by running it, unchanged, over a file that DOES carry such constructs.
  4. ONE LOCATION COMPUTER — the arming marker's location comes from the imported `arm_path()` and
     is computed nowhere else in this capability. Mutant: an inline
     `pkg / "coordination" / "edge-fastpath.json"`, the second reader whose disagreement with the
     first IS the C4 failure.

Nothing here reads or writes a live goals package. Every mutant lives under `tempfile`.
"""

import ast
import re
import sys
import tempfile
from pathlib import Path

CAP = Path(__file__).resolve().parents[1]
HANDLER = CAP / "tool" / "goal_creation_request.py"
# A file known to carry the very constructs check 3 scans for — the positive control's subject.
CONTROL_SUBJECT = CAP.parents[1] / "team-kit" / "coord.py"

# Seat-materialization / harness-launch constructs that are NOT the ruled name. `scaffold-seats`
# itself is deliberately absent from this alternation: the check asks what the call site reaches
# for INSTEAD of the ruled name.
# ⚠ `\W+`, NOT `\s+`, BETWEEN THE VERB AND ITS SUBCOMMAND — and that is the whole reason this
# pattern is written out rather than grepped. A bespoke spawn in Python is an ARGV LIST
# (`["tmux", "new-window"]`), not a shell string (`tmux new-window`), so a `\s+` form matches the
# documentation and misses the code. Measured: the first draft used `\s+`, its mutant arm stayed
# GREEN, and its positive control still reported 9 hits — every one of them from the OTHER
# alternation arm. A blind arm hiding behind a healthy arm's count is why the control below is
# reported PER ARM.
BESPOKE_ARMS = {
    "script-path-not-the-ruled-name": re.compile(r"materialize-seats(?:\.py)?"),
    "hand-rolled-tmux-spawn": re.compile(
        r"\btmux\W+(?:new-window|split-window|new-session|send-keys)"),
    "direct-harness-spawn": re.compile(
        r"\bsubprocess\.[A-Za-z_]+\([^)]*['\"](?:claude|codex|opencode)['\"]"),
}


def bespoke_search(line):
    """The first arm that matches, or None. One instrument, three named arms."""
    for arm, rx in BESPOKE_ARMS.items():
        if rx.search(line):
            return arm
    return None
# A location computation that is not the imported one.
INLINE_ARM_PATH = re.compile(r"""["']coordination["']\s*[/,]\s*["']edge-fastpath\.json["']""")


def code_only(src):
    """The source with every DOCSTRING and comment blanked — line numbering preserved.

    ⚠ THIS FUNCTION IS THE PROBE'S OWN BUG FIX, AND IT IS WHY THE CHECK IS NOT A GREP. Check 3's
    first draft scanned raw text and went RED on the real file — on the handler's own docstring
    sentence *"it never invokes the script path `materialize-seats.py`"*. A checker that matches
    the forbidden token fires on the line FORBIDDING it, and a reader would have "fixed" a correct
    file by deleting the sentence that documents the bound. The check must match the construct as
    CODE, never the noun as prose.
    """
    lines = src.splitlines()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src
    blank = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = node.body[0] if node.body else None
            if (isinstance(doc, ast.Expr) and isinstance(doc.value, ast.Constant)
                    and isinstance(doc.value.value, str)):
                blank.update(range(doc.lineno, (doc.end_lineno or doc.lineno) + 1))
    out = []
    for i, ln in enumerate(lines, 1):
        if i in blank:
            out.append("")
        else:
            out.append("" if ln.lstrip().startswith("#") else ln)
    return "\n".join(out)

FAILED = []
INOPERATIVE = []


def report(check, arm, ok, expected, detail=""):
    verdict = "GREEN" if ok else "RED"
    flag = "ok " if (ok == expected) else "BAD"
    print(f"  [{flag}] {check} · {arm} arm -> {verdict} (expected {'GREEN' if expected else 'RED'})"
          + (f" — {detail}" if detail else ""))
    return ok == expected


# ------------------------------------------------------------ the four checks
# Each takes the handler's SOURCE TEXT plus a live module, and returns (ok, detail). Written
# against text-or-module rather than against the installed path so the identical check runs over a
# mutant copy — a check that could only ever read the real file could never be shown able to fail.

def check_validation_names_fields(src, mod):
    if mod is None:
        return False, "module did not import"
    out = mod.validate({"goal-name": "x-y", "goal-type": "one-shot",
                        "goal-contract": "c", "goal-kind": "interactive"})
    named = {c["field"] for c in out.get("checked", [])}
    missing = [f for f in ("goal-name", "goal-type", "goal-contract", "goal-kind")
               if f not in named]
    if missing:
        return False, f"validator did not name field(s) it checked: {missing}"
    return True, f"named {len(named)} field(s)"


def check_ruled_name(src, mod):
    if not re.search(r"RULED_LAUNCH_NAME\s*=\s*[\"']scaffold-seats[\"']", src):
        return False, "the ruled name is not bound as the launch name"
    if not re.search(r"cmd\s*=\s*\[\s*RULED_LAUNCH_NAME", src):
        return False, "the create act's argv does not lead with the ruled name"
    return True, "create act invokes scaffold-seats by name"


def check_no_bespoke_spawn(src, mod):
    hits = [(bespoke_search(ln), ln) for ln in code_only(src).splitlines() if bespoke_search(ln)]
    if hits:
        return False, f"{len(hits)} bespoke spawn construct(s): [{hits[0][0]}] {hits[0][1].strip()[:60]}"
    return True, "0 bespoke spawn constructs (docstrings/comments excluded — see code_only)"


def check_one_location_computer(src, mod):
    if not re.search(r"mod\.arm_path\(", src):
        return False, "the arm act does not call the imported arm_path()"
    hits = [ln for ln in code_only(src).splitlines() if INLINE_ARM_PATH.search(ln)]
    if hits:
        return False, f"a SECOND location computation: {hits[0].strip()[:70]}"
    return True, "location computed only by the imported arm_path()"


def check_fails_closed(src, mod):
    """A failed CREATE must stop the chain — the arm act never runs on it.

    THIS CHECK EXISTS BECAUSE THE DEFECT WAS REAL, not anticipated. On task 7.211's first exercise
    `scaffold-seats` refused the bindings and returned rc=1, and the handler armed the package
    anyway and reported ACCEPTED. An arming marker on a package that was never created is read by
    the door as a package to advance.

    Driven by substituting the two acts, so the check needs no filesystem and no subprocess: what
    is under test is the ORDERING, not either act's own work.
    """
    if mod is None:
        return False, "module did not import"
    armed = []
    real_create, real_arm, real_launch = mod.create, mod.arm, mod.launch
    try:
        mod.create = lambda *a, **k: [{"step": "create-package", "rc": 1, "argv": [],
                                       "stdout": "", "stderr": "refused"}]
        mod.arm = lambda *a, **k: (armed.append("arm"), {"step": "arm"})[1]
        mod.launch = lambda *a, **k: (armed.append("launch"), {"step": "launch"})[1]
        out = mod.handle({"goal-name": "x-y", "goal-type": "one-shot",
                          "goal-contract": "c", "goal-kind": "interactive"},
                         None, "/nonexistent/pkg", "cat", "bind", "cond", "cmd", "budget",
                         "job", "prof", seat="s", root=True)
    finally:
        mod.create, mod.arm, mod.launch = real_create, real_arm, real_launch
    if armed:
        return False, f"a later act RAN after create failed: {armed}"
    if not str(out.get("outcome", "")).startswith("FAILED"):
        return False, f"outcome does not report the failure: {out.get('outcome')!r}"
    return True, "create rc=1 -> no arm, no launch, outcome FAILED"


def check_launch_gates_outcome(src, mod):
    """A launch that returns 0 but leaves NO session row must NOT report ACCEPTED.

    The discriminating case, and the reason this is not just "check the exit code": `session_open`
    runs only after the harness is verified up, so a pane that opened and whose harness then died
    can leave rc=0 and no trace row. An entry whose create and arm are proven and whose launch
    never actually ran is the artifact that passes every gate and then dies.
    """
    if mod is None:
        return False, "module did not import"
    real_create, real_arm, real_launch = mod.create, mod.arm, mod.launch
    try:
        mod.create = lambda *a, **k: [{"step": "create-package", "rc": 0}]
        mod.arm = lambda *a, **k: {"step": "arm", "accepted-by-fastpath-reader": True}
        # rc=0 — a SUCCESSFUL-looking launch — against a package with no sessions.csv.
        mod.launch = lambda *a, **k: {"step": "launch", "rc": 0}
        out = mod.handle({"goal-name": "x-y", "goal-type": "one-shot",
                          "goal-contract": "c", "goal-kind": "interactive"},
                         None, "/nonexistent/pkg", "cat", "bind", "cond", "cmd", "budget",
                         "job", "prof", seat="s", root=True)
    finally:
        mod.create, mod.arm, mod.launch = real_create, real_arm, real_launch
    if str(out.get("outcome", "")).startswith("ACCEPTED"):
        return False, "rc=0 with NO session row was reported ACCEPTED — the trace was never asserted"
    if not str(out.get("outcome", "")).startswith("FAILED at launch"):
        return False, f"outcome does not name the launch failure: {out.get('outcome')!r}"
    return True, "launch rc=0 + no session row -> outcome FAILED at launch"


# ------------------------------------- the three checks task 7.206 AUTHORS (E11, refusal arm `a`)
#
# THE MALFORMED CASE USED BELOW IS THE SCHEMA'S OWN WORKED EXAMPLE (§6.2), not one invented here:
#   {goal-name: "x", goal-contract: "  ", goal-kind: "interactive", priority: "high"}
# The schema states its correct report verbatim — `{S2}` ALONE — because `S2` matches, class `S` is
# therefore the first class in which any member matched, and evaluation stops there. `P2` and `V5`
# are REAL of this request and are deliberately suppressed on this pass. That published expectation
# is what makes check 8 an assertion rather than a restatement of whatever the code happens to do.
MALFORMED = {"goal-name": "x", "goal-contract": "  ", "goal-kind": "interactive",
             "priority": "high"}
# The thirteen ids, spelled out HERE rather than read from the handler under test. A check whose
# expectation reads the value it is checking moves with the code and passes any change to it.
THIRTEEN = {"S1", "S2", "S3", "P1", "P2", "P3", "P4", "V1", "V2", "V3", "V4", "V5", "V6"}


def check_refusal_names_a_member(src, mod):
    """A refusal NAMES the member of E3's closed set that matched — U3's third criterion.

    A refusal reporting only a field and a constraint cannot be told apart from a refusal invented
    at the call site, and it cannot be checked against the closed set at all.
    """
    if mod is None:
        return False, "module did not import"
    out = mod.validate(MALFORMED)
    if out.get("accepted"):
        return False, "the malformed request was ACCEPTED — F-E11a"
    members = [r.get("member") for r in out.get("refusals", [])]
    if not members or any(m is None for m in members):
        return False, f"a refusal named no member: {out.get('refusals')}"
    outside = [m for m in members if m not in THIRTEEN]
    if outside:
        return False, f"member(s) outside the closed thirteen: {outside}"
    return True, f"named {members}, all members of the closed thirteen"


def check_class_stop_order(src, mod):
    """S -> P -> V with a stop at the first matched class (§6.2), asserted on the schema's own
    worked example, whose correct report the schema publishes as `{S2}` alone.

    The discriminating case, and why this is not "did it refuse": the pre-7.206 entry refused this
    exact request too — with `{S2, P2, V5}`, three members across three classes. A verdict-only
    check cannot tell the two apart, and two implementers reporting different members for one
    request is precisely what §6.2 exists to prevent.
    """
    if mod is None:
        return False, "module did not import"
    out = mod.validate(MALFORMED)
    members = sorted(r.get("member") for r in out.get("refusals", []))
    if members != ["S2"]:
        return False, (f"reported {members}, but §6.2's worked example rules exactly ['S2'] — "
                       "evaluation did not stop at the first matched class")
    # The accepting path must still traverse every class, or the stop above would be indis-
    # tinguishable from a validator that gave up early on everything.
    ok = mod.validate({"goal-name": "a-b", "goal-type": "one-shot", "goal-contract": "c",
                       "goal-kind": "interactive"})
    if not ok.get("accepted") or ok.get("classes-evaluated") != "S,P,V":
        return False, f"the accepting path did not traverse S,P,V: {ok.get('classes-evaluated')!r}"
    return True, "malformed -> ['S2'] alone (class S stop); valid -> S,P,V traversed"


def check_refusal_is_stated(src, mod):
    """The refusal carries TEXT naming what was rejected — never a bare status.

    Checked at the surface that answers the requester: `handle()`'s own `outcome`, which is what a
    caller reads. A `stated-refusal` field that the requester-facing outcome does not carry is a
    stated refusal only to whoever already knows to look for it.
    """
    if mod is None:
        return False, "module did not import"
    real_create = mod.create
    try:
        # If validation ever failed to refuse, this substitute makes the escape loud rather than
        # letting the check pass on a create that quietly did nothing.
        mod.create = lambda *a, **k: [{"step": "create-package", "rc": 0,
                                       "NOTE": "REACHED — the malformed request was not refused"}]
        out = mod.handle(MALFORMED, None, "/nonexistent/pkg", "cat", "bind", "cond", "cmd",
                         "budget", "job", "prof", seat="s", root=True)
    finally:
        mod.create = real_create
    if out.get("acts", {}).get("create"):
        return False, "an act was performed on a malformed request — F-E11a"
    outcome = str(out.get("outcome", ""))
    if not outcome.startswith("REFUSED"):
        return False, f"outcome does not refuse: {outcome!r}"
    stated = out.get("stated-refusal") or ""
    # The three things that make it STATED rather than a status: the member id, the member's name,
    # and the offending detail. A status carries none of them.
    for token in ("S2", "field-name-not-in-the-five", "priority"):
        if token not in stated or token not in outcome:
            return False, (f"the refusal is a bare status — {token!r} appears in neither the "
                           f"stated text nor the requester-facing outcome: {outcome[:80]!r}")
    return True, "requester-facing outcome names the member, its name and the offending field"


# The mutation each check must be able to catch. Text substitutions, applied to a throwaway copy.
CHECKS = [
    # ⚠ THIS MUTATION WAS REPAIRED BY TASK 7.206, AND THE REPAIR IS THE HARNESS WORKING. The
    # refusal arm moved the verdict dict into `_verdict()`, so the old substitution text matched
    # nothing — and this probe reported INOPERATIVE rather than a pass, which is the whole reason
    # the "mutation matched nothing" branch exists.
    ("1 validation-names-its-fields", check_validation_names_fields,
     lambda s: s.replace('            "checked": checked,\n',
                         '            "checked": [],\n')),
    ("2 ruled-name-invoked", check_ruled_name,
     lambda s: s.replace('RULED_LAUNCH_NAME = "scaffold-seats"',
                         'RULED_LAUNCH_NAME = "materialize-seats.py"')),
    ("3 no-bespoke-spawn", check_no_bespoke_spawn,
     lambda s: s.replace("    ruled = shutil.which(RULED_LAUNCH_NAME)",
                         "    subprocess.run(['tmux', 'new-window', '-d'])\n"
                         "    ruled = shutil.which(RULED_LAUNCH_NAME)")),
    ("4 one-location-computer", check_one_location_computer,
     lambda s: s.replace("    path = mod.arm_path(package)",
                         '    path = Path(package) / "coordination" / "edge-fastpath.json"')),
    ("5 chain-fails-closed", check_fails_closed,
     lambda s: s.replace('    failed = [s for s in result["acts"]["create"] if s.get("rc") not in (0, None)]',
                         '    failed = []')),
    ("6 launch-gates-the-outcome", check_launch_gates_outcome,
     lambda s: s.replace("        if rc not in (0, None) or not row:",
                         "        if False:")),
    # --- task 7.206's three, each mutated at the condition it exists to catch ---
    # The member id is dropped from the REPORTED refusals: the pre-7.206 shape, which refused
    # correctly and named nothing checkable against the closed set.
    # ⚠ MUTATED AT THE OUTPUT, NOT AT `refuse()`. The first draft removed the key where refusals are
    # built — and `_stated()` reads it too, so the mutant raised `KeyError` and the check never
    # rendered a verdict at all. A mutant that CRASHES proves nothing about the check: the red it
    # produces is the traceback's, not the condition's.
    ("7 refusal-names-a-member", check_refusal_names_a_member,
     lambda s: s.replace('            "refusals": refusals,\n',
                         '            "refusals": [{k: v for k, v in r.items() if k != "member"}\n'
                         '                         for r in refusals],\n')),
    # Class-stop removed: the S stage no longer returns, so P and V are evaluated too and the
    # worked example reports {S2, P2, V5} — a refusal that is still correct as a VERDICT and wrong
    # as a REPORT, which is the exact defect §6.2 exists to prevent.
    ("8 class-stop-S-P-V", check_class_stop_order,
     lambda s: s.replace("    if refusals:\n        return _verdict(checked, refusals, \"S\")\n",
                         "    if False:\n        return _verdict(checked, refusals, \"S\")\n")),
    # The stated text is replaced by a bare status at the requester-facing surface — the refusal
    # still fires and still performs no act, and the requester can no longer tell what was rejected.
    ("9 refusal-is-stated", check_refusal_is_stated,
     lambda s: s.replace('        result["outcome"] = "REFUSED — no act performed\\n" + verdict["stated-refusal"]',
                         '        result["outcome"] = "REFUSED"\n        result["stated-refusal"] = ""')),
]


def load(path):
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location(f"probe_target_{path.stem}_{id(path)}", path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    except Exception:
        return None


def main():
    if not HANDLER.is_file():
        print(f"INOPERATIVE — no handler at {HANDLER}")
        return 2
    real_src = HANDLER.read_text(encoding="utf-8")
    real_mod = load(HANDLER)
    print(f"probe-goal-creation-request — target {HANDLER}")

    ok_all = True
    with tempfile.TemporaryDirectory() as td:
        for name, fn, mutate in CHECKS:
            # GREEN arm — the real file must pass.
            ok, detail = fn(real_src, real_mod)
            ok_all &= report(name, "real  ", ok, True, detail)
            if not ok:
                FAILED.append(name)

            # RED arm — the same check, over a copy carrying the defect it exists to catch.
            mutant_src = mutate(real_src)
            if mutant_src == real_src:
                print(f"  [BAD] {name} · mutant arm -> NOT APPLIED "
                      f"(the mutation matched nothing — the check is unproven)")
                INOPERATIVE.append(name)
                ok_all = False
                continue
            # ⚠ THE MUTANT SITS AT THE SAME DIRECTORY DEPTH AS THE REAL FILE, DELIBERATELY. The
            # handler resolves a sibling module by `parents[3]`, so a mutant written to a shallow
            # temp path raises at IMPORT — and the check then goes red on the path, not on the
            # mutation. Measured: check 1's first mutant arm reported "module did not import" and
            # would have been recorded as a proven red control while proving nothing at all.
            mdir = Path(td) / name.split()[0] / "ignite" / "capabilities" / "goal-creation-request" / "tool"
            mdir.mkdir(parents=True, exist_ok=True)
            mpath = mdir / "goal_creation_request.py"
            mpath.write_text(mutant_src, encoding="utf-8")
            mmod = load(mpath)
            if mmod is None and fn is not check_ruled_name:
                print(f"  [BAD] {name} · mutant arm -> INOPERATIVE (the mutant did not import, so "
                      f"any red it produces is the import's, not the mutation's)")
                INOPERATIVE.append(name)
                ok_all = False
                continue
            mok, mdetail = fn(mutant_src, mmod)
            ok_all &= report(name, "mutant", mok, False, mdetail)
            if mok:
                INOPERATIVE.append(name)

    print()
    if INOPERATIVE:
        print(f"VERDICT: INOPERATIVE — {len(INOPERATIVE)} check(s) stayed GREEN under their own "
              f"mutation and have therefore scored nothing: {INOPERATIVE}")
        return 2
    if FAILED:
        print(f"VERDICT: RED — {len(FAILED)} check(s) failed against the real file: {FAILED}")
        return 1
    print(f"VERDICT: GREEN — all {len(CHECKS)} checks pass, and all {len(CHECKS)} were shown able "
          f"to FAIL under mutation.")
    return 0


if __name__ == "__main__":
    rc = main()
    # Check 3's POSITIVE CONTROL. The mutant arm above proves the instrument fires on an injected
    # construct; this proves it fires on real code nobody wrote for it. A zero from an instrument
    # never shown able to return non-zero is not accepted, so the count is printed either way.
    if CONTROL_SUBJECT.is_file():
        ctl_src = code_only(CONTROL_SUBJECT.read_text(encoding="utf-8", errors="replace"))
        print(f"positive control — the SAME instrument over {CONTROL_SUBJECT.name}, PER ARM "
              f"(a single total would let a blind arm hide behind a healthy one):")
        blind = []
        for arm, rx in BESPOKE_ARMS.items():
            n = sum(1 for ln in ctl_src.splitlines() if rx.search(ln))
            print(f"  {arm}: {n} hit(s)")
            if n == 0:
                blind.append(arm)
        if blind:
            print(f"NOTE — arm(s) with 0 hits in the control: {blind}. Their 0 on the TARGET is "
                  f"carried by the mutant arm above, which injects the construct directly; the "
                  f"control file simply does not happen to contain that form.")
    sys.exit(rc)
