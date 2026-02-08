---
stepNumber: 1
stepName: 'init'
knowledgeFile: ../data/milestone-overview.md
projectMemo: '{project-root}/_bmad-output/{project-name}/founder/project-memo.md'
---

# Step 01: M4 Prototypation Framework Menu

**Progress: M4 Prototypation Milestone** — Select framework to work on

---

## STEP GOAL

Present M4 Prototypation framework menu, identify completed frameworks, suggest next framework based on dependencies, and route user to the selected framework workflow or BMAD bridge.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a YC mentor. Guide the founder through prototypation frameworks with strategic ordering. Push for conversion-focused design, challenge decorative choices, demand usability validation. Prototypes that don't communicate value clearly are worthless.

### Step-Specific Rules

- Read project-memo frontmatter to determine which M4 frameworks are completed
- Suggest the logical next framework based on stepsCompleted and dependencies
- Allow user to override suggestion and select any framework
- Framework workflows will update project-memo on completion — do not duplicate this logic
- [D] Design Direction routes via bi-m4-design-context bridge to BMAD create-ux-design

---

## MANDATORY SEQUENCE

### 1. Load Project State

Read `{projectMemo}` frontmatter to understand:
- currentMilestone
- currentFramework
- stepsCompleted array

Look for these step IDs to determine M4 framework completion:
- `bi-m4-user-flow-ia`
- `bi-m4-design-context`
- `bi-m4-build-prototype`
- `bi-m4-conversion-centered-design`
- `bi-m4-heuristic-evaluation`
- `bi-m4-testing-prep`

### 2. Analyze Progress and Dependencies

**Recommended Execution Order:**
1. User Flow & IA → 2. Design Direction → 3. Build Prototype → 4. Conversion Optimization → 5. Heuristic Evaluation → 6. Testing Prep

Determine suggested next framework from stepsCompleted:

| State | Recommended Next | Rationale |
|-------|------------------|-----------|
| No M4 frameworks completed | User Flow & IA | Foundation for all design work (Order: 1) |
| Only [U] complete | Design Direction | Visual design via BMAD bridge (Order: 2) |
| [U] + [D] complete | Build Prototype | Implement HTML prototype (Order: 3, planned) |
| [U] + [D] + [B] complete | Conversion Optimization | Apply CCD principles (Order: 4) |
| [U] + [D] + [B] + [C] complete | Heuristic Evaluation | Usability evaluation (Order: 5) |
| First 5 complete | Testing Prep | F&F testing protocol (Order: 6, planned) |
| All M4 complete | Return to milestone selection | M4 Prototypation milestone complete |

**Framework Dependencies:**
- User Flow & IA [U]: None (start here)
- Design Direction [D]: User Flow & IA recommended
- Build Prototype [B]: User Flow & IA AND Design Direction (planned)
- Conversion Optimization [C]: User Flow & IA required
- Heuristic Evaluation [H]: Build Prototype recommended (can run without)
- Testing Prep [F]: Build Prototype, Conversion Optimization, Heuristic Evaluation recommended (planned)

**Note:** While the recommended order optimizes learning flow, user can choose any available framework with met prerequisites.

### 3. Present Status Summary

Display current M4 state:
```
=== M4 PROTOTYPATION STATUS ===

Frameworks Completed: {count}/6

Completed:
{list completed frameworks with [x]}

Next Recommended: {suggestion based on analysis}
```

### 4. Present Framework Menu

```
Select a framework to work on:

[U] User Flow & IA — Map conversion paths + content hierarchy {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: None
     Output: user-flow-ia.md

[D] Design Direction — Visual design via BMAD create-ux-design {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: User Flow & IA (recommended)
     Output: design_brief.md + design.json (via BMAD)
     Note: Routes via bi-m4-design-context bridge

[B] Build Prototype — HTML/CSS implementation {recommended-indicator-if-suggested}
     Status: 🚧 Planned (to be created)
     Prerequisites: User Flow & IA, Design Direction
     Output: HTML/CSS prototype files

[C] Conversion Optimization — Apply conversion-centered design {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: User Flow & IA
     Output: conversion-optimization.md

[H] Heuristic Evaluation — Nielsen's 10 usability heuristics {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Build Prototype (recommended)
     Output: heuristic-evaluation.md

[F] Testing Prep — F&F testing protocol {recommended-indicator-if-suggested}
     Status: 🚧 Planned (to be created)
     Prerequisites: Build Prototype, Conversion Optimization, Heuristic Evaluation (recommended)
     Output: testing-protocol.md

---
[S] Status — Show detailed completion status
[BK] Back — Return to milestone selection
[X] Exit — Exit workflow
```

