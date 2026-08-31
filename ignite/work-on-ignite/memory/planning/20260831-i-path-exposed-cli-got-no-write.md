# 20260831-i-path-exposed-cli-got-no-write — path-exposed CLI got no write-roots, skill-routed did

kind: issue
component: planning
date: 2026-08-31
commit: f55dc3a3
deployed: no
pin: ignite/planning/materialize-seats.py
register-id: G-leader-0828-2023

## Observed
`resolve_cli_write_roots` (`ignite/planning/materialize-seats.py`) left `plan["cli_write_roots"]`
empty for any seat exposing a CLI directly via `exposes: path:` with no `skill:` in the chain — no
warning, no refusal. Measured (task 162, seed evidence): on `ignite-engine-planning`, `fix-judge`
exposed `ignite/coord/file-issue` under `exposes.path` only; birth showed four sibling seats with
`cli-write-roots:` baked and `fix-judge` with none, EROFS after owner approval. Reproduced
2026-08-31 by calling `resolve_seat_exposes`/`resolve_cli_write_roots` directly against a real
`exposure.csv` fixture (file-issue-shaped row, `write-roots=!register`): a seat exposing it under
`path:` got `cli_write_roots == {}`; a control seat exposing the same CLI under `skill:` got the
root, correctly.

## Mechanism
`resolve_cli_write_roots`'s per-part loop opened with `if method != "skill": continue`, so a
`method == "path"` part — the seat's OWN direct CLI grant — was skipped entirely before the loop
body that reads `WRITE_ROOTS_RESOLVED` off the row. `_write_roots` (the function that resolves
that column) already runs for EVERY exposure.csv row regardless of method and stores the result on
`row[WRITE_ROOTS_RESOLVED]` — the data was already there, just never read for a path-exposed CLI.

## Attempts
First attempt held — checked commit `98186c76` (`20260831-i-caged-planning-seat-could-not`, this
same day): that fix bound `resolveCliWriteRootGrants` into `composeCageFor` on the spawn.js side
and added `skill: file-system-issue` to the plan-console prompts so THEIR seats route through the
skill branch — it sidesteps this defect for those five prompts but does not touch
`resolve_cli_write_roots`'s `method != "skill": continue`, so any OTHER path-only exposure (like
`fix-judge`'s) still reproduced red on today's tree.

## Fix
Added a `method == "path"` branch ahead of the skill branch: it reads the row's own
`WRITE_ROOTS_RESOLVED`, composes into the SAME `entries`/`roots` dicts the skill branch uses (so a
seat reaching one CLI both ways still dedupes by target, and a genuine collision is still caught),
and `continue`s past the skill branch. Rejected: silently leaving path-exposed CLIs ungranted (the
observed defect) or refusing at materialize time instead of composing — the docstring already
anticipated dual-reach dedup as the intended shape, so completing that shape was the smaller,
correct fix over inventing a new refusal class. Tagged each provenance chain with `"path"`/`"skill"`
so the existing `write-root GRANTED` / `write-root-private` messages read correctly instead of
mislabeling a direct grant as routed through a skill.

## Consequences
No deletions. The two message-render sites (`write-root-private` refusal, `write-root GRANTED`
warning) were reworded to branch on provenance so a direct-path grant is never described as
"through skill '<pid>'".

## Verification
Direct-call reproduction against real `_exposure_rows`/`resolve_cli_write_roots` (not the full CLI
— the ref-resolution grammar layer is orthogonal to this defect): red confirmed empty
`cli_write_roots` for the path-only seat before the fix, green (root composed, matching the
skill-control seat) after. Revert-in-place control: stashing just this file's diff and rerunning
reproduced red again. Full `materialize-seats.py --selftest`: 343 `ok` checks pass; the run stops at
a PRE-EXISTING, unrelated `SC-1` failure (`ending_store` workspace-root detection in a tmp fixture)
reproduced identically before this change (confirmed by stash/rerun). Not deployed.

## ATTENTION
- `_write_roots` already resolves `WRITE_ROOTS_RESOLVED` for every exposure.csv row at generation
  time regardless of method — a future reader who assumes it's skill-only will make the same
  mistake this fix corrects.
- The provenance chain tuple grew a 4th element (`"path"`/`"skill"`) — a caller pattern-matching the
  old 3-tuple shape (`[seat, pid, cli_pid]`) will break; both message-render sites now read
  `chain[3]`.
- This is distinct from task 163 (declared `rw-paths` never composed for template family
  `rbtv-and-mirror`) and task 122 (spawn.js later-wins `rw-paths` vs `exposedCliCode` collision) —
  neither was touched.
