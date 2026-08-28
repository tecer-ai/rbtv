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

⚑ WHEN THE CAP TRUNCATES, THE HEADER STATES A NUMBER FOR EVERY COUNT THE VISIBLE LIST COULD BE
SUMMED INTO — one per kind, plus the goals the halts span. Measured 2026-08-26 (acceptance wave
test 2): the header carried only the OWED total, so the halted count existed NOWHERE but the
truncated list, and the channel master relayed the CAP as the halted count — "5 ⛔ RUN HALTED"
against ten real halts across three goals. A cap indistinguishable from a count is a wrong number,
not a short list. `--all` drops the cap entirely.

    owed-answers                      # every live package under the workspace
    owed-answers --all                # every row, never the cap
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
# One label per VISIBLE tag in the list below, in sort order. A reader can sum the shown rows of
# each of these, so the capped header must carry all three as numbers — see `render`. `{s}` is
# where the plural goes; a label that reads the same at any count simply has none.
KIND_LABELS = (("halt", "⛔ run-halted"), ("waiting", "⏳ awaiting a reply"), ("ask", "open ask{s}"))
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


def collect_unanswered_asks(label, base, coord=None):
    """The OTHER direction: every owner ask TO `goal-master` nothing has answered yet — ONE row per
    open ask, oldest first, each carrying its Slack thread id as `num` so a reader can tell them
    apart and reply in the right thread.

    A NEW union member, never a widen of `coord.open_asks` (`p-owed-answers-locus` forbids that —
    four hold gates read it). Read-only over the `open_asks` table in `.rbtv/runtime/ignite/heart.db`
    (spec-state-store §3); `ignite/bridges/chat/ask-store.js` is the ONE writer.

    ⚠ `owner-asks.json` IS GONE, and with it both shapes this used to normalize. The ONE record is
    the store row, `ask_id` IS the Slack thread [T5-R7], and the ask body is read back off
    `evidence_pointer` — §3 defines it as the thread permalink or the on-disk reply copy.

    `list_open_asks` IS §2.1's own WHERE clause (`state='open' AND posted=1`), asked once rather
    than re-filtered here, so the digest and the scheduler can never disagree about which asks are
    open. An absent store is an ABSENT ask: the caller's `except Exception` still owns genuine
    unreadability of the package around it.
    """
    mod = coord or load_coord()
    rows = []
    for row in mod.ending_store.list_open_asks(base.parent, seat="goal-master"):
        text = mod.ask_body(row)
        if not text:
            continue
        rows.append({
            "kind": "waiting",
            "label": label,
            "num": str(row.get("ask_id") or "?"),
            "sender": str(row.get("seat") or "goal-master"),
            "age": age_of_coord_ts(row.get("posted_at") or ""),
            "body": text[:200],
        })
    return rows


