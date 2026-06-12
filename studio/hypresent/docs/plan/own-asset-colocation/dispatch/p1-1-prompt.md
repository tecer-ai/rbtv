---
execution_kind: code
executor: codex
allowed_workdir: 3-resources/tools/rbtv/studio/hypresent
allowlist:
  - server/deck_api.py
  - server/recompose.py
sandbox: workspace-write
commit_policy: none
test_command: pytest tests/test_deck_api.py tests/test_recompose.py -q
forbidden_ops:
  - git push
  - git commit / git add (the conductor commits via rbtv-commit)
  - destructive git reset / amend
  - writes outside the allowlist (the two server files) — see exception for the return/validation evidence files below
  - running stamp.py or editing deliverables.md, the plan checkbox, or decisions.md
  - external production API calls
  - "--dangerously-bypass-approvals-and-sandbox"
doubt_policy: halt
reviewer: claude-opus
---

# Dispatch — Task p1-1: Own-asset colocation + collision-safe rename/rewrite (codex worker)

You are a code-executing worker. Your working directory (`--cd`) is the hypresent app dir
`3-resources/tools/rbtv/studio/hypresent/`. All `server/…`, `tests/…` paths below resolve from there.
`pytest` runs from there.

## Run-binding header

### Worker obligations (BINDING — imperative)

1. **Return-schema compliance.** Your final message MUST be the five-field schema in "Return format" below — every field present, none renamed, none invented. A prose-only return is a contract violation.
2. **Allowlist boundary.** Create / modify ONLY these files: `server/deck_api.py` and `server/recompose.py`. Do NOT touch any other tracked file. (The conductor diffs your changes against this allowlist on return.)
3. **Doubt policy = HALT.** On any ambiguity the task + spec do not resolve, STOP and return `status: DOUBT_ESCALATED` with the precise question in `open_questions`. NEVER guess past a doubt.
4. **Evidence on disk.** Write your validation command output to `docs/plan/own-asset-colocation/dispatch/p1-1-validation.txt` (capture the full `pytest` output there). The `validation` return field cites the commands; this file is the proof.
5. **NO commit.** `commit_policy: none` — do NOT run `git add`, `git commit`, `git push`, or any git write. The conductor commits via `rbtv-commit` after review.
6. **NO state writes.** Do NOT run `stamp.py`, and do NOT edit `deliverables.md`, the plan checkbox, or `decisions.md`. If execution produces a decision/discovery worth recording (e.g. you chose post-recompose surgery over the `existing`-`html` override, or hit a recompose limitation), put it in the `concerns` return field — the CONDUCTOR appends it to `decisions.md`.
7. **Sandbox = workspace-write.** Confined to the work-dir. Temp files for smoke-testing go to an OS temp dir (via `tempfile`), never into the repo.
8. **Allowed evidence-file exception to the allowlist:** you MAY write ONLY to `docs/plan/own-asset-colocation/dispatch/p1-1-validation.txt` (your validation capture) in addition to the two server files. Nothing else.

### decisions.md pointer (READ — do not edit)

Read `docs/plan/own-asset-colocation/decisions.md` before coding — it carries the locked decisions (approach **(a)** replicate referenced own-assets into the destination `assets/`; collision handling **(B)** rename the colliding own-asset + rewrite its ref inside the owning source section) and the constraints (byte-for-byte span preservation relaxed ONLY for colliding own-asset refs inside source sections; non-colliding sections + inter-slide separators MUST stay byte-identical; existing `test_deck_api` / `test_recompose` faithfulness tests must stay green).

### Path-resolution note (the task body below uses plan-folder-relative refs — map them to your cwd)

| Task body ref | Read it at (relative to your `--cd`) |
|---------------|--------------------------------------|
| `../specs/own-asset-colocation-spec.md` | `docs/plan/own-asset-colocation/specs/own-asset-colocation-spec.md` |
| `../decisions.md` | `docs/plan/own-asset-colocation/decisions.md` |
| `server/deck_api.py` | `server/deck_api.py` |
| `server/recompose.py` | `server/recompose.py` |
| `tests/test_deck_api.py`, `tests/test_recompose.py` | same, under `tests/` |

