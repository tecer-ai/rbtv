"""The leader's RULING acts — the things a leader does to a row it did not sit in.

`accept`   a finished seat's work: the current ending becomes `done`, outputs re-checked.
`instruct` a seat's ended session out of the state that keeps re-waking the chair: the leader's
           judgment is recorded where the daemon already drains it.
`hold`     a row the leader has ruled it CANNOT rule yet: the wake and the attempt counter stop
           until a NAMED change happens. `release` ends a hold early.
`record_decision`  the ledger half of a ruling — appended to the goal's `decision-log`
           (`<goal>/decisions.md`) in the SAME act as the send that carries it (`send --record`).

⚠ THE WORD `disposition` IS DEAD AND IS NOT REVIVED HERE. `rule-disposition` (the verb that used
to flip an ENDED `sessions.csv` row) was deleted whole [T2-R12, T1-R9] with the grant-store
authority model it implemented, and `state-store/vocabulary.js#KILLED_WORDS` refuses the word at
the store's own door. `sessions.csv` is session bookkeeping; the WORK ending lives in the ending
store (spec-state-store §4.1) and that is the only surface these verbs write. Anything here that
spelled `disposition` would be a second vocabulary over one fact.

⚠ NO PER-VERB ROLE GATE, AND THAT IS THE RULED SHAPE, NOT AN OMISSION. `is_leader` and every
sibling predicate were DELETED whole [T2-R10, D24, F-simplicity-7]: this kit enforces exactly two
refusal points — the cage envelope and the send-time refusal of an owner-ask from a non-designated
seat. The AUDIENCE bound on these two verbs is the DOOR: both sit in `SUPERVISION_COMMANDS`, so
`coordinate accept` / `coordinate instruct` are refused by name at the parser and only `supervise`
accepts them (owner ruling 2026-08-25, the audience split). The caller's resolved identity is
recorded on every write instead of gating it — a ruling nobody signed is the failure this records.
"""
import json
import subprocess
from pathlib import Path

# ---------- where the leader's judgment lands ----------
#
# ⚠ THE INBOX IS THE DAEMON'S, ALREADY DRAINED — this verb writes it, it does not invent it.
# `supervisor/relaunch-budget.js#drainLeaderInstructions` runs at the TOP of every reconcile pass
# and applies every pending file for the goal through `executeLeaderInstruction`, then moves it to
# `done/` or `refused/` with an outcome beside it. That module's own ATTENTION note names this
# verb's job exactly: *"The answer path is a FILE because no ruling CLI exists. If a leader-facing
# ruling instrument is ever built (matrix B9), this inbox is the thing it should write, not a
# second channel beside it."*
RELAUNCH_BUDGET_JS = Path(__file__).resolve().parent.parent / "supervisor" / "relaunch-budget.js"
# The hold's release vocabulary is the ENDING STORE's, read off it for `instruction_kinds`' reason:
# a second copy in Python is how a door accepts a word the store refuses.
VOCABULARY_JS = Path(__file__).resolve().parent.parent / "state-store" / "vocabulary.js"
LEADER_INSTRUCTIONS_REL = Path(".rbtv") / "runtime" / "ignite" / "leader-instructions"

# The keys `executeLeaderInstruction` refuses as WORK PRODUCT [CF-3, T2-R5] — a leader reports, it
# never does the seat's work. Refused HERE too, at write time, so the leader meets the wall while
# it can still fix the payload instead of finding a `refused/` file it never reads.
WORK_PRODUCT_KEYS = ("work_product", "patch", "outputs")


# THE WORKSPACE WALK IS `ending_store.workspace_root` AND THERE IS NO SECOND COPY HERE. This file
# used to carry its own, whose docstring said it resolved "the way `ending_store.ending_store_db`
# resolves it" — a promise held by a comment, which is how the two drift. Both walked up for a bare
# `.rbtv/` DIRECTORY, which is not what a workspace is (D27: the ancestor holding the install
# record `.rbtv/modules/ignite/server.json`), and that wrong rule cost the 2026-08-28 outage —
# 5815fbaa, memory `observation/20260828-i-a-rbtv-that-does-not-root-the`. `ending_store` is bound
# in this namespace by `coord.py:48`; the walk, its stderr line for a bare `.rbtv/` walked past,
# and its citation of `config.js#findInstallRoot` all live there, once.


