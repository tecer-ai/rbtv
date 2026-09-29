"""Finding the install root when no --target was given."""
from __future__ import annotations

from pathlib import Path
import os

from discovery import Refuse

from .constants import STATE_REL


DISCOVER_STATE = "state file"

DISCOVER_RBTV = ".rbtv/ directory"

DISCOVER_CWD = "cwd (no .rbtv/ found above)"

DISCOVER_FLAG = "--target"


def is_user_home(cand: Path) -> bool:
    """Home's `.rbtv/` is the per-user runtime (`~/.rbtv/bin`), present on every
    machine that ran the installer — it never marks a workspace by itself."""
    return cand == Path.home().resolve()


def discover_target(start: Path) -> tuple[Path, str]:
    """Resolve the install root from `start` upward. Returns (root, why)."""
    here = start.resolve()
    chain = [here, *here.parents]
    for cand in chain:
        if (cand / STATE_REL).is_file():
            return cand, DISCOVER_STATE
    for cand in chain:
        if (cand / ".rbtv").is_dir() and not is_user_home(cand):
            return cand, DISCOVER_RBTV
    return here, DISCOVER_CWD


def resolve_target(explicit: str | None, start: Path,
                   environ: dict[str, str] | None = None) -> tuple[Path, str]:
    """Resolve one target for every command: flag, agent home, workspace."""
    if explicit is not None:
        return Path(explicit).expanduser().resolve(), DISCOVER_FLAG
    env = os.environ if environ is None else environ
    raw = env.get("IGNITE_AGENT_HOME")
    if raw is not None:
        if not raw.strip():
            raise Refuse("agent-home-invalid",
                         "IGNITE_AGENT_HOME is empty. Set it to an existing "
                         "agent directory or pass --target explicitly")
        home = Path(raw).expanduser()
        if not home.is_dir():
            raise Refuse(
                "agent-home-invalid",
                f"IGNITE_AGENT_HOME={raw!r} is not an existing directory. "
                "Set it to the agent home or pass --target explicitly")
        return home.resolve(), "IGNITE_AGENT_HOME"
    return discover_target(start)
