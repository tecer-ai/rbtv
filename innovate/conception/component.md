---
description: "The conception component — milestone 1 of the innovation trail: the frameworks that turn a raw idea into an articulated business concept (customer, problem, job, alternatives, solution fit, business model, root cause), plus the benchmark and product-map techniques that ground the concept in real products."
---

# conception

An agent enters this component to structure an idea into a business concept it can state
plainly: who the customer is, what problem they have, what job they hire a solution for,
what alternatives already exist, why this solution fits, what the business model hypothesis
is, and what the structural cause under the problem is. Each reference carries one
framework's substance and quality bar; the agent checks the work it produces against them.

The boundary with the sibling `validation/` component: conception decides what the venture
IS and records the assumptions that claim makes. `validation/` tests whether those
assumptions hold. A framework that produces a claim belongs here; a framework that tries to
break one belongs there.

| Part | What it is |
|---|---|
| `references/working-backwards.md` (reference) | The future press release plus external and internal FAQ — customer, problem, value, and "is it worth doing?" |
| `references/jobs-to-be-done.md` (reference) | The job customers hire a solution for: job statement, job types, the four forces, the job map, and the interview method |
| `references/competitive-landscape.md` (reference) | How the market addresses the job today: direct, indirect, non-consumption, geographic benchmarks, cross-industry analogues, positioning |
| `references/problem-solution-fit.md` (reference) | The narrow canvas testing whether one solution fits one customer problem in one context |
| `references/lean-canvas.md` (reference) | The nine-block business-model hypothesis, every block an assumption |
| `references/five-whys.md` (reference) | Root-cause chains from one concrete problem down to a structural cause |
| `references/benchmark-analysis.md` (reference) | Turning a pile of benchmark documents into a taxonomy, per-product profiles with a residual channel, and a feature-by-competitor synthesis |
| `references/product-landscape.md` (reference) | The founder-owned module and feature map — benchmark-informed, never benchmark-copied, with conscious omissions and V1/later classification |

## Entry points

- `references/` — one file per framework, read on demand; the trail order and when to reach
  each one live in `../trail/references/innovation-trail.md`.
- No `exposure.csv`: no part here is exposed on its own. Every reference is reached through
  the trail reference or the mentor prompt, which is the reference kind's default and a
  sanctioned state, not a gap.

## Origin (owner-ruled 2026-08-21)

Migrated from the rbtv repo's old-standard module at
`3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m1/` — six framework
folders, each with a knowledge document, a workflow, and numbered step files. Only the
framework substance and its quality bar were carried. The step machinery, the framework
menus, the `[S]`/`[B]` navigation, the per-step frontmatter, and the memo-update
instructions were deliberately NOT carried: pacing and state belong to
`../trail/references/innovation-trail.md`, and the mentor voice to
`../trail/prompts/innovation-mentor.md`.

`benchmark-analysis.md` and `product-landscape.md` were folded in from the separate
`3-resources/tools/rbtv/innovation/workflows/product-discovery/` workflow (steps 01–04) by
owner ruling: include its value, not its verbatim five-step workflow, and mint no fourth
milestone. Its fifth step became `../validation/references/v1-scoping.md`.
