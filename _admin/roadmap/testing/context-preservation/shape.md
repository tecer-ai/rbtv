# Shape - Context Preservation

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Implement RBTV Memory System — `.claude/memory/` infrastructure, agent behavior rule, self-correction capture, reorganize command
- Implement Context Preservation Rule — Detect→Discover→Confirm→Capture sequence for session context, universal shape template
- Integrate context preservation into plan-lifecycle workflow — merge logic, template unification, reference updates

**What this plan does NOT include:**
- Automatic memory extraction (NLP over conversation) — manual/agent-triggered writes only
- Cross-workspace or cloud-backed memory — local filesystem only
- Claude Code native `memory:` agent field — file-based system until integrated
- Modifying core workflow engine (`core/tasks/workflow.xml`) — rule-based approach, no engine changes
- Creating actual memory files — these are user/agent-generated, accumulate over time

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Memory location | `.claude/memory/` | Follows Claude Code conventions; outside RBTV git tree in IDE mode |
| Memory entry format | `date \| what \| why` | Minimal, scannable, appendable |
| Self-correction format | `date \| SELF-CORRECTION: failed → working \| reason` | Superset of standard format; captures both approaches for comparison |
| Context preservation approach | Option 6: Detect→Discover→Confirm→Capture | Addresses both failure modes (no capture mechanism + wrong destination) |
| Shape.md role | Universal fallback, not universal destination | Target system conventions take priority when they exist |
| Rules directory | `_bmad/rbtv/.cursor/rules/` | Corrected from compound doc's `_config/.cursor/rules/` which doesn't exist |
| Universal template location | `_bmad/rbtv/workflows/_shared/templates/shape-template.md` | Shared workflows directory; decouples template from plan-lifecycle ownership |
| Dependency ordering | Memory System before Context Preservation | CP rule references Memory System as complementary; Memory is self-contained |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| File-based only, local filesystem | Memory PRD | No cloud, no cross-workspace, no NLP extraction |
| Memory never committed to git | Memory PRD | `.gitignore` needed for RBTV admin/standalone mode |
| Both BMAD IDE and RBTV standalone modes | Memory PRD | Path resolution differs; IDE mode is outside RBTV git tree |
| Installer must not overwrite memory | Memory PRD | `bootstrap.py` needs protection logic for `.claude/memory/` |
| No trigger for low-context sessions | CP compound | Detection signals must be reliable without being rigid |
| Must not break existing workflow outputs | CP compound | Plan-lifecycle integration is additive, not destructive |
| Quality review edge cases | CP compound QR | Freeform session naming convention needed; single-turn rich context trigger fix |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Scope | "I want to plan the execution of context-preservation" (entire folder) | Plan covers both PRDs: Memory System + Context Preservation Rule |
| 2 | Plan name | Confirmed `context-preservation` | Plan folder at `.cursor/plans/context-preservation/` |
| 3 | Context completeness | Confirmed compiled context was complete and accurate | Proceeded to structure creation |
| 4 | Structure approval | Selected Continue on proposed 4-phase structure | 15 items: 11 tasks + 4 checkpoints |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Path correction | Accepted | Discovered `_config/.cursor/rules/` doesn't exist; rules live at `_bmad/rbtv/.cursor/rules/` | Use corrected path for both new rules |
| 2 | Phase structure | Accepted 4-phase proposal | Proposed Memory→CP→Integration→Finalization based on dependency analysis | Linear 4-phase plan with 4 checkpoints |
| 3 | Micro-step file selection | Accepted | Identified 6 tasks needing micro-step files based on complexity criteria | p1-1, p1-2, p1-4, p2-1, p2-2, p3-1 get task files |

---

## Standards Applied

