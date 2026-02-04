# Execution Decisions: Doc Component PRD Plan

**Plan:** Doc Component PRD Creation  
**Date Range:** 2026-02-02 to 2026-02-03  
**Status:** Completed  
**PRD Location:** `robotville/docs/to_dos/doc-component-v2/doc_component_prd.md`

---

## Plan Overview

Created a Product Requirements Document for the unified `/rbtv_doc` command that consolidates three existing documentation commands (`/doc`, `/compound`, `/handoff`) into a single component following BMAD's agentic architecture patterns.

**Deliverables:** Context document, PRD (2544 lines), phase execution decisions

---

## Critical Architectural Decisions

### A1: Three Top-Level Modes (Not Four)

**Decision:** Define 3 top-level modes: `product`, `handoff`, `compound`

**Rationale:**
- Maps cleanly to existing commands being absorbed
- Use case is a documentation type within product mode, not a standalone mode
- Keeps mental model simple for users

**User Feedback:** "lets make usecase a type of documentation that can be selected in product mode"

**Implementation:** Read PRD Modes section.

---

### A2: Master Orchestrator as Agent (Not Workflow)

**Decision:** Make the master doc orchestrator an agent with full BMAD agent structure

**Rationale:**
- Provides consistent character throughout documentation sessions
- Menu-driven UX aligns with BMAD patterns
- Agent can enforce shared rules across all modes
- User explicitly requested this change mid-execution

**Previous Decision (Reversed):** Plan originally stated "Agent persona for orchestration — Overkill; workflow.md suffices"

**Agent Design:** Read PRD Workflows section for agent specification.

---

### A3: Directory Structure — `_rbtv/work/doc/`

**Decision:** Place all doc component files in `_rbtv/work/doc/` (not `system/doc/`)

**Rationale:**
- Matches robotville's work component pattern
- Keeps robotville-specific components separate from BMAD core
- Consistent with existing `_rbtv/work/` structure

**Structure:** Read PRD Architecture section.

---

### A4: Implementation Focus — Compound Mode First

**Decision:** Focus PRD detail on compound mode; mark product and handoff as "(on hold)"

**Rationale:**
- User specified: "focus on the compound mode for now, but the new rbtv_doc must be built foreseeing that other modes will be implemented soon"
- Validates one mode fully before expanding
- Architecture must support future modes (proper abstractions, extensible design)
- Reduces initial implementation scope and risk

**What Gets Detailed:**
- ✅ Compound mode workflow specifications
- ✅ Compound mode step-file specifications  
- ✅ Compound mode templates
- ⏸️ Product/handoff mode workflows (high-level only)
- ⏸️ Product/handoff mode step-files (deferred)
- ⏸️ Product/handoff mode templates (deferred)

**Validation Criteria:**
- Architecture can accommodate additional modes without refactoring
- Orchestrator routing mechanism works for all modes
- Directory structure is consistent and extensible

---

## Mode Behavior Decisions

### B1: Compound Mode Behavior — Document Only (No Implementation)

**Decision:** Compound mode creates backlog PRDs; does NOT implement changes

**Rationale:**
- Separates identification from execution
- Enables evaluation and prioritization before implementation
- Creates auditable backlog of improvements

**Contrast with Current `/compound`:**
- Current: captures learning → proposes location → asks questions → **implements change**
- New: captures learning → proposes location → asks questions → **documents as PRD**

---

### B2: Compound Mode — Yolo Sub-Mode

**Decision:** Add `compound:yolo` sub-mode that skips user discussion

**Rationale:**
- User explicitly requested: "it must also have a yolo mode where it does not discuss with user"
- Enables faster workflow when user wants agent's best judgment without discussion
- Preserves self-assessment step (analysis still happens)

**Implementation:**
- Standard: `/rbtv_doc compound` → self-assessment → discuss → document
- Yolo: `/rbtv_doc compound:yolo` → self-assessment → document (skips discussion)
- Yolo flag lives in output document frontmatter (workflow state), not step frontmatter
- Step-03-discussion reads frontmatter to check `yoloMode` field

---

### B3: Self-Assessment Protocol for Compound Mode

**Decision:** Preserve self-assessment protocol from current `/compound`

**Rationale:**
- User confirmed: "the doc/compound must first make a self assessment, then discuss with user, then document"
- Self-assessment provides valuable context for PRD
- Protocol includes: error analysis, context source evaluation, 5 improvement options

**Step Sequence:** Read PRD Components section for step-file specifications.

---

### B4: Intelligent Mode Suggestion When No Argument

**Decision:** When user invokes `/rbtv_doc` without argument, orchestrator analyzes conversation context to suggest most likely mode

