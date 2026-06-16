---
name: Git Commit
description: Commit local changes with correct file-op hygiene, remote sync, and conflict handling.
---

# Git Commit

The agent supplies the judgment — which files belong together, what each message says — and the deterministic script `commit.py` owns every git mechanic in ONE invocation per commit: remote sync, the staging gate, the commit, and the optional push. The agent NEVER runs the stage / sync / commit git commands by hand.

## When to Use

| Signal | Example |
|--------|---------|
| User requests a commit | "commit", "commita", "salva no git" |
| Task completed and user asks to persist | "done, commit this" |

## Procedure

### 1. Analyze and plan (agent judgment)

1. `git -C "{repo}" status` — see which files changed (modified, new, deleted). Staged-vs-unstaged does not matter here: the script re-stages from scratch.
2. `git -C "{repo}" diff` — review the changes
3. Cluster the changes by concern — files serving the same feature, fix, or content batch form one cluster:
   - One commit per cluster. Default is a single commit — split ONLY when clusters are genuinely unrelated.
   - Relatedness decides, never size: a large related batch is ONE commit; two unrelated files are TWO commits.
   - NEVER bundle unrelated clusters into one umbrella commit.
4. File-op hygiene: for a move or rename, run `git -C "{repo}" mv {old} {new}` FIRST, then pass BOTH `{old}` and `{new}` as files for that cluster. A deletion needs only the deleted path passed.
5. Draft one commit message per cluster (see Commit Message Style). Present the full plan — clusters, files, messages — in a SINGLE confirmation. Wait for user confirmation before proceeding.

### 2. Commit each cluster via the script

Resolve `{rbtv_path}` from `rbtv.json` at the workspace root. For each confirmed cluster, in plan order, run the script with the working directory INSIDE `{repo}` (the script locates the repo root itself):

```
python "{rbtv_path}/core/workflows/commit/commit.py" -m "<message>" -f <file> [-f <file> ...] [--push]
```

- Pass each file with its own `-f`, repo-root-relative. List every path the cluster touches (including both sides of a rename).
- Add `--push` ONLY if the user asked to push.
- The script unstages everything, stages ONLY the listed files (so a parallel session's staged file is never committed — its changes stay in the working tree), syncs the remote commit-first (a clean auto-merge is silent), commits, and pushes when `--push` is given.
- On exit 0 the script prints `committed <hash>`, then `files in commit (<n>): …` read back from the commit OBJECT, and a `synced remote: merge commit …` line if a sync merge was created. The staging gate guarantees the committed files equal exactly the files you listed — it aborts otherwise. TRUST this output: do NOT run `git show`, `git log`, or any other command to re-verify the commit's contents. The script IS the verification.

### 3. On a non-zero exit — the script made NO commit

Read the script's error and act:

| Error | Meaning | Action |
|-------|---------|--------|
| `no changes to commit: <files>` | A listed file was unchanged | Fix the file list, retry the script for that cluster |
| `merge conflict pulling remote changes in: <files>` | The remote diverged and conflicts with this cluster | Read and follow `{rbtv_path}/core/workflows/commit/merge-conflict.md` |

NEVER move to the next cluster until the current one has committed.

## Commit Message Style

- Follow conventional commits
- Summarize the "why", not the "what" — the diff shows the what
- Keep first line under 72 characters
- NEVER add a `Co-Authored-By` trailer, a `Generated with Claude Code` line, or any other AI-attribution line to the commit message or its trailer
