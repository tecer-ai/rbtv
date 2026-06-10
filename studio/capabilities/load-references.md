---
type: capability
module: studio
created: 2026-06-10
status: active
---

# load-references

> v1's only shipped capability. Loads the project's reference set from the workspace path and halts on any missing or unannotated layer per the contract. This capability LOADS — it never authors or corrects reference content (D4).

**Workspace path:** `5-workbench/tecer-biz/brand/studio-references/`  
**Contract authority:** `studio/standards/reference-set-contract.md` — read it for layer definitions, file names, annotated-check logic, and all on-absence behavior.

---

## When to Invoke

Invoke this capability at the START of any beat that requires the reference set (beat-02-art-direction, beat-03-generate). Never proceed to beat execution until all four layers are confirmed present and annotated.

---

## Execution Procedure

Execute each step in order. Do not skip or parallelize.

### Step 1 — Load Layer 1: Tokens File

1. Read `5-workbench/tecer-biz/brand/studio-references/tokens.md` in full.
2. Check that each of the four token categories (`## Color`, `## Type`, `## Spacing`, `## Motion`) has at least one non-empty slot value (a slot reading `[empty …]` or blank counts as empty).
3. **HALT if:** the file is absent OR all slots in any category are empty. Name the missing layer as "tokens file". Stop — do not load remaining layers. Report to the owner and wait.
4. **On pass:** hold token values in working context. Note: if a downstream step needs JSON-formatted tokens, perform the conversion from the markdown values in context — never require the owner to author JSON.

### Step 2 — Load Layer 2: Exemplars

1. Read `5-workbench/tecer-biz/brand/studio-references/exemplars/manifest.md`.
2. Confirm the manifest contains at least one non-stub row (a row reading `*(empty …)*` does not count).
3. For each row in the manifest, note the filename and confirm the image file exists at `exemplars/{filename}` (or `exemplars/charts/{filename}` for chart-prefixed rows). A manifest row pointing to a missing file is treated as an absent exemplar.
4. **HALT if:** the manifest is empty (no real rows) OR zero image files are confirmed present. Name the missing layer as "exemplars". Stop — do not proceed. Report to the owner and wait.
5. **On pass:** hold the list of confirmed exemplar filenames in working context.

### Step 3 — Load Layer 3: Taste File

1. Read `5-workbench/tecer-biz/brand/studio-references/taste-file.md` in full.
2. For each confirmed exemplar filename from Step 2, check that `taste-file.md` contains a matching H3 heading (exact filename match, case-sensitive) with at least one non-template bullet.
3. **HALT if:** the taste file is absent, has no H3 sections, or has NO confirmed exemplar with a matching annotated H3 section. Name the missing layer as "taste file — unannotated". Stop — halt the art-direction beat to the owner. Report: "Taste file present but unannotated for [filename list]. Art-direction beat cannot proceed until the owner annotates these entries. (The `p3-gate` clears this halt for the GSMM run once annotations are in place.)" Wait.
4. **On pass:** hold the taste-file annotation content in working context, keyed by exemplar filename.

### Step 4 — Load Layer 4: Chart Exemplar

1. List files in `5-workbench/tecer-biz/brand/studio-references/exemplars/charts/`.
2. Identify the first image file present (PNG or JPG). Ignore `SLOT.md` and any non-image files.
3. **HALT if:** no image file is found. Name the missing layer as "chart exemplar". Stop — the chart beat is blocked. Report to the owner and wait.
4. **On pass:** hold the chart-exemplar image path in working context.

### Step 5 — Confirm All Layers Loaded

After all four steps pass, confirm to the calling beat:

```
Reference set loaded.
  Tokens:        tokens.md — [n] non-empty categories
  Exemplars:     [n] confirmed; [n] annotated in taste file
  Taste file:    [n] annotated exemplars
  Chart exemplar: [filename]
```

The calling beat may now proceed.

---

## Non-Authoring Boundary

This capability NEVER:
- Writes or edits `tokens.md`, `taste-file.md`, `exemplars/manifest.md`, or any image file
- Generates, guesses, or substitutes content for a missing or empty layer
- Infers brand tokens from training knowledge or web data
- Proceeds in any reduced-capability mode on a partial reference set

A partial reference set is not a degraded-mode reference set — it is an absent layer. HALT and surface the gap; the owner fills it.

---

## Registry Consistency

This file is the reference-LOADING capability (architecture §1.3 row 2 / §7 — v1's only shipped capability). It is DISTINCT from `studio/capabilities/registry.md` row 1 (`follow-tokens / brandbook`, a `convention` capability woven into the beats): row 1 CONSUMES this capability's output (its **inputs** field names "the tokens file ... loaded by the reference-loading capability"). Row 1's spec pointer references `studio/standards/reference-set-contract.md` for the token layer definition.

The registry carries no discrete row for `load-references` itself. The authoritative spec for this capability is THIS file plus `studio/standards/reference-set-contract.md`. Any update to the layer list, file paths, or on-absence behavior MUST update both this file and the contract simultaneously.
