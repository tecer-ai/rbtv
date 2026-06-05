# M1 Conception Milestone Overview

## Purpose

M1 Conception transforms an idea into a comprehensive business concept through systematic exploration using 6 frameworks. At the end of M1, the founder should clearly articulate: Who is the customer? What problem are we solving? Why is our solution compelling? What must be true for this to work?

---

## Framework Sequence and Dependencies

### Recommended Execution Order

The frameworks should be completed in this order for optimal learning flow (from conception_process.md):

1. **Working Backwards** (Step 2) — Foundation framework
2. **Jobs-to-be-Done** (Step 3) — Customer job analysis
3. **Competitive Landscape** (Step 4) — Market positioning + benchmarking
4. **Problem-Solution Fit** (Step 5) — Alignment validation
5. **Lean Canvas** (Step 6) — Business model hypothesis
6. **Five Whys** (Step 7) — Root cause analysis

### Foundation Framework

**Working Backwards** — Start here. Creates the north star for all other frameworks.
- Prerequisites: None
- Recommended Order: 1st
- Output: Press release + FAQ
- Feeds into: All other M1 frameworks

### Progressive Build Frameworks

**Jobs-to-be-Done** — Customer job analysis
- Prerequisites: Working Backwards
- Recommended Order: 2nd
- Output: Job hypotheses + job stories
- Feeds into: Problem-Solution Fit, Lean Canvas

**Competitive Landscape** — Market positioning + benchmarking
- Prerequisites: Working Backwards
- Recommended Order: 3rd
- Output: Competitive analysis + positioning
- Feeds into: Lean Canvas (Unfair Advantage)

**Problem-Solution Fit** — Problem/solution canvas + assumptions
- Prerequisites: Working Backwards AND Jobs-to-be-Done
- Recommended Order: 4th
- Output: Problem-solution fit canvas
- Feeds into: Lean Canvas

**Lean Canvas** — Business model canvas
- Prerequisites: Working Backwards, Jobs-to-be-Done, Problem-Solution Fit
- Recommended Order: 5th
- Output: Complete Lean Canvas with assumptions
- Feeds into: Five Whys (Problem block refinement)

### Final Framework

**Five Whys** — Root cause analysis
- Prerequisites: Working Backwards
- Recommended: Complete Lean Canvas first for Problem block refinement
- Recommended Order: 6th (final M1 framework)
- Output: Root cause map + updated Lean Canvas
- Completes: M1 Conception milestone

---

## Execution Pattern

1. **Start with Working Backwards** — Foundation for everything else
2. **Run JTBD and Competitive Landscape in parallel** — No interdependency
3. **Complete Problem-Solution Fit** — After WB + JTBD
4. **Create Lean Canvas** — Synthesizes all prior frameworks
5. **Run Five Whys** — Final deep dive on problem structure
6. **Return to milestone selection** — M1 complete, proceed to M2 Validation

---

## Success Criteria

M1 Conception is complete when:

1. ✅ Working Backwards document exists with Press Release and FAQ
2. ✅ Jobs-to-be-Done analysis exists with job stories
3. ✅ Competitive Landscape analysis exists with geographic benchmarks
4. ✅ Problem-Solution Fit Canvas exists with assumptions
5. ✅ Lean Canvas exists with informed Unfair Advantage
6. ✅ Five Whys analysis exists with root cause map
7. ✅ Project-memo Progress > Conception section lists all completed frameworks
8. ✅ Founder can clearly articulate:
   - Who is the customer?
   - What problem are we solving?
   - Why is our solution compelling?
   - What must be true for this to work?

---

## Framework Routing Codes

| Code | Framework | Workflow Path |
|------|-----------|---------------|
| [WB] | Working Backwards | ../bi-m1-working-backwards/workflow.md |
| [JT] | Jobs-to-be-Done | ../bi-m1-jobs-to-be-done/workflow.md |
| [CL] | Competitive Landscape | ../bi-m1-competitive-landscape/workflow.md |
| [PS] | Problem-Solution Fit | ../bi-m1-problem-solution-fit/workflow.md |
| [LC] | Lean Canvas | ../bi-m1-lean-canvas/workflow.md |
| [5W] | Five Whys | ../bi-m1-five-whys/workflow.md |

---

## State Tracking

All framework completion is tracked in project-memo.md frontmatter:

```yaml
stepsCompleted:
  - bi-m1-working-backwards
  - bi-m1-jobs-to-be-done
  - bi-m1-competitive-landscape
  - bi-m1-problem-solution-fit
  - bi-m1-lean-canvas
  - bi-m1-five-whys
```

Each framework workflow's final synthesis step adds its entry to stepsCompleted.

---

## Referral Logic

- **Milestone workflow (bi-m1):** Entry points to framework workflows (menu). User selects a framework → load that framework's workflow.
- **Framework workflow (last step):** Update project_memo (stepsCompleted, synthesis); instruct user to return to milestone menu to pick next framework or [B] Back.
- **project_memo:** Single source of truth for state (stepsCompleted, current milestone, synthesis from each framework).
