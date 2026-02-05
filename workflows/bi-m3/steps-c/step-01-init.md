---
stepNumber: 1
stepName: 'init'
knowledgeFile: ../data/milestone-overview.md
projectMemo: '{project-root}/_bmad-output/{project-name}/founder/project-memo.md'
---

# Step 01: M3 Brand Framework Menu

**Progress: M3 Brand Milestone** — Select framework to work on

---

## STEP GOAL

Present M3 Brand framework menu, identify completed frameworks, suggest next framework based on dependencies, and route user to the selected framework workflow.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a YC mentor. Guide the founder through brand frameworks with strategic ordering. Challenge superficial brand choices, demand grounding in customer evidence, push for authentic expression. This is a partnership.

### Step-Specific Rules

- Read project-memo frontmatter to determine which M3 frameworks are completed
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

Look for these step IDs to determine M3 framework completion:
- `bi-m3-brand-archetypes`
- `bi-m3-brand-prism`
- `bi-m3-golden-circle`
- `bi-m3-brand-positioning`
- `bi-m3-messaging-architecture`
- `bi-m3-tone-of-voice`

### 2. Analyze Progress and Dependencies

**Recommended Execution Order (from brand_process.md):**
1. Brand Archetypes → 2. Brand Prism → 3. Golden Circle → 4. Brand Positioning → 5. Messaging Architecture → 6. Tone of Voice

Determine suggested next framework from stepsCompleted:

| State | Recommended Next | Rationale |
|-------|------------------|-----------|
| No M3 frameworks completed | Brand Archetypes | Foundation for all other frameworks (Order: 1) |
| Only BA complete | Brand Prism | Build on archetype foundation (Order: 2) |
| BA + BP complete | Golden Circle | Define purpose grounded in prism (Order: 3) |
| BA + BP + GC complete | Brand Positioning | Craft competitive position with full identity (Order: 4) |
| BA + BP + GC + PO complete | Messaging Architecture | Translate positioning into hierarchical messages (Order: 5) |
| First 5 complete | Tone of Voice | Operationalize personality into writing guidelines (Order: 6) |
| All M3 complete | Return to milestone selection | M3 Brand milestone complete |

**Framework Dependencies:**
- Brand Archetypes: Requires M1 (Working Backwards, JTBD, Lean Canvas), M2 (3+ frameworks)
- Brand Prism: Requires Brand Archetypes (recommended), M1 (WB, JTBD, LC), M2 (3+ frameworks)
- Golden Circle: Requires Brand Prism (recommended), Brand Archetypes (recommended), M1 (WB, LC), M2 (3+ frameworks)
- Brand Positioning: Requires Golden Circle (recommended), Brand Prism (recommended), Brand Archetypes (recommended), M1 (WB, JTBD, LC), M2 (TAM/SAM/SOM)
- Messaging Architecture: Requires Brand Positioning (recommended), Golden Circle (recommended), Brand Prism (recommended), M1 (WB, JTBD, LC), M2 (3+ frameworks)
- Tone of Voice: Requires Messaging Architecture (recommended), Brand Archetypes (recommended), Brand Prism (recommended), M1 (WB, JTBD), M2 (3+ frameworks)

**Note:** While the recommended order optimizes learning flow, user can choose any framework with met prerequisites.

### 3. Present Status Summary

Display current M3 state:
```
=== M3 BRAND STATUS ===

Frameworks Completed: {count}/6

Completed:
{list completed frameworks with [x]}

Next Recommended: {suggestion based on analysis}
```

### 4. Present Framework Menu

