---
name: 'step-02-funnel-mapping'
description: 'Map conversion funnel stages and identify friction points'
nextStepFile: './step-03-hypothesis-generation.md'
outputFile: '{outputFolder}/conversion-optimization.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Funnel Mapping & Friction Analysis

**Progress: Step 2 of 5** — Next: Hypothesis Generation

---

## STEP GOAL

Map the conversion funnel through AIDA stages (Attention → Interest → Credibility → Action), analyze each stage against CCD principles, and identify friction points with severity ratings.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Be brutally honest about friction. If something doesn't serve conversion, call it out. Founders often fall in love with design elements that hurt conversion.

### Step-Specific Rules
- Every friction point needs a severity rating (Critical/Major/Moderate/Minor/Cosmetic)
- Reference specific elements from user-flow-ia.md — don't analyze in abstract
- If prototype exists, analyze actual implementation; if not, analyze planned structure

---

## CONTEXT BOUNDARIES

**Available context:**
- conversion-optimization.md from Step 1
- user-flow-ia.md for funnel structure
- design_brief.md / design.json if available
- data/conversion-framework.md for principles

**Out of scope:**
- Generating optimization solutions (Step 3)
- Prioritizing fixes (Step 4)
- Technical implementation details

---

## MANDATORY SEQUENCE

### 1. Load Funnel Structure

From user-flow-ia.md, extract:
- Entry points
- Screen/section sequence
- Decision points
- Conversion goal
- Content hierarchy per section

Present the funnel structure for confirmation:
> "Based on your User Flow & IA, here's the conversion funnel I'll analyze:
> 
> **Entry:** [entry points]
> **Flow:** [section 1] → [section 2] → ... → [CTA]
> **Goal:** [conversion action]
> 
> Is this accurate?"

Wait for confirmation before proceeding.

### 2. AIDA Stage Analysis

For each AIDA stage, analyze against CCD principles:

**Attention Stage (Hero/Above-fold):**
- Does the headline stop the scroll?
- Is the value proposition immediately clear?
- What is the attention ratio? (count links vs. conversion goal)
- Are there visual distractions competing with the message?

**Interest Stage (Problem/Benefits):**
- Does content address the customer's problem?
- Is the language customer-focused ("you") vs. company-focused ("we")?
- Is information progressively disclosed or overwhelming?
- Are directional cues guiding toward next section?

**Credibility Stage (Social Proof/Trust):**
- What trust elements exist? (testimonials, logos, data)
- Are trust signals placed near decision points?
- Is there specificity? (vague praise vs. concrete results)
- Missing trust elements that competitors have?

**Action Stage (CTA Zone):**
- Is CTA the most visually prominent element?
- Is there encapsulation (clear decision zone)?
- Does CTA copy specify the benefit? (not "Submit")
- What happens after click? Is it clear?
- Is CTA above fold AND repeated at scroll points?

Present analysis to founder section by section.

### 3. Friction Point Identification

For each identified issue, document:

| Friction Point | Stage | Category | Severity | Evidence |
|----------------|-------|----------|----------|----------|
| [Description] | [AIDA stage] | [Cognitive/Mechanical/Trust/Value/Technical] | [5-1] | [What you observed] |

**Severity Guide:**
- **5 (Critical):** Blocks conversion entirely
- **4 (Major):** Significant barrier, many abandon
- **3 (Moderate):** Noticeable hesitation
- **2 (Minor):** Small annoyance
- **1 (Cosmetic):** Polish only

Ask founder to validate or challenge each friction point:
> "I've identified [N] friction points. Let me walk through them:
> 
> 1. **[Friction Point]** — [Evidence]. I rate this [Severity] because [rationale].
>    Do you agree?"

### 4. Distraction Audit

Review all page elements against the "5 Questions":
1. Does this drive conversion? 
2. Does this answer a key objection?
3. Is this above the fold? If yes, is it essential?
4. Does this link away from the page?
5. Would a first-time visitor understand this?

List elements that fail multiple questions:
> "**Distraction Candidates:**
> - [Element]: Fails questions [N, N] — recommend [remove/move/justify]"

### 5. Update Output Document

Add to conversion-optimization.md:

```markdown
## Funnel Analysis

### Entry Points
[List from user-flow-ia]

### AIDA Stage Breakdown

#### Attention
[Analysis]

#### Interest
[Analysis]

#### Credibility
[Analysis]

#### Action
[Analysis]

## Friction Points

| # | Friction Point | Stage | Category | Severity | Evidence |
|---|----------------|-------|----------|----------|----------|
| 1 | [Description] | [Stage] | [Category] | [5-1] | [Evidence] |
| ... | ... | ... | ... | ... | ... |

### Distraction Audit

| Element | Fails Questions | Recommendation |
|---------|-----------------|----------------|
| [Element] | [1, 4] | [Remove/Move/Justify] |
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-funnel-mapping']
```

### 6. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on any friction point or stage
- **[P] Party Mode** — get multi-agent perspectives on friction analysis
- **[C] Continue** — proceed to Hypothesis Generation

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Funnel Analysis and Friction Points sections are complete
2. Verify frontmatter updated with `step-02-funnel-mapping`
3. Load `./step-03-hypothesis-generation.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All AIDA stages analyzed, friction points documented with severity, distraction audit complete, founder validated findings

❌ **FAILURE:** Skipping stages, not rating severity, generating solutions instead of identifying problems, not getting founder validation
