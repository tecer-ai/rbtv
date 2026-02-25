# PRD: BMAD Delegation Standards and Optional Analyst at M2

## Status: Proposed
## Priority: Medium
## Source: System Audit Task 8 — bmad-analyst-vs-m2-evaluation.md

---

## Problem

Task 8 evaluation concluded that BMAD's analyst (Mary) and RBTV's M2 validation frameworks serve distinct purposes (overlap ~20-30%). However, running BMAD analyst workflows *before* M2 frameworks can provide valuable upstream data — market research, brainstorming, product briefs — that strengthens M2 analysis. Currently there is no mechanism in M2 to offer this optional step.

Beyond M2, BMAD delegation is central to RBTV's architecture: M4 already delegates to BMAD create-ux-design, and M6 is planned as a full BMAD routing milestone (PRD, architecture, epics/stories, dev sprints, QA — see `business-innovation-migration_v3.plan.md` tasks p6-17 and p6-18). The existing M4 bridge pattern works but is heavier than necessary, and several delegation gaps must be addressed before scaling to M6's extensive BMAD integration.

This PRD covers three concerns:
1. Standardize a lightweight BMAD delegation pattern applicable everywhere
2. Add optional BMAD analyst step at M2 start
3. Ensure M2 frameworks consume analyst output when available

---

## Context: Current BMAD Delegation Landscape

### Existing and Planned Delegation Points

| Milestone | Delegation | Pattern | Status |
|-----------|-----------|---------|--------|
| M2 Validation | None (this PRD adds optional analyst) | — | Proposed |
| M4 Design Context | BMAD create-ux-design (bmm) | Bridge workflow (6 steps across 5 files) | Built |
| M6 MVP | Full BMAD integration — PRD, architecture, epics/stories, dev sprint, QA | Routing milestone | Planned (p6-17, p6-18) |
| Party Mode | BMAD party-mode (core) | Inline exec (25+ step files) | Collaboration, NOT delegation |

**M6 is the highest-volume delegator** — it routes entirely to BMAD development workflows. Getting the delegation pattern right now is critical for M6's implementation.

### M4 Bridge Pattern (Current Reference)

The M4 Design Context bridge is the only built delegation pattern:

```
Step 01:  Init (collect context from M1/M3 + User Flow & IA)
Step 02:  Format Context (build design-context.md for BMAD)
Step 02b: Update Config (update-bmad-config task -> redirect BMAD output to RBTV folder)
Step 03:  Invoke BMAD (instruct user to load/run BMAD create-ux-design)
Step 03b: Restore Config (restore-bmad-config task -> reset to BMAD defaults)
Step 04:  Synthesis (read BMAD output, update project-memo, instruct return to M4 menu)
```

**Key characteristics:**
- User manually loads and runs the BMAD workflow (mentor instructs, user executes)
- Config update/restore bracket the BMAD invocation to redirect outputs
- Synthesis step updates project-memo and routes user back to RBTV milestone menu
- BMAD workflow itself is unaware of RBTV — it writes to whatever config says

### Gaps in the M4 Bridge Pattern

These gaps apply to ALL current and future BMAD delegations:

| # | Gap | Impact | Applies To |
|---|-----|--------|------------|
| G1 | BMAD workflows don't update project-memo | RBTV synthesis must discover and integrate BMAD output manually | All delegations |
| G2 | BMAD workflows don't route user back to RBTV | User must remember to return; mentor gives instructions but can't enforce | All delegations |
| G3 | Persona conflict during BMAD execution | BMAD agent persona (Mary: excited analyst) overtakes mentor persona (YC mentor) | All agent-mediated delegations |
| G4 | No input handoff mechanism | BMAD workflows don't accept structured input from RBTV; context must be placed in output folder | All delegations |
| G5 | Config update/restore adds friction | 2 dedicated step files (step-02b + step-03b) per delegation is heavy for a mechanical operation | All delegations |
| G6 | BMAD output files may land in unexpected locations | BMAD workflow may write files to subfolders or with names the synthesis step doesn't expect | All delegations |

