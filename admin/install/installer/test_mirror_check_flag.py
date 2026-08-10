"""Tests for `install.py --mirror --check` — the read-only mirror drift probe.

Two layers:

  1. The ARGUMENT GUARDS, which fire straight after parse_args and before any target
     resolution, so they run with argv alone and no workspace. The `--check` without
     `--mirror` guard is the load-bearing one: without it, a caller who types
     `install.py --check` expecting a dry run gets a FULL INSTALL.
  2. The end-to-end probe over a scratch workspace: drift must reach the EXIT CODE
     (the 2026-07-26 defect was a mirror that printed "stale" and exited 0), the probe
     must never repair what it reports, and a refresh must clear it.

Stdlib + pytest only. No network / clock / randomness.
"""
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
_ADMIN_INSTALL = _HERE.parents[1]          # admin/install
RBTV_ROOT = _HERE.parents[3]               # 3-resources/tools/rbtv

# Make `import installer.*` resolve regardless of pytest CWD (cli.py uses relative imports,
# so it must load as part of the `installer` package — admin/install is its parent).
if str(_ADMIN_INSTALL) not in sys.path:
    sys.path.insert(0, str(_ADMIN_INSTALL))

from installer.cli import main  # noqa: E402

_PACKAGES = ["codex-cli", "kimi-code-cli", "opencode"]


def _run(argv):
    """Run the installer CLI, capturing output. Returns (exit_code, stdout+stderr)."""
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, str):        # SystemExit("message") — argparse-style bail
            err.write(code)
            code = 1
    return (code if code is not None else 0), out.getvalue() + err.getvalue()


# --- argument guards (no workspace needed) ------------------------------------------------

def test_check_without_mirror_is_refused():
    """Without this guard `install.py --check` would run a FULL INSTALL — the exact
    opposite of what the flag's name promises."""
    code, text = _run(["--check", "--target", str(RBTV_ROOT)])
    assert code != 0
    assert "--check applies only with --mirror" in text


def test_check_with_uninstall_is_refused_with_exit_2():
    """One writes nothing, the other deletes every artifact — no combined meaning.
    Exit 2 matches the mirror driver's own rejection of the same pair."""
    code, text = _run(["--mirror", "--check", "--uninstall", "--target", str(RBTV_ROOT)])
    assert code == 2
    assert "mutually exclusive" in text


# --- end-to-end probe over a scratch workspace --------------------------------------------

@pytest.fixture
def workspace(tmp_path):
    """A minimal installed workspace: the .claude/ inputs the mirror renders from,
    plus an rbtv.json electing the three mirrorable CLI packages."""
    (tmp_path / ".claude" / "rules").mkdir(parents=True)
    (tmp_path / ".claude" / "rules" / "r1.md").write_text("# rule one\nbody\n", encoding="utf-8")
    (tmp_path / ".claude" / "skills" / "s1").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "s1" / "SKILL.md").write_text(
        "---\nname: s1\ndescription: demo skill\n---\nbody\n", encoding="utf-8"
    )
    (tmp_path / "CLAUDE.md").write_text("# root guidance\n", encoding="utf-8")
    (tmp_path / "rbtv.json").write_text(
        json.dumps({"rbtv_version": "0.0.0", "modules": [], "installed_files": [],
                    "model_packages": _PACKAGES}),
        encoding="utf-8",
    )
    _run(["--mirror", "--non-interactive", "--target", str(tmp_path)])
    return tmp_path


def test_check_passes_on_a_freshly_rendered_workspace(workspace):
    code, text = _run(["--mirror", "--check", "--target", str(workspace)])
    assert code == 0
    assert "is in sync" in text


def test_edited_source_makes_check_exit_1_and_name_the_file(workspace):
    """The 2026-07-26 defect: content drift was printed but never reached the exit code."""
    (workspace / ".claude" / "skills" / "s1" / "SKILL.md").write_text(
        "---\nname: s1\ndescription: demo skill\n---\nEDITED\n", encoding="utf-8"
    )
    code, text = _run(["--mirror", "--check", "--target", str(workspace)])
    assert code == 1
    assert "OUT OF SYNC" in text
    assert ".agents/skills/s1/SKILL.md" in text


def test_check_repairs_nothing(workspace):
    """A probe that silently fixed what it measured would make drift unobservable."""
    mirrored = workspace / ".agents" / "skills" / "s1" / "SKILL.md"
    before = mirrored.read_bytes()
    state_before = (workspace / "rbtv.json").read_bytes()

    (workspace / ".claude" / "skills" / "s1" / "SKILL.md").write_text(
        "---\nname: s1\ndescription: demo skill\n---\nEDITED\n", encoding="utf-8"
    )
    assert _run(["--mirror", "--check", "--target", str(workspace)])[0] == 1

    assert mirrored.read_bytes() == before, "check mode must not refresh the mirror"
    assert (workspace / "rbtv.json").read_bytes() == state_before, \
        "check mode must not rewrite the model_mirror state block"


def test_refresh_clears_the_drift(workspace):
    """The signal has to be actionable — the command the failure message names must work."""
    # A .claude/ source edit — a CLAUDE.md edit stales nothing since the guidance
    # leg was retired (d-hard-guard-retire-model-mirror, 2026-08-10).
    (workspace / ".claude" / "rules" / "r1.md").write_text(
        "# rule one\nEDITED\n", encoding="utf-8"
    )
    assert _run(["--mirror", "--check", "--target", str(workspace)])[0] == 1

    assert _run(["--mirror", "--non-interactive", "--target", str(workspace)])[0] == 0

    assert _run(["--mirror", "--check", "--target", str(workspace)])[0] == 0
