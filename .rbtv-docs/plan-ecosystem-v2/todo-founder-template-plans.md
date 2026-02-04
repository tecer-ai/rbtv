# Founder Template Plans

**Status:** Future Development  
**Created:** 2026-01-31

---

## Overview

Convert the 6 founder milestone process files into executable template plans. Users instantiate templates via commands, which create project-specific plans ready for execution.

**Current state:** Process files are reference documents in `system/founder/m[N]_*/`.

**Proposed state:** Template plans in `.cursor/plan-templates/` instantiated via `/founder-m[N]` commands.

---

## Scope

All 6 founder milestones:

| Milestone | Current Process File | Template Plan |
|-----------|---------------------|---------------|
| M1 Conception | `system/founder/m1_conception/conception_process.md` | `.cursor/plan-templates/founder-m1-conception.template.plan.md` |
| M2 Validation | `system/founder/m2_validation/validation_process.md` | `.cursor/plan-templates/founder-m2-validation.template.plan.md` |
| M3 Brand | `system/founder/m3_brand/brand_process.md` | `.cursor/plan-templates/founder-m3-brand.template.plan.md` |
| M4 Prototypation | `system/founder/m4_prototypation/prototypation_process.md` | `.cursor/plan-templates/founder-m4-prototypation.template.plan.md` |
| M5 Market Validation | `system/founder/m5_market_validation/market_validation_process.md` | `.cursor/plan-templates/founder-m5-market-validation.template.plan.md` |
| M6 MVP | `system/founder/m6_mvp/mvp_process.md` | `.cursor/plan-templates/founder-m6-mvp.template.plan.md` |

---

## Template Structure

Each template follows standard plan structure with placeholders:

```yaml
---
name: founder-m1-conception
template: true
description: "Transform initial idea into comprehensive business concept"
instantiate_via: "/founder-m1 [project-name]"
---
# {PROJECT_NAME} — Conception Milestone

## Context

Project: {PROJECT_NAME}
Started: {DATE}
Founder inputs: {TO_BE_GATHERED}

## Execution Instructions

This is a **template plan**. Before execution:
1. Replace all `{PLACEHOLDER}` values with project-specific content
2. The instantiating command gathers inputs through user dialogue
3. Executing agents follow standard plan-execution protocol

## Todos

todos:
  - id: p1-1
    content: "Initialize project structure and memo"
    status: pending
    agent: executor
    judge_required: false
    framework_reference: "None (structural setup)"
```

---

## Instantiation Commands

One command per milestone:

| Command | Action |
|---------|--------|
| `/founder-m1 [project-name]` | Instantiate M1 Conception template |
| `/founder-m2 [project-name]` | Instantiate M2 Validation template |
| `/founder-m3 [project-name]` | Instantiate M3 Brand template |
| `/founder-m4 [project-name]` | Instantiate M4 Prototypation template |
| `/founder-m5 [project-name]` | Instantiate M5 Market Validation template |
| `/founder-m6 [project-name]` | Instantiate M6 MVP template |

### Command Flow

1. Read template from `.cursor/plan-templates/`
2. Gather project-specific context through user dialogue [TBD: dialogue flow]
3. Replace placeholders with gathered values
4. Create concrete plan at `.cursor/plans/[project]-m[N]-[milestone]/`
5. Optionally start execution

---

## Template Content Mapping

### M1 Conception

Based on `system/founder/m1_conception/conception_process.md`:

| Step | Task | Framework Reference | Agent | Judge Required |
|------|------|---------------------|-------|----------------|
| 1 | Initialize project structure and memo | None | executor | false |
| 2 | Define customer and problem | `conception_frameworks/working_backwards.md` | executor | true |
| 3 | Understand customer's progress goal | `conception_frameworks/jobs_to_be_done.md` | executor | true |
| 4 | Map competitive landscape | `conception_frameworks/competitive_landscape.md` | executor | true |
| 5 | Validate problem-solution alignment | `conception_frameworks/problem_solution_fit.md` | executor | true |
| 6 | Map business model hypothesis | `conception_frameworks/lean_canvas.md` | executor | true |
| 7 | Identify root causes | `conception_frameworks/five_whys.md` | executor | true |
| 8 | Synthesize into project memo | None | executor | true |
| 9 | Document key decisions | None | executor | false |

### M2 Validation

Based on `system/founder/m2_validation/validation_process.md`:

| Step | Task | Framework Reference | Agent | Judge Required |
|------|------|---------------------|-------|----------------|
| 1 | Initialize validation and collect assumptions | None | executor | false |
| 2 | Identify leap-of-faith assumptions | `validation_frameworks/leap_of_faith.md` | executor | true |
| 3 | Map assumptions by risk and uncertainty | `validation_frameworks/assumption_mapping.md` | executor | true |
| 4 | Size market opportunity | `validation_frameworks/tam_sam_som.md` | executor | true |
| 5 | Model unit economics | `validation_frameworks/unit_economics.md` | executor | true |
| 6 | Assess technical readiness | `validation_frameworks/technology_readiness_level.md` | executor | true |
| 7 | Run pre-mortem | `validation_frameworks/pre_mortem.md` | executor | true |
| 8 | Synthesize into project memo | None | executor | true |
| 9 | Document key decisions | None | executor | false |

### M3-M6

[TBD: Map remaining milestone process files to template tasks]

---

## Task YAML Fields

Each task in template includes:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Task identifier (e.g., `p1-1`) |
| `content` | Yes | Task description |
| `status` | Yes | Always `pending` in template |
| `agent` | No | `executor` for complex tasks, omit for simple |
| `judge_required` | No | `true` for complex tasks requiring validation |
| `framework_reference` | No | Path to framework document if applicable |
| `depends_on` | No | Task ID(s) that must complete first |
| `workflow` | No | Multi-agent sequence if needed (see [context-optimization.md](context-optimization.md)) |

---

## Relationship to Current Founder Module

| Aspect | Current | Proposed |
|--------|---------|----------|
| Process files | Reference documents | Source for template generation |
| Frameworks | Referenced in process files | Referenced in template tasks |
| Mentor agent | Guides through milestones conversationally | Could invoke template instantiation commands |
| Execution | Manual following of process steps | Automated via plan execution protocol |

**Note:** Process files remain as reference documentation. Templates are generated from them but don't replace them.

---

## Open Questions

| Question | Status |
|----------|--------|
| Command dialogue flow for gathering context | [TBD] |
| M3-M6 task mapping | [TBD] |
| Integration with mentor agent | [TBD] |
| Template update process when process files change | [TBD] |

---

*Last updated: 2026-01-31*
