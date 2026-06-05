---
stepNumber: 1
stepName: 'init'
knowledgeFile: ../data/milestone-overview.md
projectMemo: '{project-name}/business-innovation/project-memo.md'
---

# Step 01: M2 Validation Framework Menu

**Progress: M2 Validation Milestone** — Select framework to work on

---

## STEP GOAL

Present M2 Validation framework menu, identify completed frameworks, suggest next framework based on dependencies, and route user to the selected framework workflow.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a YC mentor. Guide the founder through validation frameworks with strategic ordering. Challenge assumptions, demand evidence, push for honest assessment. Every unvalidated assumption is a risk you're choosing to ignore. This is a partnership.

### Step-Specific Rules

- Read project-memo frontmatter to determine which M2 frameworks are completed
- Suggest the logical next framework based on stepsCompleted and dependencies
- Allow user to override suggestion and select any framework
- Framework workflows will update project-memo on completion — do not duplicate this logic

---

## MANDATORY SEQUENCE

### 1. Load Project State

Read `{projectMemo}` frontmatter to understand:
- currentMilestone
- currentFramework
- stepsCompleted array

Look for these step IDs to determine M2 framework completion:
- `bi-m2-leap-of-faith`
- `bi-m2-assumption-mapping`
- `bi-m2-tam-sam-som`
- `bi-m2-unit-economics`
- `bi-m2-technology-readiness-level`
- `bi-m2-pre-mortem`

### 1b. Market Research Recommendation

Check project-memo frontmatter for `externalResearchCompleted: true`. If set, skip this section.

If NOT set, present:

> "💡 **Market data improves M2 quality.** TAM/SAM/SOM and Unit Economics both require external data — industry sizing, competitive benchmarks, pricing references. If you haven't gathered this yet, consider running market research before starting M2 frameworks.
>
> If you have the `bmad-method-lifecycle` plugin installed, `bmad-method-lifecycle:bmad-market-research` (or `bmad-domain-research` / `bmad-technical-research`) can generate structured research from your M1 artifacts. Run it in a separate session, save outputs to `{project-name}/business-innovation/m2-validation/external-research/`.
>
> [P] Proceed to M2 frameworks
> [X] Proceed and don't show this again"

**On selection:**
- **[P]**: Continue to Section 2 (framework menu)
- **[X]**: Set `externalResearchCompleted: true` in project-memo frontmatter, continue to Section 2

---

### 2. Analyze Progress and Dependencies

**Recommended Execution Order (from validation_process.md):**
1. Leap of Faith → 2. Assumption Mapping → 3. TAM/SAM/SOM → 4. Unit Economics → 5. Technology Readiness Level → 6. Pre-mortem

Determine suggested next framework from stepsCompleted:

| State | Recommended Next | Rationale |
|-------|------------------|-----------|
| No M2 frameworks completed | Leap of Faith | Foundation — identifies critical assumptions and kill criteria (Order: 1) |
| Only LoF complete | Assumption Mapping | Build on LoF — prioritize assumptions for testing (Order: 2) |
| LoF + AM complete | TAM/SAM/SOM | Market sizing before financial modeling (Order: 3) |
| LoF + AM + TS complete | Unit Economics | Financial viability model (Order: 4) |
| LoF + AM + TS + UE complete | Technology Readiness Level | Technical feasibility assessment (Order: 5) |
| First 5 complete | Pre-mortem | Final comprehensive risk analysis (Order: 6) |
| All M2 complete | Return to milestone selection | M2 Validation milestone complete |

**Framework Dependencies:**
- Leap of Faith: Requires ALL M1 frameworks (Working Backwards, JTBD, Competitive Landscape, Problem-Solution Fit, Lean Canvas, Five Whys)
- Assumption Mapping: Requires Leap of Faith
- TAM/SAM/SOM: Requires Leap of Faith (recommended)
- Unit Economics: Requires TAM/SAM/SOM
- Technology Readiness Level: Requires Leap of Faith (recommended)
- Pre-mortem: Requires ALL prior M2 frameworks (LoF, AM, TS, UE, TR)

**Note:** While the recommended order optimizes learning flow, user can choose any framework with met prerequisites.

### 3. Present Status Summary

Display current M2 state:
```
=== M2 VALIDATION STATUS ===

Frameworks Completed: {count}/6

Completed:
{list completed frameworks with [x]}

Next Recommended: {suggestion based on analysis}
```

### 4. Present Framework Menu

