---
title: 'Compound: Pitch Artifact Synchronization Rule'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md', 'step-03-discussion.md', 'step-04-document.md']
inputDocuments: ['_bmad/rbtv/agents/leo.md', '_bmad/rbtv/agents/roelof.md', '_bmad/rbtv/agents/vivian.md', '_bmad/rbtv/workflows/pitch/steps-e/step-e01-load.md', '_bmad/rbtv/workflows/pitch/steps-e/step-e02-edit.md', '_bmad/rbtv/workflows/pitch/steps-c/step-07-generate.md']
outputPath: '_bmad/rbtv/_admin/roadmap/todos'
date: '2026-03-17'
yoloMode: false
---

# Pitch Artifact Synchronization Rule

**Type:** Rule + System File
**Priority:** High
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

Pitch agents (Leo, Roelof, Vivian) edit the HTML deck without updating the pitch narrative or companion documents. This causes the documents to drift out of sync silently. The user must manually request discrepancy checks and direct corrections — extra work that should not exist.

Root cause: no rule, constraint, or workflow instruction tells agents that pitch artifacts are a linked unit.

### Goals

1. Any change to the HTML deck MUST also be reflected in the narrative and companion docs, in the same operation.
2. Any change to the narrative MUST also be reflected in the HTML deck, in the same operation.
3. Agents must treat HTML + narrative + companion docs as a single atomic unit.
4. Vivian must update the narrative when user-directed HTML changes alter narrative content (not just design).

### Constraints

- Must not add significant overhead to simple edits (e.g., a CSS-only fix does not require narrative changes)
- Must work across all three pitch agents and both create/edit workflow modes
- Must follow existing BMAD patterns for agent rules and workflow step instructions
- Vivian's "take narrative as INPUT" principle remains — she does not redo strategic work, but she MUST keep the narrative synchronized when HTML content changes

---

## Self-Assessment

### Error Analysis

**Error type:** Knowledge gap

The pitch agents have no rule or workflow instruction mandating cross-document synchronization. Each agent's `<rules>` section contains persona-specific guidance (challenge slides, push back on weak narratives) but nothing about document sync. The edit workflow (`step-e01-load.md`) loads only the HTML — it does not load or reference the narrative.

**Expectation vs. actual:**
- **Expected:** Agent edits HTML and narrative together as a single unit
- **Actual:** Agent edited only the HTML. Narrative was only updated when user explicitly requested it.

**Impact:** Documents drift. If the narrative is later used as source-of-truth for a future workflow step (e.g., generating a new version, handing off to another agent), it contains stale information.

### Context Source Evaluation

| File | Status | Issue |
|------|--------|-------|
| `_bmad/rbtv/agents/leo.md` | Loaded, followed | No sync rule exists |
| `_bmad/rbtv/agents/roelof.md` | Not in session | Same gap — no sync rule |
| `_bmad/rbtv/agents/vivian.md` | Not in session | Has "take narrative as INPUT" rule but no bidirectional sync |
| `_bmad/rbtv/workflows/pitch/steps-e/step-e01-load.md` | Loaded, followed | Loads HTML only. Does not load narrative. |
| `_bmad/rbtv/workflows/pitch/steps-e/step-e02-edit.md` | Not loaded | Likely same gap |
| `_bmad/rbtv/workflows/pitch/steps-c/step-07-generate.md` | Not loaded | No sync instruction after HTML generation |
| `.cursor/rules/` | Globally applied | No pitch-specific sync rules exist |

**Gap:** No file defines the relationship between HTML deck, narrative, and companion documents as a linked unit.

### Improvement Options

1. **New Rule**: Create `.cursor/rules/bmad-rbtv-pitch-sync.mdc` with glob pattern matching pitch files
   - **Rationale:** Auto-applies via glob whenever pitch files are touched
   - **Location:** `.cursor/rules/bmad-rbtv-pitch-sync.mdc`
   - **Pattern Consistency:** High — follows existing naming/glob conventions

