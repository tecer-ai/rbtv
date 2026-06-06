# Shape - Hypresent v1

> **Purpose:** Captures shaping decisions, discoveries, constraints, and references future agents need. Original Shaping is immutable. Other sections are append-only.

---

## Original Shaping

### Scope Definition

**What this accomplishes:**
- A local web tool (Python stdlib server + Chrome browser frontend) that OPENS an existing AI-generated HTML file from disk and edits it WYSIWYG, then "Save As" a new standalone HTML.
- Editing operations in v1: text edit, text format (bold/italic/font-size), flow-aware resize, transform-translate move, recolor (palette tokens + per-element + inline-style), embedded comments (hidden JSON island, Google-Slides-style UX).
- Works on BOTH analyzed test files (slide deck + scrolling report) and generalizes to other formats via a format-agnostic editability-hints convention.

**What this does NOT include:**
- No build step / bundler; no server framework (stdlib only).
- No new document creation (the tool edits EXISTING files only).
- No collaboration/real-time sync (comments are local + embedded, single-user).
- No conversion of flow layouts to absolute positioning.
- No vendoring of a heavy page-builder (GrapesJS/Penpot) — studied, not imported.
- The editor does NOT police project-deliverable formats; it edits whatever HTML it is given.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Isolation | Same-origin iframe; app shell in parent; `hyp-`namespaced edit-runtime injected in iframe | Only model where the document's relative assets + own JS run unmodified; full record `../../decision-log.md` A1–A3. |
| Where Moveable runs | Inside the iframe, on the iframe's document | Avoids fragile parent↔iframe coordinate mapping across scroll/reflow; A5. |
| Resize | Flow-aware (D1) | Documents stay responsive; no absolute conversion. |
| Move | `transform: translate()` only (D2) | Non-destructive, reversible; flag when visually out of flow. |
| Format control | We own a format-agnostic hints convention (D3) | Robust on conforming files, graceful degradation otherwise. |
| Comments | Hidden `<script type="application/json" id="hyp-comments">` island (D4) | Inert, portable, invisible in normal view. |
| Open/Save | Server reads/writes disk from the file's original directory (D5) | Relative `assets/` + CDN refs resolve. |
| Recolor | Tokens + per-element + inline-style (D6) | CSS variables alone miss inline colors (proved by REPORT file). |
| History | One unified command/inverse stack (A7) | Coherent Ctrl-Z across mixed operations. |
| Serialization | Clone → strip ALL `hyp` chrome (namespace strip only) → re-embed island → node-count guard → emit (A8/A11). NO document-body DOMPurify. | Zero leakage; the document's own JS survives by NOT being touched (the opened file is the user's own, not untrusted). See superseding entry in Decisions and Discoveries (the original "DOMPurify keeps doc scripts" framing was impossible — DOMPurify has no provenance signal). |
| Vendoring | Moveable, Coloris, DOMPurify copied to `app/js/vendor/`; comments + text-format built from scratch (A9) | Per `../../research-oss.md` recommendations (all MIT/permissive). |
| Server | Python stdlib `http.server` (A10) | Trivial install; single run command. |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Must work on both test files AND generalize | Product goal + the two analyses | No `.slide`/`.block` selector presupposition; region detection is heuristic/hint-driven. |
| Editor coexists with the document's own JS | `../../fixture-profiles.md` (report fixture IIFE: scroll-spy, reveal, expand) | All injected classes/ids `hyp-`prefixed; native classes/ids/`data-*` read-only; runtime tolerates concurrent DOM mutation. |
| `position:absolute` may be SEMANTIC content | Report fixture's semantic absolutely-positioned nodes at `left:%` | Resize/move read layout role before acting; never treat all absolute as decorative. |
| Inline SVG present | Report fixture hero + icon SVGs | Traverse SVG without treating `<path>` as editable text. |
| Inline-`style` colors exist outside `:root` | Report fixture legend swatches, span overrides | Recolor must mutate inline styles, not only tokens. |
| Pre-existing native `data-*` carries content | Report fixture's native `data-*` content attributes | Injected attrs strictly `data-hyp-*`; never overwrite native `data-*`. |
| kimi is a non-reasoning executor | `../../kimi-cheatsheet.md` | Each task prompt must be fully self-contained; per-task contracts in `../../spec/04-implementation-plan.md`. |
| Headless kimi auto-approves all tool calls; no native allowlist | `../../kimi-cheatsheet.md` | Confinement via `--work-dir`, agent-file tool stripping, and post-run `git diff` against the task's declared files. |

