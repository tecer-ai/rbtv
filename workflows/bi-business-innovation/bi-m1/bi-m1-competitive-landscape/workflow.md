---
name: 'bi-m1-competitive-landscape'
description: 'Map competitive landscape with verified current data via web research'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m1/workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m1-conception'
outputFile: competitive-landscape.md
---

# Competitive Landscape Framework Workflow

**Goal:** Map the competitive landscape using verified current data to understand how the market addresses the customer's job, benchmark solutions across geographies, and identify differentiation opportunities.

**Your Role:** YC mentor guiding competitive intelligence. CRITICAL: Web research is MANDATORY for this framework. You must verify all competitor claims with current sources. Training data alone is insufficient.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in output document frontmatter.

### Critical Rules

- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update frontmatter after completing each step
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Map competitive landscape | steps-c/step-01-init.md | competitive-landscape.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, explain framework, CHECK web access |
| 02 | Competitor ID | Identify direct/indirect competitors via web research |
| 03 | Benchmarking | Benchmark US/China markets, cross-industry analogues |
| 04 | Positioning | Analyze competitor strengths/weaknesses, map positioning |
| 05 | Synthesis | Extract threats/opportunities, UPDATE project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. At least 5 direct competitors and 5 indirect alternatives identified with source URLs
2. US and China market benchmarks captured with specific players and lessons
3. At least 3 cross-industry analogues identified with transferable insights
4. Positioning map shows hypothesized position and identified white space
5. At least 5 competitive threats and 5 differentiation opportunities documented
6. At least 10 assumptions tagged for M2 validation
7. All factual claims include source URLs
8. project-memo.md updated with Competitive Landscape synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/competitive-landscape-framework.md | Framework methodology and guidance | Step 01 |

---

## CRITICAL: WEB RESEARCH REQUIREMENT

⛔ **Web search is MANDATORY for this framework.** If web search is unavailable, abort and inform the user. Never fill competitive analysis from training data alone. All competitor claims must be verified with current sources.
