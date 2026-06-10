You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

D29 EVIDENCE-METRICS BLOCK (binding): record measured WALL_MS + EXIT + ran/passed/failed/SKIPPED counts + SKIPPED_LINES_COUNT + each skip's exact reason string. Implausible WALL_MS or unexpected skip → BUG section + STOP.

Edit-anchoring rule: locate by exact strings, NEVER line numbers.

# PB-T4 — Engine suite: §I negative matrix + DT5 self-test + install-engine test

## Objective
Write the second half of the engine unit suite: the 24-row negative-case matrix (fixture-spec §I), the DT5-procedure property self-test on the seed entry (test-plan §1.5), and the install-engine test (test-plan §1.6).

## FILE ALLOWLIST
- ✚ create `html/slide-library/engine/tests/test_engine_negatives.py`
- ✚ create `html/slide-library/engine/tests/test_engine_dt5.py`
- ✗ nothing else. Do NOT modify the engine.

## Preconditions
- Engine at `html/slide-library/engine/assemble.py`; re-vendor tool at `html/slide-library/engine/install-engine.py` (from PB-T5); fixture at `html/slide-library/tests/fixture-library/` + `html/slide-library/tests/shared-brand/partner-mark.png`.
- Same temp-copy exercise pattern as PB-T3 (copy `fixture-library/` + `shared-brand/` into a temp parent, drop `assemble.py` into the temp library, run via subprocess with `--json`).

## Negative-case matrix (test-plan §1.3) — implement EVERY row of fixture-spec §I
The fixture on disk STAYS valid. For each row: COPY the valid fixture to a tempdir, apply the mutation to the COPY, run the engine, assert the verdict + a message matching the pattern, then discard. ERROR rows → exit 1 (die) with the pattern in `errors` (json mode) or stderr; WARNING rows → `ok:true` AND a matching warning; report rows → exit 1 listing tokens. The 24 rows (fixture-spec §I — implement each as its own test method):

| § 8 rule | Mutation | Verdict | Pattern (regex-ish) |
|---|---|---|---|
| 1 | Delete `theme.css` | ERROR | `theme.css not found` |
| 2a | Lowercase `## Slides` → `## slides` | ERROR | `(?i)slides .*heading\|section heading` |
| 2b | Rename header `id`→`Id` | ERROR | `header.*mismatch` |
| 4 | Delete one cell from a slide row (→9 cells) | ERROR | `(9 columns\|cells).*expected 10\|line \d+` |
| 5 | Insert a literal `\|` into `cover-nimbus.en` summary | ERROR | `pipe.*cover-nimbus\.en\|line \d+` |
| 6 | Blank `intro-pillars` title cell | ERROR | `empty.*required.*intro-pillars\|title` |
| 7 | Set `cover-nimbus.pt` kind to `Template` | ERROR | `kind.*Template.*not in .*ready.*template` |
| 8 | Set `intro-pillars` lang to `EN` | ERROR | `lang.*EN` |
| 9 | Set `proof-metrics` section to `proofs` | ERROR | `section.*proofs.*not declared` |
| 10 | Duplicate the `intro-pillars` id onto a 2nd row | ERROR | `duplicate.*id.*intro-pillars` |
| 11 | Delete `slides/proof-metrics.html` (row stays) | ERROR | `fragment.*missing.*proof-metrics\|not found` |
| 12 | Add a `<style>` block inside `intro-pillars.html` | ERROR | `(?i)fragment.*<style\|purity` |
| 13 | Delete `assets/nimbus-mark.png` | ERROR | `asset.*nimbus-mark\.png.*not found` |
| 14 | Add a `@root/x.png` entry, set `extra_asset_root: null` | ERROR | `@root.*extra_asset_root\|no extra_asset_root` |
| 15 | Assemble a `{client-logo}`-bearing cover with NO `--client-logo` | ERROR | `\{client-logo\}.*--client-logo` |
| 16 | Put a comma inside an asset filename (`nim,bus-mark.png`) | ERROR | `asset.*comma\|not found` |
| 17 | Remove the `nimbus-mark.png` row from `## Assets` (file on disk) | WARNING (proceeds) | warns `(?i)assets.*row.*nimbus-mark`; assembly succeeds |
| 18 | Delete `<!-- {{SLIDES}} -->` from `base.html` | ERROR | `base\.html.*missing.*marker.*SLIDES` |
| 19 | (covered by 1) Delete `theme.css` | ERROR | `theme.css not found` |
| 20 | `convention_version: "2.0"` | ERROR | `convention.*2\.0.*unsupported\|major` |
| 21 | `convention_version: "1.9"` | WARNING (proceeds) | warns `(?i)minor`; succeeds |
| 22 | `engine_version: "9.9"` | WARNING (proceeds) | warns `(?i)engine.*version.*drift\|stamp`; succeeds |
| 23 | Hand-write as-built `deviations: [modified: x]` (`:` in flow elem) | ERROR | round-trip/parse failure on the `:`-in-flow-element |
| 24 | `--check` the un-filled seed reproduction (templates unfilled) | reports exit 1 | lists `{{TOKEN}}`s; exit 1 |

