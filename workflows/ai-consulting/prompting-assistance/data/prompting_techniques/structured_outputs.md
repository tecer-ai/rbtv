---
---

# Structured Outputs

**Problem Type:** Structured Outputs

**Related Anti-Patterns:** Addresses [Vague Output Format](prompting_anti_patterns.md#clarity-and-structure-anti-patterns)

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

LLMs generate unpredictable free-form text that breaks downstream parsing, validation, and system integration.

---

## Technique Overview

Force LLM outputs into machine-readable formats (JSON, XML) using schema constraints. Progresses from JSON Mode (syntax guarantee) to JSON Schema (structure guarantee) to tool/function calling (semantic execution).

**Core Mechanism:** Schema constraints during generation prevent malformed outputs at the source. The model generates tokens that satisfy the schema, eliminating post-hoc parsing failures. Validation shifts from reactive (fix after generation) to proactive (constrain during generation).

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| API integrations requiring predictable data formats | Creative writing or conversational responses |
| Data extraction from unstructured text | Tasks where format flexibility aids quality |
| Tool/function calling in agentic systems | Simple Q&A without downstream processing |
| Automated evaluation and testing pipelines | Human-only consumption of outputs |
| Multi-step workflows requiring reliable handoffs | Exploratory prototyping (adds overhead) |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Define output schema | Create JSON Schema specifying required fields, types, constraints using Pydantic/Zod |
| 2 | Choose constraint mode | Select JSON Mode (syntax only), JSON Schema (structure), or function calling (execution) |
| 3 | Include schema in prompt | Provide schema definition in system prompt or API parameter (`response_format`) |
| 4 | Use deterministic serialization | Use `sort_keys=True` (Python) or equivalent ordered serialization when passing JSON to context; ensures identical key ordering prevents cache breaks |
| 5 | Specify exact format | Show complete template skeleton with exact markdown syntax, not just descriptions; include exact section names, heading levels, table columns, footer formats |
| 6 | Instruct strict adherence | Add explicit instruction: "Respond ONLY with valid JSON matching the schema" |
| 7 | Validate output | Parse response with schema validator; catch structural violations |
| 8 | Implement recovery | On validation failure, retry with error context for self-healing |
| 9 | Monitor schema drift | Log validation errors to detect model behavior changes over time |

**Key Considerations:**
- Native API modes (OpenAI `response_format`, Gemini `response_schema`) provide stronger guarantees than prompt-only approaches
- Function calling adds semantic understanding—model knows what the function does, not just its signature
- Schema complexity inversely correlates with reliability; keep schemas as simple as possible

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| JSON Mode | Basic syntax guarantee sufficient, no strict schema | Only ensures valid JSON; doesn't enforce field structure |
| JSON Schema Mode | Production systems needing predictable structure | Schema defines exact fields, types, and constraints |
| Function/Tool Calling | LLM needs to invoke external actions | Schema maps to executable function with semantic descriptions |
| Grammar Constraints (CFG) | Generating code, SQL, DSLs with strict syntax | Uses formal grammar (Lark) to constrain output; syntax-perfect by construction |
| Free-Form Tools | Integrating with text-based systems (shell, SQL) | Custom tools accept raw text instead of JSON arguments |
| Prefill for Format | Rigid output formats where even native modes may add extra text | Pre-populate beginning of assistant response (e.g., start with `{` to force JSON output) |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Relying on prompt-only JSON instructions | Model may add explanatory text, break format, or omit fields | Use native API modes that enforce structure at generation time |
| Overly complex schemas | Model struggles with deep nesting, many optional fields; Structured Outputs may fail or produce poor results | Keep schemas simple; 2-3 nesting levels maximum; flat structure preferred; split into multiple simpler schemas if needed |
| No validation layer | Downstream code crashes on unexpected output variations | Always validate with schema library before processing |
| Ignoring retry with context | First-attempt failures waste the call entirely | Implement self-healing: return error to model, request correction |
| Schema without descriptions | Model misinterprets field purpose, generates wrong values | Add semantic descriptions to every field in schema definition |
| Hardcoded version assumptions | Schema changes break existing processing code | Include version field; plan migrations; maintain backward compatibility |

---

## Examples

### Example 1: Data Extraction with JSON Schema

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>`Extract user info from: "John Smith, john@email.com, age 30"` | **Prompt:**<br>`Extract user info. Respond with JSON matching this schema: {"type":"object","properties":{"name":{"type":"string"},"email":{"type":"string"},"age":{"type":"integer"}},"required":["name","email","age"]}` |
| **Output:**<br>`The user is John Smith, email john@email.com, 30 years old.` | **Output:**<br>`{"name":"John Smith","email":"john@email.com","age":30}` |
| **Issue:** Free-form text requires regex parsing, breaks on format changes | **Result:** Directly parseable JSON with guaranteed structure |

**Metric:** 100% parse success rate vs ~60% with regex on free-form text

---

### Example 2: Function Calling for Calculator

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>`What is 125 times 4?` | **Same prompt with calculator tool defined** |
| **Output:**<br>`125 times 4 equals 500.` | **Tool Call:**<br>`{"name":"calculator","arguments":{"expression":"125*4"}}`<br>**Tool Result:** `500`<br>**Final Output:** `125 times 4 equals 500.` |
| **Issue:** No verifiable computation; model may hallucinate math | **Result:** Actual calculation via tool; result is reliable |

**Metric:** 100% arithmetic accuracy (tool execution) vs ~85% (model-only for complex math)

---

### Example 3: Self-Healing Validation Recovery

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **First Attempt:**<br>Schema requires `priority: enum["low","medium","high"]`<br>Model outputs `{"priority":"urgent"}` | **Same first attempt, but with retry logic** |
| **Output:**<br>Validation error → pipeline failure | **Retry Prompt:**<br>`Your output failed validation: 'urgent' not in enum. Correct and respond with valid JSON.`<br>**Output:** `{"priority":"high"}` |
| **Issue:** Single validation failure stops pipeline | **Result:** Self-healing corrects error; pipeline continues |

**Metric:** 95% recovery rate on first retry for enum/type violations

---

## Quality Checklist

- [ ] Output schema is defined using a typed library (Pydantic, Zod, JSON Schema)
- [ ] Native API structured output mode is used when available (`response_format`, `tool_use`)
- [ ] Schema includes semantic descriptions for all fields
- [ ] Prompt explicitly instructs "respond ONLY with valid JSON matching the schema"
- [ ] Validation layer parses and verifies output before downstream use
- [ ] Retry-with-context logic handles validation failures
- [ ] Schema versioning strategy exists for production systems
- [ ] Validation error logs feed into monitoring and alerting
- [ ] Tools/functions follow single-responsibility principle (atomic operations)
- [ ] Complex schemas are split into simpler, composable structures

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| OpenAI Structured Outputs | https://platform.openai.com/docs/guides/structured-outputs |
| OpenAI Function Calling | https://platform.openai.com/docs/guides/function-calling |
| Anthropic Tool Use | https://docs.anthropic.com/en/docs/build-with-claude/tool-use |
| Gemini Structured Output | https://ai.google.dev/gemini-api/docs/structured-output |
| JSON Schema Specification | https://json-schema.org/ |
| Pydantic (Python) | https://docs.pydantic.dev/ |
| Zod (TypeScript) | https://zod.dev/ |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | OpenAI Docs — Structured Outputs | https://platform.openai.com/docs/guides/structured-outputs | 2025-11-20 | 2025 | 9.3 | 10 | 9 | 9 |
| 2 | OpenAI Docs — Function Calling | https://platform.openai.com/docs/guides/function-calling | 2025-11-20 | 2025 | 9.3 | 10 | 9 | 9 |
| 3 | Anthropic — Structured Outputs Beta | https://www.claude.com/blog/structured-outputs-on-the-claude-developer-platform | 2025-11-20 | 2025-11 | 9.0 | 10 | 9 | 8 |
| 4 | Agenta — Guide to Structured Outputs and Function Calling | https://agenta.ai/blog/the-guide-to-structured-outputs-and-function-calling-with-llms | 2025-11-20 | 2025-09 | 7.3 | 7 | 7 | 8 |
| 5 | Anthropic — Building Effective Agents | https://www.anthropic.com/research/building-effective-agents | 2025-11-20 | 2024-12 | 8.3 | 10 | 8 | 7 |
| 6 | Zhu et al. — Divide-Then-Aggregate (DTA) | https://arxiv.org/abs/2501.12432 | 2025-11-20 | 2025 | 7.7 | 8 | 8 | 7 |
| 7 | JSON Schema Specification | https://json-schema.org/ | 2025-11-20 | 2025 | 8.7 | 9 | 9 | 8 |

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| Vellum — When to use function calling | 5.7 | Marketing language penalty (TR: 8→5), moderate topic match |

---

## For AI Agents

Read [`prompting_technique.md`](../prompting_technique.md) before updating this document.

---

*Last updated: 2026-01-20*

