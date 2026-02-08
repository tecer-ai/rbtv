---
---

# Template Instructions: Framework Guide

**Purpose:** Meta-template for creating framework execution guides that enable sophisticated, task-based execution of business methodologies with explicit progress tracking.

**Naming Convention:** `[framework_name].md` (e.g., `working_backwards.md`, `lean_canvas.md`)

**Location:** `system/founder/m[x]_[milestone]/[milestone]_frameworks/[framework_name].md`

---

## Framework Template Philosophy

This template creates framework guides for sophisticated practitioners—not beginners. The design assumes investment banking-level business acumen and focuses on rigorous execution.

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Task-based structure** | Each framework breaks into discrete tasks enabling "I'm in Step X, Task Y" tracking |
| **Explicit dependencies** | Each task declares Inputs (what you need) and Outputs (what you produce) |
| **Validation criteria** | Clear completion signals—no ambiguity about when to proceed |
| **Sophisticated audience** | Assumes deep business knowledge; avoids basic explanations |
| **Pitfalls over basics** | Teaches through negative requirements (what NOT to do) |
| **Cross-framework integration** | Shows how frameworks connect and build on each other |
| **No artificial constraints** | Framework guides can be 500+ lines if depth requires it |
| **Actionable rigor** | Every instruction must be executable; no vague guidance |

### Why Task-Based Structure

Framework guides decompose into tasks to enable precise position tracking within complex frameworks: "Milestone 1, Step 4, Task 3."

---

## Section Guidelines

Framework guides must follow this structure:

| Section | Required | Description |
|---------|----------|-------------|
| **Purpose** | Required | One-sentence: what this framework accomplishes |
| **Context** | Required | When in milestone, which step, prerequisites from prior frameworks |
| **Framework Overview** | Required | Origin, key principles, why it matters (2-3 paragraphs) |
| **Task Structure** | Required | Table listing all tasks with Goal, Inputs, Outputs |
| **Task Sections** | Required | One section per task with Goal, Inputs, Action, Output, Validation |
| **Pitfalls** | Required | What NOT to do—sophisticated warnings, not beginner tips |
| **Integration** | Required | How this framework connects to others in the milestone |
| **Success Criteria** | Required | Checklist: framework complete when... |
| **References** | Recommended | Source materials, books, papers (with citations) |
| **Examples** | Optional | Real or realistic examples (only if they clarify complex points) |

---

## How to Write a Framework Guide

Follow this workflow when creating a new framework guide:

| Step | Action | Notes |
|------|--------|-------|
| 1 | Research the framework | Read source material (books, papers, case studies) |
| 2 | Identify natural task boundaries | Where does execution break into distinct phases? |
| 3 | Map inputs/outputs per task | What does each task consume and produce? |
| 4 | Define validation criteria | How does user know task is complete? |
| 5 | Document pitfalls | What mistakes do sophisticated practitioners make? |
| 6 | Show integration | How does this framework connect to others? |
| 7 | Write with specificity | Every instruction must be actionable |

---

## Task Section Format

Each task must follow this structure:

```markdown
## Task [N]: [Task Name]

**Goal:** [One sentence: what this task accomplishes]

**Inputs:** [What you need before starting this task]

| Input | Source | Required |
|-------|--------|----------|
| [Input name] | [Where it comes from] | Yes/No |

**Action:**

1. [First concrete action step]
2. [Second concrete action step]
3. [Continue with all action steps]
   - [Sub-steps if needed for clarity]
   - [Keep granular enough to be actionable]

**Output:** [What you produce from this task]

| Output | Format | Purpose |
|--------|--------|---------|
| [Output name] | [Document type, artifact] | [Why it matters] |

**Validation:**

How to know you're done correctly:

- [ ] [First validation criterion]
- [ ] [Second validation criterion]
- [ ] [Continue with all criteria]
```

---

## Writing Standards

### Language and Tone

| Standard | Description |
|----------|-------------|
| **Direct, no fluff** | Eliminate unnecessary words; get to the point |
| **Imperative mood** | "Write the press release" not "You should write" |
| **Precise terminology** | Use correct business terms; don't dumb down |
| **Honest about difficulty** | Don't pretend hard things are easy |
| **Opinionated** | State what works; framework guides are not neutral surveys |

### Depth vs. Brevity

