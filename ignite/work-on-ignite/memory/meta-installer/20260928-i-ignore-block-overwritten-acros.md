# 20260928-i-ignore-block-overwritten-acros — ignore block overwritten across machines; strays unlisted

kind: issue
component: meta-installer
date: 2026-09-28
commit: 93b3a2ba
deployed: no
pin: NONE

## Observed
On the Windows desktop vault (2026-09-27), installer loaders kept surfacing as untracked files for commit although D14's fenced `rbtv2` block is meant to keep every installer artifact out of git: `.claude/skills/audio-io/SKILL.md` and `.claude/skills/generate-image/SKILL.md` (booked on the desktop), plus `cli-creator` and `ponytail-debt` (on disk, marked, not booked). The committed `.gitignore` block held 123 entries while the desktop's book planned 61. Separately, 13 marked loaders were tracked in git from before the block existed.

## Mechanism
Two causes. (1) The block lived in the COMMITTED `.gitignore`, but its content is machine-local: each machine's installer rewrote it from ITS book. The VPS and the desktop share the vault repo, so whichever machine committed last won. `git log -S` shows the desktop's install added `audio-io` on 2026-09-22 (46f3efcb3) and a VPS commit dropped it on 2026-09-26 (62d298495), replacing the list with the VPS's install set (`team-kit`, `meeting-summarizer`, ...). (2) The block was computed from the book only, so a marked artifact whose book entry was lost (an earlier run's output) stayed on disk and was never listed.

## Attempts
First attempt held — checked: meta-installer `_issues.md`/`_creations.md` (20260824-i-path-links-unusable-on-windows, 20260901-i-exposure-canon-two-tool-rows-f, 20260822-c-installer-home-in-meta, 20260823-c-installer-split-into-lib-selft) and D14 in design-decisions.md; no earlier fix of this problem. A first draft of this fix added only the stray scan; tracing the two missing loaders showed they were booked, which exposed the cross-machine overwrite, so the per-clone move was added before committing.

## Fix
The block is now a D7/D12 claim on `.git/info/exclude` (`EXCLUDE_REL`), git's own per-clone ignore file: read like `.gitignore`, never committed, so each machine keeps its own list. Chosen over merging a shared list (rejected: entries for removed loaders would accumulate forever and the shared file would still churn on every install on either machine). An older run's `.gitignore` claim is an ordinary stale claim, released on the next run with the foreign lines kept. `_stray_artifacts` globs every MATRIX destination template for files carrying `MANAGED_MARK` that the book does not list and adds them (a skill as its folder, D15); booked files stay the book's business so a harness narrowing still shrinks the block. A `.git` FILE (linked worktree, submodule) is not claimed.

## Consequences
The shared `.gitignore` no longer changes on install. A machine still running the old installer keeps its block in `.gitignore` until it re-runs the updated installer, which releases it; until then that block sits in the shared file and the new installer leaves it alone (not ours on the other clone). Vault side (owner ruling 2a): the 13 tracked loaders were untracked (vault 5d6a765a1); a clone pulling that deletes its tracked copies until its next install regenerates them. `_add_gitignore` now takes the booked file set; its three callers (do_install, do_uninstall, doctor) pass `known_files(state)`.

## Verification
`install.py selftest`: G1-G7 re-pointed at `.git/info/exclude` pass; new G8 (stray marked skill folder and rule listed, unmarked user skill not, idempotent re-run, `.gitignore` never written) and G9 (old `.gitignore` block released, foreign lines kept) pass. The same 4 unrelated failures and the later WinError 1314 symlink stop occur on HEAD before the change (compared in a scratch worktree). On the desktop vault, `install.py add -c <audio-io>,<generate-image>` wrote a 74-entry block to `.git/info/exclude` and `git check-ignore` confirms all four loaders ignored. Committed 93b3a2ba, merged 613a02a4; not deployed (installer runs in place).

## ATTENTION
- The ignore block is per clone now: NEVER look for it in `.gitignore`, and never re-add an `rbtv2` block there — the shared file is exactly what made machines overwrite each other.
- `add -c` with list NUMBERS is only safe right after `ls`: a pull that changes the catalogue shifts the numbers (24→22 observed), and `index-stale` refuses; selecting by component NAME pulls in every part of the component and can collide with foreign skills.
- A clone that pulls a commit untracking loaders LOSES those files on disk until its next install run regenerates them.
- block is in .git/info/exclude per clone; never re-add rbtv2 block to .gitignore
