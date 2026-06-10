You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context. This task operates in the tecer-biz repo on the branch `slide-library-convention-migration` (after PB-T18).

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any step, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

D29 EVIDENCE-METRICS BLOCK (binding for the render-sanity step): record WALL_MS + per-skip reasons; implausible browser timing → BUG + STOP.

Edit-anchoring rule: locate by exact strings, NEVER line numbers.

# PB-T19 — tecer-biz: migration validation (jui-py + camu DT5 bar) + merge gate

## Objective
Validate the migrated tecer library by re-assembling two known decks (jui-py + camu) and running the convention-spec §4.4 5-check mechanical property bar; confirm the round-trip; then MERGE the branch to tecer-biz `main` ONLY if all gate conditions pass (U2-S4).

## FILE ALLOWLIST (under 5-workbench/tecer-biz/)
- ✚ append to `slide-library/docs/migration-validation.md` (the validation report)
- Git operations (merge) in `5-workbench/tecer-biz/`.
- ✗ no other source-file writes. If a deck fails the bar, do NOT edit fragments/manifest — write BLOCKED + stop.

## Precondition
- PB-T17 converted + PB-T18 vendored the engine; `assemble.py --catalog-data --json` returns `ok:true` on the tecer library.
- `as-built.md` (from PB-T17) contains the 11 retro entries; among them are the records for the two validation decks. The orchestrator picked **jui-py** (a ~11-slide pt deck, zero-deviation identity case) and **camu** (a ~11-slide en deck, different spine) as the validation decks (changelog: recon-tecer-library best-validation-decks). Find their `### ` entries in `as-built.md` by id (the entry whose `slides`/`output` correspond to jui-py and to camu). If you cannot identify both entries unambiguously, write BLOCKED naming what you found — do NOT guess.

## The DT5 5-check property bar (convention-spec §4.4 — quote; implement checks 1–5)
> "1. Order identity — the slide ids and their order in the re-assembled deck EXACTLY equal the entry's `slides`. 2. Per-slide skeleton equality — for each slide, the tag/class skeleton (element tree + `class` attributes, in document order) equals the original deck's, with the text content of token-bearing nodes EXCLUDED. 3. Asset parity — the set of filenames copied into the reproduction's `assets/` equals the set the original referenced, and every reference resolves on disk. 4. Clean token report — `--check` on the reproduction reports EXACTLY the template tokens expected unfilled. 5. Headed render sanity — the reproduction loads in a visible browser, theme.css is applied, console shows zero errors."
> convention-spec §4.4: "Immediately post-migration this [upgraded canonical copy] class is EMPTY by construction (no fragment has changed since cutover) — so a fresh tecer reproduction MUST pass checks 1-5 with no excused diffs."

### Reproduction procedure (convention-spec §4.4 step 1)
For EACH of jui-py and camu: parse its as-built entry; re-run the vendored engine with the recorded `slides` (via `--slides`), the recorded `lang`, and — when each is non-`-` — the recorded `title` (`--title`), `accent` (`--accent`), `client_logo` (`--client-logo`, the same asset). Write to a FRESH reproduction path in the OS tempdir (NEVER into the library — sibling assets/ collision). Use `--json` to capture `slides`, `assets_copied`, `unfilled_tokens`.

**BOTH reproduction runs MUST pass `--no-log` (convention-spec ADX-4 / build-spec S-A12.5 / RV2-2).** A reproduction re-assembles a KNOWN deck to compare it; recording the replay would APPEND a spurious `### ` entry to the very `as-built.md` being validated — on-branch, pre-merge, polluting the committed log. `--no-log` performs the full assembly but suppresses the § 4 append; `--json` still returns the would-be `as_built_entry` (marked `logged: false`) so checks 1/3/4 can read `slides`/`assets_copied`/`unfilled_tokens`. The argv for EACH run is `python assemble.py --slides <recorded> --out <tmp>/repro.html --no-log --json [--lang ...] [--title ...] [--accent ...] [--client-logo ...]`. camu's check-2 self-consistency re-assembles TWICE (below) — BOTH of those runs ALSO pass `--no-log`.

**As-built non-pollution self-check (RV2-2 — Kimi runs this, hash compare):** BEFORE any reproduction run, record `sha256(slide-library/as-built.md)` of the validated tecer library. AFTER all reproduction runs (jui-py + camu, including the twice-assembled self-consistency runs), re-hash `slide-library/as-built.md` and assert it is BYTE-IDENTICAL (same sha256) — proving `--no-log` left the committed log untouched. A hash mismatch = the gate FAILS (a reproduction polluted the log): write BLOCKED, do NOT merge. Record both hashes in the evidence file.