```
Select a framework to work on:

[LF] Leap of Faith — Critical assumptions + kill criteria (foundation framework) {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: All M1 frameworks
     Output: leap-of-faith.md

[AM] Assumption Mapping — Importance × Uncertainty matrix {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Leap of Faith
     Output: assumption-mapping.md

[TS] TAM/SAM/SOM — Market opportunity sizing [WEB RESEARCH MANDATORY] {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Leap of Faith (recommended)
     Output: tam-sam-som.md

[UE] Unit Economics — Financial viability model [WEB RESEARCH MANDATORY] {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: TAM/SAM/SOM
     Output: unit-economics.md

[TR] Technology Readiness Level — Technical feasibility assessment {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Leap of Faith (recommended)
     Output: technology-readiness.md

[PM] Pre-mortem — Comprehensive risk analysis {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: All prior M2 frameworks (LoF, AM, TS, UE, TR)
     Output: pre-mortem.md

---
[S] Status — Show detailed completion status
[B] Back — Return to milestone selection
[X] Exit — Exit workflow
```

**Instructions for displaying recommended indicator:**
- Add ` ← Recommended next` after the framework name ONLY if it matches the recommended next framework from Section 2
- Example: `[AM] Assumption Mapping — Importance × Uncertainty matrix ← Recommended next`
- Prerequisites shown below should indicate ✓ for completed or ✗ for not completed
- Example: `Prerequisites: Leap of Faith ✓`

### 5. HALT

ALWAYS halt and wait for user selection.

---

## MENU ROUTING

| Selection | Action |
|-----------|--------|
| [LF] | Check prerequisites (all M1) → Update project-memo frontmatter currentFramework → Load `../bi-m2-leap-of-faith/workflow.md` |
| [AM] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m2-assumption-mapping/workflow.md` |
| [TS] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m2-tam-sam-som/workflow.md` |
| [UE] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m2-unit-economics/workflow.md` |
| [TR] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m2-technology-readiness-level/workflow.md` |
| [PM] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m2-pre-mortem/workflow.md` |
| [S] | Display detailed status, then redisplay menu |
| [B] | Load `../../workflow.md` → step-02-milestone-select.md |
| [X] | Exit workflow |

### Prerequisite Checking

If user selects a framework with unmet prerequisites, display:
```
⚠️ Prerequisites not met for {framework}

Required frameworks:
{list required frameworks with completion status}

You can:
- Start a prerequisite framework first
- Override (not recommended — may result in incomplete analysis)

[O] Override and proceed anyway
[C] Cancel and choose different framework
```

If user chooses [O], proceed with warning logged in project-memo.

---

## STATUS DISPLAY (for [S] option)

```
=== M2 VALIDATION DETAILED STATUS ===

M2 Frameworks (6 total):

[ ] Leap of Faith
    Prerequisites: All M1 frameworks (Working Backwards, JTBD, Competitive Landscape, Problem-Solution Fit, Lean Canvas, Five Whys)
    Output: m2-validation/leap-of-faith.md
    
[ ] Assumption Mapping
    Prerequisites: Leap of Faith
    Output: m2-validation/assumption-mapping.md
    
[ ] TAM/SAM/SOM [WEB RESEARCH MANDATORY]
    Prerequisites: Leap of Faith (recommended)
    Output: m2-validation/tam-sam-som.md
    
[ ] Unit Economics [WEB RESEARCH MANDATORY]
    Prerequisites: TAM/SAM/SOM
    Output: m2-validation/unit-economics.md
    
[ ] Technology Readiness Level
    Prerequisites: Leap of Faith (recommended)
    Output: m2-validation/technology-readiness.md
    
[ ] Pre-mortem
    Prerequisites: All prior M2 frameworks (LoF, AM, TS, UE, TR)
    Output: m2-validation/pre-mortem.md

(Replace [ ] with [x] for completed frameworks based on stepsCompleted)

Completion: {count}/6 frameworks
```

After displaying status, return to framework menu.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when user selects a framework [LF/AM/TS/UE/TR/PM]:
1. Check prerequisites (if applicable)
2. Update project-memo.md frontmatter: set currentFramework
3. Load the selected framework workflow and follow its instructions

When user selects [B] Back:
1. Load `../../workflow.md` → follow to step-02-milestone-select.md
2. That step will present the milestone menu

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Project state correctly read from project-memo frontmatter
- Accurate framework completion counts displayed
- Logical next framework suggested based on dependencies
- Prerequisites validated before loading framework workflow
- User selection routed to correct workflow
- Project-memo updated before loading new workflow

❌ **FAILURE:**
- Incorrect framework counts
- Loading framework workflow before checking prerequisites
- Loading framework workflow before updating project-memo
- Missing status information
- Proceeding without user selection
- Breaking the referral logic (milestone = menu, framework = work + return to menu)
