---
description: "Unit Economics — reduce the business model to the economics of one customer: lifetime value, acquisition cost, their ratio, payback period, break-even, and which assumptions the answer actually depends on."
tags: [validation]
---

# Unit Economics

If money cannot be made on one unit, it cannot be made on a million. This framework fixes what "one
unit" means (a customer, a transaction, a seat), then models what that unit earns, what it costs to
acquire, how long the money takes to come back, and how many units are needed to cover fixed costs.
Run it after market sizing, which supplies the customer counts and average revenue it consumes.

## The sequence

Worked in this order, always. Each step consumes the previous one's output, so a skipped or
reordered step is not a shortcut — it silently invalidates everything downstream of it.

| # | Step | What it produces | What breaks if it is skipped or taken out of order |
|---|---|---|---|
| 1 | Define the unit | A statement of what one unit is — a customer, a transaction, a seat — and how revenue is generated from it | Every figure below is computed against a different denominator, and the ratios are arithmetic on unrelated numbers |
| 2 | Pull the inputs from market sizing | Customer counts, average revenue per customer and churn taken from `tam-sam-som.md` rather than re-estimated here | Two models of the same business circulate with different numbers, and neither is the one anybody updates |
| 3 | Set gross margin | Revenue minus cost of goods sold, over revenue, with the cost lines named | Lifetime value gets computed on revenue instead of margin, which overstates it by whatever the delivery cost is |
| 4 | Compute lifetime value | Average revenue per user × gross margin × average lifetime, with the churn assumption visible and lifetime capped at five years | An uncapped lifetime turns a small churn assumption into a decade of imagined revenue |
| 5 | Compute acquisition cost | Cost per channel AND blended, counting people, advertising, tools, content, commissions and founder time | An advertising-only acquisition cost is the standard way this model comes out healthy and is wrong |
| 6 | Compute the ratio and the payback period | Lifetime value to acquisition cost, and acquisition cost over monthly margin per customer, each read against its band | Viability gets judged on lifetime value alone, with no view of how long the business is cash-negative |
| 7 | Compute break-even | Monthly fixed costs over monthly contribution margin per customer, with founder salaries at a real imputed rate | The number of customers needed to survive is never stated, and "we'll raise more" quietly replaces it |
| 8 | Build the three scenarios | Pessimistic, base and optimistic, each carrying its own churn, revenue-per-user and acquisition-cost inputs | Single-point estimates present a guess as a forecast, and there is no pessimistic case to judge viability on |
| 9 | Tag every number | DATA, BENCH or HYPO on each input, plus a high / medium / low confidence rating | Hypotheses and real data become indistinguishable the moment the document is read by anyone else |
| 10 | Run the sensitivity analysis | Each input varied, with the top 3–5 assumptions that actually move the outcome named | Validation effort gets spread evenly across inputs instead of aimed at the few that decide the answer |
| 11 | State the viability conclusion | A conclusion that names which scenario it rests on — judged on the pessimistic one | An optimistic-case conclusion travels forward with no label and is read as the expected outcome |

Nothing here may be worked out of order — in particular, the conclusion is never written before the
sensitivity analysis says which assumptions it depends on.

## The structure

**Lifetime value** = average revenue per user × gross margin × average customer lifetime, where
gross margin = (revenue − cost of goods sold) / revenue and average lifetime = 1 / churn rate.

**Acquisition cost** = total acquisition spend / new customers acquired. Include ALL of it: people,
advertising, tools, content, commissions, and founder time.

| Lifetime value : acquisition cost | Reading |
|---|---|
| below 1:1 | Losing money on every customer — the model is broken |
| 1:1 to 3:1 | Marginal — no margin for error |
| 3:1 to 5:1 | Healthy — room to invest in growth |
| above 5:1 | Possibly under-investing in acquisition |

**Payback period (months)** = acquisition cost / (monthly revenue per user × gross margin). Under 12
months is strong; 12–18 is acceptable for business-to-business with annual contracts; over 18 months
means running cash-negative too long.

**Break-even customers** = monthly fixed costs / monthly contribution margin per customer, where
fixed costs are salaries, office, tools and infrastructure (not per-customer costs) and contribution
margin is monthly revenue per user × gross margin. Founder salaries go in at a reasonable imputed
rate — never zero.

**Churn benchmarks**, used only when real data is absent and always tagged as benchmarks: small and
medium business software 3–7% monthly (14–33 months of lifetime); mid-market 0.8–1.2% (7–10 years);
enterprise 0.4–0.8% (10–20 years); consumer subscription 5–10% (10–20 months). Cap lifetime at five
years for an early-stage venture to keep the model out of fantasy.

**Three scenarios, always.** Pessimistic (higher churn, lower revenue per user, higher acquisition
cost, no expansion), base (best current assumptions with realistic ranges), optimistic (lower churn,
higher revenue per user, expansion included). Judge viability on the PESSIMISTIC scenario.

**Tag every number** with its source — DATA (real data from the business or validated research),
BENCH (an industry benchmark from a credible source), HYPO (a hypothesis with no evidence) — and its
confidence: high (multiple supporting data points), medium (some evidence, gaps remain), low (a
single data point or a guess).

**Sensitivity analysis** — vary each input and record which ones actually move the outcome. Those
are the assumptions worth testing; the rest are noise.

## What a good output contains

- A unit-definition statement naming the unit and how revenue is generated from it.
- Acquisition cost per channel AND blended, in all three scenarios.
- Lifetime value with its revenue-per-user, margin and churn assumptions visible.
- The lifetime-value-to-acquisition-cost ratio computed for at least the pessimistic and base cases.
- Payback period stated with its cash-flow implication.
- Break-even customer count and the timeline to reach it.
- Sensitivity analysis naming the top 3–5 assumptions the conclusion depends on.
- A viability conclusion that is honest about which scenario it rests on.

Failure looks like: single-point estimates with no ranges, an acquisition cost that counts only
advertising spend, churn assumed better than the industry's best with no evidence, founder salaries
at zero, confusing booked revenue with collected cash (acquisition cost is paid immediately,
revenue arrives later), and skipping break-even because "we'll raise more".

## Builds on / feeds

Builds on `tam-sam-som.md` — it references SAM and takes its customer counts, average deal size and
churn for revenue projections rather than recomputing the market — and on the revenue-stream, cost-
structure and channel work from conception. It OWNS acquisition cost, lifetime value and payback; no
later framework re-derives them. Its critical economic assumptions go back into the Test quadrant of
`assumption-mapping.md`, and its financial failure and break-even risks feed `pre-mortem.md`.

## Sources

Distilled from
`3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m2/bi-m2-unit-economics/`
(`data/unit-economics-framework.md`, `workflow.md`, `steps-c/step-05-synthesis.md`).
