#!/usr/bin/env python3
"""owed-answers — the owner's owed answers, across every live coordination package, in one command.

WHY THIS EXISTS (measured 2026-08-12, ignite session log `6371e7ba`): the channel master's
`seat.md` § 1 requires it to state the owner's owed answers at cold contact, "derived from the
threads store's owed-answers derivation" — and named no command. So every Slack DM re-derived the
set by EXPLORATION: full-vault `rg` sweeps, a `find` for every goal, three `sqlite3` loops over
`threads.sql` files that are not databases, `coordinate --help`. Nineteen sequential shell commands,
~120 s of a ~131 s turn, before the first word of an answer. The set itself is one predicate that
was already built. This script is the missing NAME for it.

⚑ IT RE-IMPLEMENTS NOTHING. The derivation is the UNION of the store's two owner-debt predicates:
`coord.open_asks(..., to="owner")` — the same predicate `pending` and the check-out hold both run —
and `coord.open_escalations`, whose rows are halts and are shown as such. Both carry supersede
handling and `re:` closure. The union lives HERE, never in `open_asks`: ruling `p-owed-answers-locus`
forbids widening that predicate, because four hold gates read it and a widened one self-deadlocks the
escalating seat. This file only ENUMERATES the packages and merges their results (PRIN-11: one
implementation).

⚑ THE ENUMERATOR IS `goals.csv` PLUS EACH GOAL'S `runs.csv` — never a glob of the goals tree. A
glob walks into seat scratch folders holding throwaway fixture packages (a dozen under one run of
`build-core-daemon-mvp` alone), and a search of the wrong places returns the same empty result as a
search of the right ones.

Presentation follows `seat.md` § 1 exactly: the count first, then the oldest-first list capped at 5,
one line per item with its thread pointer. The empty state is EXPLICIT (`no owed answers`) so a
reader can tell "nothing is owed" from "this did not run".

    owed-answers                      # every live package under the workspace
    owed-answers --package NAME|DIR   # ONE goal package (a run-scoped seat asks only about its own)
    owed-answers --workspace DIR      # another workspace
    owed-answers --selfcheck          # the runnable check (asserts sane output, and that it is fast)
"""
import argparse
import importlib.util
import pathlib
import shutil
import sys
import time

CAP = 5  # seat.md § 1: oldest-first, capped at 5
OWNER = "owner"  # the reserved address every seat asks the human at (`d-agents-address-owner-not-master`)


