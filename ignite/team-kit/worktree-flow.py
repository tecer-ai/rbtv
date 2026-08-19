#!/usr/bin/env python3
"""worktree-flow.py — the PRODUCT worktree flow (task 7.38; settle ledger R14/R25/R26/R27).

Per-seat git worktrees under the CENTRAL `.rbtv/worktrees/` root — never inside a goal
folder, never beside the repo checkout (R27). One worktree per seat, named
`{repo}--{goal}--{seat}`; the goal's integration worktree is that same rule with the seat
name `integration`. The daemon derives a seat's bwrap grants from this naming and from
nothing a caller can pass (server/spawn/spawn.js resolveSeatGrants), so the naming is the
mechanism, not a label.

SELF-ROOT OVERRIDE (P3).  A repo whose realpath equals the workspace realpath is the
"self repo" (the vault, when the vault IS the workspace). By default it uses the same
`.rbtv/worktrees/` root as every other repo. If `{ws}/.rbtv/config/worktrees-self-root`
exists, its first non-empty line is a workspace-relative directory used INSTEAD for the
self repo only. Absent or empty file → today's behaviour, including for the self repo.
Both this tool and spawn.js#resolveSeatGrants read that one file; it is not a CLI flag.
On this vault the file contains `5-workbench/vault-worktrees` (one level under
`5-workbench/`, so `5-workbench/*/` gitignores it). The directory is created on demand.

REPOS DECLARATION.  `{ws}/.rbtv/goals/{goal}/goal.md` frontmatter MUST carry a `repos:`
list of workspace-relative repo paths. The self repo is spelled `.`. `open-goal` and
`open-seat` refuse (E_UNDECLARED_REPO) if the key is absent or if `--repo` (by realpath)
is not in the list. No silent "allow anything" fallback.

READ-ONLY REFUSAL.  `{ws}/.artifacts/repos.md` rows containing `READ ONLY` contribute
every backticked token (trailing `/` stripped) as a forbidden repo. A `--repo` whose
realpath equals `{ws}/{that path}` is refused (E_READ_ONLY_REPO) before anything is
created. If the registry file is absent, one loud line is printed and only the
declaration gate applies.

BRANCHES.  X = the goal integration branch, Y = a seat branch cut from X at seat open and
deleted after it merges.

  ⚠ THE RULED NAMES CANNOT BOTH EXIST IN GIT.  R27 rules X = `goal/{slug}` and
  Y = `goal/{slug}/{seat}`.  A git ref is a FILE, so `refs/heads/goal/{slug}` existing
  forbids the DIRECTORY `refs/heads/goal/{slug}/` that Y needs:

      $ git branch goal/mygoal && git branch goal/mygoal/seat1
      fatal: cannot lock ref 'refs/heads/goal/mygoal/seat1':
             'refs/heads/goal/mygoal' exists; cannot create 'refs/heads/goal/mygoal/seat1'

  Creating Y first only moves the conflict onto X. No config, no packed-refs state and no
  worktree flag lifts it. So X carries ONE extra segment — the whole deviation lives in
  INTEGRATION_LEAF below and nowhere else.

  AMENDED BY RULING: runs/run-3/decisions.md#p-r27-branch-scheme-amended-integration-suffix
  (leader, PROVISIONAL, 2026-08-05; coordination #3872 -> #3878). X = `goal/{slug}/integration`,
  Y unchanged. A flat `goal/{slug}--{seat}` was rejected there for a hazard worth carrying here:
  its one-goal glob catches SIBLING GOALS whose slug is a prefix of another's, so a cleanup flow
  built on it eventually deletes a sibling goal's branch and looks correct doing it. The path
  separator is the one separator a slug cannot contain.

MERGE (R25/R26).  A seat's "PR" is its done-report carrying its branch. A verifier reads
`git diff X...Y` LOCALLY; the leader (or deputy) runs `merge-seat` in the goal's
integration worktree on that verdict. Conflicts are NEVER force-merged — this tool aborts
the merge and tells the seat to rebase its own Y onto current X and re-submit. Only the
goal-close X->main step is a real GitHub PR, one owner-visible artifact per goal, executed
by the owner or by master — not by this tool, which refuses to touch main.

PROPOSE-MERGE (D4).  `propose-merge` never merges. It refuses if X is missing (E_NO_X) or
has no commits ahead of `--main` (E_NOT_AHEAD). Self-repo OR no GitHub `origin` → bus
route (compose an owner-facing body; send via team-kit/coord.py `--file`, never an inline
shell arg). Otherwise → PR route: push X to origin, `gh pr create` (never merge, never
push main). `--body-out PATH` writes the composed body; `--dry-run` prints the argv that
would run and performs no network/bus side effect.

CLOSE-GOAL --park (P2).  Removes every worktree directory for the goal (integration and
seats) and deletes NO branch. Prints each `goal/{slug}/*` branch with its merge status
against `--main`. Mutually exclusive with `--force` (E_PARK_FORCE). Plain `close-goal`
keeps its exit-4 refusal unless X is already merged into main. Unmerged branches are
never auto-deleted: `delete_branch` asserts ancestry; `merge-seat` deletes Y only after
the merge that made it an ancestor.

WHAT THIS TOOL IS NOT.  Branch discipline is enforced by PR REVIEW, not by the kernel
(R14: kernel-hard isolation would need per-seat clones, deliberately not taken). The
kernel half that DOES exist is the bwrap bind template — a seat cannot write main's
working tree or another seat's worktree, proven on disk by file-absence
(server/spawn/probes/probe-worktree-flow.js). Nothing here stops a seat that HOLDS a
worktree from committing whatever it likes to its OWN branch; only review does.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

# The one deviation from R27's literal branch names, and the only place it exists.
# X = f"goal/{slug}/{INTEGRATION_LEAF}", Y = f"goal/{slug}/{seat}".  See the D/F note above.
INTEGRATION_LEAF = "integration"

# Typed exit codes. The reserved-name refusal carries its OWN code because a caller (and the
# selftest) must be able to tell it apart from the incidental "that branch already exists" —
# without a code the two are one message apart, and a check that accepts either passes when the
# rider is deleted. Measured: with a bare `except FlowError` the M2 mutation ran GREEN.
E_RESERVED_SEAT_NAME = 5
E_UNDECLARED_REPO = 6
E_READ_ONLY_REPO = 7
E_NO_X = 8
E_NOT_AHEAD = 9
E_PARK_FORCE = 10

SELF_ROOT_CONFIG = os.path.join(".rbtv", "config", "worktrees-self-root")
COORD_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coord.py")


def x_branch(goal):
    return f"goal/{goal}/{INTEGRATION_LEAF}"


def y_branch(goal, seat):
    if seat == INTEGRATION_LEAF:
        # RESERVED NAME rider of #p-r27-branch-scheme-amended-integration-suffix. Under (a) a seat
        # called `integration` IS its goal's integration branch. Refuse loudly at creation; never
        # silently disambiguate, which would hand one seat the goal's own worktree.
        raise FlowError(
            f"seat name {INTEGRATION_LEAF!r} is RESERVED — it is the goal's own integration "
            f"branch ({x_branch(goal)}) and its worktree. Name the seat something else.",
            code=E_RESERVED_SEAT_NAME)
    return f"goal/{goal}/{seat}"


def worktree_name(repo, goal, seat):
    return f"{repo}--{goal}--{seat}"


class FlowError(Exception):
    """A refusal with an exit code — never a silent fallback."""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def git(repo, *args, check=True):
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True,
    )
    if check and p.returncode != 0:
        raise FlowError(f"git {' '.join(args)} failed (exit {p.returncode}):\n{p.stderr.strip()}")
    return p


def repo_root(path):
    p = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise FlowError(f"{path} is not inside a git repository")
    return p.stdout.strip()


def workspace_root(explicit=None):
    """The workspace whose `.rbtv/` holds the worktrees root. Walk up from cwd by default."""
    if explicit:
        return os.path.abspath(explicit)
    d = os.getcwd()
    while True:
        if os.path.isdir(os.path.join(d, ".rbtv")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise FlowError("no .rbtv/ found walking up from cwd — pass --ws")
        d = parent


def is_self_repo(repo, ws):
    return os.path.realpath(repo) == os.path.realpath(ws)


def self_root_rel(ws):
    """Workspace-relative self-root, or None if the override file is absent/empty."""
    cfg = os.path.join(ws, SELF_ROOT_CONFIG)
    if not os.path.isfile(cfg):
        return None
    with open(cfg, encoding="utf-8") as f:
        for line in f:
            rel = line.strip()
            if rel:
                return rel
    return None


def worktrees_root(ws, repo=None):
    """`.rbtv/worktrees` unless this is the self repo and a self-root override is set."""
    default = os.path.join(ws, ".rbtv", "worktrees")
    if repo is None or not is_self_repo(repo, ws):
        return default
    rel = self_root_rel(ws)
    if not rel:
        return default
    return os.path.normpath(os.path.join(ws, rel))


def all_worktrees_roots(ws):
    """Default root plus the self-root override when configured (dirs may be absent)."""
    roots = [os.path.join(ws, ".rbtv", "worktrees")]
    rel = self_root_rel(ws)
    if rel:
        alt = os.path.normpath(os.path.join(ws, rel))
        if alt not in roots:
            roots.append(alt)
    return roots


def _goal_frontmatter(ws, goal):
    path = os.path.join(ws, ".rbtv", "goals", goal, "goal.md")
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end < 0:
        return ""
    return text[3:end]


def _parse_repos_key(fm):
    """Return the repos: list, or None if the key is absent."""
    lines = fm.splitlines()
    for i, raw in enumerate(lines):
        if not raw.startswith("repos:"):
            continue
        after = raw[len("repos:"):].strip()
        if after.startswith("["):
            inner = after[1:]
            if "]" in inner:
                inner = inner[:inner.rfind("]")]
            return [x.strip().strip("'\"") for x in inner.split(",") if x.strip().strip("'\"")]
        if after:
            return [after.strip("'\"")]
        out = []
        for s in lines[i + 1:]:
            st = s.strip()
            if st.startswith("- "):
                out.append(st[2:].strip().strip("'\""))
            elif st == "":
                continue
            else:
                break
        return out
    return None


def read_only_repo_rels(ws):
    """Workspace-relative read-only paths, or None if the registry file is absent."""
    path = os.path.join(ws, ".artifacts", "repos.md")
    if not os.path.isfile(path):
        return None
    rels = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "READ ONLY" not in line:
                continue
            for tok in re.findall(r"`([^`]+)`", line):
                tok = tok.rstrip("/")
                if tok:
                    rels.append(tok)
    return rels


def gate_repo(ws, goal, repo):
    """Refuse a read-only or undeclared --repo before anything is created."""
    repo_rp = os.path.realpath(repo)
    ro = read_only_repo_rels(ws)
    if ro is None:
        print("WARNING: read-only registry .artifacts/repos.md not found — "
              "only the declaration gate applies", file=sys.stderr)
    else:
        for rel in ro:
            if os.path.realpath(os.path.join(ws, rel)) == repo_rp:
                raise FlowError(
                    f"READ ONLY: repo {repo_rp} is listed read-only in .artifacts/repos.md "
                    f"(path {rel!r}). A goal must never open a worktree here for writing.",
                    code=E_READ_ONLY_REPO)
    declared = _parse_repos_key(_goal_frontmatter(ws, goal))
    if declared is None:
        raise FlowError(
            f"goal {goal!r} has no repos: key in goal.md — declare the repos this goal "
            f"may touch (workspace-relative paths; '.' for the workspace/self repo).",
            code=E_UNDECLARED_REPO)
    allowed = [os.path.realpath(os.path.join(ws, rel)) for rel in declared]
    if repo_rp not in allowed:
        raise FlowError(
            f"repo {repo_rp} is not declared for goal {goal!r}. "
            f"goal declares: {declared!r}",
            code=E_UNDECLARED_REPO)


def branch_exists(repo, branch):
    return git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}",
               check=False).returncode == 0


def worktree_paths(repo):
    """{path: branch-or-None} from git's own record, never from a directory listing."""
    out = git(repo, "worktree", "list", "--porcelain").stdout
    seen, path = {}, None
    for line in out.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
            seen[path] = None
        elif line.startswith("branch ") and path:
            seen[path] = line[len("branch refs/heads/"):]
    return seen