### User Inputs

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Isolation preference | "I strongly favor the iframe option — argue if you disagree" | Adopted iframe isolation (A1); concurred (see Collaborative Decisions). |
| 2 | Locked decisions | 6 non-negotiable decisions (resize/move/format/comments/open-save/recolor) | Recorded verbatim in `../../decision-log.md` D1–D6. |
| 3 | Module shape | "small, single-purpose, independently testable; no monolith" | Module map `../../spec/03-module-map.md`; one kimi task per module. |
| 4 | Vendoring | Moveable + Coloris + DOMPurify, no build step | A9 + `../../decision-log.md` Vendored Libraries. |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Iframe isolation | Strongly favored; invited disagreement | Examined the alternative (Shadow DOM / inline injection): inline injection pollutes the saved DOM and collides with the document's own JS; Shadow DOM cannot host the document's existing global CSS/JS. Iframe is correct. | Concur with iframe (A1). No counter-argument survived: the document's relative assets + self-contained JS only work in a same-origin iframe; alternatives break D5 or coexistence. |
| 2 | Where Moveable runs | Open question posed | Parent-overlay requires continuous iframe→parent coordinate mapping across scroll/responsive reflow (fragile, laggy); in-iframe mounting gives native coordinates. | Moveable runs inside the iframe (A5). |
| 3 | DOMPurify on a file with the document's own JS | "run DOMPurify script-safe pass" | A blanket script strip would break REPORT's IIFE. Initially proposed: config DOMPurify to keep the document's own scripts. **SUPERSEDED (see Decisions and Discoveries):** DOMPurify cannot distinguish injected from native scripts by provenance, so "keep doc scripts, drop injected" is not achievable. | A11 (revised) — NO document-body DOMPurify; editor chrome removed by namespace strip ONLY; the document's own scripts survive untouched; DOMPurify is OPTIONAL comment-text-only defense-in-depth. |

---

## Standards Applied

### Planning Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Zero-context plans | Each `Tn` is implementable from its `../../spec/04-implementation-plan.md` row + named spec sections alone. |
| Explicit file operations | Every task row uses CREATE/UPDATE with exact paths. |
| Dependency ordering | Foundation T1–T9 + CP1 precede all features; pair T10→T11 explicit. |
| Plan body minimalism | Full contracts/acceptance live in the spec (`../../spec/`), not duplicated in the plan body. |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| No editor leakage | `../../spec/05-verification-plan.md` §4 gate item 2. |
| Namespacing absolute | `../../spec/05-verification-plan.md` §3 regression checklist. |
| Document-JS preservation | V-SAVE-2 + §4 gate item 4. |
| Per-task confinement | kimi `git diff` confined to the task's declared files (`../../kimi-cheatsheet.md` Confinement). |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Implement a module from a self-contained contract | kimi sub-agent (headless) | Each task is a bounded unit; `../../kimi-cheatsheet.md`. |
| End-to-end behavioral verification | Chrome DevTools MCP | Navigate/snapshot/evaluate against both fixtures. |
| Strip web tools from a code task | kimi `--agent-file` | Confinement per cheatsheet. |

---

## Decisions and Discoveries

> **APPEND-ONLY:** Capture decisions/discoveries/unexpected constraints only. Never modify or delete prior entries.

<!-- Decisions and discovery entries will be appended below this line -->

### Decision (2026-06-03, adversarial pre-build review): Serialization is namespace-strip only — no document-body DOMPurify (supersedes Collaborative Decision 3 framing)

