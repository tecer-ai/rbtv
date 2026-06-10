# docs-sync confirmation — prez-builder v1

**Dispatch:** ORCHESTRATOR DOCS-SYNC for prez-builder v1  
**Completed:** 2026-06-07  
**Verifier:** Kimi Code CLI

---

## Files touched

1. `html/slide-library/README.md` — created; concise convention overview, artifacts (spec, canonical engine, re-vendor tool, fixture library), adoption pointer.
2. `html/hypresent/README.md` — added Builder section (second static page, library pick, preset + scratch flows, pointer-events drag-reorder tray, assemble → `?file=` editor handoff, library-vendored engine relationship).
3. `html/hypresent/docs/spec/03-module-map.md` — added `server/builder_api.py` and the 7 `app/js/builder/*` modules with one-line purposes; updated File/Folder Tree.
4. `html/hypresent/docs/decision-log.md` — appended 7 decision rows (D20–D26) under a new *Prez-builder v1 decisions* section.
5. `html/hypresent/docs/build-log.md` — appended one Session-4 paragraph covering convention + engine + builder + migration.
6. `README.md` (repo root) — left untouched; it describes the `html` module at a high level and does not inventory its contents.

---

## Append-only verification

- `decision-log.md`: before = 73 lines, after = 88 lines, delta = +15 lines (section header + 7 decision rows + separators). **Zero lines removed.** All original content (D1–D19, Move/Resize reconciliation, A1–A12, Vendored Libraries) remains unchanged.
- `build-log.md`: appended only; no prior content modified.

---

## Root-file guard

- No files created at repository root.
- No files deleted.

---

## Citations verified against live files

- Builder section claims verified against:
  - `html/hypresent/app/builder.html`
  - `html/hypresent/app/js/builder/builder-main.js`
  - `html/hypresent/server/builder_api.py`
  - `html/hypresent/app/js/main.js`
- Decision rows D20–D26 cite `build-spec` sections and live file lines confirmed in:
  - `builder_api.py` (`_run_engine`, `--catalog-data --json`, `--slides ... --json`) → D21
  - `tray-sorter.js` (`pointerdown`/`pointermove`/`pointerup` + `requestAnimationFrame`) → D22
  - `previews.js` (`IntersectionObserver`, `MOUNT_CAP = 24`, LRU/in-view-protected eviction) → D23
  - `builder-main.js` (`encodeURIComponent(result.output)`) and `main.js` (`URLSearchParams(location.search).get("file")`) → D24
  - `convention-spec.md` ADX-13 → D25
  - `builder-main.js` (`body.lang = lang`) → D26
- `slide-library/README.md` references `docs/convention-spec.md`, `engine/assemble.py`, `engine/install-engine.py`, and `tests/fixture-library/`, all confirmed present on disk.
