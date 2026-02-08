# Shape - RBTV Tools Manifest and Documentation Fix

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Create unified tools manifest (`_bmad/rbtv/tools-manifest.csv`) with id, skill_path, subagent_path, description columns
- Update core plan-lifecycle documentation (4 files) to reference manifest and clarify skills vs subagents distinction
- Update onboarding documentation (2 files) with manifest location and tool invocation methods
- Rename task file from `judge.xml` to `quality-review.xml` for naming consistency
- Clean up obsolete `rbtv-manifest.csv` after verifying no references

**What this plan does NOT include:**
- Creating new skills or subagents (only documenting existing ones)
- Modifying tool behavior or implementation (documentation-only changes)
- Updates to BMM (BMAD Methodology Module) documentation
- Changes to compound todo beyond cp-bmad-domain-and-manifests.md

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Manifest structure | id, skill_path, subagent_path, description columns (one row per tool) | Skills and subagents share same id (tool identity); unified view instead of flat type column |
| Skill invocation documentation | "Read skill_path in current context" | Skills have no separate invoke API; agent reads SKILL.md and applies in-context |
| Subagent invocation documentation | "Use Task tool with `subagent_type='<id>'`" | Explicit mechanism per Cursor's Task tool; runs in fresh context |
| Task scope | Single BMAD task (not multi-task plan) | Bounded deliverable with clear completion criteria; manifest creation + doc updates |
| Cleanup approach | Delete rbtv-manifest.csv after verification | Tools-manifest replaces it as single source of truth |
| File rename | judge.xml → quality-review.xml | Align task name with subagent/skill naming (quality-review) |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Derive from _bmad/rbtv/.cursor/ folder | Technical (source of truth for existing tools) | Manifest must accurately reflect <20 skills/subagents currently installed |
| Skills and subagents share same id | Architectural (tool identity model) | One manifest row per tool with both paths; id used for both skill lookup and subagent_type |
| Subagents cannot invoke other subagents | Architectural (nesting prohibited) | Documentation must clarify: subagents can only use skills, not other subagents |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Misleading subagent documentation | "plan-creation-rules.md lists only judge, generalPurpose, explore but doesn't say where to find full list" | Goal 2 (update plan-creation-rules.md to point to manifest for complete subagent types list) |
| 2 | Tools manifest doesn't exist | "workflow.md references tools-manifest.csv but it doesn't exist; only rbtv-manifest.csv exists" | Goal 1 (CREATE tools-manifest.csv) + cleanup decision (delete rbtv-manifest.csv) |
| 3 | Skills omitted from "tools" framing | "workflow.md says 'tools for Task tool' which implies only agents, but skills are also available tools" | Update workflow.md to clarify manifest lists both skills (read path) and subagents (Task tool) |
| 4 | No pointer to tool catalog | "plan-task-microstep-template.md says to include Tools section if task needs specialized skills/subagents but doesn't say where to find them" | Add instruction in template: "Available tools: see _bmad/rbtv/tools-manifest.csv" |
| 5 | Judge naming inconsistency | "Task file is judge.xml but subagent is quality-review" | Goal 4 (RENAME judge.xml to quality-review.xml for consistency) |
| 6 | Source constraint clarification | "Derive from _bmad/rbtv/.cursor/ folder (less than 20 skills/subagents)" | Constraint captured; manifest generation scans .cursor/skills/ and .cursor/agents/ folders |
| 7 | Compound todo removed from scope | "Goal 4 (cp-bmad-domain-and-manifests.md) is not necessary" | Scope exclusion confirmed; compound todo not updated |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Manifest column structure | User confirmed: "id, skill_path, subagent_path (same id for both)" | Proposed unified row-per-tool vs flat type column (rbtv-manifest.csv has type, name, path, description) | Unified structure adopted: one row per tool with id shared between skill and subagent columns |
| 2 | How skills are "invoked" | User asked: "I don't know how to invoke skills, only subagents" | Explained: Skills have no separate invoke API; agent reads SKILL.md when description matches task; subagents use Task tool with subagent_type | Documentation will clarify: skills = read path in-context; subagents = Task tool + subagent_type |
| 3 | Whether to model as BMAD task | User asked: "Help me evaluate if this should be a task (in BMAD terms)" | Analyzed: bounded scope (1 artifact + N doc updates), clear completion criteria, fits single work unit | Agreed: model as single BMAD task (not multi-phase plan) |
| 4 | Cleanup of rbtv-manifest.csv | User confirmed: "rbtv-manifest can be deleted (just check if no file reference to it)" | Proposed verification step before deletion | Decision: DELETE rbtv-manifest.csv after verifying no references |
| 5 | Handoff workflow fix | User identified: "step-03-extraction.md mentions judge but doesn't explain what it is, and judge doesn't exist anymore" | Added to scope: update handoff workflow step-03 that references judge | Goal 4 expanded: rename judge.xml + update handoff workflow references |