2. **Modify Existing Rule**: Extend `atomic-files.mdc` with "linked artifact groups"
   - **Rationale:** Atomic-files already governs document relationships
   - **Location:** `.cursor/rules/bmad-rbtv-atomic-files.mdc`
   - **Pattern Consistency:** Moderate — blurs that rule's purpose

3. **Update System File**: Add sync rule to each agent's `<rules>` section ★ SELECTED
   - **Rationale:** Direct, always in context, no external dependency
   - **Location:** `_bmad/rbtv/agents/leo.md`, `roelof.md`, `vivian.md`
   - **Pattern Consistency:** High — follows existing agent rule pattern

4. **Add Constraint**: Add sync instructions to workflow steps ★ SELECTED
   - **Rationale:** Mechanically enforced during edit and create workflows
   - **Location:** `step-e01-load.md`, `step-e02-edit.md`, `step-07-generate.md`
   - **Pattern Consistency:** High — workflow steps already have step-specific rules

5. **Alternative Approach**: Per-presentation `_manifest.yaml` listing all related files
   - **Rationale:** Scales to future artifact types
   - **Location:** One manifest per presentation folder
   - **Pattern Consistency:** Low — introduces new convention with no precedent

---

## Proposed Solution

Combine Options 3 and 4: add a sync rule to all three pitch agents AND update workflow steps to mechanically enforce synchronization.

### Part A: Agent Rule Addition

Add the following rule to the `<rules>` section of `leo.md`, `roelof.md`, and `vivian.md`:

```xml
<r>Pitch artifacts (HTML deck, narrative, companion docs) are a linked unit. When editing ANY pitch artifact, ALL related documents MUST be updated in the same operation. Never edit one in isolation. Content-only changes (not CSS/styling) in the HTML MUST be reflected in the narrative, and vice versa.</r>
```

For `vivian.md` specifically, also update the existing INPUT rule:

**Current:**
```xml
<r>You take strategy and structure documents as INPUT — never redo narrative or strategic work. Design within those constraints.</r>
```

**New:**
```xml
<r>You take strategy and structure documents as INPUT — never redo narrative or strategic work. Design within those constraints. However, when user-directed HTML changes alter content that exists in the narrative, you MUST update the narrative to match.</r>
```

### Part B: Workflow Step Updates

**`step-e01-load.md`** — Add to "Read and Analyze" section (step 2):

```markdown
### 2b. Load Companion Documents

After loading the HTML, also load:
- The pitch narrative markdown (typically `artifacts/pitch-narrative.md` in the same presentation folder)
- Any companion docs (typically `artifacts/pitch-narrative-context.md`)

If companion documents are not found, ask the user for their location.

All edits in subsequent steps MUST update both the HTML and the narrative simultaneously.
```

**`step-e02-edit.md`** — Add to step-specific rules:

```markdown
### Sync Enforcement

After applying each edit to the HTML:
1. Identify whether the edit changes content (text, data, claims, structure) vs. only styling (CSS, layout, colors)
2. If content changed → update the corresponding section in the pitch narrative immediately
3. If narrative was the edit target → update the corresponding HTML section immediately
4. After all edits are complete, verify no drift remains between HTML and narrative
```

**`step-07-generate.md`** (creation workflow) — Add to step-specific rules:

```markdown
### Post-Generation Sync Check

After generating the HTML deck:
1. Compare key content (slide titles, main messages, supporting elements, data points) against the narrative produced in step-03
2. If any user-directed changes during HTML generation altered narrative content, update the narrative to match
3. Report any narrative updates made to the user
```

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `_bmad/rbtv/agents/leo.md` (add 1 rule) |
| | `_bmad/rbtv/agents/roelof.md` (add 1 rule) |
| | `_bmad/rbtv/agents/vivian.md` (add 1 rule, modify 1 rule) |
| | `_bmad/rbtv/workflows/pitch/steps-e/step-e01-load.md` (add section 2b) |
| | `_bmad/rbtv/workflows/pitch/steps-e/step-e02-edit.md` (add sync enforcement section) |
| | `_bmad/rbtv/workflows/pitch/steps-c/step-07-generate.md` (add post-generation sync check) |
| Scope of change | Comprehensive — 6 files modified, no new files created |
| Related files | All pitch presentation folders (consumers of the sync rule) |

