---
name: 'step-05-synthesis'
description: 'Extract threats/opportunities and UPDATE project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/competitive-landscape.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Synthesize competitive analysis into threats and opportunities, document assumptions for M2 validation, and UPDATE project-memo.md to capture learnings across frameworks.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Be honest about competitive threats. Celebrate differentiation opportunities. Connect everything to M2 validation.

### Step-Specific Rules
- project-memo.md MUST be updated with Competitive Landscape synthesis
- Synthesis must be concise (300 words max)
- Document at least 10 assumptions for M2 validation
- Flag high-risk assumptions explicitly

---

## CONTEXT BOUNDARIES

**Available context:**
- Complete competitive-landscape.md from Steps 1-4
- project-memo.md

**Out of scope:**
- Other M1 frameworks (separate workflows)
- M2 experiment design (M2 workflows)

---

## MANDATORY SEQUENCE

### 1. Extract Competitive Threats

Identify threats across categories:

| Threat Category | Specific Threats |
|-----------------|------------------|
| Incumbent Advantages | Distribution, brand, switching costs, data moats |
| Emerging Players | Well-funded startups, pivoting companies |
| Platform Risk | Dependency on ecosystems (AWS, Apple, Google) |
| Geographic Entry | Could US/China players enter your market? |
| Cross-Industry Disruption | Could adjacent industry players expand? |
| Technology Shifts | Could new tech (AI, etc.) commoditize value? |
| Regulatory Changes | Could regulation favor incumbents or entrants? |

For each threat, assess:

| Threat | Severity (H/M/L) | Mitigation Strategy |
|--------|------------------|---------------------|
| ... | ... | ... |

Target: At least **5 specific threats**.

### 2. Extract Differentiation Opportunities

Identify opportunities from analysis:

| Opportunity Source | Specific Opportunities |
|--------------------|------------------------|
| Competitor Weaknesses | Gaps all competitors share |
| Underserved Segments | Customer segments competitors ignore |
| Unmet Jobs | Jobs-to-be-done competitors don't address |
| Geographic Lessons | Innovations from mature markets not yet applied |
| Cross-Industry Patterns | Innovations from analogues not yet imported |
| Positioning White Space | Unoccupied areas in positioning map |
| Technology Arbitrage | New tech competitors haven't adopted |

Prioritize each opportunity:

| Opportunity | Impact (H/M/L) | Feasibility (H/M/L) | Priority |
|-------------|----------------|---------------------|----------|
| ... | ... | ... | ... |

Select **Top 3-5 opportunities** to inform solution design.

### 3. Document Assumptions for Validation

Extract all assumptions made during analysis:

| Assumption | Category | Confidence | Validation Method |
|------------|----------|------------|-------------------|
| Competitor X lacks Y capability | Competitive | Medium | Product trial, feature docs |
| Segment Z is underserved | Market | Low | Customer interviews |
| US model will work in our market | Geographic | Low | Market test |
| Risk model from [industry] applies | Cross-Industry | Medium | Domain expert review |

Categories: Competitive, Market, Geographic, Cross-Industry, Customer.

Target: At least **10 assumptions** documented.

### 4. Flag High-Risk Assumptions

From the full inventory, flag assumptions that, if wrong, would invalidate differentiation strategy:

**High-Risk Assumptions (Require Priority Validation in M2):**

1. [Assumption] — Why it's critical: [explanation]
2. [Assumption] — Why it's critical: [explanation]
3. [Assumption] — Why it's critical: [explanation]

Target: **3-5 high-risk assumptions** flagged.

### 5. Update competitive-landscape.md

Add Sections 6, 7, and Synthesis to competitive-landscape.md:
- **Section 6: Threats & Opportunities** — Threat inventory (category, severity, mitigation), opportunity inventory (source, impact, feasibility), top 3-5 prioritized
- **Section 7: Assumptions** — Full inventory table, high-risk assumptions table
- **Synthesis** — Key findings, strategic implications, framework connections

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-competitor-id', 'step-03-benchmarking', 'step-04-positioning', 'step-05-synthesis']
status: completed
```

### 6. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m1-competitive-landscape` to `stepsCompleted` array

**In Progress > M1 Conception section:**

```markdown
### Competitive Landscape

**Status:** Completed

**Key Findings:**
- Direct Competitors: {count} identified, led by {top competitors}
- Geographic Benchmark: {key lesson from US/China}
- Positioning: {white space identified}

**Top Threats:** {list 2-3}

**Top Opportunities:** {list 2-3}

**Assumptions for M2:** {count} documented, {count} high-risk

**Output:** [Link to competitive-landscape.md]
```

### 7. Completion Summary

Present to founder:

> "Competitive Landscape analysis complete!
>
> **What we mapped:**
> - [N] direct competitors and [N] indirect alternatives
> - US and China market benchmarks
> - [N] cross-industry analogues
> - Positioning map with white space at [position]
>
> **Key insights:**
> - Top threat: [threat]
> - Top opportunity: [opportunity]
> - [N] assumptions tagged for M2 validation
>
> **Next recommended framework:** [Problem-Solution Fit / Lean Canvas]
>
> **Return path:** To continue other M1 frameworks, return to bi-m1 milestone workflow."

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M1** — return to M1 Conception milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M1** is selected:
1. Verify competitive-landscape.md has status: completed
2. Verify project-memo.md has Competitive Landscape entry
3. Load `../bi-m1/workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** At least 5 threats and 5 opportunities documented, 10+ assumptions inventoried, 3-5 high-risk flagged, competitive-landscape.md complete, project-memo.md updated

❌ **FAILURE:** project-memo.md not updated, synthesis missing, assumptions not documented, no threats or opportunities extracted
