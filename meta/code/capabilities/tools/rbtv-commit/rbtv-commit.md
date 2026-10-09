# rbtv-commit

`rbtv-commit` makes one git commit of a chosen set of paths in one invocation: it syncs the remote, stages the listed paths, commits, and pushes when asked. The agent supplies the judgment: which files belong together and what each message says. The tool owns every git mechanic. The agent never runs the git commands that stage, sync or commit by hand, except the ones this page names. `rbtv-commit -h` is the interface reference.

## Plan the commits

1. Run `git status` in the repository to see the modified, new and deleted files. Entries staged outside your clusters belong to parallel sessions: never unstage them.
2. Run `git diff` and read the changes.
3. Cluster the changes by concern: files that serve the same feature, fix or content batch form one cluster. Make one commit per cluster. The default is a single commit; split only when clusters are unrelated. Relatedness decides, never size: a large related batch is one commit, and two unrelated files are two commits. Never put unrelated clusters in one commit.
4. For a move or rename, run `git mv <old> <new>` first, then pass both the old and the new path as files of that cluster. A deletion needs only the deleted path.
5. Draft one message per cluster, as [The commit message](#the-commit-message) states.

Present the whole plan (clusters, files, messages) in your message. When the user asked for a commit, commit the clusters in plan order. Push only when the user asked for a push.

## Run one commit per cluster

Run the tool with the working directory inside the repository. The tool finds the repository root from its working directory: run from the workspace root or from another repository, it operates on that other repository and reports `no changes to commit` for paths that did change.

- **The message.** Pass a one-line message with `-m`. For a message with a body, a list or blank lines, write the whole message to a scratch file with the harness's file-writing tool and pass the file's absolute path with `-F`. Never build a multi-line message with a shell heredoc or here-string (`<<EOF`, PowerShell `@'...'@`): the two shells' syntaxes differ, and one pasted into the other leaves stray `@` or `EOF` markers in the commit.
- **The paths.** Pass every path the cluster touches, each with its own `-f`, relative to the repository root, including both sides of a rename. A path is a name, never a pattern: quote it for the shell when it holds `*`, `?`, `[`, `]` or a leading `:`, and add no escaping for git, so `-f 'f[1].md'` commits that one file and never `f1.md`.
- **A directory as a path.** A directory includes every changed file beneath it. Use one when a cluster touches more files than fit on one command line; an explicit list of a few hundred `-f` paths exceeds the OS argument limit. A directory commits whatever is under it at that moment, including a file a parallel session put there: pass explicit file paths when the cluster must be exact.

Never start the next cluster until the current one is committed.

## What a run guarantees

- The tool stages only the listed paths and commits from a temporary index that holds nothing else. An entry a parallel session staged is never committed, including one staged during the run, and it stays staged as that session left it.
- An executable bit staged on a listed path with `git update-index --chmod=+x` is committed.
- The tool commits first and then syncs the remote; a clean automatic merge prints nothing. Its pull is always a merge, also where the repository sets `pull.rebase`.
- A commit a parallel session makes during the run is never reverted: the tool's commit lands on top of it and differs from it by the listed paths alone.
- The repository's `pre-commit`, `commit-msg` and `post-commit` hooks run, with the outcomes `git commit` gives them: a failing `pre-commit` or `commit-msg`, or a message that `commit-msg` leaves empty, refuses the commit; a failing `post-commit` is a `WARNING` and the commit stands. `prepare-commit-msg` does not run.
- A merge, rebase, cherry-pick or revert already in progress in the repository is never aborted, finished or changed. The tool still commits the listed paths, then prints `WARNING: a <operation> is in progress in this working tree … Commit <hash> was made`. When that warning adds `The remote is ahead and was NOT pulled`, the cluster is committed and the remote is not merged: run `git pull --no-edit --no-rebase` once the operation is finished.

## What a successful run prints

On exit 0 the tool prints `committed <hash>`, only while the branch holds that commit; then `files in commit (<n>): …`, read back from the commit object; and a `synced remote: merge commit …` line when the sync created a merge. The temporary index guarantees that the committed files fall under the paths you listed, and a listed path with no changes aborts the run. Trust this output: do not run `git show`, `git log` or any other command to check the commit's contents again.

## When a run fails

On a nonzero exit the tool made no commit, unless the error says `Commit <hash> was made` (the last three rows). Read the error and take the action of its row.

| Error | Meaning | Action |
|---|---|---|
| `no changes to commit: <paths>` | A listed file or directory had no changes | Correct the path list and run the tool again for that cluster |
| `merge conflict pulling remote changes in: <files>` | The remote diverged and conflicts with this cluster | Follow [Resolving a merge conflict](#resolving-a-merge-conflict) |
| `could not pull remote changes. NOT a merge conflict` | The remote sync failed for a reason that is not a conflict; git's own error follows the message | Read that error and fix its cause: a stale `.git/index.lock` (verify that no git process is running, then remove it), a network or authentication failure, a refused fast-forward. Then run the tool again for that cluster. There is no conflict to resolve. When the message lists entries other sessions have staged, git refused the merge because of them: leave them staged and run again once those sessions have committed them |
| `could not pull remote changes: the working tree already held unresolved conflicts before the pull, in: <files>` | The listed files were in conflict before the tool ran, with no merge, rebase, cherry-pick, revert or patch application in progress (for example after `git stash pop`), and git refuses to pull over them. Nothing conflicts with the remote. The tool made no commit and left those conflicts as they were; this cluster's changes are staged | Never enter Resolving a merge conflict: there is no merge. The conflicts belong to whoever ran the command that left them: tell the user. Run the tool again once they are resolved with git itself |
| `another session committed these requested paths during this run: <paths>` | A parallel session committed a change to a listed path while the tool ran. The tool made no commit, so that change is not overwritten; this cluster's changes are still staged | Read `git diff --cached -- <paths>`, which now shows this cluster's change against the other session's commit. When it is what the cluster intends, run the tool again; when it would undo the other session's change, tell the user before running again |
| `the commit-msg hook left the commit message empty` | The repository's `commit-msg` hook emptied the message, so the commit was refused; this cluster's changes are staged | Tell the user that the hook rejects this message. Run the tool again with a message the hook accepts |
| `a <operation> is in progress in this working tree and left these requested paths in conflict: <paths>` | A listed path is one that an unfinished merge, rebase, cherry-pick, revert or patch application (`git am`) left in conflict. The tool made no commit and staged nothing | Never commit those paths with the tool: whoever started the operation finishes them with git itself (for a merge that the procedure below left open: its steps 5 to 7). Run the tool again without them |
| `these requested paths are in conflict, with no merge, rebase, cherry-pick, revert or patch application in progress: <paths>` | A listed path is one git records as in conflict, and no operation is in progress (for example after `git stash pop`). The tool made no commit and staged nothing: staging the path would tell git the conflict is resolved, with whatever the file holds | Never resolve it without the user and never guess: present each path to the user and ask how to resolve it. Edit it to the agreed content, run `git add <path>`, then run the tool again |
| `a <operation> is in progress in this working tree … Commit <hash> was made. The remote is ahead and was NOT pulled … Nothing was pushed` | `--push` was given, the commit was made, and the tool could not pull because of the unfinished operation, so it pushed nothing | The cluster is committed: never run the tool again for it. Once the operation is finished, run `git pull --no-edit --no-rebase`, then `git push` |
| `Commit <hash> was made, but another session moved the branch to <tip>, which does not contain it`, with no pull error | The commit was made and the remote sync did not fail, but a parallel session then moved the branch off the commit. Nothing was pushed | The cluster is not on the branch: never run the tool again for it. Tell the user before running the `git cherry-pick <hash>` the error names |
| Any pull error above, carrying `Commit <hash> was made` in place of `No commit made` | The pull failed and another session moved the branch after this cluster's commit, so the tool undid nothing: its undo removes its own commit and nothing else. The sentence says where the commit is: still on the branch under the other session's commit, still the branch tip (the undo itself failed), or off the branch | The cluster is committed: never run the tool again for it. Fix the cause the error names, then run `git pull --no-edit --no-rebase`; on a conflict, enter Resolving a merge conflict at step 3. When the sentence says the branch no longer contains the commit, tell the user before running the `git cherry-pick <hash>` it names |

## Resolving a merge conflict

The tool exited nonzero with `merge conflict pulling remote changes in: <files>` and `No commit made`. It left this state:

- This cluster's changes are staged. The working tree holds no conflict markers: the tool aborted the merge and undid its commit.
- The remote's divergence is not integrated; the local branch is still behind the remote.
- Other changes in the working tree are untouched, and an entry a parallel session staged is still staged.

Follow these steps in order and skip none. Run each git command in the repository.

1. Stop. Do not run the tool again and commit nothing else until the conflict is resolved; running it again reproduces the same conflict.
2. Record this cluster as a local commit so the work cannot be lost: `git commit -m "<this cluster's message>" -- <this cluster's paths>`. The paths limit the commit to this cluster; without them it carries every staged entry, including a parallel session's. This form drops an executable bit staged with `git update-index --chmod=+x`: stage it again and commit it after step 7.
3. Pull to merge the remote: `git pull --no-edit --no-rebase`. This creates the conflict again, now as a merge with conflict markers in the working tree. While this merge is open, a parallel session's `rbtv-commit` run leaves it as it is.
4. List the conflicting files: `git diff --name-only --diff-filter=U`.
5. Present every conflicting file to the user and ask how to resolve each one. Never resolve one without the user's answer, and never guess.
6. Edit each conflicting file to the agreed content, then run `git add <file>` for each resolved file.
7. Complete the merge: `git commit --no-edit`.
8. When the project has a test command (check its `CLAUDE.md` or `package.json`), run it. On a failure, stop, tell the user and do not push.
9. Push only when the user asked for a push: `git push`.

Continue with the next cluster of the plan only after this one is committed and, when a push was asked for, pushed.

## The commit message

- Follow conventional commits.
- Summarize why the change was made; the diff shows what changed.
- Keep the first line under 72 characters.
- Never add a `Co-Authored-By` trailer, a `Generated with Claude Code` line or any other AI-attribution line to the message or its trailers.

## Maintenance

The program is one file, `commit.py`, using the Python 3 standard library only. `test_commit.py`, beside it, is its pytest suite; after a change, run it from the repository root:

```
python -m pytest meta/code/capabilities/tools/rbtv-commit/test_commit.py -q
```

For a change to the tool's verbs, options, help or output, follow [Building a command-line interface](../../methods/building-a-cli.md). The error texts in the table above are the program's own: change a message in `commit.py` and its row together.