---

## Architecture Decision: Bypass Agent, Delegate to Workflows Directly

**Recommendation: Delegate directly to BMAD workflows, NOT through the analyst agent.**

The BMAD analyst agent (Mary) is a menu router — it loads persona, displays menu, and routes to workflows. Its workflows are:

| Menu | Workflow Path | Useful for M2? |
|------|--------------|----------------|
| [RS] Research | `bmm/workflows/1-analysis/research/workflow.md` | YES — market/competitive/domain research |
| [BP] Brainstorm | `core/workflows/brainstorming/workflow.md` | YES — explore assumptions and opportunities |
| [CB] Create Brief | `bmm/workflows/1-analysis/create-product-brief/workflow.md` | MAYBE — if M1 brief is incomplete |
| [DP] Document Project | `bmm/workflows/document-project/workflow.yaml` | NO — not relevant to M2 |
| [PM] Party Mode | `core/workflows/party-mode/workflow.md` | NO — already available in steps |

**Why bypass the agent:**
1. **Persona conflict eliminated** (G3) — mentor stays in character; no Mary persona takeover
2. **Simpler delegation** — no agent activation/menu overhead; direct workflow load
3. **Selective offering** — only present Research and Brainstorm (relevant to M2), not full analyst menu
4. **Input context preserved** — mentor can pass M1 artifacts as context without agent re-initialization clearing it

**Tradeoff:** User loses Mary's persona flavor during these workflows. Acceptable because the mentor persona is stronger and more relevant for M2 validation context.

### Does config.yaml Already Solve Output Placement?

**Partially.** The `update-bmad-config` / `restore-bmad-config` task pair redirects BMAD output_folder to the RBTV project folder. This means BMAD workflow outputs will land in the correct directory.

**What config.yaml solves:**
- Output file placement — BMAD writes to RBTV project folder instead of BMAD root

**What config.yaml does NOT solve:**
- Project-memo updates (G1) — BMAD workflows don't know about project-memo
- Return routing (G2) — BMAD workflows don't know about RBTV milestone menu
- Input context passing (G4) — BMAD workflows don't accept structured RBTV input
- Completion tracking (stepsCompleted array not updated)
- File discovery (G6) — even with correct output folder, BMAD may write files the synthesis step doesn't expect

**Conclusion:** Config update is necessary but insufficient. A lightweight bridge with mentor-assisted file placement is still needed.

---

## Implementation Design: Lightweight Bridge Pattern (Standard)

### The Standard BMAD Delegation Sequence

This replaces the current M4 6-step/5-file bridge with a lightweight inline pattern. It should be the **standard for all BMAD delegations** — M2 analyst, M4 design context, M6 all routes.

```
BMAD Lightweight Delegation Sequence:

1. PREPARE CONTEXT
   Collect relevant RBTV artifacts as files on disk. Explain to user what BMAD will
   receive as input and what output to expect.

2. UPDATE CONFIG
   Run task: {project-root}/_bmad/rbtv/tasks/update-bmad-config.xml
   Inputs: target_module, project_name, rbtv_output_folder
   Optionally set planning_artifacts separately (see "Input Context via Config" below).

3. INSTRUCT USER
   Provide exact BMAD workflow path. Instruct:

   "Open a NEW conversation (or agent session) and load the following BMAD workflow:
    {workflow-path}

    The BMAD workflow will read its config.yaml to find input context and output
    location — these have been configured in the previous step.

    After the BMAD workflow completes, return to THIS conversation and select
    [C] Continue."

   Note: The user MUST open a new conversation because BMAD workflows load their
   own agent persona and activation sequence. Running BMAD in the same conversation
   as the mentor would cause persona conflict and context contamination.

4. WAIT FOR COMPLETION
   HALT — wait for user to return and select [C] Continue.

5. MENTOR-ASSISTED FILE PLACEMENT
   When user returns, mentor:
   a. Asks user what files BMAD produced and where they are
   b. If files are not in the expected RBTV output subfolder, helps user move/copy them
   c. Verifies expected output files are in place
   Note: Mentor knows which BMAD workflow was run and what output to expect,
   because the user returns to the SAME conversation where mentor sent them.

6. RESTORE CONFIG
   Run task: {project-root}/_bmad/rbtv/tasks/restore-bmad-config.xml

7. SYNTHESIS
   - Read BMAD output from expected location
   - Update project-memo (add completion entry, set flags, summarize findings)
   - Instruct return to milestone menu
```

