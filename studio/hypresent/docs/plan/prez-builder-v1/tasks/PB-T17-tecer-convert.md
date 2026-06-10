You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context. This task operates in the tecer-biz repo on the branch `slide-library-convention-migration` (created by PB-T16).

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any step, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate by exact strings, NEVER line numbers.

# PB-T17 — tecer-biz: conversion script + run (manifest 9→10, title backfill, library.json, as-built extract, cross-root PNG, presets cleanup)

## Objective
Write `slide-library/migrate_to_convention.py` (stdlib-only) and run it ONCE to convert the live tecer library in place on the branch, implementing convention-spec §9 EXACTLY. Then a human-quality review of the 57 backfilled titles (orchestrator gate). Validate round-trip + pipe-scan.

## FILE ALLOWLIST (all under 5-workbench/tecer-biz/slide-library/)
- ✚ create `migrate_to_convention.py`
- ✎ modify `manifest.md` (9→10 columns + title backfill + cross-root cell rewrite + lowercase enums)
- ✎ modify `presets.md` (remove the `## As-built log` section after extraction; MAY add title/audience keys)
- ✚ create `as-built.md` (the extracted 11 entries in library-YAML)
- ✚ create `library.json`
- ✎ modify `assets/**` ONLY to add the vendored cross-root PNG (copy in `tecer-logo-white-transparent.png`)
- ✗ do NOT vendor the engine here (PB-T18) and do NOT write `README-FOR-AGENTS.md`/`CLAUDE.md` here (PB-T18).

