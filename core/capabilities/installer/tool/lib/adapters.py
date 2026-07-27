"""adapters.py — the CMP-12 per-harness exposure adapter matrix, in code.

ONE home for method -> harness realization (PRIN-11). Every other module of this
installer asks this table; none of them states a per-harness path of its own.

The rows transcribe `architecture/CMP-12-exposure-adapter-matrix.md` in the rbtv
system-definition registry. CON-2 bounds the BUILD to the three POC-proven
harnesses (claude, codex, opencode); the registry models five, and the two
unmodelled-here harnesses (qwen, kimi) are reference-only there, so building them
would be inventing a build commitment the registry does not make.

A method that a harness cannot realize NATIVELY carries a fallback; a method a
harness cannot realize AT ALL carries None and the installer refuses that row for
that harness with a named reason rather than guessing a location.
"""
from __future__ import annotations

from dataclasses import dataclass

# The canonical exposure-method vocabulary (decisions.md#d-exposure-method-canon).
# A method outside this set is a refusal, never a guess.
CANONICAL_METHODS = (
    "skill",
    "command",
    "rule",
    "hook",
    "sub-agent",
    "agents.md",
    "config",
)

HARNESSES = ("claude", "codex", "opencode")


@dataclass(frozen=True)
class Realization:
    """How one method lands on one harness.

    path_template: workspace-root-relative, `{name}` substituted with the part id.
    native:        True when the harness loads this location on its own.
    note:          the registry's own wording for a fallback, carried not paraphrased.
    """

    path_template: str
    native: bool
    note: str = ""


# method -> harness -> Realization | None  (None = the harness has no realization)
MATRIX: dict[str, dict[str, Realization | None]] = {
    "skill": {
        "claude": Realization(".claude/skills/{name}/SKILL.md", True),
        "codex": Realization(".agents/skills/{name}/SKILL.md", True),
        "opencode": Realization(".opencode/skills/{name}/SKILL.md", True),
    },
    "command": {
        "claude": Realization(".claude/commands/{name}.md", True),
        "codex": Realization(".codex/prompts/{name}.md", True),
        "opencode": Realization(".opencode/commands/{name}.md", True),
    },
    "rule": {
        "claude": Realization(".claude/rules/{name}.md", True),
        "codex": Realization(
            ".agents/behavior-rules/{name}.md",
            False,
            "no native behaviour rule; mirrored verbatim, and the AGENTS.md preamble "
            "must FORCE the read by naming the file",
        ),
        "opencode": Realization(
            ".agents/behavior-rules/{name}.md",
            False,
            "no separate rule type; reached via AGENTS.md/CLAUDE.md or an "
            "`instructions` pointer in opencode.json",
        ),
    },
    "agents.md": {
        "claude": Realization("CLAUDE.md", True),
        "codex": Realization("AGENTS.md", True, "32KiB cap"),
        "opencode": Realization("AGENTS.md", True),
    },
    "sub-agent": {
        "claude": Realization(".claude/agents/{name}.md", True),
        "codex": None,  # no confirmed-native definition file (task-file contract scope)
        "opencode": Realization(".opencode/agents/{name}.md", True),
    },
    "hook": {
        "claude": Realization(".claude/settings.json", True),
        "codex": Realization(
            ".codex/hooks.json", True, "transpiled from settings.json"
        ),
        "opencode": None,  # no hooks.json; a plugin is opencode's "hook"
    },
    "config": {
        # The seventh method: folder AND file name both vary per harness.
        # `.{harness}/config.json` is the schema's generic name, never a literal path.
        "claude": Realization(".claude/settings.json", True),
        "codex": Realization(".codex/config", True),
        "opencode": Realization("opencode.json", True),
    },
}


class UnknownMethod(Exception):
    """The exposure manifest named a method outside the canonical vocabulary."""


class NoRealization(Exception):
    """This harness has no realization for this method — refuse, never guess."""


def realize(method: str, harness: str, name: str) -> tuple[str, Realization]:
    """Resolve one exposure row to a workspace-root-relative target path.

    Raises rather than guessing: an unknown method and an unrealizable
    (method, harness) pair are both named refusals.
    """
    if method not in MATRIX:
        raise UnknownMethod(
            f"method {method!r} is not in the canonical vocabulary "
            f"({', '.join(CANONICAL_METHODS)}) — d-exposure-method-canon"
        )
    if harness not in MATRIX[method]:
        raise NoRealization(
            f"harness {harness!r} is not built (CON-2 bounds the build to "
            f"{', '.join(HARNESSES)})"
        )
    slot = MATRIX[method][harness]
    if slot is None:
        raise NoRealization(
            f"harness {harness!r} has no realization for method {method!r} — "
            f"CMP-12 records no native location and no fallback"
        )
    return slot.path_template.format(name=name), slot


def is_shared_file(method: str) -> bool:
    """True when the method's target is a MARKDOWN file shared with other content.

    Such a file is never overwritten whole: the installer edits a managed marker
    block inside it. Overwriting a workspace's CLAUDE.md/AGENTS.md would destroy
    hand-authored content that is not ours.

    `hook` and `config` are deliberately NOT here — see `is_structured_file`.
    """
    return method == "agents.md"


def is_structured_file(method: str) -> bool:
    """True when the method's target is a STRUCTURED config file (JSON-ish).

    These cannot take a marker block: `<!-- ... -->` is not valid JSON, so
    appending one to `.claude/settings.json` / `.codex/hooks.json` /
    `opencode.json` INVALIDATES the file — corrupting exactly the content the
    marker mechanism exists to protect. Measured, not reasoned: an early build of
    this installer did precisely that and produced an unparseable settings.json.

    Merging into them needs the harness-config schema, which the registry marks
    Phase-3/4 design output (`concepts/exposure-manifest.md`, CMP-12 § config) —
    so there is nothing to implement against yet. The installer therefore REFUSES
    these rows with a named reason rather than inventing a merge, per this
    capability's standing rule: refuse, never guess.
    """
    return method in ("hook", "config")
