#!/usr/bin/env python3
"""cagespec.py — THE ONE PYTHON READING OF `cage.SeatBinds`, GOAL-RELATIVE.

WHAT THIS IS. `server/spawn/cage.js#composeSeatCage` is the daemon's cage composer and stays the
only thing that composes a real bwrap spec. This module is its MIRROR for the two Python gates that
must answer "is this goal-relative path writable / readable in the seat cage?" BEFORE any process
exists. Its ONE caller today is `team-kit/materialize-seats.py`'s generation-time preflight; a
second reading in it would be a second place the wall is reasoned about, which is the defect the
shared reader exists to remove.

⚠ ITS SECOND CALLER — `jobs/edge-runner-job.py`'s enqueue-time declared-output admission check —
WAS DELETED (`build/one-readiness-predicate.md`). Its successor `engine/cage-admission.js` drives
`cage.js#composeSeatCage` LIVE in JavaScript rather than mirroring it, which is the improvement the
ruling names. So the two admission gates no longer share this evaluator: they share the TEMPLATE
(`cage.SeatBinds`), and this module is now one side of a mirror whose held-against check went with
the file that held it (see 1 below).

⚠ IT IS A MIRROR, AND MIRRORS DRIFT. Two things held it against `cage.js`:
  1. ⚠ GONE. `edge-runner-job.py#check_deriver_mirrors_the_composer` drove the REAL `composeSeatCage`
     through node over the LIVE SeatBinds and asserted this module's `compose` matched it
     entry-for-entry after re-rooting — and that every entry this module DROPS resolves outside the
     goal folder under node. A verb, slot or grant class added to the template turned that check
     red. It was deleted with its file and NOTHING replaces it: this mirror is currently unpinned,
     and a template change can now diverge silently on the Python side. Filed, not fixed here.
  2. Everything underivable is UNDECIDED, and undecided REFUSES at every caller. An unknown verb, an
     unknown slot, an unknown `{grant:FIELD}`, a malformed entry, an escaping token or an empty
     template all return `None`/`undecided` rather than a guess. Fail-closed here is load-bearing:
     a token that reads admissible on paper but is unwritable in fact turns a gap into a green.

WHY GOAL-RELATIVE. The callers hold goal-relative tokens (`issues.md`, `coordination/p-a.json`,
`seats/<seat>/x.json`) and no absolute paths at all — there is no goal folder on disk at the moment
either gate runs. So this module resolves the template's `{goalDir}` to `""` and its `{seatDir}` /
`{workdir}` to `seats/<seat>`, and DROPS every entry that composes outside the goal folder by
construction. Dropping is not ignoring: each dropped class is named below with the reason its
absence cannot change a goal-relative verdict, and check #1 above re-derives every drop through the
real composer rather than trusting this comment.

THE READING IS `cage.js`'s OWN AND MUST STAY IT: input order is output order, and the LAST entry
covering a path decides what that path IS — `assertGroundTruthUnwritable`'s reading. A `tmpfs` or a
`ro-bind` placed after an opening takes it back. That is why ground truth needs no list here:
`sessions.csv` and `state.csv` are carved back read-only immediately after the `goal-writes` line,
peer seat folders sit under the `seats` tmpfs, and `seat.md` under its own carve — each answers
"not writable" by POSITION, with nobody restating it.

No yaml, no node, no filesystem: this module is pure so both hosts can call it from wherever they
already loaded the template. `python3 cagespec.py` runs its own asserts.
"""

from __future__ import annotations

import re

# The bind verbs a template may declare, and the two that open a path READ-WRITE. Both are
# `cage.js`'s vocabulary (`BIND_VERBS` / `RW_VERBS`), mirrored here because the gates and the
# emitter sit on opposite sides of a language boundary. `bind-try` COUNTS AS RW: when the source is
# there the opening is read-write, and a reader that treated it as anything else would drift from
# the wall on every one of the five goal-root ledgers.
RW_VERBS = ("bind", "bind-try")
BIND_VERBS = ("ro-bind", "ro-bind-try", "bind", "bind-try", "tmpfs")

