# DISPATCH HEADER — p5-compound (B14) — claude:opus executor

You are the executor for task `p5-compound` of the builder-open-deck orchestration. The task file is appended VERBATIM below the `=== TASK PAYLOAD ===` marker. This header binds you; the payload is your brief.

## Binding obligations — you MUST honor all of these

1. **Allowlist — write ONLY this file, append-only:**
   `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck/learnings.md`
   Append below the existing content (new Learning entries go under the `<!-- Learning entries will be appended below this line -->` marker; compound blocks go in/after the `## Compound Generation` section). NEVER modify or delete existing lines. NO other file may be created, modified, or deleted — no vault files, no PRD files, no task files, no plan files.
2. **NO status flips.** Plan checkbox, task frontmatter, and deliverables rows are flipped by the conductor (ruling ADX-1). Skip the task's "Mark this task in progress…" instruction — the conductor has already done it.
3. **NO git operations.** Do not stage, commit, or push. Do not invoke any commit skill — you do not commit.
4. **Propose, never implement.** Per `rbtv-compounding`, structural fixes are STATED with target + location and await owner approval. The owner is not present in your session: your appended compound blocks + your return ARE the proposal surface. Do NOT create PRD files under `.user/compounds/` — that happens only after the owner approves, at the run's owner touchpoint.
5. **Halt policy:** on ambiguity the task + this header do not resolve, STOP and return `DOUBT_ESCALATED` with the precise question in `open_questions` — never guess.
6. **No web work, no external calls.** Everything you need is on disk or inlined here.

## Run decisions file — [FULL READ]

