---
description: Mandatory principles for self-contained, lean documentation files without content repetition or context-only references
---
# Atomic Files Rule

## Four Mandatory Principles

1. **Self-Contained** — Each file MUST be interpretable independently. All instructions the agent needs MUST live in the file itself.
2. **No Content Repetition** — NEVER duplicate, summarize, or explain referenced file content. ONLY state "Read [file]", "Follow [file]", or "Use [file]".
3. **Functional References Only** — Reference a file ONLY when agents must read it to execute. Remove "for context", "for background", "see also", and "learn more" references.
4. **Lean and Objective** — Every sentence MUST be necessary. Use mandatory language ("must", "never", "always"). NEVER use "should", "consider", "check", "may want to".

## Violations to Detect and Fix

| Violation Type | Example (BAD) | Correct (GOOD) |
|----------------|---------------|----------------|
| Content repetition | "The judge evaluates work quality by checking code style, testing coverage, and documentation completeness. Read [quality-review.md]." | "Read [quality-review.md]." |
| Context-only reference | "See [plan-creation.mdc] for background on planning principles." | *(Remove entirely)* |
| Vague language | "Consider checking the file descriptions." | "Read each file's description header." |
| Verbose explanation | "This step is important because it ensures that the agent has all the necessary context to make informed decisions about the implementation." | "This step provides required context." |
| Summarizing referenced file | "The atomic files rule (see [atomic-files.mdc]) requires self-contained files without repetition." | "Follow [atomic-files.mdc]." |

## Preserve

- File purpose — one sentence describing what this file does
- Internal logic — instructions and steps that belong in this file
- Functional references — links to files agents must read for execution
- Examples — code, command, or format samples
- Tables — structured data (workflows, checklists, decision matrices)

## Enforcement

When editing in-scope files: remove content repetition, remove context-only references, convert vague language to mandatory language, and condense verbose passages.
