You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context. This is a FRESH implementation — you are NOT copying tecer's assemble.py; the divergence callouts below are binding (porting tecer's behavior where a divergence is stated is a DEFECT).

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate code/content by the exact strings quoted in this file. NEVER use line numbers.

# PB-T2 — The RBTV slide-library engine (single file)

## Objective
Implement the engine at `html/slide-library/engine/assemble.py` — ONE stdlib-only Python file, internally section-disciplined. It assembles single-file HTML decks from a spec-compliant library, validates per the 24-rule table, writes an append-only as-built log in a pinned YAML subset, generates a catalog, and exposes a `--json` machine-readable face. Verify it imports and `--help` works; the full test verification is PB-T3/PB-T4.

## FILE ALLOWLIST
- ✚ create `html/slide-library/engine/assemble.py`
- ✗ nothing else.

## Stack invariants
- Python STANDARD LIBRARY ONLY (`argparse`, `html`, `re`, `shutil`, `sys`, `json`, `pathlib`, `datetime`). NEVER a YAML/CSV/TOML library.
- `argparse` with `allow_abbrev=False`.
- The file resolves the library root as its own parent directory: `LIBRARY = Path(__file__).resolve().parent`. All library artifacts are `LIBRARY / name` EXCEPT explicit CLI path args (`--out`, `--check FILE`, `--client-logo PATH`).
- Internal section banners (comments) in this order: Parsing / library-YAML subset / Validation / Assembly / As-built writer / Catalog / CLI.

---

## REUSE THESE EXACT MECHANICS from the proven tecer engine (unchanged behavior — match them)

These pieces are identical in behavior to tecer's live `assemble.py`. Reproduce their shape:

Row splitter (handles the surrounding-pipe markdown form):
```python
def _split_row(line):
    cells = line.strip().split("|")
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]
```

Token + slide-number regexes:
```python
TOKEN_RE = re.compile(r"\{\{[^}]+\}\}")
SLIDE_NUMBER_RE = re.compile(r'(<div class="slide-number">)\{\{N\}\}(</div>)')
```

Renumbering (counter advances ONLY on a real {{N}}):
```python
def renumber_slides(body):
    counter = {"n": 0}
    def repl(match):
        counter["n"] += 1
        return f"{match.group(1)}{counter['n']}{match.group(2)}"
    return SLIDE_NUMBER_RE.sub(repl, body)
```

base.html filling (marker set + accent-line removal):
```python
for marker in ("{{LANG}}", "{{TITLE}}", "/* {{ACCENT_CSS}} */",
               "/* {{THEME_CSS}} */", "<!-- {{SLIDES}} -->"):
    if marker not in doc:
        die(f"base.html is missing the marker: {marker}")
doc = doc.replace("{{LANG}}", lang)
doc = doc.replace("{{TITLE}}", html.escape(title))
if accent:
    accent_css = f":root {{ --client-accent: {accent}; }}"
    doc = doc.replace("/* {{ACCENT_CSS}} */", accent_css)
else:
    doc = re.sub(r"^[ \t]*/\* \{\{ACCENT_CSS\}\} \*/[ \t]*\n", "", doc, count=1, flags=re.MULTILINE)
doc = doc.replace("/* {{THEME_CSS}} */", theme)
doc = doc.replace("<!-- {{SLIDES}} -->", slides_html)
```

Asset copy (validate ALL sources before any write; copy leaf names into sibling assets/):
```python
asset_plan = {}  # leaf_name -> source Path
for ...:
    src = resolve_asset_source(entry, client_logo)
    asset_plan[src.name] = src
# ... after all validation passes:
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(document, encoding="utf-8")
if asset_plan:
    sibling_assets = out.parent / "assets"
    sibling_assets.mkdir(parents=True, exist_ok=True)
    for name, src in sorted(asset_plan.items()):
        shutil.copy2(src, sibling_assets / name)
```

