"""Finding the install root when no --target was given."""
from __future__ import annotations

from pathlib import Path
import os

from discovery import Refuse

from .constants import AGENT_RECORD, STATE_REL


DISCOVER_STATE = "state file"

DISCOVER_RBTV = ".rbtv/ directory"

DISCOVER_CWD = "cwd (no .rbtv/ found above)"

DISCOVER_FLAG = "--target"


def is_user_home(cand: Path) -> bool:
    """Home's `.rbtv/` is the per-user runtime (`~/.rbtv/bin`), present on every
    machine that ran the installer — it never marks a installation by itself."""
    return cand == Path.home().resolve()


def discover_target(start: Path) -> tuple[Path, str]:
    """Resolve the install root from `start` upward. Returns (root, why)."""
    here = start.resolve()
    chain = [here, *here.parents]
    for cand in chain:
        if (cand / STATE_REL).is_file() or ((cand / "agent.md").is_file()
                                            and (cand / AGENT_RECORD).is_file()):
            return cand, DISCOVER_STATE
    for cand in chain:
        if (cand / ".rbtv").is_dir() and not is_user_home(cand):
            return cand, DISCOVER_RBTV
    return here, DISCOVER_CWD


def discover_installation(start: Path) -> tuple[Path, str]:
    """Find an installation for an agent verb, never an agent folder itself."""
    here = start.resolve()
    for cand in (here, *here.parents):
        if (cand / STATE_REL).is_file():
            return cand, DISCOVER_STATE
    for cand in (here, *here.parents):
        if (cand / ".rbtv").is_dir() and not is_user_home(cand):
            return cand, DISCOVER_RBTV
    return here, DISCOVER_CWD


def resolve_target(explicit: str | None, start: Path,
                   environ: dict[str, str] | None = None) -> tuple[Path, str]:
    """Resolve one target for every command: flag, agent home, installation."""
    if explicit is not None:
        return Path(explicit).expanduser().resolve(), DISCOVER_FLAG
    env = os.environ if environ is None else environ
    raw = env.get("RBTV_AGENT_HOME")
    if raw is not None:
        if not raw.strip():
            raise Refuse("agent-home-invalid",
                         "RBTV_AGENT_HOME is empty. Set it to an existing "
                         "agent directory or pass --target explicitly")
        home = Path(raw).expanduser()
        if not home.is_dir():
            raise Refuse(
                "agent-home-invalid",
                f"RBTV_AGENT_HOME={raw!r} is not an existing directory. "
                "Set it to the agent home or pass --target explicitly")
        return home.resolve(), "RBTV_AGENT_HOME"
    return discover_target(start)