---

## Standards Applied

### Plan Creation Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Task granularity (WHAT not HOW) | Goals describe deliverables (CREATE manifest, UPDATE files, RENAME task) without prescribing implementation details |
| Explicit file operations | All file tasks use CREATE/UPDATE/DELETE/MOVE verbs with file paths |
| Zero-context plans | Shape.md captures all context; plan will be self-contained for any executing agent |
| Dependency ordering | Manifest creation before doc updates; verification before rbtv-manifest.csv deletion |

### Documentation Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Atomic files rule | Each doc update targets specific section; no content repetition across files |
| Single source of truth | Tools-manifest.csv becomes canonical list; all docs reference it (not hardcode tool lists) |
| Clear invocation instructions | Every tool reference states explicit mechanism (read skill_path vs Task tool with subagent_type) |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Must scan _bmad/rbtv/.cursor/ for existing tools | Manifest generation validates <20 tools exist; errors if mismatch |
| No hardcoded tool lists in docs | All references point to manifest; "see tools-manifest.csv" pattern enforced |
| Verify before delete | rbtv-manifest.csv deletion blocked until grep confirms no references |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | Judge needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

---

## Execution Log

> **APPEND-ONLY RULES:**
> 1. After completing each task, append an entry below
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Use the exact format shown

### Entry Format

```markdown
### Task [id]: [Title]
**Completed:** YYYY-MM-DD
**Outcome:** [Brief summary of what was delivered]
**Decisions:**
- [Decision]: [Rationale]
**Issues:** [Any blockers or surprises encountered]
**Files Modified:** [List of files created/updated/deleted]
```

<!-- Execution entries will be appended below this line -->

### Task p1-1: CREATE tools-manifest.csv
**Completed:** 2026-02-05
**Outcome:** Created `_bmad/rbtv/tools-manifest.csv` with 15 tool rows (id, skill_path, subagent_path, description). 13 tools have both skill + subagent; 2 (help, mentor) are subagent-only.
**Decisions:**
- Descriptions extracted from skill SKILL.md frontmatter (primary) or subagent frontmatter (for subagent-only tools), condensed to one sentence
- Commas stripped from descriptions to keep CSV simple (no quoted fields needed)
- help and mentor included despite having no skill — they are valid subagent_type values for the Task tool
**Issues:** None
**Files Modified:** Created `_bmad/rbtv/tools-manifest.csv`

### Task p1-1 (update): Rescan after user deletions
**Completed:** 2026-02-05
**Outcome:** Updated `_bmad/rbtv/tools-manifest.csv` from 15 to 12 rows after user deleted domcobb, help, and mentor. All 12 remaining tools have both skill + subagent.
**Decisions:**
- Removed domcobb (skill + subagent deleted), help (subagent deleted), mentor (subagent deleted)
**Issues:** None
**Files Modified:** Updated `_bmad/rbtv/tools-manifest.csv`

### Task p2-1: UPDATE plan-creation-rules.md
**Completed:** 2026-02-05
**Outcome:** Replaced hardcoded subagent types (judge, generalPurpose, explore) with manifest reference. Added explicit invocation methods: skill = read skill_path, subagent = Task tool with subagent_type='<id>'. Example updated to use quality-review.
**Decisions:**
- Point to _bmad/rbtv/tools-manifest.csv for available tools instead of listing types
- Use quality-review in example (aligns with judge.xml → quality-review.xml rename)
**Issues:** None
**Files Modified:** Updated `_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md`

### Task p2-2: UPDATE workflow.md
**Completed:** 2026-02-05
**Outcome:** Clarified knowledge files table: manifest lists both skills (read skill_path) and subagents (Task tool + subagent_type='id').
**Decisions:** Single table row update; no content repetition
**Issues:** None
**Files Modified:** Updated `_bmad/rbtv/workflows/plan-lifecycle/workflow.md`

