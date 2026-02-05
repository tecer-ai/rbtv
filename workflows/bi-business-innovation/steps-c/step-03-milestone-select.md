---
stepNumber: 3
stepName: 'milestone-select'
knowledgeFile: ../data/founder-process.md
projectMemo: '{project-root}/_bmad-output/{project-name}/founder/project-memo.md'
---

# Step 03: Milestone Selection

**Progress: Step 3 of 3** — Routes to milestone workflows

---

## STEP GOAL

Present milestone overview, identify current project state, and route user to the appropriate milestone workflow.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a YC mentor. Help the founder understand where they are in the journey and what comes next. Be direct about progress and gaps.

### Step-Specific Rules

- Read project-memo frontmatter to determine current state
- Suggest the logical next milestone based on stepsCompleted
- Allow user to override suggestion and select any milestone
- Update project-memo frontmatter on milestone selection

---

## MANDATORY SEQUENCE

### 1. Load Project State

Read `{projectMemo}` frontmatter to understand:
- currentMilestone
- currentFramework
- stepsCompleted array

### 2. Analyze Progress

Determine suggested next action from stepsCompleted:

| State | Suggestion |
|-------|------------|
| No frameworks completed | Start M1: Conception |
| M1 partially complete | Continue M1: {next framework} |
| M1 complete, M2 not started | Start M2: Validation |
| M{N} partially complete | Continue M{N}: {next framework} |
| All milestones complete | Review and refine |

### 3. Present Status Summary

Display current project state:
```
Project: {project-name}
Current Milestone: {currentMilestone}
Frameworks Completed: {count}/{total}

Suggested Next: {suggestion based on analysis}
```

### 4. Present Milestone Menu

```
Select a milestone to work on:

[M1] Conception — Structure idea into business concept
     Frameworks: Working Backwards, JTBD, Competitive, PSF, Lean Canvas, 5 Whys
     Status: {completed}/{total} frameworks

[M2] Validation — Validate technical and financial feasibility
     Frameworks: Leap of Faith, Assumptions, TAM/SAM/SOM, Unit Econ, TRL, Pre-mortem
     Status: {completed}/{total} frameworks

[M3] Brand — Create preliminary brand identity
     Frameworks: Archetypes, Brand Prism, Golden Circle, Positioning, Tone, Messaging
     Status: {completed}/{total} frameworks

[M4] Prototypation — Build working HTML prototype
     Status: {completed}/{total} frameworks

[M5] Market Validation — Validate market demand
     Status: {completed}/{total} frameworks

[M6] MVP — Create minimum viable product
     Status: {completed}/{total} frameworks

---
[S] Status — Show detailed project status
[X] Exit — Exit workflow
```

### 5. HALT

ALWAYS halt and wait for user selection.

---

## MENU ROUTING

| Selection | Action |
|-----------|--------|
| [M1] | Update project-memo frontmatter → Load `../../../bi-m1/workflow.md` |
| [M2] | Update project-memo frontmatter → Load `../../../bi-m2/workflow.md` |
| [M3] | Update project-memo frontmatter → Load `../../../bi-m3/workflow.md` |
| [M4] | Update project-memo frontmatter → Load `../../../bi-m4/workflow.md` |
| [M5] | Update project-memo frontmatter → Load `../../../bi-m5/workflow.md` |
| [M6] | Update project-memo frontmatter → Load `../../../bi-m6/workflow.md` |
| [S] | Display detailed status, then redisplay menu |
| [X] | Exit workflow |

---

## STATUS DISPLAY (for [S] option)

```
=== PROJECT STATUS: {project-name} ===

Current Milestone: {currentMilestone}

M1: Conception
  [ ] Working Backwards
  [ ] Jobs-to-be-Done
  [ ] Competitive Landscape
  [ ] Problem-Solution Fit
  [ ] Lean Canvas
  [ ] Five Whys

M2: Validation
  [ ] Leap of Faith
  [ ] Assumption Mapping
  [ ] TAM/SAM/SOM
  [ ] Unit Economics
  [ ] Technology Readiness Level
  [ ] Pre-mortem

M3: Brand
  [ ] Brand Archetypes
  [ ] Brand Prism
  [ ] Golden Circle
  [ ] Brand Positioning
  [ ] Tone of Voice
  [ ] Messaging Architecture

(Replace [ ] with [x] for completed frameworks based on stepsCompleted)

Open Questions:
- {from project-memo}
```

After displaying status, return to milestone menu.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when user selects a milestone [M1-M6]:
1. Update project-memo.md frontmatter: set currentMilestone
2. Load the selected milestone workflow and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Project state correctly read from project-memo frontmatter
- Accurate progress summary displayed
- Logical next milestone suggested
- User selection routed to correct workflow
- Project-memo updated before loading new workflow

❌ **FAILURE:**
- Incorrect framework counts
- Loading milestone workflow before updating project-memo
- Missing status information
- Proceeding without user selection
