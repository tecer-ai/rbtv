# PRD: Split Pitch Workflow Design Steps into Dedicated Design Agent

## Status: Proposed
## Priority: Medium
## Scope: Creation mode only — edit mode (E01/E02) is explicitly out of scope
## Description: Extract HTML generation and image steps from both pitch workflows into a new design-focused agent, and evaluate merging both workflows into a single parameterized flow

---

## Problem

Both pitch creation workflows (investor via Roelof, client via Leo) assign HTML deck generation (step 07) and image prompt creation (step 08) to agents whose core competency is narrative stress-testing — not visual design. Roelof thinks like a VC partner evaluating deal quality. Leo thinks like a procurement VP evaluating vendor credibility. Neither persona is optimized for design craftsmanship, visual hierarchy, brand consistency, or CSS/HTML pattern application.

This mismatch produces two failure modes:

1. **Design quality gap**: The narrative agent treats step 07 as "translate structure to HTML" rather than "design a visually compelling presentation." Design constraints (min font sizes, optical centering, card density limits) are followed mechanically rather than with design intent. The recent design review of the Tecer investor deck surfaced 34 issues — the majority were visual design failures, not narrative failures.

2. **Agent overload**: Roelof/Leo maintain narrative context across 6 steps (01–06), then switch to an entirely different skill domain (design) for steps 07–08. This context switch degrades both roles — the design steps don't benefit from the narrative persona, and the narrative context accumulated in steps 01–06 is wasted on CSS generation.

---

## Current Architecture

Both workflows follow the same 9-step create flow:

| Step | File | Purpose | Domain |
|------|------|---------|--------|
| 01 | step-01-init.md | Project detection, output path, pitch context | Setup |
| 02 | step-02-context-gather.md | Extract pitch content from founder docs, build pitch brief | Narrative |
| 03 | step-03-narrative.md | Draft slide-by-slide narrative with stress-testing | Narrative |
| 04 | step-04-data-layer.md | Identify validating data, build thesis/counter-thesis | Narrative |
| 05 | step-05-research-prompt.md | Generate research prompts for external AI | Narrative |
| 06 | step-06-structure.md | Plan slide structure, layout types, focal elements | Narrative → Design bridge |
| 07 | step-07-generate.md | Generate full HTML deck (colors, typography, layout) | **Design** |
| 08 | step-08-images.md | Brand asset integration, image slots, image prompts | **Design** |
| 09 | step-09-synthesis.md | Quality checks, deliverable summary, next steps | Synthesis |

**Agents:** Roelof runs investor workflow. Leo runs client workflow. Both handle all 9 steps.

**Key observation:** The two workflows use nearly identical step files. Differences are driven by agent persona lens, not by structural divergence in the steps themselves.

---

## Proposed Solution

### 1. New Design Agent

Create a new RBTV agent dedicated to pitch deck visual design. This agent:

- Has a persona optimized for design craftsmanship, visual hierarchy, and brand systems
- Loads `html-patterns.md` and `html-components.md` as core knowledge
- Takes the structure document (step 06 output) as input
- Produces the HTML deck (step 07) and image prompts (step 08)
- Is NOT Roelof, NOT Leo — a distinct agent with design-first identity

**Persona direction:** Think presentation designer who has internalized Tufte's principles, understands print-to-PDF constraints, and treats every pixel as communication. Not a generic "creative" — a precision design craftsman.

### 2. Split Boundary: After Step 06

The narrative agent (Roelof or Leo) owns steps 01–06. The design agent owns steps 07–08.

**Why this boundary:**

- Step 06 (Structure) decides WHAT goes on each slide — this is a narrative decision. The agent who stress-tested the story should decide slide order, focal elements, and content mapping.
- Step 07 (Generate HTML) decides HOW it looks — this is where design begins.
- Step 06 produces a structure document that serves as the handoff artifact between narrative and design agents.

**Step 09 (Synthesis)** is an open question. Options:
- Keep with narrative agent (checks narrative fidelity)
- Move to design agent (checks visual quality)
- Split into two sub-steps (narrative check + design check)

Recommend deferring this decision until the design agent is built and tested.

### 3. Evaluate Merging Both Workflows

The two pitch creation workflows are structurally near-identical. Documented differences:

| Step | Investor (Roelof) | Client (Leo) | Structural difference? |
|------|-------------------|--------------|----------------------|
| 01 | Same | Same | No |
| 02 | Same | Same | No |
| 03 | VC stress-test | Buyer stress-test | Agent persona only |
| 04 | TAM/SAM/SOM, unit economics | ROI, proof points, case studies | Agent persona + data focus |
| 05 | Counter-thesis research | Objection research | Agent persona only |
| 06 | 12–15 slides | 10–12 slides, proof earlier | Minor parameterization |
| 07 | Standard palette | Conservative palette, trust-focused | One-line config difference |
| 08 | Brand integration + visual enhancement | Audit + image prompts (simpler) | Minor flow difference |
| 09 | Same | Same | No |

