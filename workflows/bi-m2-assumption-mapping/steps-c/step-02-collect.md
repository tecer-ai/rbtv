---
name: 'step-02-collect'
description: 'Collect and normalize assumptions from all sources'
nextStepFile: './step-03-rate.md'
outputFile: '{outputFolder}/assumption-mapping.md'
---

# Step 2: Collect & Normalize Assumptions

**Progress: Step 2 of 6** — Next: Rate Importance & Uncertainty

---

## STEP GOAL

Build a single, deduplicated assumption inventory from Leap of Faith and all M1 sources, with consistent metadata for scoring.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for clarity in assumption statements. Merge duplicates ruthlessly. Reject vague statements.

### Step-Specific Rules
- Do NOT score assumptions yet — that's Step 3
- Target 8-25 assumptions after normalization
- Each assumption must start with "We assume that..."

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/leap-of-faith.md` for prioritized assumptions
2. Read `{outputFolder}/lean-canvas.md` for business model assumptions (if exists)
3. Read `{outputFolder}/problem-solution-fit.md` for behavioural assumptions (if exists)
4. Read `{outputFolder}/working-backwards.md` for Internal FAQ assumptions (if exists)
5. Read `{outputFolder}/five-whys.md` for root cause hypotheses (if exists)

---

## MANDATORY SEQUENCE

### 1. Source Review

Walk through each source with the founder:

**Leap of Faith (Primary Source):**
> "Let's start with your Leap of Faith assumptions. These are your prioritized value and growth hypotheses."

List all assumptions from leap-of-faith.md with their classification (Value/Growth).

**M1 Framework Sources:**
> "Now let's cross-reference with M1 frameworks to catch anything we might have missed."

For each available M1 document, identify tagged assumptions or hypotheses.

### 2. Deduplication

Identify assumptions that say the same thing in different words:
> "I see these might be duplicates — they seem to address the same underlying belief:
> - [Assumption A from source X]
> - [Assumption B from source Y]
>
> Should we merge these? If so, what's the clearest phrasing?"

Keep the clearest phrasing. Note all source frameworks in metadata.

### 3. Normalization

For each unique assumption, confirm the following format:

| Field | Description |
|-------|-------------|
| ID | Short label (AM-01, AM-02, etc.) |
| Statement | One sentence starting with "We assume that..." |
| Category | Behavioural, Technical, or Economic |
| LoF Class | Value Hypothesis, Growth Hypothesis, or Neither |
| Sources | Which M1/M2 frameworks surfaced this |
| Evidence | What you already know (interviews, data, logic, nothing) |
| Confidence | High, Medium, or Low based on current evidence |

### 4. Inventory Count Check

After normalization:
- **If more than 25:** "You have [N] assumptions. Let's consolidate related ones into clusters to make this manageable."
- **If fewer than 8:** "Only [N] assumptions seems low for this stage. Let's review M1 frameworks for hidden assumptions we might have missed."

### 5. Document Inventory

Update assumption-mapping.md with the normalized inventory:

```markdown
## Normalized Assumption Inventory

**Total Assumptions:** [N]

| ID | Statement | Category | LoF Class | Sources | Evidence | Confidence |
|----|-----------|----------|-----------|---------|----------|------------|
| AM-01 | We assume that [statement] | [Cat] | [Class] | [Sources] | [Evidence] | [H/M/L] |
| AM-02 | We assume that [statement] | [Cat] | [Class] | [Sources] | [Evidence] | [H/M/L] |
| ... | ... | ... | ... | ... | ... | ... |
```

### 6. Validation Questions

Before proceeding, confirm with founder:
- "Every assumption from Leap of Faith appears here? No orphans?"
- "Each assumption has exactly one category and one LoF class?"
- "A neutral reader can understand each statement without source documents?"

### 7. Update Frontmatter

Update stepsCompleted:
```yaml
stepsCompleted: ['step-01-init', 'step-02-collect']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Rate Importance & Uncertainty
- **[R] Revise** — add, remove, or edit assumptions

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify assumption inventory has 8-25 entries
2. Verify all required fields are populated
3. Verify `step-02-collect` is in `stepsCompleted`
4. Load `./step-03-rate.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 8-25 normalized assumptions, no duplicates, all metadata fields populated, clear statements

❌ **FAILURE:** Scoring assumptions in this step, accepting duplicates, vague statements, count outside 8-25 range without justification
