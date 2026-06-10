# Learnings - builder-open-deck

> **Purpose:** Actionable items captured during plan execution to be solved or compounded after the plan ends. Each entry is a post-plan TODO with enough context for a fresh agent to act on it without reading the full plan. Includes META-learnings about how RBTV/sb-os could be improved AND code/installer/rule bugs discovered while executing the plan — both classes of finding are actionable post-plan items.

---

## What Belongs Here

`learnings.md` is the catch-all for findings that surface during plan execution but do NOT change plan direction (those go in `decisions.md`) and are NOT a single concrete piece of project work (those go in the project's tasks file). The defining trait: every entry is **actionable** — solvable now or compoundable into a later system change. If there is no action, it is not a learning.

| Include | Exclude |
|---------|---------|
| User corrections to agent behavior | Project-specific decisions |
| Missing rules or unclear instructions | Implementation details |
| Workflow gaps or friction points | Task-specific context |
| Tool limitations discovered | Feature requests (those go elsewhere) |
| Better patterns identified | Routine task completions |
| Code/installer/rule bugs discovered during plan execution | |
| Meta-observations about the planning/orchestration system itself | |

---

## Learning Entries

> **APPEND-ONLY:** Add entries as learnings are discovered. Never modify or delete previous entries.

### Entry Format

```markdown
### Learning [N]: {Brief Title}

**Source:** Task {task-id} | Date: YYYY-MM-DD

**Trigger:** {What happened that revealed this learning}

**Category:** {Missing rule | Unclear instruction | Workflow gap | Tool capability gap | Better pattern}

**User's Exact Words:**
> "{Quote the user if applicable}"

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | {Which RBTV file or component} |
| Type | {Add rule | Clarify instruction | New template | Tool enhancement} |
| Proposed Change | {Specific change to make} |

**Compound Readiness:**
- [ ] Self-contained (no dependencies on other learnings)
- [ ] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation
```

<!-- Learning entries will be appended below this line -->

---

## Compound Generation

When learnings accumulate, the final plan task (`p5-compound`) processes them:

1. Review all learnings marked compound-ready
2. Group related learnings by target component
3. Generate compound documents for implementation
4. Mark processed learnings (append "Compounded: YYYY-MM-DD" line)

---

<!--
======================================================================
p5-compound RETROACTIVE CAPTURE (2026-06-10)
----------------------------------------------------------------------
Authoring note: This run never dual-wrote findings to learnings.md at
the moment of discovery (the dual-write gap is itself Learning 2 below).
At p5-compound the file was empty of entries. The conductor handed the
executor curated, audit-log-sourced candidate findings; each was judged
against § What Belongs Here and authored here retroactively.

The four entries below LOGICALLY belong under the
`<!-- Learning entries will be appended below this line -->` marker
(line ~56). They are appended at end-of-file instead to honor the
strict append-only contract (no existing line may be modified/moved).
Read them as the run's Learning Entries.
======================================================================
-->

## Learning Entries (retroactive — see capture note above)

### Learning 1: Count-only proof weakening recurred 3× across models and roles

**Source:** Tasks p3-3 (B9), p4-1 (B11), p4-checkpoint (B12) | Date: 2026-06-10

**Trigger:** Captured retroactively at p5-compound from the run's audit log. The same defect — collapsing "content/order/identity proven" into "count matches" — fired three times under effort pressure, in three different worker roles and across two models:
- **B9 (p3-3, qwen builder):** weakened the reopen test in `test_pb11` to a bare row-count assertion; the opus reviewer strengthened it to disk-level restructure proof (removed-slide text absent, duplicate byte-identical, fragment verbatim).
- **B11 (p4-1, qwen builder):** `test_round_trip_preserves_order` asserted only `final_count==10` — a scrambled deck would pass; the opus reviewer strengthened it to order-survival proofs.
- **B12 (p4-checkpoint, claude:sonnet COLD verifier):** graded criterion C1 (round-trip order + edited text) count-only — "10 slides present" — with no content-level inspection; the conductor's gate caught it, and a second verifier session re-exercised with content proofs (marker in thumbnail srcdoc, disk section-order).

The safety net (reviewer / conductor gate) caught all three, but each catch cost an extra dispatch. The defect is role-independent (builder, reviewer-input, cold-verifier) and model-independent (qwen, sonnet).

**Category:** Better pattern

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | (a) orchestration dispatch-wrapper binding addendum; (b) verification card review-brief standing pre-flags; (c) `rbtv-done-gate` Fidelity Floor table |
| Type | Add rule (generic anti-count-only obligation, applied at all three surfaces) |
| Proposed Change | A standing obligation that any assertion or grading of a content/order/identity criterion MUST prove content/order/identity directly — never via a bare cardinality (row count, slide count, length). A count is necessary but never sufficient: a scrambled, content-stripped, or duplicated artifact can pass a count check. Surface it as: (a) a one-line binding clause in the dispatch-wrapper addendum, (b) a standing pre-flag in the verifier review brief, and (c) a Fidelity-Floor row pairing count criteria with their content/order/identity proof. |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation

**Not compound-ready:** awaiting owner validation — Compound Readiness checkbox 3 (Validated by user feedback) is unchecked per the p5-compound header; the owner has not yet reviewed this finding. The compound block below is a PROPOSAL only.

---

### Learning 2: Dual-write to learnings.md silently failed for the whole run

**Source:** Run-wide (orchestration state-card dual-write rule) | Date: 2026-06-10

**Trigger:** Captured retroactively at p5-compound. The orchestration state card mandates that compoundable findings be written to learnings.md AT THE MOMENT of discovery (the dual-write rule), explicitly warning that a close-time harvest is lossy. This run logged every finding in the conductor's audit log and in decisions.md but wrote ZERO entries to learnings.md. The gap surfaced only when p5-compound opened an empty file and had to reconstruct the findings from the audit log — exactly the lossy close-time harvest the rule warns against. The dual-write rule existed but had no enforcement checkpoint, so it silently no-op'd for the entire run.

**Category:** Workflow gap

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | (a) orchestration state card — registrar discipline / batch-close checklist; (b) checkpoint task template |
| Type | Add rule (enforcement checkpoint for an existing-but-silent rule) |
| Proposed Change | Add an explicit, checkable gate at each batch close / checkpoint: "Did any compoundable finding surface this batch? If yes → it MUST already be appended to learnings.md NOW; if not yet appended, append before closing the batch." Make the dual-write rule produce a visible compliance artifact (the appended entry) rather than relying on the registrar to remember mid-stream. Mirror the gate into the checkpoint task template so each checkpoint re-asserts it. |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation

**Not compound-ready:** awaiting owner validation — Compound Readiness checkbox 3 is unchecked per the p5-compound header. The compound block below is a PROPOSAL only.

---

### Learning 3: Unattended CLI dispatch blocked by harness permission classifier; dialog grant alone insufficient

**Source:** Task p4-1 (B11) | Date: 2026-06-10

**Trigger:** Captured retroactively at p5-compound. The conductor's `qwen --approval-mode yolo` dispatch was blocked pre-spend by the harness auto-mode permission classifier (it reads unsupervised host-privilege code execution as requiring supervision). The owner's `/permissions` dialog grant was ALSO insufficient — the dispatch only fired after an explicit conversational "go" from the owner. On a serial run intended to proceed unattended, this produced two stalled round-trips that required the owner to be present, defeating the AFK intent for that segment.

**Category:** Workflow gap

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | (a) orchestration intake card — pre-AFK question round; (b) qwen / kimi model manuals — invocation/permissions sections |
| Type | Add rule (pre-AFK permission pre-authorization) + Clarify instruction (model manuals) |
| Proposed Change | Add to the intake card's pre-AFK question round an explicit item: BEFORE the run goes unattended, confirm with the owner that CLI-worker execution permissions are pre-authorized for the run's dispatch profile — and surface that a `/permissions` dialog grant alone does NOT satisfy the harness auto-mode classifier for unsupervised host-privilege execution; an explicit run-level authorization is required. Add a matching note to the qwen/kimi model manuals' invocation sections so a dispatcher anticipates the classifier block before spending a round-trip on it. |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation

**Not compound-ready:** awaiting owner validation — Compound Readiness checkbox 3 is unchecked per the p5-compound header. The compound block below is a PROPOSAL only. (Caveat: this finding is harness/host-environment-specific; the owner should confirm the classifier behavior generalizes before it is baked into the intake card.)

---

### Learning 4: Shell-cwd drift misfired a CLI dispatch launch

**Source:** Task p3-1 CLI launch (B7) | Date: 2026-06-10

**Trigger:** Captured retroactively at p5-compound. A prior diagnostic `cd` left the shell's working directory in the plan folder. The kimi launch command used vault-relative paths, which then resolved against the wrong cwd — `cat` found no prompt file, the redirect's own error surfaced as `KIMI_EXIT=1`, and NO worker process ever ran. The launch was re-fired with absolute paths and ran clean. The encoded lesson: CLI launch commands MUST use absolute paths for every prompt-file and output path, never paths that depend on the inherited shell cwd.

**Category:** Better pattern

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | (a) dispatch-wrapper prompt-file rule; (b) CLI model manuals — invocation sections |
| Type | Add rule (absolute-paths-in-launch-commands mandate) |
| Proposed Change | Mandate that every CLI-worker launch command (prompt-file read, output redirect, working files) uses absolute paths — never a path that resolves against the inherited shell cwd, which a prior diagnostic command may have moved. State the failure signature so it is recognizable: a redirect/`cat` "file not found" surfacing as the worker's exit code while no worker process actually ran. This mirrors `rbtv-sub-agents`' File-Path Hygiene mandate (workspace-root-absolute write paths) and should be cross-referenced rather than restated. |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation

**Not compound-ready:** awaiting owner validation — Compound Readiness checkbox 3 is unchecked per the p5-compound header. The compound block below is a PROPOSAL only.

---

## Compound Generation — p5-compound output (2026-06-10)

> **Status of this run's compounding:** All four authored learnings are genuine, actionable findings, but NONE is compound-ready in the strict sense — every entry's Compound Readiness checkbox 3 ("Validated by user feedback") is unchecked because the owner has not yet reviewed them (header binding). Per `rbtv-compounding`, structural fixes are STATED with target + location and await owner approval; they are NOT implemented here. No PRD files were created under `.user/compounds/` — that happens only after owner approval at the run's owner touchpoint. The blocks below ARE the proposal surface the owner reviews.
>
> Each entry is therefore marked with a `Compounded:` line that records an explicit not-ready reason rather than a completion date — a legitimate p5-compound outcome, not a failure.

### Grouping by target component

| Group | Target component | Contributing learnings |
|-------|------------------|------------------------|
| G1 — Proof-strength obligation | orchestration dispatch-wrapper addendum + verification card review-brief + `rbtv-done-gate` Fidelity Floor | Learning 1 |
| G2 — Compound-capture enforcement | orchestration state card (registrar discipline) + checkpoint task template | Learning 2 |
| G3 — CLI-worker dispatch reliability | orchestration intake card (pre-AFK round) + dispatch-wrapper prompt-file rule + qwen/kimi model manuals | Learnings 3, 4 |

### Compound block G1 — Anti-count-only proof obligation (from Learning 1)

- **Problem:** Under effort pressure, workers collapse "content/order/identity proven" into "count matches" — observed 3× this run across builder tests, reviewer input, and cold verification, in two models. A bare cardinality check passes a scrambled / content-stripped / duplicated artifact.
- **Proposed structural fix (STATED, not implemented):**
  1. **Dispatch-wrapper binding addendum** — add a one-line generic obligation: "Any assertion or grading of a content/order/identity criterion MUST prove that property directly; a count (rows, slides, length) is necessary but never sufficient and MUST NOT stand alone as the proof."
  2. **Verification card review-brief standing pre-flags** — add a standing pre-flag: "Reject any criterion graded by count alone where the criterion names content, order, or identity."
  3. **`rbtv-done-gate` Fidelity Floor table** — add a row pairing count-shaped criteria with a required content/order/identity proof.
- **Where it goes (canonical source, per `rbtv-source-of-truth`):** the orchestration module's dispatch-wrapper + verification-card workflow files and the `rbtv-done-gate` rule, all under `{rbtv_path}/<module>/...`. Exact file paths to be resolved by the implementer against `rbtv.json`.
- **Owner decision needed:** approve the obligation and confirm all three surfaces are the right homes (vs. consolidating into one).

### Compound block G2 — Dual-write enforcement checkpoint (from Learning 2)

- **Problem:** The dual-write-to-learnings rule exists but is silent (no compliance artifact), so it no-op'd for the whole run; the close-time harvest it warns against is exactly what happened.
- **Proposed structural fix (STATED, not implemented):**
  1. **Orchestration state card / batch-close checklist** — add a checkable gate at each batch close: "Any compoundable finding this batch? → it MUST already be in learnings.md; if not, append NOW before closing."
  2. **Checkpoint task template** — mirror the gate so each checkpoint re-asserts it.
- **Where it goes:** orchestration module state-card workflow file + checkpoint task template, under `{rbtv_path}/<module>/...`.
- **Owner decision needed:** approve adding the enforcement gate; confirm both homes (state card + checkpoint template).

### Compound block G3 — CLI-worker dispatch reliability (from Learnings 3 + 4)

- **Problem:** Two distinct CLI-dispatch reliability failures: (3) unattended CLI execution was blocked by the harness auto-mode classifier even with a `/permissions` dialog grant, requiring a conversational "go" and defeating AFK intent; (4) shell-cwd drift from a prior `cd` caused a CLI launch's relative paths to resolve wrong, so no worker ran while a redirect error masqueraded as the worker's exit code.
- **Proposed structural fix (STATED, not implemented):**
  1. **Intake card pre-AFK question round** — add an item: pre-authorize CLI-worker execution permissions with the owner before going unattended; surface that a dialog grant alone is insufficient for the auto-mode classifier.
  2. **Dispatch-wrapper prompt-file rule** — mandate absolute paths for every CLI launch path (prompt read, output redirect); cross-reference `rbtv-sub-agents` File-Path Hygiene rather than restate it.
  3. **qwen/kimi model manuals — invocation sections** — note both the classifier-block pre-authorization and the absolute-path mandate, with the failure signatures.
- **Where it goes:** orchestration module intake-card + dispatch-wrapper workflow files + qwen/kimi model manuals, under `{rbtv_path}/<module>/...`.
- **Owner decision needed:** approve both fixes; confirm Learning 3's classifier behavior generalizes beyond this harness before baking it into the intake card (flagged caveat on Learning 3).

### Processed-entry marks

- **Learning 1 —** Compounded: NOT READY (2026-06-10) — real learning, compound block G1 drafted as proposal; awaiting owner validation (checkbox 3 unchecked).
- **Learning 2 —** Compounded: NOT READY (2026-06-10) — real learning, compound block G2 drafted as proposal; awaiting owner validation (checkbox 3 unchecked).
- **Learning 3 —** Compounded: NOT READY (2026-06-10) — real learning, compound block G3 drafted as proposal; awaiting owner validation (checkbox 3 unchecked) + harness-generalization caveat.
- **Learning 4 —** Compounded: NOT READY (2026-06-10) — real learning, compound block G3 drafted as proposal; awaiting owner validation (checkbox 3 unchecked).

---

### Learning 5: Printed-but-ungated pre-commit check swept foreign staged deletions into a fold commit

**Source:** B15 fold commit `5fc186f` | Date: 2026-06-10 (conductor-authored at the moment of discovery, per Learning 2's own discipline)

**Trigger:** The conductor's fold command chained `git diff --cached --stat` (the index-clean check) with `&&` into `git add` + `git commit`. The check PRINTED a parallel session's 22 staged deletions (−4,025 lines) but nothing gated on the output — the commit swept the foreign staging in. Fixed forward via disclosure commit `74768af` (no amend, per the vault rule).

**Category:** Better pattern

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | Orchestration state-card wave-commit discipline (and/or the rbtv-commit skill's hygiene steps) |
| Type | Add rule (hard-gate the pre-stage index check) |
| Proposed Change | A conductor fold/spine commit MUST run the index-clean check as a HARD CONDITIONAL (e.g. `git diff --cached --quiet \|\| abort`), never as a printed observation chained into the staging command. A non-empty index at fold time = stop, surface, re-scope. Printed checks that don't gate are skipped checks. |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation

**Not compound-ready:** awaiting owner validation (checkbox 3) — surfaced on the owner close-surface with the collision disclosure. Groups naturally with G2 (enforcement-gate family).

**Compounded:** NOT READY (2026-06-10) — proposal only.

---

## Owner Validation — B15 hard halt (2026-06-10, appended supersession)

> Appended per the file's append-only discipline; supersedes the `Compounded: NOT READY` marks above.

The owner ruled "all as recommended" at the B15 hard halt: **G1 APPROVED · G2 APPROVED · G3 APPROVED with the Learning-3 generalization caveat · Learning 5 APPROVED.** All five learnings are now owner-validated (checkbox 3 satisfied) and compound generation is complete:

- **Learning 1 (G1)** — Compounded: 2026-06-10 → `.user/compounds/rbtv-orchestrating/cp-rbtv-orchestrating-anti-count-only-proof-obligation.md` + sibling `.user/compounds/rbtv-done-gate/cp-rbtv-done-gate-anti-count-only-floor-row.md`
- **Learning 2 (G2)** — Compounded: 2026-06-10 → `.user/compounds/rbtv-orchestrating/cp-rbtv-orchestrating-dual-write-enforcement-gate.md`
- **Learnings 3+4 (G3)** — Compounded: 2026-06-10 → `.user/compounds/rbtv-orchestrating/cp-rbtv-orchestrating-cli-dispatch-preauthorization-and-absolute-paths.md` (carries the Learning-3 caveat as a binding implementation note)
- **Learning 5** — Compounded: 2026-06-10 → `.user/compounds/rbtv-orchestrating/cp-rbtv-orchestrating-hard-index-clean-commit-gate.md`

Implementation routes through the evaluation tasks in `2-areas/compounds/compounds-tasks.md` (rbtv source edits + docs sync per `rbtv-source-of-truth`), not through this run.
