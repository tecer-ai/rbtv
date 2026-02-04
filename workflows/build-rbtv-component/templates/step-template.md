# Step File Template

Use this template to create a step file for a BMAD workflow.

---

## Template

```markdown
---
name: 'step-{NN}-{short-name}'
description: '{What this step accomplishes}'
nextStepFile: './step-{NN+1}-{next-name}.md'
outputFile: '{planning_artifacts}/{output-name}.md'
---

# Step {N}: {Title}

**Progress: Step {N} of {Total}** — Next: {Next Step Title}

---

## STEP GOAL

{Single sentence: what this step accomplishes and why it matters.}

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

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
- **[A] Advanced Elicitation** — go deeper on any generated content
- **[P] Party Mode** — get multi-agent perspectives on this step's output
- **[C] Continue** — proceed to next step

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
- **nextStepFile**: Relative path to next step
- **outputFile**: Path to output document (use config variables)

### Sections
- **Progress indicator**: "Step N of Total — Next: Title"
- **STEP GOAL**: Single sentence purpose statement
- **MANDATORY EXECUTION RULES**: Behavioral constraints
- **MANDATORY SEQUENCE**: Numbered actions to follow
- **Menu Options**: Standard A/P/C pattern
- **CRITICAL STEP COMPLETION NOTE**: State update procedure

---

## Step Types

| Type | File Pattern | Purpose |
|------|-------------|---------|
| Init | step-01-init.md | Detect state, discover inputs, create output doc |
| Continuation | step-01b-continue.md | Resume from stepsCompleted |
| Middle | step-02 to step-N | Core workflow steps |
| Branch | step-N-branch.md | Route based on user choice |
| Final | step-N-complete.md | Review, polish, save |

---

## Standard Menu Patterns

**Standard (most steps):**
```
[A] Advanced Elicitation — go deeper on generated content
[P] Party Mode — get multi-agent perspectives
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