### Input Context via Config (How BMAD Finds RBTV Files)

BMAD workflows in the new conversation read `{project-root}/_bmad/{module}/config.yaml` during agent activation (step 2 of every BMAD agent). The config fields that control file discovery are:

| Config Field | What BMAD Reads From It | What RBTV Should Set It To |
|---|---|---|
| `output_folder` | Where BMAD writes its output files | RBTV output subfolder (e.g., `{outputFolder}/bmad-analysis`) |
| `planning_artifacts` | Where BMAD looks for existing project context | RBTV artifacts folder containing input context for this delegation |
| `implementation_artifacts` | Where BMAD looks for code/implementation | Same as output_folder (or RBTV implementation folder if relevant) |
| `project_knowledge` | Where BMAD looks for domain docs | Usually unchanged (leave as BMAD default) |

**Critical insight:** `output_folder` and `planning_artifacts` serve different purposes — output is where BMAD writes, planning_artifacts is where BMAD reads existing context. For delegations where RBTV wants BMAD to read from one location and write to another, these must be set independently.

**Current limitation:** The `update-bmad-config.xml` task sets all three paths (`output_folder`, `planning_artifacts`, `implementation_artifacts`) to the same `rbtv_output_folder` value. This works for M4 Design Context (where the context document is placed in the output folder before invoking BMAD), but doesn't work when input context is at a different path than the desired output location.

**Required enhancement to `update-bmad-config.xml`:** Add an optional `rbtv_planning_artifacts` input that, when provided, sets `planning_artifacts` independently from `output_folder`. When omitted, current behavior (all three set to same path) is preserved.

**Key improvement over M4's current pattern:** Steps 2, 3, 4, 5, 6, 7 are inline within a single step file (or small section of an init step), not spread across 5 separate step files. Step 5 (mentor-assisted file placement) is new — it closes gap G6 by having mentor verify and help organize BMAD output before synthesis.

### Simplifying M4 Design Context to Use the Standard Pattern

The current M4 bridge uses 5 step files (step-02b, step-03, step-03b, step-04 plus the format step). With the lightweight pattern, this can be reduced:

**Current M4 (6 steps across 5 files):**
```
step-01-init.md         -> Load context, verify prerequisites
step-02-format-context.md -> Build design-context.md
step-02b-update-config.md -> update-bmad-config task
step-03-invoke-bmad.md    -> Instruct user to run BMAD
step-03b-restore-config.md -> restore-bmad-config task
step-04-synthesis.md      -> Integrate output, update project-memo
```

**Simplified M4 (3 steps across 3 files):**
```
step-01-init.md           -> Load context, verify prerequisites (unchanged)
step-02-format-context.md -> Build design-context.md (unchanged)
step-03-delegate-and-synthesize.md -> Standard delegation sequence:
                             update config, instruct user, wait, file placement,
                             restore config, synthesis, return to M4 menu
```

This collapses steps 02b + 03 + 03b + 04 into a single step file that follows the standard lightweight delegation sequence. The file stays well under 250 lines because the delegation sequence is procedural (not elicitation-heavy).

---

## M2 Implementation: Optional Analyst Step

### Changes to `bi-m2/steps-c/step-01-init.md`

