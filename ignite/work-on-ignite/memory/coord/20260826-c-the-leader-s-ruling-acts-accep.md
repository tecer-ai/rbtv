# 20260826-c-the-leader-s-ruling-acts-accep — The leader's ruling acts: accept, instruct, send --record

kind: creation
component: coord
date: 2026-08-26
commit: d7841291
deployed: no
pin: ignite/coord/coord_selftest.py
components: supervisor,meta-leader

## Motivation
`rule-disposition` was deleted whole [T2-R12, T1-R9] with the grant-store authority model it
implemented, and nothing replaced it. The measured consequence, recorded as role-action-program
matrix rows B9/B10/B14: 18 leader-addressed disposition asks piled across two goals while the
daemon re-woke the chair every 5 minutes on rows nothing could rule; `relaunch-budget.js`'s newly
wired leader handoff (`20260826-c-the-retry-budget-handoff-to-th`) had to carry the leader's answer
as a hand-written JSON file, its own ATTENTION note saying *"The answer path is a FILE because no
ruling CLI exists. If a leader-facing ruling instrument is ever built (matrix B9), this inbox is
the thing it should write, not a second channel beside it."*; and six sites across `launch.py`,
`attest.py`, `ready.py`, `records.py` and `cli_main.py` — enumerated in
`20260824-c-delete-rule-disposition-ruled`'s ATTENTION 3 — told a leader in prose that no
instrument existed. A third gap, matrix M15: no command recorded a ruling into the goal's
decision-log in the same act as the message that carried it.

## Design
Three verbs' worth of behaviour in ONE new split module, `coord/ruling.py`, registered in
`coord.py`'s `SPLIT_MODULES` and `PRODUCT_ORDER` and nothing else.

`instruct` writes the inbox the daemon ALREADY drains rather than inventing a second channel —
`drainLeaderInstructions` runs at the top of every reconcile pass and applies each pending file
through `executeLeaderInstruction`. Its kind list is READ OFF `relaunch-budget.js#INSTRUCTION_LIST`
through a `node -e` shell-out, never re-spelled in Python: a second copy is the shape that ships a
verb whose accepted kinds and the daemon's executable kinds drift, telling the caller `yes` for a
kind the drain files under `refused/`. It fails CLOSED — a list that cannot be read is an empty
list and the command refuses.

`accept` goes through `stamp_checkout_ending(..., "done")`, so the ending store re-runs its own
mechanical output check; an acceptance of work whose declared `## Outputs` are not on disk is
refused BY NAME here rather than silently downgraded to `failed/outputs-missing` inside the store.

REJECTED: reviving `rule-disposition` or its surface. `disposition` is a killed word at
`state-store/vocabulary.js#KILLED_WORDS`; `sessions.csv` is session bookkeeping and the WORK ending
lives in the ending store (spec-state-store §4.1). Both verbs write the ENDING.

REJECTED: a per-verb role gate. Every `is_leader`-shaped predicate was deleted whole [T2-R10, D24,
F-simplicity-7]; the AUDIENCE bound is the DOOR — both verbs sit in `SUPERVISION_COMMANDS`, so
`coordinate accept` is refused by name at the parser and only `supervise` accepts them (owner
ruling 2026-08-25, the audience split). The caller's resolved identity is RECORDED on every write
instead of gating it.

B14's flag went on `coordinate send` and on nothing else: the matrix cell (M15) names the act
directly above it — relaying the ruling by message — and a ruling that never reached the bound seat
is not a ruling. Three flags where one does the job is the YAGNI failure; `record_decision()` is one
helper and gains a second caller the day one is needed.

## How it works
`supervise instruct <seat> <kind> [--go]` validates the seat against
`launch.discover_workers` (a well-formed name that names no seat is how a ruling reaches nobody —
`executeLeaderInstruction` validates neither), validates the kind against the JS list, composes the
per-kind payload (`rewrite-brief` needs `--brief-file` + `--brief-path`, `reassign` `--to-seat`,
`blocked-pending-plan-gap` `--gap` [`--milestone`], `escalate` `--report-file`), enforces the CF-3
wall at the door (a payload carrying `work_product`/`patch`/`outputs` is refused where the leader
can still fix it, not as a `refused/` file nobody re-reads), and atomically writes
`<workspace>/.rbtv/runtime/ignite/leader-instructions/<goal>--<seat>.json`. Text rides a FILE and
never argv — a shell eats backticks and `$(...)` first. `workspace_root` walks up for `.rbtv` the
same way `ending_store` does, so the kit and the engine land on one directory by construction.

`supervise accept <seat> --anchor <ref> [--go]` refuses a missing anchor, refuses an unknown seat,
refuses declared-but-absent outputs (naming each resolved path), then stamps the ending `done` with
`evidence=accept:<caller>:<anchor>`. `--anchor` is recorded, never verified — no tool can check
that an anchor names a real investigation.

