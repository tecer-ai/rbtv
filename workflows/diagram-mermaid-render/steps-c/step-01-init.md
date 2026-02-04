---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-convert.md
---

# Step 01: Init

**Progress: Step 1 of 4** — Next: Convert Diagrams

---

## STEP GOAL

Verify prerequisites, identify Mermaid blocks in target file, and prepare output folder structure.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Diagram Conversion Specialist. Methodical, precise, focused on producing portable diagram images.

### Step-Specific Rules

- Verify mmdc CLI is available before proceeding
- Count all Mermaid code blocks in the target file
- Create output folder following naming convention
- Report diagram count and complexity assessment

---

## MANDATORY SEQUENCE

### 1. Greet and Identify Target

Present brief introduction:

```
I'll convert Mermaid diagrams in your Markdown file to PNG images.

I need to confirm:
1. The Markdown file containing Mermaid diagrams
2. Any specific conversion preferences
```

If Markdown file already in conversation context, confirm:
- "I see you want to convert diagrams in [filename]. Is this correct?"

If no file specified, ask:
- "Which Markdown file contains the Mermaid diagrams to convert?"

HALT and wait for confirmation.

### 2. Verify mmdc CLI

Execute:

```bash
mmdc --version
```

**If command succeeds:** Report version, proceed to step 3.

**If command fails:**
- Report: "The Mermaid CLI (mmdc) is not installed."
- Provide installation instruction: `npm install -g @mermaid-js/mermaid-cli`
- HALT — Cannot proceed without mmdc

### 3. Extract Mermaid Blocks

Read the target Markdown file and identify all Mermaid code blocks:

1. Find code fences: start ` ```mermaid`, end ` ``` `
2. Count total diagrams found
3. For each diagram, count nodes (rough estimate: count node definitions)

Report findings:

```
Found {N} Mermaid diagram(s) in {filename}:

| # | Type | Estimated Nodes | Needs Validation |
|---|------|-----------------|------------------|
| 1 | {flowchart/sequence/etc} | {count} | {Yes/No} |
...

Diagrams with 5+ nodes will be validated for visual clarity.
```

**If no diagrams found:** Report and offer to exit workflow.

### 4. Create Output Folder

Create folder next to target file:
- Folder name: `{file_name}_mmdc/`
- `file_name` is target file base name without extension

**Example:**
- Target: `docs/methodology.md`
- Output folder: `docs/methodology_mmdc/`

Confirm folder creation or report if folder already exists.

### 5. Track State

Store in workflow state:
- Target file path
- Output folder path
- Diagram count
- List of diagrams needing validation (5+ nodes)

### 6. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to convert diagrams (step-02)
- **[X] Exit Workflow** — Cancel conversion

ALWAYS halt and wait for user selection.

---

## DIAGRAM TYPE REFERENCE

| Type | Identifier | Common Patterns |
|------|------------|-----------------|
| Flowchart | `flowchart`, `graph` | `-->`, `---`, subgraph |
| Sequence | `sequenceDiagram` | `->`, `->>`, participant |
| Class | `classDiagram` | `class`, `<\|--` |
| State | `stateDiagram` | `[*]`, `-->` |
| ER | `erDiagram` | `\|\|--o{` |
| Gantt | `gantt` | `section`, `task` |

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure workflow state contains all required data
2. Load `./step-02-convert.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- mmdc CLI verified working
- All Mermaid blocks identified and counted
- Output folder created
- Complexity assessment completed
- Menu presented with explicit HALT

❌ **FAILURE:**
- Proceeding without mmdc verification
- Missing diagram count or complexity assessment
- Proceeding without user confirmation
- Proceeding to next step without user selecting Continue
