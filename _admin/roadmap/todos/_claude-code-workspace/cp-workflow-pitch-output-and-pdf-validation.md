---
title: 'Compound: Pitch Output Management and PDF Review Loop'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments:
  - workflows/pitch-creation/workflow.md
  - workflows/pitch-creation/steps-c/step-01-init.md
  - workflows/pitch-creation/steps-c/step-07-generate.md
  - workflows/pitch-creation/steps-c/step-09-synthesis.md
outputPath: '{project-root}/_bmad/rbtv/_admin/roadmap/todos'
date: '2026-03-13'
yoloMode: false
---

# Pitch Output Management and PDF Review Loop

**Type:** Workflow
**Priority:** High
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

The pitch creation workflow has two structural gaps:

1. **Flat output structure.** All pitch deliverables land in a single flat folder (`_fundraising/pitch-deck` or `_clients/pitch-deck`). Repeated pitch runs overwrite previous deliverables. There is no date-based organization, no target-specific separation, and no way to maintain a history of pitches across meetings or rounds.

2. **No PDF validation.** After HTML generation (step-07), the workflow performs a code-level self-check but never renders the HTML visually. PDF export is entirely manual — step-09 tells the user to open in browser, Ctrl+P, and visually verify. The Playwright MCP is configured but never used. Layout breaks at page boundaries go undetected until the user manually checks.

### Goals

1. Structured, non-destructive output folders organized by target and date, with dedicated subfolders for artifacts, assets, and research
2. Agent asks user to confirm output path before creating folders
3. Automated PDF export from the generated HTML
4. Automated visual QA loop: screenshot PDF pages, review for layout breaks, fix HTML, re-export, repeat until clean

### Constraints

- MCP tool for PDF export is not yet determined — the specification must be tool-agnostic, describing the capability needed rather than a specific MCP
- Must follow RBTV micro-file step architecture
- Must not break existing pitch workflow steps (1-9)
- Agent must always suggest the folder path; user must always approve before creation

---

## Self-Assessment

### Error Analysis

**Error type: Knowledge gap / Feature gap**

Two capabilities are missing from the pitch creation workflow:

**Gap 1 — Flat output structure.** All pitch deliverables (narrative MD, research prompt MD, HTML deck, image prompts MD) land in a single flat folder. The only subfolder created is `images/`. There is no date-based organization, no target-specific separation, and no way to distinguish between multiple pitches for different targets. Repeated pitch runs overwrite previous deliverables.

**Gap 2 — No PDF validation.** After HTML generation (step-07), the workflow performs a code-level self-check (slide count, page breaks, icons, colors) but never renders the HTML visually. PDF export is entirely manual — step-09 (synthesis) tells the user to open in browser, Ctrl+P, and visually verify. The Playwright MCP is configured in `.mcp.json` but never referenced or used in any pitch workflow step. There is no automated render → screenshot → review → fix loop.

### Context Source Evaluation

| File | Finding |
|------|---------|
| `workflows/pitch-creation/workflow.md` | Defines flat output paths per pitch type. No folder structure logic beyond `images/` |
| `workflows/pitch-creation/steps-c/step-01-init.md` | Sets output folder from config. No user prompt for custom path or target name |
| `workflows/pitch-creation/steps-c/step-07-generate.md` | HTML generation + code-level self-check only. No visual rendering or PDF conversion |
| `workflows/pitch-creation/steps-c/step-09-synthesis.md` | Manual PDF instructions given to user. No automation |
| `.claude/.mcp.json` | Playwright MCP configured but unused by any pitch step |
| `_config/config.yaml` | `bmad_output` resolves to `{project-root}/projects` — no date/target templating |

### Improvement Options

1. **New Rule**: Pitch output folder convention rule
   - **Rationale:** Standardizes folder structure across all pitch workflows so multiple pitches don't collide and assets are organized predictably
   - **Location:** New rule file `_config/.claude/rules/bmad-rbtv-pitch-output.md`
   - **Pattern Consistency:** Follows existing RBTV rule file conventions (`bmad-rbtv-*.md` naming, mandatory language, table format)

