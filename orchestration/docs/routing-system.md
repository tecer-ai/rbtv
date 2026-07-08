# Model Routing System — Developer Reference

> **Scope.** This document explains how the deterministic router *works* — the mechanism, the file layout, how to run its tests, and how to add a model. The per-model capability *values* (each variant's reasoning/coding/cost integers, prices, evidence) live in [`routing-matrix-reference.md`](./routing-matrix-reference.md); the field definitions live in [`../models/manifest-schema.md`](../models/manifest-schema.md). This doc does not restate either.
>
> **Authority.** The routing *card* (`orchestration/skills/orchestrating/cards/routing.md` §2a) is the algorithm authority; `orchestration/models/route.py` is the executable selector the card and the planner both call. On any script-vs-card divergence the card text wins and a defect is filed against the script.

---

## 1. What the router is

A stdlib-only Python selector that maps a **task profile** to a deterministic worker pick:

```
python orchestration/models/route.py <profile.json>          # from repo root
python orchestration/models/route.py <profile.json> --explain # + filter/rank trace
```

It returns one of three verdicts:

| Verdict | Meaning |
|---------|---------|
| `route` | A `(model, variant, carrier)` worker was selected (plus an `effort` label for multi-mode CLI families). |
| `self_execute` | The profile set `self_execute` — the conductor does it in-session, no dispatch. |
| `halt_seam` | An unresolved decision (unset `stakes`, a `cross_strategy` fork) must be taken to the owner before routing. |

Error verdicts (`malformed_profile`, `no_models`, `no_available_variants`, `zero_candidates`) carry a `details` string.

The same script is called at **plan time** (the planner pins each task's executor) and at **run time** (the conductor routes), so plan-time and run-time picks can never disagree.

---

## 2. The selection flow — GATE → RANK → PIN

`route()` runs these stages in order. The three headline stages are **GATE → RANK → PIN**; the surrounding steps prepare and finish the pipeline.

| # | Stage | Function | What it does |
|---|-------|----------|--------------|
| 0 | Enumerate | `_enumerate_models()` | Walk `orchestration/models/{model}/manifest.yaml`, keep only **elected** packages/variants (§7), skip infra dirs (`_api`, `_fixture`, `mirror`) and malformed manifests. |
| 1 | Scope | `_scope_eligible_set()` | The **boundedness master cut** — see §3. Restricts the candidate set by how fully the task is specified. |
| 2 | Plan caps | `_apply_plan_caps()` | Lower each variant's `context_window` to the per-deployment cap (§8). |
| 3 | Availability | `_is_variant_available()` | Drop variants flagged `available: false`, or whose API key is absent (OS env, then the `env_file` in `rbtv.json`). |
| 4 | **GATE** | `_filter()` | Hard pass/fail on every routing requirement (§3). |
| 5 | Haiku guard | `_exclude_haiku()` | Drop `haiku` variants before ranking unless the profile sets `delegation_map_allows_haiku: true`. |
| 6 | **RANK** | `_rank()` | Cost-ascending total order over the survivors (§4). |
| 7 | **PIN / stakes** | `_apply_pins_and_stakes()` | Raise the pick to a pinned-role floor and apply stakes tier-up (§5). Never lowers. |
| 8 | Effort | `_resolve_effort()` | Set the effort label (`low`/`medium`/`high`/`max`) from the chosen variant's `reasoning_modes.depths` and the task's boundedness. CLI carriers only; a no-op on single-mode workers. |

A **footprint fallback** (`_apply_footprint_fallback()`) fires between GATE and the zero-candidates error when the profile carries a `known_input_size` and no worker's capped window holds it: it re-runs every non-window gate over the full roster and picks the largest-window non-haiku survivor, still raised to any pinned floor.

---

## 3. GATE — the boundedness cut, floors, and role-eligibility

### Boundedness master cut

`boundedness` is the first thing the router reads. It both scopes the candidate set and sets the reasoning floor and effort. The three bands:

| Band | Scope (`_scope_eligible_set`) | Reasoning floor | Coding floor | Effort |
|------|-------------------------------|:---------------:|:------------:|--------|
| `fully-bounded` | all eligible variants | 1 | 1 | low |
| `partially-bounded` | Claude mid-tier and up (reasoning ≥ 6) | 6 | 4 | medium |
| `unbounded` | Claude top-tier only (reasoning ≥ 7) | 7 | 5 | high / max |

Floors are byte-for-byte integer comparisons against the 1–7 axes — there is no value-lookup table. Constants: `REASONING_FLOOR_BY_BAND`, `CODING_FLOOR_BY_BAND`.

### The 1–7 axes

`reasoning`, `coding`, and `cost` are comparable integers 1–7, re-derived from one external methodology (the Artificial Analysis leaderboard) so they do not rot:

- **reasoning / coding** — 1 = weakest, 7 = strongest. Used as `score ≥ floor` at GATE and as the capability tiebreak at RANK.
- **cost** — 1 = cheapest, 7 = priciest. The primary RANK key, **ascending**, so the cheapest-capable worker wins; the priciest bin `7` ranks last and is never auto-picked on a cost tie.

### Other hard gates (`_filter`)

A variant is dropped if it fails any of: reasoning floor · coding floor (code leaves only) · `context_window ≥` the task size (after the plan cap) · `web_access` when the task needs web · **`routable_for` allows this leaf**.

### Role-eligibility is independent of the coding score

`routable_for` is an allow-list over the closed role vocabulary `bounded-code · unbounded-code · reasoning · web-research · text-synthesis · other`:

- **Absent or empty** → eligible for every leaf (back-compat default).
- **Present** → eligible only for the listed roles.
- **Code-eligibility rule:** the two code roles (`bounded-code`, `unbounded-code`) are gated on `routable_for` *membership*, not on the coding integer. A non-executor (e.g. an API chat worker) may carry an honest coding score of 3–4 yet never receive a code leaf, because its `routable_for` omits the code roles. An honest coding score never re-enables an ineligible code route.
- An unknown role string is treated as not-matching — never a crash.

When a task routes via the `other` catch-all role, the router records the task's instructions/arguments (`_build_other_routing_audit()`) so under-served task types surface for promotion to a first-class role.

---

## 4. RANK — cost-ascending total order

`_rank()` sorts survivors by this key (all ascending):

1. `cost` (1–7, cheapest first)
2. `evidence_status` (`validated` before `probe-pending`)
3. capability — reasoning on text leaves, coding on code leaves (higher first)
4. carrier preference — Agent-tool Claude before the CLI-process Claude carrier
5. model name, then variant name (final deterministic tiebreak)

Because cost is the primary key, two code-task survivors tied on cost are ordered directly by their `coding` integer — there is no separate sub-rank step.

---

## 5. PIN — role floors, debug floor, stakes, empty-pipeline fallback

Pins raise the pick after ranking; they never lower it. Floors are defined in `_PINNED_FLOORS` and applied by `_apply_pinned_role_floor()`:

| Pinned role | Floor |
|-------------|-------|
| `reviewer` | ≥ executor reasoning + 1, floor Sonnet (reasoning 6), never Haiku. `reviews_external_cli_code: true` forces Opus. |
| `debug` | any code-eligible executor with reasoning ≥ 7. |
| `commit` | Agent-tool Claude Sonnet; if no Claude is available, the strongest-reasoner across all elected packages (excluding Haiku), cost ignored. |

**Stakes tier-up** (`_apply_stakes_tier_up`): a profile with `stakes_tier: tier_up` raises the boundedness band one level and re-resolves (re-scope, re-filter, re-rank) over the full enumeration.

**Empty-pipeline fallback:** when the band-scoped pipeline yields zero candidates but a `pinned_role` is set, the pin's own floor computation runs over the *full pre-scope* roster before returning the error — so a pinned role (e.g. a reviewer) can still be filled when the scoped set came up empty.

---

## 6. Manifest schema — the data interface

`orchestration/models/manifest-schema.md` is the **single source of truth** for the field list and the 1–7 vocabulary; `manifest-template.yaml` is the fill-in skeleton. `route.py`, every package manifest, `test_route.py`, the routing card, and the matrix reference all comply with it.

A package `manifest.yaml` carries package-level keys (`model`, `display`, `evidence_status`, optional `permission_rules`) and a `variants` list — routing always routes on `(model, variant)` pairs, never bare model names. Each variant carries the routing inputs (`reasoning`, `coding`, `cost`, `context_window`, `max_output`, `web_access`, optional `routable_for`, optional `reasoning_modes`, …) plus dispatch and metadata fields. Every required field must hold an evidence-traceable value — no placeholders.

---

## 7. Package layout & election

```
orchestration/models/
  {model}/
    manifest.yaml   # capability + routing inputs (the only routing source)
    delta.md        # model-specific render source (see §8)
    manual.md       # GENERATED dispatch manual — never hand-edit
  manifest-schema.md / manifest-template.yaml   # the schema + skeleton
  model-plans-schema.md / model-plans-example.yaml
  route.py / test_route.py / render-manuals.py
  _api/ _fixture/ mirror/                        # infra dirs — never enumerated
```

**Election is authoritative.** `route.py` enumerates only the packages listed in `rbtv.json` → `model_packages`, and (for a configurable package such as a multi-backend CLI) only the backends listed in `model_variants`. A package or backend absent from those lists is skipped at enumeration. When the lists are absent (e.g. a `--models-dir` override) no election filter applies.

The orchestrating skill recalls the elected (and therefore routable) set on demand by running `python {rbtv_path}/orchestration/models/route.py --availability`, which prints `{elected:[ids], not_elected:[ids]}` from `rbtv.json` `model_packages` filtered to packages present on disk — a **recall surface only**, not a routing input. Nothing is baked into the shared repo, so the recall cannot go stale. `route.py` reads election from `rbtv.json` for routing too; the `--availability` flag just exposes that election for the conductor to read.

---

## 8. Plan-size context caps

A deployment can cap a model's usable context below its true ceiling (e.g. a subscription tier). The cap file is **cap-only** — it carries `context_window` per model and nothing else (cost stays board-derived in the manifests).

- `rbtv.json` → `model_plans_file` points at the cap file (shape and fields: `model-plans-schema.md`; example: `model-plans-example.yaml`).
- `_apply_plan_caps()` sets each variant's effective window to `min(manifest context_window, plan cap)` — downward only.
- The file is never required: if the pointer is absent or the file is unreadable/unparseable, routing proceeds on the manifest windows unchanged.

---

## 9. Render pipeline — manuals are generated

A model's dispatch **manual** (`manual.md`) is composed by `render-manuals.py` from two sources — never hand-written:

- the shared wrapper template `orchestration/skills/orchestrating/cards/dispatch-wrapper.md` (the generic dispatch contract + render seams), and
- the model's `delta.md` (model-specific content; every delta must supply the `invocation` section).

Composition uses an HTML-comment marker grammar (`RENDER:BEGIN/END`, `RENDER:INSERT`, `RENDER:DELTA`). Rendering is deterministic (write-if-changed, no timestamps), so re-rendering unchanged inputs is byte-identical.

```
python orchestration/models/render-manuals.py            # regenerate all manuals
python orchestration/models/render-manuals.py --check     # report drift, write nothing; exit 1 if any manual is stale
```

`--check` must exit 0 (zero drift). To change a manual, edit the wrapper template (cross-model behavior) or the model's `delta.md` (model-specific behavior), then re-render — never edit `manual.md` directly.

---

## 10. Running the tests

**Canonical command (from the repo root):**

```
python -m pytest orchestration/models/test_route.py
```

**Gotcha — `python orchestration/models/test_route.py` collects ZERO tests** and exits 0 with no output. The suite's tests take pytest fixtures (`tmp_path`) and the file has no `if __name__ == "__main__"` block, so running it as a plain script merely loads the test classes without invoking anything. Always run it through `pytest`. (This silent no-op is the gap this document exists to close.)

The suite covers the reference profiles (fully/partially/unbounded), the boundedness keystone, determinism, API-key availability, plan caps (parse, apply, graceful skip), halt seams, self-execute, the `--explain` trace, failure modes, stakes/pinned-role floors, the Haiku guard, and a live-corpus enumeration.

---

## 11. Add or migrate a model

1. **Elect** the package: add it to `model_packages` in `rbtv.json` (run the installer's picker, or pass `--model-packages …`). For a multi-backend package, also set its `model_variants` subset.
2. **Author** `orchestration/models/{model}/manifest.yaml` from `manifest-template.yaml`, filling every required field with an evidence-traceable value per `manifest-schema.md`. Set the 1–7 axes from the external methodology used by all other models (keep them comparable).
3. **Write** `delta.md` with the model's dispatch specifics, including the required `invocation` section.
4. **Render** the manual: `python orchestration/models/render-manuals.py`, then confirm `--check` exits 0.
5. **Add/extend tests** in `test_route.py` for any new routing behavior.
6. **Run the suite:** `python -m pytest orchestration/models/test_route.py` — all green.
7. **Keep docs in sync** (repo hard rule): update `modules/orchestration.md`, the per-model reference tables in Part II below if a routable variant changed, and `admin/install/module-manifest.json` if a package was added/removed/renamed.

---

# Part II — Per-Model Reference Data

> **Reference data, NOT a router.** These are the per-model values the router reads and the conductor consults as a **within-tier tiebreaker** — never the master cut (boundedness-first stays the cut, per `skills/orchestrating/cards/routing.md`). Capability scores (`reasoning`/`coding`) and `cost` are integers 1–7 derived from one external methodology (the Artificial Analysis leaderboard — Intelligence Index + per-axis sub-tests for capability, Blended Price binned for cost). `routable_for` is an eligibility allow-list (absent ⇒ eligible for all leaves). **Model ids and prices are 2026 figures — re-verify against provider docs before relying on any specific id or price.** The DeepSeek and Gemini ids + prices were live-confirmed 2026-06-09.

## Anthropic Claude

| Model | reasoning | coding | cost | Context | Max Output | Price (blended) | reasoning_modes | evidence_status |
|-------|:---------:|:------:|:----:|---------|------------|------------------|-----------------|-----------------|
| Claude Fable 5 | 7 | 7 | 7 | 1M tokens | 128k | n/a (not on the AA board — owner-approved ceiling; premium tier, cost 7 ranks last on cost-ascending rank) | single-mode (effort not settable via Agent-tool) | validated (both carriers; CLI = effort-dial probe 2026-07-07, task-bearing dispatch unexercised) |
| Claude Opus 4.8 | 7 | 6 | 6 | 1M tokens | 128k | $3.85/MTok | single-mode (effort not settable via Agent-tool) | validated |
| Claude Sonnet 4.6 | 6 | 5 | 5 | 1M tokens | 64k | $2.31/MTok | single-mode (effort not settable via Agent-tool) | validated |
| Claude Haiku 4.5 | 3 | 2 | 3 | 200k tokens | 64k | $0.77/MTok | single-mode no-op | validated |

**CLI carrier (`claude-code-cli`):** same capability integers; adds the 5-level effort ladder (`low|medium|high|xhigh|max` via `--effort`) for fable, opus and sonnet. Fable's CLI-side effort ladder was probe-confirmed 2026-07-07 via two trivial `claude -p --model fable --effort low|max` dispatches (both `is_error:false`, `modelUsage.claude-fable-5`); a full task-bearing CLI dispatch remains unexercised. Haiku is a no-op single-mode even on the CLI. `cost` integers identical (board market price, no subscription discount).

**Capability:** Fable = premium senior-most tier (reasoning 7 / coding 7, ceiling on both axes) — the conductor and final-plan-reviewer pin target (opus falls back when fable is unavailable), never auto-picked on a cost tie (cost 7 ranks last in cost-ascending rank; reached ONLY via the conductor/final-plan-reviewer pins). Opus = frontier reasoning + strong agentic coding; Sonnet = strong reasoning; Haiku = fast/cheap volume tasks. No `routable_for` restriction — all four eligible for all leaves. `reasoning`/`coding` for Fable are owner-approved (Fable 5 is not on the AA leaderboard — no board data); Opus/Sonnet/Haiku `reasoning` source: Intelligence Index + GPQA/HLE cross-checks, `coding` source: Terminal-Bench Hard.

## DeepSeek (API)

| Variant | reasoning | coding | cost | reasoning_modes | routable_for | Price (blended) | evidence_status |
|---------|:---------:|:------:|:----:|-----------------|--------------|------------------|-----------------|
| v4-flash | 4 | 3 | 1 | `[off, on]` via `thinking` param | `[reasoning, text-synthesis, other]` | $0.06/MTok | validated |
| v4-pro | 5 | 4 | 1 | `[off, on]` via `thinking` param | `[reasoning, text-synthesis, other]` | $0.18/MTok | validated |

Ids + prices live-confirmed 2026-06-09. The legacy `deepseek-chat`/`deepseek-reasoner` compatibility aliases are removed — dispatch `deepseek-v4-flash`/`deepseek-v4-pro`, never the aliases.

**Capability:** API chat text-worker (OpenAI-compatible, JSON mode) — stateless text synthesis only; executes NO code in this dispatch. `coding` is the honest board score; code-ineligibility is carried by `routable_for` (omits the code roles), never by the coding integer. No native web. V4-Flash = cheapest text worker; V4-Pro = cheapest top-reasoning-tier text.

## Kimi (Moonshot AI)

| Variant | reasoning | coding | cost | Context | reasoning_modes | routable_for | Price (blended) | evidence_status |
|---------|:---------:|:------:|:----:|---------|-----------------|--------------|------------------|-----------------|
| kimi | 6 | 4 | 3 | 256k tokens | `[no-think, think]` via `--thinking`/`--no-thinking` | (all leaves) | $0.70/MTok | validated |

**Capability:** CLI code-executor — writes/edits files, runs scripts, commits locally; validated bounded-code executor. Resume via session id. 256k context; multimodal (text+image); thinking toggle. No `routable_for` restriction. Runs as a CLI code-executor in this workspace — NOT a chat API worker.

## Gemini (Google API)

| Variant | reasoning | coding | cost | reasoning_modes | routable_for | Price (blended) | evidence_status |
|---------|:---------:|:------:|:----:|-----------------|--------------|------------------|-----------------|
| 3.5-flash | 6 | 3 | 4 | `[off, on]` via `thinkingBudget` (0=off) | `[reasoning, text-synthesis, web-research, other]` | $1.31/MTok | validated |
| 3.1-flash-lite | 2 | 1 | 2 | `[off, on]` via `thinkingBudget` (0=off) | `[reasoning, text-synthesis, web-research, other]` | $0.22/MTok | validated |

Prices live-confirmed 2026-06-09; the manifest's `3.5-flash` / `3.1-flash-lite` variants map to `gemini-3.5-flash` / `gemini-3.1-flash-lite`.

**Capability:** API chat text-worker — carries native web access (search grounding; dispatch `--grounded` for the light-grounding web-research leaf). `coding` is the honest board score; code-ineligibility carried by `routable_for` (omits the code roles; `web-research` included — native grounding qualifies it for the research leaf). The ONLY `web_access: true` API chat worker.

## OpenAI (codex-cli)

> **ONE row per MODEL** — effort levels (`low|medium|high` via `model_reasoning_effort`) are the post-pin dial stored in `reasoning_modes`, NOT separate rows. `routable_for` absent = eligible for all leaves.

| Variant | reasoning | coding | cost | reasoning_modes | routable_for | Price (blended) | evidence_status |
|---------|:---------:|:------:|:----:|-----------------|--------------|------------------|-----------------|
| gpt-5.5 | 7 | 7 | 7 | `[low, medium, high]` via `model_reasoning_effort` | (all leaves) | $4.35/MTok | validated |
| gpt-5.4 | 6 | 6 | 5 | `[low, medium, high]` via `-m gpt-5.4 -c model_reasoning_effort` | (all leaves) | $2.19/MTok | validated |

**Capability:** CLI code-executor (`codex exec`) — separate-process execution, writes/edits files, runs commands, sandboxed. GPT-5.5: frontier on both axes. GPT-5.4: near-frontier reasoning; coding one below GPT-5.5. `cost` 7 for GPT-5.5 (priciest — ranks last on a cost tie); `cost` 5 for GPT-5.4. GPT-5.5 manifest `context_window`: 1M tokens (capped per-deployment via the plan-caps file). Routed via the `codex-cli` package (code execution) — NOT an API chat worker.

## Manus (API)

| Variant | reasoning | coding | cost | reasoning_modes | routable_for | evidence_status |
|---------|:---------:|:------:|:----:|-----------------|--------------|-----------------|
| manus-autonomous | 1 | 1 | 1 | `[]` none — server-side autonomous loop | `[web-research]` | validated |

**Capability:** Autonomous web-research agent — browser navigation, clicks, form-fill, full multi-step workflows; RESTful task API; per-task cost; ~5-min timeout. `routable_for: [web-research]` ONLY — dropped from every non-web-research leaf. Values are owner-sourced (not on the board); `cost: 1` is hardcoded (no board backing). Complement to LLMs for autonomous browser work, not a general-purpose substitute.

## Qwen Code CLI (multi-backend)

The `qwen-code-cli` package is a **CLI code-executor** running FOUR configured backends (OpenAI-compatible; `--auth-type openai -m <id>`, omit `-m` → `qwen3.6-plus`). ONE row per MODEL. Per-backend thinking depth is NOT controllable through the qwen-code CLI (`reasoning_modes.depths: UNKNOWN`, accepted-as-final).

| Variant | reasoning | coding | cost | Backend id | Context | Max Output | Price in/out | evidence_status |
|---------|:---------:|:------:|:----:|-----------|---------|-----------|---------------|-----------------|
| `qwen3.6-plus` | 5 | 4 | 2 | qwen3.6-plus | 1M | 65,536 | $0.28/$1.65 (0–256K band) | validated |
| `deepseek-flash` | 4 | 3 | 1 | deepseek-v4-flash | 1M | 384k | $0.14/$0.28 | validated |
| `deepseek-pro` | 5 | 4 | 1 | deepseek-v4-pro | 1M | 384k | $0.435/$0.87 | validated |
| `glm` | 5 | 4 | 3 | glm-5.1 | 204,800 | 131,072 | ~$0.98/$3.08 | validated |

**Capability:** CLI code-executor (NOT a chat worker) — writes/edits files, runs shells/tests, native `--worktree` isolation; `web_access: false` (route web research elsewhere). No `routable_for` restriction — all backends eligible for all leaves (they execute code). `deepseek-flash` = cheap workhorse (same DeepSeek V4 Flash model as `deepseek-api`, different ROLE — code executor vs text worker); `deepseek-pro` = deeper reasoning; `qwen3.6-plus` = native Qwen flagship; `glm` = model diversity.

## Quick-Decision Matrix

| Need | Package | Variant | Reason |
|------|---------|---------|--------|
| Maximum reasoning + coding | codex-cli | gpt-5.5 | reasoning 7 / coding 7 — frontier both axes |
| Deep reasoning, lower cost | claude-code-native | opus | reasoning 7 / coding 6 / cost 6 |
| Strong reasoning, balanced | claude-code-native | sonnet | reasoning 6 / coding 5 / cost 5 |
| Top open-weight reasoning | kimi-code-cli | kimi | reasoning 6 / coding 4 / cost 3 |
| Cheapest text synthesis | deepseek-api | v4-flash | reasoning 4 / cost 1; routable_for text only |
| Top-reasoning text synthesis | deepseek-api | v4-pro | reasoning 5 / cost 1; routable_for text only |
| Web-grounded lookup (light) | gemini-api | 3.5-flash | reasoning 6 / cost 4; native search grounding |
| Web-grounded cheapest | gemini-api | 3.1-flash-lite | reasoning 2 / cost 2; cheapest web-capable text |
| Autonomous multi-step browser | manus-api | manus-autonomous | routable_for: [web-research] only; per-task cost |
| Bounded code, cheapest CLI | qwen-code-cli | deepseek-flash | reasoning 4 / coding 3 / cost 1; 384k output |
| Bounded code, deeper reasoning | qwen-code-cli | deepseek-pro | reasoning 5 / coding 4 / cost 1 |
| Code-fleet model diversity | qwen-code-cli | glm / qwen3.6-plus | non-DeepSeek options |
| High volume, cheapest Claude | claude-code-native | haiku | reasoning 3 / coding 2 / cost 3 |

## Overlap Disambiguation — within-tier "use X / use Y"

These rows resolve specific worker overlaps. They are **within-tier tiebreakers only** — boundedness-first stays the master cut; consult a row only to break a tie between workers the boundedness tree already placed in the same tier. Each variant's positive "best at" line lives in its manifest `specialty` field; these rows state the BOUNDARY between two overlapping choices.

**DeepSeek-API vs codex-cli** — the cut is **text-synthesis vs code-execution**, enforced by `routable_for`. Route a TEXT leaf (synthesis/logic over inlined sources, no execution) to `deepseek-api` (cheapest capable text; its `routable_for` omits code roles). Route a leaf that **executes code** to `codex-cli` (sandboxed separate process); DeepSeek-API cannot receive a code leaf. Never route code to DeepSeek-API; never route pure text-synthesis to a costlier code-executing process when a text worker suffices.

**qwen-code-cli (DeepSeek/GLM backend) vs DeepSeek-API** — the qwen CLI can run the SAME DeepSeek V4 models, but as a different ROLE. **Does the task touch the filesystem or run tools? → qwen-code-cli (DeepSeek backend)** (tool-using code executor, no `routable_for` restriction). **Pure text in → text out? → deepseek-api** (stateless text synthesis; gate removes it from every code leaf).

**Gemini-grounding vs `rbtv-web-searching` vs Manus** — three web escalation levels by autonomy/rigor/cost. **Single grounded lookup → Gemini** (`--grounded`; the only `web_access: true` API chat worker). **Rigorous cited multi-source research → `rbtv-web-searching`** (the in-session path, always available even with no web-capable model installed; never an API chat worker for this). **Autonomous multi-step browser work → Manus** (`routable_for: [web-research]` only; per-task cost, minutes-scale). Match the level the task needs.

**claude-code-cli (process) vs Agent-tool Claude** — **default to Agent-tool Claude** (`claude-code-native:opus`/`sonnet`) — in-session sub-agent, no process overhead; does NOT natively load workspace rules (the parent inlines them) and CANNOT spawn sub-agents (the nesting wall). **Escalate to `claude-code-cli`** ONLY for a process boundary (the worker must itself drive CLI workers — sub-conducting) or native workspace-rule loading (a `claude -p` process auto-loads the cwd rules). Both are distinct `(model, variant)` pairs — never collapsed; same Claude budget either way (not cost arbitrage).

## Source Citations

- Anthropic: https://platform.claude.com/docs/en/about-claude/models/overview
- DeepSeek: https://api-docs.deepseek.com/quick_start/pricing , https://api-docs.deepseek.com/guides/thinking_mode
- Kimi: https://platform.kimi.ai/docs/models , https://platform.kimi.ai/docs/api
- Gemini: https://ai.google.dev/gemini-api/docs/models , https://ai.google.dev/gemini-api/docs/pricing
- OpenAI: https://platform.openai.com/docs/models
- Qwen: https://dashscope.aliyuncs.com/docs
- Manus: https://open.manus.ai/docs/v2/
