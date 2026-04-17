# PRD: Creative Design Agent — Visual Work Across RBTV Workflows

## Status: Proposed
## Priority: High
## Scope: All visual/design work currently handled by non-design agents
## Description: Create a dedicated design agent that owns visual identity work across the system — pitch deck generation, brand visual guidelines, and any future visual design steps

---

## Problem

Multiple RBTV workflows assign visual design work to agents whose core competency is something else:

**Pitch decks (Roelof/Leo):** HTML deck generation (step 07) and image prompt creation (step 08) are handled by agents optimized for narrative stress-testing. Roelof thinks like a VC partner. Leo thinks like a procurement VP. Neither is optimized for design craftsmanship, visual hierarchy, or CSS/HTML pattern application. The Tecer investor deck design review surfaced 34 issues — the majority were visual design failures, not narrative failures.

**M3 Brand (Paul):** The Brandbook framework (step-03-visual) requires color palette creation, typography selection, logo AI prompt crafting, imagery guidelines, and iconography — all guided by Paul, a YC Mentor whose persona is "Former founder with 2 exits, obsessed with customer obsession." His principles are "Talk to customers. Build. Repeat." Zero mention of creative or visual work. During the Ayutan M3 brandbook, the founder had to take color proposals to external AI agents to get better options, validating the mismatch.

**Root cause:** The system has no creative/design agent. All visual work is assigned to the nearest available agent by workflow proximity, not by competency.

**Two failure modes:**

1. **Design quality gap**: Strategy agents treat visual work as "translate decisions to output" rather than "design with visual intent." Design constraints are followed mechanically rather than with design sensitivity.

2. **Agent overload**: Agents maintain deep narrative/strategic context across many steps, then switch to an entirely different skill domain (design). This context switch degrades both roles.

---

## Diagnostic Evidence

### Error Type

Architecture gap — the system has no creative agent and routes all milestones through a single business mentor (Paul) or narrative stress-testers (Roelof/Leo).

### Observed Failures

**M3 Brand (Ayutan):**
- Expected: Visual identity work guided by an agent with creative sensitivity, design craft awareness, and platform-specific image generation expertise.
- Actual: Paul applied business-strategic thinking to visual decisions. Color proposals were functional but needed external validation. Typography and logo direction lacked the creative depth a design-focused agent would provide.
- The founder felt the need to seek external AI agents for color palette validation — confirming the mismatch is user-visible, not just theoretical.
- M3 workflow role reinforcement says "YC mentor" at every step, compounding the mismatch for visual work.

**Pitch Decks (Tecer):**
- The Tecer investor deck design review surfaced 34 issues — the majority were visual design failures, not narrative failures.

### File-Level Mismatch Audit

| File | Issue |
|------|-------|
| `agents/paul.md` | Persona is entirely business/startup. No creative or visual scope defined. |
| `workflows/bi-business-innovation/workflow.md` | Routes ALL milestones through Paul. No per-milestone agent selection mechanism. |
| `workflows/bi-business-innovation/bi-m3/workflow.md` | Role reinforcement: "YC mentor guiding the founder through brand frameworks." Correct for strategy, wrong for visual design. |
| `workflows/bi-business-innovation/bi-m3/bi-m3-brandbook/workflow.md` | Same "YC mentor" framing for a step that needs a designer. |
| `workflows/bi-business-innovation/bi-m3/bi-m3-brandbook/steps-c/step-03-visual.md` | Requires AI image prompt crafting, visual art direction, platform-specific knowledge — none align with Paul's defined strengths. |

### Agent Roster Gap

Current agents: ana, domcobb, fernando, leo, paul, roelof. No creative/design agent exists.

---

## Current Architecture

### Pitch Creation Workflows

Both workflows follow the same 9-step create flow:

| Step | Purpose | Domain | Current Agent |
|------|---------|--------|---------------|
| 01 | Project detection, output path | Setup | Roelof/Leo |
| 02 | Extract pitch content, build brief | Narrative | Roelof/Leo |
| 03 | Draft slide-by-slide narrative | Narrative | Roelof/Leo |
| 04 | Identify validating data, thesis/counter-thesis | Narrative | Roelof/Leo |
| 05 | Generate research prompts | Narrative | Roelof/Leo |
| 06 | Plan slide structure, layout types | Narrative → Design bridge | Roelof/Leo |
| 07 | Generate full HTML deck | **Design** | Roelof/Leo |
| 08 | Brand asset integration, image prompts | **Design** | Roelof/Leo |
| 09 | Quality checks, deliverable summary | Synthesis | Roelof/Leo |

### M3 Brand — Brandbook Workflow