2. **Modify Existing Step**: Update step-01-init to prompt for output location and create structured folders
   - **Rationale:** Step-01 already handles output path setup — extending it is a natural fit
   - **Location:** `workflows/pitch-creation/steps-c/step-01-init.md` — modify sections 3-4
   - **Pattern Consistency:** Follows existing micro-step pattern. Step-01 is already responsible for folder setup

3. **New Step**: Add step-10 for combined PDF export + visual QA loop
   - **Rationale:** Single step keeps the tight iteration loop together (export → screenshot → review → fix → repeat)
   - **Location:** New file `steps-c/step-10-pdf-validation.md` + update `workflow.md` and step-09's `nextStepFile`
   - **Pattern Consistency:** Follows micro-file architecture. Slightly compound (export + review) but justified by the iterative nature

4. **Add Constraint**: MCP tool dependency declaration in workflow frontmatter
   - **Rationale:** New steps depend on MCP tools. Declaring dependencies upfront prevents mid-workflow failures
   - **Location:** `workflows/pitch-creation/workflow.md` frontmatter — add `requiredMCPs` field
   - **Pattern Consistency:** New pattern — no existing workflow declares MCP dependencies. Deferred as nice-to-have

5. **Alternative Approach**: Two separate steps (step-10 export + step-11 review) instead of combined
   - **Rationale:** Cleaner separation of concerns but awkward for iterative loops
   - **Location:** Two new files instead of one
   - **Pattern Consistency:** Purer architecturally but pragmatically worse for tightly coupled iteration

---

## Proposed Solution

Implement Options 1 + 2 + 3 together:

**Part A — Folder Structure (Options 1 + 2):**

Create a new rule file defining the output folder convention. Modify step-01-init to prompt the user for the output path (suggesting a default based on pitch type and target), then create the folder structure upon user approval.

**Client pitch folder structure:**
```
{bmad_output}/{project-name}/_clients/{client-name}/presentations/YYYY-MM-DD-{meeting-objective}/
├── pitch-deck.html          # final HTML pitch
├── pitch-deck.pdf           # exported PDF
├── artifacts/               # workflow markdown outputs (narrative, research prompt, image prompts)
├── assets/                  # images used in the pitch
├── research/                # research outputs specific to this presentation
└── meeting-transcript/      # meeting transcript and notes (client pitches only)
```

**Fundraising pitch folder structure:**
```
{bmad_output}/{project-name}/_fundraising/{round-or-context}/YYYY-MM-DD-{fund-name}/
├── pitch-deck.html
├── pitch-deck.pdf
├── artifacts/
├── assets/
└── research/
```

Key differences: client pitches have a `presentations/` folder between `{client-name}` and the date folder (fundraising pitches do not). Client pitches also include a `meeting-transcript/` subfolder by default (fundraising pitches do not).

The agent MUST suggest the full path. The user MUST approve before any folder is created.

**Part B — PDF Validation Loop (Option 3):**

Add a new step-10-pdf-validation.md after step-09. This step runs an iterative loop:

1. Open the generated HTML in a browser via MCP
2. Export to PDF
3. Screenshot each PDF page
4. Review screenshots for layout breaks at page boundaries
5. If issues found: fix the HTML, re-export, re-screenshot, re-review
6. Repeat until the PDF renders cleanly or the user approves

The specific MCP tool is left open — the step must describe the capability needed (browser automation with PDF export and screenshot) without locking to a specific tool. At implementation time, evaluate available MCPs.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | **Create:** `_config/.claude/rules/bmad-rbtv-pitch-output.md` (folder convention rule), `workflows/pitch-creation/steps-c/step-10-pdf-validation.md` (PDF loop step). **Modify:** `workflows/pitch-creation/steps-c/step-01-init.md` (add folder prompt + creation), `workflows/pitch-creation/workflow.md` (add step-10 to step list), `workflows/pitch-creation/steps-c/step-09-synthesis.md` (update nextStepFile to step-10) |
| Scope of change | Comprehensive — new rule, modified init step, new validation step, workflow metadata update |
| Related files | `workflows/_shared/pitch-data/html-patterns.md` (may need PDF-specific CSS guidance), `_config/.claude/.mcp.json` (MCP availability) |

---

## Rationale

