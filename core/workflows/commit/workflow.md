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

**Run the script with the working directory INSIDE `{repo}`** — `cd "{repo}"` first (or pass it as the command's cwd). The script locates the repo root from its own cwd; invoking it from the workspace root (or any other repo) makes it operate on the WRONG repo and report `no changes to commit` for paths that plainly changed. The `-f` paths are repo-root-relative, so they only resolve correctly from inside `{repo}`.

Resolve `{rbtv_path}` from `rbtv.json` (at the WORKSPACE root) to an ABSOLUTE path BEFORE invoking — its value is recorded relative to the workspace root, NOT to `{repo}`. The script runs with the working directory INSIDE `{repo}` (which is often a repo nested below the workspace root; the script locates the repo root itself), so a bare relative `{rbtv_path}/core/...` resolves against the repo's cwd and fails. Build the absolute path by joining the workspace root (the directory that contains `rbtv.json`) with `rbtv_path`, then invoke `commit.py` by that absolute path. NEVER build the path relative to the current working directory, and NEVER open `rbtv.json` by a cwd-relative path from inside `{repo}` (it lives at the workspace root, not the repo root). For each confirmed cluster, in plan order:

```
python "{rbtv_path}/core/workflows/commit/commit.py" -m "<message>" -f <path> [-f <path> ...] [--push]
```

(`{rbtv_path}` above is the ABSOLUTE workspace-root-anchored path resolved here. The `-f` paths, by contrast, stay repo-root-relative — the script's cwd is inside `{repo}`.)

- **Message passing — pick by shape:**
  - **Single-line message** → inline `-m "<message>"`.
  - **Multi-line message (body, bullet list, blank lines)** → NEVER inline it. Write the full message to a scratch file with the **Write tool** (e.g. the session scratchpad `commit-msg.txt`), then pass `-F "<abs-path-to-file>"` instead of `-m`. The Write tool stores the text verbatim, so the shell never quotes a multi-line string. **NEVER build a multi-line message with a shell heredoc or here-string** (`<<EOF`, PowerShell `@'...'@`) — the two shells' syntaxes differ and pasting one into the other silently corrupts the message (stray `@`/`EOF` markers land in the commit). `-m` and `-F` are mutually exclusive; give exactly one.
- Pass each path with its own `-f`, repo-root-relative. List every path the cluster touches (including both sides of a rename).
- A `-f` path may be a FILE or a DIRECTORY. A directory includes every changed file beneath it — use it when a cluster touches more files than fit on one command line (a long explicit `-f` list overflows the OS argument limit at a few hundred files). CAUTION: a directory commits whatever currently lives under it, so a parallel session's file dropped there rides along — prefer explicit file paths when the cluster must be exact.
- Add `--push` ONLY if the user asked to push.
- The script unstages everything, stages ONLY the listed files (so a parallel session's staged file is never committed — its changes stay in the working tree), syncs the remote commit-first (a clean auto-merge is silent), commits, and pushes when `--push` is given.
- On exit 0 the script prints `committed <hash>`, then `files in commit (<n>): …` read back from the commit OBJECT, and a `synced remote: merge commit …` line if a sync merge was created. The staging gate guarantees the committed files equal exactly the files you listed — it aborts otherwise. TRUST this output: do NOT run `git show`, `git log`, or any other command to re-verify the commit's contents. The script IS the verification.

### 3. On a non-zero exit — the script made NO commit

Read the script's error and act:

| Error | Meaning | Action |
|-------|---------|--------|
| `no changes to commit: <paths>` | A listed file/directory had no changes | Fix the path list, retry the script for that cluster |
| `merge conflict pulling remote changes in: <files>` | The remote diverged and conflicts with this cluster | Read and follow `{rbtv_path}/core/workflows/commit/merge-conflict.md` |

NEVER move to the next cluster until the current one has committed.

## Commit Message Style

- Follow conventional commits
- Summarize the "why", not the "what" — the diff shows the what
- Keep first line under 72 characters
- NEVER add a `Co-Authored-By` trailer, a `Generated with Claude Code` line, or any other AI-attribution line to the commit message or its trailer