- **Prioritize completeness over brevity** — if a task requires 20 action steps, list all 20
- **Context matters** — provide enough context for sophisticated practitioners to understand why
- **No artificial limits** — a framework guide can be 500+ lines if needed
- **But eliminate waste** — every sentence must earn its place

### Pitfalls Section Requirements

The Pitfalls section teaches through negative requirements—what NOT to do.

**What to include:**
- Mistakes sophisticated practitioners make (not beginner errors)
- Trade-offs that look attractive but backfire
- Common misinterpretations of the framework
- When NOT to use this framework

**What to exclude:**
- Basic mistakes (e.g., "don't skip validation")
- Generic advice (e.g., "quality matters")
- Obvious cautions

**Format:**

```markdown
## Pitfalls

**[Pitfall Name]**

[Description of the mistake, why it's tempting, why it fails. 2-4 sentences.]

**Example:** [Concrete illustration if helpful]

**Instead:** [What to do instead]
```

---

## Integration Section Requirements

The Integration section shows how this framework connects to others in the milestone and across milestones.

**What to include:**
- Which frameworks must complete before this one
- Which frameworks build on this one's outputs
- How outputs map to inputs of subsequent frameworks
- Optional: visual diagram showing flow

**Format:**

```markdown
## Integration

**Prerequisites:** [Which frameworks must complete first]

**Builds on:**
- [Framework name] — [Specific output used as input]

**Feeds into:**
- [Framework name] — [Specific output that becomes input]

**Workflow Position:**

[Visual representation of framework position in milestone flow]
```

---

## AI Agent Instructions

Include this section in the template content (the part agents will read in instances):

```markdown
## For AI Agents

**Template reference:** This document was created from [`meta_business_framework.md`](../../../system/founder/templates/meta_business_framework.md). Agents MUST read the template before making updates.

**Execution context:** When executing this framework with a user:

1. Read this framework guide completely before starting
2. Track progress: "Currently in Task [N]: [Task Name]"
3. Do not skip validation—confirm each task's validation criteria before proceeding
4. Reference the milestone process document for step-level context
5. Update the founder log with key decisions and insights as they emerge

**Working with tasks:**
- Each task is atomic—complete it fully before moving to the next
- If a task's validation criteria cannot be met, surface this immediately
- Task outputs become inputs to subsequent tasks—maintain traceability
```

---

## Validation Checklist

Before finalizing a framework guide, verify:

- [ ] Purpose statement clearly defines what framework accomplishes
- [ ] Context explains when in milestone and prerequisites
- [ ] Framework Overview provides origin and principles (2-3 paragraphs)
- [ ] Task Structure table lists all tasks with Goal, Inputs, Outputs
- [ ] Each task has: Goal, Inputs table, Action steps, Output table, Validation checklist
- [ ] Pitfalls section includes sophisticated warnings (not basic tips)
- [ ] Integration section shows framework connections with Prerequisites and Feeds into
- [ ] Success Criteria provides clear completion checklist
- [ ] All action steps are executable (no vague guidance)
- [ ] Language is direct, precise, opinionated
- [ ] Last updated footer uses ISO 8601 format (`*Last updated: YYYY-MM-DD*`)

---

## Examples of Good vs. Bad

### Action Steps

**Bad (vague):**
> "Think about your customer."

**Good (executable):**
> "List 5 specific customer segments. For each segment, document: job title, company size, current tools used, annual budget for this problem area."

### Validation Criteria

**Bad (ambiguous):**
> "Customer is well-defined."

**Good (testable):**
> "You can name 3 real companies matching this customer profile. You can describe what triggers their need to search for a solution. You can estimate their willingness to pay within an order of magnitude."

### Pitfalls

**Bad (basic):**
> "Don't skip customer research."

**Good (sophisticated):**
> "**Pitfall: Conflating early adopters with mainstream customers.** Your first 10 enthusiastic customers may love your solution for reasons unrelated to your core value proposition. They'll tolerate rough edges mainstream customers won't. Validating with early adopters creates false confidence in product-market fit. Instead: Explicitly segment early adopters vs. mainstream; test different messaging and value props with each; don't assume learnings transfer."

---

## References

