"""Shared terminal-presentation vocabulary: the `--type` value table, the
title line every command starts with, source-of-target labels, and plain-text
table rendering (with the narrow-terminal labeled-block fallback). One
authored place so list/search/show/add/remove/doctor never spell the same
vocabulary or table shape three ways.
"""
from __future__ import annotations

import os
import re
import shutil
import textwrap

from .constants import CATALOG_TYPES, HARNESSES
from .target import DISCOVER_FLAG

# --type / --exclude-type value -> short meaning, in the one order every
# help screen and error message shows them.
TYPE_MEANING = {
    "skill": "Ability an agent can invoke for a task.",
    "rule": "Standing instruction applied to an agent.",
    "command": "Explicit command an operator or agent can invoke.",
    "agent": "Agent a component ships; an rbtv agent or a harness-native sub-agent.",
    "hook": "Action triggered by a tool event.",
    "mcp-server": "Server an agent tool connects to for extra tools.",
    "tool": "Runnable program exposed through a command shortcut.",
    "folder-instructions": "Text added to a folder's instructions file.",
    "pack": "A named list of files a component declares.",
}
assert set(TYPE_MEANING) == set(CATALOG_TYPES)

HARNESS_MEANING = {"claude": "Claude Code", "codex": "Codex", "opencode": "OpenCode"}
assert set(HARNESS_MEANING) == set(HARNESSES)

GUIDANCE_MEANING = {
    "CLAUDE.md": "Claude Code instruction file",
    "AGENTS.md": "Codex/OpenCode instruction file",
}


def types_block(values=CATALOG_TYPES, *, indent: str = "  ") -> str:
    """The accepted --type values with their meanings, one per line."""
    width = max(len(v) for v in values)
    return "\n".join(f"{indent}{v.ljust(width)}  {TYPE_MEANING[v]}" for v in values)


def harness_block(*, indent: str = "  ") -> str:
    return "\n".join(f"{indent}{h} ({HARNESS_MEANING[h]})" for h in HARNESSES)


def title(command: str) -> str:
    """The `rbtv — <command>` line every screen opens with."""
    return f"rbtv — {command}"


# The root command inventory, grouped by what a reader is trying to DO.
# `root_help()` owns the full root `-h` / bare-command screen; argparse
# owns every per-command `-h`.
COMMAND_GROUPS = (
    ("Discover", (
        ("status", "Show target, saved settings, and recorded selections."),
        ("list [NAME]", "Browse exact module, component, or file scope."),
        ("search WORDS", "Search catalog names and descriptions broadly."),
        ("show NAME", "Show description, included files, and installation details."),
    )),
    ("Change this installation", (
        ("configure", "Initialize or change receiving tools and guidance settings."),
        ("add [NAME...]", "Add named or filtered files, or turn a pack on."),
        ("remove [NAME...]", "Remove installed files, or turn a pack off."),
        ("update SCOPE", "Make the folder match the file. The scope is required."),
    )),
    ("Agents", (
        ("agent VERB", "Act on one agent instead of this installation: create it, change its\n"
                       "                files, harness, model or effort, or list the agents. See: rbtv agent -h"),
    )),
    ("Check and guided use", (
        ("doctor", "Check generated files and selected command shortcuts."),
        ("interactive", "Choose files through a guided menu (asks questions)."),
        ("selftest", "Run checks in isolated temporary installations."),
    )),
)


def root_help() -> str:
    """The full `rbtv -h` / bare-command screen (approved screen 100)."""
    lines = [title("help"), ""]
    for heading, rows in COMMAND_GROUPS:
        width = max(max(len(name) for name, _ in rows), 12 if heading == "Agents" else 0)
        lines.append(heading)
        lines.extend(f"  {name.ljust(width)}  {desc}" for name, desc in rows)
        lines.append("")
    lines.append("Shared options: --target PATH  --json  -h, --help  --version")
    lines.append("Non-interactive changes also accept --dry-run and --details.")
    lines.append("Only interactive asks questions.")
    lines.append("Target order: --target, then RBTV_AGENT_HOME, then discovery from the current folder.")
    lines.append("Aliases: ls=list; li=list --installed; rm=remove.")
    lines.append("A file id is module/component#name. A pack is named only with --pack.")
    lines.append("A bare name never resolves to a pack.")
    lines.append("With no command, this page is printed.")
    lines.append("")
    lines.append("Start: rbtv status")
    lines.append("More:  rbtv COMMAND -h")
    lines.append("Exit codes: 0 success; 1 refused or check failed; 2 invalid arguments.")
    return "\n".join(lines) + "\n"


