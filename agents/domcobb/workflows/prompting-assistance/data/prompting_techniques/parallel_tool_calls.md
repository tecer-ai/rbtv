---
---

# Parallel Tool Calls

**Problem Type:** Iteration & Refinement

**Related Anti-Patterns:** Addresses [Sequential Inefficiency](prompting_anti_patterns.md#efficiency-anti-patterns)

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

Agents execute independent tool calls sequentially when they could run in parallel, wasting time and increasing latency.

---

## Technique Overview

Parallel tool calls instruct the model to execute independent or read-only tool actions simultaneously in the same turn, rather than sequentially. This reduces latency for read-heavy operations.

**Core Mechanism:** By explicitly instructing parallel execution, the model recognizes when tool calls are independent and can be executed concurrently, reducing total execution time from sum of individual calls to maximum of individual calls.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Read-heavy operations with independent queries | Tool calls with dependencies (output of one feeds into next) |
| Multiple data lookups that don't depend on each other | Write operations that might conflict |
| Batch operations where order doesn't matter | Tool calls requiring sequential execution |
| Performance-critical workflows with multiple independent steps | Simple workflows with single tool call |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Identify independent tool calls | Determine which tool calls don't depend on each other's outputs |
| 2 | Verify read-only or safe operations | Ensure parallel calls are read-only or won't conflict |
| 3 | Add parallel instruction | Include: "Run independent/read-only tool actions in parallel (same turn) to reduce latency" |
| 4 | Specify which calls to parallelize | Explicitly list tool calls that can run in parallel |
| 5 | Monitor execution patterns | Track if model actually parallelizes calls or still executes sequentially |

**Key Considerations:**
- Only parallelize independent operations (no data dependencies)
- Prefer read-only operations for parallel execution
- Model may not parallelize by default; explicit instruction is required

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| **Selective Parallelization** | Mixed dependent/independent calls | Specify which calls to parallelize: "Parallelize search calls, but execute analysis sequentially" |
| **Batch Parallelization** | Large numbers of independent operations | Group operations into batches for parallel execution |
| **Conditional Parallelization** | Operations with optional dependencies | "If operations are independent, parallelize; if dependent, execute sequentially" |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| **Parallelizing dependent calls** | Results incorrect due to missing dependencies | Only parallelize truly independent operations |
| **No explicit instruction** | Model executes sequentially by default | Always include explicit parallel instruction |
| **Conflicting write operations** | Parallel writes cause data corruption | Only parallelize read-only operations or ensure no conflicts |
| **Assuming automatic parallelization** | Model doesn't parallelize without instruction | Explicitly instruct parallel execution |

---

## Examples

### Example 1: Data Lookup — Multiple Independent Queries

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Get the population of Paris, London, and Tokyo."<br><br>**Output:**<br>Agent calls search("Paris population") → waits → calls search("London population") → waits → calls search("Tokyo population")<br>Total time: 3 seconds (1s each, sequential)<br><br>**Issue:** Sequential execution wastes time | **Prompt:**<br>"Get the population of Paris, London, and Tokyo. Run independent/read-only tool actions in parallel (same turn) to reduce latency."<br><br>**Output:**<br>Agent calls all three searches in parallel<br>Total time: 1 second (all execute simultaneously) |
| **Issue:** 3x latency due to sequential execution | **Result:** 66% latency reduction through parallelization |

**Metric:** 66% latency reduction (3s → 1s), 3x throughput improvement

---

### Example 2: Research Task — Multiple Source Lookups

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Research React, Vue, and Angular frameworks."<br><br>**Output:**<br>Agent searches React → waits → searches Vue → waits → searches Angular<br>Total time: 6 seconds (2s each, sequential)<br><br>**Issue:** Slow research due to sequential lookups | **Prompt:**<br>"Research React, Vue, and Angular frameworks. Run independent/read-only tool actions in parallel."<br><br>**Output:**<br>Agent searches all three frameworks in parallel<br>Total time: 2 seconds (all execute simultaneously) |
| **Issue:** 3x slower than necessary | **Result:** 66% latency reduction, faster research completion |

**Metric:** 66% latency reduction (6s → 2s), research completes 3x faster

---

## Quality Checklist

Before deploying parallel tool calls, verify:

- [ ] Tool calls are truly independent (no data dependencies)
- [ ] Operations are read-only or safe for parallel execution
- [ ] Explicit instruction to parallelize is included in prompt
- [ ] Model actually parallelizes calls (monitor execution patterns)
- [ ] No conflicting write operations are parallelized
- [ ] Performance improvement is measurable (latency reduction)

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| Agent Efficiency Patterns | See [prompt_engineering.md](prompt_engineering.md) for ReAct patterns |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | GPT-5 Prompting Guide | https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide | 2026-01-23 | 2025 | 8.7 | 10 | 8 | 9 |

---

## Discarded Sources

*No sources were discarded during research.*

---

## For AI Agents

**Working instructions:** When updating this document, agents MUST read this template first. Read [`prompting_technique.md`](../prompting_technique.md) before updating this document. Follow Section Guidelines for required sections, size restrictions, and format requirements. Ensure examples use side-by-side tables (Before | After) and include measurable results.

---

*Last updated: 2026-01-23*





