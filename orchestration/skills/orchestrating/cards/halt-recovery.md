# Card: Halt-Resolution + Recovery

Opened when a worker stops short of a clean `DONE` — it **halted** on a doubt, returned `BLOCKED`, **died** mid-run (crash, transient exit, hang), or its return **drifted** from the disk state. This card answers ONE question: given a worker that did not cleanly finish, how does the conductor get the run back to a correct, dispatchable state without wasting work or improvising decisions. It owns the Halt→Decide→Resume loop, the recovery ladder, the doubt-escalation chain, red-set bookkeeping at resume, the precondition-override protocol, and USER-EXECUTED-ONLY handovers.

Iron rules it serves (from the core protocol): **halts are the loop, never a blind retry** (a halt is the entry point of a productive Decide→Resume cycle, not a failure to retry away), **disk = truth** (recovery decisions are made against verified repo state, never against the return message), and **the conductor never executes the work itself** (recovery routes a worker or rules and resumes — it does not become the executor, except for the mechanical commit/verify steps the ladder names explicitly).

**This card consumes a return that has already been reconciled.** The verification card runs the return gate and the tripwire reconciliation FIRST; this card is opened by the situation the gate detects (a non-`DONE` status, a tripwire mismatch, or a dead worker). It does not re-run reconciliation — it acts on the gate's outcome. The State card owns the file semantics of `run-log.md` / `state-capsule.md` / `decisions.md`; this card writes to them per those semantics and never restates them.

---

## When this card is open — the four situations

| Situation | Trigger | Entry path |
|-----------|---------|------------|
| **Halt / doubt** | Worker returned `DOUBT_ESCALATED` or `NEEDS_CONTEXT`, or hit a judgment point a non-max conductor must escalate (D9) | Doubt-escalation chain (§4) → Halt→Decide→Resume (§2) |
| **Blocked** | Worker returned `BLOCKED` — an external obstacle or a failed validation it could not resolve | Recovery ladder (§3) from the rung that fits the failure |
| **Death** | Worker did not return cleanly: transient non-zero exit (e.g. exit 75), hang (never exits), or crash mid-task | Recovery ladder (§3) — L2 disk-state recovery is the death path |
| **Drift** | Reconciliation (verification card) found the return message disagrees with disk — claimed work that is not there, or landed work the message understates | Recovery ladder (§3); a drift toward *more done than claimed* often resolves at L2 (disk is correct, the commit/return is what was missed) |

Every worker failure mode in the corpus maps to exactly one entry path: halt → §4; doubt → §4; blocked → §3; death (exit-75 / hang / crash) → §3 L2; drift / faked-or-garbled return → §3 (L2 when disk is correct, otherwise the failure handling its tripwire dictates). No failure mode is left without a path.

---

## 1. The D9 floor — who may rule, who must escalate

Everything in this card forks on conductor reasoning tier (D9). Resolve this BEFORE acting on any halt, because it decides whether a step is a conductor ruling or a halt-to-user.

| Conductor tier | Authority on this card |
|----------------|------------------------|
| **Max-reasoning (intended conductor)** | MAY rule on doubts, issue ADX errata, run bounded design probes, grant single-resume allowlist extensions, and execute the L1/L2 recovery rungs unilaterally — every move in §2 and §3 is available. |
| **Downgraded (a weaker model is orchestrating)** | MUST treat **every judgment point as a halt-and-ask**. Mechanical dispatch/track work is still allowed, but the following are NOT self-authorized and become a halt to the user: any **doubt ruling** (§2 Decide), any **ADX erratum** authored, any **design-probe** verdict applied, any **allowlist-extension grant** (§2), any **L2 disk-state recovery commit** (§3), and any **precondition override acceptance** (§6). The recovery ladder still applies, but L2/L3 collapse to "surface to the user with the verified disk state and the recommended action." |

