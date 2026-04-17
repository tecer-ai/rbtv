# Founder Process Knowledge

Master navigation for the 6-milestone business innovation lifecycle from idea to MVP.

---

## Milestones Summary

| Milestone | Goal | Key Frameworks | Workflow |
|-----------|------|----------------|----------|
| M1: Conception | Structure idea into comprehensive business concept | Working Backwards, Jobs-to-be-Done, Competitive Landscape, Problem-Solution Fit, Lean Canvas, 5 Whys | bi-business-innovation/bi-m1/workflow.md |
| M2: Validation | Validate technical and financial feasibility | Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL, Pre-mortem | bi-business-innovation/bi-m2/workflow.md |
| M3: Brand | Create comprehensive brand book | Brand Archetypes, Brand Prism, Golden Circle, Brand Positioning, Messaging Architecture, Tone of Voice, Brandbook | bi-business-innovation/bi-m3/workflow.md |
| M4: Prototypation | Build working HTML prototype for F&F testing | User Flow, Information Architecture, Design Brief, Atomic Design, Conversion Design, WCAG | bi-business-innovation/bi-m4/workflow.md |
| M5: Market Validation | Validate market demand with low spending | Mom Test, SPIN Selling, Smoke Test, Van Westendorp PSM, Bullseye, Sean Ellis PMF | bi-business-innovation/bi-m5/workflow.md |
| M6: MVP | Create minimum viable product for real clients | User Story Mapping, INVEST, MoSCoW, Scrum, CI/CD, OWASP Top 10 | bi-business-innovation/bi-m6/workflow.md |

---

## Output Folder Structure

```
{bmad_output}/{project-name}/business-innovation/
├── project-memo.md           # Cumulative summary + state tracking (frontmatter)
├── m1-conception/
│   ├── working-backwards.md
│   ├── jobs-to-be-done.md
│   ├── competitive-landscape.md
│   ├── problem-solution-fit.md
│   ├── lean-canvas.md
│   └── five-whys.md
├── m2-validation/
│   └── ...
├── m3-brand/
│   └── ...
├── m4-prototypation/
│   └── ...
├── m5-market-validation/
│   └── ...
└── m6-mvp/
    └── ...
```

---

## Milestone Workflow Routing

| User Selection | Target Workflow | First Step |
|----------------|-----------------|------------|
| [M1] Conception | bi-business-innovation/bi-m1/workflow.md | bi-business-innovation/bi-m1/steps-c/step-01-init.md |
| [M2] Validation | bi-business-innovation/bi-m2/workflow.md | bi-business-innovation/bi-m2/steps-c/step-01-init.md |
| [M3] Brand | bi-business-innovation/bi-m3/workflow.md | bi-business-innovation/bi-m3/steps-c/step-01-init.md |
| [M4] Prototypation | bi-business-innovation/bi-m4/workflow.md | bi-business-innovation/bi-m4/steps-c/step-01-init.md |
| [M5] Market Validation | bi-business-innovation/bi-m5/workflow.md | bi-business-innovation/bi-m5/steps-c/step-01-init.md |
| [M6] MVP | bi-business-innovation/bi-m6/workflow.md | bi-business-innovation/bi-m6/steps-c/step-01-init.md |

---

## Framework Naming Convention

All framework workflows follow the pattern: `bi-m{N}-{framework-name}/`

| Pattern | Example |
|---------|---------|
| Milestone prefix | `bi-m1-`, `bi-m2-`, etc. |
| Framework name | Full name, kebab-case |
| Complete path | `bi-business-innovation/bi-m1/bi-m1-working-backwards/workflow.md` |

---

## State Tracking

### Project Memo (Single Source of Truth)

The `project-memo.md` is the single source of truth for project state:
- Updated after each framework completion
- Contains synthesized findings from all frameworks
- Frontmatter YAML tracks: currentMilestone, currentFramework, stepsCompleted
- Used by agents to understand project context

---

## Agent Handoff Protocol

When starting work on a project:

| Step | Action | File |
|------|--------|------|
| 1 | Read project-memo | `{bmad_output}/{project-name}/business-innovation/project-memo.md` |
| 2 | Check frontmatter | currentMilestone, currentFramework, stepsCompleted |
| 3 | Load milestone workflow | Based on current milestone |
| 4 | Confirm with user | Present state and next steps |

