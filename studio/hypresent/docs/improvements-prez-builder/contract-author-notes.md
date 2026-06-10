# Contract Author Notes — RBTV Slide-Library Convention v1

**Author dispatch:** prez-builder workstream 1 (CONTRACT). Orchestrator-facing.
**Date:** 2026-06-06
**Scope authored:** problem-tree branch 1 (CONTRACT). Branches 2-4 are consumers.
**Deliverables produced:**
- `3-resources/tools/rbtv/html/slide-library/docs/convention-spec.md` (normative, sections 1-7 + 9)
- `3-resources/tools/rbtv/html/slide-library/docs/fixture-spec.md` (section 8, executor-ready)
- this file (forks / contradictions / gaps / assumptions)

This document is how you ratify. Each fork below has a recommendation. **Ratify or override by number** (e.g. "F3: ratify", "F7: override → option b"). Ratifications land as amendments in `convention-spec.md` § Amendments (ADX-N); executors then cite "per ADX-N".

---

## How I read the mandate

The convention is the keystone: engine (2), builder UI (3), and tecer migration (4) all code against it. My single most important job was **coherence** — one manifest schema, one token grammar, one asset-resolution rule, one as-built schema, referenced identically everywhere. I optimized every fork toward: (1) DT4 (cold agent assembles from library contents alone), (2) stdlib-only Python engine with no exotic deps, (3) nothing tecer-specific, (4) the proven informal convention survives migration with minimal semantic loss.

Live source was read in full and **outranks recon** wherever they disagree — see Contradictions C1-C5, several of which correct the recon.

---

## FORKS RESOLVED (awaiting ratification)

### F1 — Manifest format: front-matter-fenced TSV vs Markdown table vs YAML vs CSV vs JSON

**Decision:** Markdown table inside a fenced section of a `manifest.md` file (carry forward tecer's proven shape), BUT with a machine-contract hardening: the spec pins the exact column order, the exact header text, and a strict cell-count parse (engine `die()`s on mismatch — tecer's `assemble.py` already does this).

