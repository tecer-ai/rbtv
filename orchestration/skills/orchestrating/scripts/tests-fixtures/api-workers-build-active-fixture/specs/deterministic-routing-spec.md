# Spec — Deterministic `(model, variant)` Selection + Claude-Tier Modeling

> This feature is **conductor behavior** (routing-card prose + a new manifest), not Python. Its "build" is the `models/claude/` package + the routing/intake card edits; its "test" is exercised by the conductor on real installed manifests. Build paths are relative to the **rbtv repo root** (`3-resources/tools/rbtv/`).

## Goal

When the conductor selects a worker for a task leaf, it **enumerates every installed `(model, variant)`**, filters to the capable ones, ranks them by a **total order**, picks deterministically, and **names the chosen `(model, variant)`** in the run-log and the intake budget summary — **never** collapsing a provider (e.g. "Claude") to a single entity. The Agent-tool Claude tiers are enumerable because they now have a manifest.

## Context Snapshot

**Current collapse (root cause):** `models/` holds `claude-cli` (the `claude -p` *process* worker, which DOES model `opus`/`sonnet` variants), `codex`, `kimi`, `qwen` — but the **Agent-tool Claude tiers** (the in-session default carrier, routing §4) have **no manifest**. The intake budget sketch (intake.md §4) therefore assigns prose roles ("a top-tier Claude") instead of `(model, variant)` pairs — that absence IS the collapse.

**Manifest variant fields used by the selector** (manifest-schema.md §2): `reasoning_tier`, `context_window`, `cost_class` (`cheapest`<`low`<`mid`<`high`), `code_competence`, `web_access`, `evidence_status` (`validated`>`probe-pending`).

**The new `models/claude/` package:** Agent-tool Claude tiers as variants — `opus` (reasoning_tier `top`, cost_class `high`, ctx 1M, code `strong`, web false-native), `sonnet` (`mid`, `mid`, ctx ~200k–1M, `strong`). **No haiku variant** (the sonnet-floor policy; add only under an approved delegation map). Repurposed CLI-shaped fields: `headless`→"in-session, non-interactive", `auth`→`{required:false, method:none}` (the conductor IS Claude), `guidance_file`→omitted (Agent-tool does not natively load `CLAUDE.md`), `confinement.write_enforcement`→`git-diff-vs-allowlist`, `swarm_support`→nesting-wall (subagents cannot nest). Sibling to — not a replacement for — `claude-cli` (process boundary, different properties).

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | A leaf needs a worker | The conductor enumerates ALL installed `(model, variant)` from the live `models/` folder — Claude (Agent-tool), claude-cli, kimi, codex, the API packages — never a bare provider name |
| 2 | The leaf has hard requirements (reasoning, context size, web, code) | **Filter**: keep only variants meeting them (`reasoning_tier ≥ needed`, `context_window ≥ inlined size`, `web_access` if web, `code_competence ≥ needed`) |
| 3 | ≥1 variant survives the filter | **Rank by the total order**: `cost_class` ↑ → `evidence_status` (validated > probe-pending) → `reasoning_tier` fit (closest-not-over) → model-name lexical → `variant-name` lexical. Pick the top |
| 4 | Stakes tier-up or a pinned-role floor applies | Apply AFTER the cheapest pick — pins/stakes may override it upward (reviewer ≥ sonnet, etc.) |
| 5 | The assignment is logged / summarized | The run-log and the intake budget summary name the chosen `(model, variant)` — e.g. `claude:sonnet`, `deepseek:v4-flash` — never just "Claude" |
| 6 | Two Claude carriers exist (Agent-tool vs process) | §4 carrier-resolution picks `claude` (Agent-tool, default) vs `claude-cli` (process, when a sub-conductor / native-rules load is needed) — both enumerated as distinct `(model, variant)` |

## Edge Cases & Error Behavior

| Condition | Required behavior |
|-----------|-------------------|
| Two surviving variants would tie on `cost_class` | The total order MUST break it (`evidence_status` → `reasoning_tier` fit → model-name → `variant-name`) — and Key 5 (`variant-name`) closes it absolutely: the `(model-name, variant-name)` pair is unique per enumerated row, so no tie can survive all five keys. The order is PROVABLY TOTAL and the selector is NEVER non-deterministic — including future manifests where two variants of one model differ only on a non-rank field, since they still differ on `variant-name` |
| Zero variants survive the filter | Degrade per routing §1 (next-capable / Agent-tool Claude fallback) or HALT — never silently pick an incapable variant |
| A provider has many modes | Author a variant ONLY where a mode changes a routing-relevant field; identical-routing modes are NOT separate variants (variant field-count discipline) |
| `models/` has zero CLI packages | Only `models/claude/` (Agent-tool) is routable — the baseline always-present carrier |

## Out of Scope

- Changing the **boundedness/stakes scoring** — that stays judgment (the selector is deterministic only AFTER requirements are scored).
- Re-modeling or migrating `claude-cli` — it stays as-is; `models/claude/` is added beside it.
- Per-task cost forecasting math — the budget summary reads `cost_class`, it does not compute dollar figures here.

## Test Plan

> Fidelity floor: exercise the selector as the conductor on the **real installed manifests** in this workspace; evidence = a written trace of the enumerate→filter→rank for a sample leaf, plus a sample intake summary.

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Every installed `(model, variant)` is enumerated, Claude included | Run the selection for a partially-bounded text leaf against the live `models/` (with `models/claude/` present) | The trace lists Claude `opus`/`sonnet` alongside the API + CLI variants | written selection trace file |
| 2 | The pick is deterministic | Run the SAME leaf selection twice | Identical `(model, variant)` both times; no tie reached the judgment fallback | two traces, identical |
| 3 | No bare-provider collapse | Produce a sample intake budget summary for a mixed build | Every row names a `(model, variant)` pair — no row says just "Claude" | sample summary file |
| 4 | A web leaf filters correctly | Select for a web-needing leaf | Only `web_access: true` variants survive (Gemini variants, Manus, claude-cli) — DeepSeek/OpenAI filtered out | selection trace |
| 5 | Pins still win | Select a reviewer role | The reviewer floors at sonnet regardless of a cheaper capable variant | selection trace |

## Return Expectations

This feature is verified by the `p3-checkpoint` (determinism + no-collapse): the conductor exhibits the enumerate→filter→rank traces and a sample summary naming pairs. No executor "return" beyond the card edits + the `models/claude/` manifest landing on disk and the checkpoint evidence.
