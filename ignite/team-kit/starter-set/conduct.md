# conduct.md — run conduct manual

The run's rulebook. Every seat's executor READS this at boot and FOLLOWS it. Shipped as the
goal-generic STARTER SET and byte-copied into this run package at scaffold time
(`scaffold-seats --conduct`); from that copy onward it is THIS run's own manual. FROZEN once the run
opens — an amendment is a ruling by the seat holding run authority, recorded as an entry in this run
folder's own `decisions.md`.

Your briefing (`seat.md`) never overrides this manual silently — surface any conflict before acting.
Two kit files bind in full and this manual restates neither: the coordination protocol
`3-resources/tools/rbtv/ignite/team-kit/protocol.md` (messaging, identity, lifecycle mechanics) and
`3-resources/tools/rbtv/ignite/team-kit/communication.md` (message form, caps, the volunteer floor).

Paths are workspace-root-relative — the directory that roots `.rbtv/`. From this run folder the goal
root is `../../`: its contract `../../goal.md`, its goal-durable ledger `../../decisions.md`, its run
register `../../runs.csv`. Anchors cited `r-*`/`d-*` resolve in `../../decisions.md`; run-scoped
PROVISIONAL `p-*` anchors resolve in THIS folder's own `decisions.md`. **No seat reads either ledger
end to end** — every ruling that binds you is compiled into your `seat.md` or cited to you as an
anchor you resolve.

## 1 · What this run is

- **The goal's contract is `../../goal.md`.** Read it. This manual never restates it, and a done
  radius remembered from anywhere else is not the contract.
- This is the goal's first run, created with the goal itself. Its first workflow is **planning**: a
  9-seat DAG whose entry seat is `elicitator`. **The plan is this run's first deliverable** — nothing
  downstream is built, staffed, or committed before the plan exists.
- Work from YOUR seat folder. Execute ONLY your briefing. Never read another seat's folder or
  briefing, and never resume from another seat's state.
- No fixed deliverable floor is declared here. The floor is whatever `../../goal.md` states; a run
  whose contract states none produces the plan and stops.

## 2 · Terminology is king (PRIN-10)

- Before using, naming, or defining ANY term of the rbtv system, consult the knowledge graph:
  `sd-graph show <term>` (`sd-graph find` before coining — reuse beats coining). Terms are settled
  and exact; a term `show` cannot resolve is NOT a term of this system — say so, never invent a
  meaning.
- This run speaks KG: **seat** (= executor + task), never "worker" (kit-internal legacy wording); the
  seat descriptor is `seat.md`, never `agent.md`.
- One term, one purpose, one name. Correct misused terms in any message, including to the owner —
  convergence is a duty, not a courtesy.
- Nothing you author assumes one harness (PRIN-6): any supported harness may occupy a seat, and a
  seat folder carries every harness's scaffolding from creation. Harness-specific spelling lives at
  the exposure edge, never inside the content.

## 3 · Deterministic first (PRIN-9, PRIN-8, PRIN-2, PRIN-13)

- Every exact answer — count, date, total, diff, reconciliation, transform — comes from a computation
  visible in your transcript, NEVER from reasoning or estimation. Publish figures with the command
  that derived them (protocol R-compute). Laundering a guess through a tool call is not computing.
- Tools before improvisation (PRIN-8): you are HANDED your means — consult the workspace capability
  inventory before hand-rolling a procedure. Caught improvising twice → propose registering the
  capability.
- Every action you take is a replayable CLI command (PRIN-2). An act you can only perform by hand is
  a parity defect — file it, never normalize it.
- What you do build, build capability-shaped (PRIN-13): own entry point, own i/o, no caller-baked
  paths or constants. KISS still caps the scope; recurrence still gates registration.
- Prefer deterministic structure — scripted checks, edge code, scheduled jobs — over agent
  improvisation anywhere the step has a repeatable answer.
