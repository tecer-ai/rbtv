#!/usr/bin/env python3
"""worktree-flow.py — the PRODUCT worktree flow (task 7.38; settle ledger R14/R25/R26/R27).

Per-seat git worktrees under the CENTRAL `.rbtv/worktrees/` root — never inside a goal
folder, never beside the repo checkout (R27). One worktree per seat, named
`{repo}--{goal}--{seat}`; the goal's integration worktree is that same rule with the seat
name `integration`. The daemon derives a seat's bwrap grants from this naming and from
nothing a caller can pass (server/spawn/spawn.js resolveSeatGrants), so the naming is the
mechanism, not a label.

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

WHAT THIS TOOL IS NOT.  Branch discipline is enforced by PR REVIEW, not by the kernel
(R14: kernel-hard isolation would need per-seat clones, deliberately not taken). The
kernel half that DOES exist is the bwrap bind template — a seat cannot write main's
working tree or another seat's worktree, proven on disk by file-absence
(server/spawn/probes/probe-worktree-flow.js). Nothing here stops a seat that HOLDS a
worktree from committing whatever it likes to its OWN branch; only review does.
"""

import argparse
import os
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


def worktrees_root(ws):
    return os.path.join(ws, ".rbtv", "worktrees")


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


# ── verbs ────────────────────────────────────────────────────────────────────────────────

def cmd_open_goal(a):
    repo = repo_root(a.repo)
    name = os.path.basename(repo)
    ws = workspace_root(a.ws)
    x = x_branch(a.goal)
    path = os.path.join(worktrees_root(ws), worktree_name(name, a.goal, INTEGRATION_LEAF))
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
    x, y = x_branch(a.goal), y_branch(a.goal, a.seat)
    if not branch_exists(repo, x):
        raise FlowError(f"goal integration branch {x} does not exist — run open-goal first")
    if branch_exists(repo, y):
        raise FlowError(f"seat branch {y} already exists — a seat opens once per goal")
    path = os.path.join(worktrees_root(ws), worktree_name(name, a.goal, a.seat))
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
    integ = os.path.join(worktrees_root(ws), worktree_name(name, a.goal, INTEGRATION_LEAF))
    seat_wt = os.path.join(worktrees_root(ws), worktree_name(name, a.goal, a.seat))
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


def cmd_close_goal(a):
    """R27 — integration worktree + X go after X->main has merged. This tool never touches main."""
    repo = repo_root(a.repo)
    name = os.path.basename(repo)
    ws = workspace_root(a.ws)
    x = x_branch(a.goal)
    integ = os.path.join(worktrees_root(ws), worktree_name(name, a.goal, INTEGRATION_LEAF))

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
    root = worktrees_root(ws)
    if not os.path.isdir(root):
        print(f"{root} (absent — no worktrees open)")
        return 0
    repo = repo_root(a.repo) if a.repo else None
    known = worktree_paths(repo) if repo else {}
    for entry in sorted(os.listdir(root)):
        path = os.path.join(root, entry)
        if not os.path.isdir(path):
            continue
        if a.goal and f"--{a.goal}--" not in entry:
            continue
        branch = known.get(path, "?" if repo else "")
        print(f"{entry}\t{branch or '(detached/unregistered)'}\t{path}")
    return 0


# ── selftest ─────────────────────────────────────────────────────────────────────────────

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
        os.makedirs(repo)
        os.makedirs(os.path.join(ws, ".rbtv"))
        git(repo, "init", "-q", "-b", "main", ".")
        git(repo, "config", "user.email", "selftest@local")
        git(repo, "config", "user.name", "selftest")
        with open(os.path.join(repo, "source.txt"), "w") as f:
            f.write("ORIGINAL\n")
        git(repo, "add", "source.txt")
        git(repo, "commit", "-q", "-m", "base")
        step(f"fixture: repo {repo}, ws {ws}")

        ns = argparse.Namespace(repo=repo, ws=ws, goal="testgoal", base="main",
                                seat="alpha", force=False, main="main")
        cmd_open_goal(ns)
        integ = os.path.join(worktrees_root(ws), "repo--testgoal--integration")
        assert os.path.isdir(integ), "integration worktree absent"
        assert branch_exists(repo, x_branch("testgoal")), "X branch absent"
        step(f"OK open-goal: X={x_branch('testgoal')}, integration worktree on disk")

        cmd_open_seat(ns)
        seat_wt = os.path.join(worktrees_root(ws), "repo--testgoal--alpha")
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
        beta_wt = os.path.join(worktrees_root(ws), "repo--testgoal--beta")
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
        left = [e for e in os.listdir(worktrees_root(ws)) if "--testgoal--" in e]
        assert left == [], f"RESIDUE under the worktrees root: {left}"
        step("OK close-goal: integration worktree + X removed; worktrees root holds NO testgoal residue")

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
    p.set_defaults(fn=cmd_close_goal)

    p = sub.add_parser("list", help="what is open under the worktrees root")
    p.add_argument("--ws", help="workspace root holding .rbtv/ (default: walk up from cwd)")
    p.add_argument("--repo", help="resolve each worktree's branch from git's own record")
    p.add_argument("--goal", help="filter to one goal")
    p.set_defaults(fn=cmd_list)

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
