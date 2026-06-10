#!/usr/bin/env python3
"""render-manuals.py — compose per-model CLI dispatch manuals from one source.

THE render step behind D18's drift guard. Manuals are GENERATED, never
hand-edited: this script composes the single-source dispatch-wrapper template
with each model package's delta into that model's full dispatch manual, stamped
with a DO-NOT-EDIT banner. A protocol change is made ONCE in the wrapper template
(or a model's delta) and re-rendered into every manual.

No external dependencies — Python 3.11+ only.

Usage (run from the rbtv repo root):
    python orchestration/models/render-manuals.py            # render all manuals
    python orchestration/models/render-manuals.py --check    # report drift, write nothing (exit 1 if stale)
    python orchestration/models/render-manuals.py --model kimi-code-cli   # render one model only

Inputs:
    Wrapper template : orchestration/skills/orchestrating/cards/dispatch-wrapper.md
    Model deltas     : orchestration/models/<model>/delta.md   (one per model package)
Output:
    Rendered manual  : orchestration/models/<model>/manual.md  (DO-NOT-EDIT — generated)

----------------------------------------------------------------------------
Marker grammar
----------------------------------------------------------------------------
The wrapper template declares the composition seams as HTML comments
(namespace RENDER:, repo convention <!-- {NS}:{VERB} -->):

    <!-- RENDER:BEGIN <block-id> -->   ... generic content copied verbatim ...
    <!-- RENDER:END <block-id> -->
    <!-- RENDER:INSERT <point-id> -->  ... a single line; the model delta plugs in here ...

Only content INSIDE a BEGIN/END block is rendered into the manual; everything
outside those blocks (the card's prose ABOUT the render machinery) is template-
only and never reaches a manual. INSERT points may sit inside a block; the
delta section named by <point-id> replaces the INSERT line in the output.

Each model's delta.md supplies one section per seam it fills:

    <!-- RENDER:DELTA <point-id> -->   ... content for that INSERT point ...
    <!-- RENDER:DELTA-END <point-id> -->

Plus one MANDATORY free-form section for the invocation shape, which the
generic card explicitly does NOT carry (dispatch-wrapper §7 — the exact command,
flags, work-dir, exit codes are the delta's territory):

    <!-- RENDER:DELTA invocation -->   ... the model's CLI invocation manual ...
    <!-- RENDER:DELTA-END invocation -->

The rendered manual = banner + every BEGIN/END block in template order (INSERT
points substituted) + the `invocation` section under its own heading.

----------------------------------------------------------------------------
Behavior contract
----------------------------------------------------------------------------
- Deterministic: no timestamps, no machine-specific paths — re-rendering with no
  input change is byte-identical (write-if-changed; --check reports zero drift).
- Missing delta: a models/<model>/ folder with no delta.md is SKIPPED with a
  message (not an error) — the package is not ready to render yet.
- Malformed markers FAIL LOUDLY, naming the file and the marker:
    * an INSERT point with no matching delta section,
    * a delta section naming an INSERT point the template does not declare,
    * a missing mandatory `invocation` delta section,
    * an unterminated BEGIN / DELTA marker,
    * a duplicate block / section id.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
_DEFAULT_MODELS_DIR = SCRIPT_PATH.parent  # orchestration/models/ (default; overridable via --models-dir)
MODELS_DIR = _DEFAULT_MODELS_DIR  # legacy module-level alias preserved for callers (e.g. scaffold.py RENDER_MANUALS import)
REPO_ROOT = _DEFAULT_MODELS_DIR.parent.parent  # rbtv repo root

# Template that defines the generic dispatch contract + the render seams.
TEMPLATE_PATH = (
    REPO_ROOT / "orchestration" / "skills" / "orchestrating" / "cards" / "dispatch-wrapper.md"
)

DELTA_FILENAME = "delta.md"
MANUAL_FILENAME = "manual.md"

# The free-form delta section carrying the CLI invocation shape (lives OUTSIDE
# the card's RENDER:BEGIN/END blocks per dispatch-wrapper.md §7). Every package
# delta MUST supply it; it is appended to the manual under INVOCATION_HEADING.
INVOCATION_SECTION = "invocation"
INVOCATION_HEADING = "## Invocation — the exact command shape"

# Marker patterns. Ids are lowercase-kebab tokens.
RE_TPL_BEGIN = re.compile(r"^<!--\s*RENDER:BEGIN\s+([a-z0-9][a-z0-9-]*)\s*-->\s*$")
RE_TPL_END = re.compile(r"^<!--\s*RENDER:END\s+([a-z0-9][a-z0-9-]*)\s*-->\s*$")
RE_TPL_INSERT = re.compile(r"^<!--\s*RENDER:INSERT\s+([a-z0-9][a-z0-9-]*)\s*-->\s*$")
RE_DELTA_BEGIN = re.compile(r"^<!--\s*RENDER:DELTA\s+([a-z0-9][a-z0-9-]*)\s*-->\s*$")
RE_DELTA_END = re.compile(r"^<!--\s*RENDER:DELTA-END\s+([a-z0-9][a-z0-9-]*)\s*-->\s*$")


class RenderError(Exception):
    """A malformed-marker condition that must fail the render loudly."""


def rel(path: Path, repo_root: Path | None = None) -> str:
    """Repo-root-relative POSIX path for stable, machine-independent messages/banners.

    When a custom models_dir is active the effective repo_root differs from REPO_ROOT;
    callers that know the active root pass it explicitly. Falls back to REPO_ROOT.
    """
    root = repo_root if repo_root is not None else REPO_ROOT
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# Template parsing
# ---------------------------------------------------------------------------

class TemplateBlock:
    """A generic RENDER:BEGIN/END block: an ordered list of literal lines and
    INSERT placeholders (carried as ('insert', point_id) sentinels)."""

    def __init__(self, block_id: str) -> None:
        self.block_id = block_id
        self.parts: list[tuple[str, str]] = []  # ('text', line) | ('insert', point_id)

    def add_text(self, line: str) -> None:
        self.parts.append(("text", line))

    def add_insert(self, point_id: str) -> None:
        self.parts.append(("insert", point_id))


def parse_template(path: Path) -> tuple[list[TemplateBlock], list[str]]:
    """Return (blocks in document order, INSERT point ids in document order).

    Only lines inside a BEGIN/END block are captured. INSERT lines inside a
    block become placeholders. INSERT lines outside a block, mismatched ends,
    duplicate ids, and unterminated blocks all raise RenderError.
    """
    if not path.exists():
        raise RenderError(f"wrapper template not found: {rel(path)}")

    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[TemplateBlock] = []
    insert_ids: list[str] = []
    seen_block_ids: set[str] = set()
    seen_insert_ids: set[str] = set()

    current: TemplateBlock | None = None
    open_line_no = 0

    for line_no, line in enumerate(lines, start=1):
        m_begin = RE_TPL_BEGIN.match(line)
        m_end = RE_TPL_END.match(line)
        m_insert = RE_TPL_INSERT.match(line)

        if m_begin:
            if current is not None:
                raise RenderError(
                    f"{rel(path)}:{line_no}: RENDER:BEGIN '{m_begin.group(1)}' opened while "
                    f"block '{current.block_id}' (opened at line {open_line_no}) is still open"
                )
            block_id = m_begin.group(1)
            if block_id in seen_block_ids:
                raise RenderError(f"{rel(path)}:{line_no}: duplicate RENDER:BEGIN id '{block_id}'")
            seen_block_ids.add(block_id)
            current = TemplateBlock(block_id)
            open_line_no = line_no
            continue

        if m_end:
            end_id = m_end.group(1)
            if current is None:
                raise RenderError(f"{rel(path)}:{line_no}: RENDER:END '{end_id}' with no open block")
            if end_id != current.block_id:
                raise RenderError(
                    f"{rel(path)}:{line_no}: RENDER:END '{end_id}' does not match open "
                    f"block '{current.block_id}'"
                )
            blocks.append(current)
            current = None
            continue

        if m_insert:
            point_id = m_insert.group(1)
            if current is None:
                raise RenderError(
                    f"{rel(path)}:{line_no}: RENDER:INSERT '{point_id}' outside any BEGIN/END block"
                )
            if point_id in seen_insert_ids:
                raise RenderError(f"{rel(path)}:{line_no}: duplicate RENDER:INSERT id '{point_id}'")
            seen_insert_ids.add(point_id)
            insert_ids.append(point_id)
            current.add_insert(point_id)
            continue

        if current is not None:
            current.add_text(line)

    if current is not None:
        raise RenderError(
            f"{rel(path)}: RENDER:BEGIN '{current.block_id}' (line {open_line_no}) was never closed"
        )

    if not blocks:
        raise RenderError(f"{rel(path)}: no RENDER:BEGIN/END blocks found — nothing to render")

    return blocks, insert_ids


# ---------------------------------------------------------------------------
# Delta parsing
# ---------------------------------------------------------------------------

def parse_delta(path: Path) -> dict[str, str]:
    """Return {section_id: content} for every RENDER:DELTA section in the file.

    Content is the lines between the DELTA / DELTA-END markers, stripped of
    leading/trailing blank lines (joined with newlines). Mismatched ends,
    nested deltas, duplicate ids, and unterminated sections raise RenderError.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: dict[str, str] = {}
    current_id: str | None = None
    buf: list[str] = []
    open_line_no = 0

    for line_no, line in enumerate(lines, start=1):
        m_begin = RE_DELTA_BEGIN.match(line)
        m_end = RE_DELTA_END.match(line)

        if m_begin:
            if current_id is not None:
                raise RenderError(
                    f"{rel(path)}:{line_no}: RENDER:DELTA '{m_begin.group(1)}' opened while "
                    f"section '{current_id}' (opened at line {open_line_no}) is still open"
                )
            current_id = m_begin.group(1)
            if current_id in sections:
                raise RenderError(f"{rel(path)}:{line_no}: duplicate RENDER:DELTA id '{current_id}'")
            buf = []
            open_line_no = line_no
            continue

        if m_end:
            end_id = m_end.group(1)
            if current_id is None:
                raise RenderError(
                    f"{rel(path)}:{line_no}: RENDER:DELTA-END '{end_id}' with no open section"
                )
            if end_id != current_id:
                raise RenderError(
                    f"{rel(path)}:{line_no}: RENDER:DELTA-END '{end_id}' does not match open "
                    f"section '{current_id}'"
                )
            sections[current_id] = _strip_blank_edges(buf)
            current_id = None
            continue

        if current_id is not None:
            buf.append(line)

    if current_id is not None:
        raise RenderError(
            f"{rel(path)}: RENDER:DELTA '{current_id}' (line {open_line_no}) was never closed"
        )

    return sections


