---
name: 'step-02-customer-problem'
description: 'Populate Problem, Customer Segments, and Early Adopters blocks'
nextStepFile: './step-03-value-solution.md'
outputFile: '{outputFolder}/lean-canvas.md'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Customer & Problem Blocks

**Progress: Step 2 of 6** — Next: Value & Solution Blocks

---

## STEP GOAL

Populate the **Problem**, **Customer Segments**, and **Early Adopters** blocks using prior framework outputs, not fresh brainstorming.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Reject generic problem statements. Push for customer language, not feature gaps. Early Adopters must be specific enough to find 3 real examples.

### Step-Specific Rules
- Problem statements MUST NOT mention your solution
- Every problem must trace to JTBD or PSF output
- Customer Segments must match those used in PSF
- Early Adopters are a narrower slice of primary segment

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/working-backwards.md` — Customer & Problem Brief
2. Read `{outputFolder}/jobs-to-be-done.md` — job stories and forces
3. Read `{outputFolder}/problem-solution-fit.md` — problem brief
4. Read `./data/lean-canvas-framework.md` — block guidance

---

## MANDATORY SEQUENCE

### 1. Extract Problem Candidates

From prior frameworks, list problem candidates:

> "Let me pull the problems documented in your prior work..."

**From JTBD:**
- Push forces (current situation pain)
- Anxieties (barriers to change)

**From PSF:**
- Problem brief statements
- Triggers and constraints

**From Working Backwards:**
- Problem paragraph from PR

Present consolidated list: "Here are the problems we've identified..."

### 2. Select Top 3 Problems

Ask:
> "From these candidates, let's pick the **top 3 problems** for your Lean Canvas. For each:
> - Express in **customer language** (how they describe it)
> - Note **frequency** (how often it occurs)
> - Note **severity** (consequences if unsolved)
>
> Which 3 problems are most critical for your primary segment?"

Challenge weak answers:
- "That sounds like a feature gap — what's the actual pain?"
- "Who loses money or time when this happens?"

### 3. Draft Problem Block

Collaboratively draft:

```markdown
## 1. Problem

| # | Problem Statement | Frequency | Severity |
|---|-------------------|-----------|----------|
| 1 | [Customer language] | [Daily/Weekly/Monthly] | [High/Medium] |
| 2 | [Customer language] | [Daily/Weekly/Monthly] | [High/Medium] |
| 3 | [Customer language] | [Daily/Weekly/Monthly] | [High/Medium] |

**Existing Alternatives:**
- [Alternative 1 — how they solve it today]
- [Alternative 2 — another workaround]
```

### 4. Define Customer Segments

Ask:
> "Let's define your **primary customer segment**. From your PSF and JTBD work:
> - **Role/Title**: Who owns this problem?
> - **Organization**: What type/size company?
> - **Context**: What situation triggers the problem?
>
> Is this consistent with your Working Backwards customer definition?"

### 5. Define Early Adopters

Ask:
> "Within that segment, who are your **Early Adopters** — the subset who:
> - Feel the pain most acutely
> - Have fewer internal constraints
> - Are more willing to try new solutions
>
> Be specific enough that we could find 3 real examples."

Challenge:
- "That's still too broad — what makes them different from the rest of the segment?"
- "Can you name 3 companies or people who fit this description?"

### 6. Draft Customer Segments Block

Collaboratively draft:

```markdown
## 2. Customer Segments

**Primary Segment:**
[Role] at [Organization Type/Size] in [Geography/Industry]

**Context:**
[One paragraph describing their situation and why the problem matters now]

**Early Adopters:**
[Narrower slice] characterized by [specific traits that make them feel pain more acutely]

**Examples in the Wild:**
1. [Concrete example — can be named or archetypal]
2. [Concrete example]
3. [Concrete example]
```

### 7. Tag Assumptions

Add to Assumptions List:

```markdown
## Assumptions List

### Problem Assumptions
- **P1**: [Problem 1] occurs [frequency] for segment — needs validation
- **P2**: [Problem 2] has severity [X] — needs validation
- **P3**: Existing alternatives are insufficient because [Y]

### Segment Assumptions
- **CS1**: Market has >[N] organizations fitting primary segment
- **CS2**: Early adopters make up [X]% of segment
```

### 8. Validation Checklist

Before proceeding, confirm:
- [ ] Each problem traces to at least one JTBD job story or PSF situation
- [ ] Problem statements do NOT mention your product
- [ ] Can name at least 3 real organizations/people who fit Early Adopters
- [ ] Primary segment matches PSF and Working Backwards definitions
- [ ] At least 2 existing alternatives listed

If any fail, iterate before continuing.

### 9. Update Output Document

Update lean-canvas.md with completed Problem and Customer Segments blocks.

### 10. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on problem definition or segment refinement
- **[P] Party Mode** — get multi-perspective challenge on blocks
- **[C] Continue** — proceed to Value & Solution blocks

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update lean-canvas.md with Problem and Customer Segments sections
2. Update frontmatter: add `step-02-customer-problem` to `stepsCompleted`
3. Load `./step-03-value-solution.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Problem block with 3 customer-language statements, Customer Segments with Early Adopters, all traced to prior frameworks, assumptions tagged

❌ **FAILURE:** Generic problem statements, solution-focused problems, segment too broad to find examples, no traceability to prior work