### RBTV Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Atomic Files Rule | Each rule file must be self-contained and interpretable independently |
| Chat Discipline | New value only in plan interactions; no restating approved content |
| Background Agents Rule | Use context-distill for multi-file reads during execution |
| Plan Linking Standard | Internal links use file-relative paths; external links use project-root-relative paths |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Memory files are never committed | `.gitignore` inclusion verified at P1 checkpoint |
| "Write immediately" principle | Both rules enforce immediate capture, never deferred |
| Rule files follow existing patterns | Executing agent must reference existing `.mdc` files for structure/convention |
| Installer safety | bootstrap.py modification verified at P1 checkpoint |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | quality-review needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter in one month?" If no, don't log it
>
> **What belongs here:** Decisions made during execution (with rationale), discoveries that change prior decisions, unexpected constraints
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y")

<!-- Decisions and discovery entries will be appended below this line -->

### 2026-03-17 — P1 Execution: bootstrap.py protection approach

**Decision:** Used a `PROTECTED_SUBDIRS` constant + `_is_protected_path()` helper to guard `copy_folder`, `admin_copy_folder`, and `admin_delete_managed_files` against touching `memory/`. Also added `.claude/memory/` to `ADMIN_GITIGNORE_ENTRIES` so it's included automatically by `admin_ensure_gitignore`.

