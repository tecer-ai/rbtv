# 20260831-i-caged-planning-seat-could-not — caged planning seat could not file the engine register

kind: issue
component: supervisor
date: 2026-08-31
commit: 98186c76
deployed: no
pin: NONE
components: coord,meta-planning

## Observed
Every caged planning seat that hit an ignite or meta defect dumped it into the goal issues.md because file-issue doctor reported writable False and file-issue file refused register-not-writable. Uncaged leader then hand-filed. Measured 2026-08-31 on today's tree: live plan-designer seat.md has no cli-write-roots and no file-system-issue expose; composeCageFor against a planning-seat fixture produced zero --bind of the engine register; a bwrap ro-root with no register grant printed writable: False / refuse: register-not-writable against both a scratch register and the live path `.rbtv/goals/ignite-engine/register`.

## Mechanism
Two origins, both required. Planning prompts never declared skill file-system-issue, so materialize never baked cli-write-roots for plan-* seats. Independently, spawn.js defined resolveCliWriteRootGrants but composeCageFor never called it after the envelope rewrite: the compiled spec is vault-wide-read ro over the workspace, and the W6 bind never landed. os.access on the register then failed inside the cage. Staff chairs are uncaged so their baked roots never had to become binds; planning seats are caged and had neither the bake nor the bind.

## Attempts
First attempt held — checked: 2524e4c9 (file-issue CLI plus skill, write-root on the exposure row), 2b00b593 (cli-write-roots goals-tree rule), 20260822-c-file-issue-cli-skill, and d6b59389 (rw-paths extraPaths compose). Those made the CLI and the skill-walk exist; they did not call resolveCliWriteRootGrants from composeCageFor, and they did not put the skill on planning prompts. Passing cli-write-roots through admitLaunch extraPaths was rejected here because compilePlanning wipes extraPaths and the memory root sits under rbtv-repo which has no authorizedCarve.

## Fix
composeCageFor now appends --bind for each resolveCliWriteRootGrants entry after the compiled spec and before private-scope masks, so lastCovering does not re-ask the compiler and a deny still wins. Plan-console prompts (understander, designer, drafter, reviewer, verifier) declare the skill and the file-issue path so materialize bakes the register write-root. Raw --bind rather than extraPaths because the memory write-root lives under rbtv-repo (seat 122's carve) and compilePlanning zeros extraPaths on planning goals.

## Consequences
A granted caged seat can file without an uncaged leader ferry. Seats that do not expose the skill still refuse. Live planning seat.md files stay stale until rematerialize. spawn.js bind is daemon JS and is inert until deploy. Forge prompts (intake, builder, dod-judge, unblock-checker) were left without the grant on purpose so criterion 3 keeps a control class. 163 and 122 were not closed.

## Verification
Red: bwrap --ro-bind / / file-issue doctor against the live register printed writable: False / refuse: register-not-writable (exit 1). composeCageFor on a planning fixture without cli-write-roots produced binds=[]. After the fix: composeCageFor on a fixture with cli-write-roots pointing at a scratch copy of `.rbtv/goals/ignite-engine/register` produced --bind of that path; bwrap with that bind printed writable: True and file-issue file created G-plan-filer-0831-test under the scratch open/; the control seat without the bind still refused register-not-writable exit 2. file-issue.py selftest PASS. Not deployed.

## ATTENTION
- cli-write-roots must stay raw --bind after the compiled spec. Feeding them through extraPaths hits compilePlanning's extraPaths wipe on planning goals and authorizedCarve's missing rbtv-repo carve on the memory root.
- Planning seat.md only gains the grant after rematerialize. Editing the prompt is not enough for a sitting already on disk.
- A grant that lands on every caged seat (not just those exposing file-system-issue) fails the discriminating control: researcher/diagnoser/writer and forge seats must still refuse.
- cli-write-roots must stay raw --bind after the compiled spec; extraPaths hits compilePlanning wipe and the rbtv-repo carve hole
- Planning seat.md only gains the grant after rematerialize; editing the prompt is not enough for a sitting already on disk