# THE DISTINCT-SUCCESSOR SENTINEL. `readable-by-a-successor` is the SAME composition asked with a
# different occupant, so it is `evaluate(..., seat=PEER, goal_writes=())` and not a second table. A
# successor's list differs from the producer's in exactly two lines — `{seatDir}` and
# `{grant:goalWrite}` — and both moves err CLOSED: `seats/ peer` can never cover the producer's own
# seat folder (the `seats` tmpfs stays the last cover there, so the answer is `absent`), and
# omitting the successor's own goal-writes grant can only under-report what it may write.
# ⚠ The space is deliberate: a seat name can never contain one, so this sentinel can never collide
# with a real seat, and `materialize-seats.py` reuses it as its "no particular occupant" seat.
PEER = " peer"

# `{grant:FIELD}` — the one PARAMETERIZED slot form (`cage.js` GRANT_SLOT_RE). An entry carrying it
# is expanded once per grant rather than once.
_GRANT_SLOT = re.compile(r"\{grant:([a-zA-Z][a-zA-Z0-9_]*)\}")

# THE ONE GRANT CLASS THAT LANDS INSIDE THE GOAL FOLDER (owner ruling D9): the seat's declared
# `goal-writes` path. Its template entry composes one opening per declared item — zero items, zero
# openings, and no special case.
GOAL_WRITE_GRANT = "goalWrite"

# THE GRANT CLASSES DROPPED, each with the reason its absence cannot change a goal-relative verdict.
# ⚠ THIS TUPLE IS A CLAIM ABOUT THE COMPOSER, NOT A PREFERENCE, and it is re-derived through the
# real `composeSeatCage` by `check_deriver_mirrors_the_composer` — a class added here without that
# check agreeing is a hole nobody sees.
#   readRoot                — the workspace root, READ-ONLY, first in the stack; the goal folder is
#                             inside it and `ro-bind:{goalDir}` re-covers it identically. Same
#                             verdict either way.
#   busWrite                — the seat's OWN goal resolves to the same path the literal
#                             `bind:{goalDir}/coordination` line already opens; every OTHER goal is
#                             outside this goal folder.
#   goalsWrite              — `resolveGoalsWriteGrants` EXCLUDES the seat's own goal, so every
#   goalsWriteGroundTruth     opening of this class (and its carve) lies outside this goal folder.
#   worktree · repoGit      — worktrees, git plumbing, harness credentials, `~/.local/bin` and
#   worktreeGitDir            tmux's socket dir are outside the goals tree by construction.
#   harnessCreds · localBin
#   tmuxSocketDir
#   rwPath                  — `resolveRwPathGrants` REFUSES any entry overlapping `<ws>/.rbtv/goals`
#                             in either direction, so an rw-paths opening can never reach a goal
#                             folder. (⚠ Not listed in the IPH-2 design's drop table — an omission
#                             there, not a new class: it is in the live template and its refusal
#                             rule is the same "outside by construction" the row above states.)
DROPPED_GRANTS = ("readRoot", "busWrite", "goalsWrite", "goalsWriteGroundTruth",
                  "worktree", "repoGit", "worktreeGitDir", "harnessCreds",
                  "localBin", "tmuxSocketDir", "rwPath")

