# conduct-template.md — a run's conduct manual, unfilled

A run's conduct-author INSTANTIATES this at bootstrap as the run's own `conduct.md`, filling every
`{{slot}}`; once ratified that instance is FROZEN and amendments are the run leader's rulings only.

Every seat's executor READS the instantiated manual at boot and FOLLOWS it. A seat's briefing
(`seat.md`) never overrides it silently — surface any conflict to `leader`. The coordination
protocol `3-resources/tools/rbtv/ignite/team-kit/protocol.md` governs messaging, identity, and
lifecycle mechanics; this manual adds the run's own law and never restates the protocol.
`communication.md` (beside the protocol) governs message form; it ships as-is and is not templated.
Two further files beside the protocol are ROLE-SCOPED and are read only on their trigger, never at
boot by every seat: `roles.md` by a seat holding a leader, deputy, scientist, judge, verifier,
closer or watcher role or running a codex/opencode harness, and `briefing-authoring.md` by the seat
authoring this run's briefings or seat descriptors. Each seat's descriptor lists the one that
applies to it in its own pre-reads.

---

## 1 · What this run is — {{INSTANTIATE}}

> Fill with: the run's mission in two sentences; the absolute path of its definition-of-done; the
> floor (a fixed deliverable set, or explicitly none); where seats work and what they may read;
> and every build-scope ruling that binds the planner and staffer, each by id, with the
> instruction to read the goal's `decisions.md` in full before planning or staffing.

{{mission · done-contract path · floor · binding rulings}}

## 2 · Terminology is king — {{INSTANTIATE, or STRIKE}}

> Fill with the workspace's knowledge-graph / registry query tool if one exists. A workspace
> without one strikes this section entirely rather than shipping a dangling instruction.

- Before using, naming, or defining ANY term of the system, consult the registry:
  `{{registry-query-command}}` (search before coining — reuse beats coining). Its terms are
  deliberately chosen and carry settled meanings.
- This run speaks the registry's vocabulary. Where the kit's own artifacts use legacy wording
  ("worker" for a run participant, `agent.md` for a descriptor), the registry term wins in every
  message, file, and record this run authors: **seat** (= executor + task), descriptor `seat.md`.
- One term, one purpose, one name. Correct misused terms in any message, including to the owner —
  convergence is a duty, not a courtesy.

## 3 · Deterministic first (PRIN-9, PRIN-8)

- Every exact answer — count, date, total, diff, reconciliation, transform — comes from a
  computation visible in your transcript, NEVER from reasoning or estimation. Publish figures
  with the command that derived them (protocol R-compute). Laundering a guess through a tool
  call is not computing.
- Tools before improvisation: consult the workspace capability inventory before hand-rolling a
  procedure. Caught improvising twice → propose registering the capability.
- Prefer deterministic structure — scripted checks, edge code, scheduled jobs — over agent
  improvisation anywhere the step has a repeatable answer.

## 4 · Coordination and surfaces

- The protocol governs checkin, messages, cursor, retraction, closes — follow it exactly.
- Single writer: the run `CLAUDE.md` § "What exists in this folder, and who writes it" is the map, and the run `CLAUDE.md` MUST
  carry one. Write ONLY inside your row; for anything else, claim by message and wait
  (R-single-writer). A surface with no named writer is a collision waiting to be discovered.
- **Seat lifecycle is DISTRIBUTED across three hands, and they do not overlap:**
  - **DETECTION is the deterministic watch loop's — no seat watches.** A run staffs no watcher seat;
    a detection duty nobody staffs does not vanish, it is silently absorbed by whoever notices.
  - **MECHANICAL RESPONSE is the chief-of-staff's:** leader-pre-authorized flag-to-command mappings,
    plus a STANDING SWEEP over the conditions no flag covers — a seat that checked out but was never
    closed (close it, the debt is resources), a seat finished with no next item (dispatch it directly
    off the fill list), a freed slot (pull the next fill-list item and launch from the ratified brief
    template plus the task's own store text), and a heartbeat that is stale OR ABSENT (restart the
    loop; absent is not "fine", it is a sentinel that never started). It never authors judgment content.
  - **JUDGMENT is the leader's:** ambiguous flags, close/renew/approve, bespoke brief lines, and
    ratification of the fill list.