When ending work:

| Step | Action | File |
|------|--------|------|
| 1 | Update project-memo frontmatter | currentMilestone, currentFramework |
| 2 | Confirm with user | Summary of session |

---

## Content Ownership Mapping

Defines which framework owns each concept per milestone. Within a milestone, every concept MUST have exactly one owning framework — the first framework in the milestone sequence that defines it. Later frameworks MUST reference the owning framework's definition by file path and section. They may extend, challenge, or refine the concept with new analytical dimensions, but they MUST NOT restate the original definition.

When a framework needs to reference a concept it does not own, it MUST use the `## Prior Context` section format rather than restating the definition.

### M1: Conception

| Concept | Owning Framework | Later Frameworks Reference + Add |
|---------|-----------------|----------------------------------|
| Customer definition / target customer | Working Backwards | PSF refines segment boundaries; Lean Canvas maps segments to channels |
| Problem statement / customer problem | Working Backwards | PSF adds triggers and emotional dimensions; Lean Canvas distills to top-3 list; Five Whys traces root causes |
| Value proposition | Working Backwards | Lean Canvas distills to single UVP statement |
| Customer jobs / hiring-firing criteria | Jobs-to-be-Done | PSF references jobs when mapping solution fit |
| Competitive positioning / market alternatives | Competitive Landscape | Lean Canvas references for unfair advantage |
| Solution description / fit validation | Problem-Solution Fit | Lean Canvas references for solution box |
| Customer segments / business model structure | Lean Canvas | — (terminal framework for business model) |
| Root cause structure | Five Whys | — (terminal framework for causal analysis) |

**First framework (concept originator):** Working Backwards

### M2: Validation

| Concept | Owning Framework | Later Frameworks Reference + Add |
|---------|-----------------|----------------------------------|
| Assumption inventory / classification | Leap of Faith | Assumption Mapping scores and prioritizes; Pre-mortem references for failure mode alignment |
| Assumption scoring / test cards | Assumption Mapping | — |
| Market sizing (TAM/SAM/SOM) | TAM/SAM/SOM | Unit Economics references SAM for revenue projections |
| Unit economics (CAC, LTV, payback) | Unit Economics | — |
| Technical feasibility / component readiness | Technology Readiness Level | — |
| Failure modes / risk mitigation | Pre-mortem | — |

**First framework (concept originator):** Leap of Faith

### M3: Brand

| Concept | Owning Framework | Later Frameworks Reference + Add |
|---------|-----------------|----------------------------------|
| Emotional territory / archetype selection | Brand Archetypes | Brand Prism references for personality facet; Tone of Voice references for emotional register |
| Brand identity facets (physique, personality, culture, reflection, self-image, relationship) | Brand Prism | Brandbook consolidates all facets |
| Purpose (Why / How / What) | Golden Circle | Brand Positioning references Why for positioning rationale; Messaging Architecture references Why for brand promise |
| Positioning statement / perceptual map | Brand Positioning | Messaging Architecture references for message differentiation |
| Voice dimensions / communication style | Tone of Voice | Messaging Architecture references for message tone; Brandbook consolidates |
| Brand promise / key messages / proof points | Messaging Architecture | Brandbook consolidates |
| Consolidated brand identity | Brandbook | — (terminal framework — synthesizes all M3 outputs) |

**First framework (concept originator):** Brand Archetypes

### M4: Prototypation

| Concept | Owning Framework | Later Frameworks Reference + Add |
|---------|-----------------|----------------------------------|
| Conversion paths / information architecture | User Flow & IA | Design Context references for content hierarchy; CCD references for funnel analysis |
| Content hierarchy / CTA priorities / design brief | Design Context | CCD references for optimization targets |
| Funnel optimization / friction analysis | Conversion-Centered Design | Heuristic Evaluation references for usability context |
| Usability validation / violation assessment | Heuristic Evaluation | — (terminal framework for quality validation) |

**First framework (concept originator):** User Flow & IA

---

## Quick Reference

- **6 milestones**: Conception → Validation → Brand → Prototypation → Market Validation → MVP
- **State tracking**: project-memo.md frontmatter (currentMilestone, currentFramework, stepsCompleted)
- **Output location**: `{bmad_output}/{project-name}/business-innovation/`
- **Framework synthesis**: Every framework MUST update project-memo.md on completion