**Rationale:**
- User specified: "if used without arguments, the master orchestrator must suggest a mode and provide list of all available modes"
- Reduces friction — user sees smart suggestion first
- Still presents full menu for override
- Heuristics detect common patterns

**Mode Detection Heuristics:**
- User corrected agent behavior → compound
- Discussion about system design/architecture → product
- User mentions "for the agent that will continue" → handoff
- No clear pattern → present menu without suggestion

---

### B5: Handoff Mode — Single Structure (No Sub-Types)

**Decision:** Handoff mode has one structure, not separate "plan development" vs "execution" types

**Rationale:**
- User explicitly instructed: "forget the 2 handoff modes from use_cases_context.md"
- Simpler UX — one handoff flow
- Template can include optional sections that may be emphasized based on context

---

## Workflow Architecture Decisions

### C1: Shared Rules in Orchestrator Agent

**Decision:** Include shared rules in the agent that apply to ALL documentation modes

**Rationale:**
- User confirmed: "yes, contain shared rules"
- Prevents duplication of rules across mode workflows
- Agent enforces consistent behavior regardless of mode

**Shared Rules:**
1. Language: Communicate in config-specified language
2. State persistence: Track progress in output document frontmatter
3. Halt behavior: Always halt at menus and wait for user input
4. No implementation: Documentation modes create documents only
5. Template usage: All outputs must use mode's template
6. Output location: Respect configured paths from config.yaml

---

### C2: Focus Only on steps-c/ (Create Mode)

**Decision:** Specify only Create mode steps; Validate and Edit modes are future additions

**Rationale:**
- User specified: "lets focus only on steps-c for now"
- Validates architecture with one complete mode
- Reduces initial PRD complexity
- Architecture already includes placeholder directories for steps-v/ and steps-e/

**Implementation:**
- steps-c/ fully specified with 4 step files
- steps-v/ and steps-e/ mentioned as "(future)" throughout PRD

---

### C3: Component Configuration

**Decision:** Include `config.yaml` at component level for output paths and settings

**Rationale:**
- Architecture section originally said "No config.yaml — Deterministic paths"
- User feedback changed this: config provides flexibility
- BMAD pattern compliance (workflows load config during initialization)

**Config Fields:**
- `default_output_folder`
- `compound_output_folder`
- `communication_language`
- `document_output_language`

**Default Output Location:**
- User specified: "can be configurable, but first location is on the [project folders]/docs/todos/"
- Default: `{project-root}/_bmad-output/` (inherited from core/config.yaml)

---

### C4: Mode-Specific Templates

**Decision:** Each mode owns its templates in `{mode}/templates/` directory

**Rationale:**
- Colocation improves maintainability
- Each mode's template is specific to that mode's output
- Easier to find and update templates

**Structure:**
- `compound/templates/compound-prd.md`
- `product/templates/product-doc.md` (future)
- `handoff/templates/handoff-summary.md` (future)

---

### C5: Thin Loader Uses Agent Activation Pattern

**Decision:** Thin loader in `.cursor/commands/rbtv_doc.md` uses BMAD agent activation structure

**Rationale:**
- Consistent with BMAD command patterns
- `<agent-activation>` block clearly instructs the AI
- 7-step activation sequence matches other BMAD agents

**Structure:** Read PRD Entry Point Specification section.

---

## Component Specification Decisions

### D1: Four-Layer Component Organization

**Decision:** Organize the component inventory by BMAD's four architectural layers

**Rationale:**
- Matches BMAD architecture reference structure
- Makes dependencies clear (entry point → agent → workflows → templates)
- Helps developers understand the system hierarchy

**Layers:**
- Layer 1: Entry Point (1 file: rbtv_doc.md)
- Layer 2: Orchestrator Agent (2 files: agent.md + config.yaml)
- Layer 3: Mode Workflows (5 files: workflow.md + 4 steps)
- Layer 4: Templates (1 file: compound-prd.md)
- **Total: 9 files for compound mode**

---

### D2: Complete File Specifications (Not Just Listings)

**Decision:** Provide detailed specifications for each file, not just file paths

**Rationale:**
- Judge's feedback emphasized implementability
- Developers need to know file type, size, purpose, dependencies, and structure
- Complete specifications reduce ambiguity during implementation

**Specification Elements:**
- **Type:** Component type (Agent, Workflow, Step, Template, Config, Entry Point)
- **Size:** Estimated line count with justification
- **Purpose:** One-sentence description
- **Dependencies:** What this file requires to function
- **References/Referenced By:** Cross-reference map
- **Structure:** Key sections or frontmatter fields

---

### D3: Separate Frontmatter Schemas for Steps vs. Output Documents

**Decision:** Create two distinct frontmatter schema sections

