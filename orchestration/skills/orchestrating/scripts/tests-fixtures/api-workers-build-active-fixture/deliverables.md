# Deliverables Map - API Workers Build

> **Single index of every artifact this plan produces.**
>
> **Every agent working on this plan MUST:**
> 1. Read this file BEFORE starting any task — it tells you the exact path your output must land at.
> 2. UPDATE this file AFTER delivering — flip the Status to ✅ and confirm the Path matches what you produced.
>
> The synthesis task (`p6-compound`) reads this map + `decisions.md` + `learnings.md`. If an artifact lands somewhere this map doesn't list, the synthesis agent will miss it. The index being accurate is a hard dependency, not a courtesy.
>
> **Paths:** rbtv-repo files are shown vault-root-relative (`3-resources/tools/rbtv/…`); plan-internal files use `./`. Worker work-dir for build tasks = the rbtv repo (`3-resources/tools/rbtv/`).

---

## Phase 1 deliverables — Runner + DeepSeek

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p1-1 | Schema repurpose + api-key-availability prose | `3-resources/tools/rbtv/orchestration/models/manifest-schema.md` | ✅ committed d4d6e498 |
| p1-2 | Synchronous provider base | `3-resources/tools/rbtv/orchestration/models/_api/clients/base.py` | ✅ committed d4d6e498 |
| p1-3 | DeepSeek client | `3-resources/tools/rbtv/orchestration/models/_api/clients/deepseek.py` | ✅ committed d4d6e498 |
| p1-4 | Shared runner | `3-resources/tools/rbtv/orchestration/models/_api/run.py` | ✅ committed d4d6e498 |
| p1-5 | DeepSeek package (multi-variant) | `3-resources/tools/rbtv/orchestration/models/deepseek/{manifest.yaml,delta.md}` | ✅ committed d4d6e498 |
| p1-6 | Routing-matrix reference doc | `3-resources/tools/rbtv/orchestration/docs/routing-matrix-reference.md` | ✅ committed d4d6e498 |
| p1-checkpoint | DeepSeek pilot evidence + approval | `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/2026-06-08-api-deepseek-pilot.md` | ✅ PASSED + approved 2026-06-09 (builder 7/7 + cold-verify 6/6) |

## Phase 2 deliverables — Gemini + OpenAI

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p2-1 | Gemini client | `…/orchestration/models/_api/clients/gemini.py` | ✅ committed 678a453; opus-reviewed clean |
| p2-2 | Gemini package (multi-variant, web) | `…/orchestration/models/gemini/{manifest.yaml,delta.md}` | ✅ committed 678a453; opus-reviewed (delta grounding→deferred P5) |
| p2-3 | OpenAI client | ~~`…/_api/clients/openai.py`~~ | ⏸ deferred (OpenAI dropped — D1) |
| p2-4 | OpenAI package (multi-variant) | ~~`…/models/openai/`~~ | ⏸ deferred (OpenAI dropped — D1) |
| p2-checkpoint | Chat-**duo** pilot (DeepSeek+Gemini) evidence + approval | `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/2026-06-09-api-chat-duo.md` | ✅ PASSED + approved 2026-06-09 (builder 6/6 + cold-verify 5/5 AGREE; gemini-2.5-flash; grounding deferred P5) |

## Phase 3 deliverables — Deterministic routing + Claude-tier modeling

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p3-1 | Agent-tool Claude package | `…/orchestration/models/claude/{manifest.yaml,delta.md}` | pending |
| p3-2 | Routing card: selector + carrier + API hooks | `…/orchestration/skills/orchestrating/cards/routing.md` | pending |
| p3-3 | Intake card: pair-enumerated budget summary | `…/orchestration/skills/orchestrating/cards/intake.md` | pending |
| p3-checkpoint | Determinism + no-collapse evidence + approval | `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/2026-06-09-deterministic-routing.md` | pending |