### Task p2-3: UPDATE plan-task-microstep-template.md
**Completed:** 2026-02-05
**Outcome:** Added manifest pointer to Tools section. Removed judge from "Include this section when" bullet.
**Decisions:** Pointer references tools-manifest.csv with column names
**Issues:** None
**Files Modified:** Updated `_bmad/rbtv/workflows/plan-lifecycle/templates/plan-task-microstep-template.md`

### Task p2-4: UPDATE step-04-generate-artifacts.md
**Completed:** 2026-02-05
**Outcome:** Added manifest pointer to Tools section generation instructions for micro-step task files.
**Decisions:** Instruction added to Content includes bullet; references tools-manifest.csv
**Issues:** None
**Files Modified:** Updated `_bmad/rbtv/workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md`

### Task p2-5: UPDATE readme.md
**Completed:** 2026-02-05
**Outcome:** Added "Manifest and Invocation" subsection after Implications with manifest location, skill/subagent invocation methods, and subagent nesting rule.
**Decisions:** Placed after Tool Delivery Model; lean invocation instructions per atomic-files
**Issues:** None
**Files Modified:** Updated `_bmad/rbtv/readme.md`

### Task p2-6: UPDATE get_started.md
**Completed:** 2026-02-05
**Outcome:** Added tool catalog line with manifest path and invocation methods after Tool Delivery Mechanisms section.
**Decisions:** Single sentence with path and mechanisms; avoids repetition with readme
**Issues:** None
**Files Modified:** Updated `_bmad/rbtv/get_started.md`

### Task p3-1: MOVE judge.xml to quality-review.xml
**Completed:** 2026-02-05
**Outcome:** Created `_bmad/rbtv/tasks/quality-review.xml` from quality-evaluator.xml (judge.xml did not exist; quality-evaluator.xml contained task id=judge.xml). Updated task id to quality-review.xml, name to "Quality Review", and data file references from judge-criteria.md/judge-atomic-files.md to quality-evaluator-criteria.md/quality-evaluator-atomic-files.md. Deleted quality-evaluator.xml.
**Decisions:** Treated quality-evaluator.xml as source (legacy judge task); aligned file name with tools-manifest id "quality-review"; preserved references to existing data files (quality-evaluator-*)
**Issues:** judge.xml not found at expected path; resolved by using quality-evaluator.xml as current incarnation
**Files Modified:** Created `_bmad/rbtv/tasks/quality-review.xml`; Deleted `_bmad/rbtv/tasks/quality-evaluator.xml`

### Task p3-2: UPDATE step-03-extraction.md — replace judge with quality-review
**Completed:** 2026-02-05
**Outcome:** Replaced Judge Feedback Summary with Quality Review Feedback Summary in step-03-extraction.md and step-04-document.md; added invocation clarification (subagent via Task tool with subagent_type='quality-review'). Updated judge.xml to quality-review.xml in skill, command, and agent files. Replaced judge with quality-review in plan-creation-rules.md, shape-template.md, plan-template.md. Updated example references judge.md to quality-review.md in atomic-files.mdc and quality-evaluator-atomic-files.md.
**Decisions:** Updated all handoff and plan-lifecycle references to quality-review for consistency; left role-name "judge" in example prose where it describes the evaluator role
**Issues:** None
**Files Modified:** step-03-extraction.md, step-04-document.md, plan-creation-rules.md, shape-template.md, plan-template.md, quality-review SKILL.md, quality-review.md (command), quality-review.md (agent), atomic-files.mdc, quality-evaluator-atomic-files.md

### Task p3-3: Verify no remaining references to rbtv-manifest.csv
**Completed:** 2026-02-05
**Outcome:** Grep confirmed zero references to rbtv-manifest.csv outside plan artifacts (.cursor/plans/rbtv-tools-manifest/) and the file itself. Updated _bmad-output/rbtv-development/todo/cp-bmad-domain-and-manifests.md to reference tools-manifest.csv instead of rbtv-manifest.csv so no broken references remain after deletion.
**Decisions:** Excluded plan artifacts and the file itself per p3-3 task; updated compound todo doc to tools-manifest.csv for consistency
**Issues:** None
**Files Modified:** _bmad-output/rbtv-development/todo/cp-bmad-domain-and-manifests.md (rbtv-manifest.csv → tools-manifest.csv)

### Task p3-4: DELETE rbtv-manifest.csv
**Completed:** 2026-02-05
**Outcome:** Deleted _bmad/rbtv/rbtv-manifest.csv after p3-3 confirmed no remaining references outside plan and file.
**Decisions:** None
**Issues:** None
**Files Modified:** Deleted _bmad/rbtv/rbtv-manifest.csv

