#!/usr/bin/env python3
"""component-lint — one growing deterministic lint over an rbtv component folder.

Detection only; never writes. Owner ruling D19 (planning-v4-build decisions.md)
picks the check roster; the design is `evidence/E-mechanization-survey.md` § 3.

Two carried requirements bind every check:
  1. the census is printed AND gated — a check that discovered nothing where its
     surface exists FAILS, because a green run over undiscovered files is a
     false green that is invisible rather than loud;
  2. every check ships a red arm in test_component_lint.py.

Exit: 0 clean · 1 findings · 2 broken preconditions.

Target scope (7.625 ruling): any mirror/meta component, not only planning. A
component's seats.csv must share the five-column header PREFIX (seat-id,
executor, task, staffing-hints, description) and may append columns after it
(master adds cage-grants, rw-paths — read positionally, extras ignored);
a header diverging inside the prefix is still a broken precondition. Checks
whose surface is planning-shaped guard their vacuity tripwire per component
shape (see check_dimension_roster) instead of failing components that
legitimately lack the surface.
"""

import argparse
import csv
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

# ---------------------------------------------------------------- vocabularies
# HARDCODED + CROSS-CHECKED. Each vocabulary below is asserted against the
# artifact that owns it (a reference page, or the KG record) at run time, so a
# silent copy cannot drift: the two police each other. Never "just update" one
# side — a mismatch is a finding on THIS FILE.

# Owner: references/exposure.md §1 (the eighth value `path` is owner-ruled
# 2026-08-09, core-build decisions.md#d-tool-inventory-exposure-rows).
EXPOSURE_METHODS = ("skill", "command", "rule", "hook", "sub-agent",
                    "agents.md", "config", "path", "pool")

# Owner: references/exposure.md §1 (stated from `sd-graph show "exposure
# manifest"` § file schema, part-kind column; the tool inventory ruling above
# mints the `tool` value; the seventh value `plugin/MCP` is owner-ruled
# 2026-08-15, sd `decisions.md#d-exposure-part-kind-plugin-mcp`).
EXPOSURE_PART_KINDS = ("capability", "reference", "workflow", "task", "prompt", "tool",
                      "plugin/MCP")

# The SEVENTH column is `write-roots` (W6): the directories a `method=path`
# row's CLI must be able to WRITE. `;`-separated; each entry carries the
# DANGER SIGIL `!` and takes the entry-point grammar (component-relative or
# `ws:<path-from-the-workspace-root>`, no `..`). The marker is IN-CELL and
# the header stays SEVEN columns: it qualifies one entry, not the row. An
# unmarked entry is refused HERE and at materialize both — a write grant is
# never inferred.
EXPOSURE_HEADER = ["part-id", "part-kind", "method", "rbtv-cli", "entry-point",
                   "description", "write-roots"]
DANGER_SIGIL = "!"
WS_PREFIX = "ws:"
# The DISCOVERY layer (W6): the file a `method=skill` row's entry-point NAMES
# carries a flat `exposes-cli:` list of the CLIs that skill routes to, in the
# `exposes:` reference grammar. NOT "SKILL.md" — 10 of the 11 live skill rows
# point at some other file.
EXPOSES_CLI_KEY = "exposes-cli"

# Owner: `sd-graph show "workflow manifest"` (Modality column desc).
MODALITIES = ("deterministic", "agentic", "interactive")

MANIFEST_HEADER = ["Seat/workflow", "after", "i/o", "Modality"]
SEATS_HEADER = ["seat-id", "executor", "task", "staffing-hints", "description"]

# Owner: `sd-graph show "cognitive unit"` § Requirement matrix. Section tag per
# matrix kind; only top-level (non-indented) kinds are sections — the nested
# ones (persona/agent type; input/outcome/output) are sub-kinds, M6's subject.
KIND_TAGS = {
    "role": "role", "procedure": "procedure", "permissions": "permissions",
    "restrictions": "restrictions", "constraints": "constraints",
    "i/o spec": "io-spec", "resources": "resources", "task goal": "task-goal",
    "scope": "scope", "done contract": "done-contract",
}
# carrier -> {tag: required|optional}; every other tag is n-a (forbidden).
MATRIX = {
    "prompt": {"role": "required", "procedure": "required", "permissions": "required",
               "restrictions": "required", "constraints": "optional",
               "io-spec": "required", "resources": "optional"},
    "task": {"task-goal": "required", "scope": "required", "done-contract": "required"},
}
# Owner: references/file-prompt.md and references/file-task.md ("Body — one
# kind-named XML section per ... unit, in this order"). Cross-checked below.
ORDER = {
    "prompt": ["role", "procedure", "resources", "io-spec", "permissions",
               "restrictions", "constraints"],
    "task": ["task-goal", "scope", "done-contract"],
}

# Owner: D14 (interactive-seat doctrine) via D19's typed-field pick.
FALLBACK_ARMS = ("park", "default-and-disclose", "block-and-queue")
AUTONOMOUS_ARM = "Autonomous arm —"  # the step marker a block-and-queue <procedure> carries

# Owner ruling 2026-08-10 (execution-mode lifecycle). The field a workflow
# definition declares, and the goal.md field a workflow-producing run carries it
# from. Absent on both sides is legal: the creation path derives from Modality.
DECLARED_MODE = re.compile(r"^default-execution-mode:\s*(\S+)\s*$", re.M)

SECTION_OPEN = re.compile(r"^<([a-z][a-z0-9-]*)((?:\s[^>]*)?)>\s*$")
SECTION_CLOSE = re.compile(r"^</([a-z][a-z0-9-]*)>\s*$")
SOURCE_ATTR = re.compile(r'\bsource="([^"]+)"')
NEAR_MISS_SOURCE = re.compile(r"\bsource\s*=\s*(?!\")")
DIMENSION_CLAUSE = re.compile(r"no finding cites any dimension other than ([A-Za-z0-9-]+)",
                              re.IGNORECASE)
GUARD = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[([A-Za-z0-9_.-]+)=([^\]]+)\])?$")

# Owner: `ignite/jobs/edge-runner-job.py` — the runner that DISCHARGES a guard.
# Its `_PATHISH` reads a declared artifact as a backticked token carrying a `/`
# and an extension, taken from the `## Outputs` section INSIDE `<io-spec>`, and
# its field surface is `.json` top-level scalars only. Prose the parser cannot
# read declares nothing, whatever it says.
DECLARED_PATH = re.compile(r"`([^`\s]*/[^`\s]*\.[A-Za-z0-9]{1,6})`")
OUTPUTS_SECTION = re.compile(r"##\s*Outputs\s*(.*?)(?=\n##\s|\Z)", re.S)
# Owner: the convention stated as a rule in references/kind-io-spec.md — a
# `.json` output NAMES its top-level fields as backticked bare tokens in the
# same bullet that declares the artifact.
FIELD_TOKEN = re.compile(r"`([A-Za-z0-9_.-]+)`")


# The component this tool ships in. The vocabularies above are cross-checked
# against ITS references, never the linted component's: a cross-check indicts
# THIS FILE's hardcoded copy, so it must read the one home of each vocabulary
# regardless of which component is under the lint.
HOME = Path(__file__).resolve().parents[3]


class Precondition(Exception):
    """The check could not run at all — exit 2, never a silent pass."""


# ------------------------------------------------------------------- utilities

def split_outside_brackets(text, sep):
    """Split on `sep`, ignoring separators inside [...]. The manifest's live
    3-limb guard `a[f=x|y]` puts an alternation INSIDE one bracket; a naive
    split shreds it into unresolvable refs."""
    parts, depth, buf = [], 0, []
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_flow_list(value):
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [unquote(v) for v in next(csv.reader([inner], skipinitialspace=True))]


def parse_frontmatter(text, label):
    """Minimal YAML-subset frontmatter reader (stdlib-only convention).

    Handles what the prompt/task cards use: scalars, flow lists, block lists,
    block mappings. Anything else raises Precondition rather than guessing —
    a frontmatter this cannot read is a broken precondition, not a pass."""
    if not text.startswith("---\n"):
        raise Precondition(f"{label}: no frontmatter")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise Precondition(f"{label}: unterminated frontmatter")
    data, key = {}, None
    for raw in text[4:end + 1].splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] not in " \t":
            m = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", raw)
            if not m:
                raise Precondition(f"{label}: unparseable frontmatter line {raw!r}")
            key, value = m.group(1), m.group(2).strip()
            if value == "":
                data[key] = None
            elif value.startswith("[") and value.endswith("]"):
                data[key] = parse_flow_list(value)
            else:
                data[key] = unquote(value)
        else:
            if key is None:
                raise Precondition(f"{label}: indented frontmatter line before any key")
            item = raw.strip()
            if item.startswith("- "):
                if data.get(key) is None:
                    data[key] = []
                if not isinstance(data[key], list):
                    raise Precondition(f"{label}: list item under non-list key {key!r}")
                data[key].append(unquote(item[2:]))
            else:
                m = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", item)
                if not m:
                    raise Precondition(f"{label}: unparseable nested line {raw!r}")
                if data.get(key) is None:
                    data[key] = {}
                if not isinstance(data[key], dict):
                    raise Precondition(f"{label}: mapping entry under non-mapping key {key!r}")
                value = m.group(2).strip()
                data[key][m.group(1)] = (parse_flow_list(value)
                                         if value.startswith("[") and value.endswith("]")
                                         else unquote(value))
    return data


def read_text(path, label):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Precondition(f"{label}: cannot read {path}: {exc}") from exc


