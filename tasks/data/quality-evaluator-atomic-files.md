# Atomic Files Criteria

Reference knowledge for evaluating atomicity of instruction and process files.

---

## Scope

Atomicity evaluation applies to:

| In-Scope | Excluded |
|----------|----------|
| `.cursor/` rules, commands, skills, agents, plans | `system/map/` navigation files |
| `system/ai_pro/` agent definitions, templates | All `README.md` files |
| `system/business-innovation/` process files, frameworks | `how_it_works.md`, `glossary.md`, `vision.md` |

---

## Four Atomicity Principles

### 1. Self-Contained

**Each file MUST be interpretable independently.**

| PASS | FAIL |
|------|------|
| Agent understands what to do without reading other files first | Requires reading other files to understand instructions |
| All critical instructions present in the file | Critical instructions missing, only in referenced files |
| References use clear, actionable language | References are vague or unclear |

### 2. No Content Repetition

**NEVER repeat, summarize, or explain referenced file content.**

| PASS | FAIL |
|------|------|
| References say only "Read [file]" or "Follow [file]" | Duplicates explanations from referenced files |
| No summaries of what other files contain | Summarizes what another file contains |
| No explanations of how referenced systems work | Explains how a referenced system works |

### 3. Functional References Only

**ONLY reference files when functionally required for execution.**

| PASS | FAIL |
|------|------|
| Every reference is necessary for task completion | Contains "for context" or "for background" references |
| No optional reading suggestions | Contains "see also" or "learn more" references |
| Agent must read referenced file to complete task | References files that aren't needed for execution |

### 4. Lean and Objective

**Every sentence MUST be necessary.**

| PASS | FAIL |
|------|------|
| Uses mandatory language: "must", "never", "always" | Uses vague language: "should", "consider", "may want to" |
| One sentence per instruction when possible | Verbose multi-sentence explanations |
| No conversational filler | Contains filler or unnecessary context |

---

## Violation Examples

| Violation Type | BAD | GOOD |
|----------------|-----|------|
| Content repetition | "The judge evaluates work quality by checking code style, testing coverage, and documentation completeness. Read [quality-review.md]." | "Read [quality-review.md]." |
| Context-only reference | "See [plan-creation.mdc] for background on planning principles." | *(Remove entirely)* |
| Vague language | "Consider checking the file descriptions." | "Read each file's description header." |
| Verbose explanation | "This step is important because it ensures that the agent has all the necessary context to make informed decisions about the implementation." | "This step provides required context." |
| Summarizing referenced file | "The atomic files rule (see [atomic-files.mdc]) requires self-contained files without repetition." | "Follow [atomic-files.mdc]." |

---

## What to Preserve

These elements are NOT violations:

1. **File purpose statement** - One sentence describing what this file does
2. **Internal logic** - Instructions and steps that belong in this file
3. **Functional references** - Links to files agents must read for execution
4. **Examples** - Code samples, command examples, format examples
5. **Tables** - Structured data (workflows, checklists, decision matrices)
