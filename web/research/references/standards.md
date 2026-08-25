---
description: "Read at the moment of conducting or reporting multi-source web research — the whole rigor standard from first search to finished report: how a source is scored, when a claim counts as verified, how the report cites, flags, and discards, and when to stop and ask."
---

# Web research — the rigor standard

Every rule here binds every research output, whatever asked for it.

## Reaching a page

Finding a URL is a live web search. Reading what sits behind that URL is the sibling `web/browse`
component — its routing capability picks the surface and states its own failure modes.

## 1. Identify the topic

- Structured input ("Research Topic: X", "Context: Y") MUST be used exactly as given.
- With no structured input, the user's most recent question IS the topic, and the surrounding
  conversation supplies its context.

## 2. Execute searches

- A live web search MUST run before any factual claim is written. Presenting a factual claim about
  market conditions, competitors, industry data, or any current state without a verified source
  behind it is FORBIDDEN.
- A **critical claim** — market share, pricing, competitor capability, market size, or any figure a
  decision turns on — MUST be supported by **2+ independent sources**. Two pages from one publisher
  are ONE source unless § 4 says otherwise.
- Searching MUST continue until every critical claim holds its 2+ sources, or until § 5 fires.

## 3. Score every source

Every source MUST be scored on all three criteria before it is used or discarded.

| Code | Attribute | What it measures | Scale |
|------|-----------|------------------|-------|
| AT | Authority | The source's expertise in the field | 1–10 |
| TR | Trustability | Reputation — well-known versus niche | 1–10 |
| TM | Topic Match | How well the researched topic fits the source's content | 1–10 |

**TS = the average of AT, TR, TM.**

**A source with TS < 6 is FORBIDDEN.** It NEVER supports a claim, and it MUST be listed in
§ Sources discarded.

### Marketing-language penalty

The TR score MUST be reduced when the source's own writing is promotional:

| Penalty | Applied when the source is |
|---------|----------------------------|
| −1 TR | Mostly factual, with occasional marketing |
| −2 TR | A mix of factual content and frequent marketing |
| −3 TR | Primarily promotional, with limited factual content |

Judgment call: which of the three bands a source falls in. Read a representative stretch of the
page, not its headline, and prefer the harsher band when the two are equally arguable.

This penalty scores the SOURCE's language. The vocabulary the research output itself NEVER uses is a
separate rule (§ Prohibited terms).

## 4. Group same-domain sources

**Default: multiple links from one domain count as ONE source.**

They MUST be counted as separate sources when any of these holds:

- Academic papers from the same institution (different arXiv papers, different journal articles).
- Consultancy reports from the same firm (different Gartner reports, different Forrester analyses).
- Distinct authored articles or posts (different blog posts by different authors).
- Different publication types from the same organization (documentation versus blog versus research
  paper).

When links are grouped, each sub-source MUST be nested under its parent, and:

- Each nested entry MUST get its own AT, TR, TM, and TS.
- The marketing-language penalty MUST be applied to each nested entry individually.
- A nested entry with TS < 6 MUST be discarded; the remaining nested entries are still used.
- The parent row's score MUST be the average of its non-discarded nested entries.

## 5. When to stop

- **No source found with TS ≥ 6** → the research MUST stop, report that no source cleared the
  threshold, and request guidance from the user. The gap is NEVER filled with unsourced material.
- **A critical claim cannot be verified with 2+ independent sources** → that claim MUST be flagged
  explicitly, in the output, BEFORE proceeding with anything that rests on it.

## Sources manifest — an optional layer

A run MAY be pointed at a user-curated **sources manifest**: a file declaring which sources to
favor and which to avoid.