def instruction_kinds():
    """The closed list, READ OFF `relaunch-budget.js` rather than re-spelled.

    A second copy of this list in Python is the shape that ships a verb whose accepted kinds and
    the daemon's executable kinds have drifted — the caller would be told `yes` and the drain
    would file the answer under `refused/`. Fail-CLOSED: a list that cannot be read is an empty
    list, and the command refuses rather than guessing."""
    try:
        proc = subprocess.run(
            ["node", "-e",
             "process.stdout.write(JSON.stringify(require(process.argv[1]).INSTRUCTION_LIST))",
             str(RELAUNCH_BUDGET_JS)],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    try:
        kinds = json.loads(proc.stdout or "[]")
    except ValueError:
        return []
    return [str(k) for k in kinds] if isinstance(kinds, list) else []


def instruction_path(root, goal, seat):
    """`<workspace>/.rbtv/runtime/ignite/leader-instructions/<goal>--<seat>.json` — the exact name
    `leaderInstructionPath` composes and `drainLeaderInstructions` matches by `<goal>--` prefix."""
    return Path(root) / LEADER_INSTRUCTIONS_REL / f"{goal}--{seat}.json"


# ⚠ THE SEAT IS CHECKED FOR EXISTENCE, and the ruling is exactly the one `route-fail` already
# answers to: *"a well-formed name that names no seat is how a routed FAIL reached nobody"*
# (`d-fail-route-back-mechanism`). Neither of these verbs' downstream has such a check —
# `executeLeaderInstruction` stamps whatever (goal, seat) the filename carries, and the ending
# store keys on the pair rather than validating it — so a typo'd name here mints an ending row for
# a seat that does not exist, and nothing ever reads it or complains.
def known_seats(args):
    return sorted(w["agent"] for w in launch.discover_workers(workers_dir(args, register=False)))


def require_seat(args, seat):
    seats = known_seats(args)
    if seat in seats:
        return
    refuse("state",
           f"this goal staffs no seat named `{seat}`, so there is no row to rule on. A "
           f"well-formed name that names no seat is how a ruling reaches nobody.\n"
           f"  staffed here: {', '.join(seats) or '(none — no seat descriptor was found)'}\n"
           f"NOTHING WAS WRITTEN.", 1)


def cmd_instruct(args):
    caller = gate(args, "instruct")
    pkg = package_dir(args, register=bool(args.go))
    goal = pkg.name
    root = ending_store.workspace_root(pkg)
    if root is None:
        refuse("state",
               f"no workspace above `{pkg}` — nothing up to the filesystem root holds the install "
               f"record `{ending_store.INSTALL_RECORD_REL}` (D27's definition of a workspace, "
               f"`ignite/ignite-cli/lib/config.js#findInstallRoot`; a folder merely holding a "
               f"`.rbtv/` is NOT one). The daemon drains this goal's instructions from "
               f"`<workspace>/{LEADER_INSTRUCTIONS_REL}/`, and without a workspace root there is "
               f"no inbox to write. NOTHING WAS WRITTEN.", 1)
    require_seat(args, args.seat)
    kinds = instruction_kinds()
    if not kinds:
        refuse("state",
               f"could not read the closed instruction list off `{RELAUNCH_BUDGET_JS}` (needs "
               f"`node`). This verb NEVER guesses the list: a kind the daemon cannot execute is "
               f"filed under `refused/` and the judgment is lost. NOTHING WAS WRITTEN.", 1)
    if args.kind not in kinds:
        refuse("input",
               f"`{args.kind}` is not a leader instruction. The list is CLOSED — a fifth would be "
               f"a remedy verb nobody ruled [D6, T4-R6]: {', '.join(kinds)}.\n"
               f"NOTHING WAS WRITTEN.", 2)

    payload = {"kind": args.kind, "ruled_by": caller or "(unresolved)", "ruled_at": now()}
    if args.kind == "rewrite-brief":
        if not (args.brief_file and args.brief_path):
            refuse("input",
                   "`rewrite-brief` rewrites a seat's brief on disk, so it needs BOTH the new "
                   "text and the path it lands at: --brief-file <file> --brief-path <target>. "
                   "The text rides a FILE and never argv — a shell eats backticks and $(...) "
                   "before this command can see them. NOTHING WAS WRITTEN.", 2)
        try:
            payload["brief"] = Path(args.brief_file).read_text(encoding="utf-8")
        except OSError as e:
            refuse("input", f"--brief-file unreadable: {e}. NOTHING WAS WRITTEN.", 2)
        payload["brief_path"] = str(Path(args.brief_path).resolve())
    elif args.kind == "reassign":
        if not args.to_seat:
            refuse("input", "`reassign` hands the work to a different seat DESIGN and needs its "
                            "name: --to-seat <seat>. NOTHING WAS WRITTEN.", 2)
        payload["to_seat"] = args.to_seat
    elif args.kind == "blocked-pending-plan-gap":
        if not args.gap:
            refuse("input", "`blocked-pending-plan-gap` says the gap is in the PLAN, not the "
                            "seat, and the daemon records a scoped re-plan request naming it: "
                            "--gap \"<what the plan does not say>\". NOTHING WAS WRITTEN.", 2)
        payload["gap"] = args.gap
        if args.milestone:
            payload["milestone"] = args.milestone
    else:                                   # escalate
        if not args.report_file:
            refuse("input",
                   "`escalate` forms a decision-ask to the owner, and the owner reads it on a "
                   "phone with none of this run's context — it needs the report: --report-file "
                   "<file>. A FILE and never argv (a shell eats backticks and $(...)).\n"
                   "NOTHING WAS WRITTEN.", 2)
        try:
            payload["report"] = Path(args.report_file).read_text(encoding="utf-8")
        except OSError as e:
            refuse("input", f"--report-file unreadable: {e}. NOTHING WAS WRITTEN.", 2)

    # THE CF-3 WALL, at the door instead of after the fact. `executeLeaderInstruction` refuses a
    # payload carrying the seat's work; the leader should meet that refusal while it can still fix
    # the payload, not as a `refused/` outcome file nobody re-reads.
    hit = [k for k in WORK_PRODUCT_KEYS if k in payload]
    if hit:
        refuse("state",
               f"a leader instruction may carry a JUDGMENT, never the seat's work [CF-3, T2-R5] — "
               f"and this payload carries {', '.join(hit)}. NOTHING WAS WRITTEN.", 1)

    target = instruction_path(root, goal, args.seat)
    if not args.go:
        print(f"WOULD WRITE {target}")
        print(json.dumps(payload, indent=2, sort_keys=True))
        print(c(f"next: add --go to record it. The daemon drains this inbox at the top of every "
                f"reconcile pass ({RELAUNCH_BUDGET_JS.name}#drainLeaderInstructions) and applies "
                f"it once, then files it under `done/`.", C_HINT))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(target, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"instructed: {goal}/{args.seat} -> {args.kind} (by {caller or '(unresolved)'})")
    print(f"  recorded at {target}")
    print(c("next: the daemon applies it on its next reconcile pass and moves the file to "
            "`leader-instructions/done/` with the outcome beside it. One file per (goal, seat) — "
            "writing again before it drains REPLACES this judgment, it does not add a second.",
            C_HINT))


def cmd_accept(args):
    """ACCEPT finished work: the seat's current ending becomes `done` in ONE act.

    The KG names this authority the leader's own — *"the leader holds the goal's authority
    (acceptance, the failure-path close gate, the relaunch, the escalation)"* (`concepts/leader.md`
    § differentiation) — and `records.py`'s writer table already carries the ruling that admits it
    (`d-exited-row-closure`, owner ruling A-10: *"if the work had in fact CONCLUDED, simply switch
    the row to `done`"*), for `done` and for NOTHING else.

    ⚠ THE OUTPUTS ARE RE-CHECKED, NOT TAKEN ON THE LEADER'S WORD. This goes through
    `stamp_checkout_ending(..., "done")`, so the store re-runs its own mechanical output check
    (§1.3) against the seat's declared `## Outputs` — an acceptance of work whose outputs are not
    on disk is refused here, by name, rather than silently downgraded to `failed/outputs-missing`
    inside the store where the leader would never see why.

    ⚠ `--anchor` IS MANDATORY AND IS RECORDED, NEVER VERIFIED. Same discipline as `--rerun`'s and
    `--reopen`'s: no tool can check that an anchor names a real investigation, and an acceptance
    citing nothing is exactly the misgrading R-6 bars."""
    caller = gate(args, "accept")
    pkg = package_dir(args, register=bool(args.go))
    anchor = (args.anchor or "").strip()
    if not anchor:
        refuse("input",
               "--anchor carries WHY this work is accepted — the message ref, decision anchor or "
               "evidence the leader read. It is recorded, never verified (no tool can check that "
               "an anchor names a real investigation), and an acceptance citing nothing is a "
               "`done` nobody can audit.\n"
               f"Name it: {coord_invocation(args, "supervise")} accept {args.seat} --anchor <ref> --go\n"
               "NOTHING WAS WRITTEN.", 2)
    require_seat(args, args.seat)
    declared, missing, has_block, _chat = declared_outputs(args, args.seat)
    if missing:
        refuse("state",
               f"`{args.seat}` declares outputs that are NOT on disk, so its work is not finished "
               f"and cannot be accepted:\n  " + "\n  ".join(str(m) for m in missing) + "\n"
               f"The ending store re-runs this same check and would stamp `failed/outputs-missing` "
               f"rather than `done`. Rule on the row instead: "
               f"{coord_invocation(args, "supervise")} instruct {args.seat} <kind> --go.\n"
               "NOTHING WAS WRITTEN.", 1)
    prior = ending_store.get_current_ending(pkg, args.seat)
    prior_word = (prior or {}).get("ending") or "(none)"
    if not args.go:
        print(f"WOULD ACCEPT {pkg.name}/{args.seat}: ending `{prior_word}` -> `done`")
        print(f"  outputs re-checked ({len(declared)} declared"
              f"{'' if has_block else ', no `## Outputs` block'}): all present")
        print(f"  anchor (recorded, not verified): {anchor}")
        print(c("next: add --go to record it.", C_HINT))
        return
    row = stamp_checkout_ending(args, args.seat, "done", declared=declared,
                                evidence=f"accept:{caller or 'unresolved'}:{anchor}")
    print(f"accepted: {pkg.name}/{args.seat} — ending `{prior_word}` -> "
          f"`{(row or {}).get('ending', 'done')}` (by {caller or '(unresolved)'})")
    print(f"  anchor (recorded, not verified): {anchor}")
    print(c(f"next: the seat advances every `after` edge that waited on it. To re-open this on a "
            f"LATE finding: {coord_invocation(args, "supervise")} launch --only {args.seat} --reopen <reason> "
            f"— the `done` row stands unrewritten (D54).", C_HINT))


# ---------- the ledger half of a ruling (B14) ----------
#
# ⚠ ONE ACT, AND THE ORDER IS DELIBERATE. *"A ruling recorded only in a message is not recorded"* —
# so `send --record` appends to the goal's decision-log in the SAME invocation as the send. The
# append runs AFTER `append_message` and never before, for two reasons: the entry can then CITE the
# message number (the ledger's stated consumption is anchor-resolution, so an entry nobody can
# resolve back to its message is half a record), and the risky write goes first — the send has real
# failure modes, the local append has almost none, which keeps the window where one landed and the
# other did not as small as it can be. An append that DOES fail is LOUD and non-zero: the caller is
# handed the exact text to put in the file by hand, because a silently-unrecorded ruling is the
# whole defect this flag exists to close.

def decision_log(pkg):
    """`<goal>/decisions.md` — the KG `decision-log`, the goal's ONE decision record."""
    return Path(pkg) / "decisions.md"


def decision_entry(title, body, *, caller, to, mtype, num):
    """One append-only entry, in the shape the live ledgers already carry (`## <stamp> — <title>`).

    NO ANCHOR IS MINTED. The `r-*`/`d-*`/`p-*` anchor classes are hand-authored and the file's own
    rule calls its entries frozen history pruned BY HAND; a slug this command invented could
    collide with one a person wrote, and a colliding anchor breaks the resolution every consumer
    uses. The dated heading is the other live shape and it needs nobody's permission."""
    return (f"\n## {now()} — {title}\n\n"
            f"Ruled by `{caller or '(unresolved)'}`, sent to `{to}` as `{mtype}` "
            f"— `coordination/messages.md` #{num}.\n\n"
            f"{body.rstrip()}\n")


def record_decision(args, title, body, *, caller, to, mtype, num):
    """Append the ruling to the goal's decision-log. Returns the path written."""
    pkg = package_dir(args, register=False)
    path = decision_log(pkg)
    with coord_lock(base_dir(args)):
        prior = path.read_text(encoding="utf-8") if path.exists() else (
            f"# decisions.md — {pkg.name}\n\n"
            "Write here when you have a settled decision, and the reason it was settled that way.\n")
        atomic_write(path, prior.rstrip("\n") + "\n" + decision_entry(
            title, body, caller=caller, to=to, mtype=mtype, num=num))
    return path


# ---- the THIRD ruling act: HOLD, and its release ----------------------------------------------
#
# ⚠ WHY A HOLD IS STATE AND NOT A MESSAGE. `owed-from-endings.js` turns a `failed` ending into a
# `nonterm` owed row and `reconcile.js` answers that row by launching the LEADER, every ~5-min
# pass. `accept` and `instruct` stop it because both END the row. A leader's third legitimate
# verdict — "I have read this and it cannot be ruled until X happens" — used to be a message and
# nothing else, so the pass could not tell it from a sitting that did nothing: it counted each one
# as a burned attempt, disarmed the lane at N=3, and the next code deploy re-armed the counter and
# bought three more. Nine identical HOLD verdicts, nine paid sittings, on `goal-memory-management`,
# 2026-08-28. This verb makes the verdict a row the pass reads.
#
# ⚠ THIS IS NOT THE DELETED `rule-disposition`, AND `hold-anchor` IS NOT COMING BACK. That was a
# column on `sessions.csv` under the grant-store authority model, deleted whole [T2-R12, T1-R9],
# and both words are refused at the ending store's own door. What is written here is a row IN the
# ending store — the ONE work-state surface — and it changes no ending.


def hold_until_words():
    """The CLOSED release vocabulary, READ OFF `state-store/vocabulary.js` rather than re-spelled.

    Fail-CLOSED for `instruction_kinds`' reason: a list that cannot be read is an empty list and
    the command refuses, because a `--until` word this door accepted and the store rejects is a
    ruling the leader believes it recorded and did not."""
    try:
        proc = subprocess.run(
            ["node", "-e",
             "process.stdout.write(JSON.stringify(require(process.argv[1]).HOLD_UNTIL))",
             str(VOCABULARY_JS)],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    try:
        words = json.loads(proc.stdout or "[]")
    except ValueError:
        return []
    return [str(w) for w in words] if isinstance(words, list) else []


def parse_until(spec, words):
    """`<word>` or `ask-answered:<ask-id>` -> (word, ask_id). Returns (None, None) on a bad word."""
    raw = str(spec or "").strip()
    word, _, arg = raw.partition(":")
    word = word.strip()
    if word not in words:
        return None, None
    return word, (arg.strip() or None)


def cmd_hold(args):
    caller = gate(args, "hold")
    pkg = package_dir(args, register=bool(args.go))
    anchor = (args.anchor or "").strip()
    if not anchor:
        refuse("input",
               "--anchor carries WHAT you read to reach this hold — the message ref, decision "
               "anchor or evidence. It is recorded, never verified, and a hold citing nothing is a "
               "stopped lane nobody can audit.\n"
               f"Name it: {coord_invocation(args, "supervise")} hold {args.seat} --until <change> "
               "--anchor <ref> --go\n"
               "NOTHING WAS WRITTEN.", 2)
    words = hold_until_words()
    if not words:
        refuse("state",
               f"could not read the closed release vocabulary off `{VOCABULARY_JS}` (needs `node`). "
               f"This verb NEVER guesses it: a `--until` word the store refuses is a hold you would "
               f"believe you recorded and did not. NOTHING WAS WRITTEN.", 1)
    until, ask_id = parse_until(args.until, words)
    if not until:
        refuse("input",
               f"`{args.until}` is not a hold release condition. The list is CLOSED — a hold with "
               f"no named release is a stall, not a ruling: {', '.join(words)}.\n"
               "  new-ending            — released when THIS seat's ending is re-stamped\n"
               "  ask-answered:<ask-id> — released when that open ask leaves `open`\n"
               "  release               — released only by `supervise release <seat> --go`\n"
               "NOTHING WAS WRITTEN.", 2)
    if until == "ask-answered" and not ask_id:
        refuse("input",
               "`--until ask-answered` must NAME the ask that releases it: "
               "`--until ask-answered:<ask-id>`. The ask ids open on this goal are listed by "
               f"{coord_invocation(args, "supervise")} ready-seats.\n"
               "NOTHING WAS WRITTEN.", 2)
    require_seat(args, args.seat)
    if until == "ask-answered":
        # A well-formed ask id that names no open ask releases INSTANTLY (the predicate fails open
        # by design), so the hold would be a no-op the leader never learns about. Caught here.
        open_ids = [a.get("ask_id") for a in ending_store.list_open_asks(pkg, posted=None)]
        if ask_id not in open_ids:
            refuse("state",
                   f"`{ask_id}` is not an OPEN ask on this goal, so a hold waiting on it would "
                   f"release on the very next pass and hold nothing.\n"
                   f"  open here: {', '.join(i for i in open_ids if i) or '(none)'}\n"
                   "NOTHING WAS WRITTEN.", 1)
    prior = ending_store.get_current_ending(pkg, args.seat)
    prior_word = (prior or {}).get("ending") or "(none)"
    if not args.go:
        print(f"WOULD HOLD {pkg.name}/{args.seat}: ending `{prior_word}` stands, and this pass "
              f"stops driving it")
        print(f"  until: {until}" + (f":{ask_id}" if ask_id else ""))
        print(f"  anchor (recorded, not verified): {anchor}")
        print(c("next: add --go to record it. While the hold is live the daemon launches no leader "
                "for this row and advances NO attempt counter; a code-deploy re-arm does not clear "
                "it, because a hold is a ruling and not a counter.", C_HINT))
        return
    out = ending_store.hold_seat(pkg, args.seat, until, anchor=anchor,
                                 held_by=caller or "(unresolved)", ask_id=ask_id)
    row = (out or {}).get("hold") or {}
    same = bool((out or {}).get("idempotent"))
    print(f"held: {pkg.name}/{args.seat} — ending `{prior_word}` stands, until "
          f"`{until}{':' + ask_id if ask_id else ''}` (by {caller or '(unresolved)'})"
          + (" — ALREADY HELD on the same terms, nothing changed" if same else ""))
    print(f"  held at {row.get('held_at', '(unstamped)')}")
    print(f"  anchor (recorded, not verified): {anchor}")
    print(c(f"next: nothing on your side. The reconcile pass excludes this row every pass and says "
            f"so (`heldExcluded`). It comes back on its own when the change you named happens; to "
            f"end it early: {coord_invocation(args, "supervise")} release {args.seat} --go.", C_HINT))


def cmd_release(args):
    """END a hold early. Releasing a seat that is not held is NOT an error — the hold may have been
    released by its own named change one pass ago, and the leader asked for the state it has."""
    caller = gate(args, "release")
    pkg = package_dir(args, register=bool(args.go))
    require_seat(args, args.seat)
    prior = ending_store.get_seat_hold(pkg, args.seat)
    if not prior:
        print(f"not held: {pkg.name}/{args.seat} carries no hold — nothing to release.")
        print(c("next: the row is already whatever its ending says it is; "
                f"{coord_invocation(args, "supervise")} ready-seats.", C_HINT))
        return
    until = prior.get("until")
    if not args.go:
        print(f"WOULD RELEASE {pkg.name}/{args.seat}: hold until `{until}` placed "
              f"{prior.get('held_at')} by {prior.get('held_by')}")
        print(f"  anchor it was held on: {prior.get('anchor')}")
        print(c("next: add --go to record it. The row becomes owed again on the next pass and the "
                "leader gets ONE sitting to rule it.", C_HINT))
        return
    ending_store.release_seat(pkg, args.seat)
    print(f"released: {pkg.name}/{args.seat} — the hold until `{until}` is gone "
          f"(by {caller or '(unresolved)'})")
    print(c("next: the next reconcile pass owes this row again and wakes the leader ONCE for it. "
            "Rule it with `accept` or `instruct`, or hold it again on new terms.", C_HINT))
