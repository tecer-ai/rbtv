You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

D29 EVIDENCE-METRICS BLOCK (binding for this test task): every evidence file MUST record measured WALL_MS (time.perf_counter around the test command) + unittest EXIT code + the ran/passed/failed/SKIPPED counts + SKIPPED_LINES_COUNT + each skip's exact reason string. A physically-implausible WALL_MS or an unexpected skip → write a BUG section and STOP; never report green.

Edit-anchoring rule: locate code/content by exact strings, NEVER line numbers.

# PB-T3 — Engine unit suite (core: self-check, happy-path, round-trip, --json)

## Objective
Write the first half of the engine unit suite (pure Python unittest, NO browser) verifying `html/slide-library/engine/assemble.py` against the fixture library at `html/slide-library/tests/fixture-library/`.

## FILE ALLOWLIST
- ✚ create `html/slide-library/engine/tests/__init__.py` (empty)
- ✚ create `html/slide-library/engine/tests/test_engine_core.py`
- ✗ nothing else. Do NOT modify the engine (addendum rule 1).

## Preconditions you can rely on
- The engine exists at `html/slide-library/engine/assemble.py` with: a CLI (`--preset/--slides/--check/--catalog/--catalog-data` + `--out/--lang/--title/--accent/--client-logo/--json`), `ENGINE_VERSION="1.0"`, a `--json` envelope with keys `ok, mode, errors, warnings, unfilled_tokens, output, assets_copied, as_built_entry, catalog_data`, and an as-built writer in the library-YAML subset.
- The fixture exists at `html/slide-library/tests/fixture-library/` (9 slides, 6 sections, 2 presets `nimbus-intro-en`/`nimbus-intro-pt`, 1 seed as-built entry `2026-06-06-seed-demo` with `deviations: -`), with the extra-root at `html/slide-library/tests/shared-brand/partner-mark.png`.

## How to exercise the engine (subprocess, json mode)
For each test: copy the fixture library tree into a fresh tempdir, copy `engine/assemble.py` into that temp library root (so `LIBRARY = parent` resolves), and shell `subprocess.run([sys.executable, f"{tmplib}/assemble.py", ...], capture_output=True, text=True, encoding="utf-8")`. Parse stdout as JSON when `--json` is used. NEVER assemble into the real fixture (sibling assets/ collision). The extra-root sibling must be copied too (copy both `fixture-library/` and `shared-brand/` into the same temp parent so `../shared-brand` resolves).

## Tests to implement (test-plan §1.1, §1.2, §1.4, §1.7)

### Fixture self-check (test-plan §1.1) — re-run fixture-spec §H 1–11 as test methods
Assert the fixture is structurally valid (9 rows × 10 cells; 9 files; bare assets exist; shared-brand png exists; 2 yaml + 1 as-built block; fragment purity; covers unnumbered + 7 numbered; exact-case headings; no in-cell pipe + required non-empty; round-trip of seed + presets). These do NOT need the engine — pure file/string checks.

### Happy-path (test-plan §1.2)
- `--preset nimbus-intro-en --out {tmp}/d.html --json`: assert `ok:true`; `as_built_entry.slides` is the 7-id list `[cover-nimbus.en, intro-pillars, problem-cards, how-nimbus-works, nimbus-divider, proof-metrics, closing-nimbus]` in that order; `assets_copied` includes `partner-mark.png` (the `@root` asset copied by leaf name — convention-spec §2.4); the written deck's `{{N}}` are sequential 1-based across the numbered slides (read the deck, find `<div class="slide-number">N</div>`, assert 1,2,3,... with covers contributing no number); `theme.css` content is inlined (a known class like `.slide--cover` appears in the deck); `unfilled_tokens` equals exactly the set of `{{TOKEN}}`s present in the composed template slides (cover + problem-cards + proof-metrics tokens; NO `{{N}}`, NO `{{LANG}}`/`{{TITLE}}`). Assert the temp library's `as-built.md` gained a `### {date}-d` block.
- `--slides cover-nimbus.en,intro-pillars,closing-nimbus --out {tmp}/d2.html --json` (no preset): `ok:true`, 3 slides, `as_built_entry.lang == "en"` (default_lang fallback — convention-spec §6.5 `--slides` mode), `preset == "-"`.
- `--preset nimbus-intro-pt --out {tmp}/d3.html --json`: `as_built_entry.lang == "pt"` (preset lang — convention-spec §6.5 `--preset` mode).

### library-YAML round-trip property (test-plan §1.4)
Import the engine module (importlib spec_from_file_location) and exercise its reader+writer directly:
- Parse the seed as-built entry text → assert `deviations` is "none" (NOT `[]` or `['']`), `engine_version == "1.0"` (quotes stripped → the string `1.0`), `slides` is a 7-id list.
- Parse both presets → each `slides` is a 7-id list (the wrapped `nimbus-intro-en` list and the single-line `nimbus-intro-pt` list both parse correctly).
- Construct an entry dict carrying `accent: "#B8875A"` and a `deviations` block list `["removed: proof-metrics", "modified: x — y"]`; `write` it, `parse` it back, assert field-for-field equality (the `modified: x — y` line round-trips as the verbatim STRING, never a sub-mapping; the em-dash and colon survive; `#B8875A` survives quote-unwrap). (convention-spec §4.1 round-trip invariant.)
- NEGATIVE: feed the reader a hand-written `deviations: [modified: x]` (a `:` inside a flow element) and assert it FAILS (raises / returns an error) — `:` in a flow element is forbidden (convention-spec §4.1; fixture-spec §I rule 23).

If the engine does not expose named parse/write functions, exercise the round-trip via assembling (which writes an entry) then re-reading `as-built.md` and comparing — but prefer the direct functions if present.

### --json envelope shape (test-plan §1.7)
- Success assemble → `ok:true`, `as_built_entry` populated, `output` set, `assets_copied` non-empty, `mode == "assemble"`.
- A die() case (e.g. `--slides nonexistent-id --out {tmp}/x.html --json`) → `ok:false`, `errors` non-empty, exit code 1, and stdout is a SINGLE valid JSON document (json.loads succeeds on the whole stdout).
- `--catalog-data --json` → `catalog_data` with `sections` (6, ordered), `slides` (9), `presets` (2), `mode == "catalog-data"`.
- Drift: set the temp library's `library.json` `engine_version` to `"9.9"`, run `--catalog-data --json` → `warnings` non-empty (drift warning), `ok:true` (convention-spec §8 rule 22 is a WARNING).

## Suite scaffold (match the live unittest idiom)
```python
import os, sys, json, subprocess, shutil, tempfile, time, importlib.util, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "assemble.py")
FIXTURE_PARENT = os.path.abspath(os.path.join(HERE, "..", "..", "tests"))  # holds fixture-library/ and shared-brand/
```
Provide a helper that copies `fixture-library/` + `shared-brand/` into a temp parent and drops `assemble.py` into the temp `fixture-library/`, returning the temp library path.

## Acceptance criteria
Run: `python -m unittest discover -s html/slide-library/engine/tests -p "test_engine_core.py" -v` from the repo root. ALL tests pass. Record the D29 metrics block.

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/engine-unit-result.md` the D29 block (SUITE name, exact CMD, WALL_MS, EXIT, ran/passed/failed/skipped, SKIPPED_LINES_COUNT, SKIP_REASONS, full STDOUT+STDERR). Append a one-line PASS/FAIL header.

DONE means: the suite is green, evidence with the D29 block written. Any failure or implausible metric → BLOCKED/BUG section + stop.
