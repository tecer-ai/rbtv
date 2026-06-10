---
type: standard
module: studio
created: 2026-06-10
status: active
---

# Reference-Set Contract

> Defines the four layers the workspace MUST supply before any design beat runs. The studio module LOADS and ENFORCES this contract; it NEVER authors or ships reference content (D4). Workspace path: `5-workbench/tecer-biz/brand/studio-references/`.

---

## Workspace Path

All four layers live under one workspace-owned folder:

```
5-workbench/tecer-biz/brand/studio-references/
├── tokens.md
├── taste-file.md
├── exemplars/
│   ├── manifest.md
│   └── {exemplar-image-files}
└── exemplars/charts/
    └── {chart-image-file}
```

**Do not rename files or restructure this folder** without updating this contract and `studio/capabilities/load-references.md`.

---

## The Four Required Layers

### Layer 1 — Tokens File

| Field | Value |
|-------|-------|
| **File** | `tokens.md` (markdown, owner-curated) |
| **Content** | Color, type, spacing, and motion tokens for the project's brand system — one H2 section per category: `## Color`, `## Type`, `## Spacing`, `## Motion` |
| **Token form** | Owner-readable markdown with explicit values per slot. The `extract-tokens-from-site` capability (`studio/capabilities/registry.md` row 2) can populate this file from a live site. If the capability's JSON output (`design-extraction/templates/design-tokens.json`) is ever needed as a downstream input, the consuming capability performs the conversion — the owner never authors JSON directly. |
| **Completeness check** | A slot is considered EMPTY if its value reads `[empty …]` or is blank. A file with all slots empty is treated as absent. |
| **On absence** | HALT — name the missing layer as "tokens file" and stop all beat execution. Never proceed on training-mean defaults. |

---

### Layer 2 — Exemplars

| Field | Value |
|-------|-------|
| **Folder** | `exemplars/` |
| **Content** | World-class exemplar screenshots (PNG/JPG) curated by the owner. At least one image file must be present. |
| **Manifest** | `exemplars/manifest.md` — one row per image file; the module reads the manifest to enumerate exemplars. An exemplar image with no manifest row is treated as unannotated. |
| **On absence** | HALT — name the missing layer as "exemplars" (no image files in `exemplars/`) and stop all beat execution. |

---

### Layer 3 — Taste File

| Field | Value |
|-------|-------|
| **File** | `taste-file.md` |
| **Content** | One H3 section per exemplar listed in `exemplars/manifest.md`. Each section heading matches the exemplar filename exactly (case-sensitive; chart exemplars prefixed `charts/`). Each section carries 3–5 specific, named admirable-principle bullets. |
| **Annotated check** | A taste file with no H3 sections, or with every H3 section containing only template-example content, is treated as unannotated. An exemplar whose filename has no matching H3 in `taste-file.md` is considered unannotated for that file. |
| **On absence or unannotated** | The art-direction beat (beat-02) HALTS to the owner — never substitutes model taste silently. This is not an error the module corrects; it is an owner-curation gap. The `p3-gate` clears this halt for the GSMM run once the owner annotates the file. |

---

### Layer 4 — Chart Exemplar

| Field | Value |
|-------|-------|
| **Folder** | `exemplars/charts/` |
| **Content** | At least one chart-slide image file (PNG/JPG) — the visual bar for data communication in this project. The module reads the first image file in the folder (ignoring `SLOT.md` and any non-image files). |
| **On absence** | HALT — name the missing layer as "chart exemplar" and block the chart beat. A folder containing only `SLOT.md` (no image files) is treated as absent. |

---

## On-Absence Behavior Summary

| Layer | Missing means | Module action |
|-------|--------------|---------------|
| Tokens file | File absent OR all slots empty | HALT — name "tokens file"; never use training-mean defaults |
| Exemplars | No image files in `exemplars/` | HALT — name "exemplars" |
| Taste file | File absent, unannotated, or no matching H3 for any exemplar | HALT (art-direction beat) to owner; never substitute model taste |
| Chart exemplar | No image files in `exemplars/charts/` | HALT — name "chart exemplar"; chart beat blocked |

The module NEVER proceeds past a HALT. A partial reference set is not a degraded-mode reference set — it is an absent layer.

---

## Scope

This contract binds `studio/capabilities/load-references.md` (the v1 capability that loads and checks all four layers) and every beat that consumes the reference set (`beat-02-art-direction.md`, `beat-03-generate.md`). Read `studio/capabilities/load-references.md` for the invocation procedure.
