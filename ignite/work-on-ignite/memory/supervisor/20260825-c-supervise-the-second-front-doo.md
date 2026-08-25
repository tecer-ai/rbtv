# 20260825-c-supervise-the-second-front-doo — supervise — the second front door, split by audience

kind: creation
component: supervisor
date: 2026-08-25
commit: 7dd08887,d60c73df
deployed: no
pin: ignite/coord/probes/probe-save-gate.py
components: coord,ignite-cli,planning,runtime,deploy,operator

## Motivation
The owner ruled on 2026-08-25: "coordinate must also be split at entry point. two different
systems: one for the daemon or for leaders (if smth broken), the other for all agents working on
ignite (checkin, checkout, message, etc)." One front door was carrying two audiences, so every
seat's `-h` taught it the daemon's remedial surface and the daemon's surface was reachable by any
seat that typed it.

## Design
`coordinate` keeps the 25 seat-facing verbs; `supervise` — a new thin door at
`supervisor/supervise.py` — takes the 16 launch and remedial ones. The two doors PARTITION the
surface: 25 + 16 = 41, the pre-split count, and no verb is reachable through both.

THE SPLIT IS BY AUDIENCE, NOT BY MODULE HOME, and one verb proves the difference is real:
`rule-guard` is defined in `supervisor/attest.py` and is an AGENT command, because the seat named
in the (seat, key) pair is the only writer of its own guard value. A door table derived from the
file layout would have taken it from every seat.

## How it works
`SUPERVISION_COMMANDS` in `cli_main.py` is the ONE place the mapping is spelled, and anything
absent from it is a `coordinate` command — the default is the agent surface, because a verb that
silently appeared there is a far smaller failure than a remedial verb silently vanishing from the
daemon's. `build_parser(door)` registers every command exactly as before and puts the other door's
onto a DISCARD parser, so each door accepts only its own while `command_parsers` still carries the
whole inventory for the help audits. `main(door)` picks the parser and nothing else changes: no
verb's behaviour, flags or output moved, and each door's epilog carries every verb's one-line
description verbatim. `supervise.py` imports the kit rather than re-executing it, so the kit stays
ONE namespace named `coord`.

## Consequences
Advice that named the wrong door had to move with the verbs: ~30 sites across examples, `next:`
hints and refusal texts, plus `protocol.md`'s `$SUPERVISE` block (loader step 4 for every seat),
the three router surfaces, `team-kit.md`, the starter-set router and the caged seat's own
end-of-session instruction. Executable callers were swept from the grep: `seeding.js` (four
verbs), `spawn.js` (attest-exit), `goal_creation_request.py`, `recover-room.py` — which DERIVES
the door from the `--coord` path it already takes, so `reconcile.js` needed no edit and no file
holds a second spelling of where the door lives — `materialize-seats.py`'s two acceptance suites,
and two probes. `lifecycle_exec`'s detached fork re-enters through `supervise.py`. `link-tools.py`
links the second bare name; both `exposure.csv` files and the audience map carry it.

## Verification
`coord.py selftest` PASS, 0 failures — including a NEW row asserting the two doors partition the
command surface, and a rewritten row asserting each command's worked example INVOKES THE DOOR THAT
ACCEPTS IT. `materialize-seats.py --selftest` PASS, 0 failed rows of 62. `probe-lifecycle-idents`
42/42 with 7/7 RED ARMS; `probe-save-gate` PASS 27/27. Both doors `--help` exit 0. `node --check`
clean on every edited JS file. Not deployed: worktree branch `ignite/core-redesign` only.

## ATTENTION
- A NEW VERB LANDS ON `coordinate` BY DEFAULT. If it is a daemon or leader remedial act, add it to
  `SUPERVISION_COMMANDS` in the same change — and put its worked example on that door, or the
  selftest reds.
- `coord.py` REFUSES the 16 supervision verbs by name. Any caller, probe fixture or doc line that
  still spells `coordinate launch` is now teaching a command that door rejects.
- The trampoline in `coord.py` re-enters BY PATH, never by name. `import coord` would resolve
  through sys.path and could execute a different `coord.py` than the one invoked — measured:
  by-name re-entry made every `save-coord.py` gate candidate test the INSTALLED kit and pass,
  mutant or not, and `probe-save-gate` is what caught it.
- a new verb lands on coordinate by default; a daemon/leader remedy must join SUPERVISION_COMMANDS in the same change