| Document | Why Consult |
|----------|-------------|
| [founder_process.md](../founder_process.md) | Understand milestone structure and glossary |
| [conception_process.md](m1_conception/conception_process.md) | Example of step-level process document |
| [meta_template.md](../ai_pro/my_cursor/meta_template.md) | General template structure standards |
| [index.md](../map/index.md) | Navigate to other system documents |

---

<!-- DOCUMENT CONTENT BELOW — Copy from here -->

# [Framework Name]

**Purpose:** [One sentence: what this framework accomplishes]

**Context:** [When in milestone process this framework is applied; which step; prerequisites]

---

## Framework Overview

[2-3 paragraphs describing:
- Origin of framework (who created it, when, why)
- Core principles and key insights
- Why it matters for this milestone
- What makes this framework powerful]

---

## Task Structure

High-level view of framework execution:

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. [Task Name] | [What this task accomplishes] | [Primary inputs] | [Primary outputs] |
| 2. [Task Name] | [What this task accomplishes] | [Primary inputs] | [Primary outputs] |
| 3. [Task Name] | [What this task accomplishes] | [Primary inputs] | [Primary outputs] |

[Continue for all tasks]

---

## Task 1: [Task Name]

**Goal:** [One sentence: what this task accomplishes]

**Inputs:** [What you need before starting this task]

| Input | Source | Required |
|-------|--------|----------|
| [Input name] | [Where it comes from—prior framework, user knowledge, research] | Yes/No |
| [Input name] | [Where it comes from] | Yes/No |

**Action:**

1. [First concrete, executable action step]
2. [Second concrete, executable action step]
3. [Continue with all action steps needed to complete this task]
   - [Sub-steps if needed for clarity]
   - [Keep granular enough to be actionable without ambiguity]

**Output:** [What you produce from this task]

| Output | Format | Purpose |
|--------|--------|---------|
| [Output name] | [Document type, artifact, decision] | [Why it matters, who uses it] |
| [Output name] | [Format] | [Purpose] |

**Validation:**

How to know you're done correctly:

- [ ] [First validation criterion—must be testable/verifiable]
- [ ] [Second validation criterion]
- [ ] [Continue with all criteria needed to confirm task completion]

---

## Task 2: [Task Name]

[Repeat Task 1 structure for each task]

---

[Continue with all tasks]

---

## Pitfalls

What NOT to do—sophisticated warnings for experienced practitioners.

**[Pitfall Name]**

[Description of the mistake: why it's tempting, why it fails, what the consequences are. 2-4 sentences.]

**Example:** [Concrete illustration if it clarifies]

**Instead:** [What to do instead—the correct approach]

---

**[Pitfall Name]**

[Repeat structure for each major pitfall]

---

[Continue with all significant pitfalls]

---

## Integration

**Prerequisites:** [Which frameworks or steps must complete before this framework can be executed]

**Builds on:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| [Framework name] | [Specific output] | [How this framework uses that output] |

**Feeds into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| [Framework name] | [Output from this framework] | [How subsequent framework uses it] |

**Workflow Position:**

[Optional: Diagram or text description showing where this framework sits in milestone flow]

```
[Prior Framework] → [This Framework] → [Next Framework]
        ↓                   ↓                   ↓
    [Output]           [Output]            [Output]
```

---

## Success Criteria

This framework is complete when:

- [ ] [First completion criterion]
- [ ] [Second completion criterion]
- [ ] [Continue with all criteria that must be met]
- [ ] All task validation criteria have been met
- [ ] Outputs are documented and accessible
- [ ] Key decisions and insights recorded in founder log

---

## References

[Optional but recommended: Source materials, books, papers, case studies]

| Source | Type | Notes |
|--------|------|-------|
| [Author], *[Title]* | Book/Paper/Article | [Key insights or chapters] |

---

## For AI Agents

**Template reference:** This document was created from [`meta_business_framework.md`](../../../system/founder/templates/meta_business_framework.md). Agents MUST read the template before making updates.

**Execution context:** When executing this framework with a user:

1. Read this framework guide completely before starting
2. Track progress: "Currently in Task [N]: [Task Name]"
3. Do not skip validation—confirm each task's validation criteria before proceeding
4. Reference the milestone process document for step-level context
5. Update the founder log with key decisions and insights as they emerge

**Working with tasks:**
- Each task is atomic—complete it fully before moving to the next
- If a task's validation criteria cannot be met, surface this immediately
- Task outputs become inputs to subsequent tasks—maintain traceability

---