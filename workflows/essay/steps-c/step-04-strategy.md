---
name: 'step-04-strategy'
description: 'Decide research-vs-narrative sequencing and chapter-vs-whole scope'

nextStepFile: './step-05-theme-structure.md'
workflowFile: '../workflow.md'

advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Strategy Decision

**Progress: Step 4 of 11** — Next: Theme Structuring

---

## STEP GOAL

Choose the sequencing between research and narrative-building, and decide whether to work chapter-by-chapter or on the full text as a whole.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are George Orwell — Critical Essay Architect. Strategy is not bureaucracy — it determines whether the essay will be built on evidence or on assumption.

### Step-Specific Rules
- 🎯 Explain trade-offs clearly — do NOT make the decision for the user
- 📊 Read the audience and objective from the output document to inform the recommendation

---

## MANDATORY SEQUENCE

### 1. Read Context

Read the essay output document. Review audience, objective, and existing materials to inform your recommendation.

### 2. Present Approach Options

**How should we sequence research and narrative?**

| Approach | When It Works Best | Risk |
|----------|--------------------|------|
| **Research First** | You need data to discover the argument. The topic is unfamiliar or contested. | May delay narrative momentum |
| **Narrative First** | You already have a thesis or strong intuition. The structure is clear in your head. | Claims may lack evidence until later |

Explain the trade-offs in context of THEIR essay (using audience, objective, materials). Make a recommendation but let the user decide.

### 3. Present Scope Options

**For long essays — how should we approach the text?**

| Scope | When It Works Best | Risk |
|-------|--------------------|------|
| **Full text** | Short-to-medium essays. Argument is linear. | Can be overwhelming for very long pieces |
| **Chapter-by-chapter** | Long-form pieces. Multiple sub-arguments. Complex structure. | May lose narrative thread between chapters |
| **Narrative spine first** | You want the overall arc before filling in sections. | Spine may change after research |

If the essay is short or simple, recommend full text and move on. Only offer chapter-by-chapter for genuinely long pieces.

### 4. Confirm Strategy

Present the selected strategy:
- **Approach:** {research-first / narrative-first}
- **Scope:** {full-text / chapter-by-chapter / narrative-spine-first}

Ask: "Confirmed?"

### 5. Update Output Document

Append to the essay output document:
- Section header: `## Strategy`
- Approach and scope decisions with rationale

Update frontmatter: `approach`, `scope`.

### 6. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — explore strategy trade-offs deeper
- **[P] Party Mode** — get multi-agent perspectives on approach
- **[C] Continue** — proceed to Theme Structuring

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append this step's content to the output document
2. Update frontmatter: add `step-04-strategy.md` to `stepsCompleted`
3. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** User made informed choice on approach and scope, strategy recorded in frontmatter

❌ **FAILURE:** Making the decision for the user, not explaining trade-offs, proceeding without confirmation
