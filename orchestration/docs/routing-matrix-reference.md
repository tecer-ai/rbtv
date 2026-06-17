> **Reference data — NOT a router.** This is a within-tier tiebreaker the conductor may consult; it is NEVER the master routing cut (boundedness-first stays the cut, per `cards/routing.md`). Capability scores (`reasoning`/`coding`/`cost`) are integers 1–7 derived from the Artificial Analysis leaderboard (AA board) — see `value-derivation.md` for the full methodology and per-model evidence. `routable_for` is an eligibility allow-list (absent = eligible for all leaves). Model ids and prices are 2026 figures from the AA board and provider docs — **re-verify against provider docs before relying on any specific id/price.** EXCEPTION: the **DeepSeek (§2)** and **Gemini (§4)** ids + prices were **live-confirmed 2026-06-09** (p6-1 orchestrated pilot, two independent paid workers — D-exec-15); see each section's note.

# AI Provider Routing Matrix — Reference

## 1. Anthropic Claude

| Model | reasoning | coding | cost | Context | Max Output | Price (AA blended) | reasoning_modes | evidence_status |
|-------|:---------:|:------:|:----:|---------|------------|---------------------|-----------------|-----------------|
| Claude Opus 4.8 | 7 | 6 | 6 | 1M tokens | 128k | $3.85/MTok | single-mode (effort not settable via Agent-tool) | validated |
| Claude Sonnet 4.6 | 6 | 5 | 5 | 1M tokens | 64k | $2.31/MTok | single-mode (effort not settable via Agent-tool) | validated |
| Claude Haiku 4.5 | 3 | 2 | 3 | 200k tokens | 64k | $0.77/MTok | single-mode no-op | validated |

> **CLI carrier (`claude-code-cli`):** same capability integers; adds the 5-level effort ladder (`low|medium|high|xhigh|max` via `--effort`) for opus and sonnet. Haiku is a no-op single-mode even on the CLI. `cost` integers identical (board market price, no subscription discount — D11).

**Capability:** Opus = frontier reasoning + strong agentic coding; Sonnet = strong reasoning (Hard-Prompts cross-check raises it above the AA-II bin-5 anchor); Haiku = fast/cheap volume tasks. No `routable_for` restriction — all three eligible for all leaves. `reasoning` source: AA Intelligence Index + GPQA/HLE cross-checks + Hard-Prompts (Sonnet). `coding` source: AA Terminal-Bench Hard.

## 2. DeepSeek (API)

| Variant | reasoning | coding | cost | reasoning_modes | routable_for | Price (AA blended) | evidence_status |
|---------|:---------:|:------:|:----:|-----------------|--------------|---------------------|-----------------|
| v4-flash | 4 | 3 | 1 | `[off, on]` via `thinking` param | `[reasoning, text-synthesis, other]` | $0.06/MTok | validated |
| v4-pro | 5 | 4 | 1 | `[off, on]` via `thinking` param | `[reasoning, text-synthesis, other]` | $0.18/MTok | validated |

> **Live-confirmed 2026-06-09** (p6-1 pilot, D-exec-15): the ids + prices above are current. The legacy `deepseek-chat`/`deepseek-reasoner` compatibility aliases are **removed 2026-07-24 15:59 UTC** — dispatch `deepseek-v4-flash`/`deepseek-v4-pro`, never the aliases.

**Capability:** API chat text-worker (OpenAI-compatible, JSON mode) — stateless text synthesis only; executes NO code in this dispatch. `coding` is the honest AA Terminal-Bench Hard board score (D13 capability-vs-eligibility split) — code-ineligibility is carried by `routable_for` (omits `bounded-code`/`unbounded-code`), never by the coding integer. `routable_for: [reasoning, text-synthesis, other]` — no native web. V4-Flash = cheapest text worker; V4-Pro = cheapest top-reasoning-tier text.

## 3. Kimi (Moonshot AI)

| Variant | reasoning | coding | cost | Context | reasoning_modes | routable_for | Price (AA blended) | evidence_status |
|---------|:---------:|:------:|:----:|---------|-----------------|--------------|---------------------|-----------------|
| kimi | 6 | 4 | 3 | 256k tokens | `[no-think, think]` via `--thinking`/`--no-thinking` | (all leaves) | $0.70/MTok | validated |

