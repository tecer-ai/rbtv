---
name: 'step-10-critical-review'
description: 'Full adversarial review with critics panel — Orwell standards + AI-pattern audit + voice fidelity + reader advocate'
aiAntiPatterns: '../data/ai-anti-patterns.md'

nextStepFile: './step-11-synthesis.md'
workflowFile: '../workflow.md'

---

# Step 10: Critical Review

**Progress: Step 10 of 11** — Next: Final Synthesis

---

## STEP GOAL

Perform a full adversarial review of the complete essay using two review passes: (1) Orwell's Standards — the 5 classic quality categories, and (2) Critics Panel — three specialized perspectives that catch what Orwell's standards miss.

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

### 3. Critics Panel (Three Additional Perspectives)

After completing the 5 Orwell categories, run three specialized critics. Each reviews the COMPLETE essay from a distinct angle.

**F. AI-Pattern Audit (The Detector)**
- Load `{aiAntiPatterns}`
- Scan the entire essay against all 8 anti-pattern categories
- For each finding: quote the offending passage, name the anti-pattern, propose a human-sounding alternative
- Pay special attention to: over-symmetry, generic phrasing, edge erosion, premature resolution

**G. Voice Fidelity Check (The Mimic)**
- Compare the draft against the voice profile established in step 03
- If a persistent style guide exists (`styleGuide` in frontmatter): compare against the guide's signature moves, core directives, and anti-patterns
- Flag passages where the voice drifts — becomes generic, loses characteristic patterns, or contradicts the guide
- Score estimate: what proportion of the essay sounds like the writer vs. sounds like "AI writing"?

**H. Reader Advocate (The Outsider)**
- Read as the target audience defined in step 02
- Flag: where would THIS specific reader lose interest? Get confused? Push back? Disagree?
- Flag: "so what?" moments — where the essay hasn't earned the reader's attention
- Be audience-specific: a CEO flags different things than a developer, an academic different things than a journalist

### 4. Present Review

**Orwell's Standards** — present findings in a structured format:

| # | Category | Location | Severity | Finding | Recommendation |
|---|----------|----------|----------|---------|----------------|

Group by severity: critical issues first, then moderate, then minor.

**Critics Panel** — present in a separate table:

| Critic | Location | Finding | Suggested Fix |
|--------|----------|---------|---------------|

### 5. Discuss with User

For each critical and moderate finding (from both tables):
- Explain WHY it weakens the essay
- Propose a specific fix
- Ask: "Address this, or keep as-is with justification?"

### 6. Update Output Document

Append to the essay output document:
- Section header: `## Critical Review`
- Orwell's Standards findings table
- Section header: `## Critics Panel Review`
- Critics Panel findings table
- User decisions on each finding

### 7. Present Menu Options

**Select an Option:**
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

✅ **SUCCESS:** All 5 Orwell categories reviewed, all 3 critics panel perspectives applied, findings are specific and actionable, user addressed all critical issues, AI anti-patterns flagged with alternatives

❌ **FAILURE:** Rubber-stamping the essay, vague findings ("could be better"), missing logical fallacies, skipping the critics panel, not checking source links, not loading ai-anti-patterns.md
