# Fixture Self-Check Results

Check 1: PASS -- 6 keys present: ['convention_version', 'default_lang', 'engine_version', 'extra_asset_root', 'name', 'sections']
Check 2: PASS -- 9 data rows, each exactly 10 cells
Check 3: PASS -- all 9 slide files exist
Check 4: PASS -- all 4 bare assets exist
Check 5: PASS -- shared-brand/partner-mark.png exists
Check 6: PASS -- presets: 2 yaml blocks, as-built: 1 yaml block
Check 7: PASS -- no forbidden tags in any fragment
Check 8: PASS -- covers have no slide-number; other 7 have exactly one
Check 9: PASS -- all headings exact case
Check 10: PASS -- no literal pipes, required cells non-empty, kinds valid, langs lowercase
Check 11: FAIL -- preset2 slides length=6, expected 7

## BLOCKED

Check 11 fails because `fixture-spec.md` section C specifies the `nimbus-intro-pt` preset with only 6 slide ids:

```yaml
slides: [cover-nimbus.pt, intro-pillars, problem-cards, how-nimbus-works, proof-metrics, closing-nimbus]
```

However, `fixture-spec.md` section H check 11 requires "both presets' `slides` parse to 7 ids each".
The `nimbus-intro-en` preset has 7 ids (including `nimbus-divider`), but `nimbus-intro-pt` is missing `nimbus-divider` and therefore has only 6 ids. The prose in section C says the pt preset has the "Same spine as nimbus-intro-en with the Portuguese cover", which suggests `nimbus-divider` should be present, but it is absent in the verbatim YAML block.

Per the ORCHESTRATOR ADDENDUM rule 1, the fixture files were created verbatim from the binding source and were NOT modified to "fix" this inconsistency. The self-check therefore cannot pass check 11 as written.

## Git status

```
?? html/slide-library/tests/
```

## Rerun after ADX-10

Check 1: PASS -- 6 keys present: ['convention_version', 'default_lang', 'engine_version', 'extra_asset_root', 'name', 'sections']
Check 2: PASS -- 9 data rows, each exactly 10 cells
Check 3: PASS -- all 9 slide files exist
Check 4: PASS -- all 4 bare assets exist
Check 5: PASS -- shared-brand/partner-mark.png exists
Check 6: PASS -- presets: 2 yaml blocks, as-built: 1 yaml block
Check 7: PASS -- no forbidden tags in any fragment
Check 8: PASS -- covers have no slide-number; other 7 have exactly one
Check 9: PASS -- all headings exact case
Check 10: PASS -- no literal pipes, required cells non-empty, kinds valid, langs lowercase
Check 11: PASS -- round-trip OK: deviations='-', engine_version='1.0', all slides lists have 7 ids

## Git status (rerun)

```
?? html/slide-library/tests/
```