Preset-block discovery regex:
```python
blocks = re.findall(r"```ya?ml\s*\n(.*?)```", text, re.DOTALL)
```

---

## DIVERGE FROM TECER HERE (binding — these are the NEW behaviors; tecer does it differently)

The frozen contract `convention-spec.md` mandates these. Each quote below is the contract clause you implement, marked with its § origin.

### Manifest = 10 columns (tecer has 9; NEW column `title` at position 4)
> convention-spec §2.2: "The 10-column slide schema: `id | file | section | title | audience | lang | kind | summary | assets | provenance`". The header MUST equal exactly these 10 names in order; mismatch → die() with line number.
Constant:
```python
MANIFEST_COLUMNS = ["id","file","section","title","audience","lang","kind","summary","assets","provenance"]
```

### Heading match is CASE-SENSITIVE (tecer lower-cases)
> convention-spec §2.1: "the section heading MUST be exactly `## Slides` (likewise `## Assets`, `## Presets`, `## As-built log`)... A library author's `## SLIDES` or `Id` column is INVALID."
Track the slides table only under a heading whose stripped text == `## Slides` EXACTLY (NOT `.lower()`). Same for `## Assets`.

### Separator row is POSITIONAL (tecer uses a content guard)
> convention-spec §2.1: "The separator row is identified POSITIONALLY: it is the SECOND physical table row, immediately after the header — never identified by content. The engine skips exactly that one row and treats every later `|`-row as data."
Skip the 2nd `|`-row under `## Slides` unconditionally. Do NOT use any `set(...) <= set("-: ")` content check.

### Pipe-in-cell FORBIDDEN (tecer has no guard)
> convention-spec §2.1: "A literal `|` is FORBIDDEN inside any cell. ... On a pipe-induced cell-count mismatch the engine MUST die() naming the offending row's `id` if recoverable, else the line number." (Backslash-escaping `\|` is NOT supported — a cell containing `\|` is still invalid.)
A row whose split cell-count ≠ 10 → die() naming `cells[0]` (the id) if present, else the line number.

### Empty required cells REJECTED (tecer accepts '')
> convention-spec §2.5: "Any MUST cell is empty after trim ... The non-empty-required set is: `id`, `file`, `section`, `title`, `lang`, `kind`, `summary`." Reject (die) any empty one. `audience` empty → `general`; `assets` empty/`-` → none; `provenance` may be `-`.

### Enums CASE-SENSITIVE exact-match (tecer unpinned)
> convention-spec §2.2 / §8 rules 7,8,9: "`kind` ∈ {`ready`,`template`} (exact lowercase); `lang` a lowercase ISO-639-1-style token; `section` MUST exactly match a `library.json` `sections` entry." A miscased/unknown value (`Template`, `EN`, `Opening`) → die().

### Duplicate id REJECTED
> convention-spec §2.5: "Any `id` is duplicated → invalid library." die().