**Instructions for displaying recommended indicator:**
- Add ` ← Recommended next` after the framework name ONLY if it matches the recommended next framework from Section 2
- Example: `[D] Design Direction — Visual design via BMAD create-ux-design ← Recommended next`
- Prerequisites shown below should indicate ✓ for completed or ✗ for not completed
- Example: `Prerequisites: User Flow & IA ✓`
- For planned frameworks [B] and [F], show status as "🚧 Planned (to be created)" and note they cannot be selected yet

### 5. HALT

ALWAYS halt and wait for user selection.

---

## MENU ROUTING

| Selection | Action |
|-----------|--------|
| [U] | Update project-memo frontmatter currentFramework → Load `../bi-m4-user-flow-ia/workflow.md` |
| [D] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m4-design-context/workflow.md` (bridge to BMAD) |
| [B] | Display "🚧 This framework is planned for future creation. Please select an available framework." |
| [C] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m4-conversion-centered-design/workflow.md` |
| [H] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m4-heuristic-evaluation/workflow.md` |
| [F] | Display "🚧 This framework is planned for future creation. Please select an available framework." |
| [S] | Display detailed status, then redisplay menu |
| [BK] | Load `../../bi-business-innovation/workflow.md` → step-02-milestone-select.md |
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
=== M4 PROTOTYPATION DETAILED STATUS ===

M4 Frameworks (6 total):

[ ] User Flow & IA
    Prerequisites: None
    Output: m4-prototypation/user-flow-ia.md
    
[ ] Design Direction (via BMAD bridge)
    Prerequisites: User Flow & IA (recommended)
    Output: m4-prototypation/design_brief.md + design.json
    
[ ] Build Prototype
    Status: 🚧 Planned (to be created)
    Prerequisites: User Flow & IA, Design Direction
    Output: HTML/CSS prototype files
    
[ ] Conversion Optimization
    Prerequisites: User Flow & IA
    Output: m4-prototypation/conversion-optimization.md
    
[ ] Heuristic Evaluation
    Prerequisites: Build Prototype (recommended)
    Output: m4-prototypation/heuristic-evaluation.md
    
[ ] Testing Prep
    Status: 🚧 Planned (to be created)
    Prerequisites: Build Prototype, Conversion Optimization, Heuristic Evaluation (recommended)
    Output: m4-prototypation/testing-protocol.md

(Replace [ ] with [x] for completed frameworks based on stepsCompleted)

Completion: {count}/6 frameworks (4 available, 2 planned)
```

After displaying status, return to framework menu.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when user selects a framework [U/D/C/H]:
1. Check prerequisites (if applicable)
2. Update project-memo.md frontmatter: set currentFramework
3. Load the selected framework workflow and follow its instructions

When user selects [BK] Back:
1. Load `../../bi-business-innovation/workflow.md` → follow to step-02-milestone-select.md
2. That step will present the milestone menu

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Project state correctly read from project-memo frontmatter
- Accurate framework completion counts displayed
- Logical next framework suggested based on dependencies
- Prerequisites validated before loading framework workflow
- User selection routed to correct workflow or bridge
- Project-memo updated before loading new workflow
- Planned frameworks [B] and [F] clearly marked and not selectable

❌ **FAILURE:**
- Incorrect framework counts
- Loading framework workflow before checking prerequisites
- Loading framework workflow before updating project-memo
- Missing status information
- Proceeding without user selection
- Allowing selection of planned frameworks [B] and [F]
- Breaking the referral logic (milestone = menu, framework = work + return to menu)
