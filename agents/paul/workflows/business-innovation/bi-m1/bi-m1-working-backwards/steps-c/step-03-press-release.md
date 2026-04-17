---
name: 'step-03-press-release'
description: 'Draft customer-facing press release answering four core questions'
nextStepFile: './step-04-faq.md'
outputFile: '{outputFolder}/working-backwards.md'
---

# Step 3: Draft Press Release

**Progress: Step 3 of 5** — Next: Draft FAQ

---

## STEP GOAL

Write a one-page press release, set at a future launch date, that answers the four core customer questions in clear, compelling language.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for customer language over internal jargon. Every sentence must tie to customer benefit. Cut fluff ruthlessly.

### Step-Specific Rules
- Press Release must fit on ONE PAGE at readable font size
- Remove ALL internal jargon and implementation detail
- Every claim must be verifiable or labeled as assumption
- Do NOT draft FAQ in this step — that's Step 4

---

## CONTEXT BOUNDARIES

**Available context:**
- Customer & Problem Brief from Step 2
- Project context from project-memo
- Framework knowledge from data/working-backwards-framework.md

**Out of scope:**
- FAQ drafting (Step 4)
- Internal feasibility questions (Step 4)
- Synthesis and project-memo update (Step 5)

---

## MANDATORY SEQUENCE

### 1. Launch Context Setup

Ask:
> "Let's set the scene for this press release:
> 1. What's a realistic future launch date? (typically 6-24 months out)
> 2. What's the launch context? (event, blog post, email announcement, etc.)"

### 2. Headline and Subheading

Ask:
> "The headline should capture the core customer benefit — not the technology. What's the single most important thing that changes for your customer?"

Draft headline together. Then:
> "The subheading names the primary customer and what changes. Let's write it."

### 3. Problem Paragraph

Ask:
> "Paint a vivid picture of your customer's pain today. Be specific:
> - What triggers the pain?
> - What emotions does it create?
> - What do they try that doesn't work?"

Draft the problem paragraph from their response.

### 4. Solution Paragraph

Ask:
> "Now describe how your product solves that pain — but in customer language. What do they experience? What changes in their daily work?"

**Challenge if too technical:**
> "A customer wouldn't say that. How would you explain this to your primary customer over coffee?"

### 5. Leader Quote

Ask:
> "What quote from you (or a founder) would explain why this matters? Make it personal and specific."

### 6. How It Works

Ask:
> "Walk me through a typical customer's first day with your product. What do they do? What happens? What result do they see?"

Draft 1-2 paragraphs from the journey.

### 7. Customer Quote

Ask:
> "Imagine an ideal customer just finished their first week. What would they say to a colleague about the experience?"

Draft a hypothetical quote with a named archetype (e.g., "Sarah, Marketing Director at a 50-person SaaS company").

### 8. Getting Started

Ask:
> "How does someone get started?
> - Is there a trial? Waitlist? Demo?
> - What's the high-level pricing model?
> - What's the onboarding friction?"

### 9. Assemble Full Press Release

Compile all sections into structured PR:

```markdown
## Press Release

**[HEADLINE]**
*[Subheading: names customer and change]*

[CITY, DATE] — [Intro paragraph: category and context]

[Problem paragraph]

[Solution paragraph]

"[Leader quote]" — [Name, Title]

**How It Works**
[Customer journey paragraphs]

"[Customer quote]" — [Customer Name, Title, Company Type]

**Getting Started**
[Access, pricing, onboarding]
```

### 10. Jargon Check

Read the PR aloud. Highlight any sentence that:
- Uses internal terminology
- Makes unverifiable claims
- Doesn't tie to customer benefit

Revise with founder until clean.

### 11. Validation Checklist

Before proceeding, confirm:
- [ ] Fits on one page at readable font size
- [ ] Customer and problem clear in first two paragraphs
- [ ] No internal jargon or implementation detail
- [ ] Claims are either verifiable or labeled as assumptions

### 12. Update Output Document

Update working-backwards.md with completed Press Release section.

### 13. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Draft FAQ

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append Press Release to working-backwards.md
2. Update frontmatter: add `step-03-press-release` to `stepsCompleted`
3. Load `./step-04-faq.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** One-page PR completed, all four core questions answered, jargon-free

❌ **FAILURE:** PR exceeds one page, uses internal jargon, skips validation checklist