| Step | Purpose | Domain | Current Agent |
|------|---------|--------|---------------|
| 01 | Init, verify prerequisites, AI tool selection | Setup | Paul |
| 02 | Compile Brand Identity from frameworks | Strategy | Paul |
| 03 | Color palette, typography, logo, imagery, icons | **Design** | Paul |
| 04 | Messaging & Tone compilation, tagline | Strategy | Paul |
| 05 | Synthesis, validate consistency | Synthesis | Paul |

### Other M3 Brand Frameworks

M3 frameworks 1-6 (Archetypes, Prism, Golden Circle, Positioning, Messaging Architecture, Tone of Voice) are brand strategy work where Paul's challenger persona adds genuine value. The mismatch is isolated to the Brandbook visual identity step.

---

## Proposed Solution

### 1. New Creative Design Agent

Create a single RBTV agent that owns all visual/design work across the system. This agent:

- Has a persona optimized for design craftsmanship, visual hierarchy, brand systems, and color theory
- Handles pitch deck HTML generation (currently Roelof/Leo steps 07-08)
- Handles M3 Brandbook visual identity (currently Paul step 03)
- Loads design-specific knowledge: `html-patterns.md`, `html-components.md`, prompting knowledge for AI image tools
- Takes structure/strategy documents as input (the strategy agent's output IS the handoff)
- Is NOT Roelof, NOT Leo, NOT Paul — a distinct agent with design-first identity

**Persona direction:** A designer who has internalized Tufte's principles for presentations AND understands brand systems (color theory, typography pairing, logo design principles, visual hierarchy). Thinks visually — considers how every element communicates. Treats the brand frameworks as constraints to design within, not content to translate. Precision design craftsman, not a generic "creative."

**Key capability areas:**
- Pitch deck visual design (HTML/CSS, print-to-PDF constraints, slide composition)
- Brand visual identity (color palette, typography, logo direction, imagery guidelines)
- AI image prompt crafting (platform-specific optimization — Nano Banana, Midjourney, DALL-E)
- Design critique and iteration (can articulate why something works or doesn't)

### 2. Split Boundaries

**Pitch decks:** Narrative agent (Roelof/Leo) owns steps 01-06. Design agent owns steps 07-08.
- Step 06 (Structure) decides WHAT goes on each slide — narrative decision
- Step 07 (Generate HTML) decides HOW it looks — design decision
- The structure document is the handoff artifact

**M3 Brandbook:** Paul owns steps 01-02 and 04. Design agent owns step 03.
- Steps 01-02 (Init, Brand Identity) are strategy compilation — Paul's domain
- Step 03 (Visual Guidelines) is design — design agent's domain
- Step 04 (Messaging & Tone) is verbal identity compilation — Paul's domain
- Step 05 (Synthesis) validates both — open question on ownership

**Future:** Any workflow that adds visual/design steps should route to this agent.

### 3. Evaluate Merging Pitch Workflows

The two pitch creation workflows are structurally near-identical. All differences can be handled by:

1. A `pitch_type` variable (`investor` | `client`) set at init
2. Conditional blocks within step files
3. The invoking agent's persona providing the right lens

**Recommendation:** Merge into a single `pitch-creation` workflow with parameterized steps. This is independent from the agent split and can be done first.

### 4. Handoff Mechanism

**Pitch decks — same-session handoff (recommended):**
Step 06 ends with the exact command to invoke the design agent. The design agent reads the structure document + pitch brief from disk. No explicit handoff document needed.

**M3 Brandbook — mid-workflow agent switch:**
Two options:
- **Option A (recommended):** Step 02 completion triggers an instruction to invoke the design agent for step 03. After step 03, instruction to return to Paul for step 04.
- **Option B:** Refactor the Brandbook workflow so visual steps are a sub-workflow the design agent runs independently, with output written to the brandbook document.

Option A is simpler and consistent with the pitch deck pattern.

---

## Implementation Scope

### In Scope

1. Create the new design agent (persona, menu, activation) in `_bmad/rbtv/agents/`
2. Create loader (command + skill + cursor sub-agent) for the design agent
3. Refactor pitch step 07 and step 08 to be invoked by the design agent
4. Refactor M3 Brandbook step 03 to be invoked by the design agent
5. Evaluate and implement pitch workflow merge (single `pitch-creation` directory)
6. Update Roelof, Leo, and Paul agent menus to reflect the split
7. Update workflow.md files, routing tables, and knowledge file references
8. Add handoff instructions at split boundaries (step 06 for pitches, step 02 for brandbook)

### Out of Scope

- **Pitch edit mode (E01/E02):** Not touched. A future PRD should address design-edit.
- **Pitch step 09 (Synthesis) ownership:** Deferred until design agent is tested.
- **M3 strategy frameworks (1-6):** Stay with Paul. No change.
- **Design validation skill integration:** Could be invoked by design agent, but is a separate enhancement.
- **M3 Brandbook step 05 (Synthesis) ownership:** Deferred.

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Context loss at handoff | Design agent doesn't understand narrative/strategic intent | Structure document (pitch) and Brand Identity section (brandbook) must carry sufficient context |
| Pitch workflow merge breaks edge cases | Client-specific or investor-specific logic gets lost | Audit every conditional branch before merging |
| Agent persona too broad | One agent covering pitch design + brand identity may lack depth in either | Design persona around visual principles that apply to both; load domain-specific knowledge per workflow |
| Over-splitting | Three agents for one workflow adds coordination overhead | Monitor friction in practice |
| Mid-workflow agent switching UX | Founder must switch agents mid-brandbook | Clear handoff instructions with exact commands |

---

## Open Challenges

1. **Step 06 may need a design review pass.** Layout type selection in pitch structure is partly a design decision. Consider a "design review of structure" sub-step at the beginning of step 07.

2. **Workflow merge is higher-leverage than the agent split.** Every pitch improvement currently must be applied twice. The merge eliminates this regardless of the agent split. Consider implementing the merge first.

3. **Same-session handoff creates user friction.** Step completion should output the exact command to invoke the design agent, reducing handoff to a copy-paste.

4. **M3 Brandbook has a round-trip handoff.** Unlike pitch decks (one-way narrative → design), the brandbook goes Paul → Design Agent → Paul. This is more complex and may require the design agent to write directly to the brandbook document rather than producing a separate artifact.

5. **Agent persona breadth vs depth.** Pitch deck design (HTML/CSS, slide composition, data visualization) and brand identity design (color theory, typography, logo, imagery) are related but distinct skill sets. The persona must be crafted to cover both without being generic. Consider organizing the agent around visual communication principles that apply universally, with domain-specific knowledge loaded per workflow.

6. **Orchestrator agent for multi-agent workflows.** With agent splits, workflows like pitch creation (Roelof → Designer) and M3 Brand (Paul → Designer → Paul) become multi-agent sequences. Currently the user must manually invoke each agent at handoff points. A lightweight orchestrator agent — with no personality, no domain expertise, purely a router — could manage these transitions automatically. The orchestrator would read workflow state, determine the next agent, output the invocation command, and track progress across agent boundaries. This is especially relevant for the M3 round-trip pattern (Paul → Designer → Paul) where the user would otherwise need to switch agents twice. Consider whether this orchestrator is a new agent, an extension of the existing command/workflow system, or a capability added to the `bi-business-innovation` workflow itself.

---

## Success Criteria

1. A new design-focused agent exists in `_bmad/rbtv/agents/` with a persona covering both pitch deck and brand visual work
2. Pitch steps 07-08 are executed by the design agent, not by Roelof/Leo
3. M3 Brandbook step 03 is executed by the design agent, not by Paul
4. Narrative/strategy agents run only their competency steps, and their menus reflect this
5. Design quality improves measurably (fewer design review issues in pitch decks; founder doesn't need external validation for brand colors)
6. Handoff mechanism works smoothly for both one-way (pitch) and round-trip (brandbook) patterns
7. If merged: a single `pitch-creation` workflow directory replaces both pitch workflows, parameterized by `pitch_type`

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/agents/paul.md` | M3 Brand strategy agent — keeps frameworks 1-6, loses Brandbook visual step |
| `_bmad/rbtv/agents/roelof.md` | Investor pitch narrative agent — keeps steps 01-06, loses 07-08 |
| `_bmad/rbtv/agents/leo.md` | Client pitch narrative agent — keeps steps 01-06, loses 07-08 |
| `_bmad/rbtv/workflows/bi-business-innovation/bi-m3/bi-m3-brandbook/steps-c/step-03-visual.md` | Visual Guidelines step — moves to design agent |
| `_bmad/rbtv/workflows/bi-business-innovation/bi-m3/workflow.md` | M3 milestone workflow — needs routing update |
| `_bmad/rbtv/workflows/_shared/pitch-data/html-patterns.md` | Design knowledge — loaded by design agent |
| `_bmad/rbtv/workflows/prompting-assistance/data/knowledge-index.csv` | AI image model knowledge — loaded by design agent for brandbook |

---

## Merge History

This PRD merges two previously separate documents:
- Original pitch design agent split PRD (`prd-pitch-design-agent-split.md`)
- M3 Brand creative agent compound (`prd-m3-brand-creative-agent.md`) — now deleted; diagnostic evidence (error analysis, file-level mismatch audit, context source evaluation) integrated into the "Diagnostic Evidence" section above