`coordinate send <to> "<body>" --record "<title>"` appends `## <stamp> — <title>` to
`<goal>/decisions.md` under the coord lock, AFTER `append_message` so the entry can cite `#N` (the
decision-log's consumption is anchor-resolution) and so the write with real failure modes goes
first. No anchor slug is minted: the `r-*`/`d-*`/`p-*` classes are hand-authored and an invented
slug could collide with one a person wrote.

`outputs.coord_invocation` gained a `door=` parameter (defaulting to `coordinate`, so every
existing caller is byte-identical) — since the audience split a verb sits on exactly ONE door, and
a refusal advising the other hands the reader a command the parser refuses by name.

## Consequences
The six stale sites now name the live verbs; `grep -rn 'no replacement ruling instrument' ignite/
meta/` returns nothing outside the memory store. `meta/leader/prompts/leader.md` §3 (the ANSWER
disposition), §4 and its `<restrictions>` bullet, and `meta/leader/tasks/serve-staff-mail.md`'s
done-criterion no longer tell the leader the act does not exist; the leader's `exposes: skill:`
gained `ignite/supervisor/supervise-a-seat` and the EXISTING `ignite/coord/team-kit` (a second
`coordinate` reference was rejected — the panel resolution the owner ratified). A new skill,
`supervisor/skills/supervise-a-seat/SKILL.md`, is the leader-facing written reference over the
`supervise` door.

NOT deployed: `~/.local/state/rbtv-deploy` is a separate worktree and the daemon boots from it.

## Verification
Commit `d7841291`. `coord.py selftest` PASS, 0 failures, 1008 ok rows, exit 0 — including two new
checks: `instruct -h` names EXACTLY the kinds `INSTRUCTION_LIST` carries (asserted against the JS
list itself, so a fifth added on BOTH sides passes and a fifth added on one side reds), and both
verbs sit on the supervision door and on neither the coordination one. All 13 supervisor selftests
exit 0. End-to-end on a scratch workspace: `supervise instruct builder reassign --to-seat builder-b
--go` wrote `scratch-goal--builder.json`, and a real `drainLeaderInstructions` call against a real
ending store returned `applied:true kind:reassign`, stamped the ending `incomplete armed:1
diagnostic:"leader reassigned to builder-b"` and moved the file to `done/`. `supervise accept` then
took that `incomplete` to `done`; with the declared output absent it refused by name, and with the
output on disk the same call passed. `coordinate send --record` sent message #1 and appended the
cited entry in one act; with the ledger path made unwritable it printed MESSAGE #1 WAS SENT / THE
LEDGER ENTRY WAS NOT WRITTEN plus the exact text to paste, and exited 1. `component-lint` on
`ignite/coord`, `ignite/supervisor` and `meta/leader`: no new finding (supervisor's 67 and
meta/leader's 2 are pre-existing and unchanged).

## ATTENTION
1. `instruct`'s kind list is READ OFF `relaunch-budget.js` at runtime via `node -e`. Adding a fifth
   kind to the JS list makes the CLI accept it immediately — but the `-h` PROSE is the one
   surviving second copy of that list and argparse cannot check it. The coord selftest asserts the
   help against the JS list; a fifth kind added without touching the help REDS there, deliberately.
2. A BARE `accept`/`instruct` (no `--go`) still REGISTERS the run tag in
   `~/.config/rbtv/coordinate-runs.json`, because `gate()` -> `resolve_agent` -> `base_dir(args)`
   resolves with `register=True`. This is pre-existing and kit-wide — `route-fail` bare does the
   same — but it contradicts every such verb's own "bare writes nothing" help. Scratch/`/tmp`
   packages mint permanent-looking tags (pruned only when the path disappears).
3. `accept` reads the seat's declared outputs through the io-spec `## Outputs` block INSIDE an
   `<io-spec>` element. A `## Outputs` heading outside that element parses as zero declarations and
   the acceptance passes vacuously reporting "no `## Outputs` block" — a fixture written without
   `<io-spec>` proves nothing about the output re-check.
4. One instruction file per (goal, seat). Writing again before the drain REPLACES the judgment
   rather than adding a second — the same property that makes `settleInstruction` necessary on the
   daemon side.
5. The two verbs' audience bound is MEMBERSHIP IN `SUPERVISION_COMMANDS` and nothing else. Moving
   a verb out of that tuple silently makes it typeable by every working seat; there is no per-verb
   role predicate anywhere in this kit to catch it [T2-R10, D24, F-simplicity-7].
- instruct's kind list is read off relaunch-budget.js at runtime; the -h prose is the one second copy and the coord selftest catches its drift
