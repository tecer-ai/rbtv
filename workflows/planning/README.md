# Plan Lifecycle Workflow

Complete workflow for creating and executing plans with quality gates.

## Structure

```
plan-lifecycle/
├── workflow.md                    # Entry point - mode routing
├── steps-c/                       # Create mode (4 steps)
│   ├── step-01-init.md           # Initialize - scope and plan name
│   ├── step-02-context.md        # Gather context + spec artifacts
│   ├── step-03-structure.md      # Generate phases, tasks, checkpoints
│   └── step-04-finalize.md       # Write plan file + initial log
├── steps-x/                       # Execute mode (3 steps, looping)
│   ├── step-01-init.md           # Load plan, read prior decisions
│   ├── step-02-execute.md        # Execute work + invoke judge
│   └── step-03-document.md       # Write execution decisions, loop
├── data/                          # Knowledge files
│   ├── plan-creation-rules.md    # Granularity, file ops, dependencies
│   └── execution-protocol.md     # 3-step guardrail workflow
└── templates/
    └── plan-template.md           # Plan document template
```

## Usage

**Create a plan:**
```
/rbtv-plan
> "I want to create a plan"
```

**Execute a plan:**
```
/rbtv-plan
> Reference a *.plan.md file or say "execute plan"
```

## Key Features

### Creation Mode
- **4-step guided process:** Init → Context → Structure → Finalize
- **Spec artifacts:** shape.md, standards.md, references.md
- **Dependency validation:** Checks CREATE-before-UPDATE, circular deps
- **Explicit file operations:** Tasks use CREATE/UPDATE/DELETE/MOVE verbs
- **Context budgeting:** Guidance for splitting oversized tasks (>100k tokens)
- **Zero-context plans:** Self-contained, executable by any agent

### Execution Mode
- **3-step guardrail:** Read decisions → Execute with Judge → Write decisions
- **Quality gates:** Judge approval mandatory before marking tasks complete
- **Checkpoint handling:** Human approval required at phase transitions
- **State tracking:** Execution decisions logs preserve context
- **Automatic condensation:** Reduces context load as plan progresses
- **Escalation protocol:** After 10 rejections, escalate to user

## Improvements vs Original

Based on plan-ecosystem-v2 research:

1. ✅ **Spec artifacts** - Preserve shaping decisions, standards, references
2. ✅ **Explicit file operations** - CREATE/UPDATE/DELETE/MOVE required
3. ✅ **Dependency validation** - Dependencies-before-dependents enforced
4. ✅ **Architectural constraints** - Documented patterns in plan template
5. ✅ **Context budgeting** - ~100k token heuristic with research-first pattern

## Entry Points

- Command: `.cursor/commands/planning.md`
- Manifest: `_bmad/rbtv/rbtv-manifest.csv` (lines 18-19)

## Recovered

This structure was recovered from conversation history on 2026-02-04 after file operation loss.
All files restored with improvements integrated.
