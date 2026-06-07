# prez-builder v1 — Build Spec (normative, S-numbered)

**Status:** authored 2026-06-06 against the FROZEN contract (`html/slide-library/docs/convention-spec.md` v1, ADX-1..3) and `fixture-spec.md`. This document is the build's normative target. The convention is REFERENCED by section (`convention-spec §N.M`) and NEVER duplicated — where a behavior is contract-defined, this spec cites the section and adds only build-specific detail (file paths, CLI surface, endpoints, UX flow, migration steps).

**Consumers:** Kimi non-reasoning executors (one task file each), the cold verifier (DT4/DT5/EX2), the migration converter. Every S-requirement maps to ≥1 task in `docs/plan/prez-builder-v1/prez-builder-v1-plan.md` (traceability table there).

**Module homes (per U3-S4, D6-S4, D7-S4):**
- ENGINE canonical source: `html/slide-library/engine/assemble.py` (SINGLE FILE, section-disciplined internally — D6-S4 vendoring atomicity). Re-vendor tool: `html/slide-library/engine/install-engine.py`. Engine unit tests: `html/slide-library/engine/tests/`.
- EXPERIENCE: a second static page `html/hypresent/app/builder.html` + its own JS modules under `html/hypresent/app/js/builder/` + a new server module `html/hypresent/server/builder_api.py`. Hypresent app/server code stays MODULAR (D6-S4) — no monolith. e2e suites under `html/hypresent/tests/e2e/`.
- MIGRATION: a conversion script that lives IN tecer-biz on a dedicated branch (`5-workbench/tecer-biz/slide-library/migrate_to_convention.py`), run once, plus the vendored engine copied into `5-workbench/tecer-biz/slide-library/assemble.py`.

**Stack invariants (live-verified):** engine = Python stdlib ONLY (matches live `assemble.py`; `convention-spec §0` "stdlib-only"). Server = `http.server.ThreadingHTTPServer`, stdlib only, handler returns `(status_int, dict)` tuples (live `server/server.py`, `server/api.py`). App JS = vanilla ES modules, `type="module"`, no framework, no build step, `camelCase` fns / `kebab-case` files (live `app/js/`). Tests = Playwright via Python `unittest.TestCase`, real server subprocess (live `tests/e2e/`).

---

## PART A — ENGINE

The engine is a FRESH implementation to `convention-spec`, NEVER a copy-port of tecer's `assemble.py` (`convention-spec §8.1` lists 19 divergences; porting any live behavior in that table is a DEFECT). Live `assemble.py` is the PARITY REFERENCE for the unchanged mechanics only (concatenation, theme inlining, renumbering, asset copy, token report) — read it to match those, diverge everywhere §8.1 says so.

### S-A1 — Engine artifact and layout
- **S-A1.1** The engine is ONE file: `html/slide-library/engine/assemble.py`. No helper modules, no package. Internally section-disciplined with comment-banner sections (Parsing / library-YAML / Validation / Assembly / As-built writer / Catalog / CLI). Rationale: `convention-spec §1.1` vendoring + D6-S4 atomicity (the file travels into a library verbatim).
- **S-A1.2** The engine carries an internal version stamp constant `ENGINE_VERSION = "1.0"` and a supported-convention constant `SUPPORTED_CONVENTION_MAJOR = 1`. Both are the single source for the version checks (S-A8).
- **S-A1.3** A spec-compliant library contains a COPY of this file at `{library}/assemble.py` (`convention-spec §1.1`). The engine resolves all paths relative to its own location's parent = the library root, EXCEPT explicit CLI path args. Concretely: `LIBRARY = Path(__file__).resolve().parent`; `manifest.md`, `presets.md`, `as-built.md`, `base.html`, `theme.css`, `library.json`, `slides/`, `assets/`, `catalog.html` are all `LIBRARY / name`. This REPLACES tecer's `LIB`/`REPO_ROOT` constants (`convention-spec §8.1 #19`).

### S-A2 — `library.json` load (the version + config sidecar)
- **S-A2.1** On every assembly/check/catalog run the engine reads `{library}/library.json` via stdlib `json`. Absent or invalid JSON → `die()`. Schema per `convention-spec §7.1`: `convention_version`, `engine_version`, `name`, `default_lang`, `sections` (ordered list), `extra_asset_root` (string or `null`).
- **S-A2.2** `sections` is the ordered authority for catalog order and the `section`-declared check (S-A6 rule 9). `default_lang` is the terminal language fallback (S-A5). `extra_asset_root` drives `@root/` resolution (S-A4).
- **S-A2.3** Version checks per `convention-spec §7.2` are S-A8 (not duplicated here).