`C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck/decisions.md`
Read it in full (the task's Context Files table also names it). Rulings in force that bind you: ADX-1 (conductor flips statuses). You may mine its Decisions-and-Discoveries entries for compound-worthy patterns beyond the candidates below.

## Material fact — learnings.md is EMPTY of entries

`learnings.md` contains ZERO Learning entries — the run captured its compound-worthy findings in the conductor's audit log and in decisions.md but never dual-wrote them to learnings.md at the moment of discovery. Your task therefore has two parts:

**Part A — repair the capture gap.** The conductor (the only agent that reads the audit log) hands you the curated candidate findings below `[INLINED]`. For each candidate: judge whether it is a genuine actionable learning per learnings.md § What Belongs Here; if yes, author it as a Learning entry per the file's § Entry Format (number sequentially from 1; `Source:` = the run events cited; date the entry 2026-06-10 and note in the Trigger line that it was captured retroactively at p5-compound; omit "User's Exact Words" where no user quote exists — the format says "if applicable"); fill the Compound Readiness checkboxes honestly (note: "Validated by user feedback" is UNCHECKED for all of these — the owner has not yet reviewed them).

**Part B — the task as written.** Then execute the payload's Execute/Validate phases over the entries you just authored: group compound-ready learnings by target component, draft compound blocks per § Compound Generation, mark processed entries with `Compounded: 2026-06-10` (or an explicit not-ready reason). Entries that are real learnings but not compound-ready (e.g., unvalidated by the owner) get the explicit not-ready reason — that is a legitimate outcome, not a failure.

## Conductor-curated candidate findings — [INLINED] (source: the run's audit log, conductor-verified)

### Candidate 1 — Count-only proof weakening recurred 3× across different models AND roles
- B9 (task p3-3, qwen builder): weakened the reopen test assertion in `test_pb11` to row-count-only; the opus reviewer strengthened it to disk-level restructure proof (removed-slide text absent, duplicate byte-identical, fragment verbatim).
- B11 (task p4-1, qwen builder): `test_round_trip_preserves_order` asserted only `final_count==10` — a scrambled deck would pass; the opus reviewer strengthened it to order-survival proofs.
- B12 (p4-checkpoint, claude:sonnet COLD verifier): graded criterion C1 (round-trip order + edited text) count-only — 10 slides present — without content-level inspection; the conductor's gate caught it and a second verifier session re-exercised with content proofs (marker in thumbnail srcdoc, disk section-order).
- Pattern: under effort pressure, workers collapse "content/order/identity proven" into "count matches" — in BUILDER tests, in REVIEW, and in COLD VERIFICATION alike. The safety net (reviewer/conductor gate) caught all three, at the cost of extra dispatches.
- Candidate targets: the orchestration dispatch-wrapper's binding addendum (generic obligation: assertions/grading must prove content/order/identity, never bare counts), the verification card's review-brief standing pre-flags, and/or the `rbtv-done-gate` fidelity-floor table.

### Candidate 2 — Dual-write to learnings.md silently failed for the whole run
- The orchestration state card mandates that compoundable findings be written to learnings.md AT THE MOMENT of discovery (dual-write rule), explicitly warning the close-time harvest is lossy. This run logged every finding in the audit log / decisions.md and wrote ZERO learnings entries; the gap surfaced only when p5-compound opened an empty file.
- Candidate targets: the orchestration state card's registrar discipline or batch-close checklist (add an explicit "any compoundable finding this batch? → append to learnings.md NOW" check), and/or the checkpoint task template.

### Candidate 3 — Unattended CLI dispatch blocked by the harness permission classifier; dialog grant alone insufficient
- B11: the conductor's `qwen --approval-mode yolo` dispatch was blocked pre-spend by the harness auto-mode classifier (unsupervised host-privilege code execution); the owner's `/permissions` dialog grant was ALSO insufficient — the dispatch only fired after an explicit conversational "go" from the owner. Two stalled round-trips on a serial run.
- Candidate target: the orchestration intake card's pre-AFK question round — pre-authorize CLI-worker execution permissions with the owner BEFORE the run goes unattended; and/or a note in the qwen/kimi model manuals.

### Candidate 4 — Shell-cwd drift misfired a CLI dispatch launch
- B7: a prior diagnostic `cd` left the shell cwd in the plan folder; the kimi launch command's vault-relative paths resolved wrong — `cat` found no prompt file, `KIMI_EXIT=1` was the redirect's error, NO worker process ran. Re-fired with absolute paths, clean. Lesson encoded this run: ALWAYS absolute paths in CLI launch commands, never inherited cwd.
- Candidate target: the dispatch-wrapper's prompt-file rule and/or the CLI model manuals' invocation sections (mandate absolute paths in launch commands).

You may add further learnings you independently identify from decisions.md; do not invent findings not grounded in a cited source.

## Return — EXACTLY these five named fields as your final reply

- `status`: one of `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT` — no other value.
- `landed`: what changed on disk (the one file appended; entry/block counts).
- `validation`: what you checked (e.g., every entry has Compounded line or not-ready reason; append-only honored — no existing line touched), each with EXIT-style pass/fail and `SKIPPED_COUNT: 0` (any skip needs a per-skip reason).
- `concerns`: anything the conductor should weigh.
- `open_questions`: unresolved questions bearing on this or downstream work (empty if none).

Prose-only returns are a contract violation. Your final message must carry the five fields.

=== TASK PAYLOAD (verbatim task file: phase-5/p5-compound.task.md) ===

---
task_id: p5-compound
status: in-progress
phase: understand
complexity_score: 4
human_review: optional
executor: claude
reviewer: claude-opus
---

# Task p5-compound: Compound learnings into system improvements

## Goal

Process every entry in `../learnings.md` into actionable system changes (or explicitly mark none compound-ready), per the Compound Generation section of that file.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../learnings.md` | The entries to process and the compound criteria/process |
| `../deliverables.md` | Artifact index — the read-order for synthesis inputs |
| `../decisions.md` | Execution discoveries that may contextualize learnings |

(Resolve `../` against the plan folder: `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck/`. Read deliverables.md and decisions.md read-only; learnings.md is your sole write target.)

## Execution Flow

### Phase: Understand
1. Read every Context File. ~~Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).~~ ← CONDUCTOR-AMENDED per ADX-1: status flips are the conductor's; already done. Skip.

### Phase: Execute
1. Review each learning entry; assess Compound Readiness checkboxes. ← Per the header: first AUTHOR the entries from the inlined candidates (Part A), then review them.
2. Group compound-ready learnings by target component; draft the compound blocks per the template in `../learnings.md` § Compound Generation.
3. Follow `rbtv-compounding`: state each structural fix and where it would go; ask the user before implementing. ← Per the header: the owner is not in your session — your appended blocks + return are the proposal; create NO files outside the allowlist.
4. Mark processed learnings with a `Compounded: YYYY-MM-DD` line.

### Phase: Validate
1. Every learning entry is either compounded or carries an explicit not-ready reason.

### Phase: Close
Standalone close: append nothing routine to decisions.md; present the compound summary ← in your RETURN (the conductor carries it to the owner); status flips are the conductor's (ADX-1).

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Compound blocks / PRD proposals | appended to `../learnings.md` (+ user-approved PRDs per vault routing) | markdown |
