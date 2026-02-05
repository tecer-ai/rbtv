---
name: 'step-05-synthesis'
description: 'Define validation signals, kill criteria, and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/leap-of-faith.md'
---

# Step 5: Synthesis & Kill Criteria

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Define observable validation signals for each top assumption, establish kill/pivot/persevere criteria, create a Validation Backlog wired to M2/M5 frameworks, and UPDATE project-memo.md.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Kill criteria that can never be triggered are not criteria — they're theatre. Force the founder to pre-commit to honest decision rules before sunk-cost bias sets in.

### Step-Specific Rules
- project-memo.md MUST be updated with Leap of Faith synthesis
- Kill criteria MUST be reachable within validation timeline — no "if zero customers want it" cop-outs
- Invalidation signals must be defined BEFORE validation signals (prevents confirmation bias)
- Every top assumption must map to at least one M2 or M5 validation activity

---

## CONTEXT BOUNDARIES

**Available context:**
- Complete leap-of-faith.md from Steps 1-4
- project-memo.md
- M2/M5 framework references

**Out of scope:**
- Actually running validation experiments (downstream frameworks)

---

## MANDATORY SEQUENCE

### 1. Define Validation Signals

For each top 5-10 assumption, create Validation Signal Spec:

**CRITICAL: Define invalidation signal FIRST to prevent confirmation bias.**

| Field | Question to Ask |
|-------|-----------------|
| Invalidation Signal | "What would prove this wrong?" |
| Validation Signal | "What would increase confidence this is true?" |
| Signal Threshold | "How much evidence is 'enough'?" |
| Collection Method | "How will we gather this signal?" |
| Timeline | "By when must we have this?" |
| Owner | "Who is responsible?" |

Example:
```markdown
### LOF-005: Product managers will pay $49/month

**Invalidation Signal:** Fewer than 3/10 interviewed PMs say they would pay $30+ for this
**Validation Signal:** At least 7/10 interviewed PMs say they would pay $49+ for this
**Threshold:** 10 SPIN Selling interviews with target segment
**Method:** SPIN Selling interviews (M5)
**Timeline:** End of M5 Market Validation
**Owner:** Founder
```

### 2. Establish Kill Criteria

**This is the most important part of the entire framework.**

Define three outcomes and triggers:

> "Let's pre-commit to decision rules before the data arrives:
>
> **KILL:** What combination of invalidated assumptions would stop the venture?
> Example: 'If the primary problem doesn't exist for 7+/10 interviewed customers AND market is below EUR 50M, we kill.'
>
> **PIVOT:** What distinguishes 'wrong solution' from 'wrong problem'?
> Example: 'If problem exists but our solution mechanism is wrong, we pivot approach. If problem doesn't exist, we kill.'
>
> **PERSEVERE:** What positive evidence (not just absence of negative) is required?
> Example: 'At least 7/10 Value signals validated AND Unit Economics shows plausible LTV:CAC > 3.'"

**Aggregate criteria:**
- How many Value assumptions can fail before killing?
- How many Growth assumptions can fail before pivoting the business model?
- Maximum time/money to invest before go/no-go decision?

**Decision Review Schedule:**
- When will you review evidence against criteria? (e.g., after each M2 framework, end of M2, end of M5)
- Who participates?
- What's the decision protocol?

### 3. Create Validation Backlog

Map each top assumption to downstream validation:

| ID | Assumption | M2/M5 Framework | Specific Activity | Status |
|----|------------|-----------------|-------------------|--------|
| LOF-005 | PMs will pay $49 | Unit Economics (M2) | Pricing sensitivity analysis | Not Started |
| LOF-005 | PMs will pay $49 | SPIN Selling (M5) | 10 customer interviews | Not Started |
| LOF-012 | Problem exists weekly | TAM/SAM/SOM (M2) | Segment sizing | Not Started |
| LOF-012 | Problem exists weekly | SPIN Selling (M5) | Problem discovery questions | Not Started |