**Rationale:**
- Judge identified confusion between step file frontmatter and output document frontmatter
- These serve different purposes and have different fields
- Separation improves clarity and prevents implementation errors

**Step File Frontmatter:**
- Required: stepNumber, stepName, nextStepFile, outputFile
- Optional: templateFile, stepDescription

**Output Document Frontmatter:**
- Required: title, docType, mode, stepsCompleted, inputDocuments, outputPath, date, yoloMode
- Includes state tracking and resumption logic

---

### D4: Step File Instruction Format Section

**Decision:** Add a comprehensive section showing the exact structure of step file instructions

**Rationale:**
- Judge feedback: "A developer reading this PRD would not be able to implement the step files without additional information"
- Need to show HOW instructions are written, not just WHAT they do
- BMAD pattern relies on precise instruction format for AI execution

**Key Elements:**
- Standard markdown structure with frontmatter
- MANDATORY SEQUENCE section with numbered actions
- MENU section with explicit halt instruction
- NEXT STEP section with state update instructions
- Advanced Elicitation behavior definition

---

### D5: Comprehensive Error Handling Specifications

**Decision:** Document 6 error scenarios with specific behaviors

**Rationale:**
- Judge feedback: "No mention of what happens if files are missing or config is malformed"
- Production-ready component needs graceful degradation
- Error messages must guide users to resolution

