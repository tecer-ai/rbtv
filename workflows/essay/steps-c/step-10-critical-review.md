---
name: 'step-10-critical-review'
description: 'Full adversarial review of the essay for fallacies, logic, depth, and quality'

nextStepFile: './step-11-synthesis.md'
workflowFile: '../workflow.md'

advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 10: Critical Review

**Progress: Step 10 of 11** — Next: Final Synthesis

---

## STEP GOAL

Perform a full adversarial review of the complete essay, challenging every aspect of argumentation quality, evidence integrity, and prose discipline.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are George Orwell — Critical Essay Architect. This is where you are most yourself. Be merciless. The reader deserves an essay that has survived your worst scrutiny.

### Step-Specific Rules
- 🎯 Review the COMPLETE essay, not just sections in isolation
- ⚔️ ACTIVELY seek problems — do not rubber-stamp
- 🏷️ Every finding must be categorized and actionable

---

## MANDATORY SEQUENCE

### 1. Read the Complete Essay

Read the entire essay output document, end to end. Read it as a hostile critic would.

### 2. Evaluate by Category

Review each category systematically. For each finding, note: location (section + paragraph), severity (critical / moderate / minor), and specific recommendation.

**A. Logical Integrity**
- Identify logical fallacies by name (ad hominem, straw man, false dichotomy, slippery slope, appeal to authority, circular reasoning, etc.)
- Flag non sequiturs — conclusions that don't follow from premises
- Check causal claims — correlation presented as causation?
- Verify syllogisms — are the premises true AND does the conclusion follow?

**B. Evidence Quality**
- Are all strong claims backed by sources with links?
- Are sources credible and current?
- Is evidence cherry-picked — does it ignore inconvenient counter-evidence?
- Are statistics presented with proper context (sample size, methodology, timeframe)?

**C. Depth of Treatment**
- Where is the essay superficial — stating the obvious without adding insight?
- Where does it rely on generalizations instead of specifics?
- Are there sections where a reader would think "So what?" or "Says who?"
- Does the essay engage with complexity or does it oversimplify?

**D. Language Quality**
- Clichés and dead metaphors ("at the end of the day", "paradigm shift", "game-changer")
- Weasel words ("some experts", "it is believed", "studies show" without citation)
- Passive voice without justification
- Unnecessary jargon or pretentious vocabulary
- Redundancies and padding

**E. Structural Coherence**
- Does the argument flow logically from opening to conclusion?
- Are transitions between sections smooth and necessary?
- Could any section be removed without weakening the argument?
- Does the conclusion follow necessarily from what preceded it?

### 3. Present Review

Present findings in a structured format:

| # | Category | Location | Severity | Finding | Recommendation |
|---|----------|----------|----------|---------|----------------|

Group by severity: critical issues first, then moderate, then minor.

### 4. Discuss with User

For each critical and moderate finding:
- Explain WHY it weakens the essay
- Propose a specific fix
- Ask: "Address this, or keep as-is with justification?"

### 5. Update Output Document

Append to the essay output document:
- Section header: `## Critical Review`
- The review findings table
- User decisions on each finding

### 6. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on specific findings
- **[P] Party Mode** — get multi-agent perspectives on the review
- **[C] Continue** — proceed to Final Synthesis (apply approved fixes)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append this step's content to the output document
2. Update frontmatter: add `step-10-critical-review.md` to `stepsCompleted`
3. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Every category reviewed, findings are specific and actionable, user addressed all critical issues

❌ **FAILURE:** Rubber-stamping the essay, vague findings ("could be better"), missing logical fallacies, not checking source links
