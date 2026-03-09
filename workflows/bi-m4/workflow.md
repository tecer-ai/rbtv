---
name: 'bi-m4-prototypation'
description: 'Transform validated concepts into working HTML prototypes through user flow mapping, design creation, and usability testing'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-business-innovation/workflow.md
outputFolder: '{bmad_output}/{project-name}/founder/m4-prototypation'
---

# M4 Prototypation Milestone Workflow

**Goal:** Build working HTML prototypes that communicate the product vision, test user comprehension, and enable early feedback from friends & family testing before market validation in M5.

**Your Role:** YC mentor guiding the founder through prototypation. Push for conversion-focused design, challenge decorative choices, demand usability validation. Prototypes that don't communicate value clearly are worthless.

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
| Create | Run prototypation frameworks | steps-c/step-01-init.md | Framework documents, HTML prototypes |
| Continue | Resume from last framework | steps-c/step-01-init.md (auto-detects) | Updated outputs |

---

## FRAMEWORK ROUTING

| Code | Framework | Workflow | Output | Status |
|------|-----------|----------|--------|--------|
| [U] | User Flow & IA | ../bi-m4-user-flow-ia/workflow.md | user-flow-ia.md | ✅ Available |
| [D] | Design Direction | ../bi-m4-design-context/workflow.md | design_brief.md + design.json (via bridge) | ✅ Available |
| [B] | Build Prototype | *(to be created)* | HTML/CSS prototype | 🚧 Planned |
| [C] | Conversion Optimization | ../bi-m4-conversion-centered-design/workflow.md | conversion-optimization.md | ✅ Available |
| [H] | Heuristic Evaluation | ../bi-m4-heuristic-evaluation/workflow.md | heuristic-evaluation.md | ✅ Available |
| [F] | Testing Prep | *(to be created)* | testing-protocol.md | 🚧 Planned |

### BMAD Integration Note

**[D] Design Direction** routes via **bi-m4-design-context** (bridge):

- **Path:** `../bi-m4-design-context/workflow.md`
- When user selects [D], load the bridge workflow. The bridge prepares M1–M3 and User Flow & IA context, then invokes BMAD create-ux-design (`{bmad_bmm}/workflows/2-plan-workflows/create-ux-design/workflow.md`) with that context.
- Return to M4 milestone menu after the bridge completes.

### Navigation

| Code | Action |
|------|--------|
| [S] | Show framework completion status |
| [B] | Back to milestone selection (bi-business-innovation) |

---

## RECOMMENDED SEQUENCE

1. **User Flow & IA** [U] — Map conversion paths and content hierarchy *(available)*
2. **Design Direction** [D] — Create visual direction via BMAD (design discovery via visual-design-extraction, playwright-browser-automation; optionally design-validation) *(available)*
3. **Build Prototype** [B] — Implement HTML prototype *(to be created)*
4. **Conversion Optimization** [C] — Apply conversion-centered design principles *(available)*
5. **Heuristic Evaluation** [H] — Evaluate usability against Nielsen's heuristics *(available)*
6. **Testing Prep** [F] — Prepare F&F testing protocol *(to be created)*

---

## SUCCESS CRITERIA

Prototypation milestone is complete when:

1. User flow map exists with entry points, screens, decisions, and conversion goal *(framework available: [U])*
2. Information architecture defines content hierarchy and section structure *(framework available: [U])*
3. Design brief and design specs exist (via BMAD create-ux-design) *(bridge available: [D])*
4. HTML prototype is functional with all sections implemented *(framework to be created: [B])*
5. Prototype passes WCAG AA accessibility (contrast, keyboard nav, alt text, headings) *(framework to be created: [B])*
6. Prototype is responsive at 375px, 768px, and 1200px+ *(framework to be created: [B])*
7. Heuristic evaluation completed with Critical/Major issues resolved *(framework available: [H])*
8. F&F test protocol prepared with clear objectives and 5-10 testers identified *(framework to be created: [F])*
9. Project-memo Progress > Prototypation section updated *(all frameworks)*
10. Founder can articulate: What action do we want users to take? Does the prototype communicate our value clearly? *(all frameworks)*

**Current State:** [U] User Flow & IA, [D] Design Direction bridge, [C] Conversion Optimization, and [H] Heuristic Evaluation are available. Frameworks [B], [F] are planned for future creation.

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/milestone-overview.md | Framework dependencies, recommended execution order, success criteria | step-01-init.md |

**Note:** Framework-specific knowledge files exist in individual framework workflows (bi-m4-user-flow-ia, bi-m4-conversion-centered-design, bi-m4-heuristic-evaluation). Frameworks [B] Build Prototype and [F] Testing Prep are planned for future creation.