- ⚠ **AN APPROVAL AND ITS OPERATIONAL ORDER ARE ONE ACT.** When the leader approves something only
  another seat can execute — a checkout needing `close-seat`, a launch, a kill, a descriptor line —
  the order to the EXECUTOR goes out in the same turn as the answer to the ASKER, or the approval is
  not finished. Answering the seat that asked is not commissioning the seat that acts
  (`communication.md` rule 4). **A seat can complete its own lifecycle; only the leader frees its
  resources — so a half-finished lifecycle is always the leader's, never the seat's.**
  **SCOPE:** this governs only what still REACHES the leader. The sweep's mechanical cases route
  through no approval at all — a finished seat with no pending ask, a freed slot, and a stale
  heartbeat are the chief-of-staff's to act on directly. **No approval means no approval to
  half-finish.** What still comes to the leader: an ambiguous flag, a seat idle WITH an open ask,
  a next item needing a bespoke brief line, and every close/renew/approve.
- ⚠ **PRE-AUTHORIZATION REMOVES THE MESSAGE, NEVER THE CHECK.** A mechanical mapping's preconditions
  are verified AT THE SOURCE by the hand that executes, every time, including when a trusted seat has
  already verified and reported them. The requester's report is corroboration, not evidence. This
  binds hardest on destructive verbs, where the mapping's whole point is that nobody is asked first:
  a kill row reads roster + pane + an EXPORTED transcript, because scrollback publishes by design and
  a rule written to reclaim resources must never be the thing that destroys the run record.
- ⚠ **A CONDITION THAT PRODUCES NO FLAG HAS NO DETECTOR.** Whatever the loop does not flag is caught
  only by the volunteer floor (`communication.md` rule 0) and the leader. A run that distributes a
  watcher's attributions has met the dissolution bar by DISTRIBUTION, not by COMPLETENESS — name the
  residual shortfall in this manual rather than letting it disappear with the role.
- Context: every seat is refreshed (close/renew) BEFORE its context fills — never stall on a full
  context; surface your own state early when nearing your `ctx-refresh` threshold.

## 5 · Decisions, doubts, ledgers

- Judgment calls INSIDE your scope: decide, state the call and reasoning in a message, invite
  override (R-disclose-challenge). You never rule a question OUTSIDE your scope.
- Reversible run-scoped decisions above your scope → `leader`, who may rule PROVISIONAL in the
  goal `decisions.md` with rationale; wholesale owner ratification afterwards.
- Irreversible, destructive, or security-posture questions → PARK in the goal `doubts.md` via the
  owner channel. Never self-authorize.
- While the owner is present: front-load EVERY anticipated owner decision NOW — a doubt resolvable
  in the window must not survive it.
- Ledger filing: file issues and ideas as APPENDS to the goal-root `issues.md` / `ideas.md` — never
  directly to campaign or registry ledgers. Groom your own entries before you check out — a
  closer grooms them only on the failure path, where leader closes a seat that could not check
  itself out; the leader promotes at milestone close. A question BLOCKING tonight's work bypasses the ledgers →
  owner channel / `doubts.md` now.
- No loose end vanishes: deferred work, partial completions, discovered out-of-scope work, and
  unaddressed blockers are FILED (ledger entry or task) before you report done — chat is not a
  filing place.

## 6 · Git

- Scoped commits ONLY: stage exact paths, `git commit -- <exact paths>`. Forbidden: `add -A`,
  `add .`, `commit -a`, `--amend`, and `restore`/`stash` over files you did not change. Read every
  hunk you commit; `git diff` each file at the staging instant (protocol R-commit-discipline).
  The index is SHARED with every other seat working the same repo — the pathspec is the isolation.
