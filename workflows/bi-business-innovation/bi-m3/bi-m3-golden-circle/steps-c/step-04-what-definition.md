---
name: 'step-04-what-definition'
description: 'State tangible offering connected to Why and How'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/golden-circle.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: What Definition

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

State the tangible products or services, connecting them explicitly back to Why and How through the complete narrative chain.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The What is deliberately simple — a plain description of the offering. Don't let founders embed purpose language into product description. The Why and How give the What meaning.

### Step-Specific Rules
- What must name a recognizable product category
- What must use customer language, not internal terminology
- What must NOT include superlatives or purpose language
- The Why-How-What chain must read as coherent narrative

---

## CONTEXT TO LOAD

1. Read current `{outputFolder}/golden-circle.md` for Why and How
2. Read `{outputFolder}/lean-canvas.md` Solution block
3. Read Working Backwards PR headline and solution paragraph

---

## MANDATORY SEQUENCE

### 1. Ground in Customer Language

Review customer-facing descriptions:

> "From your Lean Canvas Solution and Working Backwards PR headline, here's how you've described the product to customers..."

Present the existing descriptions.

### 2. Draft What Statement

Guide founder to articulate the What in 1-2 sentences:

**Format:** Plain description of product category and primary offering.

**Rules:**
- Name a category customers already understand
- Use the words customers would use
- No purpose language ("revolutionary", "empowering", etc.)
- No superlatives ("best", "most powerful", etc.)
- No jargon customers wouldn't know

**Example transformations:**

| Before (Bad) | After (Good) |
|--------------|--------------|
| "Revolutionary AI-powered analytics platform that empowers teams" | "Business analytics software for small marketing teams" |
| "The world's most intuitive project management solution" | "Project management tool for remote creative agencies" |

Ask:
> "In plain language, what do you make and for whom?"

### 3. Test Category Recognition

> "If a potential customer heard this What statement, would they immediately understand what category you're in?"

If confusion → simplify until category is obvious

### 4. Test Plainness

> "Does this What statement try to do the work of Why or How?"

**Signs of overreach:**
- Includes "because" or "so that" clauses
- Uses emotional language
- Makes promises beyond the product category

If overreach → strip back to simple description

### 5. Write the Why-How-What Chain

Compose the complete narrative:

> "We believe [Why].
> That is why we [How].
> And that is how we deliver [What]."

**Example:**
> "We believe small businesses deserve the same insights as enterprises. That is why we show our reasoning and design for clarity over features. And that is how we deliver business analytics software for small marketing teams."

### 6. Test Chain Coherence

Read the chain aloud:

> "Does this read as a coherent story from belief to offering? Or does any link feel forced?"

If forced:
- Identify the weak link
- Revise the weak element
- Re-test until chain flows naturally

### 7. Test What Independence

> "If I read ONLY the What statement, would it be indistinguishable from a generic competitor description?"

If yes → the Why and How are doing their job (giving the What meaning)

If the What alone is distinctive → it may be doing the work of Why/How (revise)

### 8. Update golden-circle.md

Update the What section with:
- What Statement (1-2 sentences)
- Why-How-What Chain (complete narrative paragraph)

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-why-discovery', 'step-03-how-articulation', 'step-04-what-definition']
```

### 9. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine What or chain narrative
- **[C] Continue** — proceed to Synthesis (validation and project-memo update)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure What Statement exists (plain, category-naming, customer language)
2. Ensure Why-How-What Chain exists and reads coherently
3. Verify `step-04-what-definition` is in `stepsCompleted`
4. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** What statement names recognizable category in customer language, is plain without superlatives, the Why-How-What chain reads as coherent narrative

❌ **FAILURE:** What includes purpose language or superlatives, uses internal jargon, chain narrative feels forced or disconnected