- ⚠ **`sb-task edit`'s body flags are not additive, and there is no class to remember.** `--why`
  REPLACES. `--context` REPLACES, APPENDS, or silently APPENDS A DUPLICATE depending on what the
  task's bullet label IS — including when it is absent. **`--dry-run` FIRST, ALWAYS, on every task,
  every time.** Every attempt to predict this from a remembered class has been wrong; the dry run is
  what makes a wrong prediction cost nothing.

## 4 · Coordination and surfaces

- The protocol governs checkin, messages, cursor, retraction, closes — follow it exactly.
- **Single writer:** this run's `CLAUDE.md` § Surface ownership is the map. Write ONLY inside your
  row; for anything else, claim by message and wait (R-single-writer). A surface with no named writer
  is a collision waiting to be discovered — name one before you write, do not just write.
- **`coord.py` custody is never seat-bound:** claim it BY MESSAGE on the bus before you change it,
  and save ONLY via `python3 3-resources/tools/rbtv/ignite/team-kit/save-coord.py --candidate
  <NEW.py>` — nothing else. `--candidate` is a FLAG, not a positional. A hand-rolled temp-file →
  `os.replace` DROPS THE EXEC BIT and takes the room's messaging down at module import, including
  every recovery path.
- **A clean CHECK-OUT is what advances the workflow.** Your check-out must be clean and carry a
  disposition. A successor seat is READY only when EVERY predecessor has checked out clean with
  disposition `done`. This is an obligation on your own close: a check-out you skip or leave dirty
  blocks seats you will never meet.
- **The `exited` disposition never advances an edge.** It is written by the MACHINERY for a seat that
  could not write its own. It routes to the seat holding run authority, which has exactly two exits:
  rule a relaunch, or flip the row to `done`. A routed edge never sits blocking its successors.
- **DETECTION is the deterministic watch layer's — no seat watches, and no watcher seat is staffed.**
  Its chain is: detect → inline mechanical fix → nudge the SEAT → nudge the run authority
  (`d-watcher-deterministic-chain`). ⚠ **`chief-of-staff` and `closer` are RETIRED roles.** Never
  wake, spawn, address, or fall back to one; any code, config, or prompt that does is built against a
  dead spec — flag it, never extend it.
- ⚠ **A CONDITION THAT PRODUCES NO FLAG HAS NO DETECTOR.** Whatever the watch layer does not flag is
  caught only by the volunteer floor (`communication.md` rule 0). So a seat that runs out of work SAYS
  SO unprompted, and every seat treats "no flag" as "no detector fired", never as "nothing is wrong".
- **Resolve the escalation addressee from the ROSTER, never from memory or from this file.** A seat
  holding run authority is resolved from `taskforce.csv` / `coordinate workers` at the instant of use.
  **A freshly scaffolded run carries the planning DAG's seats and NO authority seat** — when no such
  row exists, the call is neither yours to make nor to improvise: file it in the goal's
  owner-decision queue `../../doubts.md`, say so on the bus, and stop the dependent work. Inventing an
  addressee and self-authorizing are the same failure.
- ⚠ **AN APPROVAL AND ITS OPERATIONAL ORDER ARE ONE ACT.** When an authority approves something only
  another seat can execute — a close, a launch, a kill, a descriptor line — the order to the EXECUTOR
  goes out in the same turn as the answer to the ASKER, or the approval is not finished. Answering the
  seat that asked is not commissioning the seat that acts.
- ⚠ **PRE-AUTHORIZATION REMOVES THE MESSAGE, NEVER THE CHECK.** A pre-authorized mapping's
  preconditions are verified AT THE SOURCE by the hand that executes, every time; the requester's
  report is corroboration, not evidence. This binds hardest on destructive verbs, where nobody is
  asked first: an act written to reclaim resources must never destroy run record.
- **A seat can complete its own lifecycle.** A seat's own renewal is its own deterministic act —
  `coordinate checkout --renew --handoff "<note>"`: no approval, no greenlight. Only the run authority
  frees ANOTHER seat's resources.
- When you report a refusal, **NAME ITS LAYER**. `refused [coord …]` is `coord.py`'s own gate;
  anything else is your harness's permission classifier. A bare "refused" sends the run at the wrong
  fix.
