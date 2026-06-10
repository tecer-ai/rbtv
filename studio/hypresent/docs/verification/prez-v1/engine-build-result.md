# PB-T2 Engine Build Result

## Probe 1: `--help`

**Command:**
```
python html/slide-library/engine/assemble.py --help
```

**Outcome:** exits 0. Help text lists all modes (`--preset`, `--slides`, `--check`, `--catalog`, `--catalog-data`) and all flags including `--no-log`.

**Status: PASS**

---

## Probe 2: Import test

**Command:**
```
python -c "import importlib.util,sys; spec=importlib.util.spec_from_file_location('a', r'html/slide-library/engine/assemble.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('OK', m.ENGINE_VERSION)"
```

**Outcome:** prints `OK 1.0`. Module imports cleanly.

**Status: PASS**

---

## Probe 3: `--catalog-data --json`

**Command:**
```
python {tmplib}/assemble.py --catalog-data --json
```

**Outcome:** `ok: True`. `catalog_data` contains 9 slides, 2 presets, 6 sections. One WARNING emitted for `partner-mark.png` not listed in the Assets table (it is referenced via `@root/` and lives in `shared-brand/`, not in the library `assets/` folder).

**Status: PASS**

---

## Probe 4: `--preset` assembly

**Command (as specified in acceptance criteria):**
```
python {tmplib}/assemble.py --preset nimbus-intro-en --out {tmp}/deck.html --json
```

**Outcome:** `ok: false`. Error: `Row cover-nimbus.en: {client-logo} requested but --client-logo not provided`.

**Root cause:** The engine correctly implements convention-spec §8 rule 15: `{client-logo}` with no `--client-logo` → die. The `nimbus-intro-en` preset includes slide `cover-nimbus.en`, whose manifest `assets` cell lists `{client-logo}`. Because `--client-logo` is not provided, validation fails before any byte is written.

**Verification with `--client-logo` (to confirm the rest of the pipeline):**
When `--client-logo` IS passed (pointing to a dummy logo file), the same command returns:
- `ok: true`
- 7 slides
- `assets_copied` includes `partner-mark.png`
- `as_built_entry.logged == true`

**Status: BLOCKED** — blocked by the interaction between the fixture’s `{client-logo}` asset and the engine’s strict rule-15 enforcement.

---

## Probe 5: `--no-log` line-count delta

**Command (as specified):**
```
python {B}/assemble.py --preset nimbus-intro-en --out {tmpB}/d.html --no-log --json
```

**Outcome:** Same block as Probe 4: assemble aborts because `{client-logo}` is required by the preset but `--client-logo` is not passed.

**Verified behavior with `--client-logo` added:**
- Fresh copy A (normal assembly, no `--no-log`): as-built.md lines before=25, after=43, **delta=+18** (entry appended).
- Fresh copy B (`--no-log`): as-built.md lines before=25, after=25, **delta=0** (unchanged).
- Deck file `{tmpB}/d.html` exists.
- JSON envelope `as_built_entry.logged == false`.

**Status: BLOCKED** — same rule-15 interaction as Probe 4. The `--no-log` mechanism itself is verified to work correctly when assembly is allowed to proceed.

---

## Probe 6: Collect-all (RV2-4)

**Collect-all test:**
- Mutated manifest: changed `kind: template` → `Template` on multiple rows, and `section: opening` → `Openning` on multiple rows.
- Ran `python {tmplib}/assemble.py --catalog-data --json`.
- Result: `ok: false`, `error_count: 7` (both violations present on multiple rows; engine did NOT die on the first).

**Hard-fault test:**
- Deleted `manifest.md` from a fresh copy.
- Ran `python {tmplib}/assemble.py --catalog-data --json`.
- Result: `ok: false`, `error_count: 1`, single error `manifest.md not found` — immediate abort.

**Status: PASS**

---

## git status

```
?? html/slide-library/engine/
```

Only `html/slide-library/engine/assemble.py` (and its parent directory) is untracked, as required.
