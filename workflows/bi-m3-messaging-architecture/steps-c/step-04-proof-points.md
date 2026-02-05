---
name: 'step-04-proof-points'
description: 'Build evidence library with 2-3 proof points per message'
nextStepFile: './step-05-cta-matrix.md'
outputFile: '{outputFolder}/messaging-architecture.md'
---

# Step 4: Build Proof Points

**Progress: Step 4 of 6** — Next: Define CTA Matrix

---

## STEP GOAL

For each key message, define 2-3 proof points that make the message credible. Proof points are evidence: data, customer quotes, features framed as benefits, or third-party validation.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Unattributed proof points are opinions, not evidence. "Customers love us" without a specific quote is marketing fiction. Every claim needs a source.

### Step-Specific Rules
- Each message MUST have at least 2 proof points
- Each proof point MUST have documented source
- At least one proof point per message from JTBD customer interviews
- At least one proof point per message from M2 validation (if available)
- Messages with <2 validated proof points are flagged for M5 validation

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/messaging-architecture.md` from Steps 1-3
2. Load upstream framework outputs:
   - JTBD analysis (customer quotes, workarounds, forces)
   - M2 Validation data (experiment results, survey data)
   - Working Backwards (claims, features, customer quote)
   - Lean Canvas Solution block (top features/capabilities)
   - Problem-Solution Fit (before/after emotions, constraints — optional)

---

## MANDATORY SEQUENCE

### 1. Inventory Available Evidence

Before building proof points, inventory what evidence exists:

```markdown
## Evidence Inventory

### From JTBD
| Type | Content | Status |
|------|---------|--------|
| Customer quote | "[quote]" | Validated |
| Customer quote | "[quote]" | Validated |
| Workaround | [description] | Validated |
| Force | [description] | Validated |

### From M2 Validation
| Type | Content | Status |
|------|---------|--------|
| Experiment result | [result] | Validated |
| Survey finding | [finding] | Validated |
| Market data | [data] | Validated |

### From Working Backwards
| Type | Content | Status |
|------|---------|--------|
| Customer quote | "[quote]" | Hypothetical |
| Claim | [claim] | Hypothetical |
| Feature-benefit | [feature → benefit] | Hypothetical |

### From Lean Canvas
| Type | Content | Status |
|------|---------|--------|
| Feature-benefit | [feature → outcome] | Hypothetical |
| Metric | [metric] | Hypothetical |
```

Present inventory to user.

### 2. Map Evidence to Messages

For each key message, identify available evidence:

```markdown
### Message: "[Message text]"
**Audience:** [Audience]
**Traceability:** [Source]

**Available Evidence:**
1. [Evidence type]: [Content] — [Status: Validated/Hypothetical]
2. [Evidence type]: [Content] — [Status]
3. [Evidence type]: [Content] — [Status]

**Best 2-3 Proof Points:**
- [ ] [Selected proof point 1]
- [ ] [Selected proof point 2]
- [ ] [Selected proof point 3]
```

Work through each message systematically.

### 3. Document Proof Points

For each selected proof point, document:

**Proof Point Card:**
```markdown
| Field | Value |
|-------|-------|
| Message | "[Message it supports]" |
| Proof Point | "[The evidence statement]" |
| Source | [Framework, interview, data set] |
| Type | [Data / Customer quote / Feature-benefit / Third-party] |
| Status | [Validated / Hypothetical] |
```

### 4. Apply Quality Filters

**Filter 1: Source documented**
- Can you cite exactly where this came from?
- If no source, mark as hypothetical

**Filter 2: Customer language (for quotes)**
- Is it verbatim from interview?
- Not paraphrased into corporate language?

**Filter 3: Feature-as-benefit formatted**
- States the outcome, not the capability?
- "Reduces 4 hours to 20 minutes" not "has automated reports"

**Filter 4: Prism consistency**
- Doesn't contradict Culture or Relationship facets?

### 5. Flag Evidence Gaps

For each message, check:
- Does it have at least 2 proof points?
- Is at least one from JTBD?
- Is at least one from M2 validation?

If <2 proof points or all hypothetical:

```markdown
## Evidence Gaps

| Message | Gap | Recommended M5 Experiment |
|---------|-----|---------------------------|
| "[Message]" | No validated evidence | [Experiment to generate proof] |
| "[Message]" | Missing customer quote | [Interview to conduct] |
| "[Message]" | No metric data | [Survey or test to run] |
```

Flag these for M5 validation planning.

### 6. Build Proof Point Library

Compile into structured library:

```markdown
## Proof Point Library

| Message | Proof Point | Source | Type | Status |
|---------|-------------|--------|------|--------|
| [M1] | [PP1] | JTBD interview | Customer quote | Validated |
| [M1] | [PP2] | M2 experiment | Data | Validated |
| [M2] | [PP1] | Working Backwards | Feature-benefit | Hypothetical |
| [M2] | [PP2] | Lean Canvas | Metric | Hypothetical |
| ... | ... | ... | ... | ... |

### Evidence Gap Summary

**Messages with sufficient proof (≥2 validated):** [N]
**Messages needing validation:** [N]

**Flagged for M5:**
- [List messages needing validation experiments]
```

Update messaging-architecture.md with this section.

### 7. Update Output Document

Update messaging-architecture.md frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-brand-promise', 'step-03-key-messages', 'step-04-proof-points']
```

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine proof points further
- **[C] Continue** — proceed to Define CTA Matrix

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Proof Point Library section is complete
2. Verify evidence gaps are flagged
3. Load `./step-05-cta-matrix.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 2-3 proof points per message, all sourced, types documented, gaps flagged with M5 experiments

❌ **FAILURE:** Proof points without sources, fabricated evidence, gaps not flagged, customer quotes paraphrased
