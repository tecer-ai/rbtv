# Learnings - API Workers Build

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
| Better patterns identified | Routine task completions ("created file X", "ran test Y") |
| Code/installer/rule bugs discovered during plan execution — even if fixed in-plan, log here so the fix is auditable and the discovery pattern is preserved as precedent | |
| Meta-observations about the planning/orchestration system itself | |

---

## Learning Entries

> **APPEND-ONLY:** Add entries as learnings are discovered. Never modify or delete previous entries.

### Entry Format

```markdown
### Learning [N]: {Brief Title}

**Source:** Task {task-id} | Date: YYYY-MM-DD

**Trigger:** {What happened that revealed this learning}
- [ ] User correction
- [ ] User suggestion
- [ ] Unexpected friction
- [ ] Tool limitation
- [ ] Pattern discovery

**Category:**
- [ ] Missing rule in RBTV
- [ ] Unclear instruction that caused confusion
- [ ] Workflow gap or missing step
- [ ] Tool capability gap
- [ ] Better pattern than current approach

**User's Exact Words:**
> "{Quote the user if applicable}"

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | {Which RBTV file or component} |
| Type | {Add rule \| Clarify instruction \| New template \| Tool enhancement} |
| Proposed Change | {Specific change to make} |

**Compound Readiness:**
- [ ] Self-contained (no dependencies on other learnings)
- [ ] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation
```

<!-- Learning entries will be appended below this line -->

### Learning 1: Pinned-flag gate false-negative from CLI help-table truncation

**Source:** Task p1-2 dispatch pre-flight | Date: 2026-06-09

**Trigger:** Tool limitation — kimi 1.41.0 `--help` truncates long flag names in its boxed table (`--final-message-only` renders as `--final-message…`). The routing §4 pinned-flag-existence gate run as a literal `--help` string match returned ABSENT for `--final-message-only` — a FALSE negative; the flag exists (confirmed by inspecting the truncated help line + the present `--quiet` alias).

**Category:** Tool capability gap / better pattern.

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | `cards/routing.md` §4 pinned-flag gate + kimi `delta.md` Pre-flight |
| Type | Clarify instruction |
| Proposed Change | The gate's existence check must match the flag PREFIX up to truncation (or verify via the documented alias, e.g. `--quiet`), not a full-literal-string match — CLI help tables truncate long flag names. Mirrors the Windows-Glob false-negative caveat: a negative match from one method is not proof of absence; confirm a second way before STOP. |

**Compound Readiness:** [x] Self-contained · [x] Clear implementation path · [ ] Validated by user · [ ] Ready for compound generation — confirm at p6-compound.

**DEFERRED at p6-compound (2026-06-09):** user-validation box unchecked; refines the already-applied `cp-rbtv-orchestrating-cli-flag-existence-preflight.md` gate (truncation-tolerance amendment) — fold into that compound when user-validated.

### Learning 3: run.py `sanitize_path` uses string-prefix containment, not a path-boundary check

**Source:** Task p1-checkpoint cold verifier | Date: 2026-06-09

**Trigger:** Pattern discovery — independent cold-verifier adversarial finding (the conductor exercise + the opus batch review both missed it because every adversarial input they fed hit the basename-reduction first).

**Category:** Better pattern than current approach (latent robustness weakness in security-relevant code).

**Finding:** `run.py` `sanitize_path` (~L88-95) reduces any `..`/absolute/drive-bearing path to a basename BEFORE joining to the output folder, then guards the result with `joined_real.startswith(output_folder_real)` — a STRING-prefix check. It HELD at the floor (crit 3, both exercises) because the basename-reduction prevents traversal from ever reaching the prefix check. BUT `startswith` is not a true path-boundary check: a sibling directory like `<out>-evil` shares the string prefix of `<out>`, so a future change that let a non-basename relative path reach the join could slip past the guard.

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | `3-resources/tools/rbtv/orchestration/models/_api/run.py` → `sanitize_path` |
| Type | Tool enhancement (defensive hardening) |
| Proposed Change | Replace the `startswith` containment guard with a true boundary check — `os.path.commonpath([real_out, joined_real]) == real_out` (or `Path(joined_real).relative_to(real_out)` in a try/except). Foundational: the runner is shared by every API worker (DeepSeek/Gemini/Manus). |

**Compound Readiness:** [x] Self-contained · [x] Clear implementation path · [x] Validated by user (chose fix-in-plan at p1-checkpoint) · [x] Resolved.