def add_worktree(repo, path, branch, start_point=None):
    if os.path.exists(path):
        raise FlowError(f"{path} already exists — refusing to reuse a path git may not own")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if start_point is None:
        git(repo, "worktree", "add", path, branch)
    else:
        git(repo, "worktree", "add", "-b", branch, path, start_point)
    return path


def remove_worktree(repo, path, force=False):
    """R27 cleanup, one step. Refuses on a dirty tree unless forced — determinism first."""
    steps = []
    if os.path.exists(path):
        args = ["worktree", "remove", path] + (["--force"] if force else [])
        p = git(repo, *args, check=False)
        if p.returncode != 0:
            raise FlowError(
                f"worktree remove refused for {path}:\n{p.stderr.strip()}\n"
                "The tree holds uncommitted or untracked work. Land it, or re-run with --force "
                "to discard it deliberately.", code=4)
        steps.append(f"worktree removed: {path}")
    else:
        steps.append(f"worktree already absent: {path}")
    git(repo, "worktree", "prune")
    steps.append("worktree prune: run")
    return steps


def delete_branch(repo, branch, merged_into, force=False):
    """Delete a branch only once its commits live in `merged_into` — never against HEAD.

    `git branch -d` asks "is it merged into the CURRENT branch", which in the main checkout
    is main — the wrong question here: Y merges into X, and X merges into main. So the
    ancestry is asserted explicitly and the delete is then unconditional (-D).
    """
    if not branch_exists(repo, branch):
        return [f"branch already absent: {branch}"]
    if not force:
        merged = git(repo, "merge-base", "--is-ancestor", branch, merged_into,
                     check=False).returncode == 0
        if not merged:
            raise FlowError(
                f"branch delete refused for {branch}: its commits are not in {merged_into}.\n"
                "Unmerged commits would be lost. Merge it, or re-run with --force.", code=4)
    git(repo, "branch", "-D", branch)
    return [f"branch deleted: {branch} (merged into {merged_into})" if not force
            else f"branch deleted: {branch} (FORCED — unmerged commits discarded)"]


