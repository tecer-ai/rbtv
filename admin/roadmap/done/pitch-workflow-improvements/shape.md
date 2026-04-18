# Shape - Pitch Workflow Improvements

> **Purpose:** This document captures shaping decisions and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping

### Scope Definition

**What this accomplishes:**
- Enforce HTML quality patterns (logo sizing, background textures, page-break overflow) so decks export cleanly on first attempt
- Structure pitch output folders by target type (client/fundraising) and date, with automated PDF export and visual QA
- Enforce bidirectional sync between HTML, narrative, and companion docs across all three pitch agents

**What this does NOT include:**
- New pitch workflow steps beyond step-10 (PDF validation)
- Changes to pitch narrative content or slide structure
- New agent capabilities beyond sync enforcement
- Browser-based HTML validation (no Playwright for HTML — only for PDF screenshots)
- Pixel-perfect PDF rendering guarantees across all browsers

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| PDF export tool | Decktape (`npx decktape generic`) | Validated 2026-03-14; headless, no browser dependency |
| Screenshot tool | Playwright MCP | Already configured in `.mcp.json` |
| Client folder structure | `_clients/{client}/presentations/YYYY-MM-DD-{objective}/` | Separates by client, date, and meeting purpose |
| Fundraising folder structure | `_fundraising/{round}/YYYY-MM-DD-{fund}/` | No `presentations/` nesting — fundraising is the presentation |
| Narrative sync approach | Options 3+4: agent-level rule + step-level enforcement | Dual-layer coverage without adding workflow steps |
| Asset handling scope | Update `html-patterns.md` and `step-07-generate.md` only | Smallest change surface for maximum impact |
| Phase ordering | Asset Handling → Output & PDF → Narrative Sync | Asset quality improvements benefit PDF validation; step-07 changes ordered before sync additions |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Must fit existing step-07 structure | RBTV micro-file architecture | Changes are additive sections, not restructuring |
| Must not break steps 1–9 | Backward compatibility | All changes are additive or modify frontmatter only |
| Patterns must work for client AND investor decks | Both pitch workflows use same generation | Pattern rules must be target-agnostic |
| No extra overhead for CSS-only edits | Narrative sync constraint | Sync rule must distinguish content vs. style changes |
| Vivian's INPUT rule stays | Agent architecture decision | Sync is additive — Vivian still takes narrative as input |
| User must approve folder path | Output management requirement | step-01 prompts and halts for approval |

### User Inputs

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Plan scope | "the execution of pitch-workflow" (pointing to 3 compound docs) | Three-phase plan covering asset handling, output management, and narrative sync |
| 2 | Plan name | Accepted suggested name | `pitch-workflow-improvements` |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Phase ordering | No explicit preference | Proposed Asset Handling → Output & PDF → Narrative Sync based on dependency analysis | Accepted — asset quality feeds PDF validation |
| 2 | Task granularity | No explicit preference | Combined identical agent updates (leo+roelof) into one task; kept vivian separate due to INPUT rule | Accepted |
| 3 | Micro-step file selection | No explicit preference | Only p1-1 and p2-2 warrant micro-step files; rest are inline | Accepted |
| 4 | Eliminate rule file | User challenged need for separate `bmad-rbtv-pitch-output.md` rule | Folder conventions belong inline in step-01-init — one file, one source of truth | Accepted — p2-1 removed, Phase 2 renumbered |

---

## Standards Applied

### RBTV Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Atomic files rule | All modified files must remain self-contained |
| Micro-file architecture | New step-10 follows existing step file structure |
| BMAD agent patterns | Sync rules use existing `<rules>` XML structure in agent files |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Path verification | First task in each phase must verify target file paths exist |
| Compound doc as source of truth | All implementation details derived from the three compound docs — not invented |
| step-07 change ordering | Phase 1 verification rows before Phase 3 sync check |

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

### 2026-03-17 — Phase 2 quality review: step-09 references now stale

Quality review approved all Phase 2 deliverables but flagged two non-blocking observations in step-09-synthesis.md (pre-existing content, not part of Phase 2 scope):
1. Package summary still references `images/` subfolder — step-01 now defines `assets/` as the image subfolder
2. Quality checklist and next steps reference manual Ctrl+P PDF export — now partially superseded by step-10's Decktape automation

Both are cosmetic inconsistencies in step-09's summary sections, not functional breaks. Recommend addressing in a follow-up cleanup pass.

### 2026-03-17 — Progress line updates across all steps

