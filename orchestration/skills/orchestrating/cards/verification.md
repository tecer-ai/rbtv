# Card: Verification

Opened at EVERY worker return and at EVERY quality gate. A dispatch has come back, or a feature/phase boundary has been reached — and nothing the worker claims is trusted until this card has run. Verification is the conductor-SIDE gate: it RUNS the return-verification check the dispatch-wrapper made parseable, RUNS the review gates routing pinned, RUNS the cold verifier for development dispatches, drives the debug roles, and personally exercises the exit probes before the run is declared done. Its output is a return either CERTIFIED (proceed) or routed to recovery (the halt-recovery card owns what happens to a return that does not pass).

Iron rules it serves (from the core protocol): **disk = truth — every return is reconciled against repo state, the message is only a hint** (this card is where that reconciliation is performed); **evidence must be plausible** (the tripwire field-checks below are how plausibility is mechanically tested, not eyeballed); and **the conductor never trusts a self-grade** (review gates and the cold verifier exist because a builder grading its own work is structurally unsound — self-preference bias is strongest exactly where "done" gets declared).

**This card RUNS the gate; sibling cards supply its inputs and consume its outputs.** The dispatch-wrapper packaged the return into the named-field schema and DEFINED the tripwire field checks (its §4) — this card EXECUTES them and acts on them. Routing PINNED the reviewer / cold-verifier / debug-role floors — this card FIRES them on schedule. The halt-recovery card is opened by what this card detects: a non-`DONE` status, a tripwire mismatch, or a dead worker. The State card owns `run-log.md` / `state-capsule.md` semantics; this card writes verdicts and gate events to them per those semantics and never restates them. The installed `rbtv-done-gate` rule is the single source of truth for the fidelity floor and the cold-verifier contract — this card composes with it, never re-derives or contradicts it.

---

## When this card is open — every return, every gate

| Situation | What this card runs |
|-----------|---------------------|
| **Any worker return** (`DONE` included) | The return-verification gate (§1): tripwire field checks → repo-state reconciliation. ALWAYS, no return exempt. |
| **A development dispatch returned** | The return gate (§1) AND a review gate (§2). At a FEATURE commit boundary, ALSO the cold verifier (§3). |
| **An API text-worker returned** | The return gate (§1, deliverable-scoped per §1c) AND the review gate's content-review variant (§2). NOT the cold verifier (§3) — no executable behavior. |
| **A micro-dispatch inside a feature** | The return gate (§1) + the review gate (§2). The cold verifier fires at the feature boundary, not per micro-dispatch. |
| **An interaction / behavior bug surfaced** | A debug role (§4) — never a CLI worker root-causing. |
| **The run is about to be declared done** | The orchestrator-executed exit probes (§5) — the conductor personally exercises N probes before declaring the run complete. |
| **The run is being closed** (exit probes held) | Run finalization (§6) — complete the exit scorecard, set the honest status, and surface every Human Review block + low-confidence/red-flag decision before reporting completion. |

A return that does not clear §1 (and, for development work, §2–§3) is NOT done — it is routed to the halt-recovery card with the gate's finding. This card never marks a task done on the strength of a return message; "done" is purchased only by evidence that clears these gates.

**"Development work" defined.** A development dispatch is one whose deliverable is CODE or executable behavior — the work classes the routing card sends down the code path (a bounded code slice, a feature build, a bug fix, an sdd dispatch). It is the trigger for the code-diff review gate (§2) AND the cold verifier (§3). A non-development dispatch (a doc, a vault-content edit, a research brief, a plan artifact) clears at §1 alone — §2–§3 do not fire. **An API text-worker's output is the one non-development case that still takes a review** — §2's content-review variant (a reviewer reads the files; the cold verifier §3 still does not fire). When in doubt, the routing card's work categories decide; this card does not re-derive them.

