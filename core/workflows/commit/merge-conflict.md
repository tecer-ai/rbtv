---
name: Resolve Merge Conflict
description: How the agent resolves a merge conflict that commit.py reported and refused to commit through.
---

# Resolve Merge Conflict

`commit.py` exited non-zero with `merge conflict pulling remote changes in: <files>` and made NO commit. Follow these steps in order. NEVER skip a step.

## State the script left

- This cluster's changes are STAGED. The working tree is clean — no conflict markers (the script aborted the merge and undid its commit).
- The remote divergence is NOT integrated — local is still behind the remote.
- Any other unrelated changes in the working tree are untouched and still unstaged.

## Procedure

1. STOP. Do NOT retry `commit.py` and do NOT commit anything until the conflict is resolved — retrying only reproduces the same conflict.
2. Capture this cluster as a local commit so the work cannot be lost: `git -C "{repo}" commit -m "<this cluster's confirmed message>"`.
3. Pull to merge the remote: `git -C "{repo}" pull --no-edit`. This re-creates the conflict, now as a real merge with conflict markers in the working tree.
4. List the conflicting files: `git -C "{repo}" diff --name-only --diff-filter=U`.
5. Present EVERY conflicting file to the user. Ask how to resolve each one — NEVER resolve silently or guess.
6. Execute the user's resolution: edit each conflicting file to the agreed content, then `git -C "{repo}" add {file}` for each resolved file.
7. Complete the merge: `git -C "{repo}" commit --no-edit`.
8. If the project has a test command (check `CLAUDE.md` or `package.json`), run it. Fail → STOP and notify the user; do NOT push.
9. Push ONLY if the user requested a push: `git -C "{repo}" push`.

Return to the commit plan and continue with the next cluster only after this one is committed and (if requested) pushed.
