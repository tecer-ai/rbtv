---
name: 'step-03-target-trl'
description: 'Identify technical risks, unknowns, and target TRL for M4'
nextStepFile: './step-04-gap-analysis.md'
outputFile: '{outputFolder}/technology-readiness-level.md'
---

# Step 3: Target TRL & Risk Analysis

**Progress: Step 3 of 5** — Next: Gap Analysis (Spike Design)

---

## STEP GOAL

Define target TRL for each component before M4 Prototypation, identify specific technical risks and unknowns across risk categories, and create a technical risk inventory.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Surface risks that could block progress. Don't let "we'll figure it out" pass as a plan.

### Step-Specific Rules
- MUST set target TRL of at least 4 for all components before M4
- MUST identify risks across multiple categories (Performance, Scalability, Integration, Data, Security, Skills, Cost)
- MUST cross-reference with Working Backwards Internal FAQ technical questions
- Components with 3+ high-uncertainty risks need spikes even if TRL ≥ 4

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/technology-readiness-level.md` for component inventory and scores
2. Review Working Backwards Internal FAQ technical questions
3. Review component dependencies

---

## MANDATORY SEQUENCE

### 1. Set Target TRL for Each Component

Define where each component needs to be before M4 Prototypation:

> "Before M4 Prototypation, each component should reach at least TRL 4 (validated in lab). Preferably TRL 5 (validated in relevant environment) for critical-path components."

| ID | Name | Current TRL | Target TRL | Gap | Critical Path? |
|----|------|-------------|------------|-----|----------------|
| TC-01 | [Name] | [X] | [4-5] | [Y levels] | [Yes/No] |
| TC-02 | [Name] | [X] | [4-5] | [Y levels] | [Yes/No] |
| ... | ... | ... | ... | ... | ... |

Components on critical path (where failure blocks other components) should target TRL 5.

### 2. Identify Risks Per Component

For each component, assess across 7 risk categories:

| Category | Key Question |
|----------|--------------|
| **Performance** | Can it meet speed, accuracy, throughput, latency targets? |
| **Scalability** | Can it scale to expected volume within cost constraints? |
| **Integration** | Does it depend on external APIs that could change or fail? |
| **Data** | Does it require data you don't have or quality unproven? |
| **Security** | Does it handle sensitive data or require compliance? |
| **Skills** | Does it need expertise the team doesn't have? |
| **Cost** | Could variable costs become prohibitive at scale? |

For each risk identified:

| ID | Component | Risk Description | Category | Current Mitigation | Residual Uncertainty |
|----|-----------|------------------|----------|-------------------|---------------------|
| TR-01 | TC-01 | [What could go wrong] | [Category] | [What you know/have done] | [High/Med/Low] |
| TR-02 | TC-01 | [What could go wrong] | [Category] | [What you know/have done] | [High/Med/Low] |
| ... | ... | ... | ... | ... | ... |

### 3. Cross-Reference Internal FAQ

Map every technical question from Working Backwards Internal FAQ to the risk inventory:

| FAQ Question | Mapped To | Status |
|--------------|-----------|--------|
| [Technical question 1] | [TR-XX or TC-XX] | [Addressed/Open] |
| [Technical question 2] | [TR-XX or TC-XX] | [Addressed/Open] |
| ... | ... | ... |

> "Every technical question from Internal FAQ should map to a risk or component. Any unmapped questions are blind spots."

If questions are unmapped, add as new risks.

### 4. Identify Dependency Chains

Document critical path risks where one component's failure cascades:

**Dependency Chain Analysis:**

```
[TC-01] → [TC-02] → [TC-04]
              ↓
          [TC-03]
```

| Chain | Components | Failure Impact |
|-------|------------|----------------|
| Primary | TC-01 → TC-02 → TC-04 | [What breaks if TC-01 fails] |
| Secondary | TC-02 → TC-03 | [What breaks if TC-02 fails] |

Mark chains as **Critical Path Risks**.

### 5. Count Risks Per Component

Summarize risk concentration:

| Component | Total Risks | High Uncertainty | Spike Needed? |
|-----------|-------------|------------------|---------------|
| TC-01 | [X] | [Y] | [Yes if TRL<4 OR 3+ high uncertainty] |
| TC-02 | [X] | [Y] | [Yes/No] |
| ... | ... | ... | ... |

**Rule:** Components need spikes if:
- Current TRL < 4, OR
- 3+ risks with High residual uncertainty

### 6. Assess Risk Distribution

Check risk category coverage:

| Category | Risk Count | % of Total |
|----------|------------|------------|
| Performance | [X] | [Y]% |
| Scalability | [X] | [Y]% |
| Integration | [X] | [Y]% |
| Data | [X] | [Y]% |
| Security | [X] | [Y]% |
| Skills | [X] | [Y]% |
| Cost | [X] | [Y]% |

> "You should have risks in at least 3 of 7 categories. If concentrated in one category, you may have blind spots in others."

### 7. Update Output Document

Update technology-readiness-level.md with:
- Target TRL table
- Technical Risk Inventory
- Internal FAQ cross-reference
- Dependency chains
- Risk summary by component

Update frontmatter: add `step-03-target-trl` to `stepsCompleted`

### 8. Present Menu Options

**Summary:**
> "Technical risks identified: [N]
> - High uncertainty: [N] risks
> - Components needing spikes: [N]
> - Critical path risks: [N]
> - FAQ questions addressed: [X] of [Y]"

**Select an Option:**
- **[C] Continue** — proceed to Gap Analysis (Spike Design)
- **[R] Refine** — revisit risk identification

ALWAYS halt and wait for user selection.

---

## VALIDATION CHECKLIST

Before proceeding, verify:
- [ ] Every component with TRL < 6 has at least one identified risk
- [ ] Every technical question from Internal FAQ is mapped to a risk or marked addressed
- [ ] Dependency chains are documented
- [ ] Risk categories cover at least 3 of 7 categories
- [ ] Components with 3+ high-uncertainty risks are flagged for spikes

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all validation checklist items pass
2. Ensure technology-readiness-level.md is updated
3. Load `./step-04-gap-analysis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Risks identified across categories, FAQ mapped, dependency chains documented

❌ **FAILURE:** Ignoring integration risks, unmapped FAQ questions, no critical path analysis