def read_csv(path, label):
    """Rows as lists, header first. '#' comments and blank lines before the
    header are skipped (the capability-cards precedent, ADX-1/ADX-3)."""
    lines = read_text(path, label).splitlines(keepends=True)
    offset = 0
    while offset < len(lines) and (lines[offset].startswith("#") or not lines[offset].strip()):
        offset += 1
    try:
        rows = list(csv.reader(lines[offset:]))
    except csv.Error as exc:
        raise Precondition(f"{label}: malformed csv {path}: {exc}") from exc
    return [r for r in rows if any(f.strip() for f in r)], offset


def sections_of(text):
    """Top-level kind-named XML sections: [(tag, attrs, open_line, body)]."""
    lines = text.splitlines()
    found, depth, open_tag, start = [], 0, None, 0
    for i, line in enumerate(lines):
        if depth == 0:
            m = SECTION_OPEN.match(line)
            if m:
                depth, open_tag, start, attrs = 1, m.group(1), i, m.group(2)
                continue
        else:
            if SECTION_OPEN.match(line) and SECTION_OPEN.match(line).group(1) == open_tag:
                depth += 1
            elif SECTION_CLOSE.match(line):
                if SECTION_CLOSE.match(line).group(1) == open_tag:
                    depth -= 1
                    if depth == 0:
                        found.append((open_tag, attrs, start + 1,
                                      "\n".join(lines[start + 1:i])))
                        open_tag = None
    if open_tag is not None:
        found.append((open_tag, attrs, start + 1, None))  # unclosed
    return found


def normalize(block):
    lines = block.splitlines()
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "\n".join(line.rstrip() for line in lines)


# ------------------------------------------------------------------- component

class Component:
    """Everything every check needs, parsed ONCE (survey §3 reason 1)."""

    def __init__(self, root, extra_roots, cards_root, home=None, goal=None, produced=()):
        # ABSOLUTE, always: every entry-point check is `c.root / entry` tested
        # for a `..` part. A relative --component (`../../..`, the natural form
        # from a nested cwd) would put its OWN `..` into every one of those
        # joins and make every entry point read as an escape.
        self.root = Path(root).resolve()
        self.home = Path(home) if home else HOME
        # The produced-workflow pairing: the goal folder whose goal.md carries
        # the owner's confirmed default, and the workflow names THAT goal
        # produced into this component. Absent -> M11 is not applicable.
        self.goal = Path(goal) if goal else None
        self.produced = list(produced)
        if not self.root.is_dir():
            raise Precondition(f"component path is not a directory: {self.root}")
        self.extra_roots = [Path(r) for r in extra_roots]
        self.cards_root = Path(cards_root) if cards_root else self.root.parent.parent

        self.prompts = self._load_pool("prompts")
        self.tasks = self._load_pool("tasks")
        self.seats = self._load_seats()
        self.manifests = self._load_manifests()
        self.exposure = self._load_exposure()
        self.references = sorted(p for p in (self.root / "references").glob("*.md")) \
            if (self.root / "references").is_dir() else None
        self.capabilities = sorted(p for p in (self.root / "capabilities").iterdir() if p.is_dir()) \
            if (self.root / "capabilities").is_dir() else None
        self.markdown = sorted(self.root.rglob("*.md"))

    def _load_pool(self, name):
        folder = self.root / name
        if not folder.is_dir():
            return None
        pool = {}
        for path in sorted(folder.glob("*.md")):
            text = read_text(path, name)
            pool[path.stem] = {"path": path, "text": text,
                               "fm": parse_frontmatter(text, str(path))}
        return pool

    def _load_seats(self):
        path = self.root / "seats.csv"
        if not path.is_file():
            return None
        rows, offset = read_csv(path, "seats")
        header, data = rows[0], rows[1:]
        # Prefix match (7.625): a component may append columns after the shared
        # five (master adds cage-grants, rw-paths); rows are read
        # positionally from the shared prefix, so extras are ignored, but a
        # header that diverges INSIDE the prefix is still refused.
        if header[:len(SEATS_HEADER)] != SEATS_HEADER:
            raise Precondition(f"seats.csv: unrecognized header {header}")
        return {"path": path, "rows": [
            {"seat-id": r[0], "executor": r[1] if len(r) > 1 else "",
             "task": r[2] if len(r) > 2 else "", "description": r[4] if len(r) > 4 else "",
             "line": offset + 2 + i} for i, r in enumerate(data)]}

    def _load_manifests(self):
        folder = self.root / "workflows"
        if not folder.is_dir():
            return None
        manifests = []
        for path in sorted(folder.glob("*/*.csv")):
            rows, offset = read_csv(path, "manifest")
            header, data = rows[0], rows[1:]
            if header != MANIFEST_HEADER:
                raise Precondition(f"{path}: unrecognized manifest header {header}")
            manifests.append({"path": path, "rows": [
                {"seat": r[0], "after": r[1] if len(r) > 1 else "",
                 "io": r[2] if len(r) > 2 else "", "modality": r[3] if len(r) > 3 else "",
                 "line": offset + 2 + i} for i, r in enumerate(data)]})
        return manifests

    def _load_exposure(self):
        path = self.root / "exposure.csv"
        if not path.is_file():
            return None
        rows, offset = read_csv(path, "exposure")
        return {"path": path, "header": rows[0],
                "rows": [{"fields": r, "line": offset + 2 + i}
                         for i, r in enumerate(rows[1:])]}

    def resolve(self, ref):
        """Resolve a declared path against the component root, the mirror root,
        and every --root. Returns the resolved Path or None.

        A `ws:` prefix is the ONE sanctioned way out of the component (owner-ruled
        2026-08-11, IPH-6 / D33), same meaning as on an exposure entry-point: the
        rest is a path from the WORKSPACE root. No workspace above the component
        -> nothing to resolve against, so None; a linter reports, it never raises."""
        if ref.startswith("ws:"):
            ws = workspace_root(self.root)
            target = ws / ref[3:] if ws else None
            return target if target and target.exists() else None
        for base in [self.root, self.cards_root] + self.extra_roots:
            if (base / ref).exists():
                return base / ref
        return None

    @property
    def resolve_roots(self):
        return [str(self.root), str(self.cards_root)] + [str(r) for r in self.extra_roots]


# ---------------------------------------------------------------------- checks
# Each check: (id, needs, run). `needs` names the surfaces the check reads —
# ALL absent -> the check is not applicable to this component and is REPORTED
# skipped; present-but-empty -> a census FAIL, never a silent pass.

def _fail(out, check, where, message):
    out.append({"severity": "FAIL", "check": check, "where": str(where), "message": message})


def _info(out, check, where, message):
    out.append({"severity": "INFO", "check": check, "where": str(where), "message": message})


def _guide_canon(c, member):
    """A canon as references/exposure.md §1 states it — the bold middot-joined
    run containing `member` — or None. Cross-checks a hardcoded vocabulary."""
    guide = c.home / "references" / "exposure.md"
    if not guide.is_file():
        return None
    for m in re.finditer(r"\*\*([^*]+)\*\*", read_text(guide, "exposure guide")):
        if "·" in m.group(1):
            values = {v.strip() for v in m.group(1).split("·")}
            if member in values:
                return values
    return None


def guide_methods(c):
    """The method canon (the run naming `skill`), or None."""
    return _guide_canon(c, "skill")


def guide_part_kinds(c):
    """The part-kind canon (the run naming `capability`), or None."""
    return _guide_canon(c, "capability")


def workspace_root(start):
    """The first ancestor of `start` holding a `.rbtv/config/` DIRECTORY — the
    base a `ws:` entry-point resolves against — or None when none does.

    Mirrors `materialize-seats.py#_workspace_root`, which REFUSES where this
    returns None: a linter reports findings, it never raises."""
    start = Path(start).resolve()
    for parent in (start, *start.parents):
        if (parent / ".rbtv" / "config").is_dir():
            return parent
    return None


