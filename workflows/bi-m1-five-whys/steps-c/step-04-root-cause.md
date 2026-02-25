---
name: 'step-04-root-cause'
description: 'Synthesize root causes and select structural levers to target'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/five-whys.md'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Root Cause Synthesis

**Progress: Step 4 of 5** — Next: Final Synthesis

---

## STEP GOAL

Convert raw 5 Whys chains into a concise Root Cause Map and decide which causes your initial concept will deliberately address (targeted) vs acknowledge but not tackle (non-targeted).

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for explicit decisions about what you're targeting vs ignoring. Challenge "we'll do everything" — force trade-offs.

### Step-Specific Rules
- At least one Non-Targeted Root Cause MUST be documented — you can't target everything
- Targeted causes must link to specific behaviours/metrics you expect to change
- Root Cause Statements must be about systems, not individuals
- Map every root cause back to Lean Canvas blocks

---

## CONTEXT BOUNDARIES

**Available context:**
- five-whys.md with completed 5 Whys chains and Root Cause Candidates
- Prior M1 artefacts for validation

**Out of scope:**
- Updating project-memo (Step 5)
- Designing M2 validation experiments (Step 5 seeds these)

---

## MANDATORY SEQUENCE

### 1. List Root Cause Candidates

Extract all Root Cause Candidates from chain endpoints:

> "From your 5 Whys chains, here are the root cause candidates:
> 1. [Candidate from Chain 1 terminal node]
> 2. [Candidate from Chain 2 terminal node] (if applicable)
> 3. ..."

Ask: "Are there any causes we missed that became apparent during the analysis?"

### 2. Categorize Root Causes

Cluster root causes into categories:

| Category | Description | Your Causes |
|----------|-------------|-------------|
| Customer behaviour and context | Habits, incentives, skills, workflows | ... |
| Product and UX | Discovery, onboarding, feedback loops | ... |
| Business model and pricing | Misaligned incentives, approval cycles | ... |
| Go-to-market and channels | Wrong decision-maker, weak trust signals | ... |
| Organisation and operations | Internal bottlenecks, silos | ... |
| External constraints | Regulation, vendor lock-in, platform risk | ... |

Present categorization and ask: "Does this grouping make sense? Any recategorizations?"

### 3. Define Root Cause Statements

For each cluster, draft a Root Cause Statement (1-2 sentences):

Requirements:
- Describes what is structurally true about the world that creates symptoms
- Avoids blaming individuals — focuses on systems, incentives, constraints
- Is actionable or at least addressable

Present each statement:
> "Root Cause [N]: [Statement]
> This explains why [upstream symptoms] occur."

Confirm with founder before proceeding.

### 4. Map to M1 Artefacts

For each Root Cause Statement, map back:

| Root Cause | Already in M1? | Location | Contradicts/Refines |
|------------|----------------|----------|---------------------|
| RC1 | Yes/No | PR/FAQ, JTBD, PSF, LC block | What it challenges |
| RC2 | Yes/No | ... | ... |

Ask:
> "Which root causes are NEW insights vs already implicit in your M1 work?"

### 5. Select Targeted vs Non-Targeted

Present the decision framework:

> "Now we decide which root causes your initial product will TARGET vs which you'll ACKNOWLEDGE but not tackle in v1.
>
> Consider:
> - Addressability: Can your solution actually move this lever?
> - Scope: Is it feasible in initial version?
> - Impact: Does fixing this cause meaningful behaviour change?"

For each root cause, ask:
- "Will you target this in v1, or acknowledge it as a limitation?"
- If targeted: "What specific behaviour or metric do you expect to change?"
- If non-targeted: "What's your rationale for not addressing this now?"

### 6. Draft Root Cause Map

Create the Root Cause Map table:

| ID | Root Cause Statement | Category | Targeted? | Related Lean Canvas Blocks | Evidence Status |
|----|---------------------|----------|-----------|---------------------------|-----------------|
| RC1 | ... | Customer behaviour | Yes | Problem, Segments | Mostly Fact |
| RC2 | ... | Product/UX | Yes | Solution, UVP | Mixed |
| RC3 | ... | External | No (v1 limitation) | — | Hypothesis |

### 7. Draft Targeted Root Cause Hypotheses

For each TARGETED root cause, create a hypothesis:

**Format:**
> "If we [intervention], we expect [root cause] to shift, as evidenced by [behaviour/metric change]."

Example:
> "If we automate data consolidation, we expect users to complete onboarding 50% faster, as evidenced by setup completion rates within first 7 days."

List 3-5 Targeted Root Cause Hypotheses.

### 8. Document Non-Targeted Causes

For each NON-TARGETED root cause, document:

| Root Cause | Why Not Targeted | Implication for v1 |
|------------|------------------|---------------------|
| RC3 | Requires regulatory change we can't influence | Users must work around this manually |
| RC4 | Beyond technical scope for initial version | Future feature candidate |

### 9. Validation Checklist

Before proceeding, confirm:
- [ ] At least one Root Cause Statement is non-obvious compared to initial problem
- [ ] Each Targeted Root Cause Hypothesis links to specific behaviours/metrics
- [ ] At least one Non-Targeted Root Cause is documented
- [ ] All root causes map to Lean Canvas blocks where applicable

If any fail, iterate before continuing.

### 10. Update Output Document

Update five-whys.md with:

```markdown
## Root Cause Map

| ID | Root Cause Statement | Category | Targeted? | Lean Canvas Blocks | Evidence |
|----|---------------------|----------|-----------|-------------------|----------|
| RC1 | ... | ... | Yes | ... | F/H |
| ... | ... | ... | ... | ... | ... |

## Targeted Root Cause Hypotheses

1. **[RC1]:** If we [intervention], we expect [outcome], as evidenced by [metric].
2. **[RC2]:** If we [intervention], we expect [outcome], as evidenced by [metric].
3. ...

## Non-Targeted Root Causes (v1 Limitations)

| Root Cause | Why Not Targeted | v1 Implication |
|------------|------------------|----------------|
| RC3 | ... | ... |
| ... | ... | ... |
```

### 11. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine root cause statements or targeting decisions
- **[P] Party Mode** — get multi-perspective challenge on targeting choices
- **[C] Continue** — proceed to Final Synthesis

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure Root Cause Map and Hypotheses are saved
2. Update frontmatter: add `step-04-root-cause` to `stepsCompleted`
3. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Root causes categorized and mapped, targeted vs non-targeted decisions made with rationale, hypotheses link to measurable outcomes, non-targeted causes documented

❌ **FAILURE:** No non-targeted causes documented, hypotheses lack metrics, root causes blame individuals, "we'll target everything" accepted
