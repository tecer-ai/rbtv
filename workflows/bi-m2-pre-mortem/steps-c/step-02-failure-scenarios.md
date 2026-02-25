---
name: 'step-02-failure-scenarios'
description: 'Brainstorm failure modes across 7 categories using prospective hindsight'
nextStepFile: './step-03-risk-ranking.md'
outputFile: '{outputFolder}/pre-mortem.md'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Brainstorm Failure Scenarios

**Progress: Step 2 of 5** — Next: Risk Ranking

---

## STEP GOAL

Generate the fullest possible list of plausible failure reasons across all 7 categories without filtering, editing, or debating. Use prospective hindsight framing throughout.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor conducting a pre-mortem. Maintain past-tense framing: "We failed because..." not "We might fail if..." Correct the user if they slip into conditional language.

### Step-Specific Rules
- MUST maintain prospective hindsight frame throughout — failure is a fact, not a possibility
- MUST NOT filter, dismiss, or merge failure modes during brainstorming
- MUST draw explicitly from all M2 framework outputs before asking for additional brainstorming
- If user says "that would never happen," respond: "In this exercise, it already did. Let's keep it and rank it later."
- Minimum target: 15 failure modes across at least 5 of 7 categories

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/pre-mortem.md` for current state
2. Read all M2 framework outputs:
   - `{outputFolder}/leap-of-faith.md` — kill criteria, high-risk assumptions
   - `{outputFolder}/assumption-mapping.md` — "Test" and "Accept" quadrants
   - `{outputFolder}/tam-sam-som.md` — market sizing gaps, segment risks
   - `{outputFolder}/unit-economics.md` — sensitivity points, break-even risks
   - `{outputFolder}/technology-readiness-level.md` — low-TRL components, technical unknowns

---

## MANDATORY SEQUENCE

### 1. Set the Failure Prompt

Write the failure prompt establishing the prospective hindsight frame:

> "It is [date 12 months from now]. {Project Name} has failed. The product never reached product-market fit. The team has disbanded. Funding ran out or was not secured. We are now conducting a post-mortem to understand why."

Present to user and confirm the time horizon (default 12 months; adjust to 6 for very early concepts or 18 for complex ventures).

### 2. Display Category Checklist

Present the 7 failure categories:

| Category | Failure Mode Focus |
|----------|-------------------|
| **Market** | Customers don't exist, don't care, or can't be reached |
| **Product** | Solution doesn't solve problem, is unusable, or not differentiated |
| **Team** | Missing skills, founder conflict, burnout, key person leaves |
| **Financial** | Revenue too low, costs too high, funding not secured, cash runs out |
| **Technical** | Can't build it, performance inadequate, integration fails, security breach |
| **Competitive** | Incumbent responds, new entrant captures market, open-source alternative |
| **Operational** | Regulatory block, legal issue, partner dependency fails, scaling bottleneck |

### 3. Seed Failure Modes from M2 Frameworks

BEFORE asking user for brainstorming, propose failure modes derived from each M2 framework:

**From Leap of Faith:** Convert each kill criterion into a failure mode
- "Kill criterion X was triggered because..."

**From Assumption Mapping:** Convert each "Test" assumption into a failure mode
- "We assumed X, but it turned out..."

**From TAM/SAM/SOM:** Convert market sizing gaps into failure modes
- "The market was actually 10x smaller because..."

**From Unit Economics:** Convert sensitivity points into failure modes
- "CAC was 3x higher than modeled because..."

**From TRL:** Convert technical risks into failure modes
- "Component X never reached TRL 6 because..."

Present seeded failure modes and ask: "What additional failure scenarios come to mind?"

### 4. Collaborative Brainstorming

For each category not yet covered:
- Prompt: "In the {category} category, what caused the failure?"
- Enforce past-tense framing
- Push for specifics: reject "market risk" → demand "what specifically about the market?"

Write each failure mode as:
> "{Category}: We failed because [concrete past-tense explanation]."

Example:
> "Financial: We failed because enterprise buyers required 90-day payment terms while our suppliers required 30-day payment, creating a cash flow crisis we couldn't fund."

### 5. Validate Completeness

Check coverage:
- [ ] At least 15 failure modes total
- [ ] At least 5 of 7 categories represented
- [ ] Every Leap of Faith kill criterion appears as a failure mode
- [ ] All failure modes are concrete past-tense explanations

If under 15 modes:
> "We have [N] failure modes. Let's push harder on underrepresented categories: [list categories with few/no modes]."

### 6. Compile Raw Failure Mode Inventory

Present the complete numbered list:

```markdown
## Raw Failure Mode Inventory

### Market (N modes)
1. We failed because...
2. We failed because...

### Product (N modes)
...

### Team (N modes)
...

### Financial (N modes)
...

### Technical (N modes)
...

### Competitive (N modes)
...

### Operational (N modes)
...

**Total: [N] failure modes across [N] categories**
```

### 7. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — add more failure modes to specific categories
- **[P] Party Mode** — get multi-agent perspectives on hidden risks
- **[C] Continue** — proceed to Risk Ranking

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update pre-mortem.md with Failure Prompt and Raw Failure Mode Inventory
2. Update frontmatter: add `step-02-failure-scenarios` to `stepsCompleted`
3. Load `./step-03-risk-ranking.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 15+ failure modes across 5+ categories, all written as concrete past-tense explanations, no filtering during brainstorming

❌ **FAILURE:** Filtering/dismissing modes during brainstorming, accepting vague category-level failures, fewer than 15 modes