# THE ONE GRANT CLASS THAT IS NEITHER DROPPED NOR THE GOAL-WRITES FAN-OUT (W3, adv C34). It lands
# INSIDE the goal folder — `{goalDir}/coordination/permission-edits.csv` — so dropping it would be
# the one thing the table above cannot say about a class: that its absence cannot change a
# goal-relative verdict. It is the leader's audit file, carved back READ-ONLY for every seat that
# is not the permission editor (`spawn.js#resolvePermissionEditsRoGrant` /
# `PERMISSION_EDITOR_SEAT`), after the `coordination` opening that would otherwise make every
# audited party a writer of its own audit.
#
# ⚠ WITHOUT THIS BRANCH THE WHOLE TEMPLATE FAILS CLOSED, and that is measured, not feared: an
# unknown grant field returns None from `compose`, so EVERY goal-relative token — `taskforce.csv`,
# the five ledgers, the planning workspace — evaluates `undecided`, and
# `materialize-seats.py`'s preflight then refuses `cage-goal-writes-ungranted` for every seat that
# declares an output. Template growth failing closed is the design; a growth that fails closed
# SILENTLY and universally is what this branch (and the selftest's CG-1/CG-2 rows) catches.
#
# The JS emits no grant when the file does not exist. Modeling the carve unconditionally is the
# fail-CLOSED direction of that difference — this reader may under-report a write, never invent one.
PERMISSION_EDITS_GRANT = "permissionEditsRo"
PERMISSION_EDITS_REL = "coordination/permission-edits.csv"
PERMISSION_EDITOR_SEAT = "leader"

WRITABLE = "writable"
READONLY = "readonly"
ABSENT = "absent"
UNDECIDED = "undecided"


