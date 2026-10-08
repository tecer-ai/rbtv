---
name: commit
description: "Use when committing changes to git. Triggers: user says \"commit\", \"salva no git\", \"commita\", or a task finishes and changes must be persisted. Handles file-op hygiene (git mv/git rm), remote sync, conflict detection, and commit message generation from diff analysis."
---

# commit — deterministic git commit

The agent supplies the judgment — which files belong together, what each message says — and the
deterministic command `rbtv-commit` ([commit.py](../capabilities/tools/rbtv-commit/commit.py) in this component) owns every git mechanic in
ONE invocation per commit: remote sync, staging the listed paths, the commit,
and the optional push. The agent NEVER runs the stage / sync / commit git commands by hand.

## When to use

| Signal | Example |
|--------|---------|
| User requests a commit | "commit", "commita", "salva no git" |
| Task completed and user asks to persist | "done, commit this" |

## Procedure

### 1. Analyze and plan (agent judgment)

1. `git -C "{repo}" status` — see which files changed (modified, new, deleted). The script stages
   the listed paths from the working tree itself. Entries staged outside your clusters belong to
   parallel sessions: NEVER unstage them.
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

Invoke the installed `rbtv-commit` command from inside `{repo}`. For each confirmed cluster,
in plan order:

```
rbtv-commit -m "<message>" -f <path> [-f <path> ...] [--push]
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
- A `-f` path is a NAME, never a pattern: `*`, `?`, `[`, `]` and a leading `:` in it are ordinary
  characters, so `-f 'f[1].md'` commits that one file and never `f1.md`. Quote such a path for the
  shell; add no escaping for git.
- A `-f` path may be a FILE or a DIRECTORY. A directory includes every changed file beneath it —
  use it when a cluster touches more files than fit on one command line (a long explicit `-f` list
  overflows the OS argument limit at a few hundred files). CAUTION: a directory commits whatever
  currently lives under it, so a parallel session's file dropped there rides along — prefer
  explicit file paths when the cluster must be exact.
- Add `--push` ONLY if the user asked to push.
- The script stages ONLY the listed paths and commits from a temporary index that holds nothing
  else — so an entry a parallel session staged is never committed, not even one staged *during*
  the run, and it stays staged exactly as that session left it. An executable bit staged on a
  listed path with `git update-index --chmod=+x` is committed. The script syncs the remote
  commit-first (a clean auto-merge is silent), commits, and pushes when `--push` is given. Its pull
  is always a merge, also where the repository sets `pull.rebase`.
- A commit a parallel session makes during the run is never reverted: the script's commit lands on
  top of it and differs from it by the listed paths alone. The repository's `pre-commit`,
  `commit-msg` and `post-commit` hooks run, with the outcomes `git commit` gives them: a failing
  `pre-commit` or `commit-msg`, or a message `commit-msg` leaves empty, refuses the commit; a
  failing `post-commit` is a `WARNING` and the commit stands. `prepare-commit-msg` does not run.
- A merge, rebase, cherry-pick or revert already in progress in `{repo}` is never aborted, finished
  or changed by the script. It still commits the listed paths, then prints
  `WARNING: a <operation> is in progress in this working tree … Commit <hash> was made`. When that
  warning adds `The remote is ahead and was NOT pulled`, the cluster is committed and the remote is
  not merged: run `git -C "{repo}" pull --no-edit --no-rebase` once the operation is finished.
- On exit 0 the script prints `committed <hash>` (only while the branch holds that commit), then `files in commit (<n>): …` read back from
  the commit OBJECT, and a `synced remote: merge commit …` line if a sync merge was created. The
  temporary index guarantees the committed files fall exactly under the paths you listed (a listed
  DIRECTORY still sweeps everything changed beneath it — see the CAUTION above); a listed path with
  no changes aborts the run. TRUST this output: do NOT run `git show`, `git log`, or any other
  command to re-verify the commit's contents. The script IS the verification.

### 3. On a non-zero exit — no commit, unless the error says one was made

The script made NO commit, with one exception: an error that says `Commit <hash> was made` (see
the last three rows). Read the script's error and act:

| Error | Meaning | Action |
|-------|---------|--------|
| `no changes to commit: <paths>` | A listed file/directory had no changes | Fix the path list, retry the script for that cluster |
| `merge conflict pulling remote changes in: <files>` | The remote diverged and conflicts with this cluster | Follow **Resolving a merge conflict** below |
| `could not pull remote changes. NOT a merge conflict` | The remote sync failed for a NON-conflict reason; git's own error follows the message | Read that error and fix its cause — a stale `.git/index.lock` (verify NO git process is running, then remove it), a network/auth failure, a refused fast-forward. Then retry the script for that cluster. There is no conflict to resolve. When the message lists entries other sessions have staged, git refused the merge because of them: leave them staged and retry once those sessions have committed them. |
| `could not pull remote changes: the working tree already held unresolved conflicts before the pull, in: <files>` | The listed files were in conflict before the script ran, with no merge, rebase, cherry-pick, revert or patch application in progress (for example after `git stash pop`), and git refuses to pull over them. Nothing conflicts with the remote. The script made no commit and left those conflicts as they were; this cluster's changes are staged | NEVER enter **Resolving a merge conflict**: there is no merge. The conflicts belong to whoever ran the command that left them: tell the user. Retry the script once they are resolved with git itself |
| `another session committed these requested paths during this run: <paths>` | A parallel session committed a change to a listed path while the script ran. The script made no commit, so that change is not overwritten; this cluster's changes are still staged | Read `git -C "{repo}" diff --cached -- <paths>`, which now shows this cluster's change against the other session's commit. When it is what the cluster intends, retry the script; when it would undo the other session's change, tell the user before retrying |
| `the commit-msg hook left the commit message empty` | The repository's `commit-msg` hook emptied the message, so the commit was refused; this cluster's changes are staged | Tell the user: the hook rejects this message. Retry the script with a message the hook accepts |
| `a <operation> is in progress in this working tree and left these requested paths in conflict: <paths>` | A listed path is one that an unfinished merge, rebase, cherry-pick, revert or patch application (`git am`) left in conflict. The script made no commit and staged nothing | NEVER commit those paths with the script: they are finished with git itself, by whoever started the operation (for a merge this skill left open: **Resolving a merge conflict**, steps 5 to 7). Retry the script without them |
| `these requested paths are in conflict, with no merge, rebase, cherry-pick, revert or patch application in progress: <paths>` | A listed path is one git records as in conflict, and no operation is in progress (for example after `git stash pop`). The script made no commit and staged nothing: staging the path would tell git the conflict is resolved, with whatever the file holds | NEVER resolve silently or guess: present each path to the user and ask how to resolve it. Edit it to the agreed content, `git -C "{repo}" add <path>`, then retry the script |
| `a <operation> is in progress in this working tree … Commit <hash> was made. The remote is ahead and was NOT pulled … Nothing was pushed` | `--push` was given, the commit was made, and the script could not pull because of the unfinished operation, so it pushed nothing | The cluster IS committed: NEVER rerun the script for it. Once the operation is finished, `git -C "{repo}" pull --no-edit --no-rebase`, then `git -C "{repo}" push` |
| `Commit <hash> was made, but another session moved the branch to <tip>, which does not contain it`, with no pull error | The commit was made and the remote sync did not fail, but a parallel session then moved the branch off the commit. Nothing was pushed | The cluster is NOT on the branch: NEVER rerun the script for it. Tell the user before running the `git cherry-pick <hash>` the error names |
| any pull error above, carrying `Commit <hash> was made` in place of `No commit made` | The pull failed AND another session moved the branch after this cluster's commit, so the script undid nothing — its undo removes its own commit and nothing else. The sentence says where the commit is: still on the branch under the other session's commit, still the branch tip (the undo itself failed), or off the branch | The cluster IS committed: NEVER rerun the script for it. Fix the cause the error names, then `git -C "{repo}" pull --no-edit --no-rebase`; on a conflict, enter **Resolving a merge conflict** at step 3. When the sentence says the branch no longer contains the commit, tell the user before running the `git cherry-pick <hash>` it names. |

NEVER move to the next cluster until the current one has committed.

## Resolving a merge conflict

`commit.py` exited non-zero with `merge conflict pulling remote changes in: <files>` and
`No commit made`. Follow these steps in order. NEVER skip a step.

**State the script left:**

- This cluster's changes are STAGED. The working tree is clean — no conflict markers (the script
  aborted the merge and undid its commit).
- The remote divergence is NOT integrated — local is still behind the remote.
- Any other unrelated changes in the working tree are untouched, and an entry a parallel session
  staged is still staged.

**Procedure:**

1. STOP. Do NOT retry `commit.py` and do NOT commit anything until the conflict is resolved —
   retrying only reproduces the same conflict.
2. Capture this cluster as a local commit so the work cannot be lost:
   `git -C "{repo}" commit -m "<this cluster's confirmed message>" -- <this cluster's paths>`.
   The paths bound the commit to this cluster; without them it carries every staged entry,
   including a parallel session's. This form drops an executable bit staged with
   `git update-index --chmod=+x`: stage it again and commit it after step 7.
3. Pull to merge the remote: `git -C "{repo}" pull --no-edit --no-rebase`. This re-creates the
   conflict, now as a real merge with conflict markers in the working tree. While this merge is
   open, a parallel session's `rbtv-commit` run leaves it exactly as it is.
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
