#!/usr/bin/env python3
"""owed-answers — the owner's owed answers, across every live coordination package, in one command.

WHY THIS EXISTS (measured 2026-08-12, ignite session log `6371e7ba`): the channel master's
`seat.md` § 1 requires it to state the owner's owed answers at cold contact, "derived from the
threads store's owed-answers derivation" — and named no command. So every Slack DM re-derived the
set by EXPLORATION: full-vault `rg` sweeps, a `find` for every goal, three `sqlite3` loops over
`threads.sql` files that are not databases, `coordinate --help`. Nineteen sequential shell commands,
~120 s of a ~131 s turn, before the first word of an answer. The set itself is one predicate that
was already built. This script is the missing NAME for it.

⚑ IT RE-IMPLEMENTS NOTHING. `coord.open_asks(..., to="owner")` IS the derivation — the same
predicate `pending` and the check-out hold both run, carrying supersede handling and `re:` closure.
This file only ENUMERATES the packages and merges their results (PRIN-11: one implementation).

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
            if name:
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


def collect(coord, workspace, only=None):
    """Every open ask addressed to the owner, oldest first, plus the packages that could not be
    read. An unreadable package is COUNTED and disclosed, never dropped: an absence that reads as
    "no debt" when it really means "could not look" is the one wrong answer this must not give."""
    rows, unreadable = [], []
    for label, base in packages(workspace, only):
        try:
            _, blocks = coord.load_messages(base)
            for b in coord.open_asks(blocks, to=OWNER):
                rows.append({
                    "label": label,
                    "num": b["num"],
                    "sender": b["sender"],
                    "age": coord.age_of(b["ts"]),
                    "body": coord.truncate(coord.body_of(b)),
                })
        except Exception as exc:                      # noqa: BLE001 — one bad package never hides the rest
            unreadable.append(f"{label}: {exc}")
    rows.sort(key=lambda r: age_minutes(r["age"]), reverse=True)
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
            lines.append(f"- {r['age']} old · {r['sender']} ({r['label']}) · {r['body']} "
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
