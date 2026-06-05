---
name: 'step-02-discover'
description: 'Clarify customer and problem through structured questioning'
nextStepFile: './step-03-press-release.md'
outputFile: '{outputFolder}/working-backwards.md'
---

# Step 2: Customer & Problem Discovery

**Progress: Step 2 of 5** — Next: Draft Press Release

---

## STEP GOAL

Produce a concise, evidence-informed Customer & Problem Brief that clearly defines WHO we serve and WHAT hurts, without mentioning our solution.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Challenge vague answers. Push for names, numbers, and specifics. Reject "everyone" and "anyone who..." as customer definitions.

### Step-Specific Rules
- Problem statement must NOT mention the solution
- Customer definition must be specific enough to find 3 real examples
- Keep questioning until the founder can articulate clearly without prompting
- Do NOT draft the Press Release in this step — that's Step 3

---

## EXECUTION PROTOCOLS

1. Load project context from project-memo and step-01 outputs
2. Run structured questioning sequence
3. Draft Customer & Problem Brief collaboratively
4. Validate with checklist before proceeding

---

## MANDATORY SEQUENCE

### 1. Idea Synopsis

Ask the founder:
> "In one paragraph, describe: Who do you think you serve? What do you imagine building? Why now?"

Wait for response. Probe for clarity:
- If vague: "Can you name a specific company or person who fits this?"
- If solution-focused: "Let's step back — what's the problem they have today?"

### 2. Customer Segment Enumeration

Ask:
> "Let's map out 3-5 possible customer segments. For each, tell me:
> - Job title or role
> - Company size and industry
> - Geographic or usage context"

Create a table from responses:

| Segment | Job Title | Company Profile | Context |
|---------|-----------|-----------------|---------|
| 1 | ... | ... | ... |
| 2 | ... | ... | ... |
| 3 | ... | ... | ... |

### 3. Segment Deep Dive

For each segment, ask:
> "For [Segment N]:
> 1. What job are they trying to get done in their own words?
> 2. What workarounds or alternatives do they use today?
> 3. What's the most painful friction or failure mode?"

Challenge weak answers:
- "That sounds generic — can you give me a specific example?"
- "Who loses money or time when this goes wrong?"

### 4. Primary Segment Selection

Present criteria:
> "Let's pick one primary segment for this PR/FAQ. Consider:
> - Pain intensity and frequency
> - Willingness and ability to pay
> - Ease of reaching them for validation"

Ask: "Which segment should we focus on first, and why?"

### 5. Draft Customer & Problem Brief

Collaboratively draft (max 1 page):

**Primary Customer:**
*(One sentence describing who they are)*

**Their Context:**
*(One paragraph about their situation)*

**Problem Statement:**
*(Clearly worded problem that does NOT mention your solution)*

**Examples in the Wild:**
1. *(Concrete example)*
2. *(Concrete example)*
3. *(Concrete example)*

**Current Alternatives:**
- *(Alternative 1)*
- *(Alternative 2)*

### 6. Validation Checklist

Before proceeding, confirm:
- [ ] Can name at least 3 real organizations/people who fit the customer description
- [ ] Problem statement makes sense without mentioning product
- [ ] Founder can paraphrase the customer and problem without prompting
- [ ] At least 2 current alternatives listed

If any fail, iterate before continuing.

### 7. Update Output Document

Update working-backwards.md with completed Customer & Problem Brief section.

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Draft Press Release

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append Customer & Problem Brief to working-backwards.md
2. Update frontmatter: add `step-02-discover` to `stepsCompleted`
3. Load `./step-03-press-release.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Customer & Problem Brief completed with specific examples, validation checklist passed

❌ **FAILURE:** Accepting vague customer definitions, problem statement mentions solution, skipping validation
