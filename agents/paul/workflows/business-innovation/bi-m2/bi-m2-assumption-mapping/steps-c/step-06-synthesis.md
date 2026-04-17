---
name: 'step-06-synthesis'
description: 'Synthesize findings and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/assumption-mapping.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 6: Synthesis

**Progress: Step 6 of 6** — Final Step

---

## STEP GOAL

Synthesize Assumption Mapping findings into a concise summary, wire into downstream M2 frameworks, and UPDATE project-memo.md.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate the triage achieved. Note what happens next. Be honest about validation work ahead.

### Step-Specific Rules
- project-memo.md MUST be updated with Assumption Mapping synthesis
- Synthesis must be concise (300 words max)
- Wire test cards to downstream M2 frameworks
- Mark framework as completed in project-memo frontmatter

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/assumption-mapping.md` for complete analysis
2. Read `{outputFolder}/project-memo.md` for update

---

## MANDATORY SEQUENCE

### 1. Review Completed Work

Summarize what was accomplished:

> "Let's review what we built:
> - Normalized inventory of [N] assumptions from [sources]
> - Scored each on Importance (1-5) and Uncertainty (1-5)
> - Placed on 2x2 matrix: [N] Test, [N] Accept, [N] Monitor, [N] Ignore
> - Designed [N] test cards with concrete validation methods
> - Total validation timeline: [X] weeks"

### 2. Wire to Downstream Frameworks

Connect test cards to M2 frameworks:

**TAM/SAM/SOM:**
> "These assumptions need market sizing evidence:
> - [AM-XX]: [Statement] — needs market data on [X]"

**Unit Economics:**
> "These assumptions need financial modeling:
> - [AM-YY]: [Statement] — needs LTV/CAC/retention analysis"

**TRL (Technology Readiness Level):**
> "These assumptions need technical validation:
> - [AM-ZZ]: [Statement] — needs spike/PoC for [X]"

**Pre-mortem:**
> "All Test and Accept assumptions are candidate failure modes for Pre-mortem"

### 3. Draft Framework Synthesis

Create a concise synthesis (300 words max):

**Key Findings:**
- Total assumptions: [N]
- Action distribution: [N]% Test, [N]% Accept, [N]% Monitor, [N]% Ignore
- Highest-risk: [Top 3 assumptions with highest combined scores]

**Validation Backlog:**
- [N] tests planned over [X] weeks
- Priority 1: [Test description]
- Priority 2: [Test description]
- Kill criteria tests: [Which tests connect to kill decisions]

**Downstream Integration:**
- TAM/SAM/SOM will address: [assumptions]
- Unit Economics will stress-test: [assumptions]
- TRL will validate: [assumptions]

### 4. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/agents/paul/workflows/business-innovation/data/founder-process.md` for M2.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 5. Update assumption-mapping.md

Add Synthesis section:

```markdown
## Synthesis

### Key Findings

**Total Assumptions:** [N]

**Action Distribution:**
| Quadrant | Count | Percentage |
|----------|-------|------------|
| Test | [N] | [X]% |
| Accept | [N] | [X]% |
| Monitor | [N] | [X]% |
| Ignore | [N] | [X]% |

**Highest-Risk Assumptions:**
1. [AM-XX]: [Statement] — I:[score], U:[score]
2. [AM-YY]: [Statement] — I:[score], U:[score]
3. [AM-ZZ]: [Statement] — I:[score], U:[score]

### Validation Backlog Summary

- **Tests planned:** [N]
- **Total timeline:** [X] weeks
- **Kill criteria tests:** [Which ones]

### Downstream Framework Integration

| Framework | Assumptions to Address |
|-----------|----------------------|
| TAM/SAM/SOM | [IDs] |
| Unit Economics | [IDs] |
| TRL | [IDs] |
| Pre-mortem | All Test + Accept |
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-collect', 'step-03-rate', 'step-04-matrix', 'step-05-tests', 'step-06-synthesis']
status: completed
```

### 6. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m2-assumption-mapping` to `stepsCompleted` array

**In Progress > M2 Validation section:**

```markdown
### Assumption Mapping

**Status:** Completed

**Key Findings:**
- [N] assumptions mapped: [N]% Test, [N]% Accept, [N]% Monitor, [N]% Ignore
- Top risks: [List 2-3 highest-priority assumptions]
- Validation timeline: [X] weeks for [N] tests

**Validation Backlog:**
1. [Priority 1 test]
2. [Priority 2 test]
3. [Priority 3 test]

**Output:** [Link to assumption-mapping.md]
```

### 7. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 8. Completion Summary

Present to founder:
> "Assumption Mapping framework complete!
>
> **What we achieved:**
> - Triaged [N] assumptions into Test/Accept/Monitor/Ignore
> - Designed [N] validation tests with [X]-week timeline
> - Wired high-priority assumptions to downstream frameworks
>
> **What's next:**
> - Execute validation backlog (priority order)
> - TAM/SAM/SOM to address market assumptions
> - Unit Economics to stress-test financial assumptions
> - Pre-mortem to explore failure modes
>
> **Return path:** To continue other M2 frameworks, return to bi-m2 milestone workflow."

### 9. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M2.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M2 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 10. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M2** — return to M2 Validation milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M2** is selected:
1. Verify assumption-mapping.md has status: completed
2. Verify project-memo.md has Assumption Mapping entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** assumption-mapping.md complete with synthesis, project-memo.md updated, downstream wiring documented

❌ **FAILURE:** project-memo.md not updated, synthesis missing, downstream frameworks not connected
