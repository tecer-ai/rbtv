---
description: 'Use when committing changes to git. Triggers: user says "commit", "salva no git", "commita", or a task finishes and changes must be persisted. Handles file-op hygiene (git mv/git rm), remote sync, conflict detection, and commit message generation from diff analysis.'
tags: [coding]
---

# commit — deterministic git commit

The agent supplies the judgment — which files belong together, what each message says — and the
deterministic script `commit.py` (beside this file, at `3-resources/tools/rbtv/core/coding/tool/commit.py`)
owns every git mechanic in ONE invocation per commit: remote sync, the staging gate, the commit,
and the optional push. The agent NEVER runs the stage / sync / commit git commands by hand.

## When to use

| Signal | Example |
|--------|---------|
| User requests a commit | "commit", "commita", "salva no git" |
| Task completed and user asks to persist | "done, commit this" |

## Procedure

### 1. Analyze and plan (agent judgment)

1. `git -C "{repo}" status` — see which files changed (modified, new, deleted). Staged-vs-unstaged
   does not matter here: the script re-stages from scratch.
2. `git -C "{repo}" diff` — review the changes
3. Cluster the changes by concern — files serving the same feature, fix, or content batch form one
   cluster:
   - One commit per cluster. Default is a single commit — split ONLY when clusters are genuinely
     unrelated.
   - Relatedness decides, never size: a large related batch is ONE commit; two unrelated files are
     TWO commits.
   - NEVER bundle unrelated clusters into one umbrella commit.
4. File-op hygiene: for a move or rename, run `git -C "{repo}" mv {old} {new}` FIRST, then pass
   BOTH `{old}` and `{new}` as files for that cluster. A deletion needs only the deleted path
   passed.
5. Draft one commit message per cluster (see Commit Message Style). Present the full plan —
   clusters, files, messages — in a SINGLE confirmation. Wait for user confirmation before
   proceeding.

### 2. Commit each cluster via the script

