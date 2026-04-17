---
name: 'step-04-gap-analysis'
description: 'Design spike cards for low-TRL components'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/technology-readiness-level.md'
---

# Step 4: Gap Analysis (Spike Design)

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

Design technical spike cards for every component below TRL 4, defining what must be proven, how, and with what success/failure criteria. Sequence spikes by priority.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Keep spikes focused on ONE question with minimum effort. If a spike exceeds 2 weeks, it's too broad — split it.

### Step-Specific Rules
- MUST create spike card for every component with TRL < 4
- MUST also create spikes for TRL 4-5 components with 3+ high-uncertainty risks
- Each spike MUST have measurable success AND failure criteria
- Spike effort MUST be realistic (typically person-days, not months)
- At least one spike MUST connect failure criteria to a kill criterion

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/technology-readiness-level.md` for components and risks
2. Review components flagged for spikes in Step 3
3. Review Leap of Faith kill criteria (if available)

---

## MANDATORY SEQUENCE

### 1. Identify Components Needing Spikes

From Step 3, list components requiring spikes:

| ID | Name | Current TRL | Target TRL | Reason for Spike |
|----|------|-------------|------------|------------------|
| TC-XX | [Name] | [1-3] | [4-5] | TRL below 4 |
| TC-YY | [Name] | [4-5] | [5] | 3+ high-uncertainty risks |
| ... | ... | ... | ... | ... |

**If no components below TRL 4:**
> "All components are at TRL 4 or above. No technical spikes are required before M4 Prototypation.
>
> You still have [N] residual technical risks to track, but the technical foundation is solid enough to proceed."

Document this finding and skip to Step 7.

### 2. Create Spike Cards

For each component needing a spike, create a spike card:

```markdown
---
## Spike Card: [Component ID]

**Component:** [Name]
**Current TRL:** [X]
**Target TRL:** [4 or 5]

### Key Question
Can we [specific capability] with [specific constraints]?

### Method
Select lightest-weight approach that produces credible evidence:
- [ ] Build minimal proof-of-concept
- [ ] Run benchmark against representative data/load
- [ ] Evaluate third-party service/library
- [ ] Consult domain expert for feasibility assessment
- [ ] Analyze comparable implementations

### Success Criteria
[Specific, measurable outcomes that advance TRL]

Examples:
- "Model achieves 85% accuracy on 500-sample test set"
- "API handles 200 req/sec with <500ms p95 latency"
- "Third-party service meets all 5 integration requirements"

### Failure Criteria
[What result would indicate this component cannot be built as conceived]

Connect to kill criteria where applicable:
- "If accuracy < 70%, revisit core approach"
- "If latency > 2s, architecture is non-viable"

### Estimated Effort
[Person-days or person-weeks]
Rule: If > 2 weeks, split into smaller spikes

### Dependencies
- [ ] [Other spikes that must complete first]
- [ ] [Data or access needed]
- [ ] [Resources required]

### Owner
[Who executes this spike]

### Downstream Framework
Which M2 framework receives the results:
- [ ] Pre-mortem (if failure mode)
- [ ] Assumption Mapping (if uncertain assumption)
---
```

### 3. Ensure Kill Criteria Connection

At least one spike card MUST connect to a kill criterion:

> "Which spike, if it fails, would cause you to abandon or pivot the core approach?"

If no spike connects to kill criteria, identify which failure would be fatal and add connection.

### 4. Validate Spike Scope

For each spike, check scope:

**If estimated effort > 2 weeks:**
> "This spike is scoped at [X] weeks. That's too broad — spikes answer ONE specific question with minimum effort.
>
> Split into smaller questions:
> 1. [Focused question 1]
> 2. [Focused question 2]"

Help user split large spikes.

### 5. Sequence Spikes

Order by priority:

| Priority | Spike | Reason |
|----------|-------|--------|
| 1 | [Spike for TC-XX] | Critical path — blocks others |
| 2 | [Spike for TC-YY] | Highest uncertainty |
| 3 | [Spike for TC-ZZ] | Quick win — fast to resolve |
| ... | ... | ... |

**Sequencing Rules:**
1. Critical path first (blocks other components)
2. Highest uncertainty next (most dangerous unknowns)
3. Quickest wins last (when equal priority, faster first)

**Parallelization:**
Note which spikes can run in parallel (no dependencies):

| Parallel Track A | Parallel Track B |
|-----------------|-----------------|
| Spike 1 | Spike 2 |
| Spike 4 (after 1) | Spike 3 (after 2) |

### 6. Calculate Total De-Risking Effort

Sum all spike efforts:

| Metric | Value |
|--------|-------|
| Total spikes | [N] |
| Total effort (person-days) | [X] |
| Total effort (calendar weeks) | [Y] with parallelization |
| Team capacity | [Z] person-days/week |
| De-risking timeline | [W] weeks |

**Reality Check:**
> "Total technical de-risking requires [X] person-days, approximately [Y] weeks with your team.
>
> [If > 4 weeks]: This is significant de-risking work. Consider whether this validates or questions your technical approach."

### 7. Update Output Document

Update technology-readiness-level.md with:
- List of components needing spikes (or "None required")
- All spike cards
- Spike sequence with priorities
- Parallelization options
- Total de-risking effort estimate

Update frontmatter: add `step-04-gap-analysis` to `stepsCompleted`

### 8. Present Menu Options

**Summary:**
> "Spike cards created: [N]
> - Total effort: [X] person-days
> - Estimated timeline: [Y] weeks
> - Critical path spikes: [N]
> - Connected to kill criteria: [N]"

**Select an Option:**
- **[C] Continue** — proceed to Synthesis
- **[R] Refine** — revisit spike designs

ALWAYS halt and wait for user selection.

---

## VALIDATION CHECKLIST

Before proceeding, verify:
- [ ] Every component below TRL 4 has a spike card
- [ ] Each spike has measurable success AND failure criteria
- [ ] Spike methods are lightest-weight credible approach
- [ ] No spike exceeds 2 weeks estimated effort
- [ ] Spike sequence respects dependency chains
- [ ] At least one spike connects to a kill criterion

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all validation checklist items pass
2. Ensure technology-readiness-level.md is updated
3. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Focused spike cards with measurable criteria, realistic effort, proper sequencing

❌ **FAILURE:** Vague "see if it works" criteria, month-long spikes, no kill criteria connection
