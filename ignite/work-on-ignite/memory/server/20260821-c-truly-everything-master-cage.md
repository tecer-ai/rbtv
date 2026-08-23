# 20260821-c-truly-everything-master-cage — Truly everything master cage

kind: creation
component: server
date: 2026-08-21
commit: 92e7156c
deployed: yes
pin: server/spawn/probes/probe-master-cage.js (D48-annotated, scheduled)
seeded: true

## Motivation
Strand C of the 2026-08-21 decision review measured the live 13:40Z `goal-master` launch argv and overturned the "manager is over-caged" framing: the cage was already the widest in the system — RW over `1-projects`, `2-areas`, `.rbtv/config/modules`, and other open goals' entire folders including their `seats/` — while the wall landed only at home. Peer seat folders were a `tmpfs` that accepted writes and discarded them; own `seat.md` and `permission-edits.csv` were RO carves; secrets masked over `/dev/null` (`decision-review-2026-08-21.md` §3). The template comment conceded the blocking `tmpfs` line was kept because it was "free"; no ruling required it, and recorded rulings (`d-master-zero-restrictions-accepted`, seed §2 "full read/write grants") pointed the other way. Cost measured that morning: stools #167 — a smith burned eight sub-60s `incomplete` sittings waiting on a one-line descriptor edit only `goal-master` could make, blocked on this cage change.

D48 (owner, same sitting) picked D-6 option C (wide cage) and approved the companion that fake-success tmpfs must REFUSE writes instead of silently discarding them. D49 the same day settled the mechanism (`redesign-plan/decisions.md:680-698`): cage = "truly everything, for ALL master roles" (`goal-master`, `channel-master`; `console-master` is owner-invoked and unsandboxed, so unaffected) — everything writable, including the rbtv repo, spawn profiles, own `seat.md`, own-goal seats — with ONLY secrets-read still masked. The owner accepted the stated risk that a master sitting can rewrite the machinery that governs it, including live-read `coord.py`. Secret-add mediation and drop-file key delivery are the other D49 clauses; they live in sibling `20260821-c-secret-add-mediated`, not here.

## Design
`92e7156c` (2026-08-21 15:58:14Z) split the bind template rather than widening `SeatBinds` for everyone. Workers keep `SeatBinds` but swap the peer-seats overlay from `tmpfs` to a new verb `ro-mask`. Masters get a new `MasterBinds` stack selected by seat name.

`ro-mask` is SRC≠DEST: `specToBwrapFlags` in `cage.js` emits `--ro-bind <emptySource> <dest>` so the path lists nothing AND writes fail EROFS. `tmpfs` stays in `BIND_VERBS` only for older fixture templates that still spell it; the code comment names the discarded overlay "the false-complete shape." When the masked path contains the occupant's own `seatDir`, `punchMaskSource()` synthesizes a directory that recreates that subpath so a later `bind:{seatDir}` has a mountpoint; otherwise `emptyMaskSource()` from `private-scope.js`. `MasterBinds` itself has no `ro-mask` line.

`isCagedMasterRole(seatPath)` is name-based: the parsed seat name ends with `-master` and is not `console-master`. `composeCageFor` (the one composer both spawn doors use) then picks `resolvedSandbox.MasterBinds` over `SeatBinds` when that array is non-empty. `resolveSandbox` skips `MasterBinds` the same way it already skipped `SeatBinds` — `cage.js` resolves against the seat's own records, not the workdir. `launch-profiles/profiles.js` added `MasterBinds` to `KNOWN_SANDBOX_KEYS`; `validateSandbox` throws `SpawnError(E_CONFIG_LOAD)` if the key is declared without a `seatBindValidator`, "refusing rather than accepting an unvalidated bind template." Python-side `cagespec.py` classifies `ro-mask` as `ABSENT` (same bucket as `tmpfs`) so live `coord.py` tooling agrees with the JS composer.

`MasterBinds` grants via `bind:` (not `ro-bind`) the workspace (`{grant:readRoot}`), goal, seat, rbtv repo (`bind-try`), bus, other executing goals, worktree, git internals (`.git` root stays RO; `objects`/`refs`/`logs` RW), harness creds, `local-bin`, tmux socket, `rw-paths`, and CLI write-roots. It omits the peer-seats mask, the `seat.md` carve, and the `permission-edits.csv` carve. Private-scope masks still append last (GRANTS → MASKS → PIERCES in the `spawn-profiles.yaml` comment), so secrets still win over this stack.

Rejected: keep silent-discard tmpfs; a narrower or mediated master cage (the other unnamed D-6 lettered options — C was picked); treating `console-master` as a caged role (it never reaches this stack). D49's secret-add write is not this commit — `b6c64a25` / `ac1c08d8` are the sibling.

## How it works
At spawn both doors call `composeCageFor`. If the seat folder's parsed `seat` is `goal-master`, `channel-master`, or any other `*-master` except `console-master`, and `cage.MasterBinds` is a non-empty array in `spawn-profiles.yaml`, that stack is the template; otherwise `cage.SeatBinds`. Adding a new caged master role is naming it `*-master`. There is no grant flag.