**Run the script with the working directory INSIDE `{repo}`** — `cd "{repo}"` first (or pass it as
the command's cwd). The script locates the repo root from its own cwd; invoking it from the
workspace root (or any other repo) makes it operate on the WRONG repo and report
`no changes to commit` for paths that plainly changed. The `-f` paths are repo-root-relative, so
they only resolve correctly from inside `{repo}`.

Invoke the script by ABSOLUTE path, built from the WORKSPACE root (the directory containing
`.rbtv/`): `<workspace-root>/3-resources/tools/rbtv/core/coding/tool/commit.py`. The script runs with the
working directory inside `{repo}` — often a repo nested below the workspace root — so a bare
relative `.rbtv/mirror/...` resolves against the repo's cwd and fails. For each confirmed cluster,
in plan order:

```
python "<workspace-root>/3-resources/tools/rbtv/core/coding/tool/commit.py" -m "<message>" -f <path> [-f <path> ...] [--push]
```

(The `-f` paths, by contrast, stay repo-root-relative — the script's cwd is inside `{repo}`.)

- **Message passing — pick by shape:**
  - **Single-line message** → inline `-m "<message>"`.
  - **Multi-line message (body, bullet list, blank lines)** → NEVER inline it. Write the full
    message to a scratch file with the **Write tool** (e.g. the session scratchpad
    `commit-msg.txt`), then pass `-F "<abs-path-to-file>"` instead of `-m`. The Write tool stores
    the text verbatim, so the shell never quotes a multi-line string. **NEVER build a multi-line
    message with a shell heredoc or here-string** (`<<EOF`, PowerShell `@'...'@`) — the two shells'
    syntaxes differ and pasting one into the other silently corrupts the message (stray `@`/`EOF`
    markers land in the commit). `-m` and `-F` are mutually exclusive; give exactly one.
- Pass each path with its own `-f`, repo-root-relative. List every path the cluster touches
  (including both sides of a rename).
- A `-f` path may be a FILE or a DIRECTORY. A directory includes every changed file beneath it —
  use it when a cluster touches more files than fit on one command line (a long explicit `-f` list
  overflows the OS argument limit at a few hundred files). CAUTION: a directory commits whatever
  currently lives under it, so a parallel session's file dropped there rides along — prefer
  explicit file paths when the cluster must be exact.
- Add `--push` ONLY if the user asked to push.
- The script unstages everything, stages ONLY the listed files, then commits with the listed paths
  as a pathspec (`git commit -- <paths>`) — so a parallel session's staged file is never
  committed, not even one staged *during* the run, and its changes stay in the working tree. It
  syncs the remote commit-first (a clean auto-merge is silent), commits, and pushes when `--push`
  is given.
- On exit 0 the script prints `committed <hash>`, then `files in commit (<n>): …` read back from
  the commit OBJECT, and a `synced remote: merge commit …` line if a sync merge was created. The
  commit pathspec guarantees the committed files fall exactly under the paths you listed (a listed
  DIRECTORY still sweeps everything changed beneath it — see the CAUTION above); a listed path with
  no changes aborts the run. TRUST this output: do NOT run `git show`, `git log`, or any other
  command to re-verify the commit's contents. The script IS the verification.

### 3. On a non-zero exit — the script made NO commit

Read the script's error and act:

| Error | Meaning | Action |
|-------|---------|--------|
| `no changes to commit: <paths>` | A listed file/directory had no changes | Fix the path list, retry the script for that cluster |
| `merge conflict pulling remote changes in: <files>` | The remote diverged and conflicts with this cluster | Follow **Resolving a merge conflict** below |
| `could not pull remote changes — NOT a merge conflict` | The remote sync failed for a NON-conflict reason; git's own error follows the message | Read that error and fix its cause — a stale `.git/index.lock` (verify NO git process is running, then remove it), a network/auth failure, a refused fast-forward. Then retry the script for that cluster. There is no conflict to resolve. |

NEVER move to the next cluster until the current one has committed.

## Resolving a merge conflict

`commit.py` exited non-zero with `merge conflict pulling remote changes in: <files>` and made NO
commit. Follow these steps in order. NEVER skip a step.

**State the script left:**

- This cluster's changes are STAGED. The working tree is clean — no conflict markers (the script
  aborted the merge and undid its commit).
- The remote divergence is NOT integrated — local is still behind the remote.
- Any other unrelated changes in the working tree are untouched and still unstaged.

**Procedure:**

1. STOP. Do NOT retry `commit.py` and do NOT commit anything until the conflict is resolved —
   retrying only reproduces the same conflict.
2. Capture this cluster as a local commit so the work cannot be lost:
   `git -C "{repo}" commit -m "<this cluster's confirmed message>"`.
3. Pull to merge the remote: `git -C "{repo}" pull --no-edit`. This re-creates the conflict, now as
   a real merge with conflict markers in the working tree.
4. List the conflicting files: `git -C "{repo}" diff --name-only --diff-filter=U`.
5. Present EVERY conflicting file to the user. Ask how to resolve each one — NEVER resolve silently
   or guess.
6. Execute the user's resolution: edit each conflicting file to the agreed content, then
   `git -C "{repo}" add {file}` for each resolved file.
7. Complete the merge: `git -C "{repo}" commit --no-edit`.
8. If the project has a test command (check `CLAUDE.md` or `package.json`), run it. Fail → STOP and
   notify the user; do NOT push.
9. Push ONLY if the user requested a push: `git -C "{repo}" push`.

Return to the commit plan and continue with the next cluster only after this one is committed and
(if requested) pushed.

## Commit Message Style

- Follow conventional commits
- Summarize the "why", not the "what" — the diff shows the what
- Keep first line under 72 characters
- NEVER add a `Co-Authored-By` trailer, a `Generated with Claude Code` line, or any other
  AI-attribution line to the commit message or its trailer
