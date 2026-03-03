---
name: 'bi-m3-brand'
description: 'Create comprehensive brand book through 7 brand frameworks'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-business-innovation/workflow.md
outputFolder: '{project-root}/_bmad-output/{project-name}/founder/m3-brand'
---

# M3 Brand Milestone Workflow

**Goal:** Create a comprehensive brand book that defines who this brand is (archetype, personality), why it exists (purpose, positioning), how it speaks (tone, messaging), and what it looks like (visual identity) — all grounded in M1 Conception outputs and M2 Validation findings, culminating in a unified brandbook document.

**Your Role:** YC mentor guiding the founder through brand frameworks. Challenge superficial choices, demand grounding in customer evidence, push for authentic expression. This is a partnership — you bring startup expertise, they bring domain knowledge.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each framework, update `stepsCompleted` in project-memo frontmatter.

### Critical Rules

- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update project-memo after completing each framework
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Run brand frameworks | steps-c/step-01-init.md | Framework documents |
| Continue | Resume from last framework | steps-c/step-01-init.md (auto-detects) | Updated outputs |

---

## FRAMEWORK ROUTING

| Code | Framework | Workflow | Output File |
|------|-----------|----------|-------------|
| [BA] | Brand Archetypes | ../bi-m3-brand-archetypes/workflow.md | brand-archetypes.md |
| [BP] | Brand Prism | ../bi-m3-brand-prism/workflow.md | brand-prism.md |
| [GC] | Golden Circle | ../bi-m3-golden-circle/workflow.md | golden-circle.md |
| [PO] | Brand Positioning | ../bi-m3-brand-positioning/workflow.md | brand-positioning.md |
| [TV] | Tone of Voice | ../bi-m3-tone-of-voice/workflow.md | tone-of-voice.md |
| [MA] | Messaging Architecture | ../bi-m3-messaging-architecture/workflow.md | messaging-architecture.md |
| [BB] | Brandbook | ../bi-m3-brandbook/workflow.md | brandbook.md |

### Navigation

| Code | Action |
|------|--------|
| [S] | Show framework completion status |
| [B] | Back to milestone selection (bi-business-innovation) |

---

## SUCCESS CRITERIA

Brand milestone is complete when:

1. Brand Archetypes analysis exists with primary archetype selected and justified
2. Brand Prism document exists with all six facets defined and consistent
3. Golden Circle document exists with authentic Why, How, What
4. Positioning statement exists as a single sentence with competitive differentiation
5. Tone of Voice guide exists with dimensions, do/don't examples, and sample copy
6. Messaging Architecture exists with hierarchical structure and audience variants
7. Brandbook exists with visual identity (logo, colors, typography), compiled brand identity, messaging, and quick reference
8. Project-memo Progress > Brand section lists all completed frameworks
9. Founder can articulate: Who is our brand? What do we stand for? How do we sound? How are we different? What do we look like?

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/milestone-overview.md | M3 structure, framework dependencies | Step 01 |