def age_of_coord_ts(ts):
    """`coord.age_of` needs a live `coord` module handle this file does not carry at import time
    (it is loaded per-call via `load_coord()`), so the ONE parse this predicate needs — the same
    `YYYY-MM-DD HH:MM` local-clock format `ask-store.js#coordTimestamp` stamps `posted_at` with —
    is inlined rather
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
            rows.extend(collect_unanswered_asks(label, base, coord))
        except Exception as exc:                      # noqa: BLE001 — one bad package never hides the rest
            unreadable.append(f"{label}: {exc}")
    # Halts FIRST, then oldest-first within each kind — reverse makes True (halt) lead and the
    # larger age lead. Without this a halt can be pushed off the CAP-5 list by five older asks,
    # which is the one row that must never be the one truncated away.
    rows.sort(key=lambda r: (r["kind"] == "halt", age_minutes(r["age"])), reverse=True)
    return rows, unreadable


def render(rows, unreadable, cap=CAP):
    """The digest. `cap=None` shows every row (`--all`).

    ⚠ A TRUNCATED LIST MAY NEVER BE THE ONLY PLACE A COUNT LIVES. When the cap bites, the header
    states the total for EVERY kind in `KIND_LABELS` that is present, plus the goals the halts span
    — so a reader summing the visible `⛔ RUN HALTED` rows and a reader reading the header get the
    same number, and the cap can never masquerade as the halted count (acceptance wave test 2,
    2026-08-26: "5 ⛔ RUN HALTED" reported against ten halts across three goals). Below the cap
    nothing is hidden, so the header stays the bare count, and the empty state stays byte-identical.
    """
    lines = []
    if not rows:
        lines.append("no owed answers")
    else:
        head = f"{len(rows)} owed answer{'' if len(rows) == 1 else 's'}"
        if cap is not None and len(rows) > cap:
            for kind, label in KIND_LABELS:
                of_kind = [r for r in rows if r["kind"] == kind]
                if not of_kind:
                    continue
                head += f" · {len(of_kind)} {label.format(s='' if len(of_kind) == 1 else 's')}"
                if kind == "halt":
                    goals = len({r["label"] for r in of_kind})
                    head += f" across {goals} goal{'' if goals == 1 else 's'}"
            head += f" — oldest {cap} shown (--all lists every row)"
        lines.append(head)
        for r in (rows if cap is None else rows[:cap]):
            tag = ("⛔ RUN HALTED · " if r["kind"] == "halt"
                   else "⏳ AWAITING A REPLY FROM · " if r["kind"] == "waiting" else "")
            lines.append(f"- {tag}{r['age']} old · {r['sender']} ({r['label']}) · {r['body']} "
                         f"· answer in thread: {r['label']} #{r['num']}")
    for u in unreadable:
        lines.append(f"⚠ package unreadable, this list may be SHORT — {u}")
    return "\n".join(lines)


def selfcheck(coord, workspace, text, elapsed_ms, only=None, cap=CAP):
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
        if cap is not None:
            assert len(items) <= cap, f"cap of {cap} not applied: {len(items)} items"
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

    # THE OWNER-ASK ARM — the OTHER direction. Both polarities, same fixture package, so a wrong
    # predicate that reports everything (or nothing) cannot pass by accident.
    #
    # ⚠ SEEDED THROUGH THE REAL WRITER PATH (`insertAsk` / `postAsk` / `reapAndRelaunch` on the ONE
    # store — the same three calls `server/heart/ask-record.js` makes when the daemon serves the
    # `record-owner-ask` intent), never by writing a file this reader then parses. The old fixture
    # hand-wrote `owner-asks.json`, so it asserted a SHAPE rather than the store, and it stayed
    # green over anything that produced the same JSON. The store's own CHECK constraints now gate
    # the seed, so a fixture the production writer could not have created cannot be built here.
    es = coord.ending_store
    asks_dir = pkg / "asks"
    asks_dir.mkdir(parents=True, exist_ok=True)

    def seed_ask(ask_id, text):
        """Insert one POSTED open ask, with the on-disk copy `evidence_pointer` names (§3)."""
        copy = asks_dir / f"{ask_id}.txt"
        copy.write_text(text, encoding="utf-8")
        es.ending_store_op("insertAsk", {"ask_id": ask_id, "goal": "fixture",
                                         "seat": "goal-master", "label": "work-content",
                                         "evidence_pointer": str(copy)}, start=pkg.parent)
        es.ending_store_op("postAsk", {"ask_id": ask_id, "posted_at": "2026-08-20 03:00"},
                           start=pkg.parent)

    seed_ask("t-1", "still open?")
    assert kinds("") == ["waiting"], "an OPEN unanswered owner ask is not reported owed"
    es.ending_store_op("reapAndRelaunch", {"ask_id": "t-1"}, start=pkg.parent)
    assert kinds("") == [], "a REAPED owner ask is still reported owed"

    # TWO THREADS, TWO ASKS [T5-R7]: the ask IS its Slack thread, so two open questions are two
    # rows and answering one leaves exactly the other open. This replaces the old per-seat QUEUE
    # arm — a second message in the SAME thread is the same ask now, not a queued second one, and
    # the "settle the oldest open ask" rule it tested is deleted [D-4-ruling].
    seed_ask("t-2", "ship today?")
    seed_ask("t-3", "or wait for review?")
    (pkg / "messages.md").write_text("", encoding="utf-8")
    rows = collect(coord, str(tmp), "fixture")[0]
    assert len(rows) == 2 and all(r["kind"] == "waiting" for r in rows), \
        f"two open asks on two threads are not both reported owed, one row each: {rows}"
    assert [r["body"] for r in rows] == ["ship today?", "or wait for review?"], \
        f"two open asks did not both render, oldest first: {[r['body'] for r in rows]}"
    assert [r["num"] for r in rows] == ["t-2", "t-3"], \
        f"an ask's `num` is not its thread id, so a reply cannot be aimed: {[r['num'] for r in rows]}"
    es.ending_store_op("reapAndRelaunch", {"ask_id": "t-2"}, start=pkg.parent)
    rows2 = collect(coord, str(tmp), "fixture")[0]
    assert [r["body"] for r in rows2] == ["or wait for review?"], \
        f"answering ONE thread did not leave exactly the other open: {rows2}"

    # THE CAP-IS-NOT-A-COUNT ARM (acceptance wave test 2, 2026-08-26). Over the cap the list is
    # SHORT, so the only trustworthy halted count is the header's. Driven on the throwaway
    # workspace, over the cap and with more halts than the cap shows, so it discriminates whatever
    # the live tree happens to hold. `t-3` is still open here, so all three kinds are present.
    over_cap = "\n".join(
        f"## {110 + i} | from: leader | to: owner | type: escalation | exec: e | "
        f"2026-08-20 03:{10 + i:02d}\n\nescalation {i}: the run is halted\n" for i in range(7))
    over_cap += ("\n## 200 | from: leader | to: owner | type: ask | exec: e | 2026-08-20 03:05\n"
                 "\nan ordinary ask alongside the halts\n")
    (pkg / "messages.md").write_text(over_cap, encoding="utf-8")
    big = collect(coord, str(tmp), "fixture")[0]
    halts = [r for r in big if r["kind"] == "halt"]
    assert len(big) > CAP and len(halts) >= 2, \
        f"the over-cap fixture is not over the cap: {len(big)} rows, {len(halts)} halts"
    capped = render(big, []).splitlines()
    shown_halts = [ln for ln in capped[1:] if "⛔ RUN HALTED" in ln]
    assert 0 < len(shown_halts) < len(halts), \
        f"the fixture truncates no halt — the arm cannot discriminate: {len(shown_halts)} shown"
    assert len(capped) - 1 == CAP, f"the capped list is not {CAP} rows:\n{capped}"
    assert f"{len(halts)} ⛔ run-halted" in capped[0], \
        (f"the capped header does not state the halted TOTAL, so a reader sums the "
         f"{len(shown_halts)} visible ⛔ rows and reports the CAP as the halted count: {capped[0]!r}")
    for kind, label in KIND_LABELS:
        n = sum(1 for r in big if r["kind"] == kind)
        stated = f"{n} {label.format(s='' if n == 1 else 's')}"
        assert not n or stated in capped[0], \
            f"the capped header states no total for {n} {label!r} row(s): {capped[0]!r}"
    every = render(big, [], cap=None).splitlines()
    assert len(every) - 1 == len(big), \
        f"--all rendered {len(every) - 1} of {len(big)} rows"
    assert "oldest" not in every[0], f"--all still claims a cap: {every[0]!r}"

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
    ap.add_argument("--all", action="store_true",
                    help="print EVERY row, not just the oldest 5 (the default stays capped: the "
                         "masters' cold-contact statement is the capped one)")
    ap.add_argument("--selfcheck", action="store_true", help="assert the digest is sane and fast")
    args = ap.parse_args()

    # An unmatched filter must REFUSE, never print "no owed answers": a typo'd package and a zero
    # debt are the same output, and the wrong one of them tells the owner nothing is owed.
    if args.package and not packages(args.workspace, args.package):
        print(f"error: --package {args.package} matched no coordination package under "
              f"{args.workspace}", file=sys.stderr)
        return 2

    started = time.time()
    cap = None if args.all else CAP
    rows, unreadable = collect(coord, args.workspace, args.package)
    text = render(rows, unreadable, cap)
    elapsed_ms = int((time.time() - started) * 1000)

    print(text)
    if args.selfcheck:
        print()
        print(selfcheck(coord, args.workspace, text, elapsed_ms, args.package, cap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