def check_exposure_canon(c, out, census):
    """M1 — exposure-manifest canon + entry-point existence."""
    ex = c.exposure
    census["exposure-rows"] = len(ex["rows"])
    if ex["header"] != EXPOSURE_HEADER:
        _fail(out, "exposure-canon", ex["path"], f"header is {ex['header']}, expected {EXPOSURE_HEADER}")
        return
    if not ex["rows"]:
        _fail(out, "exposure-canon", ex["path"], "discovered 0 manifest rows — nothing was checked")
        return
    declared = guide_methods(c)
    if declared is None:
        _fail(out, "exposure-canon", c.home / "references" / "exposure.md",
              "no method canon found to cross-check the hardcoded vocabulary against")
    elif declared != set(EXPOSURE_METHODS):
        _fail(out, "exposure-canon", "component_lint.py",
              f"method canon cross-check: hardcoded {sorted(EXPOSURE_METHODS)} != "
              f"reference {sorted(declared)} — the two homes disagree")
    kinds = guide_part_kinds(c)
    if kinds is None:
        _fail(out, "exposure-canon", c.home / "references" / "exposure.md",
              "no part-kind canon found to cross-check the hardcoded vocabulary against")
    elif kinds != set(EXPOSURE_PART_KINDS):
        _fail(out, "exposure-canon", "component_lint.py",
              f"part-kind canon cross-check: hardcoded {sorted(EXPOSURE_PART_KINDS)} != "
              f"reference {sorted(kinds)} — the two homes disagree")
    seen = {}
    for row in ex["rows"]:
        f, line = row["fields"], row["line"]
        where = f"{ex['path']}:{line}"
        if len(f) != len(EXPOSURE_HEADER):
            _fail(out, "exposure-canon", where, f"row has {len(f)} fields, expected {len(EXPOSURE_HEADER)}")
            continue
        part_id, part_kind, method, rbtv_cli, entry, desc, write_roots = f
        if not part_id.strip():
            _fail(out, "exposure-canon", where, "empty part-id")
        if part_id in seen:
            _fail(out, "exposure-canon", where, f"duplicate part-id {part_id!r} (also line {seen[part_id]})")
        seen[part_id] = line
        if not method.strip():
            _fail(out, "exposure-canon", where,
                  f"empty method on {part_id!r} — a method-less row is not expressible")
        elif method not in EXPOSURE_METHODS:
            _fail(out, "exposure-canon", where, f"method {method!r} is outside the canon {list(EXPOSURE_METHODS)}")
        if part_kind not in EXPOSURE_PART_KINDS:
            _fail(out, "exposure-canon", where, f"part-kind {part_kind!r} is outside {list(EXPOSURE_PART_KINDS)}")
        if method == "path":
            if rbtv_cli.strip() or desc.strip():
                _fail(out, "exposure-canon", where,
                      "a method=path row leaves rbtv-cli and description empty (the tool self-documents via -h)")
            # `ws:` — the ONE sanctioned way an entry-point leaves its
            # component (owner-ruled 2026-08-11, IPH-6 / D33): a path from the
            # WORKSPACE root, not from the component. It is expanded BEFORE
            # the existence test, or every `ws:` row reads as a missing file
            # against a component-relative join that was never meant.
            raw = entry.strip()
            ws = workspace_root(c.root) if raw.startswith("ws:") else None
            target = (ws / raw[3:]) if ws else c.root / entry
            if not raw:
                _fail(out, "exposure-canon", where, "method=path with no entry-point")
            elif raw.startswith("ws:") and ws is None:
                _fail(out, "exposure-canon", where,
                      f"entry-point {raw} is `ws:`-prefixed but no `.rbtv/config/` directory "
                      "exists at or above the component — no workspace to resolve it against")
            elif ".." in Path(target).parts:
                _fail(out, "exposure-canon", where,
                      f"entry-point climbs out of its component with `..`: {raw} — reach a "
                      "workspace tool with `ws:<path-from-the-workspace-root>` instead "
                      "(materialize REFUSES this at generation time)")
            elif not target.exists():
                _fail(out, "exposure-canon", where, f"entry-point does not exist on disk: {entry}")
            elif not os.access(target, os.X_OK):
                # INFO, not FAIL: this component's tools are invoked as
                # `python <path>` by their own capability cards, so the exec
                # bit is not their invocation contract. Disclosed deviation
                # from the survey's M1(b) wording.
                _info(out, "exposure-canon", where, f"entry-point is not executable: {entry}")
        elif method and not entry.strip():
            _fail(out, "exposure-canon", where, f"method={method} with no entry-point")
        _check_write_roots(c, out, where, part_id, method, write_roots)
        if method == "skill" and entry.strip():
            _check_skill_clis(c, out, where, part_id, c.root / entry.strip(), census)


def _check_write_roots(c, out, where, part_id, method, cell):
    """The SEVENTH column. Same two rules as the entry-point (`ws:` base, then
    the `..` refusal) plus the danger sigil every entry must carry — stated in
    ONE place so the lint and `materialize-seats.py#_write_roots` cannot drift
    into two different grammars."""
    cell = (cell or "").strip()
    if not cell:
        return
    if method != "path":
        _fail(out, "exposure-canon", where,
              f"{part_id!r} declares write-roots on a method={method or '(empty)'} row — "
              "a write root belongs to a CLI, so the column is legal on method=path rows ONLY")
        return
    for authored in (e.strip() for e in cell.split(";")):
        if not authored:
            continue
        if not authored.startswith(DANGER_SIGIL):
            _fail(out, "exposure-canon", where,
                  f"{part_id!r} declares write-root {authored!r} without the danger marker — "
                  f"every entry is written '{DANGER_SIGIL}<path>'. A write grant reaches a seat "
                  "only because an author typed the marker; it is never inferred")
            continue
        body = authored[len(DANGER_SIGIL):].strip()
        if not body:
            _fail(out, "exposure-canon", where,
                  f"{part_id!r} declares write-root {authored!r} — the marker carries no path")
            continue
        # Prefix stripped BEFORE the `..` test, matching the entry-point rule and
        # `materialize-seats.py#_write_roots`: `!ws:../x` and `!../x` take ONE rule.
        prefixed = body.startswith(WS_PREFIX)
        rel = body[len(WS_PREFIX):] if prefixed else body
        if ".." in PurePosixPath(rel).parts:
            _fail(out, "exposure-canon", where,
                  f"{part_id!r} declares write-root {authored!r}, which climbs with `..` — "
                  "reach a workspace path with `ws:<path-from-the-workspace-root>` instead")
            continue
        if prefixed:
            ws = workspace_root(c.root)
            if ws is None:
                _fail(out, "exposure-canon", where,
                      f"{part_id!r} declares write-root {authored!r} but no `.rbtv/config/` "
                      "directory exists at or above the component — no workspace to resolve it")
                continue
            target = ws / rel
        else:
            target = c.root / rel
        if not target.is_dir():
            _fail(out, "exposure-canon", where,
                  f"{part_id!r} declares write-root {authored!r}, which is no directory on "
                  f"disk ({target}) — the cage binds it, and bwrap needs a source that exists")


def _skill_cli_refs(path):
    """The flat `exposes-cli:` list off a skill entry-point file's frontmatter,
    or None when the file is unreadable/keyless. [] is a real declaration
    ("routes to no CLI"); None means "said nothing"."""
    try:
        fm = parse_frontmatter(path.read_text(encoding="utf-8"), str(path))
    except (OSError, Precondition):
        # No frontmatter at all is a legal skill entry point (the two live
        # console-entry.md files carry none) — it declares no CLI, which is the
        # same answer as a missing key. It must NOT block the whole check.
        return None
    raw = fm.get(EXPOSES_CLI_KEY)
    return raw if isinstance(raw, list) else ([] if raw == [] else None)


def _check_skill_clis(c, out, where, part_id, entry_path, census):
    """`skill-cli-dangling` — every `exposes-cli:` ref on a skill's entry point
    resolves to a `method=path` row. Enforced HERE and at materialize both: the
    lint catches it while the author still holds the file, materialize catches
    it before a dead reference reaches a seat."""
    refs = _skill_cli_refs(entry_path)
    if refs is None:
        return                                   # absence is normal
    census["skill-cli-refs"] = census.get("skill-cli-refs", 0) + len(refs)
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            _fail(out, "exposure-canon", entry_path,
                  f"`{EXPOSES_CLI_KEY}:` carries a non-string entry {ref!r} — the key is a flat "
                  "list of part references")
            continue
        if ref.strip().startswith("rbtv:"):
            continue                                # resolved by materialize, not here
        ref_dir, pid = _ref_target(c.root, ref.strip())
        if ref_dir is None:
            _fail(out, "exposure-canon", entry_path,
                  f"skill {part_id!r} routes to CLI {ref!r} — a reference is `part`, "
                  "`component/part`, or `module/component/part` (`rbtv:` refs are resolved by "
                  "materialize against the repo and are not checked here)")
            continue
        rows = _exposure_index(ref_dir)
        if rows.get(pid) != "path":
            _fail(out, "exposure-canon", entry_path,
                  f"skill-cli-dangling: skill {part_id!r} routes to CLI {ref!r} — no "
                  f"`method=path` row {pid!r} under {ref_dir / 'exposure.csv'}. A skill is the "
                  "DISCOVERY layer; exposure.csv stays the declaration layer")


def _ref_target(comp_dir, ref):
    """(component dir, part-id) for one `exposes:`-grammar reference, or
    (None, ref) when the grammar refuses it. `rbtv:` refs return (None, ...)
    deliberately: resolving them needs the repo root materialize derives from
    rbtv.json, and a linter that guesses it would report a false dangling."""
    if ref.startswith("rbtv:"):
        return None, ref
    segs = ref.split("/")
    if not all(s.strip() for s in segs) or len(segs) > 3:
        return None, ref
    if len(segs) == 1:
        return comp_dir, segs[0]
    if len(segs) == 2:
        return comp_dir.parent / segs[0], segs[1]
    return comp_dir.parent.parent / segs[0] / segs[1], segs[2]


def _exposure_index(comp_dir):
    """part-id -> method for one component's manifest ({} when absent). `#`-led
    lines dropped before the header, matching every other reader."""
    path = comp_dir / "exposure.csv"
    if not path.is_file():
        return {}
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
             if not ln.lstrip().startswith("#")]
    return {(r.get("part-id") or "").strip(): (r.get("method") or "").strip()
            for r in csv.DictReader(lines) if (r.get("part-id") or "").strip()}