Updated "Step X of 9" to "Step X of 10" across all 10 step files (steps 01–10) for consistency after adding step-10. This was not explicitly called out in any task but is a necessary side effect of adding a new step.

### 2026-03-17 — Phase 3 implementation complete

All six files modified per compound doc specifications:
- **leo.md, roelof.md**: Identical artifact sync rule added to `<rules>` sections
- **vivian.md**: Same sync rule added + INPUT rule extended with content-change detection clause
- **step-e01-load.md**: Section 2b added for loading narrative/companion docs; step-specific rule added about linked artifact loading
- **step-e02-edit.md**: Sync Enforcement subsection added to step-specific rules with content vs. styling distinction
- **step-07-generate.md**: Section 6b (Post-Generation Sync Check) added between verification and menu presentation, with CSS-only exemption

CSS-only exemption is enforced at three levels: (1) agent rules specify "content-only changes (not CSS/styling)", (2) step-e02-edit distinguishes content vs. styling explicitly, (3) step-07 section 6b exempts "CSS/styling-only decisions."

### 2026-03-17 — Path discrepancy in shape.md References table

The "Files to Load During Execution" table lists `workflows/pitch/data/html-patterns.md` and `workflows/pitch/data/html-components.md` for task p1-1. The actual file paths are `workflows/_shared/pitch-data/html-patterns.md` and `workflows/_shared/pitch-data/html-components.md`. The compound doc and step-07 frontmatter both reference the correct `_shared/pitch-data/` path. Non-blocking — the task file's Context Files table also has the correct compound doc path which contains the correct paths.

### 2026-03-17 — Phase 4: File reference review (p4-refs) complete

Verified all 28 static path references across 11 modified files. Zero broken links. Runtime paths (`{output_folder}/...`) excluded from verification as they depend on execution-time values.

### 2026-03-17 — Phase 4: Learnings compound (p4-compound) complete

Reviewed learnings.md — no learning entries were captured during plan execution. Three shape.md discoveries were evaluated but none qualify as compound-ready meta-learnings (all project-specific, not system-level). Documented "no learnings" result in learnings.md.

### 2026-03-17 — step-09 stale references already resolved

The Phase 2 quality review flagged step-09-synthesis.md as still referencing `images/` subfolder and manual Ctrl+P PDF. Post-Phase 4 verification confirms these references no longer exist in the file — step-09 correctly uses `assets/` and references step-10 for PDF export. The stale references were fixed during Phase 2 implementation. The earlier shape.md entry describing the issue is now outdated.

---

## References

> **Path format:** External files (outside this plan folder) use project-root-relative paths. Internal files (within this plan folder) use file-relative paths (`./`, `../`).

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `_admin/roadmap/todos/_claude-code-workspace/pitch-workflow/cp-workflow-pitch-asset-handling-and-layout-overflow.md` | Logo patterns, background image constraints, design constraint rows 13–16, step-07 verification rows |
| `_admin/roadmap/todos/_claude-code-workspace/pitch-workflow/cp-workflow-pitch-output-and-pdf-validation.md` | Folder conventions (client/fundraising), step-10 PDF validation with Decktape + Playwright, step-01 output path prompt |
| `_admin/roadmap/todos/_claude-code-workspace/pitch-workflow/cp-workflow-pitch-narrative-sync.md` | Agent sync rules (leo, roelof, vivian), edit step sync enforcement, step-07 post-gen check, CSS-only exemption |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `workflows/_shared/pitch-data/html-patterns.md` | Target file for pattern additions | p1-1 |
| `workflows/_shared/pitch-data/html-components.md` | Reference for component structure | p1-1 |
| `workflows/pitch/steps-c/step-07-generate.md` | Target for verification rows and sync check | p1-2, p3-5 |
| `workflows/pitch/steps-c/step-01-init.md` | Target for output path prompt | p2-2 |
| `workflows/pitch/steps-c/step-09-synthesis.md` | Chain to step-10 | p2-4 |
| `workflows/pitch/workflow.md` | Register step-10 | p2-5 |
| `agents/leo.md` | Target for sync rule | p3-1 |
| `agents/roelof.md` | Target for sync rule | p3-1 |
| `agents/vivian.md` | Target for sync rule + INPUT update | p3-2 |
| `workflows/pitch/steps-e/step-e01-load.md` | Target for narrative loading | p3-3 |
| `workflows/pitch/steps-e/step-e02-edit.md` | Target for sync enforcement | p3-4 |
