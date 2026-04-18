---
stepNumber: 2
stepName: 'self-assessment'
nextStepFile: ./step-03-discussion.md
---

# Step 02: Self-Assessment

**Purpose:** Perform deep error analysis, evaluate context sources, and generate 5 distinct improvement options.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Error Analysis

- Analyze what went wrong in the conversation that triggered this compound
- Determine error type:
  - **Misunderstanding** — AI misinterpreted instructions
  - **Execution failure** — AI understood but executed incorrectly
  - **Constraint violation** — AI violated explicit rules
  - **Knowledge gap** — AI lacked necessary context
- Identify the user's expectation vs. actual behavior
- Document the impact of the error

### 2. Context Source Evaluation

- List all files that influenced the agent's behavior in the triggering conversation:
  - Rules files (`.claude/rules/*.md`)
  - Persona files (`{rbtv_path}/personas/*.md`)
  - Command files (`.claude/commands/*.md`)
  - Skill files (`.claude/skills/*/SKILL.md`)
  - Workflow files (`{rbtv_path}/workflows/`, `_system/workflows/`)
  - System files (`_system/`)
- For each file, evaluate:
  - Was the guidance ambiguous or conflicting?
  - Was the file missing when it should have been loaded?
  - Was the file loaded but ignored or misinterpreted?
- Identify gaps:
  - What context was needed but not available?
  - What files should exist but don't?
- **Identify the primary affected file** — the single file most responsible for the incorrect behavior or most in need of change. Record its full path.

### 2b. Resolve Output Path

Use the primary affected file's path to determine where the compound PRD belongs:

| Primary affected file lives under... | Output folder |
|---|---|
| `{rbtv_path}/` | `{rbtv_path}/_admin/roadmap/todos/` |
| `_system/` or `.claude/` (non-rbtv) | `_system/roadmap/todos/` |
| `5. Workbench/{project}/` | Defer to that project's CLAUDE.md conventions |
| Ambiguous / no specific file | Ask user: "Is this about RBTV behavior or vault/system behavior?" |

Update the output document's `outputPath` frontmatter field with the resolved path. Create the folder if it does not exist.

Present the resolved path to the user for confirmation before proceeding.

### 3. Generate 5 Improvement Options

Generate exactly 5 distinct improvement approaches, one from each category.

**For each option, evaluate consistency with existing patterns:** Before recommending any option, check whether it follows or breaks the patterns already established in the target system. Consistency with existing conventions (file naming, structural patterns, menu patterns, frontmatter fields) is a first-class evaluation criterion alongside technical factors like performance or complexity. Flag inconsistencies explicitly — a technically optimal approach that breaks established patterns may be the wrong choice.

**Option 1: New Rule**
- Propose a new rule file or rule within an existing file
- Specify the rule's purpose and when it should apply
- Identify the file location (create new or add to existing)

**Option 2: Modify Existing Rule**
- Identify the specific rule file and section to modify
- Explain what's ambiguous or insufficient
- Propose the clarified wording

**Option 3: Update System File**
- Identify a system file (agent, workflow, step, task) that needs updating
- Explain what behavior needs to change
- Propose the specific modification

**Option 4: Add Constraint**
- Propose a new constraint or guardrail
- Explain what behavior it prevents
- Specify where the constraint should be enforced (globally or in specific contexts)

**Option 5: Alternative Approach**
- Propose a different architectural or workflow approach
- Explain why the current approach is problematic
- Describe the alternative and its benefits

### 4. Append Analysis to Output Document

Write all analysis to the `## Self-Assessment` section of the output document:

```markdown
## Self-Assessment

### Error Analysis
[Error type, expectation vs. actual, impact]

### Context Source Evaluation
[Files that influenced behavior, ambiguities, gaps]

### Improvement Options

1. **New Rule**: [Description]
   - **Rationale:** [Why this would help]
   - **Location:** [Where to implement]
   - **Pattern Consistency:** [Follows/breaks existing patterns — explain]

2. **Modify Existing Rule**: [Description]
   - **Rationale:** [Why this would help]
   - **Location:** [Where to implement]
   - **Pattern Consistency:** [Follows/breaks existing patterns — explain]

3. **Update System File**: [Description]
   - **Rationale:** [Why this would help]
   - **Location:** [Where to implement]
   - **Pattern Consistency:** [Follows/breaks existing patterns — explain]

4. **Add Constraint**: [Description]
   - **Rationale:** [Why this would help]
   - **Location:** [Where to implement]
   - **Pattern Consistency:** [Follows/breaks existing patterns — explain]

5. **Alternative Approach**: [Description]
   - **Rationale:** [Why this would help]
   - **Location:** [Where to implement]
   - **Pattern Consistency:** [Follows/breaks existing patterns — explain]
```

### 5. Update State

- Add `step-02-self-assessment.md` to `stepsCompleted` array
- Save updated output document to memory

### 6. Present Menu

- Present the following menu and HALT
- Wait for user selection

---

## MENU

Present the following menu and HALT. Wait for user selection.

**Options:**
- `[C] Continue` → Load and execute `step-03-discussion.md` (step-03 will self-skip if yoloMode is true)
- `[X] Exit Workflow` → Save current state, exit agent

---

## NEXT STEP

On Continue selection:
1. Update output document frontmatter: add `step-02-self-assessment.md` to `stepsCompleted` array
2. Load and execute: `./step-03-discussion.md`

**Note:** Step-03 will check yoloMode and skip itself if true, proceeding directly to step-04.

---

## SUCCESS CRITERIA

- Error analysis completed with error type explicitly stated as one of: Misunderstanding, Execution failure, Constraint violation, or Knowledge gap
- Context source evaluation lists specific file paths with analysis for each
- Primary affected file identified and its full path recorded
- `outputPath` resolved from primary affected file's location and confirmed with user
- Exactly 5 improvement options generated, one from each category: New Rule, Modify Existing Rule, Update System File, Add Constraint, Alternative Approach
- All analysis appended to output document's `## Self-Assessment` section
- `stepsCompleted` array contains exactly two entries: `step-01-init.md`, `step-02-self-assessment.md`
- Menu presented with explicit HALT and execution stopped