**Pointer mechanism.** The dispatch prompt or the user names a manifest path (for example, "honor
the sources manifest at `<path>`"). When a path is named, that file MUST be loaded at the start of
the run, before the first search. The manifest file is owned by the user or the workspace; it is
never shipped with this component.

**Graceful skip.** With no path named, this section MUST be skipped silently — no manifest is
hunted for, nothing is announced, and every other rule in this file governs unchanged.

**Shape.** Read whatever subset of these the file provides:

| Field | Declares |
|-------|----------|
| Preferred sources | Origins, domains, or publishers the user trusts, optionally tiered |
| Banned sources | Origins or domains the user rejects or rates below the evidence bar |
| Per-topic notes (optional) | Topic- or anchor-scoped guidance, applied ONLY to the matching topic |

**Honor semantics:**

| Stage | With a manifest loaded |
|-------|------------------------|
| Selection and ranking | Among sources of comparable topic-relevance, a preferred-listed source MUST rank first; a banned-listed source MUST be excluded from primary support |
| Evaluation | The manifest layers ON TOP of AT/TR/TM scoring and NEVER lowers the TS ≥ 6 bar. A preferred source still MUST clear TS ≥ 6; a banned source is dropped even when it would score above 6 |
| Sole support | A claim whose ONLY support is a banned source MUST be treated as unsupported: surface it as below-bar, then hunt the trustworthy source behind it |
| Conflict | Manifest preference breaks ties between comparable sources and NEVER overrides the rules of § Data integrity — the 2+ source requirement, conflict resolution, and confidence flagging all still bind |

## Reporting

Every research output MUST carry all three of: the legend, the scored citation list, and the Sources
Discarded section.

### Data integrity

| Rule | Requirement |
|------|-------------|
| Anti-hallucination | Information NEVER appears without a verified source behind it |
| No fabrication | Data is NEVER fabricated, estimated, or extrapolated. Where it is unavailable, the output MUST state "DATA NOT FOUND IN SOURCES" |
| Inline citations | Every number, statistic, and claim MUST cite its source inline (for example, "[Source 12]") |
| Date specificity | Exact years and dates MUST be stated. A vague term such as "recently" is NEVER used without defining the period it covers |
| Conflict resolution | Where sources conflict, ALL views MUST be presented and the discrepancy noted explicitly. The conflict is NEVER silently resolved in favor of one side |
| Confidence flagging | Uncertain or single-source data MUST be tagged `[High Confidence]`, `[Medium Confidence]`, or `[Low Confidence]` |

### Quantification

Every figure MUST carry its unit:

| Data type | Required unit | Example |
|-----------|---------------|---------|
| Market sizes | $ billions / millions | "The market reached $2.3B in 2025" |
| Market shares | % | "Company X holds 34% market share" |
| Growth rates | % CAGR or % YoY | "Growing at 8.5% CAGR (2020–2025)" |
| Revenues | $ millions / billions | "Revenue: $450M (2024)" |
| Capacities | beds / m² / hectares / units | "Hospital has 2,400 beds" |
| Counts | # (a number) | "Operating 47 facilities nationwide" |
| Prices | $ per unit, with the unit named | "$85/m² residential, $120/m² commercial" |
| Penetration or adoption | % of the relevant population | "Internet penetration: 72% urban, 23% rural" |

### Temporal terms

| Term | Default meaning | Rule |
|------|-----------------|------|
| "Recent" | The last 3–5 years | The exact years MUST be stated alongside it |
| "Historical" | 5–10 years | The exact period covered MUST be stated |
| "Current" | The most recent available data | The date of that data MUST be cited |

### Player terms

| Term | Definition | Rule |
|------|------------|------|
| "Major players" | Top 3–5 by market share or revenue | The metric used for the ranking MUST be named |
| "Leading" | #1, or top 2 | The ranking metric MUST be stated |
| "Notable" | Holds a differentiated characteristic | Why it is notable MUST be explained |

### Prohibited terms

These are NEVER written in a research output: "sophisticated", "revolutionary", "cutting-edge",
"best-in-class", "industry-leading", "game-changing", "transformative".

Neutral verbs MUST be used in their place: "supports", "enables", "provides", "implements".

### Fact, analysis, speculation

Every statement MUST be identifiable as exactly one of these:

| Type | What it is | How it MUST appear |
|------|------------|--------------------|
| Fact | Taken directly from a verified source | Cited with its URL |
| Analysis | The agent's own interpretation or synthesis | Stated explicitly as analysis |
| Speculation | A hypothesis or projection | Flagged as speculation, with a confidence level |

### Citations

Every cited source MUST use this format:

```
[n] Title — URL — Research Date (YYYY-MM-DD) — Source Date — TS:x (AT:x TR:x TM:x)
```

Example:

```
[1] Anthropic Claude Documentation — https://docs.anthropic.com — 2025-12-02 — 2025-11-15 — TS:9 (AT:10 TR:9 TM:8)
```

### Legend

The legend is this block, verbatim:

```markdown
> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6
```

### Sources discarded

The section's shape:

```markdown
## Sources Discarded

| Source | TS | Reason |
|--------|-----|--------|
| [Title](link) | 5.3 | Low authority (AT:4) |
```

When nothing was discarded, the section MUST state: "No sources discarded — all sources met TS ≥ 6
threshold."

### Link verification

Every link in the output MUST carry its tested status:

| Status | Meaning |
|--------|---------|
| ✓ Verified | The link was tested and works |
| ⚠ Redirect | The link redirects — the destination MUST be noted |
| ✗ Broken | The link no longer works |

### Tone

| Context | Required tone | NEVER |
|---------|---------------|-------|
| Investment or economic research | Direct, financial, action-oriented | Academic hedging, passive voice, jargon |
| Technical documentation | Practical, instructional | Narrative, promotional |
| Academic research | Formal, cited, methodological | Casual, unsupported claims |

### Output length

When a length is requested in pages, the output MUST be sized by this table (Arial 10pt,
characters including spaces):

| Pages | Characters |
|-------|------------|
| 10 | ~25,000–30,000 |
| 20 | ~50,000–60,000 |
| 50 | ~125,000–150,000 |
| 70 | ~175,000–210,000 |

Judgment call: no length requested. Length is then set by what the sources support — and a page
count is NEVER reached by adding unsourced material.