def has_github_origin(repo):
    p = git(repo, "remote", "get-url", "origin", check=False)
    if p.returncode != 0:
        return False
    return "github.com" in (p.stdout or "")


def compose_merge_request_body(repo, goal, x, main, ahead):
    stat = git(repo, "diff", "--stat", f"{main}...{x}").stdout.strip()
    merge_cmd = f"git -C {repo} merge --no-ff -m 'merge {x} into {main}' {x}"
    return (
        f"MERGE REQUEST — owner approval required (this tool never merges)\n"
        f"goal: {goal}\n"
        f"repo: {repo}\n"
        f"branch: {x}\n"
        f"commits ahead of {main}: {ahead}\n"
        f"\n"
        f"diff --stat {main}...{x}:\n"
        f"{stat}\n"
        f"\n"
        f"To merge (owner only):\n"
        f"  {merge_cmd}\n"
    )


# ── verbs ────────────────────────────────────────────────────────────────────────────────

def cmd_open_goal(a):
    repo = repo_root(a.repo)
    name = os.path.basename(repo)
    ws = workspace_root(a.ws)
    gate_repo(ws, a.goal, repo)
    x = x_branch(a.goal)
    path = os.path.join(worktrees_root(ws, repo), worktree_name(name, a.goal, INTEGRATION_LEAF))
    existed = branch_exists(repo, x)
    add_worktree(repo, path, x, start_point=None if existed else a.base)
    print(f"goal open: {a.goal}")
    print(f"  X branch: {x}  ({'existing' if existed else 'cut from ' + a.base})")
    print(f"  integration worktree: {path}")
    return 0


