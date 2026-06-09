# Spec — Deck Recompose Save

## Goal

The owner can save a restructured deck from the builder — the deck's own slides reordered/removed/duplicated, with library slides and blanks spliced in — to a new file or over the original, and the saved file opens as a working presentation with its theme, scripts, and untouched slides preserved byte-for-byte.

## Context Snapshot

**Why a new path exists:** the library engine (`assemble.py`, invoked via `_run_engine` in `server/builder_api.py`) rebuilds a deck from `base.html` + blank library fragments — running it on a filled deck would wipe its content (ADX-2 forbids re-implementing it; this path manipulates a finished deck instead). The editor's serializer is a live-DOM strip pass, not available server-side.

**Deck shape:** a standalone HTML file; slides are top-level `<section>` elements (the slide-library system's own output — see `docs/spec/02-html-convention.md` §4: regions are direct children of the content root that are sectioning elements). The deck's theme is inlined in `<head>`; it may carry its own `<script>` blocks and inline SVG.

**Existing write idiom** (`server/api.py`, `handle_save_as`): payload `{path, html}` → writes with `target.write_text(html, encoding="utf-8")`, refuses if parent dir missing, returns `(200, {"ok": True, "path": path_str})`. Errors return `(500, {"error": ...})`. Handlers are pure `(status:int, dict)` tuples — no HTTP logic.

**Library fragments** are served by `handle_library_asset` (`server/builder_api.py`): payload `{path: libraryPath, name: "slides/{id}.html"}` → `{"content": ...}`. Fragments carry no inline style and may reference relative assets (e.g. `assets/logo.png`); the assembler copies referenced assets today — this path must too.

**New modules:**
- `server/recompose.py` — pure functions, stdlib only, no HTTP:
  - `split_sections(html: str) -> list[tuple[int, int]]` — byte spans `(start, end)` of each TOP-LEVEL `<section>…</section>` in the document, in order. Depth-counts nested `<section>` tags; ignores tags inside HTML comments (`<!-- -->`).
  - `recompose(html: str, items: list[dict]) -> str` — rebuilds the document: prefix (everything before the first section) + the items' markup in order + suffix (everything after the last section). Items: `{"kind": "existing", "index": int}` (the source deck's Nth section span, copied verbatim — a repeated index duplicates it), `{"kind": "fragment", "html": str}` (library fragment, inserted as a `<section>` as-is), `{"kind": "blank"}` (a plain placeholder `<section>` with minimal editable content, no `hyp-`/`data-hyp-*` markers).
- `server/deck_api.py` — handlers `handle_deck_load`, `handle_deck_save`, `handle_dialog_save_path` (native Save dialog returning the chosen path WITHOUT writing — reuses `_launch_dialog("save")` from `server/api.py`, injectable for tests via the existing `set_dialog_launcher` seam).

**`/api/deck-save` contract:** payload `{"source_path": str, "out_path": str, "items": [...], "libraries": {"<libraryPath>": true}}` where fragment items carry `{"kind": "library", "library_path": str, "slide_id": str}` (the handler fetches each fragment file itself, then maps to recompose `fragment` items). Response `{"ok": true, "path": out_path, "assets_copied": [...]}`.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | `/api/deck-save` with items reordering the source deck's sections | Written file has sections in the new order; everything outside the moved spans (head, theme, scripts, inter-slide markup) is byte-identical to the source |
| 2 | Items omit a section index | That slide is absent from the written file; all other content intact |
| 3 | Items repeat a section index | The written file contains that section's markup twice |
| 4 | Items include a library fragment | The fragment's markup appears as a `<section>` at its position, unmodified (no theme reconciliation) |
| 5 | A spliced fragment references relative assets (e.g. `assets/x.png`) present in its library | Those asset files are copied into the out file's folder preserving relative paths; response lists them in `assets_copied` |
| 6 | Items include a blank | A plain `<section>` placeholder appears at that position; it contains NO `hyp-` classes or `data-hyp-*` attributes |
| 7 | `out_path` equals `source_path` | The deck is overwritten in place (read fully before write) |
| 8 | The written deck is opened in a browser | It renders and its own scripts run without console errors caused by the recompose |

