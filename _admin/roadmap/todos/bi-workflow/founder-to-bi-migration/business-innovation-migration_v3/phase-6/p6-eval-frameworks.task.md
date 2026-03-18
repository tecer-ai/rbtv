---
task_id: p6-eval-frameworks
status: pending
phase: understand
complexity_score: 10
human_review: required
---

# Task: CRITICAL — Evaluate Omitted founder_process Frameworks Across M4-M6

## Goal

The original `founder_process.md` reference lists framework candidates that were NOT included in the migration plan. This task evaluates every omitted framework to decide whether it should be incorporated as an RBTV workflow, is genuinely covered by BMAD routing, or should be explicitly excluded with documented rationale.

For M6 frameworks that were "routed to BMAD," verify that actual BMAD workflows exist and cover the intent of the original framework — do not assume routing is valid without confirmation.

---

## Context Files

| File | Purpose |
|------|---------|
| `refs/founder/founder_process.md` | Source: full framework candidate lists for all milestones |
| `refs/founder/m4_prototypation/prototypation_process.md` | Source: M4 process detail |
| `refs/founder/m5_market_validation/market_validation_process.md` | Source: M5 process detail |
| `refs/founder/m6_mvp/mvp_process.md` | Source: M6 process detail |
| `_bmad/rbtv/workflows/bi-business-innovation/bi-m4/workflow.md` | Current: M4 milestone workflow |
| `_bmad/rbtv/readme.md` | Current: RBTV readme (M4 note needs update) |
| shape.md | Prior decisions from p6-1 and p6-2 |

> **Note:** `refs/` is relative to this plan folder and contains the original founder module content.

---

## Tools

| Tool | Mode | Purpose |
|------|------|---------|
| Read | direct | Load source refs and existing workflows |
| explore | subagent | Search BMAD workflows for claimed routing targets |

---

## Frameworks to Evaluate

### M4 Prototypation — 5 Omitted Candidates

These were in founder_process.md as YES candidates but have no RBTV workflow:

| Framework | Claimed Disposition | Verify |
|-----------|-------------------|--------|
| Atomic Design | Routed to BMAD create-ux-design | Confirm BMAD coverage |
| WCAG Accessibility | Embedded in synthesis | Confirm it's actually embedded somewhere |
| Responsive Design | Not addressed | Decide: embed, route, or exclude |
| Design Tokens | Routed to BMAD create-ux-design | Confirm BMAD coverage |
| Progressive Disclosure | Not addressed | Decide: embed, route, or exclude |

Also evaluate: the readme note "*Build Prototype and Testing Prep frameworks are planned*" — update or remove based on findings.

### M5 Market Validation — 4 Omitted Candidates

These are founder-specific (no BMAD equivalent) but were dropped without documented rationale:

| Framework | Notes |
|-----------|-------|
| A/B Testing | Validation technique |
| Funnel Analysis | Conversion tracking |
| Customer Development | Steve Blank methodology |
| Fake Door Test | Cheap validation technique |

Decide for each: add as RBTV workflow task to the plan, embed in existing M5 framework, or exclude with rationale.

### M6 MVP — 12 Routed Candidates

The plan claims "Full BMAD integration — all software development routes to BMAD workflows." Verify each has a real BMAD target:

| Framework | Expected BMAD Workflow | Verify Exists |
|-----------|----------------------|---------------|
| User Story Mapping | ? | Check |
| INVEST Criteria | ? | Check |
| MoSCoW Prioritization | ? | Check |
| Scrum/Agile | ? | Check |
| Feature Flags | ? | Check |
| Technical Architecture Patterns | ? | Check |
| CI/CD Pipeline | ? | Check |
| Instrumentation/Analytics | ? | Check |
| Error Monitoring | ? | Check |
| OWASP Top 10 | ? | Check |
| Launch Checklist | ? | Check |
| Soft Launch Strategy | ? | Check |

---

## Execution Flow

### Phase: Understand

1. Read `refs/founder/founder_process.md` — extract complete framework lists per milestone
2. Read M4, M5, M6 process docs from refs for full context on each framework's intent
3. Read shape.md for prior p6-1/p6-2 decisions and rationale
4. Search BMAD workflows to catalog what actually exists for M6 routing claims

### Phase: Execute

1. **M4 evaluation**: For each of the 5 omitted frameworks:
   - If claimed "routed to BMAD": verify the BMAD workflow actually covers it
   - If "embedded": locate where it's embedded and confirm adequacy
   - If unaddressed: decide disposition (add workflow, embed, or exclude)
   - Document rationale for each decision

2. **M5 evaluation**: For each of the 4 omitted frameworks:
   - Assess if it's a distinct methodology or overlaps with an existing M5 framework
   - If distinct and valuable: propose adding a new task to the plan
   - If overlapping: identify which existing framework absorbs it
   - If not valuable at this stage: exclude with rationale

3. **M6 evaluation**: For each of the 12 frameworks:
   - Search for the specific BMAD workflow that handles it
   - Map: `M6 Framework → BMAD Workflow Path`
   - Flag any framework with NO actual BMAD coverage
   - For uncovered frameworks: propose RBTV workflow or documented exclusion

4. **Produce decision matrix** (single table, all 21 frameworks):

   | Milestone | Framework | Decision | Target/Rationale |
   |-----------|-----------|----------|-----------------|
   | M4 | ... | COVERED / ADD / EMBED / EXCLUDE | ... |
   | M5 | ... | ... | ... |
   | M6 | ... | ... | ... |

5. **Update readme.md**: Remove or reword the stale M4 note on line 170

### Phase: Validate

1. Verify every framework from founder_process.md is accounted for (no gaps)
2. Verify every "routed to BMAD" claim has a confirmed BMAD workflow path
3. Present decision matrix to user for approval

### Phase: Close

1. Append execution entry to shape.md
2. If new framework tasks are approved, add them to the plan YAML and markdown body
3. Mark task status as completed in plan YAML
4. Update readme.md M4 note based on findings

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Decision matrix (21 frameworks) | shape.md | Markdown table |
| BMAD routing verification map (M6) | shape.md | Framework → BMAD path table |
| Plan updates (if any new tasks) | plan YAML + markdown | New todo entries |
| Readme M4 note update | `_bmad/rbtv/readme.md` | Remove or reword line 170 |

---

## Revolving Plan Rules

**When discoveries occur:**
- If frameworks need new RBTV workflows, add tasks to plan with appropriate IDs
- If M6 routing claims are invalid, flag as blocker requiring re-evaluation
- Append discovery to shape.md
- **MANDATORY**: In output message, clearly state any tasks added or removed