def check_seat_integrity(c, out, census):
    """M2 — seat/manifest referential integrity, orphans, modality, acyclicity."""
    seats = {s["seat-id"]: s for s in c.seats["rows"]}
    census["seats"] = len(seats)
    census["prompts"] = len(c.prompts) if c.prompts is not None else 0
    census["tasks"] = len(c.tasks) if c.tasks is not None else 0
    if not seats:
        _fail(out, "seat-integrity", c.seats["path"], "discovered 0 seats — nothing was checked")
        return
    for empty, label in ((not c.prompts, "prompts/"), (not c.tasks, "tasks/")):
        if empty:
            _fail(out, "seat-integrity", c.root / label, f"discovered 0 files in {label} while seats reference it")

    used_prompts, used_tasks = set(), set()
    for row in c.seats["rows"]:
        where = f"{c.seats['path']}:{row['line']}"
        if c.prompts is not None:
            if row["executor"] not in c.prompts:
                _fail(out, "seat-integrity", where,
                      f"seat {row['seat-id']!r} executor {row['executor']!r} has no prompts/{row['executor']}.md")
            else:
                used_prompts.add(row["executor"])
        if c.tasks is not None:
            if row["task"] not in c.tasks:
                _fail(out, "seat-integrity", where,
                      f"seat {row['seat-id']!r} task {row['task']!r} has no tasks/{row['task']}.md")
            else:
                used_tasks.add(row["task"])

    for pool, used, name in ((c.prompts, used_prompts, "prompts"), (c.tasks, used_tasks, "tasks")):
        if pool is None:
            continue
        for stem, item in pool.items():
            if stem not in used:
                _fail(out, "seat-integrity", item["path"], f"orphan {name[:-1]} file — no seats.csv row uses it")
            declared = item["fm"].get("id")
            if declared != stem:
                _fail(out, "seat-integrity", item["path"],
                      f"frontmatter id {declared!r} does not match the filename stem {stem!r}")

    manifest_seats = set()
    for manifest in c.manifests or []:
        if not manifest["rows"]:
            _fail(out, "seat-integrity", manifest["path"], "discovered 0 manifest rows — nothing was checked")
            continue
        ids = {r["seat"] for r in manifest["rows"]}
        graph = {}
        for row in manifest["rows"]:
            where = f"{manifest['path']}:{row['line']}"
            manifest_seats.add(row["seat"])
            if row["seat"] not in seats:
                _fail(out, "seat-integrity", where, f"manifest row {row['seat']!r} resolves to no seat id")
            if row["modality"] not in MODALITIES:
                _fail(out, "seat-integrity", where,
                      f"Modality {row['modality']!r} is outside {list(MODALITIES)}")
            preds = []
            for entry in split_outside_brackets(row["after"], ","):
                for alt in split_outside_brackets(entry, "|"):
                    m = GUARD.match(alt)
                    if not m:
                        _fail(out, "seat-integrity", where, f"unparseable after entry {alt!r} (grammar: ref[field=value])")
                        continue
                    ref = m.group(1)
                    if ref not in ids:
                        _fail(out, "seat-integrity", where, f"after ref {ref!r} resolves to no manifest row")
                    else:
                        preds.append(ref)
            graph[row["seat"]] = preds
        for cycle in find_cycles(graph):
            _fail(out, "seat-integrity", manifest["path"], f"after graph is cyclic: {' -> '.join(cycle)}")

    if c.manifests:
        # A no-manifest seat is sanctioned by a sub-agent or pool exposure row
        # on its executor prompt (owner-ruled, planning-v4 D22); neither → FAIL.
        sanctioning = {r["fields"][0] for r in c.exposure["rows"]
                       if len(r["fields"]) == len(EXPOSURE_HEADER)
                       and r["fields"][2] in ("sub-agent", "pool")}
        census["sanctioned-no-manifest"] = 0
        for seat_id in sorted(set(seats) - manifest_seats):
            if seats[seat_id]["executor"] in sanctioning:
                census["sanctioned-no-manifest"] += 1
            else:
                _fail(out, "seat-integrity", c.seats["path"],
                      f"seat {seat_id!r} holds no manifest node and its executor has no "
                      f"sanctioning exposure row (method sub-agent or pool)")


def find_cycles(graph):
    cycles, state = [], {}

    def walk(node, stack):
        state[node] = 1
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                cycles.append(stack[stack.index(nxt):] + [nxt])
            elif state.get(nxt) is None:
                walk(nxt, stack + [nxt])
        state[node] = 2

    for node in graph:
        if state.get(node) is None:
            walk(node, [node])
    return cycles


def check_task_no_context(c, out, census):
    """M3 — task frontmatter carries NO `context:` field (DELETED, W6/R3).

    It REPLACES the retired `check_context_refs`, which validated the field's
    list shape and resolved its references. Left in place that check would be
    vacuous forever: a field no author may write can never fail a shape test,
    and a green run over a surface that cannot exist is the false green this
    tool exists to catch. So the check is not disabled — it is REPLACED by the
    refusal, on the same M3 slot and the same `tasks` surface.

    The pointer CONTENT is never silently dropped: it moves into the task's own
    `<scope>` read surface, which is where a task already says what it reads.
    (`<resources>` is a PROMPT unit — the requirement matrix makes it n-a on a
    task file, so the pointers cannot land there.)

    ⚠ `<scope>` is the RULED destination, not merely the one the W6 builder
    chose. The W6 task file directed the pointers to `<resources>`; the builder
    deviated for the two reasons above and migrated 32 files across 3
    components (rbtv `791553a4`, vault `408f7c5d6`). The owner RATIFIED the
    `<scope>` deviation on 2026-08-15 (closeout R5.1). Nothing is re-migrated,
    and any text still naming `<resources>` as the pointers' home is stale.

    WARN, not FAIL, on an already-MATERIALIZED seat.md: live descriptors carry
    the field from before the deletion and a re-render drops it
    (`materialize-seats.py#RETIRED_DESCRIPTOR_KEYS`). This check reads tasks and
    components, where it REFUSES."""
    census["task-context"] = 0
    if not c.tasks:
        _fail(out, "task-no-context", c.root / "tasks", "discovered 0 task files — nothing was checked")
        return
    for stem, item in c.tasks.items():
        if "context" not in item["fm"]:
            continue
        census["task-context"] += 1
        _fail(out, "task-no-context", item["path"],
              "context: is a DELETED task field (W6/R3) — a task names what it reads in its "
              "own <scope>, and the paired prompt names its instruments in <resources>. "
              "Move the pointers, never drop them")


def check_task_no_capabilities(c, out, census):
    """M4 — task frontmatter carries NO `capabilities:` field (retired,
    d-task-capabilities-retired): means are identified at prompt-authoring
    (`exposes:` / `<resources>`) and by the resource-definer/mechanizer
    toolsmith flow, never declared task-side."""
    if not c.tasks:
        _fail(out, "task-no-capabilities", c.root / "tasks", "discovered 0 task files — nothing was checked")
        return
    for stem, item in c.tasks.items():
        if "capabilities" in item["fm"]:
            _fail(out, "task-no-capabilities", item["path"],
                  "capabilities: is a retired task field (d-task-capabilities-retired) — "
                  "the paired prompt's exposes:/<resources> carry the means")


def kg_matrix(kg_cmd):
    """The Requirement matrix as the KG record states it: {carrier: {tag: status}}.
    Raises Precondition when the record cannot be read — never a silent skip."""
    # Resolve the binary through PATH ourselves: Windows CreateProcess does NOT
    # apply PATHEXT, so a `sd-graph.cmd` sitting on PATH is invisible to a
    # shell=False subprocess and raises WinError 2 (IPH-22). shutil.which DOES
    # honor PATHEXT, and on POSIX it just returns the symlink's path — one
    # cross-platform answer, no platform branch. Unresolvable -> leave the argv
    # as authored so the existing OSError arm raises its Precondition unchanged.
    resolved = shutil.which(kg_cmd[0])
    argv = ([resolved] if resolved else kg_cmd[:1]) + kg_cmd[1:]
    try:
        proc = subprocess.run(argv + ["show", "cognitive unit"], capture_output=True, text=True)
    except OSError as exc:
        raise Precondition(f"cannot run the KG query {kg_cmd}: {exc}") from exc
    if proc.returncode != 0:
        raise Precondition(f"KG query failed (exit {proc.returncode}): {proc.stderr.strip()}")
    parsed = {"prompt": {}, "task": {}}
    for line in proc.stdout.splitlines():
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0].startswith("Cognitive-unit") or cells[0].startswith("-"):
            continue
        kind = cells[0]
        if kind.startswith("↳"):
            continue  # nested sub-kind: M6's subject, not a top-level section
        tag = KIND_TAGS.get(kind)
        if tag is None:
            continue
        for carrier, col in (("prompt", 3), ("task", 4)):
            if cells[col] in ("required", "optional"):
                parsed[carrier][tag] = cells[col]
    if not parsed["prompt"] or not parsed["task"]:
        raise Precondition("KG requirement matrix not found in the `cognitive unit` record")
    return parsed


def guide_order(c, carrier):
    """The canonical order as the kind guide's section-order line states it, or
    None if absent. Anchored on the "… in this order:" heading and the arrow
    line directly under it — NEVER a first-match scan over the whole file: an
    unrelated bullet carrying three backticked tags plus an arrow once won that
    scan and the check indicted the hardcoded constant (task 7.646)."""
    guide = c.home / "references" / ("file-prompt.md" if carrier == "prompt" else "file-task.md")
    if not guide.is_file():
        return None
    lines = read_text(guide, "kind guide").splitlines()
    for i, line in enumerate(lines):
        if "in this order:" not in line:
            continue
        for follow in lines[i + 1:i + 4]:  # the order line sits within a blank line or two
            tags = re.findall(r"`<([a-z][a-z0-9-]*)>`", follow)
            if tags and "→" in follow:
                return tags
        return None  # anchor present but no order line under it
    return None


