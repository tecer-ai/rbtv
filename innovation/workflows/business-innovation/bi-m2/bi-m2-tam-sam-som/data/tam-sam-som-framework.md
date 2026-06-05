---
name: 'tam-sam-som-framework'
description: 'Reference methodology for TAM/SAM/SOM market sizing framework'
---

# TAM/SAM/SOM Framework Reference

## Overview

Market sizing is not a pitch exercise. It is a discipline for quantifying:

1. **TAM (Total Addressable Market):** The entire revenue opportunity if every potential customer bought your product type
2. **SAM (Serviceable Addressable Market):** The portion you can serve given geographic, segment, channel, and capability constraints
3. **SOM (Serviceable Obtainable Market):** What you can realistically capture in Years 1-3 given your go-to-market capacity

Every number is a hypothesis. Document sources, use ranges, flag weak reasoning.

---

## Two-Method Requirement

Always calculate using BOTH methods:

### Top-Down
- Start from published industry data
- Narrow using segment filters
- Sources: Gartner, IDC, Forrester, Statista, public filings, government data
- Risk: Often inflated, may not match your specific segment

### Bottom-Up
- Count potential customers directly
- Multiply by average revenue per customer (ARPU)
- Sources: LinkedIn data, industry directories, government registries
- Risk: May miss segments, ARPU estimates often uncertain

**When they diverge by more than 2x:** The gap is the most valuable finding — it reveals where assumptions are weakest.

---

## Importance Scale for Market Assumptions

| Confidence | Description |
|------------|-------------|
| High | Multiple independent sources agree, recent data, exact segment match |
| Medium | Single reliable source, or multiple sources with some discrepancy |
| Low | Old data, proxy markets, significant extrapolation required |

---

## SAM Narrowing Filters

Apply these filters sequentially from TAM:

1. **Geography:** Which countries/regions will you serve?
2. **Customer Segment:** Which company sizes, industries, roles?
3. **Product Fit:** Does your product serve a sub-use-case within the category?
4. **Channel Constraints:** Which distribution channels can you operate?
5. **Technical/Regulatory:** Any infrastructure, integration, or compliance requirements?

For each filter, record the percentage reduction and rationale.

---

## SOM Calculation Components

Build SOM from go-to-market capacity, not percentages:

| Input | How to Estimate |
|-------|-----------------|
| Monthly leads | Channel capacity × conversion to lead |
| Conversion rate | Industry benchmarks for your segment |
| Sales cycle length | Days from first touch to revenue |
| Onboarding capacity | Customers per month you can support |
| Churn rate | Segment-appropriate annual churn |
| Expansion revenue | Upsells, seat growth, usage growth |

**Formula:** (monthly leads × conversion × 12 months) × ARPU = Year 1 revenue

---

## Healthy Market Share Benchmarks

| Timeframe | Typical Range | Notes |
|-----------|---------------|-------|
| Year 1 | 0.5-2% of SAM | >2% is aggressive for most startups |
| Year 3 | 2-10% of SAM | >10% requires strong competitive moat |

---

## Integration Points

### Prerequisites

| Framework | What It Provides |
|-----------|------------------|
| Lean Canvas (M1) | Customer Segments, Revenue Streams, Channels |
| Working Backwards (M1) | Customer definition, Internal FAQ economics |
| JTBD (M1) | Segment selection, alternatives |
| Leap of Faith (M2) | Market-related assumptions |
| Assumption Mapping (M2) | Market assumptions flagged for testing |

### Feeds Into

| Framework | What It Receives |
|-----------|------------------|
| Unit Economics (M2) | SOM customer counts, ARPU, churn rate |
| Assumption Mapping (M2) | New fragile assumptions with confidence ratings |
| Pre-mortem (M2) | Market risk scenarios |
| M5 Market Validation | Target segment size, capture assumptions |

---

## Common Pitfalls

1. **Using TAM as pitch number** — TAM is a ceiling, not a target. SOM is what matters.
2. **Single data source** — Always use top-down AND bottom-up. No error correction with one method.
3. **Point estimates** — Use ranges. "TAM = $2.4B" implies false precision.
4. **Inflated category** — Size your actual product category, not a broader market.
5. **SOM as % of SAM** — Build SOM from leads, conversion, capacity — not arbitrary percentages.
6. **One-time exercise** — Update when you get real data (customers, pricing tests, channel experiments).

---

## Data Source Quality

| Source Type | Reliability | Notes |
|-------------|-------------|-------|
| Major analyst reports (Gartner, IDC) | High | Often broad categories, adjust for your segment |
| Public company filings | High | Competitors/adjacents reveal market structure |
| Government/census data | High | May be dated, good for unit counts |
| Trade association data | Medium | May have industry bias |
| Startup databases (Crunchbase) | Medium | Incomplete coverage |
| LinkedIn counts | Medium | Good for SMB/professional segments |
| Blog posts/articles | Low | Use for triangulation only |
