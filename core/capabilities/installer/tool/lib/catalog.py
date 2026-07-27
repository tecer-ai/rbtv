"""catalog.py — reading the CMP-5 component databases off a catalog root.

A catalog root is EITHER the rbtv scaffolding repo OR an install's
`.rbtv/mirror/`. They are treated identically and nothing here may branch on
which one it is (CMP-3: moving meta components from `mirror/meta/` into `rbtv/`
later must change nothing about how components work).

Shape read (CMP-5 § layout):

    <root>/<module>/module.md              module entry point (skill format)
    <root>/<module>/<component>/
        component.md                       component entry point
        exposure.csv                       exposure manifest
        prompts.csv  tasks.csv  seats.csv  the catalogs
        prompts/cognitive-units/<kind>/    prompt pool
        tasks/cognitive-units/<kind>/      task pool

VERSION RESOLUTION IS A STAND-IN, PENDING CMP-5. The repo-root
`cognitive-units-index.csv` that CMP-5 specifies does not exist anywhere
(divergence D4 / issue G-109), so `@latest` freezes to
`latest+sha256:<12 hex of the unit's bytes>`. That preserves the assembly
lockfile's FUNCTION — a frozen, verifiable reference — without inventing the
index schema. It is NOT the settled scheme and must not harden into one.

NAME resolution, by contrast, needs no index: every cognitive-unit file declares
its own `id:` in frontmatter, and the catalog's reference id is NOT the file
stem (`master-role` -> `roles/master.md`). The pool is indexed by DECLARED id.
"""
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

STANDIN_VERSION_PREFIX = "latest+sha256:"  # NOT THE SETTLED SCHEMA — see module docstring

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
_ID_LINE = re.compile(r"^id:\s*(.+?)\s*$", re.MULTILINE)
_DESC_LINE = re.compile(r"^description:\s*(.+?)\s*$", re.MULTILINE)


class CatalogError(Exception):
    """A refusal with a named reason — never a guess."""


@dataclass
class Unit:
    unit_id: str
    path: Path
    kind: str  # the pool sub-folder: roles, procedures, io-specs, ...
    side: str  # "prompts" or "tasks"

    def body(self) -> str:
        """The unit's content with its frontmatter stripped."""
        text = self.path.read_text(encoding="utf-8")
        return _FRONTMATTER.sub("", text, count=1).strip()

    def frozen_ref(self) -> str:
        """The stand-in version freeze: content-addressed, index-free."""
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()[:12]
        return f"{STANDIN_VERSION_PREFIX}{digest}"


@dataclass
class Component:
    name: str
    module: str
    path: Path
    entry_point: Path | None = None
    units: dict[str, Unit] = field(default_factory=dict)

    def catalog_rows(self, catalog: str) -> list[dict[str, str]]:
        f = self.path / f"{catalog}.csv"
        if not f.exists():
            return []
        with f.open(newline="", encoding="utf-8") as fh:
            return [dict(r) for r in csv.DictReader(fh)]

    def exposure_rows(self) -> list[dict[str, str]]:
        return self.catalog_rows("exposure")


@dataclass
class Module:
    name: str
    path: Path
    entry_point: Path | None
    components: dict[str, Component] = field(default_factory=dict)


def frontmatter_field(path: Path, pattern: re.Pattern[str]) -> str | None:
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER.match(text)
    if not m:
        return None
    hit = pattern.search(m.group(1))
    return hit.group(1).strip() if hit else None


def unit_id_of(path: Path) -> str | None:
    return frontmatter_field(path, _ID_LINE)


def description_of(path: Path) -> str | None:
    return frontmatter_field(path, _DESC_LINE)


def _index_units(component_dir: Path) -> dict[str, Unit]:
    """Index both pools by the id each unit file DECLARES.

    A duplicate id is a refusal: silently picking one would make assembly depend
    on directory order.
    """
    units: dict[str, Unit] = {}
    for side in ("prompts", "tasks"):
        pool = component_dir / side / "cognitive-units"
        if not pool.is_dir():
            continue
        for f in sorted(pool.rglob("*.md")):
            uid = unit_id_of(f)
            if uid is None:
                raise CatalogError(
                    f"cognitive-unit file declares no `id:` frontmatter: {f} — "
                    "references resolve by declared id, never by filename"
                )
            if uid in units:
                raise CatalogError(
                    f"duplicate cognitive-unit id {uid!r}: {units[uid].path} and {f}"
                )
            units[uid] = Unit(uid, f, f.parent.name, side)
    return units


