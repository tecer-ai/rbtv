# M4 Prototypation Milestone Overview

## Purpose

M4 Prototypation transforms validated concepts (M1-M3) into working HTML prototypes that communicate product vision, test user comprehension, and enable early feedback before market validation in M5. At the end of M4, the founder should have: user flow map, design direction, functional HTML prototype, conversion optimization analysis, heuristic evaluation, and F&F testing protocol.

---

## Framework Sequence and Dependencies

### Recommended Execution Order

The frameworks should be completed in this order for optimal learning flow:

1. **User Flow & IA** [U] — Foundation framework (conversion paths + content hierarchy)
2. **Design Direction** [D] — Visual design via BMAD create-ux-design bridge
3. **Build Prototype** [B] — HTML implementation (planned for future creation)
4. **Conversion Optimization** [C] — Apply conversion-centered design principles
5. **Heuristic Evaluation** [H] — Usability evaluation against Nielsen's heuristics
6. **Testing Prep** [F] — F&F testing protocol (planned for future creation)

### Foundation Framework

**User Flow & IA** [U] — Start here. Maps conversion paths and content hierarchy.
- Prerequisites: None (but M1-M3 outputs inform the work)
- Recommended Order: 1st
- Output: user-flow-ia.md
- Feeds into: Design Direction, Build Prototype, Conversion Optimization

### BMAD Integration Framework

**Design Direction** [D] — Visual design discovery via BMAD
- Prerequisites: User Flow & IA recommended
- Recommended Order: 2nd
- Path: Routes via bi-m4-design-context bridge to BMAD create-ux-design
- Output: design_brief.md + design.json (via BMAD)
- Feeds into: Build Prototype
- Note: Uses visual-design-extraction and playwright-browser-automation skills for design discovery

### Implementation Frameworks

**Build Prototype** [B] — HTML/CSS prototype implementation
- Prerequisites: User Flow & IA, Design Direction
- Recommended Order: 3rd
- Output: HTML/CSS prototype files
- Status: 🚧 Planned (to be created)
- Feeds into: Conversion Optimization, Heuristic Evaluation

**Conversion Optimization** [C] — Apply conversion-centered design principles
- Prerequisites: User Flow & IA
- Recommended: Build Prototype complete for concrete optimization
- Recommended Order: 4th
- Output: conversion-optimization.md
- Feeds into: Testing Prep

**Heuristic Evaluation** [H] — Usability evaluation
- Prerequisites: Build Prototype recommended
- Recommended Order: 5th
- Output: heuristic-evaluation.md
- Feeds into: Testing Prep

### Final Framework

**Testing Prep** [F] — F&F testing protocol
- Prerequisites: Build Prototype, Conversion Optimization, Heuristic Evaluation recommended
- Recommended Order: 6th (final M4 framework)
- Output: testing-protocol.md
- Status: 🚧 Planned (to be created)
- Completes: M4 Prototypation milestone

---

## Execution Pattern

1. **Start with User Flow & IA** [U] — Foundation for all design work
2. **Run Design Direction** [D] — Visual design via BMAD bridge (uses M1-M3 context)
3. **Build Prototype** [B] — Implement HTML prototype (planned)
4. **Run Conversion Optimization and Heuristic Evaluation in parallel** — Can be done independently
5. **Complete Testing Prep** [F] — Final synthesis for F&F testing (planned)
6. **Return to milestone selection** — M4 complete, proceed to M5 Market Validation

---

## Success Criteria

M4 Prototypation is complete when:

1. ✅ User flow map exists with entry points, screens, decisions, and conversion goal
2. ✅ Information architecture defines content hierarchy and section structure
3. ✅ Design brief and design specs exist (via BMAD create-ux-design)
4. ✅ HTML prototype is functional with all sections implemented (planned)
5. ✅ Prototype passes WCAG AA accessibility (contrast, keyboard nav, alt text, headings) (planned)
6. ✅ Prototype is responsive at 375px, 768px, and 1200px+ (planned)
7. ✅ Conversion optimization analysis completed with hypothesis-driven improvements
8. ✅ Heuristic evaluation completed with Critical/Major issues resolved
9. ✅ F&F test protocol prepared with clear objectives and 5-10 testers identified (planned)
10. ✅ Project-memo Progress > Prototypation section updated with all framework syntheses
11. ✅ Founder can articulate: What action do we want users to take? Does the prototype communicate our value clearly?

**Current State:** [U] User Flow & IA, [D] Design Direction bridge, [C] Conversion Optimization, and [H] Heuristic Evaluation are available. Frameworks [B] Build Prototype and [F] Testing Prep are planned for future creation.

---

## Framework Routing Codes

| Code | Framework | Workflow Path | Status |
|------|-----------|---------------|--------|
| [U] | User Flow & IA | ../bi-m4-user-flow-ia/workflow.md | ✅ Available |
| [D] | Design Direction | ../bi-m4-design-context/workflow.md (bridge to BMAD) | ✅ Available |
| [B] | Build Prototype | *(to be created)* | 🚧 Planned |
| [C] | Conversion Optimization | ../bi-m4-conversion-centered-design/workflow.md | ✅ Available |
| [H] | Heuristic Evaluation | ../bi-m4-heuristic-evaluation/workflow.md | ✅ Available |
| [F] | Testing Prep | *(to be created)* | 🚧 Planned |

---

## State Tracking

All framework completion is tracked in project-memo.md frontmatter:

```yaml
stepsCompleted:
  - bi-m4-user-flow-ia
  - bi-m4-design-context
  - bi-m4-build-prototype
  - bi-m4-conversion-centered-design
  - bi-m4-heuristic-evaluation
  - bi-m4-testing-prep
```

Each framework workflow's final synthesis step adds its entry to stepsCompleted.

---

## Referral Logic

- **Milestone workflow (bi-m4):** Entry points to framework workflows (menu). User selects a framework → load that framework's workflow.
- **Framework workflow (last step):** Update project_memo (stepsCompleted, synthesis); instruct user to return to milestone menu to pick next framework or [B] Back.
- **project_memo:** Single source of truth for state (stepsCompleted, current milestone, synthesis from each framework).
- **BMAD Bridge:** Design Direction [D] routes via bi-m4-design-context bridge which prepares founder context then invokes BMAD create-ux-design. After BMAD completes, bridge updates project-memo and returns to M4 menu.
