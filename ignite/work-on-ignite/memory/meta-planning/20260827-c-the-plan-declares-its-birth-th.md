# 20260827-c-the-plan-declares-its-birth-th — the plan declares its birth; the leader binds it

kind: change
component: meta-planning
date: 2026-08-27
commit: ee4a0334
deployed: no
pin: ignite/planning/probes/probe-approve-package.js
components: meta-leader,planning

## Motivation
Test 4 of the acceptance wave ran the whole five-seat `plan-console` pipeline on the live goal
`scratch-tool-reach-note` on 2026-08-27 and stopped inside verify with both contract checks
PASSING. Two things the pipeline never produced made the plan unapprovable, and neither was any
seat's failure. First, the binding commit: `review-plan.md:22`, `reviewer.md:25` and
`workflow.md:60` all promised "approval binds at a git commit the verifier will record", and the
verifier proved it cannot — it runs caged with `.git` masked
(`ignite/supervisor/spawn/private-scope.js`, `**/.git` in `DEFAULT_PATTERNS`), so
`git rev-parse HEAD` answers "not a repository", and `approve_package.py` refused
`bad-bound-commit` on the literal `HEAD` the prompt told it to derive. From outside, nobody
committed the artifacts either: `git -C <vault> ls-files .rbtv/goals/scratch-tool-reach-note` = 0,
while other goals' `planning/` folders ARE tracked. Second, the execution goal: `approve` runs a
Path-B BIRTH (`state-store/heart/start-execution.js` → `wrapper.py#supervised_materialize`) that
scaffolds a NEW goal folder and mints its roster, but `draft-plan.md` and `review-plan.md` asked
for no name, lane or roster — so the drafter planned to "execute in place" and assigned `leader`
to cast the new seat by hand, which `leader`'s own `<restrictions>` forbid. The leader escalated
both (escalation #12, goal `decisions.md` 19:37Z) and the owner ruled on 2026-08-27 20:29Z that
the contract is fixed at its cause and the wave re-runs test 4 on a fresh goal.

## Design
The BINDING PERFORMER is the `leader`, and it learns the act as a GENERIC rule in its own §4
rather than as a plan-console step: accepting a seat whose declared `goal-writes` lands under
`planning/` commits those artifacts, because approval-binds-at-a-commit is a planning-component
invariant and not one workflow's trick. The leader is the only chair that can do it — it is
uncaged and holds git — and `supervise accept` is the act that advances the `after` edge to the
verifier, so the binding happens exactly where the artifacts stop changing. The hand-off channel
is A FILE, `<goal>/planning/bound-commit`, not a bus note: `planning/` is read-write to every seat
through `bind:{goalDir}` (D3), the file sits beside `approve-package.json` and `bound-plan.json`
which the same door already reads, it is read deterministically rather than parsed out of prose
(the same reasoning that put the approve-package behind a writer instead of letting a seat type
JSON), and it survives a relaunch without depending on the verifier's mail cursor. It is
deliberately NOT inside the commit it names — a file cannot contain its own hash, and it is a
pointer, not a plan artifact.

The EXECUTION DECLARATION carries exactly the fields `approve_package.py` takes and nothing it
does not — `execution-goal` (a bare safe name, `^[A-Za-z0-9][A-Za-z0-9._-]*$`, never `owner`),
`lane`, `roster`, `workflow`+`sheet`, `contract-file` — because THE READER DEFINES THE CONTRACT,
the same rule the writer itself was built on (b2449ebe). Rejected: an in-place execution mode.
The owner ruled the built mechanism (birth) is the design, and a second mode would have needed a
second door, a second package shape and a fork in every downstream reader. Rejected: letting the
verifier default a name — approval births a goal under it, so inventing one approves a goal the
plan never described.

## How it works
`meta/leader/prompts/leader.md` §4 gains the binding act with its exact commands —
`git -C <vault root> add .rbtv/goals/<goal>/planning`, then
`git -C <vault root> commit -m "<goal>: plan artifacts for approval" -- .rbtv/goals/<goal>/planning`,
then `git -C <vault root> rev-parse HEAD` — with the vault's parallel-session discipline stated as
the reason (`-- <pathspec>` on the COMMIT is the only bound that holds on a shared index; never
`add -A`, never `--amend`), the already-clean case (nothing staged → HEAD still contains them,
check with `ls-files` before writing it), and the wake-up arm: a seat reporting a missing
`bound-commit` is disposition 1, FIX AND RELAUNCH. Its `<permissions>` and `<restrictions>` gain
the carve-out that committing is not editing. `tasks/serve-staff-mail.md` carries the matching
done clause and write surface; `component.md` states the invariant.

On the planning side, `tasks/draft-plan.md` and `prompts/drafter.md` gain the execution
declaration as step 4 of the procedure and a done criterion, plus the statement that the daemon
mints the roster at birth and no seat casts an execution seat — which removes the "who performs
the casting act" class rather than re-assigning it. `tasks/review-plan.md` and `prompts/reviewer.md`
make a missing or invalid declaration `blocking`, and make a mechanism that names ANY seat as the
caster blocking too, with the warning that R2 was born by reasoning about the CAGE and concluding
about the DESCRIPTOR. `tasks/verify-plan.md` and `prompts/verifier.md` replace `git rev-parse HEAD`
with reading `planning/bound-commit`, refuse to compose or send without it (never
`commit: uncommitted`, which asserts something a caged seat cannot know), and pass the declared
fields straight to the writer. `workflow.md` states the birth at the top and the 4→5 binding edge
in step 4; `plan-console.csv` and `seats.csv` carry the new input and outputs in their row
descriptions.

## Consequences
Nothing was deleted and `ignite/planning/approve_package.py` is byte-unchanged — every declared
field already had a flag. One pre-existing defect was fixed in passing: `tasks/review-plan.md`
ended with a stray `</output>` closing tag that had no opener. The verifier prompt's frontmatter
`description` and `<role>` scope still said "do not post (a later seat posts)", left behind by
8f299bc6 which gave that seat the Send clause; both now agree with the task. The plan-console
pipeline gains one relaunch on the path where the reviewer checks out `done` on its own and the
leader is therefore never woken to bind: the verifier refuses, checks out `--incomplete`, the
staff mail wakes the leader, it binds and relaunches. That is the intended self-healing shape, not
a gap — but it is a relaunch that did not exist before.

## Verification
Offline on a scratch git repo under `/tmp` mimicking `<vault>/.rbtv/goals/<goal>/planning/`, never
the live goals root. The leader's three commands run with a parallel session's file already
STAGED: the commit carried the four planning artifacts and not the peer's file, proving the
pathspec bound holds. `approve-package` then accepted that sha plus a declared execution goal and
wrote the package (`python3 -m json.tool` shows `bound_commit`, `execution_goal`, `lane`,
`plan_artifacts`, `roster`, `sheet`, `workflow`); the BIRTH DOOR's own reader agrees at that
commit — `path_b.commit_exists` True, `path_b.artifacts_resolvable` True, and False for a bogus
sha. The two refusals the live run hit still fire on the old inputs: `bad-bound-commit` on `HEAD`
and `bad-execution-goal` on `in place`, both exit 2. `component_lint` before/after: `meta/planning`
5 findings (the two extra in the HEAD worktree were `ws:`-prefix artifacts of running from /tmp),
`meta/leader` 2 findings — all pre-existing and untouched. `probe-approve-package` 16/16 PASS.
NOT DEPLOYED, and no deploy is needed for these texts: the catalog root for the `meta` module is
`rbtv.json`'s `rbtv_path` (`ignite/planning/unbuilt-seats.js:61`), i.e. the working repo, so a
FRESH goal materializing reads them immediately. Already-materialized descriptors do not.

## ATTENTION
- These `meta/` texts are LIVE the moment they are on disk in the working repo. The catalog root
  resolves through `rbtv.json`'s `rbtv_path`, NOT the deploy worktree — there is no "not deployed
  yet" safety margin for a bad edit here, only "no goal has materialized since".
- An already-materialized goal does NOT pick up a changed task or prompt. `seat.md` has one
  writer, `planning/materialize-seats.py`, reached by the creation route or
  `--seat <name> --refresh`, and nothing in the spawn path re-renders it.
- Never tell a caged seat to run `git`. `**/.git` is a default mask in
  `supervisor/spawn/private-scope.js`, and the failure is not a permission error — the directory
  lists EMPTY, so git reports "not a repository" and a seat can read that as "no commits exist".
- `bound-commit` cannot be inside the commit it names. A future editor tempted to "fix" that by
  committing twice will produce a hash that names a tree without the second commit's content.
- Reason about a seat's DESCRIPTOR, never its cage, when assigning an act. R2 assigned seat-casting
  to `leader` because it is uncaged; `leader`'s `<restrictions>` forbid it. Being able to is not
  being permitted to, and the reviewer text now says so.
- meta/ texts are live from the working repo, not the deploy worktree
