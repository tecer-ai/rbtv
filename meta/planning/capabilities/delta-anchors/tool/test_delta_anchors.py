#!/usr/bin/env python3
"""Red arms for delta_anchors.py — every finding code proved to FIRE, plus green and atomicity.

Run: python3 3-resources/tools/rbtv/meta/planning/capabilities/delta-anchors/tool/test_delta_anchors.py
Arm ids match the fix design's §4 verification plan (R1-R5, G1, G2). R6 (mutation proof) is run
by hand against a COPY of the tool: neuter the `elif n_from != 1:` guard and R1+R2 must go green
while every other arm holds.

The design's `anchor-not-line-aligned` code does NOT exist: measured against the reconstructed
round-7 delta list it fired on three anchors the leader's hand audit verified SOUND, and a
verbatim-byte applier swallows nothing by construction — the bytes quoted are the bytes replaced.
R3 is therefore the INVERSE arm: a mid-line, multi-line phrase anchor must be accepted and applied
byte-exactly. It goes red if anyone re-adds the rule.
"""
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delta_anchors  # noqa: E402

SEAT = "planning/current/seats/widget-smith/task.md"
TARGET_TEXT = """# widget-smith

## Criterion 3 - the fixture set
The suite seeds two instances and validates both.
Every arm names its id.

## Criterion 6 - nothing else touched
No file under `tools/` is modified.
"""


