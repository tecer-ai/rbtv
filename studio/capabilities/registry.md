---
type: capability-registry
module: studio
created: 2026-06-09
status: active
---

# Studio Capability Registry

The single index a worker consults to discover and invoke any studio capability. This is a **module-internal index** — not a `.claude/` install. Workers reach it via the studio loop; it is not user-invocable as a standalone command until `p6-3`.

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
4. After `p5-4` alignment, both `built` rows will carry a uniform invocation interface; until then, follow their native `workflow.md` directly.

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
| **entry point** | Workflow: `studio/workflows/design-extraction/workflow.md` · Command loader: `studio/commands/design-extractor.md` (invocable as `/rbtv-design-extractor` once studio is in the install set; module-internal in v1) |
| **inputs** | A live site URL; access to a headed browser (Playwright via `browser-automation` infra) |
| **outputs** | `design-extraction/templates/design-brief.md` — narrative token summary · `design-extraction/templates/design-tokens.json` — structured per-token JSON with per-token source annotations (color / type / spacing / motion) |
| **spec / source pointer** | `studio/workflows/design-extraction/workflow.md` (native workflow; alignment to registry convention at `p5-4`) |

> **Note:** re-registered AS-IS at `p1-7`. Alignment to the uniform invocation interface (consistent field names, input/output contracts) happens at `p5-4`.

---

### 3. image→JSON

| Field | Value |
|-------|-------|
| **name** | image→JSON |
| **status** | `built` |
| **entry point** | Workflow: `studio/workflows/vision-to-json/workflow.md` · Command loader: `studio/commands/vision-to-json.md` (invocable as `/rbtv-vision-to-json` once studio is in the install set; module-internal in v1) |
| **inputs** | A single image file (screenshot, exemplar, or reference visual) |
| **outputs** | A strict JSON spec describing the image's visual elements + three regeneration prompts (Nano-Pro, Flux, Midjourney) for AI image generation from the spec |
| **spec / source pointer** | `studio/workflows/vision-to-json/workflow.md` (native workflow; alignment to registry convention at `p5-4`) |

> **Note:** re-registered AS-IS at `p1-7`. Alignment to the uniform invocation interface happens at `p5-4`.

---

### 4. extract-subtle-refs

| Field | Value |
|-------|-------|
| **name** | extract-subtle-refs |
| **status** | `planned` — built at `p5-1` |
| **entry point** | Not yet built. Will land at `studio/capabilities/extract-subtle-refs.md` (per the spec) |
| **inputs** | TBD per spec — expected: reference exemplars (motion / interaction samples or video captures) |
| **outputs** | TBD per spec — expected: structured extraction of motion/interaction references (timing, easing, transition patterns) usable by the art-direction beat |
| **spec / source pointer** | `1-projects/rbtv-evolution/design-module/design-module-v1-build/specs/subtle-refs-spec.md` |

---

### 5. image-gen

| Field | Value |
|-------|-------|
| **name** | image-gen |
| **status** | `planned` — built at `p5-2` |
| **entry point** | Not yet built. Will land at `studio/capabilities/image-gen.md` (per the spec); provider-pluggable interface, Gemini provider first |
| **inputs** | TBD per spec — expected: an image spec (likely from the image→JSON capability output) + provider selection |
| **outputs** | TBD per spec — expected: a generated image file via the selected provider |
| **spec / source pointer** | `1-projects/rbtv-evolution/design-module/design-module-v1-build/specs/image-gen-spec.md` |

> **Design note:** source-pluggable multi-provider interface. Add providers without rewrite. Gemini is the first concrete provider.

---

### 6. exemplar-screenshot capture

| Field | Value |
|-------|-------|
| **name** | exemplar-screenshot capture |
| **status** | `planned` — built at `p5-3` |
| **entry point** | Not yet built. Will land at `studio/capabilities/screenshot-capture.md` (per the spec) |
| **inputs** | TBD per spec — expected: a URL or local file path + capture parameters (viewport, timing) |
| **outputs** | TBD per spec — expected: a screenshot file suitable for use as a reference exemplar in the workspace reference set |
| **spec / source pointer** | `1-projects/rbtv-evolution/design-module/design-module-v1-build/specs/screenshot-capture-spec.md` |

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