## Phase 4 deliverables — Wire into the conductor

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p4-1 | Dispatch-wrapper: API transport row | `…/orchestration/skills/orchestrating/cards/dispatch-wrapper.md` | ✅ committed 9c0bbaa; opus-reviewed (heading two→multiple fixed); hunk-isolated from mirror's §2 row |
| p4-2 | Verification: lighter text gate | `…/orchestration/skills/orchestrating/cards/verification.md` | ✅ committed 9c0bbaa; opus-reviewed (§1d↔§2 content-review contradiction fixed across 5 touchpoints) |
| p4-3 | Core-protocol: capability roster | `…/orchestration/skills/orchestrating/core-protocol.md` | ✅ committed 9c0bbaa; §1-certified (recall-only); hunk-isolated from mirror's ORCH:AVAILABILITY hunk |
| p4-4 | Installer: env_file preserve + record (idempotent) | `3-resources/tools/rbtv/admin/install/installer/{state.py,cli.py}` (RE-SCOPED ADX-2 — `install.py` is a bootstrap; logic is here) | ✅ committed a298702; opus-reviewed CLEAN; preserve/record/override + --mirror-preserve verified; availability-bake (orchestration.py) already-built, not touched |
| p4-5 | `.env.example` key names (vault-side, inline) | `.user/config/env/.env.example` | ✅ committed 39a7529b (VAULT, branch main); 3 keys DEEPSEEK/GEMINI/MANUS (no openai/D1) |
| p4-6 | Rendered manuals (verify-only) | `…/orchestration/models/{deepseek,gemini,claude}/manual.md` + re-rendered existing | ✅ VERIFIED zero-diff: `render-manuals.py --check` EXIT 0 = 8 manuals fresh/unchanged. NOT committed by api-workers — manuals are mirror's PAUSED uncommitted footprint (mirror commits on resume) |
| p4-7 | Docs-sync (README + module + manifest) | `3-resources/tools/rbtv/{readme.md, modules/orchestration.md, admin/install/module-manifest.json}` | ✅ committed 342346d (BUILD-BLOB isolated from mirror's hunks; manifest +deepseek/gemini/claude, NO openai/manus; modules+readme API-worker prose). §1 conductor-certified (non-dev docs) |
| p4-checkpoint | Conductor-integration evidence + approval | `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/2026-06-09-conductor-integration.md` (+ `/_coldverify/`) | ✅ APPROVED 2026-06-09 — 6/7 HELD (builder + cold-verify AGREE); crit 7 = USER-EXECUTED install (owner UAT pending). **PHASE 4 CLOSED.** |

## Phase 5 deliverables — Manus agentic worker

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p5-1 | Manus agentic client | `…/orchestration/models/_api/clients/manus.py` | ✅ 9c5d5c9 (initial) → **11dcb38 (rewritten to Manus API v2, VALIDATED live)**; opus-reviewed both |
| p5-2 | Manus package (agentic profile) | `…/orchestration/models/manus/{manifest.yaml,delta.md}` | ✅ 9c5d5c9 + **11dcb38** (synced to v2; `evidence_status: validated`); opus-reviewed (3rd §2a agentic-web block, ADX-3) |
| p5-3 | run.py: generic agentic handling | `…/orchestration/models/_api/run.py` | ✅ committed **4d9a524** (`--timeout` + generic `--grounded`/`--extra-params`, ADX-1); conductor-diff-reviewed (cross-client None-safety) |
| p5-4 | Routing: autonomous-web leaf | `…/orchestration/skills/orchestrating/cards/routing.md` | ✅ committed **f115cac** (§6 three-tier web; §2/§2a keystone byte-identical, D-exec-9c); opus-reviewed (qwen `web_access:false` defect fixed → D-exec-11) |
| p5-5 | Verification: Manus latency/cost note | `…/orchestration/skills/orchestrating/cards/verification.md` | ✅ committed **8b48e83** (§1b agentic WALL_MS calibration + per-task cost note); conductor-diff-reviewed |
| p5-6 | Docs-sync for Manus | `3-resources/tools/rbtv/{readme.md, modules/orchestration.md, admin/install/module-manifest.json}` | ✅ committed **c9fbff7** (BUILD-BLOB isolated from mirror's co-resident hunks); §1 conductor-certified (non-dev docs) |
| p5-7 | Manus manual (render run) | `…/orchestration/models/manus/manual.md` | ✅ rendered v2 (`render-manuals.py --model manus`); **UNCOMMITTED — rides the mirror's resume commit** (like the other API-worker manuals) |
| p5-checkpoint | Manus pilot evidence + approval | `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/2026-06-09-manus-pilot.md` (+ `/-v2/` captures) | ✅ **VALIDATED + owner-approved 2026-06-09**. The v1 pilot exposed that the source client used a WRONG/outdated API (D-exec-12 → D-exec-13: real API is `api.manus.ai/v2` + `x-manus-api-key`); `manus.py` rewritten to v2 (`11dcb38`); v2 re-test HELD (real task create→poll→output, key-safe). Crit 2 = **held-surprising** (captured agent narration, not the file-artifact report — D-exec-14; owner ACCEPTED). `evidence_status: validated`. **PHASE 5 CLOSED.** |

## Phase 6 deliverables — Live orchestrated pilot + close

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p6-1 | Live-pilot evidence + earn-their-keep verdict | `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/2026-06-09-orchestrated-pilot.md` (+ `/2026-06-09-orchestrated-pilot/` captures) | ✅ ALL 6 criteria HELD (crit 2 with the Manus supplementary-section review-FAIL surfaced). 3 paid calls (deepseek:v4-flash digest DONE · gemini:3.5-flash --grounded first-live-firing WORKS · manus ~3min report in message text); §2a traces + §1 gates + batched opus §2 review (digest PASS-WITH-NOTES · Manus FAIL on supplementary §2 · Gemini PASS); Gemini⊕Manus cross-check AGREE 6/6; key-leak 0/0/0. Seam verdict: deepseek + gemini EARN KEEP; Manus MIXED (lost this leaf on value-per-dollar). Discovery D-exec-15 (deepseek-chat deprecates 2026-07-24; live ids confirmed). |
| p6-refs | Link-check result + fixes | `./` (in-place) | ✅ 1 broken path fixed (`deliverables.md` p1-checkpoint garbled prefix); 0 PLS violations; all 31 arrow-refs resolve; all 33 task files referenced |
| p6-compound | Compound PRDs (if any) + processed learnings | `.user/compounds/rbtv-orchestrating/` + `./learnings.md` | ✅ 2026-06-09 — 4 PRDs created A–D (manus-message-text-prompt-shaping · cross-tier-corroboration-web-content · routable-carrier-must-be-manifested · variant-field-count-discipline); L1 deferred (folds into cli-flag-existence-preflight when user-validated); L3 already-resolved in-plan; both seeds confirmed |
| p6-checkpoint | Final approval + exit scorecard | `./decisions.md` → D-exec-16 + `./run-log.md` → Exit Scorecard | ✅ **OWNER APPROVED 2026-06-09 (option A). PLAN COMPLETE PENDING USER ACTION** (crit-7 install with owner). All 6 criteria PASS; follow-ons captured in `1-projects/rbtv-evolution/rbtv-evolution-tasks.md` + 4 compound PRDs tracked in `2-areas/compounds/compounds-tasks.md`. **RUN CLOSED.** |

**Status values:** `pending` | `in-progress` | `✅` | `⏸ deferred` — deferrals carry a parenthetical reason in the cell.

---

## How the synthesis task consumes this index

A fresh agent at `p6-compound` reads, in order:

1. **This file (`deliverables.md`)** — the artifact index.
2. `./decisions.md` end-to-end — every Decision and Discovery; the running rationale.
3. `./learnings.md` — the queue + the two candidate seeds.
4. Each pilot's evidence sheet under `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/`.

`p6-compound` folds compound-ready learnings into PRDs under `.user/compounds/orchestration/`; `p6-checkpoint` assembles the exit scorecard from the evidence sheets.

---

## Sub-folder creation

`specs/` holds the three behavior specs (pre-created). `phase-{1..6}/` hold the task files (pre-created). Done-gate evidence sub-folders under `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/{date}-{feature}/` are created on demand by the first pilot that needs them — never pre-created empty.