def goal_with(target_text=TARGET_TEXT, rel=SEAT):
    root = tempfile.mkdtemp(prefix="delta-anchors-")
    full = os.path.join(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w").write(target_text)
    open(os.path.join(root, "planning", "current", "task-dag.md"), "w").write("the source of truth\n")
    return root


def delta_file(root, name, body):
    path = os.path.join(root, name)
    open(path, "w").write(body)
    return path


def block(idx, target, frm, to, source="planning/current/task-dag.md"):
    src = "source: %s\n" % source if source is not None else ""
    return "## delta %s\ntarget: %s\n%s```from\n%s\n```\n```to\n%s\n```\n\n" % (idx, target, src, frm, to)


def run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = delta_anchors.main(argv)
    return code, buf.getvalue()


def codes(out):
    return sorted(line.split()[1] for line in out.splitlines() if line.startswith("FAIL "))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


ARMS = []


def arm(fn):
    ARMS.append(fn)
    return fn


@arm
def R1_anchor_absent():
    """A `from` block that is not in the target at all."""
    root = goal_with()
    df = delta_file(root, "deltas-widget-smith-round-1.md",
                    block(1, SEAT, "no test file edits any file under `tools/`", "REPLACED"))
    code, out = run(["check", df, "--goal", root])
    assert code == 1, out
    assert codes(out) == ["anchor-absent"], out
    shutil.rmtree(root)


@arm
def R2_anchor_ambiguous():
    """A `from` block occurring twice in the target."""
    root = goal_with(TARGET_TEXT + "Every arm names its id.\n")
    df = delta_file(root, "deltas-widget-smith-round-1.md",
                    block(1, SEAT, "Every arm names its id.", "Every arm names its own id."))
    code, out = run(["check", df, "--goal", root])
    assert code == 1, out
    assert codes(out) == ["anchor-ambiguous"], out
    assert "occurs 2 times" in out, out
    shutil.rmtree(root)


@arm
def R3_mid_line_phrase_anchor_is_sound():
    """A multi-line phrase anchor starting and ending mid-line is a NORMAL anchor, never a finding."""
    root = goal_with()
    frm = "seeds two instances and validates both.\nEvery arm names"
    assert TARGET_TEXT.count(frm) == 1
    df = delta_file(root, "deltas-widget-smith-round-1.md", block(1, SEAT, frm, "seeds three.\nEach arm names"))
    code, out = run(["check", df, "--goal", root])
    assert code == 0, out
    code, out = run(["apply", df, "--goal", root])
    assert code == 0, out
    assert open(os.path.join(root, SEAT)).read() == TARGET_TEXT.replace(frm, "seeds three.\nEach arm names")
    shutil.rmtree(root)


@arm
def R3b_two_deltas_one_file_record_spans_hold():
    """Two deltas in ONE file: each record's line span must name the region in the FINAL file."""
    root = goal_with()
    df = delta_file(root, "deltas-widget-smith-round-2.md",
                    # authored high-offset first, so a naive in-order apply staled the first record
                    block(1, SEAT, "No file under `tools/` is modified.", "No file under `tools/` or\n`seams/` is modified.")
                    + block(2, SEAT, "The suite seeds two instances and validates both.",
                            "The suite seeds two instances.\nIt validates both against the minted schema."))
    assert run(["apply", df, "--goal", root])[0] == 0
    lines = open(os.path.join(root, SEAT)).read().splitlines()
    for rec in json.load(open(os.path.join(root, "applied-deltas-widget-smith-round-2.json"))):
        span = "\n".join(lines[rec["start_line"] - 1:rec["end_line"]])
        assert span in ("No file under `tools/` or\n`seams/` is modified.",
                        "The suite seeds two instances.\nIt validates both against the minted schema."), (rec, span)
    shutil.rmtree(root)


@arm
def R4_already_applied():
    """`to` present and `from` absent — a no-op or a double-apply."""
    root = goal_with()
    df = delta_file(root, "deltas-widget-smith-round-1.md",
                    block(1, SEAT, "The suite seeds three instances.", "The suite seeds two instances and validates both."))
    code, out = run(["check", df, "--goal", root])
    assert code == 1, out
    assert codes(out) == ["already-applied"], out
    shutil.rmtree(root)


@arm
def R5_source_not_routed():
    """A seat file is a rendering — an unrouted fix is reverted on the next re-seed."""
    frm, to = "Every arm names its id.", "Every arm names its id and its owner."
    root = goal_with()
    df = delta_file(root, "deltas-widget-smith-round-1.md", block(1, SEAT, frm, to, source=None))
    code, out = run(["check", df, "--goal", root])
    assert code == 1, out
    assert codes(out) == ["source-not-routed"], out

    # control: an explicit rendering-only declaration is clean
    df2 = delta_file(root, "deltas-widget-smith-round-2.md",
                     block(1, SEAT, frm, to, source="none — rendering-only wording"))
    code, out = run(["check", df2, "--goal", root])
    assert code == 0, out

    # control: a `source:` naming a file that does not exist is NOT routing
    df3 = delta_file(root, "deltas-widget-smith-round-3.md",
                     block(1, SEAT, frm, to, source="planning/current/no-such-file.md"))
    code, out = run(["check", df3, "--goal", root])
    assert codes(out) == ["source-not-routed"], out
    shutil.rmtree(root)


@arm
def R5b_target_missing_and_malformed():
    """The two precondition codes: an unresolvable target and a delta missing its fences."""
    root = goal_with()
    df = delta_file(root, "deltas-widget-smith-round-1.md",
                    block(1, "planning/current/seats/ghost/task.md", "x", "y"))
    code, out = run(["check", df, "--goal", root])
    assert codes(out) == ["target-missing"], out

    df = delta_file(root, "deltas-widget-smith-round-2.md",
                    "## delta 1\ntarget: %s\n```from\n\n```\n" % SEAT)
    code, out = run(["check", df, "--goal", root])
    assert codes(out) == ["malformed-delta"], out
    assert "```to" in out, out

    # an escape out of the goal folder is refused, never followed
    df = delta_file(root, "deltas-widget-smith-round-3.md", block(1, "../../../etc/hosts", "x", "y"))
    code, out = run(["check", df, "--goal", root])
    assert codes(out) == ["target-missing"], out
    shutil.rmtree(root)


@arm
def G1_green_and_idempotence():
    """Clean check -> apply -> the record names file, span and heading -> re-check is already-applied."""
    root = goal_with()
    frm = "Every arm names its id."
    to = "Every arm names its id and the criterion it serves."
    df = delta_file(root, "deltas-widget-smith-round-1.md", block(1, SEAT, frm, to))
    code, out = run(["check", df, "--goal", root])
    assert code == 0 and out.strip().endswith("0 finding(s)"), out

    code, out = run(["apply", df, "--goal", root])
    assert code == 0, out
    body = open(os.path.join(root, SEAT)).read()
    assert body.count(to) == 1 and body.count(frm) == 0, body

    rec = json.load(open(os.path.join(root, "applied-deltas-widget-smith-round-1.json")))
    assert len(rec) == 1, rec
    assert rec[0]["target"] == SEAT, rec
    assert rec[0]["source"] == "planning/current/task-dag.md", rec
    assert rec[0]["section"] == "## Criterion 3 - the fixture set", rec
    assert rec[0]["start_line"] == rec[0]["end_line"] == 5, rec
    assert body.splitlines()[rec[0]["start_line"] - 1] == to, rec

    code, out = run(["check", df, "--goal", root])
    assert code == 1 and codes(out) == ["already-applied"], out
    shutil.rmtree(root)


@arm
def G2_atomicity():
    """One bad delta in a two-delta file modifies NEITHER target."""
    root = goal_with()
    other = "planning/current/seats/gadget-smith/task.md"
    os.makedirs(os.path.dirname(os.path.join(root, other)))
    open(os.path.join(root, other), "w").write(TARGET_TEXT)
    before = {p: sha(os.path.join(root, p)) for p in (SEAT, other)}
    df = delta_file(root, "deltas-widget-smith-round-1.md",
                    block(1, SEAT, "Every arm names its id.", "Every arm names its own id.")
                    + block(2, "planning/current/seats/ghost/task.md", "x", "y"))
    code, out = run(["apply", df, "--goal", root])
    assert code == 1, out
    assert "REFUSED" in out and "target-missing" in out, out
    after = {p: sha(os.path.join(root, p)) for p in (SEAT, other)}
    assert before == after, "apply is all-or-nothing"
    assert not os.path.exists(os.path.join(root, "applied-deltas-widget-smith-round-1.json"))
    shutil.rmtree(root)


@arm
def G3_apply_needs_a_round_number():
    """The record's name carries the round — a delta file that cannot name it is BLOCKED."""
    root = goal_with()
    df = delta_file(root, "deltas-widget-smith.md",
                    block(1, SEAT, "Every arm names its id.", "Every arm names its own id."))
    assert delta_anchors.main(["apply", df, "--goal", root]) == 2
    assert delta_anchors.main(["check", df, "--goal", "/no/such/goal"]) == 2
    shutil.rmtree(root)


@arm
def G4_multi_seat_same_round_two_records():
    """task 130 defect 1: two seats returning edits in the SAME round must not collide on one filename."""
    root = goal_with()
    other = "planning/current/seats/gadget-smith/task.md"
    os.makedirs(os.path.dirname(os.path.join(root, other)))
    open(os.path.join(root, other), "w").write(TARGET_TEXT)
    df1 = delta_file(root, "deltas-widget-smith-round-1.md",
                     block(1, SEAT, "Every arm names its id.", "Every arm names its own id."))
    df2 = delta_file(root, "deltas-gadget-smith-round-1.md",
                     block(1, other, "Every arm names its id.", "Every arm names a distinct id."))
    assert run(["apply", df1, "--goal", root])[0] == 0
    assert run(["apply", df2, "--goal", root])[0] == 0
    rec1 = os.path.join(root, "applied-deltas-widget-smith-round-1.json")
    rec2 = os.path.join(root, "applied-deltas-gadget-smith-round-1.json")
    assert os.path.exists(rec1) and os.path.exists(rec2), \
        "two same-round records must both survive — the second must not overwrite the first"
    assert json.load(open(rec1))[0]["target"] == SEAT
    assert json.load(open(rec2))[0]["target"] == other
    shutil.rmtree(root)


@arm
def G5_record_beside_delta_not_hardcoded_current():
    """task 130 defect 2: re-applying deltas against an ALREADY-ARCHIVED milestone (meet's m4
    re-check case) must write the record beside that archived delta file — not at a hardcoded
    goal/planning/current/, which by then belongs to a different, live milestone."""
    root = goal_with()
    # a prior milestone was already promoted: its target + delta live under an archive folder,
    # NOT under planning/current — planning/current/ now belongs to the NEXT, unrelated milestone
    archived_target = "planning/archive-m1/seats/widget-smith/task.md"
    os.makedirs(os.path.dirname(os.path.join(root, archived_target)))
    open(os.path.join(root, archived_target), "w").write(TARGET_TEXT)
    df = delta_file(root, "planning/archive-m1/deltas-widget-smith-round-1.md",
                    block(1, archived_target, "Every arm names its id.", "Every arm names its own id."))

    live_current_before = set(os.listdir(os.path.join(root, "planning", "current")))
    assert run(["apply", df, "--goal", root])[0] == 0

    beside_rec = os.path.join(root, "planning", "archive-m1", "applied-deltas-widget-smith-round-1.json")
    assert os.path.exists(beside_rec), \
        "the record must land beside the archived delta file it describes, not under " \
        "goal/planning/current/ (which now belongs to a different, live milestone): " + beside_rec
    live_current_after = set(os.listdir(os.path.join(root, "planning", "current")))
    assert live_current_after == live_current_before, \
        "the live, unrelated planning/current/ of the NEXT milestone must be untouched"
    shutil.rmtree(root)


@arm
def G6_crlf_target_keeps_crlf_and_touches_only_the_edited_span():
    """task 130 defect 3: a CRLF target must not come back entirely LF."""
    root = goal_with()
    full = os.path.join(root, SEAT)
    with open(full, "wb") as fh:
        fh.write(TARGET_TEXT.replace("\n", "\r\n").encode("utf-8"))
    frm, to = "Every arm names its id.", "Every arm names its id and the criterion it serves."
    before_lines = open(full, "rb").read().decode("utf-8").split("\r\n")
    df = delta_file(root, "deltas-widget-smith-round-1.md", block(1, SEAT, frm, to))
    code, out = run(["apply", df, "--goal", root])
    assert code == 0, out
    after_raw = open(full, "rb").read()
    assert b"\r\n" in after_raw and b"\r\r\n" not in after_raw, \
        "the target must stay CRLF, not come back entirely LF"
    after_lines = after_raw.decode("utf-8").split("\r\n")
    changed = [i for i in range(min(len(before_lines), len(after_lines))) if before_lines[i] != after_lines[i]]
    assert changed == [4], ("only the edited line should differ", before_lines, after_lines)
    assert to in after_raw.decode("utf-8")
    shutil.rmtree(root)


@arm
def G6b_lf_target_stays_lf():
    """The LF counterpart of G6 — an LF target must not gain CRLF endings."""
    root = goal_with()
    frm, to = "Every arm names its id.", "Every arm names its id and the criterion it serves."
    df = delta_file(root, "deltas-widget-smith-round-1.md", block(1, SEAT, frm, to))
    assert run(["apply", df, "--goal", root])[0] == 0
    after_raw = open(os.path.join(root, SEAT), "rb").read()
    assert b"\r\n" not in after_raw, "an LF target must not gain CRLF endings"
    assert after_raw.decode("utf-8") == TARGET_TEXT.replace(frm, to)
    shutil.rmtree(root)


if __name__ == "__main__":
    failed = 0
    for fn in ARMS:
        try:
            fn()
            print("ok   %s" % fn.__name__)
        except AssertionError as exc:
            failed += 1
            print("FAIL %s: %s" % (fn.__name__, exc))
    print("%d arm(s), %d failed" % (len(ARMS), failed))
    sys.exit(1 if failed else 0)
