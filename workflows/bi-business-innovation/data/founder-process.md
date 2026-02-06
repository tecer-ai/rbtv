# Founder Process Knowledge

Master navigation for the 6-milestone business innovation lifecycle from idea to MVP.

---

## Milestones Summary

| Milestone | Goal | Key Frameworks | Workflow |
|-----------|------|----------------|----------|
| M1: Conception | Structure idea into comprehensive business concept | Working Backwards, Jobs-to-be-Done, Competitive Landscape, Problem-Solution Fit, Lean Canvas, 5 Whys | bi-m1/workflow.md |
| M2: Validation | Validate technical and financial feasibility | Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL, Pre-mortem | bi-m2/workflow.md |
| M3: Brand | Create preliminary brand book | Brand Archetypes, Brand Prism, Golden Circle, Positioning, Tone of Voice, Messaging Architecture | bi-m3/workflow.md |
| M4: Prototypation | Build working HTML prototype for F&F testing | User Flow, Information Architecture, Design Brief, Atomic Design, Conversion Design, WCAG | bi-m4/workflow.md |
| M5: Market Validation | Validate market demand with low spending | Mom Test, SPIN Selling, Smoke Test, Van Westendorp PSM, Bullseye, Sean Ellis PMF | bi-m5/workflow.md |
| M6: MVP | Create minimum viable product for real clients | User Story Mapping, INVEST, MoSCoW, Scrum, CI/CD, OWASP Top 10 | bi-m6/workflow.md |

---

## Output Folder Structure

```
_bmad-output/{project-name}/founder/
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
| [M1] Conception | bi-m1/workflow.md | bi-m1/steps-c/step-01-init.md |
| [M2] Validation | bi-m2/workflow.md | bi-m2/steps-c/step-01-init.md |
| [M3] Brand | bi-m3/workflow.md | bi-m3/steps-c/step-01-init.md |
| [M4] Prototypation | bi-m4/workflow.md | bi-m4/steps-c/step-01-init.md |
| [M5] Market Validation | bi-m5/workflow.md | bi-m5/steps-c/step-01-init.md |
| [M6] MVP | bi-m6/workflow.md | bi-m6/steps-c/step-01-init.md |

---

## Framework Naming Convention

All framework workflows follow the pattern: `bi-m{N}-{framework-name}/`

| Pattern | Example |
|---------|---------|
| Milestone prefix | `bi-m1-`, `bi-m2-`, etc. |
| Framework name | Full name, kebab-case |
| Complete path | `bi-m1-working-backwards/workflow.md` |

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
| 1 | Read project-memo | `_bmad-output/{project-name}/founder/project-memo.md` |
| 2 | Check frontmatter | currentMilestone, currentFramework, stepsCompleted |
| 3 | Load milestone workflow | Based on current milestone |
| 4 | Confirm with user | Present state and next steps |

When ending work:

| Step | Action | File |
|------|--------|------|
| 1 | Update project-memo frontmatter | currentMilestone, currentFramework |
| 2 | Confirm with user | Summary of session |

---

## Quick Reference

- **6 milestones**: Conception → Validation → Brand → Prototypation → Market Validation → MVP
- **State tracking**: project-memo.md frontmatter (currentMilestone, currentFramework, stepsCompleted)
- **Output location**: `_bmad-output/{project-name}/founder/`
- **Framework synthesis**: Every framework MUST update project-memo.md on completion
