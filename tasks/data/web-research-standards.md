# Web Research Standards

Reference data for rigorous research, source evaluation, and citation.

---

## Data Integrity Rules

| Rule | Requirement |
|------|-------------|
| **Anti-hallucination** | NEVER present information without verified sources. Web search is REQUIRED for factual claims about current market conditions, competitors, or industry data |
| **No fabrication** | NEVER fabricate, estimate, or extrapolate data. If data unavailable, state "DATA NOT FOUND IN SOURCES" |
| **Inline citations** | Every number, statistic, or claim must cite its source inline (e.g., "[Source 12]") |
| **Date specificity** | Always state exact years/dates when citing data—never use vague terms like "recently" without defining the period |
| **Multiple sources** | Critical claims (market share, pricing, competitor capabilities, market size) REQUIRE 2+ independent sources for verification |
| **Conflict resolution** | When sources conflict, present all views and note discrepancies explicitly |
| **Confidence flagging** | Tag uncertain or single-source data as [High/Medium/Low Confidence] |

---

## Quantification Standards

| Data Type | Required Unit | Example |
|-----------|---------------|---------|
| Market sizes | $ billions/millions | "The market reached $2.3B in 2025" |
| Market shares | % | "Company X holds 34% market share" |
| Growth rates | % CAGR or YoY | "Growing at 8.5% CAGR (2020-2025)" |
| Revenues | $ millions/billions | "Revenue: $450M (2024)" |
| Capacities | beds/m²/hectares/units | "Hospital has 2,400 beds" |
| Counts | # (number) | "Operating 47 facilities nationwide" |
| Prices | $/unit with unit specified | "$85/m² residential, $120/m² commercial" |
| Penetration/adoption | % of relevant population | "Internet penetration: 72% urban, 23% rural" |

---

## Temporal Definitions

| Term | Default Meaning | Rule |
|------|-----------------|------|
| "Recent" | Last 3-5 years | Always specify exact years when citing |
| "Historical" | 5-10 years | State the exact period covered |
| "Current" | Most recent available data | Cite the data date |

---

## Player Thresholds

| Term | Definition | Rule |
|------|------------|------|
| "Major players" | Top 3-5 by market share or revenue | Always specify which metric used for ranking |
| "Leading" | #1 or top 2 | State the ranking metric |
| "Notable" | Has differentiated characteristic | Explain why notable |

---

## Source Evaluation Criteria

Evaluate all sources using three criteria:

| Code | Attribute | Description | Scale |
|------|-----------|-------------|-------|
| AT | Authority | Source expertise in the field | 1-10 |
| TR | Trustability | Reputation (well-known vs niche) | 1-10 |
| TM | Topic Match | How well topic fits source content | 1-10 |

**Total Score (TS):** Average of AT, TR, TM

**Threshold:** Sources with TS < 6 are FORBIDDEN

---

## Marketing Language Penalty

Reduce TR score for promotional content:

| Penalty | When to Apply |
|---------|---------------|
| -1 TR | Mostly factual with occasional marketing |
| -2 TR | Mix of factual and frequent marketing |
| -3 TR | Primarily promotional, limited factual content |

---

## Prohibited Marketing Terms

**PROHIBITED:** "sophisticated", "revolutionary", "cutting-edge", "best-in-class", "industry-leading", "game-changing", "transformative"

**REQUIRED:** Neutral terms — "supports", "enables", "provides", "implements"

---

## Citation Format

```
[n] Title — URL — Research Date (YYYY-MM-DD) — Source Date — TS:x (AT:x TR:x TM:x)
```

**Example:**
```
[1] Anthropic Claude Documentation — https://docs.anthropic.com — 2025-12-02 — 2025-11-15 — TS:9 (AT:10 TR:9 TM:8)
```

---

## Legend Requirement

Research outputs **must** include:

```markdown
> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6
```

---

## Discarded Sources Format

```markdown
## Sources Discarded

| Source | TS | Reason |
|--------|-----|--------|
| [Title](link) | 5.3 | Low authority (AT:4) |
```

---

## Link Verification

| Status | Meaning |
|--------|---------|
| ✓ Verified | Link tested and working |
| ⚠ Redirect | Link redirects (note destination) |
| ✗ Broken | Link no longer works |

---

## Domain Grouping Rules

**Default:** Multiple links from same domain count as ONE source.

**Exceptions — count as separate sources:**
- Academic papers from same institution (different arXiv papers, journal articles)
- Consultancy reports from same firm (different Gartner reports, Forrester analyses)
- Distinct authored articles/posts (different blog posts by different authors)
- Different publication types from same organization (documentation vs blog vs research paper)

**Scoring for nested sources:**
- Each nested entry has its own individual evaluation (AT, TR, TM, TS)
- Apply marketing language penalty to each nested entry individually
- Nested entries with TS < 6 are discarded; remaining entries are still used
- Parent row shows average scores of all non-discarded nested entries

---

## Fact vs Analysis Distinction

| Type | Definition | When to Use |
|------|------------|-------------|
| **Facts** | Information directly from verified sources | Cite with URL |
| **Analysis** | Your interpretation or synthesis | State explicitly as analysis |
| **Speculation** | Hypotheses or projections | Flag as speculation with confidence level |

---

## Tone Guidelines

| Context | Required Tone | Avoid |
|---------|---------------|-------|
| Investment/economic research | Direct, financial, action-oriented | Academic hedging, passive voice, jargon |
| Technical documentation | Practical, instructional | Narrative, promotional |
| Academic research | Formal, cited, methodological | Casual, unsupported claims |

---

## Output Length Standards

| Pages (Arial 10pt) | Characters (incl. spaces) |
|--------------------|---------------------------|
| 10 pages | ~25,000-30,000 |
| 20 pages | ~50,000-60,000 |
| 50 pages | ~125,000-150,000 |
| 70 pages | ~175,000-210,000 |