## Edge Cases & Error Behavior

| Case | Required behavior |
|------|-------------------|
| Source deck has zero top-level `<section>`s | `(500, {"error": "no <section> slides found — not a conforming deck"})`; nothing written |
| `section` tags inside HTML comments | Not counted as boundaries |
| Nested `<section>` inside a slide | Depth counting keeps the outer span whole; inner sections never split |
| Item index out of range | `(500, {"error": ...})`; nothing written |
| Library fragment file missing | `(500, {"error": ...})`; nothing written (all-or-nothing save) |
| Asset name colliding with an existing file in the out folder | Existing file is NOT overwritten; the collision is reported in the response (`assets_skipped`) |
| Out parent directory missing | Same refusal as `handle_save_as` |

## Out of Scope

- Provenance markers, library round-trip, theme merging.
- Editing slide content (the editor owns that).
- Non-`<section>` deck formats (best-effort is NOT required to work; the error path above is the contract).

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Reordered save preserves the deck | `pytest tests/test_recompose.py` — fixture copied from a real root deck; reorder via the API; diff untouched spans | Untouched spans byte-identical; sections reordered; exit 0 | pytest output log |
| 2 | Remove + duplicate work | Same suite: items omitting one index and repeating another | Written file reflects both; exit 0 | pytest output log |
| 3 | Fragment + blank splice with assets | `pytest tests/test_deck_api.py` against the e2e fixture library (`tests/e2e/fixtures/builder-lib/`) | Fragment section present verbatim; blank marker-free; referenced assets copied | pytest output log |
| 4 | Saved deck opens clean | Open the recomposed copy of a real root deck in a headed browser | Renders; zero console errors attributable to recompose | screenshot + console log capture |
| 5 | Overwrite-in-place | deck-save with `out_path == source_path` on a temp copy | File rewritten correctly; original root deck NEVER touched | pytest output log |

> Every criterion obeys the **Fidelity floor** + **Evidence plausibility** rules: real app, owner's real deck copies, evidence files written during the exercise; implausibly fast e2e timings are auto-reject + rerun.

**Fidelity floor for every criterion:** the real application running whole, on the owner's real data when one exists; UI criteria use a visible browser + real input, never synthetic `dispatchEvent`. Evidence is a file on disk written DURING the exercise. A genuinely undriveable criterion is marked `unexercisable` with the concrete blocker.

## Return Expectations

Files changed, validation commands run + exit codes + any skips with reasons, local commit hash if committed, concerns, blockers. The report is a hint; the repo state is the truth.

---

> **ADX-2 (run erratum, 2026-06-09) — `recompose` function contract corrected; supersedes the Context Snapshot sketch above.**
> The Context Snapshot's `recompose` description ("prefix + the items' markup in order + suffix") contradicts Behavior row 1 ("inter-slide markup … byte-identical") and the shaping decision ("raw spans preserve the deck byte-for-byte outside the spliced edits"). The Behavior row and shaping decision are authoritative. Corrected contract:
>
> `recompose(html, items)` rebuilds the document as `prefix + item₀ + sep(item₀) + item₁ + sep(item₁) + … + itemₙ₋₁ + suffix` — separators between items, none after the last item. Where: source separators `sep[i] = html[end_of_section_i : start_of_section_i+1]`; `sep(item)` for an `existing` item with source index `i < n-1` is `sep[i]` (its own trailing separator travels with it); for an `existing` item that was the source's LAST section, or a `fragment`/`blank` item, it is the deck's DEFAULT separator (the most common source separator string, ties broken by first occurrence in document order; `"\n"` when the deck has fewer than 2 sections).
> Consequence: an identity recompose (all sections, source order) reproduces the source **byte-for-byte, in full**.
