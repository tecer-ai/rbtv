---
title: 'Compound: M3 Brand Milestone Needs a Creative Agent, Not a Business Mentor'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md']
inputDocuments: []
outputPath: '{project-root}/_bmad/rbtv/_admin/roadmap/todos'
date: '2026-03-06'
yoloMode: false
---

# M3 Brand Milestone Needs a Creative Agent, Not a Business Mentor

**Type:** Workflow / Agent Architecture
**Priority:** High
**Tracker:**
**Status:** Superseded — merged into `prd-pitch-design-agent-split.md` (now "Creative Design Agent — Visual Work Across RBTV Workflows")

---

## Overview

### Problem

Paul (YC Mentor) guides all Business Innovation milestones, including M3 Brand. His persona — "Former founder with 2 exits, YC partner, obsessed with customer obsession" — is optimized for business validation and startup thinking. M3 Brand contains two fundamentally different types of work: (a) brand strategy frameworks (Archetypes, Prism, Golden Circle, Positioning, Messaging, Tone of Voice) where a challenger mentor adds value, and (b) visual identity creation (Brandbook — color, typography, logo, imagery, iconography) where a creative/design agent is needed. The founder had to externally validate color proposals because Paul's approach was strategic rather than creatively informed.

### Goals

- M3 Brand visual identity work is guided by an agent with creative/design expertise
- Brand strategy frameworks can still benefit from a challenger/mentor perspective
- The system routes different types of work to the right agent persona
- AI image prompt crafting, color theory, typography selection, and visual art direction are handled by an agent whose persona aligns with these competencies

### Constraints

- The existing `prd-pitch-design-agent-split.md` already proposes a design agent for pitch decks — any M3 solution should be compatible with or extend that proposal
- M3 strategy frameworks (1-6) genuinely benefit from Paul's challenger persona — the fix should not remove that value
- The creative agent must still enforce brand framework consistency (traceability to Archetypes, Prism, etc.)
- Agent switching mid-milestone must be seamless for the founder

---

## Self-Assessment

### Error Analysis

**Error type:** Architecture gap — the system has no creative agent and routes all milestones through a single business mentor.

**Expectation vs. actual:**
- Expected: Visual identity work guided by an agent with creative sensitivity, design craft awareness, and platform-specific image generation expertise.
- Actual: Paul applied business-strategic thinking to visual decisions. Color proposals were functional but needed external validation. Typography and logo direction lacked the creative depth a design-focused agent would provide.

**Impact:**
- Founder felt the need to seek external AI agents for color palette validation
- Visual identity step (step-03-visual.md) requires AI image prompt crafting, visual art direction, and platform-specific knowledge — none align with Paul's defined strengths
- M3 workflow role reinforcement says "YC mentor" at every step, compounding the mismatch for visual work

### Context Source Evaluation

| File | Issue |
|------|-------|
| `_bmad/rbtv/agents/paul.md` | Persona is entirely business/startup. No creative or visual scope defined. |
| `_bmad/rbtv/workflows/bi-business-innovation/workflow.md` | Routes ALL milestones through Paul. No per-milestone agent selection mechanism. |
| `_bmad/rbtv/workflows/bi-m3/workflow.md` | Role reinforcement: "YC mentor guiding the founder through brand frameworks." Correct for strategy, wrong for visual design. |
| `_bmad/rbtv/workflows/bi-m3-brandbook/workflow.md` | Same "YC mentor" framing for a step that needs a designer. |
| `_bmad/rbtv/workflows/bi-m3-brandbook/steps-c/step-03-visual.md` | Requires AI image prompt crafting, visual art direction, platform-specific knowledge. |
| `_bmad/rbtv/_admin/roadmap/todos/prd-pitch-design-agent-split.md` | Identifies the same pattern for pitch decks (Roelof/Leo doing design work). Does NOT address M3 Brand. |

**Gap:** No creative/design agent exists in the RBTV agent roster (current agents: ana, domcobb, fernando, leo, paul, roelof).

### Improvement Options

1. **New Rule**: Agent-milestone routing rule that maps specific milestones to specialized agents (e.g., M3 visual work → creative agent, M1/M2 → Paul).
   - **Rationale:** Cleanest separation. Each agent stays in their competency zone.
   - **Location:** New rule file + update `bi-business-innovation/workflow.md` routing logic.

2. **Modify Existing Rule**: Update M3 workflow role reinforcement from "YC mentor" to a dual-role that shifts from strategic to creative at the Brandbook step.
   - **Rationale:** Minimal system change — adjust the framing, not the architecture.
   - **Location:** `bi-m3/workflow.md`, `bi-m3-brandbook/workflow.md`, and all M3 step files.

3. **Update System File**: Create a new creative agent and update M3 routing to hand off at the Brandbook framework.
   - **Rationale:** Best-fit solution. Aligns with the existing `prd-pitch-design-agent-split.md` pattern.
   - **Location:** New agent file in `agents/`, update `bi-m3/workflow.md` routing, update `bi-m3-brandbook/workflow.md`.

4. **Add Constraint**: Add scope exclusion to Paul's agent file — visual/design work is outside his competency and should be delegated.
   - **Rationale:** Prevents the problem even without a new agent. Paul would flag when entering visual territory.
   - **Location:** `agents/paul.md` rules section.

5. **Alternative Approach**: Split M3 into two sub-phases — **M3a: Brand Strategy** (Paul: frameworks 1-6) and **M3b: Brand Design** (new creative agent: Brandbook with visual identity).
   - **Rationale:** Recognizes that M3 contains two fundamentally different types of work. Strategy benefits from a challenger; visual work benefits from a creative partner.
   - **Location:** Restructure `bi-m3/workflow.md`, create new agent, update `bi-business-innovation/workflow.md`.

---

## Proposed Solution

[To be completed in Step 3]

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | [To be completed] |
| Scope of change | [To be completed] |
| Related files | [To be completed] |

---

## Rationale

[To be completed in Step 3]

---

## Acceptance Criteria

- [ ] [To be completed in Step 4]

---

## Related Files

| File | Relationship |
|------|--------------|
| [To be completed] | [To be completed] |

---

## References

[To be completed]

---

## Discussion Notes

[To be completed in Step 3]