def _strip_blank_edges(buf: list[str]) -> str:
    start = 0
    end = len(buf)
    while start < end and buf[start].strip() == "":
        start += 1
    while end > start and buf[end - 1].strip() == "":
        end -= 1
    return "\n".join(buf[start:end])


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

def make_banner(model: str, models_dir: Path | None = None) -> str:
    """The DO-NOT-EDIT banner — names the sources and the render command.

    Deterministic: no timestamp (a timestamp would break idempotency / the
    re-render zero-diff check). The sources ARE the provenance.

    models_dir: the active models directory (default: _DEFAULT_MODELS_DIR).
    When models_dir differs from _DEFAULT_MODELS_DIR the banner uses the
    default paths so the composed manual is byte-identical to a default render
    (confinement-mode renders are test-only and must not drift the real manuals).
    """
    # Always use the canonical default paths in the banner so that a
    # confinement-override render against a scratch tree produces a banner
    # identical to a normal render — no leak of temp paths into a manual.
    active_models_dir = _DEFAULT_MODELS_DIR
    return (
        f"<!-- AUTO-GENERATED — DO NOT EDIT. Rendered by "
        f"{rel(SCRIPT_PATH)} from {rel(TEMPLATE_PATH)} + {rel(active_models_dir / model / DELTA_FILENAME)}. -->\n"
        f"\n"
        f"> [!danger] GENERATED FILE — DO NOT EDIT\n"
        f"> This dispatch manual is composed by `{rel(SCRIPT_PATH)}` from:\n"
        f"> - the generic dispatch contract `{rel(TEMPLATE_PATH)}`, and\n"
        f"> - the `{model}` package delta `{rel(active_models_dir / model / DELTA_FILENAME)}`.\n"
        f">\n"
        f"> Hand-edits are overwritten on the next render and are forbidden. To change\n"
        f"> packaging/addendum/return behavior, edit the wrapper template; to change\n"
        f"> {model}-specific behavior, edit the delta. Then re-render:\n"
        f">\n"
        f"> ```\n"
        f"> python {rel(SCRIPT_PATH)}\n"
        f"> ```\n"
    )


