---
stepNumber: 2
stepName: 'location-selection'
nextStepFile: ./step-03-extraction.md
outputFile: '{outputFolder}/{filename}.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
---

# Step 02: Location Selection

**Progress: Step 2 of 4** — Next: Context Extraction

---

## STEP GOAL

Determine where to save the handoff file by analyzing conversation context and presenting relevant location options to the user.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Context Curator. Continue your existing persona as Ana and communication style.

### Step-Specific Rules

- Generate 3 contextual location suggestions
- Always include a default fallback option
- Allow custom path input
- Confirm filename with user

---

## MANDATORY SEQUENCE

### 1. Analyze Context for Location Suggestions

Examine the conversation to generate relevant location suggestions:

| Context Pattern | Suggested Location |
|-----------------|-------------------|
| Specific project mentioned | `{project-path}/docs/handoffs/` |
| Plan-related discussion | `.cursor/plans/{plan-name}/` |
| Architecture/design context | `docs/architecture/` |
| Product documentation context | `docs/product/` |
| No specific context | `{outputFolder}` (default from workflow.md) |

### 2. Generate Three Location Options

Create 3 contextually relevant suggestions:

1. **Project-specific location** — If conversation involves a specific project
2. **Topic-specific location** — Based on conversation topic
3. **Default location** — `{outputFolder}` as fallback (from workflow.md)

### 3. Present Location Selection

Display the following format:

```
Before I create the handoff summary, where would you like me to save it?

1. `{contextual suggestion 1}` — {brief reason}
2. `{contextual suggestion 2}` — {brief reason}
3. `{outputFolder}` — default handoff location

Please choose a number or specify a custom path.
```

HALT and wait for user selection.

### 4. Process User Response

Based on user selection:

- **Number 1-3**: Use the corresponding path
- **Custom path**: Validate path format and use it
- **Clarification needed**: Ask for clarification

### 5. Confirm Filename

Present the suggested filename from step-01:

```
Suggested filename: `{filename}`

Is this filename okay, or would you like a different name?
```

Accept user confirmation or alternative filename.

### 6. Update Output Document

- Set `outputPath` in frontmatter to the selected location
- Update filename if user provided alternative
- Add `step-02-location-selection.md` to `stepsCompleted` array

### 7. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to context extraction (step-03)
- **[AE] Advanced Elicitation** — Load and execute `{advancedElicitationTask}`, then return and redisplay this step's menu
- **[X] Exit Workflow** — Save current state, exit agent

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-02-location-selection.md` in `stepsCompleted`
2. Ensure `outputPath` and filename are set
3. Load `./step-03-extraction.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**

- 3 contextual location suggestions presented
- User selected or provided a valid path
- Filename confirmed with user
- `stepsCompleted` array contains: `step-01-init.md`, `step-02-location-selection.md`
- Menu presented with explicit HALT and execution stopped

❌ **FAILURE:**

- Fewer than 3 location suggestions
- Proceeding without user confirmation of location
- Missing `outputPath` in frontmatter
- Proceeding to next step without user selecting Continue