The rule a non-max conductor MUST escalate, stated once: **halt rulings, recovery commits, ambiguity resolutions, and allowlist/precondition grants are judgment — escalate them.** This is the same carve-out the exit-75 and HDR pilots applied (the disk-state verification and the doubt ruling are judgment work); it is unified here so the card is unambiguous about which moves a downgraded conductor may not make alone.

**Design probe — gather is allowed, rule is not.** A downgraded conductor MAY dispatch a bounded READ-ONLY design probe (§2) to gather evidence for the user to rule on — dispatching a single read-only probe is mechanical, not a ruling. What it MUST NOT do is APPLY the probe's verdict itself: it surfaces the probe's finding + a recommendation to the user, who rules. (It gathers; it does not rule.)

---

## 2. Halt→Decide→Resume — the working core loop

A `doubt_policy: halt` stop is the NORMAL path for a high-reasoning conductor, not an error. Five-for-five correct halts with zero wasted retries is the strongest operational evidence this design has produced (hypresent Session 3). The loop is three moves: **Halt** (the worker stops with a precise blocker), **Decide** (the conductor rules, optionally after a probe), **Resume** (the same worker session continues with the ruling carried in the artifact it consumes).

### Halt — the worker stops with a precise blocker

The worker has already returned `DOUBT_ESCALATED` / `NEEDS_CONTEXT` with the precise blocker in its `open_questions` field (the dispatch-wrapper binds it to halt rather than guess). The conductor does NOT retry the worker to "see if it resolves itself" — a halt with a stated blocker is information, and blind re-dispatch burns the run (a 25-minute CLI run re-run for nothing is the exact anti-pattern the death path documents). Read the blocker; proceed to Decide.

### Decide — rule, or escalate

| Move | When | Discipline |
|------|------|------------|
| **Conductor ruling** | Max-reasoning conductor; the doubt is answerable from the decisions, the spec, the codebase, or a bounded probe | Resolve it, then record the ruling as an **ADX erratum** (below). A non-max conductor does NOT rule — it halts to the user (§1). |
| **Bounded design probe** | The doubt turns on third-party / internal behavior the conductor cannot answer from the artifacts (library API semantics, an internal contract) | Dispatch a SINGLE reasoning agent, ONE question, evidence cited at file:line, ≤1 agent. The probe answers the question and nothing else; its verdict feeds the ruling. (Probe-backed ADX-4 in the pilot is the canonical example.) A probe is an orchestrator-initiated dispatch, NOT a plan task — do not force it into the task taxonomy. |
| **Halt to the user** | The doubt is a genuine executive decision (irreversibility, scope, taste, a tradeoff only the owner can weigh), OR the conductor is downgraded (D9) | Surface the blocker + options with a recommendation; resume only on the user's answer. In `halt` and `end-to-end` run modes a worker doubt halts to the user; in `autonomous` mode the conductor decides unilaterally and logs the decision as a labeled, confidence-rated `run-log.md` row. |

**ADX erratum — the ruling lives in the consumed artifact, append-only.** A ruling that affects the halted task (or any queued task) is written as an **append-only erratum** into the artifact the worker consumes — the task file's amendments section (a trailing `## Amendments` heading appended to the task file, where the task-file contract collects post-authoring errata), or the run's `decisions.md` for cross-task rulings — numbered (`ADX-1`, `ADX-2`, …) so a resumed worker cites "per ADX-N" without re-reading conversation history. This is propagation discipline (the State card owns the mechanics): the ruling is placed IN the artifact, never left in chat, because that is what makes the resume self-contained. The erratum is append-only — NEVER edit a prior amendment or rewrite the task body; append the correction and log a `run-log.md` row pointing to it.

**Single-resume allowlist grant.** When the ruling requires the worker to touch a file outside its declared allowlist (a fix the doubt surfaced needs an adjacent edit), the conductor may grant an **explicit, logged, single-resume** allowlist extension: name the exact added path(s), record the grant in `run-log.md` (what was added, why, which resume it is scoped to), and state in the resume addendum that the extension applies to THIS resume only. The grant does not widen the task's standing allowlist — the next dispatch of that task uses the original. A non-max conductor does NOT grant — it halts (§1).

