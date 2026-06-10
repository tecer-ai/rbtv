---
name: 'step-01-intake'
description: 'Resolve the target component, capture owner hypotheses, create the diagnosis document.'
nextStepFile: './step-02-measure.md'
workflowFile: './workflow.md'
outputFile: 'efficiency-diagnosis-{component}-{date}.md'
---

# Step 1: Intake & Hypotheses

**Progress: Step 1 of 4** — Next: Measure

---

## STEP GOAL

Pin exactly what is being reviewed, record the owner's felt-waste hypotheses as testable claims, and create the diagnosis document.

---

## MANDATORY EXECUTION RULES

- 🛑 NEVER begin measuring or investigating in this step — scope first
- 🧭 NEVER conclude a file is absent from a single empty Glob result — verify with `ls`/`find` or a content grep (Glob returns false negatives on some hosts)
- 📋 Hypotheses are recorded verbatim and labeled — they are claims to TEST, not facts

---

## MANDATORY SEQUENCE

### 1. Resolve the Target

If the owner has not named a component, HALT and ask: "Which component should I review? Name it or give a path." Then:

1. If the given path is an installed thin loader (e.g., under `.claude/skills/` or `.claude/commands/`), follow its LOAD/READ reference to the SOURCE files — the source is the review target, never the installed copy.
2. Enumerate the target's complete file tree with `ls`/`find` (Bash), recording every file path.
3. Record: component type(s) per `{rbtv_path}/builder/workflows/component-creation/data/rbtv-architecture.md` taxonomy, file count, owning repo(s), and any sibling components it references.

### 2. Capture Owner Hypotheses

Ask the owner in ONE pass:

> "Two questions before I measure anything: (1) Which parts of this component feel wasteful to you, and why? (2) Which protections must NOT be weakened, whatever we find?"

Record each felt-waste claim verbatim as a numbered hypothesis (H1, H2, …). Zero hypotheses is a valid answer — the diagnosis then runs purely evidence-first.

### 3. Set the Quality-Floor Frame

State to the owner: "Default frame: every protection keeps its value — only its delivery format is on trial. Savings come from deduplication, restructuring, event-scoping, and determinism." If the owner wants a different floor (e.g., willing to drop protections for failures with no recent recurrence), record the stated floor in the document. Never assume a floor looser than the default.

### 4. Create the Diagnosis Document

Resolve the output path per the workflow's Initialization (already confirmed with the owner). Create the document:

```markdown
---
type: efficiency-diagnosis
status: in-progress
stepsCompleted: []
target: {component name}
target_paths: [{source root(s)}]
created: {date}
---

# Efficiency Diagnosis: {Component}

## Target & Scope
{type, file count, repos, file tree summary}

## Owner Hypotheses
{H1..Hn verbatim, or "none offered"}
## Quality Floor
{the confirmed frame}

## Measured Baseline
{Step 2}

## Discoveries
{Step 3}

## Problem Tree
{Step 4}

## Verdicts & Priorities
{Step 4}
```

### 5. Present Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 2 — Measure |
| **[X] Exit** | Stop the review |

HALT and WAIT for user input.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update the diagnosis document frontmatter: add `step-01-intake` to `stepsCompleted`
2. Load `./step-02-measure.md` and follow its instructions

---

✅ **SUCCESS:** target resolved to source files, tree enumerated, hypotheses + floor recorded, document created.
❌ **FAILURE:** measuring before scoping; reviewing an installed copy instead of source; paraphrasing hypotheses instead of recording them verbatim.
