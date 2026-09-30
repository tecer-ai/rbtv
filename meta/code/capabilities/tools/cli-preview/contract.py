"""Markdown authoring contract for a CLI output review folder.

A review folder holds:
  - review.md            required, exactly one: title, fixture description,
                          and the command inventory (commands in scope).
  - any other *.md file   screens, sorted by filename. Each screen is a
                          "## <id>. <title>" heading followed by metadata
                          fields and one (or two, for stdout+stderr) fenced
                          code block.

Screen fields (one per line, "Key: value"):
  Category, Command, Terminal width, Scenario, Exit code, Command-path
                                                             -- all required
  Help: yes|no                                              -- optional,
      marks this screen as the help screen for its Command-path. Requires
      Command to contain a literal -h or --help token.
  Stream: stdout|stderr|both                                -- optional,
      default stdout. "both" requires two fenced blocks, each immediately
      preceded by a literal "Stdout:" / "Stderr:" marker line.

Terminal width must be a positive integer; Exit code a nonnegative integer
0-255; screen id a positive integer, unique across every screens file (not
necessarily contiguous). A ```json fence must be strict JSON (no NaN/
Infinity). A leading "## " line only starts a screen when it is outside an
open fenced block. Content before the first screen heading in a screens
file must be blank or a single "<!-- ... -->" comment.

This module only parses and validates; it does not touch disk beyond
reading. parse_folder() returns a ParseResult; the folder is invalid if
result.issues is non-empty. Each issue is {file, line, message, fix}.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FIELDS = ["Category", "Command", "Terminal width", "Scenario", "Exit code", "Command-path"]
KNOWN_FIELDS = set(REQUIRED_FIELDS) | {"Help", "Stream"}

HEADING_RE = re.compile(r"^## (\d+)\. (\S.*)$")
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z \-]*?): ?(.*)$")
FENCE_START_RE = re.compile(r"^```(text|json)\s*$")
FENCE_END_RE = re.compile(r"^```\s*$")
HELP_TOKEN_RE = re.compile(r"(^|\s)(-h|--help)(\s|$)")


def _reject_nonfinite(token: str):
    raise ValueError(f"non-strict JSON token {token!r} (NaN/Infinity are not valid JSON)")


def _issue(file: str, line: int | None, message: str, fix: str) -> dict:
    return {"file": file, "line": line, "message": message, "fix": fix}


def _read_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8-sig")
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def _strip_paired_backticks(value: str) -> str:
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


@dataclass
class ParseResult:
    title: str = ""
    disclaimer: str = ""
    inventory: list[str] = field(default_factory=list)
    screens: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def _parse_review_md(path: Path) -> tuple[str, str, list[str], list[dict]]:
    issues: list[dict] = []
    text = _read_text(path)
    lines = text.split("\n")

    title_idx = None
    title = ""
    for i, line in enumerate(lines):
        if line.startswith("# "):
            if title_idx is None:
                title_idx = i
                title = line[2:].strip()
                if title.lower().startswith("review:"):
                    title = title[len("review:"):].strip()
            else:
                issues.append(_issue("review.md", i + 1, "multiple top-level '# Title' headings",
                                      "keep exactly one '# Review: <title>' heading"))
    if title_idx is None:
        issues.append(_issue("review.md", 1, "missing a top-level '# Title' heading",
                              "add '# Review: <title>' as the first heading"))
    elif not title:
        issues.append(_issue("review.md", title_idx + 1, "review title is empty",
                              "add a title after '# Review:', e.g. '# Review: My CLI'"))

    inv_indices = [i for i, l in enumerate(lines) if l.strip().lower() == "## command inventory"]
    for extra in inv_indices[1:]:
        issues.append(_issue("review.md", extra + 1, "multiple '## Command inventory' sections",
                              "keep exactly one '## Command inventory' section"))

    # review.md only defines two heading kinds: the '# ' title and the one
    # '## Command inventory' section. Any other '## ' heading (before,
    # between, or after those) is unsupported — report it instead of
    # silently dropping its content from the disclaimer or the inventory
    # scan below.
    for i, l in enumerate(lines):
        if l.startswith("## ") and l.strip().lower() != "## command inventory":
            issues.append(_issue("review.md", i + 1, f"unsupported section {l.strip()!r} in review.md",
                                  "review.md only holds a title, a fixture description, and one "
                                  "'## Command inventory' section — remove this section or move its content elsewhere"))

    inventory: list[str] = []
    if not inv_indices:
        issues.append(_issue("review.md", None, "missing a '## Command inventory' section",
                              "add '## Command inventory' with one '- `command`' bullet per declared command"))
        disclaimer_lines = lines[title_idx + 1:] if title_idx is not None else lines[1:]
    else:
        inv_idx = inv_indices[0]
        disclaimer_lines = lines[(title_idx or 0) + 1:inv_idx]
        seen_bullet = False
        for j in range(inv_idx + 1, len(lines)):
            line = lines[j]
            if line.startswith("## "):
                break
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("-"):
                m = re.match(r"^-\s*`([^`]+)`\s*$", stripped)
                if m:
                    seen_bullet = True
                    cmd = m.group(1).strip()
                    if not cmd:
                        issues.append(_issue("review.md", j + 1, "command inventory entry is empty or whitespace-only",
                                              "put a real command path between the backticks, or remove the bullet"))
                    elif cmd in inventory:
                        issues.append(_issue("review.md", j + 1, f"duplicate command inventory entry '{cmd}'",
                                              "list each command path once"))
                    else:
                        inventory.append(cmd)
                else:
                    seen_bullet = True
                    issues.append(_issue("review.md", j + 1, f"unparseable command inventory bullet: {line!r}",
                                          "use '- `command path`' for each declared command"))
            elif seen_bullet:
                issues.append(_issue("review.md", j + 1, f"trailing content after command inventory bullets: {line!r}",
                                      "keep only '- `command`' bullets and blank lines after the first bullet"))
            # else: intro prose before the first bullet — allowed.
        if not inventory:
            issues.append(_issue("review.md", inv_idx + 1, "command inventory has no entries",
                                  "list at least one '- `command`' entry"))

    disclaimer = "\n".join(l for l in disclaimer_lines if not l.startswith("## ")).strip()
    if not disclaimer:
        issues.append(_issue("review.md", None, "fixture description is empty",
                              "add a 'Fixture: ...' description between the title and the command inventory"))
    return title, disclaimer, inventory, issues


def _split_screens(text: str) -> tuple[list[tuple[int, list[str], int]], list[dict]]:
    """Return ((start_line_1based, block_lines, heading_line) per screen, leading-content issues).

    A '## ' line only starts a new screen when it occurs outside an open
    fenced (```) block, so literal '## heading' text inside a screen's
    terminal output is preserved as payload, not mistaken for a heading.
    """
    lines = text.split("\n")
    starts: list[int] = []
    in_fence = False
    for i, l in enumerate(lines):
        if FENCE_START_RE.match(l) and not in_fence:
            in_fence = True
        elif FENCE_END_RE.match(l) and in_fence:
            in_fence = False
        elif l.startswith("## ") and not in_fence:
            starts.append(i)

    issues: list[dict] = []
    leading = lines[:starts[0]] if starts else lines[:]
    leading_text = "\n".join(leading).strip()
    if leading_text:
        is_comment = leading_text.startswith("<!--") and leading_text.endswith("-->")
        if not is_comment:
            issues.append(_issue("", 1, f"unexpected content before the first screen heading: {leading_text[:60]!r}",
                                  "leave this area blank, or use a single '<!-- ... -->' comment"))

    blocks = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        blocks.append((start + 1, lines[start:end], start + 1))
    return blocks, issues


def _parse_screen_file(path: Path, name: str) -> tuple[list[dict], list[dict]]:
    issues: list[dict] = []
    screens: list[dict] = []
    text = _read_text(path)
    blocks, leading_issues = _split_screens(text)
    for it in leading_issues:
        it["file"] = name
    issues.extend(leading_issues)

    for start_line, block, heading_line in blocks:
        heading = block[0]
        m = HEADING_RE.match(heading)
        if not m:
            issues.append(_issue(name, heading_line, f"malformed screen heading: {heading!r}",
                                  "use '## <numeric id>. <title>'"))
            continue
        sid = int(m.group(1))
        if sid <= 0:
            issues.append(_issue(name, heading_line, f"screen id {sid} must be a positive integer",
                                  "use a numeric id of 1 or higher"))
        title = m.group(2).strip()

        fields: dict[str, str] = {}
        fence_events: list[tuple[str, int, int, str | None]] = []  # (type, start, end, marker)
        pending_marker = None
        j = 1
        n = len(block)
        seen_first_fence = False
        while j < n:
            line = block[j]
            fs = FENCE_START_RE.match(line)
            if fs:
                if seen_first_fence and pending_marker is None:
                    issues.append(_issue(name, start_line + j,
                                          "second fenced block needs an immediately preceding 'Stdout:' or 'Stderr:' marker line",
                                          "add a line reading exactly 'Stdout:' or 'Stderr:' right before the fence"))
                ftype = fs.group(1)
                k = j + 1
                while k < n and not FENCE_END_RE.match(block[k]):
                    k += 1
                if k >= n:
                    issues.append(_issue(name, start_line + j, "fenced code block never closes",
                                          "close the ``` block before the next screen heading"))
                    j = n
                    break
                fence_events.append((ftype, j, k, pending_marker))
                pending_marker = None
                seen_first_fence = True
                j = k + 1
                continue
            if not seen_first_fence:
                if line.strip() == "":
                    pass
                elif line.strip() in ("Stdout:", "Stderr:"):
                    pending_marker = line.strip()[:-1]
                elif (fm := FIELD_RE.match(line)):
                    key, val = fm.group(1), fm.group(2).strip()
                    if key not in KNOWN_FIELDS:
                        issues.append(_issue(name, start_line + j, f"unknown field '{key}'",
                                              f"remove it, or use one of: {', '.join(sorted(KNOWN_FIELDS))}"))
                    elif key in fields:
                        issues.append(_issue(name, start_line + j, f"duplicate field '{key}'",
                                              "each field appears at most once per screen"))
                    else:
                        fields[key] = val
                else:
                    issues.append(_issue(name, start_line + j, f"unrecognized line before fenced block: {line!r}",
                                          "use a known 'Key: value' field, a blank line, or the opening fence"))
            else:
                if line.strip() in ("Stdout:", "Stderr:"):
                    pending_marker = line.strip()[:-1]
                elif line.strip() == "":
                    pass
                else:
                    issues.append(_issue(name, start_line + j, f"unexpected content after fenced block: {line!r}",
                                          "leave only blank lines between the end of a screen and the next heading"))
            j += 1

        for req in REQUIRED_FIELDS:
            if req not in fields or not fields[req]:
                issues.append(_issue(name, heading_line, f"screen {sid} missing required field '{req}'",
                                      f"add '{req}: <value>'"))

        command = _strip_paired_backticks(fields.get("Command", "").strip())

        width_raw = fields.get("Terminal width", "").strip()
        if width_raw and (not width_raw.isdigit() or int(width_raw) <= 0):
            issues.append(_issue(name, heading_line, f"screen {sid} Terminal width '{width_raw}' must be a positive integer",
                                  "use a positive integer number of columns"))

        exit_raw = fields.get("Exit code", "").strip()
        if exit_raw and (not exit_raw.isdigit() or not (0 <= int(exit_raw) <= 255)):
            issues.append(_issue(name, heading_line, f"screen {sid} Exit code '{exit_raw}' must be an integer 0-255",
                                  "use a nonnegative exit status in the documented 0-255 domain"))

        stream = fields.get("Stream", "stdout")
        if stream not in ("stdout", "stderr", "both"):
            issues.append(_issue(name, heading_line, f"screen {sid} has invalid Stream value '{stream}'",
                                  "use one of: stdout, stderr, both"))

        if stream == "both":
            if len(fence_events) != 2:
                issues.append(_issue(name, heading_line, f"screen {sid} declares Stream: both but has {len(fence_events)} fenced block(s)",
                                      "add exactly two fenced blocks, marked 'Stdout:' and 'Stderr:'"))
            else:
                markers = [f[3] for f in fence_events]
                if markers != ["Stdout", "Stderr"]:
                    issues.append(_issue(name, heading_line, f"screen {sid}'s two fenced blocks must be marked 'Stdout:' then 'Stderr:' in order",
                                          "reorder so the stdout block comes first"))
        else:
            if len(fence_events) != 1:
                issues.append(_issue(name, heading_line, f"screen {sid} must have exactly one fenced block (has {len(fence_events)})",
                                      "declare 'Stream: both' if you need two, otherwise keep one"))

        help_flag = fields.get("Help", "no").strip().lower()
        if help_flag not in ("yes", "no"):
            issues.append(_issue(name, heading_line, f"screen {sid} has invalid Help value '{fields.get('Help')}'",
                                  "use 'yes' or 'no'"))
            help_flag = "no"
        if help_flag == "yes" and not HELP_TOKEN_RE.search(f" {command} "):
            issues.append(_issue(name, heading_line, f"screen {sid} has Help: yes but Command {command!r} has no -h/--help token",
                                  "either add -h/--help to Command, or set Help: no (a success screen is not a help screen)"))

        contents = {}
        for ftype, fstart, fend, marker in fence_events:
            key = marker.lower() if marker else "stdout"
            content = "\n".join(block[fstart + 1:fend])
            contents[key] = content
            if ftype == "json":
                try:
                    json.loads(content, parse_constant=_reject_nonfinite)
                except (json.JSONDecodeError, ValueError) as e:
                    issues.append(_issue(name, start_line + fstart, f"screen {sid} json fence is not valid strict JSON: {e}",
                                          "fix the JSON so json.loads succeeds (no NaN/Infinity)"))

        primary_type = fence_events[0][0] if fence_events else "text"
        primary_content = contents.get("stdout", contents.get("stderr", ""))

        screens.append({
            "file": name,
            "line": heading_line,
            "id": sid,
            "title": title,
            "category": fields.get("Category", ""),
            "command": command,
            "width": fields.get("Terminal width", ""),
            "scenario": fields.get("Scenario", ""),
            "exitCode": fields.get("Exit code", ""),
            "command_path": fields.get("Command-path"),
            "help": help_flag == "yes",
            "type": primary_type,
            "content": primary_content,
            "stream": "stderr" if (stream == "stderr") else "stdout",
            "stderr_content": contents.get("stderr") if stream == "both" else None,
        })
    return screens, issues


def parse_folder(folder: Path) -> ParseResult:
    result = ParseResult()
    review_path = folder / "review.md"
    if not review_path.is_file():
        result.issues.append(_issue("review.md", None, "review.md not found",
                                     "create review.md with a title, fixture description, and command inventory"))
        return result

    title, disclaimer, inventory, review_issues = _parse_review_md(review_path)
    result.title = title
    result.disclaimer = disclaimer
    result.inventory = inventory
    result.issues.extend(review_issues)

    screen_files = sorted(
        p for p in folder.glob("*.md")
        if p.name != "review.md"
    )
    if not screen_files:
        result.issues.append(_issue(".", None, "no screen files found (need at least one *.md besides review.md)",
                                     "add a screens file, e.g. '01-screens.md'"))

    all_screens: list[dict] = []
    for p in screen_files:
        screens, issues = _parse_screen_file(p, p.name)
        all_screens.extend(screens)
        result.issues.extend(issues)

    seen_ids: dict[int, str] = {}
    for s in all_screens:
        if s["id"] in seen_ids:
            result.issues.append(_issue(s["file"], s["line"],
                                         f"duplicate screen id {s['id']} (also in {seen_ids[s['id']]})",
                                         "renumber so every screen id is globally unique"))
        else:
            seen_ids[s["id"]] = s["file"]

    for s in all_screens:
        cp = s["command_path"]
        if cp is not None and inventory and cp not in inventory:
            result.issues.append(_issue(s["file"], s["line"],
                                         f"screen {s['id']} declares Command-path '{cp}' not in review.md's command inventory",
                                         "add it to '## Command inventory' in review.md, or fix the typo"))

    covered = {s["command_path"] for s in all_screens if s["command_path"] and s["help"]}
    for cmd in inventory:
        if cmd not in covered:
            result.issues.append(_issue("review.md", None,
                                         f"no help screen declared for inventory command '{cmd}'",
                                         f"add a screen with Command-path: {cmd}, Help: yes, and -h/--help in Command"))

    result.screens = all_screens
    return result
