---
name: builder-open-deck
overview: "Open an existing deck in the builder, restructure it (reorder/remove/duplicate slides, add blanks and library slides), save it through a new non-assembler recompose path, and bridge builder↔editor via save-and-switch."
orchestrated: true
orchestration_mode: deep
---

# Builder Open Deck

> Read `decisions.md` for full context, decisions, and constraints.
> Read `./deliverables.md` for the artifact index — where every task lands its output.
> Task files (`→ path`) contain per-task execution instructions.
> Behavior specs live in `./specs/` — tasks reference them, never restate them.

## Architectural Constraints

Patterns and principles that MUST be followed during execution.

| Principle | Enforcement |
|-----------|-------------|
| Byte-range section splicing only — the recompose path NEVER parses-and-re-serializes the whole deck | Reviewer greps `recompose.py` for HTML-parser usage; unit tests assert untouched spans byte-identical |
| ADX-2 — never re-implement `assemble.py`; recompose manipulates a finished deck's own sections | Reviewer compares the recompose path against the engine's responsibilities |
| Clean output — no `hyp-`/`data-hyp-*` tokens ever written into saved decks | Checkpoints inspect saved files for marker leakage |
| Two-page architecture (D20) — builder and editor stay separate; crossings are Save-As + `?file=` handoff | p4 review criteria |
| Root decks (`tecer-gsmm-introduction*.html`) are READ-ONLY owner data — tests copy before writing | Allowlists exclude them; checkpoints verify bit-identity |
| Native dialogs keep injectable launchers (`set_dialog_launcher` seam) so e2e can drive them | New dialog endpoints reuse `api._launch_dialog` |
| Assemble mode regression-free — deck mode is additive | Checkpoint regression suites (`test_pb2`–`test_pb5`) |

**Execution Rules:**
1. Read ./deliverables.md before starting any task — it tells you the exact path your output must land at
2. Update ./deliverables.md after delivering — flip your task's Status, confirm the Path matches what you produced
3. Read decisions.md before starting any task
4. One task in progress at a time
5. Dependencies are sacred — never skip prerequisite tasks
6. Checkpoints: evaluate work against review criteria in the checkpoint task file, present findings, HALT for human approval
7. decisions.md is append-only and reserved for Decision/Discovery entries per the decisions template — executors follow the executor-prompt's decisions rule for the binding constraint at dispatch time. Never modify previous decisions entries
8. Internal links use file-relative paths (`./`, `../`); external links use project-root-relative paths

## Orchestration (DEEP pre-resolution)

| Field | Value |
|-------|-------|
| Executor / reviewer | Per task frontmatter: `kimi` / `claude-opus` (checkpoints: `claude` / `claude-opus`) |
| Allowlists + validation commands | Per task frontmatter (`allowlist`, `test_command`, expected EXIT 0) |
| Batching | All tasks SERIAL in plan order — no parallel waves |
| Shared-file serialization | `app/js/builder/builder-main.js`: p2-1 → p3-1 → p3-2 → p3-3 → p4-1 · `app/js/builder/tray.js`: p2-2 → p3-1 · `server/server.py`: p1-2 only · `tests/e2e/test_pb8_deck_open.py`: p2-1 → p2-2 |
| **Hard-halt registry** | `p1-checkpoint` and `p5-checkpoint` are NEVER auto-passed, in any autonomous mode. `p2/p3/p4-checkpoint` may auto-pass in full-auto with all-PASS criteria |

## Revolving Plan Rules

- Simple discovery (<5 min): resolve immediately, document in decisions.md
- Complex discovery: add new task to plan, document in decisions.md, notify user

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Tasks

### Phase 1: Save Core — the non-assembler recompose path (the heart)

- [x] `p1-1` CREATE `server/recompose.py` (byte-range section splitting + recompose engine) with unit tests against a real deck copy → `phase-1/p1-1.task.md`
- [x] `p1-2` CREATE `server/deck_api.py` (deck-load, deck-save with asset copy, path-only dialogs) and UPDATE `server/server.py` routes → `phase-1/p1-2.task.md`
- [x] `p1-checkpoint` **CHECKPOINT** — recompose proven on a real deck: saved file opens clean headed, content intact (HARD HALT) → `phase-1/p1-checkpoint.task.md`

### Phase 2: Ingest — open a deck in the builder

- [x] `p2-1` UPDATE builder with "Open deck…" entry + `?file=` arrival loading the deck model and filling the tray → `phase-2/p2-1.task.md`
- [x] `p2-2` UPDATE tray/previews so existing-section rows render thumbnails with the deck's own theme → `phase-2/p2-2.task.md`
- [x] `p2-checkpoint` **CHECKPOINT** — deck opens with all slides as correct themed thumbnails → `phase-2/p2-checkpoint.task.md`

### Phase 3: Compose — heterogeneous tray + save UI

- [x] `p3-1` UPDATE tray to uid identity with three row kinds (existing · library · blank), duplicate control, and `getItems()` → `phase-3/p3-1.task.md`
- [x] `p3-2` UPDATE builder so library browse adds to the deck tray and an "Add blank slide" button appends blanks → `phase-3/p3-2.task.md`
- [x] `p3-3` CREATE the Save deck UI — new-file vs overwrite chooser on every save, wired to `/api/deck-save` → `phase-3/p3-3.task.md`
- [ ] `p3-checkpoint` **CHECKPOINT** — full restructure loop: open → reorder/remove/duplicate/add → save → reopen intact → `phase-3/p3-checkpoint.task.md`

### Phase 4: Bridge — cross to the editor

- [ ] `p4-1` UPDATE both pages with save-and-switch controls ("Switch to editor" / "Open in builder"), Save-As gated → `phase-4/p4-1.task.md`
- [ ] `p4-checkpoint` **CHECKPOINT** — round trip builder↔editor without losing work → `phase-4/p4-checkpoint.task.md`

### Phase 5: Validation and Completion

- [ ] `p5-refs` Verify all internal links resolve and comply with the Plan Linking Standard (internal = file-relative, external = project-root-relative)
- [ ] `p5-compound` Process learnings.md entries into system improvements → `phase-5/p5-compound.task.md`
- [ ] `p5-checkpoint` **FINAL CHECKPOINT** — v1 success criteria exercised end-to-end; user approval to complete plan (HARD HALT) → `phase-5/p5-checkpoint.task.md`
