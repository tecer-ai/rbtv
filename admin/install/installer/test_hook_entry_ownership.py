"""Tests for `sync_hook_entry()` — foreign PostToolUse entries must survive the rewrite.

`sync_hook_entry()` rebuilds `hooks.PostToolUse` as `[every entry it does not own] +
[one fresh rbtv entry]`. Everything it does NOT own must come through byte-for-byte,
ownership markers included: a sibling installer (sb-os) identifies its own managed
entry by its `__sb__` key, so an entry that comes back without its marker is an entry
its owner no longer recognizes — and the next sibling install ADDS A DUPLICATE rather
than replacing it. The failure is silent and lands at someone else's install.

Ownership is decided by `_is_rbtv_hook_entry()`. It matches on the `__rbtv__` sentinel
OR — as a harness-robust fallback — on the intrinsic rbtv script path appearing in a
command. The fallback used to outrank an explicit FOREIGN ownership marker, so a
foreign entry that merely wrapped the rbtv script was deleted whole.

Stdlib + pytest only. No network / clock / randomness. Every case runs against a
throwaway workspace under tmp_path — `install.py` is never invoked.
"""
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ADMIN_INSTALL = _HERE.parents[1]          # admin/install

# Make `import installer.*` resolve regardless of pytest CWD.
if str(_ADMIN_INSTALL) not in sys.path:
    sys.path.insert(0, str(_ADMIN_INSTALL))

from installer.orchestration import (  # noqa: E402
    _HOOK_COMMAND_SIGNATURE,
    _HOOK_SENTINEL,
    sync_hook_entry,
)

RBTV_RELATIVE = Path("3-resources/tools/rbtv")


def _write_settings(target_root: Path, settings: dict) -> Path:
    path = target_root / ".claude" / "settings.local.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return path


def _post_tool_use(path: Path) -> list:
    return json.loads(path.read_text(encoding="utf-8"))["hooks"]["PostToolUse"]


def _foreign_entry(command: str) -> dict:
    """A hook entry owned by another component, carrying ITS ownership marker."""
    return {
        "__someothercomponent__": "other:its-marker",
        "someOtherUnknownKey": {"nested": [1, 2]},
        "matcher": "Read",
        "hooks": [{"type": "command", "command": command}],
    }


def test_foreign_entry_wrapping_the_rbtv_script_survives(tmp_path):
    """THE DISCRIMINATOR — fails before the ownership fix, passes after.

    A foreign entry claimed by its own `__*__` marker that happens to invoke the rbtv
    context-monitor script (a wrapper, a re-use with extra args) used to match the
    command-signature fallback and be DELETED — marker, matcher, command and all.
    Ownership must outrank the signature.
    """
    entry = _foreign_entry(
        f"python /opt/other/wrap.py {_HOOK_COMMAND_SIGNATURE} --their-flag"
    )
    path = _write_settings(tmp_path, {"hooks": {"PostToolUse": [json.loads(json.dumps(entry))]}})

    changed, msg = sync_hook_entry(tmp_path, RBTV_RELATIVE)
    assert changed, msg

    after = _post_tool_use(path)
    survivors = [e for e in after if e.get("__someothercomponent__")]
    assert survivors, (
        "foreign entry was DELETED by the rbtv hook sync — its owner's next install "
        f"will re-add it as a duplicate. PostToolUse after sync: {after}"
    )
    assert survivors[0] == entry, "foreign entry did not survive byte-for-byte"


def test_foreign_entry_keeps_marker_and_unknown_keys(tmp_path):
    """The baseline the sibling installers depend on: pass-through, unchanged."""
    entry = _foreign_entry("python /opt/other/component-hook.py")
    stale_rbtv = {
        "__rbtv__": _HOOK_SENTINEL,
        "matcher": "",
        "hooks": [{"type": "command", "command": f"STALE {_HOOK_COMMAND_SIGNATURE}"}],
    }
    path = _write_settings(
        tmp_path,
        {
            "permissions": {"allow": ["Bash(ls:*)"]},
            "hooks": {"PostToolUse": [json.loads(json.dumps(entry)), stale_rbtv]},
        },
    )

    changed, msg = sync_hook_entry(tmp_path, RBTV_RELATIVE)
    assert changed, msg

    after = _post_tool_use(path)
    assert after[0] == entry, "foreign entry must pass through byte-for-byte"
    assert sum(1 for e in after if e.get("__rbtv__") == _HOOK_SENTINEL) == 1
    # Unrelated top-level settings keys are untouched.
    settings = json.loads(path.read_text(encoding="utf-8"))
    assert settings["permissions"] == {"allow": ["Bash(ls:*)"]}


def test_stripped_rbtv_entry_is_still_re_adopted(tmp_path):
    """The fallback the ownership rule must NOT cost us.

    Claude Code owns settings.local.json at runtime and may drop the injected
    `__rbtv__` key on a re-serialize. Such an entry carries NO ownership marker, so
    the signature fallback still recognizes it and REPLACES it — never duplicates.
    """
    stripped = {
        "matcher": "",
        "hooks": [{"type": "command", "command": f"python OLD/{_HOOK_COMMAND_SIGNATURE}"}],
    }
    path = _write_settings(tmp_path, {"hooks": {"PostToolUse": [stripped]}})

    changed, msg = sync_hook_entry(tmp_path, RBTV_RELATIVE)
    assert changed, msg

    after = _post_tool_use(path)
    assert len(after) == 1, f"stripped rbtv entry was duplicated, not replaced: {after}"
    assert after[0]["__rbtv__"] == _HOOK_SENTINEL


def test_real_world_sb_entry_survives_both_events(tmp_path):
    """Regression guard on the reported shape: sb-os's own two managed entries.

    `PreToolUse` is not rbtv's to touch at all; `PostToolUse`'s sb entry is foreign.
    Both must come back carrying `__sb__`.
    """
    sb_command = (
        "python -c \"...3-resources/tools/sb-os/para/workflows/"
        "sb-inject-context/resolve_context.py...\""
    )
    pre = {
        "__sb__": "sb:context-injection",
        "matcher": "Skill",
        "hooks": [{"type": "command", "command": sb_command}],
    }
    post = {
        "__sb__": "sb:context-injection",
        "matcher": "Read",
        "hooks": [{"type": "command", "command": sb_command}],
    }
    path = _write_settings(
        tmp_path,
        {
            "hooks": {
                "PreToolUse": [json.loads(json.dumps(pre))],
                "PostToolUse": [json.loads(json.dumps(post))],
            }
        },
    )

    changed, msg = sync_hook_entry(tmp_path, RBTV_RELATIVE)
    assert changed, msg

    settings = json.loads(path.read_text(encoding="utf-8"))
    assert settings["hooks"]["PreToolUse"] == [pre]
    assert settings["hooks"]["PostToolUse"][0] == post