### Resume — continue the same session with the ruling carried

Resume carries the ruling forward with an **"Additional Context Provided by Orchestrator" addendum** that: (a) cites the erratum (`per ADX-N`), (b) re-pins the return contract by NAMING the five fields verbatim — `status` · `landed` · `validation` · `concerns` · `open_questions` (resumed long-context sessions drift to prose, so the re-pin is mandatory and must be concrete at the moment of drift; the dispatch-wrapper §3 owns the full schema), and (c) names any single-resume allowlist grant in force.

**Transport split — how "resume" is carried differs by worker type** (mirroring the dispatch-wrapper's two-carrier model):

| Worker type | How to resume |
|-------------|---------------|
| **CLI worker** (`kimi`, `codex exec`, `claude -p`) | Resume the SAME session via the model's resume flag (`-r` / session id where supported). The addendum rides the worker's normal prompt transport — no new invocation machinery. |
| **Agent-tool sub-agent** | There is NO session to resume (each Agent-tool dispatch is fresh and stateless). Re-dispatch a FRESH Agent-tool worker carrying the SAME (now amended) task file + the addendum as a new dispatch. "Resume" for an Agent-tool worker IS a fresh re-dispatch — do not look for a session id that does not exist. |

Before resuming, run the red-set check (§5). After the resume returns, it goes back through the verification card's gate like any return — a resume is not trusted on its message.

---

## 3. The recovery ladder — L1 → L2 → L3

A worker failure (blocked, death, drift) is recovered by climbing the ladder from the lowest rung that fits — never jump to a halt when a deterministic retry is correct, never blind-retry when the disk is already correct.

| Rung | Name | When it applies | Action |
|------|------|-----------------|--------|
| **L1** | Deterministic retry | The failure is transient AND nothing was produced (worker crashed before writing, a transient error with a clean work-dir, a flaky-tool failure with no partial state) | Re-dispatch the SAME prompt file once. Deterministic, no judgment. If L1 fails again the same way, climb — do NOT loop L1. |
| **L2** | Bounded agentic recovery | **A CLI worker** DIED after producing work, OR drift shows disk is more-done than the message claims — disk state may already be correct. (L2 is a CLI-process phenomenon — write-then-die / exit-75. An Agent-tool worker has no separate process and makes no commit; a malformed Agent-tool return has no disk-state to recover and routes to L3 / `BLOCKED` instead.) | Run the **disk-state recovery protocol** (below). Max-reasoning conductor only; a downgraded conductor surfaces the verified state to the user instead (§1). |
| **L3** | Halt→Decide→Resume | The failure is a doubt, an ambiguity, an under-specified task (`NEEDS_CONTEXT`), or anything L1/L2 cannot mechanically resolve | Enter the §2 loop: Decide (rule / probe / halt-to-user) → Resume. A failure that arrives at L3 is already past the cheap context-recovery moves, so `NEEDS_CONTEXT` here goes STRAIGHT to Decide (supply the context / amend the task), not back through the §4 chain's earlier rungs. This is where genuine blockers and judgment land. |

### L2 — disk-state recovery (the death / drift path)

The death pattern: a CLI worker's tool-loop completes and writes the work product to disk, but the LLM connection drops on the FINAL return turn — the worker exits non-zero (typically **exit 75 = EX_TEMPFAIL**) with no structured return, and the local-only commit it normally makes after printing the return never ran. **The disk state is correct; the commit and the return are what was lost.** Blind retry re-runs 25+ minutes of LLM work and risks the same transient failure — the corrective path is verify + commit, not re-dispatch.

**Trigger — fires only when ALL hold** (any false → fall back to standard `BLOCKED` + surface):

1. The worker exited non-zero and the five SCHEMA FIELDS are absent or unparseable on stdout (no `status` / `landed` / `validation` returned in parseable form). Evidence files alone on disk do NOT satisfy this condition — the discriminator is the missing structured RETURN, not missing work product (work product present + no structured return is exactly the death signature; work product present + structured return is a clean `DONE` to reconcile, not a death).
2. `git -C <work-target> status` (the work-target's git — the task's `allowed_workdir`, never the worker's launch root) shows uncommitted changes inside the task's allowlist.
3. `git -C <work-target> log -1` does NOT show the expected `[<task-id>]` prefix — the worker did not commit before exiting.

**Protocol** (max-reasoning conductor; judgment work — a downgraded conductor halts to the user with the verified state):

1. **Verify on-disk state against the task's Implementation Requirements.** Read each file the worker was to produce; confirm structure, exports, signatures, expected shape. Note any apparent gap (incomplete file, missing function).
2. **Run the task's declared `test_command` / smoke checks** — the same validation a clean `DONE` return would trigger. Passing validation = the work is functionally complete despite the transient exit.
3. **Verify allowlist compliance** — `git -C <work-target> diff --name-only HEAD` (in the WORK-TARGET's git, never the launch-root's); every changed path MUST be in the task's allowlist. ANY out-of-allowlist edit → HALT + surface (recovery does NOT auto-bless out-of-allowlist edits, regardless of the transient signal).
4. **Verify forbidden-ops compliance** — no frozen-doc touches, no locked-file edits, no push, no destructive reset — the same checks a normal return gets.
5. **Commit manually with the recovery marker.** The recovery commit is a NAMED mechanical orchestrator action — one of the explicit Invariant-1 exceptions (core-protocol Invariant 1: the conductor does not write the deliverable, but recovery commits are a named hands-on action). The conductor creates it via the commit-pinned `rbtv-commit` path; the subject line MUST carry the **`(orchestrator-recovered)`** suffix:
   `[<task-id>] <description> (orchestrator-recovered)`
   The suffix is mandatory: it marks the commit as orchestrator-authored rather than worker-end-to-end and tells every later reader (owner at review, reviewers, audits, `git log --grep="(orchestrator-recovered)"`) to apply EXTRA scrutiny — the worker never printed its `concerns` / blockers list, so gaps it would have flagged are now the reviewer's responsibility.
6. **Log to `run-log.md`** — exit code observed, files verified + smoke result, the recovery commit hash, the reason for not retrying, and an explicit note that the reviewer must FULLY re-validate (not merely trust the conductor's smoke pass).

**Reviewer mandate after an `(orchestrator-recovered)` commit** (the verification card owns review dispatch; this is the brief addendum it MUST carry): re-validate every Implementation Requirement against the as-shipped code (not just structural review), re-check any behavior/UX contract against as-shipped behavior, and be EXTRA willing to FIX in place — the worker got no chance to print its own concerns.

**The recovery commit is reversible** — it is a normal commit, so `git revert <hash>` restores the pre-recovery state and a fresh dispatch can re-run the task. Preserve this reversibility; do not over-rely on the protocol (its piloted recovery rate was 100%, but the sample is small).

**The hang variant** (worker never exits): the conductor kills the dispatch, then runs the SAME disk-state evaluation (steps 1–4) and decides between recover-commit (work is complete) and re-dispatch a fresh worker (work is partial/absent). Same judgment-tier carve-out applies.

**Rest ≠ death — verify a genuine stall before killing or L2-recovering an async worker.** A background/async worker that fires a notification when it "comes to rest" (between turns, or after backgrounding a long op) is NOT thereby dead or hung. An intermediate progress message — anything other than a final, parseable five-field return — signals it may still be progressing. Before treating such a worker as a death (L2) or killing an apparently-hung one, VERIFY a genuine stall: re-check the work-target's disk state across an INTERVAL (still changing → still working) and/or await the next notification — a single stale snapshot is not evidence of a park (disk = truth, read over TIME, not once). Treat it as death/hang only when disk is quiescent AND no structured return is coming. Stopping a still-progressing worker on a stale snapshot is wasted work; where the harness exposes no resume-message channel and the worker IS genuinely parked, "resume" for an Agent-tool worker is a fresh re-dispatch from the verified disk state (§2 transport split).

**What L2 does NOT cover:** a worker that crashed BEFORE writing files (→ L1 deterministic retry or `BLOCKED`); out-of-allowlist edits found at step 3 (→ halt + surface); anything requiring a decision (→ L3).

---

## 4. The doubt-escalation chain

When a worker (or the conductor itself) is uncertain how to proceed, follow this chain IN ORDER — never guess, never proceed past a doubt. Each rung is tried only if the previous did not resolve it.

| Step | Action | Resolves → |
|------|--------|-----------|
| **1. Re-read the decisions + inlined context** | Re-read the run's `decisions.md` and the task's `[INLINED]` excerpts — the answer is often already there, just not yet applied. | proceed |
| **2. Doc-reader dispatch** | If the doubt is "what does document X say about Y," dispatch a doc-reader sub-agent: a sonnet sub-agent, ONE document, ONE question, answer quoted verbatim from the doc, no speculation. It preserves the caller's context by offloading the read. The doc-reader returns `ANSWERED` / `NOT_FOUND` / `READ_FAILED`. | proceed (on `ANSWERED`) |
| **3. Halt** | If the doubt persists after re-read and doc-reader, STOP. For a worker doubt this is the Halt→Decide→Resume entry (§2); for the conductor's own doubt this is a halt to the user (max conductor: only on a genuine executive decision; downgraded conductor: on any judgment point, per §1). | Decide (§2) / user |

The chain is the same one the dispatch-wrapper binds workers to and the verification card references for review doubts — it lives here as the single definition. Steps 1–2 are context recovery (cheap, no user interruption); step 3 is the halt only after the cheap rungs are exhausted. A doubt that reaches step 3 is a real one — treat it as the productive entry to §2, not a dead end.

---

## 5. Red-sets at resume

A red-set is a set of test files whose failures are PLANNED — a RED task wrote failing tests and its GREEN pair has not yet landed. Under any parallelism these planned failures sit in the shared work-dir and would falsely trip every other task's "full suite must be zero-fail" gate. The registry makes the exclusion mechanical, auditable, and self-expiring. The registry LIVES in `state-capsule.md` (the State card owns its storage); this card owns the three operations recovery touches.

| Operation | Rule |
|-----------|------|
| **Register** | When a RED task's return is CERTIFIED by verification (never on the raw return message — a red set registered from an unverified message can mis-scope every later gate), ADD its planned-failing test files to the active-red-sets list in `state-capsule.md`. The set names exactly the files whose failures are expected. Register via the capsule's atomic-overwrite protocol (write `.tmp`, verify, replace — State card §3); the list is a capsule section, not an in-place targeted edit. |
| **Check before resume** | Before resuming or re-dispatching ANY task whose gate runs the suite, read the active-red-sets list and scope the gate to "full suite EXCLUDING active red sets per the registry." A failure that is IN the registry is planned — it does NOT halt. A failure NOT in the registry still halts everything (the registry never excuses a non-test-file failure or an unregistered red). |
| **Retire on resolution** | When the GREEN pair commits and its tests pass (certified), REMOVE that red-set from the registry in the SAME orchestration beat, via the same atomic-overwrite protocol. Exclusions are self-expiring — a green that does not retire its red leaves a stale exclusion that could mask a real future failure. |

This keeps planned reds from producing false halts (which would otherwise cost a resume round-trip each) and stops the conductor from hand-crafting per-dispatch `--ignore` exclusions that only session memory holds together. Never weaken the discipline: an unregistered failure is a real failure.

---

## 6. Precondition-override protocol

A plan may carry a hard **PRECONDITION** (uppercase, exact — e.g. "MUST NOT be dispatched until phase-1b is closed"). It encodes planning-time risk: dispatching before the condition is met is unsafe. Unlike a HARD halt (an irreversibility gate, NEVER overridable), a PRECONDITION is typically about content-staleness or context-completeness and CAN be safely overridden **if its protective scope is verified empty.** This protocol is how.

When loading the plan, scan its constraints for any `PRECONDITION`. For each, verify the stated condition (e.g. check the depended-on phase folder for `checkpoint: completed`). If the condition is NOT met, HALT and present:

| Option | Meaning |
|--------|---------|
| **A) Wait** | Defer dispatch until the condition is met. Strictly safe. |
| **B) Override** | Proceed despite the unmet condition. The user MUST give a one-sentence justification, captured **verbatim** in `run-log.md`. |
| **C) Cancel** | Abandon the run. |

