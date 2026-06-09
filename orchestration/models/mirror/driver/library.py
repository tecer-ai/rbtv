"""library.py — shared .agents/ worker library render module.

Renders the source-agnostic shared worker library from `.claude/` inputs:
  - `.agents/behavior-rules/`  ← `.claude/rules/*.md`  (verbatim, one-to-one)
  - `.agents/skills/<name>/`   ← `.claude/skills/*/SKILL.md`
                                + `.claude/commands/*.md` WITH `name`+`description` frontmatter
                               (verbatim; frontmatter-less commands are SKIPPED + logged)

Design constraints (from decisions.md):
  - Source-agnostic: NEVER reads `module-manifest.json`, `sb-os.json`, or any manifest.
    All inputs come exclusively from `.claude/`.
  - Reuses `mirror.py`'s `write_if_changed` for idempotent, check-mode-aware writes.
  - Defensively double-quotes YAML `description` values so a worker YAML parser cannot
    silently drop a skill whose description contains an unquoted `:`.

Public API
----------
  render_behavior_rules(target_root, *, check) -> list[dict]
  render_skills(target_root, *, check)         -> list[dict]

Each returns a list of managed-file records:
  {"path": str (workspace-root-relative POSIX), "kind": "behavior-rule"|"skill", "owner": "shared"}
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import the shipped write_if_changed primitive from mirror.py (sibling file).
# This keeps guidance writes byte-identical to mirror.py output.
# ---------------------------------------------------------------------------
_MIRROR_PY = Path(__file__).resolve().parent.parent / "mirror.py"
if str(_MIRROR_PY.parent) not in sys.path:
    sys.path.insert(0, str(_MIRROR_PY.parent))

from mirror import write_if_changed  # noqa: E402  (dynamic sys.path setup above)


# ---------------------------------------------------------------------------
# Binary-mode write helper for truly verbatim (byte-for-byte) copies.
# mirror.py's write_if_changed uses text mode; on Windows that converts LF→CRLF,
# breaking the byte-equality contract for behavior-rules (spec Behavior #2).
# ---------------------------------------------------------------------------

def _write_if_changed_binary(path: Path, data: bytes, *, check: bool) -> str:
    """Like `write_if_changed` but operates in binary mode to preserve line endings.

    Returns 'created' | 'refreshed' | 'in-sync' | 'stale'.
    Never writes in check mode.
    """
    existed = path.exists()
    current = path.read_bytes() if existed else None
    if current == data:
        return "in-sync"
    if check:
        return "stale"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return "refreshed" if existed else "created"


# ---------------------------------------------------------------------------
# YAML frontmatter parsing — minimal, no external dependency
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return a flat {key: value} dict if `text` starts with a YAML frontmatter
    block (`---` ... `---`), else return None.

    Handles single-quoted, double-quoted, and bare values.  Multi-line / block
    values are not supported (skill frontmatter is always flat single-line).
    """
    if not text.startswith("---"):
        return None
    # Find the closing ---
    rest = text[3:]
    end = rest.find("\n---")
    if end == -1:
        return None
    fm_block = rest[:end]
    result: dict[str, str] = {}
    for line in fm_block.splitlines():
        # Strip inline comments (not standard YAML but defensively ignored)
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, raw_value = line.partition(":")
        key = key.strip()
        value = raw_value.strip()
        # Strip surrounding quotes (single or double)
        if len(value) >= 2:
            if (value[0] == "'" and value[-1] == "'") or (
                value[0] == '"' and value[-1] == '"'
            ):
                value = value[1:-1]
        result[key] = value
    return result


def _double_quote_description(description: str) -> str:
    """Return `description` wrapped in double quotes, with any interior double
    quotes escaped.  This ensures a YAML parser never silently drops a skill
    whose description contains an unquoted `:`.

    Idempotent: if the value is already correctly double-quoted (starts and
    ends with `"`, no unescaped interior double quotes), it is returned as-is.
    """
    # Escape any interior double-quotes
    inner = description.replace('"', '\\"')
    return f'"{inner}"'


def _rewrite_description_in_frontmatter(text: str, new_description: str) -> str:
    """Replace the `description:` line in a frontmatter block with a version
    that uses the defensively double-quoted description value.

    Works on multi-line files: finds the first `description:` line inside the
    leading `---` ... `---` block and replaces its value.

    If no `description:` line is found, returns `text` unchanged.
    """
    # Locate the frontmatter end boundary
    if not text.startswith("---"):
        return text
    fm_end_match = re.search(r"\n---", text[3:])
    if not fm_end_match:
        return text
    fm_end = 3 + fm_end_match.start() + 1  # position of the '\n---' end marker

    header = text[:fm_end]
    tail = text[fm_end:]

    # Replace the description line in the header
    quoted = _double_quote_description(new_description)

    def _replace_description(m: re.Match) -> str:
        return f"description: {quoted}"

    new_header, count = re.subn(
        r"^description:.*$", _replace_description, header, count=1, flags=re.MULTILINE
    )
    if count == 0:
        return text  # nothing to replace
    return new_header + tail


