# Step File Template

Use this template to create a step file for a BMAD workflow.

---

## Template

```markdown
---
name: 'step-{NN}-{short-name}'
description: '{What this step accomplishes}'

# File References
nextStepFile: './step-{NN+1}-{next-name}.md' # Remove for final step
altStepFile: './step-{NN}-{alt-name}.md' # Remove if no branching
workflowFile: './workflow.md'
outputFile: '{output-name}.md' # Remove if step does not write a file

# Task References

# Template References (if this step uses specific templates)
templateFile: './templates/{template-name}.md'

# Data References (if this step uses data files)
dataFile: './data/{data-name}.csv'
---

# Step {N}: {Title}

**Progress: Step {N} of {Total}** — Next: {Next Step Title}

---

## STEP GOAL

{Single sentence: what this step accomplishes and why it matters.}

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are a {role}. Continue your existing persona and communication style.

### Step-Specific Rules
- {Rule specific to this step's focus area}
- {Another rule specific to this step}

---

## EXECUTION PROTOCOLS

1. {What context to load or reference}
2. {What analysis to perform}
3. {What to produce for the user}
4. {How to present it}

---

## CONTEXT BOUNDARIES

**Available context:**
- Output document built so far
- Input documents loaded in step-01
- {Any step-specific data files}

**Out of scope:**
- {What this step does NOT address}

---

## MANDATORY SEQUENCE

### 1. {First Action Title}
{Detailed instructions for the first action}

### 2. {Second Action Title}
{Detailed instructions for the second action}

### 3. {Third Action Title}
{Detailed instructions for the third action}

### 4. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to next step

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append this step's content to the output document
2. Update frontmatter: add `step-{NN}-{short-name}.md` to `stepsCompleted`
3. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** {What constitutes successful completion of this step}

❌ **FAILURE:** {What constitutes a broken step — generating without input, skipping sequence, loading next step prematurely}
```

---

## Field Instructions

### Frontmatter
- **name**: Step identifier, format: `step-{NN}-{short-name}`
- **description**: What this step accomplishes
- **nextStepFile**: Relative path to next step (remove for final step)
- **altStepFile**: Relative path to alternate step (for branching; remove if no branching)
- **workflowFile**: Relative path to parent workflow.md
- **outputFile**: (Optional) Path where step writes its result. Used by framework synthesis steps that generate documents. Use `{rbtv_path}` path conventions. Omit if step does not produce a file.
- **partyModeWorkflow**: Path to party mode workflow
- **templateFile**: Path to template used by this step (if any)
- **dataFile**: Path to data file used by this step (if any)

### Sections
- **Progress indicator**: "Step N of Total — Next: Title"
- **STEP GOAL**: Single sentence purpose statement
- **MANDATORY EXECUTION RULES**: Behavioral constraints
- **MANDATORY SEQUENCE**: Numbered actions to follow
- **Menu Options**: Standard A/P/C pattern
- **CRITICAL STEP COMPLETION NOTE**: State update procedure

---

## Step Types

| Type | File Pattern | Template | Purpose |
|------|-------------|----------|---------|
| Init | step-01-init.md | This template | Detect state, discover inputs, create output doc |
| Init (continuable) | step-01-init.md | `step-init-continuable-template.md` | Init with continuation detection for multi-session workflows |
| Continuation | step-01b-continue.md | `step-continue-template.md` | Resume from stepsCompleted |
| Middle | step-02 to step-N | This template | Core workflow steps |
| Branch | step-N-branch.md | This template | Route based on user choice |
| Final | step-N-complete.md | This template | Review, polish, save |

**Multi-session workflows** MUST use the continuable init + continuation pair. Use `step-init-continuable-template.md` for the init step and `step-continue-template.md` for the continuation step.

---

## Standard Menu Patterns

**Standard (most steps):**
```
[C] Continue — proceed to next step
```

**Auto-proceed (init steps):**
```
[C] Continue — proceed to next step
```

**Branch (decision points):**
```
[1] Option A — take path A
[2] Option B — take path B
[R] Restart — restart this step
```

---

## Size Guidelines

| Metric | Target | Max |
|--------|--------|-----|
| Total lines | 80-200 | 250 |
| Mandatory rules | 6-8 | 14 |
| Sequence actions | 4-7 | 10 |
| Menu options | 3 | 5 |

---

## Common Mistakes

1. **Missing progress indicator** — Always show "Step N of Total"

2. **No STOP instruction** — Always end with "halt and wait for user selection"

3. **Loading next step early** — Only load nextStepFile AFTER [C] is selected AND frontmatter is updated

4. **Forgetting state update** — Always add step name to stepsCompleted before loading next