### S-A3 — Manifest parser (fresh, stdlib string ops only)
Implements `convention-spec §2.1`-`§2.5`. NEVER a YAML/CSV/TOML lib.
- **S-A3.1** Read `manifest.md`. Track the current `##` heading with CASE-SENSITIVE exact match: the slides table is the rows under a heading that is exactly `## Slides`; the assets table under exactly `## Assets` (`convention-spec §2.1`, §8 rule 2; DIVERGES from live `assemble.py:91` `stripped.lower() == "## slides"` per §8.1 #5).
- **S-A3.2** The header row is the FIRST `|`-row under `## Slides`; its trimmed cells MUST equal exactly the 10 names in order: `id, file, section, title, audience, lang, kind, summary, assets, provenance` (`convention-spec §2.2`). Mismatch → `die()` with line number. (DIVERGES from tecer's 9-column set per §8.1 #1.)
- **S-A3.3** The separator row is the SECOND `|`-row, skipped POSITIONALLY (never by content) (`convention-spec §2.1`, §8 rule 3; DIVERGES from live `assemble.py:106` content guard `set("".join(cells)) <= set("-: ")` per §8.1 #7).
- **S-A3.4** Every subsequent `|`-row is a fragment. Split on `|`, drop the leading/trailing empty cells (the `_split_row` shape in live `assemble.py:64-72` is the correct splitter for the surrounding-pipe form). A row whose cell count ≠ 10 → `die()` naming the line number (`convention-spec §2.1`, §8 rule 4).
- **S-A3.5** A literal `|` inside any cell is FORBIDDEN (including `\|`) (`convention-spec §2.1`, §8 rule 5). Because the split happens before any unescape, an in-cell pipe over-counts the row → the cell-count `die()` fires; the message MUST name the offending row's `id` if the first cell is recoverable, else the line number. (DIVERGES from tecer no-guard per §8.1 #3.)
- **S-A3.6** Trim each cell. Reject (`die()`) any EMPTY required cell after trim; the non-empty-required set is exactly `id, file, section, title, lang, kind, summary` (`convention-spec §2.5`, §8 rule 6; DIVERGES from tecer "`''` is valid" per §8.1 #8). `audience` empty → sentinel `general`; `assets` empty or `-` → no assets; `provenance` MAY be `-`.
- **S-A3.7** Enum validation, all CASE-SENSITIVE exact-string (`convention-spec §2.1`, §8 rules 7/8/9; DIVERGES from tecer unpinned per §8.1 #6): `kind` ∈ {`ready`, `template`}; `lang` a lowercase token; `section` ∈ `library.json` `sections`. Any miscased/unknown value → `die()`.
- **S-A3.8** Duplicate `id` across rows → `die()` (`convention-spec §2.5`, §8 rule 10).
- **S-A3.9** Build an ordered list of row-dicts AND an `id → row` map (matches live `load_fragments` `by_id` shape). Preserve manifest order.

### S-A4 — Asset resolution (fresh — `@root/` prefix keyed, NOT `/`-presence)
Implements `convention-spec §2.4`. Resolve ALL asset sources for the requested composition BEFORE writing any output (validation-before-write — live `assemble.py:297-303` proves the pattern; keep it).
- **S-A4.1** Per entry in a fragment's `assets` cell (comma-split, `-` → none): bare filename → `{library}/assets/{name}`; `@root/path` → `{extra_asset_root joined with path}` relative to the library root; `{client-logo}` → the `--client-logo` flag value; `-` → nothing. (`convention-spec §2.4` table.)
- **S-A4.2** Resolution keys on the LITERAL `@root/` PREFIX, NEVER on `/`-presence. A bare `path/with/slash` resolves from `{library}/assets/` (and `die()`s if absent), never from the extra root. (CRITICAL DIVERGENCE — live `assemble.py:206` `"/" in entry → REPO_ROOT` is INVERTED here; porting it is the defect called out in `convention-spec §2.4` and §8.1 #11.)
- **S-A4.3** `@root/...` while `library.json` `extra_asset_root` is `null` → `die()` (`convention-spec §8 rule 14`). `{client-logo}` with no `--client-logo` passed → `die()` (`§8 rule 15`). A resolved source that does not exist on disk → `die()` (`§8 rule 13`). A comma inside a filename mis-splits → the resulting entry won't resolve → `die()` (`§8 rule 16`). Rules 13 and 15 are PER-COMPOSITION (they resolve the assets of the slides actually composed, "for the requested composition" — `convention-spec §2.4` / §8 rule 13) and therefore fire ONLY in assemble modes (`--preset`/`--slides`); `--catalog-data` has no composition and MUST NOT run them (S-A12.4). Rule 14 (`@root` while `extra_asset_root` null) and rule 16 (comma hygiene) are scoped the same way — they only matter for a composed entry.
- **S-A4.4** Output filename for each copied asset = the source leaf name (`src.name`), copied into a sibling `assets/` of the deck output (live `assemble.py:316-322` shape). For `@root/` assets this means the deck references them by bare leaf name (`fixture-spec §G.7` note: `@root/partner-mark.png` → output `assets/partner-mark.png`).
- **S-A4.5** Assets-table (`## Assets`) completeness is a WARNING not an error (`convention-spec §8 rule 17`): every fragment-referenced BARE asset SHOULD have an `## Assets` row; a missing row warns and assembly proceeds.

### S-A5 — Language fallback precedence
Implements `convention-spec §6.5` EXACTLY (DIVERGES from tecer hardcoded `"pt"` in all modes per §8.1 #13 — the engine reads `default_lang` and NEVER hardcodes a language):
- **S-A5.1** `--preset` mode: `--lang` flag > chosen preset's `lang` > `library.json` `default_lang`.
- **S-A5.2** `--slides` mode (no preset): `--lang` flag > `library.json` `default_lang`.
- **S-A5.3** `--catalog` mode: `library.json` `default_lang` only (no `--lang`, no preset).
- **S-A5.4** `--lang` is document-chrome ONLY — it fills `{{LANG}}`/`<title>` default; it NEVER selects or rewrites slide ids (`convention-spec §2.2` id row, §8.1 #14). Presets and `--slides` list fully-qualified ids; the engine never auto-resolves a bare `cover` to `cover.pt`.

### S-A6 — Validation (the §8 24-rule table is authoritative)
- **S-A6.1** The engine enforces every rule in `convention-spec §8` (24 rows) with the verdict in that table (ERROR; WARNING = emit + proceed; reports = exit 1 if any). This spec does NOT restate the rules — `convention-spec §8` governs. The engine test suite implements `fixture-spec §I` (one negative mutation per rule).
- **S-A6.1a — error accumulation by mode (collect-all vs fail-fast).** The §8 ERROR verdict is realized differently per mode:
  - `--check` and `--catalog-data` (the GUI/diagnostic modes) ACCUMULATE every §8 violation they can decide into an `errors[]` list — one run yields the FULL list, validation continuing past each failure wherever continuing is decidable (e.g. multiple bad rows, multiple bad enums) — THEN exit 1 with `{ok:false, errors:[<all>]}`. The GUI consumes this full list (S-B9.2 → S-B11.2). This satisfies ADX-2's "a GUI needs the full list" and DIVERGES from tecer's die-on-first.
  - `--preset`/`--slides` (assemble) stay FAIL-FAST: the first hard ERROR aborts before any byte is written (S-A6.4, no partial output). In `--json` mode the assemble envelope still emits `{ok:false, errors:[...]}` carrying everything collected up to the abort (S-A12.3).
  - HARD FAULTS that make continued checking meaningless — `library.json` or `manifest.md` absent or unreadable/unparseable — abort immediately in EVERY mode (an accumulator over an unreadable manifest is impossible). These remain a single-error `die()`/`EngineDie`.
  - Accumulation is bounded to decidable rules: a violation that prevents deciding later rules for the SAME element (e.g. a row that fails the 10-cell count cannot also be enum-checked) records its own error and skips dependent checks on that element, but other elements continue to be validated.
- **S-A6.2** Fragment purity (rule 12): substring scan of each composed fragment's RAW text for `<head`, `<style`, `<script`, `<html`, `<body` → any present = `die()` (`convention-spec §6.3`, §8 rule 12; NEW engine work — tecer has no such scan, §8.1 #17).
- **S-A6.3** `base.html` 5-marker check (rule 18): all of `{{LANG}}`, `{{TITLE}}`, `/* {{ACCENT_CSS}} */`, `/* {{THEME_CSS}} */`, `<!-- {{SLIDES}} -->` present → else `die()` naming the missing marker (live `assemble.py:267-270` shape; `convention-spec §6.1`).
- **S-A6.4** All validation runs BEFORE any byte is written. A failure leaves zero partial output and no `assets/` folder (live `assemble.py:288-314` ordering; `convention-spec §2.4`).

### S-A7 — Assembly mechanics (parity with live, where §8.1 does not diverge)
- **S-A7.1** Resolve the ordered id list (from `--preset` slides or `--slides` csv) → load fragments in order → concatenate raw fragment HTML joined by `\n` (live `assemble.py:305`).
- **S-A7.2** Renumber `<div class="slide-number">{{N}}</div>` sequentially 1-based across the concatenated body; the counter advances ONLY on a real `{{N}}` token (live `renumber_slides` + `SLIDE_NUMBER_RE` at `assemble.py:51,234-247`; `convention-spec §6.3` `{{N}}` rule). Reuse this regex shape verbatim.
- **S-A7.3** Fill `base.html` markers: `{{LANG}}` → resolved lang; `{{TITLE}}` → HTML-escaped resolved title (stdlib `html.escape`); `/* {{ACCENT_CSS}} */` → `:root { --client-accent: #HEX; }` when `--accent` given, ELSE the whole marker line is removed (live `assemble.py:272-283` shape; `convention-spec §6.1`); `/* {{THEME_CSS}} */` → entire `theme.css` verbatim; `<!-- {{SLIDES}} -->` → renumbered body.
- **S-A7.4** Write the deck to `--out` (mkdir parents). Copy every resolved asset into `{out.parent}/assets/{leaf}` (live `assemble.py:310-322`).
- **S-A7.5** Compute the unfilled-token report: `sorted(set(TOKEN_RE.findall(document)))` where `TOKEN_RE = re.compile(r"\{\{[^}]+\}\}")` (live `assemble.py:50,324`). These are the creative-pass to-do (`convention-spec §6.3`).
- **S-A7.6** After a successful assembly the engine MUST append one as-built entry (S-A9) — both flows inherit it, no manual gate (`convention-spec §4`).

### S-A8 — Version compatibility checks
Implements `convention-spec §7.2`:
- **S-A8.1** `library.json.convention_version` MAJOR > `SUPPORTED_CONVENTION_MAJOR` (or unparseable MAJOR) → `die()` (`§8 rule 20`).
- **S-A8.2** `convention_version` MINOR ≠ the engine's target minor → WARNING, proceed (`§8 rule 21`).
- **S-A8.3** `ENGINE_VERSION` ≠ `library.json.engine_version` → WARNING (vendored-engine drift), proceed (`convention-spec §1.1`, §7.2, §8 rule 22). The `--json` envelope surfaces this warning so the GUI can show it (ADX-2).

### S-A9 — As-built writer (the library-YAML subset — fresh parser AND writer)
Implements `convention-spec §4.1`-`§4.3`. The engine implements a FRESH reader/writer to the §4.1 grammar — explicitly NOT a port of tecer's `_parse_yaml_block` (which list-parses only `slides`, keeps quotes literally; §8.1 #2).
- **S-A9.1** WRITER emits ONLY constructs in the `convention-spec §4.1` grammar: scalars; quoted scalars (MAY quote on emit; re-parse unwraps); flow lists `[a, b]` for `slides`; block lists (one `- ` line per element) for `deviations`. An empty deviation set is `deviations: -` (single `-` scalar), NEVER `deviations: []` (`convention-spec §4.1` final bullet).
- **S-A9.2** Entry schema per `convention-spec §4.2`. Engine fills: `date` (`YYYY-MM-DD`), `timestamp` (ISO-8601), `output` (path RELATIVE to library root — `convention-spec §4.2` RV-12), `slides` (actual ordered ids), `lang` (resolved), `title` (resolved, `-` when engine default used and none supplied), `accent` (resolved hex, `-` when none), `client_logo` (copied leaf name, `-` when none), `engine_version` (`ENGINE_VERSION`), `preset` (name or `-`). Optional: `order: true` when assembly started from a preset and the assembled set equals the preset set but the sequence differs (S-A9.4); `deviations` block (S-A9.3).
- **S-A9.3** Engine fills ONLY machine-decidable deviations (`convention-spec §4.3`): `added: {id}` / `removed: {id}` by set difference between the preset's id list and the assembled ids. The engine NEVER fabricates `modified:` / `bespoke:` / `reordered:` (creative-pass facts, out of v1 engine scope).
- **S-A9.4** When started from a preset and the assembled set == the preset set but order differs, emit `order: true` (`convention-spec §4.2`/§4.3 RV-6). The engine NEVER emits a prose `reordered:` line.
- **S-A9.5** READER parses the §4.1 grammar for: reading preset blocks (S-A10), and the DT5 round-trip self-check (S-A11). `parse(write(entry)) == entry` field-for-field for every entry the writer emits (`convention-spec §4.1` round-trip invariant, §8 rule 23).
- **S-A9.6** Append the entry to `{library}/as-built.md` under the `## As-built log` section, as a `### {date}-{slug}` heading + fenced ` ```yaml ` block. `{slug}` derives from the `--out` deck filename stem. Appending NEVER rewrites prior entries (append-only — `convention-spec §4`).

### S-A10 — Preset reader
Implements `convention-spec §3.1`-`§3.2`.
- **S-A10.1** Find all fenced ` ```yaml ` / ` ```yml ` blocks in `presets.md` (live `assemble.py:136` regex shape `r"```ya?ml\s*\n(.*?)```"` is correct). Parse each via the library-YAML reader (S-A9.5), match on the `preset:` key.
- **S-A10.2** Return the matched preset's `slides` (flow list of ids), `lang`, `title`, `audience`. Unknown preset or a preset missing `slides` → `die()`. Every id in `slides` MUST exist in the manifest (caught at load — S-A7.1).

### S-A11 — DT5 reproduction self-test hook
- **S-A11.1** The engine exposes, via `--json` (S-A12) on assembly, an `as_built_entry` field = the entry just written (the machine-readable record the test/migration round-trip consumes). The actual DT5 property checks (`convention-spec §4.4`, 5 checks) are executed by the test suite (test-plan), NOT inside the engine. The engine's contribution is: deterministic re-assembly from a recorded entry (re-run with `--slides` + recorded lang/title/accent/client-logo per `convention-spec §4.4` step 1) and the `--check` token report (S-A7.5 / S-A13). DT5/§4.4 reproduction re-runs MUST pass `--no-log` (S-A12.5) so the replay never appends to the `as-built.md` it is validating (ADX-4); the `as_built_entry` still surfaces in `--json` marked `"logged": false`.

### S-A12 — `--json` machine-readable face (the GUI's only parser-free seam, per ADX-2 / D2-S4)
The hypresent server NEVER parses manifests/presets/as-built — it shells out to the library's vendored engine with `--json` and reads ONE JSON envelope from stdout. This is the single behavior source (ADX-2).
- **S-A12.1** `--json` is a GLOBAL flag valid with `--check`, `--catalog`, `--preset`, `--slides`, AND a new read-only mode `--catalog-data` (S-A12.4). When `--json` is set, the engine prints EXACTLY ONE JSON object to stdout as its LAST output and nothing else on stdout (warnings/human text go to stderr so stdout stays a clean single JSON document). Exit code still follows the operation (0 ok, 1 on `die()`/unfilled-token).
- **S-A12.2** The envelope is a JSON object with these keys (absent keys default per type):
  - `ok` (bool) — true iff the operation succeeded (no `die()`).
  - `mode` (str) — `assemble` | `check` | `catalog` | `catalog-data`.
  - `errors` (list[str]) — the §8 violation message(s); empty on success. In `--check`/`--catalog-data` this is the FULL accumulated list (S-A6.1a); in assemble it carries everything collected up to the fail-fast abort. On any error path the engine still prints a `{ "ok": false, "errors": [...] }` envelope (S-A12.3) instead of only writing to stderr.
  - `warnings` (list[str]) — version-drift / minor-skew / missing-assets-row warnings (S-A4.5, S-A8.2, S-A8.3).
  - `unfilled_tokens` (list[str]) — sorted unique `{{TOKEN}}`s (assemble + check modes).
  - `output` (str|null) — absolute path of the deck written (assemble mode), else null.
  - `assets_copied` (list[str]) — leaf names copied (assemble mode).
  - `as_built_entry` (object|null) — the parsed entry just appended (assemble mode), per S-A9.2 keys. Under `--no-log` (S-A12.5) this is the entry that WOULD have been written, carrying `"logged": false` (per ADX-4); on a normal assembly it carries `"logged": true`.
  - `catalog_data` (object|null) — present in `--catalog-data` mode (S-A12.4); else null.
- **S-A12.3** When `--json` is set, the engine MUST NOT exit before emitting the envelope. Two error shapes converge into the one envelope:
  - Accumulated §8 violations (`--check`/`--catalog-data`, S-A6.1a): the validator returns the full `errors[]`; the mode prints `{ok:false, errors:[<all>]}` and exits 1. No exception is needed for accumulated soft errors — they are collected, not raised.
  - Hard faults and assemble fail-fast: a `die()` raises the module-level `EngineDie` exception which, in json mode, is caught at the top of the mode, its message appended to whatever `errors[]` was already accumulated, the envelope printed, exit 1. In non-json mode `die()` keeps the live behavior (stderr + exit 1, live `assemble.py:54-57`). `EngineDie` is reserved for hard faults (unreadable/absent `library.json`/`manifest.md`) and the assemble first-error abort — NOT for each accumulable §8 row in check/catalog-data.
- **S-A12.4** `--catalog-data` is a READ-ONLY introspection mode (NO file written). With `--json` it returns `catalog_data` = `{ "name": <library.json name>, "default_lang": ..., "sections": [<ordered>], "slides": [ {id, file, section, title, audience, lang, kind, summary, assets (list), provenance} ... in manifest order ], "presets": [ {preset, slides (list), lang, title, audience} ... ], "extra_asset_root": <value> }`. This is the GUI's library-load payload (S-B3). It runs the LIBRARY-LEVEL validation (the §8 rules that need no composition — rules 1, 2, 4-12, 18-22) and NOT the per-composition asset rules (13, 15), which require a requested composition that `--catalog-data` has no notion of (§8 rule 13 resolves "for the requested composition" — `convention-spec §2.4`; rule 15 needs `--client-logo`). A library carrying a `{client-logo}`-bearing or `@root/` fragment therefore loads `ok:true` for browsing; those asset rules fire only in assemble modes (S-A4 / S-A6 run per composition). An invalid library returns `ok:false` + `errors` and the GUI shows the invalid-library state (S-B9).
- **S-A12.5** `--no-log` is a GLOBAL replay flag implementing `convention-spec` ADX-4 VERBATIM. When set on an assembly (`--preset`/`--slides`), the engine performs the FULL assembly (resolve → concatenate → inline → renumber → fill markers → copy assets → token report) but SUPPRESSES the § 4 as-built append (S-A9.6) — `as-built.md` is NOT touched. In `--json` mode the envelope's `as_built_entry` carries the entry that WOULD have been written, marked `"logged": false` (the `logged` key in S-A12.2). On a normal assembly (no `--no-log`) the appended entry is reflected with `"logged": true`. `--no-log` is the ONLY mechanism that skips the § 4 append; every PRODUCTION assembly (GUI flow S-B10, cold-agent flow) NEVER passes it (ADX-4). Its sole legitimate callers are DT5/§ 4.4 reproduction runs (S-C5.2) and test/verification harnesses on temp copies. `README-FOR-AGENTS.md` (S-C3.1) does NOT advertise it.

### S-A13 — CLI surface (exact)
`argparse`, `allow_abbrev=False` (live `assemble.py:393` — a stale/abbreviated flag MUST error loudly, not prefix-match). Mutually-exclusive required mode group + global flags:

| Flag | Mode/global | Arg | Meaning |
|------|-------------|-----|---------|
| `--preset` | mode | `NAME` | Assemble from a named preset (`presets.md`). |
| `--slides` | mode | `id1,id2,...` | Assemble from an explicit comma-separated id order. |
| `--check` | mode | `FILE` | Scan a file for residual `{{TOKEN}}` (exit 1 if any) (`convention-spec §8 rule 24`). |
| `--catalog` | mode | (flag) | Regenerate `{library}/catalog.html` (S-A14). |
| `--catalog-data` | mode | (flag) | Read-only introspection; meaningful with `--json` (S-A12.4). |
| `--out` | global | `FILE` | Output deck path (required for `--preset`/`--slides`). |
| `--lang` | global | `L` | Document language override (S-A5). |
| `--title` | global | `T` | Document title override. |
| `--accent` | global | `#HEX` | Client accent → `--client-accent` (S-A7.3). |
| `--client-logo` | global | `PATH` | Path for the `{client-logo}` asset entry (S-A4.1). |
| `--json` | global | (flag) | Emit the S-A12 envelope on stdout. |
| `--no-log` | global | (flag) | Replay mode (ADX-4): full assembly, SKIP the as-built append (S-A12.5). Valid with `--preset`/`--slides`; `--json` marks `as_built_entry."logged": false`. |

- **S-A13.1** `--preset`/`--slides` require `--out` → else `die()` (live `assemble.py:419-420`).
- **S-A13.2** Removed-flag discipline (matches tecer p5-1): there is NO `--client` and NO `--date`. `allow_abbrev=False` makes any abbreviation/unknown flag exit 2.

### S-A14 — Catalog generation
Implements `convention-spec §6.4`.
- **S-A14.1** `--catalog` regenerates `{library}/catalog.html`: every manifest fragment, in `library.json` section order THEN manifest order, each preceded by a label bar `id · kind · audience · lang · summary` (live `build_catalog` `assemble.py:359-381` shape), with `theme.css` inlined and NO client accent. Language = `default_lang` (S-A5.3). Empty manifest → a valid empty catalog.
- **S-A14.2** `catalog.html` is a generated artifact (OPTIONAL on disk, regenerated on demand). The GUI does NOT use `catalog.html` for previews — it renders per-fragment `srcdoc` (S-B5); `catalog.html` is the standalone/agent preview path.

### S-A15 — Re-vendor tool `install-engine.py`
Implements `convention-spec §1.1` re-vendor command + D6-S4.
- **S-A15.1** `html/slide-library/engine/install-engine.py` is a stdlib-only CLI: `python install-engine.py --library {path}` copies `engine/assemble.py` over `{library}/assemble.py` AND syncs `{library}/library.json`'s `engine_version` to the engine's `ENGINE_VERSION`.
- **S-A15.2** It reads `ENGINE_VERSION` from the engine source (import or regex), updates the `engine_version` key in the target `library.json` (stdlib `json` round-trip preserving key order is NOT required; a simple load→set→dump is acceptable), and reports both the copy and the stamp bump. A missing target `library.json` or `assemble.py` source → loud error exit 1.

---

## PART B — EXPERIENCE (the builder page)

Two static pages + plain nav (D7-S4). Builder page assembles via the target library's vendored engine subprocess (ADX-2). Server gets a new MODULAR endpoint module; builder JS lives in its own files (D6-S4). ZERO regression to the existing editor boot.

### S-B1 — Page topology and navigation (D7-S4)
- **S-B1.1** Two static pages, both served by the existing static router with ZERO server routing change (live `server/server.py:114-115` serves `/app/*` from `APP_ROOT`; recon confirms `app/builder.html` → `GET /app/builder.html`): `app/index.html` (existing editor) and a NEW `app/builder.html` (the builder).
- **S-B1.2** Both pages carry a plain top-bar nav with two `<a href>` links: "Editor" → `/app/` and "Builder" → `/app/builder.html`. Add the nav to `index.html` (additive — a new `<nav>` element inside `.shell-toolbar` or above it; MUST NOT alter existing toolbar button ids/wiring) and to `builder.html`. No SPA router, no history API (recon R7).
- **S-B1.3** Adding the nav to `index.html` MUST NOT regress the editor boot: the existing `DOMContentLoaded` handler in `main.js` queries `.shell-toolbar`, `.shell-main`, `.doc-frame-mount`, `.doc-frame`, `#open-btn`, `#save-btn`, `#save-as-btn` (live `main.js:353-455`) — none of these selectors may change. The nav is new DOM only.

### S-B2 — Builder page shell (`app/builder.html` + `app/css/builder.css`)
- **S-B2.1** `builder.html` is a standalone HTML document (same `<head>` conventions as `index.html`: `shell.css` + a new `builder.css`; `type="module"` entry `app/js/builder/builder-main.js`). Layout (three zones): (1) a top bar with the nav (S-B1.2) + a "Pick library…" control + the library name/status; (2) a LEFT browse pane (section-grouped slide previews + a language filter) ; (3) a RIGHT compose tray (ordered tagged slides, drag-reorder, remove) + a preset selector + a destination/filename control + an "Assemble" button.
- **S-B2.2** `builder.css` is NEW and self-contained (thumbnail grid, tray, drag-ghost, state banners). It MUST NOT modify `shell.css`.

### S-B3 — Library pick + load + validate
- **S-B3.1** "Pick library…" calls a NEW endpoint `POST /api/dialog-folder` (S-B8) which opens a WinForms `FolderBrowserDialog` (the folder-picker that does not exist today — recon §4). The returned folder path is the library root.
- **S-B3.2** On a picked folder, the builder calls a NEW endpoint `POST /api/library-load {path}` (S-B8) which shells the library's vendored engine `python {path}/assemble.py --catalog-data --json` (ADX-2; S-A12.4) and returns the parsed `catalog_data` envelope. The server NEVER parses manifests itself (ADX-2).
- **S-B3.3** `ok:false` (invalid library) → the builder shows the invalid-library state (S-B9) listing `errors`. `warnings` (e.g. engine-drift) surface as a non-blocking banner (ADX-2 stamp warnings in GUI).
- **S-B3.4** On `ok:true` the builder renders the browse pane (S-B5) grouped by `catalog_data.sections` order, the preset selector from `catalog_data.presets`, and stores the library path for assembly.

### S-B4 — Section-grouped browse + language filter
- **S-B4.1** The browse pane groups slide cards by `section`, in `catalog_data.sections` order; each group is a labeled block. Within a group, manifest order (`convention-spec §6.4` order maps the GUI grouping — `convention-spec §2.2` `section` row: "drives GUI left-pane grouping").
- **S-B4.2** A language-filter control (derived from the distinct `lang` values in `catalog_data.slides`, plus an "all" option). Filter semantics per `convention-spec §2.2` id row / §8.1 #14: a slide matches the selected language when its `lang` equals the selection OR its `id` has NO `.{lang}` suffix (language-neutral ids always pass). The filter is GUI-only; it NEVER changes assembly (the engine selects by id).
- **S-B4.3** Each card shows `title`, `kind` badge (`ready`/`template`), `lang`, and the D5 preview (S-B5). Clicking a card TAGS it (appends to the tray — S-B6); a tagged card shows a tagged state.

### S-B5 — Previews (D5-S4: IntersectionObserver-gated `srcdoc` iframes)
Implements D5-S4 + research-01-ui §2.1.
- **S-B5.1** Each card holds a preview wrapper with a NOT-yet-mounted `<iframe>`. An `IntersectionObserver` (`rootMargin: '200px'`) mounts a card's iframe by setting `iframe.srcdoc = <single-fragment deck HTML>` only when it scrolls near view; once mounted, `dataset.mounted='true'` prevents remount (research-01-ui §2.1 code).
- **S-B5.2** The `srcdoc` content is a minimal self-contained renderable unit: `<!DOCTYPE html><html><head><style>{theme.css}</style></head><body>{fragment HTML}</body></html>` — i.e. `theme.css` injected per the convention's renderable unit (D5-S4; `convention-spec §6.2` theme is the visual truth). The builder obtains `theme.css` once per library via a NEW endpoint `POST /api/library-asset {path, name:"theme.css"}` (S-B8) OR the `--catalog-data` envelope MAY include the theme — choose the endpoint (keeps the envelope small). The fragment HTML comes from a NEW endpoint `POST /api/library-asset {path, name:"slides/{id}.html"}` (S-B8). Previews NEVER inject the editor runtime (`/runtime/js/runtime-main.js`) — recon §4 (previews are read-only).
- **S-B5.3** Scale: the iframe renders at a fixed virtual viewport (1280×720) and is shrunk with CSS `transform: scale()` + `transform-origin: top left` inside an `overflow:hidden` wrapper; `pointer-events:none` on the iframe so clicks hit the card (research-01-ui §2.1 scale block).
- **S-B5.4** A mounted-count cap: track mounted iframes; when the cap (e.g. 24) is exceeded, evict by this policy (RV2-5):
  - Eviction candidates are ONLY mounted iframes NOT currently intersecting the viewport. An in-view (intersecting) iframe is NEVER evicted — blanking a visible preview is a regression.
  - Among the non-intersecting candidates, evict the LEAST-RECENTLY-USED (the one whose last intersection/mount is oldest) by setting `srcdoc=''`, deleting `dataset.mounted`, and removing it from the tracking set, before mounting the new iframe.
  - If EVERY mounted iframe is currently intersecting at the cap (no evictable candidate), the cap raises TRANSIENTLY — mount the new iframe anyway rather than blank an in-view one. The cap re-tightens on the next eviction pass once any iframe scrolls out of view.
  - The FIFO/oldest-in-Set fallback is REMOVED — it could evict an in-view iframe and is a divergent-implementation seam. The cap is a constant in the builder JS.
- **S-B5.5** `{client-logo}`/`@root/` assets and `{{TOKEN}}`s render as missing/placeholder in previews — acceptable (previews show SHAPE; `onerror` image hiding already in the fixtures). No token filling in the builder (D7-S4 v1 exclusion).

### S-B6 — Click-to-tag + the compose tray
- **S-B6.1** Clicking a browse card appends `{id, title, kind, lang}` to the tray model and re-renders the tray as an ordered list (Google-Slides-style). Re-clicking a tagged card is a no-op (or toggles off — choose: append-once, with removal via the tray's remove button to keep the interaction unambiguous).
- **S-B6.2** Each tray row shows the position number, `title`, a `kind` badge, and a remove (✗) button. Remove deletes the row and re-numbers.
- **S-B6.3** A preset selector (S-B7) preloads the tray. The tray model is the assembly order ground truth (`convention-spec §4.2` `slides` is ground truth).

### S-B7 — Preset preload
- **S-B7.1** Selecting a preset from the selector replaces the tray with the preset's `slides` (in order), and sets the destination filename default + the document lang default from the preset's `lang`/`title` (`catalog_data.presets[*]`). The user MAY then tweak order/membership (`convention-spec §3.3` deviation-via-as-built, NOT preset mutation — the builder NEVER edits the preset).
- **S-B7.2** v1 has NO token filling and NO draft persistence (D7-S4): the tray is in-memory only; navigating away loses it.

### S-B8 — Drag-reorder tray (D4-S4: hand-rolled pointer-events sorter)
Implements D4-S4 + research-01-ui §1.3. NO vendored DnD lib.
- **S-B8.1** A self-contained module `app/js/builder/tray-sorter.js` (~150 lines) implements reorder with `pointerdown` / `pointermove` (inside `requestAnimationFrame`) / `pointerup`, computing the insertion index via `getBoundingClientRect()` per tray row (research-01-ui §1.3 pattern). `touch-action:none` on the tray container; `pointercancel`/`pointerleave` cancel the drag (research-01-ui §1.3).
- **S-B8.1a — Escape cancels an active drag (RV2-6).** A `keydown` listener, wired ONLY while a drag is active (added on `pointerdown`, removed on drag end), cancels the drag on `Escape`: it RESTORES the pre-drag DOM order (the row returns to its start index), releases pointer capture (`releasePointerCapture`), removes the ghost class + transform, removes the transient `keydown`/`pointermove` listeners, and does NOT call `onReorder` (the model is left at its pre-drag order). Escape is distinct from `pointerup` (which commits the new order). The listener is bound only during a drag so it never intercepts Escape outside reordering.
- **S-B8.2** Real-input testable BY CONSTRUCTION: `pointerdown/move/up` are exactly what Playwright `mouse.down/move/up` fires (research-01-ui §1.1 — native HTML5 DnD is RULED OUT as untestable under the real-mouse mandate). NO `draggable="true"`, NO `dragstart`/`drop`, NO `DataTransfer`.
- **S-B8.3** On drop, the tray model array reorders to match the DOM order; the assembly order reads from the model.

### S-B9 — New server endpoints (each fully specified)
A NEW MODULE `server/builder_api.py` (handlers return `(status_int, dict)` tuples — live `api.py` contract). `server/server.py` gets new POST routes that delegate to it (additive to the live `do_POST` dispatch at `server.py:145-161`; existing routes untouched). All handlers stdlib-only; engine calls via `subprocess.run([sys.executable, f"{library}/assemble.py", ...], capture_output=True, text=True, encoding="utf-8")`.

| Endpoint | Request JSON | Response JSON (200) | Errors |
|----------|--------------|---------------------|--------|
| `POST /api/dialog-folder` | (none) | `{path:str}` or `{cancelled:true}` | `{error}` 500 on dialog failure |
| `POST /api/library-load` | `{path}` | the engine `--catalog-data --json` envelope (S-A12.4), passed through | `{error}` 500 if engine spawn fails; `{ok:false,errors}` from the engine passes through as 200 |
| `POST /api/library-asset` | `{path, name}` | `{content:str}` (UTF-8 file text) | 404 if file missing; 400 if `name` escapes the library root (traversal guard, mirror `server.py:80-95`) |
| `POST /api/assemble` | `{path, slides:[...], out, lang?, title?, accent?, client_logo?}` | the engine `--slides ... --out ... --json` envelope (S-A12.2) | `{error}` 500 if spawn fails; engine `ok:false` passes through |

- **S-B9.1** `POST /api/dialog-folder`: spawn a WinForms `FolderBrowserDialog` via PowerShell, using the SAME idiom as the live file dialogs (`api.py:45-120`): `-STA -NoProfile -NonInteractive -Command <script>`, `pwsh` then `powershell.exe` fallback, serialized by a `threading.Lock`, hidden TopMost owner Form (`api.py:51-65`). The script creates `System.Windows.Forms.FolderBrowserDialog`, `.ShowDialog($owner)`, writes `$d.SelectedPath` on OK. A test seam mirrors `set_dialog_launcher` (`api.py:39-43`) so e2e can inject a fake folder path (HYP_TEST_DIALOG gate — `server.py:138`).
- **S-B9.2** `POST /api/library-load`: `subprocess.run([sys.executable, f"{path}/assemble.py", "--catalog-data", "--json"], ...)`. Parse stdout as JSON, return it verbatim (status 200). If stdout is not valid JSON or the process cannot spawn → `{error}` 500. The server does NOT interpret the envelope (ADX-2).
- **S-B9.3** `POST /api/library-asset`: read `{path}/{name}` as UTF-8 text and return `{content}`. Reject `name` containing `..` components or resolving outside `{path}` (traversal guard mirroring `server.py:_serve_static`). This serves `theme.css` and `slides/{id}.html` for previews (S-B5.2).
- **S-B9.4** `POST /api/assemble`: build the argv `[sys.executable, f"{path}/assemble.py", "--slides", ",".join(slides), "--out", out, "--json"]` + optional `--lang/--title/--accent/--client-logo`; `subprocess.run`. Return the parsed envelope (200). The deck and its sibling `assets/` are written by the engine to `out` (S-A7.4); the as-built entry is appended by the engine (S-A9.6). `ok:false` (validation/assembly error) passes through for the GUI to show (S-B10).
- **S-B9.5** Endpoint registration in `server.py` is additive: import `builder_api`, add `elif path == "/api/dialog-folder": ... ` etc. to `do_POST`. The existing 5 routes and the test seam are unchanged (zero regression — S-B1.3 analogue for the server).

### S-B10 — Assemble flow + editor handoff (D7-S4: smallest-change, specced from live)
- **S-B10.1** "Assemble" requires: a loaded library, a non-empty tray, and a destination. The destination is the OUTPUT deck path. v1 destination input: a "Pick destination…" control reusing the EXISTING `POST /api/dialog-save-as` is NOT suitable (it needs html). Instead, reuse `POST /api/dialog-folder` (S-B9.1) to pick the output FOLDER + a text input for the deck filename; the output path = `{folder}/{filename}.html`. (Writing the deck OUTSIDE the library — `convention-spec §1.2`/§5.1 §4 — is the user's responsibility; the builder defaults the filename and warns if the folder equals the library root.)
- **S-B10.2** On Assemble, POST `/api/assemble` (S-B9.4) with the tray ids as `slides`, the chosen `out`, and the resolved `lang`/`title`. On `ok:true`: show success (deck path + `assets_copied` count + `unfilled_tokens` count + the as-built confirmation from `as_built_entry`).
- **S-B10.3** EDITOR HANDOFF (smallest change from live code): the editor has NO URL-param open today — `main.js`'s `DOMContentLoaded` wires `#open-btn` → `openViaDialog(iframe)` only (live `main.js:385-399`); `file-controls.js` ALREADY EXPORTS an unused `openFile(path, iframe)` that does `apiClient.open(path)` then `loadIntoIframe(name, iframe)` (live `file-controls.js:22-25`). The handoff is:
  1. ADD a tiny boot hook to `main.js` `DOMContentLoaded`: after the existing wiring, read `new URLSearchParams(location.search).get('file')`; if present, `await openFile(file, iframe); ensureBridge(iframe);` (reusing the SAME post-open path the open-btn uses — `main.js:391-394`). `URLSearchParams.get()` ALREADY returns the percent-decoded value (verified against live `api-client.js`, which `open`s with a single `JSON.stringify({path})` and no URL layer) — so NO additional `decodeURIComponent` is applied; a second decode would mis-handle a deck path bearing a literal `%` (a legal Windows filename char) → `URIError`/corruption (RV2-3). The builder still `encodeURIComponent`s on the way out (step 2); `URLSearchParams.get` is the matching single decode. Absent param → existing boot is byte-for-byte unchanged (zero regression — the param branch is skipped). This is additive: `openFile` is imported alongside the existing `openViaDialog` from `file-controls.js`.
  2. On builder Assemble success, the builder navigates the editor page with the deck path: `window.location.href = '/app/?file=' + encodeURIComponent(absOutPath)`. The editor boot's new hook opens it via the existing `/api/open` + `/doc/` mechanism (live `api.py:handle_open` re-points `/doc/` to the deck's parent, so the sibling `assets/` resolve — recon R5).
- **S-B10.4** Rationale this is the smallest change: it adds ONE param-read branch to the editor boot and reuses the ALREADY-EXPORTED `openFile`; no server change, no new editor endpoint, no localStorage. (Recon Option A is the chosen handoff; Option D single-page is rejected by D7-S4's two-static-pages decision.)

### S-B11 — Error / empty / invalid states
- **S-B11.1** No library loaded → browse pane and tray show an empty-state prompt ("Pick a slide library to begin").
- **S-B11.2** Invalid library (engine `ok:false`) → a state listing ALL the `errors` (S-B3.3) — the engine's `--catalog-data` returns the FULL accumulated §8 violation list (S-A6.1a / RV2-4), and the GUI renders every entry, not just the first; no browse pane rendered.
- **S-B11.3** Empty tray on Assemble → Assemble disabled with a hint.
- **S-B11.4** Engine/spawn error on assemble → an error banner with the `errors`/`error` message; nothing is opened.
- **S-B11.5** Library with zero presets → preset selector shows "(no presets)"; the scratch flow (tag from browse) still works (`convention-spec §3` zero-presets is valid).

---

## PART C — MIGRATION (tecer → the convention, per U2-S4 + `convention-spec §9`)

Migration is mechanical and implements `convention-spec §9` (appendix) EXACTLY. It runs on a DEDICATED tecer-biz branch; the live library MUST keep producing decks throughout (no broken weeks — `convention-spec §9`). The engine is verified against the fixture BEFORE it touches tecer (plan sequencing). U2-S4: commit BEFORE conversion, validate jui-py + camu, merge to tecer-biz `main` in-session after validation.

### S-C1 — Branch + pre-conversion commit (U2-S4)
- **S-C1.1** Create a dedicated branch in `5-workbench/tecer-biz` (e.g. `slide-library-convention-migration`) from `main`. COMMIT the current clean state BEFORE any conversion (U2-S4 "commit BEFORE conversion") — this is the rollback point.

### S-C2 — Conversion script (lives in tecer-biz on the branch)
- **S-C2.1** `5-workbench/tecer-biz/slide-library/migrate_to_convention.py` (stdlib-only) performs the §9.1 artifact conversions on the live library IN PLACE on the branch. It is run ONCE and committed with the converted artifacts.
- **S-C2.2** Manifest 9→10 column conversion (`convention-spec §9.1` manifest row): insert a `title` column at position 4 into every one of the 57 rows; backfill each `title` via the DETERMINISTIC chain in `convention-spec §9.5` (`.slide-title` text → first heading-like element `.cover-title`/`.divider-statement`/first `.kicker`/`.card-title` → `summary` truncated at first `.`/`;`/`:` or 6 words → humanized `id`). Lowercase any miscased `section`/`lang`/`kind` (`convention-spec §9.1`/§9.2, RV-4). Scan all 57 rows for a literal `|` BEFORE conversion and ABORT on any (`convention-spec §9.5` pipe scan; corpus is verified pipe-free).
- **S-C2.3** Title backfill output is a DRAFT — the migration includes a ONE-PASS human-quality review of all 57 titles before commit (`convention-spec §9.5` / §9.1; titles are GUI labels, low blast radius). The plan marks this as a human-review gate inside the migration task.
- **S-C2.4** `library.json` CREATE (`convention-spec §9.1` library.json row): `convention_version: "1.0"`, `engine_version` = the vendored `ENGINE_VERSION`, `name: "tecer"`, `default_lang: "pt"`, `sections:` the ordered union of tecer's distinct section values LOWERCASED (`convention-spec §9.2` section row), `extra_asset_root: null` (ADX-3 — the cross-root PNG is vendored, S-C2.6).
- **S-C2.5** As-built extraction (`convention-spec §9.1` as-built row): extract the 11 retroactive entries from `presets.md` `## As-built log` into a NEW `as-built.md` `## As-built log`, each converted to the `convention-spec §4.2` schema in the library-YAML subset (§4.1): `deviations` as a block list (`- ` plain-string lines; empty → `deviations: -`), `slides` as a flow list, `retroactive: true` on each. `date` backfill for year-only entries (`tecer-institucional` `2026`, `small-deck-v3`/`small-deck-v3-1` `2026-05`) from the git commit date that introduced the entry's line in `presets.md` (`convention-spec §9.5` date backfill); `timestamp` MAY be omitted for retro entries. `preset` where the entry maps to a named preset (`investor-small`↔`small-deck-v3-1`, etc.), else `-`. Preserve every deviation line's CONTENT VERBATIM as a block-list string (never a sub-mapping) (`convention-spec §9.1`). Accept id-less `bespoke:` lines and orphan-from-presets slides (`convention-spec §9.5` survival).
- **S-C2.6** Cross-root PNG vendoring (ADX-3 BINDING, `convention-spec §9.3`): tecer's ONLY `/`-cross-root user is `cover-investor` at manifest row 48, asset cell `cover-bg.jpg, brand/logo/tecer-logo-white-transparent.png`. (a) Copy `brand/logo/tecer-logo-white-transparent.png` into `slide-library/assets/` as `tecer-logo-white-transparent.png` (or reuse the byte-identical existing `tecer-wordmark-white.png`); (b) rewrite row 48's asset cell to the bare leaf name. After this NO `/`-bearing asset entry remains (`convention-spec §9.3` exact cutover edit). VERIFY no other row references a cross-root path before/after.
- **S-C2.7** Presets (`convention-spec §9.1` presets row): `presets.md` format unchanged; MAY add `title`/`audience` keys. Remove the `## As-built log` section from `presets.md` after extraction (it now lives in `as-built.md`) so the engine's auto-appends never touch curated presets (`convention-spec §9.3`).

### S-C3 — Self-description (`convention-spec §9.1` CLAUDE.md row)
- **S-C3.1** Author `slide-library/README-FOR-AGENTS.md` from the `convention-spec §5.1` template, porting tecer's MUST-step content into the matching sections (selection → README section 3; leakage/freshness/upstream → README section 6) (`convention-spec §9.1`). Tecer's freshness section MUST name where Tecer-fact source-of-truth lives (`convention-spec §5.1` README §6 placeholder).
- **S-C3.2** Replace `slide-library/CLAUDE.md`'s body with a thin one-line pointer to `README-FOR-AGENTS.md` (`convention-spec §9.1`, §5). Discard the stale "54 slides" count (`convention-spec §9.3` — counts derive from the manifest, never prose).

### S-C4 — Engine vendoring into tecer (`convention-spec §9.1` assemble.py row)
- **S-C4.1** Vendor the RBTV engine into tecer: `python html/slide-library/engine/install-engine.py --library 5-workbench/tecer-biz/slide-library` copies `engine/assemble.py` over `slide-library/assemble.py` and syncs `engine_version` (S-A15). This REPLACES tecer's 440-line tecer-anchored `assemble.py`.
- **S-C4.2** Regenerate `catalog.html` with the new engine (`python slide-library/assemble.py --catalog`) (`convention-spec §9.1` catalog row).

### S-C5 — Migration validation (the DT5 procedure, `convention-spec §4.4` + §9.5)
- **S-C5.1** Round-trip + pipe-scan programmatic checks (`convention-spec §9.5`): for every converted as-built entry `parse(write(entry)) == entry` field-for-field (§4.1, §8 rule 23); a mismatch FAILS migration. Pipe-scan all 57 rows (done pre-conversion, S-C2.2).
- **S-C5.2** Re-assembly validation for jui-py + camu (U2-S4; `convention-spec §9.4`/§4.4): re-assemble each known deck from its as-built record with the new engine and run the `convention-spec §4.4` 5-check mechanical property bar (order identity; per-slide tag/class skeleton equality excluding token-bearing text; asset set parity by filename; clean `--check` token report = expected template tokens; headed render sanity — zero console errors, theme applied). IMMEDIATELY post-migration the "upgraded canonical copy" class is EMPTY by construction (`convention-spec §4.4`) — both decks MUST pass all 5 checks with no excused diffs.
- **S-C5.3** The headed render-sanity check (§4.4 check 5) is a HEADED browser load of each re-assembled deck — this is part of the done-boundary protocol (test-plan), exercised by the verifier on the MIGRATED library, NOT by the dev e2e suites.

### S-C6 — Merge gate (U2-S4)
- **S-C6.1** Merge the migration branch to tecer-biz `main` IN-SESSION ONLY AFTER: S-C5.1 round-trip passes, S-C5.2 jui-py + camu both pass the 5-check bar, and the 57-title human-review (S-C2.3) is complete. Any failure → STOP, do not merge (rollback point is S-C1.1).
- **S-C6.2** The merge is a tecer-biz git operation (separate repo); commit/merge hygiene per tecer-biz `CLAUDE.md` (`git mv`/`git rm`, Conventional Commits). The build plan ENDS at "migration validated + merged"; the DT1–DT5/EX1–EX2 done-boundary (test-plan) is the orchestrator's to exercise on the merged library.

---

## Done-boundary artifacts (what the orchestrator's DT1–DT5/EX1–EX2 protocol consumes)

The plan ends at: all engine unit suites green, all builder e2e suites green, a clean Kimi-evidenced server run, and migration validated+merged. The done-boundary protocol (test-plan §Done-Boundary) THEN uses these artifacts (it is NOT claimable by the dev suites):
- The MIGRATED tecer library (`5-workbench/tecer-biz/slide-library/` on `main`) — the Fidelity Floor data for DT1–DT5.
- `app/builder.html` + the builder server endpoints — exercised HEADED with real gestures (DT1/DT2/DT3).
- The vendored engine + `--json` face — the assembly + as-built path (DT3/DT5).
- `README-FOR-AGENTS.md` of the migrated library — the cold-agent interface (DT4).
- jui-py + camu re-assembly property results (S-C5.2) — DT5 evidence.

---

## Amendments (ADX)

> Append-only. Orchestrator rulings during EXECUTION land here as `ADX-N`, numbering CONTINUING from the convention-spec's ADX-3 — the first build-spec erratum is `ADX-4`. Executors cite "per build-spec ADX-N". Each entry: `ADX-N — {date} — {topic} — {ruling}`.

- **ADX-4 — 2026-06-07 — `--no-log` replay flag (implements convention-spec ADX-4).** The engine (PB-T2, sole `assemble.py` writer) gains the global `--no-log` flag: full assembly, § 4 as-built append suppressed; in `--json` the envelope's `as_built_entry` carries the would-be entry marked `"logged": false`. Specced as S-A12.5 + the `logged` key in S-A12.2 + the CLI row in S-A13. DT5/§4.4 reproduction (S-A11, S-C5.2) and the migration reproduction (PB-T19) MUST pass it; production flows (GUI S-B10, cold agent) NEVER do.
- **ADX-5 — 2026-06-07 — `--check`/`--catalog-data` collect-all (fix-cycle RV2-4).** The §8 ERROR verdict accumulates the FULL violation list in `--check`/`--catalog-data` (one run = every decidable error, then exit 1) so the GUI invalid-library state shows all errors (ADX-2's "GUI needs the full list"). Assemble modes stay fail-fast (no partial output) but still emit `{ok:false, errors:[...]}` in `--json` with everything collected to the abort. Hard faults (unreadable/absent `library.json`/`manifest.md`) abort immediately in every mode. Specced as S-A6.1a + S-A12.3.
- **ADX-6 — 2026-06-07 — `--catalog-data` validation scope (fix-cycle RV2-9).** `--catalog-data` runs library-level §8 rules only (1, 2, 4-12, 18-22), NOT the per-composition asset rules (13, 15) — there is no requested composition. A `{client-logo}`/`@root` fragment no longer spuriously fails browse-pane load. Specced in S-A4.3 + S-A12.4.
- **ADX-7 — 2026-06-07 — handoff single-decode (fix-cycle RV2-3).** The editor `?file=` boot reads the value via `URLSearchParams.get()` ONLY (already decoded); the redundant `decodeURIComponent` is removed (a literal `%` in a deck path would otherwise throw). Builder-side `encodeURIComponent` is retained. Specced in S-B10.3 step 1; PB-T11 code corrected.
- **ADX-8 — 2026-06-07 — preview eviction never blanks an in-view iframe (fix-cycle RV2-5).** Cap eviction = LRU among NON-intersecting iframes only; in-view iframes are never evicted; at-cap with all-in-view raises the cap transiently. The FIFO fallback is removed. Specced in S-B5.4; PB-T9 + PB-T13 updated.
- **ADX-9 — 2026-06-07 — Escape cancels an active drag (fix-cycle RV2-6).** A drag-scoped `keydown`/Escape handler restores pre-drag order, releases capture, drops transient listeners, and does NOT call `onReorder`. Specced in S-B8.1a; PB-T10 + PB-T14 updated.

---

## CONTRADICTIONS (live source vs inputs — flagged, not silently resolved)

- **X1 — `--json` envelope is NEW design, not in any input.** ADX-2/D2-S4 mandate "a machine-readable output mode whose exact form workstream 2 designs" — S-A12 IS that design (no contradiction with inputs; flagged because it is net-new contract the engine MUST honor and the GUI depends on). Resolution: specified here as S-A12; the GUI (S-B) and the cold-agent CLI (`convention-spec §5.1` human invocation) BOTH stay valid because `--json` is additive — the human/agent text invocation in `convention-spec §5.1` §4 is unchanged (json is opt-in).
- **X2 — recon "57 vs 58 vs 54" slide-count drift.** Live verification (changelog row 238 TRUTH CORRECTION; `convention-spec §9.3`) = tecer has 57 manifest rows = 57 disk files. Recon-hypresent referenced "58"; tecer `slide-library/CLAUDE.md` says "54". Resolution: migration derives ALL counts from the live manifest (S-C2.2 uses "57"); the stale prose counts are discarded (S-C3.2). NO build action beyond using 57.
- **X3 — recon Option D (single-page) vs D7-S4 (two static pages).** Recon-hypresent §3 called Option D "lowest-friction"; D7-S4 RULED two static pages + nav. Resolution: D7-S4 governs (S-B1); the handoff uses recon Option A (URL param) implemented as the smallest additive change (S-B10.3). Flagged because recon's recommendation was overridden by a later locked decision.
- **X4 — live editor has NO `?file=` handling (recon R3) — the handoff REQUIRES adding it.** Confirmed against live `main.js:353-455` (no `URLSearchParams`/`location.search` read) and `file-controls.js` (exports `openFile` but it is UNUSED). Resolution: S-B10.3 adds exactly one param-read branch reusing the already-exported `openFile`; this is additive and zero-regression (absent param = unchanged boot). Flagged because it is the one editor-file modification the build makes outside the builder's own files.
- **X5 — `module-manifest.json` registration.** Recon §9 + changelog (S2 row 77, U3-S4) note hypresent itself is NOT in `modules/`/`module-manifest.json` ("not an installable component"); rbtv `CLAUDE.md` mandates manifest sync on component creation. Resolution per U3-S4: the slide-library engine + builder page follow the hypresent precedent (NOT installed) — no manifest entry — "unless architects rule otherwise". Flagged as an orchestrator decision point if RBTV later ships the engine as an installable component. NO build action in v1.
