---
name: 'step-03-solution-space'
description: 'Articulate solution in context of observed behaviours and constraints'
nextStepFile: './step-04-assumptions.md'
outputFile: '{outputFolder}/problem-solution-fit.md'
---

# Step 3: Solution Articulation

**Progress: Step 3 of 5** — Next: Critical Assumptions

---

## STEP GOAL

Define the solution concept at the right level of abstraction — explicitly as a response to observed behaviours, alternatives, and constraints from Step 2.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Reject feature lists. Force the founder to articulate WHAT the customer does differently and WHY, not HOW the software works.

### Step-Specific Rules
- Solution MUST be articulated in terms of behaviours it changes
- Every solution element MUST trace to a behaviour, alternative, or constraint
- Do NOT create feature backlog or implementation details
- This is problem-solution concept level, not MVP specification

---

## CONTEXT TO LOAD

1. problem-solution-fit.md with Step 2 content (Problem-Space Brief, all problem-side blocks)
2. working-backwards.md (Press Release solution description)

---

## MANDATORY SEQUENCE

### 1. Review Problem-Side Context

Summarize from Step 2:
> "Before we articulate the solution, let's review what we mapped:
>
> **Problem situations:** [summarize 2-3 key moments]
> **Key triggers:** [summarize main triggers]
> **Current behaviours:** [summarize coping strategies]
> **Constraints:** [summarize top 3 constraints]
>
> Our solution must respond to these realities."

### 2. Solution Reframe

Retrieve the solution description from Working Backwards Press Release.

Ask founder to reframe in terms of problem-side blocks:
> "Looking at your PR description: '[excerpt]'
>
> Now let's reframe it:
> 1. Which **specific behaviours** does this replace, augment, or automate?
> 2. Which **constraints** does it respect, relax, or shift?
> 3. What **new journey** does the customer take in the situations we identified?"

### 3. Core Mechanism

Ask:
> "What is the **core mechanism** of value creation? What fundamentally changes in how the customer gets the job done?
>
> Complete this sentence: 'Instead of [current behaviour], the customer now [new behaviour], which means [outcome].'"

Challenge weak answers:
- If feature-focused: "That's HOW it works. What does the CUSTOMER do differently?"
- If outcome-only: "How does the customer get to that outcome? What action do they take?"

### 4. Traceability Check

For each major solution element, verify traceability:

| Solution Element | Traces to... (Behaviour/Alternative/Constraint) |
|------------------|------------------------------------------------|
| [Element 1] | [Specific behaviour or constraint from Step 2] |
| [Element 2] | [Specific behaviour or constraint from Step 2] |

Ask founder:
> "For each element, can you point to the specific behaviour or constraint it addresses?"

If an element cannot be traced:
> "This element doesn't trace to anything in our problem mapping. Either:
> - We missed something in Step 2, or
> - This element doesn't belong in the solution

Which is it?"

### 5. New Customer Journey

For the situations identified in Step 2, ask:
> "Walk me through the NEW customer journey:
> - Same situation and trigger from Step 2
> - But now with your solution available
> - What do they do differently? How does it feel?"

### 6. Draft Solution Block

Collaboratively draft "Our Solution" canvas block (max 1 page):

**Core Mechanism:**
*(One paragraph: what fundamentally changes)*

**Behaviours Changed:**
- [Behaviour 1]: was [old], now [new]
- [Behaviour 2]: was [old], now [new]

**Constraints Addressed:**
- [Constraint]: solution [respects/relaxes/shifts] by [how]

**New Customer Journey:**
*(One paragraph describing the transformed experience)*

### 7. Validation Checklist

Before proceeding, confirm:
- [ ] Solution described without feature list or technical details
- [ ] Every major element traces to a behaviour, alternative, or constraint
- [ ] Can explain the solution to someone who never saw the problem-side canvas
- [ ] Removing any behaviour or constraint from Step 2 would make part of this solution nonsensical

If any fail, iterate before continuing.

### 8. Update Output Document

Update problem-solution-fit.md with "Our Solution" section.

### 9. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine solution articulation or traceability
- **[P] Party Mode** — get multi-perspective challenge on solution fit
- **[C] Continue** — proceed to Critical Assumptions

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify "Our Solution" block is complete with traceability
2. Update frontmatter: add `step-03-solution-space` to `stepsCompleted`
3. Load `./step-04-assumptions.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Solution articulated in terms of behaviours, every element traceable, no feature lists

❌ **FAILURE:** Feature-focused solution, elements without traceability, including implementation details, skipping constraint consideration