A worker write into `{goalDir}/seats` now hits the `ro-mask` overlay and fails EROFS/EACCES instead of appearing to succeed. A master write into a peer seat, own `seat.md`, `permission-edits.csv`, an ordinary workspace path, or an rbtv-shaped file lands on disk. A master `cat` of `.env` or `private.json` still returns empty. To keep that last property, do not reorder composition so a `MasterBinds` grant is emitted after the private-scope masks, and do not promote a secrets path into this stack as a pierce.

`coord.py` / live Python reads the same spec through `cagespec.py`. A new bind verb has to land in both vocabularies or the evaluator drifts from the wall the process actually gets.

## Consequences
Replaced the un-ruled "already-wide cage plus a free tmpfs at home" default. Workers lost silent-success peer-seat writes. Masters lost the peer-seats mask and the two wall-control RO carves, and gained RW on the rbtv repo itself.

Same-night D50 (`decisions.md:702-708`) left this cage standing and added a procedural rule `r-master-never-edits-system`: a master may touch anything but does not edit ignite/daemon code unless the owner instructs; standard procedure on a system defect is to file it. `system-problems-2026-08-21.md` measured the next day that live prompts still implement D49 ("Write the whole workspace … the rbtv repo"), the rule lives only in a goal ledger, and `<restrictions>` is empty — #693's already-chosen fix was deliberately not applied because of that unread rule.

Next-day follow-ups, none reverts: `6b55b1c4` (D53/#576, `20260822-i-ro-mask-private-scope-fix`) excuses `ro-mask` covers in private-scope `visible()` — a daemon-fired leader died on `bwrap: Can't mkdir parents … Read-only file system` when a pattern-floor match nested under a peer seat's mask. `7f6eaf3e` / `9060c3cc` (D56/D74, `20260821-i-stools-undeclared-tool-refusal`) add a named refusal for undeclared tools and pin the stools pierce on this same probe (S1/S2/S2-control), proving the wide cage does not itself unmask `stools` credentials. Sibling entries that assume this grant: `20260821-c-secret-add-mediated`, `team-kit/20260821-c-caged-identity-corroboration`.

## Verification
New scheduled probe `probe-master-cage.js` drives `composeCageFor` against the shipped `cage.SeatBinds` / `cage.MasterBinds` in a scratch fixture under `os.tmpdir()` — never a live goal. Legs in this commit: M1 master write into an own-goal peer seat lands; M2 own `seat.md`; M3 `permission-edits.csv`; M4 ordinary workspace; M5 rbtv-shaped file; M6 `.env` / `private.json` still read-masked; W1 worker peer-seat write fails EROFS/EACCES and does not land; W2 worker cage still ro-masks `seats/`, master cage does not; C1 `channel-master` (service seat) workspace write lands. Same commit: `probe-seat-cage.js` gained `P8e-write`; `probe-seat-grant-classes.js` leg `G6b` was rewritten from asserting a `--tmpfs` flag to asserting a `--ro-bind <emptySrc> <ownSeats>` pair.

`decision-review-2026-08-21.md` §6 (added ~18:30Z the same day) records D47–D49 "executed and deployed (`fecd3b6a → ac1c08d8`)" and "all six probe reds green." Header `deployed: yes`. The S1/S2/S2-control legs on this probe arrived the next day in `9060c3cc`, not in `92e7156c`.

## ATTENTION
- D49's width is an accepted risk, not an oversight: the owner recorded that a master sitting can rewrite the machinery that governs it, including live-read `coord.py`. Named mitigations were the F-8 identity fix and git history, not prevention. Treat a narrowing proposal as a new ruling, not a bugfix of this commit.
- The cage answers "can"; D50 `r-master-never-edits-system` answers "should." Machinery implements D49 (whole-workspace RW). The procedure ("file, don't fix" unless the owner instructs) lived only in a goal ledger the day after this shipped, and live prompts still said the inverse. Checking only `MasterBinds` gives the wrong answer to whether a master may edit ignite/daemon code.
- Secrets stay read-masked because private-scope masks append last and win over `MasterBinds`. Reordering bind composition, or promoting a secrets path into this stack as a pierce, drops that property without touching the template text. Re-confirmed at `system-problems-2026-08-21.md:482` against `config.yaml` and both credentials directories.
- `ro-mask` as shipped here was incomplete: next day `6b55b1c4` (D53/#576, `20260822-i-ro-mask-private-scope-fix`) had to excuse ro-mask covers in `private-scope.js` `visible()`. A pattern-floor match nested under a peer seat's mask made bwrap try `mkdir` on a read-only cover and kill the spawn.
- Narrowing `MasterBinds` can silently break secret-add mediation (`20260821-c-secret-add-mediated`) and launch-identity corroboration (D43/D45), both of which assume a master can observe and write broadly. The next-day stools pin (`9060c3cc` S2-control) also proves the wide cage does not itself unmask undeclared-tool credentials — do not "fix" a secrets pierce by shrinking this grant.
