---
description: "TAM/SAM/SOM — size the market by two independent methods, narrow to what can be served through named filters, and build the obtainable share from go-to-market capacity rather than a percentage."
tags: [validation]
---

# TAM / SAM / SOM

Market sizing as a discipline, not a pitch number. TAM is the whole revenue opportunity if every
potential customer bought this product type; SAM is the portion serviceable given geography,
segment, channel and capability constraints; SOM is what can realistically be captured in years 1–3
given actual go-to-market capacity. Every number is a hypothesis: record its source, use ranges, and
flag weak reasoning as weak.

## The sequence

Worked in this order, always. Each step consumes the previous one's output, so a skipped or reordered
step is not a shortcut — it silently invalidates everything downstream of it.

| # | Step | What it produces | What breaks if it is skipped or taken out of order |
|---|---|---|---|
| 1 | Define the category and the unit | The product category being sized, who counts as one customer, and what one customer's annual revenue means | Both sizing methods size different things, so step 4's reconciliation is meaningless and the divergence cannot be interpreted |
| 2 | TAM top-down | A whole-category revenue figure from published data, narrowed by segment filters, with sources and a confidence rating | There is nothing to check the bottom-up count against, and an inflated adjacent category goes undetected |
| 3 | TAM bottom-up | A customer count × average revenue per customer, with sources and a confidence rating | The published category number stands unchallenged — the single most common way TAM ends up inflated |
| 4 | Reconcile the two TAMs | A stated divergence and, above 2×, an explanation naming the weakest assumption | The weakest assumption in the model is never surfaced; averaging the two hides it permanently |
| 5 | SAM narrowing waterfall | A sequential reduction — geography → customer segment → product fit → channel constraints → technical and regulatory — each step carrying its percentage cut and rationale | SAM becomes an asserted fraction of TAM instead of a derived one, and step 6's sanity band has no denominator to check against |
| 6 | SOM from capacity | Years 1–3 built from monthly leads, conversion, sales-cycle length, onboarding capacity, churn and expansion — then sanity-checked against the SAM bands | SOM defaults to an arbitrary percentage of SAM, which is the failure this framework exists to prevent |
| 7 | Fragility pass | A confidence rating on every market assumption and the top 3–5 fragile ones, each linked to a validation method | The model is presented as fact; nobody knows which number to go and test first |
| 8 | Extract the handoff inputs | Customer counts, average revenue per customer and churn, stated explicitly for `unit-economics.md` | The unit-economics framework recomputes these from scratch and diverges from the sizing model |

Steps 2 and 3 are the one permitted exception: they are independent by design and may be worked in
either order, or in parallel. Nothing else moves.

## The structure

**Two methods, always both.**

| Method | How | Typical sources | Failure mode |
|---|---|---|---|
| Top-down | Start from published industry data, narrow by segment filters | Analyst reports, market databases, public filings, government data | Often inflated; the published category rarely matches the actual segment |
| Bottom-up | Count potential customers directly, multiply by average revenue per customer | Industry directories, professional-network counts, government registries | May miss segments; the revenue-per-customer estimate is usually the weak link |

When the two diverge by more than 2×, the gap IS the finding — it points at the weakest assumption
in the model. Explain it; do not average it away.

**SAM narrowing waterfall** — apply sequentially from TAM, recording the percentage reduction and
the rationale at each step: geography → customer segment (size, industry, role) → product fit (which
sub-use-case within the category) → channel constraints → technical and regulatory requirements.

**SOM from capacity, never from a share percentage.** Build it from monthly leads (channel capacity ×
conversion to lead), conversion rate, sales-cycle length, onboarding capacity, churn, and expansion
revenue. Year-1 revenue = (monthly leads × conversion × 12) × average revenue per customer. Sanity
band: year 1 is typically 0.5–2% of SAM (above 2% is aggressive), year 3 is 2–10% (above 10% needs a
real competitive moat).

**Confidence rating for every market assumption.** High: multiple independent recent sources agree
and match the exact segment. Medium: a single reliable source, or several with discrepancies. Low:
old data, proxy markets, or significant extrapolation.

**Source quality.** Analyst reports, public company filings and government or census data are the
strong tier; trade-association data and startup or professional-network databases are the medium
tier; blog posts and articles are triangulation only, never a load-bearing figure. This framework
sets WHICH numbers are needed — how a web source is scored, cited and reported is the workspace's
research-rigor standard at `web/research/references/standards.md`, not restated here.

## What a good output contains

- TAM calculated by BOTH methods, with the sources for each stated.
- A SAM waterfall in which every constraint is named and quantified, not just asserted.
- SOM projected for years 1–3, derived from capacity inputs that are visible in the document.
- Top-down and bottom-up compared at every layer, with each discrepancy explained.
- Ranges, not point estimates — "$2.4B" implies a precision the evidence does not support.
- The top 3–5 fragile assumptions identified and each linked to a validation method.
- The inputs the unit-economics model needs, extracted explicitly: customer counts, average revenue
  per customer, churn.

Failure looks like: quoting TAM as the target (TAM is a ceiling; SOM is what matters), a single
sourcing method with no error correction, sizing an inflated adjacent category instead of the real
product category, deriving SOM as an arbitrary percentage of SAM, and never revisiting the model
once real pricing or channel data arrives.

## Builds on / feeds

Builds on the conception outputs that define who is being sold to and how (customer segments,
revenue streams, channels, the customer definition and the alternatives), and on the market-related
assumptions flagged by `leap-of-faith.md` and `assumption-mapping.md`. It OWNS market sizing:
`unit-economics.md` references its SAM and takes its customer counts, average revenue and churn for
revenue projections rather than recomputing them; its market-risk scenarios feed `pre-mortem.md`.

## Sources

Distilled from
`3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m2/bi-m2-tam-sam-som/`
(`data/tam-sam-som-framework.md`, `workflow.md`, `steps-c/step-07-synthesis.md`).