### Asset resolution keys on the `@root/` PREFIX, NEVER on `/`-presence (tecer triggers on `/` — INVERTED here)
> convention-spec §2.4: "The engine MUST key extra-root resolution on the literal `@root/` PREFIX, NEVER on `/`-presence. ... a bare `path/with/slash` resolves from `{library}/assets/` (and 404s if absent), never from the extra root. ... Only `@root/...` reaches `extra_asset_root`."
Resolution table (convention-spec §2.4):
- bare filename → `LIBRARY/assets/{name}`
- `@root/path` → `extra_asset_root` (from library.json) joined with `path`, relative to LIBRARY
- `{client-logo}` → the `--client-logo` flag value
- `-` → nothing
> convention-spec §8 rules: 13 (resolved source must exist on disk → die), 14 (`@root/` while `extra_asset_root` is null → die), 15 (`{client-logo}` with no `--client-logo` → die), 16 (comma inside a filename mis-splits → won't resolve → die).
Output filename for every copied asset is the source LEAF name (`src.name`) — including `@root/` assets (so `@root/partner-mark.png` → output `assets/partner-mark.png`).

### Language precedence reads library.json default_lang (tecer hardcodes "pt")
> convention-spec §6.5: "`--preset`: `--lang` flag > the chosen preset's `lang` > `library.json` `default_lang`. `--slides` (no preset): `--lang` flag > `library.json` `default_lang`. `--catalog`: `library.json` `default_lang`."
NEVER hardcode `"pt"`. `--lang` is document-chrome only; it NEVER selects/rewrites ids (convention-spec §2.2 id row).

### Fragment purity scan (NEW — tecer has none)
> convention-spec §6.3 / §8 rule 12: substring scan of the RAW fragment for `<head`, `<style`, `<script`, `<html`, `<body` → any present makes the library invalid → die().

### library.json REQUIRED + version checks (NEW — tecer has no library.json)
> convention-spec §7.1 keys: `convention_version`, `engine_version`, `name`, `default_lang`, `sections` (ordered list), `extra_asset_root` (string or null).
> convention-spec §7.2 / §8 rules 20-22: convention MAJOR unsupported → die (20); MINOR differs from engine target → WARN proceed (21); engine stamp ≠ library.json engine_version → WARN proceed (22).
Constants:
```python
ENGINE_VERSION = "1.0"
SUPPORTED_CONVENTION_MAJOR = 1
ENGINE_TARGET_MINOR = 0
```
Read library.json via stdlib `json`; absent/invalid → die().

---

## The as-built log — PINNED library-YAML subset (FRESH parser AND writer; NOT tecer's _parse_yaml_block)

> convention-spec §4.1: "The library-YAML subset is NORMATIVE ... The engine implements a FRESH parser to exactly this grammar — explicitly NOT a copy-port of tecer's reader. The engine's writer MUST emit ONLY constructs in this grammar."

The grammar (convention-spec §4.1) — implement reader + writer to EXACTLY this:
- `mapping_entry := key ":" value` — `value` is a scalar, a flow_list, or EMPTY (EMPTY → the key owns the block-list `- ` lines that follow).
- `scalar` := plain or quoted. A `quoted_scalar` ('"' chars '"') UNWRAPS — the value is the content between the quotes, quotes discarded. `engine_version: "1.0"` parses to the string `1.0`. The writer MAY quote on emit; a re-parse yields the same string (round-trip holds).
- `flow_list := "[" elem ("," elem)* "]"` — plain scalars only; a `:` inside an element is FORBIDDEN. MAY wrap across physical lines until `]`.
- `block_list_item := optional_ws "-" ws rest` — `rest` is ONE PLAIN STRING, verbatim to end of line. NEVER re-parsed as a nested mapping: `"- modified: x — y"` IS the string `"modified: x — y"`.
- `#` comments and blank lines ignored anywhere.
> convention-spec §4.1: "The writer emits `deviations:` ALWAYS as a block list ... An empty deviation set is emitted as the block-list-absent form `deviations: -` (single `-` scalar meaning 'none'), NOT `deviations: []`."
> convention-spec §4.1 Round-trip invariant: "for every entry the engine writes, `parse(write(entry)) == entry` field-for-field."

Entry schema (convention-spec §4.2) — the WRITER fills:
- `date` (YYYY-MM-DD), `timestamp` (ISO-8601, datetime.now().isoformat(timespec='seconds')).
- `output`: the deck path RELATIVE to the library root (compute `os.path.relpath(out, LIBRARY)` with forward slashes).
- `slides`: the actual ordered ids (flow list).
- `lang`: resolved.
- `title`: resolved (`-` when the engine default was used and no `--title` supplied).
- `accent`: resolved hex, or `-` when no `--accent`.
- `client_logo`: the copied leaf name when `--client-logo` was passed, else `-`.
- `engine_version`: ENGINE_VERSION (quoted on emit).
- `preset`: preset name or `-`.
- `order: true` ONLY when started from a preset and the assembled SET equals the preset set but the SEQUENCE differs (convention-spec §4.2/§4.3 RV-6). Otherwise omit.
- `deviations`: block list of machine-decidable deltas ONLY — `added: {id}` / `removed: {id}` by SET DIFFERENCE between the preset's id list and the assembled ids (convention-spec §4.3). Empty set → `deviations: -`. The engine NEVER fabricates `modified:`/`bespoke:`/`reordered:`.

> convention-spec §4: "The engine MUST append one entry on every successful assembly." Append under the `## As-built log` section of `LIBRARY/as-built.md` as a `### {date}-{slug}` heading + a fenced ```yaml``` block. `{slug}` = the `--out` filename stem (e.g. `nimbus-demo.html` → `nimbus-demo`). Append-only — NEVER rewrite prior entries. EXCEPTION — `--no-log` (build-spec ADX-4 / S-A12.5): when `--no-log` is set, build the entry object normally but DO NOT append it (skip the `as-built.md` write entirely); in `--json` it surfaces in `as_built_entry` with `logged: false`. Structure the code so the entry is constructed once, then either appended-and-marked-`logged:true` OR not-appended-and-marked-`logged:false` based on the flag.

Reference entry shape (convention-spec §4.5 example) the writer must be able to round-trip:
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
```
(In the example above the agent later appends prose `reordered:`/`modified:` lines by hand; the ENGINE emits only `removed: proof-metrics` + `order: true`.)

---

## Validation = the §8 24-rule table (authoritative)
Implement every rule in convention-spec §8 with its verdict (ERROR; WARNING = emit to stderr + proceed; reports = exit 1 if any). Run ALL validation BEFORE any byte is written — a failure leaves zero partial output and no assets/ folder. The §8 rules and their decidable methods are the ones inlined above (manifest §2.x, assets §2.4, purity §6.3, markers §6.1, version §7.2, round-trip §4.1, `--check` §6.3). Assets-table completeness (rule 17) is a WARNING.

### Error accumulation by mode (build-spec S-A6.1a / RV2-4 — collect-all vs fail-fast)
The §8 ERROR verdict is realized DIFFERENTLY per mode — do NOT die on the first error in the diagnostic modes:
- **`--check` and `--catalog-data`** (the GUI/diagnostic modes): ACCUMULATE every decidable §8 violation into a list (one run = the FULL list), continuing validation past each failure wherever the next check is still decidable (e.g. keep scanning rows after a bad row, keep checking other enums after a bad enum), THEN return `{ok:false, errors:[<all messages>]}` and exit 1. The GUI consumes the full list (the invalid-library state shows ALL errors, not just the first — ADX-2 "a GUI needs the full list"). Implement this with an `errors = []` accumulator passed through the validator; append a message instead of raising for each accumulable soft violation.
- **`--preset`/`--slides`** (assemble): stay FAIL-FAST — the first hard ERROR aborts before any byte is written (zero partial output). In `--json` the envelope still emits `{ok:false, errors:[...]}` with everything collected up to the abort.
- **HARD FAULTS** (`library.json` or `manifest.md` absent / unreadable / unparseable): abort IMMEDIATELY in every mode via `die()`/`EngineDie` — you cannot accumulate over an unreadable manifest. These stay single-error.
- A violation that blocks deciding later checks on the SAME element (e.g. a row failing the 10-cell split cannot be enum-checked) records its own error and skips dependent checks on that element only; OTHER elements continue to be validated.

## CLI surface (exact)
Mutually-exclusive required mode group: `--preset NAME`, `--slides id1,id2,...`, `--check FILE`, `--catalog`, `--catalog-data`. Global flags: `--out FILE`, `--lang L`, `--title T`, `--accent #HEX`, `--client-logo PATH`, `--json`, `--no-log`. `--preset`/`--slides` require `--out` → else die. `allow_abbrev=False`. There is NO `--client` and NO `--date`.

### `--no-log` replay flag (build-spec ADX-4 / S-A12.5 — implements convention-spec ADX-4 verbatim)
> convention-spec ADX-4: "The engine gains a `--no-log` flag: a VERIFICATION/REPLAY mode that performs the full assembly but suppresses the § 4 as-built append. ... In `--json` mode with `--no-log`, the envelope's `as_built_entry` field carries the entry that WOULD have been written, marked `"logged": false`."
`--no-log` is a global boolean flag (`action="store_true"`). On an assembly (`--preset`/`--slides`):
- Perform the FULL assembly exactly as without the flag (resolve order → concatenate → inline theme → renumber → fill base.html markers → validate + copy assets → token report). The deck and its sibling `assets/` ARE written.
- SKIP the as-built append (the S-A9.6 append to `LIBRARY/as-built.md`) — `as-built.md` is NOT opened or modified.
- BUILD the would-be entry object exactly as the writer would (all S-A9.2 fields). In `--json` mode put it in the envelope's `as_built_entry` with an added key `logged: false`. On a NORMAL assembly (no `--no-log`) the appended entry is reflected in `as_built_entry` with `logged: true`.
- `--no-log` is meaningful ONLY for assemble modes; it is a no-op for `--check`/`--catalog`/`--catalog-data` (those never append). Production callers (the GUI, the cold agent) NEVER pass it; only DT5/reproduction + test harnesses do. Do NOT mention it in any generated README.

`--check FILE` (convention-spec §6.3 / §8 rule 24): scan FILE for residual `{{TOKEN}}`; list them; exit 1 if any.

`--catalog` (convention-spec §6.4): regenerate `LIBRARY/catalog.html` — every manifest fragment, in `library.json` section order THEN manifest order, each preceded by a label bar `id · kind · audience · lang · summary`, theme.css inlined, NO client accent, lang = default_lang. Empty manifest → valid empty catalog.

## The `--json` envelope (NEW design — ADX-2 / build-spec S-A12)
When `--json` is set, print EXACTLY ONE JSON object to stdout as the LAST stdout output and nothing else on stdout (send all human/warning text to stderr). Exit code follows the operation. Two error shapes converge into the one envelope (RV2-4):
- ACCUMULATED §8 soft violations in `--check`/`--catalog-data` (the collect-all path above): the validator returns the full `errors[]` list — these are COLLECTED, not raised. The mode prints `{ok:false, errors:[<all>]}` and exits 1.
- HARD FAULTS and the assemble first-error abort: `die()` raises the custom exception `class EngineDie(Exception)` when a module-level `JSON_MODE` flag is true, caught at the top of each mode; the caught message is APPENDED to whatever `errors[]` was already accumulated, the envelope is printed, exit 1. When `JSON_MODE` is false, `die()` keeps the classic behavior (`print("ERROR: "+msg, file=sys.stderr); sys.exit(1)`).
`EngineDie` is reserved for HARD faults (unreadable/absent `library.json`/`manifest.md`) and the assemble fail-fast abort — it is NOT raised per accumulable §8 row in `--check`/`--catalog-data` (those append to `errors[]` and continue).

Envelope keys (build-spec S-A12.2):
- `ok` (bool), `mode` (str: assemble|check|catalog|catalog-data), `errors` (list[str]), `warnings` (list[str]), `unfilled_tokens` (list[str]), `output` (str|null), `assets_copied` (list[str]), `as_built_entry` (object|null = the entry; carries `logged: true` when appended, `logged: false` under `--no-log`), `catalog_data` (object|null).

`--catalog-data` (build-spec S-A12.4 / RV2-9): READ-ONLY (no file written). Runs the LIBRARY-LEVEL validation first — the §8 rules that need NO composition (rules 1, 2, 4-12, 18-22) — and does NOT run the per-composition asset rules (13 asset-resolves, 15 `{client-logo}`-without-flag): there is no requested composition at catalog-data time (rule 13 resolves "for the requested composition" — convention-spec §2.4; rule 15 needs `--client-logo`). So a library carrying a `{client-logo}`-bearing or `@root/` fragment loads `ok:true` for browsing; those asset rules fire ONLY in assemble modes. On success returns `catalog_data`:
```
{ "name": <library.json name>, "default_lang": ..., "sections": [<ordered>],
  "slides": [ {id, file, section, title, audience, lang, kind, summary, assets:[<list>], provenance} ... manifest order ],
  "presets": [ {preset, slides:[...], lang, title, audience} ... ],
  "extra_asset_root": <value> }
```
An invalid library → `{ "ok": false, "errors": [...] }` (the GUI shows the invalid state).

## die() helper
```python
def die(message):
    if JSON_MODE:
        raise EngineDie(message)
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(1)
```

## Acceptance criteria (self-verifiable — run these yourself in the OS tempdir)
1. `python html/slide-library/engine/assemble.py --help` exits 0 and lists all modes + flags (INCLUDING `--no-log`).
2. `python -c "import importlib.util,sys; spec=importlib.util.spec_from_file_location('a', r'html/slide-library/engine/assemble.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('OK', m.ENGINE_VERSION)"` prints `OK 1.0` (the file imports cleanly).
3. Copy the fixture library (created by PB-T1) into a tempdir, copy YOUR `assemble.py` into that temp library root, then run `python {tmplib}/assemble.py --catalog-data --json` and confirm stdout is ONE valid JSON object with `ok:true` and a `catalog_data` carrying 9 slides + 2 presets + 6 sections. (If PB-T1's fixture is not yet present, SKIP this probe and note it in evidence — PB-T3/T4 will fully verify.)
4. `python {tmplib}/assemble.py --preset nimbus-intro-en --out {tmp}/deck.html --json` → `ok:true`, 7 slides, an as-built entry appended to the temp library's `as-built.md`, `assets_copied` includes `partner-mark.png`, AND `as_built_entry.logged == true`.
5. **`--no-log` line-count delta (RV2-1 — self-verifiable, run twice on separate temp copies):** Make TWO fresh temp copies of the fixture (each with YOUR `assemble.py`). On copy A: count `as-built.md` lines, run `python {A}/assemble.py --preset nimbus-intro-en --out {tmpA}/d.html`, recount → assert the line count INCREASED (an entry was appended; delta of as-built `### ` headings == 1). On copy B: count `as-built.md` lines, run `python {B}/assemble.py --preset nimbus-intro-en --out {tmpB}/d.html --no-log --json`, recount → assert the line count is UNCHANGED (delta of `### ` headings == 0, no append) AND `{tmpB}/d.html` exists (full assembly performed) AND the `--json` envelope's `as_built_entry.logged == false`. The delta is exactly 1 (without) vs 0 (with `--no-log`). (Skip with the exact reason if PB-T1's fixture is absent.)
6. **Collect-all (RV2-4 — self-verifiable):** Make a temp fixture copy, mutate its `manifest.md` to introduce TWO independent §8 errors on DIFFERENT rows (e.g. one row's `kind` → `Template` (bad enum), another row's `section` → an undeclared value). Run `python {tmplib}/assemble.py --catalog-data --json` → assert `ok:false` AND `len(errors) >= 2` (BOTH violations present, engine did NOT die on the first). Then delete `manifest.md` from a fresh copy → assert a SINGLE error + abort (hard-fault path). (Skip with the exact reason if PB-T1's fixture is absent.)

Do these probes against TEMP COPIES only — NEVER assemble into the real fixture or library root (a sibling assets/ would collide).

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/engine-build-result.md`: the 4 acceptance probe results (command + outcome), and `git status --porcelain html/slide-library/engine/` showing only `assemble.py` created.

DONE means: `assemble.py` exists, probes 1–2 pass, probes 3–4 pass if the fixture is present (else noted), evidence written. If a probe fails, write the failure into the BLOCKED section and stop.
