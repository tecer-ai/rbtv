---
---

# Template Instructions: prompting_technique

**Purpose:** Document prompting techniques that solve specific problems (context management, structured outputs, reasoning, safety, iteration).

**Required:** Optional. Create when documenting a reusable prompting pattern that solves a specific problem across models or contexts.

---

## How to Use This Template

Follow these steps in order when creating a new prompting technique document:

| Step | Section | Description |
|------|---------|-------------|
| 1 | [Problem Solved](#problem-solved) | Define the specific problem this technique addresses |
| 2 | [Technique Overview](#technique-overview) | Describe what the technique is and how it works |
| 3 | [When to Apply](#when-to-apply) | Specify use cases and scenarios |
| 4 | [Application Pattern](#application-pattern) | Provide step-by-step application guidance |
| 5 | [Variations](#variations) | Document technique variations or adaptations |
| 6 | [Pitfalls](#pitfalls) | List common mistakes and solutions |
| 7 | [Examples](#examples) | Show before/after comparisons with measurable results |
| 8 | [Quality Checklist](#quality-checklist) | Create verification checklist |
| 9 | [Technical Reference](#technical-reference) | Link to official documentation |
| 10 | [Sources](#sources) | Document research sources with evaluation |

**Iteration:** Verify examples have measurable results. Application pattern MUST be actionable.

---

## Section Guidelines

| Section | Required | Notes |
|---------|----------|-------|
| [Problem Solved](#problem-solved) | Required | 140 chars max. One sentence describing the specific problem this technique addresses |
| [Technique Overview](#technique-overview) | Required | Concise description (280 chars max) of what the technique is and how it works at high level |
| [When to Apply](#when-to-apply) | Required | Table format: Ideal For \| Avoid For. Be specific about scenarios |
| [Application Pattern](#application-pattern) | Required | Step-by-step guidance. Max 7 steps. Use tables for structured application |
| [Variations](#variations) | Recommended | Different approaches or adaptations of the core technique. Omit if no meaningful variations exist |
| [Pitfalls](#pitfalls) | Required | Table format: Pitfall \| Why It Fails \| Solution. Focus on common mistakes specific to this technique |
| [Examples](#examples) | Required | Min 2-3 examples. Use side-by-side tables (Before \| After) with measurable results. Keep terse (3-5 lines each) |
| [Quality Checklist](#quality-checklist) | Required | Actionable verification items. Max 10 items. Must be technique-specific |
| [Technical Reference](#technical-reference) | Recommended | Links to official docs or authoritative sources. Omit if no specific references exist |
| [Sources](#sources) | Required | Follow ai_model.md standards: TS ≥ 6, marketing penalty, grouped domains. Min 3 sources for new techniques |
| [Discarded Sources](#discarded-sources) | Required | Transparency on sources below threshold |
| [Last updated](#last-updated) | Required | ISO 8601 format at end of file |

**Size Restrictions:**
- Problem Solved: 140 chars max
- Technique Overview: 280 chars max
- Application Pattern: 7 steps max
- Quality Checklist: 10 items max

---

## Notes

### Scope

Prompting technique documents capture **reusable patterns for structuring prompts**. Each document MUST include:
- The problem the technique addresses
- How to apply the technique (prompt patterns)
- When to use vs avoid
- Variations and adaptations
- Pitfalls specific to the technique
- Before/after examples with measurable improvements

Documents MUST NOT:
- Duplicate general prompting advice
- Repeat model-specific guidance (use ai_models/ documents)
- Focus on code implementation (unless prompt involves code generation)

### Naming

Files follow pattern: `[technique_name].md` (e.g., `few_shot.md`, `chain_of_thought.md`, `structured_outputs.md`)

Use lowercase with underscores. Name should clearly indicate the technique.

### When to Create

Create a prompting technique document when:
- The technique solves a specific, recurring prompting problem
- The technique is reusable across multiple contexts or models
- The technique has measurable impact on output quality
- Multiple practitioners would benefit from documented guidance

Do NOT create if:
- The technique is model-specific (document in ai_models/ instead)
- The technique is an anti-pattern (document in cursor rules instead)
- The technique is too simple to warrant documentation
- No measurable examples exist to demonstrate value

### Problem Type Categories

Prompting techniques are organized by the type of problem they solve:

| Category | Problem Domain | Examples |
|----------|----------------|----------|
| **Context Management** | Handling large contexts, RAG, memory, retrieval | Long context strategies, chunking, context windows |
| **Structured Outputs** | Controlling output format, schema compliance, parsing | JSON mode, XML formatting, structured generation |
| **Reasoning Scaffolds** | Improving logical reasoning, planning, problem-solving | Chain-of-thought, tree of thoughts, self-consistency |
| **Safety & Guardrails** | Preventing harmful outputs, prompt injection, alignment | Input delimiters, content filtering, safety instructions |
| **Iteration & Refinement** | Improving outputs through feedback, self-critique, multi-turn | Reflexion, critique loops, iterative generation |
| **Knowledge Injection** | Providing context, examples, demonstrations | Few-shot learning, knowledge grounding, demonstrations |
| **Task Decomposition** | Breaking complex tasks into manageable steps | Subtask prompting, step-by-step guidance, planning |

**Usage:** Every technique document MUST specify which problem type(s) it addresses in the Technique Overview section.

---

<!-- DOCUMENT CONTENT BELOW — Copy from here -->

# [Technique Name]

**Problem Type:** [Context Management | Structured Outputs | Reasoning Scaffolds | Safety & Guardrails | Iteration & Refinement | Knowledge Injection | Task Decomposition]

**Related Anti-Patterns:** [Optional: Link to relevant anti-patterns this technique addresses, e.g., "Addresses [Vagueness and Ambiguity](prompting_techniques/prompting_anti_patterns.md#clarity-and-structure-anti-patterns)"]

---

## Table of Contents

1. [Problem Solved](#problem-solved)
2. [Technique Overview](#technique-overview)
3. [When to Apply](#when-to-apply)
4. [Application Pattern](#application-pattern)
5. [Variations](#variations)
6. [Pitfalls](#pitfalls)
7. [Examples](#examples)
8. [Quality Checklist](#quality-checklist)
9. [Technical Reference](#technical-reference)
10. [Sources](#sources)
11. [Discarded Sources](#discarded-sources)

---

## Problem Solved

[One sentence, 140 chars max. What specific problem does this technique address?]

---

## Technique Overview

[Concise description, 280 chars max. What is this technique and how does it work at a high level?]

**Core Mechanism:** [Brief explanation of why/how this technique works]

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| [Specific scenarios where this technique excels] | [Specific scenarios where this technique is inappropriate or ineffective] |

---

## Application Pattern

Step-by-step guidance for applying this technique. Max 7 steps.

| Step | Action | Details |
|------|--------|---------|
| 1 | [Action to take] | [Specific guidance on how to execute this step] |
| 2 | [Action to take] | [Specific guidance on how to execute this step] |
| ... | ... | ... |

**Key Considerations:**
- [Important point to remember when applying this technique]
- [Another critical consideration]

---

## Variations

Document different approaches or adaptations of the core technique. Omit section if no meaningful variations exist.

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| [Variation name] | [Scenario where this variation is preferred] | [How this differs from the base technique] |

---

## Pitfalls

Common mistakes when applying this technique and how to avoid them.

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| [Common mistake specific to this technique] | [Reason this mistake causes problems] | [How to prevent or fix this mistake] |

---

## Examples

Minimum 2-3 examples showing before/after comparisons with measurable results. Keep terse (3-5 lines each).

### Example 1: [Scenario Description]

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>[Original prompt, 3-5 lines] | **Prompt:**<br>[Improved prompt using technique, 3-5 lines] |
| **Output:**<br>[Resulting output] | **Output:**<br>[Improved output] |
| **Issue:** [Problem observed] | **Result:** [Measurable improvement with specific metric] |

**Metric:** [Specific measurement of improvement, e.g., "50% reduction in hallucinations", "95% schema compliance", "3x faster to correct answer"]

---

### Example 2: [Scenario Description]

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>[Original prompt] | **Prompt:**<br>[Improved prompt] |
| **Output:**<br>[Resulting output] | **Output:**<br>[Improved output] |
| **Issue:** [Problem observed] | **Result:** [Measurable improvement] |

**Metric:** [Specific measurement]

---

## Quality Checklist

Before deploying prompts using this technique, verify these technique-specific items. Max 10 items. Must be actionable and specific.

- [ ] [Technique-specific verification item — e.g., "Prompt includes [specific element required by this technique]"]
- [ ] [Technique-specific verification item]
- [ ] [Technique-specific verification item]

---

## Technical Reference

Links to official documentation or authoritative sources for this technique. Omit if no specific references exist.


| Topic | Official Documentation |
|-------|------------------------|
| [Specific aspect of technique] | [URL to authoritative source] |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | [Source title] | [URL] | [YYYY-MM-DD] | [YYYY-MM-DD or n.a] | [x.x] | [x] | [x] | [x] |
| 2 | [Grouped source — parent] | — | — | — | [avg] | [avg] | [avg] | [avg] |
|   | ↳ [Nested source 1] | [URL] | [YYYY-MM-DD] | [YYYY-MM-DD or n.a] | [x.x] | [x] | [x] | [x] |
|   | ↳ [Nested source 2] | [URL] | [YYYY-MM-DD] | [YYYY-MM-DD or n.a] | [x.x] | [x] | [x] | [x] |

> **Format:** 
> - Each nested source has its own evaluation; parent shows average of non-discarded entries
> - Apply marketing language penalty (-1 to -3 TR) before calculating TS
> - Strikethrough discarded nested entries (TS < 6); they still count toward transparency

---

## Discarded Sources

[List sources that were considered but did not meet the TS >= 6 threshold, including nested entries that were discarded from grouped sources.]

| Source | TS | Reason |
|--------|-----|--------|
| [Title](URL) | [x.x] | [e.g., Low authority (AT:4), Marketing language penalty (TR: 8→5), Poor topic match (TM:3)] |


---

*Last updated: 2026-02-04*