- **Context:** every seat is refreshed (close/renew) BEFORE its context fills — never stall on a full
  context; surface your own state early when nearing your `ctx-refresh` threshold.

## 5 · Decisions, doubts, ledgers (PRIN-12)

- Judgment calls INSIDE your scope: decide, state the call and reasoning in a message, invite override
  (R-disclose-challenge). You never rule a question OUTSIDE your scope.
- Reversible run-scoped decisions above your scope → the run authority, which may rule PROVISIONAL
  (`p-*`) in THIS folder's `decisions.md` with rationale; owner ratification follows. With no
  authority seat rostered, § 4's escalation rule governs.
- Irreversible, destructive, or security-posture questions → PARK in `../../doubts.md`. Never
  self-authorize.
- While the owner is present, front-load EVERY anticipated owner decision — a doubt resolvable in the
  window must not survive it.
- **Ledger filing.** File issues and ideas as APPENDS to `../../issues.md` / `../../ideas.md` (each is
  created by its first append) — never directly to a campaign or registry ledger. **`issues.md` is
  PURE APPEND-ONLY at write time:** append your row and stop — no dedup scan, no max-id derivation, no
  renumbering, no rating. Id = `G-<seat>-<MMDD>-<HHMM>`; duplicates are tolerated until a grooming
  pass, which owns dedup and the impact/effort rating. A question BLOCKING current work bypasses the
  ledgers → `../../doubts.md` now.
- **Entry shape** for both `decisions.md` files: decision + rationale + scope only, per
  `3-resources/tools/rbtv/orchestration/workflows/_shared/authoring/decisions-discipline.md`. Supersede
  by appending; never rewrite an entry.
- **The remember set is MECE:** `ideas.md` holds what was framed but never ruled · `issues.md` holds
  the open questions that must be ruled · the two `decisions.md` ledgers hold every ruling · the run's
  settled content holds what a ruling made TRUE. Nothing falls outside the four; nothing sits in two.
- The run compounds only through what lands durably (PRIN-12): a learning that dies with your session
  has changed nothing. **No loose end vanishes** — deferred work, partial completions, discovered
  out-of-scope work, unaddressed blockers and reusable findings are FILED (ledger entry or task)
  before you report done. Chat is not a filing place; the next run reads only what was written.

## 6 · Git

- **Scoped commits ONLY:** stage exact paths, `git commit -- <exact paths>`. Forbidden: `add -A`,
  `add .`, `commit -a`, `--amend`, and `restore`/`stash` over files you did not change. Read every
  hunk you commit. The index is SHARED with every other seat in the same repo — the pathspec is the
  isolation.
- ⚠⚠ **`git commit -- <pathspec>` COMMITS THE WORKING TREE AT THOSE PATHS AND IGNORES THE INDEX.**
  Hunk-level isolation — `git apply --cached`, `add -p` — is SILENTLY DISCARDED at the commit verb:
  exit 0, no warning, while `git diff --cached` keeps showing your isolation truthfully. ⇒ **WHEN A
  PATH CARRIES A FOREIGN HUNK THERE ARE EXACTLY TWO OPTIONS: commit the file WHOLE and disclose the
  foreign hunk truthfully, or do not commit that path at all.** Hunk-level staging is not a third
  option.
- ⚠ Check BEFORE with **`git diff HEAD -- <file>`, NEVER bare `git diff`** — the bare form compares
  against the INDEX and is BLIND to a foreign hunk a parallel session has already staged, which is a
  shared room's normal condition. `git diff HEAD` is exactly the set the commit will take.
- ⚠ Verify AFTER with **`git show <sha> -- <path>`** — the only artifact that settles what you
  actually took. The two checks cover DIFFERENT failures and neither substitutes for the other: the
  before-check fixes what the TOOL cannot see; the after-check fixes what the PERSON does not read.
  Run BOTH, every commit.
- ⚠⚠ **A FOREIGN HUNK THAT IS A DEPENDENCY OF YOUR OWN CHANGE DEFEATS BOTH OPTIONS — THE ANSWER IS
  ORDERING, NOT ISOLATION.** Sequence the landings: the seat whose change is DEPENDED ON commits
  first, the dependent commits on top and RE-RUNS ITS PROOF afterwards. A green taken against a tree
  carrying someone else's uncommitted change is a claim about a tree nobody has committed.