**If the user picks B, the conductor MUST run protective-scope verification BEFORE accepting** (this is the load-bearing, mechanical operation — it is what distinguishes a safe override from an unsafe one):

1. Identify the files/folders the precondition was protecting (derive from the plan's "what this reads/writes" surface).
2. Cross-check the remaining work in the un-closed dependency: read its remaining task files, extract their write-target paths, and intersect against THIS plan's read-target paths.
3. **Intersection empty → override is safe**, proceed; record a labeled `[PRECONDITION-OVERRIDE]` row in `run-log.md` capturing: confidence (`medium` when protective-scope-verified; `low` if accepted on user-rationale the conductor cannot independently verify), the PRECONDITION text verbatim, the user justification verbatim, the protective-scope verification result, the realistic alternative (Option A), the risk accepted, and the reversibility path (typically per-output `last-verified-against` drift markers enabling selective re-run). **If either path set is NOT mechanically extractable** (a plan-less dependency with no task files to read, or tasks whose allowlists/read-targets are not machine-readable), the override CANNOT be verified safe → treat it as intersection-NON-empty (fail safe): HARD halt and surface to the user. Never proceed on an unverifiable intersection.
4. **Intersection non-empty → HALT and surface the conflict** — the user CANNOT override a PRECONDITION whose protective scope is actively violated. A PRECONDITION whose scope is violated IS a HARD halt at the moment of violation; **`autonomous` mode does NOT bypass this check** (parallel to "plan-marked HARD halts are NEVER overridden"). A downgraded conductor (§1) does not accept the override itself — it surfaces the verification result and the recommendation to the user.

---

## 7. USER-EXECUTED-ONLY handover

Some steps only the user can perform — actions the conductor and its workers have no authority or ability to execute (a credentialed external action, a manual approval in a third-party system, a physical or account-bound step). A task marked USER-EXECUTED-ONLY is NOT a doubt and NOT a failure — it is a planned handover.

| Run mode | Behavior at a USER-EXECUTED-ONLY step |
|----------|----------------------------------------|
| **Halt** | HALT and hand over: surface exactly what the user must do, then wait. Resume only after the user confirms it is done. |
| **End-to-end** | HALT and hand over (same as halt mode — end-to-end skips checkpoints, NOT user-only steps). |
| **Autonomous** | Skip and log: record in `run-log.md` that the user-only step was reached and which defaults were accepted in its place; never fabricate having performed it. |

Hand the step over with the precise action stated (what, where, why), do NOT attempt a workaround that simulates the user-only action, and record the handover in `run-log.md`. When the user confirms completion, verify any resulting state on disk (disk = truth) before resuming dependent work.

---

## Hand off — back to the loop

Recovery's output is a run restored to a correct, dispatchable state: a doubt ruled and the worker resumed, a transient death recovered and committed, a blocked task re-routed, or a halt surfaced to the user with the decision it needs. From here the run returns to its normal flow — the next dispatch goes through routing and the dispatch-wrapper; the resumed or recovered return goes through the verification card's gate like any other. Do not mark a recovered task `DONE` on this card: a recovery commit and a resumed return are still subject to the verification gate (and, for development dispatches, the cold verifier). Follow the situation table in the core protocol; this card's responsibility ends when the run is back to a state the loop can carry forward.
