---
name: 'step-04-faq'
description: 'Draft external and internal FAQ, answer Is it worth doing?'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/working-backwards.md'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Draft FAQ

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

Create External FAQ (customer questions) and Internal FAQ (feasibility, economics, strategy) culminating in a clear answer to "Is it worth doing?"

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Ask the hard questions. Push on assumptions. "Is it worth doing?" must be answered honestly — even if the answer is "not yet" or "no."

### Step-Specific Rules
- External FAQ must have at least 10 substantial questions
- Internal FAQ MUST answer "Is it worth doing?" explicitly
- Unknown answers must be tagged as assumptions for M2 validation
- Do NOT skip the Internal FAQ — it's the most critical part

---

## CONTEXT BOUNDARIES

**Available context:**
- Customer & Problem Brief from Step 2
- Press Release from Step 3
- Project context from project-memo

**Out of scope:**
- Project-memo update (Step 5)
- Detailed validation experiment design (M2)

---

## MANDATORY SEQUENCE

### Part A: External FAQ

### 1. Question Brainstorm

Guide the founder:
> "Let's anticipate what customers, partners, and stakeholders will ask when they read the press release. Think about:
> - Product understanding: 'What is it?', 'How does it work?'
> - Eligibility: 'Is this for companies like mine?'
> - Pricing and terms
> - Integration and migration
> - Data, privacy, and trust
> - Support and reliability"

Ask: "Give me 10-15 questions a serious buyer would ask."

### 2. Question Prioritization

From the brainstorm, select 10-15 core questions that:
- A serious buyer would ask before adopting
- Reveal hidden complexity or trade-offs

### 3. Draft Answers

For each question:
> "Let's answer this in customer language. Be specific — avoid 'it depends' without context."

If the founder cannot answer credibly:
- Tag as **[ASSUMPTION — requires validation]**
- Add to assumption list for M2

### 4. Coverage Check

Verify:
> "Every bold claim in the PR should have at least one FAQ explaining constraints or conditions. Let me check..."

Review PR claims against FAQ coverage.

---

### Part B: Internal FAQ

### 5. Internal Question Themes

Explain:
> "The Internal FAQ surfaces the hard questions about whether this is worth pursuing. We'll cover:
> - Feasibility and resources
> - Economics (TAM, unit economics, pricing)
> - Dependencies and risks
> - Strategic fit
> - Success metrics and kill criteria"

### 6. Feasibility Questions

Ask:
> "What capabilities must you build that you don't have today? What are the top 3 technical unknowns?"

Document answers honestly.

### 7. Economics Questions

Ask:
> "Let's talk numbers:
> - What's your rough TAM estimate? (order of magnitude is fine)
> - What has to be true about customer behavior for unit economics to work?
> - What's your initial pricing hypothesis?"

Use ranges, not fake precision.

### 8. Risk and Dependencies

Ask:
> "What external dependencies could block you? (partners, regulation, data, platform risk)"
>
> "What would make you kill this project after 3-6 months?"

### 9. Is It Worth Doing?

**CRITICAL — This must be answered explicitly.**

Ask:
> "Based on everything we've discussed:
> - What's the economic potential? (magnitude, time to impact)
> - What are the main risks and unknowns?
> - What's your investment thesis?"

Draft the answer together:
> "Is it worth doing? [Yes/Not yet/Only if X/No]
>
> Rationale: [Summary]
>
> Next steps if advancing: [What assumptions to validate in M2]"

### 10. Assumption Inventory

Compile all assumptions tagged throughout:

| # | Assumption | Source | Priority |
|---|------------|--------|----------|
| 1 | ... | External FAQ Q3 | High |
| 2 | ... | Internal FAQ - Economics | High |
| ... | ... | ... | ... |

### 11. Update Output Document

Update working-backwards.md with:
- External FAQ section
- Internal FAQ section
- Assumption inventory

### 12. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on specific FAQ areas
- **[P] Party Mode** — stress-test "Is it worth doing?" from multiple perspectives
- **[C] Continue** — proceed to Synthesis

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append External FAQ, Internal FAQ, and Assumption Inventory to working-backwards.md
2. Update frontmatter: add `step-04-faq` to `stepsCompleted`
3. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 10+ External FAQs answered, Internal FAQ with explicit "Is it worth doing?" answer, assumptions tagged

❌ **FAILURE:** Skipping Internal FAQ, no "Is it worth doing?" answer, assumptions left untagged