- **Push policy: this run does not push.** Commits are local and scoped; the owner pushes. A run whose
  `../../goal.md` puts a push in scope states the branch, the hand and the triggering event as a
  ruling in this folder's `decisions.md` before the first push — a push policy nobody wrote down is
  re-derived wrongly.
- Until a per-seat worktree flow is adopted, the surface-ownership partition is the isolation
  mechanism.

## 7 · Host rights

- A run does NOT deploy, restart, or stop a host service unless its own `../../goal.md` puts that in
  scope. When it does, the act is CLAIMED on the bus before it is performed, so two seats never
  restart into each other.
- A newly built feature is adopted by the run's own control loop only after it ran in SHADOW beside
  the existing mechanism, AGREED with it, and passed its probes; the existing path stays one command
  away. No control-loop cutover without a probe trail.
- The team kit is a benchmark, not a relic: adapt the implementation, never regress the function
  (pane-per-seat, typed append-only log, roster-verified identity, bounded reads, staged launches,
  close/renew ceremonies).

## 8 · Budget and model policy (PRIN-11)

- **Every capacity and policy NUMBER of this run has ONE home: this run's `budget.json`**
  (`r-bar-home-is-the-run-budget-json`, `r-floor-single-source`). A consumer READS it — a number
  carried by argv, env, prose, or memory is a COPY, and every copy drifts. `floor-lint.py` refuses a
  floor literal anywhere else, this manual included. **That is why no threshold below is stated
  numerically, and why you must not add one.**
- The pane cap (`budget.json` → `cap.agent_panes`) counts AGENT panes ONLY — an owner door, a
  dashboard, the watch loop NEVER count — and the census is MEASURED at each fill pass, never
  remembered. ONE headless browser run-wide. **The cap is a CEILING, not a licence:** memory binds
  first, and below it the `coord.py` single-writer queue. Reading cap headroom as room to launch is
  the error — measure RAM and let the gate refuse.
- **Two floors, two purposes** (`budget.json` → `floors.launch_refuse_mb` / `floors.pressure_warn_mb`):
  the value at which `coord.py` REFUSES a launch, and the value at which the watch layer FLAGS system
  pressure. A distress warning is NOT an early warning for launches. **Equal values are a coincidence
  of value, never of meaning** — neither is derived from the other, and neither may be moved to match
  the other.
- A memory-gate refusal is CORRECT: re-sequence, never `--force-memory`. **`--force` does not lift the
  memory gate and never will be re-attached to it** — it carries identity mismatch, the role gate, and
  validation.
- **LANDED IS NOT LIVE.** A number written to `budget.json` does not reach a running consumer until an
  actuation carries it. Take the EFFECTIVE value from the RUNNING system when it matters; whoever
  performs the act that invalidates a written claim owes the walk-back in the same act.
- When two records disagree on a policy value, adopt the SAFE reading immediately — the one that
  cannot overshoot what the owner authorized under either reading — and put the conflict to the
  authority. Never average, never pick a winner, never quietly "harmonise".
- **Model policy.** **EVERY planning and staffing seat binds `claude-opus-5` at effort `max` — no
  exceptions** (owner, 2026-08-06). This binds the whole planning workflow — `elicitator`,
  `planning-strategist`, `execution-strategist`, `execution-tactical-designer`, `execution-tactical`,
  `workflow-designer`, `seat-designer`, `staffer`, `ledger-groomer` — plus the collapsed-mode
  `planner`. It binds at BINDING time AND sweeps every already-bound seat; a seat ALREADY LIVE on
  another model keeps running, and the binding applies at its next launch. Other ranked design and
  judgment routes to **opus/high**; **opus writes code, at medium effort**; **verification runs on
  swarms of cheap, good headless executors.**
- The cap's basis is MEMORY and flag coverage. **No gate watches CPU**, so contention is bounded by no
  gate. If the box feels slow while RAM reads healthy, suspect CPU FIRST and say so unprompted.