### Apply the 5 checks
- Check 1 (order identity): the reproduction's slide order (from `--json` `as_built_entry.slides`, or by scanning the deck's `<section>`s in order) == the entry's `slides`.
- Check 2 (skeleton equality): the original deck for these retro entries may NOT exist on disk (the `output` is a historical sentinel — convention-spec §4.2/RV-5). Since there is no committed original, apply the ZERO-DEVIATION self-consistency form (convention-spec §4.4 zero-deviation case): re-assemble the SAME recorded input TWICE (BOTH runs with `--no-log` — RV2-2) and assert the two reproductions' tag/class skeletons (element tree + class attrs, document order, excluding token-bearing text) are identical. Parse with stdlib `html.parser`. (If the original deck DOES exist on disk at the recorded `output`, compare against it instead — but only excuse a skeleton diff if `git log` evidences a fragment change between the entry's date and now; absent that, a diff is a FAILURE.)
- Check 3 (asset parity): the reproduction's `assets/` filename set == the assets the entry's slides reference (resolve via the manifest); every reference resolves on disk.
- Check 4 (clean token report): `python assemble.py --check {reproduction} --json` → the residual `{{TOKEN}}` set == the template tokens in the composed templates (the entry's template-kind slides). exit 1 (tokens present, as expected for an unfilled reproduction). (`--check` is a check mode — it never appends to `as-built.md`, so no `--no-log` is needed here; only the assemble re-runs take `--no-log`.)
- Check 5 (headed render sanity): load the reproduction in a HEADED browser (Playwright `chromium.launch(headless=False)` if a display is available; if the agent-chain desktop is headless — `GetForegroundWindow()==0` class, learnings S2.2 — SKIP check 5 with the EXACT reason string and note that the done-boundary protocol will perform the headed render; do NOT fail). When it runs: assert theme.css is applied (a known class renders) and ZERO console errors.

BOTH decks MUST pass checks 1–4 (and 5 if a display is available) with NO excused diffs (post-migration empty upgraded class).

## Round-trip re-confirm (convention-spec §9.5 / §8 rule 23)
Re-run the as-built round-trip for all 11 entries via the vendored engine's reader/writer (or the migration script's checker): `parse(write(entry)) == entry`. A mismatch FAILS the gate.

## MERGE GATE (U2-S4 / build-spec S-C6) — all conditions MUST hold
1. Round-trip passes for all 11 entries.
2. jui-py AND camu both pass checks 1–4 (5 if available) with no excused diffs.
3. The 57-title human review (PB-T17) is RECORDED as complete by the orchestrator. (You cannot self-approve the titles — if the orchestrator has not marked the review complete in `migration-validation.md`, STOP before merging and surface it.)
4. The `as-built.md` non-pollution self-check PASSES: `sha256(slide-library/as-built.md)` is byte-identical before vs after all reproduction runs (RV2-2 — proves `--no-log` suppressed every replay append). A mismatch FAILS the gate.

If ALL hold: merge the branch to `main`:
```
git -C 5-workbench/tecer-biz checkout main
git -C 5-workbench/tecer-biz merge --no-ff slide-library-convention-migration -m "feat(slide-library): migrate to RBTV slide-library convention v1"
```
(Do NOT push unless the orchestrator says so.) If ANY condition fails → do NOT merge; stay on the branch; write BLOCKED naming the failed condition (the PB-T16 pre-commit is the rollback point).

## Acceptance criteria (self-verifiable)
1. Both jui-py and camu reproductions ran (every assemble run passing `--no-log`); their check-1..4 results are PASS (check 5 PASS or SKIP-with-reason).
2. Round-trip PASS for all 11 entries.
3. `sha256(slide-library/as-built.md)` is IDENTICAL before vs after all reproduction runs (the `--no-log` non-pollution self-check — RV2-2); both hashes recorded in evidence.
4. If merged: `git -C 5-workbench/tecer-biz log -1 --pretty=%s` on `main` == `feat(slide-library): migrate to RBTV slide-library convention v1`, and `git -C 5-workbench/tecer-biz status --porcelain` is clean. If NOT merged: BLOCKED records exactly which gate condition failed.

## Evidence file
Append to `5-workbench/tecer-biz/slide-library/docs/migration-validation.md` a `## PB-T19` section: per-deck (jui-py, camu) the 5 check verdicts (check 5 = PASS/SKIP+reason), the round-trip result, the `as-built.md` before/after sha256 pair (non-pollution self-check, RV2-2), the merge-gate condition checklist, and the merge commit hash (or the BLOCKED reason). Record the D29 metrics for the headed-render step.

DONE means: both decks validated to the §4.4 bar (check 5 may skip if headless, with reason), round-trip green, the `as-built.md` hash byte-identical before/after (no replay pollution), and EITHER the merge landed (all gate conditions met) OR a precise BLOCKED record of the failed condition. NEVER merge with a failing gate.