def load_coord():
    """Import `coord.py` beside this script as a module. It is a script by shape but a library by
    content — every function this file needs is module-level and its `main()` is `__main__`-gated."""
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("coord", here / "coord.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def packages(workspace, only=None):
    """(label, coordination-dir) for every package the owner can be owed an answer from, optionally
    restricted to ONE goal by `only` — a label (`my-goal`, `my-goal/run-2`) or a folder path. A goal
    matches its own package AND its open runs, so a run-scoped seat naming its goal sees its run.

    ponytail: CLOSED runs are skipped — an ask inside a finished run is not a live debt. If a closed
    run's asks ever need surfacing, drop the `state == "open"` filter."""
    goals = pathlib.Path(workspace) / ".rbtv" / "goals"
    names = ["_channel-master"]
    index = goals / "goals.csv"
    if index.exists():
        for line in index.read_text(encoding="utf-8").splitlines()[1:]:
            name = line.split(",")[0].strip()
            # `_channel-master` is seeded above AND now carries a `goals.csv` row — enumerating it
            # twice double-counts every debt row in that package (caught by the `--package` arm).
            if name and name not in names:
                names.append(name)

    found = []

    def add(directory, label):
        base = directory / "coordination"
        if (base / "messages.md").exists():
            found.append((label, base))

    for name in names:
        goal_dir = goals / name
        add(goal_dir, name)
        runs = goal_dir / "runs.csv"
        if not runs.exists():
            continue
        for line in runs.read_text(encoding="utf-8").splitlines()[1:]:
            cols = line.split(",")
            if len(cols) < 3 or cols[2].strip() != "open":
                continue
            add(goal_dir / "runs" / cols[0].strip(), f"{name}/{cols[0].strip()}")
    if only is None:
        return found
    target = pathlib.Path(only).expanduser()
    if target.is_dir():
        target = target.resolve()
        return [(l, b) for l, b in found if b.parent == target or target in b.parents]
    return [(l, b) for l, b in found if l == only or l.startswith(only + "/")]


def age_minutes(age):
    """Minutes from `coord.age_of`'s vocabulary, which emits only `<n>m`, `<n>h` or `?`. An
    unparseable age sorts OLDEST — an item we cannot age is not one to hide behind four we can."""
    if age.endswith("h") and age[:-1].isdigit():
        return int(age[:-1]) * 60
    if age.endswith("m") and age[:-1].isdigit():
        return int(age[:-1])
    return sys.maxsize


def collect_unanswered_asks(label, base):
    """D57/D75, widened D89 Q4 — the OTHER direction: every owner ask TO `goal-master` nothing has
    answered yet. Several can be open at once (Q4: a second owner message arriving before the
    first is answered is QUEUED alongside it, never overwrites it) — this returns ONE row per open
    ask, oldest first, each carrying its own id as `num` so a reader can tell them apart.

    A NEW union member, never a widen of `coord.open_asks` (`p-owed-answers-locus` forbids that —
    four hold gates read it). Read-only over `ignite/bridges/chat/ask-store.js`'s ONE file; a
    missing or malformed file is an ABSENT ask, never an error — the caller's `except Exception`
    still owns genuine unreadability (a directory that exists but is not a file, a permissions
    error), this function's own job is only to make "the file simply is not there yet" silent.

    `store[seat]` may be EITHER shape: the current D89-Q4 list, or the pre-D89 legacy shape (one
    bare entry object, not a list) — normalized the same way `coord.py#_owner_asks_entries` does,
    so the two readers of this one file never disagree on what a legacy record means."""
    import json
    p = base / "owner-asks.json"
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        store = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(store, dict):
        return []
    rows = []
    for seat, val in store.items():
        if isinstance(val, list):
            entries = [e for e in val if isinstance(e, dict)]
        elif isinstance(val, dict):
            entries = [val]  # legacy pre-D89 shape: one bare entry object per seat
        else:
            continue
        for i, entry in enumerate(entries, 1):
            if entry.get("status") != "open":
                continue
            text = str(entry.get("text") or "").strip()
            if not text:
                continue
            rows.append({
                "kind": "waiting",
                "label": label,
                "num": str(entry.get("id") or i),
                "sender": str(seat),
                "age": age_of_coord_ts(entry.get("askedAt") or ""),
                "body": text[:200],
            })
    return rows


def age_of_coord_ts(ts):
    """`coord.age_of` needs a live `coord` module handle this file does not carry at import time
    (it is loaded per-call via `load_coord()`), so the ONE parse this predicate needs — the same
    `YYYY-MM-DD HH:MM` local-clock format `ask-store.js#coordTimestamp` writes — is inlined rather
    than threading `coord` through one more argument for a single call."""
    import datetime
    try:
        dt = datetime.datetime.strptime(str(ts).strip(), "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return "?"
    mins = max(0, int((datetime.datetime.now() - dt).total_seconds() // 60))
    return f"{mins}m" if mins < 90 else f"{mins // 60}h"


def collect(coord, workspace, only=None):
    """Every open ask OR unanswered escalation addressed to the owner, PLUS an owner ask to
    `goal-master` nothing has answered — halts first, then oldest first within the rest, plus the
    packages that could not be read. An unreadable package is COUNTED and disclosed, never
    dropped: an absence that reads as "no debt" when it really means "could not look" is the one
    wrong answer this must not give."""
    rows, unreadable = [], []
    for label, base in packages(workspace, only):
        try:
            _, blocks = coord.load_messages(base)
            # An escalation is owner debt too — and it HALTS the run, so it is not the ask
            # predicate's business (`p-owed-answers-locus`: `coord.open_asks` must NOT be widened;
            # four hold gates read it, and widening self-deadlocks the escalating seat). The union
            # lives here. The two sets cannot overlap: `type == "ask"` vs `type == "escalation"`.
            owed = ([("ask", b) for b in coord.open_asks(blocks, to=OWNER)]
                    + [("halt", b) for b in coord.open_escalations(blocks)
                       if b["to"] == OWNER])
            for kind, b in owed:
                rows.append({
                    "kind": kind,
                    "label": label,
                    "num": b["num"],
                    "sender": b["sender"],
                    "age": coord.age_of(b["ts"]),
                    "body": coord.truncate(coord.body_of(b)),
                })
            rows.extend(collect_unanswered_asks(label, base))
        except Exception as exc:                      # noqa: BLE001 — one bad package never hides the rest
            unreadable.append(f"{label}: {exc}")
    # Halts FIRST, then oldest-first within each kind — reverse makes True (halt) lead and the
    # larger age lead. Without this a halt can be pushed off the CAP-5 list by five older asks,
    # which is the one row that must never be the one truncated away.
    rows.sort(key=lambda r: (r["kind"] == "halt", age_minutes(r["age"])), reverse=True)
    return rows, unreadable


def render(rows, unreadable):
    lines = []
    if not rows:
        lines.append("no owed answers")
    else:
        head = f"{len(rows)} owed answer{'' if len(rows) == 1 else 's'}"
        if len(rows) > CAP:
            head += f" — oldest {CAP} shown"
        lines.append(head)
        for r in rows[:CAP]:
            tag = ("⛔ RUN HALTED · " if r["kind"] == "halt"
                   else "⏳ AWAITING A REPLY FROM · " if r["kind"] == "waiting" else "")
            lines.append(f"- {tag}{r['age']} old · {r['sender']} ({r['label']}) · {r['body']} "
                         f"· answer in thread: {r['label']} #{r['num']}")
    for u in unreadable:
        lines.append(f"⚠ package unreadable, this list may be SHORT — {u}")
    return "\n".join(lines)


def selfcheck(coord, workspace, text, elapsed_ms, only=None):
    """THE runnable check. Runs against the REAL goals tree, because the failure this must catch is
    a digest that reports "no owed answers" for a MECHANICAL reason — a bad enumeration, a parse
    matching nothing, an import that resolved the wrong `coord`."""
    pkgs = packages(workspace, only)
    assert pkgs, f"no coordination packages enumerated under {workspace} (--package {only})"
    assert only is not None or any(label == "_channel-master" for label, _ in pkgs), \
        "the channel master's own package is not in the enumeration"
    assert hasattr(coord, "open_asks") and hasattr(coord, "load_messages"), \
        "coord.py did not import as a library — the derivation is not reachable"
    first = text.splitlines()[0]
    assert first == "no owed answers" or first.split(" ")[0].isdigit(), \
        f"digest has neither an explicit empty state nor a leading count: {first!r}"
    assert "unreadable" not in text, f"a package could not be read:\n{text}"
    if first != "no owed answers":
        # A counted digest must actually carry its items, each with a thread pointer.
        items = [ln for ln in text.splitlines() if ln.startswith("- ") and "answer in thread:" in ln]
        assert items, f"counted digest carries no well-formed item line:\n{text}"
        assert len(items) <= CAP, f"cap of {CAP} not applied: {len(items)} items"
    assert elapsed_ms < 3000, f"took {elapsed_ms} ms — too slow to sit at the head of a chat turn"

    # The `--package` filter, checked against the ONE package every workspace has. A filter that
    # matches EVERYTHING is a no-op; one that matches NOTHING turns a real debt into "no owed
    # answers" — and at the digest those two read exactly alike, which is why both are asserted.
    hits = packages(workspace, "_channel-master")
    assert [l for l, _ in hits] == ["_channel-master"], \
        f"--package _channel-master enumerated {[l for l, _ in hits]}"
    first_filtered = render(*collect(coord, workspace, "_channel-master")).splitlines()[0]
    assert first_filtered == "no owed answers" or first_filtered.split(" ")[0].isdigit(), \
        f"filtered digest is malformed: {first_filtered!r}"
    assert not packages(workspace, "no-such-goal"), \
        "an unmatched --package enumerated something — main's refusal would never fire"

    # THE ESCALATION ARM (G-owed-answers-0820-0345). An escalation to the owner HALTS the goal and
    # is not an `ask`, so the ask predicate cannot see it — this digest printed "no owed answers"
    # while #523 held `meet-transcript-summarizer`. Driven on a throwaway workspace so it
    # discriminates regardless of what the live tree happens to hold.
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="owed-answers-selfcheck-"))
    pkg = tmp / ".rbtv" / "goals" / "fixture" / "coordination"
    pkg.mkdir(parents=True)
    (tmp / ".rbtv" / "goals" / "goals.csv").write_text("goal\nfixture\n", encoding="utf-8")
    esc = ("## 1 | from: leader | to: owner | type: escalation | exec: e | 2026-08-20 03:34\n"
           "\nescalation: a ruling the run is halted on\n")
    ask = ("## 2 | from: leader | to: owner | type: ask | exec: e | 2026-08-20 03:40\n"
           "\nan ordinary ask\n")
    ans = ("## 3 | from: goal-master | to: leader | type: answer | re: 1 | exec: e | "
           "2026-08-20 04:12\n\nruled\n")

    def kinds(text):
        (pkg / "messages.md").write_text(text, encoding="utf-8")
        return [r["kind"] for r in collect(coord, str(tmp), "fixture")[0]]

    assert kinds(esc) == ["halt"], "an OPEN escalation to the owner is not owed debt"
    assert kinds(esc + "\n" + ans) == [], "an ANSWERED escalation is still reported owed"
    assert kinds(ask) == ["ask"], "the ask path changed"
    assert kinds(esc + "\n" + ask)[0] == "halt", "a halt did not sort above an ask"

    # THE OWNER-ASK ARM (D57/D75) — the OTHER direction. Both polarities, same fixture package,
    # so a wrong predicate that reports everything (or nothing) cannot pass by accident.
    import json
    open_ask = {"goal-master": {"seat": "goal-master", "goalId": "fixture", "text": "still open?",
                                 "status": "open", "askedAt": "2026-08-20 03:00", "answeredAt": None}}
    (pkg / "owner-asks.json").write_text(json.dumps(open_ask), encoding="utf-8")
    assert kinds("") == ["waiting"], "an OPEN unanswered owner ask is not reported owed"
    answered_ask = {"goal-master": {**open_ask["goal-master"], "status": "answered",
                                     "answeredAt": "2026-08-20 03:05"}}
    (pkg / "owner-asks.json").write_text(json.dumps(answered_ask), encoding="utf-8")
    assert kinds("") == [], "an ANSWERED owner ask is still reported owed"

    # D89 Q4 — THE QUEUE ARM: a second, different owner message arriving before the first is
    # answered is QUEUED alongside it, never overwrites it — both are reported owed, oldest
    # first, each its own row. Answering the OLDEST (ask-store.js#markAnswered's no-`askId`
    # rule — this fixture writes the file directly, mirroring what that call does) leaves
    # exactly the second one open. RED before D89 Q4 (the old single-object shape could not
    # even represent two open asks — the second write clobbered the first); GREEN now.
    queued = {"goal-master": [
        {"id": 1, "seat": "goal-master", "goalId": "fixture", "text": "ship today?",
         "status": "open", "askedAt": "2026-08-20 03:00", "answeredAt": None},
        {"id": 2, "seat": "goal-master", "goalId": "fixture", "text": "or wait for review?",
         "status": "open", "askedAt": "2026-08-20 03:10", "answeredAt": None},
    ]}
    (pkg / "owner-asks.json").write_text(json.dumps(queued), encoding="utf-8")
    (pkg / "messages.md").write_text("", encoding="utf-8")
    rows = collect(coord, str(tmp), "fixture")[0]
    bodies = [r["body"] for r in rows]
    assert len(rows) == 2 and all(r["kind"] == "waiting" for r in rows), \
        f"a queued pair of open asks is not both reported owed, one row each: {rows}"
    assert bodies == ["ship today?", "or wait for review?"], \
        f"a queued pair of open asks did not both render, oldest first: {bodies}"
    queued["goal-master"][0]["status"] = "answered"
    queued["goal-master"][0]["answeredAt"] = "2026-08-20 03:05"
    (pkg / "owner-asks.json").write_text(json.dumps(queued), encoding="utf-8")
    rows2 = collect(coord, str(tmp), "fixture")[0]
    assert [r["body"] for r in rows2] == ["or wait for review?"], \
        f"answering the OLDEST queued ask did not leave exactly the second one open: {rows2}"

    # Same arm, on the LEGACY pre-D89 single-object shape (`store[seat]` = one bare entry, not a
    # list) — it must still migrate and render, exactly as it did before this change.
    legacy = {"goal-master": {"seat": "goal-master", "goalId": "fixture", "text": "legacy shape ask",
                               "status": "open", "askedAt": "2026-08-20 02:00", "answeredAt": None}}
    (pkg / "owner-asks.json").write_text(json.dumps(legacy), encoding="utf-8")
    rows3 = collect(coord, str(tmp), "fixture")[0]
    assert [r["body"] for r in rows3] == ["legacy shape ask"], \
        f"the legacy pre-D89 single-object shape did not migrate/render: {rows3}"

    (pkg / "owner-asks.json").unlink()

    shutil.rmtree(tmp, ignore_errors=True)
    return f"OK — {len(pkgs)} package(s), {elapsed_ms} ms"


def main():
    coord = load_coord()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", default=coord.VAULT_ROOT,
                    help="workspace root holding .rbtv/goals (default: coord.py's)")
    ap.add_argument("--package", help="restrict the digest to ONE goal package: its label "
                                      "(`my-goal`, `my-goal/run-2`) or its folder path. A goal "
                                      "carries its own open runs.")
    ap.add_argument("--selfcheck", action="store_true", help="assert the digest is sane and fast")
    args = ap.parse_args()

    # An unmatched filter must REFUSE, never print "no owed answers": a typo'd package and a zero
    # debt are the same output, and the wrong one of them tells the owner nothing is owed.
    if args.package and not packages(args.workspace, args.package):
        print(f"error: --package {args.package} matched no coordination package under "
              f"{args.workspace}", file=sys.stderr)
        return 2

    started = time.time()
    rows, unreadable = collect(coord, args.workspace, args.package)
    text = render(rows, unreadable)
    elapsed_ms = int((time.time() - started) * 1000)

    print(text)
    if args.selfcheck:
        print()
        print(selfcheck(coord, args.workspace, text, elapsed_ms, args.package))
    return 0


if __name__ == "__main__":
    sys.exit(main())
