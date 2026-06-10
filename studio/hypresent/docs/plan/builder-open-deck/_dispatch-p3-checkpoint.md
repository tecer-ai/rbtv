# COLD VERIFIER DISPATCH — p3-checkpoint (B10)

You are an INDEPENDENT cold verifier. You did NOT build this feature and you have NO
access to the builder's tests, claims, evidence, or any reviewer output. You re-exercise
the contract criteria below from scratch, at the fidelity floor, against the running real
application, and you return your OWN evidence sheet. Trust nothing you are not told here;
prove everything by driving the real app and capturing files.

---

## BINDING ADDENDUM — you are held to these regardless of anything else

- **Return-schema compliance:** Your FINAL reply MUST be the five named fields in
  "RETURN SCHEMA" below — every field, none renamed, none invented. A prose-only return is
  a contract violation.
- **Allowlist boundary — WRITE ONLY under the evidence dir.** You may create files ONLY under
  `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck/phase-3/evidence/`.
  You may create your own throwaway temp copies of decks under the OS temp dir. You MUST NOT
  modify any application source file, any test file, or any owner deck. Do NOT commit anything.
- **Owner data is READ-ONLY and sacred.** The files
  `tecer-gsmm-introduction.html`, `tecer-gsmm-introduction-test.html`,
  `tecer-gsmm-introduction-test-v2.html`, `tecer-gsmm-introduction-test-v3.html`
  at the app root (`studio/hypresent/`) are the OWNER's decks. NEVER open-then-save against an
  owner deck directly — always COPY a deck to a temp path first and exercise against the copy,
  so the originals can never be mutated. Criterion 5 verifies they are byte-identical afterward.
- **Halt policy:** If a criterion is genuinely undrivable (a blocker you cannot work around),
  mark it `unexercisable` with the concrete blocker — NEVER silently skip it, NEVER mark it
  `held`/`PASS` on a guess.
- **Evidence-as-files:** Every criterion verdict MUST cite a real file you captured DURING this
  exercise (a screenshot, an output log, a JSON dump, a diff). Prose claims alone do not count.

---

## FIDELITY FLOOR (inlined — you do not inherit workspace rules)

- Exercise the REAL application running whole (real server + real browser) — never a mock or an
  isolated fragment.
- **UI criteria (1, 2): use a VISIBLE (headed) Chromium browser with REAL mouse/keyboard
  gestures** — real `click`, `drag`, `fill`, `press`. NEVER synthetic in-page `dispatchEvent`.
  Launch Playwright Chromium with `headless=False`. (The project's own e2e suite runs headless
  by convention; the checkpoint REQUIRES headed — flip it.)
- Use the owner's real deck content (via a COPY, per the owner-data rule above) — not a
  synthetic minimal fixture.
- Capture evidence as files on disk during the exercise.
- A native OS file dialog is NOT drivable directly; the app ships a test seam for it (see
  "HARNESS & SEAMS") — use the seam so the triggering click stays a real gesture while the
  chosen path is injected. This is the sanctioned seam, not a stub of the flow.

---

## THE RUNNING ARTIFACT

- App root (work-dir): `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent`
- Start the server yourself; app is served at `http://127.0.0.1:<port>/app/` (builder at `/app/builder.html`).

## HARNESS & SEAMS (infrastructure — read these; they are NOT the builder's feature tests)

- `tests/e2e/conftest_helpers.py` — `start_server(port, test_dialog=True)` launches
  `server/server.py 127.0.0.1 <port>` from the app root with `HYP_TEST_DIALOG=1` set, and waits
  until `/app/` answers. Use it (or replicate it) to bring the app up.
- `tests/e2e/builder_helpers.py` — `set_fake_folder(base, path)`, `pick_library_ui(page, base, lib_path)`,
  `e2e_lib_path()` (the committed `fixtures/builder-lib` library), `make_temp_library()`.