# ---------------------------------------------------------------------------
# render_behavior_rules
# ---------------------------------------------------------------------------

def render_behavior_rules(target_root: Path | str, *, check: bool = False) -> list[dict]:
    """Copy each `.claude/rules/*.md` verbatim into `.agents/behavior-rules/<name>.md`.

    Idempotent: uses `write_if_changed` — in check mode, returns the same record
    list but writes nothing (exit-code semantics are the caller's responsibility).

    Returns a list of managed-file records:
      {"path": "<workspace-root-relative POSIX>", "kind": "behavior-rule", "owner": "shared"}
    """
    target_root = Path(target_root).resolve()
    rules_src = target_root / ".claude" / "rules"
    rules_dst = target_root / ".agents" / "behavior-rules"

    records: list[dict] = []

    if not rules_src.is_dir():
        # No .claude/rules/ — nothing to render; not an error (graceful sb-os)
        return records

    for src_file in sorted(rules_src.glob("*.md")):
        data = src_file.read_bytes()  # binary: preserve exact line endings
        dst_file = rules_dst / src_file.name
        _write_if_changed_binary(dst_file, data, check=check)
        rel = dst_file.relative_to(target_root).as_posix()
        records.append({"path": rel, "kind": "behavior-rule", "owner": "shared"})

    return records


# ---------------------------------------------------------------------------
# render_skills
# ---------------------------------------------------------------------------

def render_skills(
    target_root: Path | str,
    *,
    check: bool = False,
) -> tuple[list[dict], list[str]]:
    """Render `.agents/skills/` from `.claude/skills/*/SKILL.md` and
    `.claude/commands/*.md` WITH `name`+`description` frontmatter.

    Rules:
      - Each `.claude/skills/<name>/SKILL.md`     → `.agents/skills/<name>/SKILL.md` (verbatim,
        with description defensively double-quoted).
      - Each `.claude/commands/<stem>.md` WITH `name`+`description` frontmatter
                                                   → `.agents/skills/<name>/SKILL.md` (verbatim,
        with description defensively double-quoted).
      - A command file that lacks frontmatter (or lacks `name` or `description` keys)
        is SKIPPED; its stem is recorded in the returned skip list.

    Returns (records, skipped_names) where:
      records       — list of managed-file dicts {"path", "kind": "skill", "owner": "shared"}
      skipped_names — list of command stems that were skipped (no frontmatter / missing keys)
    """
    target_root = Path(target_root).resolve()
    skills_src = target_root / ".claude" / "skills"
    commands_src = target_root / ".claude" / "commands"
    skills_dst = target_root / ".agents" / "skills"

    records: list[dict] = []
    skipped: list[str] = []

    # --- Skills (always have frontmatter by convention) ---
    if skills_src.is_dir():
        for skill_dir in sorted(skills_src.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            content = skill_md.read_text(encoding="utf-8")
            fm = _parse_frontmatter(content)
            if fm and "name" in fm and "description" in fm:
                # Defensively double-quote description
                content = _rewrite_description_in_frontmatter(content, fm["description"])
                name = fm["name"]
            else:
                # Fall back to the directory name if frontmatter is absent/incomplete
                name = skill_dir.name
            dst_file = skills_dst / name / "SKILL.md"
            write_if_changed(dst_file, content, check=check)
            rel = dst_file.relative_to(target_root).as_posix()
            records.append({"path": rel, "kind": "skill", "owner": "shared"})

    # --- Commands (only those WITH name+description frontmatter) ---
    if commands_src.is_dir():
        for cmd_file in sorted(commands_src.glob("*.md")):
            content = cmd_file.read_text(encoding="utf-8")
            fm = _parse_frontmatter(content)
            if not fm or "name" not in fm or "description" not in fm:
                # SKIP: frontmatter-less or missing required keys
                skipped.append(cmd_file.stem)
                continue
            # Defensively double-quote description
            content = _rewrite_description_in_frontmatter(content, fm["description"])
            name = fm["name"]
            dst_file = skills_dst / name / "SKILL.md"
            write_if_changed(dst_file, content, check=check)
            rel = dst_file.relative_to(target_root).as_posix()
            records.append({"path": rel, "kind": "skill", "owner": "shared"})

    return records, skipped
