# Shape - BMAD Upgrade v6.0.4

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Upgrade RBTV BMAD compatibility from v6.0.0-Beta.4 to v6.0.4 (stable)
- Fix all 14 RBTV-BMAD touchpoints for v6.0.4 compatibility
- Refactor installer to preserve user-chosen output folder name
- Update all documentation, config, and compatibility metadata

**What this plan does NOT include:**
- `_mobile/` files (Henri updates manually)
- RBTV workflow structural conversion to split `workflow-*.md` pattern (deferred to BMB)
- Bulk mirror directory replacement (only MIRROR-VERSION.md update)

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Mirror update scope | Update MIRROR-VERSION.md only; fix hardcoded mirror reads | Mirror is a Claude Code reference snapshot, not a functional dependency; bulk copy is unnecessary overhead |
| RBTV workflow conversion | Excluded from this upgrade | All RBTV workflows already use micro-step split pattern; confirmed via prompting-assistance and git-commit checks |
| Output folder fix approach | Refactor installer to read and preserve existing folder name | Root cause fix: eliminate hardcoded `_bmad-output` rather than changing to a different hardcoded name |
| Literal _bmad-output replacement | Replace with `{bmad_output}` path variable | Path variable is the root cause fix; hardcoded strings break when users configure different folder names |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Execute from RBTV repo root | PRD execution context | All paths relative to `_bmad/rbtv/` |
| Compare against two reference directories | PRD | Mirror (Beta.4 baseline) vs BMAD-v6.0.4 (target) |
| Conditional tasks based on investigation | PRD changes #2-5, #8-9 | Some tasks may be no-ops if v6.0.4 didn't change referenced items |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Mirror update | "Step 4 is not necessary... the mirror only exists so claude code can know 'where he is at'" | Reduced mirror scope to MIRROR-VERSION.md only + verify no hardcoded mirror reads (p4-4, p4-5) |
| 2 | Workflow conversion | "I believe all of rbtv workflows already use the microstep files standard" | Confirmed via investigation; excluded structural conversion entirely |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Mirror update scope | Drop entirely | Recommended keeping MIRROR-VERSION.md update + verifying nothing hardcodes mirror reads | Update MIRROR-VERSION.md + verify hardcodes; drop bulk copy |
| 2 | RBTV workflow conversion token cost | Asked about cost | Estimated 50-100k tokens for reads alone if monolithic workflows existed; identified it as judgment-heavy too | Confirmed all already split; exclusion validated |

---

## Standards Applied

### BMAD/RBTV Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Zero-context plans | Plan is self-contained with all context in PRD and Files to Load |
| Explicit file operations | All tasks use CREATE/UPDATE/DELETE/MOVE verbs |
| Single action per task | Each task is one discrete action |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Investigation before implementation | Phase 1 must complete before Phase 2/3 |
| Conditional tasks | p2-3, p2-4, p3-1, p3-2 execute only if Phase 1 finds changes |
| Output folder name preservation | No task may introduce new hardcoded output folder names |

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

### p1-1 Findings (2026-03-08)

**BMM Workflow Paths:**
| Path | Mirror (Beta.4) | v6.0.4 | Status |
|------|-----------------|--------|--------|
| `bmm/workflows/1-analysis/create-product-brief/` | `workflow.md` | `workflow.md` | **Unchanged** |
| `bmm/workflows/2-plan-workflows/create-prd/` | `workflow.md` | `workflow-create-prd.md`, `workflow-edit-prd.md`, `workflow-validate-prd.md` | **SPLIT — workflow.md removed** |
| `bmm/workflows/2-plan-workflows/create-ux-design/` | `workflow.md` | `workflow.md` | **Unchanged** |

**Advanced Elicitation Path:**
| Path | Mirror (Beta.4) | v6.0.4 | Status |
|------|-----------------|--------|--------|
| `core/workflows/advanced-elicitation/` | `workflow.xml` | `workflow.xml` | **Unchanged** |

**Core Directory Structure:** `_config/`, `core/`, `bmm/` all present in v6.0.4. No structural changes.

**Decision:** Task p3-1 (update ana.md) IS NEEDED — `create-prd/workflow.md` must be updated to `workflow-create-prd.md`. Task p3-2 (update elicitation path) is a NO-OP — `workflow.xml` still exists unchanged.

### p1-2 Findings (2026-03-08)

**bmad-help.csv Schema:** Identical 16-column header in both versions. No schema change.
→ **p2-3 is a NO-OP** (cancel task)

**bmm/config.yaml Fields:** `output_folder`, `planning_artifacts`, `implementation_artifacts` — same field names. Only values changed (`_bmad-output` → `projects`).
→ No field rename handling needed in installer

