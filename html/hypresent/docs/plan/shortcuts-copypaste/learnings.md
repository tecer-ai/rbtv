# Learnings - shortcuts-copypaste

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

### Learning 1: CLI-worker self-commit sweeps a contaminated index in a shared repo

**Source:** Task p2-fix | Date: 2026-06-09

**Trigger:** Pattern discovery / unexpected friction
- [x] Unexpected friction
- [x] Pattern discovery

**What happened:** The rbtv repo was being edited by a parallel session during this orchestration. When kimi self-committed the single p2-fix task (`git add <2 files>; git commit`, no pathspec on `commit`), the commit `a3e217d` swept in 5 FOREIGN files that the parallel session had already `git add`-ed to the shared index (`admin/install/installer/cli.py`+`state.py`, `orchestration/models/mirror/driver/*`, `orchestration/skills/orchestrating/cards/routing.md`). `git commit` commits the entire index, not just the worker's freshly-staged paths. No data lost (foreign work committed, not destroyed); history NOT rewritten per the parallel-session discipline. The earlier W2 wave-commit avoided this only because the conductor staged explicitly when the index happened to be clean.

**Category:**
- [x] Missing rule / workflow gap in the orchestration commit discipline

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | `rbtv` orchestration: kimi delta (`models/kimi/delta.md` commit-authorization section) + dispatch-wrapper commit-discipline + routing commit-pin |
| Type | Add rule |
| Proposed Change | In a repo with possible concurrent writers, a CLI worker's local commit MUST be pathspec-limited: `git commit -- <explicit paths>` (commits ONLY those paths regardless of index state), never a bare `git commit` after `git add`. Equivalently/better: the conductor performs ALL commits with explicit pathspec (the wave-commit pattern) and CLI workers never self-commit when a parallel writer may be active. The kimi delta's local-commit grant should mandate the `-- <paths>` form. |

**Compound Readiness:**
- [x] Self-contained
- [x] Clear implementation path
- [x] Validated by user feedback (observed live this run)
- [x] Ready for compound generation

---

### Learning 2: A "hidden/closed" done-gate verdict must read user-perceived visibility, never DOM presence

**Source:** Task p4-1 | Date: 2026-06-09

**Trigger:** Tool limitation / Pattern discovery
- [x] Unexpected friction
- [x] Pattern discovery

**What happened:** The independent cold verifier graded **C5 `failed`** — reporting the cheat-sheet overlay "still visible" after Escape / outside-click / toggle-reclick — across 3 runs on two automation stacks. The verdict was a **false negative**: its "visible?" boolean checked node presence / `getBoundingClientRect` / `offsetParent` / `display`, none of which detect an `opacity:0; pointer-events:none` hide. The overlay's scrim stays in the DOM when closed (`display:flex; position:fixed; inset:0`) — a full-viewport rect at opacity 0 — so a presence-based check reports "visible" forever. The verifier's OWN screenshots showed the overlay closed, and the conductor's measured re-exercise (computed `opacity 1→0`, `is-open` toggled) confirmed C5 held. Left unreconciled, this false negative would have FAILED the dispatch (Verification §3d) and re-opened a correct, shipped feature.

**Category:**
- [x] Better pattern than current approach (cold-verifier / done-gate exercise methodology)

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | `rbtv-done-gate` § Fidelity Floor (visual/layout criteria) + the cold-verifier guidance in `rbtv-orchestrating` verification card §3 |
| Type | Clarify instruction |
| Proposed Change | (1) For any criterion whose outcome is "element is hidden / overlay closed / dismissed", the assertion MUST read **user-perceived** visibility — computed `opacity`, `visibility`, `pointer-events`, and/or an on-screen pixel check (screenshot) — NEVER node presence, `offsetParent`, bounding-rect, or `display` (an opacity/pointer-events hide leaves a full-rect node in the DOM). (2) The reconciliation step must compare a verifier's verdict against its OWN captured screenshots: when the boolean contradicts the pixels, **the pixels win** (disk = truth applies to the verifier's return). A presence-based "still visible" with a screenshot showing it closed is a measurement bug, not a fail. |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [x] Validated by user feedback (observed live this run — verifier verdict vs. its own pixels)
- [x] Ready for compound generation

---

## Compound Generation

When learnings accumulate, the final plan task (`p4-compound`) processes them:

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
