You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context. This task operates in the SEPARATE tecer-biz git repository at `5-workbench/tecer-biz/`.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any step, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate by exact strings, NEVER line numbers.

# PB-T16 — tecer-biz: migration branch + commit clean pre-state

## Objective
Create the dedicated migration branch in the tecer-biz repo and COMMIT the current clean state BEFORE any conversion (U2-S4 "commit BEFORE conversion") — this is the rollback point. NO library files change in this task.

## FILE ALLOWLIST
- No source-file writes. Git operations only, in `5-workbench/tecer-biz/`.
- ✚ create `5-workbench/tecer-biz/slide-library/docs/migration-precommit.md` (a one-paragraph note recording the pre-state) — this is the only file you create, and it rides the pre-commit.

## Context (facts)
- tecer-biz is its own git repo (separate from the rbtv repo and the vault). It is on branch `main`, clean (per the session pre-flight). Repo conventions (tecer-biz CLAUDE.md): `git mv`/`git rm` for moves; Conventional Commits `type(scope): description`.
- The migration converts the live `slide-library/` IN PLACE on a branch; the live library must keep producing decks (no broken weeks) — hence the pre-conversion commit as the rollback point.

## Steps
1. Confirm the repo is clean: `git -C 5-workbench/tecer-biz status --porcelain` → empty (if not, STOP, write BLOCKED with the dirty list — do not proceed; foreign changes must be resolved by the orchestrator).
2. Create + checkout the branch: `git -C 5-workbench/tecer-biz checkout -b slide-library-convention-migration`.
3. Create `slide-library/docs/migration-precommit.md` with: the date, the current `git rev-parse HEAD` of `main`, and one line: "Pre-conversion snapshot — rollback point for the slide-library convention migration (U2-S4). Conversion lands in the next commits on this branch."
4. Commit it: `git -C 5-workbench/tecer-biz add slide-library/docs/migration-precommit.md` then `git -C 5-workbench/tecer-biz commit -m "chore(slide-library): pre-conversion snapshot before convention migration"`. (Do NOT push.)

## Acceptance criteria
1. `git -C 5-workbench/tecer-biz rev-parse --abbrev-ref HEAD` == `slide-library-convention-migration`.
2. `git -C 5-workbench/tecer-biz log -1 --pretty=%s` == `chore(slide-library): pre-conversion snapshot before convention migration`.
3. `git -C 5-workbench/tecer-biz status --porcelain` is empty (clean after the commit).

## Evidence file
Write to `5-workbench/tecer-biz/slide-library/docs/migration-validation.md` (create it; later tasks append) a `## PB-T16` section: the branch name, the recorded `main` HEAD hash, the new commit hash.

DONE means: branch created, pre-state committed (rollback point exists), evidence written. If the repo was not clean → BLOCKED + stop.