def cmd_open_seat(a):
    repo = repo_root(a.repo)
    name = os.path.basename(repo)
    ws = workspace_root(a.ws)
    gate_repo(ws, a.goal, repo)
    x, y = x_branch(a.goal), y_branch(a.goal, a.seat)
    if not branch_exists(repo, x):
        raise FlowError(f"goal integration branch {x} does not exist — run open-goal first")
    if branch_exists(repo, y):
        raise FlowError(f"seat branch {y} already exists — a seat opens once per goal")
    path = os.path.join(worktrees_root(ws, repo), worktree_name(name, a.goal, a.seat))
    add_worktree(repo, path, y, start_point=x)
    print(f"seat open: {a.seat}")
    print(f"  Y branch: {y}  (from {x})")
    print(f"  worktree: {path}")
    print("  record this path in the run's sessions.csv worktree-path column")
    return 0


def cmd_merge_seat(a):
    """R25/R26 — the merge runs in the goal's INTEGRATION worktree, on a verifier's verdict."""
    repo = repo_root(a.repo)
    name = os.path.basename(repo)
    ws = workspace_root(a.ws)
    x, y = x_branch(a.goal), y_branch(a.goal, a.seat)
    root = worktrees_root(ws, repo)
    integ = os.path.join(root, worktree_name(name, a.goal, INTEGRATION_LEAF))
    seat_wt = os.path.join(root, worktree_name(name, a.goal, a.seat))
    if not os.path.isdir(integ):
        raise FlowError(f"integration worktree missing at {integ} — run open-goal first")
    if not branch_exists(repo, y):
        raise FlowError(f"seat branch {y} does not exist")

    p = git(integ, "merge", "--no-ff", "-m", f"merge {y} into {x}", y, check=False)
    if p.returncode != 0:
        git(integ, "merge", "--abort", check=False)
        raise FlowError(
            f"CONFLICT merging {y} into {x} — aborted, nothing force-merged (R26).\n"
            f"{p.stdout.strip()}\n"
            f"The SEAT rebases its own Y onto current {x} and re-submits; the leader arbitrates "
            "only when two seats collide on the same file.", code=3)
    print(f"merged: {y} -> {x} (in {integ})")

    # R27 cleanup at its ruled moment: seat worktree + Y go as soon as Y has merged.
    for line in remove_worktree(repo, seat_wt, force=a.force):
        print(f"  {line}")
    for line in delete_branch(repo, y, merged_into=x, force=a.force):
        print(f"  {line}")
    return 0


def _goal_worktree_dirs(root, goal):
    if not os.path.isdir(root):
        return []
    out = []
    for entry in sorted(os.listdir(root)):
        if f"--{goal}--" not in entry:
            continue
        path = os.path.join(root, entry)
        if os.path.isdir(path):
            out.append(path)
    return out


def cmd_close_goal(a):
    """R27 — integration worktree + X go after X->main has merged. This tool never touches main."""
    if getattr(a, "park", False) and getattr(a, "force", False):
        raise FlowError(
            "--park and --force are mutually exclusive: preserve everything, or discard "
            "deliberately — not both.",
            code=E_PARK_FORCE)
    repo = repo_root(a.repo)
    name = os.path.basename(repo)
    ws = workspace_root(a.ws)
    x = x_branch(a.goal)
    root = worktrees_root(ws, repo)
    integ = os.path.join(root, worktree_name(name, a.goal, INTEGRATION_LEAF))

    if getattr(a, "park", False):
        for path in _goal_worktree_dirs(root, a.goal):
            for line in remove_worktree(repo, path, force=False):
                print(f"  {line}")
        refs = git(repo, "for-each-ref", "--format=%(refname:short)",
                   f"refs/heads/goal/{a.goal}/").stdout.split()
        for br in refs:
            merged = git(repo, "merge-base", "--is-ancestor", br, a.main,
                         check=False).returncode == 0
            status = "merged" if merged else "UNMERGED"
            print(f"preserved: {br}  {status} into {a.main}")
        print(f"goal parked: {a.goal} (worktrees removed, branches kept)")
        return 0

    if branch_exists(repo, x) and not a.force:
        merged = git(repo, "branch", "--merged", a.main, "--format=%(refname:short)",
                     check=False).stdout.split()
        if x not in merged:
            raise FlowError(
                f"{x} is not merged into {a.main} — refusing to delete it.\n"
                f"X->main is a real GitHub PR (R25), approved by the owner and executed by the "
                "owner or master — never by this tool. Re-run after it lands, or --force to "
                "discard the branch deliberately.", code=4)
    for line in remove_worktree(repo, integ, force=a.force):
        print(f"  {line}")
    for line in delete_branch(repo, x, merged_into=a.main, force=a.force):
        print(f"  {line}")
    print(f"goal closed: {a.goal}")
    return 0


def cmd_list(a):
    ws = workspace_root(a.ws)
    repo = repo_root(a.repo) if a.repo else None
    known = worktree_paths(repo) if repo else {}
    printed = False
    for root in all_worktrees_roots(ws):
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            path = os.path.join(root, entry)
            if not os.path.isdir(path):
                continue
            if a.goal and f"--{a.goal}--" not in entry:
                continue
            branch = known.get(path, "?" if repo else "")
            print(f"{entry}\t{branch or '(detached/unregistered)'}\t{path}")
            printed = True
    if not printed:
        print(f"{worktrees_root(ws)} (absent — no worktrees open)")
    return 0