**Alternatives weighed:**
- **(a) YAML** — richest structure (lists, nested asset specs), but: multi-line diffs are noisier than a one-row-per-slide table; hand-editing a 57-row YAML is more error-prone than a table; a stdlib YAML parser does not exist (tecer wrote a *minimal* hand-rolled YAML reader only for the tiny preset blocks — scaling that to the full manifest is real parser surface). Rejected.
- **(b) CSV/TSV** — strictly parseable with stdlib `csv`, but unreadable in raw git diffs and in an editor; summaries contain commas (CSV quoting hell) and the `·`/accented Portuguese text; loses the "open the file and read it" property the cold agent and human both rely on. Rejected.
- **(c) JSON** — strict and stdlib-parseable, but hand-editing is painful (trailing-comma errors, no comments) and diffs are verbose. The manifest MUST stay hand-editable (the upstream rule has authors add rows by hand). Rejected.
- **(d) Markdown table (CHOSEN)** — hand-editable, diff-friendly (one row per slide = one diff line per change), strictly parseable with ~40 lines of stdlib string code (proven: tecer's `parse_manifest()`), readable raw. The cost — markdown tables cannot nest — is handled by keeping the per-slide schema flat (all columns scalar; `assets` is a comma-joined scalar, not a nested list).

**Tradeoff accepted:** flat schema only. No nested per-slide data. If a future need wants per-asset metadata (alt text, role), it cannot live in the table cell cleanly — it would force a format change or a sidecar. Judged acceptable for v1; flagged as G2.

---

### F2 — Per-slide schema: which of tecer's 9 columns survive, what is added, what becomes optional

**Decision:** Keep all 9 columns; ADD one (`title`); make `audience`, `assets`, `provenance` carry explicit empty sentinels rather than dropping them. Final 10-column schema:

`id | file | section | title | audience | lang | kind | summary | assets | provenance`

**Reasoning per column:**
- `id` — SURVIVES, required, the contract key. Unchanged.
- `file` — SURVIVES, required. CHANGED semantics: spec mandates it is `slides/{id}.html` (path-prefixed, as tecer does) so the engine resolves it library-relative.
- `section` — SURVIVES, required. PROMOTED to first-class (the GUI left-pane grouping, locked decision). Added: sections get an explicit ORDER declaration (see F4) — tecer had no section order, sections only appeared in manifest row order.
- `title` — **ADDED**, required. Rationale: the GUI browse pane and the catalog need a short human label per slide; tecer overloaded `summary` for this, but `summary` is a 1-2 sentence description (too long for a card title) and the GUI needs both a title (card heading) and a summary (hover/detail). Also: `base.html`'s `{{TITLE}}` is the *document* title; a per-slide `title` is distinct. Making it a column (not derived) keeps the GUI free of HTML parsing.
- `audience` — SURVIVES, optional with sentinel `general`. Rationale: tecer treats audience as "primary use, not a hard filter" (the institutional preset reuses prospect-tagged ids). So audience is advisory metadata, not a selection gate. Kept for GUI/agent hints; never a hard filter.
- `lang` — SURVIVES, required. The GUI language filter keys on it (locked decision: language is per-slide). Values are BCP-47-ish short codes (`pt`, `en`); spec allows any token but recommends ISO 639-1.
- `kind` — SURVIVES, required, the single most important field (recon orchestrator-note #1 agrees). `ready` | `template`. Drives whether a creative pass is needed.
- `summary` — SURVIVES, required. Free text 1-2 sentences. The disambiguator between sibling slides (tecer's summaries do heavy lifting distinguishing e.g. the 6 next-steps variants).
- `assets` — SURVIVES, required with sentinel `-`. Comma-separated. Two-root resolution formalized (see F5).
- `provenance` — SURVIVES, optional with sentinel `-`. Rationale: provenance (`{deck} ({date})`) is tecer-history-specific; a fresh RBTV library has no provenance decks. Making it optional (sentinel `-`) is what de-tecer-izes it. For template slides it doubles as the "read this exemplar before filling tokens" pointer — valuable but not always present.

**Dropped from consideration:** a `status`/`freshness` column. Recon flagged staleness is a workflow concern, not a manifest field. I kept it out of the table (a freshness date would rot silently and give false confidence) — freshness stays a governance practice in the self-description (see F6). Flagged as a deliberate non-add.

**Alternative considered & rejected:** collapsing `audience` into `section`. Rejected — they are orthogonal (a `team` section slide can be `investor` or `general` audience; tecer has both).

---

### F3 — ENGINE DISTRIBUTION (the critical fork) — how a cold library carries its assembly tool

**This is the fork the dispatch flagged as CRITICAL and asked me to recommend with tradeoffs for your ratification.**

**Options:**
- **(a) Engine vendored INTO each library** — `assemble.py` physically copied into the library folder (tecer's current precedent). DT4-perfect (the tool literally travels in the folder). But: every library carries a frozen copy; an engine bugfix must be re-vendored into every library by hand; libraries drift to different engine versions silently; "self-updating concerns" (the dispatch's words) are real — a library that travels for months runs stale assembly logic.
- **(b) Thin in-library wrapper that locates/bootstraps the RBTV engine** — a tiny `assemble.py` (or `assemble.cmd`/`.sh`) in the library that finds the RBTV engine (env var `RBTV_SLIDE_ENGINE`, or a configured path, or a vendored fallback) and execs it against `--library .`. Bugfixes propagate (engine is central); the library still "contains" an entry point. But: bootstrap can fail (engine not found on a fresh machine), which dents DT4 ("nothing but what the library contains").
- **(c) Instructions-only, pointing at an engine path** — the self-description tells the agent "run `python {RBTV}/html/slide-library/engine/assemble.py --library .`". Zero code in the library. Cleanest propagation. But: weakest DT4 — a cold agent on a machine without the RBTV repo is stuck; a traveling library (tecer-biz is its own repo) has no engine at all.

**MY RECOMMENDATION: (a) vendored engine + a version stamp + a documented re-vendor command — a "vendored-but-versioned" hybrid.**

Concretely:
1. The engine is authored ONCE, centrally, in the RBTV repo at `html/slide-library/engine/assemble.py` (workstream 2 builds it there). This is the canonical source.
2. A spec-compliant library MUST contain a copy of the engine at `{library}/assemble.py` (or `engine/assemble.py`). DT4 is satisfied literally — the tool is in the folder.
3. The library's `library.json` (the convention-version file, see F7) records `engine_version`. The engine stamps the same version. On run, the engine compares the stamp in the file it is running from against the `library.json` it reads and warns on mismatch.
4. The convention documents the re-vendor command (`python {RBTV}/html/slide-library/engine/install-engine.py {library-path}` or equivalent — workstream 2 owns the exact form): copy the central engine over the library's copy and bump the stamp.

**Why (a)-hybrid over (b)/(c):** DT4 is a *contracted done-test* and it is unambiguous — "using NOTHING but what the library contains". Options (b) and (c) both fail the literal reading the moment a library is on a machine without the RBTV repo, and tecer-biz IS its own repo that travels. The dispatch explicitly lists "libraries travel" as a weight. The only real cost of (a) is propagation, and the version stamp + re-vendor command converts silent drift into a loud, fixable warning — which is exactly how tecer already handles its own staleness (loud failure + upstream rule). Stdlib-only and zero-runtime-dependency, so vendoring is cheap (one ~450-line file).

**What I need from you:** ratify (a)-hybrid, OR pick (b)/(c). If (b), the spec's self-description template changes to describe the bootstrap; if (c), DT4's acceptance criteria must be relaxed (and I'd push back on that — it weakens the keystone contract). The spec is currently written for (a)-hybrid; § 5 and § 1 both depend on this answer. **This is the highest-leverage ratification.**

---

### F4 — Section definition & ordering: where do sections live and how is deck/catalog order derived

**Decision:** Sections are declared in `library.json` as an ORDERED list (`sections: ["opening", "intro", ...]`). The manifest `section` column references a declared section by name. Catalog rendering and any "by section" GUI grouping use the `library.json` order; within a section, manifest row order is the tiebreak.

**Reasoning:** tecer had sections only as free strings in the manifest column, with no canonical order — the catalog rendered in manifest row order, which conflates "authoring order" with "narrative order". The GUI needs a stable left-pane section order independent of when rows were added. A declared list also lets validation reject a manifest row whose `section` is not declared (catches typos like `next-step` vs `next-steps`).

**Alternative rejected:** subfolders per section (`slides/opening/`, `slides/intro/`). Rejected — tecer deliberately uses a flat `slides/` dir and encodes section in metadata; subfolders would force a file move to re-section a slide and break the `file = slides/{id}.html` simplicity. Flat dir + declared order is strictly better for the GUI.

---

### F5 — Asset resolution: keep tecer's implicit two-root (`/` = repo root, bare = library assets) or make it explicit

**Decision:** Keep the two-root SCHEME but make BOTH roots explicit and library-anchored, and add an explicit prefix grammar to remove the fragility recon flagged.

- Bare filename (`cover-bg.jpg`) → resolves from `{library}/assets/`. (Unchanged from tecer.)
- `{client-logo}` sentinel → resolves from the engine's `--client-logo` flag (per-deck, never in the library). (Unchanged.)
- `-` → no assets. (Unchanged.)
- Cross-root paths → tecer used "contains a `/` → resolve from tecer-biz repo root". This is the fragile bit (recon orchestrator-note #3): a bare filename that accidentally contains `/` resolves from the wrong root, AND "repo root" is a tecer-specific concept (a generic library has no parent repo). **Replaced with an explicit, opt-in second root:** `library.json` MAY declare `extra_asset_root` (a path relative to the library, e.g. `../brand/logo`). An asset entry of the form `@root/path` resolves from that declared root. No declared `extra_asset_root` → `@root/...` entries are a validation error. A bare filename NEVER resolves from the second root regardless of slashes.

**Reasoning:** the only real-world cross-root user is tecer's `cover-investor` slide pulling `brand/logo/tecer-logo-white-transparent.png` from the tecer-biz repo. The migration maps that to `extra_asset_root: ../brand/logo` + asset entry `@root/tecer-logo-white-transparent.png` (or tecer can simply vendor that one PNG into `assets/` and drop the cross-root entirely — recommended, see migration appendix). Making the second root explicit and optional means a generic RBTV library that self-contains all assets never touches it, and the "accidental slash" failure mode is gone.

**Tradeoff:** migration must rewrite tecer's one cross-root asset entry. Trivial (one row). Recommended alternative in the appendix: vendor the PNG and delete the cross-root feature use entirely for tecer.

---

### F6 — Self-description: one entry-point doc, and what governance it carries vs delegates

**Decision:** A single required file `README-FOR-AGENTS.md` at the library root (NOT `CLAUDE.md` — see reasoning). It is the cold-agent entry point. The spec provides the complete template text (in convention-spec § 5). It carries: what the library is, how to read manifest/presets/`library.json`, the EXACT engine invocation for both preset and explicit-order assembly, the creative-pass rules ({{TOKEN}} grammar, ready-vs-template), and a "Human/agent judgment — NOT automated" section listing freshness checks and upstream proposals (lifted from recon's governance classification: the (b) "agent/human judgment" rows stay practice; the (a) "mechanically enforceable" rows are the engine's job).

**Why `README-FOR-AGENTS.md`, not `CLAUDE.md`:** tecer's entry point is `CLAUDE.md`, which works because tecer-biz is a Claude-Code workspace. But the convention is RBTV-generic and the cold agent may not be Claude Code (the dispatch says "a cold agent", not "Claude Code"). `CLAUDE.md` is a Claude-Code-specific filename with auto-load semantics that don't generalize. A neutral, self-explaining filename that ANY agent is told to read first is more honest to DT4. **However** — a library that lives inside a Claude-Code workspace (like tecer-biz) SHOULD ALSO keep a thin `CLAUDE.md` that says "read `README-FOR-AGENTS.md`" so Claude-Code auto-load still works. The spec marks `CLAUDE.md` as OPTIONAL (a one-line pointer) and `README-FOR-AGENTS.md` as REQUIRED.

**Fork sub-decision F6a — is the as-built log a mandatory gate or an optional record?** Recon orchestrator-note #4 surfaces this: tecer's log is entirely retroactive (aspirational, not live discipline). **Decision: the engine writes the as-built entry AUTOMATICALLY on every successful assembly (locked decision says "written BY THE ENGINE on every assembly"). So it is neither a manual gate nor optional — it is an automatic side effect of assembly.** This dissolves the tension: there is no discipline to forget because the engine does it. The human/agent governance rows (freshness, upstream) stay judgment; the as-built write does not.

---

### F7 — Convention versioning: how a library declares its version and how engines check compatibility

**Decision:** A required `library.json` (stdlib `json`) at the library root carries:
```json
{ "convention_version": "1.0", "engine_version": "1.0", "name": "...", "default_lang": "pt", "sections": [...], "extra_asset_root": null }
```
The engine declares the convention version(s) it supports. On run it reads `library.json`, and if `convention_version`'s MAJOR component is unsupported, it `die()`s loud (semver-major = breaking). MINOR mismatch warns but proceeds.

**Why a JSON sidecar and not front-matter in the manifest:** the version/section/config data is read by the engine AND the GUI AND the cold agent's bootstrap, all of which benefit from a single tiny strict-parse file. Keeping it out of `manifest.md` keeps the manifest a pure slide table. JSON (not YAML/TOML) because stdlib `json` is the only zero-dep strict parser, and this file is config (not hand-edited often) so JSON's no-comments cost is low.

**Alternative rejected:** version as a line in `README-FOR-AGENTS.md`. Rejected — prose is not strict-parseable; the engine compatibility check needs a machine field.

---

### F8 — Presets format: keep tecer's prose-intro + fenced YAML, or move to JSON/table

**Decision:** Keep tecer's exact shape — a `presets.md` with one section per preset: a prose intro paragraph + a fenced ```yaml block (`preset`, `lang`, `slides: [...]`). Carry tecer's proven minimal-YAML parse.

**Reasoning:** this is the one place tecer's hand-rolled tiny-YAML parser already works and is proven across 4 presets; the prose intro is genuinely valuable (it documents WHEN to use the preset and the deviation rules — exactly what a cold agent reads to choose). Moving presets to JSON would kill the prose intro (no comments) or force an awkward description field. The YAML block is tiny (3 keys, the slides list) so the stdlib-parse surface is small and already written.

**ADDED to the preset schema (optional keys):** `title` (default document title for decks from this preset) and `audience` (advisory). Both optional. The `slides` list and `lang` are the only required keys (matches tecer).

**Deviation semantics (F8a):** the dispatch asks how the as-built record expresses "preset X + deviations". **Decision:** the as-built entry carries an optional `preset:` field (the preset name, or `-` for scratch). When a deck started from a preset but the final composition differs, the as-built entry's `slides:` list is ALWAYS the actual final ordered ids (ground truth), and a `deviations:` block describes the delta in tecer's proven free-text vocabulary (`added: {id}`, `removed: {id}`, `reordered: ...`, `modified: {id} — what`, `bespoke: {desc}`). The engine fills `preset` + `slides` mechanically; `deviations` is filled by the agent/GUI (the engine knows the id delta from the preset but NOT the "modified/bespoke" semantics, which are creative-pass facts). See F8b.

**F8b — can the engine compute deviations automatically?** Partially. The engine CAN compute the set/order delta between a named preset's id list and the actual `--slides` it assembled (added/removed/reordered ids). It CANNOT know `modified:`/`bespoke:` (those are creative-pass edits to token content, invisible at assembly time). **Decision:** the engine auto-writes the structural delta (added/removed/reordered) into the as-built entry when `--preset` is given but the final ids differ (the GUI's "start from preset then tweak" flow); the `modified:`/`bespoke:` lines are appended by whoever fills tokens (out of v1 engine scope — the editor/creative pass owns them). This keeps the engine honest (it only records what it can observe) while preserving tecer's richer vocabulary for the human pass.

---

### F9 — Theme/base contract & token grammar: formalize tecer's, or redesign

**Decision:** Formalize tecer's exact model as the contract (it is proven and the editor/runtime already consume `<section>` fragments). Specifics pinned in convention-spec § 6:
- `base.html` MUST contain exactly the 5 markers: `{{LANG}}`, `{{TITLE}}`, `/* {{ACCENT_CSS}} */`, `/* {{THEME_CSS}} */`, `<!-- {{SLIDES}} -->`. Engine fills all 5.
- `theme.css` is the single design system, inlined whole at assembly.
- Fragments are bare `<section class="slide ...">` — NEVER `<head>`/`<style>`/`<script>` (the architectural invariant; recon orchestrator-note #2). Validation rejects fragments containing these.
- {{TOKEN}} grammar: `{{SCREAMING_SNAKE_CASE}}`. Numbered variants use `_1`/`_2`/`_A`/`_B` suffixes. Two RESERVED token classes: engine-filled (`{{LANG}}`, `{{TITLE}}`, `{{N}}`) and creative-pass (everything else). `{{N}}` is special: the engine renumbers `<div class="slide-number">{{N}}</div>` sequentially; a fragment with no `{{N}}` div is unnumbered (covers).
- Special creative-pass tokens for the client lockup: `{{CLIENT_LOGO_SRC}}` and `{{CLIENT_NAME}}` are RECOMMENDED names (not mandated) for the per-deck logo/name — the convention names them so the GUI/agent and the editor agree, but a library MAY use others.
- **Token authoring comments are part of the contract:** each `{{TOKEN}}` in a template fragment SHOULD be preceded by an HTML comment describing what to author (tecer's `<!-- PAINS_KICKER: ... -->` pattern). The convention formalizes this comment as the machine-readable fill-spec for the creative pass (recon orchestrator-note #5). RECOMMENDED, not MUST (a template with self-evident tokens may skip it), but the fixture exercises it.

**Reasoning:** zero benefit to redesigning a token grammar the 57 existing fragments and the hypresent editor already speak. The only formalization work is writing down the invariants and the validation rules. Redesign would orphan tecer's library and the editor's `<section>` detection.

---

### F10 — As-built log: separate file vs tecer's "inside presets.md"

**Decision:** A SEPARATE file, `as-built.md`, at the library root. NOT inside `presets.md` (tecer's current shape). Append-only. Machine-readable entry schema (convention-spec § 4).

**Reasoning:** tecer co-locates the as-built log inside `presets.md` (recon § 6). That conflates two different artifacts with different write patterns: presets are hand-curated and rarely change; the as-built log is engine-appended on EVERY assembly (locked decision). Co-locating them means every automatic as-built write touches the hand-curated presets file — a recipe for merge conflicts in parallel use and a confusing diff history. Separating them gives the engine a clean append target and keeps presets stable. This is a deliberate IMPROVEMENT over tecer; the migration appendix extracts tecer's 11 retro entries from `presets.md` into the new `as-built.md`.

**Entry format decision (F10a):** machine-readable but markdown-embedded — each entry is a fenced ```yaml block under a `### {entry-id}` heading (mirrors the preset format for parser reuse: the engine already has the minimal-YAML reader). Required keys: `date`, `output`, `slides` (ordered ids), `lang`, `engine_version`. Optional: `preset`, `deviations`, `intent` (free-text), `upstream` (proposals made). This makes DT5 ("re-assemble a known deck from its as-built record and compare") a pure mechanical read: parse the entry's `slides` + `lang` → feed to the engine → compare. The e2e-report precedent (betano reassembly) proves the comparison bar is **structural + visual parity, byte-exact is a non-goal** — I wrote DT5's acceptance criteria to match that proven bar.

---

## CONTRADICTIONS FOUND (live source vs recon, and internal)

**C1 — Slide count: recon says 58, CLAUDE.md says 54, TRUTH is 57.** [HIGH — corrects recon]
I parsed the live manifest with the exact same strict logic tecer's `assemble.py` uses: **57 slide rows.** I cross-checked against `slides/` on disk: **57 files, perfect 1:1, zero drift, zero duplicates.** (Verification: a Python script replicating `parse_manifest()` + a dir listing — `in manifest not on disk: []`, `on disk not in manifest: []`.) The recon's § 2 "58" is wrong — its own contradiction section spirals through 57-vs-58 reasoning and lands on a false "no mismatch at 58". The actual numbers: tecer's `CLAUDE.md` Structure block says "54 slide rows" / "54 fragments" (TWICE, lines 12 + 19) — stale, pre-trust-arc (the trust-arc commit added 3: `method-refusals`, `team-lived-it`, `proof-snapshots`; 54+3=57). **The live manifest and disk agree at 57; both docs that cite a count are wrong.** Migration impact: the migration appendix instructs deriving counts from the live manifest, never from any doc string. This is the canonical example of why a count in prose rots — the convention deliberately puts NO slide-count in any prose file (the manifest IS the count).

**C2 — recon's manifest-vs-disk "mismatch" is a non-issue.** [resolved] Recon § 2 spends a long paragraph unable to decide if there's a 1-file mismatch. There is not. Settled by C1's cross-check.

**C3 — `--client-logo` flag: accepted but unused when no fragment lists `{client-logo}`.** [LOW — recon C3 is right] Confirmed against live `assemble.py` (`resolve_asset_source` only consults `--client-logo` for the `{client-logo}` sentinel) and the e2e-report (betano passed the flag; it was unused; the logo reached the cover via the `{{CLIENT_LOGO_SRC}}` *token*, not the flag). The convention resolves this cleanly: `{{CLIENT_LOGO_SRC}}` is a creative-pass TOKEN (filled in the editor, points at a file the author drops into the deck's `assets/`), while `{client-logo}` is an ASSET-CELL sentinel (engine copies a file via `--client-logo`). They are two different mechanisms; tecer currently uses only the token path. The spec documents both and marks the asset-cell `{client-logo}` path as the one `--client-logo` serves.

**C4 — "groups" = `section`, no new concept.** [resolved — confirms structured-problem] The structured-problem doc (discovery #5) and locked decisions both say groups = the existing `section`. Confirmed: nothing in the data needs a new grouping concept. Sections are promoted to first-class (declared + ordered, F4) but they are the same `section` column tecer has.

**C5 — `theme.css` external font/icon CDNs mean assembled decks are NOT offline.** [MEDIUM — gap, not contradiction] Live `base.html` links Google Fonts (Outfit, Space Mono) + FontAwesome 6.5.1 via CDN; these are NOT inlined. So an "assembled standalone deck" is standalone for CSS/structure but needs network for fonts/icons. The convention documents this as an explicit known limitation of the base/theme contract (§ 6) rather than mandating offline-completeness (which would require vendoring fonts + an icon set — out of v1 scope). Flagged so you know "standalone" has an asterisk.

---

## GAPS (need information I could not get from the codebase; no web allowed)

**G1 — Engine re-vendor mechanism is workstream 2's to design.** My F3 recommendation (vendored-but-versioned) assumes workstream 2 builds an `install-engine.py` / version-stamp mechanism. I specified the DATA CONTRACT (the `engine_version` field in `library.json` + a stamp in the engine) but not the engine's internal stamping code (out of my scope — "you author specs, not code"). If you ratify F3=(a)-hybrid, dispatch workstream 2 to implement the stamp + re-vendor command.

**G2 — Per-asset metadata has no home in the flat manifest.** If the GUI later wants per-asset alt-text or a per-asset role, the flat markdown table can't carry it (F1 tradeoff). Not needed for v1 (tecer has none). Noted so a future need triggers a conscious format decision, not a hack.

**G3 — Multi-library / registry is explicitly out of v1** (locked exclusion). The convention is single-library. `library.json` has a `name` field so a future registry could key on it, but no registry contract is specified.

**G4 — Fragment preview / catalog rendering is the engine's job (workstream 2) and the GUI's (workstream 3).** The convention specifies that the engine MUST be able to render a catalog (every fragment, theme-injected, labeled) — tecer's `--catalog` proves it — and that this same rendering is the GUI's thumbnail source. I did not design the GUI preview mechanism (not my scope); I only pinned the data contract it consumes (theme + base + fragment = renderable unit).

**G5 — The exact `default_lang` semantics when a preset omits `lang`.** tecer's engine falls back `--lang` → preset `lang` → hardcoded `pt`. I generalized the final fallback to `library.json`'s `default_lang` (no tecer-hardcoded `pt`). Workstream 2 must implement that precedence: `--lang` flag > preset `lang` > `library.json default_lang`. Documented in § 6; flagged because it's a behavior the engine must get right and tecer's current code hardcodes `pt`.

---

## ASSUMPTIONS (stated, proceeding — challenge any)

**A1 — DT4's "nothing but what the library contains" is read literally** (the tool travels in the folder). This drove F3=(a)-hybrid. If you intend a softer reading ("the library + a standard RBTV install"), F3 could become (b) or (c) and the spec relaxes. I assumed literal because it is a *contracted* done-test and the dispatch stressed "libraries travel".

**A2 — The cold agent is NOT necessarily Claude Code.** Drove F6's `README-FOR-AGENTS.md` over `CLAUDE.md`. If you intend the cold agent to always be Claude Code, `CLAUDE.md` alone would suffice and the README becomes redundant — but I judged the generic reading safer and cheap (one extra file, with a thin `CLAUDE.md` pointer for the Claude-Code case).

**A3 — Engine stays stdlib-only Python** (locked: "stdlib-only Python engine"). This eliminated YAML/TOML libs from every format fork (F1, F7, F8, F10). All chosen formats parse with stdlib (`json`, hand-rolled markdown-table + minimal-YAML readers tecer already proved).

**A4 — Byte-exact deck reproduction is a non-goal for DT5** (lifted from tecer's e2e-report Decision F, which is live and authoritative). DT5's acceptance bar = structural + visual parity, deviations logged. If you want stricter (byte-exact), say so — but tecer already ruled it out for good reasons (canonical upgrades, asset optimization) and I followed the proven precedent.

**A5 — `title` as a new required manifest column is worth the migration cost** (every tecer row needs a title added). I judged yes: the GUI needs it and deriving it from HTML is fragile. The migration appendix handles backfill (derive from the slide's `.slide-title` text or the summary's leading phrase). If you'd rather keep the 9-column schema and have the GUI derive titles, override F2 and I'll drop the column.

---

## RATIFICATION CHECKLIST (for your reply)

| Fork | Topic | My rec | Your call |
|------|-------|--------|-----------|
| F1 | Manifest format | Markdown table | |
| F2 | Slide schema (10 cols, +`title`) | as specified | |
| **F3** | **Engine distribution** | **(a)-hybrid: vendored + versioned** | |
| F4 | Section declaration + order | `library.json` ordered list | |
| F5 | Asset roots | explicit `@root` + optional `extra_asset_root` | |
| F6 | Self-description file | `README-FOR-AGENTS.md` (req) + thin `CLAUDE.md` (opt) | |
| F6a | As-built gate | engine auto-writes (no manual gate) | |
| F7 | Versioning | `library.json` + semver-major compat check | |
| F8 | Presets format | keep prose + fenced YAML | |
| F8a/b | Deviation semantics | engine writes structural delta; human writes modified/bespoke | |
| F9 | Theme/base/token grammar | formalize tecer's | |
| F10 | As-built location | separate `as-built.md` | |
| F10a | As-built entry format | fenced YAML per entry | |

**12 forks (+4 sub-forks) awaiting ratification. F3 is the highest-leverage.**

Ratified rulings land in `convention-spec.md` § Amendments as ADX-1, ADX-2, … Executors cite "per ADX-N".
