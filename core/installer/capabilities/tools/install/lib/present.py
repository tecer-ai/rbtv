"""Shared terminal-presentation vocabulary: the `--type` value table, the
title line every command starts with, source-of-target labels, and plain-text
table rendering (with the narrow-terminal labeled-block fallback). One
authored place so list/search/show/add/remove/doctor never spell the same
vocabulary or table shape three ways.
"""
from __future__ import annotations

import os
import shutil

from .constants import CANONICAL_METHODS, HARNESSES
from .target import DISCOVER_FLAG

# --type / --exclude-type value -> short meaning, in the one order every
# help screen and error message shows them.
TYPE_MEANING = {
    "skill": "Ability an agent can invoke for a task.",
    "rule": "Standing instruction applied to an agent.",
    "command": "Explicit command an operator or agent can invoke.",
    "agent": "An agent's prompt and the units it uses.",
    "hook": "Action triggered by a tool event.",
    "mcp-server": "Server an agent tool connects to for extra tools.",
    "tool": "Runnable program exposed through a command shortcut.",
    "folder-instructions": "Text added to a folder's instructions file.",
}
assert set(TYPE_MEANING) == set(CANONICAL_METHODS)

HARNESS_MEANING = {"claude": "Claude Code", "codex": "Codex", "opencode": "OpenCode"}
assert set(HARNESS_MEANING) == set(HARNESSES)

GUIDANCE_MEANING = {
    "CLAUDE.md": "Claude Code instruction file",
    "AGENTS.md": "Codex/OpenCode instruction file",
}


def types_block(values=CANONICAL_METHODS, *, indent: str = "  ") -> str:
    """The accepted --type values with their meanings, one per line."""
    width = max(len(v) for v in values)
    return "\n".join(f"{indent}{v.ljust(width)}  {TYPE_MEANING[v]}" for v in values)


def harness_block(*, indent: str = "  ") -> str:
    return "\n".join(f"{indent}{h} ({HARNESS_MEANING[h]})" for h in HARNESSES)


def title(command: str) -> str:
    """The `RBTV install — <command>` line every screen opens with."""
    return f"RBTV install — {command}"


# The root command inventory, grouped by what a reader is trying to DO —
# argparse's own subparsers listing is one flat alphabetical block with no
# such grouping (and, separately, cannot hide a retired verb's help text via
# `help=SUPPRESS` on a subaction — https://bugs.python.org/issue22848-style
# gap). `root_help()` below is the one place that owns the full `-h` /
# bare-command screen text; argparse still owns every per-command `-h`.
COMMAND_GROUPS = (
    ("Discover", (
        ("status", "Show target, saved settings, and recorded selections."),
        ("list [NAME]", "Browse exact module, component, or item scope."),
        ("search WORDS", "Search catalog names and descriptions broadly."),
        ("show NAME", "Show description, included items, and installation "
                       "details."),
    )),
    ("Change this workspace", (
        ("configure", "Initialize or change receiving tools and guidance "
                       "settings."),
        ("add [NAME...]", "Select and install named or filtered items."),
        ("remove", "Remove selected installed items."),
        ("update", "Regenerate selected files from local RBTV source."),
    )),
    ("Check and guided use", (
        ("doctor", "Check target files and selected shared command "
                    "shortcuts."),
        ("interactive", "Choose items through a guided menu (asks "
                         "questions)."),
        ("selftest", "Run installer checks in isolated temporary "
                      "workspaces."),
    )),
)