def cmd_propose_merge(a):
    """D4 — propose X→main. This verb NEVER merges."""
    repo = repo_root(a.repo)
    ws = workspace_root(a.ws)
    x = x_branch(a.goal)
    main = a.main
    if not branch_exists(repo, x):
        raise FlowError(
            f"integration branch {x} does not exist — nothing to propose",
            code=E_NO_X)
    ahead = git(repo, "rev-list", "--count", f"{main}..{x}").stdout.strip()
    if ahead == "0":
        raise FlowError(
            f"{x} has no commits ahead of {main} — empty merge request refused",
            code=E_NOT_AHEAD)
    body = compose_merge_request_body(repo, a.goal, x, main, ahead)
    body_path = getattr(a, "body_out", None)
    if body_path:
        parent = os.path.dirname(os.path.abspath(body_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(body_path, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"body written: {body_path}")
    use_bus = is_self_repo(repo, ws) or not has_github_origin(repo)
    route = "bus" if use_bus else "pr"
    print(f"propose-merge: route={route} goal={a.goal} branch={x} ahead={ahead}")
    dry = getattr(a, "dry_run", False)
    if use_bus:
        pkg = os.path.join(ws, ".rbtv", "goals", a.goal)
        if not body_path:
            tmp = tempfile.NamedTemporaryFile(
                prefix="wtflow-mr-", suffix=".txt", delete=False, mode="w", encoding="utf-8")
            tmp.write(body)
            tmp.close()
            body_path = tmp.name
        argv = [sys.executable, COORD_PY, "--package", pkg,
                "send", "owner", "--type", "escalation", "--file", body_path, "--as", "leader"]
        if dry:
            print("dry-run coord argv:")
            print("  " + " ".join(argv))
            return 0
        p = subprocess.run(argv, capture_output=True, text=True)
        sys.stdout.write(p.stdout)
        sys.stderr.write(p.stderr)
        if p.returncode != 0:
            raise FlowError(f"coord send failed (exit {p.returncode})", code=p.returncode)
        return 0
    title = f"goal {a.goal}: merge {x} into {main}"
    if not body_path:
        tmp = tempfile.NamedTemporaryFile(
            prefix="wtflow-pr-", suffix=".txt", delete=False, mode="w", encoding="utf-8")
        tmp.write(body)
        tmp.close()
        body_path = tmp.name
    gh_argv = ["gh", "pr", "create", "--base", main, "--head", x,
               "--title", title, "--body-file", body_path]
    if dry:
        print("dry-run git argv:")
        print(f"  git -C {repo} push -u origin {x}")
        print("dry-run gh argv:")
        print("  " + " ".join(gh_argv))
        return 0
    git(repo, "push", "-u", "origin", x)
    p = subprocess.run(gh_argv, cwd=repo, capture_output=True, text=True)
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    if p.returncode != 0:
        raise FlowError(f"gh pr create failed (exit {p.returncode}):\n{p.stderr.strip()}")
    return 0


# ── selftest ─────────────────────────────────────────────────────────────────────────────

def _write_goal_md(ws, goal, repos):
    gdir = os.path.join(ws, ".rbtv", "goals", goal)
    os.makedirs(gdir, exist_ok=True)
    lines = ["---", "repos:"]
    for r in repos:
        lines.append(f"  - {r}")
    lines.append("---\n")
    with open(os.path.join(gdir, "goal.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _init_repo(path, branch="main"):
    os.makedirs(path, exist_ok=True)
    git(path, "init", "-q", "-b", branch, ".")
    git(path, "config", "user.email", "selftest@local")
    git(path, "config", "user.name", "selftest")
    with open(os.path.join(path, "source.txt"), "w") as f:
        f.write("ORIGINAL\n")
    git(path, "add", "source.txt")
    git(path, "commit", "-q", "-m", "base")


def cmd_selftest(a):
    """One full cycle in a throwaway workspace: open-goal, open-seat, merge, cleanup.

    This is the R27 CLEANUP DETERMINISM TRACE — every removal is asserted by on-disk
    absence and by git's own worktree/branch record, never by the command's success line.
    """
    tmp = tempfile.mkdtemp(prefix="wtflow-selftest-")
    trace = []

    def step(s):
        trace.append(s)
        print(s)

    try:
        ws = os.path.join(tmp, "ws")
        repo = os.path.join(ws, "repo")
        os.makedirs(os.path.join(ws, ".rbtv"))
        _init_repo(repo)
        _write_goal_md(ws, "testgoal", ["repo"])
        step(f"fixture: repo {repo}, ws {ws}")

        ns = argparse.Namespace(repo=repo, ws=ws, goal="testgoal", base="main",
                                seat="alpha", force=False, main="main", park=False)
        cmd_open_goal(ns)
        integ = os.path.join(worktrees_root(ws, repo), "repo--testgoal--integration")
        assert os.path.isdir(integ), "integration worktree absent"
        assert branch_exists(repo, x_branch("testgoal")), "X branch absent"
        step(f"OK open-goal: X={x_branch('testgoal')}, integration worktree on disk")

        cmd_open_seat(ns)
        seat_wt = os.path.join(worktrees_root(ws, repo), "repo--testgoal--alpha")
        assert os.path.isdir(seat_wt), "seat worktree absent"
        assert branch_exists(repo, y_branch("testgoal", "alpha")), "Y branch absent"
        step(f"OK open-seat: Y={y_branch('testgoal', 'alpha')}, seat worktree on disk")

        # RESERVED NAME rider — a seat called `integration` is refused, and refused BEFORE
        # anything lands: the integration worktree must be byte-identical afterwards.
        integ_before = sorted(os.listdir(integ))
        try:
            cmd_open_seat(argparse.Namespace(**{**vars(ns), "seat": INTEGRATION_LEAF}))
            raise AssertionError(f"seat named {INTEGRATION_LEAF!r} was ACCEPTED — rider breached")
        except FlowError as e:
            assert e.code == E_RESERVED_SEAT_NAME, (
                f"refused with code {e.code}, not the reserved-name code "
                f"{E_RESERVED_SEAT_NAME} — the leg would pass on an incidental collision too")
        assert sorted(os.listdir(integ)) == integ_before, \
            "the refused seat name still disturbed the integration worktree"
        step(f"OK reserved name: seat {INTEGRATION_LEAF!r} refused, integration worktree untouched")

        with open(os.path.join(seat_wt, "seat-work.txt"), "w") as f:
            f.write("SEAT WORK\n")
        git(seat_wt, "add", "seat-work.txt")
        git(seat_wt, "-c", "user.email=s@l", "-c", "user.name=s", "commit", "-q", "-m", "seat work")
        step("OK seat commit landed on Y (a seat commits in its own worktree)")

        cmd_merge_seat(ns)
        assert os.path.exists(os.path.join(integ, "seat-work.txt")), "merge did not carry the file"
        # R27 cleanup, asserted two differently-keyed ways: the filesystem, and git's record.
        assert not os.path.exists(seat_wt), f"RESIDUE: seat worktree still on disk at {seat_wt}"
        assert seat_wt not in worktree_paths(repo), "RESIDUE: git still lists the seat worktree"
        assert not branch_exists(repo, y_branch("testgoal", "alpha")), "RESIDUE: Y still exists"
        step("OK merge-seat: Y->X merged; seat worktree + Y removed (fs absent AND git-record absent)")

        # Conflict rule: a second seat colliding on the same file must abort, never force-merge.
        ns2 = argparse.Namespace(**{**vars(ns), "seat": "beta"})
        cmd_open_seat(ns2)
        beta_wt = os.path.join(worktrees_root(ws, repo), "repo--testgoal--beta")
        with open(os.path.join(beta_wt, "seat-work.txt"), "w") as f:
            f.write("BETA VERSION\n")
        git(beta_wt, "add", "seat-work.txt")
        git(beta_wt, "-c", "user.email=b@l", "-c", "user.name=b", "commit", "-q", "-m", "beta work")
        # make X diverge on the same file
        with open(os.path.join(integ, "seat-work.txt"), "w") as f:
            f.write("X VERSION\n")
        git(integ, "add", "seat-work.txt")
        git(integ, "-c", "user.email=x@l", "-c", "user.name=x", "commit", "-q", "-m", "x work")
        try:
            cmd_merge_seat(ns2)
            raise AssertionError("conflict was NOT refused — a force-merge slipped through")
        except FlowError as e:
            assert e.code == 3, f"conflict exited {e.code}, expected 3"
        assert git(integ, "rev-parse", "-q", "--verify", "MERGE_HEAD",
                   check=False).returncode != 0, "merge left MERGE_HEAD — not aborted"
        assert open(os.path.join(integ, "seat-work.txt")).read() == "X VERSION\n", \
            "X's working tree was mutated by the aborted merge"
        assert os.path.isdir(beta_wt), "aborted merge removed the seat worktree anyway"
        step("OK conflict: merge aborted, X untouched, seat worktree + Y kept for the rebase (R26)")

        # close-goal refuses while X is unmerged into main — X->main is a real PR, not this tool's.
        try:
            cmd_close_goal(ns)
            raise AssertionError("close-goal deleted an unmerged X")
        except FlowError as e:
            assert e.code == 4, f"unmerged close exited {e.code}, expected 4"
        step("OK close-goal refuses while X is unmerged into main (X->main is the owner's PR)")

        # THE RULED REMEDY (R26): the SEAT rebases its own Y onto current X and re-submits.
        # Run here exactly as a seat would, in the seat's own worktree.
        git(beta_wt, "rebase", x_branch("testgoal"), check=False)
        with open(os.path.join(beta_wt, "seat-work.txt"), "w") as f:
            f.write("X VERSION + BETA\n")
        git(beta_wt, "add", "seat-work.txt")
        git(beta_wt, "-c", "user.email=b@l", "-c", "user.name=b",
            "-c", "core.editor=true", "rebase", "--continue")
        cmd_merge_seat(ns2)
        assert not os.path.exists(beta_wt), "RESIDUE: beta worktree survived its merge"
        step("OK rebase-and-resubmit: the re-submitted Y merges cleanly and cleans up (R26 remedy)")

        git(repo, "merge", "--no-ff", "-m", "X->main", x_branch("testgoal"))
        cmd_close_goal(ns)
        assert not os.path.exists(integ), f"RESIDUE: integration worktree still at {integ}"
        assert integ not in worktree_paths(repo), "RESIDUE: git still lists the integration worktree"
        assert not branch_exists(repo, x_branch("testgoal")), "RESIDUE: X still exists"
        left = [e for e in os.listdir(worktrees_root(ws, repo)) if "--testgoal--" in e]
        assert left == [], f"RESIDUE under the worktrees root: {left}"
        step("OK close-goal: integration worktree + X removed; worktrees root holds NO testgoal residue")

        # ── self-root override (P3) ────────────────────────────────────────────────
        self_ws = os.path.join(tmp, "selfws")
        os.makedirs(os.path.join(self_ws, ".rbtv", "config"))
        with open(os.path.join(self_ws, SELF_ROOT_CONFIG), "w", encoding="utf-8") as f:
            f.write("wb/vault-worktrees\n")
        _init_repo(self_ws)
        _write_goal_md(self_ws, "selfgoal", ["."])
        self_ns = argparse.Namespace(repo=self_ws, ws=self_ws, goal="selfgoal", base="main",
                                     seat="alpha", force=False, main="main", park=False)
        cmd_open_goal(self_ns)
        self_integ = os.path.join(self_ws, "wb", "vault-worktrees",
                                  f"{os.path.basename(self_ws)}--selfgoal--integration")
        default_wrong = os.path.join(self_ws, ".rbtv", "worktrees",
                                     f"{os.path.basename(self_ws)}--selfgoal--integration")
        assert os.path.isdir(self_integ), f"self-root worktree absent at {self_integ}"
        assert not os.path.exists(default_wrong), f"self repo leaked into default root: {default_wrong}"
        step("OK self-root override: self-repo worktree landed under override, not .rbtv/worktrees")

        # ── goal-declaration gate (accept already proven above; refuse both arms) ──
        other = os.path.join(ws, "other")
        _init_repo(other)
        try:
            cmd_open_goal(argparse.Namespace(**{**vars(ns), "repo": other, "goal": "testgoal"}))
            raise AssertionError("undeclared repo was ACCEPTED")
        except FlowError as e:
            assert e.code == E_UNDECLARED_REPO, f"undeclared repo exited {e.code}, expected {E_UNDECLARED_REPO}"
            assert "testgoal" in str(e) and "declares" in str(e), str(e)
        assert not branch_exists(other, x_branch("testgoal")), "undeclared open-goal created a branch"
        step("OK goal-declaration gate: declared repo accepted; undeclared repo refused")

        bare = os.path.join(ws, ".rbtv", "goals", "norepos")
        os.makedirs(bare, exist_ok=True)
        with open(os.path.join(bare, "goal.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: norepos\n---\n")
        try:
            cmd_open_goal(argparse.Namespace(**{**vars(ns), "goal": "norepos"}))
            raise AssertionError("missing repos: key was ACCEPTED")
        except FlowError as e:
            assert e.code == E_UNDECLARED_REPO, f"missing repos: exited {e.code}"
            assert "declare" in str(e).lower() or "repos:" in str(e), str(e)
        step("OK goal-declaration gate: missing repos: key refused")

        # ── read-only refusal ──────────────────────────────────────────────────────
        ro_ws = os.path.join(tmp, "rows")
        ro_repo = os.path.join(ro_ws, "3-resources", "tools", "stools")
        os.makedirs(os.path.join(ro_ws, ".rbtv"))
        os.makedirs(os.path.join(ro_ws, ".artifacts"))
        _init_repo(ro_repo)
        _write_goal_md(ro_ws, "rogoal", ["3-resources/tools/stools"])
        with open(os.path.join(ro_ws, ".artifacts", "repos.md"), "w", encoding="utf-8") as f:
            f.write(
                "| **stools** — **READ ONLY NEVER EDIT** | `3-resources/tools/stools/` "
                "(local-only) | https://example | |\n"
            )
        try:
            cmd_open_goal(argparse.Namespace(
                repo=ro_repo, ws=ro_ws, goal="rogoal", base="main",
                seat="alpha", force=False, main="main", park=False))
            raise AssertionError("read-only repo was ACCEPTED")
        except FlowError as e:
            assert e.code == E_READ_ONLY_REPO, f"read-only exited {e.code}, expected {E_READ_ONLY_REPO}"
            assert "READ ONLY" in str(e), str(e)
        assert not branch_exists(ro_repo, x_branch("rogoal")), "read-only open-goal created a branch"
        assert not os.path.isdir(os.path.join(ro_ws, ".rbtv", "worktrees")), \
            "read-only open-goal created a worktrees root"
        step("OK read-only refusal: READ ONLY repo refused, nothing created")

        # ── propose-merge bus route ────────────────────────────────────────────────
        # self_ws is the self repo (no github origin) → bus. Need X ahead of main.
        cmd_open_seat(self_ns)
        self_seat = os.path.join(self_ws, "wb", "vault-worktrees",
                                 f"{os.path.basename(self_ws)}--selfgoal--alpha")
        with open(os.path.join(self_seat, "ahead.txt"), "w") as f:
            f.write("AHEAD\n")
        git(self_seat, "add", "ahead.txt")
        git(self_seat, "-c", "user.email=s@l", "-c", "user.name=s",
            "commit", "-q", "-m", "ahead work")
        cmd_merge_seat(self_ns)
        body_out = os.path.join(tmp, "mr-body.txt")
        rc = cmd_propose_merge(argparse.Namespace(
            repo=self_ws, ws=self_ws, goal="selfgoal", main="main",
            body_out=body_out, dry_run=True))
        assert rc == 0, "propose-merge dry-run failed"
        body = open(body_out, encoding="utf-8").read()
        assert "selfgoal" in body and x_branch("selfgoal") in body, body
        assert "commits ahead of main:" in body, body
        assert "this tool never merges" in body, body
        assert "git -C" in body and "merge --no-ff" in body, body
        try:
            cmd_propose_merge(argparse.Namespace(
                repo=self_ws, ws=self_ws, goal="nosuch", main="main",
                body_out=None, dry_run=True))
            raise AssertionError("propose-merge accepted a missing X")
        except FlowError as e:
            assert e.code == E_NO_X, f"missing X exited {e.code}"
        step("OK propose-merge bus route: body composed (--body-out), missing X refused")

        # ── --park preserves unmerged branches ─────────────────────────────────────
        park_ws = os.path.join(tmp, "parkws")
        park_repo = os.path.join(park_ws, "repo")
        os.makedirs(os.path.join(park_ws, ".rbtv"))
        _init_repo(park_repo)
        _write_goal_md(park_ws, "parkgoal", ["repo"])
        park_ns = argparse.Namespace(repo=park_repo, ws=park_ws, goal="parkgoal", base="main",
                                     seat="alpha", force=False, main="main", park=False)
        cmd_open_goal(park_ns)
        cmd_open_seat(park_ns)
        park_integ = os.path.join(worktrees_root(park_ws, park_repo), "repo--parkgoal--integration")
        park_seat = os.path.join(worktrees_root(park_ws, park_repo), "repo--parkgoal--alpha")
        with open(os.path.join(park_integ, "x-ahead.txt"), "w") as f:
            f.write("X AHEAD\n")
        git(park_integ, "add", "x-ahead.txt")
        git(park_integ, "-c", "user.email=x@l", "-c", "user.name=x", "commit", "-q", "-m", "x ahead")
        with open(os.path.join(park_seat, "park.txt"), "w") as f:
            f.write("PARK\n")
        git(park_seat, "add", "park.txt")
        git(park_seat, "-c", "user.email=s@l", "-c", "user.name=s", "commit", "-q", "-m", "park work")
        # X is unmerged (Y has a commit not in X, and X is not in main beyond the cut)
        try:
            cmd_close_goal(argparse.Namespace(**{**vars(park_ns), "park": True, "force": True}))
            raise AssertionError("--park --force was ACCEPTED")
        except FlowError as e:
            assert e.code == E_PARK_FORCE, f"park+force exited {e.code}"
        assert os.path.isdir(park_integ) and os.path.isdir(park_seat), "park+force still removed trees"
        cmd_close_goal(argparse.Namespace(**{**vars(park_ns), "park": True}))
        assert not os.path.exists(park_integ), "park left integration worktree"
        assert not os.path.exists(park_seat), "park left seat worktree"
        assert branch_exists(park_repo, x_branch("parkgoal")), "park deleted X"
        assert branch_exists(park_repo, y_branch("parkgoal", "alpha")), "park deleted Y"
        try:
            delete_branch(park_repo, x_branch("parkgoal"), merged_into="main", force=False)
            raise AssertionError("delete_branch deleted an unmerged X")
        except FlowError as e:
            assert e.code == 4, f"unmerged delete_branch exited {e.code}"
        assert branch_exists(park_repo, x_branch("parkgoal")), "unmerged delete_branch still removed X"
        step("OK --park: worktrees gone, X and Y preserved; park+force refused; "
             "delete_branch refuses unmerged")

        print("\nselftest: PASS")
        return 0
    except AssertionError as e:
        print(f"\nselftest: FAIL — {e}", file=sys.stderr)
        return 1
    finally:
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"fixture kept at {tmp}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="worktree-flow.py",
        description="the PRODUCT worktree flow — .rbtv/worktrees/ root, branch scheme, "
                    "merge machinery (task 7.38; R14/R25/R26/R27)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # --ws hangs off each VERB, not off the program: argparse only accepts a global option before
    # the subcommand, so a program-level --ws makes `open-goal --ws X` a usage error at exactly
    # the moment someone is copying a command out of a runbook.
    def common(p, seat=False):
        p.add_argument("--ws", help="workspace root holding .rbtv/ (default: walk up from cwd)")
        p.add_argument("--repo", required=True, help="path inside the repo to branch from")
        p.add_argument("--goal", required=True, help="goal slug")
        if seat:
            p.add_argument("--seat", required=True)

    p = sub.add_parser("open-goal", help="create X + the goal integration worktree")
    common(p)
    p.add_argument("--base", default="main", help="what X is cut from (default: main)")
    p.set_defaults(fn=cmd_open_goal)

    p = sub.add_parser("open-seat", help="create Y from X + the seat's worktree")
    common(p, seat=True)
    p.set_defaults(fn=cmd_open_seat)

    p = sub.add_parser("merge-seat", help="merge Y->X in the integration worktree, then clean up")
    common(p, seat=True)
    p.add_argument("--force", action="store_true",
                   help="discard uncommitted/unmerged seat work during cleanup")
    p.set_defaults(fn=cmd_merge_seat)

    p = sub.add_parser("close-goal", help="remove the integration worktree + X (after X->main)")
    common(p)
    p.add_argument("--main", default="main", help="the branch X must have merged into")
    p.add_argument("--force", action="store_true", help="delete X even if unmerged")
    p.add_argument("--park", action="store_true",
                   help="remove worktrees only; preserve every goal/* branch")
    p.set_defaults(fn=cmd_close_goal)

    p = sub.add_parser("list", help="what is open under the worktrees root")
    p.add_argument("--ws", help="workspace root holding .rbtv/ (default: walk up from cwd)")
    p.add_argument("--repo", help="resolve each worktree's branch from git's own record")
    p.add_argument("--goal", help="filter to one goal")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("propose-merge",
                       help="propose X→main (never merges): PR or owner-bus")
    common(p)
    p.add_argument("--main", default="main", help="the branch X would merge into (default: main)")
    p.add_argument("--body-out", dest="body_out",
                   help="write the composed owner-facing body to PATH")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="compose and print argv; do not push, open a PR, or send on the bus")
    p.set_defaults(fn=cmd_propose_merge)

    p = sub.add_parser("selftest", help="one full cycle in a throwaway repo (R27 cleanup trace)")
    p.add_argument("--keep", action="store_true", help="keep the fixture for inspection")
    p.set_defaults(fn=cmd_selftest)

    a = ap.parse_args(argv)
    if not hasattr(a, "ws"):
        a.ws = None
    try:
        return a.fn(a)
    except FlowError as e:
        print(f"refused: {e}", file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
