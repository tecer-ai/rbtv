# OSS Building Blocks — Hypresent WYSIWYG Editor

Research date: 2026-06-03

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1–10 | Threshold: TS ≥ 6

---

## Category 1 — On-Canvas Element Select + Drag-Resize Handles

| Library | Repo | License | Last Release | Stars | Bundle (min+gz) | Fit/Risk |
|---------|------|---------|-------------|-------|-----------------|----------|
| **Moveable** | https://github.com/daybrush/moveable | MIT | v0.53.0 — 2023-12-03 | ~10.5k | ~85 kB min / ~30 kB gz (est.) | Best-fit: visual handle system purpose-built for WYSIWYG-style resize/drag; single-author maintenance risk, last npm publish Dec 2023 |
| **interact.js** | https://github.com/taye/interact.js | MIT | v1.10.27 — 2024-03 | ~12k | ~70 kB min / ~25 kB gz (est.) | Mature, framework-agnostic drag+resize without visual handles; dev must build handle chrome manually; low-commit cadence since 2022 |
| **subjx** | https://github.com/nichollascarter/subjx | MIT | v1.1.2 — 2025-10-13 | ~200 | ~30 kB min | Lightweight drag/resize/rotate; SVG + HTML; small community but actively patched as of Oct 2025 |
| **neodrag** | https://github.com/PuruVJ/neodrag | MIT | 2024 | ~4k | ~3 kB gz | Drag only — no resize handles; unsuitable as primary pick for this use case |

**Recommendation:** **Moveable** (MIT) — only library with production-grade visual handles including resize corners/edges and snapping that matches PowerPoint-style UX out of the box. Maintenance gap (no release since Dec 2023) is a risk but the library is stable and can be vendored as-is. If maintenance is a blocker, **subjx** is an actively-patched lighter alternative with acceptable feature coverage.

**Safety:** Moveable MIT license, 10.5k stars, solo maintainer (daybrush), no known supply-chain flags. Subjx MIT, small but active.

---

## Category 2 — Inline Rich-Text / Contenteditable Formatting

| Approach | Repo / Spec | License | Bundle | Fit/Risk |
|----------|-------------|---------|--------|----------|
| **Raw contenteditable + execCommand** | MDN [1] | N/A (browser API) | 0 kB | execCommand is deprecated-in-spec but Chrome/Firefox support it through at least v147 [2]; undo buffer is preserved natively; covers bold/italic/fontSize; zero dependencies |
| **Quill 2** | https://github.com/slab/quill | BSD-3 | ~40 kB gz [3] | Full WYSIWYG toolbar editor; last npm publish 2025-01-20; overkill for 3-format need but well-maintained |
| **Trix** | https://github.com/basecamp/trix | MIT | ~47 kB gz | Basecamp-maintained; limited to heading/bold/italic/href/strike; React-free web component; heavier than raw approach for 3-format need |
| **ProseMirror core** | https://github.com/ProseMirror/prosemirror | MIT | ~60 kB gz | Foundation of TipTap/Notion; extreme power but complex API; not justified for bold/italic/size only |

**Recommendation:** **Raw contenteditable + execCommand + Selection API** — build from scratch. For the exact scope (bold, italic, font size only), execCommand remains universally supported in all modern browsers [2], preserves undo history for free, and adds 0 kB to the bundle. Risk: if a future Chrome version removes it, the fallback is Selection API + `document.createElement` wrappers, which are ~50 lines of code. Quill 2 is a valid upgrade path if scope expands.

---

## Category 3 — Color Picker Components (Vanilla JS)

| Library | Repo | License | Last npm publish | Bundle | Fit/Risk |
|---------|------|---------|-----------------|--------|----------|
| **Coloris** (melloware npm wrapper) | https://github.com/melloware/coloris-npm | MIT | 2025-06-02 | ~8 kB min / ~3 kB gz | Actively maintained npm wrapper of mdbassit/Coloris; vanilla ES6, zero deps, accessible; attaches to any input |
| **Coloris** (original) | https://github.com/mdbassit/Coloris | MIT | 2022-04 (upstream stalled) | same | Original author inactive since 2022; community melloware fork keeps npm up to date |
| **Pickr** | https://github.com/simonwep/pickr | MIT | 2024-05-10 | ~17 kB gz | Multi-themed, alpha channel, hsla/rgba; author notes monolithic arch makes new features hard; no new features expected |
| **vanilla-picker** | https://vanilla-picker.js.org | MIT | 2022 | ~8 kB gz | Simple API, alpha support; unmaintained since ~2022 |

