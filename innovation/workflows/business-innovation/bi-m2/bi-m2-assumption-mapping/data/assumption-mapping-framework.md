---
name: 'assumption-mapping-framework'
description: 'Reference methodology for Assumption Mapping framework'
---

# Assumption Mapping Framework Reference

## Overview

Assumption Mapping converts a flat list of assumptions into a visual decision tool. Every assumption from Leap of Faith is rated on two axes:

- **Importance (Y-axis):** If wrong, how much damage? (1=minor, 5=fatal)
- **Uncertainty (X-axis):** How little evidence do we have? (1=strong evidence, 5=no evidence)

The intersection determines what you do next:

| Quadrant | Importance | Uncertainty | Action |
|----------|------------|-------------|--------|
| Top-right | 3-5 | 3-5 | **TEST** — Design and run validation experiment |
| Top-left | 3-5 | 1-2 | **ACCEPT** — Treat as working assumption, revisit if contradicted |
| Bottom-right | 1-2 | 3-5 | **MONITOR** — Track passively, move to Test if importance increases |
| Bottom-left | 1-2 | 1-2 | **IGNORE** — No action needed |

---

## Importance Scale

Use these anchors consistently:

| Score | Label | Description |
|-------|-------|-------------|
| 5 | Fatal if wrong | Business model collapses. Matches Leap of Faith kill criteria. |
| 4 | Severe | Major pivot required. Revenue model or core value proposition breaks. |
| 3 | Significant | Important feature, channel, or cost assumption fails. Workaround possible but painful. |
| 2 | Moderate | Secondary assumption. Affects efficiency or timeline, not viability. |
| 1 | Minor | Nice-to-know. No material impact on go/no-go decision. |

---

## Uncertainty Scale

Use these anchors consistently:

| Score | Label | Description |
|-------|-------|-------------|
| 5 | No evidence | Pure guess. No data, no interviews, no analogies. |
| 4 | Weak signal | One anecdote, one data point, or founder intuition only. |
| 3 | Mixed signals | Some evidence supports, some contradicts. Or evidence is indirect. |
| 2 | Moderate evidence | Multiple data points or interviews support. Minor gaps remain. |
| 1 | Strong evidence | Robust data, validated in adjacent markets, or already tested. |

---

## Test Card Template

For each "Test" assumption, create a test card:

```markdown
### Test Card: [Assumption ID]

**Assumption:** [Statement]

**Hypothesis:** If [assumption] is true, then [observable outcome].

**Test Method:** [Lightest-weight method that produces credible evidence]
- Desk research (market data, competitor analysis)
- Customer interviews (5-10 targeted conversations)
- Landing page / smoke test (measure intent)
- Technical spike / PoC (for technical assumptions)
- Financial modeling with sensitivity analysis (for economic assumptions)
- Expert consultation (for domain-specific unknowns)

**Success Signal:** [Concrete evidence that validates — not "seems interested"]

**Failure Signal:** [Concrete evidence that invalidates — connect to kill criteria]

**Timeline:** [Days or weeks, not months]

**Owner:** [Founder / team member / AI agent]

**Downstream Framework:** [TAM/SAM/SOM / Unit Economics / TRL / Pre-mortem]
```

---

## Healthy Quadrant Distribution

For an early-stage startup:

| Quadrant | Target Range |
|----------|--------------|
| Test | 20-40% |
| Accept | 20-30% |
| Monitor | 15-25% |
| Ignore | 10-25% |

**Warning:** If Test exceeds 50%, you have too many unknowns to proceed without significant de-risking.

---

## Integration Points

### Builds On

| Framework | What It Provides |
|-----------|------------------|
| Leap of Faith (M2) | Prioritized assumptions, value/growth hypothesis classification, kill criteria |
| Lean Canvas (M1) | Economic and business model assumptions (P1, CS2, UVP1, etc.) |
| Problem-Solution Fit (M1) | Behavioural assumptions about customer and solution fit |
| Working Backwards (M1) | Internal FAQ assumptions about feasibility and economics |
| Five Whys (M1) | Root cause hypotheses about underlying problem causes |

### Feeds Into

| Framework | What It Receives |
|-----------|------------------|
| TAM/SAM/SOM (M2) | Economic assumptions flagged for market sizing validation |
| Unit Economics (M2) | Financial assumptions (LTV, CAC, retention) to stress-test |
| TRL (M2) | Technical assumptions flagged for feasibility assessment |
| Pre-mortem (M2) | All Test and Accept assumptions as potential failure modes |

---

## Common Pitfalls

1. **Skipping Leap of Faith** — Never start without completed Leap of Faith analysis
2. **Equal Importance Trap** — Never give everything a 4-5 importance score; differentiate ruthlessly
3. **Heavy Tests** — Never design multi-month research; use lightest-weight credible method
4. **Ignoring Accept** — Never treat "Accept" as "proven"; note what would cause revisiting
5. **One-Time Exercise** — Never freeze the map; update as tests produce evidence
