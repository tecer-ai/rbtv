"""m7 probe harness — scratch remotes, scratch clones, and the fixture summarizer.

NOTHING here touches a live destination. Every repository a probe sees is created
by this file under a scratch root OUTSIDE the workspace (`/tmp` by default, or
`$M7_SCRATCH_ROOT`), and is deleted with it. That is the point: a race, a rejected
push and an owner-side commit can only be staged safely where destroying the tree
costs nothing.

The two regimes are built the same way and published differently, which is what
makes "prove it in both" a real check rather than a relabelled one:

  alpha-works      regime "git"    — a clone this workflow owns
  wellbeing-vault  regime "vault"  — stands in for a SHARED working tree of which
                                     the destination is one subtree
  gamma-corp       regime "git"    — the delegated-placement case
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRODUCT = HERE.parent.parent
TOOLS = PRODUCT / "tools"
FIXTURES = HERE / "fixtures"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

CONFIG_ROOT = FIXTURES / "config"
JOBS = FIXTURES / "jobs"

# Which fixture repo stands for which regime. Read from the fixture config so the
# harness cannot drift from what the layer is actually told.
REGIME_REPO = {"git": "alpha-works", "vault": "wellbeing-vault"}

GIT_ENV = {
    "GIT_AUTHOR_NAME": "m7 probe", "GIT_AUTHOR_EMAIL": "probe@fixture.invalid",
    "GIT_COMMITTER_NAME": "m7 probe", "GIT_COMMITTER_EMAIL": "probe@fixture.invalid",
    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
}


def git(cwd, *args, check=True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV})
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} in {cwd}: {proc.stderr or proc.stdout}")
    return proc


def scratch_root() -> Path:
    base = os.environ.get("M7_SCRATCH_ROOT")
    if base:
        root = Path(base)
        root.mkdir(parents=True, exist_ok=True)
        return root
    return Path(tempfile.mkdtemp(prefix="m7-publish-"))


class Scratch:
    """One probe's whole world: a scratch remote and clone per repo, plus state."""

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else scratch_root()
        self.remotes = self.root / "remotes"
        self.checkouts = self.root / "checkouts"
        self.state = self.root / "state"
        for path in (self.remotes, self.checkouts, self.state):
            path.mkdir(parents=True, exist_ok=True)
        self._built: dict[str, Path] = {}

    # -------------------------------------------------------------- repos
    def repo(self, name: str) -> Path:
        """A bare scratch remote plus a clone of it, seeded with one commit."""
        if name in self._built:
            return self._built[name]
        bare = self.remotes / f"{name}.git"
        subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(bare)],
                       capture_output=True, check=True, env={**os.environ, **GIT_ENV})
        checkout = self.checkouts / name
        subprocess.run(["git", "clone", str(bare), str(checkout)],
                       capture_output=True, check=True, env={**os.environ, **GIT_ENV})
        git(checkout, "config", "user.name", "m7 probe")
        git(checkout, "config", "user.email", "probe@fixture.invalid")
        git(checkout, "symbolic-ref", "HEAD", "refs/heads/main")
        (checkout / "README.md").write_text(f"# {name}\n\nscratch fixture repository\n",
                                            encoding="utf-8")
        git(checkout, "add", "--", "README.md")
        git(checkout, "commit", "-m", "seed")
        git(checkout, "push", "origin", "HEAD:main")
        git(checkout, "fetch", "origin", "main")
        self._built[name] = checkout
        return checkout

    def owner_clone(self, name: str) -> Path:
        """A SECOND clone of the same remote — the owner's own working copy.

        Criterion 7 is about the owner's text surviving. It is staged from here,
        so the owner's commit reaches the remote by exactly the route a real
        owner-side commit takes, and never through the layer under test.
        """
        clone = self.root / "owner" / name
        if not clone.exists():
            clone.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", str(self.remotes / f"{name}.git"), str(clone)],
                           capture_output=True, check=True, env={**os.environ, **GIT_ENV})
            git(clone, "config", "user.name", "Henrique")
            git(clone, "config", "user.email", "owner@fixture.invalid")
        return clone

    def owner_commits(self, name: str, path: str, text: str) -> str:
        """The owner writes a line of their own and pushes it. Returns the line."""
        clone = self.owner_clone(name)
        git(clone, "fetch", "origin", "main")
        git(clone, "merge", "--ff-only", "FETCH_HEAD", check=False)
        handle = clone / path
        handle.parent.mkdir(parents=True, exist_ok=True)
        existing = handle.read_text(encoding="utf-8") if handle.exists() else ""
        handle.write_text(existing + text, encoding="utf-8")
        git(clone, "add", "--", path)
        git(clone, "commit", "-m", "owner edit")
        git(clone, "push", "origin", "HEAD:main")
        return text

    def remote_text(self, name: str, path: str) -> str:
        """What the REMOTE actually holds — read from the bare repository itself,
        never from a working copy that might merely not have noticed a loss."""
        bare = self.remotes / f"{name}.git"
        proc = subprocess.run(["git", "-C", str(bare), "show", f"main:{path}"],
                              capture_output=True, text=True, env={**os.environ, **GIT_ENV})
        return proc.stdout if proc.returncode == 0 else ""

    def unreachable(self, name: str) -> None:
        """Point the clone's remote at nothing. The push cannot land."""
        git(self.checkouts / name, "remote", "set-url", "origin",
            str(self.root / "remotes" / "no-such-remote.git"))

    def clean(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


# -------------------------------------------------------------- the inputs
def job(name: str) -> dict:
    return json.loads((JOBS / f"{name}.json").read_text(encoding="utf-8"))


def transcripts(*sources: str) -> dict:
    return {source: f"# transcript ({source})\n\nfixture transcript body for {source}.\n"
            for source in (sources or ("meet",))}


class Summarizer:
    """The fixture summary writer, and a SPY on when it was called.

    `calls` records the pre-check decision the layer had already reached at the
    moment it asked for text. That is what makes the pre-check's ORDERING
    checkable: a layer that summarized first would call this with no decision in
    hand at all.
    """

    def __init__(self, text: str, path: str | None = None):
        self.text = text
        self.path = path
        self.calls: list[dict] = []

    def __call__(self, request: dict) -> dict:
        self.calls.append({"disposition": request["decision"]["disposition"],
                           "discriminator": request["discriminator"]})
        answer = {"text": self.text}
        if self.path:
            answer["path"] = self.path
        return answer


class Bus:
    """Collects what the layer posted, in order."""

    def __init__(self):
        self.posted: list[dict] = []

    def __call__(self, payload: dict) -> dict:
        self.posted.append(payload)
        return {"ok": True}

    def of_kind(self, kind: str) -> list[dict]:
        return [row for row in self.posted if row.get("kind") == kind]