def _rel(path):
    """A goal-relative path in canonical form, or None when it is not one.

    None is the fail-closed answer for absolute paths and for anything climbing out with `..` —
    both are underivable here, and neither may resolve to a lexical prefix of something inside the
    goal by accident."""
    if not isinstance(path, str):
        return None
    if path.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", path):
        return None
    parts = []
    for seg in path.replace("\\", "/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            return None
        parts.append(seg)
    return "/".join(parts)


def _seat_folder(seat):
    """`seats/<seat>`, or None for a seat name this reader cannot place (case 6, fail-closed)."""
    if not isinstance(seat, str) or not seat.strip() or "/" in seat or seat.strip() in (".", ".."):
        return None
    return "seats/" + seat


def _resolve_scalar(template, seat):
    """The goal-relative path a SCALAR-slotted template composes to, or None (undecided).

    `{workdir}` resolves to the seat folder exactly as it does in `cage.js` — the vocabulary the
    rest of the config already speaks. A template carrying no known scalar slot (an unknown slot, or
    a literal absolute path) is UNDECIDED rather than dropped: an unknown slot silently resolving to
    nothing is how a cage opens a hole nobody sees."""
    if template == "{goalDir}" or template.startswith("{goalDir}/"):
        return _rel(template[len("{goalDir}"):].lstrip("/"))
    for slot in ("{seatDir}", "{workdir}"):
        if template == slot or template.startswith(slot + "/"):
            home = _seat_folder(seat)
            if home is None:
                return None
            return _rel(home + "/" + template[len(slot):].lstrip("/"))
    return None


def compose(seat_binds, *, seat, goal_writes=()):
    """The ORDERED goal-relative spec `seat_binds` composes for `seat`, or None when undecidable.

    `[(verb, goal-relative path)]`, input order preserved — the goal root is `""`. None means the
    template carries something this reader cannot derive, and every caller REFUSES on it rather than
    picking a side: the whole point of the derivation is that a wall nobody can read is not a wall
    that may be assumed open.

    ⚠ AN EMPTY OR NON-LIST `seat_binds` IS None, NOT AN EMPTY SPEC. A half-answered probe
    (`caged: true` with no binds) would otherwise compose a cage in which nothing is covered and
    every token reads `absent` — a confident refusal of everything, arrived at from a missing
    measurement. Undecided is the honest verdict for it."""
    if not isinstance(seat_binds, (list, tuple)) or not seat_binds:
        return None
    spec = []
    for entry in seat_binds:
        if not isinstance(entry, str) or ":" not in entry:
            return None
        verb, _, template = entry.partition(":")
        if verb not in BIND_VERBS or not template:
            return None
        fields = _GRANT_SLOT.findall(template)
        if fields:
            if fields == [PERMISSION_EDITS_GRANT]:
                if template != "{grant:%s}" % PERMISSION_EDITS_GRANT:
                    return None               # welded onto a path: not this reading
                if seat != PERMISSION_EDITOR_SEAT:
                    spec.append((verb, PERMISSION_EDITS_REL))
                continue
            if any(f not in DROPPED_GRANTS and f != GOAL_WRITE_GRANT for f in fields):
                return None                       # template GROWTH fails closed, by construction
            if any(f in DROPPED_GRANTS for f in fields):
                continue                          # composes outside the goal folder (see the table)
            if template != "{grant:%s}" % GOAL_WRITE_GRANT:
                return None                       # the grant welded onto a path: not this reading
            for item in goal_writes:
                path = _rel(item)
                if not path:
                    return None
                spec.append((verb, path))
            continue
        path = _resolve_scalar(template, seat)
        if path is None:
            return None
        spec.append((verb, path))
    return spec


def evaluate(seat_binds, token, *, seat, goal_writes=()):
    """`(verdict, deciding-entry)` for ONE goal-relative token. THE CAGE'S OWN READING, as code.

    Verdict is `writable` | `readonly` | `absent` | `undecided`. The LAST entry covering the token
    decides — `cage.js#assertGroundTruthUnwritable`'s reading, and the reason a `ro-bind-try` carve
    placed after the `goal-writes` grant takes that grant back BY POSITION rather than by a second
    list. Nothing covering the token means nothing bound it: `absent`, which is not writable and not
    readable.

    The deciding entry is returned in the template's own vocabulary (`bind:{goalDir}/coordination`)
    so a refusal carrying it needs no second document to be read against."""
    spec = compose(seat_binds, seat=seat, goal_writes=goal_writes)
    if spec is None:
        return (UNDECIDED,
                "the cage template does not compose goal-relative under this reader — an unknown "
                "verb, slot or grant field, a malformed entry, or an empty `SeatBinds`")
    path = _rel(token)
    if not path:
        return (UNDECIDED,
                "`%s` is absolute, escapes the goal folder with `..`, or names the goal root "
                "itself — no composed entry can be said to cover it" % (token,))
    hit = None
    for verb, p in spec:
        if p == "" or p == path or path.startswith(p + "/"):
            hit = (verb, p)                       # last covering entry wins
    if hit is None:
        return (ABSENT, "no composed entry covers `%s` — absent by construction" % (token,))
    verb, p = hit
    where = "%s:{goalDir}%s" % (verb, "/" + p if p else "")
    if verb in RW_VERBS:
        return (WRITABLE, where)
    if verb == "tmpfs":
        return (ABSENT, where)
    return (READONLY, where)


def seat_declares_list(seat_md_text, key):
    """The Python half of `spawn.js#seatDeclaresList` — a frontmatter block list, same grammar.

    Same surface (seat.md frontmatter, ro-bound inside the cage), same lightweight parse, same
    fail-closed absence: no frontmatter, no key, or a mis-indented entry yields `[]` rather than a
    guess. The block ends at the first line that is not a `- item`, so a malformed entry ends the
    list instead of swallowing the keys after it."""
    m = re.match(r"^---\n([\s\S]*?)\n---", seat_md_text or "")
    if not m:
        return []
    items, in_block = [], False
    for line in m.group(1).split("\n"):
        if not in_block:
            if re.match(r"^%s:\s*$" % re.escape(key), line):
                in_block = True
            continue
        item = re.match(r"^\s*-\s*(.*)$", line)
        if not item:
            break
        items.append(re.sub(r"^[\"']|[\"']$", "", item.group(1).strip()))
    return items


if __name__ == "__main__":
    # A SIX-LINE FIXTURE carrying every shape the live template uses: a dropped grant, the goal
    # floor, the goal-writes grant, a carve that takes it back, the peer-seat tmpfs, and the seat's
    # own folder. Small enough to read, complete enough that every branch below is exercised on it.
    FX = [
        "ro-bind:{grant:readRoot}",
        "ro-bind:{goalDir}",
        "bind-try:{grant:goalWrite}",
        "ro-bind-try:{goalDir}/sessions.csv",
        "tmpfs:{goalDir}/seats",
        "bind:{seatDir}",
    ]

    # COMPOSITION — the dropped grant leaves no entry; the goal root is `""`.
    assert compose(FX, seat="p") == [("ro-bind", ""), ("ro-bind-try", "sessions.csv"),
                                     ("tmpfs", "seats"), ("bind", "seats/p")]
    # GRANT FAN-OUT 0 / 1 / 2 — one opening per declared item, and no special case at zero.
    assert len(compose(FX, seat="p", goal_writes=["goal.md"])) == 5
    assert len(compose(FX, seat="p", goal_writes=["goal.md", "notes/x.md"])) == 6

    # ORDERING TAKE-BACK — the carve after the grant wins BY POSITION, with no second list.
    assert evaluate(FX, "goal.md", seat="p", goal_writes=["goal.md"])[0] == WRITABLE
    assert evaluate(FX, "sessions.csv", seat="p", goal_writes=["sessions.csv"])[0] == READONLY
    # …and `bind-try` COUNTS AS RW: the assert above would read `readonly` if it did not.
    assert evaluate(FX, "goal.md", seat="p")[0] == READONLY          # no grant -> the ro floor

    # tmpfs -> ABSENT, and it is the last cover over a peer's folder.
    assert evaluate(FX, "seats/q/a.json", seat="p")[0] == ABSENT
    assert evaluate(FX, "seats/p/a.json", seat="p")[0] == WRITABLE
    # THE SENTINEL NEVER COVERS THE PRODUCER'S OWN SEAT FOLDER — the successor reading errs closed.
    assert evaluate(FX, "seats/p/a.json", seat=PEER)[0] == ABSENT

    # THE PERMISSION-EDITS CARVE (W3): goal-relative, occupant-dependent, and it must NOT poison the
    # rest of the template — the arm that would have caught the live regression it was landed with.
    PE = ["ro-bind:{goalDir}", "bind:{goalDir}/coordination",
          "ro-bind-try:{grant:permissionEditsRo}", "bind-try:{grant:goalWrite}"]
    assert evaluate(PE, PERMISSION_EDITS_REL, seat="p")[0] == READONLY
    assert evaluate(PE, PERMISSION_EDITS_REL, seat=PERMISSION_EDITOR_SEAT)[0] == WRITABLE
    assert evaluate(PE, "coordination/messages.md", seat="p")[0] == WRITABLE
    assert evaluate(PE, "taskforce.csv", seat="p",
                    goal_writes=["taskforce.csv"])[0] == WRITABLE

    # FAIL-CLOSED: unknown verb, unknown scalar slot, unknown grant field, empty template.
    assert compose(["mount:{goalDir}"], seat="p") is None
    assert compose(["bind:{runDir}/x"], seat="p") is None
    assert compose(["bind:{grant:futureCageThing}"], seat="p") is None
    assert compose([], seat="p") is None
    assert evaluate(["bind:{grant:futureCageThing}"], "issues.md", seat="p")[0] == UNDECIDED
    # …and a token that is absolute or climbs out of the goal folder.
    assert evaluate(FX, "/etc/passwd", seat="p")[0] == UNDECIDED
    assert evaluate(FX, "../outside/x.json", seat="p")[0] == UNDECIDED
    # An unplaceable seat name is undecided too, not a bare `seats/`.
    assert evaluate(FX, "seats/p/a.json", seat="")[0] == UNDECIDED

    # THE DECIDING ENTRY reads in the template's own vocabulary.
    assert evaluate(FX, "seats/p/a.json", seat="p")[1] == "bind:{goalDir}/seats/p"

    # The frontmatter reader, in both directions.
    assert seat_declares_list("---\ngoal-writes:\n  - \"goal.md\"\n---\nbody\n",
                              "goal-writes") == ["goal.md"]
    assert seat_declares_list("---\nseat: p\n---\n", "goal-writes") == []

    print("cagespec: %d asserts hold" % 24)