def compose_manual(
    model: str,
    blocks: list[TemplateBlock],
    insert_ids: list[str],
    delta_sections: dict[str, str],
    delta_path: Path,
) -> str:
    """Compose the full manual text for one model. Raises RenderError on any
    INSERT/delta-section mismatch, naming the file and marker."""
    # Every template INSERT point must have a delta section.
    for point_id in insert_ids:
        if point_id not in delta_sections:
            raise RenderError(
                f"{rel(delta_path)}: missing RENDER:DELTA section '{point_id}' required by "
                f"INSERT point in {rel(TEMPLATE_PATH)}"
            )
    # Mandatory invocation section.
    if INVOCATION_SECTION not in delta_sections:
        raise RenderError(
            f"{rel(delta_path)}: missing mandatory RENDER:DELTA section '{INVOCATION_SECTION}' "
            f"(the CLI invocation shape — dispatch-wrapper.md §7)"
        )
    # Every delta section must be consumed: either a known INSERT point or `invocation`.
    known = set(insert_ids) | {INVOCATION_SECTION}
    for section_id in delta_sections:
        if section_id not in known:
            raise RenderError(
                f"{rel(delta_path)}: RENDER:DELTA section '{section_id}' matches no INSERT point "
                f"in {rel(TEMPLATE_PATH)} (and is not '{INVOCATION_SECTION}')"
            )

    out: list[str] = [make_banner(model)]
    for block in blocks:
        for kind, value in block.parts:
            if kind == "text":
                out.append(value)
            else:  # insert
                out.append(delta_sections[value])
    # Invocation section last, under its own heading, outside the card blocks.
    out.append("")
    out.append("---")
    out.append("")
    out.append(INVOCATION_HEADING)
    out.append("")
    out.append(delta_sections[INVOCATION_SECTION])

    text = "\n".join(out).rstrip("\n") + "\n"
    return text


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def discover_model_dirs(only: str | None, models_dir: Path | None = None) -> list[Path]:
    """Return the list of model package directories to render.

    models_dir: the active models directory. Defaults to _DEFAULT_MODELS_DIR.
    When --models-dir is given, discovers packages from the override directory.
    """
    active = models_dir if models_dir is not None else _DEFAULT_MODELS_DIR
    if only is not None:
        d = active / only
        if not d.is_dir():
            raise RenderError(f"--model '{only}': folder not found at {rel(d)}")
        return [d]
    return sorted(p for p in active.iterdir() if p.is_dir())


