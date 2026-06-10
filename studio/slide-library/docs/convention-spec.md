# RBTV Slide-Library Convention — v1 (Normative Specification)

**Status:** v1 draft for orchestrator ratification. Convention version `1.0`.
**Audience:** the RBTV assembly engine, the hypresent builder GUI, and any cold agent pointed at a library. This document is the single normative contract all three code against.
**Language:** MUST / NEVER are binding. SHOULD / RECOMMENDED are strong defaults a library MAY deviate from with reason. MAY is optional.

This spec defines a **slide library**: a self-describing folder from which a deterministic engine assembles single-file HTML presentation decks. A spec-compliant library serves two consumers identically: a graphical builder, and a cold autonomous agent given only the folder and a deck intent.

---

## 0. Terminology

| Term | Definition |
|------|------------|
| **Library** | A folder conforming to this spec. The unit that travels and is pointed at. |
| **Fragment** | One slide as a bare `<section>` HTML file in `slides/`. NEVER a full HTML document. |
| **Engine** | The stdlib-only Python program that assembles fragments into a deck. Vendored into the library (§ 1). |
| **Deck** | An assembled, single-file, self-contained `.html` output. NEVER stored inside the library. |
| **Manifest** | `manifest.md` — the strict table of every fragment's metadata. The source of truth. |
| **Preset** | A named, ordered fragment-id list in `presets.md` — a reusable composition. |
| **As-built entry** | A machine-readable record of one assembly, appended to `as-built.md` by the engine. |
| **`ready` fragment** | A fragment with NO creative-pass tokens — ships verbatim. |
| **`template` fragment** | A fragment with `{{TOKEN}}` slots a creative pass MUST fill. |
| **Token** | A `{{SCREAMING_SNAKE_CASE}}` placeholder (§ 6). Engine-filled or creative-pass. |

---

## 1. Library Layout

A spec-compliant library is a single folder containing the following. **Required** artifacts MUST exist; an engine MUST reject a library missing any required artifact (loud failure, no output).

```
{library}/
├── library.json            REQUIRED  convention version, engine version, config, ordered sections (§ 7)
├── README-FOR-AGENTS.md     REQUIRED  the cold-agent entry point — the self-description (§ 5)
├── manifest.md              REQUIRED  strict per-fragment metadata table (§ 2)
├── presets.md               REQUIRED  named compositions (MAY contain zero presets) (§ 3)
├── as-built.md              REQUIRED  append-only assembly log; engine writes here (§ 4)
├── base.html                REQUIRED  document skeleton with the 5 markers (§ 6)
├── theme.css                REQUIRED  the single design system, inlined at assembly (§ 6)
├── assemble.py              REQUIRED  the vendored engine (§ 1.1)
├── slides/                  REQUIRED  flat directory of {id}.html fragments (§ 2)
├── assets/                  REQUIRED  shared images referenced by fragments (MAY be empty)
├── catalog.html            OPTIONAL  engine-generated; every fragment rendered (§ 6.4)
├── CLAUDE.md               OPTIONAL  thin pointer to README-FOR-AGENTS.md for Claude-Code workspaces
└── docs/                   OPTIONAL  design notes, extraction logs — never read by the engine
```

### 1.1 The vendored engine (per F3 — ratify before building)

The engine's canonical source lives ONCE, centrally, in the RBTV repo at `html/slide-library/engine/assemble.py`. **A spec-compliant library MUST contain a copy of the engine at `{library}/assemble.py`.** This satisfies the cold-agent contract literally: the assembly tool travels inside the folder.

To prevent silent drift, the library's `library.json` records `engine_version` and the engine stamps the same version internally. On every run the engine MUST compare its own stamp against the `engine_version` in the `library.json` it reads and warn (not fail) on mismatch. The convention provides a documented re-vendor command (engine implementation — workstream 2) that copies the central engine over the library's copy and bumps the stamp.

> Engine-distribution model is fork F3 in `contract-author-notes.md` and is pending orchestrator ratification. If F3 is overridden to a bootstrap (b) or instructions-only (c) model, this section and § 5 change accordingly. Until ratified, build against the vendored-but-versioned model above.

### 1.2 Layout invariants (MUST)

- The library is ONE folder. All required artifacts are at its root except fragments (`slides/`) and shared images (`assets/`).
- `slides/` is FLAT — NEVER subfolders. Section grouping is metadata (§ 4), never directory structure.
- The library NEVER contains an assembled deck. Decks are build outputs written elsewhere.
- The library NEVER contains per-deck client data (a client logo, filled tokens, a client name). Client-identifying content enters ONLY the build output. (The "leakage rule": fragments and templates carry ZERO client data.)

---

## 2. The Manifest (`manifest.md`)

`manifest.md` is the source of truth for every fragment. It is a Markdown file containing a `## Slides` section with one strict table, and a `## Assets` section with a second table.

### 2.1 Format and parse rules