def check_kind_sections(c, out, census, kg_cmd):
    """M5 — kind-section presence · order · uniqueness vs the requirement matrix."""
    live = kg_matrix(kg_cmd)
    for carrier in ("prompt", "task"):
        if live[carrier] != MATRIX[carrier]:
            _fail(out, "kind-sections", "component_lint.py",
                  f"requirement-matrix cross-check ({carrier}): hardcoded {MATRIX[carrier]} != "
                  f"KG record {live[carrier]} — update this file from the record, never the reverse")
        declared = guide_order(c, carrier)
        if declared is None:
            _fail(out, "kind-sections", c.home / "references",
                  f"no {carrier} kind guide to cross-check the section order against")
        elif declared != ORDER[carrier]:
            _fail(out, "kind-sections", "component_lint.py",
                  f"section-order cross-check ({carrier}): hardcoded {ORDER[carrier]} != guide {declared}")

    census["sections"] = 0
    for carrier, pool in (("prompt", c.prompts), ("task", c.tasks)):
        if pool is None:
            continue
        if not pool:
            _fail(out, "kind-sections", c.root / f"{carrier}s", f"discovered 0 {carrier} files — nothing was checked")
            continue
        rules, order = MATRIX[carrier], ORDER[carrier]
        for stem, item in pool.items():
            found = sections_of(item["text"])
            census["sections"] += len(found)
            counts, seq = {}, []
            for tag, _attrs, line, body in found:
                if body is None:
                    _fail(out, "kind-sections", f"{item['path']}:{line}", f"<{tag}> is never closed")
                    continue
                counts[tag] = counts.get(tag, 0) + 1
                seq.append(tag)
            if not found:
                _fail(out, "kind-sections", item["path"], "no kind-named sections found — nothing was checked")
                continue
            for tag, n in sorted(counts.items()):
                if tag not in rules:
                    _fail(out, "kind-sections", item["path"],
                          f"<{tag}> is n-a for a {carrier} file per the requirement matrix")
                elif n > 1:
                    _fail(out, "kind-sections", item["path"], f"<{tag}> appears {n} times — one section per kind")
            for tag, status in sorted(rules.items()):
                if status == "required" and tag not in counts:
                    _fail(out, "kind-sections", item["path"], f"<{tag}> is required for a {carrier} file and is absent")
            ranked = [order.index(t) for t in seq if t in order]
            if ranked != sorted(ranked):
                _fail(out, "kind-sections", item["path"],
                      f"sections out of canonical order: {seq} (canonical: {order})")


def check_dimension_roster(c, out, census):
    """M10 — the check-dimension roster is one set across three homes."""
    roster = {}
    for stem, item in (c.tasks or {}).items():
        m = DIMENSION_CLAUSE.search(item["text"])
        if m:
            roster[stem] = m.group(1)
    census["dimensions"] = len(roster)
    if not roster:
        # Vacuity tripwire, scoped (7.625): the sign a check SWARM exists is a
        # check-* task held by a MANIFEST ROW — the same sign the converse
        # branch at the end of this check uses. Zero dimension clauses under
        # that sign means the clause parse broke. A check-* task STEM alone is
        # NOT the sign: a component may hold a lone check-* task that is no
        # dimension at all (planning's `check-unblocked`, a judge-pool seat
        # with no manifest node, after the check swarm was retired), and a
        # component with no check rows at all (master) has no roster to check
        # and passes clean.
        swarm_seats = {r["seat"] for m in (c.manifests or []) for r in m["rows"]}
        if any(row["task"].startswith("check-") and row["seat-id"] in swarm_seats
               for row in (c.seats["rows"] if c.seats else [])):
            _fail(out, "dimension-roster", c.root / "tasks",
                  "check-* task files exist but 0 carry a dimension clause — nothing was checked")
        return

    # Same multi-need hazard as exposes-body-match: needs ("tasks","seats.csv"),
    # so c.seats may be None (no seats.csv FILE) while tasks carry the run. The
    # roster's PAIRING half is then not applicable — the task-side kill-criteria
    # half below still runs. A seats.csv that EXISTS with no rows is not this
    # case: by_task stays empty and the "paired by 0 seat rows" FAIL fires.
    all_seats = c.seats["rows"] if c.seats else []
    by_task = {}
    for row in all_seats:
        by_task.setdefault(row["task"], []).append(row)
    manifest_rows = {r["seat"]: (m["path"], r)
                     for m in (c.manifests or []) for r in m["rows"]}

    for task, dimension in sorted(roster.items()):
        item = c.tasks[task]
        body = next((b for tag, _a, _l, b in sections_of(item["text"]) if tag == "done-contract"), None)
        criteria = []
        if body:
            after = body.split("Kill criteria", 1)
            if len(after) == 2:
                for line in after[1].splitlines()[1:]:
                    if line.startswith("- "):
                        criteria.append(line)      # the contiguous bullet run
                    elif line.strip() or criteria:
                        break                      # the next prose header, or the run's end
        if not criteria:
            _fail(out, "dimension-roster", item["path"], "kill-criteria block is empty or absent")

        if c.seats is None:
            continue  # no seats.csv surface — nothing to pair this task against
        seat_rows = by_task.get(task, [])
        if len(seat_rows) != 1:
            _fail(out, "dimension-roster", c.seats["path"],
                  f"dimension task {task!r} is paired by {len(seat_rows)} seat rows, expected exactly 1")
            continue
        seat = seat_rows[0]
        if dimension not in seat["description"]:
            _fail(out, "dimension-roster", f"{c.seats['path']}:{seat['line']}",
                  f"seat {seat['seat-id']!r} description names no dimension {dimension!r}")
        if c.manifests is None:
            continue
        if seat["seat-id"] not in manifest_rows:
            _fail(out, "dimension-roster", c.seats["path"],
                  f"dimension seat {seat['seat-id']!r} holds no manifest row")
            continue
        path, row = manifest_rows[seat["seat-id"]]
        if dimension not in row["io"]:
            _fail(out, "dimension-roster", f"{path}:{row['line']}",
                  f"manifest i/o cell names no dimension {dimension!r}")

    # converse: a manifest check row that declares no dimension at all
    for seat_id, (path, row) in sorted(manifest_rows.items()):
        seat = next((s for s in all_seats if s["seat-id"] == seat_id), None)
        if seat and seat["task"].startswith("check-") and seat["task"] not in roster:
            _fail(out, "dimension-roster", f"{path}:{row['line']}",
                  f"check row {seat_id!r} whose task {seat['task']!r} declares no dimension clause")


def check_carried_blocks(c, out, census):
    """M7 — byte-diff EVERY `source=`-attributed carried block against its
    source, generalizing the ethos-specific checker's proven logic."""
    census["carried-blocks"] = 0
    for path in c.markdown:
        text = read_text(path, "markdown")
        if NEAR_MISS_SOURCE.search(text):
            _fail(out, "carried-blocks", path,
                  "a source= attribute in a non-double-quoted form — the carried-block "
                  "convention is source=\"<path>[#anchor]\"")
        for tag, attrs, line, body in sections_of(text):
            m = SOURCE_ATTR.search(attrs or "")
            if not m:
                continue
            census["carried-blocks"] += 1
            where = f"{path}:{line}"
            if body is None:
                _fail(out, "carried-blocks", where, f"carried <{tag}> is never closed")
                continue
            ref, _, anchor = m.group(1).partition("#")
            source = c.resolve(ref)
            if source is None:
                _fail(out, "carried-blocks", where, f"carried-block source does not resolve: {ref!r}")
                continue
            name = anchor or Path(ref).stem
            start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
            lines = read_text(source, "carried source").splitlines()
            try:
                i, j = lines.index(start), lines.index(end, lines.index(start) + 1)
            except ValueError:
                _fail(out, "carried-blocks", where,
                      f"markers {start} / {end} malformed or absent in {source}")
                continue
            blines = body.splitlines()
            try:
                bi, bj = blines.index(start), blines.index(end, blines.index(start) + 1)
            except ValueError:
                _fail(out, "carried-blocks", where,
                      f"carrier lacks {start} / {end} around its copy — the carried block is "
                      "marker-delimited; carrier-local content lives below the end marker")
                continue
            canonical, copy = normalize("\n".join(lines[i + 1:j])), normalize("\n".join(blines[bi + 1:bj]))
            if canonical != copy:
                diff = "\n".join(difflib.unified_diff(canonical.splitlines(), copy.splitlines(),
                                                      fromfile=str(source), tofile=str(path), lineterm=""))
                _fail(out, "carried-blocks", where, f"carried <{tag}> has DRIFTED from {source}\n{diff}")


def check_interactive_fallback(c, out, census):
    """M9 — the typed `fallback:` field, and its correspondence with the
    `human-interactive` flag and the manifest's interactive modality."""
    census["interactive-prompts"] = 0
    if not c.prompts:
        _fail(out, "interactive-fallback", c.root / "prompts", "discovered 0 prompt files — nothing was checked")
        return
    interactive_executors = set()
    if c.seats and c.manifests:
        by_seat = {s["seat-id"]: s for s in c.seats["rows"]}
        for manifest in c.manifests:
            for row in manifest["rows"]:
                if row["modality"] == "interactive" and row["seat"] in by_seat:
                    interactive_executors.add(by_seat[row["seat"]]["executor"])

    for stem, item in sorted(c.prompts.items()):
        flag = str(item["fm"].get("human-interactive", "")).lower() in ("yes", "true")
        arm = item["fm"].get("fallback")
        if flag:
            census["interactive-prompts"] += 1
            if not arm:
                _fail(out, "interactive-fallback", item["path"],
                      "human-interactive: yes with no fallback: field — every interactive seat "
                      f"names its autonomous arm ({'|'.join(FALLBACK_ARMS)})")
            elif arm not in FALLBACK_ARMS:
                _fail(out, "interactive-fallback", item["path"],
                      f"fallback: {arm!r} is outside {list(FALLBACK_ARMS)}")
        elif arm:
            if stem in interactive_executors:
                if arm not in FALLBACK_ARMS:
                    _fail(out, "interactive-fallback", item["path"],
                          f"fallback: {arm!r} is outside {list(FALLBACK_ARMS)}")
            else:
                _fail(out, "interactive-fallback", item["path"],
                      "fallback: present with neither human-interactive: yes nor an "
                      "interactive-modality manifest row")
        elif stem in interactive_executors:
            _fail(out, "interactive-fallback", item["path"],
                  "an interactive-modality manifest row's prompt carries no human-interactive: yes")
        if arm == "block-and-queue" and not any(
                tag == "procedure" and body and AUTONOMOUS_ARM in body
                for tag, _a, _l, body in sections_of(item["text"])):
            _fail(out, "interactive-fallback", item["path"],
                  f"fallback: block-and-queue with no {AUTONOMOUS_ARM!r} step in <procedure> — "
                  "in autonomous mode the ask parks, nobody answers and the engine does not hold, "
                  "so this arm IS the workaround and the procedure carries it in its own words")