def write_if_changed(path: Path, content: str, *, check: bool) -> str:
    """Return 'written' | 'unchanged' | 'drift' (check mode). Never writes in check mode."""
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        return "unchanged"
    if check:
        return "drift"
    path.write_text(content, encoding="utf-8")
    return "written"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Render per-model CLI dispatch manuals from the dispatch-wrapper "
                    "template + each model's delta. Manuals are generated, never hand-edited."
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Report drift and exit 1 if any manual is stale; write nothing.",
    )
    parser.add_argument(
        "--model", metavar="NAME",
        help="Render only this model package (folder name under orchestration/models/).",
    )
    parser.add_argument(
        "--models-dir", metavar="DIR", default=None,
        help=(
            "Override the catalog root (the orchestration/models/ directory). "
            "When given, BOTH render and --check paths discover and resolve model packages "
            "from this directory instead of the default orchestration/models/ tree. "
            "Confinement seam: manual.md outputs are written inside the override directory; "
            "the DO-NOT-EDIT banner always uses the canonical default paths so rendered content "
            "is byte-identical to a default render. "
            "Default: None — uses the orchestration/models/ directory co-located with this script."
        ),
    )
    args = parser.parse_args(argv)

    # Resolve the active models directory (override or default).
    active_models_dir: Path | None = Path(args.models_dir).resolve() if args.models_dir else None

    try:
        blocks, insert_ids = parse_template(TEMPLATE_PATH)
        model_dirs = discover_model_dirs(args.model, models_dir=active_models_dir)
    except RenderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    written: list[str] = []
    unchanged: list[str] = []
    drifted: list[str] = []
    skipped: list[str] = []

    for model_dir in model_dirs:
        model = model_dir.name
        delta_path = model_dir / DELTA_FILENAME
        manual_path = model_dir / MANUAL_FILENAME

        if not delta_path.exists():
            skipped.append(model)
            print(f"skip {model}: no {DELTA_FILENAME} yet ({rel(delta_path)})")
            continue

        try:
            delta_sections = parse_delta(delta_path)
            manual = compose_manual(model, blocks, insert_ids, delta_sections, delta_path)
        except RenderError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

        status = write_if_changed(manual_path, manual, check=args.check)
        if status == "written":
            written.append(model)
            print(f"wrote {rel(manual_path)}")
        elif status == "drift":
            drifted.append(model)
            print(f"drift {rel(manual_path)} — re-render needed")
        else:
            unchanged.append(model)
            print(f"unchanged {rel(manual_path)}")

    # Summary.
    parts = []
    if written:
        parts.append(f"{len(written)} written")
    if unchanged:
        parts.append(f"{len(unchanged)} unchanged")
    if drifted:
        parts.append(f"{len(drifted)} stale")
    if skipped:
        parts.append(f"{len(skipped)} skipped (no delta)")
    print("Manuals: " + (", ".join(parts) if parts else "no model packages found"))

    if args.check and drifted:
        print("\nStale manuals — run:\n  python " + rel(SCRIPT_PATH), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
