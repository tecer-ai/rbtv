"""m6 probe harness — the write COUNTER, and the scaffolding a case runs in.

The counted zero is the point. goal.md clause 7 and design.md § m6 both say the
same thing about an unroutable meeting: the write count before the answer is
**0**, "asserted as a count, not by inspecting a file that should not exist",
because an absent file is indistinguishable from a file that was written and
removed.

So the count here is taken at the WRITE ITSELF, from outside the code under
test: `io.open`/`builtins.open` in a writing mode, `os.replace`/`rename`/
`remove`/`mkdir`/`makedirs`, `shutil.copyfile`, and every `subprocess` launch.
Nothing in tools/ increments a counter of its own — a product that counts its
own writes would pass this probe by being wrong in two places at once.

Run output lives OUTSIDE the product tree (the RUNS_ROOT pattern m4 established:
generated evidence is not product).
"""

from __future__ import annotations

import builtins
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRODUCT = HERE.parent.parent          # .../workflows/transcript-summarizer
FIXTURES = HERE / "fixtures"
TOOLS = PRODUCT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

WRITE_MODES = set("wax+")


def default_runs_root() -> Path:
    """Where probe runs write. NOT inside the product tree."""
    override = os.environ.get("RUNS_ROOT")
    if override:
        return Path(override)
    return (PRODUCT / "../../../../../goals/transcript-summarizer-build/seats"
            / "per-meeting-summarizer-smith/outputs/m6/case-runs").resolve()


class WriteCount:
    """Counts real write operations, bucketed by which declared root they land in.

    `roots` maps a bucket name to a directory. A write outside every declared
    root is counted under 'elsewhere', so nothing escapes the tally by being
    unexpected.
    """

    def __init__(self, roots: dict[str, Path]):
        self.roots = {name: Path(path).resolve() for name, path in roots.items()}
        self.counts = {name: 0 for name in self.roots}
        self.counts["elsewhere"] = 0
        self.operations: list[dict] = []
        self.subprocesses: list[list[str]] = []
        self._patched: list[tuple] = []

    # -------------------------------------------------------------- tallying
    def _bucket(self, target) -> str:
        try:
            resolved = Path(target).resolve()
        except (TypeError, ValueError, OSError):
            return "elsewhere"
        for name, root in self.roots.items():
            if resolved == root or root in resolved.parents:
                return name
        return "elsewhere"

    def _record(self, operation: str, target) -> None:
        bucket = self._bucket(target)
        self.counts[bucket] += 1
        self.operations.append({"op": operation, "target": str(target), "bucket": bucket})

    # -------------------------------------------------------------- patching
    def _wrap_open(self, original):
        def opener(file, mode="r", *args, **kwargs):
            if WRITE_MODES & set(str(mode)):
                self._record("open", file)
            return original(file, mode, *args, **kwargs)
        return opener

    def _wrap_one(self, module, name, arg_index=0, label=None):
        original = getattr(module, name)

        def wrapped(*args, **kwargs):
            if len(args) > arg_index:
                self._record(label or name, args[arg_index])
            return original(*args, **kwargs)
        self._patched.append((module, name, original))
        setattr(module, name, wrapped)

    def _wrap_subprocess(self, name):
        original = getattr(subprocess, name)

        def wrapped(*args, **kwargs):
            self.subprocesses.append([str(part) for part in (args[0] if args else [])])
            return original(*args, **kwargs)
        self._patched.append((subprocess, name, original))
        setattr(subprocess, name, wrapped)

    def __enter__(self):
        for module in (io, builtins):
            original = module.open
            self._patched.append((module, "open", original))
            module.open = self._wrap_open(original)
        for name in ("replace", "rename", "remove", "unlink", "mkdir", "makedirs", "rmdir"):
            if hasattr(os, name):
                self._wrap_one(os, name)
        for name in ("copyfile", "copytree", "move", "rmtree"):
            if hasattr(shutil, name):
                self._wrap_one(shutil, name, arg_index=1 if name in ("copyfile", "copytree", "move") else 0)
        # Popen ONLY. `run`, `call`, `check_call` and `check_output` all funnel
        # through it, so wrapping them too reported one launch as two — measured,
        # and a wrong number in a report is worse than no number.
        self._wrap_subprocess("Popen")
        return self

    def __exit__(self, *exc):
        for module, name, original in reversed(self._patched):
            setattr(module, name, original)
        self._patched.clear()
        return False

    def report(self) -> dict:
        return {"counts": dict(self.counts), "subprocesses": len(self.subprocesses),
                "operations": self.operations}


def manifest(root: Path) -> dict:
    """sha256 per file under `root` — the corroborating check beside the count."""
    root = Path(root)
    if not root.is_dir():
        return {}
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            out[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def materialise(case: str, runs_root: Path) -> dict:
    """One case's own copy of every fixture, outside the product tree."""
    root = Path(runs_root) / case
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    # The config-module home sits where an installation keeps it, so the tools
    # find that installation's runtime folder beside it.
    config = root / ".rbtv" / "config" / "meeting-summarizer"
    shutil.copytree(FIXTURES / "config", config)
    shutil.copytree(FIXTURES / "scope", root / "work")
    shutil.copytree(FIXTURES / "checkout", root / "checkout")
    shutil.copytree(FIXTURES / "artifacts", root / "artifacts")
    binding = json.loads((root / "artifacts" / "binding.json").read_text(encoding="utf-8"))
    for entry in binding["artifacts"].values():
        entry["location"] = entry["location"].replace("FIXTURES/artifacts", str(root / "artifacts"))
    (root / "artifacts" / "binding.json").write_text(
        json.dumps(binding, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"root": root, "config": config, "work": root / "work",
            "checkout": root / "checkout", "binding": binding,
            "channel": root / "channel", "state": root / "state"}