**Recommendation:** **@melloware/coloris** (MIT) — the actively maintained npm distribution of Coloris. Ships 2025-06-02, 3 kB gz, zero deps, accessible, attaches as an input overlay. Permissive license, popular community fork with no supply-chain flags.

---

## Category 4 — Comment / Annotation / Threading UI

| Library | Repo | License | Status | Fit/Risk |
|---------|------|---------|--------|----------|
| **html-commenter** | https://github.com/alexispurslane/html-commenter | Unknown (source available) | Active 2025 (HN post) [4] | Vanilla JS, zero deps, DOM-path-anchored comments, author name prompt, no login; data in localStorage + shareable URLs; no server; closest public match to spec |
| **Annotorious** | https://github.com/annotorious/annotorious | BSD-3 | Active 2025, ~530 stars | Image annotation lib (draw shapes on images); text/DOM anchoring not its primary use case; over-engineered for box-comment UX |
| **Annotator (OKFN)** | https://github.com/edsu/annotator-okfn | MIT | Archived/deprecated | Text selection annotation; threaded replies not native; stale |
| **Build from scratch** | N/A | N/A | N/A | A floating panel anchored via `getBoundingClientRect()`, a `<details>` thread list, and a `localStorage`/`sessionStorage` store is ~200 lines of vanilla JS |

**Recommendation:** **Build from scratch** — the closest lib (html-commenter) has no declared license (code is public but terms are unclear, creating legal risk for vendoring). Google-Slides-style threads with resolve + reply + one-time name prompt are a well-defined, bounded UI problem. Implementation: anchor overlay div to target element bounding rect, store threads keyed to a stable `data-comment-id` attribute, render reply list in a panel. Estimated ~250–350 lines of vanilla JS + CSS. Zero dependency risk.

Reference pattern to study (do not vendor): html-commenter for DOM-path anchoring strategy [4].

---

## Category 5 — DOM-to-Clean-HTML Serialization

| Approach | Spec / Repo | License | Bundle | Fit/Risk |
|----------|-------------|---------|--------|----------|
| **`document.documentElement.outerHTML`** | MDN [5] | Browser API | 0 kB | Serializes full live DOM to string; editor overlay elements must be removed from DOM before call; no extra lib needed |
| **XMLSerializer** | W3C / MDN [6] | Browser API | 0 kB | `new XMLSerializer().serializeToString(document)` produces XHTML-style output; may add namespace attrs; `outerHTML` is simpler for HTML5 |
| **DOMPurify** | https://github.com/cure53/DOMPurify | Apache-2.0 / MPL-2.0 | ~7 kB gz | XSS sanitizer; useful as post-processing pass to strip any injected scripts before saving; high trust (cure53), 15k+ stars |
| **SingleFile (ext)** | https://github.com/gildas-lormeau/SingleFile | AGPL-3.0 | Extension | Inlines all assets into one HTML file; AGPL license and browser-extension architecture make it unsuitable to vendor directly |

**Recommendation:** **Native `outerHTML` + DOMPurify pass** — serialize with `document.documentElement.outerHTML` (or clone + strip editor chrome from clone first), then run DOMPurify with a permissive `FORCE_BODY: false` config to strip any stray scripts. DOMPurify (Apache-2.0 / MPL-2.0) is safe to vendor; cure53 authorship, 15k+ GitHub stars, zero supply-chain concerns. No third-party serializer library needed beyond that.

> **SUPERSEDED by adversarial pre-build review (2026-06-03 — see `spec/review-log.md` finding 1):** the "+ DOMPurify pass to strip stray scripts" half of this recommendation is NOT adopted. DOMPurify has no provenance signal, so it cannot strip "stray" injected scripts while keeping the opened file's own scripts (the report's IIFE). The serializer removes editor chrome by NAMESPACE STRIPPING ONLY and runs NO document-body sanitizer; the opened file is the user's own (not untrusted). DOMPurify is retained ONLY as optional defense-in-depth on comment-text rendering. The native-`outerHTML`-on-a-stripped-clone half stands. Authoritative serialization contract: `spec/01-architecture.md` §5.

---

## Category 6 — Existing Open-Source "Edit Live HTML" Visual Editors (Reference)

