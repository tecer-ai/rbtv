# p2-3 — Live builder save copies no own-assets: root-cause evidence

**Date:** 2026-06-12
**Task:** `docs/plan/own-asset-colocation/dispatch/p2-3-dispatch.md`
**Method:** `superpowers:systematic-debugging` (root cause before any fix)
**Verdict:** ROOT CAUSE = **suspect #1 — assets-less `source_path` is the INPUT; the handler is correct.** No code fix landed. Returned `DONE_WITH_NOTES` with a design question for the conductor/owner.

---

## 1. Summary (one line)

The committed handler `handle_deck_save` (`3ce0400`) is correct and the live builder→server save path is correct. The owner's failed save copied nothing because **the deck the owner opened had no `assets/` folder beside its source file** — there were no own-assets to copy, so the handler correctly skipped (spec Behavior row 5: missing source asset tolerated, no error).

## 2. The decisive evidence — captured live `/api/deck-save` payloads

Instrumentation was temporarily added to `handle_deck_save` to log the received `source_path`, `out_path`, `items`, `source_root`, `source_root/assets` existence, and the result. Two scenarios were driven HEADED through the REAL builder UI (open → restructure → Save-As to a new empty dir). Instrumentation removed after capture (`server/deck_api.py` is byte-identical to `3ce0400`; `git diff` empty).

Captured log: `./p2-3-live-payloads.jsonl`
Repro result summary: `./p2-3-repro-results.json`
Headed driver: `tests/e2e/p2_3_live_repro.py`

| Scenario | Source dir has `assets/`? | `source_root_assets_exists` (captured) | Assets copied to dest | Live path verdict |
|----------|---------------------------|-----------------------------------------|------------------------|-------------------|
| **(a)** real `small-deck-v3/tecer-pitch-deck.html` copied to temp WITH its `assets/` | yes | `true` | **5** (`tecer-wordmark.png`, `light-mesh-bg.png`, `founder-guilherme.png`, `founder-henrique.jpeg`, `founder-luiz.jpeg`) | **WORKS** |
| **(b)** bare `tecer-gsmm-introduction-test-v3.html` copied to temp with NO `assets/` beside it | no | `false` | **0** (`assets_copied: []`) | correct skip (Behavior row 5) |

Both saves returned STATUS 200. The ONLY difference between copy-everything and copy-nothing is whether `source_root/assets/` exists. The live builder→server path replicates the direct-call behavior exactly; there is no live-path divergence in the handler.

## 3. Why this is the owner's exact scenario (forensic match)

The owner reported `teste.html` referenced: `founder-guilherme.png`, `founder-henrique.jpeg`, `founder-luiz.jpeg`, `gsmm-logo.png`, `tecer-wordmark-white.png`.

The repo-root `tecer-gsmm-introduction-test-v3.html` (and `tecer-gsmm-introduction.html`) reference EXACTLY those names (`gsmm-logo.png`, `tecer-wordmark-white.png`, `founder-*`), and **neither has an `assets/` folder beside it** (verified on disk). A deck of this shape — a standalone gsmm pitch HTML shipped/copied WITHOUT its assets folder — is what the owner opened. With no source assets present, the colocation feature correctly copies nothing.

(The Desktop `teste.html` itself was already deleted by the time this task ran — conductor verified it existed earlier; it no longer does. The forensic match above stands on the gsmm-deck asset-name fingerprint, which is unambiguous.)

## 4. Suspects ruled OUT by the captured evidence

- **Suspect #2 (stale bytecode / wrong server instance):** `__pycache__` was cleared and `deck_api.__file__` confirmed to resolve to the committed file. Scenario (a) on a fresh server copied all 5 assets — the live server runs the `3ce0400` code correctly. RULED OUT.
- **Suspect #3 (restructured `items` shape):** the captured `items` after a real restructure (drop slide 3 + duplicate slide 1) are all `{"kind":"existing","index":i}` with the expected indices; the loop scanned them correctly and copied every referenced asset in scenario (a). RULED OUT.

## 5. Root cause (named, per systematic-debugging Phase 1–3)

**The feature works as specified. The owner's failure is an input condition the spec explicitly tolerates (Behavior row 5), not a bug in the code.** The deck opened had no own-assets on disk beside it, so "copy the deck's own referenced assets" had nothing to copy. The handler, the builder POST (`deck-save.js` sends `source_path: deck.path` = the real resolved open path), and the open-flow (`api.py` resolves the real path) are all correct.

