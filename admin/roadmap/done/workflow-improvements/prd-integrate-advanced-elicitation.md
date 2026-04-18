# PRD: Integrate Advanced Elicitation with RBTV

## Status: Proposed
## Priority: Low
## Overlap: 100%
## Description: Enable RBTV workflows to use BMAD's advanced elicitation task via the [A] menu option

---

## Problem

RBTV step templates include an `[A] Advanced Elicitation` menu option, but the `advancedElicitationTask` frontmatter field is commented out because the integration has never been validated. RBTV workflows currently cannot use advanced elicitation — the menu option exists in the template pattern but has no working backend reference.

BMAD's advanced elicitation (`core/workflows/advanced-elicitation/workflow.xml`) is a fully functional task that loads 50 elicitation methods from a CSV, presents context-aware selections, and iteratively enhances content. There is no reason to internalize this — RBTV must reference BMAD's existing component.

## What Exists in BMAD

| Component | Path | Purpose |
|-----------|------|---------|
| Task file | `{bmad_core}/workflows/advanced-elicitation/workflow.xml` | XML task: loads methods, presents menu, executes selected method on content, loops until user selects 'x' |
| Methods CSV | `{bmad_core}/workflows/advanced-elicitation/methods.csv` | 50 methods across 10 categories (collaboration, advanced, competitive, technical, creative, research, risk, core, learning, philosophical, retrospective) |

### How It Works

1. Loads `methods.csv` and agent manifest
2. Analyzes current context (content type, complexity, risk level)
3. Selects 5 context-appropriate methods and presents a menu (1-5, [r] reshuffle, [a] list all, [x] proceed)
4. User selects a method; task executes it against current content and presents enhanced version
5. User approves/rejects changes, then menu re-displays
6. Loop continues until user selects 'x', which returns enhanced content to the calling step

### Integration Contract

When called from a workflow step:
- Receives the current section content (from conversation context)
- Returns enhanced content when user selects 'x'
- The calling step's menu redisplays after return

## What RBTV Needs

### 1. Uncomment `advancedElicitationTask` in Step Template

In `workflows/build-rbtv-component/templates/step-template.md`, change:

```yaml
# advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml' # Not yet integrated into RBTV
```

To:

```yaml
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
```

### 2. Update Step Template Menu Handling

The step template's menu handling for `[A]` must reference `{advancedElicitationTask}`:

```markdown
- IF A: Execute {advancedElicitationTask}
```

This already exists in BMAD's step template pattern. Verify RBTV's template matches.

### 3. Update Existing RBTV Workflow Steps

Audit all existing RBTV step files in `workflows/*/steps-*/`. For steps that present the A/P/C menu pattern, add `advancedElicitationTask` to their frontmatter and ensure menu handling references it.

### 4. Validate in a Running Workflow

Run a RBTV workflow end-to-end (e.g., build-rbtv-component) in an installed BMAD instance. At a step menu, select `[A]` and verify:
- Advanced elicitation task loads and presents method options
- A method can be selected and executed against current content
- Enhanced content returns correctly when 'x' is selected
- The calling step's menu redisplays

## Proposed Solution

1. **Uncomment** `advancedElicitationTask` in the step template
2. **Audit** existing step files and add the field where the A/P/C menu is used
3. **Validate** the integration works in an installed BMAD instance
4. **No internalization** — reference BMAD's component directly per admin restrictions

## Risks

- **Path resolution:** RBTV references `{bmad_core}/...` which only resolves in an installed BMAD instance, not in standalone RBTV development
- **Context handoff:** The advanced elicitation task assumes conversation context contains the content to enhance — verify RBTV steps provide this naturally

## Success Criteria

- `advancedElicitationTask` field is uncommented and active in the step template
- All RBTV step files with A/P/C menus include the field in frontmatter
- Selecting `[A]` in a running RBTV workflow correctly invokes BMAD's advanced elicitation
- Enhanced content returns to the calling step without data loss