**RESOLVED in-plan 2026-06-09:** `sanitize_path` now uses `os.path.commonpath([output_folder_real, joined_real]) == output_folder_real` (with `ValueError`→outside) instead of the `startswith` string-prefix guard. Applied verbatim by kimi, regression battery passed (`../escape`/abs→basename; normal/sub-rel preserved), conductor(opus)-reviewed the diff. Committed `[p1-harden]` (separate commit on top of d4d6e498). This learning is closed; no post-plan action needed — recorded as precedent (cold-verifier caught a latent weakness both the conductor exercise AND the opus batch review missed because every adversarial input hit the basename-reduction first → independent cold verification earns its keep).

### Learning 4: Manus message-text prompt shaping closes the D-exec-14 narration gap — promote to the manus package's prompt-authoring guidance

**Source:** Task p6-1 | Date: 2026-06-09

**Trigger:** Pattern discovery — the p5 pilot's held-surprising (client captures `assistant_message.content` narration, not file artifacts) was avoided at p6-1 by prompt shaping alone: the dispatch demanded "deliver the COMPLETE report as plain markdown text in your chat reply message; do NOT create file attachments; do NOT reply with only progress narration." The live p6-1 task returned the full substantive report in message text — no artifact loss, no narration-only return.

**Category:** Better pattern than current approach (works around a tool capability gap without code).

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | `models/manus/delta.md` (prompt-composition guidance) → re-render `manual.md` |
| Type | Clarify instruction |
| Proposed Change | Add a MANDATORY prompt-shaping row to the manus delta: every Manus dispatch whose output the client must capture DEMANDS the complete deliverable in reply message text and FORBIDS attachments/narration-only replies — until the D-exec-14 artifact-fetch enhancement ships, message text is the ONLY capturable channel. |

**Compound Readiness:** [x] Self-contained · [x] Clear implementation path · [x] Validated (live p6-1 task, evidence on sheet) · [x] Ready for compound generation.

**Compounded: 2026-06-09** → `cp-rbtv-orchestrating-manus-message-text-prompt-shaping.md`

### Learning 5: cross-tier corroboration — pair an expensive autonomous-web task with a cents-scale grounded lookup over the overlapping slice

**Source:** Task p6-1 | Date: 2026-06-09

**Trigger:** Pattern discovery — the owner-added Gemini grounded call independently corroborated the Manus report on all 6 cross-checked dimensions (different worker, different transport, different official source host). The content reviewer could not verify live-web truth (no web access by design); the corroboration carried the confidence instead. It also exposed by contrast the part of the Manus output that was defective (its supplementary section failed review while the corroborated core stood).

**Category:** Better pattern than current approach (verification design for web-derived content).

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | `cards/verification.md` (§2 content-review variant note) and/or `cards/routing.md` §6 |
| Type | Add rule (lightweight note) |
| Proposed Change | When an autonomous-web (per-task-fee) dispatch produces decision-bearing factual content, ALSO dispatch a cents-scale grounded single-call over the highest-stakes overlapping slice and have the content reviewer cross-check the two — agreement substitutes for the reviewer's missing web access; disagreement is an automatic review flag. |

**Compound Readiness:** [x] Self-contained · [x] Clear implementation path · [x] Validated (p6-1 cross-check table in the opus review) · [x] Ready for compound generation.

**Compounded: 2026-06-09** → `cp-rbtv-orchestrating-cross-tier-corroboration-web-content.md`

---

## Candidate Seed (pre-execution — confirm or discard during the run)

> Surfaced during planning; NOT yet a confirmed learning. The `p6-compound` task decides whether each becomes a compound entry.

- **Agent-tool Claude tiers had no manifest** — the cause of the "Claude collapses to one entity" routing/intake gap. This plan fixes it via `models/claude/`, but the broader meta-lesson (every routable carrier must be manifest-modeled, or the deterministic selector cannot see it) may warrant a routing-card invariant. Target: `cards/routing.md` §1.
  - **CONFIRMED at p6-compound (2026-06-09)** → `cp-rbtv-orchestrating-routable-carrier-must-be-manifested.md`
- **Variant explosion risk** — the field-count discipline (a field must answer a routing question) should be explicitly restated for *variants* (a variant must change a routing decision), not just fields. Target: `models/manifest-schema.md` §2.
  - **CONFIRMED at p6-compound (2026-06-09)** → `cp-rbtv-orchestrating-variant-field-count-discipline.md`

---

## Compound Generation

When learnings accumulate, the final plan task (`p6-compound`) processes them:

### Compound Criteria

A learning is compound-ready when:
1. All four checkboxes in Compound Readiness are checked
2. Implementation path is clear and specific
3. No conflicting learnings exist

### Compound Process

1. Review all learnings marked compound-ready
2. Group related learnings by target component
3. Generate compound documents for implementation
4. Mark processed learnings (append "Compounded: YYYY-MM-DD" line)