---

## Rationale

The combined approach addresses the problem at two levels:

1. **Agent rules (Option 3)** make the obligation explicit and portable. Regardless of which workflow step is active — or if the agent is operating outside a formal workflow (e.g., ad-hoc edits) — the rule travels with the agent. This is the safety net.

2. **Workflow steps (Option 4)** provide mechanical enforcement at the points where edits actually happen. Loading the narrative alongside the HTML in `step-e01-load.md` ensures the agent has both documents in context. The sync check in `step-e02-edit.md` prevents drift after each edit. The post-generation check in `step-07-generate.md` catches divergence during creation.

Neither approach alone is sufficient: agent rules without workflow support means the agent may forget to load the narrative; workflow steps without agent rules means ad-hoc edits outside the workflow are unprotected.

---

## Acceptance Criteria

- [ ] All three pitch agents (Leo, Roelof, Vivian) have the sync rule in their `<rules>` section
- [ ] Vivian's INPUT rule is updated to clarify narrative sync obligation
- [ ] `step-e01-load.md` loads narrative and companion docs alongside the HTML
- [ ] `step-e02-edit.md` includes sync enforcement after each edit
- [ ] `step-07-generate.md` includes post-generation sync check
- [ ] During a test edit session: editing the HTML automatically triggers narrative updates without user prompting
- [ ] CSS/styling-only changes do NOT trigger unnecessary narrative updates

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/agents/leo.md` | Pitch agent — add sync rule |
| `_bmad/rbtv/agents/roelof.md` | Pitch agent — add sync rule |
| `_bmad/rbtv/agents/vivian.md` | Pitch agent — add sync rule, modify INPUT rule |
| `_bmad/rbtv/workflows/pitch/steps-e/step-e01-load.md` | Edit workflow — add narrative loading |
| `_bmad/rbtv/workflows/pitch/steps-e/step-e02-edit.md` | Edit workflow — add sync enforcement |
| `_bmad/rbtv/workflows/pitch/steps-c/step-07-generate.md` | Create workflow — add post-generation sync check |
| `_bmad/rbtv/workflows/pitch/steps-c/step-03-narrative.md` | Create workflow — produces the narrative (no changes needed) |

---

## References

- Triggering session: Leo client-pitch edit session for Tecer × ContabExpress proposal (2026-03-17)
- Pattern reference: existing agent `<rules>` sections in `_bmad/rbtv/agents/*.md`
- Pattern reference: existing step-specific rules in `_bmad/rbtv/workflows/pitch/steps-e/*.md`

---

## Discussion Notes

### Selected Improvement Option
Options 3 + 4 combined: Add sync rule to all three pitch agent `<rules>` sections AND update edit workflow steps to mechanically enforce sync.

### Implementation Preferences
- **File Location:** Agent files (`leo.md`, `roelof.md`, `vivian.md`) + workflow steps (`step-e01-load.md`, `step-e02-edit.md`) + creation step for Vivian (`step-07-generate.md`)
- **Scope:** Comprehensive — covers all three agents and both create/edit workflows
- **Priority:** High

### Additional Context
- Sync rule applies during creation workflow too, specifically for Vivian (step-07 HTML generation). User inputs during HTML generation commonly cause narrative divergence.
- Vivian's existing rule "take narrative as INPUT" is NOT a barrier to editing the narrative. Vivian must update the narrative when user-directed HTML changes alter its content. The "INPUT" rule means Vivian doesn't redo strategic/narrative work from scratch — but she must keep it synchronized.
- All three agents carry the same sync obligation: never edit one artifact in isolation.
