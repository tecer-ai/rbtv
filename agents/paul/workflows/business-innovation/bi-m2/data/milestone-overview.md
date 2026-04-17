# M2 Validation Milestone Overview

## Purpose

M2 Validation stress-tests the assumptions, feasibility, and financial viability of the business concept produced in M1 Conception before committing resources to brand, prototype, or market validation. At the end of M2, the founder should have explicit persevere/pivot/kill criteria and evidence-backed confidence (or lack thereof) in the concept's viability.

---

## Framework Sequence and Dependencies

### Recommended Execution Order

The frameworks should be completed in this order for optimal learning flow (from validation_process.md):

1. **Leap of Faith** (Step 2) — Identify critical assumptions and kill criteria
2. **Assumption Mapping** (Step 3) — Prioritize assumptions for testing
3. **TAM/SAM/SOM** (Step 4) — Size the market opportunity
4. **Unit Economics** (Step 5) — Model financial viability
5. **Technology Readiness Level** (Step 6) — Assess technical feasibility
6. **Pre-mortem** (Step 7) — Surface hidden risks

### Foundation Framework

**Leap of Faith** — Start here. Identifies the make-or-break assumptions.
- Prerequisites: All M1 frameworks (Working Backwards, JTBD, Competitive Landscape, Problem-Solution Fit, Lean Canvas, Five Whys)
- Recommended Order: 1st
- Output: Prioritized assumptions with value/growth classification and kill criteria
- Feeds into: All other M2 frameworks

### Progressive Build Frameworks

**Assumption Mapping** — Visual prioritization matrix
- Prerequisites: Leap of Faith
- Recommended Order: 2nd
- Output: Importance × Uncertainty matrix with test-or-accept decisions
- Feeds into: M5 Market Validation test designs

**TAM/SAM/SOM** — Market opportunity sizing
- Prerequisites: Leap of Faith (recommended)
- Recommended Order: 3rd
- Output: Market sizing with sourced estimates using top-down and bottom-up methods
- Feeds into: Unit Economics (market capture assumptions)
- **WEB RESEARCH MANDATORY**

**Unit Economics** — Financial viability model
- Prerequisites: TAM/SAM/SOM
- Recommended Order: 4th
- Output: LTV, CAC, payback period, break-even analysis with sensitivity analysis
- Feeds into: Pre-mortem (financial failure modes)
- **WEB RESEARCH MANDATORY**

**Technology Readiness Level** — Technical feasibility assessment
- Prerequisites: Leap of Faith (recommended)
- Recommended Order: 5th
- Output: TRL assessment with component-level ratings and de-risking plan
- Feeds into: Pre-mortem (technical failure modes), M4 Prototypation, M6 MVP

### Final Framework

**Pre-mortem** — Comprehensive risk analysis
- Prerequisites: All prior M2 frameworks (Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL)
- Recommended Order: 6th (final M2 framework)
- Output: Ranked failure modes with mitigation actions
- Completes: M2 Validation milestone

---

## Execution Pattern

1. **Start with Leap of Faith** — Identifies critical assumptions and kill criteria
2. **Complete Assumption Mapping** — Prioritizes testing strategy
3. **Run TAM/SAM/SOM and TRL in parallel** — No interdependency (both feed Pre-mortem)
4. **Complete Unit Economics** — After TAM/SAM/SOM (needs market capture assumptions)
5. **Run Pre-mortem** — Final comprehensive risk assessment after all frameworks
6. **Make explicit persevere/pivot/kill recommendation** — Based on M2 evidence
7. **Return to milestone selection** — M2 complete, proceed to M3 Brand

---

## Success Criteria

M2 Validation is complete when:

1. ✅ Leap of Faith analysis exists with prioritized assumptions, value/growth classification, and kill criteria
2. ✅ Assumption map exists showing test-or-accept decisions for all M1 assumptions
3. ✅ TAM/SAM/SOM analysis exists with sourced estimates using both top-down and bottom-up methods
4. ✅ Unit economics model exists with LTV, CAC, payback period, and break-even estimates
5. ✅ TRL assessment exists with component-level ratings and de-risking plan
6. ✅ Pre-mortem analysis exists with ranked failure modes and mitigation actions
7. ✅ Project-memo Progress > Validation section lists all completed frameworks
8. ✅ There is an explicit persevere/pivot/kill recommendation with supporting evidence
9. ✅ All market facts and industry benchmarks have verified web sources (no training-data hallucinations)
10. ✅ Founder can articulate: What must be true? What evidence supports it? What would change our mind?

---

## Framework Routing Codes

| Code | Framework | Workflow Path |
|------|-----------|---------------|
| [LF] | Leap of Faith | ../bi-m2-leap-of-faith/workflow.md |
| [AM] | Assumption Mapping | ../bi-m2-assumption-mapping/workflow.md |
| [TS] | TAM/SAM/SOM | ../bi-m2-tam-sam-som/workflow.md |
| [UE] | Unit Economics | ../bi-m2-unit-economics/workflow.md |
| [TR] | Technology Readiness Level | ../bi-m2-technology-readiness-level/workflow.md |
| [PM] | Pre-mortem | ../bi-m2-pre-mortem/workflow.md |

---

## State Tracking

All framework completion is tracked in project-memo.md frontmatter:

```yaml
stepsCompleted:
  - bi-m2-leap-of-faith
  - bi-m2-assumption-mapping
  - bi-m2-tam-sam-som
  - bi-m2-unit-economics
  - bi-m2-technology-readiness-level
  - bi-m2-pre-mortem
```

Each framework workflow's final synthesis step adds its entry to stepsCompleted.

---

## Referral Logic

- **Milestone workflow (bi-m2):** Entry points to framework workflows (menu). User selects a framework → load that framework's workflow.
- **Framework workflow (last step):** Update project_memo (stepsCompleted, synthesis); instruct user to return to milestone menu to pick next framework or [B] Back.
- **project_memo:** Single source of truth for state (stepsCompleted, current milestone, synthesis from each framework).