Notes (fixture-spec §I): rules 15/24 require assembling; for 15 assemble `nimbus-intro-en` (its cover lists `{client-logo}`) with no `--client-logo`. For 24, assemble the seed composition to a temp deck (templates stay unfilled) then `--check` it. Rule 23 is exercised by feeding the engine reader the bad text (direct function or via a hand-edited temp `as-built.md` the engine reads in a round-trip path).

## DT5-procedure self-test (test-plan §1.5) — convention-spec §4.4 5-check bar on the seed entry
Re-assemble the seed entry (`2026-06-06-seed-demo`, `deviations: -`, slides = the 7 `nimbus-intro-en` ids) FRESH and apply the convention-spec §4.4 property checks. Inlined §4.4 (the acceptance bar — quote):
> "1. Order identity — the slide ids and their order in the re-assembled deck EXACTLY equal the entry's `slides`. 2. Per-slide skeleton equality — for each slide, the tag/class skeleton (element tree + `class` attributes, in document order) equals the original's, with the text content of token-bearing nodes EXCLUDED. 3. Asset parity — the set of filenames copied into the reproduction's `assets/` equals the set the original referenced. 4. Clean token report — `--check` on the reproduction reports EXACTLY the template tokens expected unfilled. 5. Headed render sanity — [deferred to the done-boundary; NOT in this task]."
> convention-spec §4.4 Zero-deviation case: "checks 1-5 apply with no excused diffs whatsoever ... The fixture ships NO committed expected-output file; the property checks are run against a freshly re-assembled reproduction."

Implement checks 1–4 (check 5 = headed render is the done-boundary, NOT here):
- Re-assemble the seed ids twice to two temp decks (zero-deviation: the record's input is fully determined). Check 1: assert both decks' slide order == the entry's `slides`. Check 2: parse each deck's body into a tag+class skeleton (e.g. via html.parser collecting (tag, sorted(class list)) per element in document order), EXCLUDING text content; assert the two skeletons are identical (structural self-consistency — there is no committed golden, convention-spec §4.4 zero-deviation). Check 3: assert the two `assets/` filename SETS are equal and every reference resolves on disk. Check 4: `--check` the deck → assert the residual token set equals the template tokens in the composed templates (the cover/problem/proof tokens), exit 1.

## install-engine test (test-plan §1.6)
- Copy the fixture to a temp lib; set its `library.json` `engine_version` to `"0.9"`. Run `python html/slide-library/engine/install-engine.py --library {tmplib}`. Assert: `{tmplib}/assemble.py` now byte-equals `html/slide-library/engine/assemble.py`; `{tmplib}/library.json` `engine_version` == the engine's `ENGINE_VERSION` (`1.0`). A missing target `library.json` → exit 1.

## Acceptance criteria
Run both: `python -m unittest html.slide-library.engine.tests.test_engine_negatives html.slide-library.engine.tests.test_engine_dt5 -v` (or via discover with both patterns). ALL pass. Record the D29 metrics block. (If install-engine.py is absent because PB-T5 has not landed, SKIP the install-engine test with the exact reason string and note it — do NOT fail the suite.)

## Evidence file
Append to `html/hypresent/docs/verification/prez-v1/engine-unit-result.md` (the same file PB-T3 wrote, under a new `## PB-T4` section) the D29 block for both suites.

DONE means: both suites green (install-engine test passing once PB-T5 is present), D29 evidence written. Any failure/implausible metric → BLOCKED/BUG + stop.