**Ignore the task's "Phase: Close" stamping step** (steps about `--status in_progress`, the `stamp.py` command, "mark complete") — those are the conductor's job per obligation 6 above. Do the Understand / Execute / Validate phases, then return the schema.

The task references `rbtv-coding-discipline` (`.claude/skills/rbtv-coding-discipline/`). Follow disciplined coding practice: minimal diff, reuse the existing asset machinery (`_find_referenced_assets`, skip-if-exists, `shutil.copy2`), no parallel copy path, no speculative options.

### Return format — return EXACTLY these five fields as your final message

- **`status`**: one of `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`.
- **`landed`**: files modified (with one-line summary of the change in each) — NO commit (you do not commit).
- **`validation`**: each command run, its `EXIT` code, its `WALL_MS` (wall-clock ms), and `SKIPPED_COUNT` (0 if none; each skip needs a reason). Cite the evidence file `dispatch/p1-1-validation.txt`.
- **`concerns`**: risks, smells, partial confidence, any decision/discovery for the conductor to log in `decisions.md`, adjacent issues spotted but not fixed.
- **`open_questions`**: unresolved questions bearing on this or downstream work (the doubt, if `DOUBT_ESCALATED`).

---

## Payload — Task p1-1 (verbatim)

# Task p1-1: Implement own-asset colocation + collision-safe rename/rewrite

## Goal

`/api/deck-save` copies the source deck's own referenced `assets/*` into the destination on save-to-a-new-directory, resolving name collisions by renaming the own-asset and rewriting its ref inside the owning preserved source section. Behavior + invariants source of truth: `../specs/own-asset-colocation-spec.md` (all Behavior rows, Invariants, Edge Cases).

**Path anchor:** `server/…` and `tests/…` are relative to the hypresent app dir `3-resources/tools/rbtv/studio/hypresent/`. Run `pytest` from there.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/own-asset-colocation-spec.md` | Behavior rows, Invariants, Edge Cases, recommended mechanism — the contract you build to |
| `server/deck_api.py` | `handle_deck_save` + the existing library copy loop, `_find_referenced_assets`, `_ASSET_RE`, response shape you extend with `assets_renamed` |
| `server/recompose.py` | `recompose`/`split_sections`; the `existing`-item separator logic you must preserve if you add the optional `html` override |
| `../decisions.md` | Locked decisions (approach a + collision B), constraints (byte-for-byte relaxed ONLY on collision) |

## Execution Flow

### Phase: Understand
1. Read every Context File.
2. Confirm the recommended mechanism vs your choice: rewrite colliding refs on each preserved section's ISOLATED HTML before splicing (the spec's `existing`-`html`-override option) — or an equivalent that satisfies the Invariants. Do NOT do a global string replace on the recompose result (it would corrupt library refs).

### Phase: Execute
1. Implement the own-asset copy pass in `handle_deck_save`, reusing `_find_referenced_assets` + the skip-if-exists + `shutil.copy2` pattern. Source root = `Path(source_path).resolve().parent`; destination = `out_dir`.
2. Collision handling (Behavior row 3): on a different-file collision at `out_dir/assets/x.png`, copy the own-asset under a unique `assets/x-{n}.ext` and rewrite that ref ONLY inside the owning preserved source section(s); record `assets_renamed`.
3. Preserve the Invariants: only source sections rewritten; non-colliding sections + separators byte-identical; one source asset → one new name (consistency map); boundary-safe replacement; same-dir save = no-op (same-file check); refuse on a violated 1:1 item→section mapping.
4. Add `assets_renamed: [{from, to}]` to the response when any own-asset is renamed.

### Phase: Validate
1. Run the EXISTING suite — it must stay green (proves the byte-for-byte invariant held): `pytest tests/test_deck_api.py tests/test_recompose.py -q` → expected EXIT 0.
2. Smoke the new behavior on a scratch source deck with an `assets/own.png` ref saved to a temp out_dir; confirm the file lands and the response reports it. (New formal unit tests are p1-2.)

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Own-asset copy + collision rename/rewrite | `server/deck_api.py` (and `server/recompose.py` if override used) | edits |