def check_declared_mode_carry(c, out, census):
    """The owner's confirmed default execution mode survives into a workflow
    definition PRODUCED by a planned taskforce.

    The assembler drafts the declaration only where planning itself writes the
    definition; on a scaffolding-output run the produced taskforce authors
    `workflow.md` as normal work, and nothing downstream of the task text
    carries the field. This is the edge check that task text names. Absent on
    BOTH sides stays legal — the creation path derives from the Modality
    column — so the check indicts a DROPPED value and an INVENTED one alike,
    never the absence itself."""
    goal_md = c.goal if c.goal.is_file() else c.goal / "goal.md"
    if not goal_md.is_file():
        raise Precondition(f"--goal names no goal.md: {goal_md}")
    match = DECLARED_MODE.search(read_text(goal_md, "goal.md"))
    declared = match.group(1) if match else None
    census["produced-workflows"] = 0
    for name in c.produced:
        path = c.root / "workflows" / name / "workflow.md"
        if not path.is_file():
            _fail(out, "declared-mode-carry", path,
                  f"--workflow {name} names no workflow definition on disk")
            continue
        census["produced-workflows"] += 1
        fm = parse_frontmatter(read_text(path, "workflow definition"), str(path))
        carried = fm.get("default-execution-mode")
        carried = str(carried) if carried is not None else None
        if declared and carried is None:
            _fail(out, "declared-mode-carry", path,
                  f"{goal_md} declares default-execution-mode: {declared} — the produced "
                  "workflow definition declares none, so the owner's confirmed default was "
                  "DROPPED and every goal born from this workflow will derive instead")
        elif declared and carried != declared:
            _fail(out, "declared-mode-carry", path,
                  f"declares default-execution-mode: {carried} — {goal_md} carries "
                  f"{declared}; the declaration is verbatim or it is wrong")
        elif not declared and carried is not None:
            _fail(out, "declared-mode-carry", path,
                  f"declares default-execution-mode: {carried} while {goal_md} declares "
                  "none — an invented declaration outranks the Modality derivation nobody "
                  "asked it to override")
    if not census["produced-workflows"]:
        _fail(out, "declared-mode-carry", c.root / "workflows",
              "discovered 0 produced workflow definitions — nothing was checked")


def declared_json_outputs(text):
    """[(token, {stated field})] — every `.json` artifact a prompt declares in its
    `<io-spec>` `## Outputs` section; None when there is no such section at all.

    The section anchor, the backtick-and-slash artifact grammar, and the
    JSON-only field surface are the EDGE RUNNER's, mirrored: a declaration this
    cannot read is one the runner cannot read either. The field NAMES are the
    authored convention (references/kind-io-spec.md): backticked bare tokens
    sharing the artifact's bullet."""
    io = next((b for tag, _a, _l, b in sections_of(text) if tag == "io-spec"), None)
    if not io:
        return None
    section = OUTPUTS_SECTION.search(io)
    if not section:
        return None
    found = []
    for bullet in re.split(r"^(?=- )", section.group(1), flags=re.M):
        fields = set(FIELD_TOKEN.findall(bullet))
        found.extend((tok, fields) for tok in DECLARED_PATH.findall(bullet)
                     if tok.lower().endswith(".json"))
    return found


def check_fork_discharge(c, out, census):
    """M12 — every guarded manifest edge is DISCHARGEABLE at the edge runner.

    A guard `pred[key=value]` is read off `pred`'s VALIDATED OUTPUT: the runner
    takes the artifacts declared under the predecessor prompt's `## Outputs`
    heading, keeps the `.json` ones, and looks for `key` among their top-level
    fields. A predecessor whose outputs are prose the parser cannot read declares
    NOTHING, serves no key, and the guard reads UNEVALUABLE forever — the fork
    neither opens nor dies. The defect is static, in the authored files, so it is
    caught here rather than by a run that hangs.

    An alternate is checked LIMB BY LIMB: a guarded limb needs its key served, a
    bare limb declares no field and needs nothing."""
    census["guards"] = 0
    seats = {s["seat-id"]: s for s in (c.seats["rows"] if c.seats else [])}
    guardish = False
    for manifest in c.manifests or []:
        for row in manifest["rows"]:
            where = f"{manifest['path']}:{row['line']}"
            for member in split_outside_brackets(row["after"], ","):
                guardish = guardish or "[" in member
                for limb in split_outside_brackets(member, "|"):
                    m = GUARD.match(limb)
                    if not m or not m.group(2):
                        continue  # unparseable (M2's finding) or bare — it needs no key
                    ref, key = m.group(1), m.group(2)
                    census["guards"] += 1
                    seat = seats.get(ref)
                    prompt = (c.prompts or {}).get(seat["executor"]) if seat else None
                    if prompt is None:
                        continue  # a dangling ref or executor is M2's finding, not a second one
                    declared = declared_json_outputs(prompt["text"])
                    head = f"row {row['seat']!r} member {member!r} -> {prompt['path']}"
                    if declared is None:
                        _fail(out, "fork-discharge", where,
                              f"{head}: no `## Outputs` heading inside <io-spec> — it declares "
                              f"NOTHING to the edge runner, so the guard {key!r} can never be served")
                    elif not declared:
                        _fail(out, "fork-discharge", where,
                              f"{head}: `## Outputs` declares no `.json` artifact (a declared "
                              "artifact is a backticked token carrying a `/` and an extension) — "
                              f"guard fields are read off JSON top-level fields only, so {key!r} "
                              "is unservable")
                    elif not any(key in fields for _tok, fields in declared):
                        _fail(out, "fork-discharge", where,
                              f"{head}: declares {sorted(t for t, _f in declared)} but states no "
                              f"top-level field {key!r} on any of them — the guard stays "
                              "UNEVALUABLE and this edge blocks forever")
    if guardish and not census["guards"]:
        _fail(out, "fork-discharge", c.root / "workflows",
              "manifest after-cells carry guard syntax but 0 guards parsed — nothing was checked")


ETHOS_BLOCK = re.compile(r"<!--\s*ethos:start\s*-->.*?<!--\s*ethos:end\s*-->", re.S)
# Owner-ruled standing checkout grant: every seat declares it, few name it in
# prose, and it is never drift.
COORDINATE_GRANT = "rbtv:ignite/coordinate"
# The exposure methods whose part-id is an instrument a prompt BODY would name.
# Direction 1 (declared-but-unused) covers all three; direction 2
# (used-but-undeclared) is scoped tighter — measured 2026-08-12 over the live
# pool: workflow part-ids ("planning", "forge") and skill-method parts match
# ordinary prose vocabulary, not invocations, so direction 2 reads only
# method=path parts (distinctive CLI names) and method=sub-agent parts on
# lines that talk dispatch.
BODY_METHODS = ("sub-agent", "skill", "path")
D2_DISPATCH_CONTEXT = re.compile(r"\b(dispatch|fan)", re.I)


def prompt_body(text):
    """Everything below the frontmatter. The frontmatter is already validated by
    the pool loader, so a missing terminator here means the whole file is body."""
    end = text.find("\n---\n", 3) if text.startswith("---\n") else -1
    return text[end + 5:] if end != -1 else text