After loading project state (Section 1) and before analyzing progress (Section 2), insert:

```
### 1b. Optional BMAD Analyst Workflows

Check project-memo frontmatter for `bmadAnalystCompleted: true`. If set, skip this section entirely.

If NOT set, present:

> "Before diving into M2 validation frameworks, you can optionally run
> BMAD market research or brainstorming to gather additional data.
>
> This is recommended if:
> - You haven't done market/competitive research yet
> - You want structured brainstorming before assumption testing
> - Your M1 conception feels incomplete
>
> BMAD outputs will feed into your M2 frameworks as source material.
>
> [R] Run BMAD Research -- market, competitive, or domain analysis
> [B] Run BMAD Brainstorm -- expert-guided brainstorming session
> [S] Skip -- proceed directly to M2 frameworks
> [X] Skip permanently -- never show this option again"

On selection:
- [R] or [B]: Execute standard lightweight delegation sequence (below)
- [S]: Continue to Section 2 (framework menu)
- [X]: Set `bmadAnalystCompleted: true` in project-memo frontmatter, continue to Section 2
```

Analyst delegation sequence (inline, following standard pattern):

```
1. PREPARE CONTEXT
   M1 conception artifacts already exist on disk at:
   {project-root}/_bmad-output/{project-name}/founder/m1-conception/
   No files to copy — config update (next step) will point BMAD to this location.

2. UPDATE CONFIG
   Run task: {project-root}/_bmad/rbtv/tasks/update-bmad-config.xml
   Inputs:
     target_module="bmm"
     project_name={project-name}
     rbtv_output_folder="{outputFolder}/bmad-analysis"
     rbtv_planning_artifacts="{project-root}/_bmad-output/{project-name}/founder/m1-conception"

   This sets:
   - output_folder -> bmad-analysis/ (where BMAD writes new files)
   - planning_artifacts -> m1-conception/ (where BMAD reads M1 context)

3. INSTRUCT USER
   "Open a NEW conversation and load the BMAD workflow directly (do NOT load the analyst
   agent — we are delegating to the workflow, not the agent):

   [R] Research: {bmad_bmm}/workflows/1-analysis/research/workflow.md
   [B] Brainstorm: {bmad_core}/workflows/brainstorming/workflow.md

   The workflow will automatically find your M1 conception artifacts via config.yaml
   (planning_artifacts has been set to your M1 folder).

   After the BMAD workflow completes, return to THIS conversation and select [C] Continue."

4. WAIT FOR COMPLETION
   "[C] Continue -- BMAD workflow complete"
   HALT -- wait for user confirmation.

5. MENTOR-ASSISTED FILE PLACEMENT
   Ask user what files BMAD produced. Verify they are at {outputFolder}/bmad-analysis/.
   If files landed elsewhere, help user move/copy them to {outputFolder}/bmad-analysis/.

6. RESTORE CONFIG
   Run task: {project-root}/_bmad/rbtv/tasks/restore-bmad-config.xml
   Inputs: target_module="bmm"

7. SYNTHESIS
   - Read BMAD output at {outputFolder}/bmad-analysis/
   - Update project-memo:
     - Set `bmadAnalystCompleted: true` in frontmatter
     - Add to Progress > Validation section:
       "### BMAD Analysis (Optional)
        **Status:** Complete
        **Output:** {outputFolder}/bmad-analysis/
        **Summary:** [brief summary of research/brainstorm output]"

8. RETURN TO FRAMEWORK MENU
   Continue to Section 2 (framework progress analysis and menu display).
   User may run the delegation sequence again for a different workflow (e.g., Research then Brainstorm).
```

### Changes to M2 Framework Init Steps (Analyst Output as Input)

When BMAD analyst output exists, M2 framework init steps should load it as additional context. This follows the same pattern as M2 frameworks already loading M1 outputs.

**Affected files and changes:**