**API text-worker returns are non-development.** An API text worker (the runner-driven chat workers — DeepSeek, Gemini) emits TEXT/files, never code or executable behavior, so its return is classified non-development: it clears at the §1 return-verification gate PLUS a content review (a reviewer Claude reads the output for quality, §2 reading content instead of diffing code) — NOT through git reconciliation, NOT a test suite. The cold verifier (§3) does NOT fire for a non-development text output — there is no owner-observable executable behavior to re-exercise at the fidelity floor. The agentic worker (Manus) is a different transport (task-create → poll → raw-dump): it composes with this same non-development classification (raw-dump reviewed for content, no code cold-verifier), and its latency / per-task-cost gate specifics — a minutes-scale `WALL_MS` is PLAUSIBLE, and it is billed per task not per token — live in §1b's `Implausible WALL_MS` tripwire and its budget note.

---

## 1. The return-verification gate (D8 — disk = truth)

Runs on EVERY return before its `status` is trusted or logged. The dispatch-wrapper bound the worker to the named-field schema and made the checks below mechanical; this card executes them in order. Run the field checks FIRST (cheap, mechanical), then the repo-state reconciliation (authoritative).

### 1a. Parse the named fields

The return carries the five fields the dispatch-wrapper schema fixed (`status` · `landed` · `validation` · `concerns` · `open_questions`). A return that is prose-only — fields renamed, missing, or dissolved into narrative — is itself a contract violation (resumed long-context sessions drift to prose; a garbled or summary return is the SYMPTOM, not an acceptable form). Do not parse meaning out of prose: a non-conforming return is treated as a drift instance, logged, and the return is re-exercised (resume + re-pin the schema, per halt-recovery), never hand-interpreted into a pass.

### 1b. Run the tripwire field checks mechanically

These are field-level checks against the parsed schema — the field-mechanics live on the dispatch-wrapper (its §4); this card RUNS them and decides the consequence. Run ALL of them on every return; any one firing blocks `DONE`.

| Tripwire | Mechanical check the conductor runs | Fires → |
|----------|-------------------------------------|---------|
| **Phantom commit** | For each commit hash in `landed`: `git -C <workdir> log` MUST contain that hash. | Hash absent → the commit was never made → treat as not-done; route to recovery (drift / death path). |
| **Implausible WALL_MS** | For each `validation` entry: its `WALL_MS` must be plausible for the work claimed (a full suite reporting near-zero ms did not run; a build claimed in milliseconds did not build). Apply the concrete per-work-class bars in `{rbtv_path}/orchestration/workflows/_shared/authoring/spec-template.md` § Evidence Plausibility (e.g., a browser e2e under ~1s, an OS-dialog test under ~1.5s, are auto-reject) — those bars live in one place (the spec-template) and are applied here at run time. A duration physically impossible for the work class → the check did not really run. **The plausibility bar is calibrated PER WORK CLASS** (this calibrates the spec-template bars for the class, it does not contradict them): a chat call is sub-second-to-seconds, but an **agentic worker (Manus: task-create → poll → raw-dump)** runs a real autonomous task that takes minutes — so a LARGE `WALL_MS` of **seconds-to-minutes is PLAUSIBLE / expected** for a Manus return. Do NOT treat a minutes-scale Manus `WALL_MS` as a "did-not-run" or a hang (the small-WALL_MS auto-reject above is the only direction that fires for the agentic class). | Implausible → re-exercise that validation before accepting it. |
| **EXIT codes** | Every `validation` entry's `EXIT` must be present and `0` (or an explicitly-explained non-zero the task sanctions). A missing or non-zero unexplained EXIT = a failed gate. | Non-zero / missing → the gate did not pass → do not accept `DONE`. |
| **SKIPPED_COUNT** | Any skipped check MUST carry a reason; `SKIPPED_COUNT > 0` without a stated reason per skip = a silent skip. | Unexplained skip → the suite did not really pass → block `DONE`. |
| **Commit-message validation** | A committed task's commit message MUST carry the run's mandated convention string (e.g. the `[<task-id>]` prefix). Check the MESSAGE, not just the file list — `git -C <workdir> log -1 --format=%s`. | Convention dropped → flag it (grep-ability is load-bearing for audits), even when the file list is correct. |

