---
name: Analyze Requirements
description: Understand what the user needs and determine the right component type.
nextStepFile: step-02-discover-placement.md
---

# Step 1: Analyze Requirements

**Goal:** Determine the exact component type and design through critical partnership — resolve every design decision before proceeding.

---

## Critical Design Partner Behaviors

| Behavior | How it applies |
|----------|---------------|
| Force design decisions | Never accept vague requirements. If the user says "build me a skill", ask what it does, what problem it solves, and how it is triggered. |
| Challenge assumptions | Walk every request through the decision tree in rbtv-architecture.md. Push back when the proposed component type is wrong. |
| Surface edge cases | Identify boundary conditions, empty states, and error cases before scaffolding. |
| Propose and critique | Offer a concrete proposal, then critique it — identify its weaknesses before the user accepts it. |
| No premature building | Never proceed to Step 02 until every design decision in this step is resolved. |

---

## Mandatory Sequence

### 1. Capture Intent

Ask these three questions. Do NOT proceed until all are answered:

| Question | Why it matters |
|----------|---------------|
| What are you building? | Determines component type |
| What problem does it solve? | Validates necessity — checks against existing components |
| How is it triggered? | Determines entry point type (skill, command, or none) |

### 2. Check for Existing Components

Before designing anything new, scan for overlap:

- Read `{rbtv_path}/workflows/component-creation/data/component-patterns.md` Naming Standard table
- Check component naming patterns against what the user describes
- If an existing component partially covers the need: surface it and ask whether to extend or create new

Never create a new component when an existing one can be extended.

### 3. Walk the Decision Tree

Run the user's requirement through the Component Decision Tree in rbtv-architecture.md. Present the tree result explicitly:

```
Based on your requirements, this is a [component type] because [reason].
Decision tree path: [1 → 2 → 3 → ...]
```

If the user disagrees: challenge their counter-proposal against the tree. Do not accept "I want a skill" as a substitute for design thinking.

### 4. Resolve Component-Specific Details

For each component type, these details are mandatory before continuing:

| Component | Required details |
|-----------|----------------|
| Workflow | Step count, step names, goals, data file needs, output document structure |
| Agent/Persona | Persona identity, communication style, menu capabilities |
| Rule | Behavior being enforced, scope, trigger conditions, enforcement mechanism, anti-pattern table |
| Task | Objective, input/output contract, invocation context |
| Skill | Backing component (workflow or task), trigger description for auto-detection |
| Command | Backing component, target file path |

For skills: the backing workflow or task must already exist OR be designed in this step. A skill without a backing file is not buildable — create the backing file design first.

For rules: read `{rbtv_path}/workflows/component-creation/data/rule-design-guide.md`. Resolve every element in the "Required Design Elements" table before proceeding. A rule that only describes desired behavior is a suggestion — the guide explains how to make rules enforceable.

### 5. Confirm with User

Present a confirmation summary:

```
Component type: [type]
Name: [name]
Problem solved: [one sentence]
Dependencies: [list or "none"]
Proposed structure: [brief description]
Files to create: [list]
```

Wait for explicit approval before proceeding. If the user modifies anything, re-validate against the decision tree.

---

## Step Menu

| Option | Action |
|--------|--------|
| [C] Continue | Proceed to Step 02 — Discover Placement |
| [X] Exit | Stop workflow |

HALT and WAIT for user input.
