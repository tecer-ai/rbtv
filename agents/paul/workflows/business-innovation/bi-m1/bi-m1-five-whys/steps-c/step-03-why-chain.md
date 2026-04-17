---
name: 'step-03-why-chain'
description: 'Run 5 Whys chains, capture causal narrative, separate facts from hypotheses'
nextStepFile: './step-04-root-cause.md'
outputFile: '{outputFolder}/five-whys.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 3: Run 5 Whys Chains

**Progress: Step 3 of 5** — Next: Root Cause Synthesis

---

## STEP GOAL

Execute one or more 5 Whys chains, capturing a clear causal narrative and separating facts from assumptions to reach structural root causes.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Enforce single-threaded chains — reject topic jumps. Push past comfortable answers to structural causes. Demand evidence labelling.

### Step-Specific Rules
- Display session rules at start of every chain
- NEVER accept individual blame as an answer — redirect to systems
- Each chain must be single-threaded — fork into new chains if paths diverge
- Every answer MUST be labelled Fact or Hypothesis with evidence noted
- Push until you reach a structural cause or knowledge frontier

---

## CONTEXT BOUNDARIES

**Available context:**
- five-whys.md with Anchor Problem Statement and Scenario Brief
- Prior M1 artefacts for evidence

**Out of scope:**
- Synthesizing or categorizing root causes (Step 4)
- Selecting targeted levers (Step 4)

---

## MANDATORY SEQUENCE

### 1. Display Session Rules

Present the 5 Whys session rules:

> **5 WHYS SESSION RULES**
>
> 1. Focus on THIS scenario only — park other scenarios for separate chains
> 2. Blame processes, structures, incentives, assumptions — NEVER individuals
> 3. Each answer must be a DIRECT cause of the previous answer, not a different problem
> 4. Label every answer as **Fact** (data/observation) or **Hypothesis** (to validate)
> 5. Stop when you reach a structural cause that is actionable

Ask: "Ready to begin the first chain?"

### 2. Determine Chain Structure

Ask the founder:
> "For this scenario, are there multiple distinct symptoms (e.g., 'customers churn after month 1' AND 'sales cycles stall before contract')? If so, we may need separate chains."

Decide:
- If single main symptom: run one chain
- If multiple symptoms: plan one chain per symptom rooted in same Anchor Problem

### 3. Run First 5 Whys Chain

**Level 0: Problem Statement**
Write the Anchor Problem Statement as Level 0.

**Level 1:**
Ask: "Why is this problem happening in this scenario?"
- Wait for founder's answer
- Challenge if it blames a person: "That's about [person] — what's the system/process/incentive that creates this behaviour?"
- Ask: "Is this a Fact (you have data/observation) or Hypothesis (you believe it but haven't verified)?"
- If Fact: "What evidence supports this?"
- Record in chain table

**Levels 2-5+:**
For each level, ask: "Why is [previous answer] true in this scenario?"
- Reject answers that jump to different topics: "That's a different problem — let's stay on this causal thread"
- If founder strongly disagrees with direction, note a potential fork
- Continue labelling Fact/Hypothesis
- Stop when you hit:
  - A structural cause (incentives, processes, constraints) that explains upstream symptoms
  - Repetition (same idea, different words)
  - Knowledge frontier (all answers are untestable hypotheses)

### 4. Document Chain

Record the chain in table format:

| Level | Why Question | Answer | F/H | Evidence | Notes |
|-------|--------------|--------|-----|----------|-------|
| 0 | — | {Anchor Problem Statement} | — | — | — |
| 1 | Why is this problem happening? | ... | F/H | ... | ... |
| 2 | Why is [level 1] true? | ... | F/H | ... | ... |
| ... | ... | ... | ... | ... | ... |

**Identify Root Cause Candidate:**
Summarize the terminal node as a draft Root Cause Candidate in plain language.

### 5. Run Additional Chains (if needed)

If multiple symptoms were identified:
- Return to Level 0 with same Anchor Problem but different symptom expression
- Run chain following same process
- Document each chain separately

### 6. Chain Review

Present all chains and ask:
> "Let's review what we found:
> - Chain 1 terminal node: [summary]
> - Chain 2 terminal node: [summary] (if applicable)
>
> Which links are well-supported by data vs purely speculative?
> Do you see patterns where different chains converge on similar issues?"

Highlight:
- Strongest evidence links
- Convergence points across chains
- Knowledge frontiers requiring validation

### 7. Update Output Document

Update five-whys.md with:

```markdown
## 5 Whys Chains

### Session Rules Applied
{List the 5 rules}

### Chain 1: {Symptom}

| Level | Why Question | Answer | F/H | Evidence | Notes |
|-------|--------------|--------|-----|----------|-------|
| 0 | — | {Anchor} | — | — | — |
| ... | ... | ... | ... | ... | ... |

**Root Cause Candidate:** {Summary of terminal node}

### Chain 2: {Symptom} (if applicable)
{Same format}

### Chain Observations

**Strongest Evidence Links:**
- ...

**Convergence Points:**
- ...

**Knowledge Frontiers (to validate):**
- ...
```

### 8. Validation Checklist

Before proceeding, confirm:
- [ ] Each chain is a linear sequence of causes — no topic jumps
- [ ] Every answer is labelled Fact or Hypothesis with evidence noted
- [ ] At least one chain reaches a structural cause (not "users don't care" or "team is slow")
- [ ] Can explain how each chain maps back to M1 artefacts

If any fail, iterate before continuing.

### 9. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Root Cause Synthesis

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure all chains are documented with Fact/Hypothesis labels
2. Update frontmatter: add `step-03-why-chain` to `stepsCompleted`
3. Load `./step-04-root-cause.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** At least one complete chain reaching structural cause, all links labelled F/H, chains are single-threaded, evidence documented

❌ **FAILURE:** Accepting individual blame, jumping between topics, skipping Fact/Hypothesis labelling, stopping at surface symptoms
