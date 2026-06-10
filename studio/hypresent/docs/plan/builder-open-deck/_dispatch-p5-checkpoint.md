# DISPATCH HEADER — p5-checkpoint (B15) — COLD VERIFIER (claude:sonnet)

You are the INDEPENDENT COLD VERIFIER for the FINAL checkpoint of the builder-open-deck plan. You verify the whole v1 against its contract criteria by exercising the REAL application yourself. You receive ONLY the contract criteria and the running artifact — never the builders' tests-as-claims, evidence sheets, or return messages. Your verdicts come from YOUR OWN exercise.

## Isolation — what you MUST NOT read

- Any `findings-*.md` under `phase-1/` … `phase-4/` evidence folders (prior builder/verifier sheets)
- `run-log.md`, `state-capsule.md`, any `_dispatch-*.md`, any `_*-run-*.log` (conductor surfaces)
- Builder test FILES as a substitute for exercising (you RUN the suite in criterion 4; you do not grade criteria by reading test code)

## What you work with

- **App root (work-dir):** `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent`
- **Plan folder:** `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck`
- **Context files you MUST read** (the task's own table): `deliverables.md`, `decisions.md`, `structured-problem-2026-06-09.md` § Success Criteria, `learnings.md` — all in the plan folder.
- **Test seams** (env-gated, for native dialogs only — every other gesture is REAL): set `HYP_TEST_DIALOG=1` on the server process; `POST /api/_test/set-dialog` (native open/save file dialogs), `POST /api/_test/set-folder-dialog` (library folder picker). Server start + browser helpers: see `tests/e2e/conftest_helpers.py` (`start_server`) and `tests/e2e/builder_helpers.py` for the idiom — reuse the helpers to LAUNCH; the exercising gestures stay yours.
- **OWNER DATA — READ-ONLY, ABSOLUTE:** the root decks `tecer-gsmm-introduction*.html` at the app root are the owner's REAL decks. NEVER write to them or save over them. Copy ONE original (e.g. `tecer-gsmm-introduction.html`) to an OS temp folder and exercise on the COPY. SHA-256 hash all 4 originals BEFORE and AFTER your whole session and record both sets (must be identical). Ignore the `-test*/-v2/-v3` leftover files; do not use or modify them.

## The contract — 6 criteria (from `phase-5/p5-checkpoint.task.md`, verbatim intent)

1. **v1 success criteria hold end-to-end:** ONE CONTINUOUS HEADED session on a real deck copy — open it in the builder; reorder slides; remove a slide; duplicate a slide; add a blank slide; add a library slide; save as a NEW file; switch to editor (the save-and-switch crossing); make a real edit (type a recognizable marker ` [CV-B15]` into a slide's text via real keyboard); switch back to the builder. Every gesture works as the structured problem's Success Criteria state. Evidence captured to `phase-5/evidence/` DURING the session.
2. **All deliverables landed:** every `deliverables.md` row is ✅ (or explicitly deferred with a reason). Audit the actual table.
3. **No marker leakage anywhere:** the files YOUR session saved contain no `hyp-` / `data-hyp-*` tokens. Check the saved bytes on disk.
4. **Full regression green:** run `python -m pytest tests/e2e -q` from the app root; exit code 0 read off the UN-PIPED process. (If failures occur, report them as failures — there is no sanctioned pre-existing-failure baseline.)
5. **p5-refs passed:** evaluate against the adjudicated report `phase-5/evidence/p5-refs-link-check.md` and the `D-link-standard-adjudication` entry in `decisions.md` — rows adjudicated there as noise / tolerated variants / historical records are NOT failures. You may re-run `phase-5/evidence/p5-refs-link-check.py` to confirm the current state matches the report.
6. **decisions.md audit:** append-only history intact (Original Shaping immutable, entries never rewritten — supersession only by appending); entries are decision+rationale+scope shaped, not file-lists or execution narratives.

## Fidelity floor — binding (per the installed `rbtv-done-gate` rule)

- HEADED browser (`headless=False`), REAL mouse/keyboard gestures — NEVER synthetic in-page `dispatchEvent` for the owner-gesture criteria.
- Real application running whole (the real server, the real pages); the owner's real deck (as a temp COPY).
- Evidence captured as FILES on disk DURING the exercise (screenshots at each criterion-1 stage, saved-file byte checks, suite output, hash records). Prose claims never count.
- **ANTI-COUNT-ONLY OBLIGATION (binding):** any criterion about content, order, or identity MUST be proven at content/order/identity level — a bare count (rows, slides, length) is necessary but NEVER sufficient. Concretely for criterion 1: prove the reorder by section-content order in the SAVED file's bytes (e.g., extract each top-level `<section>`'s identifying text and show the new order); prove the removal by the removed slide's text being ABSENT; prove the duplicate by the duplicated content appearing at both expected positions; prove the post-crossing edit by ` [CV-B15]` present in the round-trip saved bytes. Screenshots support; disk-content assertions decide.
- A criterion you genuinely cannot exercise → verdict `unexercisable` + the concrete blocker. Never silently skip; never grade a criterion you did not exercise.

## Required outputs

1. **Evidence captures** → `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck/phase-5/evidence/` (screenshots, byte-check outputs, suite log, hash records, any driver script you write).
2. **Findings sheet** → same folder, `findings-p5.md`: one row per criterion — criterion (verbatim) | gesture performed | observed result | evidence file(s) | verdict `held` / `held-surprising` / `failed` / `unexercisable` + reason. End the sheet with a **`## Human Review Presentation`** section: per-criterion verdict list + the specific items that need the owner's judgment, written for a reader with zero session context.
3. **Done-gate evidence sheet** (same verdicts, done-gate table shape) → `C:/Users/henri/Documents/second-brain/1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-10-builder-open-deck.md` — cite evidence files by vault-root-relative paths (`3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck/phase-5/evidence/...`).

## Bounds

- Write ONLY: the two evidence locations above + OS-temp working copies. NEVER app/server/test source, never task/plan/decisions files, never the owner decks.
- NO git operations (no staging/commit/push) — do not invoke any commit skill. NO web work.
- Do not fix defects you find — report them. A `failed` verdict with evidence is a valid, useful return.

## Return — EXACTLY these five named fields as your final reply

- `status`: EXACTLY one of `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`. (`DONE`/`DONE_WITH_NOTES` = the exercise COMPLETED — even with `failed` criterion verdicts; the verdicts live in the sheet. No other status value is valid.)
- `landed`: the evidence files you created (both locations), with the per-criterion verdict summary (e.g. "C1 held, C2 held, …").
- `validation`: each command/exercise you ran — command, `EXIT`, `WALL_MS`, `SKIPPED_COUNT: 0` (any skip needs a per-skip reason). Include the suite run, the hash brackets, and the disk-content assertions.
- `concerns`: honest residual doubts, surprising observations, anything the owner should weigh.
- `open_questions`: unresolved items (empty if none).

Your final text IS the parse surface — the five fields, nothing after them.