def discover(root: Path) -> dict[str, Module]:
    """Find every KG-shape module under a catalog root.

    A module is a directory holding `module.md`. Nothing here inspects the root's
    identity — mirror and repo take the identical path.
    """
    if not root.is_dir():
        raise CatalogError(f"--catalog-root is not a directory: {root}")

    modules: dict[str, Module] = {}
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        mod_md = entry / "module.md"
        if not mod_md.exists():
            continue
        module = Module(entry.name, entry, mod_md)
        for sub in sorted(entry.iterdir()):
            if not sub.is_dir():
                continue
            comp_md = sub / "component.md"
            if not comp_md.exists():
                continue
            module.components[sub.name] = Component(
                name=sub.name,
                module=entry.name,
                path=sub,
                entry_point=comp_md,
                units=_index_units(sub),
            )
        modules[entry.name] = module
    return modules


def resolve_ref(component: Component, ref: str) -> tuple[Unit, str]:
    """Resolve one `<unit-id>@<version>` catalog cell to a unit + frozen version.

    Only `@latest` is supported: with no `cognitive-units-index.csv` there is no
    table mapping a pinned version-id to a commit, so accepting a pin would mean
    silently serving whatever is on disk under a name that promises otherwise.
    """
    ref = ref.strip()
    if not ref:
        raise CatalogError("empty cognitive-unit reference")
    if "@" not in ref:
        raise CatalogError(
            f"reference {ref!r} carries no version — expected `<unit-id>@latest`"
        )
    unit_id, version = ref.rsplit("@", 1)
    if version != "latest":
        raise CatalogError(
            f"reference {ref!r} pins version {version!r}, but the repo-root "
            "`cognitive-units-index.csv` (CMP-5) does not exist on this install "
            "(issue G-109), so no version-id can be resolved to a commit. "
            "Only `@latest` is resolvable; this is a STAND-IN pending CMP-5."
        )
    unit = component.units.get(unit_id)
    if unit is None:
        known = ", ".join(sorted(component.units)) or "(pool empty)"
        raise CatalogError(
            f"no cognitive unit declares id {unit_id!r} in component "
            f"{component.module}/{component.name}. Declared ids: {known}"
        )
    return unit, unit.frozen_ref()


# Columns of prompts.csv / tasks.csv that carry cognitive-unit references. The
# remaining columns are metadata, not content, and are never assembled.
_NON_UNIT_COLUMNS = {
    "prompt-id",
    "task-id",
    "seat-id",
    "description",
    "staffing-recommendations",
    "staffing-hints",
    "capabilities",
    "context-pointers",
    "executor",
    "task",
}


def assemble(component: Component, catalog: str, row_id: str) -> tuple[str, dict[str, str]]:
    """Assemble one catalog row into a body, plus its lockfile of frozen refs.

    Content is a file; arrangement is a row (CMP-5). The row's column ORDER is
    the assembly order — authored order, not alphabetical.
    """
    rows = component.catalog_rows(catalog)
    if not rows:
        raise CatalogError(
            f"component {component.module}/{component.name} has no {catalog}.csv"
        )
    id_col = next(iter(rows[0]))  # first column is the row id by CMP-5's shape
    match = [r for r in rows if (r.get(id_col) or "").strip() == row_id]
    if not match:
        ids = ", ".join(sorted((r.get(id_col) or "") for r in rows))
        raise CatalogError(
            f"{catalog}.csv has no row {row_id!r} in "
            f"{component.module}/{component.name}. Rows: {ids}"
        )
    row = match[0]

    parts: list[str] = []
    lock: dict[str, str] = {}
    for col, cell in row.items():
        if col == id_col or col in _NON_UNIT_COLUMNS or not cell:
            continue
        cell = cell.strip()
        if "@" not in cell:
            continue  # a metadata cell that happens to be populated
        unit, frozen = resolve_ref(component, cell)
        lock[unit.unit_id] = frozen
        parts.append(unit.body())
    if not parts:
        raise CatalogError(
            f"row {row_id!r} of {catalog}.csv references no cognitive units"
        )
    return "\n\n".join(parts) + "\n", lock