**Assessment:** No step file has structural differences that justify maintaining two separate workflow directories. All differences can be handled by:

1. A `pitch_type` variable (`investor` | `client`) set at init and available to all steps
2. Conditional blocks within step files (e.g., "if investor: 12–15 slides; if client: 10–12 slides")
3. The invoking agent's persona naturally providing the right lens (Roelof thinks VC, Leo thinks buyer)

**Recommendation:** Merge into a single `pitch-creation` workflow with parameterized steps. This eliminates the current duplication and ensures improvements (like the html-patterns.md update) propagate to both flows without double-editing.

### 4. Handoff Mechanism

The split between narrative agent and design agent requires a handoff. Two options:

**Option A — Same chat session (recommended):**
Step 06 ends with a menu that includes an instruction to invoke the design agent. The user runs the design agent command in the same or new chat, and the design agent reads the structure document + pitch brief from disk. No explicit handoff document needed — the structure document IS the handoff.

**Option B — Explicit handoff document:**
Step 06 produces a design brief document with visual direction, brand tokens, slide-by-slide layout specs. The design agent loads this document at step 07 init.

Option A is simpler and consistent with how BMAD workflows already operate. Option B adds overhead but is more resilient to context loss across sessions.

---

## Implementation Scope

### In Scope (Creation Mode)

1. Create the new design agent (persona, menu, activation)
2. Create a thin loader (command + skill + cursor sub-agent) for the design agent
3. Refactor step 07 and step 08 to be invoked by the design agent instead of narrative agents
4. Evaluate and implement workflow merge (single `pitch-creation` directory)
5. Update Roelof and Leo agent menus to reflect the split (steps 01–06 only)
6. Update workflow.md file tables and knowledge file references

### Out of Scope

- **Edit mode (E01/E02):** Not touched. Edit steps remain with Roelof/Leo as-is. A future PRD should address splitting edit mode into content-edit vs design-edit.
- **Step 09 (Synthesis) ownership:** Deferred until design agent is tested. Currently stays with narrative agent.
- **Design validation skill integration:** The existing `design-validation` skill could be invoked by the design agent at step 07, but this integration is a separate enhancement.

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Context loss at handoff | Design agent doesn't understand narrative intent | Structure document from step 06 must carry sufficient context (slide purposes, focal elements, narrative beats) |
| Workflow merge breaks edge cases | Client-specific or investor-specific logic gets lost | Audit every conditional branch before merging; maintain test coverage for both pitch types |
| New agent persona quality | Design agent is generic rather than design-specific | Invest in persona design — use design-domain metaphors, specific beliefs about visual communication |
| Over-splitting | Three agents for one workflow adds coordination overhead | Monitor friction in practice; merge design agent back if overhead > benefit |

---

## Open Challenges (Review During Implementation)

1. **Step 06 may need a design agent review pass.** Structure is assigned entirely to the narrative agent, but layout type selection (grid-2 vs grid-3, stat blocks vs cards) is a design decision. The design agent may want to revise layout choices from step 06 at the start of step 07. Consider adding a "design review of structure" sub-step at the beginning of step 07.

2. **Workflow merge is higher-leverage than the agent split.** Every improvement to step files currently must be applied twice. The merge eliminates this maintenance burden regardless of whether the design agent split happens. Consider implementing the merge first, then the agent split — they are independent changes.

3. **Same-session handoff creates user friction.** The "same chat session" handoff relies on the user manually switching agents. Step 06's completion should automatically output the exact command to invoke the design agent (e.g., "Run `/bmad-rbtv-pitch-design` to continue with deck generation"), reducing the handoff to a copy-paste rather than requiring the user to know which command to run.

---

## Success Criteria

1. A new design-focused agent exists in `_bmad/rbtv/agents/` with a design-specific persona
2. Step 07 (Generate HTML) and step 08 (Images) are executed by the design agent, not by Roelof/Leo
3. The narrative agents (Roelof, Leo) run steps 01–06 only, and their menus reflect this
4. Design quality of generated decks improves measurably (fewer design review issues)
5. If merged: a single `pitch-creation` workflow directory replaces both `investor-pitch-creation` and `client-pitch-creation`, parameterized by `pitch_type`
6. Both pitch types (investor and client) produce correct output after the refactor