def check_exposes_body_match(c, out, census):
    """`exposes:` and the prompt BODY name the same instruments, both ways.

    Declared-but-unused: an entry nobody mentions is a grant that outlived the
    procedure that needed it. Used-but-undeclared: a prompt that names an
    instrument it was never granted instructs a caged seat to run what it cannot
    reach (the measured `coordinate` gap, 2026-08-10).

    ponytail: substring / word-boundary heuristics, not a parser — this is a
    drift tripwire. A name mentioned only inside a code fence, a URL, or an
    unrelated English word ("path", "writer") reads as a mention and silences
    direction 1; upgrade to a prose/code-fence split only if that measurably
    hides real drift."""
    census["exposes-entries"] = 0
    # Multi-need check: run() starts it when ANY of ("prompts","exposure.csv")
    # is present, so c.prompts may be None (no prompts/ FOLDER — the sanctioned
    # prompt-less shape, web/browse) while exposure.csv carries the run. None is
    # NOT applicable; {} is a present-but-empty pool and stays a census FAIL.
    if c.prompts is None:
        return
    if not c.prompts:
        _fail(out, "exposes-body-match", c.root / "prompts",
              "discovered 0 prompt files — nothing was checked")
        return
    instruments = {r["fields"][0].strip(): r["fields"][2].strip()
                   for r in (c.exposure["rows"] if c.exposure else [])
                   if len(r["fields"]) == len(EXPOSURE_HEADER)}
    kinds = {r["fields"][0].strip(): r["fields"][1].strip()
             for r in (c.exposure["rows"] if c.exposure else [])
             if len(r["fields"]) == len(EXPOSURE_HEADER)}
    # ponytail: direction 2 skips method=skill and part-kind=workflow rows —
    # their names double as prose vocabulary; direction 1 still covers them.
    body_instruments = sorted(
        p for p, m in instruments.items()
        if p and m in ("path", "sub-agent") and kinds.get(p) != "workflow")

    for stem, item in sorted(c.prompts.items()):
        body = prompt_body(item["text"])
        lowered = body.lower()
        groups = item["fm"].get("exposes") or {}
        if not isinstance(groups, dict):
            _fail(out, "exposes-body-match", item["path"],
                  f"exposes: is a {type(groups).__name__}, not a mapping of method -> part-ids")
            continue
        declared = set()
        for key, entries in sorted(groups.items()):
            for entry in (entries if isinstance(entries, list) else [entries]):
                entry = str(entry).strip()
                census["exposes-entries"] += 1
                name = entry.rsplit("/", 1)[-1]
                declared.add(name)
                if key == "path" and entry == COORDINATE_GRANT:
                    continue  # standing checkout grant — exempt by owner ruling
                if name.lower() not in lowered:
                    _fail(out, "exposes-body-match", item["path"],
                          f"exposes.{key} declares {entry!r} but the body never names "
                          f"{name!r} — a grant no procedure uses")

        # Direction 2 reads the body MINUS the carried ethos block: the ethos is
        # copied verbatim into every prompt, so a name it happens to carry is
        # not this prompt's own use.
        own = ETHOS_BLOCK.sub("", body)
        for part in body_instruments:
            if part == stem or part in declared:
                continue
            hits = [m for m in re.finditer(r"\b" + re.escape(part) + r"\b", own, re.I)]
            if instruments[part] == "sub-agent":
                # A sub-agent part-id ("writer") is also an English word; count
                # only mentions on a line that talks dispatch/fan-out.
                hits = [m for m in hits
                        if D2_DISPATCH_CONTEXT.search(
                            own[own.rfind("\n", 0, m.start()) + 1:
                                (own.find("\n", m.end()) if own.find("\n", m.end()) != -1
                                 else len(own))])]
            if hits:
                _fail(out, "exposes-body-match", item["path"],
                      f"body names the instrument {part!r} (exposure.csv "
                      f"method={instruments[part]}) but no exposes: group declares it — "
                      "a caged seat cannot reach what it was not granted")


RESOURCES_BULLET_CAP = 280
RESOURCES_INSTRUMENT_METHODS = ("path", "skill", "sub-agent")
# The optional `**` is not cosmetic tolerance: a bold-wrapped part-id is live
# house style (office/meeting-summarizer), and a token regex blind to it reads
# the bullet as naming no instrument — which silently lifts the 280-char cap on
# exactly the bullets it should measure.
BULLET_LEAD_TOKEN = re.compile(r"^\*{0,2}`([^`]+)`\*{0,2}")

# Owner-ruled 2026-08-12 (references/workflow-authoring-checklist.md §2): two
def resources_bullets(body):
    """[(raw_chunk, leading_token_or_None, measured_text)] for each top-level
    `- ` bullet in a <resources> section body. `measured_text` has the
    leading `- ` and the leading backtick-wrapped token (if any) stripped,
    per the checklist's bullet shape (`` - `<part-id>` <description> ``) —
    prose before the first bullet (a section intro) is not a bullet."""
    out = []
    for chunk in re.split(r"^(?=- )", body, flags=re.M):
        chunk = chunk.strip("\n")
        if not chunk.startswith("- "):
            continue
        text = chunk[2:]
        m = BULLET_LEAD_TOKEN.match(text)
        token = m.group(1) if m else None
        measured = text[m.end():] if m else text
        out.append((chunk, token, measured.strip()))
    return out


def check_resources_coverage(c, out, census):
    """Owner-ruled 2026-08-12 (workflow-authoring-checklist.md §2): every
    `exposes:` entry of method path/skill/sub-agent ALSO gets its own bullet
    inside the prompt's <resources> section, at most 280 characters — prose
    a materializer-bound grant is not prose an OCCUPANT reads. Exempt: the
    standing `rbtv:ignite/coordinate` checkout grant, and every
    command/rule/hook entry (those arrive as standing behaviour, never a
    chosen instrument) — same exemptions check_exposes_body_match carries."""
    census["resources-entries"] = 0
    census["resources-bullets"] = 0
    if not c.prompts:
        _fail(out, "resources-coverage", c.root / "prompts",
              "discovered 0 prompt files — nothing was checked")
        return
    for stem, item in sorted(c.prompts.items()):
        groups = item["fm"].get("exposes") or {}
        if not isinstance(groups, dict):
            continue  # exposes-body-match already indicts the malformed shape
        declared = []
        for key in RESOURCES_INSTRUMENT_METHODS:
            for entry in groups.get(key) or []:
                entry = str(entry).strip()
                if key == "path" and entry == COORDINATE_GRANT:
                    continue  # standing checkout grant — exempt by owner ruling
                declared.append((key, entry, entry.rsplit("/", 1)[-1]))
        census["resources-entries"] += len(declared)

        section = next((b for tag, _a, _l, b in sections_of(item["text"]) if tag == "resources"), None)
        if declared and section is None:
            _fail(out, "resources-coverage", item["path"],
                  f"exposes: declares {len(declared)} path/skill/sub-agent instrument(s) but "
                  "the prompt carries no <resources> section at all — the occupant has no "
                  "bullet telling it when or why to reach for any of them")
            continue
        if section is None:
            continue

        bullets = resources_bullets(section)
        census["resources-bullets"] += len(bullets)
        for key, entry, part_id in declared:
            if not re.search(r"\b" + re.escape(part_id) + r"\b", section, re.I):
                _fail(out, "resources-coverage", item["path"],
                      f"exposes.{key} declares {entry!r} but no bullet inside <resources> "
                      f"names {part_id!r} — the RESOURCES SECTION specifically (distinct from "
                      "exposes-body-match, which reads the whole prompt body): the occupant "
                      "has no prose on when or why to reach for it")

        # The cap is the RULE's cap, and the rule caps the description of a
        # DECLARED instrument — not every bullet a <resources> section carries.
        # A section may also hold prose about a file, a folder, or a standing
        # output contract; that prose answers to no ceiling, and measuring it
        # here would invent a rule the checklist never states. No grandfather
        # list exists, deliberately: an instrument bullet over the cap is
        # trimmed, and a fact that cannot survive the trim moves to the
        # <procedure> step or <restrictions> line that owns it.
        declared_tokens = {part_id.lower() for _k, _e, part_id in declared}
        for _raw, token, measured in bullets:
            n = len(measured)
            names_instrument = token is not None and (
                token.rsplit("/", 1)[-1].lower() in declared_tokens)
            if n <= RESOURCES_BULLET_CAP or not names_instrument:
                continue
            _fail(out, "resources-coverage", item["path"],
                  f"<resources> bullet {(token or measured[:40])!r} measures {n} characters, "
                  f"over the {RESOURCES_BULLET_CAP}-character ceiling (280 is a ceiling, not a "
                  "target — trim it, don't grandfather it)")


CHECKS = [
    ("exposure-canon", ("exposure.csv",), "M1 exposure-manifest canon + entry-point existence"),
    ("seat-integrity", ("seats.csv",), "M2 seat/manifest integrity, orphans, modality, acyclicity"),
    ("task-no-context", ("tasks",), "M3 task files carry no deleted context: field"),
    ("task-no-capabilities", ("tasks",), "M4 task files carry no retired capabilities: field"),
    ("kind-sections", ("prompts", "tasks"), "M5 kind-section presence/order/uniqueness vs the KG matrix"),
    ("dimension-roster", ("tasks", "seats.csv"), "M10 check-dimension roster coverage"),
    ("carried-blocks", ("*.md",), "M7 byte-diff of every source= carried block"),
    ("interactive-fallback", ("prompts",), "M9 human-interactive <-> fallback: <-> interactive modality"),
    ("declared-mode-carry", ("--goal + --workflow",),
     "M11 produced workflow.md carries goal.md's default-execution-mode verbatim"),
    ("fork-discharge", ("workflows",),
     "M12 every manifest guard is served by its predecessor's declared ## Outputs"),
    ("exposes-body-match", ("prompts", "exposure.csv"),
     "exposes: entries and the prompt body name the same instruments, both ways"),
    ("resources-coverage", ("prompts",),
     "workflow-authoring-checklist §2: every exposes path/skill/sub-agent entry gets its own "
     "<=280-char <resources> bullet"),
]

RUNNERS = {
    "exposure-canon": check_exposure_canon, "seat-integrity": check_seat_integrity,
    "task-no-context": check_task_no_context, "task-no-capabilities": check_task_no_capabilities,
    "dimension-roster": check_dimension_roster, "carried-blocks": check_carried_blocks,
    "interactive-fallback": check_interactive_fallback,
    "declared-mode-carry": check_declared_mode_carry,
    "fork-discharge": check_fork_discharge,
    "exposes-body-match": check_exposes_body_match,
    "resources-coverage": check_resources_coverage,
}


def surface_present(c, name):
    return {"exposure.csv": c.exposure is not None, "seats.csv": c.seats is not None,
            "prompts": c.prompts is not None, "tasks": c.tasks is not None,
            "*.md": bool(c.markdown), "workflows": c.manifests is not None,
            # Both halves, never one: the pairing IS the surface. Naming no
            # produced workflow would silently widen the check to definitions
            # this goal never produced, and every one of those would fail.
            "--goal + --workflow": bool(c.goal and c.produced)}[name]


# ------------------------------------------------------------------------ main