**manifest.yaml Format:** `installation.version` field exists in v6.0.4 (value: `6.0.4`). Same YAML structure with `modules` array. Added `ides` array (not read by RBTV).
→ **p2-4 is a NO-OP** (cancel task)

**Output Folder Confirmed:** `_bmad-output` (Beta.4) → `projects` (v6.0.4) in both `core/config.yaml` and `bmm/config.yaml`.

### p1-3 Findings (2026-03-08)

**TEA Path References:** No RBTV agents, workflows, or tasks reference `_bmad/tea/`. Only matches are in BMAD-v6.0.4 docs (expected) and plan/PRD files (self-references). → No action needed.

**Hardcoded Mirror Reads:** 18 files reference `_admin/docs/BMAD-mirror/` — all are documentation/instruction references (CLAUDE.md path resolution, admin-restrictions, compat report template). These correctly tell agents where to find the mirror. None are code-level hardcoded reads that would break. → No action needed.

### Phase 1 Conditional Task Decisions

| Task | Decision | Reason |
|------|----------|--------|
| p2-3 (bmad-help.csv schema) | **CANCEL** | Schema identical — same 16 columns |
| p2-4 (manifest.yaml format) | **CANCEL** | Format unchanged — `installation.version` still exists |
| p3-1 (ana.md paths) | **NEEDED** | `create-prd/workflow.md` → `workflow-create-prd.md` |
| p3-2 (elicitation path) | **CANCEL** | `workflow.xml` unchanged in v6.0.4 |

### p2-1/p2-2 Installer Refactoring (2026-03-08)

**Decision:** Added `_extract_output_folder_name()` helper that reads `output_folder` from `core/config.yaml` and extracts the folder name (strips `{project-root}/` prefix and `/{project-name}` suffix). Falls back to `_bmad-output` if config is unreadable.

**Changes:**
- `normalize_bmad_output_paths()` now calls `_extract_output_folder_name()` before modifying any files, then uses the extracted name in all replacement strings
- `ide_merge_cursorignore()` now calls `_extract_output_folder_name()` to build the archive pattern dynamically
- No hardcoded `_bmad-output` remains in active replacement logic (only in fallback defaults)

### p3-5 Bulk Replace (2026-03-08)

**Result:** 56 files modified, 104 `_bmad-output` occurrences replaced with `{bmad_output}` path variable. Zero remaining `_bmad-output` references in `workflows/` and `tasks/` directories.

**Discovery:** `_config/config.yaml` `paths.bmad_output` needed a real default value (not a circular `{bmad_output}` self-reference). Set to `{project-root}/_bmad-output` as default; added installer logic to update it from BMAD's `core/config.yaml` during `normalize_bmad_output_paths()`.

### p4-6 Compatibility Check (2026-03-08)

**Result:** All 11 RBTV→BMAD touchpoints verified against v6.0.4 reference — **ALL COMPATIBLE**. No breaking changes found. Verified: config fields, CSV schema, manifest format, workflow paths, directory structure.

### p4-refs File Reference Review (2026-03-08)

**Result:** One expected mismatch: `ana.md` references `workflow-create-prd.md` (v6.0.4) which doesn't exist in BMAD mirror (Beta.4). This is expected since mirror was not bulk-updated (plan decision). In installed BMAD mode, the reference resolves correctly.

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| prd-bmad-upgrade-v6.0.4.md | All 14 changes, risk assessment, execution context, file modification list |
| BMAD release history (in PRD) | 8 releases from Beta.5 to v6.0.4; key changes per version |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| _admin/roadmap/todos/_claude-code-workspace/bmad-upgrade-v6.0.4/prd-bmad-upgrade-v6.0.4.md | Full PRD with all changes | p1-1, p2-1 |
| _config/install-rbtv.py | Installer code to refactor | p2-1, p2-2, p2-3, p2-4 |
| _config/config.yaml | RBTV config — versions, paths | p3-3 |
| bmad-compat.yaml | Compatibility metadata | p4-1 |
| agents/ana.md | BMM workflow path references | p3-1 |
| workflows/doc-compound-learning/workflow.md | Advanced elicitation path | p3-2 |
| CLAUDE.md | Path variable resolution table | p3-4 |
| readme.md | Path references | p4-3 |
| workflows/build-rbtv-component/data/bmad-architecture.md | Architecture reference | p4-2 |
| _admin/docs/BMAD-v6.0.4/ | Target state for comparisons | p1-1, p1-2 |
| _admin/docs/BMAD-mirror/ | Beta.4 baseline for comparisons | p1-1, p1-2 |
| _admin/docs/BMAD-mirror/MIRROR-VERSION.md | Version tracking | p4-4 |