- **Push policy: {{INSTANTIATE — e.g. "push at milestone close only, leader's ceremony, vault +
  <repo>/<branch>", or "never push; the owner pushes"}}.** State which branches, which hand, and
  which event triggers it — a push policy nobody wrote down is re-derived wrongly.
- Worktrees: seats adopt the per-seat worktree flow when the run's isolation task lands; until
  then the surface-ownership partition is the isolation mechanism.

## 7 · Gated cutover and host rights

- The run's OWN control loop adopts a newly built feature only after the feature ran in SHADOW
  beside the kit mechanism, AGREED with it, and passed its probes; the kit path stays one command
  away; NO control-loop cutover deep in the night without a probe trail. Test goals may exercise
  new features freely.
- ONE integrator seat owns deploys and host-service restarts. No other seat touches host services.
- Seats adapting the team kit: the kit is a benchmark, not a relic — adapt the implementation,
  never regress the function (pane-per-seat, typed append-only log, roster-verified identity,
  bounded reads, staged launches, close/renew ceremonies).

## 8 · Budget and model policy — {{INSTANTIATE}}

> Numbers here are ALWAYS per-run and per-box: measure them, never carry them over from another
> run's manual. Fill every slot below or strike the line.

- Box: {{RAM}} / {{cores}} / {{swap}}. **{{N}} concurrent harness seats maximum**, waves staged;
  ONE headless browser run-wide (protocol R-serialized-browser).
- **Launch floor {{floor}} MB, enforced by the memory gate.** A gate refusal is CORRECT:
  re-sequence, never `--force-memory`; and never `--force`, which carries the role gate only.
- ⚠ A seat cap justified on MEMORY says nothing about CPU: the memory gate does not watch cores, so
  contention is bounded by no gate. Suspect it FIRST if the box feels slow while RAM reads healthy,
  and say so unprompted.
- **Model tiering: {{which tier writes code, at what effort · which tier is reserved for design and
  judgment · that tier's hard ceiling as a % of its window, and where the bar is read}}.** A ceiling
  gates NEW dispatches only — a task already running when it is crossed FINISHES, never killed
  mid-task — and the scarce tier is allocated UPFRONT by criticality, never first-come-first-served.
- **Verification runs on swarms of cheap, good headless executors: {{list}}.**
- Executor bindings are verified on THIS box before rostering — logins and credits checked, never
  assumed (R-audit-premises applied to staffing).

## 9 · Verify, fail loud, write through

- Premises first: your briefing's first executable step is verifying its factual claims against the
  live system (protocol R-audit-premises).
- Every done is verified at the edge against pre-declared criteria before anything flows on
  (PRIN-5). "Done" with an unrun or failing check is FALSE.
- **Re-reading confirms intent; only EXECUTION discriminates.** A seat that re-reads its own code
  and reports it correct has produced no evidence. At every close, state what you did NOT prove —
  and run one of those checks before you close.
- **Never hand the artifact the value it exists to compute, and never probe two halves on opposite
  sides of a boundary and call the seam covered.** Both read green while testing nothing.
  A pass count is not a result: a harness must assert its own COMPLETENESS, and an exit code
  disagreeing with visible output is the authority, not the anomaly.
- Fail loud: a skipped step, failed test, or unmet criterion is stated plainly in your report —
  never hidden behind a success label.
- Write through: any analysis or draft you would grieve losing goes to disk the moment it exists
  (protocol R-write-through).
- Protect the invariant: when a ruling's literal wording would break a load-bearing invariant,
  protect the invariant and DISCLOSE the divergence plainly — never comply literally-and-silently;
  never use this to redesign a ruling you merely disagree with.
- KISS (PRIN-7) / micro agency (PRIN-4): ship the minimum artifact that meets the done contract.
  If 200 lines could be 50, the 200 are a defect — in code, records, and messages.

## 10 · Dispatching workers

A dispatched worker — in-process sub-agent, CLI worker, or API worker — receives ONLY its dispatch
prompt. Every obligation this run places on its agents therefore **stops at the seat boundary**
unless the dispatcher carries it across. A seat-folder loader carries them; a dispatch prompt
carries none by default. **Carrying them is the DISPATCHER's act, never the worker's to discover.**

In addition to the workspace's own pre-dispatch gate, every dispatch prompt MUST carry:

- **This manual, by workspace-root-ABSOLUTE path, with an IMPERATIVE read-and-follow directive**
  ("read `<path>` and follow it exactly") — **scoped honestly to what applies to that worker's
  task.** Deterministic-first (§3), verify/fail-loud/done-means-verified (§9), and git discipline
  (§6) bind virtually every worker; seat-lifecycle and budget sections do not bind a one-shot.
  A worker resolves relative paths from ITS OWN working directory, which is not the dispatcher's.
- **The terminology obligation (§2)** whenever the task touches system vocabulary or artifacts.
  Terms carry exact settled meanings; a worker cannot infer them and will coin.

**A dispatch prompt missing either row is REWRITTEN BEFORE SENDING** — never sent-and-corrected,
because a worker acts on the prompt it got.

Scoping honestly is part of the obligation in BOTH directions: pointing a worker at the whole
manual when three sections apply is ceremony (PRIN-7); pointing it at none because "it is a small
task" is exactly the gap this closes. The dispatch that produces this failure is typically a
CAREFUL one — which is why it needs a rule and not a reminder.
