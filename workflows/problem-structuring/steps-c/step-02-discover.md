---
stepNumber: 2
stepId: discover
nextStepFile: ./step-03-structure.md
---

# Step 2: Framework Selection & Deep Discovery

**Goal:** Select appropriate framework(s) and gather deep context through structured questioning.

---

## MANDATORY SEQUENCE

### 1. Load Knowledge Files

Load and internalize these framework files:
- `data/pyramid-principle.md`
- `data/mece-framework.md`
- `data/problem-trees.md`

### 2. Framework Selection

Based on the problem type identified in Step 1, recommend framework combination:

| Problem Type | Primary Framework | Supporting Framework |
|--------------|-------------------|----------------------|
| **Diagnostic** ("Why is this happening?") | Problem Tree (diagnostic) | MECE for branch validation |
| **Solution-seeking** ("How can we solve this?") | Problem Tree (solution-focused) | Pyramid for recommendation |
| **Decision** ("Should we do X?") | Problem Tree (decision) | Pyramid for communication |

Present recommendation:
> "For your [problem type] problem, I recommend using [primary framework] as our main tool, supported by [supporting framework]. Here's why: [brief rationale]."

### 3. Generate Question Bank

Generate 15-20 questions to understand the problem deeply. Organize by category:

**Categories:**
- **Root Cause:** Why is this happening? What's the underlying issue?
- **Impact:** Who/what is affected? How severe? What's the cost of inaction?
- **Context:** What's been tried? What constraints exist? What resources available?
- **Success Criteria:** What does "solved" look like? How will we measure?
- **Stakeholders:** Who decides? Who influences? Who implements?

### 4. Curate Questions

From the 15-20 questions:
1. Remove low-impact questions
2. Identify dependencies (which answers unlock other questions)
3. Sequence by priority

### 5. Iterative Questioning

Conduct 2-3 rounds of questioning:

**Round 1:** 4-5 highest-impact questions
**Round 2:** 3-4 follow-up questions based on answers
**Round 3:** 2-3 clarification questions

For each question:
- Present with 2-3 possible answer options when helpful
- Accept user's answer
- Note implications for problem structure

### 6. Synthesize Discoveries

Summarize what you've learned:

> "From our discussion, here's what I understand:
> - **Core Issue:** [synthesis]
> - **Key Drivers:** [list 2-4]
> - **Constraints:** [list]
> - **Success Looks Like:** [definition]
>
> Have I captured this accurately?"

Update output document with discoveries under a new section:

```markdown
## Deep Context

### Key Discoveries
{Numbered list of important findings}

### Constraints Identified
{List of constraints}

### Success Criteria
{What "solved" looks like}
```

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 3: Structure the Problem |
| **[MQ] More Questions** | Additional questioning round |
| **[AE] Advanced Elicitation** | Deep-dive into a specific area |
| **[R] Revise** | Correct any misunderstandings |

---

## ON CONTINUE

1. Update output document frontmatter: add "step-02-discover" to `stepsCompleted`
2. Save output document
3. Load `./step-03-structure.md`
