# PRD: Add Continuation Support to All RBTV Workflows

## Status: Proposed
## Priority: Low
## Overlap: 0%
## Description: Update all output-producing workflows with continuable init and step-01b continuation files

---

## Problem

Two new templates were created to standardize multi-session workflow continuation:
- `step-init-continuable-template.md` — init step with continuation detection
- `step-continue-template.md` — step-01b that analyzes state and resumes

**Zero existing workflows comply.** Of 36 workflows, 28 produce output documents (`outputFile` in frontmatter) and should support continuation. Currently:
- 0 step-01b-continue.md files exist across all RBTV workflows
- 0 init steps reference `continueStepFile` in frontmatter
- A few init steps (e.g., lean-canvas) have ad-hoc inline continuation that doesn't follow the formal pattern
- Workflows have not been properly tested for multi-session resumption

## Scope

Add continuation support to **28 workflows** that produce output documents. The 8 workflows without `outputFile` (milestone orchestrators and action-only workflows) are out of scope.

## Per-Workflow Change

For each affected workflow:

### 1. Update step-01-init.md

Apply the pattern from `step-init-continuable-template.md`:
- Add `continueStepFile: './step-01b-continue.md'` to frontmatter
- Add continuation detection logic before fresh workflow setup:
  - Check if `{outputFile}` exists with `stepsCompleted` → route to step-01b
  - Check if all steps complete → offer "new" vs "continue modifying"
- Remove any ad-hoc inline continuation logic (replace with formal routing)

### 2. Create step-01b-continue.md

Create a new file following `step-continue-template.md`:
- Analyze `stepsCompleted` from output document frontmatter
- Read completed step files to reconstruct context
- Determine next step from last completed step's `nextStepFile`
- Present welcome-back dialog with progress summary
- Route to correct next step on [C] Continue

## Affected Workflows (28)

### Business Innovation — M1 (6)
| Workflow | Init Step | Output File |
|----------|-----------|-------------|
| bi-m1-competitive-landscape | steps-c/step-01-init.md | competitive-landscape.md |
| bi-m1-five-whys | steps-c/step-01-init.md | five-whys.md |
| bi-m1-jobs-to-be-done | steps-c/step-01-init.md | jobs-to-be-done.md |
| bi-m1-lean-canvas | steps-c/step-01-init.md | lean-canvas.md |
| bi-m1-problem-solution-fit | steps-c/step-01-init.md | problem-solution-fit.md |
| bi-m1-working-backwards | steps-c/step-01-init.md | working-backwards.md |

### Business Innovation — M2 (6)
| Workflow | Init Step | Output File |
|----------|-----------|-------------|
| bi-m2-assumption-mapping | steps-c/step-01-init.md | assumption-mapping.md |
| bi-m2-leap-of-faith | steps-c/step-01-init.md | leap-of-faith.md |
| bi-m2-pre-mortem | steps-c/step-01-init.md | pre-mortem.md |
| bi-m2-tam-sam-som | steps-c/step-01-init.md | tam-sam-som.md |
| bi-m2-technology-readiness-level | steps-c/step-01-init.md | technology-readiness-level.md |
| bi-m2-unit-economics | steps-c/step-01-init.md | unit-economics.md |

### Business Innovation — M3 (6)
| Workflow | Init Step | Output File |
|----------|-----------|-------------|
| bi-m3-brand-archetypes | steps-c/step-01-init.md | brand-archetypes.md |
| bi-m3-brand-positioning | steps-c/step-01-init.md | brand-positioning.md |
| bi-m3-brand-prism | steps-c/step-01-init.md | brand-prism.md |
| bi-m3-golden-circle | steps-c/step-01-init.md | golden-circle.md |
| bi-m3-messaging-architecture | steps-c/step-01-init.md | messaging-architecture.md |
| bi-m3-tone-of-voice | steps-c/step-01-init.md | tone-of-voice.md |

### Business Innovation — M4 (3)
| Workflow | Init Step | Output File |
|----------|-----------|-------------|
| bi-m4-conversion-centered-design | steps-c/step-01-init.md | conversion-optimization.md |
| bi-m4-heuristic-evaluation | steps-c/step-01-init.md | heuristic-evaluation.md |
| bi-m4-user-flow-ia | steps-c/step-01-init.md | user-flow-ia.md |

### Utility Workflows (7)
| Workflow | Init Step | Output File |
|----------|-----------|-------------|
| browser-web-automation | steps-c/step-01-init.md | browser-session-{slug}.md |
| design-qa-validation | steps-c/step-01-init.md | design-validation-{slug}.md |
| design-token-extraction | steps-c/step-01-init.md | design-extraction-{slug}.md |
| doc-compound-learning | steps-c/step-01-init.md | {filename}.md |
| doc-context-handoff | steps-c/step-01-init.md | {filename}.md |
| plan-lifecycle | steps-c/step-01-init.md | {plan-name}.plan.md |
| problem-structuring | steps-c/step-01-init.md | structured-problem-{date}.md |

## Out of Scope (8 workflows)

These have no `outputFile` and don't need continuation:
- bi-m1, bi-m2, bi-m3, bi-m4 (milestone orchestrators — route to sub-workflows)
- git-commit (action-only, completes in one session)
- diagram-mermaid-render (action-only)
- prompting-assistance (action-only)
- bi-m4-design-context (invokes BMAD workflow)

## Implementation Strategy

Each workflow is independent. Changes can be parallelized across all 28 workflows. The change is mechanical:

1. Read the existing step-01-init.md
2. Add `continueStepFile` to frontmatter
3. Insert continuation detection block (sections 1-2 from template) before existing setup logic
4. Remove any ad-hoc inline continuation if present
5. Create step-01b-continue.md from template, customized with the workflow's `outputFile` path

## Risks

- **Mechanical but voluminous:** 28 workflows x 2 file changes = 56 file operations. Risk of copy-paste errors.
- **Untested workflows:** Existing workflows have not been properly tested for multi-session behavior. Adding continuation may surface latent bugs in `stepsCompleted` tracking.
- **Dynamic output paths:** Some workflows use `{slug}` or `{date}` in outputFile paths (e.g., `browser-session-{slug}.md`). The continuation step must handle pattern-based file discovery rather than exact path matching.

## Success Criteria

- All 28 workflows have a `step-01b-continue.md` following `step-continue-template.md`
- All 28 init steps reference `continueStepFile` in frontmatter
- All 28 init steps detect existing output and route to step-01b
- No ad-hoc inline continuation remains (replaced with formal routing)
- Dynamic output path workflows handle file discovery correctly
