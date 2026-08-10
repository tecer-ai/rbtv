#!/usr/bin/env python3
"""probe-store-ready-suppression.py — the STORE-radius suppression consumer, and the standing
proof that it still refuses.

WHAT THIS IS (design row U2.2 / store row 7.225, element E10 of the row-terminal-states wave):
a MECHANICAL consumer of the store-radius readiness. `sb-task deps <store> --ready` offers every
row whose dependency edges are met — including rows a ruling has already taken out of play. This
file is the filter that removes them, evaluated by a tool and never by a seat's reading.

THE PREDICATE, from the ruled design (u1d `bindability-evidence.suppression-set`, accepted
PROVISIONAL at runs/run-3/decisions.md#p-U1-terminal-state-design-ACCEPTED-PROVISIONAL-...):

    a row is SUPPRESSED from the offer set IFF its title-line tags carry ANY `row-outcome/*` value

BOTH u1b classes suppress, and that is the load-bearing part of the wording:
  terminal-class : row-outcome/skipped-by-guard
                   row-outcome/finished-unsatisfiable
                   row-outcome/unreachable-by-construction   (no event exits these — always wrong)
  holding-class  : row-outcome/accepted-not-closable-yet
                   row-outcome/held-by-ruling                (an exit event exists, has NOT fired)
The baseline pair needs no tag: `done` is the checkbox `[x]` (already absent from `--ready`), and
`untouched` is the offerable state. Naming the terminal class ALONE would have left the majority
of the measured mis-offers standing — that is why the namespace, not the class, is the predicate.

`#barred` IS NOT THE VOCABULARY and this file does not suppress on it (B-4: set equality computed
5 != 13, and the census anchors are run-scoped `p-*` while the store outlives the run). It is
reported as a LEGACY CARRIER only, pending U3.2, so that a live run says something true about it
without pre-empting a decision this file does not hold.

TWO MODES, one file:
  (no args)          PROBE mode — builds its own fixture from a COPY of the store in a temp dir
                     and asserts three things: the filter REFUSES a suppressed row (negative arm),
                     does NOT refuse a clean row (positive arm), and REAPPEARS the row when the
                     predicate is mutated away (red control — a guard only ever seen passing is
                     indistinguishable from a guard that cannot fire). exit 0 all green, 1 on any
                     failure. This is the mode the hourly probe suite runs.
  --offer            CONSUMER mode — runs the filter against a real store and prints the OFFERED
                     set with suppressed rows removed. Exit 0 when nothing was suppressed, exit 3
                     when it refused at least one row, so a scripted caller reads the exit code and
                     not prose. `--json` for the machine-readable form.

STORE SAFETY: PROBE mode never writes the store it reads. It copies it into a temp dir and tags
the COPY through the sanctioned `sb-task` CLI. Subprocesses run with HOME inside that temp dir
(G-75: a mutation test runs with the full write authority of the real program).

NO sb-os PATH IS WRITTEN by this file. `sb_task.py` is READ-ONLY here — it is resolved and
executed, never edited; the store-format alternate that would change it is U2.3's parked, owner-
gated branch (goal doubts.md #45).
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- the predicate

SUPPRESS_NAMESPACE = "row-outcome/"

# The five enumerated non-baseline values, spelled as u1b enumerates them. This set is for
# REPORTING only — the predicate is the NAMESPACE, deliberately. An unenumerated `row-outcome/*`
# token is legal under the store's own TAG_RE and is therefore reachable; it is suppressed too
# (the safe direction) and named as unrecognized rather than silently honoured or silently ignored.
ENUMERATED = {
    "row-outcome/skipped-by-guard": "terminal",
    "row-outcome/finished-unsatisfiable": "terminal",
    "row-outcome/unreachable-by-construction": "terminal",
    "row-outcome/accepted-not-closable-yet": "holding",
    "row-outcome/held-by-ruling": "holding",
}

LEGACY_CARRIER = "barred"   # reported, NEVER suppressed — B-4, pending U3.2

DEFAULT_STORE = ("1-projects/rbtv-sb-merge-refactor-core-build/"
                 "rbtv-sb-merge-refactor-core-build-tasks.md")


def suppressing_tags(tags, namespace=SUPPRESS_NAMESPACE):
    """Every tag on this row that suppresses it. The whole predicate lives here.

    `namespace` is a parameter for ONE reason: the red control mutates it to a token no row can
    carry and asserts the suppressed row reappears. No caller passes anything else, and no CLI
    flag reaches it — a filter with an off switch is not a filter.
    """
    return sorted(t for t in (tags or []) if t.startswith(namespace))


def partition(ready_rows, namespace=SUPPRESS_NAMESPACE):
    """Split the raw ready set into what may be offered and what is refused."""
    offered, refused = [], []
    for r in ready_rows:
        hits = suppressing_tags(r.get("tags"), namespace)
        (refused if hits else offered).append(
            dict(number=r.get("number"), title=r.get("title"),
                 tags=sorted(r.get("tags") or []), suppressed_by=hits))
    return offered, refused


# ---------------------------------------------------------------- the instrument

def workspace_root(start=None):
    """Walk up for the file that marks a vault root. Never a hardcoded absolute path."""
    here = (start or Path(__file__).resolve()).parent
    for d in [here, *here.parents]:
        if (d / "sb-os.json").is_file():
            return d
    raise RuntimeError("workspace root not found (no sb-os.json above %s)" % here)


def sb_task_cmd(root):
    """Resolve the sb-task CLI without depending on PATH.

    The hourly suite runs under systemd, whose PATH does not carry ~/.local/bin. Resolving through
    sb-os.json is deterministic and reports its own absence loudly. This READS sb-os source; it
    never writes it.
    """
    cfg = json.loads((root / "sb-os.json").read_text(encoding="utf-8"))
    entry = root / cfg["sb_os_path"] / "para/cli/sb-task/sb_task.py"
    if not entry.is_file():
        raise RuntimeError("sb-task CLI not at %s" % entry)
    return [sys.executable, str(entry)]


def deps_json(root, store, ready=False, env=None):
    """Run the UNCAPPED instrument and assert its envelope.

    `sb-task list` defaults to --limit 50 and truncates silently in its human render; `deps --json`
    has no cap. Where the envelope carries `count`, `count == len(tasks)` is asserted here rather
    than trusted — an unasserted census is a floor of unknown depth.
    """
    cmd = sb_task_cmd(root) + ["deps", str(store), "--json"] + (["--ready"] if ready else [])
    out = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(root))
    if out.returncode != 0:
        raise RuntimeError("sb-task deps failed (exit %d): %s" % (out.returncode, out.stderr[-400:]))
    d = json.loads(out.stdout)
    tasks = d.get("tasks") or []
    if "count" in d and d["count"] != len(tasks):
        raise RuntimeError("ENVELOPE MISMATCH: count=%r len(tasks)=%d — the census is truncated"
                           % (d["count"], len(tasks)))
    return d, tasks, " ".join(cmd)


# ---------------------------------------------------------------- consumer mode

def cmd_offer(args):
    root = workspace_root()
    store = args.store or DEFAULT_STORE
    _, ready, inv = deps_json(root, store, ready=True)
    offered, refused = partition(ready)
    legacy = [r.get("number") for r in ready if LEGACY_CARRIER in (r.get("tags") or [])]

    if args.json:
        print(json.dumps(dict(
            invocation=inv, store=store, raw_ready=len(ready),
            offered=[r["number"] for r in offered], refused=refused,
            offered_count=len(offered), refused_count=len(refused),
            legacy_carrier_pending_u3_2=sorted(legacy),
            predicate="tags[] carries any %s* value" % SUPPRESS_NAMESPACE), indent=2))
    else:
        print("store          : %s" % store)
        print("instrument     : %s" % inv)
        print("raw ready set  : %d row(s)" % len(ready))
        print("OFFERED        : %d — %s" % (len(offered), " ".join(r["number"] for r in offered)))
        print("REFUSED        : %d" % len(refused))
        for r in refused:
            unknown = [t for t in r["suppressed_by"] if t not in ENUMERATED]
            note = "  [UNRECOGNIZED VALUE — suppressed anyway]" if unknown else ""
            print("  refused %-8s %s%s" % (r["number"], ",".join(r["suppressed_by"]), note))
        if legacy:
            print("legacy carrier : %s  (#%s — NOT suppressed here; B-4, pending U3.2)"
                  % (" ".join(sorted(legacy)), LEGACY_CARRIER))
    # Exit 3 IS the refusal. A scripted caller reads this and nothing else.
    return 3 if refused else 0


# ---------------------------------------------------------------- probe mode

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print("%-46s %s%s" % (name, "PASS" if ok else "FAIL", ("  — " + detail) if detail else ""))
    return ok


def cmd_probe(args):
    """Three arms against a fixture built from a COPY of the real store."""
    root = workspace_root()
    store = root / (args.store or DEFAULT_STORE)
    if not store.is_file():
        check("store resolves", False, "no store at %s" % store)
        return 1

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        home = td / "home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home))          # G-75: the mutant runs with real authority
        store_sha = hashlib.sha256(store.read_bytes()).hexdigest()
        copy = td / store.name
        shutil.copy2(store, copy)

        _, ready_before, _ = deps_json(root, copy, ready=True, env=env)
        if not ready_before:
            return 1 if not check("fixture has a ready row to tag", False,
                                  "the copied store offers nothing") else 0

        # The subject: a REAL row of the real store, tagged through the sanctioned CLI on the COPY.
        # A store row may legitimately carry NO number (unnumbered `DECIDE:` rows are a real shape
        # and 12 of them sit in the default store today), and `sb-task edit` addresses a row by its
        # number — so the fixture picks from the NUMBERED ready rows, never from row 0 blindly.
        numbered = [r["number"] for r in ready_before if r.get("number")]
        if not numbered:
            check("fixture has a NUMBERED ready row to tag", False,
                  "%d ready row(s), none numbered" % len(ready_before))
            return 1
        subject = numbered[0]
        control = numbered[1] if len(numbered) > 1 else None
        token = "row-outcome/held-by-ruling"
        tag = subprocess.run(sb_task_cmd(root) + ["edit", str(copy), subject, "--add-tag", token],
                             capture_output=True, text=True, env=env, cwd=str(root))
        if not check("fixture: token lands on the title line",
                     tag.returncode == 0 and token in tag.stdout,
                     tag.stdout.strip()[-120:] or tag.stderr.strip()[-120:]):
            return 1

        _, ready_after, _ = deps_json(root, copy, ready=True, env=env)
        offered, refused = partition(ready_after)
        onums = {r["number"] for r in offered}

        # NEGATIVE ARM — the suppressed row is ABSENT from the offered set.
        check("negative arm: %s refused" % subject,
              subject not in onums and any(r["number"] == subject for r in refused),
              "offered=%d refused=%d" % (len(offered), len(refused)))

        # POSITIVE ARM — an untagged row is still offered. Over-refusal is as much a defect.
        if control:
            check("positive arm: %s still offered" % control, control in onums)

        # RED CONTROL — mutate the predicate away; the row must REAPPEAR. Without this, a filter
        # that cannot fire at all is indistinguishable from one that had nothing to refuse.
        mut_offered, mut_refused = partition(ready_after, namespace="no-row-carries-this/")
        check("red control: predicate mutated -> %s reappears" % subject,
              subject in {r["number"] for r in mut_offered} and not mut_refused,
              "mutated refused=%d (expected 0)" % len(mut_refused))

        # The store this probe READ is untouched — asserted against a digest taken BEFORE the
        # fixture was tagged. Comparing the file to itself would pass whatever happened.
        after = hashlib.sha256(store.read_bytes()).hexdigest()
        check("live store not written",
              after == store_sha and hashlib.sha256(copy.read_bytes()).hexdigest() != store_sha,
              "store %s..%s unchanged; the copy diverged" % (store_sha[:8], after[:8]))

    failed = [n for n, ok, _ in RESULTS if not ok]
    print("\n%d/%d green" % (len(RESULTS) - len(failed), len(RESULTS)))
    return 1 if failed else 0


def main():
    p = argparse.ArgumentParser(
        description="store-radius suppression consumer (row-outcome/* filter) + its standing proof")
    p.add_argument("--offer", action="store_true",
                   help="CONSUMER mode: print the offered set with suppressed rows removed "
                        "(exit 3 = it refused at least one row)")
    p.add_argument("--json", action="store_true", help="machine-readable output for --offer")
    p.add_argument("--store", help="store path relative to the workspace root")
    args = p.parse_args()
    return cmd_offer(args) if args.offer else cmd_probe(args)


if __name__ == "__main__":
    sys.exit(main())