**Rationale:** Rather than relying solely on prefix-based matching (which currently doesn't hit `memory/` files), explicit protection is defensive — prevents future broader delete/copy patterns from inadvertently affecting user memory. The `PROTECTED_SUBDIRS` set is extensible if other directories need protection later.

### 2026-03-17 — P1 Execution: reorganize-memory skill is inline, not task-referenced

**Decision:** The reorganize-memory skill embeds the 7-step protocol directly in SKILL.md instead of pointing to an external task file.

**Rationale:** All existing skills point to `.xml` task files, but the reorganize protocol is simple enough (7 sequential read/write steps) that creating a separate task file would be unnecessary indirection. The inline approach is self-contained per atomic files rule and avoids creating a new task file format question (XML vs MD for a non-workflow task).

### 2026-03-17 — P1 Post-checkpoint: lazy-trigger redesign (departs from PRD)

**Decision:** Replaced "read `memory.md` at session start" with lazy read triggers. Agents read zero memory files by default — reads happen only when a specific trigger matches (about to run CLI tool, need to write, working in a domain, session involves config).

**Rationale:** The PRD's "read at session start" design burns context tokens on every session regardless of relevance. User flagged the cost. Lazy triggers preserve the same safety guarantees (self-corrections are read before tool use) while eliminating unnecessary reads for quick or unrelated sessions. Trade-off: agents won't proactively surface knowledge they don't know to look for — but that edge case is rare vs. the constant cost.

**Impact:** Departs from PRD acceptance criterion #3 ("read `memory.md` at session start"). The criterion is met in spirit (agents read before acting) but not in letter (no unconditional session-start read).

### 2026-03-17 — P1 Post-checkpoint: self-correction write must be final step of recovery

**Discovery:** Agent failed to write its own self-correction (heredoc syntax in PowerShell) despite the rule being active. Root cause: the rule listed self-correction as a table row alongside other write triggers — easy to skip under task pressure. The agent treated the fix as complete when the retry succeeded.

**Fix:** Reframed self-correction capture as a named subsection with the write as the mandatory 5th beat of a 5-beat recovery sequence: attempt → fail → retry → succeed → **write to memory**. "The recovery is NOT complete until you write" makes skipping the write semantically impossible.

**Implication for rule design:** Trigger tables are good for scannable conditions, but high-stakes behaviors need forceful inline framing — not just a row in a table.

### 2026-03-17 — P2 Execution: rule file dual-location pattern

**Decision:** Created context preservation rule in both locations: canonical source at `_bmad/rbtv/_config/claude/rules/bmad-rbtv-context-preservation.md` (Claude Code) and workspace copy at `.cursor/rules/bmad-rbtv-context-preservation.mdc` (Cursor). Body content identical; only difference is `alwaysApply: true` in `.mdc` frontmatter.

**Rationale:** Matches the existing pattern for all 7 other RBTV rules. The plan's shape.md originally referenced `_bmad/rbtv/.cursor/rules/` as the target, but that directory doesn't exist and isn't where any other rule lives. Following existing conventions over the plan's stated path.

### 2026-03-17 — P2 Discovery: memory system rule missing workspace .mdc

**Discovery:** P1's memory system rule was created only at `_bmad/rbtv/_config/claude/rules/bmad-rbtv-memory-system.md` — it has no `.cursor/rules/bmad-rbtv-memory-system.mdc` workspace copy. All other RBTV rules have both. This means the memory system rule is not active in Cursor sessions.

**Impact:** Does not block P2. Should be addressed in P4 finalization or as a follow-up task.

### 2026-03-17 — P2 Post-checkpoint: detection signals consolidated 8 → 5 (departs from PRD)

**Decision:** Collapsed 8 detection signals to 5 by merging overlapping categories. Each surviving signal gets a richer description with disambiguation cues.

**Merges:** (1) "Decision with rationale" + "Correction with background" → **Reasoned choices**. (2) "Undocumented knowledge" + "Undocumented constraints" → **Unwritten knowledge**. (3) "Structured data" + "Entity relationships" → **Structured information**. (4) "Process descriptions" kept as **Process or workflow**. (5) "Historical context" kept as-is.

**Rationale:** User flagged the P1 pattern where the memory system rule was optimized from heavy upfront reads to lazy triggers. The CP rule doesn't have an upfront cost, but reducing cognitive load from 8 signals to 5 is the analogous optimization. Fewer signals with clearer descriptions reduce agent evaluation overhead per turn without losing detection fidelity.

**Impact:** Departs from PRD's "8 explicit detection signals" criterion. The criterion is met in coverage (all 8 original categories are represented) but not in count (5 signals, not 8). P2 checkpoint already passed before this change — the consolidation is a post-checkpoint optimization requested by user.

### 2026-03-17 — P2 Post-checkpoint: canonical source only — no replication during plan execution

**Decision:** During this plan, agents MUST write rules, commands, skills, and templates only to the canonical source of truth (`_bmad/rbtv/_config/claude/rules/`, `_bmad/rbtv/_config/claude/commands/`, etc.). Do NOT replicate files to workspace-level locations (`.cursor/rules/`, `.cursor/skills/`, `.claude/commands/`, etc.). Replication is a bootstrap/installer responsibility, not a plan-execution responsibility.

**Rationale:** P2 execution created the context preservation rule in both `_config/claude/rules/` (canonical) and `.cursor/rules/` (workspace copy). This is unnecessary work during plan execution — the installer (`bootstrap.py`) handles replication to all target locations. Writing to multiple locations doubles the risk of drift and doubles the file operations per task.

**Impact:** Retroactive — the `.cursor/rules/bmad-rbtv-context-preservation.mdc` file already created in P2 stays (no harm), but P3 and P4 must NOT replicate. Also supersedes the P2 discovery about missing memory system `.mdc` — that's an installer concern, not a plan task.

### 2026-03-17 — P2 Post-checkpoint: shape template moved to workflows/_shared/templates/

**Decision:** Moved universal shape template from `_bmad/rbtv/_shared/templates/shape-template.md` to `_bmad/rbtv/workflows/_shared/templates/shape-template.md`. Removed the empty `_bmad/rbtv/_shared/` directory.

**Rationale:** `workflows/_shared/` already exists with shared pitch data. Creating a parallel top-level `_shared/` directory adds unnecessary structure when the template is a workflow artifact. Updated all references in both rule files and shape.md Key Decisions table.

### 2026-03-17 — P3 Discovery: universal template actual path differs from shape.md plan

**Discovery:** The shape.md Key Decisions table specified `_bmad/rbtv/_shared/templates/shape-template.md` as the universal template location. The P2 executor actually created the file at `_bmad/rbtv/workflows/_shared/templates/shape-template.md`. The context preservation rule (both canonical and workspace copies) references the actual path. P3-1 and P3-3 initially used the planned path from shape.md — corrected to match the actual file location and the CP rule's references.

**Impact:** No functional impact — the path in workflow.md and step-04 now matches the actual file and the CP rule. The Key Decisions table entry in shape.md is historical (immutable) and doesn't need correction.

### 2026-03-17 — P4 Execution: link audit results and fixes (p4-refs)

**Finding:** Full link audit across all plan artifacts found 16 broken links and 6 format violations. Root causes:

1. **Source docs moved:** PRD and compound doc moved from `_admin/roadmap/todos/_claude-code-workspace/context-preservation/` into the plan folder during planning. References in shape.md References table still pointed to old paths — **fixed** (now use `./prd-rbtv-memory-system.md` and `./cp-rule-context-preservation.md`).
2. **`_bmad/rbtv/.cursor/rules/` doesn't exist:** Plan file checkpoint prompts and some task files reference this path. Canonical source is `_bmad/rbtv/_config/claude/rules/`, workspace copy is `.cursor/rules/`. These appear in the plan file body (not editable) and completed task files (historical). **Not fixed — documented.**
3. **`_bmad/rbtv/_shared/templates/` vs `workflows/_shared/templates/`:** Plan file P2 checkpoint and P4 checkpoint reference the planned path, not the actual path. Appears in plan file body (not editable). **Not fixed — documented.**
4. **Self-reference in shape.md:** User Inputs row 2 contains `.cursor/plans/context-preservation/` — a root-relative self-reference. Appears in immutable Original Shaping section. **Not fixed — immutable.**

**Impact:** All broken links are in immutable sections (Original Shaping, completed task files) or the plan file body (not editable per user instruction). No broken links remain in actively-referenced, editable sections. The plan is functionally complete — agents reading shape.md References table will now find the correct paths.

### 2026-03-17 — P4 Execution: learnings compound (p4-compound)

**Decision:** Extracted 3 meta-learnings from shape.md Decisions and Discoveries into learnings.md. One (L2 — "canonical source only") was compounded into `plan-creation-rules.md` as a new Task Granularity rule. L1 (forceful framing for critical behaviors) is a design principle already applied — no rule change needed. L3 (verify created paths match planned paths) is already addressed by the existing pN-refs validation task — no rule change needed.

### 2026-03-17 — P2 Execution: universal template simplification

**Decision:** Simplified the plan-lifecycle template during generalization. Removed the detailed Decision/Discovery entry format examples (with numbered headings, propagation checklists) and replaced with a cleaner append-only block. Kept the HTML comment markers (`<!-- BEGIN/END PLAN-SPECIFIC -->`) for conditional section inclusion.

**Rationale:** The plan-lifecycle template had elaborate entry formats (Discovery with propagation checklist, numbered entries) that are plan-lifecycle-specific conventions. The universal template needs to be usable by freeform sessions and non-plan workflows where those conventions add friction. Agents executing plans can follow the plan-creation-rules for the detailed format; the universal template provides the minimum viable structure.

---

## References

> **Path format:** External files (outside this plan folder) use project-root-relative paths. Internal files (within this plan folder) use file-relative paths (`./`, `../`).

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `./prd-rbtv-memory-system.md` | Full Memory System spec: structure, entry format, self-correction capture, acceptance criteria |
| `./cp-rule-context-preservation.md` | Full CP Rule spec: 8 detection signals, Detect→Discover→Confirm→Capture, plan-lifecycle integration, quality review observations |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `./prd-rbtv-memory-system.md` | Memory System PRD — full spec | p1-1, p1-2, p1-4 |
| `./cp-rule-context-preservation.md` | CP Rule compound — full spec | p2-1, p2-2 |
| `_bmad/rbtv/workflows/plan-lifecycle/templates/shape-template.md` | Current shape template to generalize | p2-1 |
| `_bmad/rbtv/workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md` | Step to modify for merge logic | p3-1 |
| `_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md` | Rules to update shape.md references | p3-2 |
| `_bmad/rbtv/workflows/plan-lifecycle/workflow.md` | Update shapeTemplateFile path | p3-3 |
| `_bmad/rbtv/.gitignore` | Add `.claude/memory/` exclusion | p1-3 |
| `_bmad/rbtv/_config/bootstrap.py` | Ensure installer protects memory directory | p1-4 |
