# Context Window Optimization

**Status:** Future Development  
**Created:** 2026-01-31  
**Inspired by:** [agent-os shape-spec](https://github.com/buildermethods/agent-os/blob/main/commands/agent-os/shape-spec.md)

---

## Overview

This document covers context window management for plan execution:

1. **Spec artifacts** — Shaping documents created during plan creation
2. **Workflow YAML field** — Multi-agent task sequences

---

## Spec Artifacts

### Inspiration

agent-os creates shaping artifacts during plan creation. Adapted for robotville's business document context:

### Artifact Structure

```
.cursor/plans/[plan-name]/
├── [plan-name].plan.md          # The plan itself
├── shape.md                      # Shaping decisions, scope, constraints
├── standards.md                  # Which rules/standards apply
├── references.md                 # Patterns and documents studied
├── research/                     # Research summaries (if applicable)
│   ├── [topic]_summary.md
│   └── ...
└── [task_id]_execution_decisions.md  # Created during execution
```

### shape.md

Captures decisions made during plan creation:

```markdown
# {Plan Name} — Shaping Notes

## Scope

[What we're building/producing]

## Decisions

- [Key decisions made during shaping]
- [Constraints or requirements noted]

## Context

- **User inputs:** [What user provided]
- **References:** [Documents/patterns studied]
- **Constraints:** [Limitations identified]

## Standards Applied

- [rule-name] — [why it applies]
```

### standards.md

Which cursor rules and robotville standards apply:

```markdown
# Standards for {Plan Name}

The following standards apply to this work.

---

## file-operations.mdc

[Summary of relevant rules from this file]

---

## atomic-files.mdc

[Summary of relevant rules from this file]
```

### references.md

Documents and patterns studied during shaping:

```markdown
# References for {Plan Name}

## Documents Analyzed

| Document | Relevance | Key Insights |
|----------|-----------|--------------|
| [path] | [why relevant] | [what to use from it] |

## Patterns to Follow

| Pattern | Source | Application |
|---------|--------|-------------|
| [pattern name] | [where found] | [how to apply] |
```

---

## Workflow YAML Field

### Purpose

Define multi-agent sequences for tasks requiring multiple subagents.

### Schema

```yaml
workflow:
  - agent: [subagent-name]
    input: [file pattern or path]
    output: [output file path]
    hint: [optional guidance for agent]
    judge_required: [true/false, for executor]
```

### Example: Summarizer → Executor → Judge

```yaml
- id: p2-1
  content: "Analyze competitive landscape from 50+ documents"
  status: pending
  workflow:
    - agent: summarizer
      input: "research/*.md"
      output: "research/competitive_summary.md"
      hint: "Focus on pricing models, market positioning, feature gaps"
    - agent: executor
      input: "research/competitive_summary.md"
      judge_required: true
```

### Execution Flow

1. Orchestrating agent encounters task with `workflow:`
2. Executes first step (summarizer)
3. Summarizer produces output file
4. Executes second step (executor)
5. Executor reads input, does work
6. If `judge_required: true`: executor invokes judge
7. On completion: orchestrating agent marks task complete

### Workflow vs Single Agent

| Scenario | Use |
|----------|-----|
| Simple task | No `agent` or `workflow` field (orchestrator executes) |
| Complex task, single agent | `agent: executor` with `judge_required: true` |
| Multi-step task | `workflow:` with agent sequence |

---

*Last updated: 2026-01-31*