**Error Scenarios Covered:**
1. Missing config.yaml → Stop execution, display error, exit agent
2. Missing template file → Display error, offer Retry/Exit menu
3. Missing step file → Display error, offer Save Progress/Exit menu
4. Missing workflow file → Display error, redisplay agent menu (don't exit)
5. Malformed config.yaml → Stop execution, display syntax error, exit agent
6. Missing required config fields → Stop execution, list required fields, exit agent

---

### D6: Template Validation Rules

**Decision:** Specify required vs. optional template sections with validation rules

**Rationale:**
- Judge feedback: "Don't specify which fields are required vs. optional, or what validation rules apply"
- Implementation needs clear acceptance criteria for output documents
- Validation rules prevent incomplete PRDs from being created

**Validation Categories:**
1. **Frontmatter Fields:** Type and format requirements
2. **Content Sections:** Required vs. optional sections
3. **Markdown Structure:** Heading levels, table formats, code block requirements

**Key Rules:**
- Self-Assessment must include exactly 5 improvement options
- Acceptance Criteria must include at least 3 checkboxes
- All required sections must have content (not just headers)

---

### D7: Advanced Elicitation Behavior Definition

**Decision:** Explicitly define what happens when user selects [AE] Advanced Elicitation

**Rationale:**
- Judge feedback: "Never define what this does"
- Menu option appears in multiple steps but behavior was vague
- Consistent behavior across steps improves UX

**Behavior:**
1. Agent asks 3-5 deeper discovery questions relevant to current step
2. User provides additional information
3. Agent incorporates new information into current step's work
4. Agent redisplays SAME step's menu (does NOT advance)
5. User can Continue when satisfied, or AE again for more discovery

---

### D8: Component Dependencies Graph

**Decision:** Include both a visual flow diagram and a detailed dependency table

**Rationale:**
- Visual learners benefit from flow diagram
- Implementation needs precise mechanism documentation
- Shows both "what depends on what" and "how dependencies are expressed"

**Two Representations:**
1. **Flow Diagram:** Linear sequence from entry point to final step
2. **Dependency Table:** Source → Target → Mechanism (e.g., "Menu item `exec` attribute")

---

### D9: File Size Estimates with Justification

**Decision:** Provide line count estimates with rationale

**Rationale:**
- Judge feedback: "Lack justification for file size estimates"
- Helps validate BMAD compliance (max 250 lines per file)
- Based on BMAD reference typical sizes and content requirements from PRD

**Justification Basis:**
- BMAD architecture reference (agent: 55-76 lines, workflow: 60-80 lines, step: 80-200 lines)
- Content requirements specified in PRD (e.g., step-02 needs 5 improvement options)
- Buffer for instruction clarity and explicit halt/menu sections

---

### D10: Path Resolution Clarification

**Decision:** Explicitly state that agent menu `exec` paths are relative to agent.md location

**Rationale:**
- Judge feedback: "Should be explicitly stated or use absolute path pattern"
- Prevents confusion during implementation
- Documents the convention for future mode additions

**Implementation:** The `exec` attribute uses paths relative to the agent.md file's directory (`_rbtv/work/doc/`). When the agent executes `exec="./compound/workflow.md"`, it resolves to `_rbtv/work/doc/compound/workflow.md`.

---

### D11: Menu Options Vary Per Step

**Decision:** Document that menu options are step-specific, not uniform across all steps

**Rationale:**
- Judge feedback: "Menu options are different per step, which is fine, but you need to specify this pattern explicitly"
- Different steps have different user needs

**Menu Variations:**
- Step-01 and step-02: Continue/AE/Exit
- Step-03: Continue/Revise Assessment/Exit (different middle option)
- Step-04: New Compound/Dismiss Agent (completion menu)

---

### D12: Thin Loader Zero-Logic Boundary

**Decision:** Command file contains only LOAD, READ, FOLLOW, DISPLAY, PRESENT, WAIT. Argument parsing and mode routing live entirely in the agent.

**Rationale:**
- Follows atomic-files: no logic in thin loader
- Aligns with ide-command-template (6-step agent activation)
- Agent's activation step 3 handles mode check; command file does not

**Implementation:** Command file steps 1–6 match the template. No "PASS mode argument" step in the command file—invocation text is in conversation context; agent reads it.

---

## Evolution of Thinking

**Key Pivot:** Master orchestrator changed from workflow.md to full BMAD agent during Phase 2 based on user feedback emphasizing need for consistent character and menu-driven UX.

---

## Critical Lessons

1. **Agent vs. workflow is a UX decision:** Complex orchestration benefits from agent persona and menu structure
2. **Frontmatter schemas need separation:** Step files and output documents have different purposes
3. **Error handling is not optional:** Production-ready PRDs must specify error behaviors, not just happy paths
4. **Implementability requires instruction format:** Show HOW instructions are structured inside files
5. **State management needs single source of truth:** Workflow state belongs in output document frontmatter

---

## PRD Sections Delivered

| Section | Lines | Phase | Status |
|---------|-------|-------|--------|
| Overview | ~30 | P1 | Complete |
| Architecture | ~200 | P2 | Complete |
| Modes | ~140 | P2 | Complete |
| Workflows | ~335 | P2 | Complete |
| Components | ~450 | P2 | Complete |
| Step File Frontmatter Schema | ~40 | P2 | Complete |
| Output Document Frontmatter Schema | ~45 | P2 | Complete |
| Step File Instruction Format | ~85 | P2 | Complete |
| Error Handling Specifications | ~60 | P2 | Complete |
| Entry Point Specification | ~90 | P3 | Complete |
| References | ~30 | All | Complete |

**Total PRD Lines:** 2544

---

## Files Modified During Plan Execution

| File | Purpose | Status |
|------|---------|--------|
| `.cursor/plans/plan_prd_creation/context.md` | All shaping decisions and context | Complete |
| `robotville/docs/to_dos/doc-component-v2/doc_component_prd.md` | Complete PRD specification | Complete |
| `.cursor/plans/plan_prd_creation/p2-1-execution-decisions.md` | Phase 2 Task 1 decisions (Modes) | Complete |
| `.cursor/plans/plan_prd_creation/p2-2-execution-decisions.md` | Phase 2 Task 2 decisions (Workflows) | Complete |
| `.cursor/plans/plan_prd_creation/p2-3-execution-decisions.md` | Phase 2 Task 3 decisions (Components) | Complete |
| `.cursor/plans/plan_prd_creation/p2-execution-decisions.md` | Phase 2 consolidated decisions | Complete |
| `.cursor/plans/plan_prd_creation/p3-3-execution-decisions.md` | Phase 3 Task 3 decisions (Entry Point) | Complete |
| `.cursor/plans/plan_prd_creation/execution_decisions.md` | **This file** — Plan-level consolidated decisions | Complete |

---

## Traceability

**Phase Execution:**
- Phase 1: Foundation (context document, architecture definition) — Completed
- Phase 2: PRD Core Sections (modes, workflows, components) — Completed
- Phase 3: PRD Details (step-files, templates, entry point) — Completed
- Phase 4: Finalize (review, validation, condensation) — Completed

**Individual Task Decisions:**
- p2-1: 10 decisions → Consolidated into A1, B1-B5
- p2-2: 10 decisions → Consolidated into A2-A3, C1-C5
- p2-3: 12 decisions → Consolidated into D1-D11
- p3-3: 5 decisions → Consolidated into D12

**Total Decisions:** 37 individual decisions condensed into 26 thematic decisions (A1-A4, B1-B5, C1-C5, D1-D12)

---

## References

| Document | Path | Purpose |
|----------|------|---------|
| Context Document | `.cursor/plans/plan_prd_creation/context.md` | All shaping decisions |
| Final PRD | `robotville/docs/to_dos/doc-component-v2/doc_component_prd.md` | Complete specification |
| Phase 2 Decisions | `.cursor/plans/plan_prd_creation/p2-execution-decisions.md` | Core architecture decisions |
| Atomic Files Rule | `robotville/.cursor/rules/documentation/atomic-files.mdc` | Documentation standards |

---

*Last updated: 2026-02-03*
