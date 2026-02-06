---
stepNumber: 1
stepName: 'init'
knowledgeFile: ../data/milestone-overview.md
projectMemo: '{project-root}/_bmad-output/{project-name}/founder/project-memo.md'
---

# Step 01: M1 Conception Framework Menu

**Progress: M1 Conception Milestone** — Select framework to work on

---

## STEP GOAL

Present M1 Conception framework menu, identify completed frameworks, suggest next framework based on dependencies, and route user to the selected framework workflow.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a YC mentor. Guide the founder through conception frameworks with strategic ordering. Challenge assumptions, demand clarity, push for specificity. This is a partnership.

### Step-Specific Rules

- Read project-memo frontmatter to determine which M1 frameworks are completed
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

Look for these step IDs to determine M1 framework completion:
- `bi-m1-working-backwards`
- `bi-m1-jobs-to-be-done`
- `bi-m1-competitive-landscape`
- `bi-m1-problem-solution-fit`
- `bi-m1-lean-canvas`
- `bi-m1-five-whys`

### 2. Analyze Progress and Dependencies

**Recommended Execution Order (from conception_process.md):**
1. Working Backwards → 2. Jobs-to-be-Done → 3. Competitive Landscape → 4. Problem-Solution Fit → 5. Lean Canvas → 6. Five Whys

Determine suggested next framework from stepsCompleted:

| State | Recommended Next | Rationale |
|-------|------------------|-----------|
| No M1 frameworks completed | Working Backwards | Foundation for all other frameworks (Order: 1) |
| Only WB complete | Jobs-to-be-Done | Build on WB foundation (Order: 2) |
| WB + JTBD complete | Competitive Landscape | Market context before problem-solution fit (Order: 3) |
| WB + JTBD + CL complete | Problem-Solution Fit | Validate alignment with all prior context (Order: 4) |
| WB + JTBD + CL + PSF complete | Lean Canvas | Synthesize into business model (Order: 5) |
| First 5 complete | Five Whys | Final root cause analysis (Order: 6) |
| All M1 complete | Return to milestone selection | M1 Conception milestone complete |

**Framework Dependencies:**
- Working Backwards: None (start here)
- JTBD: Requires Working Backwards
- Competitive Landscape: Requires Working Backwards
- Problem-Solution Fit: Requires Working Backwards AND JTBD
- Lean Canvas: Requires Working Backwards, JTBD, AND Problem-Solution Fit
- Five Whys: Requires Working Backwards

**Note:** While the recommended order optimizes learning flow, user can choose any framework with met prerequisites.

### 3. Present Status Summary

Display current M1 state:
```
=== M1 CONCEPTION STATUS ===

Frameworks Completed: {count}/6

Completed:
{list completed frameworks with [x]}

Next Recommended: {suggestion based on analysis}
```

### 4. Present Framework Menu

```
Select a framework to work on:

[WB] Working Backwards — Press release + FAQ (foundation framework) {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: None
     Output: working-backwards.md

[JT] Jobs-to-be-Done — Customer job analysis {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Working Backwards
     Output: jobs-to-be-done.md

[CL] Competitive Landscape — Market positioning + benchmarking {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Working Backwards
     Output: competitive-landscape.md

[PS] Problem-Solution Fit — Problem/solution canvas + assumptions {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Working Backwards, JTBD
     Output: problem-solution-fit.md

[LC] Lean Canvas — Business model canvas {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Working Backwards, JTBD, Problem-Solution Fit
     Output: lean-canvas.md

[5W] Five Whys — Root cause analysis {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Working Backwards
     Output: five-whys.md

---
[S] Status — Show detailed completion status
[B] Back — Return to milestone selection
[X] Exit — Exit workflow
```

**Instructions for displaying recommended indicator:**
- Add ` ← Recommended next` after the framework name ONLY if it matches the recommended next framework from Section 2
- Example: `[JT] Jobs-to-be-Done — Customer job analysis ← Recommended next`
- Prerequisites shown below should indicate ✓ for completed or ✗ for not completed
- Example: `Prerequisites: Working Backwards ✓`

### 5. HALT

ALWAYS halt and wait for user selection.

---

## MENU ROUTING

| Selection | Action |
|-----------|--------|
| [WB] | Update project-memo frontmatter currentFramework → Load `../bi-m1-working-backwards/workflow.md` |
| [JT] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m1-jobs-to-be-done/workflow.md` |
| [CL] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m1-competitive-landscape/workflow.md` |
| [PS] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m1-problem-solution-fit/workflow.md` |
| [LC] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m1-lean-canvas/workflow.md` |
| [5W] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m1-five-whys/workflow.md` |
| [S] | Display detailed status, then redisplay menu |
| [B] | Load `../../bi-business-innovation/workflow.md` → step-02-milestone-select.md |
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
=== M1 CONCEPTION DETAILED STATUS ===

M1 Frameworks (6 total):

[ ] Working Backwards
    Prerequisites: None
    Output: m1-conception/working-backwards.md
    
[ ] Jobs-to-be-Done
    Prerequisites: Working Backwards
    Output: m1-conception/jobs-to-be-done.md
    
[ ] Competitive Landscape
    Prerequisites: Working Backwards
    Output: m1-conception/competitive-landscape.md
    
[ ] Problem-Solution Fit
    Prerequisites: Working Backwards, JTBD
    Output: m1-conception/problem-solution-fit.md
    
[ ] Lean Canvas
    Prerequisites: Working Backwards, JTBD, Problem-Solution Fit
    Output: m1-conception/lean-canvas.md
    
[ ] Five Whys
    Prerequisites: Working Backwards
    Output: m1-conception/five-whys.md

(Replace [ ] with [x] for completed frameworks based on stepsCompleted)

Completion: {count}/6 frameworks
```

After displaying status, return to framework menu.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when user selects a framework [WB/JT/CL/PS/LC/5W]:
1. Check prerequisites (if applicable)
2. Update project-memo.md frontmatter: set currentFramework
3. Load the selected framework workflow and follow its instructions

When user selects [B] Back:
1. Load `../../bi-business-innovation/workflow.md` → follow to step-02-milestone-select.md
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
