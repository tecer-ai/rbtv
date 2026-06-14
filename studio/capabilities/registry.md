---
type: capability-registry
module: studio
created: 2026-06-09
status: active
---

# Studio Capability Registry

The single index a worker consults to discover and invoke any studio capability. This is a **module-internal index** — not a `.claude/` install. Workers reach it via the studio loop. The two reuse capabilities' commands (`/rbtv-design-extractor` and `/rbtv-vision-to-json`) are now installed as of 2026-06-10 (owner-approved at p6-checkpoint); the registry remains the discovery surface for workers; users may also invoke those commands directly.

---

## Invocation Convention

Every row in this registry carries these six fields. A worker can invoke a capability from the row alone — no other source is needed.

| Field | What it means |
|-------|--------------|
| **name** | The capability's human name |
| **status** | `convention` (beat-integrated, no discrete entry point) · `built` (workflow + command exist on disk, usable now) · `planned` (slot reserved; spec written; not yet built) |
| **entry point** | The discrete artifact to invoke: a command file (workers call via the `/rbtv-*` command loader, or directly read and follow the workflow), a workflow directory, or `n/a` for convention capabilities |
| **inputs** | What the worker must supply before invoking |
| **outputs** | What the capability produces |
| **spec / source pointer** | Where the authoritative spec or source workflow lives; for planned capabilities this is the spec file the building task targets |

**How a worker invokes from a row:**

1. Confirm `status` — if `planned`, the capability does not exist yet; do not proceed.
2. For `built`: read the **entry point** workflow's `workflow.md` fully, then follow it. Supply every item listed under **inputs**; expect every item listed under **outputs**.
3. For `convention`: the behavior is already woven into the beat that uses it — no separate invocation. See **spec / source pointer** for the governing beat file.
4. After the `p5-4` alignment, both reuse `built` rows carry the uniform invocation interface (entry point · inputs · outputs) — invoke them through it.

---

## Capability Rows

### 1. follow-tokens / brandbook

| Field | Value |
|-------|-------|
| **name** | follow-tokens / brandbook |
| **status** | `convention` — lives in the beats; not a discrete invocable tool |
| **entry point** | n/a — enforced within beat-02-art-direction and beat-03-generate |
| **inputs** | Tokens file at the workspace reference path (`5-workbench/tecer-biz/brand/studio-references/`) loaded by the reference-loading capability |
| **outputs** | Compliance: generated HTML uses only the project's token values; inconsistencies flagged as beat output; the module NEVER authors or corrects tokens |
| **spec / source pointer** | `studio/workflows/studio-loop/beats/beat-02-art-direction.md` (art-direction enforcement) · `studio/workflows/studio-loop/beats/beat-03-generate.md` (generation enforcement) · `studio/standards/reference-set-contract.md` (token layer definition) |

> **Hard constraint:** this capability enforces and flags — it NEVER authors or corrects brand tokens. Brandbook authoring is a permanent exclusion from this module.

---

### 2. extract-tokens-from-site

| Field | Value |
|-------|-------|
| **name** | extract-tokens-from-site |
| **status** | `built` |
| **entry point** | Command: `/rbtv-design-extractor` — installed as of 2026-06-10 (p6-checkpoint); invocable as a standalone `/rbtv-*` command OR via the loop by reading `studio/workflows/design-extraction/workflow.md` directly · Source command file: `studio/commands/design-extractor.md` |
| **inputs** | Target website URL · Output format selection (`brief` \| `tokens` \| `both`) · Runtime ability to navigate the live site and capture pages/screenshots |
| **outputs** | Design brief at `{output_folder}/design-brief-{slug}.md` (when `brief`/`both` selected) · Design tokens JSON at `{output_folder}/design-tokens-{slug}.json` (when `tokens`/`both` selected), with per-token source attribution (`dom` or `screenshot-sampled`) |
| **spec / source pointer** | `studio/workflows/design-extraction/workflow.md` · `studio/commands/design-extractor.md` |

---

### 3. image→JSON

| Field | Value |
|-------|-------|
| **name** | image→JSON |
| **status** | `built` |
| **entry point** | Command: `/rbtv-vision-to-json` — installed as of 2026-06-10 (p6-checkpoint); invocable as a standalone `/rbtv-*` command OR via the loop by reading `studio/workflows/vision-to-json/workflow.md` directly · Source command file: `studio/commands/vision-to-json.md` |
| **inputs** | One reference image file (path or attachment; PNG, JPG, WEBP, etc.) |
| **outputs** | Valid JSON file at the resolved output path (default `vision-to-json-{image-name}.json` in the resolved output folder) containing the strict schema plus three generator-ready regeneration prompts (`exact_prompt_for_nano_pro`, `exact_prompt_for_flux`, `exact_prompt_for_midjourney`) |
| **spec / source pointer** | `studio/workflows/vision-to-json/workflow.md` · `studio/commands/vision-to-json.md` |

---

### 4. extract-subtle-refs