## 6. No fix landed — and why

Per systematic-debugging, a fix must address a root cause. Here the root cause is "the input deck carried no assets," which is correct, spec-tolerated behavior — there is no defect to fix in the code. Per the dispatch's explicit suspect-#1 clause ("do NOT silently re-spec the feature — document the finding + candidate design options"), no code was changed. `server/deck_api.py` remains byte-identical to `3ce0400`.

## 7. The design question (for conductor/owner — `open_questions`)

The feature, as built, only colocates assets that physically exist beside the **opened source file**. When the owner opens a standalone deck HTML that was shipped/copied WITHOUT its `assets/` folder, save-to-new-dir copies nothing — the saved deck's own images 404 in the editor too (the source images simply do not exist on this machine at that location).

Is that acceptable, or should the feature be extended? Candidate options (NOT implemented — for the owner to rule on):

- **(A) Accept as-is.** Document the precondition: "save-to-new-dir colocates a deck's own assets only when the deck is opened from a directory that has its `assets/` folder beside it." Owner must keep decks with their assets. Zero code change. (This is the current behavior.)
- **(B) Surface a warning at save.** When a preserved section references `assets/X` that is NOT found beside the source, return those missing refs in the response and show a non-blocking builder warning ("3 own-asset references could not be colocated — source assets not found beside the deck"). Owner-rejected approach (c) "warn-at-save" was rejected for the COLOCATION mechanism, but a *missing-source* warning is a different, smaller surface — re-confirm with owner. Small code change.
- **(C) Resolve missing source assets from a fallback root** (the deck's original doc-root, or a configured asset library). Larger surface; risks pulling the wrong image; not clearly in scope. Likely over-engineering.

Recommendation: **(A)** as the default (the feature is correct), with **(B)** as a small, high-value usability follow-up IF the owner wants to be told when a deck's own assets are missing rather than silently shipping broken refs. (B) directly prevents the surprise the owner hit.

## 8. Validation (commands · EXIT · WALL_MS)

| # | What | Command | EXIT | WALL_MS | Evidence |
|---|------|---------|------|---------|----------|
| 1 | Captured live payloads (both scenarios) | `python tests/e2e/p2_3_live_repro.py` (headed) | 0 | 7504 | `./p2-3-live-payloads.jsonl`, `./p2-3-repro-results.json` |
| 2 | Headed repro: (a) 5 assets copied, (b) 0 copied | (same run, `headless=False`) | 0 | 7504 | `./p2-3-repro-results.json` |
| 3 | Full unit+e2e suite (no code changed) | `python -m pytest -q` (from hypresent app dir) | SEE RETURN | SEE RETURN | suite result below |
| 4 | Disk proof: dest `assets/` after scenario (a) save | listing in `./p2-3-repro-results.json` → `dest_assets_dir_listing` (5 files) | n/a | n/a | `./p2-3-repro-results.json` |

The editor-render proof for the working path (scenario a) is already on disk from p2-1 (`./run-summary.json`, `06-editor-open.png`, `07-editor-images-probed.png` — own + collision images `naturalWidth=1`). This task re-confirmed the disk colocation independently on the REAL `small-deck-v3` deck.

---

## Return fields (durable copy)

- **status:** `DONE_WITH_NOTES`
- **landed:** No production code changed — `server/deck_api.py` byte-identical to `3ce0400` (instrumentation added then fully removed; `git diff` empty). New files (all inside allowlist): `tests/e2e/p2_3_live_repro.py` (headed repro driver), and evidence under `docs/plan/own-asset-colocation/phase-2/done-gate-evidence/`: this sheet, `p2-3-live-payloads.jsonl`, `p2-3-repro-results.json`. No commit (commit_policy: none).
- **validation:** see §8 table. Headed repro EXIT 0 / WALL_MS 7504 captured both payloads; pytest suite result recorded in the return message.
- **concerns:** The owner's original `teste.html` was already deleted before this task, so the forensic match rests on the gsmm-deck asset-name fingerprint (unambiguous) rather than the artifact itself. The "render in builder" sub-claim remains separately unexercisable (pre-existing srcdoc `<base>` gap, decisions.md 2026-06-12) — orthogonal to this bug.
- **open_questions:** Design question in §7 — accept current behavior (A), add a missing-source warning (B), or resolve from a fallback root (C)? Recommendation: (A) default + (B) as a small usability follow-up. Owner/conductor to rule.