def root_help() -> str:
    """The full `rbtv install -h` / bare-command screen (approved screen 01):
    commands grouped by intent, shared options, renamed/aliased forms, and a
    concrete next step — never argparse's flat, ungrouped default."""
    lines = [title("help"), ""]
    for heading, rows in COMMAND_GROUPS:
        width = max(len(name) for name, _ in rows)
        lines.append(heading)
        lines.extend(f"  {name.ljust(width)}  {desc}" for name, desc in rows)
        lines.append("")
    lines.append("Shared options: --target PATH  --json  -h, --help")
    lines.append("Non-interactive changes also accept --dry-run. "
                 "Only interactive asks questions.")
    lines.append("Target order: --target, then IGNITE_AGENT_HOME, "
                 "then current-folder discovery.")
    lines.append("Aliases: ls=list; li=list --installed; rm=remove.")
    lines.append("Renamed: set -> configure; dupe-artifacts -> update "
                 "guidance;")
    lines.append("         --kind -> --type; --exclude-kind -> "
                 "--exclude-type.")
    lines.append("")
    lines.append("Start: rbtv install status")
    lines.append("More:  rbtv install COMMAND -h")
    lines.append("Exit codes: 0 success; 1 refused or check failed; "
                 "2 invalid arguments.")
    return "\n".join(lines) + "\n"


def target_source_label(why: str | None) -> str:
    """`_why` (from target.resolve_target) -> the plain-English phrase the
    Target: line shows. One mapping — every printer reads THIS, not its own
    guess at the wording."""
    if why == DISCOVER_FLAG:
        return "explicit --target"
    if why == "IGNITE_AGENT_HOME":
        return "IGNITE_AGENT_HOME"
    return "discovered from current folder"


def terminal_width(default: int = 100) -> int:
    """COLUMNS first (the documented override, and what selftest sets to
    force the narrow-terminal path); the real terminal size otherwise."""
    raw = os.environ.get("COLUMNS")
    if raw:
        try:
            return max(10, int(raw))
        except ValueError:
            pass
    return shutil.get_terminal_size(fallback=(default, 24)).columns or default


def _shorten(text: str, budget: int) -> str:
    if budget <= 0:
        return ""
    if len(text) <= budget:
        return text
    if budget <= 1:
        return text[:budget]
    head = text[:budget - 1].rsplit(" ", 1)[0]
    return (head or text[:budget - 1]).rstrip(".,;:") + "…"


def render_table(headers: list[str], rows: list[list[str]], *,
                  width: int | None = None, paint=None) -> list[str]:
    """Aligned plain-text table. The LAST column (description) may shorten
    at a word boundary to fit; every other column — identifiers, type,
    state — is never truncated, wrapped, or split. When even the essential
    (non-last) columns cannot fit the width, falls back to one labeled block
    per row instead of truncating an identifier.

    `paint`, if given, is `(row_index, cell_text) -> display_text` applied to
    the LAST column only, AFTER width/shortening is computed from the plain
    `cell_text` — so ANSI colour escapes it adds never count toward column
    width or trigger the narrow-width fallback (they are invisible bytes to
    the terminal but real characters to `len()`)."""
    if not rows:
        return []
    width = terminal_width() if width is None else width
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    gap = 2
    essential = sum(widths[:-1]) + gap * (len(widths) - 1)
    if essential + gap > width and len(headers) > 1:
        return render_blocks(headers, rows, paint=paint)

    def fmt(row_index: int, row: list[str]) -> str:
        cells = []
        for i, cell in enumerate(row):
            cell = str(cell)
            if i == len(row) - 1:
                budget = width - essential - gap if len(headers) > 1 else width
                shown = _shorten(cell, budget) if budget < len(cell) else cell
                cells.append(paint(row_index, shown) if paint and row_index >= 0
                             else shown)
            else:
                cells.append(cell.ljust(widths[i]))
        return "  ".join(cells).rstrip()

    return [fmt(-1, headers)] + [fmt(i, row) for i, row in enumerate(rows)]


def render_blocks(headers: list[str], rows: list[list[str]], *,
                  paint=None) -> list[str]:
    """One item per labeled block — the narrow-terminal fallback. Never
    truncates a value; each row's fields sit on their own line instead."""
    lines: list[str] = []
    for row_index, row in enumerate(rows):
        for i, (label, value) in enumerate(zip(headers, row)):
            shown = paint(row_index, value) if paint and i == len(row) - 1 else value
            lines.append(f"{label}: {shown}")
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines
