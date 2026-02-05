---
name: 'step-02-heuristic-review'
description: 'Evaluate design against all 10 heuristics, document violations'
nextStepFile: './step-03-severity-rating.md'
outputFile: '{project-root}/_bmad-output/{project-name}/founder/m4-prototypation/heuristic-evaluation.md'
---

# Step 2: Heuristic Review

**Progress: Step 2 of 5** — Next: Severity Rating

---

## STEP GOAL

Systematically walk through the design/prototype and identify violations of Nielsen's 10 usability heuristics with specific examples.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor conducting a usability audit. Be thorough and critical. Document specific violations, not vague observations.

### Step-Specific Rules
- Evaluate ALL 10 heuristics (no skipping)
- Document specific examples with locations (screen name, element)
- If no violations found for a heuristic, state "No violations identified"
- Push founder to show you the design (screenshot, URL, or detailed description)

---

## EXECUTION PROTOCOLS

1. Review design artifacts systematically (screen by screen, flow by flow)
2. For each heuristic, identify violations with specific examples
3. Document violations in structured format
4. Ensure all 10 heuristics are evaluated

---

## CONTEXT BOUNDARIES

**Available context:**
- Design artifacts from step-01
- Nielsen's 10 heuristics from framework knowledge
- User flows from M4 User Flow & IA (if completed)

**Out of scope:**
- Severity rating (that's step-03)
- Recommendations (that's step-04)
- Aesthetic preferences (focus on usability, not taste)

---

## MANDATORY SEQUENCE

### 1. Review Evaluation Scope

Load the output document and confirm:
- Evaluation scope (which screens/flows)
- Artifact access (how to view the design)

Ask the founder to share the design:
- **If URL:** Ask for the link
- **If file:** Ask them to describe or paste screenshot
- **If prototype:** Ask them to walk through key screens

### 2. Conduct Heuristic Review

For EACH of Nielsen's 10 heuristics, systematically evaluate the design:

**Evaluation Template (use for each heuristic):**

---

**Heuristic {N}: {Name}**

**Definition:** {Brief definition from framework}

**Evaluation Question:** {Specific question to ask about this heuristic}

**Violations Found:**
- **Location:** {Screen/element}
- **Issue:** {What's wrong}
- **Example:** {Specific instance}

OR

**No violations identified** — {Brief note on why this heuristic is satisfied}

---

**Heuristic-Specific Evaluation Questions:**

1. **Visibility of System Status:** Are users always informed about what's happening? (loading states, confirmations, active states)

2. **Match Between System and Real World:** Does the interface use familiar language and concepts? (customer terminology from JTBD, not jargon)

3. **User Control and Freedom:** Can users easily undo, cancel, or exit? (back buttons, cancel options, undo)

4. **Consistency and Standards:** Are patterns, terminology, and conventions consistent? (button styles, navigation, terminology)

5. **Error Prevention:** Does the design prevent errors before they happen? (constraints, confirmations, defaults)

6. **Recognition Rather Than Recall:** Are options visible, or must users remember? (visible navigation, autocomplete, recent items)

7. **Flexibility and Efficiency:** Are there shortcuts or optimizations for power users? (keyboard shortcuts, bulk actions, quick filters)

8. **Aesthetic and Minimalist Design:** Is the interface focused and uncluttered? (clear hierarchy, progressive disclosure, white space)

9. **Help Users Recover from Errors:** Are error messages clear and actionable? (plain language, specific guidance, no error codes)

10. **Help and Documentation:** Is help available when needed? (tooltips, FAQ, onboarding, contextual help)

### 3. Document Violations in Output Document

For each heuristic with violations, add to the "Violations by Heuristic" section:

```markdown
### Heuristic {N}: {Name}

**Violations:**

1. **Location:** {Screen/element}
   **Issue:** {What's wrong}
   **Example:** {Specific instance}
   **Severity:** {To be rated in Step 3}

2. {Additional violations}

---
```

For heuristics with no violations:

```markdown
### Heuristic {N}: {Name}

**No violations identified** — {Brief note}

---
```

### 4. Validate Completeness

Before proceeding, confirm:
- ✅ All 10 heuristics evaluated
- ✅ Violations documented with specific locations
- ✅ Examples are concrete, not vague
- ✅ At least 3-5 violations identified (if fewer, re-evaluate more critically)

**If fewer than 3 violations found:** Challenge the founder:
> "Most designs have usability issues. Let's look more carefully. Walk me through the primary user flow step-by-step."

### 5. Update Output Document

Append all violations to the "Violations by Heuristic" section.

Update frontmatter: add `step-02-heuristic-review.md` to `stepsCompleted`

### 6. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on any heuristic or violation
- **[P] Party Mode** — get multi-agent perspectives on the violations
- **[C] Continue** — proceed to severity rating

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Confirm violations are documented in output document
2. Confirm frontmatter is updated
3. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 
- All 10 heuristics evaluated systematically
- Violations documented with specific locations and examples
- At least 3-5 violations identified (typical for most designs)
- Output document updated with structured violations

❌ **FAILURE:** 
- Skipping heuristics
- Vague violations without specific examples
- Generating violations without founder input
- Loading next step before [C] is selected
