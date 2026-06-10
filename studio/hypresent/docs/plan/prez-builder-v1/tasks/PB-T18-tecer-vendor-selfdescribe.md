You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context. This task operates in the tecer-biz repo on the branch `slide-library-convention-migration` (after PB-T17).

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any step, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate by exact strings, NEVER line numbers.

# PB-T18 — tecer-biz: vendor the engine + author README-FOR-AGENTS + thin CLAUDE.md + regenerate catalog

## Objective
Vendor the RBTV engine into the tecer library, author the cold-agent self-description from the convention template, replace the tecer CLAUDE.md body with a thin pointer, and regenerate the catalog with the new engine. Implements convention-spec §9.1 (assemble.py / CLAUDE.md / catalog rows).

## FILE ALLOWLIST (all under 5-workbench/tecer-biz/slide-library/)
- ✎ modify `assemble.py` (REPLACE tecer's 440-line engine with the vendored RBTV engine via install-engine.py)
- ✎ modify `library.json` (the install-engine stamp sync)
- ✚ create `README-FOR-AGENTS.md`
- ✎ modify `CLAUDE.md` (replace the body with a thin pointer; preserve nothing of the old assembly workflow except the pointer)
- ✎ modify `catalog.html` (regenerate)
- ✗ do NOT touch manifest.md/presets.md/as-built.md (PB-T17 owns them).

## Precondition
- PB-T17 has converted the manifest (10-col), created `library.json`/`as-built.md`, vendored the cross-root PNG, and cleaned `presets.md`. The library is now spec-shaped EXCEPT it still carries tecer's OLD `assemble.py` and OLD `CLAUDE.md`, and has no `README-FOR-AGENTS.md`.
- The RBTV engine source is at (vault-relative) `3-resources/tools/rbtv/html/slide-library/engine/assemble.py` and the re-vendor tool at `3-resources/tools/rbtv/html/slide-library/engine/install-engine.py`.

## Steps

### (1) Vendor the engine (convention-spec §9.1 assemble.py row + §1.1)
Run the re-vendor tool against the tecer library:
`python 3-resources/tools/rbtv/html/slide-library/engine/install-engine.py --library 5-workbench/tecer-biz/slide-library`
This copies `engine/assemble.py` over `slide-library/assemble.py` AND syncs `slide-library/library.json` `engine_version` to the engine's `ENGINE_VERSION` (`1.0`). (Use the path that resolves on this machine — both the vault root and these subpaths exist.) `git -C 5-workbench/tecer-biz add slide-library/assemble.py slide-library/library.json` after.

### (2) Author README-FOR-AGENTS.md (convention-spec §9.1 CLAUDE.md row + §5.1 template)
Create `slide-library/README-FOR-AGENTS.md` from the convention-spec §5.1 template (the complete required content — the README's OWN `## 1`–`## 6` headings, NOT the spec's top-level sections). Fill the `{...}` placeholders with TECER specifics, porting tecer's MUST-step content (from the OLD `slide-library/CLAUDE.md` assembly workflow) into the matching README sections:
- §1 (What this library is): Tecer's reusable deck slides, brand/voice, audiences — NO client data.
- §2/§3/§4: use the template verbatim; the invocation is `python assemble.py --preset {name} --out {OUTPUT_PATH} [...]` / `--slides id1,id2,... --out {...}` (convention-spec §5.1 §4).
- §6 (judgment): port tecer's freshness rule (ready slides carry Tecer facts that drift — name WHERE the source of truth lives, e.g. the latest client/traction reality), the leakage rule (exemplars are READ never copied; client copy enters only the output), and the upstream rule (improvements to ready slides propagate back: fragment + manifest row + catalog regen + as-built `upstream` note). (convention-spec §5.1 §6 + §9.1 "leakage/freshness/upstream → section 6".)
Use the EXACT template structure from convention-spec §5.1 — do not invent sections; fill the placeholders.

### (3) Thin CLAUDE.md (convention-spec §9.1 + §5)
Replace the ENTIRE body of `slide-library/CLAUDE.md` with a one-line pointer:
```markdown
# CLAUDE.md — slide-library

Read `README-FOR-AGENTS.md` in this folder before assembling any deck. It is the
self-contained agent guide for this slide library.
```
Discard the stale "54 slides" count and the old workflow body (the manifest is the count — convention-spec §9.3). `git -C 5-workbench/tecer-biz add` the change (this is an EDIT, not a delete; do not `git rm`).

### (4) Regenerate the catalog (convention-spec §9.1 catalog row)
`python 5-workbench/tecer-biz/slide-library/assemble.py --catalog` — regenerates `catalog.html` with the new engine. `git -C 5-workbench/tecer-biz add slide-library/catalog.html` after.

## Acceptance criteria (self-verifiable)
1. `python 5-workbench/tecer-biz/slide-library/assemble.py --catalog-data --json` → ONE valid JSON object with `ok:true` and `catalog_data` carrying 57 slides + the tecer sections + the presets. (The vendored engine validates the converted tecer library — this is the proof the conversion + vendoring agree.) If `ok:false`, write the `errors` to BLOCKED and stop (do NOT edit manifest — that is PB-T17's file; surface the gap to the orchestrator).
2. `slide-library/library.json` `engine_version` == `1.0` (synced by install-engine).
3. `slide-library/assemble.py` byte-equals `3-resources/tools/rbtv/html/slide-library/engine/assemble.py` (it was vendored, not hand-edited).
4. `slide-library/README-FOR-AGENTS.md` exists and contains the README's `## 4. How to assemble` heading and the `python assemble.py --preset` invocation.
5. `slide-library/CLAUDE.md` body is the thin pointer (contains `Read \`README-FOR-AGENTS.md\``) and no longer contains `54 slide`.
6. `catalog.html` was regenerated (newer mtime; contains the catalog label-bar markup).

## Evidence file
Append to `5-workbench/tecer-biz/slide-library/docs/migration-validation.md` a `## PB-T18` section: the 6 acceptance results, INCLUDING the full `--catalog-data --json` `ok` value + slide count.

DONE means: engine vendored, README authored, CLAUDE.md thinned, catalog regenerated, the vendored engine reports `ok:true` on the converted tecer library, evidence written. Any failure → BLOCKED + stop.