The checks are mechanical precisely because the schema is named-field — that is the whole reason D8 mandated named fields over prose. A check that cannot be run mechanically (because the field was not returned in parseable form) is itself a §1a violation.

**Agentic-worker cost note (budget surface).** Manus is billed **PER TASK, not per token** — a Manus dispatch costs a whole task fee regardless of token volume. This is the budget surface for the agentic class: the conductor weighs whether the autonomy / browser-driving a Manus task buys is worth a full task fee BEFORE dispatch, rather than tracking a per-token spend as it would for a chat worker.

### 1c. Repo-state reconciliation — the message is a hint, the disk is the truth

After the field checks, reconcile the CLAIM against the actual disk state — this is the authoritative step, run on every return including `DONE`, and especially on resumes:

1. Read the actual disk state: `git -C <workdir> status --porcelain` and `git -C <workdir> log --oneline -3` (or deeper as the dispatch warrants), plus the evidence files the `validation` field cites. Resolve `<workdir>` from the dispatch's `landed` paths or the run-log dispatch row — it is the **work-target's** repo (the task's `allowed_workdir`), NEVER the worker's launch root: under the G1 launch-root split (dispatch-wrapper §1) a CLI worker launches from the orchestrator root but edits a work-target that may be a nested repo with its own git — a reconciliation run in the launch-root's git passes vacuously. For a worktree-isolated parallel worker (routing §8) it is that worker's worktree path, NOT the conductor's cwd.
2. Reconcile against `landed` / `validation`. The message is a HINT; the disk is the TRUTH.
3. **Message and disk disagree → the disk wins**, and the discrepancy is recorded as a drift instance in `run-log.md` (per State-card semantics). A return whose message contradicts the disk is logged as one — never silently smoothed over.
4. The direction of the mismatch routes the recovery: claimed-but-absent work → recovery's drift/death path (work may need re-dispatch, or the disk may simply be MORE done than the message — a dropped commit/return, recoverable at the disk-state rung); landed-but-understated work → reconcile to the disk reality and proceed once verified.

**Deliverable-scoped reconciliation for an API text worker.** An API text worker writes files into an `--output-folder`, not a git repo — its `<workdir>` carries no commit to `git log`, so the §1b phantom-commit / commit-message tripwires and the `git status` read do not apply; "disk = truth" (invariant 3) still holds, but "disk" here = the **output folder**. Reconcile the runner's output against its `landed` list and the `return.json` it wrote:

1. Reconcile **files-exist + non-empty against the runner's `landed` list** — each path the runner reports it wrote MUST exist under the output folder and be non-empty. NEVER reconcile by "folder non-empty": the conductor points `--output-folder` at the deliverable's FINAL destination, which may ALREADY hold other files, so a non-empty folder proves nothing about THIS dispatch.
2. Field-check the `return.json`: **`envelope_valid == true`** and **`finish_reason == stop`** (a falsy `envelope_valid` means the raw-dump fallback fired → `DONE_WITH_NOTES` + a concern; a `finish_reason` ≠ `stop` means truncation → flagged in `validation`, not a silent half file).
3. A `landed` path absent or empty on disk, or a `return.json` that contradicts the output folder → the disk wins; record the discrepancy as a drift instance and route per §1d.

Why this step is non-negotiable: five resumed-Kimi sessions in ONE chain drifted from the return contract while the work had landed correctly on disk (one returned a garbage non-sequitur final message while commit `045fbb3` held the complete, correct work). The orchestrator caught all five only by verifying `git` state after every return. An orchestrator that trusts final messages loses a commit, accepts a phantom gate, and re-runs completed work. Reconciliation is what makes "disk = truth" operational.

**Count / reconciliation claims get re-run, never accepted on report.** Any count, reconciliation, or "X→Y / 0-diffs" tally — whether the worker reported it or the conductor would assert it — MUST be backed by an ACTUAL run of its producing command under the project's canonical invocation (the correct environment, working dir, and any required env vars — e.g. `PYTHONPATH` for a Python pipeline; a throwaway output dir; never a destructive flag on real data), with the number taken from stdout. For non-code work, re-derive the claim from its actual source the same way (re-run the query, re-count the artifact). A produced file may have NO consumer and thus zero runtime effect; "tests pass" does not verify a narrative count. An executor count is a claim, not evidence. If the producing command cannot be run, trace its exact consumer path and say so — never certify an unverified count.

### 1d. Gate outcome

| Outcome | Route |
|---------|-------|
| All field checks clear AND disk reconciles to `landed`/`validation` AND `status` is `DONE` | Return is reconciled — proceed to the review gate (§2) for development work OR for an API text-worker return (its content-review variant, §2); certify directly for other non-development work (a doc, a vault-content edit, a research brief, a plan artifact). |
| `status` is `DONE_WITH_NOTES` | Reconcile as above, then weigh `concerns` / `open_questions`; if they surface no blocker, proceed on the same route as `DONE` — the review gate (§2) for development work or an API text-worker return, certify directly for other non-development work. A note that IS a blocker routes to halt-recovery instead. |
| Any tripwire fired, OR disk disagrees, OR `status` is `BLOCKED` / `DOUBT_ESCALATED` / `NEEDS_CONTEXT`, OR the worker died | Route to the **halt-recovery card** with the gate finding — do NOT mark the task done. This card detects; halt-recovery resolves. |

---

## 2. Review gates — reviewer ≥ executor + 1, with pre-flagged briefs

Every development dispatch that clears §1 goes through a review gate before its work counts as done. An **API text-worker return** (non-development, §1) ALSO goes through this gate — as a **content-review variant**: the reviewer READS the output files for quality (per the contract/spec the text was produced against) instead of diffing code, and the cold verifier (§3) does NOT fire (there is no executable behavior to re-exercise). Every reviewer pin and discipline below (§2a–§2d) applies to both. Routing PINNED the reviewer floor; this card RUNS the review.

### 2a. The reviewer pin (routing owns the floor; this card enforces it)

| Pin | Value |
|-----|-------|
| Reviewer tier | Reviewer pin (tier, floor, never-haiku, external-CLI-Opus): follow `cards/routing.md` §3 Pinned roles. Verification consumes the pin; routing defines it. |
| External-CLI code | **Opus reviews ALL external-CLI-worker code** — a cheaper reviewer misses inverted contracts and over-generalizations that Opus review caught in the pilots. |
| Independence | The reviewer is a SEPARATE dispatch from the executor — never the same session grading its own output. |

If the routing assignment ever presents a reviewer below this floor (a budget downgrade, a mis-route), this card REFUSES the review and surfaces the conflict — the pin wins over cost, always.

### 2b. Pre-flagged review briefs — the conductor names the suspect areas

The reviewer is NOT dispatched blind. The conductor composes a **pre-flagged review brief**: from the §1 reconciliation, the worker's `concerns` / `open_questions`, the task's stakes, and the diff's blast radius, the conductor NAMES the specific areas the reviewer must scrutinize first (the risky module, the contract the change touched, the edge case the worker flagged, the file with the largest diff). The brief focuses the review on where defects are most likely — it does not narrow the review to only those areas, but it guarantees they are not missed.

A review brief MUST carry, in addition to the suspect areas: the contract / spec the work is reviewed against, the reconciled disk state (not the worker's claim), and — when the return arrived via an `(orchestrator-recovered)` commit — the recovery mandate (re-validate every Implementation Requirement against as-shipped code, re-check behavior contracts against as-shipped behavior, be EXTRA willing to fix in place, because the worker never printed its own concerns).

### 2c. The reviewer's job — review AND fix in place

| Step | Reviewer requirement |
|------|----------------------|
| Inspect actual state | Read the files the executor created/modified — the reconciled disk reality, never the worker's narrative. |
| Re-run any count claim | Any reconciliation / count / "X→Y" tally — reported or asserted — is backed by an ACTUAL pipeline run (per §1c); a written file may have no consumer; "tests pass" does not verify a count. |
| Identify defects | Gaps, errors, inconsistencies, deviations from the contract/spec — prioritized by the pre-flagged brief. |
| **Fix in place** | The reviewer does NOT merely report — it edits, restructures, and corrects to bring the work into compliance, then re-verifies its own fixes. |
| Audit the run artifacts | Where the run carries a `decisions.md` / shape and a deliverables index, audit them against their entry-shape rules and flip any stale status — a stale index is a defect. |

### 2d. The review-fix loop with binding fix directions

When the reviewer cannot fix a defect itself (it needs the executor to redo bounded work, or the fix needs the executor's session/context), the conductor issues a **binding fix direction** back to the executor — not a vague "please revisit," but an imperative, specific directive: the exact defect, the exact required outcome, the acceptance that closes it. The fix direction is appended to the task artifact (append-only erratum, per halt-recovery / State-card propagation discipline) so the resumed/re-dispatched executor consumes it from disk, not from chat. The re-dispatched fix return goes back through §1 and §2 like any return — a fix is not trusted on its message. The loop repeats until the review is clean; "close enough" never closes a gate.

---

## 3. The cold verifier (D10) — independent, fidelity-floor, never the builder's evidence

For DEVELOPMENT dispatches, review (§2) is necessary but NOT sufficient: a reviewer reads the builder's code, but only an independent re-exercise at the fidelity floor proves the feature works the way the owner will use it. The cold verifier is that re-exercise. **It composes with the installed `rbtv-done-gate` rule's §Orchestrated Dispatches — same contract, one source of truth for the floor.** This card states WHEN it fires and WHO dispatches it; the done-gate rule states what the floor IS. Do not re-derive the floor here.

### 3a. When the cold verifier fires

| Firing point | Rule |
|--------------|------|
| **Each FEATURE commit boundary** | Feature-serial discipline (D10): a **feature** = the set of task dispatches that together deliver ONE owner-observable behavior — operationally, one spec's worth of work (the spec-template's one-spec-many-tasks unit); its boundary is the commit that completes that spec's Test Plan. At that boundary the cold verifier re-exercises that feature's contract criteria. Micro-dispatches inside the feature stay covered by the review gate (§2); the cold verifier is the feature-grain gate, not the micro-grain one. |
| **One cross-feature EXIT verification** | Once, before the run is declared done, a cross-feature verification re-exercises the criteria that span features (the integration the per-feature checks could not see). This is distinct from the orchestrator exit probes (§5) — the cold verifier exits the FEATURE contracts; the exit probes are the conductor's own final hands-on pass. |

The cold verifier is mandatory for development dispatches from day one of an orchestration — builder-graded sheets are INSUFFICIENT inside an orchestration (the done-gate rule fixes this; this card enforces it). It is NOT a cost-optimization target: routing pins it as an independent, fidelity-floor-capable worker.

### 3b. What the cold verifier receives — and never receives

| Receives | Never receives |
|----------|----------------|
| ONLY the done-contract criteria (the owner-observable outcomes) | The builder's tests |
| The running artifact (the real application, the owner's real data) | The builder's claims, return message, or `landed` field |
| The fidelity floor it must exercise at (per the done-gate rule) | The builder's evidence sheet |

The isolation is the point: a verifier handed the builder's tests or sheet inherits the builder's blind spots and self-preference bias — it would re-confirm the proxy, not the outcome. It re-exercises from the contract alone.

### 3c. What the cold verifier does and returns

The cold verifier re-exercises EACH contract criterion at the fidelity floor defined by the installed `rbtv-done-gate` rule (its §Fidelity Floor — the single source; do NOT re-derive it here), capturing evidence as FILES on disk during the exercise and recording a genuine blocker as `unexercisable` + the concrete blocker, never silently skipped. It returns its OWN evidence sheet (criterion · gesture performed · observed result · evidence-file path · verdict `held`/`failed`/`unexercisable`), at the path the done-gate rule's §Required Output formula fixes — built from its own exercise, citing its own captures.

### 3d. The mismatch rule — builder/verifier disagreement FAILS the dispatch

**Builder's sheet says held, cold verifier's sheet says `failed` → the dispatch FAILS return-verification.** The dispatch is not done; route it to halt-recovery (the builder's contract was not met, or its evidence was theater). A `failed` mismatch is never resolved in the builder's favor — the cold verifier exercised the criterion from the contract at the floor; the builder graded its own work.

A cold-verifier `unexercisable` row is NOT an automatic FAIL — it follows the installed `rbtv-done-gate` rule's §Exhibit: done is declarable with the `unexercisable` row(s) surfaced explicitly in the done message, and the OWNER decides acceptance. Surface every `unexercisable` row (with its concrete blocker) to the owner; do not silently pass it and do not auto-fail on it. (This is the one-source-of-truth alignment: `failed` → FAILS; `unexercisable` → owner decides.)

The done-gate rule's Integrity Tripwire also applies: a builder sheet caught dishonest (a claimed gesture not performed, a fabricated result, a recycled capture) permanently escalates the workspace to independent verification of every contract thereafter.

---

## 4. Debug roles (D21) — top-tier, never a CLI worker root-causing

When a defect is an interaction / behavior bug (the §1 reconciliation, a review, or a cold-verifier `failed` row surfaced it), root-causing it is judgment-dense work that routing pins to a TOP-TIER (opus) debug role — never a CLI worker. This card drives the role.

| Role | When | Discipline |
|------|------|------------|
| **DEBUG-AGENT** | A behavior/interaction bug needs root-cause + a fix spec | A top-tier reasoning agent root-causes against the reconciled disk state and the failing exercise, then produces a precise fix spec (the cause, the exact change, the acceptance). Live-validated fix specs landed first-try across 6+ dispatches — the value is in the diagnosis, so do not shortcut it to a cheaper worker. |
| **Live-debug-with-owner** | The bug reproduces only under the owner's real conditions, or the owner's eyes are needed to confirm the symptom | The conductor drives a live debugging pass WITH the owner — reproduce under real input, narrow together, confirm the fix under the owner's hand. |

**Pre-commitment slate (D21).** Before debugging starts, write down the candidate hypotheses and what each predicts — the slate is committed BEFORE evidence is gathered, so the debug pass tests hypotheses rather than rationalizing the first plausible cause. Record the slate where the run can audit it (run-log, per State-card semantics); the diagnosis names which slate hypothesis the evidence confirmed. This is the discipline that keeps root-causing honest — fix the cause the evidence proves, not the first guess that fits.

A debug role's fix spec re-enters the loop as a binding fix direction (§2d) or a fresh bounded dispatch; its return goes through §1–§3 like any other. Debugging never bypasses the gates.

---

## 5. Orchestrator-executed exit probes — the conductor's own hands-on pass

Before the run is declared done, the conductor PERSONALLY exercises N exit probes — not a dispatched worker, the conductor itself. N is **at least one probe per contracted owner-observable feature plus one cross-feature integration probe, minimum 2** (a single-feature run still gets the feature probe + one integration pass). This is the last gate, and it is deliberately hands-on: every other gate dispatched the verification; this one the conductor performs, because the run's "done" claim is the conductor's own and must be backed by the conductor's own evidence.

| Rule | Detail |
|------|--------|
| The conductor exercises, not a worker | The conductor itself drives N probes against the running, whole, as-shipped system — the integration the per-feature cold verifier and the per-task gates could not each see end-to-end. |
| Probes are owner-fidelity | Each probe is a real gesture against the real artifact with the owner's real data at the fidelity floor — the same floor the cold verifier uses (per the done-gate rule). A headless or mock probe is theater. |
| Capture evidence as files | Each probe captures its evidence (output file, screenshot, log) on disk — the exit-probe evidence is part of the run's record, cited in the close, never a prose claim. |
| A failed probe blocks done | Any probe that does not hold routes back to the loop (debug role / binding fix direction); the run is NOT declared done with a failing exit probe. Surface it; never bury it under a success label. |
| Distinct from the cold-verifier EXIT | The cold verifier's cross-feature EXIT (§3a) verifies the FEATURE contracts independently; the exit probes are the CONDUCTOR's own final confirmation that the whole run delivers. Both run before done; neither substitutes for the other. |

This is the operational form of "done is false if anything was skipped": the conductor does not certify the run on the accumulated green of dispatched gates alone — it puts its own hands on the result first.

---

## 6. Run finalization — close the run and surface review-driving content

Once the exit probes (§5) hold and the run is certifiable as done, the run is CLOSED with a finalization pass before the conductor reports completion. This is the run-end counterpart to the per-return gate: §1–§5 certify each return and the run's outcome; this step produces the run's close.

| Rule | Detail |
|------|--------|
| **Complete the exit scorecard** | Fill the `run-log.md` Exit Scorecard (the State card owns its shape): per-feature and cross-feature verification verdicts, the exit-probe verdicts with their capture paths, and the **honest exit reason** (`complete` / `blocked` / `stalled` / `degrading` / `timeout`). The scorecard is the run's durable accountability record — the close report is derived FROM it, never instead of it. |
| **Status is honest** | The run closes as **COMPLETE** only when every contracted criterion is certified and no irreversible step remains; if a USER-EXECUTED-ONLY step or an owner-decision is still outstanding, the close is **COMPLETE PENDING USER ACTION** with the remaining action named. Never label a run COMPLETE when a final step the owner must take is unfinished. |
| **Surface every Human Review block** | A run that executed any `human_review: required` task or any checkpoint carries the Human Review Presentation blocks those tasks produced. At close, surface EACH block VERBATIM, grouped by phase — never collapsed, summarized, or paraphrased. In `end-to-end` and `autonomous` modes this close is the user's FIRST sight of that per-task review content (the modes skipped the per-phase halts where `halt` mode would have shown it — intake §7); its verbatim fidelity is the point. Block format and flag criteria are the frozen planning surfaces (`{rbtv_path}/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation; `{rbtv_path}/orchestration/workflows/_shared/authoring/human-review-criteria.md`) — the conductor surfaces the blocks, it does not re-derive their format. |
| **Surface low-confidence + red-flag decisions** | In `autonomous` mode, list the `medium`- and `low`-confidence unilateral decisions from the `run-log.md` U-register, lowest confidence first (the high-confidence rows stay in the log, not the close). Any Human Review block carrying a 🔴 red flag is ALSO listed here regardless of mode — red-flag tasks belong on the priority surface, not buried in the per-phase blocks. |
| **Name the artifacts and next actions** | The close names the run's artifacts (plan, the run's `decisions.md`, `run-log.md`, and — plan runs — `deliverables.md`) and any next action the owner must take, each self-explanatory (the reader has zero session context). Leave deliberately-uncommitted working-tree state noted, not silently dropped. |

The close is a CONDUCTOR action, not a dispatch — it is the conductor's own accountable report that the run is done (or done-pending-user-action), backed by the scorecard's evidence. A plan-less run with no `human_review` tasks still closes with the scorecard, the honest status, and any run-end findings the run mode surfaces (State card §6); it simply has no HR blocks to carry.

---

## Hand off — certified, or routed to recovery

This card's output is a verdict on a return or a gate:

- **Certified** — the return cleared §1, the review gate (§2) is clean, the cold verifier (§3) held at the feature boundary, and (at run end) the exit probes (§5) held. The run proceeds: the next dispatch goes through routing and the dispatch-wrapper; a certified run-end goes to run finalization (§6) — the exit scorecard, the honest status, and the surfaced Human Review blocks — before the run is reported done.
- **Routed to recovery** — any gate detected a non-`DONE` status, a tripwire mismatch, a builder/verifier disagreement, a dead worker, or a failing probe. Open the **halt-recovery card** with the finding; it owns the Halt→Decide→Resume loop, the recovery ladder, and the resume — and a recovered/resumed return comes BACK through this card's gate before it is ever certified.

Do not mark a task or a run done on this card by narrative — done is the verdict these gates produce, backed by the evidence they cite. Follow the situation table in the core protocol; this card's responsibility is to RUN the gate on every return and every quality boundary, and to route what does not pass.