## Live tecer facts (verified — anchor on these)
- The library has 57 slide fragments = 57 manifest data rows (NOT 54, NOT 58 — the prose counts are stale; derive counts from the manifest).
- The live `## Slides` header is EXACTLY (9 columns, NO title): `| id | file | section | audience | lang | kind | summary | assets | provenance |`. The target is 10 columns with `title` at position 4: `| id | file | section | title | audience | lang | kind | summary | assets | provenance |`.
- The ONLY cross-root asset user is `cover-investor` (manifest row, id `cover-investor`), whose `assets` cell is EXACTLY `cover-bg.jpg, brand/logo/tecer-logo-white-transparent.png`. No other row references a `/`-bearing asset.
- The byte-identical library asset already exists: `assets/tecer-wordmark-white.png` is md5-identical to `brand/logo/tecer-logo-white-transparent.png` (per the manifest's own Assets note).
- The as-built log lives INSIDE `presets.md` under `## As-built log` as 11 retroactive prose-ish entries. Three record year/month only: `tecer-institucional` (`2026`), `small-deck-v3` (`2026-05`), `small-deck-v3-1` (`2026-05`).

## Conversion steps (convention-spec §9 — quotes you implement)

### (1) Pipe scan FIRST (convention-spec §9.5 / §8 rule 5)
Scan all 57 manifest data rows for a literal `|` inside any cell BEFORE converting. The corpus is verified pipe-free; if ANY pipe is found, ABORT (do not escape) and write BLOCKED.

### (2) Manifest 9→10 columns + title backfill (convention-spec §9.1 manifest row + §9.5 chain)
Insert a `title` column at POSITION 4 (between `section` and `audience`). The new header MUST be exactly the 10-col header above. For each of the 57 rows produce a DRAFT `title` by the FIRST rule yielding a non-empty string (convention-spec §9.5 title backfill chain — quote):
> "1. The text content of the fragment's `.slide-title` element, if present. 2. Else the text content of the first heading-like element in the fragment, in this order: `.cover-title`, `.divider-statement`, then the first of `.kicker`/`.card-title`. 3. Else the `summary`, truncated at the FIRST of `.`, `;`, `:` OR 6 words — whichever comes first. 4. Else the humanized `id` (kebab → spaced, capitalized)."
The chain NEVER blocks (rule 4 always yields). To read a fragment's element text, parse `slides/{id}.html` with stdlib `html.parser` (find the first element with the target class and take its text). Keep each title ≤ ~8 words (convention-spec §2.2 title column). The ≤~8-word cap binds EVERY rule's output, INCLUDING rule 4's humanized id (RV2-10) — rules 1-3 are already length-bounded but rule 4 is not bounded by the chain text, so apply the same ≤~8-word truncation to a humanized-id title (tecer ids are short kebab so a breach is unlikely, but enforce the cap uniformly). The one-pass human review (below) is the final backstop on title length/quality; titles are GUI labels, low blast radius.

### (3) Lowercase enums (convention-spec §9.1/§9.2, RV-4)
Lowercase any miscased `section`/`lang`/`kind` value (e.g. a stray `pt-BR` → `pt`). After conversion every `kind` ∈ {ready,template}, every `lang` is a lowercase token, every `section` is lowercase.

### (4) Cross-root PNG vendoring (ADX-3 BINDING; convention-spec §9.3 exact cutover edit)
> convention-spec §9.3: "(1) copy `brand/logo/tecer-logo-white-transparent.png` into `slide-library/assets/` as `tecer-logo-white-transparent.png` (or reuse the existing byte-identical `tecer-wordmark-white.png`); (2) rewrite manifest row 48's asset cell from `brand/logo/tecer-logo-white-transparent.png` to the bare filename. No other manifest row references a cross-root path."
Do BOTH: copy the PNG from `5-workbench/tecer-biz/brand/logo/tecer-logo-white-transparent.png` to `5-workbench/tecer-biz/slide-library/assets/tecer-logo-white-transparent.png` (use `git -C 5-workbench/tecer-biz add` after), AND rewrite the `cover-investor` row's `assets` cell so `cover-bg.jpg, brand/logo/tecer-logo-white-transparent.png` becomes `cover-bg.jpg, tecer-logo-white-transparent.png`. After this NO `/`-bearing asset entry remains — VERIFY by scanning all rows' asset cells for `/`.

### (5) library.json CREATE (convention-spec §9.1 library.json row)
> "`convention_version: "1.0"`; `name: "tecer"`; `default_lang: "pt"`; `sections:` the ordered union of tecer's section values (lowercased); `extra_asset_root: null` per ADX-3."
Set `engine_version` to `"1.0"` (the engine vendored in PB-T18 stamps `1.0`; PB-T18's install-engine will re-sync it). The `sections` list = the DISTINCT `section` values in MANIFEST ORDER (first-seen order), lowercased. Write valid JSON (stdlib `json`, indent=2).

### (6) As-built extraction (convention-spec §9.1 as-built row + §9.5 date backfill)
Extract the 11 entries from `presets.md` `## As-built log` into a NEW `as-built.md` with a `## As-built log` section, each as a `### {date}-{slug}` heading + fenced ```yaml``` block in the convention-spec §4.2 schema + library-YAML subset (§4.1):
- `deviations` as a BLOCK LIST (one `- ` plain-string line per deviation; empty set → `deviations: -`). Preserve each deviation line's CONTENT VERBATIM as a string (NEVER a sub-mapping): `modified: x — y` stays the string `modified: x — y`. Accept id-less `bespoke:` lines (convention-spec §9.5 — small-deck-v3's `bespoke: v3 drops the-ask…`).
- `slides` as a flow list of ids.
- `retroactive: true` on each (convention-spec §4.2/§9.1).
- `engine_version: "1.0"`.
- `date`: for the three year/month-only entries (`tecer-institucional` `2026`; `small-deck-v3`/`small-deck-v3-1` `2026-05`), backfill the full `YYYY-MM-DD` from the git commit date that introduced that entry's line in `presets.md` (convention-spec §9.5): `git -C 5-workbench/tecer-biz log -1 --format=%cs -S "<a unique string from the entry>" -- slide-library/presets.md`. `timestamp` MAY be omitted for retro entries.
  - **Ordering + determinism (RV2-12):** Run ALL `git log -S` date queries against HEAD (committed history) BEFORE the migration script rewrites `presets.md` (step 7 removes `## As-built log` from `presets.md` in this SAME task). The pickaxe walks committed history, so a working-tree edit cannot change its result — but run the queries first as belt-and-suspenders and to keep the extraction self-contained. Make each `-S` query DETERMINISTIC: use `git log -1 --format=%cs -S "<string>"` (the `-1` pins exactly the most-recent introducing commit; `%cs` is the short committer date) and choose a `<string>` UNIQUE to that one entry (e.g. its `output` path or a distinctive deviation line), so the query matches exactly one entry's introduction and the date is reproducible across runs. If a `<string>` is not unique or the query returns no commit, write BLOCKED naming the entry — do NOT guess a date.
- `preset`: where the entry maps to a named preset (`investor-small`↔`small-deck-v3-1`, etc. per convention-spec §9.1), else `-`.
- `output`: the recorded output path (a historical sentinel — the file need not exist; convention-spec §4.2/RV-5), relative to the library root.
A library slide referenced by NO preset (e.g. an orphan) is NOT an error (convention-spec §9.5) — do not drop it from the manifest.

### (7) presets.md cleanup (convention-spec §9.3)
After extraction, REMOVE the `## As-built log` section (and its entries) from `presets.md` so the engine's auto-appends never touch curated presets. The `## Presets` section stays unchanged (you MAY add `title`/`audience` keys but it is optional — prefer minimal change).

## Run + validate
Run `python migrate_to_convention.py` from `5-workbench/tecer-biz/slide-library/`. Then:
- Round-trip check (convention-spec §9.5 / §8 rule 23): for every converted as-built entry, `parse(write(entry)) == entry` field-for-field under the library-YAML subset. Use the engine's reader/writer if convenient (the engine source is at `../../../3-resources/tools/rbtv/html/slide-library/engine/assemble.py` relative to the vault, but DO NOT depend on it being vendored yet — implement a self-contained round-trip in the migration script per the §4.1 grammar). A mismatch FAILS migration → BLOCKED.
- Manifest sanity: 57 rows, each exactly 10 cells; the header is the 10-col header; no `/`-bearing asset cell remains; every `kind`∈{ready,template}, every `lang` lowercase.

## HUMAN-REVIEW GATE (convention-spec §9.5 / §9.1 — orchestrator gate)
The 57 backfilled titles are a DRAFT. Write ALL 57 `id → drafted title` pairs into the evidence file under a `## TITLE REVIEW (57)` section for the orchestrator's one-pass human-quality review. Do NOT consider the migration "done" until that review is recorded (the orchestrator confirms; titles are GUI labels, low blast radius). You produce the draft + the review table; you do not self-approve.

## Acceptance criteria (self-verifiable)
1. `python migrate_to_convention.py` exits 0; re-running it is idempotent OR it refuses to double-convert (guard on the 10-col header already present).
2. `manifest.md` header == `| id | file | section | title | audience | lang | kind | summary | assets | provenance |`; 57 data rows × 10 cells; the `cover-investor` row's asset cell == `cover-bg.jpg, tecer-logo-white-transparent.png`; no asset cell contains `/`.
3. `assets/tecer-logo-white-transparent.png` exists.
4. `library.json` parses, has the 6 keys, `name=="tecer"`, `default_lang=="pt"`, `extra_asset_root` is null, `sections` is a lowercased ordered list.
5. `as-built.md` has 11 `### ` entries, each with `retroactive: true`, `deviations` as block-list-or-`-`, `slides` as a flow list; the 3 year/month-only entries now have full `YYYY-MM-DD` dates; round-trip passes for all 11.
6. `presets.md` no longer contains `## As-built log`.

## Evidence file
Append to `5-workbench/tecer-biz/slide-library/docs/migration-validation.md` a `## PB-T17` section: the 6 acceptance results, the round-trip result for all 11 entries, the `/`-scan result (must be "none"), and the `## TITLE REVIEW (57)` table (id → title) for the human gate.

DONE means: script written + run, all 6 acceptance criteria pass, round-trip passes, the 57-title review table is recorded for the orchestrator. Any failure → BLOCKED + stop (the PB-T16 commit is the rollback point).