| Tool | Repo | License | Bundle | Fit/Risk |
|------|------|---------|--------|----------|
| **GrapesJS** | https://github.com/GrapesJS/grapesjs | BSD-3 | ~250 kB gz core + ~60 kB presets [7] | Full page-builder framework; too heavy to vendor; MIT-style license; useful to study block selection, undo, and serialization patterns |
| **Penpot** | https://github.com/penpot/penpot | MPL-2.0 | Full app (Clojure + ClojureScript) | SVG-based design tool; architecture is instructive for canvas selection + transform state; completely impractical to vendor |
| **Xinha** | https://trac.xinha.org | BSD | Legacy | Old WYSIWYG browser editor; BSD licensed; architecture is dated but useful for understanding how editors strip their own chrome on serialization |

**Assessment:** None of these are practical to vendor. GrapesJS is the closest in spirit but at 250+ kB gzipped its inclusion would dominate the bundle and couple us to its block model and plugin system. Study its source for DOM mutation patterns and undo history; do not import it.

---

## Full Citation List

[1] Document: execCommand() method — https://developer.mozilla.org/en-US/docs/Web/API/Document/execCommand — 2026-06-03 — 2025 — TS:8.7 (AT:10 TR:9 TM:7)

[2] `document.execCommand` has valid use cases without viable alternatives — https://github.com/mdn/content/issues/40245 — 2026-06-03 — 2024 — TS:8.3 (AT:9 TR:9 TM:7)

[3] Quill v2.0.3 on Bundlephobia — https://bundlephobia.com/package/quill — 2026-06-03 — 2025-01-20 — TS:8.0 (AT:8 TR:9 TM:7)

[4] Show HN: HTML Commenter — https://news.ycombinator.com/item?id=45053238 — 2026-06-03 — 2025 — TS:7.0 (AT:7 TR:8 TM:6)

[5] Element: outerHTML property — https://developer.mozilla.org/en-US/docs/Web/API/Element/outerHTML — 2026-06-03 — 2025 — TS:8.7 (AT:10 TR:9 TM:7)

[6] DOM Parsing and Serialization (W3C) — https://www.w3.org/TR/DOM-Parsing/ — 2026-06-03 — 2016 — TS:9.0 (AT:10 TR:10 TM:7)

[7] GrapesJS GitHub — https://github.com/GrapesJS/grapesjs — 2026-06-03 — 2025 — TS:8.7 (AT:9 TR:9 TM:8)

[8] Moveable GitHub — https://github.com/daybrush/moveable — 2026-06-03 — 2023-12-03 — TS:8.0 (AT:8 TR:9 TM:9)

[9] interact.js GitHub — https://github.com/taye/interact.js — 2026-06-03 — 2024-03 — TS:8.0 (AT:8 TR:9 TM:8)

[10] subjx GitHub — https://github.com/nichollascarter/subjx — 2026-06-03 — 2025-10-13 — TS:6.7 (AT:6 TR:7 TM:7)

[11] @melloware/coloris npm — https://github.com/melloware/coloris-npm — 2026-06-03 — 2025-06-02 — TS:7.7 (AT:8 TR:7 TM:8)

[12] DOMPurify GitHub — https://github.com/cure53/DOMPurify — 2026-06-03 — 2025 — TS:9.0 (AT:9 TR:10 TM:8)

[13] Quill GitHub — https://github.com/slab/quill — 2026-06-03 — 2025-01-20 — TS:8.7 (AT:9 TR:9 TM:8)

[14] Pickr GitHub — https://github.com/simonwep/pickr — 2026-06-03 — 2024-05-10 — TS:7.3 (AT:7 TR:8 TM:7)

[15] Annotorious GitHub — https://github.com/annotorious/annotorious — 2026-06-03 — 2025 — TS:7.0 (AT:7 TR:7 TM:7)

[16] Penpot GitHub — https://github.com/penpot/penpot — 2026-06-03 — 2025 — TS:8.3 (AT:9 TR:9 TM:7)

---

## Sources Discarded

| Source | TS | Reason |
|--------|----|--------|
| [neodrag](https://github.com/PuruVJ/neodrag) | 6.0 | Drag only — no resize handles; topic mismatch for this use case (TM:4) |
| [vanilla-picker](https://vanilla-picker.js.org) | 5.7 | Unmaintained since ~2022 (TR:5) |
| [Annotator OKFN](https://github.com/edsu/annotator-okfn) | 5.3 | Archived/deprecated; stale (TR:4, AT:5) |
| [Xinha](https://trac.xinha.org) | 5.0 | Legacy architecture; last active pre-2015 (TR:4, AT:5) |
| [SingleFile](https://github.com/gildas-lormeau/SingleFile) | 6.0 | AGPL-3.0 license makes vendoring legally problematic; TM:5 for this specific need |
