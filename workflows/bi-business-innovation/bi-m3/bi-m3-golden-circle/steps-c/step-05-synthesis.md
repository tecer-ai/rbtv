---
name: 'step-05-synthesis'
description: 'Validate authenticity, compile document, update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/golden-circle.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Validate the complete Golden Circle through Endurance, Authenticity, and Motivation tests. Verify consistency with Brand Prism and Archetypes. Update project-memo.md.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The Why must pass all three validation tests. If it doesn't, revise before completing. The Golden Circle is now the purpose reference for all downstream work.

### Step-Specific Rules
- All three validation tests are REQUIRED
- Consistency check with Brand Prism/Archetypes is REQUIRED
- project-memo.md MUST be updated with Golden Circle synthesis
- Integration notes for downstream frameworks are REQUIRED

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/golden-circle.md` from Steps 1-4
2. Read `{outputFolder}/brand-prism.md` for consistency check
3. Read `{outputFolder}/brand-archetypes.md` for motivation alignment
4. Read `{outputFolder}/project-memo.md` for update

---

## MANDATORY SEQUENCE

### 1. Endurance Test

Present the Why and ask:

> "Imagine you pivot to a completely different product in the same domain. For example, from SaaS to consulting, or from B2B to B2C.
>
> Does this Why still hold? Does the How still apply?"

If no:
- The Why is too product-specific
- Return to Step 2 to revise
- Do not proceed until Why survives pivot

If yes:
- Document: "Endurance Test: PASSED — Why survives product pivot"

### 2. Authenticity Test

Ask the founder directly:

> "Read this Why aloud: '[Why statement]'
>
> Does this feel true to you? Would you say this to a friend? Can you say 'I believe this' without hesitation?"

If hesitation or qualification:
- The Why needs revision to reflect genuine conviction
- Return to Step 2 to revise
- Do not proceed until founder owns it

If confident:
- Document: "Authenticity Test: PASSED — Founder owns Why without hesitation"

### 3. Motivation Test

Ask:

> "Imagine presenting this Why to a potential team member or early customer.
>
> Does this make them want to be part of this? Or does it generate indifference?"

If indifference:
- The Why lacks emotional charge
- It may be accurate but uninspiring
- Return to Step 2 to add conviction

If inspiring:
- Document: "Motivation Test: PASSED — Why generates desire to participate"

### 4. Consistency Check

Verify alignment with prior frameworks:

**Brand Prism Culture:**
> "Your Culture facet says [culture beliefs]. Does your Why echo this?"

If contradiction → decide which is more accurate, update the weaker artefact

**Brand Prism Personality:**
> "Your Personality facet says [traits]. Does your How echo this?"

If contradiction → decide which is more accurate, update

**Brand Archetypes Motivation:**
> "Your archetype [name] has core motivation [motivation]. Does your Why resonate with this?"

If contradiction → investigate and resolve

Document consistency check results and any updates made.

### 5. Prepare Integration Notes

Document what each downstream framework receives:

```markdown
## Integration Notes

**Brand Positioning:**
- Why becomes foundation of positioning benefit claim
- How principles define differentiation mechanism

**Messaging Architecture:**
- Why = brand promise layer
- How principles = supporting message pillars

**Tone of Voice:**
- Why's emotional register calibrates voice dimensions
- How principles set communication style

**M4 Design Brief:**
- Why sets emotional territory for visual identity
- How principles inform design system values

**M5 Market Validation:**
- Why statement = messaging hypothesis to test with customers
```

### 6. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` for M3.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 7. Compile Final Document

Ensure golden-circle.md contains all sections:

1. **Purpose Signals Summary** — sources that informed Why
2. **Why Statement** — single sentence
3. **Why Narrative** — supporting paragraph with traceability
4. **How Principles** — 2-3 principles with observable examples
5. **What Statement** — plain product description
6. **Why-How-What Chain** — complete narrative
7. **Validation Results** — Endurance, Authenticity, Motivation tests
8. **Consistency Check** — alignment with Prism and Archetypes
9. **Integration Notes** — downstream framework wiring

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-why-discovery', 'step-03-how-articulation', 'step-04-what-definition', 'step-05-synthesis']
status: completed
```

### 8. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m3-golden-circle` to `stepsCompleted` array

**In Progress > M3 Brand section:**

```markdown
### Golden Circle

**Status:** Completed

**Why:** "[Why statement]"

**How:**
1. [First How principle]
2. [Second How principle]
3. [Third How principle, if exists]

**What:** [What statement]

**Why-How-What Chain:**
"[Complete chain narrative]"

**Validation:**
- Endurance: PASSED
- Authenticity: PASSED
- Motivation: PASSED

**Output:** [Link to golden-circle.md]
```

### 9. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 10. Completion Summary

Present to founder:

> "Golden Circle framework complete!
>
> **Your Why:**
> '[Why statement]'
>
> **What we validated:**
> - Survives product pivot (Endurance)
> - Authentic to you (Authenticity)
> - Inspires others (Motivation)
> - Consistent with Brand Prism and Archetypes
>
> **What feeds forward:**
> - Brand Positioning: Why → benefit claim
> - Messaging Architecture: Why → brand promise layer
> - Tone of Voice: Why → emotional register
> - M4 Design Brief: Why → visual emotional territory
> - M5 Market Validation: Why → messaging hypothesis
>
> **Next recommended framework:** Brand Positioning
>
> **Return path:** To continue other M3 frameworks, return to bi-m3 milestone workflow."

### 11. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M3.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M3 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 12. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M3** — return to M3 Brand milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M3** is selected:
1. Verify golden-circle.md has status: completed
2. Verify project-memo.md has Golden Circle entry
3. Load `../bi-m3/workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All three validation tests passed, consistency check completed, integration notes prepared, project-memo.md updated, Golden Circle marked complete

❌ **FAILURE:** Validation tests failed and not re-run, project-memo.md not updated, integration notes missing, consistency contradictions unresolved
