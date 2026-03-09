---
name: 'step-02-harvest'
description: 'Extract explicit and implicit assumptions from all M1 artefacts'
nextStepFile: './step-03-classify.md'
outputFile: '{outputFolder}/leap-of-faith.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Harvest Assumptions

**Progress: Step 2 of 5** — Next: Classify Assumptions

---

## STEP GOAL

Produce a comprehensive Consolidated Assumption Inventory by extracting every assumption embedded in M1 artefacts — both explicitly tagged and implicitly embedded in narratives.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The most dangerous assumptions are the ones nobody wrote down. Challenge the founder to look harder. If they find fewer than 15 assumptions, they haven't been thorough enough.

### Step-Specific Rules
- MUST systematically review ALL 6 M1 frameworks, not just the ones with tagged assumptions
- Extract BOTH explicit assumptions (tagged) AND implicit assumptions (embedded in claims)
- Every assumption must trace to a specific source artefact and block
- Do NOT classify or prioritize in this step — that's for later steps

---

## CONTEXT BOUNDARIES

**Available context:**
- leap-of-faith.md created in Step 1
- All M1 framework outputs (6 documents)
- project-memo.md

**Out of scope:**
- Classification (Step 3)
- Prioritization (Step 4)
- Validation design (Step 5)

---

## MANDATORY SEQUENCE

### 1. Load M1 Artefacts

Read each M1 framework output:
- working-backwards.md (Press Release, External FAQ, Internal FAQ)
- jobs-to-be-done.md (Job Stories, Forces, Job Map)
- competitive-landscape.md (Competitors, Benchmarks, Positioning)
- problem-solution-fit.md (Problem Space, Solution Space, Assumptions)
- lean-canvas.md (9 blocks + Assumptions List)
- five-whys.md (Why Chains, Root Cause Map)

### 2. Extract Explicit Assumptions

From each artefact, extract tagged assumptions:

| Source | Where to Look |
|--------|---------------|
| Lean Canvas | Assumptions List (P1, CS2, UVP1, CH1, REV2, COST1, MET1, UA1, etc.) |
| Problem-Solution Fit | Critical Assumptions block |
| Working Backwards | Internal FAQ answers marked as assumptions |
| Five Whys | Chain links labelled "Hypothesis", Targeted Root Cause Hypotheses |

Present draft list to founder: "Here are the explicitly tagged assumptions I found..."

### 3. Extract Implicit Assumptions

Re-read each artefact looking for **claims that assume something unproven**:

| Source | What to Look For |
|--------|------------------|
| Working Backwards PR | Claims about customer behaviour, adoption triggers, willingness to switch |
| Working Backwards External FAQ | Answers asserting customer preferences without evidence |
| JTBD | Assumed frequency of job, assumed forces, assumed job importance hierarchy |
| Problem-Solution Fit | Assumed behaviours, constraints, solution mechanism |
| Lean Canvas | Assumed channel effectiveness, pricing acceptance, cost structure, metrics |
| Competitive Landscape | Assumed competitor weaknesses, assumed positioning viability |
| Five Whys | "Fact" labels that rest on intuition rather than hard data |

Present additions to founder: "Here are implicit assumptions I extracted..."

### 4. Build Consolidated Inventory

For each assumption, capture:

| Field | Description |
|-------|-------------|
| ID | Sequential (LOF-001, LOF-002, etc.) |
| Statement | "We assume that..." |
| Source | Artefact and block (e.g., "Lean Canvas > Revenue Streams > REV1") |
| Category | Behavioural, Technical, or Economic |
| Current Evidence | Data, quotes, observations, or "founder intuition only" |

### 5. Validation Check

Review inventory with founder:

- [ ] Reviewed **all 6 M1 frameworks** plus project-memo
- [ ] At least **15-30 distinct assumptions** (fewer = not thorough; 50+ = merge duplicates)
- [ ] Every assumption traceable to **specific artefact and block**
- [ ] At least one-third from **implicit extraction** (not pre-tagged)
- [ ] Statements are understandable **without reading source artefact**

If fewer than 15 assumptions: "We need to look harder. Let me review [specific artefact] again for implicit assumptions..."

### 6. Update Output Document

Update leap-of-faith.md with Consolidated Assumption Inventory:

```markdown
## Consolidated Assumption Inventory

| ID | Statement | Source | Category | Current Evidence |
|----|-----------|--------|----------|------------------|
| LOF-001 | We assume that... | Lean Canvas > Problem | Behavioural | Founder intuition |
| LOF-002 | We assume that... | JTBD > Job Story 1 | Technical | Indirect evidence |
| ... | ... | ... | ... | ... |

**Total:** [N] assumptions extracted from [M] M1 frameworks
- Explicit (pre-tagged): [X]
- Implicit (extracted): [Y]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-harvest']
```

### 7. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on specific artefacts to find more assumptions
- **[P] Party Mode** — get multi-agent perspectives on hidden assumptions
- **[C] Continue** — proceed to Classify Assumptions

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Consolidated Assumption Inventory has 15+ entries
2. Update frontmatter with `step-02-harvest` in `stepsCompleted`
3. Load `./step-03-classify.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 15-30+ assumptions harvested from all 6 M1 frameworks, mix of explicit and implicit, all traceable to sources

❌ **FAILURE:** Only harvesting from 1-2 frameworks, accepting fewer than 15 assumptions, classifying in this step