| Framework | Init Step | What to Add |
|-----------|-----------|-------------|
| Leap of Faith | `bi-m2-leap-of-faith/steps-c/step-01-init.md` | In CONTEXT TO LOAD, add: "Read `{outputFolder}/bmad-analysis/` contents (if exists) for market research and brainstorming findings that inform assumption harvesting" |
| Assumption Mapping | `bi-m2-assumption-mapping/steps-c/step-01-init.md` | In CONTEXT TO LOAD, add: "Read `{outputFolder}/bmad-analysis/` contents (if exists) for research-backed assumptions to include in mapping" |
| TAM/SAM/SOM | `bi-m2-tam-sam-som/steps-c/step-01-init.md` | In CONTEXT TO LOAD, add: "Read `{outputFolder}/bmad-analysis/` contents (if exists) for market data, competitive intelligence, and sizing inputs" |
| Unit Economics | `bi-m2-unit-economics/steps-c/step-01-init.md` | In CONTEXT TO LOAD, add: "Read `{outputFolder}/bmad-analysis/` contents (if exists) for market pricing data and competitive benchmarks" |
| Technology Readiness | `bi-m2-technology-readiness-level/steps-c/step-01-init.md` | In CONTEXT TO LOAD, add: "Read `{outputFolder}/bmad-analysis/` contents (if exists) for technical research findings" |
| Pre-mortem | `bi-m2-pre-mortem/steps-c/step-01-init.md` | In CONTEXT TO LOAD, add: "Read `{outputFolder}/bmad-analysis/` contents (if exists) for risk signals from market/competitive research" |

**Pattern:** Each init step adds a single line to its CONTEXT TO LOAD section. The line uses `(if exists)` so frameworks work identically whether or not analyst was run. No changes to framework logic — just additional source material loaded during init.

---

## Fixes for All BMAD Delegation (Apply Everywhere)

These fixes address the gaps identified in the M4 bridge pattern and should be applied to ALL workflows that delegate to BMAD — existing (M4 Design Context), this M2 analyst step, and planned (M6 MVP).

### Fix 1: Standardize Lightweight Bridge Pattern

Codify the lightweight delegation sequence (defined above) as the standard for all BMAD delegations. Document it as a reference protocol so future milestone implementations (M6 especially) follow it consistently.