```
Select a framework to work on:

[BA] Brand Archetypes — Identify brand personality archetype {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: M1 (WB, JTBD, LC), M2 (3+ frameworks)
     Output: brand-archetypes.md

[BP] Brand Prism — Map six facets of brand identity {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Brand Archetypes (recommended), M1 (WB, JTBD, LC), M2 (3+ frameworks)
     Output: brand-prism.md

[GC] Golden Circle — Define Why, How, What {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Brand Prism (recommended), Brand Archetypes (recommended), M1 (WB, LC), M2 (3+ frameworks)
     Output: golden-circle.md

[PO] Brand Positioning — Craft positioning statement + perceptual map {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Golden Circle (recommended), Brand Prism (recommended), Brand Archetypes (recommended), M1 (WB, JTBD, LC), M2 (TAM/SAM/SOM)
     Output: brand-positioning.md

[MA] Messaging Architecture — Build hierarchical message structure {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Brand Positioning (recommended), Golden Circle (recommended), Brand Prism (recommended), M1 (WB, JTBD, LC), M2 (3+ frameworks)
     Output: messaging-architecture.md

[TV] Tone of Voice — Define verbal identity guidelines {recommended-indicator-if-suggested}
     Status: {completed/not started}
     Prerequisites: Messaging Architecture (recommended), Brand Archetypes (recommended), Brand Prism (recommended), M1 (WB, JTBD), M2 (3+ frameworks)
     Output: tone-of-voice.md

---
[S] Status — Show detailed completion status
[B] Back — Return to milestone selection
[X] Exit — Exit workflow
```

**Instructions for displaying recommended indicator:**
- Add ` ← Recommended next` after the framework name ONLY if it matches the recommended next framework from Section 2
- Example: `[BP] Brand Prism — Map six facets of brand identity ← Recommended next`
- Prerequisites shown below should indicate ✓ for completed or ✗ for not completed
- Example: `Prerequisites: Brand Archetypes ✓, M1 (WB, JTBD, LC) ✓, M2 (3+ frameworks) ✓`

### 5. HALT

ALWAYS halt and wait for user selection.

---

## MENU ROUTING

| Selection | Action |
|-----------|--------|
| [BA] | Update project-memo frontmatter currentFramework → Load `../bi-m3-brand-archetypes/workflow.md` |
| [BP] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m3-brand-prism/workflow.md` |
| [GC] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m3-golden-circle/workflow.md` |
| [PO] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m3-brand-positioning/workflow.md` |
| [MA] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m3-messaging-architecture/workflow.md` |
| [TV] | Check prerequisites → Update project-memo frontmatter → Load `../bi-m3-tone-of-voice/workflow.md` |
| [S] | Display detailed status, then redisplay menu |
| [B] | Load `../../bi-business-innovation/workflow.md` → step-03-milestone-select.md |
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
=== M3 BRAND DETAILED STATUS ===

M3 Frameworks (6 total):

[ ] Brand Archetypes
    Prerequisites: M1 (WB, JTBD, LC), M2 (3+ frameworks)
    Output: m3-brand/brand-archetypes.md
    
[ ] Brand Prism
    Prerequisites: Brand Archetypes (recommended), M1 (WB, JTBD, LC), M2 (3+ frameworks)
    Output: m3-brand/brand-prism.md
    
[ ] Golden Circle
    Prerequisites: Brand Prism (recommended), Brand Archetypes (recommended), M1 (WB, LC), M2 (3+ frameworks)
    Output: m3-brand/golden-circle.md
    
[ ] Brand Positioning
    Prerequisites: Golden Circle (recommended), Brand Prism (recommended), Brand Archetypes (recommended), M1 (WB, JTBD, LC), M2 (TAM/SAM/SOM)
    Output: m3-brand/brand-positioning.md
    
[ ] Messaging Architecture
    Prerequisites: Brand Positioning (recommended), Golden Circle (recommended), Brand Prism (recommended), M1 (WB, JTBD, LC), M2 (3+ frameworks)
    Output: m3-brand/messaging-architecture.md
    
[ ] Tone of Voice
    Prerequisites: Messaging Architecture (recommended), Brand Archetypes (recommended), Brand Prism (recommended), M1 (WB, JTBD), M2 (3+ frameworks)
    Output: m3-brand/tone-of-voice.md

(Replace [ ] with [x] for completed frameworks based on stepsCompleted)

Completion: {count}/6 frameworks
```

After displaying status, return to framework menu.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when user selects a framework [BA/BP/GC/PO/MA/TV]:
1. Check prerequisites (if applicable)
2. Update project-memo.md frontmatter: set currentFramework
3. Load the selected framework workflow and follow its instructions

When user selects [B] Back:
1. Load `../../bi-business-innovation/workflow.md` → follow to step-03-milestone-select.md
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