| Field | Value |
|-------|-------|
| **name** | extract-subtle-refs |
| **status** | `built` (at `p5-1`; done-gate exercised + independently cold-verified 2026-06-10) |
| **entry point** | Usage doc: `studio/capabilities/extract-subtle-refs/extract-subtle-refs.md` (read it fully, then invoke) · CLI: `python studio/capabilities/extract-subtle-refs/extract.py` (run from the repo root) |
| **inputs** | `--url <URL>` (repeatable) · `--out <report.md>` (required) · `--json-out <report.json>` (optional) · `--headed` (optional debug flag) |
| **outputs** | Structured markdown report per URL with motion/interaction observations (pattern · element anchor · concrete values · note); optional JSON dump. Dead URLs exit non-zero; a report is written only when ≥1 URL succeeds |
| **spec / source pointer** | `./extract-subtle-refs/subtle-refs-spec.md` · usage doc above |

---

### 5. image-gen

| Field | Value |
|-------|-------|
| **name** | image-gen |
| **status** | `built` (at `p5-2`; done-gate exercised + independently cold-verified 2026-06-10 — live Gemini call exercised, quota resolved on the paid key, `--aspect` fixed 2026-06-12 (now uses `imageConfig.aspectRatio`); credential + error paths verified, fixture provider fully exercised) |
| **entry point** | Usage doc: `studio/capabilities/image-gen/image-gen.md` (read it fully, then invoke) · CLI: `python studio/capabilities/image-gen/generate.py` (run from the repo root) |
| **inputs** | `--prompt <text>` · `--out <path>` (format from extension: png/jpg) · `--provider gemini\|fixture` (optional, default gemini) · `--aspect <ratio>` (optional) · `--env-file <path>` (optional; key resolution = OS env `GEMINI_API_KEY` first, then the env-file path — never hardcoded) |
| **outputs** | Image file at the `--out` path. Missing key → exit 1 naming the env var, no file written; provider failure → exit 1 with provider reason on stderr, no partial file |
| **spec / source pointer** | `./image-gen/image-gen-spec.md` · usage doc above · `./image-gen/image-craft.md` (Designer prompt/style/when-to-propose craft) |

> **Design note:** source-pluggable multi-provider interface — adapters auto-discovered from `image-gen/adapters/` by filename; add a provider by dropping an adapter module, zero interface edits (proven via the `fixture` adapter). Gemini is the first concrete provider. Prompt-craft, style families, and when-to-propose heuristics live in the Designer craft guide `./image-gen/image-craft.md`.

---

### 6. exemplar-screenshot capture

| Field | Value |
|-------|-------|
| **name** | exemplar-screenshot capture |
| **status** | `built` (at `p5-3`; done-gate exercised + independently cold-verified 2026-06-10) |
| **entry point** | Usage doc: `studio/capabilities/screenshot-capture/screenshot-capture.md` (read it fully, then invoke) · CLI: `python studio/capabilities/screenshot-capture/capture.py` (run from the repo root) |
| **inputs** | `--url <URL>` (repeatable) · `--refs <reference-set-path>` (required) · `--viewport <WxH>` (optional, default 1440x900) · `--selector <css-selector>` (optional section capture) |
| **outputs** | PNG file(s) in `<refs>/exemplars/` (versioned `-v{N}` on filename collision — never a silent overwrite; page height capped at 16000px) + one manifest row per capture in `<refs>/exemplars/manifest.md` `## Exemplars` table (current behavior inserts new rows at the TOP — most-recent-first; most-recent-first ordering ruled keep, 2026-06-12). Dead URL → exit non-zero, no file, no manifest row |
| **spec / source pointer** | `./screenshot-capture/screenshot-capture-spec.md` · usage doc above |

---

### 7. load-references

| Field | Value |
|-------|-------|
| **name** | load-references |
| **status** | `built` (at `p2-12`; discrete row added at the capability wave per the p2-12 deferred follow-up — architecture §1.3/§7 list it as a distinct v1-shipped capability) |
| **entry point** | `studio/capabilities/load-references.md` (procedural capability — the agent reads it fully and executes its steps; no CLI) |
| **inputs** | The workspace reference-set path (`5-workbench/tecer-biz/brand/studio-references/`); layer definitions per `studio/standards/reference-set-contract.md` |
| **outputs** | All four reference layers (tokens · exemplars · subtle-refs · taste file) loaded into working context, each present-and-annotated per the contract; HALT naming the missing layer on any absence — it loads, never authors or corrects reference content (D4) |
| **spec / source pointer** | `studio/capabilities/load-references.md` · `studio/standards/reference-set-contract.md` (contract authority) |

---

## Registry Serialization (shared-file write order)

This file is written sequentially across the following tasks. NEVER write out of order.

| Slot | Task | What it adds |
|------|------|-------------|
| 1 | `p1-7` | All 6 rows + invocation convention (this file) |
| 2 | `p5-1` | Update row 4 (extract-subtle-refs) — `planned` → `built` |
| 3 | `p5-2` | Update row 5 (image-gen) — `planned` → `built` |
| 4 | `p5-3` | Update row 6 (exemplar-screenshot capture) — `planned` → `built` |
| 5 | `p5-4` | Update rows 2 + 3 (extract-tokens-from-site + image→JSON) — alignment to uniform invocation interface |

> **Slots 2–4 execution note (D6, 2026-06-10):** the capability wave ran `p5-1`/`p5-2`/`p5-3` as three PARALLEL workers with this registry REMOVED from their allowlists; each worker returned its row content (`registry_row` block) and the orchestration conductor wrote slots 2–4 serially in one sitting, plus the row-7 `load-references` addition deferred from `p2-12`. The serialization order above was honored; the writer changed (conductor, not the task workers). Slot 5 (`p5-4`) executed — rows 2 + 3 aligned to uniform invocation interface. |
