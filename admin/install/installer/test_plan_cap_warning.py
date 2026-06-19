"""Tests for the installer plan-size CLOBBER WARNING (D14 — multi-model harness).

Covers the pure clobber detector (orchestration.clobbered_variants / read_variant_windows)
over the REAL claude-code-native manifest, and the interactive plan-size flow
(cli._resolve_model_plan_caps) driven with fed menu answers against a scratch target —
asserting a sub-largest cap WARNS (naming the shrunk variant) while "no cap" and an
at-ceiling cap do not, and the chosen cap is still written either way (advisory, never blocks).

Stdlib + pytest only. No network / clock / randomness.
"""
import builtins
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_HERE = Path(__file__).resolve()
_ADMIN_INSTALL = _HERE.parents[1]          # admin/install
RBTV_ROOT = _HERE.parents[3]               # 3-resources/tools/rbtv

# Make `import installer.*` resolve regardless of pytest CWD (cli.py uses relative imports,
# so it must load as part of the `installer` package — admin/install is its parent).
if str(_ADMIN_INSTALL) not in sys.path:
    sys.path.insert(0, str(_ADMIN_INSTALL))

from installer.cli import _resolve_model_plan_caps  # noqa: E402
from installer.orchestration import (  # noqa: E402
    clobbered_variants,
    read_model_plan_caps,
    read_variant_windows,
)

PKG = "claude-code-native"
PLANS_REL = ".user/config/orchestration/model-plans.yaml"


# --- pure detector over the REAL claude-code-native manifest ------------------------------

def test_read_variant_windows_real_manifest():
    w = dict(read_variant_windows(RBTV_ROOT, PKG))
    assert w.get("opus") == 1_000_000
    assert w.get("sonnet") == 200_000
    assert w.get("haiku") == 200_000


def test_no_cap_clobbers_nothing():
    assert clobbered_variants(RBTV_ROOT, PKG, None) == []


def test_cap_at_ceiling_clobbers_nothing():
    assert clobbered_variants(RBTV_ROOT, PKG, 1_000_000) == []


def test_sub_largest_cap_clobbers_only_the_bigger_variant():
    # 200K caps opus's 1M window; the native-200K sonnet/haiku are untouched.
    assert clobbered_variants(RBTV_ROOT, PKG, 200_000) == [("opus", 1_000_000)]


def test_deep_cap_clobbers_every_variant():
    assert dict(clobbered_variants(RBTV_ROOT, PKG, 128_000)) == {
        "opus": 1_000_000,
        "sonnet": 200_000,
        "haiku": 200_000,
    }


# --- interactive flow: the REAL _resolve_model_plan_caps, fed input, scratch target -------

def _drive(tmp_path: Path, *answers: str):
    """Run the REAL _resolve_model_plan_caps interactively with fed menu answers against a
    scratch target. Returns (stdout, stderr, caps_dict). Patching builtins.input supplies the
    keystroke the test can't type into a non-tty; the warning logic runs for real on the real
    manifest, and the cap is written to the scratch target (never the live vault)."""
    out, err = io.StringIO(), io.StringIO()
    fed = iter(answers)
    saved_input = builtins.input
    builtins.input = lambda prompt="": next(fed)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            _resolve_model_plan_caps(
                rbtv_root=RBTV_ROOT,
                target_root=tmp_path,
                model_plans_file=PLANS_REL,
                installed_packages=[PKG],
                non_interactive=False,
                used_modules_flag=False,
            )
    finally:
        builtins.input = saved_input
    caps = read_model_plan_caps(tmp_path / PLANS_REL)
    return out.getvalue(), err.getvalue(), caps


# Menu for claude-code-native (ceiling 1M): 1)No cap 2)128K 3)200K 4)256K 5)512K 6)1M

def test_interactive_sub_largest_cap_warns_and_still_writes(tmp_path):
    out, err, caps = _drive(tmp_path, "3")  # pick 200K
    assert "WARNING" in err
    assert "opus" in err
    assert "200K" in err
    assert caps == {PKG: 200_000}  # advisory: the cap is STILL written


def test_interactive_no_cap_does_not_warn(tmp_path):
    out, err, caps = _drive(tmp_path, "1")  # pick "No cap"
    assert "WARNING" not in err
    assert caps == {}  # no integer cap written


def test_interactive_cap_at_ceiling_does_not_warn(tmp_path):
    out, err, caps = _drive(tmp_path, "6")  # pick 1M (= ceiling)
    assert "WARNING" not in err
    assert caps == {PKG: 1_000_000}