- The `## Slides` table's first row is the header and MUST be exactly the 10 columns below, in this order. An engine MUST `die()` on header mismatch. **Heading and header matching are CASE-SENSITIVE** (per RV-4): the section heading MUST be exactly `## Slides` (likewise `## Assets`, `## Presets`, `## As-built log`), and the column header cells MUST match the § 2.2 names exactly. A library author's `## SLIDES` or `Id` column is INVALID. (Divergence from tecer, which lower-cases the heading match — § 8.1.)
- The separator row is identified POSITIONALLY: it is the SECOND physical table row, immediately after the header — never identified by content (per RV-13). The engine skips exactly that one row and treats every later `|`-row as data. (Divergence from tecer's content-based `set(...) <= set("-: ")` guard, which would silently skip a degenerate all-dash data row — § 8.1.)
- Every subsequent `|`-delimited row is a fragment. A row whose cell count ≠ 10 is a loud failure (no output). An engine MUST `die()` with the line number.
- **A literal `|` is FORBIDDEN inside any cell** (per RV-2). The parser splits on `|` BEFORE any unescaping, so an in-cell pipe either over-counts the row (→ `die()`) or silently shifts columns. Backslash-escaping (`\|`) is NOT supported for v1 — a cell containing `\|` is still invalid. On a pipe-induced cell-count mismatch the engine MUST `die()` naming the offending row's `id` if recoverable, else the line number.
- Cells are trimmed of surrounding whitespace. Cells are single physical lines — no embedded newlines (rows are one line each); the engine MUST NOT add multi-line cell handling.
- **All enum-like values are lowercase and matched CASE-SENSITIVELY (exact string)** against their declarations (per RV-4): `kind` ∈ {`ready`, `template`}; `lang` is a lowercase ISO-639-1-style token (`pt`, `en`); `section` MUST exactly match a `library.json` `sections` entry. A miscased or unknown value (`Template`, `EN`, `Opening`) is INVALID — the engine rejects it (§ 2.5). Migration lowercases tecer's values (§ 9.2).
- Parsing requires only stdlib string operations — NEVER a YAML/TOML/CSV library.

### 2.2 The 10-column slide schema

| # | Column | Required | Values / rule |
|---|--------|----------|---------------|
| 1 | `id` | MUST | Unique kebab-case key. MAY carry a `.{lang}` suffix for bilingual concepts (`cover.pt`, `cover.en`). The contract key for presets, explicit order, and as-built records. Duplicate id = invalid library. **`--lang` NEVER rewrites or selects ids** (per RV-10): presets and `--slides` MUST list fully-qualified ids; the engine never auto-resolves a bare `cover` to `cover.pt` under `--lang pt`. An id with NO `.{lang}` suffix is language-neutral and passes any GUI language filter; a suffixed id matches the filter only when its `lang` equals the selected language. `--lang` is document-chrome only (fills `{{LANG}}`/`<title>` default), never slide selection. |
| 2 | `file` | MUST | `slides/{id}.html` — always path-prefixed, library-relative. The referenced file MUST exist on disk. |
| 3 | `section` | MUST | A section name declared in `library.json` `sections`. A value not declared there = invalid library (catches typos). Promoted to first-class: drives GUI left-pane grouping and catalog order. |
| 4 | `title` | MUST | Short human label (≤ ~8 words) for the GUI browse card and catalog. Distinct from the document `{{TITLE}}` and from `summary`. |
| 5 | `audience` | SHOULD | Advisory hint: `prospect` / `client` / `investor` / `general` (or library-defined). Sentinel `general` when unspecified. NEVER a hard selection filter — a slide tagged one audience MAY be used for another. |
| 6 | `lang` | MUST | Language code, RECOMMENDED ISO 639-1 (`pt`, `en`). The GUI language filter keys on this. |
| 7 | `kind` | MUST | `ready` (no tokens, ships verbatim) or `template` (has `{{TOKEN}}` slots needing a creative pass). The single most decision-bearing field. |
| 8 | `summary` | MUST | 1-2 sentence description; MUST disambiguate the fragment from its siblings. Free text; MAY contain commas. |
| 9 | `assets` | MUST | Comma-separated asset entries, or `-` for none. Resolution rules in § 2.4. |
| 10 | `provenance` | SHOULD | Origin marker `{source} ({date})`, or `-`. For `template` fragments it doubles as the exemplar pointer to read before filling tokens. |

### 2.3 The assets table

The `## Assets` section MUST contain a table with at least these columns: `file`, `description`, `used-by`. It inventories every shared image in `assets/`. The engine MAY validate that every fragment-referenced bare asset has an `## Assets` row, but the load-bearing check is existence on disk (§ 2.4).

### 2.4 Asset resolution (per F5)

Each entry in a fragment's `assets` cell resolves by these rules. The engine resolves ALL asset sources BEFORE writing any output (validation-before-write — a missing asset is a loud failure with zero partial output).

| Entry form | Resolves from | Example |
|------------|---------------|---------|
| bare filename | `{library}/assets/` | `cover-bg.jpg` |
| `@root/path` | the `extra_asset_root` declared in `library.json`, joined with `path` | `@root/logo-white.png` |
| `{client-logo}` | the engine's `--client-logo` flag (per-deck; never in the library) | `{client-logo}` |
| `-` | nothing | — |

Rules:
- A bare filename NEVER resolves from the extra root, regardless of any `/` it contains.
- `@root/...` entries are a validation error if `library.json` declares no `extra_asset_root`.
- A `{client-logo}` entry with no `--client-logo` flag passed is a loud failure.
- Asset filenames MUST NOT contain commas (the cell is comma-separated, so a comma mis-splits) and the cell is a single physical line (no embedded newlines — the engine adds no multi-line handling) (per RV-15).
- CSS-driven backgrounds COUNT as assets: if a fragment's variant pulls a background through inlined `theme.css` (`.slide--cover` → `cover-bg.jpg`, etc.), that filename MUST appear in the fragment's `assets` cell — the engine copies ONLY listed assets, so an unlisted background 404s in the output.

> **DIVERGENCE FROM TECER (per RV-7) — do NOT copy-port.** The engine MUST key extra-root resolution on the literal `@root/` PREFIX, NEVER on `/`-presence. Tecer's live `resolve_asset_source` triggers the repo root on `"/" in entry` (assemble.py:206) — that heuristic is INVERTED here: a bare `path/with/slash` resolves from `{library}/assets/` (and 404s if absent), never from the extra root. Porting tecer's `/`-branch is a defect. Only `@root/...` reaches `extra_asset_root`. (See § 8.1.)

### 2.5 What makes a library INVALID (manifest-related)

An engine MUST reject (loud, no output) a library where any of the following holds:
- `manifest.md` header row ≠ the 10 columns in § 2.2, or the section heading case ≠ `## Slides` / `## Assets` (per RV-4).
- Any slide row has ≠ 10 cells.
- Any cell contains a literal `|` (including `\|`) (per RV-2) — die naming the row id or line.
- Any MUST cell is empty after trim (per RV-14). The non-empty-required set is: `id`, `file`, `section`, `title`, `lang`, `kind`, `summary`. (`audience` and `assets` use the `general` / `-` sentinels respectively; `provenance` MAY be `-`.) An empty `id` is especially rejected — it would become the dict key `''` and silently shadow.
- Any `id` is duplicated.
- Any `kind` value ∉ {`ready`, `template`} (exact lowercase), or any `lang` not a lowercase token, or any `section` not declared in `library.json` `sections` — all matched case-sensitively (per RV-4).
- Any `file` references a non-existent fragment.
- Any referenced asset cannot be resolved (§ 2.4) at assembly time for the requested composition.
- A fragment file contains any of `<head`, `<style`, `<script`, `<html`, `<body` (substring scan of the raw fragment — the full § 6.3 invariant set, per RV-8).

The single consolidated, mechanically-decidable list of ALL validation rules (manifest, asset, fragment, version, lang) with their check method and error-vs-warning verdict is § 8.

### 2.6 Complete example manifest

```markdown
# RBTV demo-library manifest

Single source of truth for all slide fragments and presentation assets.

## Slides

| id | file | section | title | audience | lang | kind | summary | assets | provenance |
|----|------|---------|-------|----------|------|------|---------|--------|------------|
| cover-product.pt | slides/cover-product.pt.html | opening | Capa do produto | general | pt | template | Cover with product name + tagline + date over a dark background. | cover-bg.jpg | demo (2026-06-06) |
| cover-product.en | slides/cover-product.en.html | opening | Product cover | general | en | template | Cover with product name + tagline + date over a dark background (English). | cover-bg.jpg | demo (2026-06-06) |
| intro-pillars | slides/intro-pillars.html | intro | Three pillars | general | en | ready | One-liner plus three product pillars; ships verbatim. | - | demo (2026-06-06) |
| problem-cards | slides/problem-cards.html | diagnosis | Problem cards | prospect | en | template | Three problem cards the audience faces plus a synthesis aside. | - | demo (2026-06-06) |
| how-it-works | slides/how-it-works.html | product | How it works | general | en | ready | Dark slide: the product layer in three capabilities plus a callout. | bg-dark.jpg | demo (2026-06-06) |
| proof-metrics | slides/proof-metrics.html | proof | Proof metrics | general | en | template | Three metric cards plus a sources line; metrics filled per deck. | logo-mark.png | demo (2026-06-06) |
| pricing-tiers | slides/pricing-tiers.html | business-model | Pricing tiers | prospect | en | template | Three pricing tiers plus a two-ways-to-buy column. | - | demo (2026-06-06) |
| next-steps | slides/next-steps.html | next-steps | Next steps | prospect | en | template | A four-step path plus a door aside. | - | demo (2026-06-06) |
| closing | slides/closing.html | closing | Closing | general | en | ready | Lean closing statement plus a contact row and wordmark. | closing-bg.jpg, logo-mark.png | demo (2026-06-06) |

## Assets

| file | description | used-by |
|------|-------------|---------|
| `cover-bg.jpg` | Dark branded background for cover slides (theme.css `.slide--cover`). | Cover slides |
| `closing-bg.jpg` | Dark branded background for closing slides (theme.css `.slide--closing`). | Closing slides |
| `bg-dark.jpg` | Dark accent background for dark-variant slides (theme.css `.slide--dark`). | Dark slides |
| `logo-mark.png` | Product wordmark, white, transparent. | Cover, proof, closing |
```

---

## 3. Presets (`presets.md`)

A preset is a named, ordered composition. `presets.md` contains a `## Presets` section with one entry per preset: a prose intro paragraph followed by a fenced ` ```yaml ` block. A library MAY contain zero presets (the table-less assembly path always works via explicit ids).

### 3.1 Format and parse rules

- Each preset is a fenced ` ```yaml ` (or ` ```yml `) block. The engine finds all such blocks and matches on the `preset:` key.
- The block is parsed by the normative library-YAML subset (§ 4.1) — NEVER a YAML library. `slides:` is a flow list that MAY span multiple physical lines inside `[ ... ]`; all other preset keys are scalars.
- The prose intro is for human/agent reading (when to use the preset, deviation rules). The engine ignores it.

### 3.2 Preset schema

| Key | Required | Meaning |
|-----|----------|---------|
| `preset` | MUST | Unique preset name. |
| `slides` | MUST | Ordered list of fragment ids. Defines deck order exactly. Every id MUST exist in the manifest. |
| `lang` | MUST | Default document language for decks from this preset. |
| `title` | MAY | Default document title. |
| `audience` | MAY | Advisory audience hint. |

### 3.3 Deviation semantics (per F8)

A builder GUI or agent MAY start from a preset and then tweak the composition. The convention expresses this through the as-built record, NOT by mutating the preset:
- The preset file is the curated, stable composition — it is NEVER edited to record a one-off deck.
- The as-built entry's `slides:` list is ALWAYS the actual final ordered ids (ground truth).
- When a deck started from a preset, the as-built entry carries `preset: {name}` and a `deviations:` block describing the delta (§ 4.3).

### 3.4 Complete example preset file

```markdown
# demo-library presets

## Presets

<!-- One entry per named composition: a prose intro paragraph followed by a fenced YAML block. -->

### product-intro

First-touch product introduction for a prospect (English). Opens on the product cover, frames the three pillars, names the problems, shows how it works, and closes with proof and next steps. Use this when the audience is meeting the product for the first time; swap `pricing-tiers` in only when commercials are on the table.

```yaml
preset: product-intro
lang: en
title: Product Introduction
audience: prospect
slides: [cover-product.en, intro-pillars, problem-cards, how-it-works, proof-metrics,
         next-steps, closing]
```

### product-intro-pt

Brazilian-Portuguese first-touch introduction. Same spine as product-intro with the Portuguese cover.

```yaml
preset: product-intro-pt
lang: pt
slides: [cover-product.pt, intro-pillars, problem-cards, how-it-works, proof-metrics, closing]
```
```

---

## 4. The As-Built Log (`as-built.md`)

`as-built.md` is an append-only, machine-readable record of every assembly. **The engine MUST append one entry on every successful assembly** (both the GUI flow and the cold-agent flow inherit this automatically — there is no manual gate to forget). It is a SEPARATE file from `presets.md` so automatic appends never touch the hand-curated presets.

### 4.1 Format and the normative library-YAML subset (per RV-1)

The file has an `## As-built log` section. Each entry is a `### {entry-id}` heading followed by a fenced ` ```yaml ` block, parsed by the same minimal reader as presets.

**The library-YAML subset is NORMATIVE and shared by presets AND as-built entries.** It is NOT general YAML and is NOT defined by tecer's `_parse_yaml_block` (which only ever list-parses the `slides:` key — see the Divergences table § 8.1). The engine (workstream 2) implements a FRESH parser to exactly this grammar — explicitly NOT a copy-port of tecer's reader. The engine's writer MUST emit ONLY constructs in this grammar. Anything outside it is an engine bug, not a library to tolerate.

```
# ---- library-YAML subset (the ONLY grammar the engine reads or writes) ----
block        := ( line )*
line         := comment | blank | mapping_entry | block_list_item
comment      := optional_ws "#" .* NEWLINE          # ignored
blank        := optional_ws NEWLINE                  # ignored

mapping_entry := key ":" ws? value NEWLINE
key           := plain_scalar_no_colon              # e.g. preset, lang, slides, deviations
value         := scalar | flow_list | EMPTY         # EMPTY → this key owns the block-list lines that follow

scalar        := plain_scalar | quoted_scalar
plain_scalar  := any chars except a leading "[" or '"' ; trailing/leading ws stripped
quoted_scalar := '"' chars '"'                      # the surrounding quotes are STRIPPED;
                                                    #   value is the literal content between them
                                                    #   (engine_version "1.0" → the string 1.0, NOT "1.0")

flow_list     := "[" elem ( "," elem )* "]"         # MAY wrap across physical lines until "]"
elem          := plain_scalar                       # plain scalars only; NO ":" inside an element

block_list_item := optional_ws "-" ws rest NEWLINE  # belongs to the nearest preceding EMPTY-valued key
                                                    #   rest is ONE PLAIN STRING, verbatim, to end of line.
                                                    #   It is NEVER re-parsed as a nested mapping:
                                                    #   "- modified: x — y"  IS the string  "modified: x — y"
```

Grammar rules the engine MUST honor:
- A `key:` with an EMPTY value, immediately followed by one or more `- ` lines, is a **block list** whose elements are the verbatim strings after `- ` (each a single plain string, never a sub-mapping). This is how `deviations:` round-trips.
- A `key: [ ... ]` is an inline **flow list** of plain scalars. A `:` inside any element is FORBIDDEN (it breaks the comma-split) — block-list form is the only way to carry `:`-bearing lines such as `modified: …`.
- Quoted scalars unwrap: the value is the content between the quotes, quotes discarded. `engine_version: "1.0"` parses to the string `1.0`; the writer MAY quote on emit, and a re-parse yields the same string — round-trip holds.
- `#` comments and blank lines are ignored anywhere.
- The writer emits `deviations:` ALWAYS as a block list (one `- ` line per entry), NEVER as a flow list, because deviation lines carry `:` and `—`. An empty deviation set is emitted as the block-list-absent form `deviations: -` (single `-` scalar meaning "none"), NOT `deviations: []` — `[]` would parse as the one-element flow list containing the empty string under this grammar. (Fixture seed and migration both updated to `deviations: -`; see § 8.1 and the Negative-case matrix in fixture-spec § I.)

**Round-trip invariant (DT5 + migration validation):** for every entry the engine writes, `parse(write(entry)) == entry` field-for-field. The engine workstream's test task and the migration appendix (§ 9.5) both run this round-trip; a mismatch fails the gate.

### 4.2 Entry schema

| Key | Required | Filled by | Meaning |
|-----|----------|-----------|---------|
| `date` | MUST | engine | Assembly date (`YYYY-MM-DD`). |
| `timestamp` | SHOULD | engine | Full ISO-8601 timestamp for ordering within a day. |
| `output` | MUST | engine | Path the deck was written to, **relative to the library root** (per RV-12). For the seeded fixture entry this is a HISTORICAL SENTINEL — it records where the deck went; the file need not exist on disk (per RV-5). |
| `slides` | MUST | engine | The actual ordered fragment ids assembled (ground truth). Also the canonical record of order — there is no separate order field. |
| `lang` | MUST | engine | The document language used (the RESOLVED value after § 6.5 precedence). |
| `title` | MUST when non-default | engine | The RESOLVED document title actually used (the `--title` value, else the preset `title`, else the engine default). Recorded so DT5 replays the exact `<title>`/default. `-` only when the engine default was used and no title was supplied. (per RV-3) |
| `accent` | MUST when non-default | engine | The RESOLVED `--accent` hex actually injected, or `-` when no accent was passed (the `/* {{ACCENT_CSS}} */` marker was removed). (per RV-3) |
| `client_logo` | MUST when non-default | engine | The filename of the client logo asset copied into the deck's `assets/` when `--client-logo` was passed (the resolved leaf name), or `-` when no `--client-logo` was given. (per RV-3) |
| `engine_version` | MUST | engine | The engine version that produced the deck (enables DT5 reproduction with the matching engine). |
| `preset` | SHOULD | engine | The preset name if assembly started from one, else `-`. |
| `deviations` | MAY | engine + agent | Delta from the preset (§ 4.3). Valid with or without a `preset` (per the migration appendix); a deviation set against no preset records bespoke/modified facts only. |
| `order` | MAY | engine | When assembly started from a preset and the final order is a permutation of the preset's ids, `order: true` flags that a reorder occurred. The actual order is ALWAYS `slides` (no prose). (per RV-6) |
| `intent` | MAY | GUI / agent | Free-text deck intent (audience, occasion, language) — the cold-agent's stated goal. |
| `upstream` | MAY | agent | Upstream proposals made back to the library during this build, or `n/a`. |
| `retroactive` | MAY | agent | `true` for entries backfilled during migration from pre-discipline records (per the migration appendix). Absent/omitted for engine-written live entries. |

### 4.3 Deviation block

`deviations:` is a block list (§ 4.1) of plain-string lines using this vocabulary:
- `added: {id}` / `removed: {id}` — a fragment present/absent vs the named preset. Engine-filled (machine-decidable: set difference on the id lists).
- `modified: {id} — {what}` — a template fragment's filled content diverged from the canonical exemplar. Agent-only (MAY); creative-pass fact.
- `bespoke: {description}` — content with no library fragment. Agent-only (MAY); creative-pass fact. A `bespoke:` line MAY carry no id (e.g. recording a dropped slide with no replacement fragment) — the schema accepts it.
- `reordered: {description}` — order differs from the preset. Agent-only (MAY) prose, for human readability. The engine NEVER emits this — see below.

The engine fills ONLY the STRUCTURAL deltas it can decide deterministically: `added` / `removed` by set difference between the preset's id list and the assembled ids, and the boolean `order: true` (§ 4.2) when the assembled set equals the preset set but the sequence differs. The engine does NOT emit a prose `reordered:` line — for two permutations of the same set there is no single deterministic description, so the actual order is carried by `slides` and the fact-of-reorder by `order: true` (per RV-6). The engine NEVER fabricates `modified:` / `bespoke:` / `reordered:` lines — those are creative-pass facts appended by whoever fills tokens (out of v1 engine scope). An engine recording only what it can decide is the integrity rule.

### 4.4 DT5 — re-assembly validation use (mechanical bar, per RV-5/RV-12)

The as-built entry is designed so a known deck can be re-assembled from its record and compared. **Reproduction procedure** (replays the FULL recorded input, not just `slides`+`lang`):

1. Parse the entry. Re-run the engine at the matching `engine_version` with: `slides` (or `--preset` + the recorded `slides` as the order), the recorded `lang`, and — when each is non-`-` — the recorded `title` (`--title`), `accent` (`--accent`), and `client_logo` (`--client-logo`, the same asset). Write to a fresh reproduction path.

**Acceptance bar is a MECHANICAL property check — NO golden-byte files, NO visual-judgment escape.** Byte-exact reproduction is an explicit non-goal (canonical fragment upgrades and asset optimizations legitimately diverge an older original). Fixture acceptance is PROPERTY-BASED. A reproduction PASSES when ALL of:

1. **Order identity** — the slide ids and their order in the re-assembled deck EXACTLY equal the entry's `slides` (same ids, same sequence).
2. **Per-slide skeleton equality** — for each slide, the tag/class skeleton (element tree + `class` attributes, in document order) equals the original deck's, with the **text content of token-bearing nodes EXCLUDED** from the comparison. (The original was creatively filled; the reproduction's tokens are unfilled — only the structure is compared, never the filled prose.)
3. **Asset parity** — the set of filenames copied into the reproduction's `assets/` equals the set the original referenced, and every reference in the reproduction resolves on disk.
4. **Clean token report** — `--check` on the reproduction reports EXACTLY the template tokens expected unfilled (the set of `{{TOKEN}}`s in the composed templates) — no more, no fewer.
5. **Headed render sanity** — the reproduction loads in a visible browser, `theme.css` is applied, and the console shows zero errors.

**The "upgraded canonical copy" deviation class** (a slide differing because the library fragment itself changed between the original assembly date and the reproduction date) is acceptable ONLY when git history evidences a fragment change in that window. **Immediately post-migration this class is EMPTY by construction** (no fragment has changed since cutover) — so a fresh tecer reproduction MUST pass checks 1-5 with no excused diffs. The class is NOT a free pass for arbitrary content differences; absent git evidence, any skeleton diff is a FAILURE.

**Zero-deviation case** (the fixture seed, `deviations: -`): checks 1-5 apply with no excused diffs whatsoever — the cleanest possible DT5 case. The fixture ships NO committed expected-output file; the property checks above are run against a freshly re-assembled reproduction by the engine workstream's test task.

### 4.5 Complete example as-built entry

```markdown
# demo-library as-built log

## As-built log

<!-- One entry per assembled deck, appended by the engine on every assembly. -->

---

### 2026-06-06-acme-intro

```yaml
date: 2026-06-06
timestamp: 2026-06-06T14:22:05
output: ../decks/acme/2026-06-06-intro/product-acme-intro.html
preset: product-intro
slides: [cover-product.en, intro-pillars, problem-cards, next-steps, how-it-works, closing]
lang: en
title: Acme — Product Introduction
accent: "#B8875A"
client_logo: acme-logo.png
engine_version: "1.0"
order: true
deviations:
  - removed: proof-metrics
  - reordered: next-steps moved before how-it-works
  - modified: problem-cards — filled with Acme's three operational pains
intent: First-touch intro deck for Acme, prospect, English, kickoff meeting.
upstream: n/a
```

Reading this entry against the grammar (§ 4.1): `title` is a plain scalar; `accent: "#B8875A"` and `engine_version: "1.0"` are quoted scalars that unwrap to `#B8875A` and `1.0`; `slides` is a flow list of plain scalars; `order: true` is a plain scalar; `deviations:` has an EMPTY value and owns the three `- ` block-list lines, each a verbatim plain string (`removed: proof-metrics`, `reordered: …`, `modified: problem-cards — …`) — never re-parsed as sub-mappings. The engine emitted `removed: proof-metrics` + `order: true` (both machine-decidable: `proof-metrics` is in the `product-intro` preset but absent from `slides`, and the remaining set is a reorder); the agent appended the prose `reordered:` and `modified:` lines.
```

---

## 5. Self-Description — the Cold-Agent Interface (`README-FOR-AGENTS.md`)

`README-FOR-AGENTS.md` is the REQUIRED entry-point document that makes a cold agent succeed with NOTHING but the library folder. It is the contracted dual-consumer interface (done-test DT4). A library that lives inside a Claude-Code workspace SHOULD ALSO carry a one-line `CLAUDE.md` pointing here, so Claude-Code auto-load works.

The template below is the COMPLETE required content. A library author copies it verbatim and fills the `{...}` placeholders with that library's specifics. Sections marked REQUIRED MUST be present.

> **Executor note (per RV-18):** the `## 1`–`## 6` headings INSIDE the template below are the README's OWN headings — copy them verbatim into `README-FOR-AGENTS.md`. They are NOT this spec's top-level sections (§ 1–§ 9) and MUST NOT be conflated with them. Treat § 5.1's body as a literal block to copy.

### 5.1 The complete `README-FOR-AGENTS.md` template

````markdown
# Assembling Decks From This Slide Library — Agent Guide

You are pointed at a **slide library**: a folder from which you assemble a presentation
deck. Everything you need is in this folder. This guide is self-contained — read it
fully, then assemble.

## 1. What this library is

{One paragraph: what these slides are for, the brand/voice they carry, and the audiences
they target. NEVER put client-specific data here — slides are reusable inputs only.}

This library follows the RBTV slide-library convention. Its machine-readable contract:
- `library.json` — convention version, configuration, and the ordered list of sections.
- `manifest.md` — every slide with its metadata (the source of truth).
- `presets.md` — named, ready-to-use compositions.
- `as-built.md` — the log of past assemblies (the engine appends here automatically).

## 2. How to read the manifest

Open `manifest.md`. The `## Slides` table has one row per slide with these columns:
`id | file | section | title | audience | lang | kind | summary | assets | provenance`.

- **id** is the contract — you select slides by id.
- **section** groups slides by narrative role (sections are ordered in `library.json`).
- **lang** is the slide's language — filter to the deck's language.
- **kind** is `ready` (ships verbatim) or `template` (you MUST fill `{{TOKEN}}` slots).
- **summary** distinguishes a slide from its siblings — read it to choose between similar slides.
- **audience** is an advisory hint, NOT a hard filter — a slide tagged one audience may be used for another.

## 3. How to choose a composition

You were given a deck **intent**: audience, occasion, language. Choose one of:
- **A preset** — open `presets.md`. Each preset has a prose intro saying WHEN to use it.
  If one matches your intent, use its `slides` list and `lang`.
- **A custom order** — otherwise build an ordered list of ids yourself by reading the
  manifest: filter by `lang`, pick one opening / closing, and select body slides whose
  `section` and `summary` fit the occasion.

For bilingual concepts pick the right `.{lang}` id (e.g. `cover-product.pt` vs `cover-product.en`).
Your slide list MUST name fully-qualified ids — `--lang` sets the document language only; it NEVER
rewrites or auto-selects a `.{lang}` id for you. Ids with no `.{lang}` suffix are language-neutral and
fit any deck.

## 4. How to assemble (the exact tool invocation)

Run the engine that ships in this folder. From the library directory:

```bash
# From a preset:
python assemble.py --preset {preset-name} --out {OUTPUT_PATH} [--lang {lang}] [--title "{title}"] [--accent "#HEX"] [--client-logo {path}]

# From an explicit id order:
python assemble.py --slides id1,id2,id3 --out {OUTPUT_PATH} [--lang {lang}] [--title "{title}"] [--accent "#HEX"] [--client-logo {path}]
```

The engine: resolves the order → concatenates `base.html` + the chosen fragments →
inlines `theme.css` → renumbers slide numbers → injects language/title/accent →
copies each fragment's assets into a sibling `assets/` folder beside `{OUTPUT_PATH}` →
prints the list of unfilled `{{TOKEN}}`s (your fill to-do) → appends an entry to
`as-built.md` automatically (recording the resolved `slides`, `lang`, `title`, `accent`,
and `client_logo` actually used, so the deck is reproducible).

**Write the deck OUTSIDE this library** — never `--out` into the library folder
(its sibling `assets/` would collide with the library's own `assets/`). Default
`{OUTPUT_PATH}` convention when you have no project-specific one: `../decks/{slug}/{deck}.html`
relative to this library (`{slug}` = a short kebab name for the occasion). A GUI MAY override it.

**Confirm the log:** after assembly, open `as-built.md` and verify your new entry was appended
(the last `### {date}-{slug}` block, with your `slides` and `output`). If it is missing, the
assembly did not complete — do not ship.

## 5. The creative pass — filling tokens

After assembly, the engine lists every unfilled `{{TOKEN}}`. Fill them in the OUTPUT
file (NEVER edit the fragments):
- Tokens are `{{SCREAMING_SNAKE_CASE}}`. Each one in a template slide is preceded by an
  HTML comment stating what to author and at what depth — follow that comment.
- `ready` slides have no tokens — leave them verbatim.
- For a per-deck client logo/name, fill `{{CLIENT_LOGO_SRC}}` (drop the logo file into the
  output's `assets/` and reference it) and `{{CLIENT_NAME}}`.
- {{N}} slide numbers are already filled by the engine — do not touch them.

Verify when done:
```bash
python assemble.py --check {OUTPUT_PATH}   # MUST report zero unfilled tokens
```

## 6. Human / agent judgment — NOT automated

These remain your responsibility; the engine does not enforce them:
- **Freshness:** `ready` slides may carry facts that drift (counts, dates, metrics).
  Before shipping, verify every such fact is current. {Describe where the source of truth
  for these facts lives, or state "no time-sensitive facts in this library".}
- **Leakage rule:** slides carry ZERO client data. Read exemplar decks (the `provenance`
  column) to learn a template's SHAPE — NEVER copy their content into a fragment or another
  deck. Client copy enters ONLY this deck's output. If a fragment's `provenance` is a synthetic
  marker (e.g. `fixture (...)`, `original (...)`) with no real exemplar deck on disk, there is
  nothing to read — author the tokens from the template's authoring comments and your intent.
- **Upstream proposals:** if you improve a `ready` slide during a build (a sharper line, a
  corrected generic fact), propose it back: update `slides/{id}.html` + its manifest row +
  regenerate the catalog, and note it in your as-built entry's `upstream` field. Client-
  specific copy is NEVER upstreamed.
````

### 5.2 Why every section is required

The cold agent has no external instructions. Section 1 orients it; section 2 makes the manifest legible; section 3 is the selection logic; section 4 is the exact mechanical invocation (the single most important section — without it the agent cannot assemble); section 5 is the creative-pass contract; section 6 carries the governance that stays judgment (lifted from the proven informal convention's human-judgment classification). Omitting any section breaks DT4.

---

## 6. Theme and Base Contract

### 6.1 `base.html` — the document skeleton

`base.html` is the deck wrapper. It MUST contain exactly these 5 markers; the engine fills all 5 and MUST `die()` if any is absent:

| Marker | Filled with |
|--------|-------------|
| `{{LANG}}` | the document language (`<html lang="...">`) |
| `{{TITLE}}` | the document title, HTML-escaped (`<title>`) |
| `/* {{ACCENT_CSS}} */` | an optional `:root { --client-accent: #HEX; }` block, or removed if no `--accent` |
| `/* {{THEME_CSS}} */` | the entire `theme.css`, inlined verbatim |
| `<!-- {{SLIDES}} -->` | the concatenated fragment HTML, renumbered |

A complete reference `base.html`:

```html
<!DOCTYPE html>
<html lang="{{LANG}}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
/* {{ACCENT_CSS}} */
/* {{THEME_CSS}} */
</style>
</head>
<body>
<!-- {{SLIDES}} -->
</body>
</html>
```

> **Known limitation (per C5):** `base.html` MAY reference web fonts and an icon set via CDN (as the reference above does). Such a deck is self-contained for CSS and structure but requires network access to render fonts/icons. v1 does NOT mandate offline-completeness. A library MAY vendor fonts/icons and drop the CDN links for full offline decks.

### 6.2 `theme.css` — the design system

`theme.css` is the SINGLE design system for the library, inlined whole into every deck. It defines all component classes fragments use. It MUST exist; assembling without it would produce an unstyled deck, so its absence is a loud failure. It is the executable visual truth — fragments NEVER carry their own `<style>`.

### 6.3 Fragment contract and the token grammar

**Fragment invariant (MUST):** a fragment is a bare `<section class="slide ...">` element. It NEVER contains `<head>`, `<style>`, `<script>`, `<html>`, or `<body>`. Asset references are relative `assets/{filename}`. This invariant is load-bearing — the engine's inlining model and the editor's section detection both depend on it. A fragment violating it makes the library invalid (§ 2.5).

**Variant classes (RECOMMENDED):** `slide--cover`, `slide--closing`, `slide--dark`, `slide--soft`; a bare `slide` is the light/default. A library MAY define its own variants in `theme.css`.

**Token grammar (MUST):**
- A token is `{{SCREAMING_SNAKE_CASE}}` — uppercase letters, digits, underscores, between `{{` and `}}`.
- Numbered variants use suffixes `_1`, `_2`, `_3`, `_A`, `_B`, `_C` (`{{PAIN_1_TITLE}}`, `{{FRONT_A_DESC}}`).
- **Engine-filled tokens (RESERVED — a creative pass NEVER fills these):** `{{LANG}}`, `{{TITLE}}` (in `base.html`); `{{N}}` (slide number, in fragments).
- **Creative-pass tokens:** every other token. Filled in the OUTPUT, never in the fragment.
- **`{{N}}` renumbering:** the engine replaces `<div class="slide-number">{{N}}</div>` sequentially (1-based) across the assembled body. The counter advances ONLY on a real `{{N}}` token; a fragment with no such div is unnumbered (covers, dividers).
- **Client-lockup tokens (RECOMMENDED names):** `{{CLIENT_LOGO_SRC}}` (path to a per-deck client logo) and `{{CLIENT_NAME}}` (display name / alt text / fallback). The convention names them so the GUI, the agent, and the editor agree; a library MAY use other names.

**Token authoring comments (RECOMMENDED):** each `{{TOKEN}}` in a `template` fragment SHOULD be immediately preceded by an HTML comment stating what to author and at what depth — this comment IS the machine-readable fill-spec for the creative pass. Example from a template fragment:

```html
<!-- PAINS_KICKER: short framing of the audience's situation (e.g., "A group in formation") -->
<div class="kicker">{{PAINS_KICKER}}</div>
<!-- PAINS_TITLE: headline naming the structural difficulty they face, 6-10 words -->
<div class="slide-title">{{PAINS_TITLE}}</div>
```

### 6.4 Catalog rendering (engine capability)

The engine MUST support regenerating `catalog.html`: every manifest fragment, in `library.json` section order then manifest order, each preceded by a label bar (`id · kind · audience · lang · summary`), with `theme.css` inlined and no client accent. The catalog is the reusable fragment-preview mechanism the GUI draws thumbnails from. `catalog.html` is a generated artifact (OPTIONAL on disk; regenerated on demand).

### 6.5 Language fallback precedence (per G5, extended per RV-9)

When resolving the document language, the engine MUST apply this precedence by mode. The convention NEVER hardcodes a language — `default_lang` is the library's declared fallback.

| Mode | Precedence |
|------|-----------|
| `--preset` | `--lang` flag > the chosen preset's `lang` > `library.json` `default_lang` |
| `--slides` (no preset) | `--lang` flag > `library.json` `default_lang` |
| `--catalog` | `library.json` `default_lang` (no `--lang`, no preset) |

> **DIVERGENCE FROM TECER (per RV-9) — do NOT copy-port.** Tecer hardcodes `"pt"` as the terminal fallback in all three modes (assemble.py:424 preset, :430 `--slides`, :378 catalog) and reads NO `default_lang` / `library.json` at all. The engine MUST read `default_lang` from `library.json` and MUST NOT hardcode `"pt"`. (See § 8.1.)

---

## 7. Convention Versioning (`library.json`)

`library.json` is a REQUIRED stdlib-`json` file at the library root. It carries the version contract and library configuration.

### 7.1 Schema

| Key | Required | Meaning |
|-----|----------|---------|
| `convention_version` | MUST | The convention version this library targets, `MAJOR.MINOR` (e.g. `"1.0"`). |
| `engine_version` | MUST | The version of the vendored engine in this library (§ 1.1). |
| `name` | MUST | Human-readable library name (a future registry could key on it). |
| `default_lang` | MUST | Fallback document language (§ 6.5). |
| `sections` | MUST | ORDERED list of section names. The manifest `section` column MUST reference one of these. Defines GUI grouping order and catalog order. |
| `extra_asset_root` | MUST (MAY be `null`) | Path, library-relative, for `@root/...` asset resolution (§ 2.4), or `null` if unused. |

### 7.2 Compatibility check (MUST)

The engine declares the convention version(s) it supports. On every run it reads `library.json` and:
- If `convention_version` MAJOR is unsupported → `die()` loud (a major bump is breaking).
- If MINOR differs from what the engine targets → warn and proceed.
- If the engine's own stamp ≠ `engine_version` → warn (vendored engine drift, § 1.1).

### 7.3 Complete example `library.json`

```json
{
  "convention_version": "1.0",
  "engine_version": "1.0",
  "name": "demo-library",
  "default_lang": "en",
  "sections": [
    "opening",
    "intro",
    "diagnosis",
    "product",
    "proof",
    "business-model",
    "next-steps",
    "closing"
  ],
  "extra_asset_root": null
}
```

---

## 8. Validation Rules (consolidated) (per RV-8)

The single, mechanically-decidable list of every validation rule the engine enforces. One row per rule: the check, its decidable method, whether a violation is an ERROR (`die()`, no output) or a WARNING (proceed), and the section of origin. This table is authoritative; where a prose section and this table appear to differ, this table governs the verdict.

| # | Check | Decidable method | Verdict | Origin |
|---|-------|------------------|---------|--------|
| 1 | Required artifacts present | each path in § 1 tree marked REQUIRED exists | ERROR | § 1 |
| 2 | `## Slides` heading + header row | exact case-sensitive `## Slides`; header cells == the 10 § 2.2 names | ERROR | § 2.1 |
| 3 | Separator row | second physical table row skipped positionally | (parse step) | § 2.1 |
| 4 | Slide row cell count | split on `\|` → exactly 10 cells | ERROR (die w/ line) | § 2.1 |
| 5 | No pipe in cell | raw cell text contains no `\|` | ERROR (die w/ row id or line) | § 2.1 |
| 6 | Non-empty required cells | `id,file,section,title,lang,kind,summary` non-empty after trim | ERROR | § 2.5 |
| 7 | `kind` enum | exact-string ∈ {`ready`,`template`} | ERROR | § 2.2 |
| 8 | `lang` token | lowercase ISO-639-1-style token | ERROR | § 2.2 |
| 9 | `section` declared | exact-string ∈ `library.json` `sections` | ERROR | § 2.2 |
| 10 | Unique ids | no duplicate `id` across rows | ERROR | § 2.2 |
| 11 | Fragment file exists | `{library}/{file}` exists on disk | ERROR | § 2.5 |
| 12 | Fragment purity | substring scan of raw fragment for `<head`, `<style`, `<script`, `<html`, `<body` → none present | ERROR | § 6.3 |
| 13 | Asset resolves | each composed asset entry resolves per § 2.4 (bare→`assets/`, `@root/`→`extra_asset_root`, `{client-logo}`→`--client-logo`) and exists | ERROR | § 2.4 |
| 14 | `@root` without root | any `@root/` entry while `extra_asset_root` is `null` | ERROR | § 2.4 |
| 15 | `{client-logo}` without flag | a composed `{client-logo}` entry with no `--client-logo` | ERROR | § 2.4 |
| 16 | Asset-cell hygiene | no comma inside a filename; cell is one physical line | ERROR | § 2.4 |
| 17 | `## Assets` row completeness | every fragment-referenced BARE asset has an `## Assets` row | WARNING | § 2.3 |
| 18 | `base.html` markers | all 5 markers present | ERROR | § 6.1 |
| 19 | `theme.css` present | file exists | ERROR | § 6.2 |
| 20 | Convention MAJOR | `convention_version` MAJOR is supported | ERROR | § 7.2 |
| 21 | Convention MINOR | MINOR == engine target | WARNING | § 7.2 |
| 22 | Engine stamp drift | engine stamp == `library.json` `engine_version` | WARNING | § 1.1, § 7.2 |
| 23 | As-built round-trip | `parse(write(entry)) == entry` for every emitted entry | ERROR (DT5/migration gate) | § 4.1 |
| 24 | `--check` token report | output file scanned for residual `{{TOKEN}}` | reports (exit 1 if any) | § 6.3 |

Note: the live tecer engine implements NONE of the purity scan (check 12), the `library.json` checks (20-22), or the round-trip check (23) — those are new engine work (§ 8.1).

### 8.1 Divergences from tecer's informal implementation

This is the FIRST table the engine-port and migration-converter executors read. Each row is a place where v1 consciously diverges from tecer's live `assemble.py`/`manifest.md` — porting the live behavior is a DEFECT. (Ratified divergences from ADX-1/ADX-3 are the basis; the RV findings pin the unstated ones.)

| # | Dimension | Tecer live behavior (file:line) | v1 convention behavior | Source |
|---|-----------|----------------------------------|------------------------|--------|
| 1 | Manifest columns | 9 columns, no `title` (manifest.md:7) | 10 columns; `title` at position 4 | ADX-1 / RV-3 |
| 2 | As-built YAML | `_parse_yaml_block` list-parses ONLY `slides`; every other key scalar; quotes kept literally (assemble.py:146-181) | Normative library-YAML subset (§ 4.1): block lists for `deviations`, flow list for `slides`, quoted scalars unwrap. Fresh parser, NOT a port. | RV-1 |
| 3 | Pipe in cell | split on `\|`, no guard (assemble.py:64-72) — dies or silently shifts | `\|` FORBIDDEN; die naming row/line | RV-2 |
| 4 | As-built inputs | only `slides`/`lang` recoverable; `title`/`accent`/`client-logo` lost | record resolved `title`/`accent`/`client_logo` | RV-3 |
| 5 | Heading match | case-INsensitive `stripped.lower() == "## slides"` (assemble.py:91) | case-SENSITIVE `## Slides` | RV-4 |
| 6 | Enum case | unpinned (no enum validation) | lowercase, case-sensitive exact match for `kind`/`lang`/`section` | RV-4 |
| 7 | Separator row | content-based `set(...) <= set("-: ")` (assemble.py:106) | positional: 2nd table row only | RV-13 |
| 8 | Empty required cells | passes (`''` is a valid trimmed cell) | rejected for the non-empty-required set | RV-14 |
| 9 | DT5 parity bar | "visual diff judgment" + "upgraded canonical copy" excuse | mechanical property bar (§ 4.4); no golden bytes; no visual-judgment escape | RV-5 / ADX-1 A4 |
| 10 | `reordered` deviation | n/a (no engine deviation-fill) | engine emits `order: true` only; prose `reordered:` is agent-only MAY | RV-6 |
| 11 | Asset extra-root trigger | `"/" in entry` → REPO_ROOT (assemble.py:206) | literal `@root/` prefix → `extra_asset_root`; `/`-presence is NOT a trigger | ADX-3 / RV-7 |
| 12 | Cross-root path (tecer) | `cover-investor` uses `brand/logo/tecer-logo-white-transparent.png` (manifest.md:48) | vendor the PNG into `assets/`, rewrite to bare filename, `extra_asset_root: null` (the RULED tecer migration); `@root` stays a generic feature | ADX-3 / RV-7 |
| 13 | Lang fallback | hardcoded `"pt"` in all modes (assemble.py:424,430,378), no `library.json` | `--lang` > preset `lang` (preset mode only) > `library.json` `default_lang`; `--slides` and `--catalog` fall back to `default_lang`, never `"pt"` | RV-9 |
| 14 | `--lang` and id selection | `--lang` fills `{{LANG}}` only (assemble.py:272); no id rewriting | EXPLICIT: `--lang` never selects/rewrites ids; presets list fully-qualified ids; unsuffixed ids are language-neutral; GUI filter: match if `lang` == selected OR id has no `.{lang}` suffix | RV-10 |
| 15 | As-built location | inside `presets.md` `## As-built log` (presets.md:60) | separate `as-built.md` (engine auto-appends; never touches curated presets) | ADX-1 F10 |
| 16 | Sections | free strings in manifest order (no declaration) | declared ORDERED list in `library.json` `sections`; manifest `section` MUST reference one | ADX-1 F4 |
| 17 | Fragment purity | no scan exists in tecer | substring scan for `<head`/`<style`/`<script`/`<html`/`<body` (new engine work) | RV-8 |
| 18 | `library.json` | absent in tecer | REQUIRED; convention+engine version, `default_lang`, ordered `sections`, `extra_asset_root` | ADX-1 |
| 19 | Engine distribution | tecer-anchored `LIB`/`REPO_ROOT` constants | vendored copy at `{library}/assemble.py`, `engine_version` stamp, re-vendor command | ADX-1 F3 |

---

## 9. Migration Mapping Appendix — Tecer's Informal Library → This Convention

This appendix maps the proven informal convention (tecer's `slide-library/`) to v1, dimension by dimension. Migration is mechanical; the live sales library MUST keep producing decks throughout (no broken weeks). The engine is built and verified against the synthetic fixture (`fixture-spec.md`) BEFORE it touches tecer's library.

### 9.1 Artifact-by-artifact mapping

| Tecer artifact | v1 target | Migration action |
|----------------|-----------|------------------|
| `manifest.md` (`## Slides`, 9 columns) | `manifest.md` (`## Slides`, 10 columns) | Insert a `title` column (position 4) into every row; backfill via the deterministic chain in § 9.5; one-pass human-quality review of all 57 titles before commit (per RV-11). Lowercase any miscased `section`/`lang`/`kind` value (per RV-4). Scan all 57 rows for literal `\|` BEFORE conversion (per RV-2) — current corpus is pipe-free (verified), reject any future pipe. |
| `manifest.md` `## Assets` (3 cols) | `manifest.md` `## Assets` | Unchanged — already conformant. |
| `presets.md` `## Presets` (prose + YAML) | `presets.md` `## Presets` | Unchanged format. Optionally add `title`/`audience` keys. |
| `presets.md` `## As-built log` (11 retro entries, prose-ish) | `as-built.md` `## As-built log` (fenced YAML entries) | EXTRACT the 11 entries into the new file, converting each to the § 4.2 schema in the library-YAML subset (§ 4.1): `deviations` as a block list (one `- ` plain-string line per deviation; empty set → `deviations: -`), `slides` as a flow list. Mark each `retroactive: true`. Set `engine_version` to the migrated engine version; `date` per § 9.5 (year-only entries backfilled from the git commit date); `preset` where the entry maps to a named preset (`investor-small`↔small-deck-v3-1, etc.), else `-`. Preserve every deviation line's CONTENT verbatim as a block-list string — NEVER as a sub-mapping (the line `modified: x — y` becomes the string `modified: x — y`). The 11→library-YAML conversion is round-trip-tested (§ 9.5). |
| `CLAUDE.md` (agent workflow, Claude-Code-specific) | `README-FOR-AGENTS.md` (REQUIRED) + thin `CLAUDE.md` (OPTIONAL pointer) | Author `README-FOR-AGENTS.md` from the § 5.1 template, porting tecer's MUST-step content into the matching sections (selection → § 3-mapped section 3; leakage/freshness/upstream → section 6). Replace tecer's `CLAUDE.md` body with a one-line pointer to `README-FOR-AGENTS.md`. |
| `assemble.py` (440 lines, tecer-anchored paths) | `assemble.py` (vendored RBTV engine) | Replace with the RBTV engine (workstream 2). The engine reads `--library` / library-relative paths and `library.json` instead of the hardcoded `LIB`/`REPO_ROOT` constants. (per F3) |
| `base.html` (5 markers) | `base.html` | Unchanged — already conformant. |
| `theme.css` | `theme.css` | Unchanged. |
| `catalog.html` (generated) | `catalog.html` (generated) | Regenerate with the new engine. |
| (none) | `library.json` (REQUIRED) | CREATE. `convention_version: "1.0"`; `name: "tecer"`; `default_lang: "pt"`; `sections:` the ordered union of tecer's section values (lowercased, per RV-4); `extra_asset_root: null` per ADX-3 (the cross-root PNG is vendored into `assets/` — see 9.3, BINDING). |

### 9.2 Dimension mapping (metadata)

| Dimension (tecer) | v1 home | Note |
|-------------------|---------|------|
| section (free string, manifest order) | `section` column + ordered `library.json` `sections` | Sections become first-class & ordered (F4). Collect tecer's ~16 distinct section values into the ordered list, LOWERCASED and matched case-sensitively thereafter (per RV-4). |
| audience (4 values) | `audience` column (advisory) | Unchanged; stays advisory, never a hard filter. Lowercase values (per RV-4). |
| lang (column + filename suffix) | `lang` column | Lowercase the `lang` value (tecer's `pt-BR` retro prose → token `pt`; per RV-4). Bilingual `.{lang}` id suffix unchanged; `--lang` never selects ids (per RV-10). |
| kind (ready/template) | `kind` column | Unchanged values (already lowercase) — the decision-bearing field, now matched case-sensitively (per RV-4). |
| summary | `summary` column | Unchanged. |
| assets (two-root, implicit `/`) | `assets` column (explicit `@root`) | Rewrite the ONE cross-root entry (9.3). |
| provenance | `provenance` column | Unchanged; now formally optional with `-` sentinel. |
| variant (HTML `<section>` class) | fragment HTML | Unchanged — stays in the fragment, not the manifest. |
| token inventory + comments | fragment HTML | Unchanged — formalized as the fill-spec (§ 6.3). |
| (no title) | `title` column | NEW — backfill (9.1). |

### 9.3 Known tecer irregularities and how migration handles each

| Irregularity (from recon + live verification) | Handling |
|-----------------------------------------------|----------|
| **Slide-count drift: `CLAUDE.md` says "54", recon says "58", live manifest is "57".** (Contradiction C1; live-verified: 57 manifest rows = 57 disk files, zero drift.) | Migration derives ALL counts from the live manifest, NEVER from any prose string. The new convention puts NO count in any prose file — `manifest.md` IS the count. The stale "54" in tecer's `CLAUDE.md` is discarded when that file becomes a thin pointer. |
| **As-built log lives inside `presets.md`.** (recon § 6) | Extract to a separate `as-built.md` (F10) so the engine's automatic appends never touch curated presets. |
| **All 11 as-built entries are retroactive (`upstream: n/a (retro)`) — the log was never a live discipline.** (recon orchestrator-note #4) | Resolved structurally: the new engine writes the entry AUTOMATICALLY on every assembly (F6a). The 11 retro entries migrate as historical records; from cutover forward, entries are engine-written and live. |
| **Two-root asset resolution is implicit (`/` = repo root) and fragile.** (recon orchestrator-note #3) | Per **ADX-3 (BINDING)**: vendor the single cross-root PNG into the library's `assets/` and drop `@root` for tecer (`extra_asset_root: null`). `@root` + `extra_asset_root` stay generic convention features (a fixture exercises them), NOT a tecer choice. **Exact cutover edit:** tecer's only `/`-cross-root user is `cover-investor` at manifest row 48, whose `assets` cell reads `cover-bg.jpg, brand/logo/tecer-logo-white-transparent.png`. The PNG is byte-identical (md5) to the already-present library `tecer-wordmark-white.png`. At cutover: (1) copy `brand/logo/tecer-logo-white-transparent.png` into `slide-library/assets/` as `tecer-logo-white-transparent.png` (or reuse the existing byte-identical `tecer-wordmark-white.png`); (2) rewrite manifest row 48's asset cell from `brand/logo/tecer-logo-white-transparent.png` to the bare filename. No other manifest row references a cross-root path (verified). This is the engine keying on `@root/` not `/`-presence (§ 8.1 #11) — after the rewrite there is no `/`-bearing asset entry left. |
| **`--client-logo` accepted but unused when no fragment lists `{client-logo}`.** (recon C3; live-verified) | The convention documents the two distinct mechanisms (§ 2.4 asset-cell `{client-logo}` served by `--client-logo`, vs the `{{CLIENT_LOGO_SRC}}` creative-pass token). No migration action — tecer keeps using the token path; the flag stays harmless. |
| **Prose-only optionality / governance buried in `CLAUDE.md` MUST steps.** | The mechanically-enforceable steps become engine behavior (assemble, renumber, asset copy, token report, check, auto-log); the judgment steps (freshness, leakage, upstream) move to `README-FOR-AGENTS.md` § 6 verbatim in intent. |

### 9.4 Cutover ordering (migration risk control)

The migration cutover plan (problem-tree 4.3) is NOT this spec's scope, but the convention constrains it: the engine MUST pass the fixture (`fixture-spec.md`) AND reproduce a known tecer deck to the § 4.4 parity bar BEFORE replacing tecer's `assemble.py`. The reference reassembly precedent already proved this is achievable for one deck.

### 9.5 Deterministic backfills and migration validation (per RV-11/RV-1/RV-2/F8-misc)

**Title backfill chain (deterministic, per RV-11).** For each of the 57 rows, the converter produces a DRAFT `title` by the FIRST rule that yields a non-empty string:

1. The text content of the fragment's `.slide-title` element, if present.
2. Else the text content of the first heading-like element in the fragment, in this order: `.cover-title`, `.divider-statement`, then the first of `.kicker`/`.card-title` — i.e. the first prominent label the fragment carries (covers use `.cover-title`; dividers use `.divider-statement`; header-less dark slides fall through to their first label).
3. Else the `summary`, truncated at the FIRST of `.`, `;`, `:` OR 6 words — whichever comes first (the orchestrator's ≤6-word cap).
4. Else the humanized `id` (kebab → spaced, capitalized).

The chain NEVER blocks — rule 4 always yields. The output is a DRAFT: the migration agent does a ONE-PASS human-quality review of all 57 backfilled titles BEFORE commit (titles are GUI labels, low blast radius). Verified examples: `cover-client` has no `.slide-title` → rule 2 `.cover-title`; `nimbus`-style dividers → rule 2 `.divider-statement`; a row whose fragment leads with `.kicker` → rule 2's fallback or rule 3's summary clause.

**`date` backfill for year-only retro entries (per F8-misc).** § 4.2 requires `date: YYYY-MM-DD`, but three tecer retro entries record only a year or month: `tecer-institucional` (`2026`), `small-deck-v3` and `small-deck-v3-1` (`2026-05`). Backfill each from the git commit date that introduced that entry's line in tecer's `presets.md` (the durable record of when the deck was logged). Mark every migrated entry `retroactive: true` (§ 4.2). The `date` is the git commit date; `timestamp` MAY be omitted for retro entries (it is SHOULD, not MUST).

**`bespoke:`-only and orphan survival (per F8-misc).** The schema MUST accept: (a) a `bespoke:` deviation line carrying no id (small-deck-v3's `bespoke: v3 drops the-ask slide …` — a dropped slide with no replacement fragment) — § 4.3 allows id-less `bespoke:`; (b) a library slide referenced by NO preset (`intro-anchors.en` is orphan-from-presets in tecer) — the convention places NO validation rule rejecting a manifest slide absent from all presets (presets MAY omit slides; § 3). The migration confirms both survive; neither is a validation error.

**Round-trip + pipe-scan validation (per RV-1/RV-2).** Migration validation runs two programmatic checks before cutover:
- **Round-trip:** for every converted as-built entry, `parse(write(entry)) == entry` field-for-field under the library-YAML subset (§ 4.1, § 8 check 23). A mismatch (e.g. a deviation line that does not round-trip as a block-list string) FAILS migration.
- **Pipe scan:** scan all 57 manifest rows for a literal `\|` in any cell BEFORE conversion (§ 8 check 5). The current corpus is pipe-free (verified); any pipe found is rejected, not escaped.

---

## Amendments (ADX)

> Append-only. Orchestrator rulings during execution land here as `ADX-N`. Executors cite "per ADX-N". Each entry: `ADX-N — {date} — {fork or topic} — {ruling}`.

- **ADX-1 — 2026-06-06 — Ratification round (contract-author-notes.md forks).** F1, F2, F4, F5, F6, F6a, F7, F8, F8a, F8b, F9, F10, F10a: ALL RATIFIED as authored. **F3 RATIFIED as (a)-hybrid**: engine vendored at `{library}/assemble.py` (required artifact), `engine_version` stamp in `library.json`, documented re-vendor command; canonical source `html/slide-library/engine/assemble.py`. Assumptions A1–A5 accepted (A1: DT4 read literally; A4: DT5 bar = structural + visual parity, byte-exact non-goal).
- **ADX-2 — 2026-06-06 — GUI engine face (cross-workstream ruling).** The hypresent builder page consumes the TARGET LIBRARY's own vendored engine via subprocess — never a separate central code path — using a machine-readable output mode whose exact form workstream 2 designs. Version-stamp mismatch warnings surface in the GUI. Rationale: one behavior source per library; the GUI is a gesture layer over the same contract the cold agent uses.
- **ADX-3 — 2026-06-06 — Tecer cross-root asset.** Migration vendors the single cross-root PNG (`brand/logo/tecer-logo-white-transparent.png`) into the library's `assets/` and drops `@root` usage for tecer. The convention KEEPS `@root` + `extra_asset_root` for generality.
- **ADX-4 — 2026-06-07 — Replay mode (`--no-log`).** The engine gains a `--no-log` flag: a VERIFICATION/REPLAY mode that performs the full assembly but suppresses the § 4 as-built append. The § 4 MUST ("append one entry on every successful assembly") binds every PRODUCTION assembly — GUI flow, cold-agent flow — and those flows NEVER pass `--no-log`. Legitimate uses are exactly: DT5/§ 4.4 reproduction runs (re-assembling a known deck to compare — recording the replay would pollute the log it validates) and automated test/verification harnesses (which additionally run on TEMP COPIES of libraries, never on committed/live ones). `README-FOR-AGENTS.md` does NOT advertise the flag. In `--json` mode with `--no-log`, the envelope's `as_built_entry` field carries the entry that WOULD have been written, marked `"logged": false`.
- **ADX-10 — 2026-06-07 — Fixture-spec §C erratum (PB-T1 halt).** The `nimbus-intro-pt` preset YAML in `fixture-spec.md` §C was missing `nimbus-divider` (6 ids) while §C's own prose ("Same spine as nimbus-intro-en") and §H check 11 (7 ids per preset) demand it. RULED: the prose + check are the intent; the pt `slides:` list gains `nimbus-divider` after `how-nimbus-works`, mirroring the en preset. Fixture-spec amended in place; PB-T1's session resumed to re-copy `presets.md` and re-run §H. (ADX-5..9 live in build-spec § Amendments; ADX numbering is session-global.)
- **ADX-11 — 2026-06-07 — Rule 15 affirmed; happy-path tests carry the flag (PB-T3 halt, bug 1).** `{client-logo}` composed without `--client-logo` is an ERROR exactly as § 8 rule 15 and fixture-spec § I rule 15 pin — the engine implemented the contract correctly; the T3 happy-path tests were the defect. RULED: every fixture happy-path assembly that composes a cover passes `--client-logo` with the fixture's `tests/shared-brand/partner-mark.png` (also exercising the § 4.2 `client_logo` as-built key). Tecer impact: none — tecer's manifest does not use the asset-cell sentinel (token path only, recon C3).
- **ADX-12 — 2026-06-07 — Parser is grammar-faithful; `-` is the literal string (PB-T3 halt, bug 2).** `parse_yaml_subset` returns EXACTLY what the § 4.1 grammar produces: `deviations: -` parses to the plain scalar `"-"`. No key-specific normalization inside the parser (the engine's `[]`-conversion and the test's `"none"` expectation were both inventions). Consumers (DT5 comparator, GUI, § H checkers) interpret `"-"` as the none-sentinel per § 4.2. Bugs 3 (`:` in flow element not rejected — § 4.1 `elem` forbids it, § I rule 23 = ERROR) and 4 (mid-line `#` stripping corrupts quoted scalars like `"#B8875A"` — the grammar has WHOLE-LINE comments only) are engine defects to fix as specced.
- **ADX-13 — 2026-06-07 — § 4.4 check 5 refined for unfilled reproductions (PB-T19 halt).** Check 5's zero-console-error requirement EXCLUDES resource-load errors (ERR_FILE_NOT_FOUND and kin) caused by UNFILLED `{{TOKEN}}`s sitting in URL-bearing attributes (`src`/`href`) — that error class is the expected signature of an unfilled-by-design reproduction and is already asserted PRESENT by check 4's token report. Script/runtime console errors remain fatal. Companion writer rule (engine defect found same halt): `write_yaml_subset` emits a string value as a SCALAR always — `deviations` whose value is the `-` sentinel string round-trips as `deviations: -`, never as a one-item block list; block-list emission is reserved for list values.