**Location:** Add as a section in `workflows/build-rbtv-component/data/bmad-architecture.md` (the god-agent's architecture reference) so any AI building new BMAD delegation steps follows the standard.

### Fix 2: Simplify M4 Design Context Bridge

Refactor the current M4 bridge from 5 step files to 3 step files using the standard lightweight pattern. Steps 02b (update config), 03 (invoke BMAD), 03b (restore config), and 04 (synthesis) collapse into a single `step-03-delegate-and-synthesize.md`.

**Note:** step-01-init and step-02-format-context remain unchanged — they handle RBTV-specific context preparation which is distinct from the delegation mechanics.

### Fix 3: Input Context Passing (G4)

**Current state:** BMAD workflows discover input from config paths (`planning_artifacts`, `output_folder`). The `update-bmad-config.xml` task sets all three path fields to the same value, which doesn't support the common case where RBTV input context lives at a different path than the desired BMAD output location.

**Fix:** Enhance `update-bmad-config.xml` to accept an optional `rbtv_planning_artifacts` input:
- When provided: set `planning_artifacts` to this value, `output_folder` and `implementation_artifacts` to `rbtv_output_folder`
- When omitted: current behavior preserved (all three set to `rbtv_output_folder`)

This lets RBTV say "read from M1, write to bmad-analysis" in a single config update.

**For analyst workflows specifically:**
- Set `planning_artifacts` → M1 conception folder (BMAD reads M1 artifacts as context)
- Set `output_folder` → bmad-analysis subfolder (BMAD writes new output here)
- BMAD research workflow reads from `planning_artifacts` for project context automatically
- Brainstorm workflow accepts a `data` file (project-context-template) — pre-populate with M1 findings if needed

### Fix 4: Project-Memo Updates Are Always RBTV's Responsibility (G1)

**Principle:** BMAD workflows will NEVER update project-memo. This is always the RBTV synthesis step's responsibility.

**Why:** Project-memo is an RBTV artifact with RBTV-specific structure (milestones, stepsCompleted, framework references). Asking BMAD to update it would create tight coupling.

**Action:** Document this as a lightweight bridge pattern rule. No code change needed — M4 already does this correctly.

### Fix 5: Return Routing Is Always Mentor's Instruction (G2)

**Principle:** The synthesis step explicitly instructs the user to return to the RBTV milestone menu. BMAD workflows are unaware of this routing.

**Why:** Same coupling argument as Fix 4. BMAD shouldn't know about RBTV milestone structure.

**Action:** Already implemented correctly in M4 step-04-synthesis. Ensure all future synthesis steps follow the same pattern: "Return to {milestone} menu and select [B] Back."

### Fix 6: Mentor-Assisted File Placement (G5 + G6)

**New step in delegation sequence:** After user returns from BMAD workflow, mentor asks what files were produced and verifies they are in the expected output subfolder. If not, mentor helps the user move/copy them.

**Why this works:** The user returns to the same conversation where mentor sent them to BMAD. Mentor knows exactly which BMAD workflow was run and what output to expect. This is more reliable than trying to auto-discover files in arbitrary locations.

**This replaces the rigid config-only approach** — config update still redirects BMAD's output folder, but mentor-assisted verification catches cases where BMAD writes to unexpected subfolders or filenames.

---

## Migration Plan Update

### Update `business-innovation-migration_v3.plan.md`

The migration plan must be updated to ensure all pending tasks that involve BMAD delegation follow the standard lightweight bridge pattern.

**Changes to the plan's Phase 6 section:**

1. **Update Phase 6 section header text** — Add a reference to the lightweight bridge standard:

```
**BMAD Delegation Standard:**
- ALL BMAD delegations MUST use the standard lightweight bridge pattern (see prd-bmad-analyst-delegation-at-m2.md)
- Pattern: prepare context -> update config -> instruct user -> wait -> mentor-assisted file placement -> restore config -> synthesis
- Bypass BMAD agents; delegate directly to workflows to avoid persona conflict
- Mentor-assisted file placement after user returns ensures correct output location
- Project-memo updates and return routing are always RBTV's responsibility
```

2. **Update BMAD Config Management Convention** — Replace the current convention text with:

```
**BMAD Delegation Convention (Lightweight Bridge):**
- When RBTV workflows invoke BMAD workflows (M2 optional analyst, M4 Design Direction, M6 all routes), they MUST follow the standard lightweight bridge pattern:
  1. Prepare context (collect RBTV artifacts for BMAD)
  2. Run `update-bmad-config.xml` task BEFORE invoking BMAD
  3. Instruct user to load/run BMAD workflow
  4. Wait for user to return and select [C] Continue
  5. Mentor-assisted file placement (verify/move BMAD output to expected subfolder)
  6. Run `restore-bmad-config.xml` task AFTER BMAD completes
  7. Synthesis: read BMAD output, update project-memo, instruct return to milestone menu
- Bypass BMAD agents; delegate directly to their workflows
- Tasks location: `_bmad/rbtv/tasks/update-bmad-config.xml` and `restore-bmad-config.xml`
```

3. **Update task p6-17 (M6 milestone)** — Add instruction to follow the lightweight bridge standard for each BMAD workflow route. M6 has 5 routes (User Stories, Feature Docs, System Architecture, Dev Sprint, QA), each of which should use the inline delegation sequence rather than creating separate bridge workflows.

4. **Update task p6-18 (mentor M6 routing)** — Add instruction that mentor must follow lightweight bridge pattern when routing to BMAD, including mentor-assisted file placement after each BMAD workflow returns.

5. **Note about M4 simplification** — Add a note that the M4 Design Context bridge should be simplified to use the standard lightweight pattern as part of p6-19 (M4 steps-c) or as a separate refactoring task.

---

## Fallback: Manual Handoff with Project-Memo Flags

If the lightweight bridge proves too complex for the current iteration, implement a simpler manual approach:

### Minimal Implementation

1. Add a note in M2 init suggesting the user can optionally run BMAD analyst workflows
2. Add `bmadAnalystCompleted` flag to project-memo frontmatter template
3. M2 frameworks check for BMAD output at `{outputFolder}/bmad-analysis/` and reference it if found
4. No config update/restore, no bridge pattern — user handles BMAD independently

### What This Looks Like in step-01-init.md

Add a brief note after loading project state:

```
> **Optional:** Before starting M2 frameworks, consider running BMAD analyst
> workflows ([RS] Research or [BP] Brainstorm) for additional market data.
> Save outputs to {outputFolder}/bmad-analysis/ for M2 frameworks to reference.
```

**Tradeoff:** User must manage BMAD config, output placement, and return routing manually. Acceptable for v1 if bridge complexity is too high.

---

## Project-Memo Template Changes

Regardless of implementation approach, update the project-memo template:

### Frontmatter Addition

```yaml
bmadAnalystCompleted: false  # Set to true after optional BMAD analyst step
```

### Progress Section Addition

Add under M2 Validation:

```markdown
### BMAD Analysis (Optional -- Pre-M2)
**Status:** Not started | Complete | Skipped
**Output:** {outputFolder}/bmad-analysis/
**Workflows Run:** [Research / Brainstorm / None]
**Key Findings:** [Summary if completed]
```

---

## Scope and Dependencies

### In Scope
- Define standard lightweight bridge pattern for all BMAD delegations
- Enhance `update-bmad-config.xml` to support separate `rbtv_planning_artifacts` input
- M2 init step modification (optional analyst offering with inline delegation)
- M2 framework init steps (add bmad-analysis as optional input context)
- M4 Design Context simplification (collapse 5 step files to 3)
- Migration plan update (enforce delegation standard in pending M4/M5/M6 tasks)
- Project-memo template update (bmadAnalystCompleted flag + progress section)
- Documentation of lightweight bridge in bmad-architecture.md

### Out of Scope
- Modifying BMAD analyst agent or BMAD workflows (read-only dependency)
- Building M6 milestone (follows from plan, will use standard pattern)
- Automating BMAD invocation (user must manually load/run BMAD workflows)

### Dependencies
- BMAD analyst workflows must be accessible at known paths
- `update-bmad-config.xml` and `restore-bmad-config.xml` tasks must exist (already built)
- Project-memo template must support new frontmatter fields

---

## Success Criteria

- Standard lightweight bridge pattern documented and applied to M4 (simplified)
- M2 init presents optional BMAD analyst step without blocking framework progression
- User can run BMAD Research or Brainstorm and return to M2 seamlessly
- BMAD output correctly placed via mentor-assisted file placement
- All 6 M2 framework init steps load analyst output as additional context (when available)
- Project-memo updated with analyst completion status
- Mentor persona maintained throughout (no Mary persona takeover)
- Migration plan updated with delegation standards for pending M4/M5/M6 tasks
- Skip permanently option prevents repeated prompting

## Risks

- **User confusion:** Adding an optional step at M2 start may confuse users who don't know BMAD. Mitigate with clear "skip" options.
- **Context window pressure:** Loading M1 artifacts + running BMAD workflow + returning to M2 may strain context. Mitigate by instructing user to start a fresh conversation for BMAD workflow.
- **BMAD path changes:** If BMAD reorganizes workflow paths, the hardcoded paths in M2 init will break. Mitigate by documenting paths as dependencies.
- **M4 refactoring risk:** Simplifying M4 from 5 to 3 step files touches a working bridge. Mitigate by testing the simplified version against the same user flow.