### Task p4-refs: Verify all internal markdown links
**Completed:** 2026-02-05
**Outcome:** Verified internal markdown links across all plan-modified files. Fixed broken link: readme.md referenced `./GET_STARTED.md` but actual file is `get_started.md` (case mismatch). Updated link and folder structure diagram for cross-platform compatibility.
**Decisions:**
- Fix applied immediately per discovery handling (simple <5 min)
**Issues:** None
**Files Modified:** _bmad/rbtv/readme.md

### Task p4-compound: Review learnings.md and compound into system improvements
**Completed:** 2026-02-05
**Outcome:** No learnings captured during execution. learnings.md contained no learning entries (only template and Compound Generation section). No compound documents generated; no system improvement proposals to process.
**Decisions:** Followed Execute phase rule: "If NO learnings exist: Report 'No learnings captured during execution' and skip to Close phase."
**Issues:** None
**Files Modified:** None (shape.md execution log only)

---

## Execution Discoveries

> **DISCOVERY RULES:**
> 1. When execution reveals contradictions or unforeseen work, append entry
> 2. If work is simple (<5 min), do it immediately and mark checkbox
> 3. If work is complex, add new task to plan and note the task ID
> 4. NEVER modify Original Shaping - discoveries explain divergence

### Entry Format

```markdown
### Discovery [N] (from task [id])
**Date:** YYYY-MM-DD
**Finding:** [What was discovered]
**Contradicts:** [Reference to original shaping section, if any]
**Resolution:**
- [ ] Simple fix applied immediately
- [ ] New task added: [task-id]
**Details:** [Explanation]
```

<!-- Discovery entries will be appended below this line -->

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| _bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md | Current "Agent Invocation in Tasks" section (lines 117-131) lists only 3 subagent types; no pointer to full list |
| _bmad/rbtv/workflows/plan-lifecycle/workflow.md | References tools-manifest.csv (doesn't exist); frames as "Task tool" only (omits skills) |
| _bmad/rbtv/workflows/plan-lifecycle/templates/plan-task-microstep-template.md | Tools section instructions don't state where to find available tools |
| _bmad/rbtv/workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md | "Tools section — ONLY if task requires specialized RBTV skills/subagents" but no manifest pointer |
| _bmad/rbtv/readme.md | States "Agent auto-detects relevance" for skills but doesn't explain invocation mechanics |
| _bmad/rbtv/get_started.md | Lists delivery mechanisms (Command/Skill/Subagent) but no manifest location or invocation details |
| _bmad/rbtv/workflows/doc-context-handoff/steps-c/step-03-extraction.md | Mentions "judge" without explanation; judge.xml vs quality-review naming mismatch |
| _bmad/rbtv/rbtv-manifest.csv | Current flat manifest (type, name, path, description); source for tools-manifest.csv generation |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| _bmad/rbtv/.cursor/skills/bmad-rbtv/*/SKILL.md | Source: skill paths for manifest | Task: CREATE tools-manifest.csv |
| _bmad/rbtv/.cursor/agents/bmad-rbtv/*.md | Source: subagent paths for manifest | Task: CREATE tools-manifest.csv |
| _bmad/rbtv/rbtv-manifest.csv | Verify tool list completeness before deletion | Task: DELETE rbtv-manifest.csv |
| _bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md | Update "Agent Invocation in Tasks" section | Task: UPDATE plan-creation-rules.md |
| _bmad/rbtv/workflows/plan-lifecycle/workflow.md | Update knowledge files table (line 103) | Task: UPDATE workflow.md |
| _bmad/rbtv/workflows/plan-lifecycle/templates/plan-task-microstep-template.md | Add tools manifest pointer to Tools section | Task: UPDATE plan-task-microstep-template.md |
| _bmad/rbtv/workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md | Update Tools section generation instructions | Task: UPDATE step-04-generate-artifacts.md |
| _bmad/rbtv/readme.md | Add manifest location after "Tool Delivery Model" | Task: UPDATE readme.md |
| _bmad/rbtv/get_started.md | Add manifest location where mechanisms explained | Task: UPDATE get_started.md |
| _bmad/rbtv/workflows/doc-context-handoff/steps-c/step-03-extraction.md | Update judge references and add explanation | Task: UPDATE step-03-extraction.md |
| _bmad/rbtv/tasks/judge.xml | Rename to quality-review.xml | Task: RENAME judge.xml |