- **Executor bindings are verified on THIS box before rostering** — logins and credits checked, never
  assumed (R-audit-premises applied to staffing).

## 9 · Verify, fail loud, write through (PRIN-5)

- **Premises first:** your briefing's first executable step is verifying its factual claims against
  the live system (protocol R-audit-premises). A brief's claim is an INSTRUCTION, and a wrong one is
  executed.
- Every done is verified at the edge against pre-declared criteria before anything flows on. "Done"
  with an unrun or failing check is FALSE. **A green that could not have gone red is not evidence** —
  prefer controls that fail by construction when the claim is false.
- **Re-reading confirms intent; only EXECUTION discriminates.** A seat that re-reads its own code and
  reports it correct has produced no evidence. At every close, state what you did NOT prove — and run
  one of those checks before you close.
- **Never hand the artifact the value it exists to compute**, and never probe two halves on opposite
  sides of a boundary and call the seam covered. A count is necessary and NEVER sufficient: any claim
  about content, order, or identity proves that property directly.
- **Fail loud:** a skipped step, failed test, or unmet criterion is stated plainly in your report —
  never hidden behind a success label.
- **Write through:** any analysis or draft you would grieve losing goes to disk the moment it exists
  (protocol R-write-through).
- **Protect the invariant:** when a ruling's literal wording would break a load-bearing invariant,
  protect the invariant and DISCLOSE the divergence plainly — never comply literally-and-silently;
  never use this to redesign a ruling you merely disagree with.
- KISS (PRIN-7) / micro agency (PRIN-4): ship the minimum artifact that meets the done contract. If
  200 lines could be 50, the 200 are a defect — in code, records, and messages. Human-facing output is
  executive-first, plain words, no unexpanded jargon.

## 10 · Dispatching workers (PRIN-1)

A dispatched worker — in-process sub-agent, CLI worker, or API worker — is a context-bound teammate
(PRIN-1): it receives ONLY its dispatch prompt and carries nothing you did not hand it. This run's
obligations therefore **stop at the seat boundary** unless the dispatcher carries them across.
**Carrying them is the DISPATCHER's act, never the worker's to discover.**

In addition to the workspace's own pre-dispatch gate, every dispatch prompt MUST carry:

- **This manual, by workspace-root-absolute path, with an IMPERATIVE read-and-follow directive**
  ("read `<path>` and follow it exactly") — **scoped honestly to what applies to that worker's task.**
  Deterministic-first (§3), verify/fail-loud (§9), and git discipline (§6) bind virtually every
  worker; seat-lifecycle and budget sections do not bind a one-shot. Scoping honestly cuts both ways:
  the whole manual for a three-section task is ceremony; no sections because "it is a small task" is
  exactly the gap this rule closes.
- **The `sd-graph` obligation (§2)** whenever the task touches rbtv system vocabulary or artifacts.
  Terms carry exact settled meanings; a worker cannot infer them and will coin.
- **Workspace-root-absolute paths for every file the worker creates, moves, or reads** — a worker
  resolves a relative path from ITS OWN working directory, which is not yours. VERIFY each claimed
  file exists at its intended path before trusting the return.
- **A HERMETIC ENVIRONMENT, BOUND BEFORE THE WORKER'S FIRST COMMAND:** unset `TMUX` and `TMUX_PANE`,
  and grant no terminal-multiplexer commands and no `coordinate` writes — as a **PRECONDITION in the
  prompt**, never a correction after. **The bar is UNCONDITIONAL, because identity arrives from the
  ENVIRONMENT, not the prompt:** an in-process worker is born holding the dispatcher's own pane as its
  default target, and any tool acting on "the current pane" hits that pane without naming it. A
  dispatcher cannot know in advance what a worker will reach for, so a bar keyed on anticipated
  contact never fires. A worker that genuinely needs a multiplexer **names its target explicitly and
  never inherits one.**

**A dispatch prompt missing ANY of these rows is REWRITTEN BEFORE SENDING** — never
sent-and-corrected, because a worker acts on the prompt it got.