def target_source_label(why: str | None) -> str:
    """`_why` (from target.resolve_target) -> the plain-English phrase the
    Target: line shows. One mapping — every printer reads THIS, not its own
    guess at the wording."""
    if why == DISCOVER_FLAG:
        return "explicit --target"
    if why == "RBTV_AGENT_HOME":
        return "RBTV_AGENT_HOME"
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


class Whole(str):
    """A value printed on one line and never wrapped — a path or command
    that may contain spaces and must stay copyable."""


# A `backticked span`, or an `rbtv …` command introduced by a colon
# ("Example: rbtv …", "run: rbtv …") and running to the end of its
# sentence: each is kept on one line so it stays copyable. A command named
# mid-sentence in prose is ordinary words.
_UNBROKEN = re.compile(r"`[^`]*`|(?<=: )rbtv [^`\n]*?(?=\.\s|\.?$|;\s)")


def wrap(text: str, *, indent: str = "", hang: str | None = None,
         width: int | None = None) -> list[str]:
    """Prose word-wrapped to the terminal, one paragraph per input line.
    Never splits a word, ID or path, an `rbtv …` command, or a backticked
    span; a `Whole` value is never wrapped at all."""
    hang = indent if hang is None else hang
    if isinstance(text, Whole):
        return [indent + text]
    width = terminal_width() if width is None else width
    lines: list[str] = []
    for n, para in enumerate(text.split("\n")):
        kept = _UNBROKEN.sub(lambda m: m.group(0).replace(" ", "\0"), para)
        lines.extend(line.replace("\0", " ") for line in textwrap.wrap(
            kept, width=max(width, len(hang) + 20),
            initial_indent=indent if n == 0 else hang, subsequent_indent=hang,
            break_long_words=False, break_on_hyphens=False))
    return lines or [indent.rstrip()]


def fields(rows: list[tuple[str, str]], *, indent: str = "",
           width: int | None = None) -> list[str]:
    """`Label:  value` rows with every value aligned after the longest label
    and wrapped under itself. When fewer than 20 columns would remain for
    the values, each value moves to its own indented line under its label."""
    if not rows:
        return []
    width = terminal_width() if width is None else width
    label_w = max(len(label) for label, _ in rows) + 1
    lines: list[str] = []
    if width - len(indent) - label_w - 2 < 20:
        for label, value in rows:
            lines.append(f"{indent}{label}:")
            lines.extend(wrap(value, indent=indent + "  ", width=width))
        return lines
    hang = indent + " " * (label_w + 2)
    for label, value in rows:
        head = f"{indent}{(label + ':').ljust(label_w)}  "
        if isinstance(value, Whole) and len(head) + len(value) > width:
            lines.extend((head.rstrip(), indent + "  " + value))
        else:
            lines.extend(wrap(value, indent=head, hang=hang, width=width))
    return lines


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
    # Everything before the last column, including the gap in front of it.
    essential = sum(widths[:-1]) + gap * (len(widths) - 1)
    budget = width - essential if len(headers) > 1 else width
    # The last column needs its own header plus room for useful prose; a
    # column that is short anyway (doctor's Result) needs only its width.
    if budget < min(widths[-1], max(20, len(headers[-1]))):
        return render_blocks(headers, rows, paint=paint, width=width)

    def fmt(row_index: int, row: list[str]) -> str:
        cells = []
        for i, cell in enumerate(row):
            cell = str(cell)
            if i == len(row) - 1:
                shown = (_shorten(cell, budget)
                         if row_index >= 0 and budget < len(cell) else cell)
                cells.append(paint(row_index, shown) if paint and row_index >= 0
                             else shown)
            else:
                cells.append(cell.ljust(widths[i]))
        return "  ".join(cells).rstrip()

    return [fmt(-1, headers)] + [fmt(i, row) for i, row in enumerate(rows)]


def render_blocks(headers: list[str], rows: list[list[str]], *,
                  paint=None, width: int | None = None) -> list[str]:
    """One file per labeled block — the narrow-terminal fallback. Never
    truncates a value; each row's fields sit on their own line instead, and
    the last (prose) field wraps under a two-space hang."""
    lines: list[str] = []
    for row_index, row in enumerate(rows):
        for i, (label, value) in enumerate(zip(headers, row)):
            if i < len(row) - 1:
                lines.append(f"{label}: {value}")
            elif paint:
                lines.append(f"{label}: {paint(row_index, value)}")
            else:
                lines.extend(wrap(f"{label}: {value}", hang="  ", width=width))
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines
