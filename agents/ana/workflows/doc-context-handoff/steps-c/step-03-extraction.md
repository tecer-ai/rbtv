---
stepNumber: 3
stepName: 'extraction'
nextStepFile: ./step-04-document.md
outputFile: '{outputFolder}/{filename}.md'
---

# Step 03: Context Extraction

**Progress: Step 3 of 4** — Next: Document Generation

---

## STEP GOAL

Extract all essential context from the conversation — goals, decisions, constraints, current state, and next steps — structured for the receiving agent.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Context Curator. Continue your existing persona as Ana and communication style.

### Step-Specific Rules

- Extract information from conversation, not from assumptions
- Prioritize decisions and constraints over exploratory discussion
- Identify information gaps explicitly
- Capture enough context for seamless continuation

---

## EXTRACTION FRAMEWORK

Extract these elements from the conversation:

| Element | Description | Priority |
|---------|-------------|----------|
| **Context Summary** | Brief overview of conversation state (2-3 sentences) | Required |
| **Problem Being Solved** | Clear statement of what the receiving agent should address | Required |
| **Current State** | What's been completed, what's in progress | Required |
| **User Goals** | Explicit goals from the conversation (numbered list) | Required |
| **Constraints Gathered** | Technical, process, and project constraints | Required |
| **Decisions Already Made** | Prevent re-deciding settled matters | Required |
| **Information Gaps** | What remains unclear or needs resolution | Required |
| **Files to Load** | Critical files the receiving agent MUST read | Required |

### Type-Specific Elements

| Handoff Type | Additional Elements |
|--------------|---------------------|
| **plan-development** | Quality Review Feedback Summary (status, issues, coverage). Quality-review is a subagent invoked via Task tool with `subagent_type='quality-review'`. |
| **execution** | Specific task instructions, execution order |
| **project** | Root cause (if applicable), related work |

---

## MANDATORY SEQUENCE

### 1. Scan Conversation for Context Summary

Create a 2-3 sentence overview:

- What is the conversation about?
- What stage is the work in?
- What triggered the handoff?

### 2. Extract Problem Statement

Identify:

- The core problem being addressed
- Current state of the work
- Root cause (if applicable and identified)

### 3. Extract User Goals

List explicit goals from the conversation:

- Number each goal (1, 2, 3...)
- Use the user's language where possible
- Focus on what they want to achieve, not how

### 4. Extract Constraints

Create a constraints table:

| Constraint | Type | Description |
|------------|------|-------------|
| {Name} | {Technical/Process/Scope} | {Details} |

### 5. Extract Decisions Already Made

For each decision, capture:

- **Decision:** What was decided
- **Rationale:** Why this choice was made
- **Alternatives Rejected:** What we didn't do and why

### 6. Identify Information Gaps

List what remains unclear:

- Mark as "None" if all context is provided
- Be explicit about what the receiving agent may need to ask

### 7. Identify Files to Load

List critical files:

| File | Purpose | Priority |
|------|---------|----------|
| {path} | {Why this file matters} | MUST READ FIRST / Reference |

### 8. Extract Type-Specific Elements

**For plan-development handoffs:**

```
## Quality Review Feedback Summary

**Status:** {Approved | Needs Revision | Pending Review}

**Issues Identified:**
- {Issue 1}
- {Issue 2}

**Requirement Coverage:**
- {Requirement 1}: ✅ Covered / ❌ Missing
```

**For execution handoffs:**

```
## Task Instructions

### Execution Order
1. {First task}
2. {Second task}
3. {Third task}

### Guidelines
- {Approach or methodology to follow}
```

### 9. Present Extraction Summary

Display a summary of extracted content to user:

```
I've extracted the following context from our conversation:

**Context:** {2-3 sentence summary}
**Problem:** {Brief problem statement}
**Goals:** {count} goals identified
**Constraints:** {count} constraints gathered
**Decisions:** {count} decisions captured
**Information Gaps:** {count or "None"}
**Files to Load:** {count} files identified

Does this capture the essential context? Should I add or modify anything?
```

HALT and wait for user feedback.

### 10. Incorporate User Feedback

If user provides corrections or additions:

- Update the extracted content
- Confirm the changes
- Re-present summary if significant changes

### 11. Update State

- Add `step-03-extraction.md` to `stepsCompleted` array
- Store all extracted content for step-04

### 12. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to document generation (step-04)
- **[X] Exit Workflow** — Save current state, exit agent

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure all required elements are extracted
2. Ensure frontmatter is updated with `step-03-extraction.md` in `stepsCompleted`
3. Load `./step-04-document.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**

- All required elements extracted from conversation
- Type-specific elements included for plan-development/execution handoffs
- Extraction summary presented to user and confirmed
- User feedback incorporated
- `stepsCompleted` contains: `step-01-init.md`, `step-02-location-selection.md`, `step-03-extraction.md`
- Menu presented with explicit HALT and execution stopped

❌ **FAILURE:**

- Missing required elements (goals, decisions, constraints)
- Fabricating information not in conversation
- Proceeding without user confirmation of extracted content
- Proceeding to next step without user selecting Continue