The original A11 framing ("DOMPurify config keeps the document's own scripts and drops injected ones") is impossible: DOMPurify sanitizes by node/attribute rules, with NO signal for a script's provenance. It cannot keep the report's IIFE while dropping a hypothetical injected script. Resolution: editor chrome is removed SOLELY by namespace stripping (remove every `hyp-` node/attr/class token + injected inline style + the injected edit-runtime `<script>`); the document's own scripts/handlers/`<style>`/SVG/native `data-*` survive because the strip never touches them. The opened document is the USER'S OWN file (not untrusted), so no script-stripping sanitizer runs over the document body. DOMPurify's only v1 role is OPTIONAL defense-in-depth on COMMENT-TEXT rendering (v1 renders comment text via `textContent`, already XSS-safe), and MAY be dropped from v1. Applied to: decision-log A8/A11/A9/Vendored-Libraries, `01` §5, `03` serializer + comments, `04` T2/T9, task files T9/T15.

### Decision (2026-06-03, review): Dedicated fixed `/runtime/*` server route for the injected edit-runtime

The mutable `/doc/` root re-points to each opened file's directory and does not contain the editor runtime, so the injected `<script type="module">` had no resolvable origin. Resolution: add a FIXED static route `GET /runtime/*` served from the app's own `runtime/` dir (distinct from `/doc/*`). The parent injects the runtime with the ABSOLUTE src `/runtime/js/runtime-main.js`; its ES-module `import` chain resolves against `/runtime/js/` (sibling modules) and absolute `/app/js/vendor/...` (vendored libs). Applied to: decision-log A10, `01` §1/§2/§8, `03` server.py + runtime-main, `04` T1/T3, task files T1/T3.

### Decision (2026-06-03, review): Collision-resistant comment-anchor key (5 fields)

The bare structural fingerprint (tag + nth-of-type chain + nearest native id) collides on repeated identical siblings, which BOTH fixtures contain (the deck fixture and the report fixture each have repeated identical sibling cards with no id). Resolution: a 5-field key — `hook` (H1 `data-hyp-hook`, authoritative when present) + `path` (tag:nth-of-type chain from nearest native id) + `nativeId` + `contentHash` (FNV-1a of first 32 normalized chars of own textContent) + `siblingIndex` (index among same-key siblings) — with a defined match priority order and a never-lossy "unanchored" fallback. Concrete contract in `01` §6.1. Applied to: `01` §6/§6.1, `03` comments, `04` T15, task file T15.

---

## References

> **Path format:** External files use project-root-relative paths; internal files use file-relative paths.

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|------------------------|
| 3-resources/tools/hypresent/docs/kimi-cheatsheet.md | Headless kimi dispatch (`--work-dir --quiet --prompt`), auto-approval, no native allowlist, confinement via git diff, exit-code retry on 75. |
| docs/fixture-profiles.md (Fixture A) | Deck fixture: ~10 slide sections, flex/grid + decorative absolute, `:root` tokens, zero JS, no ids/`data-*`, relative `assets/`. |
| docs/fixture-profiles.md (Fixture B) | Report fixture: scrolling sections, own IIFE JS, native ids + native `data-*`, inline SVG, inline-`style` colors + `position:absolute` content; lists every slide-deck assumption that BREAKS. |
| 3-resources/tools/hypresent/docs/research-oss.md | Vendored picks: Moveable (resize/move), Coloris (color), DOMPurify (sanitize); build comments + text-format from scratch; native `outerHTML` serialize. |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| ../../decision-log.md | Locked decisions D1–D6 + architecture A1–A12 | Every task |
| ../../spec/01-architecture.md | Isolation, protocol, serialization, error handling, namespacing | T3,T4,T5,T9 + features |
| ../../spec/02-html-convention.md | Editability hints + graceful degradation + region detection | T5,T10,T14 |
| ../../spec/03-module-map.md | Per-module public contracts | Every product-code task |
| ../../spec/04-implementation-plan.md | Authoritative task contracts + acceptance + STATUS | Every task |
| ../../spec/05-verification-plan.md | Test cases, regression checklist, Save-As gate | T18 + every feature's done-check |