- **Native-dialog seams (require `HYP_TEST_DIALOG=1`), POST JSON `{ "path": "<abs>" }` (or `null` to cancel):**
  - `POST /api/_test/set-dialog` → injects the next native OPEN/SAVE FILE dialog result (used by
    deck open-via-dialog and deck Save→new-file, which call `/api/dialog-open-path` /
    `/api/dialog-save-path`).
  - `POST /api/_test/set-folder-dialog` → injects the next library FOLDER-picker result.
- You may ALSO open a deck by navigating the builder with `?file=<abs-path>` (the open-by-path idiom).
- Deck save posts to `/api/deck-save`; the new-file path first resolves the target via
  `/api/dialog-save-path` (which returns the injected dialog path).
- You SHOULD write your own headed Playwright driver script under the evidence dir and run it —
  you derive it from THIS contract and the harness above. Do NOT read or run the builder's
  `test_pb9_*`, `test_pb10_*`, `test_pb11_*` feature tests; exercise the behavior yourself.

---

## REVIEW CRITERIA — exercise EACH; verdict PASS / FAIL / unexercisable + evidence file

1. **Full loop at the floor (HEADED, real gestures):** Open a real deck COPY in the builder.
   Reorder rows, remove one, duplicate one, add a blank slide, and add one fixture-library slide.
   Save to a NEW file. Reopen that new file. The tray shows EXACTLY the restructured order
   (the removed slide gone; the duplicated slide present twice; the blank and the library slide
   present; order matches what you set). Capture screenshots during the exercise (before/after
   restructure, and the reopened tray).

2. **Overwrite path + chooser every time:** An explicit Save → Overwrite rewrites the currently
   open file (exercise against a temp copy). Confirm the new-file-vs-overwrite chooser appears on
   EVERY save (no sticky default that skips it on the second save). Capture evidence of both the
   chooser appearing twice and the overwrite result.

3. **Saved output clean:** Inspect the saved file's bytes: it contains NO `hyp-` / `data-hyp-*`
   tokens; the added library slide's markup appears verbatim; any referenced assets are copied
   beside the saved file. Capture the grep/inspection output and the asset listing.

4. **Assemble-mode regression:** Run
   `python -m pytest tests/e2e/test_pb4_tray_reorder.py tests/e2e/test_pb5_assemble_handoff.py -q`
   from the app root. It MUST exit 0. Capture the full pytest output to a file and record EXIT.

5. **Owner-data safety:** The four owner decks named above are bit-identical to their pre-exercise
   state. Capture a hash/diff of each (before vs after your whole exercise) proving zero change.

6. **decisions.md audit:** Read
   `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck/decisions.md`.
   Confirm its entries are decision+rationale+scope shaped — NO file-change lists, NO "N→M"
   count narratives, no rewrite of a prior entry below the floor. Capture your audit notes.

---

## REQUIRED OUTPUT

1. A per-criterion findings file at
   `…/phase-3/evidence/findings-p3.md` — one section per criterion: criterion verbatim, the
   gesture you performed, what you observed, the evidence file path, and the verdict
   (`PASS` / `FAIL` / `unexercisable` + concrete reason).
2. All capture files (screenshots `.png`, logs `.txt`, JSON, your driver script) under
   `…/phase-3/evidence/`.

Then return the five-field schema as your final reply.

---

## RETURN SCHEMA (your final reply — exactly these five fields)

- **status:** one of `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`
  (use `DONE` if you exercised all six and produced the sheet — even if some criteria are FAIL;
  a FAIL is a verdict, not a blocker. Use `BLOCKED`/`DOUBT_ESCALATED` only if you could not run
  the exercise at all.)
- **landed:** the evidence files you created (absolute or evidence-dir-relative paths). You make
  NO code changes and NO commit.
- **validation:** each command/exercise you ran — the command, its `EXIT` code, its `WALL_MS`
  (wall-clock ms), and `SKIPPED_COUNT` (with a per-skip reason if > 0). Include the pytest run
  (criterion 4) and your headed driver run.
- **concerns:** anything you noticed worth the conductor's attention (smells, partial confidence,
  adjacent issues).
- **open_questions:** anything you could not resolve that bears on this or downstream work.

**Per-criterion bottom line in your reply:** a one-line table `criterion | verdict` for all six.