def lint_component(component, args):
    """Build a Component at `component` and run the selected checks once.
    Returns the raw result dict; printing and exit-code policy stay with the
    caller (run() for one component, sweep() for --all) so both share this
    without duplicating the check loop."""
    c = Component(component, args.root, args.cards_root, args.home,
                  args.goal, args.workflow)
    census = {"prompts": len(c.prompts or {}), "tasks": len(c.tasks or {}),
              "seats": len(c.seats["rows"]) if c.seats else 0,
              "manifests": len(c.manifests or []),
              "manifest-rows": sum(len(m["rows"]) for m in c.manifests or []),
              "exposure-rows": len(c.exposure["rows"]) if c.exposure else 0,
              "references": len(c.references or []), "capabilities": len(c.capabilities or []),
              "markdown-files": len(c.markdown)}
    selected = set(args.check) if args.check else {cid for cid, _, _ in CHECKS}
    unknown = selected - {cid for cid, _, _ in CHECKS}
    if unknown:
        raise Precondition(f"unknown check id(s): {sorted(unknown)}")

    findings, ran, skipped, blocked = [], [], [], []
    for cid, needs, _desc in CHECKS:
        if cid not in selected:
            continue
        if not any(surface_present(c, n) for n in needs):
            skipped.append({"check": cid, "reason": f"none of {list(needs)} present/declared for this run"})
            continue
        # Per-check boundary. A Precondition raised INSIDE a check used to unwind
        # past the print block into main(), which discarded the census line AND
        # every finding the earlier checks had already accumulated — one broken
        # surface silenced the whole run. BLOCKED is not SKIP: skipped means "not
        # applicable" and exits 0; blocked means "applicable and did not run", and
        # keeps exit 2, or the tool manufactures the false green it exists to catch.
        try:
            if cid == "kind-sections":
                check_kind_sections(c, findings, census, args.kg)
            else:
                RUNNERS[cid](c, findings, census)
        except Precondition as exc:
            blocked.append({"check": cid, "reason": str(exc)})
            continue
        ran.append(cid)

    return {"component": str(c.root), "census": census, "checks-run": ran,
            "checks-skipped": skipped, "checks-blocked": blocked, "findings": findings}


def print_component_result(result):
    fails = [f for f in result["findings"] if f["severity"] == "FAIL"]
    print(f"component-lint: {result['component']}")
    print("census: " + " ".join(f"{k}={v}" for k, v in result["census"].items()))
    for entry in result["checks-skipped"]:
        print(f"  SKIP {entry['check']}: {entry['reason']}")
    for entry in result["checks-blocked"]:
        print(f"  BLOCKED {entry['check']}: {entry['reason']}")
    for f in result["findings"]:
        print(f"  {f['severity']} [{f['check']}] {f['where']}: {f['message']}")
    census = result["census"]
    print(f"component-lint: {len(result['checks-run'])} check(s) run, "
          f"{len(result['checks-skipped'])} skipped, {len(result['checks-blocked'])} blocked, "
          f"over {census['prompts']} prompts / {census['tasks']} tasks / {census['seats']} seats / "
          f"{census['manifest-rows']} manifest rows / {census['exposure-rows']} exposure rows "
          f"— {len(fails)} finding(s), {len(result['findings']) - len(fails)} info")
    return fails


def run(args):
    # Half the pairing is an operator error, never a skip: whoever asked for the
    # carry check must get it or an error, never a quiet "not applicable".
    if bool(args.goal) != bool(args.workflow):
        raise Precondition("--goal and --workflow are declared together or not at all")
    result = lint_component(args.component, args)
    fails = [f for f in result["findings"] if f["severity"] == "FAIL"]
    if args.json:
        print(json.dumps({**result, "fail-count": len(fails)}, indent=2))
    else:
        print_component_result(result)
    return 2 if result["checks-blocked"] else (1 if fails else 0)


def find_components(mirror_root):
    """Every directory under `mirror_root` carrying a component.md — "no
    component.md, no component" (sd-graph, component-anatomy.md). Enumerated
    from the tree, never a hand-written list, so a component added later is
    covered without editing this file."""
    return sorted({p.parent for p in mirror_root.rglob("component.md")})


def sweep(args):
    """--all: lint every component discovered under .rbtv/mirror/** (goal-run
    scratch fixtures under .rbtv/goals/** are excluded by construction — that
    tree is never searched). Exits non-zero if ANY component has a finding."""
    # Anchored on --component (default: the same default as single-component
    # mode), never on HOME (this tool's own component) — HOME would always
    # walk to the real repo and make --all untestable against a fixture tree.
    ws = workspace_root(Path(args.component).resolve())
    if ws is None:
        raise Precondition(f"no workspace root (.rbtv/config) found above --component {args.component}")
    mirror_root = ws / ".rbtv" / "mirror"
    if not mirror_root.is_dir():
        raise Precondition(f"no mirror root at {mirror_root}")
    components = find_components(mirror_root)
    if not components:
        raise Precondition(f"discovered 0 components under {mirror_root} — nothing was checked")

    # The legacy tree's exposure.csv files sit at MODULE roots with no
    # component.md, so find_components() silently yields nothing there — say
    # so out loud instead of leaving that absence unexplained.
    legacy = ws / "3-resources" / "tools" / "rbtv"
    legacy_note = None
    if legacy.is_dir():
        legacy_note = (f"legacy tree {legacy} contributes 0 components under this definition "
                       f"({len(list(legacy.glob('*/exposure.csv')))} exposure.csv file(s) sit at "
                       "module roots with no component.md)")

    # Per-COMPONENT boundary, the same shape run() carries per CHECK and for the
    # same reason one level up: an exception escaping ONE component's lint used
    # to unwind past the print block and discard every other component's result,
    # so one malformed component made the whole-workspace sweep report nothing.
    # BLOCKED is not SKIP: skipped means "not applicable", blocked means
    # "applicable and did not run" and keeps exit 2 — never a false green.
    results = []
    for comp in components:
        try:
            results.append(lint_component(comp, args))
        except Exception as exc:
            results.append({
                # Nothing was surveyed, so the census is zeros — the keys the
                # printer's summary line reads, and no more.
                "component": str(comp),
                "census": dict.fromkeys(
                    ("prompts", "tasks", "seats", "manifest-rows", "exposure-rows"), 0),
                "checks-run": [], "checks-skipped": [], "findings": [],
                "checks-blocked": [{"check": "component",
                                    "reason": f"{type(exc).__name__}: {exc}"}]})
    overall_blocked = any(r["checks-blocked"] for r in results)
    overall_fails = any(any(f["severity"] == "FAIL" for f in r["findings"]) for r in results)

    if args.json:
        print(json.dumps({"components": results, "legacy-note": legacy_note,
                          "fail-count": sum(1 for r in results
                                            if any(f["severity"] == "FAIL" for f in r["findings"]))},
                         indent=2))
    else:
        total_fails = 0
        for result in results:
            total_fails += len(print_component_result(result))
        if legacy_note:
            print(f"component-lint: {legacy_note}")
        print(f"component-lint sweep: {len(components)} component(s), "
              f"{sum(1 for r in results if any(f['severity'] == 'FAIL' for f in r['findings']))} "
              f"with a finding, {total_fails} finding(s) total")
    return 2 if overall_blocked else (1 if overall_fails else 0)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="component_lint",
        description="Deterministic lint over an rbtv component folder. Detection only; never writes.",
        epilog="Exit: 0 clean · 1 findings · 2 broken preconditions. "
               "A precondition broken INSIDE a check blocks only that check: it is "
               "reported BLOCKED, the rest still run, and the census and their "
               "findings are still printed — the run exits 2. "
               "A run is accepted on the CENSUS LINE, never on the exit code alone — "
               "a green run over files it failed to discover is a false green.")
    p.add_argument("--component", default="3-resources/tools/rbtv/meta/planning",
                   help="component folder to lint (default: %(default)s)")
    p.add_argument("--all", action="store_true",
                   help="lint EVERY component: enumerated from the tree as every directory "
                        "under .rbtv/mirror/** (of the workspace found by walking up from "
                        "--component) carrying a component.md (.rbtv/goals/** scratch "
                        "fixtures are excluded by construction). --component then anchors "
                        "the workspace search instead of selecting one component. Exits "
                        "non-zero if any component has a finding.")
    p.add_argument("--root", action="append", default=[], metavar="PATH",
                   help="extra root a declared path may resolve against (repeatable). "
                        "The component root and the mirror root are always tried.")
    p.add_argument("--cards-root", default=None, metavar="PATH",
                   help="mirror root declared paths also resolve against "
                        "(default: the component's grandparent)")
    p.add_argument("--home", default=None, metavar="PATH",
                   help="component holding the references the hardcoded vocabularies are "
                        "cross-checked against (default: the component this tool ships in)")
    p.add_argument("--kg", default="sd-graph", metavar="CMD",
                   help="the read-only KG query command the requirement matrix is "
                        "cross-checked against (default: %(default)s)")
    p.add_argument("--goal", default=None, metavar="PATH",
                   help="the goal folder (or goal.md) a workflow-producing run planned; "
                        "with --workflow, enables the declared-mode-carry check")
    p.add_argument("--workflow", action="append", default=[], metavar="NAME",
                   help="a workflow folder name THIS goal produced into the component "
                        "(repeatable); required with --goal, so the check never widens "
                        "onto definitions the goal never produced")
    p.add_argument("--check", action="append", default=[], metavar="ID",
                   help="run only this check (repeatable); see --list-checks")
    p.add_argument("--list-checks", action="store_true", help="print the check roster and exit")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args(argv)
    args.kg = args.kg.split()

    if args.list_checks:
        for cid, needs, desc in CHECKS:
            print(f"{cid:22s} needs {','.join(needs):18s} {desc}")
        return 0
    try:
        return sweep(args) if args.all else run(args)
    except Precondition as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