**Capability:** CLI code-executor — writes/edits files, runs scripts, commits locally; validated bounded-code executor. Resume via session id. 256k context; multimodal (text+image); thinking toggle. `reasoning` 6: AA Intelligence Index 54 (top open-weight, GPQA 53). `coding` 4: Terminal-Bench Hard 44. No `routable_for` restriction. Note: kimi runs as a CLI code-executor in this workspace — NOT a chat API worker.

## 4. Gemini (Google API)

| Variant | reasoning | coding | cost | reasoning_modes | routable_for | Price (AA blended) | evidence_status |
|---------|:---------:|:------:|:----:|-----------------|--------------|---------------------|-----------------|
| 3.5-flash | 6 | 3 | 4 | `[off, on]` via `thinkingBudget` (0=off) | `[reasoning, text-synthesis, web-research, other]` | $1.31/MTok | validated |
| 3.1-flash-lite | 2 | 1 | 2 | `[off, on]` via `thinkingBudget` (0=off) | `[reasoning, text-synthesis, web-research, other]` | $0.22/MTok | validated |

> **Live-confirmed 2026-06-09** (p6-1 pilot, D-exec-15): the prices above are current and the model names ARE the live Gemini API ids (the `gemini-api` manifest's `3.5-flash` / `3.1-flash-lite` variants map to `gemini-3.5-flash` / `gemini-3.1-flash-lite`).

**Capability:** API chat text-worker — carries native web access (search grounding; dispatch `--grounded` for the light-grounding web-research leaf). `coding` is the honest AA Terminal-Bench Hard score (D13); code-ineligibility carried by `routable_for` (omits `bounded-code`/`unbounded-code`; `web-research` included — Gemini's native grounding qualifies it for the research leaf). 3.5 Flash = highest reasoning (AA II 55, GPQA 53); 3.1 Flash-Lite = cheapest (AA II 34). The ONLY `web_access: true` API chat worker.

## 5. OpenAI (codex-cli)

> **ONE row per MODEL** — effort levels (`low|medium|high` via `model_reasoning_effort`) are the post-pin dial stored in `reasoning_modes`, NOT separate rows (D6). `routable_for` absent = eligible for all leaves.

| Variant | reasoning | coding | cost | reasoning_modes | routable_for | Price (AA blended) | evidence_status |
|---------|:---------:|:------:|:----:|-----------------|--------------|---------------------|-----------------|
| gpt-5.5 | 7 | 7 | 7 | `[low, medium, high]` via `model_reasoning_effort` | (all leaves) | $4.35/MTok | validated |
| gpt-5.4 | 6 | 6 | 5 | `[low, medium, high]` via `-m gpt-5.4 -c model_reasoning_effort` | (all leaves) | $2.19/MTok (owner-supplied) | validated |

**Capability:** CLI code-executor (`codex exec`) — separate-process execution, writes/edits files, runs commands, sandboxed. `reasoning` 7 / `coding` 7 for GPT-5.5: AA II 57–60 + Terminal-Bench Hard 58–61 — frontier on both axes. `reasoning` 6 / `coding` 6 for GPT-5.4: reasoning raised via Hard-Prompts cross-check (Elo 1490 ≈ GPT-5.5's 1492 — near-frontier, D9); coding is owner-sourced "one below GPT-5.5's 7" (base 5.4 absent from board, D13/p1 re-review c3). `cost` 7 for GPT-5.5 (priciest — ranks last on cost tie); `cost` 5 for GPT-5.4 (blended $2.19 from owner-supplied prices via AA formula). GPT-5.5 manifest `context_window`: 1M tokens (capped per-plan at 200k in `model-plans.yaml`).

> **Note:** Routed via the `codex-cli` package (code execution) in this workspace — NOT built as an API chat worker. Each model's effort levels are the post-pin dial in `reasoning_modes`; only the MODEL-level capability is a routing input.

## 6. Manus (API)

| Variant | reasoning | coding | cost | reasoning_modes | routable_for | evidence_status |
|---------|:---------:|:------:|:----:|-----------------|--------------|-----------------|
| manus-autonomous | 1 | 1 | 1 | `[]` none — server-side autonomous loop | `[web-research]` | validated |

**Capability:** Autonomous web-research agent — browser navigation, clicks, form-fill, full multi-step workflows; RESTful task API; per-task cost; ~5-min timeout. `routable_for: [web-research]` ONLY — dropped from every non-web-research leaf (D13). Values are owner-sourced (Manus not on the AA board); `cost: 1` is owner-hardcoded (no board backing). Complement to LLMs for autonomous browser work, not a general-purpose substitute.

## 7. Qwen Code CLI (multi-backend, ModelStudio US)

The `qwen-code-cli` package is a **CLI code-executor** that runs FOUR configured backends via ModelStudio US (OpenAI-compatible; `--auth-type openai -m <id>`, omit `-m` → `qwen3.6-plus`). ONE row per MODEL (D6). Per-backend thinking depth is NOT controllable through the qwen-code CLI (G1 — closed as a known CLI limitation, p1 re-review c6); `reasoning_modes.depths: UNKNOWN` is accepted-as-final.

| Variant | reasoning | coding | cost | Backend id | Context | Max Output | Price in/out (reference) | evidence_status |
|---------|:---------:|:------:|:----:|-----------|---------|-----------|--------------------------|-----------------|
| `qwen3.6-plus` | 5 | 4 | 2 | qwen3.6-plus | 1M | 65,536 | $0.28/$1.65 (0–256K band) | validated |
| `deepseek-flash` | 4 | 3 | 1 | deepseek-v4-flash | 1M | 384k | $0.14/$0.28 | validated |
| `deepseek-pro` | 5 | 4 | 1 | deepseek-v4-pro | 1M | 384k | $0.435/$0.87 | validated |
| `glm` | 5 | 4 | 3 | glm-5.1 | 204,800 | 131,072 | ~$0.98/$3.08 | validated |

**Capability:** CLI code-executor (NOT a chat worker) — writes/edits files, runs shells/tests, native `--worktree` isolation; `web_access: false` (route web research elsewhere). No `routable_for` restriction — all backends eligible for all leaves (they execute code). `reasoning`/`coding` sourced from AA II and Terminal-Bench Hard per backend. `cost` sourced from AA Blended Price. `deepseek-flash` = validated cheap workhorse (same DeepSeek V4 Flash model as `deepseek-api`, different ROLE — code executor vs text worker); `deepseek-pro` = deeper reasoning at ~3× cost; `qwen3.6-plus` = native Qwen flagship; `glm` = model diversity. ModelStudio-US billing unconfirmed — prices are reference-provider-derived (validated 2026-06-10; key pre-provisioned in `~/.qwen/settings.json` — resolves in ANY session including conductor/unattended).

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

## Overlap Disambiguation — within-tier "use X when / use Y when"

These rows resolve the specific worker overlaps the owner cares about. They are **within-tier tiebreakers only** — boundedness-first (per `cards/routing.md` §2) stays the master cut; consult a row below ONLY to break a tie between workers the boundedness tree already placed in the same tier. Each variant's positive "best at" line lives in its manifest `specialty` field; these rows state the BOUNDARY between two overlapping choices.

### DeepSeek-API vs codex-CLI

| Use… | When |
|------|------|
| **DeepSeek API** (`deepseek-api:v4-flash` / `v4-pro`) | The leaf is **text synthesis / logic over inlined sources** — no code execution. `routable_for: [reasoning, text-synthesis, other]` (omits code roles) — the `routable_for` gate already removes it from every code leaf; it wins on a TEXT leaf as the cheapest capable. Cheapest text worker (v4-flash); cheapest top-reasoning-tier text (v4-pro). |
| **codex-cli** (`gpt-5.5` / `gpt-5.4`, effort set post-pin from `reasoning_modes`) | The leaf **executes code** — edits a work-dir, runs commands, needs a sandboxed separate process. codex-cli is a code-executing agent (no `routable_for` restriction); DeepSeek-API cannot receive a code leaf (its `routable_for` omits `bounded-code`/`unbounded-code`). Within the codex variants, pick by capability (gpt-5.5 = 7/7, gpt-5.5 = pricier cost 7; gpt-5.4 = 6/6 cost 5). |

Boundary: the cut is **text-synthesis vs code-execution**, enforced by `routable_for` — never route code to DeepSeek-API, never route pure text-synthesis to a costlier code-executing process when a text worker suffices.

### qwen-code-cli (DeepSeek/GLM backend) vs DeepSeek-API

The qwen CLI can run DeepSeek V4 models too (`-m deepseek-v4-flash`/`-m deepseek-v4-pro`) — the SAME models the `deepseek-api` package serves. They are different ROLES, never interchangeable.

| Use… | When |
|------|------|
| **qwen-code-cli** (`deepseek-flash` / `deepseek-pro` / `glm` / `qwen3.6-plus`) | The leaf **executes code or agentic work** — writes/edits files, runs shells/tests, uses the `agent`/MCP tools, `--worktree` isolation, post-run allowlist diff. The qwen CLI carries DeepSeek (and GLM, and native Qwen) as a TOOL-USING code executor. No `routable_for` restriction. |
| **DeepSeek API** (`deepseek-api:v4-flash` / `v4-pro`) | The leaf is **stateless text synthesis** — summarize/classify/rewrite/JSON over inlined sources, no filesystem or tool loop. `routable_for: [reasoning, text-synthesis, other]` — the gate removes it from every code leaf. Cheapest text worker. |

Boundary: **does the task touch the filesystem or run tools? → qwen-code-cli (DeepSeek backend). Pure text in → text out? → deepseek-api.** Same underlying DeepSeek V4 models, two different ROLES.

### Gemini-grounding vs rbtv-web-searching vs manus

| Use… | When |
|------|------|
| **Gemini** (`gemini-api:3.5-flash` / `3.1-flash-lite`) | A **single grounded lookup** — one search-grounded call, light not rigorous. The ONLY `web_access: true` API chat worker with `web-research` in `routable_for`. (Grounding is shipped — dispatch with `--grounded`.) |
| **`rbtv-web-searching`** (Agent-tool path) | **Rigorous multi-source research** — source evaluation, citations, cross-checking across many sources. The in-session web path, always available even when no web-capable model package is installed (routing §6 degrade). NEVER an API chat worker for this use. |
| **Manus** (`manus-api:manus-autonomous`) | **Autonomous multi-step browser work** — the agent must navigate, click, fill, and synthesize across pages on its OWN (multi-step data collection), not a single lookup. `routable_for: [web-research]` ONLY. Per-task cost, minutes-scale latency, raw-dump return. |

Boundary: **single grounded call (Gemini) → rigorous cited multi-source (rbtv-web-searching) → autonomous multi-step browser agent (Manus)** — three distinct web escalation levels differing in autonomy, rigor, and cost (routing §6). Match the level the task needs; do not pay Manus's per-task autonomy for a single lookup, and do not ask Gemini's single grounded call to do rigorous multi-source research.

### claude-code-cli (process) vs Agent-tool Claude

| Use… | When |
|------|------|
| **Agent-tool Claude** (`claude-code-native:opus` / `claude-code-native:sonnet`) | The **default** Claude carrier — an in-session sub-agent via the Agent tool. No process overhead, no auth pre-flight, no guidance-file dependency. Use for normal in-session dispatches. It does NOT natively load workspace `CLAUDE.md`/rules (the parent inlines them) and CANNOT spawn sub-agents (the nesting wall). |
| **claude-code-cli** (`claude-code-cli:opus` / `claude-code-cli:sonnet`) | A **process-boundary sub-conductor** is needed (the worker must itself drive CLI workers — the nesting wall forces a separate process), OR **native workspace-rule loading** is required (a `claude -p` process natively auto-loads the cwd `CLAUDE.md`/rules; the Agent-tool carrier does not). |

Boundary: **default to Agent-tool Claude; escalate to claude-code-cli ONLY for a process boundary (sub-conducting) or native workspace-rule loading.** Both are enumerated as distinct `(model, variant)` pairs by §2a — NEVER collapse the two Claude carriers into one entity (routing §4 "Two distinct Claude carriers"). Same Claude budget either way — neither is cost arbitrage.

## Source Citations

- Anthropic: https://platform.claude.com/docs/en/about-claude/models/overview
- DeepSeek: https://api-docs.deepseek.com/quick_start/pricing , https://api-docs.deepseek.com/guides/thinking_mode
- Kimi: https://platform.kimi.ai/docs/models , https://platform.kimi.ai/docs/api
- Gemini: https://ai.google.dev/gemini-api/docs/models , https://ai.google.dev/gemini-api/docs/pricing
- OpenAI: https://platform.openai.com/docs/models
- Qwen: https://dashscope.aliyuncs.com/docs
- Manus: https://open.manus.ai/docs/v2/ (the v2 API the client targets — `_api/clients/manus.py` base_url `https://api.manus.ai/v2`, D-exec-13)
- Value derivation methodology: `2-areas/rbtv/model-benchmarking/5b-routing-build/value-derivation.md`