**Framework mappings:**
- Assumption Mapping (M2): All assumptions plotted
- TAM/SAM/SOM (M2): Market Size, Channel Effectiveness
- Unit Economics (M2): Pricing, LTV, CAC, Retention Economics
- Pre-mortem (M2): Top assumptions become failure mode candidates
- SPIN Selling (M5): Problem Existence, Severity, Willingness to Switch
- Smoke Test (M5): Demand, Channel, Conversion

**Handoff notes:** For each mapping, write one-sentence directive:
> "TAM/SAM/SOM must validate LOF-012 (addressable market > EUR 100M for segment X); return estimate with confidence range."

### 4. Update leap-of-faith.md

Add final sections:

```markdown
## Validation Signal Specs

[Signal specs for each top assumption]

## Kill/Pivot/Persevere Criteria

**KILL if:**
[Explicit conditions]

**PIVOT if:**
[Explicit conditions]

**PERSEVERE if:**
[Explicit conditions with positive evidence required]

### Decision Review Schedule

| Review Point | Date | Participants | Protocol |
|--------------|------|--------------|----------|
| Post-Assumption Mapping | TBD | Founder + [advisor] | Review evidence, update rankings |
| End of M2 | TBD | Founder + [advisor] | Go/no-go on M3+ |
| End of M5 | TBD | Founder + [advisor] | Final persevere/pivot/kill |

## Validation Backlog

[Backlog table mapping assumptions to frameworks]

## Synthesis

### Key Findings

**Total Assumptions Harvested:** [N]
**Classified as Value Hypothesis:** [X]
**Classified as Growth Hypothesis:** [Y]
**Top Leap-of-Faith Assumptions:** [5-10]

### Top Bets Summary

1. [LOF-ID]: [One-sentence statement]
2. ...

### Kill Criteria Summary

We will **kill** if: [One-sentence summary]
We will **pivot** if: [One-sentence summary]
We will **persevere** if: [One-sentence summary]

### Next Steps

1. Complete Assumption Mapping (M2) to visualize the full matrix
2. Run TAM/SAM/SOM (M2) to validate market size assumptions
3. Build Unit Economics (M2) model to validate pricing/LTV/CAC assumptions
4. Run Pre-mortem (M2) using top assumptions as failure mode candidates
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-harvest', 'step-03-classify', 'step-04-prioritize', 'step-05-synthesis']
status: completed
```

### 5. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m2-leap-of-faith` to `stepsCompleted` array

**In Progress > M2 Validation section:**

```markdown
### Leap of Faith

**Status:** Completed

**Key Findings:**
- Harvested [N] assumptions from M1 frameworks
- Classified: [X] Value, [Y] Growth hypotheses
- Top [5-10] leap-of-faith assumptions identified

**Top Bets:**
1. [Assumption 1 one-liner]
2. [Assumption 2 one-liner]
3. [Assumption 3 one-liner]

**Kill Criteria:** [One-sentence summary of kill condition]

**Output:** [Link to leap-of-faith.md]
```

### 6. Completion Summary

Present to founder:

> "Leap of Faith analysis complete!
>
> **What we built:**
> - Harvested [N] assumptions from all M1 frameworks
> - Classified into [X] Value and [Y] Growth hypotheses
> - Identified top [5-10] leap-of-faith assumptions
> - Defined validation signals and kill criteria
> - Created Validation Backlog mapping to M2/M5 frameworks
>
> **Pre-committed decisions:**
> - Kill if: [summary]
> - Pivot if: [summary]
> - Persevere if: [summary]
>
> **Next recommended framework:** Assumption Mapping (visualize the full matrix)
>
> **Return path:** To continue other M2 frameworks, return to bi-m2 milestone workflow."

### 7. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine kill criteria or validation signals
- **[B] Back to M2** — return to M2 Validation milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M2** is selected:
1. Verify leap-of-faith.md has status: completed
2. Verify project-memo.md has Leap of Faith entry in M2 Validation
3. Load `../bi-m2/workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Validation signals defined for all top assumptions, kill criteria are reachable and explicit, Validation Backlog complete, project-memo.md updated

❌ **FAILURE:** project-memo.md not updated, kill criteria impossible to trigger, assumptions not mapped to downstream validation