The flat output structure causes data loss through overwrites and makes it impossible to maintain pitch history across multiple meetings. Date-and-target-based folders solve this while keeping a clear organizational hierarchy aligned with how business teams think (by client, by round, by meeting).

The PDF validation loop closes the last-mile quality gap. The HTML self-check catches code-level issues but misses visual rendering problems that only appear in PDF (page break collisions, element overflow, font rendering). Automating the render → review → fix cycle eliminates the manual Ctrl+P workflow and ensures the delivered PDF matches the intended design.

---

## Acceptance Criteria

- [ ] Step-01-init prompts user for output folder path with a sensible default based on pitch type (client vs fundraising) and target name
- [ ] User must explicitly approve the folder path before any directory is created
- [ ] Client pitch folders follow the structure: `_clients/{client-name}/presentations/YYYY-MM-DD-{meeting-objective}/` with `artifacts/`, `assets/`, `research/`, `meeting-transcript/` subfolders
- [ ] Fundraising pitch folders follow: `_fundraising/{round-or-context}/YYYY-MM-DD-{fund-name}/` with same subfolders (no `presentations/` middle folder)
- [ ] HTML and PDF files are saved at the root of the meeting-objective folder, not inside subfolders
- [ ] Workflow markdown outputs (narrative, research prompt, image prompts) are saved to `artifacts/`
- [ ] Images used in the pitch are saved to `assets/`
- [ ] Research outputs are saved to `research/`
- [ ] New step-10-pdf-validation executes after step-09
- [ ] Step-10 exports HTML to PDF via MCP tool
- [ ] Step-10 screenshots each PDF page and reviews for layout breaks
- [ ] Step-10 loops (fix HTML → re-export → re-review) until PDF renders cleanly or user approves
- [ ] New rule file `bmad-rbtv-pitch-output.md` documents the folder convention with mandatory language

---

## Related Files

| File | Relationship |
|------|--------------|
| `workflows/pitch-creation/workflow.md` | Workflow orchestrator — must add step-10 reference |
| `workflows/pitch-creation/steps-c/step-01-init.md` | Must be modified for folder prompt and creation |
| `workflows/pitch-creation/steps-c/step-07-generate.md` | HTML generation — step-10 depends on its output |
| `workflows/pitch-creation/steps-c/step-09-synthesis.md` | Must update nextStepFile to point to step-10 |
| `workflows/_shared/pitch-data/html-patterns.md` | May need PDF-specific CSS guidance for clean page breaks |
| `_config/.claude/.mcp.json` | MCP configuration — step-10 depends on available MCP tools |
| `_config/.claude/rules/bmad-rbtv-pitch-output.md` | New rule file to create |

---

## References

- Current pitch workflow: `workflows/pitch-creation/workflow.md`
- Playwright MCP config: `.claude/.mcp.json`
- RBTV micro-file step architecture: `workflows/doc-compound-learning/workflow.md` (reference pattern)

---

## Discussion Notes

### Selected Improvement Options

**Combined approach: Options 1 + 2 + 3 (+ Option 4 as nice-to-have)**

- Option 1 (new rule) + Option 2 (modify step-01-init) for folder structure
- Option 5 (single combined step-10) for PDF validation loop
- Option 4 (MCP dependency declaration) deferred — nice-to-have, not blocking

### Implementation Preferences

- **Scope:** Comprehensive — both improvements in one PRD
- **Priority:** High

### Folder Structure — User Decisions

- Client: `_clients/{client-name}/presentations/YYYY-MM-DD-{meeting-objective}/` with HTML+PDF at root, `artifacts/`, `assets/`, `research/`, `meeting-transcript/` subfolders
- Fundraising: `_fundraising/{round-or-context}/YYYY-MM-DD-{fund-name}/` — no `presentations/` middle folder
- Agent MUST suggest the full path; user MUST approve before folder creation
- `research/` folder stores research outputs generated during or for the pitch workflow

### PDF Validation — User Decisions

- MCP tool left open — to be determined at implementation time
- Primary failure mode to detect: layout breaks at page boundaries
- Single-step loop approach preferred over two-step split
- Loop: print PDF → screenshot → review for layout breaks → fix HTML if needed → repeat until clean
