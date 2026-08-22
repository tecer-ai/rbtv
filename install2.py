#!/usr/bin/env python3
"""install2.py — the exposure-manifest rbtv installer (supersedes install.py).

Installs components into a workspace by reading their EXPOSURE MANIFESTS
(`exposure.csv`) and realizing each row's canonical method per harness, at the
INSTALL ROOT only. Python 3 stdlib only.

    rbtv install ls                     what is available (+ shadowed)
    rbtv install li                     what is installed (from the state file)
    rbtv install add -c <module>/<component> [--harness a,b] [--target D]
    rbtv install add -m <module> [-x skill] [--artifact CLAUDE.md|AGENTS.md|none]
    rbtv install rm -c <id> | -m <name> | -A
    rbtv install dupe-artifacts         regenerate harness guidance from the basis
    rbtv install interactive            the human flow (also: no arguments)
    rbtv install selftest               the runnable check

    --dry-run and --json on every verb where they mean something.
    Exit codes: 0 success · 1 refusal · 2 usage.

    THE TARGET. `--target D` is explicit and always wins. Without it the
    install root is DISCOVERED by walking upward from the current directory —
    first ancestor holding `.rbtv/config/install.json`, else first ancestor
    holding a `.rbtv/` directory, else the cwd (D24). So a run from anywhere
    inside the workspace finds the workspace, and a run from inside this repo
    finds nothing to install only when the repo really is outside one.

COEXISTENCE. `install.py` + `admin/install/` are untouched and keep working.
This tool never reads or writes their state file (`rbtv.json` at the target
root); its own book is `{target}/.rbtv/config/install.json`. It tolerates files
at the install root it did not write — see D6 and D12. The two installers hold
DISJOINT SETS: this one sees only new-standard component folders (D2), the old
one keeps everything else.

BOUNDARY (core-build `decisions.md#d-materializer-seat-loaders`). The installer
exposes components at the INSTALL ROOT and NEVER writes under `.rbtv/goals/`.
Seat-folder exposure belongs to the materializer (`ignite/team-kit/
materialize-seats.py`), which is not imported here — `ignite/` must stay a
relocatable subtree (repo CLAUDE.md), so the forms below are re-implemented
against CMP-12, the one form authority.

────────────────────────────────────────────────────────────────────────────
DESIGN DECISIONS (delegated to the builder; recorded here as the one home)
────────────────────────────────────────────────────────────────────────────
D1  PLACEMENT — one file at the repo root. No package. The old installer's
    thin-entry + `admin/install/` split earns nothing at this size, and the
    later supersession is then a single `git mv install2.py install.py`.

D2  WHAT A COMPONENT IS — DEPTH-2 + exposure.csv (owner ruling, 2026-08-22)
    — a directory at EXACTLY depth 2 of a scanned tree that contains
    `exposure.csv`. Identity is `<module>/<component>` (two segments), so
    depth 2 is forced by the id scheme. `component.md` is not read, not
    checked, not a marker. A depth-1 manifest (the module-root files of the
    old standard) is invisible here; a depth-3 file is not a component.
    A malformed manifest (columns other than the seven) refuses by name —
    it is never skipped. A directory without `exposure.csv` is not a
    component; there is no no-manifest report. Hub units (`_hub/`) are a
    separate branch (D15) and are untouched by this rule. The two
    installers stay separate: `install.py` + `admin/install/` keep the
    old-standard tree.

D3  TREES + PRECEDENCE — two roots, scanned together: `mirror` =
    `{target}/.rbtv/mirror`, `repo` = the directory holding this file, which
    is NOT overridable — the file and its tree ship together, so a flag
    pointing one at another's tree only ever named a broken pair (owner
    ruling, 2026-08-21). `--mirror-tree` stays. On the same id in both, the
    MIRROR WINS (workspace-local staging is the newer copy by construction) and
    the shadowing is reported, never silent.

D4  HARNESSES — the three launchable ones (claude, codex, opencode);
    `--harness` filters. The standalone kimi CLI was retired 2026-08-14 and
    its models moved under opencode; `cast` lists only these three. Kimi
    models remain reachable as opencode models. CON-2's three-harness bound
    and this tool now agree. A live book that still lists `kimi` is stripped
    on load (kept others, never an empty list) and persisted on the next write.

D5  STATE — `{target}/.rbtv/config/install.json`, recording per component: source
    tree, module, component, harnesses, every whole file written, and every
    shared-file CLAIM held. Uninstall removes exactly that set and nothing else.

D6  COLLISIONS — one rule, at two granularities. A planned WHOLE FILE that
    exists on disk and is not in our book refuses the run, pre-write, zero
    files. A planned KEY inside a shared config file that exists and is not in
    our book refuses the same way. A path or key that IS in our book is ours to
    rewrite (byte-identical → skipped; loaders are derived). This is what
    "tolerate what we did not write" means operationally: we never overwrite a
    stranger's file or key, and we never assume our book is the whole truth.

D7  SHARED FILES — `.mcp.json`, `.claude/settings.json`, `.codex/config.toml`,
    `.codex/hooks.json` and `opencode.json` belong to the whole installed set
    AND may already carry foreign content, so they are never written or deleted
    wholesale (D12). They are recomputed from the whole installed set on every
    install and uninstall; install and uninstall are the same operation on a
    set, followed by one emit.

D8  `agents.md` AND THE GUIDANCE SURFACE (rewritten 2026-08-10 to conform to
    CMP-12, the ONE form authority; the registry is never edited from here) —
    CMP-12's `agents.md` row IS this method's realization: a per-folder guidance
    file whose NAME is keyed by harness (claude `CLAUDE.md`, codex `AGENTS.md`,
    qwen `QWEN.md`, opencode `AGENTS.md`-or-`CLAUDE.md`).
    There is no index file: the earlier `.agents/rbtv2-exposure.md` was an
    invented artifact in no CMP-12 cell, auto-loaded by no harness, and is
    RETIRED — an existing one is removed by the ordinary booked-file machinery
    on the next install or uninstall. Every `agents.md` row and every forced
    rule read is carried by the GENERATED guidance file (D13), inside one fenced
    `rbtv2:start … rbtv2:end` block at its head. The BASIS is still never
    written: whatever block the basis itself would need is REPORTED for the
    human to place, and mirrors from there.

    THE FORCED READ (CMP-12 § Fallback mechanics) is for the harnesses that
    auto-inject no rule folder — Codex and Qwen ONLY. It is emitted into a
    guidance file only when an installed harness of that set reads that file's
    name, and it enumerates the paths those harnesses' rule copies were ACTUALLY
    written to — a rule whose component was installed claude-only exists at
    `.claude/rules/` and is never named to codex, whose MANDATORY Step 0 would
    otherwise point at a file that was never created.
    NEVER for claude (`.claude/rules/` auto-injects), and never for
    opencode, which CMP-12 gives no separate rule type because it reads
    `.claude/` natively — so opencode's `rule` realization in MATRIX is claude's
    own `.claude/rules/` file, deduped by path exactly as its `skill` row
    already is.

D13 THE GUIDANCE MIRROR (owner ruling 9, 2026-08-10; harness-keyed per CMP-12
    2026-08-10) — the BASIS is the guidance file the human authors (`CLAUDE.md`
    or `AGENTS.md`), NEVER written by this installer. The mirror targets are
    derived, never hardcoded:

        targets = { CMP-12 guidance filename of each INSTALLED harness }
                  − { the basis }

    so a claude-only install with basis `CLAUDE.md` writes NO mirror at all
    (empty set → nothing rendered, nothing booked), and several harnesses that
    share a filename (codex + opencode both read `AGENTS.md`) get ONE
    file. "Installed harnesses" is the union of the `harnesses` recorded for
    every component in our own book — the same set uninstall shrinks.

    The basis is asked once in `interactive`, settable/overridable by
    `--guidance-basis`, and persisted as `guidance_basis` in the state file — so
    later runs never re-ask. UNSET IS THE DEFAULT AND MEANS NO MIRROR: a
    non-interactive run never prompts, never guesses a basis, and refuses a
    basis value outside the known guidance names. Each generated mirror is a
    normal installer-owned file — booked, collision-gated (a mirror file that
    exists and is not in our book, e.g. one the old installer's `model_mirror`
    renders, refuses the run pre-write) and removed on full uninstall.

    WHEN THE TARGET SET GOES EMPTY (a basis flip that leaves every installed
    harness reading the basis), yesterday's generated file is today's authored
    one: it is kept, never booked, and its stale `GENERATED — DO NOT EDIT`
    banner and fenced block are cleaned off IN PLACE — the one write this
    installer makes to a basis name, guarded by the machine-readable banner, so
    a hand-authored file is never touched. Leaving the banner would tell the
    human their own file must not be edited.

    SCOPE — RECURSIVE (owner ruling d-s17-agents-md-handover-to-install2,
    2026-08-10; amends A6's root-only scope). A mirror is rendered beside EVERY
    basis file in the tree, each generated from THAT directory's own basis, at
    parity with the old installer's `model_mirror` driver
    (`orchestration/models/mirror/driver/guidance.py`). The walk skips: any
    directory named in `GUIDANCE_SKIP_DIRS`; any NESTED GIT REPO (a directory
    below the root holding `.git` — its guidance files belong to that repo and
    are never touched); the `GUIDANCE_ALWAYS_EXCLUDED` prefixes (`.rbtv/goals`,
    whose BOTH routers are scaffold-owned — a structural collision in every
    workspace rbtv serves, so a driver default and not a per-workspace entry);
    and whatever `--guidance-exclude` records (persisted as `guidance_excludes`;
    passing the flag REPLACES the recorded list, matching the old driver's
    `--exclude`). `protect` covers EVERY directory's basis, not just the root's.
    A basis that is itself somebody's generated mirror has its banner STRIPPED
    before mirroring, and the strip is reported — the old driver's banner-over-
    banner accumulation (task 7.623 item (a)) is a defect and is NOT ported.
    Strip rather than refuse, because the ruled recovery from a deleted basis is
    to repoint at the surviving GENERATED file: a refusal would break it.

    ADOPTION (owner ruling, 2026-08-10, unblocking the same handover). A planned
    MIRROR path that exists outside our book is ADOPTED — overwritten and booked
    — when the file itself PROVES it is generated, by carrying a machine-
    readable DO-NOT-EDIT banner (ours or `mirror.py`'s). Without that proof it
    still refuses with `guidance-mirror-collision`. That boundary is the whole
    point: the refusal protects HAND-AUTHORED guidance, and a file whose own
    header says a tool wrote it is not that. Adoption is what let install2 take
    the mirror over from `install.py`'s `model_mirror` on the maintainer's vault
    without a human hand-deleting another tool's artifact.

    A PARTIAL UNINSTALL CAN UN-MANAGE A MIRROR, briefly (task 7.623(c)).
    Removing a component must NEVER be blocked by a mirror problem, so when the
    replan refuses (a deleted basis, a hand-edited book) the mirror is SKIPPED
    and every guidance file the book holds is held off the delete set: the file
    STAYS ON DISK BUT LEAVES THE BOOK. In that window it is an unbooked file
    under a mirror name, so an install carrying a DIFFERENT basis refuses
    `guidance-mirror-collision` on it unless its own banner lets ADOPTION take
    it. The next successful install re-books it. Correct — un-managed beats
    deleted — and surprising enough to say here rather than only at the code.

    THE EXPOSURE BLOCK is rendered at the ROOT only (the installer exposes
    components at the install root — see BOUNDARY above), inside the fenced
    `rbtv2:` block D8 describes. A nested mirror is a pure per-folder guidance
    mirror: banner + that folder's basis body, nothing else. The fence is what
    makes the basis FLIP safe: a generated file that later becomes the basis has
    both its banner and its fenced block stripped before it is re-mirrored, so
    neither can stack across runs.

D14 THE `.gitignore` BLOCK (owner ruling, 2026-08-21) — every per-component
    artifact and the state file are MACHINE-LOCAL: a loader bakes an ABSOLUTE
    entry-point path (D10) and the book records an absolute target, so a
    committed copy is wrong on every other machine
    (`decisions.md#d-s15-installer2-artifacts-machine-local`). Until 2026-08-21
    the workspace enforced that with name patterns (`.claude/skills/rbtv2-*/`);
    D12 retired the prefix, and git cannot match an in-file marker — so the
    installer, which is the one thing that knows exactly what it wrote, carries
    the list itself. It is an ORDINARY D7/D12 shared-file claim: one fenced
    `# rbtv2:start … # rbtv2:end` block in `{target}/.gitignore`, recomputed
    from the whole installed set on every install and uninstall, removed with
    the last component, gated by the same collision rule as every other claim.
    Bounds: only when the target is a GIT REPO (nothing mints a `.gitignore`
    in a workspace that has no git); the GUIDANCE MIRROR is never listed (it
    carries no absolute path and is authored-adjacent content the workspace
    commits — install.py's mirrors always were); and a `.gitignore` that
    already carries a fence we do not own refuses, like any other claim.
    A file ALREADY TRACKED by git is not covered — `.gitignore` does not
    reach one, and untracking it is the workspace owner's call, not ours; the
    report names any such file so the human sees it.

D15 `_hub/` — METHOD-FIRST UNITS, NO MANIFEST (generalises the 2026-08-21
    `_skills/` ruling) — `_hub/<method>/<name>` is an installable unit with no
    `component.md` and no `exposure.csv`. The parent folder names the method.
    A hub skill folder is still copied VERBATIM (the original D15 rule). Legacy
    `_skills/<name>/` is discovered as `_hub/skills/<name>`; book keys rewrite
    the same way on load (R6). `-m hub` reaches module `_hub`. pool, and a
    directory-shaped path, refuse by name (R4).

    INSTALL copies the folder VERBATIM (bytes, so a binary reference survives)
    into `MATRIX["skill"]`'s directory for each installed harness, skipping
    `.git`, `node_modules` and `__pycache__`. UNINSTALL deletes every file it
    copied and prunes the emptied directories — the folder goes as a whole.

    OWNERSHIP is stamped ONCE, on the copied `SKILL.md` (`_mark`); the files
    beside it stay byte-identical to the source, which is the point of a
    verbatim copy. `_is_ours` therefore reads a file's OWN marker first and then
    the marker of any ancestor directory's `SKILL.md` — so every file under a
    marked skill folder is ours, and stripping the marker from that one
    `SKILL.md` releases the WHOLE folder from the book (D12's release arm),
    which is the human's way of taking a vendored skill over.

D9  `path` ROWS MINT NOTHING UNDER THE INSTALL TARGET
    (`decisions.md#d-tool-inventory-exposure-rows`). `pool` stays inventory.
    A `path` part is linked into `~/.rbtv/bin` under its part-id (human PATH);
    that reverse does not write under `{target}`.

D10 BAKED PATHS ARE ABSOLUTE — a loader points at its entry point by resolved
    absolute path (the `materialize-seats.py` precedent). Loaders are derived;
    re-running the installer is how a relocated target is fixed.

D11 NO CATALOG ASSEMBLY — an entry-point of the form `prompts.csv#row-id` is a
    catalog reference. This tool checks the FILE half exists and names the whole
    reference in the guidance index; assembling catalog rows is the assembler's
    and the materializer's job, not the installer's.

D12 OWNERSHIP IS MARKED IN THE FILE, NOT IN ITS NAME (owner amendment,
    2026-08-21; supersedes the `rbtv2-` prefix of 2026-08-09) — a part is
    realized under its OWN id (`.claude/skills/planning/SKILL.md`), and what
    makes the file ours is the machine-readable `rbtv2-managed` marker its head
    carries (`MANAGED_BANNER`, placed after any YAML frontmatter so a loader's
    `---` block still parses). The book stays the primary record; the marker is
    what lets the installer answer "may I edit this?" from the FILE, which the
    book cannot do for a file the book never saw. Two consequences:

      · ADOPTION — a planned path that exists outside our book but carries the
        marker is overwritten and booked, exactly as a banner-carrying guidance
        mirror already was (D13). Without the marker it still refuses (D6):
        the collision gate protects hand-authored files, and a file whose own
        head says this tool wrote it is not one.
      · RELEASE — a booked file whose marker is GONE (a human took it over) is
        never deleted. It is dropped from the book and reported instead.

    NAME COLLISION WITH THE OLD INSTALLER. `install.py` sweeps
    `.claude/{rules,commands,agents,skills}` for names starting `rbtv-`
    (`admin/install/installer/generator.py::clear_previous_install`). Bare part
    ids do not start with `rbtv-`, so that sweep still cannot reach our work —
    and a manifest that DOES declare a `rbtv-*` part id is refused
    (`part-id-reserved`) rather than minting a file the other installer would
    delete behind our back.

    LEGACY NAMES. Files earlier runs minted under the `rbtv2-` prefix carry no
    marker (rules were verbatim copies). `LEGACY_PREFIX` keeps them recognized
    as ours by the ownership test ALONE, so the first unprefixed run deletes
    yesterday's prefixed files as stale instead of orphaning them. Nothing
    mints that prefix any more.

    Files that can carry neither a name nor a marker — the shared config files
    of D7 — translate ownership to key/block ownership: a JSON file is edited at
    the exact key paths the book records (`mcpServers.<name>`, `hooks.<event>`,
    …) and a text file through a fenced `rbtv2:start … rbtv2:end` block;
    uninstall removes exactly those keys or that block and deletes the file ONLY
    when nothing at all is left in it.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import datetime as _dt
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

VERSION = "2.0.0-coexistence"
SCHEMA = 2
# D12 — ownership is a marker in the file, never a prefix on its name.
MANAGED_MARK = "rbtv2-managed"
MANAGED_BANNER = (f"<!-- {MANAGED_MARK} — generated by install2.py; edits are "
                  "overwritten on the next run -->\n")
# The prefix runs before 2026-08-21 minted. Nothing writes it; the ownership
# test still recognizes it so the first unprefixed run cleans those files up.
LEGACY_PREFIX = "rbtv2-"
EXPOSURE_NAME = "exposure.csv"
EXPOSURE_COLS = (
    "part-id", "part-kind", "method", "rbtv-cli",
    "entry-point", "description", "write-roots",
)
# D15 — hub units (`_hub/<method>/<name>`). `_skills/` is the legacy skill alias.
HUB_DIR = "_hub"
SKILLS_DIR = "_skills"
SKILL_FILE = "SKILL.md"
# Disk folder token → canonical method. Plural accepted; id uses HUB_ID_FOLDER.
HUB_FOLDERS = {
    "skill": "skill", "skills": "skill",
    "command": "command",
    "rule": "rule", "rules": "rule",
    "hook": "hook", "sub-agent": "sub-agent",
    "agents.md": "agents.md", "config": "config", "path": "path",
    "pool": "pool",
}
HUB_ID_FOLDER = {
    "skill": "skills", "command": "command", "rule": "rules",
    "hook": "hook", "sub-agent": "sub-agent", "agents.md": "agents.md",
    "config": "config", "path": "path", "pool": "pool",
}
SKILL_FOLDER_SKIP = frozenset({".git", "node_modules", "__pycache__"})
STATE_REL = Path(".rbtv") / "config" / "install.json"
INDEX_REL = Path(".rbtv") / "config" / "install-index.json"
FENCE_ID = "rbtv2"
PATH_BOOTSTRAP = 'export PATH="$HOME/.rbtv/bin:$PATH"'
PATH_FENCE_START = f"# {FENCE_ID}:start path"
PATH_FENCE_END = f"# {FENCE_ID}:end path"
WS_PREFIX = "ws:"
# Selftest rebinds these to a temp workspace. Production: None → $HOME.
_RUNTIME: dict = {"bin": None, "rc": None, "local": None}

# D8/D13 — CMP-12's `agents.md` row: each harness's per-folder guidance
# FILENAME. The mirror is keyed by this map and nothing else: targets = the
# installed harnesses' filenames minus the basis. (CMP-12 also models qwen =
# QWEN.md; qwen is not one of D4's harnesses, so no run can select it and
# nothing is minted for it.)
GUIDANCE_FILE = {"claude": "CLAUDE.md", "codex": "AGENTS.md",
                 "opencode": "AGENTS.md"}
# The names this installer recognizes as guidance files — the accepted basis
# values, and the only filenames the mirror collision/adoption gates apply to.
GUIDANCE_NAMES = tuple(sorted(set(GUIDANCE_FILE.values())))
# CMP-12 § Fallback mechanics — the harnesses that auto-inject no rule folder,
# so their guidance file must FORCE the rule read. Not claude (`.claude/rules/`
# auto-injects) and not opencode (reads `.claude/` natively). Qwen is on this
# list in CMP-12 and absent from D4's harnesses. Kimi left with the 2026-08-14
# harness retirement — its models ride opencode.
FORCED_READ_HARNESSES = ("codex",)
BASIS_NONE = "none"
# Directory names the recursive mirror walk never descends into.
GUIDANCE_SKIP_DIRS = frozenset({".git", "node_modules"})
# Prefixes excluded however the workspace is configured: `.rbtv/goals` routers
# (BOTH names) are written by the goals-tree scaffold, in every workspace.
GUIDANCE_ALWAYS_EXCLUDED = (".rbtv/goals",)
# A file whose head carries one of these is somebody's GENERATED mirror, not
# authored guidance — it can never be a basis (banner-over-banner).
GENERATED_MARKERS = ("AUTO-GENERATED MIRROR", "GENERATED by install2.py")

HARNESSES = ("claude", "codex", "opencode")

# The canonical exposure-method vocabulary — d-exposure-method-canon (7) plus
# `path` (d-tool-inventory-exposure-rows) and `pool` (D22 — a prompt/task pool
# member, shopped at runtime by a seat, never minted as a harness artifact;
# registry transcription into d-exposure-method-canon rides F-113).
# A method outside this set refuses.
CANONICAL_METHODS = (
    "skill", "command", "rule", "hook", "sub-agent", "agents.md", "config",
    "path", "pool",
)

# Methods realized as ONE file per part, per harness. Target templates are
# install-root-relative; `{name}` is the bare part-id (D12). None = this
# harness has no realization for this method — nothing is minted, nothing is
# guessed.
#
# Transcribed from `architecture/CMP-12-exposure-adapter-matrix.md` (the ONE
# form authority) plus the codex/opencode readings re-measured 2026-08-08/09
# that `materialize-seats.py` carries. Kimi has no column: it shared every
# path with a harness that remains (skill → claude's `.claude/skills/`,
# rule → codex's `.agents/behavior-rules/`, command and sub-agent were None),
# so dropping it deletes no file.
MATRIX: dict[str, dict[str, str | None]] = {
    "skill": {
        "claude": ".claude/skills/{name}/SKILL.md",
        # opencode natively reads `.claude/` (CMP-12, widest claude-compat) —
        # same file, deduped by path.
        "opencode": ".claude/skills/{name}/SKILL.md",
        "codex": ".agents/skills/{name}/SKILL.md",
    },
    "command": {
        "claude": ".claude/commands/{name}.md",
        "codex": ".codex/prompts/{name}.md",
        "opencode": ".opencode/commands/{name}.md",
    },
    "rule": {
        "claude": ".claude/rules/{name}.md",
        "codex": ".agents/behavior-rules/{name}.md",
        # CMP-12 gives opencode NO separate rule type — it reads `.claude/`
        # natively, so claude's own file IS its realization (same dedupe by path
        # as the `skill` row above). It therefore takes no forced read either.
        "opencode": ".claude/rules/{name}.md",
    },
    "sub-agent": {
        "claude": ".claude/agents/{name}.md",
        "opencode": ".opencode/agents/{name}.md",
        "codex": None,
    },
}

# Methods that do not land as a per-part file: they claim keys or blocks inside
# files shared with the whole installed set (D7/D12), or mint nothing (D9).
AGGREGATE_METHODS = ("hook", "config", "agents.md")
INVENTORY_METHODS = ("pool",)

LOADER_NOTE = (
    "Generated by install2.py from the component's exposure manifest "
    "(CMP-12 adapter matrix) — a thin loader, regenerated freely, never "
    "hand-edited."
)


class Refuse(Exception):
    """A loud, machine-readable, PRE-WRITE refusal."""

    def __init__(self, code: str, message: str, path: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path

    def payload(self) -> dict:
        out: dict = {"ok": False,
                     "refusal": {"code": self.code, "message": self.message}}
        if self.path:
            out["refusal"]["path"] = self.path
        return out


# ── PATH links (`~/.rbtv/bin`, book-aware — R3) ─────────────────────────────

def local_bin() -> Path:
    override = _RUNTIME.get("local")
    return Path(override) if override is not None else Path.home() / ".local" / "bin"


def bin_dir() -> Path:
    override = _RUNTIME.get("bin")
    return Path(override) if override is not None else Path.home() / ".rbtv" / "bin"


def shell_rc() -> Path:
    override = _RUNTIME.get("rc")
    if override is not None:
        return Path(override)
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if shell.endswith("zsh"):
        return home / ".zshrc"
    return home / ".bashrc"


def _forbid_local_bin(bindir: Path) -> None:
    try:
        if bindir.resolve() == (Path.home() / ".local" / "bin").resolve():
            raise Refuse("path-forbidden",
                         "this installer never touches ~/.local/bin",
                         str(bindir))
    except OSError:
        return


def workspace_root(start: Path) -> Path:
    here = start.resolve()
    for p in (here, *here.parents):
        if (p / ".rbtv" / "config").is_dir():
            return p
    return here


def resolve_path_entry(target: Path, comp_dir: Path, entry: str) -> Path:
    raw = (entry or "").split("#", 1)[0].strip()
    if not raw:
        raise Refuse("entry-point-missing", "path row declares no entry-point")
    if raw.startswith(WS_PREFIX):
        body = raw[len(WS_PREFIX):]
        dest = workspace_root(target) / body
    else:
        body = raw
        dest = comp_dir / body
    if Path(body).is_absolute() or ".." in Path(body).parts:
        raise Refuse("entry-point-escape",
                     f"entry-point {raw!r} climbs with .. — use ws:<path>",
                     str(comp_dir))
    if dest.exists():
        dest = dest.resolve()
    if not dest.is_file():
        raise Refuse("entry-point-missing",
                     f"{raw!r} resolves to no file", str(dest))
    return dest


def link_name(pid: str) -> str:
    name = (pid or "").strip()
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise Refuse("path-name-invalid", f"part-id {pid!r} is not a PATH name")
    return name


def _points_at(link: Path, dest: Path) -> bool:
    try:
        return link.readlink() == dest or link.resolve() == dest.resolve()
    except OSError:
        return False


def link_one(bindir: Path, name: str, dest: Path, *, dry: bool) -> str:
    """ok | linked | relinked. Refuse path-collision on a non-symlink."""
    _forbid_local_bin(bindir)
    path = bindir / name
    if path.is_symlink():
        if _points_at(path, dest):
            return "ok"
        if dry:
            return "relinked"
        path.unlink()
        try:
            path.symlink_to(dest)
        except OSError as exc:
            raise Refuse("path-link-failed",
                         f"could not link {path} -> {dest}: {exc}",
                         str(path)) from exc
        return "relinked"
    if path.exists():
        raise Refuse("path-collision",
                     f"{path} exists and is not a symlink — not ours",
                     str(path))
    if dry:
        return "linked"
    bindir.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(dest)
    except OSError as exc:
        raise Refuse("path-link-failed",
                     f"could not link {path} -> {dest}: {exc}",
                     str(path)) from exc
    return "linked"


def unlink_one(bindir: Path, name: str, *, dry: bool) -> str:
    """gone | unlinked. A non-symlink at a booked name is left (path-collision)."""
    _forbid_local_bin(bindir)
    path = bindir / name
    if not path.exists() and not path.is_symlink():
        return "gone"
    if not path.is_symlink():
        raise Refuse("path-collision",
                     f"{path} is not a symlink — refusing to delete a file "
                     "this installer did not create", str(path))
    if not dry:
        path.unlink()
    return "unlinked"


def plan_path_links(target: Path,
                    rows: list[tuple[str, str, Path, str]]
                    ) -> tuple[dict[str, Path], dict[str, tuple[str, str]]]:
    """rows = (component_id, part_id, comp_dir, entry). One name → one dest."""
    desired: dict[str, Path] = {}
    owners: dict[str, tuple[str, str]] = {}
    seen: dict[str, str] = {}
    for cid, pid, comp_dir, entry in rows:
        name = link_name(pid)
        dest = resolve_path_entry(target, comp_dir, entry)
        if name in desired and desired[name] != dest:
            raise Refuse("path-name-collision",
                         f"{name} claimed by {seen[name]} and {cid} "
                         f"({desired[name]} vs {dest}) — whole run", name)
        desired[name] = dest
        owners[name] = (cid, pid)
        seen[name] = cid
    return desired, owners


def booked_path_names(state: dict) -> set[str]:
    names: set[str] = set()
    for rec in (state.get("components") or {}).values():
        names.update(rec.get("path_links") or [])
        for part in (rec.get("parts") or {}).values():
            if isinstance(part, dict):
                names.update(part.get("links") or [])
    return names


def gate_path_links(bindir: Path, desired: dict[str, Path],
                    drop: set[str]) -> None:
    """Refuse path-collision before any write (D6)."""
    _forbid_local_bin(bindir)
    for name in sorted(desired):
        path = bindir / name
        if path.exists() and not path.is_symlink():
            raise Refuse("path-collision",
                         f"{path} exists and is not a symlink — not ours",
                         str(path))
    for name in sorted(drop):
        path = bindir / name
        if (path.exists() or path.is_symlink()) and not path.is_symlink():
            raise Refuse("path-collision",
                         f"{path} is not a symlink — refusing to delete a file "
                         "this installer did not create", str(path))


def reconcile(bindir: Path, desired: dict[str, Path], booked: set[str],
              *, dry: bool, keep: set[str] | None = None) -> dict:
    """Create/repair desired; unlink booked-but-not-desired. Leave the rest."""
    keep = set(keep or ())
    report = {"linked": [], "relinked": [], "ok": [], "unlinked": [],
              "unbooked": [], "dangling": []}
    _forbid_local_bin(bindir)
    if not dry:
        bindir.mkdir(parents=True, exist_ok=True)
    for name, dest in sorted(desired.items()):
        if not dest.is_file():
            report["dangling"].append(name)
            raise Refuse("entry-point-missing",
                         f"PATH target for {name} is gone: {dest}", str(dest))
        st = link_one(bindir, name, dest, dry=dry)
        report[st].append(name)
    for name in sorted(booked - set(desired) - keep):
        report["unlinked"].append(name)
        unlink_one(bindir, name, dry=dry)
    if bindir.is_dir():
        for p in bindir.iterdir():
            if p.name not in desired and p.name not in booked and p.name not in keep:
                report["unbooked"].append(p.name)
        if not dry and not any(bindir.iterdir()):
            bindir.rmdir()
    return report


def _write_shell_path() -> None:
    rc = shell_rc()
    block = f"{PATH_FENCE_START}\n{PATH_BOOTSTRAP}\n{PATH_FENCE_END}\n"
    text = rc.read_text(encoding="utf-8") if rc.is_file() else ""
    if PATH_FENCE_START in text and PATH_FENCE_END in text:
        head = text.split(PATH_FENCE_START, 1)[0]
        tail = text.split(PATH_FENCE_END, 1)[1].lstrip("\n")
        text = head + block + tail
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + block
    rc.parent.mkdir(parents=True, exist_ok=True)
    rc.write_text(text, encoding="utf-8")


def _remove_shell_path() -> None:
    rc = shell_rc()
    if not rc.is_file():
        return
    text = rc.read_text(encoding="utf-8")
    if PATH_FENCE_START not in text or PATH_FENCE_END not in text:
        return
    head = text.split(PATH_FENCE_START, 1)[0]
    tail = text.split(PATH_FENCE_END, 1)[1].lstrip("\n")
    new = (head.rstrip() + "\n" + tail) if head.strip() else tail
    rc.write_text(new, encoding="utf-8")


def _path_rows_from_report(report: dict) -> list[tuple[str, str, Path, str]]:
    return [(r["component"], r["part"], Path(r["comp_dir"]), r["entry_point"])
            for r in report.get("path_rows") or []]


# ── discovery ───────────────────────────────────────────────────────────────

def module_id(name: str) -> str:
    """Selector token → catalog module. `-m hub` reaches `_hub`. THE ONE mapping."""
    return HUB_DIR if name == "hub" else name


def _hub_unit_name(method: str, path: Path) -> str:
    return path.name if method == "path" else (path.stem if path.is_file() else path.name)


def _is_hub_unit(method: str, path: Path) -> bool:
    if path.name.startswith("."):
        return False
    if method == "skill":
        return path.is_dir() and (path / SKILL_FILE).is_file()
    if method == "pool":
        return path.is_file() or path.is_dir()
    if method == "path":
        return path.is_file() or path.is_dir()
    if method in {"command", "rule", "sub-agent", "agents.md"}:
        return path.is_file() and path.suffix == ".md"
    return path.is_file()  # hook | config


def _hub_refusal(method: str, path: Path) -> str:
    if method == "pool":
        return "hub-pool-inexpressible"
    if method == "path" and path.is_dir():
        return "hub-path-directory"
    return ""


def _hub_refuse_message(comp: dict) -> str:
    cid = comp.get("id", "?")
    code = comp.get("hub_refusal")
    if code == "hub-pool-inexpressible":
        return (f"{cid}: pool is not expressible as a hub entry — a pool "
                "part is identified by an exposure.csv row; a bare file "
                "cannot say what it is (R4)")
    if code == "hub-path-directory":
        return (f"{cid}: path is expressible only as a single FILE — a "
                "directory does not say which child to link (R4)")
    return f"{cid}: hub entry refused ({code})"


def discover_hub(root: Path, tree: str) -> dict[str, dict]:
    """Hub units under one tree. id = `_hub/<id-folder>/<name>` (never the
    on-disk relpath). `_skills/<name>/` is a legacy alias of `_hub/skills/`."""
    found: dict[str, dict] = {}
    if not root.is_dir():
        return found

    def put(path: Path, method: str, *, legacy: bool) -> None:
        name = _hub_unit_name(method, path)
        if not name or name.startswith("."):
            return
        cid = f"{HUB_DIR}/{HUB_ID_FOLDER[method]}/{name}"
        rec = {
            "id": cid, "tree": tree, "tree_root": str(root),
            "module": HUB_DIR, "component": name, "path": str(path),
            "kind": "hub", "method": method, "manifest": False,
            "legacy_skills_dir": legacy,
        }
        refusal = _hub_refusal(method, path)
        if refusal:
            rec["hub_refusal"] = refusal
        prev = found.get(cid)
        if prev and prev.get("legacy_skills_dir") and not legacy:
            found[cid] = rec
        elif prev is None:
            found[cid] = rec

    hub = root / HUB_DIR
    if hub.is_dir():
        for folder in sorted(hub.iterdir()):
            method = HUB_FOLDERS.get(folder.name)
            if not method or not folder.is_dir():
                continue
            for child in sorted(folder.iterdir()):
                if _is_hub_unit(method, child):
                    put(child, method, legacy=False)
    skills = root / SKILLS_DIR
    if skills.is_dir():
        for child in sorted(skills.iterdir()):
            if _is_hub_unit("skill", child):
                put(child, "skill", legacy=True)
    return found


def rewrite_legacy_skill_ids(state: dict) -> list[tuple[str, str]]:
    """R6 — `_skills/<name>` → `_hub/skills/<name>` on load; persist on write."""
    moved: list[tuple[str, str]] = []
    comps = state.get("components") or {}
    for old in list(comps):
        if not old.startswith(f"{SKILLS_DIR}/"):
            continue
        new = f"{HUB_DIR}/{HUB_ID_FOLDER['skill']}/{old.split('/', 1)[1]}"
        rec = comps.pop(old)
        rec["module"] = HUB_DIR
        if new in comps:
            raise Refuse("hub-id-collision",
                         f"book has both {old!r} and {new!r}", old)
        comps[new] = rec
        moved.append((old, new))
    return moved


def strip_retired_harnesses(state: dict) -> None:
    """D4 — drop `kimi` (and any other name not in HARNESSES) from every
    booked record. Persist happens on the next write. A strip that would
    leave a record with no harness refuses — never write an empty list."""
    for cid, rec in (state.get("components") or {}).items():
        raw = rec.get("harnesses")
        if raw is None:
            continue
        kept = [h for h in HARNESSES if h in raw]
        if not kept:
            raise Refuse(
                "harness-list-empty",
                f"{cid}: dropping retired harnesses would leave none "
                f"(had: {', '.join(raw) or '(empty)'})",
                cid)
        rec["harnesses"] = kept


def _is_component_dir(path: Path) -> bool:
    """D2 — a directory holding `exposure.csv`. Combined with scan_tree's
    depth-2 walk, that is the whole component rule."""
    return (path / EXPOSURE_NAME).is_file()


def scan_tree(root: Path, tree: str) -> dict[str, dict]:
    """Every component under one tree root, by id (D2) — a directory at
    EXACTLY depth 2 that holds `exposure.csv`. {} when the root is absent.
    Depth-1 (module-root) manifests and depth-3 files are invisible here.
    Hub units are a separate branch (D15)."""
    found: dict[str, dict] = {}
    if not root.is_dir():
        return found

    def record(dir_path: Path, kind: str = "component") -> None:
        rel = dir_path.relative_to(root).as_posix()
        found[rel] = {
            "id": rel,
            "tree": tree,
            "tree_root": str(root),
            "module": rel.split("/")[0],
            "component": rel.split("/")[-1],
            "path": str(dir_path),
            "kind": kind,
            "manifest": (dir_path / EXPOSURE_NAME).is_file(),
        }

    found.update(discover_hub(root, tree))
    for top in sorted(root.iterdir()):
        if not top.is_dir() or top.name.startswith("."):
            continue
        if top.name in {HUB_DIR, SKILLS_DIR}:
            continue
        # Depth 2 ONLY — a component folder lives inside a module folder (D2).
        for sub in sorted(top.iterdir()):
            if sub.is_dir() and not sub.name.startswith(".") and _is_component_dir(sub):
                record(sub)
    return found


def scan_all(mirror_root: Path, repo_root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Both trees merged, mirror winning on a shared id (D3).

    Returns (components-by-id, shadowed) — `shadowed` names every repo component
    the mirror hid, so the precedence is reported rather than silent.
    """
    repo = scan_tree(repo_root, "repo")
    mirror = scan_tree(mirror_root, "mirror")
    shadowed = [
        {"id": cid, "shadowed_path": repo[cid]["path"],
         "winner_path": mirror[cid]["path"]}
        for cid in sorted(set(repo) & set(mirror))
    ]
    merged = dict(repo)
    merged.update(mirror)
    return merged, shadowed


def exposure_rows(component: dict) -> list[dict]:
    path = Path(component["path"]) / EXPOSURE_NAME
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        # `#` comment lines: both real manifests use them for their own header.
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    reader = csv.DictReader(lines)
    got = tuple(reader.fieldnames or ())
    if got != EXPOSURE_COLS:
        raise Refuse(
            "manifest-malformed",
            f"{path}: columns are {','.join(got) or '(none)'} — "
            f"want {','.join(EXPOSURE_COLS)}",
            str(path))
    return [dict(r) for r in reader]


def _part_specs(comp: dict, *, strict: bool = False) -> list[dict]:
    """Catalog parts of one component: [{'id', 'method'}, ...].

    R1: a duplicate part-id in one exposure.csv refuses when *strict*
    (planning / install / uninstall). Upgrade and list stay silent.
    """
    if comp.get("kind") == "hub":
        return [{"id": comp["component"],
                 "method": comp.get("method") or "skill"}]
    seen: list[str] = []
    dups: set[str] = set()
    out: list[dict] = []
    for row in (comp["rows"] if "rows" in comp else exposure_rows(comp)):
        pid = (row.get("part-id") or "").strip()
        if not pid:
            continue
        if pid in seen:
            dups.add(pid)
        else:
            seen.append(pid)
        out.append({"id": pid, "method": (row.get("method") or "").strip()})
    if dups and strict:
        raise Refuse(
            "part-id-duplicate",
            f"{comp.get('id', '?')}: exposure.csv repeats part-id "
            f"{', '.join(sorted(dups))} — two rows cannot share a bare "
            "part-id (R1). Refusing before any write",
            str(Path(comp["path"]) / EXPOSURE_NAME))
    return out


def catalog_parts_map(catalog: dict[str, dict]) -> dict[str, list[dict]]:
    return {cid: _part_specs(comp) for cid, comp in catalog.items()}


def _wanted_parts(rec: dict) -> set[str] | None:
    raw = rec.get("parts")
    return None if raw is None else set(raw)


def rec_files(rec: dict) -> set[str]:
    out = set(rec.get("files") or [])
    for part in (rec.get("parts") or {}).values():
        out |= set(part.get("files") or [])
    return out


def rec_owns_nothing(rec: dict) -> bool:
    """True when a booked record holds no files, claims, or PATH links."""
    if rec_files(rec) or rec.get("path_links") or rec.get("claims"):
        return False
    for part in (rec.get("parts") or {}).values():
        if not isinstance(part, dict):
            continue
        if part.get("claims") or part.get("links"):
            return False
    return True


# ── content ─────────────────────────────────────────────────────────────────

def _yq(text: str) -> str:
    """A YAML-safe quoted scalar — json quoting is valid YAML (the colon-space
    in a `description:` is the failure class this closes)."""
    return json.dumps(str(text), ensure_ascii=False)


def _loader(part: str, desc: str, entry: str, what: str, named: bool) -> str:
    name_line = f"name: {part}\n" if named else ""
    return (f"---\n{name_line}description: {_yq(desc)}\n---\n\n"
            + LOADER_NOTE + "\n\n"
            f"Read `{entry}` NOW and follow it as this {what}'s full "
            "instructions.\n")


def _mark(text: str) -> str:
    """Stamp *text* with the ownership marker (D12), AFTER any YAML frontmatter
    — a marker above a loader's `---` block would stop that block parsing."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 3)
        if end != -1:
            cut = end + len("\n---\n")
            return text[:cut] + "\n" + MANAGED_BANNER + text[cut:]
    return MANAGED_BANNER + text


def _marked(path: Path) -> bool:
    """True when this one file's head carries a machine-readable owner mark —
    ours, or a generated-mirror banner (D13 adoption). Unreadable proves
    nothing."""
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except (OSError, UnicodeDecodeError):
        return False
    return MANAGED_MARK in head or any(m in head for m in GENERATED_MARKERS)


def _is_ours(target: Path, rel: str) -> bool:
    """True when the FILE ITSELF proves this installer wrote it (D12): our
    ownership marker, a generated-mirror banner, a legacy `rbtv2-` name from a
    run that predates the marker, or — D15 — membership in a copied skill
    folder whose `SKILL.md` carries the marker. A verbatim copy keeps its files
    byte-identical to the source, so the FOLDER is what is owned, and one
    stripped marker releases all of it."""
    if (Path(rel).name.startswith(LEGACY_PREFIX)
            or Path(rel).parent.name.startswith(LEGACY_PREFIX)):
        return True
    if _marked(target / rel):
        return True
    parts = Path(rel).parts
    return any(_marked(target.joinpath(*parts[:i], SKILL_FILE))
               for i in range(len(parts) - 1, 0, -1))


def _content_for(rel: str, method: str, part: str, desc: str, entry: str,
                 comp_dir: Path, entry_rel: str) -> str:
    return _mark(_body_for(rel, method, part, desc, entry, comp_dir, entry_rel))


def _body_for(rel: str, method: str, part: str, desc: str, entry: str,
              comp_dir: Path, entry_rel: str) -> str:
    if method == "rule":
        # Verbatim copy — CMP-12's fallback row is a mirror, not a pointer. The
        # ONE addition is the ownership marker `_content_for` stamps on (D12).
        return (comp_dir / entry_rel).read_text(encoding="utf-8")
    if method == "skill":
        return _loader(part, desc, entry, "skill", named=True)
    if method == "sub-agent":
        return _loader(part, desc, entry, "sub-agent", named=True)
    if method == "command":
        if rel.startswith(".codex/prompts/"):
            # codex prompt files are plain markdown — no frontmatter.
            return (LOADER_NOTE + "\n\n"
                    f"Read `{entry}` NOW and follow it as this command's full "
                    "instructions.\n")
        return _loader(part, desc, entry, "command", named=False)
    raise Refuse("internal", f"no content rule for method {method!r}")


def _codex_mcp_toml_block(servers: dict) -> str:
    """The `[mcp_servers.*]` tables for `.codex/config.toml`, from the neutral
    `mcpServers` shape. json.dumps of a str/list is valid TOML for both, so the
    stdlib's missing TOML writer is not needed."""
    lines: list[str] = []
    for name in sorted(servers):
        spec = servers[name]
        lines.append(f"[mcp_servers.{name}]")
        if spec.get("url"):
            lines.append(f"url = {json.dumps(str(spec['url']))}")
        else:
            lines.append(f"command = {json.dumps(str(spec.get('command', '')))}")
            if spec.get("args"):
                lines.append("args = " + json.dumps([str(a) for a in spec["args"]]))
            env = spec.get("env") or {}
            if env:
                lines.append("")
                lines.append(f"[mcp_servers.{name}.env]")
                for k in sorted(env):
                    lines.append(f"{k} = {json.dumps(str(env[k]))}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _opencode_mcp_entry(spec: dict) -> dict:
    if spec.get("url"):
        return {"type": "remote", "url": str(spec["url"]), "enabled": True}
    entry: dict = {
        "type": "local",
        "command": [str(spec.get("command", ""))]
        + [str(a) for a in (spec.get("args") or [])],
        "enabled": True,
    }
    env = spec.get("env") or {}
    if env:
        entry["environment"] = {k: str(v) for k, v in env.items()}
    return entry


def _exposure_block(name: str, harnesses: list[str],
                    agents_parts: list[tuple[str, str, str]],
                    rule_parts: list[tuple[str, str]]) -> str:
    """The rbtv exposure preamble ONE guidance file carries (D8), fenced.

    `name` is the guidance FILENAME this block is for. The Step-0 forced read is
    emitted only for the harnesses that auto-inject no rule folder
    (`FORCED_READ_HARNESSES` — CMP-12 § Fallback mechanics) AND read that name;
    claude and opencode never get it. It enumerates the paths those harnesses'
    rule files were ACTUALLY written to — a rule realized only under
    `.claude/rules/` (its component installed claude-only) is never named to
    codex, whose copy does not exist. The `agents.md` rows are named in every
    guidance file, because that method's realization IS the guidance file.

    Empty string when there is nothing to say — no block, no fence, no file
    churn.
    """
    readers = [h for h in harnesses
               if h in FORCED_READ_HARNESSES and GUIDANCE_FILE.get(h) == name]
    forced: list[tuple[str, str]] = []
    for _pid, desc, by_harness in rule_parts:
        for rel in sorted({by_harness[h] for h in readers if h in by_harness}):
            forced.append((rel, desc))
    if not agents_parts and not forced:
        return ""
    out = ["# rbtv exposure — installed components", ""]
    if forced:
        out += [
            "## Step 0 — MANDATORY, before anything else",
            "",
            "Read EACH of these behavior-rule files, one at a time, IN THIS "
            "ORDER. They are always-on rules; this harness auto-injects no rule "
            "folder, so this enumeration is the read. Do not bulk-read them — "
            "a bulk read truncates the last entries.",
            "",
        ]
        for i, (rel, desc) in enumerate(forced, 1):
            suffix = f" — {desc}" if desc else ""
            out.append(f"{i}. `{rel}`{suffix}")
        out.append("")
    if agents_parts:
        out += ["## Guidance parts", ""]
        for pid, desc, entry in agents_parts:
            suffix = f" — {desc}" if desc else ""
            out.append(f"- **{pid}**: read `{entry}`{suffix}")
    start, end = _fence("<!--")
    return f"{start}\n" + "\n".join(out).rstrip() + f"\n{end}\n"


# ── guidance mirror (D13) ───────────────────────────────────────────────────

def resolve_basis(stored, override: str | None) -> str | None:
    """The basis in force for this run: the override when one was passed, else
    what the book holds. Returns None for "no mirror"; refuses anything that is
    neither a known basis name nor `none` — including a hand-edited book."""
    value = override if override is not None else stored
    if value is None or value == BASIS_NONE or value == "":
        return None
    if value not in GUIDANCE_NAMES:
        raise Refuse(
            "guidance-basis-invalid",
            f"guidance basis {value!r} is neither {BASIS_NONE!r} nor one of "
            + " · ".join(GUIDANCE_NAMES)
            + " — refusing before any write (D13)")
    return value


def mirror_targets(harnesses, basis: str) -> list[str]:
    """The guidance filenames this run generates: CMP-12's filename for every
    INSTALLED harness, minus the basis (never written). Harnesses sharing a
    filename collapse to one target; a set that reads only the basis yields
    NOTHING — the claude-only case (D13)."""
    return sorted({GUIDANCE_FILE[h] for h in harnesses if h in GUIDANCE_FILE}
                  - {basis})


def _norm_prefix(value: str) -> str:
    return value.strip().replace("\\", "/").strip("/")


def walk_bases(target: Path, basis: str,
               excludes: list[str] | tuple[str, ...] = ()) -> list[Path]:
    """Every basis file the recursive mirror covers, root first, sorted (D13).

    Skips `GUIDANCE_SKIP_DIRS`, nested git repos, the always-excluded prefixes
    and the workspace's configured excludes. Symlinks are never followed."""
    prefixes = [p for p in
                (_norm_prefix(x) for x in (*excludes, *GUIDANCE_ALWAYS_EXCLUDED))
                if p]

    def excluded(rel: str) -> bool:
        return any(rel == p or rel.startswith(p + "/") for p in prefixes)

    found: list[Path] = []

    def walk(directory: Path) -> None:
        if directory != target:
            rel = directory.relative_to(target).as_posix()
            if (directory.name in GUIDANCE_SKIP_DIRS or excluded(rel)
                    or (directory / ".git").exists()):
                return
        source = directory / basis
        if source.is_file() and not source.is_symlink() \
                and not excluded(source.relative_to(target).as_posix()):
            found.append(source)
        try:
            entries = sorted(directory.iterdir())
        except (PermissionError, OSError):
            return
        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                walk(entry)

    walk(target)
    return found


def strip_generated_banner(body: str) -> tuple[str, bool]:
    """Drop a leading GENERATED-mirror banner from *body*, if it carries one.

    A basis file CAN legitimately be somebody's generated mirror: the ruled
    recovery from a deleted basis is to repoint at the surviving generated file.
    Re-mirroring it verbatim would stack banner on banner on every run — the
    old driver's defect (task 7.623(a)). We strip instead of refusing, so the
    recovery still works and the body stays stable across runs.

    Recognized shapes: this installer's one-comment banner, and mirror.py's
    comment + `> [!danger]` blockquote + `---` rule.
    """
    head = body[:400]
    if not (head.lstrip().startswith("<!--")
            and any(m in head for m in GENERATED_MARKERS)):
        return body, False
    rest = body.split("-->", 1)[1].lstrip("\n") if "-->" in body else ""
    lines = rest.split("\n")
    while lines and (lines[0].startswith(">") or not lines[0].strip()):
        lines.pop(0)
    if lines and lines[0].strip() == "---":
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines), True


def plan_mirror(target: Path, basis: str | None, harnesses,
                excludes: list[str] | tuple[str, ...] = (),
                blocks: dict[str, str] | None = None
                ) -> tuple[dict[str, str], frozenset[str], list[str],
                           list[str], dict[str, str]]:
    """The mirror files the basis implies: one per TARGET NAME (D13, harness-
    keyed) beside EVERY basis file in the tree (recursive).

    Returns `(files, bases, stripped, targets, debanner)` — `bases` is the set
    of basis paths that must never be written or deleted (computed even when
    there is no target, because a basis flip can put a booked name on a
    hand-authored file); `stripped` names the bases whose own generated banner
    was removed before mirroring; `targets` is the resolved filename set;
    `debanner` maps a basis path to its cleaned body (see below).

    `blocks` maps a target filename to its exposure block (D8), placed at the
    ROOT only — nested mirrors are pure per-folder guidance.
    """
    if basis is None:
        return {}, frozenset(), [], [], {}
    blocks = blocks or {}
    targets = mirror_targets(harnesses, basis)
    root_source = target / basis
    if not root_source.is_file():
        if not targets:
            # Nothing would be rendered anyway — a missing basis is not this
            # run's problem, and there is no basis on disk to protect.
            return {}, frozenset(), [], [], {}
        other = " or ".join(n for n in GUIDANCE_NAMES if n != basis)
        raise Refuse(
            "guidance-basis-missing",
            f"the recorded guidance basis {basis!r} does not exist at the "
            "install root, so there is nothing to mirror. Recover with ONE of: "
            f"restore {basis}; or `--guidance-basis {other}` to make the file "
            f"you do have the basis; or `--guidance-basis {BASIS_NONE}` to turn "
            "the mirror off. Nothing was written",
            str(root_source))
    files: dict[str, str] = {}
    bases: set[str] = set()
    stripped: list[str] = []
    debanner: dict[str, str] = {}
    for source in walk_bases(target, basis, excludes):
        rel = source.relative_to(target).as_posix()
        bases.add(rel)
        if not targets:
            # No mirror can be rendered under this name any more (every
            # installed harness reads the basis). A file that USED to be our
            # generated mirror is now the file the human authors, so our
            # DO-NOT-EDIT banner and fenced block are stale instructions on
            # their file — clean them off, in place, booking nothing. Guarded
            # by the machine-readable banner: a hand-authored basis has none
            # and is never touched.
            try:
                body = source.read_text(encoding="utf-8").lstrip("\n")
            except (OSError, UnicodeDecodeError):
                continue          # unreadable proves nothing — leave it alone
            cleaned, had_banner = strip_generated_banner(body)
            if had_banner:
                cleaned = _block_del(cleaned, "<!--").lstrip("\n")
                debanner[rel] = (cleaned if cleaned.endswith("\n")
                                 else cleaned + "\n")
            continue
        try:
            body = source.read_text(encoding="utf-8").lstrip("\n")
        except (OSError, UnicodeDecodeError) as exc:
            raise Refuse(
                "guidance-basis-unreadable",
                f"the guidance basis {rel!r} is not readable as UTF-8 text "
                f"({exc}) — a mirror of it would be garbage; refusing before "
                f"any write. Turn the mirror off with `--guidance-basis "
                f"{BASIS_NONE}` if this file is not meant to be guidance, or "
                f"exclude its directory with `--guidance-exclude`",
                str(source)) from exc
        body, stripped_banner = strip_generated_banner(body)
        if stripped_banner:
            stripped.append(rel)
        # A basis that used to be OUR generated file still carries the fenced
        # exposure block — drop it, or every flip would stack another copy.
        body = _block_del(body, "<!--")
        at_root = source.parent == target
        for mirror in targets:
            block = blocks.get(mirror, "") if at_root else ""
            text = (f"<!-- GENERATED by install2.py — DO NOT EDIT.\n"
                    f"     {mirror} mirrors {rel}, per the guidance basis "
                    f"recorded in {STATE_REL.as_posix()}.\n"
                    f"     Edit {rel}; re-run the installer to refresh this "
                    "file. -->\n\n") + (block + "\n" if block else "") + body
            mrel = (source.parent / mirror).relative_to(target).as_posix()
            files[mrel] = text if text.endswith("\n") else text + "\n"
    return files, frozenset(bases), sorted(stripped), targets, debanner


# ── shared-file claims (D7 + D12) ───────────────────────────────────────────
#
# A claim is one key path inside a JSON file, or one fenced block inside a text
# file. Nothing else in those files is ever read as ours, written, or deleted.

def _claim_id(rel: str, key: list[str] | None) -> str:
    return f"{rel}::" + (json.dumps(key) if key else "#block")


def _jget(doc: dict, key: list[str]):
    node = doc
    for k in key:
        if not isinstance(node, dict) or k not in node:
            return None, False
        node = node[k]
    return node, True


def _jset(doc: dict, key: list[str], value) -> None:
    node = doc
    for k in key[:-1]:
        node = node.setdefault(k, {})
    node[key[-1]] = value


def _jdel(doc: dict, key: list[str]) -> None:
    """Delete a key path and every container it leaves empty."""
    node = doc
    chain = [doc]
    for k in key[:-1]:
        if not isinstance(node, dict) or k not in node:
            return
        node = node[k]
        chain.append(node)
    if isinstance(node, dict):
        node.pop(key[-1], None)
    for i in range(len(chain) - 1, 0, -1):
        if isinstance(chain[i], dict) and not chain[i]:
            chain[i - 1].pop(key[i - 1], None)


def _fence(comment: str) -> tuple[str, str]:
    if comment == "#":
        return f"# {FENCE_ID}:start", f"# {FENCE_ID}:end"
    return f"<!-- {FENCE_ID}:start -->", f"<!-- {FENCE_ID}:end -->"


def _block_set(text: str, body: str, comment: str) -> str:
    start, end = _fence(comment)
    block = f"{start}\n{body.rstrip()}\n{end}\n"
    if start in text and end in text:
        head = text.split(start, 1)[0]
        tail = text.split(end, 1)[1].lstrip("\n")
        return head + block + tail
    return (text.rstrip() + "\n\n" if text.strip() else "") + block


def _block_del(text: str, comment: str) -> str:
    start, end = _fence(comment)
    if start not in text or end not in text:
        return text
    head = text.split(start, 1)[0]
    tail = text.split(end, 1)[1].lstrip("\n")
    return (head.rstrip() + "\n" + tail) if head.strip() else tail


# ── planning ────────────────────────────────────────────────────────────────

def plan_files(records: dict[str, dict], catalog: dict[str, dict]
               ) -> tuple[dict[str, str], dict[str, list], list[dict], dict]:
    """The COMPLETE set of whole files AND shared-file claims the installed set
    implies (D7). Every gate fires here, before any write — a refusal leaves
    zero files.

    Returns (rel -> content, rel -> owning component ids, claims, report).
    """
    files: dict[str, str] = {}
    owners: dict[str, list] = {}
    servers: dict[str, dict] = {}
    server_harnesses: set[str] = set()
    server_owners: dict[str, list] = {}
    hooks: dict[str, list] = {}
    hook_harnesses: set[str] = set()
    hook_owners: dict[str, list] = {}
    agents_parts: list[tuple[str, str, str]] = []
    rule_parts: list[tuple[str, str]] = []
    report: dict = {"skipped_inventory_rows": [], "no_realization": [],
                    "skill_folders": [], "path_rows": []}

    def claim_file(rel: str, content: str, cid: str, pid: str) -> None:
        if rel in files and files[rel] != content:
            other = owners[rel][0]
            other_cid = other[0] if isinstance(other, tuple) else other
            raise Refuse(
                "part-collision",
                f"components {other_cid!r} and {cid!r} both realize "
                f"{rel!r} with different content — two components exposing the "
                "same part id is a manifest conflict, not something to resolve "
                "by write order",
                rel)
        files[rel] = content
        owners.setdefault(rel, []).append((cid, pid))

    def claim_skill_folder(comp: dict, cid: str, harnesses: list[str]) -> None:
        """D15 — copy the whole folder into each harness's skills directory.

        The root `SKILL.md` is the ONE file we stamp (`_mark`); everything else
        is copied byte-for-byte, so a reference, a licence or a binary asset
        arrives unchanged. Paths shared by several harnesses dedupe on the
        template, exactly as the thin-loader `skill` row already does."""
        comp_dir = Path(comp["path"])
        named = comp["component"]
        if named.startswith("rbtv-"):
            raise Refuse(
                "part-id-reserved",
                f"{cid}: a skill folder named {named!r} would land under "
                "`rbtv-*`, which the OLD installer sweeps out of "
                "`.claude/skills/` on every run — rename the folder (D12)",
                str(comp_dir))
        members: list[tuple[str, str | bytes]] = []
        for path in sorted(comp_dir.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            member = path.relative_to(comp_dir)
            if any(part in SKILL_FOLDER_SKIP for part in member.parts):
                continue
            raw = path.read_bytes()
            if member.as_posix() == SKILL_FILE:
                body: str | bytes = _mark(raw.decode("utf-8"))
            else:
                try:
                    body = raw.decode("utf-8")
                except UnicodeDecodeError:
                    body = raw               # a binary asset rides along whole
            members.append((member.as_posix(), body))
        roots = {MATRIX["skill"][h].rsplit("/", 1)[0].format(name=named)
                 for h in harnesses if MATRIX["skill"].get(h)}
        for root_rel in sorted(roots):
            for member, body in members:
                claim_file(f"{root_rel}/{member}", body, cid, named)
        report["skill_folders"].append(
            {"component": cid, "files": len(members),
             "roots": sorted(roots)})

    for cid in sorted(records):
        rec = records[cid]
        comp = catalog.get(cid)
        if comp is None:
            raise Refuse(
                "component-vanished",
                f"component {cid!r} is recorded as installed but no longer "
                f"exists under {rec.get('tree_root')!r} (renamed or deleted "
                "upstream). Every run at this target refuses until the book "
                "agrees with the trees. Recover with EITHER: restore the "
                f"folder; or `uninstall --component {cid}`, which needs no "
                "tree — the book holds its files",
                str(rec.get("tree_root", "")))
        comp_dir = Path(comp["path"])
        harnesses = [h for h in HARNESSES if h in rec["harnesses"]]

        wanted = _wanted_parts(rec)
        if comp.get("kind") == "hub":
            if comp.get("hub_refusal"):
                raise Refuse(comp["hub_refusal"],
                             _hub_refuse_message(comp), comp["path"])
            if comp.get("method") == "skill":
                pid = comp["component"]
                if wanted is not None and pid not in wanted:
                    continue
                claim_skill_folder(comp, cid, harnesses)
                continue
            src = Path(comp["path"])
            if src.is_file():
                comp_dir = src.parent
            rows = [{"part-id": comp["component"],
                     "method": comp["method"],
                     "entry-point": src.name,
                     "description": ""}]
        else:
            _part_specs(comp, strict=True)
            rows = exposure_rows(comp)
        for row in rows:
            pid = (row.get("part-id") or "").strip()
            method = (row.get("method") or "").strip()
            entry_rel = (row.get("entry-point") or "").strip()
            desc = (row.get("description") or "").strip()
            if not pid:
                continue
            if wanted is not None and pid not in wanted:
                continue
            if method not in CANONICAL_METHODS:
                raise Refuse(
                    "method-unknown",
                    f"{cid}: exposure row {pid!r} declares method "
                    f"{method or '(empty)'!r}, which is outside the canonical "
                    f"vocabulary ({' · '.join(CANONICAL_METHODS)}) — "
                    "d-exposure-method-canon; refusing before any write",
                    str(comp_dir / EXPOSURE_NAME))
            if method in INVENTORY_METHODS:
                # D9 — pool is inventory only. path is collected below.
                report["skipped_inventory_rows"].append(
                    {"component": cid, "part": pid, "method": method,
                     "entry_point": entry_rel})
                continue
            if method == "path":
                report["path_rows"].append(
                    {"component": cid, "part": pid, "method": method,
                     "entry_point": entry_rel, "comp_dir": str(comp_dir)})
                continue
            if not entry_rel:
                raise Refuse(
                    "entry-point-missing",
                    f"{cid}: exposure row {pid!r} ({method}) declares no "
                    "entry-point — there is nothing to realize",
                    str(comp_dir / EXPOSURE_NAME))
            # D11 — a `file.csv#row` reference is checked at its file half.
            entry_file = entry_rel.split("#", 1)[0]
            if not (comp_dir / entry_file).is_file():
                raise Refuse(
                    "entry-point-missing",
                    f"{cid}: exposure row {pid!r} ({method}) points at "
                    f"{entry_rel!r}, which resolves to no file under the "
                    "component — refusing before any write",
                    str(comp_dir / entry_file))
            entry_abs = str((comp_dir / entry_file).resolve())
            entry_ref = entry_abs + (("#" + entry_rel.split("#", 1)[1])
                                     if "#" in entry_rel else "")
            if pid.startswith("rbtv-"):
                raise Refuse(
                    "part-id-reserved",
                    f"{cid}: exposure row {pid!r} starts with `rbtv-`, the "
                    "prefix the OLD installer sweeps out of "
                    "`.claude/{rules,commands,agents,skills}` on every run "
                    "(generator.py::clear_previous_install) — a file minted "
                    "under that name would be deleted behind this installer's "
                    "back. Rename the part (D12)",
                    str(comp_dir / EXPOSURE_NAME))
            named = pid

            if method == "agents.md":
                agents_parts.append((named, desc, entry_ref))
                continue
            if method == "config":
                data = _read_json(comp_dir / entry_file, "config", cid, pid)
                decl = data.get("mcpServers") if isinstance(data, dict) else None
                if decl is None:
                    continue  # another config payload kind — not ours to place
                if not isinstance(decl, dict) or not all(
                        isinstance(v, dict) for v in decl.values()):
                    raise Refuse(
                        "config-declaration-invalid",
                        f"{cid}: config entry-point {entry_rel!r} carries an "
                        "`mcpServers` that is not an object of server objects "
                        "— not the neutral schema "
                        "(d-mcp-registration-is-config)",
                        str(comp_dir / entry_file))
                for name, spec in decl.items():
                    # D12: the registration is claimed under its declared name;
                    # a foreign key of the same name refuses (D6), it is never
                    # renamed around.
                    key = name
                    if key in servers and servers[key] != spec:
                        raise Refuse(
                            "config-server-conflict",
                            f"MCP server {key!r} is declared differently by "
                            "more than one installed component — one "
                            "registration, one home",
                            str(comp_dir / entry_file))
                    servers[key] = spec
                    if (cid, pid) not in server_owners.setdefault(key, []):
                        server_owners[key].append((cid, pid))
                server_harnesses |= set(harnesses)
                continue
            if method == "hook":
                data = _read_json(comp_dir / entry_file, "hook", cid, pid)
                decl = data.get("hooks") if isinstance(data, dict) else None
                if not isinstance(decl, dict):
                    raise Refuse(
                        "hook-declaration-invalid",
                        f"{cid}: hook entry-point {entry_rel!r} carries no "
                        "`hooks` object — the neutral shape is claude's "
                        "settings `hooks` block",
                        str(comp_dir / entry_file))
                for event, entries in decl.items():
                    hooks.setdefault(event, []).extend(
                        entries if isinstance(entries, list) else [entries])
                    if (cid, pid) not in hook_owners.setdefault(event, []):
                        hook_owners[event].append((cid, pid))
                hook_harnesses |= set(harnesses)
                continue

            realized: dict[str, str] = {}
            for harness in harnesses:
                template = MATRIX[method].get(harness)
                if template is None:
                    report["no_realization"].append(
                        {"component": cid, "part": pid, "method": method,
                         "harness": harness})
                    continue
                rel = template.format(name=named)
                claim_file(rel, _content_for(
                    rel, method, named,
                    desc or f"{pid} — exposed via {cid}/{EXPOSURE_NAME}",
                    entry_abs, comp_dir, entry_file), cid, pid)
                realized[harness] = rel
            if method == "rule" and realized:
                # The REALIZED path per harness, not the part id: a component
                # installed for claude only put no file under
                # `.agents/behavior-rules/`, so codex's forced read must not
                # enumerate one (a MANDATORY Step 0 pointing at a missing file).
                rule_parts.append((named, desc, realized))

    # ── D7/D12: shared-file claims, recomputed from the whole set ──
    claims: list[dict] = []

    def claim_json(rel: str, key: list[str], value, owner=None) -> None:
        rec = {"path": rel, "fmt": "json", "key": key, "value": value}
        if owner is not None:
            rec["owner"] = owner
        claims.append(rec)

    def _owners_of(table: dict, key: str) -> list:
        return list(table.get(key) or [])

    def _all_owners(table: dict) -> list:
        seen: list = []
        for key in sorted(table):
            for owner in table[key]:
                if owner not in seen:
                    seen.append(owner)
        return seen

    if servers:
        if "claude" in server_harnesses:
            for name in sorted(servers):
                for owner in _owners_of(server_owners, name) or [None]:
                    claim_json(".mcp.json", ["mcpServers", name],
                               servers[name], owner)
            # measured 2026-08-08, claude 2.1.226: without the flag every
            # project server sits "Pending approval".
            for owner in _all_owners(server_owners) or [None]:
                claim_json(".claude/settings.json",
                           ["enableAllProjectMcpServers"], True, owner)
        if "codex" in server_harnesses:
            for owner in _all_owners(server_owners) or [None]:
                rec = {"path": ".codex/config.toml", "fmt": "text",
                       "comment": "#", "key": None,
                       "value": _codex_mcp_toml_block(servers)}
                if owner is not None:
                    rec["owner"] = owner
                claims.append(rec)
        if "opencode" in server_harnesses:
            for name in sorted(servers):
                for owner in _owners_of(server_owners, name) or [None]:
                    claim_json("opencode.json", ["mcp", name],
                               _opencode_mcp_entry(servers[name]), owner)
        # kimi: no project-local MCP auto-load (measured — `cli/mcp.py` stores
        # servers at `~/.kimi/mcp.json`). The root `.mcp.json` above IS its
        # realization, passed at launch: `kimi --mcp-config-file .mcp.json`.
    if hooks:
        for event in sorted(hooks):
            ev_owners = _owners_of(hook_owners, event) or [None]
            if "claude" in hook_harnesses:
                for owner in ev_owners:
                    claim_json(".claude/settings.json", ["hooks", event],
                               hooks[event], owner)
            if "codex" in hook_harnesses:
                # codex 0.144.5 measured shape: the claude `hooks` object
                # verbatim (d-seat-exposes-frontmatter measurement amendment).
                for owner in ev_owners:
                    claim_json(".codex/hooks.json", ["hooks", event],
                               hooks[event], owner)
        # opencode has no hooks surface; kimi's hooks are user-scope
        # (`~/.kimi/config.toml` `hooks = [...]`) — neither is minted here.

    # D8 — the exposure surface is the GENERATED GUIDANCE FILE, not a file of
    # this installer's invention. The parts ride the report to `_add_mirror`,
    # which knows the harnesses and therefore which guidance file gets what.
    report["agents_parts"] = agents_parts
    report["rule_parts"] = rule_parts
    report["shared_files"] = sorted({c["path"] for c in claims})
    return files, owners, claims, report


def _read_json(path: Path, method: str, cid: str, pid: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refuse(
            f"{method}-declaration-invalid",
            f"{cid}: {method} entry-point for {pid!r} is not readable JSON "
            f"({exc}) — refusing before any write",
            str(path)) from exc


# ── target discovery ────────────────────────────────────────────────────────

# D24  TARGET DISCOVERY (owner ruling, 2026-08-21) — `--target` stays the
#      explicit form and always wins. WITHOUT it, the target is DISCOVERED by
#      walking upward from the current directory, exactly as `install.py`
#      resolved its own `rbtv.json`: the first ancestor holding the state file
#      (`.rbtv/config/install.json`) is the workspace, and failing that the
#      first ancestor holding a `.rbtv/` directory at all — which is what a
#      never-yet-installed workspace looks like, since `.rbtv/mirror` is
#      already there. Neither found → cwd, the previous behaviour. The walk
#      stops at the filesystem root; a discovered root is always REPORTED (on
#      stderr, so `--json` stays machine-readable) because a silent target is
#      how a run lands in the wrong tree.

DISCOVER_STATE = "state file"
DISCOVER_RBTV = ".rbtv/ directory"
DISCOVER_CWD = "cwd (no .rbtv/ found above)"


def discover_target(start: Path) -> tuple[Path, str]:
    """Resolve the install root from `start` upward. Returns (root, why)."""
    here = start.resolve()
    chain = [here, *here.parents]
    for cand in chain:
        if (cand / STATE_REL).is_file():
            return cand, DISCOVER_STATE
    for cand in chain:
        if (cand / ".rbtv").is_dir():
            return cand, DISCOVER_RBTV
    return here, DISCOVER_CWD


# ── state ───────────────────────────────────────────────────────────────────

def read_state(target: Path) -> dict:
    path = target / STATE_REL
    if not path.is_file():
        return {"schema": SCHEMA, "installer": "install2.py", "components": {},
                "shared_claims": []}
    state = json.loads(path.read_text(encoding="utf-8"))
    rewrite_legacy_skill_ids(state)
    strip_retired_harnesses(state)
    return state


def write_state(target: Path, state: dict) -> None:
    path = target / STATE_REL
    state["schema"] = SCHEMA
    state["installer"] = "install2.py"
    state["version"] = VERSION
    state["marker"] = MANAGED_MARK
    state["installed_at"] = _dt.datetime.now().isoformat(timespec="seconds")
    state["target"] = str(target.resolve())
    state.pop("prefix", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def known_files(state: dict) -> set[str]:
    out = set(state.get("guidance_files") or [])
    for rec in (state.get("components") or {}).values():
        out |= rec_files(rec)
    return out


def upgrade_book(state: dict, catalog_parts: dict[str, list[dict]]) -> dict:
    """In-memory schema-2 view. Does not strip rec['files'] (apply still needs them).

    A booked id that is no longer catalogued and owns nothing (no files, no
    claims, no PATH links) is dropped: it never installed anything, so there
    is nothing to protect. A vanished id that DOES own files stays and later
    refuses component-vanished.
    """
    strip_retired_harnesses(state)
    out = dict(state)
    out["schema"] = SCHEMA
    comps = {k: dict(v) for k, v in (state.get("components") or {}).items()}
    for cid in list(comps):
        rec = comps[cid]
        if cid not in catalog_parts and rec_owns_nothing(rec):
            comps.pop(cid)
            continue
        if "parts" in rec:
            rec["parts"] = {p: dict(b) for p, b in rec["parts"].items()}
            continue
        if cid not in catalog_parts:
            continue
        rec["parts"] = {r["id"]: {"method": r["method"], "files": []}
                        for r in catalog_parts[cid]}
    out["components"] = comps
    out.pop("prefix", None)
    return out


def _rebuild_claim(target: Path, claim_id: str, owner: tuple) -> dict | None:
    """Reconstruct a planned claim from a booked id + on-disk value.

    Used when a vanished component's remaining parts cannot remint from a
    catalog: D7 still needs the claim in the planned set so apply does not
    release a sibling part's key.
    """
    rel, _, keypart = claim_id.partition("::")
    path = target / rel
    if not path.is_file():
        return None
    if keypart == "#block":
        text = path.read_text(encoding="utf-8")
        start, end = _fence("#")
        if start not in text or end not in text:
            return None
        body = text.split(start, 1)[1].split(end, 1)[0].strip("\n")
        return {"path": rel, "fmt": "text", "comment": "#", "key": None,
                "value": body, "owner": owner}
    key = json.loads(keypart)
    try:
        doc = json.loads(path.read_text(encoding="utf-8") or "{}")
    except ValueError:
        return None
    value, found = _jget(doc, key)
    if not found:
        return None
    return {"path": rel, "fmt": "json", "key": key, "value": value,
            "owner": owner}


def known_claims(state: dict) -> set[str]:
    return set(state.get("shared_claims") or [])


# ── apply ───────────────────────────────────────────────────────────────────

def apply(target: Path, files: dict[str, str], claims: list[dict], state: dict,
          dry_run: bool, protect: frozenset[str] = frozenset()) -> dict:
    """Write the planned set and remove what the previous book held but the plan
    no longer does. Every collision (D6) refuses BEFORE the first write.

    `protect` names paths that MUST NOT be deleted however the book reads them.
    It exists for the D13 basis flip: yesterday's generated mirror can be
    today's hand-authored basis under the same name, and the book alone cannot
    tell those apart — "never written" has to mean "never removed" too."""
    ours_files = known_files(state)
    ours_claims = known_claims(state)

    # D12/D13 ADOPTION — a planned path that exists and is not in our book, but
    # whose own head PROVES a tool wrote it (our ownership marker, or a
    # generated-mirror banner) is taken over and booked. The collision refusal
    # exists to protect HAND-AUTHORED files; a file that says on its face it was
    # generated is not one. Without that proof it still refuses.
    collisions, adopted = [], []
    for rel in files:
        if rel in ours_files or not (target / rel).exists():
            continue
        if _is_ours(target, rel):
            adopted.append(rel)
            continue
        collisions.append(rel)
    collisions.sort()
    adopted.sort()
    # Key-level collisions inside shared files (D12).
    for claim in claims:
        cid = _claim_id(claim["path"], claim["key"])
        if cid in ours_claims:
            continue
        path = target / claim["path"]
        if not path.is_file():
            continue
        if claim["fmt"] == "json":
            try:
                doc = json.loads(path.read_text(encoding="utf-8") or "{}")
            except ValueError as exc:
                raise Refuse(
                    "shared-file-unparseable",
                    f"{claim['path']} exists but is not readable JSON ({exc}) "
                    "— refusing before any write rather than replacing a file "
                    "this installer did not create",
                    str(path)) from exc
            if _jget(doc, claim["key"])[1]:
                collisions.append(f"{claim['path']}::"
                                  + ".".join(claim["key"]))
        else:
            start, _ = _fence(claim["comment"])
            if start in path.read_text(encoding="utf-8"):
                collisions.append(f"{claim['path']}::{FENCE_ID}-block")
    if collisions:
        collisions = sorted(set(collisions))
        # D13 — a root guidance file collides for its own reason, and the
        # generic "move or remove it" advice would tell the user to delete
        # hand-authored guidance. Say what this file actually is instead.
        mirrors = [rel for rel in collisions
                   if rel.rsplit("/", 1)[-1] in GUIDANCE_NAMES]
        if mirrors:
            raise Refuse(
                "guidance-mirror-collision",
                f"{', '.join(mirrors)} already exists and "
                "this installer did not write it — it is either hand-authored "
                "guidance or a mirror rendered by another tool (install.py's "
                "`model_mirror` renders one beside every CLAUDE.md). This run "
                f"would generate it from the basis. DO NOT delete it: either "
                f"`--guidance-basis {BASIS_NONE}` to leave both root guidance "
                "files alone, or point the basis at the file you author and "
                "retire the other tool's copy of the one it generates. "
                "Nothing was written",
                mirrors[0])
        raise Refuse(
            "collision",
            "the install root already carries content this run would write and "
            "this installer did not write it (the old installer's, or "
            "hand-placed): " + ", ".join(collisions) + " — refusing before any "
            "write; move or remove it, or narrow --component/--harness",
            collisions[0])

    # D12 RELEASE — a booked file whose marker is gone was taken over by a
    # human between runs. It leaves the book (`_rebook` recomputes from the
    # plan) but is NEVER deleted; the caller reports it instead.
    stale = sorted(ours_files - set(files) - protect)
    released = [rel for rel in stale
                if (target / rel).is_file() and not _is_ours(target, rel)]
    stale_files = [rel for rel in stale if rel not in released]
    planned_claims = {_claim_id(c["path"], c["key"]) for c in claims}
    stale_claims = sorted(ours_claims - planned_claims)

    if dry_run:
        return {"written": [], "skipped": sorted(files), "deleted": stale_files,
                "shared": sorted(planned_claims), "adopted": adopted,
                "released": released,
                "shared_removed": stale_claims, "dry_run": True}

    written, skipped = [], []
    for rel in sorted(files):
        path, body = target / rel, files[rel]
        # D15 — a copied skill folder may carry a binary asset, so a planned
        # file is bytes OR text; everything else on this path is text.
        if path.is_file() and _same(path, body):
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            path.write_bytes(body)
        else:
            path.write_text(body, encoding="utf-8", newline="\n")
        written.append(rel)

    deleted = []
    for rel in stale_files:
        path = target / rel
        if path.is_file():
            path.unlink()
            deleted.append(rel)
        _prune(target, path.parent)

    _apply_shared(target, claims, stale_claims)
    return {"written": written, "skipped": skipped, "deleted": deleted,
            "shared": sorted(planned_claims), "shared_removed": stale_claims,
            "adopted": adopted, "released": released, "dry_run": False}


def _same(path: Path, body: str | bytes) -> bool:
    """Is the file already exactly this content? Bytes compare as bytes; text
    compares as text (an unreadable file is simply not equal)."""
    try:
        return (path.read_bytes() == body if isinstance(body, bytes)
                else path.read_text(encoding="utf-8") == body)
    except (OSError, UnicodeDecodeError):
        return False


def _apply_shared(target: Path, claims: list[dict],
                  stale_claims: list[str]) -> None:
    """Set every planned claim and drop every stale one — key by key, block by
    block (D12). A shared file is deleted only when NOTHING is left in it."""
    touched: dict[str, dict] = {}
    for claim in claims:
        touched.setdefault(claim["path"], {"fmt": claim["fmt"],
                                           "comment": claim.get("comment", "#"),
                                           "set": [], "del": []})
        touched[claim["path"]]["set"].append(claim)
    for cid in stale_claims:
        rel, _, keypart = cid.partition("::")
        fmt = "json" if keypart != "#block" else "text"
        entry = touched.setdefault(rel, {"fmt": fmt, "comment": "#",
                                         "set": [], "del": []})
        entry["del"].append(None if keypart == "#block" else json.loads(keypart))

    for rel, work in touched.items():
        path = target / rel
        if work["fmt"] == "json":
            doc = {}
            if path.is_file():
                doc = json.loads(path.read_text(encoding="utf-8") or "{}")
            for key in work["del"]:
                _jdel(doc, key)
            for claim in work["set"]:
                _jset(doc, claim["key"], claim["value"])
            text = json.dumps(doc, indent=2, sort_keys=True) + "\n" if doc else ""
        else:
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
            if work["del"]:
                text = _block_del(text, work["comment"])
            for claim in work["set"]:
                text = _block_set(text, claim["value"], work["comment"])
            if not text.strip():
                text = ""
        if not text:
            if path.is_file():
                path.unlink()
            _prune(target, path.parent)
            continue
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def _clean_bases(target: Path, report: dict, dry_run: bool) -> None:
    """Write back the bases whose stale GENERATED banner we removed (D13, the
    empty-target flip). Never booked — a basis on the book is a basis on some
    later uninstall's delete set."""
    debanner = report.pop("_debanner", None) or {}
    if not dry_run:
        for rel, text in debanner.items():
            (target / rel).write_text(text, encoding="utf-8", newline="\n")
    report["guidance_debannered"] = sorted(debanner)


def _prune(target: Path, directory: Path) -> None:
    """Remove directories our deletion emptied — never above the target."""
    target = target.resolve()
    current = directory.resolve()
    while current != target and target in current.parents:
        try:
            next(current.iterdir())
            return
        except StopIteration:
            current.rmdir()
        except OSError:
            return
        current = current.parent


# ── verbs ───────────────────────────────────────────────────────────────────

def part_key(cid: str, pid: str) -> str:
    """Global selector key. R1: `{cid}#{part-id}` — no method in the key."""
    return f"{cid}#{pid}"


def iter_catalog_parts(catalog: dict[str, dict]) -> list[dict]:
    out: list[dict] = []
    for cid, c in catalog.items():
        if not is_installable(c):
            continue
        for spec in _part_specs(c):
            pid = spec["id"]
            if not pid:
                continue
            out.append({
                "key": part_key(cid, pid),
                "component": cid,
                "module": c.get("module") or cid.split("/")[0],
                "part_id": pid,
                "method": spec.get("method") or "",
            })
    return out


def iter_booked_parts(catalog: dict[str, dict],
                      book: dict[str, dict] | None) -> list[dict]:
    by_cid: dict[str, list[dict]] = {}
    for p in iter_catalog_parts(catalog):
        by_cid.setdefault(p["component"], []).append(p)
    booked: list[dict] = []
    for cid, rec in (book or {}).items():
        declared = rec.get("parts")
        if isinstance(declared, dict) and declared:
            for pid, part in declared.items():
                booked.append({
                    "key": part_key(cid, pid),
                    "component": cid,
                    "module": rec.get("module") or cid.split("/")[0],
                    "part_id": pid,
                    "method": (part or {}).get("method") or "",
                })
        elif isinstance(declared, list) and declared:
            for d in declared:
                pid = (d.get("part-id") or d.get("part_id") or "").strip()
                booked.append({
                    "key": part_key(cid, pid),
                    "component": cid,
                    "module": rec.get("module") or cid.split("/")[0],
                    "part_id": pid,
                    "method": (d.get("method") or "").strip(),
                })
        elif cid in by_cid:
            booked.extend(by_cid[cid])
        else:
            name = rec.get("component") or cid.split("/")[-1]
            booked.append({
                "key": part_key(cid, name),
                "component": cid,
                "module": rec.get("module") or cid.split("/")[0],
                "part_id": name,
                "method": "component",
            })
    return booked


def scan_fingerprint(catalog: dict[str, dict]) -> str:
    """sha256 of sorted JSON of catalog part keys ∪ catalog ids."""
    keys = sorted({p["key"] for p in iter_catalog_parts(catalog)} | set(catalog))
    return hashlib.sha256(
        json.dumps(keys, separators=(",", ":")).encode()).hexdigest()


def write_index(target: Path, catalog: dict[str, dict],
                book: dict[str, dict] | None = None) -> dict:
    parts = iter_catalog_parts(catalog)
    booked = iter_booked_parts(catalog, book) if book is not None else []
    modules = sorted({p["module"] for p in parts}
                     | {c.get("module") or cid.split("/")[0]
                        for cid, c in catalog.items()})
    components = sorted(set(catalog) | {p["component"] for p in booked})
    part_ids = sorted({p["key"] for p in parts} | {p["key"] for p in booked})
    n: dict[str, dict] = {}
    i = 1
    for mid in modules:
        n[str(i)] = {"kind": "module", "id": mid}
        i += 1
    for cid in components:
        n[str(i)] = {"kind": "component", "id": cid}
        i += 1
    for key in part_ids:
        n[str(i)] = {"kind": "part", "id": key}
        i += 1
    payload = {"fingerprint": scan_fingerprint(catalog), "n": n}
    path = target / INDEX_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def read_index(target: Path) -> dict | None:
    path = target / INDEX_REL
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _norm_comp(name: str) -> str:
    if name == "hub" or name.startswith("hub/"):
        return "_" + name
    return name


def _expand_nums(tokens: list[str], want: str, index: dict | None,
                 fp: str) -> list[str]:
    out: list[str] = []
    for t in tokens:
        if not t.isdigit():
            out.append(t)
            continue
        if not index:
            raise Refuse("index-missing",
                         f"numeric selector {t!r} but no ls/li index")
        if index.get("fingerprint") != fp:
            raise Refuse("index-stale",
                         "scanned set changed since last ls/li")
        slot = (index.get("n") or {}).get(str(t))
        if not slot:
            raise Refuse("index-unknown", f"no index slot {t}")
        sk = slot["kind"]
        if sk != want and not (want == "component" and sk == "part"):
            raise Refuse("index-kind-mismatch",
                         f"index {t} is {sk}, not {want}")
        out.append(slot["id"])
    return out


def _comp_hits(name: str, names_c: set[str], pool: list[dict]) -> bool:
    if name in names_c:
        return True
    if any(p["key"] == name for p in pool):
        return True
    if any(cid == name or cid.endswith("/" + name)
           or cid.split("/")[-1] == name for cid in names_c):
        return True
    return False


def _match_c(p: dict, toks: list[str]) -> bool:
    if p["component"] in toks or p["key"] in toks:
        return True
    short = p["component"].split("/")[-1]
    return short in toks or p["component"].endswith("/" + short) and short in toks


def resolve_selection(args, catalog: dict[str, dict],
                      book: dict[str, dict] | None = None) -> set[str]:
    """AND across selector kinds, OR within a kind, exclusions last.

    Returns a set of `{cid}#{part-id}` keys (R1). `add` universe = installable
    catalog parts. `rm` universe = catalog ∪ booked (incl. vanished); output
    is the booked intersection.
    """
    verb = getattr(args, "verb", None)
    index = getattr(args, "index", None)
    fp = scan_fingerprint(catalog)
    pos_m = [module_id(x) for x in _expand_nums(
        list(getattr(args, "module", None) or []), "module", index, fp)]
    neg_m = [module_id(x) for x in _expand_nums(
        list(getattr(args, "exclude_module", None) or []), "module", index, fp)]
    pos_c = [_norm_comp(x) for x in _expand_nums(
        list(getattr(args, "component", None) or []), "component", index, fp)]
    neg_c = [_norm_comp(x) for x in _expand_nums(
        list(getattr(args, "exclude_component", None) or []),
        "component", index, fp)]
    pos_x = list(getattr(args, "method", None) or [])
    neg_x = list(getattr(args, "exclude_method", None) or [])
    flag_a = bool(getattr(args, "all", False))
    if not (flag_a or pos_m or pos_c or pos_x):
        raise Refuse("selection-empty",
                     "need -A or a non-exclusion -m/-c/-x")

    cat_parts = iter_catalog_parts(catalog)
    booked = iter_booked_parts(catalog, book)
    names_c = set(catalog) | {p["component"] for p in booked}
    names_m = ({c.get("module") or cid.split("/")[0]
                for cid, c in catalog.items()}
               | {p["module"] for p in booked})
    pool = cat_parts + booked
    for label, bucket, names, code in (
        ("module", pos_m + neg_m, names_m, "module-unknown"),
        ("component", pos_c + neg_c, names_c, "component-unknown"),
    ):
        for n in bucket:
            if label == "component":
                if not _comp_hits(n, names, pool):
                    raise Refuse(code, f"no {label} {n!r} on either tree")
            elif n not in names:
                raise Refuse(code, f"no {label} {n!r} on either tree")
    for n in pos_c + neg_c:
        if n in catalog and not is_installable(catalog[n]) and n not in (book or {}):
            raise Refuse("component-not-installable",
                         f"{n!r} has no exposure manifest")

    by_key = {p["key"]: p for p in (cat_parts if verb != "rm" else pool)}
    universe = list(by_key.values())
    selected = set(by_key)
    if pos_m:
        selected &= {p["key"] for p in universe if p["module"] in pos_m}
    if pos_c:
        selected &= {p["key"] for p in universe if _match_c(p, pos_c)}
    if pos_x:
        selected &= {p["key"] for p in universe if p["method"] in pos_x}
    if neg_m:
        selected -= {p["key"] for p in universe if p["module"] in neg_m}
    if neg_c:
        selected -= {p["key"] for p in universe if _match_c(p, neg_c)}
    if neg_x:
        selected -= {p["key"] for p in universe if p["method"] in neg_x}

    if verb == "rm":
        booked_keys = {p["key"] for p in booked}
        hit = selected & booked_keys
        if not hit:
            raise Refuse(
                "not-installed",
                "not installed at this target: "
                + ", ".join(sorted(selected) or pos_c or pos_m or pos_x
                            or ["-A"]))
        return hit
    if not selected:
        raise Refuse("selection-empty",
                     "selectors matched no installable part")
    return selected


def _sel(verb: str = "add", **kw):
    base = dict(all=False, module=[], component=[], method=[],
                exclude_module=[], exclude_component=[], exclude_method=[],
                index=None, verb=verb)
    base.update(kw)
    return argparse.Namespace(**base)


def _has_negative(args) -> bool:
    return bool(getattr(args, "exclude_module", None)
                or getattr(args, "exclude_component", None)
                or getattr(args, "exclude_method", None))


def confirm_removal(keys, *, dry_run: bool, ask=None) -> bool:
    """R7 guard: print the full resolved removal list. Dry-run never asks."""
    print("DRY RUN — would remove:" if dry_run else "will remove:")
    for k in sorted(keys):
        print(f"  {k}")
    if dry_run:
        return True
    fn = ask or input
    try:
        ans = fn("Proceed? [y/N]: ")
    except EOFError:
        ans = ""
    return str(ans).strip().lower() in ("y", "yes")


def _split_part_keys(keys) -> tuple[list[str], list[str]]:
    return sorted({k.split("#", 1)[0] for k in keys}), sorted(keys)


def is_installable(comp: dict) -> bool:
    """A unit this installer can act on: a component with an exposure manifest,
    or a D15 whole-skill folder (which has no manifest by construction)."""
    return bool(comp["manifest"]) or (
        comp.get("kind") == "hub" and not comp.get("hub_refusal"))


def do_scan(catalog: dict[str, dict], shadowed: list[dict]) -> dict:
    entries = []
    for cid in sorted(catalog):
        c = catalog[cid]
        hub = c.get("kind") == "hub"
        rows = exposure_rows(c) if c["manifest"] else []
        refusal = c.get("hub_refusal") or ""
        specs = _part_specs(c)
        entries.append({
            "id": cid, "tree": c["tree"], "module": c["module"],
            "kind": c.get("kind", "component"),
            "manifest": c["manifest"],
            "methods": ([c["method"]] if hub else
                        sorted({(r.get("method") or "").strip() for r in rows
                                if (r.get("part-id") or "").strip()})),
            "parts": len(specs),
            "note": (_hub_refuse_message(c) if refusal else ""),
            "refusal": refusal,
        })
    return {"ok": True, "components": entries, "shadowed": shadowed,
            "hub_refusals": [e["id"] for e in entries if e.get("refusal")]}


def _rebook(state: dict, records: dict, files: dict, owners: dict,
            claims: list[dict], report: dict,
            path_owners: dict[str, tuple[str, str]] | None = None,
            keep_cids: set[str] | None = None) -> None:
    keep_cids = set(keep_cids or ())
    for cid, rec in records.items():
        parts = rec.setdefault("parts", {})
        rec_names: list[str] = []
        for pid, part in parts.items():
            part["files"] = sorted(
                rel for rel, own in owners.items() if (cid, pid) in own)
            owned = sorted(
                _claim_id(c["path"], c["key"])
                for c in claims if c.get("owner") == (cid, pid))
            if owned:
                part["claims"] = owned
            else:
                part.pop("claims", None)
            if path_owners is not None and cid not in keep_cids:
                ln = sorted(n for n, own in path_owners.items()
                            if own == (cid, pid))
                if ln:
                    part["links"] = ln
                    rec_names.extend(ln)
                else:
                    part.pop("links", None)
            elif part.get("links"):
                rec_names.extend(part["links"])
            if not part.get("links"):
                part.pop("links", None)
        if path_owners is not None and cid not in keep_cids:
            if rec_names:
                rec["path_links"] = sorted(set(rec_names))
            else:
                rec.pop("path_links", None)
        rec.pop("files", None)
    state["components"] = records
    state["guidance_files"] = sorted(
        rel for rel, own in owners.items() if own == ["<aggregate>"])
    state["shared_claims"] = sorted(
        _claim_id(c["path"], c["key"]) for c in claims)
    state["shared_files"] = report["shared_files"]
    state.pop("prefix", None)


def _add_mirror(target: Path, state: dict, files: dict, owners: dict,
                report: dict, override: str | None, harnesses,
                exclude_override: list[str] | None = None) -> frozenset[str]:
    """Fold the D13 mirror into the planned set — booked as an aggregate file,
    so collision-gating, idempotence and uninstall come from the same machinery
    every other installer-owned file uses.

    Returns the paths `apply` must never delete: EVERY directory's CURRENT basis
    (D13 is recursive). The book can hold those same names from an earlier run
    when they were the generated mirrors (the flip: yesterday's mirror is
    today's hand-authored basis), and deleting one as stale would destroy
    user-authored guidance. The book itself is corrected by `_rebook`, which
    recomputes `guidance_files` from the new plan.
    """
    basis = resolve_basis(state.get("guidance_basis"), override)
    excludes = (list(exclude_override) if exclude_override is not None
                else list(state.get("guidance_excludes") or []))
    blocks = {name: _exposure_block(name, list(harnesses),
                                    report.get("agents_parts") or [],
                                    report.get("rule_parts") or [])
              for name in GUIDANCE_NAMES}
    mirrors, bases, stripped, targets, debanner = plan_mirror(
        target, basis, harnesses, excludes, blocks)
    # Carried privately: these are writes OUTSIDE the booked-file machinery
    # (booking a basis would put it on a later uninstall's delete set).
    report["_debanner"] = debanner
    for rel, content in mirrors.items():
        files[rel] = content
        owners[rel] = ["<aggregate>"]
    report["guidance_mirror"] = (
        {"basis": basis, "targets": targets,
         "count": len(mirrors), "excludes": excludes,
         "banner_stripped": stripped} if basis
        else {"basis": None, "targets": []})
    # D8 — every guidance file an installed harness reads that this run does NOT
    # write (the basis, or all of them when the mirror is off) needs its block
    # placed by hand. Reported, never written.
    needed = {GUIDANCE_FILE[h] for h in harnesses if h in GUIDANCE_FILE}
    report["guidance_manual"] = {
        name: block for name, block in blocks.items()
        if block and name in needed and name not in targets}
    return bases


GITIGNORE_NOTE = (
    "installer2 (install2.py) artifacts — MACHINE-LOCAL, never committed: the "
    "loaders bake\nabsolute entry-point paths and the book records an absolute "
    "target, so a committed copy\nis wrong on every other machine "
    "(d-s15-installer2-artifacts-machine-local). Generated from\nthe book on "
    "every install and uninstall — edit nothing between the fences; re-run the\n"
    "installer instead. The guidance mirror is deliberately absent: it is "
    "workspace content.")


def _add_gitignore(target: Path, owners: dict[str, list], claims: list[dict],
                   report: dict) -> None:
    """Claim the `.gitignore` block that keeps our artifacts out of git (D14).

    Listed: every per-component file (the `<aggregate>` owner is the guidance
    mirror, which is workspace content and stays committable) plus the book.
    Skipped entirely off a git repo. Files git ALREADY TRACKS are reported,
    because no ignore rule reaches one."""
    if not (target / ".git").exists():
        report["gitignore"] = {"claimed": False, "reason": "not a git repo"}
        return
    paths = sorted([rel for rel, own in owners.items() if own != ["<aggregate>"]]
                   + [STATE_REL.as_posix()])
    if len(paths) == 1:                       # the book alone — nothing installed
        report["gitignore"] = {"claimed": False, "reason": "nothing installed"}
        return
    claims.append({"path": ".gitignore", "fmt": "text", "comment": "#",
                   "key": None,
                   "value": "\n".join("# " + ln for ln in
                                      GITIGNORE_NOTE.split("\n"))
                            + "\n" + "\n".join(paths)})
    report["gitignore"] = {"claimed": True, "count": len(paths),
                           "tracked": _tracked(target, paths)}


def _tracked(target: Path, paths: list[str]) -> list[str]:
    """The listed paths git already tracks — `.gitignore` cannot reach those.
    Empty when git is unavailable; this is a report, never a gate."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(target), "ls-files", "--", *paths],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    return sorted(set(out.stdout.split()) & set(paths))


def installed_harnesses(records: dict[str, dict]) -> list[str]:
    """The harness set the whole installed set targets — the union across the
    book's records, in canonical order. This is what keys the guidance mirror
    (D13): a component installed for codex is what puts AGENTS.md on the tree."""
    return [h for h in HARNESSES
            if any(h in (rec.get("harnesses") or []) for rec in records.values())]


def _merge_harnesses(old, new) -> list[str]:
    both = set(old or []) | set(new or [])
    return [h for h in HARNESSES if h in both]


def _parts_for_cid(cid: str, parts: list[str] | None) -> list[str] | None:
    """None = all/refresh. Bare pids apply to every cid. `{cid}#{pid}` only to theirs."""
    if parts is None:
        return None
    keyed, bare = [], []
    for p in parts:
        if "#" in p:
            owner, pid = p.split("#", 1)
            if owner == cid:
                keyed.append(pid)
        else:
            bare.append(p)
    return bare + keyed if (bare or keyed or not any("#" in p for p in parts)) else []


def _select_parts(comp: dict, existing_parts, requested: list[str] | None
                  ) -> dict:
    specs = {r["id"]: r["method"] for r in _part_specs(comp, strict=True)}
    if requested is None:
        if existing_parts is not None:
            return {pid: dict(p) for pid, p in existing_parts.items()}
        return {pid: {"method": method, "files": []}
                for pid, method in specs.items()}
    out = {pid: dict(p) for pid, p in (existing_parts or {}).items()}
    for pid in requested:
        if pid not in specs:
            raise Refuse(
                "part-unknown",
                f"{comp.get('id', '?')}: no part {pid!r} in the exposure "
                "manifest — refusing before any write",
                str(Path(comp["path"]) / EXPOSURE_NAME))
        if pid not in out:
            out[pid] = {"method": specs[pid], "files": []}
    return out


def do_install(target: Path, catalog: dict[str, dict], picked: list[str],
               harnesses: list[str], dry_run: bool,
               guidance_basis: str | None = None,
               guidance_excludes: list[str] | None = None,
               parts: list[str] | None = None,
               write_path: bool = False) -> dict:
    state = upgrade_book(read_state(target), catalog_parts_map(catalog))
    records = dict(state.get("components") or {})
    for cid in picked:
        c = catalog[cid]
        existing = records.get(cid) or {}
        rec = {"tree": c["tree"], "tree_root": c["tree_root"],
               "module": c["module"], "component": c["component"],
               "harnesses": _merge_harnesses(existing.get("harnesses"),
                                             harnesses),
                "parts": _select_parts(c, existing.get("parts"),
                                       _parts_for_cid(cid, parts))}
        if "files" in existing:
            rec["files"] = list(existing["files"])
        records[cid] = rec
    files, owners, claims, report = plan_files(records, catalog)
    desired, path_owners = plan_path_links(target, _path_rows_from_report(report))
    booked = booked_path_names(state)
    bindir = bin_dir()
    gate_path_links(bindir, desired, booked - set(desired))
    report["path_bootstrap"] = PATH_BOOTSTRAP
    protect = _add_mirror(target, state, files, owners, report, guidance_basis,
                          installed_harnesses(records), guidance_excludes)
    _add_gitignore(target, owners, claims, report)
    result = apply(target, files, claims, state, dry_run, protect)
    _clean_bases(target, report, dry_run)
    if not dry_run:
        _rebook(state, records, files, owners, claims, report,
                path_owners=path_owners)
        if guidance_basis is not None:
            state["guidance_basis"] = guidance_basis
        if guidance_excludes is not None:
            state["guidance_excludes"] = list(guidance_excludes)
        if write_path:
            state["path_bootstrap"] = True
        write_state(target, state)
        report["path"] = reconcile(bindir, desired, booked, dry=False)
        if write_path:
            _write_shell_path()
    else:
        report["path"] = reconcile(bindir, desired, booked, dry=True)
    return {"ok": True, "installed": picked, "harnesses": harnesses,
            "files": sorted(files), **result, "report": report}


def do_uninstall(target: Path, catalog: dict[str, dict], picked: list[str],
                 dry_run: bool, parts: list[str] | None = None) -> dict:
    state = upgrade_book(read_state(target), catalog_parts_map(catalog))
    records = dict(state.get("components") or {})
    missing = [cid for cid in picked if cid not in records]
    if missing:
        raise Refuse("not-installed",
                     "not installed at this target: " + ", ".join(missing))
    for cid in picked:
        rec = records[cid]
        want = _parts_for_cid(cid, parts)
        if want is None:
            records.pop(cid)
            continue
        if "parts" not in rec:
            name = rec.get("component") or cid.split("/")[-1]
            if set(want) <= {name}:
                records.pop(cid)
                continue
            raise Refuse(
                "part-unbooked",
                f"{cid} has no parts map (a vanished v1 record) — remove the "
                "whole component; files cannot be split across parts")
        for pid in want:
            rec["parts"].pop(pid, None)
        if not rec["parts"]:
            records.pop(cid)
    live = {cid: rec for cid, rec in records.items() if cid in catalog}
    stranded = {cid: rec for cid, rec in records.items() if cid not in catalog}
    blockers = [cid for cid, rec in stranded.items() if "parts" not in rec]
    if blockers:
        rec0 = stranded[blockers[0]]
        raise Refuse(
            "component-vanished",
            f"component {blockers[0]!r} is recorded as installed but no longer "
            f"exists under {rec0.get('tree_root')!r} (renamed or deleted "
            "upstream). Every run at this target refuses until the book "
            "agrees with the trees. Recover with EITHER: restore the "
            f"folder; or `uninstall --component {blockers[0]}`, which needs no "
            "tree — the book holds its files",
            str(rec0.get("tree_root", "")))
    files, owners, claims, report = plan_files(live, catalog)
    desired, path_owners = plan_path_links(target, _path_rows_from_report(report))
    booked = booked_path_names(state)
    keep_names = booked_path_names({"components": stranded})
    bindir = bin_dir()
    gate_path_links(bindir, desired, booked - set(desired) - keep_names)
    report["path_bootstrap"] = PATH_BOOTSTRAP
    keep_protect: set[str] = set()
    for cid, rec in stranded.items():
        for pid, part in rec["parts"].items():
            for rel in part.get("files") or []:
                keep_protect.add(rel)
                owners.setdefault(rel, []).append((cid, pid))
            for claim_id in part.get("claims") or []:
                rebuilt = _rebuild_claim(target, claim_id, (cid, pid))
                if rebuilt:
                    claims.append(rebuilt)
    report["shared_files"] = sorted({c["path"] for c in claims})
    protect: frozenset[str] = frozenset(keep_protect)
    if records:
        # Components remain → the mirror stays. A full uninstall takes it with
        # everything else (it is installer-owned output, not the basis).
        try:
            protect = protect | _add_mirror(
                target, state, files, owners, report, None,
                installed_harnesses(records))
        except Refuse as exc:
            # Removing a component must NEVER be blocked by a mirror problem
            # (a deleted basis, a hand-edited book). Skip the replan, and keep
            # EVERY guidance file the book holds, under either name and at any
            # depth, off the delete set — un-managed on disk beats deleted, and
            # the next install re-books whatever is real.
            protect = protect | frozenset(GUIDANCE_NAMES) | frozenset(
                rel for rel in known_files(state)
                if rel.rsplit("/", 1)[-1] in GUIDANCE_NAMES)
            report["guidance_mirror"] = {"basis": None, "targets": [],
                                         "skipped": exc.code}
    _add_gitignore(target, owners, claims, report)
    result = apply(target, files, claims, state, dry_run, protect)
    _clean_bases(target, report, dry_run)
    if not dry_run:
        if records:
            _rebook(state, records, files, owners, claims, report,
                    path_owners=path_owners, keep_cids=set(stranded))
            write_state(target, state)
        else:
            if state.get("path_bootstrap"):
                _remove_shell_path()
            # Nothing left of ours — take the book away too. Only OUR artifacts
            # were removed above; anything foreign at the root is still there.
            path = target / STATE_REL
            if path.is_file():
                path.unlink()
            _prune(target, path.parent)
        report["path"] = reconcile(bindir, desired, booked, dry=False,
                                   keep=keep_names)
    else:
        report["path"] = reconcile(bindir, desired, booked, dry=True,
                                   keep=keep_names)
    return {"ok": True, "uninstalled": picked,
            "remaining": sorted(records),
            **result, "report": report}


DISCOVER_FLAG = "--target"
ANSI = {"ok": "\033[32m", "part": "\033[33m", "warn": "\033[33m",
        "gone": "\033[31m", "fail": "\033[31m", "reset": "\033[0m"}


def _part_in(state: dict, cid: str, pid: str) -> bool:
    rec = (state.get("components") or {}).get(cid)
    if rec is None and cid.startswith(f"{HUB_DIR}/skills/"):
        rec = (state.get("components") or {}).get(
            f"{SKILLS_DIR}/{cid.rsplit('/', 1)[-1]}")
    if rec is None:
        return False
    parts = rec.get("parts")
    if parts is None:
        return True
    return pid in parts


def catalog_ids(catalog: dict, cid: str) -> list[str]:
    c = catalog.get(cid) or {}
    return [s["id"] for s in _part_specs(c) if s.get("id")]


def status_of(cid: str, rec: dict, catalog: dict
              ) -> tuple[str, set[str], set[str], set[str]]:
    cat = set(catalog_ids(catalog, cid))
    booked = set(rec["parts"]) if "parts" in rec else cat
    if cid not in catalog:
        return "gone", booked, set(), booked
    if not cat:
        return "ok", booked, set(), booked - cat
    miss, orph = cat - booked, booked - cat
    st = "part" if booked and booked < cat else "full"
    return st, booked, miss, orph


def build_ls(catalog: dict, shadowed: list, state: dict, *,
             modules: list[str] | None = None,
             methods: list[str] | None = None,
             components: list[str] | None = None,
             exclude_modules: list[str] | None = None,
             exclude_methods: list[str] | None = None,
             exclude_components: list[str] | None = None) -> dict:
    want_m = {module_id(m) for m in (modules or [])}
    want_x = set(methods or [])
    want_c = {_norm_comp(c) for c in (components or [])}
    drop_m = {module_id(m) for m in (exclude_modules or [])}
    drop_x = set(exclude_methods or [])
    drop_c = {_norm_comp(c) for c in (exclude_components or [])}
    entries, nmap, n = [], {}, 0
    for cid in sorted(catalog):
        c = catalog[cid]
        hub = c.get("kind") in ("hub", "skill-folder")
        mod = c.get("module") or cid.split("/")[0]
        if want_m and mod not in want_m:
            continue
        if drop_m and mod in drop_m:
            continue
        if want_c and cid not in want_c and not any(
                token == cid or token.endswith("#" + cid.split("/")[-1])
                or (token.startswith(cid + "#"))
                for token in want_c):
            continue
        if drop_c and cid in drop_c:
            continue
        items = []
        for spec in _part_specs(c):
            pid, meth = spec["id"], spec.get("method") or ""
            if want_x and meth not in want_x:
                continue
            if drop_x and meth in drop_x:
                continue
            n += 1
            items.append({"index": n, "part_id": pid, "method": meth,
                          "in": _part_in(state, cid, pid)})
            nmap[str(n)] = {"kind": "part", "id": part_key(cid, pid)}
        refusal = c.get("hub_refusal") or ""
        note = _hub_refuse_message(c) if refusal else ""
        if (want_x or drop_x) and not items:
            continue
        entries.append({
            "id": cid, "tree": c.get("tree", ""), "module": mod,
            "kind": "hub" if hub else c.get("kind", "component"),
            "manifest": bool(c.get("manifest")),
            "methods": sorted({i["method"] for i in items}),
            "parts": len(items), "note": note, "items": items,
            "refusal": refusal,
        })
    hub_refusals = [cid for cid, c in sorted(catalog.items())
                    if c.get("hub_refusal")]
    return {"ok": True, "components": entries, "shadowed": shadowed,
            "hub_refusals": hub_refusals,
            "index": {"fingerprint": scan_fingerprint(catalog), "n": nmap}}


def print_ls(data: dict, *, pretty: bool = False) -> None:
    print(f" {'#':>2}  {'COMPONENT / part':<42} {'TREE':<7} {'METHOD':<10} IN")
    for e in data["components"]:
        extra = f"  ({e['note']})" if e["note"] else ""
        n_in = sum(1 for i in e["items"] if i["in"])
        n = len(e["items"])
        tally = f"{n} part{'' if n == 1 else 's'}, {n_in} in" if n else ""
        print(f"     {e['id']:<42} {e['tree']:<7} {tally}{extra}")
        for i in e["items"]:
            flag = "in" if i["in"] else "-"
            if pretty:
                flag = ((ANSI["ok"] + "in" + ANSI["reset"]) if i["in"]
                        else flag)
            print(f"{i['index']:>3}    {i['part_id']:<39} {'':<7} "
                  f"{i['method']:<10} {flag}")
    for s in data["shadowed"]:
        print(f"\nSHADOWED: {s['id']} exists on both trees — mirror wins "
              f"({s['winner_path']}); repo copy ignored ({s['shadowed_path']})")


def write_visible_index(target: Path, index: dict) -> None:
    path = target / INDEX_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def do_list(target: Path, catalog: dict | None = None) -> dict:
    raw = read_state(target)
    catalog = catalog or {}
    state = upgrade_book(raw, catalog_parts_map(catalog)) if catalog else raw
    comps: dict = {}
    links: list[dict] = []
    for cid, rec in sorted((state.get("components") or {}).items()):
        rec = dict(rec)
        st, booked, miss, orph = status_of(cid, rec, catalog)
        rec["status"], rec["missing"], rec["orphans"] = (
            st, sorted(miss), sorted(orph))
        rec.setdefault("parts", {})
        comps[cid] = rec
        for pid, part in (rec.get("parts") or {}).items():
            if not isinstance(part, dict):
                continue
            for name in part.get("links") or []:
                links.append({"name": name, "component": cid, "part": pid})
    return {"ok": True, "target": str(target.resolve()),
            "schema": state.get("schema"),
            "state_file": str(target / STATE_REL),
            "marker": MANAGED_MARK,
            "guidance_basis": state.get("guidance_basis"),
            "components": comps,
            "guidance_files": state.get("guidance_files") or [],
            "shared_claims": state.get("shared_claims") or [],
            "path_links": links}


def print_li(data: dict, *, pretty: bool = False) -> None:
    basis = data["guidance_basis"] or "(unset — no mirror)"
    print(f"target: {data['target']}  marker: {data['marker']}  "
          f"guidance basis: {basis}")
    comps = data["components"]
    if not comps:
        print("nothing installed by install2.py")
    else:
        print(f"{'#':<3} {'ST':<5} {'IN':<6} {'COMPONENT':<42} {'TREE':<7} "
              f"HARNESSES")
        cids = list(comps)
        part_no: dict[str, dict[str, int]] = {cid: {} for cid in cids}
        k = len(cids) + 1
        for cid, rec in comps.items():
            for pid in sorted(rec.get("parts") or {}):
                part_no[cid][pid] = k
                k += 1
        for i, cid in enumerate(cids, 1):
            rec = comps[cid]
            cat_n = len((set(rec.get("parts") or {})
                         | set(rec.get("missing") or {}))
                        - set(rec.get("orphans") or {}))
            booked = set(rec.get("parts") or {})
            orph = set(rec.get("orphans") or {})
            st = rec["status"]
            if st == "gone":
                inn = f"{len(booked)}/—"
            else:
                inn = f"{len(booked - orph)}/{cat_n}"
            paint = f"{st:<5}"
            if pretty and st in ANSI:
                paint = ANSI[st] + paint + ANSI["reset"]
            hs = ",".join(rec.get("harnesses") or [])
            names = ",".join(sorted(booked))
            if pretty:
                print(f"{i:<3} {paint} {inn:<6} {cid:<42} "
                      f"{rec.get('tree', ''):<7} {hs}")
                for pid, part in sorted((rec.get("parts") or {}).items()):
                    if not isinstance(part, dict):
                        continue
                    print(f"    {part_no[cid][pid]:<3} {pid:<22} "
                          f"{part.get('method', '')}")
            else:
                print(f"{i:<3} {paint} {inn:<6} {cid:<42} "
                      f"{rec.get('tree', ''):<7} {hs}")
            miss = rec.get("missing") or []
            orph_l = rec.get("orphans") or []
            if st == "part" or miss or orph_l:
                extra = []
                if miss:
                    extra.append("out: " + ", ".join(miss))
                if orph_l:
                    extra.append("orphan: " + ", ".join(orph_l))
                if extra:
                    print("        " + " · ".join(extra))
    def _section(label: str, items: list[str]) -> None:
        """Owned outside our own files — the only place a human sees it."""
        if not items:
            print(f"\n{label}: (none)")
            return
        print(f"\n{label}:")
        for it in items:
            print(f"  {it}")

    _section("guidance files written", data["guidance_files"])
    _section("keys held in shared config files", data["shared_claims"])
    _section("commands linked onto PATH",
             [p["name"] for p in data["path_links"]])


def booked_links(state: dict) -> set[str]:
    return booked_path_names(state)


def _path_index(bindir: Path) -> int:
    want = bindir.expanduser()
    try:
        want_r = want.resolve()
    except OSError:
        want_r = want
    for i, raw in enumerate(os.environ.get("PATH", "").split(os.pathsep)):
        if not raw:
            continue
        p = Path(raw).expanduser()
        try:
            if p == want or p.resolve() == want_r:
                return i
        except OSError:
            if p == want:
                return i
    return -1


def collect_collisions(target: Path, files: dict, claims: list,
                       state: dict) -> list[tuple[str, str]]:
    ours_f, ours_c = known_files(state), known_claims(state)
    hits: list[tuple[str, str]] = []
    for rel in files:
        if rel in ours_f or not (target / rel).exists() or _is_ours(target, rel):
            continue
        hits.append((rel, "guidance-mirror-collision"
                     if rel.rsplit("/", 1)[-1] in GUIDANCE_NAMES
                     else "collision"))
    for claim in claims:
        cid = _claim_id(claim["path"], claim["key"])
        path = target / claim["path"]
        if cid in ours_c or not path.is_file():
            continue
        if claim["fmt"] == "json":
            try:
                doc = json.loads(path.read_text(encoding="utf-8") or "{}")
            except ValueError:
                hits.append((claim["path"], "shared-file-unparseable"))
                continue
            if _jget(doc, claim["key"])[1]:
                hits.append((claim["path"] + "::" + ".".join(claim["key"]),
                             "collision"))
        else:
            start, _ = _fence(claim["comment"])
            if start in path.read_text(encoding="utf-8"):
                hits.append((f"{claim['path']}::{FENCE_ID}-block", "collision"))
    return hits


def inspect_bindir(bindir: Path, booked: set[str],
                   desired: set[str]) -> dict:
    out = {"unbooked": [], "collision": [], "not_exec": []}
    if not bindir.is_dir():
        return out
    names = {p.name for p in bindir.iterdir()}
    out["unbooked"] = sorted(names - booked)
    for name in sorted(desired):
        p = bindir / name
        if p.exists() and not p.is_symlink():
            out["collision"].append(str(p))
            continue
        if p.is_symlink():
            try:
                dest = p.resolve()
            except OSError:
                dest = p
            if dest.is_file() and not os.access(dest, os.X_OK):
                out["not_exec"].append(f"{name} → {dest}")
    return out


def shadows(bindir: Path, booked: set[str]) -> list[str]:
    locdir = local_bin()
    if not locdir.is_dir():
        return []
    watch = set(booked)
    if bindir.is_dir():
        watch |= {p.name for p in bindir.iterdir()}
    hits = []
    for name in sorted(watch):
        loc = locdir / name
        if loc.exists() or loc.is_symlink():
            hits.append(f"{name} → {loc} shadows {bindir / name}")
    return hits


def render_doctor(checks: list[dict], *, pretty: bool = False) -> str:
    lines = []
    for c in checks:
        tok = {"ok": "ok  ", "warn": "warn", "fail": "FAIL"}[c["level"]]
        if pretty:
            tok = f"{ANSI[c['level']]}{tok}{ANSI['reset']}"
        lines.append(f"{tok}  {c['name']}: {c['detail']}")
    n_ok = sum(1 for c in checks if c["level"] == "ok")
    n_warn = sum(1 for c in checks if c["level"] == "warn")
    n_fail = sum(1 for c in checks if c["level"] == "fail")
    head = "FAIL" if n_fail else ("warn" if n_warn else "ok")
    extra = f" ({n_warn} warn)" if n_warn and not n_fail else ""
    lines.append("")
    lines.append(f"{head} — {n_ok}/{len(checks)} checks{extra}")
    nxt = ("next: rbtv install ls" if head == "ok" else
           f"next: fix the {head} lines above, then rerun `rbtv install doctor`")
    lines.append(nxt)
    return "\n".join(lines)


def doctor_exit(checks: list[dict]) -> int:
    return 1 if any(c["level"] == "fail" for c in checks) else 0


def _check(name: str, level: str, detail: str) -> dict:
    return {"name": name, "ok": level == "ok", "level": level, "detail": detail}


def _desired_path_names(catalog: dict, booked: set[str]) -> set[str]:
    names = set(booked)
    for p in iter_catalog_parts(catalog):
        if p["method"] != "path":
            continue
        try:
            names.add(link_name(p["part_id"]))
        except Refuse:
            continue
    return names


def _probe_add_collisions(target: Path, catalog: dict,
                          state: dict) -> tuple[list[tuple[str, str]], str]:
    installable = [cid for cid, c in catalog.items() if is_installable(c)]
    if not installable:
        return [], "no catalog — nothing to plan"
    try:
        records = dict(state.get("components") or {})
        for cid in installable:
            c = catalog[cid]
            existing = records.get(cid) or {}
            rec = {"tree": c.get("tree", ""),
                   "tree_root": c.get("tree_root", ""),
                   "module": c.get("module") or cid.split("/")[0],
                   "component": c.get("component") or cid.rsplit("/", 1)[-1],
                   "harnesses": existing.get("harnesses") or list(HARNESSES),
                   "parts": _select_parts(c, existing.get("parts"), None)}
            if "files" in existing:
                rec["files"] = list(existing["files"])
            records[cid] = rec
        files, owners, claims, report = plan_files(records, catalog)
        _add_mirror(target, state, files, owners, report, None,
                    installed_harnesses(records))
        _add_gitignore(target, owners, claims, report)
    except Refuse as exc:
        return [(exc.path or exc.code, exc.code)], ""
    return collect_collisions(target, files, claims, state), ""


def do_doctor(target: Path, why: str, catalog: dict, shadowed: list,
              repo_tree: Path, mirror_tree: Path) -> dict:
    checks: list[dict] = []
    if not target.is_dir():
        checks.append(_check("target", "fail",
                             f"{target} is not a directory"))
    else:
        checks.append(_check(
            "target", "ok",
            f"{target.resolve()}  (discovered by {why})"))

    book_path = target / STATE_REL
    state: dict = {"schema": SCHEMA, "components": {}}
    if not book_path.is_file():
        checks.append(_check("book", "ok", "no book (never installed)"))
    else:
        try:
            state = upgrade_book(read_state(target),
                                 catalog_parts_map(catalog))
            n = len(state.get("components") or {})
            checks.append(_check(
                "book", "ok",
                f"schema {state.get('schema')} · {n} components"))
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            checks.append(_check("book", "fail", f"unreadable: {exc}"))
            state = {"schema": SCHEMA, "components": {}}

    repo_found = scan_tree(repo_tree, "repo")
    checks.append(_check(
        "tree-repo", "ok",
        f"{repo_tree} — {len(repo_found)} components"))
    if mirror_tree.is_dir():
        mir_found = scan_tree(mirror_tree, "mirror")
        shadow_n = len(set(repo_found) & set(mir_found))
        extra = f" ({shadow_n} shadowing repo)" if shadow_n else ""
        checks.append(_check(
            "tree-mirror", "ok",
            f"{mirror_tree} — {len(mir_found)} components{extra}"))
    else:
        checks.append(_check(
            "tree-mirror", "ok",
            f"absent — 0 components"))

    bindir = bin_dir()
    if bindir.is_dir():
        checks.append(_check("bin-dir", "ok", f"{bindir} exists"))
    else:
        checks.append(_check(
            "bin-dir", "warn", f"{bindir} missing (add will mkdir)"))

    bidx = _path_index(bindir)
    lidx = _path_index(local_bin())
    if bidx < 0:
        checks.append(_check(
            "bin-on-path", "warn",
            f'not on PATH — add once: export PATH="$HOME/.rbtv/bin:$PATH"'))
    elif lidx >= 0 and lidx < bidx:
        checks.append(_check(
            "bin-on-path", "warn",
            f"on PATH at {bidx} but AFTER ~/.local/bin ({lidx}) "
            f"— stale local names win"))
    elif lidx < 0:
        checks.append(_check(
            "bin-on-path", "ok",
            f"{bindir} on PATH at {bidx}, ~/.local/bin absent"))
    else:
        checks.append(_check(
            "bin-on-path", "ok",
            f"{bindir} on PATH at index {bidx} (before ~/.local/bin)"))

    booked = booked_links(state)
    desired = _desired_path_names(catalog, booked)
    sh = shadows(bindir, booked)
    if sh:
        checks.append(_check("local-bin-shadow", "warn", ", ".join(sh)))
    else:
        checks.append(_check("local-bin-shadow", "ok", "none"))

    insp = inspect_bindir(bindir, booked, desired)
    if not bindir.is_dir():
        checks.append(_check("path-unbooked", "ok", "no directory"))
        checks.append(_check("path-collision", "ok", "no directory"))
        checks.append(_check("path-not-executable", "ok", "no directory"))
    else:
        if insp["unbooked"]:
            checks.append(_check(
                "path-unbooked", "warn",
                f"{', '.join(insp['unbooked'])} (left alone; next add "
                f"relinks only if desired+symlink)"))
        else:
            checks.append(_check("path-unbooked", "ok", "none"))
        if insp["collision"]:
            checks.append(_check(
                "path-collision", "warn",
                f"{', '.join(insp['collision'])} exists and is not a "
                f"symlink — next add refuses"))
        else:
            checks.append(_check("path-collision", "ok", "none"))
        if not desired and not booked:
            checks.append(_check("path-not-executable", "ok", "none booked"))
        elif insp["not_exec"]:
            checks.append(_check(
                "path-not-executable", "warn",
                ", ".join(f"{x} not executable (ok: python <path>)"
                          for x in insp["not_exec"])))
        else:
            checks.append(_check("path-not-executable", "ok",
                                 "all executable"))

    hits, empty_msg = _probe_add_collisions(target, catalog, state)
    if empty_msg:
        checks.append(_check("add-collisions", "ok", empty_msg))
    elif not hits:
        checks.append(_check("add-collisions", "ok",
                             "none — next add is clear"))
    else:
        rels = ", ".join(h[0] for h in hits)
        codes = sorted({h[1] for h in hits})
        checks.append(_check(
            "add-collisions", "warn",
            f"{rels} — next add refuses [{', '.join(codes)}]"))

    basis = state.get("guidance_basis")
    if basis is None:
        checks.append(_check("guidance-basis", "ok", "unset (no mirror)"))
    elif basis == BASIS_NONE:
        checks.append(_check("guidance-basis", "ok", "none (no mirror)"))
    elif basis in GUIDANCE_NAMES:
        checks.append(_check("guidance-basis", "ok", str(basis)))
    else:
        checks.append(_check(
            "guidance-basis", "warn",
            f"{basis!r} is neither none nor AGENTS.md · CLAUDE.md — "
            f"next add refuses [guidance-basis-invalid]"))

    failed = any(c["level"] == "fail" for c in checks)
    return {"ok": not failed, "version": VERSION,
            "target": str(target.resolve() if target.exists() else target),
            "why": why, "checks": checks}


# ── human output ────────────────────────────────────────────────────────────

def print_scan(data: dict) -> None:
    print(f"{'COMPONENT':<34} {'TREE':<7} {'PARTS':>5}  METHODS / NOTE")
    for e in data["components"]:
        note = e["note"] or ", ".join(e["methods"]) or "(manifest has no rows)"
        if (e.get("kind") == "hub" and e.get("methods") == ["skill"]
                and not e.get("refusal")):
            note = "hub skill — whole folder copied verbatim (D15)"
        print(f"{e['id']:<34} {e['tree']:<7} {e['parts']:>5}  {note}")
    for s in data["shadowed"]:
        print(f"\nSHADOWED: {s['id']} exists on both trees — mirror wins "
              f"({s['winner_path']}); repo copy ignored ({s['shadowed_path']})")


def print_result(data: dict) -> None:
    for key in ("installed", "uninstalled"):
        if data.get(key):
            print(f"{key}: {', '.join(data[key])}")
    if data.get("harnesses"):
        print(f"harnesses: {', '.join(data['harnesses'])}")
    # Printed BEFORE the dry-run branch: a planned takeover of another tool's
    # file is exactly what a human needs to see while deciding to proceed.
    for rel in data.get("adopted") or []:
        print(f"  ^ {rel} (adopted — its own head proves a tool generated it, "
              "so it is not authored content; now ours)")
    for rel in data.get("released") or []:
        print(f"  ! {rel} (released — the `{MANAGED_MARK}` marker is gone, so "
              "someone took this file over: dropped from the book, left on "
              "disk, never deleted)")
    if data.get("dry_run"):
        print(f"DRY RUN — would write {len(data.get('skipped') or [])} file(s) "
              f"and hold {len(data.get('shared') or [])} shared-file claim(s):")
        for rel in data.get("skipped") or []:
            print(f"  + {rel}")
        for rel in data.get("shared") or []:
            print(f"  ~ {rel}")
        for rel in data.get("deleted") or []:
            print(f"  - {rel}")
        for rel in data.get("shared_removed") or []:
            print(f"  ~- {rel}")
        _print_report_rows(data.get("report") or {}, planned=True)
        _print_gitignore(data.get("report") or {}, planned=True)
        _print_guidance(data.get("report") or {}, planned=True)
        return
    for rel in data.get("written") or []:
        print(f"  + {rel}")
    for rel in data.get("skipped") or []:
        print(f"  = {rel} (unchanged)")
    for rel in data.get("shared") or []:
        print(f"  ~ {rel}")
    for rel in data.get("deleted") or []:
        print(f"  - {rel}")
    for rel in data.get("shared_removed") or []:
        print(f"  ~- {rel}")
    report = data.get("report") or {}
    _print_report_rows(report, planned=False)
    _print_gitignore(report, planned=False)
    _print_guidance(report, planned=False)


def _print_report_rows(report: dict, planned: bool) -> None:
    """Why a manifest row minted nothing. Printed on DRY RUNS TOO, marked as
    planned (task 7.622): `install --component X --dry-run` is the command the
    acceptance sketches name, and suppressing these rows there left the human
    ~11 lines with no per-row detail while the data sat in `--json` all along.
    The two lists are the SAME data a real run prints; only the tense moves."""
    verb = "would skip" if planned else "skipped"
    tail = "would mint nothing" if planned else "nothing minted"
    for row in report.get("skipped_inventory_rows") or []:
        print(f"  · {verb} `{row['method']}` row {row['component']}/"
              f"{row['part']} ({row['entry_point']}) — inventory only, "
              "mints nothing")
    for row in report.get("skill_folders") or []:
        print(f"  · {'would copy' if planned else 'copied'} skill FOLDER "
              f"{row['component']} whole — {row['files']} file(s) into "
              + ", ".join(row["roots"]) + " (D15)")
    for row in report.get("no_realization") or []:
        print(f"  · {row['harness']} has no realization for method "
              f"{row['method']} ({row['component']}/{row['part']}) — {tail}")
    pathrep = report.get("path") or {}
    for name in pathrep.get("linked") or []:
        print(f"  · {'would link' if planned else 'linked'} PATH {name}")
    for name in pathrep.get("relinked") or []:
        print(f"  · {'would relink' if planned else 'relinked'} PATH {name}")
    for name in pathrep.get("unlinked") or []:
        print(f"  · {'would unlink' if planned else 'unlinked'} PATH {name}")
    if any(pathrep.get(k) for k in ("linked", "relinked", "ok")):
        print(f"  · add to shell (first wins over ~/.local/bin): "
              f"{report.get('path_bootstrap') or PATH_BOOTSTRAP}")


def _print_gitignore(report: dict, planned: bool) -> None:
    """What the `.gitignore` block covers — and what it cannot (D14)."""
    gi = report.get("gitignore")
    if not gi:
        return
    if not gi.get("claimed"):
        print(f"  · .gitignore: not claimed ({gi.get('reason')})")
        return
    print(f"  · .gitignore: {'would keep' if planned else 'keeps'} "
          f"{gi['count']} artifact path(s) out of git, in one "
          f"`{FENCE_ID}:start` block (D14)")
    for rel in gi.get("tracked") or []:
        print(f"    ⚠ {rel} is ALREADY TRACKED by git — no ignore rule reaches "
              "a tracked file. Untrack it (`git rm --cached`) or accept that "
              "it is committed.")


def _print_guidance(report: dict, planned: bool) -> None:
    """The guidance-mirror summary and the blocks the human must place. Printed
    on DRY RUNS TOO: the basis is never written, so this is the only channel
    that ever names what the human still has to do (7.622's bug class)."""
    verb = "would generate" if planned else "generated"
    mirror = report.get("guidance_mirror")
    if mirror and mirror.get("skipped"):
        print(f"  · guidance mirror: SKIPPED ({mirror['skipped']}) — not "
              "re-rendered; both root guidance files were left untouched. Fix "
              "the basis on the next install.")
    elif mirror and mirror.get("basis") and not mirror.get("targets"):
        print(f"  · guidance mirror: nothing to render — every installed "
              f"harness reads {mirror['basis']}, which is the basis and is "
              "never written (D13).")
    elif mirror and mirror.get("basis"):
        print(f"  · guidance mirror: {mirror['count']} file(s) — "
              f"{', '.join(mirror['targets'])} {verb} from "
              f"{mirror['basis']} (one set beside every {mirror['basis']} in "
              "the tree; no basis file is ever written)"
              + (f"; excluding {', '.join(mirror['excludes'])}"
                 if mirror.get("excludes") else ""))
        if mirror.get("banner_stripped"):
            print("    a generated banner was stripped from these bases before "
                  "mirroring (never stacked): "
                  + ", ".join(mirror["banner_stripped"]))
    elif mirror:
        print("  · guidance mirror: OFF — no basis recorded. Set one with "
              "`--guidance-basis CLAUDE.md|AGENTS.md` (D13).")
    if report.get("guidance_debannered"):
        print(f"  · {'would clean' if planned else 'cleaned'} a stale GENERATED "
              "banner off the file(s) you now author: "
              + ", ".join(report["guidance_debannered"]))
    for name, block in (report.get("guidance_manual") or {}).items():
        print(f"\nAdd this block to {name} — an installed harness reads it and "
              "this installer never writes it (D8). Copy from the next line to "
              "the closing fence:\n")
        # Flush, never indented: four leading spaces make markdown swallow the
        # whole block as a code span when it is pasted into the guidance file.
        print(block.rstrip())



# ── interactive ─────────────────────────────────────────────────────────────

def prompt_basis(ask=input, tries: int = 3) -> str:
    """Ask for the guidance basis, RE-PROMPTING on a typo (task 7.623(b)).

    The basis is the LAST thing `interactive` asks. A mistyped answer used to
    raise `Refuse` straight past the caller, throwing away the target, the
    component picks and the harness picks the human had already given. Bounded
    by `tries`: the FINAL try's refusal propagates unchanged, so a stdin that
    never answers cannot loop forever and the refusal stays reachable. Every
    NON-interactive path still calls `resolve_basis` directly and still refuses
    on the first bad value — no re-prompt exists to reach there.
    """
    for attempt in range(1, tries + 1):
        raw = ask(f"Basis [{'/'.join(GUIDANCE_NAMES)}/{BASIS_NONE}] "
                  f"[{BASIS_NONE}]: ").strip()
        try:
            return resolve_basis(None, raw or BASIS_NONE) or BASIS_NONE
        except Refuse as exc:
            if attempt == tries:
                raise
            print(f"  {exc.message}")
            print(f"  {tries - attempt} more attempt(s) — blank answer "
                  f"means {BASIS_NONE}.")


def interactive(target: Path, catalog: dict[str, dict]) -> int:
    print("rbtv installer (install2) — interactive\n")
    answer = input(f"Target workspace [{target}]: ").strip()
    if answer:
        target = Path(answer).expanduser()
        catalog, _ = scan_all(target / ".rbtv" / "mirror",
                              Path(__file__).resolve().parent)
    if not target.is_dir():
        raise Refuse("target-missing", f"target is not a directory: {target}")

    installable = [cid for cid in sorted(catalog)
                   if is_installable(catalog[cid])]
    if not installable:
        print("Nothing installable — no component on either tree carries an "
              f"exposure manifest, and no {HUB_DIR}/ (or legacy "
              f"{SKILLS_DIR}/) folder exists.")
        return 1
    installed = set(read_state(target).get("components") or {})
    print("\nComponents:\n")
    for i, cid in enumerate(installable, 1):
        mark = "*" if cid in installed else " "
        print(f" {mark}{i:>3}. {cid}  [{catalog[cid]['tree']}]")
    for cid in sorted(catalog):
        c = catalog[cid]
        if not is_installable(c) and c.get("hub_refusal"):
            print(f"     ---  {cid}  — {_hub_refuse_message(c)}")
    print("\n('*' = already installed)")

    raw = input("\nSelect numbers (comma-separated, blank to cancel): ").strip()
    if not raw:
        print("Cancelled.")
        return 0
    try:
        picked = [installable[int(n) - 1] for n in raw.replace(" ", "").split(",")]
    except (ValueError, IndexError):
        raise Refuse("bad-selection", f"not a valid selection: {raw!r}")

    hraw = input(f"Harnesses [{','.join(HARNESSES)}]: ").strip()
    harnesses = _parse_harnesses(hraw) if hraw else list(HARNESSES)

    # D13 — asked ONCE per target; a recorded answer (incl. `none`) is not
    # re-asked, and every non-interactive path skips this entirely.
    basis: str | None = None
    if "guidance_basis" not in read_state(target):
        print("\nRoot guidance basis — which root file do you author? The other "
              "one is GENERATED from it on every run; the basis is never "
              "written.")
        basis = prompt_basis()

    print(f"\nInstalling {', '.join(picked)} for {', '.join(harnesses)} "
          f"into {target}")
    print_result(do_install(target, catalog, picked, harnesses, dry_run=True,
                            guidance_basis=basis))
    if input("\nProceed? [y/N]: ").strip().lower() not in ("y", "yes"):
        print("Cancelled.")
        return 0
    print_result(do_install(target, catalog, picked, harnesses, dry_run=False,
                            guidance_basis=basis))
    return 0


def _parse_harnesses(raw: str) -> list[str]:
    picked = [h.strip() for h in raw.split(",") if h.strip()]
    unknown = [h for h in picked if h not in HARNESSES]
    if unknown:
        raise Refuse("harness-unknown",
                     f"unknown harness(es): {', '.join(unknown)} — known: "
                     + ", ".join(HARNESSES))
    return [h for h in HARNESSES if h in picked]


# ── selftest ────────────────────────────────────────────────────────────────

def _fixture(root: Path) -> None:
    """A throwaway tree covering every method, incl. a `path` row that must be
    skipped, a component with NO manifest, and an unknown-method component."""
    good = root / "fixmod" / "goodcomp"
    (good / "tool").mkdir(parents=True)
    for name, body in (
        ("skill-entry.md", "# the skill\n"),
        ("cmd-entry.md", "# the command\n"),
        ("rule-entry.md", "# THE RULE\n\nAlways do the thing.\n"),
        ("agent-entry.md", "# the sub-agent\n"),
        ("guide.md", "# guidance part\n"),
        ("tool/thing.py", "print('inventory only')\n"),
    ):
        (good / name).write_text(body, encoding="utf-8")
    (good / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "true"}]}]}}),
        encoding="utf-8")
    (good / "mcp.json").write_text(json.dumps({"mcpServers": {
        "fix": {"type": "http", "url": "https://example.invalid/mcp"}}}),
        encoding="utf-8")
    (good / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "fixskill,capability,skill,exhibit,skill-entry.md,A fixture skill: with a colon,\n"
        "fixcmd,workflow,command,,cmd-entry.md,,\n"
        "fixrule,reference,rule,,rule-entry.md,the fixture rule,\n"
        "fixagent,prompt,sub-agent,,agent-entry.md,,\n"
        "fixhook,capability,hook,,hooks.json,,\n"
        "fixmcp,plugin/MCP,config,,mcp.json,,\n"
        "fixguide,prompt,agents.md,exhibit,guide.md,,\n"
        "fixtool,tool,path,,tool/thing.py,,\n"
        "fixpool,prompt,pool,,guide.md,a pool member — shopped, never minted,\n",
        encoding="utf-8")

    codexc = root / "fixmod" / "codexcomp"
    codexc.mkdir(parents=True)
    (codexc / "rule-entry.md").write_text("# CODEX RULE\n", encoding="utf-8")
    (codexc / "guide.md").write_text("# codex guidance part\n", encoding="utf-8")
    (codexc / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "codexrule,reference,rule,,rule-entry.md,the codex-side rule,\n"
        "codexguide,prompt,agents.md,,guide.md,,\n", encoding="utf-8")

    bare = root / "fixmod" / "barecomp"
    bare.mkdir(parents=True)
    (bare / "component.md").write_text("# barecomp — no manifest\n",
                                       encoding="utf-8")

    res = root / "fixmod" / "reservedcomp"
    res.mkdir(parents=True)
    (res / "skill-entry.md").write_text("# the skill\n", encoding="utf-8")
    (res / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "rbtv-legacy,prompt,skill,,skill-entry.md,,\n", encoding="utf-8")

    # D2 — depth-1 module-root manifest (invisible) and a depth-2 manifest
    # with no component.md (a component). Depth-3 is added below.
    old = root / "oldmod"
    (old / "oldcomp").mkdir(parents=True)
    old_rows = ("part-id,part-kind,method,rbtv-cli,entry-point,description,"
                "write-roots\nold,prompt,skill,,entry.md,,\n")
    (old / EXPOSURE_NAME).write_text(old_rows, encoding="utf-8")
    (old / "entry.md").write_text("# old\n", encoding="utf-8")
    (old / "oldcomp" / EXPOSURE_NAME).write_text(old_rows, encoding="utf-8")
    (old / "oldcomp" / "entry.md").write_text("# old\n", encoding="utf-8")

    # D15 — a whole skill folder: SKILL.md + a nested reference + a binary
    # asset + a directory the copier must skip.
    vend = root / SKILLS_DIR / "vendored"
    (vend / "references").mkdir(parents=True)
    (vend / "__pycache__").mkdir()
    (vend / SKILL_FILE).write_text(
        "---\nname: vendored\ndescription: A vendored skill\n---\n\n"
        "# Vendored\n\nRead references/deep.md.\n", encoding="utf-8")
    (vend / "LICENSE.txt").write_text("MIT\n", encoding="utf-8")
    (vend / "references/deep.md").write_text("# deep reference\n",
                                             encoding="utf-8")
    (vend / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n binary")
    (vend / "__pycache__/junk.pyc").write_bytes(b"\x00junk")

    hub = root / HUB_DIR
    skill = hub / "skills" / "hubskill"
    skill.mkdir(parents=True)
    (skill / SKILL_FILE).write_text(
        "---\nname: hubskill\ndescription: A hub skill\n---\n\n# Hub skill\n",
        encoding="utf-8")
    (hub / "command").mkdir()
    (hub / "command" / "hubcmd.md").write_text("# hub command\n", encoding="utf-8")
    (hub / "rules").mkdir()
    (hub / "rules" / "hubrule.md").write_text("# HUB RULE\n\nDo the hub thing.\n",
                                              encoding="utf-8")
    (hub / "hook").mkdir()
    (hub / "hook" / "hubhook.json").write_text(json.dumps({"hooks": {"SessionStart": [
        {"matcher": "", "hooks": [{"type": "command", "command": "true"}]}]}}),
        encoding="utf-8")
    (hub / "sub-agent").mkdir()
    (hub / "sub-agent" / "hubagent.md").write_text("# hub sub-agent\n",
                                                   encoding="utf-8")
    (hub / "agents.md").mkdir()
    (hub / "agents.md" / "hubguide.md").write_text("# hub guidance fragment\n",
                                                   encoding="utf-8")
    (hub / "config").mkdir()
    (hub / "config" / "hubmcp.json").write_text(json.dumps({"mcpServers": {
        "hubfix": {"type": "http", "url": "https://hub.example.invalid/mcp"}}}),
        encoding="utf-8")
    (hub / "path").mkdir()
    (hub / "path" / "hubbin.py").write_text("#!/usr/bin/env python3\nprint(1)\n",
                                            encoding="utf-8")
    (hub / "path" / "hubbindir").mkdir()
    (hub / "path" / "hubbindir" / "child.py").write_text("print(2)\n",
                                                         encoding="utf-8")
    (hub / "pool").mkdir()
    (hub / "pool" / "hubpool.md").write_text("# not a pool\n", encoding="utf-8")

    # Depth 3 — not a component (D2).
    deep = root / "deepmod" / "deepcomp" / "nested"
    deep.mkdir(parents=True)
    (deep / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "deep,prompt,skill,,entry.md,,\n", encoding="utf-8")

    bad = root / "badmod" / "badcomp"
    bad.mkdir(parents=True)
    (bad / "x.md").write_text("x\n", encoding="utf-8")
    (bad / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "boom,capability,telepathy,,x.md,,\n", encoding="utf-8")

    dup = root / "fixmod" / "dupcomp"
    dup.mkdir(parents=True)
    (dup / "a.md").write_text("a\n", encoding="utf-8")
    (dup / "b.md").write_text("b\n", encoding="utf-8")
    (dup / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "same,capability,skill,,a.md,,\n"
        "same,reference,rule,,b.md,,\n", encoding="utf-8")


def _reserved_id_refuses(tmp: Path, catalog: dict[str, dict]) -> bool:
    """A manifest declaring a `rbtv-*` part id refuses, and writes nothing —
    the old installer's sweep would delete that file behind our back (D12)."""
    ws = tmp / "ws-reserved-id"
    ws.mkdir()
    try:
        do_install(ws, catalog, ["fixmod/reservedcomp"], list(HARNESSES),
                   dry_run=False)
        return False
    except Refuse as exc:
        return (exc.code == "part-id-reserved"
                and not any(ws.rglob("*.md")))


def selftest() -> int:
    ok = True

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal ok
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}"
              + (f" — {detail}" if detail and not condition else ""))
        ok = ok and condition

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        _RUNTIME["bin"] = tmp / "rbtv-bin"
        _RUNTIME["rc"] = tmp / "fake-bashrc"
        _RUNTIME["local"] = tmp / "fake-local-bin"
        if (bin_dir().resolve() == (Path.home() / ".rbtv" / "bin")
                or not str(bin_dir().resolve()).startswith(str(tmp.resolve()))
                or bin_dir().resolve()
                == (Path.home() / ".local" / "bin").resolve()):
            _RUNTIME["bin"] = None
            _RUNTIME["rc"] = None
            _RUNTIME["local"] = None
            print("FATAL: PATH bin dir was not rebound — refusing to run")
            return 1
        try:
            _forbid_local_bin(Path.home() / ".local" / "bin")
            check("L-forbid-local-bin — hardcoded ~/.local/bin is refused",
                  False, "no refusal")
        except Refuse as exc:
            check("L-forbid-local-bin — hardcoded ~/.local/bin is refused",
                  exc.code == "path-forbidden", exc.code)
        tree = tmp / "tree"
        tree.mkdir()
        _fixture(tree)
        target = tmp / "workspace"
        target.mkdir()
        catalog, shadowed = scan_all(tmp / "no-mirror", tree)

        print("scan")
        data = do_scan(catalog, shadowed)
        check("discovers every NEW-STANDARD component on the tree",
              sorted(catalog) == ["_hub/agents.md/hubguide",
                                  "_hub/command/hubcmd",
                                  "_hub/config/hubmcp",
                                  "_hub/hook/hubhook",
                                  "_hub/path/hubbin.py",
                                  "_hub/path/hubbindir",
                                  "_hub/pool/hubpool",
                                  "_hub/rules/hubrule",
                                  "_hub/skills/hubskill",
                                  "_hub/skills/vendored",
                                  "_hub/sub-agent/hubagent",
                                  "badmod/badcomp",
                                  "fixmod/codexcomp",
                                  "fixmod/dupcomp", "fixmod/goodcomp",
                                  "fixmod/reservedcomp",
                                  "oldmod/oldcomp"],
              str(sorted(catalog)))
        check("a _skills/ folder is discovered as a hub skill unit (D15)",
              catalog["_hub/skills/vendored"]["kind"] == "hub"
              and catalog["_hub/skills/vendored"]["method"] == "skill"
              and catalog["_hub/skills/vendored"]["module"] == HUB_DIR
              and catalog["_hub/skills/vendored"]["legacy_skills_dir"]
              and not catalog["_hub/skills/vendored"]["manifest"],
              str(catalog["_hub/skills/vendored"]))
        check("it is INSTALLABLE despite having no manifest, and says so",
              is_installable(catalog["_hub/skills/vendored"])
              and [e for e in data["components"]
                   if e["id"] == "_hub/skills/vendored"][0]["methods"]
              == ["skill"], str(catalog["_hub/skills/vendored"]))

        print("\nD2 — depth-2 + exposure.csv is the marker")
        check("a module-root exposure.csv is NOT a component (depth 1)",
              "oldmod" not in catalog,
              str(sorted(catalog)))
        check("a depth-2 exposure.csv IS a component even without component.md",
              "oldmod/oldcomp" in catalog
              and catalog["oldmod/oldcomp"]["manifest"],
              str(sorted(catalog)))
        check("a component.md with no exposure.csv is not a component",
              "fixmod/barecomp" not in catalog,
              str(sorted(catalog)))

        d1 = tmp / "d1-only"
        (d1 / "onlymod").mkdir(parents=True)
        (d1 / "onlymod" / EXPOSURE_NAME).write_text(
            ",".join(EXPOSURE_COLS) + "\n", encoding="utf-8")
        d1_cat, _ = scan_all(tmp / "no-mirror-d1", d1)
        check("D2-depth1 — a depth-1 manifest stays invisible",
              "onlymod" not in d1_cat
              and not any(cid == "onlymod" or cid.startswith("onlymod/")
                          for cid in d1_cat),
              str(sorted(d1_cat)))

        d2 = tmp / "d2-only"
        (d2 / "m" / "c").mkdir(parents=True)
        (d2 / "m" / "c" / EXPOSURE_NAME).write_text(
            ",".join(EXPOSURE_COLS) + "\n", encoding="utf-8")
        md_hits = list(d2.rglob("component.md"))
        d2_cat, _ = scan_all(tmp / "no-mirror-d2", d2)
        check("D2-depth2 — a depth-2 manifest is a component with no "
              "component.md present anywhere",
              not md_hits and "m/c" in d2_cat
              and d2_cat["m/c"]["manifest"],
              f"md={md_hits} cat={sorted(d2_cat)}")

        d3 = tmp / "d3-only"
        (d3 / "m" / "c" / "nested").mkdir(parents=True)
        (d3 / "m" / "c" / "nested" / EXPOSURE_NAME).write_text(
            ",".join(EXPOSURE_COLS) + "\n", encoding="utf-8")
        d3_cat, _ = scan_all(tmp / "no-mirror-d3", d3)
        check("D2-depth3 — a depth-3 manifest is not a component",
              "m/c" not in d3_cat and "m/c/nested" not in d3_cat
              and not any("nested" in cid for cid in d3_cat),
              str(sorted(d3_cat)))

        badm = tmp / "bad-manifest"
        (badm / "m" / "c").mkdir(parents=True)
        (badm / "m" / "c" / EXPOSURE_NAME).write_text(
            "part-id,method,entry-point\nfoo,skill,x.md\n", encoding="utf-8")
        bad_cat, _ = scan_all(tmp / "no-mirror-bad", badm)
        try:
            exposure_rows(bad_cat["m/c"])
            check("D2-malformed — a malformed manifest refuses by name",
                  False, "no refusal")
        except Refuse as exc:
            check("D2-malformed — a malformed manifest refuses by name",
                  exc.code == "manifest-malformed"
                  and "exposure.csv" in (exc.path or exc.message)
                  and "part-kind" in exc.message,
                  f"{exc.code}: {exc.message}")
        check("D2-malformed — the component is still catalogued "
              "(refuses, does not vanish)",
              "m/c" in bad_cat, str(sorted(bad_cat)))

        ev = tmp / "ws-empty-vanished"
        ev.mkdir()
        write_state(ev, {"components": {
            "gone/empty": {
                "module": "gone", "component": "empty",
                "harnesses": ["claude"], "files": [],
            },
            "fixmod/goodcomp": {
                "module": "fixmod", "component": "goodcomp",
                "harnesses": ["claude"], "files": [],
            },
        }, "shared_claims": []})
        ev_st = upgrade_book(read_state(ev), catalog_parts_map(catalog))
        try:
            plan_files(ev_st["components"], catalog)
            ev_refused = None
        except Refuse as exc:
            ev_refused = f"{exc.code}: {exc.message}"
        check("D2-empty-vanished — booked-but-uncatalogued owning zero "
              "files is dropped silently",
              "gone/empty" not in ev_st["components"]
              and "fixmod/goodcomp" in ev_st["components"]
              and ev_refused is None,
              f"comps={sorted(ev_st['components'])} refuse={ev_refused}")

        fv = tmp / "ws-files-vanished"
        fv.mkdir()
        write_state(fv, {"components": {
            "gone/full": {
                "module": "gone", "component": "full",
                "harnesses": ["claude"],
                "files": [".claude/rules/x.md"],
            },
            "fixmod/goodcomp": {
                "module": "fixmod", "component": "goodcomp",
                "harnesses": ["claude"], "files": [],
            },
        }, "shared_claims": []})
        fv_st = upgrade_book(read_state(fv), catalog_parts_map(catalog))
        check("D2-files-vanished — owning files is kept in the book",
              "gone/full" in fv_st["components"],
              str(sorted(fv_st["components"])))
        try:
            plan_files(fv_st["components"], catalog)
            check("D2-files-vanished — booked-but-uncatalogued owning "
                  "files still refuses component-vanished",
                  False, "no refusal")
        except Refuse as exc:
            check("D2-files-vanished — booked-but-uncatalogued owning "
                  "files still refuses component-vanished",
                  exc.code == "component-vanished"
                  and "gone/full" in exc.message,
                  f"{exc.code}: {exc.message}")

        print("\nD4 — three harnesses (kimi retired 2026-08-14)")
        check("D4-harnesses-are-three",
              HARNESSES == ("claude", "codex", "opencode")
              and len(HARNESSES) == 3
              and "kimi" not in HARNESSES
              and all(name in HARNESSES
                      for name in ("claude", "codex", "opencode"))
              and all("kimi" not in (MATRIX[method] or {})
                      for method in MATRIX)
              and all(h in MATRIX["skill"] for h in HARNESSES)
              and "kimi" not in GUIDANCE_FILE
              and "kimi" not in FORCED_READ_HARNESSES
              and FORCED_READ_HARNESSES == ("codex",)
              and all(h in GUIDANCE_FILE for h in HARNESSES),
              f"HARNESSES={HARNESSES} forced={FORCED_READ_HARNESSES}")
        try:
            _parse_harnesses("kimi")
            check("D4-harness-kimi-refuses", False, "no refusal")
        except Refuse as exc:
            known = [h for h in ("claude", "codex", "opencode")
                     if h in exc.message]
            check("D4-harness-kimi-refuses",
                  exc.code == "harness-unknown"
                  and "kimi" in exc.message
                  and known == ["claude", "codex", "opencode"]
                  and "kimi" not in exc.message.split("known:", 1)[-1],
                  f"{exc.code}: {exc.message}")
        try:
            _parse_harnesses("kimi,claude")
            check("D4-harness-kimi-mixed-refuses", False, "no refusal")
        except Refuse as exc:
            check("D4-harness-kimi-mixed-refuses",
                  exc.code == "harness-unknown" and "kimi" in exc.message,
                  f"{exc.code}: {exc.message}")
        kf = tmp / "ws-kimi-flag"
        kf.mkdir()
        try:
            cmd_add(build_parser().parse_args(
                ["add", "-c", "fixmod/goodcomp", "--harness", "kimi",
                 "--dry-run"]),
                    kf, catalog, [])
            check("D4-cli-harness-kimi-refuses", False, "no refusal")
        except Refuse as exc:
            check("D4-cli-harness-kimi-refuses",
                  exc.code == "harness-unknown"
                  and "kimi" in exc.message
                  and all(h in exc.message
                          for h in ("claude", "codex", "opencode")),
                  f"{exc.code}: {exc.message}")

        sk = tmp / "ws-strip-kimi"
        sk.mkdir()
        (sk / STATE_REL).parent.mkdir(parents=True)
        sk_book = {
            "schema": 1, "installer": "install2.py",
            "components": {
                "fixmod/goodcomp": {
                    "module": "fixmod", "component": "goodcomp",
                    "harnesses": ["kimi", "claude", "opencode", "codex"],
                    "files": [],
                },
                "fixmod/codexcomp": {
                    "module": "fixmod", "component": "codexcomp",
                    "harnesses": ["claude", "kimi"],
                    "files": [],
                },
            },
        }
        (sk / STATE_REL).write_text(json.dumps(sk_book), encoding="utf-8")
        sk_before = (sk / STATE_REL).read_text(encoding="utf-8")
        sk_st = read_state(sk)
        sk_good = sk_st["components"]["fixmod/goodcomp"]["harnesses"]
        sk_codex = sk_st["components"]["fixmod/codexcomp"]["harnesses"]
        check("D4-book-strips-kimi-keeps-others",
              sk_good == ["claude", "codex", "opencode"]
              and sk_codex == ["claude"]
              and "kimi" not in sk_good
              and "kimi" not in sk_codex
              and sk_good
              and sk_codex
              and (sk / STATE_REL).read_text(encoding="utf-8") == sk_before,
              f"good={sk_good} codex={sk_codex}")
        write_state(sk, sk_st)
        sk_persisted = json.loads((sk / STATE_REL).read_text(encoding="utf-8"))
        check("D4-book-strip-persists-on-write",
              sk_persisted["components"]["fixmod/goodcomp"]["harnesses"]
              == ["claude", "codex", "opencode"]
              and sk_persisted["components"]["fixmod/codexcomp"]["harnesses"]
              == ["claude"]
              and "kimi" not in json.dumps(sk_persisted["components"]),
              str({cid: rec["harnesses"]
                   for cid, rec in sk_persisted["components"].items()}))

        se = tmp / "ws-kimi-only"
        se.mkdir()
        (se / STATE_REL).parent.mkdir(parents=True)
        (se / STATE_REL).write_text(json.dumps({
            "schema": 1, "components": {
                "gone/kimi-only": {
                    "module": "gone", "component": "kimi-only",
                    "harnesses": ["kimi"], "files": [],
                },
            },
        }), encoding="utf-8")
        try:
            read_state(se)
            check("D4-book-kimi-only-refuses", False, "no refusal")
        except Refuse as exc:
            check("D4-book-kimi-only-refuses",
                  exc.code == "harness-list-empty"
                  and "gone/kimi-only" in exc.message
                  and "kimi" in exc.message,
                  f"{exc.code}: {exc.message}")

        print("\nD12 — the old installer's sweep cannot reach our names")
        check("a `rbtv-` part id is REFUSED, never minted",
              _reserved_id_refuses(tmp, catalog))

        # Pre-existing foreign content the run must preserve (D6/D12): an
        # old-installer `rbtv-` sibling in each swept folder, plus foreign keys
        # inside two shared config files.
        for rel, body in (
            (".claude/rules/rbtv-legacy.md", "old installer rule\n"),
            (".claude/commands/rbtv-legacy.md", "old installer command\n"),
            (".claude/agents/rbtv-legacy.md", "old installer agent\n"),
            (".claude/skills/rbtv-legacy/SKILL.md", "old installer skill\n"),
        ):
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            (target / rel).write_text(body, encoding="utf-8")
        (target / ".claude/settings.json").write_text(
            json.dumps({"foreignKey": 1}, indent=2) + "\n", encoding="utf-8")
        (target / ".mcp.json").write_text(
            json.dumps({"mcpServers": {"foreign": {"url": "https://x.invalid"}}},
                       indent=2) + "\n", encoding="utf-8")
        legacy = {rel: (target / rel).read_text(encoding="utf-8") for rel in (
            ".claude/rules/rbtv-legacy.md", ".claude/commands/rbtv-legacy.md",
            ".claude/agents/rbtv-legacy.md",
            ".claude/skills/rbtv-legacy/SKILL.md")}

        print("\ngreen arm — install all three harnesses")
        res = do_install(target, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                         dry_run=False)
        expect = {
            ".claude/skills/fixskill/SKILL.md",
            ".agents/skills/fixskill/SKILL.md",
            ".claude/commands/fixcmd.md",
            ".codex/prompts/fixcmd.md",
            ".opencode/commands/fixcmd.md",
            ".claude/rules/fixrule.md",
            ".agents/behavior-rules/fixrule.md",
            ".claude/agents/fixagent.md",
            ".opencode/agents/fixagent.md",
        }
        shared = {".claude/settings.json", ".codex/hooks.json", ".mcp.json",
                  ".codex/config.toml", "opencode.json"}
        on_disk = {p.relative_to(target).as_posix()
                   for p in target.rglob("*") if p.is_file()}
        want = expect | shared | set(legacy) | {STATE_REL.as_posix()}
        check("every CMP-12 realization landed under its BARE part id, and "
              "nothing else",
              on_disk == want,
              f"missing={sorted(want - on_disk)} extra={sorted(on_disk - want)}")
        check("D12 — no artifact carries the retired rbtv2- prefix",
              not any(Path(rel).name.startswith(LEGACY_PREFIX)
                      or Path(rel).parent.name.startswith(LEGACY_PREFIX)
                      for rel in expect), str(sorted(expect)))
        check("D12 — every artifact carries the ownership marker instead",
              all(MANAGED_MARK in (target / rel).read_text() for rel in expect)
              and all(_is_ours(target, rel) for rel in expect),
              str(sorted(rel for rel in expect
                         if MANAGED_MARK not in (target / rel).read_text())))
        check("D12 — the marker sits BELOW the frontmatter, which still parses",
              (target / ".claude/skills/fixskill/SKILL.md")
              .read_text().startswith("---\nname: fixskill\n")
              and (target / ".claude/skills/fixskill/SKILL.md")
              .read_text().split("---\n")[2].lstrip().startswith("<!--"),
              (target / ".claude/skills/fixskill/SKILL.md").read_text()[:200])
        check("`pool` minted nothing; `path` still writes nothing under target",
              not (target / ".claude/skills/fixtool").exists()
              and not (target / ".claude/skills/fixpool").exists()
              and [r["method"] for r
                   in res["report"]["skipped_inventory_rows"]] == ["pool"]
              and not (target / "fixtool").exists()
              and not (target / "tool/thing.py").exists(),
              str(res["report"]["skipped_inventory_rows"]))
        check("green — path part-id is the link name, not the basename",
              (bin_dir() / "fixtool").is_symlink()
              and not (bin_dir() / "thing.py").exists()
              and (bin_dir() / "fixtool").resolve()
              == (tree / "fixmod/goodcomp/tool/thing.py").resolve()
              and read_state(target)["components"]["fixmod/goodcomp"]
              .get("path_links") == ["fixtool"],
              str(list(bin_dir().iterdir()) if bin_dir().is_dir() else None))
        check("skill loader carries a YAML-safe description",
              '"A fixture skill: with a colon"'
              in (target / ".claude/skills/fixskill/SKILL.md").read_text())
        check("rule copied VERBATIM under one marker line",
              (target / ".claude/rules/fixrule.md").read_text()
              == MANAGED_BANNER + (tree / "fixmod/goodcomp/rule-entry.md"
                                   ).read_text(),
              (target / ".claude/rules/fixrule.md").read_text()[:200])
        check("F3 — NO code path mints the retired .agents/rbtv2-exposure.md",
              not (target / ".agents/rbtv2-exposure.md").exists()
              and not any("exposure.md" in rel for rel in expect),
              str(sorted(expect)))
        check("with no basis, the exposure block is REPORTED per guidance file "
              "an installed harness reads",
              sorted(res["report"]["guidance_manual"]) == ["AGENTS.md",
                                                           "CLAUDE.md"]
              and "Step 0" in res["report"]["guidance_manual"]["AGENTS.md"]
              and "Step 0" not in res["report"]["guidance_manual"]["CLAUDE.md"]
              and "fixguide"
              in res["report"]["guidance_manual"]["CLAUDE.md"],
              str(sorted(res["report"]["guidance_manual"])))
        check("root guidance file NEVER written (D8)",
              not (target / "CLAUDE.md").exists()
              and not (target / "AGENTS.md").exists())
        check("claude settings gained OUR keys beside the foreign one",
              json.loads((target / ".claude/settings.json").read_text())
              == {"foreignKey": 1, "enableAllProjectMcpServers": True,
                  "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                      {"type": "command", "command": "true"}]}]}})
        check("mcp.json gained the prefixed server beside the foreign one",
              sorted(json.loads((target / ".mcp.json").read_text())["mcpServers"])
              == sorted(["fix", "foreign"]))
        check("codex config.toml carries a fenced block with the url form",
              f"# {FENCE_ID}:start" in (target / ".codex/config.toml").read_text()
              and 'url = "https://example.invalid/mcp"'
              in (target / ".codex/config.toml").read_text())
        check("old-installer rbtv- siblings untouched by the install",
              all((target / rel).read_text() == body
                  for rel, body in legacy.items()))

        state = read_state(target)
        rec = state["components"]["fixmod/goodcomp"]
        check("install.json books every per-component file",
              rec_files(rec) == expect - set(state["guidance_files"]),
              str(sorted(rec_files(rec) ^ (expect - set(state["guidance_files"])))))
        check("schema 2 books parts keyed by bare part-id, no rec.files",
              state.get("schema") == SCHEMA
              and "files" not in rec
              and set(rec["parts"]) >= {"fixskill", "fixcmd", "fixrule",
                                        "fixagent", "fixhook", "fixmcp",
                                        "fixguide", "fixtool", "fixpool"}
              and rec["parts"]["fixskill"]["method"] == "skill"
              and rec["parts"]["fixmcp"]["method"] == "config"
              and ".claude/skills/fixskill/SKILL.md"
              in rec["parts"]["fixskill"]["files"],
              str(sorted(rec.get("parts") or {})))
        check("install.json books every shared-file claim",
              sorted(state["shared_claims"]) == sorted([
                  _claim_id(".claude/settings.json",
                            ["enableAllProjectMcpServers"]),
                  _claim_id(".claude/settings.json", ["hooks", "PreToolUse"]),
                  _claim_id(".codex/hooks.json", ["hooks", "PreToolUse"]),
                  _claim_id(".mcp.json", ["mcpServers", "fix"]),
                  _claim_id("opencode.json", ["mcp", "fix"]),
                  _claim_id(".codex/config.toml", None),
              ]), str(sorted(state["shared_claims"])))
        check("install.json books the source tree + harnesses",
              rec["tree"] == "repo" and rec["tree_root"] == str(tree)
              and rec["harnesses"] == list(HARNESSES))
        check("re-install is idempotent",
              do_install(target, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                         dry_run=False)["written"] == [])

        print("\nred arm — unknown method")
        try:
            do_install(target, catalog, ["badmod/badcomp"], list(HARNESSES),
                       dry_run=False)
            check("unknown method refuses", False, "no refusal raised")
        except Refuse as exc:
            check("unknown method refuses", exc.code == "method-unknown", exc.code)
            check("unknown-method refusal wrote nothing",
                  "badcomp" not in json.dumps(read_state(target)))

        print("\nred arm — collision with content we did not write")
        fresh = tmp / "workspace2"
        (fresh / ".claude" / "rules").mkdir(parents=True)
        (fresh / ".claude/rules/fixrule.md").write_text(
            "hand-placed\n", encoding="utf-8")
        (fresh / ".mcp.json").write_text(json.dumps(
            {"mcpServers": {"fix": {"url": "https://squatter.invalid"}}}),
            encoding="utf-8")
        before = {p.relative_to(fresh).as_posix(): p.read_text()
                  for p in fresh.rglob("*") if p.is_file()}
        try:
            do_install(fresh, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False)
            check("collision refuses", False, "no refusal raised")
        except Refuse as exc:
            check("collision refuses", exc.code == "collision", exc.code)
            check("both the file AND the shared key are named",
                  ".claude/rules/fixrule.md" in exc.message
                  and ".mcp.json::mcpServers." + "fix" in exc.message,
                  exc.message)
        after = {p.relative_to(fresh).as_posix(): p.read_text()
                 for p in fresh.rglob("*") if p.is_file()}
        check("collision refusal left ZERO files and changed nothing",
              before == after, str(sorted(set(after) ^ set(before))))

        print("\nharness filter")
        only = tmp / "workspace3"
        only.mkdir()
        do_install(only, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
        disk = {p.relative_to(only).as_posix()
                for p in only.rglob("*") if p.is_file()}
        check("codex/opencode files absent under --harness claude",
              not any(d.startswith((".codex/", ".opencode/", ".agents/skills"))
                      for d in disk), str(sorted(disk)))

        print("\nD13 — the guidance mirror")
        check("mirror OFF by default: nothing written, nothing recorded",
              not (target / "AGENTS.md").exists()
              and "guidance_basis" not in read_state(target))

        mt = tmp / "workspace4"
        mt.mkdir()
        basis_body = "# The workspace\n\nHand-authored guidance.\n"
        (mt / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        basis_hash = hashlib.sha256((mt / "CLAUDE.md").read_bytes()).hexdigest()
        do_install(mt, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False, guidance_basis="CLAUDE.md")
        mirrored = (mt / "AGENTS.md").read_text()
        check("mirror generated from the basis",
              mirrored.endswith(basis_body) and "DO NOT EDIT" in mirrored
              and "mirrors CLAUDE.md" in mirrored, mirrored[:120])
        check("the user-authored basis file was NEVER modified",
              hashlib.sha256((mt / "CLAUDE.md").read_bytes()).hexdigest()
              == basis_hash)
        check("the basis choice is persisted",
              read_state(mt).get("guidance_basis") == "CLAUDE.md")
        check("the mirror is booked as an installer-owned file",
              "AGENTS.md" in read_state(mt).get("guidance_files", []))
        # A later run must NOT re-ask and must NOT need the flag again.
        res4 = do_install(mt, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                          dry_run=False)
        check("re-run without the flag still mirrors, and is idempotent",
              res4["written"] == []
              and res4["report"]["guidance_mirror"]["basis"] == "CLAUDE.md",
              str(res4["written"]))
        (mt / "CLAUDE.md").write_text(basis_body + "\nA new line.\n",
                                      encoding="utf-8")
        res4 = do_install(mt, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                          dry_run=False)
        check("an edited basis re-renders the mirror on the next run",
              res4["written"] == ["AGENTS.md"]
              and "A new line." in (mt / "AGENTS.md").read_text(),
              str(res4["written"]))
        check("full uninstall takes the mirror, leaves the basis",
              do_uninstall(mt, catalog, ["fixmod/goodcomp"], dry_run=False)
              and not (mt / "AGENTS.md").exists()
              and (mt / "CLAUDE.md").is_file())

        print("\nred arm — a garbage basis value refuses")
        for bad_value, where in (("QWEN.md", "flag"), ("../etc", "book")):
            mt2 = tmp / f"workspace5-{where}"
            mt2.mkdir()
            (mt2 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
            kwargs = {"guidance_basis": bad_value} if where == "flag" else {}
            if where == "book":
                (mt2 / STATE_REL).parent.mkdir(parents=True)
                (mt2 / STATE_REL).write_text(
                    json.dumps({"schema": 1, "components": {},
                                "shared_claims": [],
                                "guidance_basis": bad_value}),
                    encoding="utf-8")
            try:
                do_install(mt2, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                           dry_run=False, **kwargs)
                check(f"garbage basis from the {where} refuses", False,
                      "no refusal raised")
            except Refuse as exc:
                check(f"garbage basis from the {where} refuses",
                      exc.code == "guidance-basis-invalid", exc.code)
                check(f"the {where} refusal wrote nothing",
                      not (mt2 / "AGENTS.md").exists()
                      and not (mt2 / ".claude").exists())

        print("\nred arm — a foreign mirror file (old installer's) refuses")
        mt3 = tmp / "workspace6"
        mt3.mkdir()
        (mt3 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        (mt3 / "AGENTS.md").write_text("rendered by the OLD installer\n",
                                       encoding="utf-8")
        try:
            do_install(mt3, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False, guidance_basis="CLAUDE.md")
            check("a foreign AGENTS.md refuses", False, "no refusal raised")
        except Refuse as exc:
            check("a foreign AGENTS.md refuses",
                  exc.code == "guidance-mirror-collision"
                  and "AGENTS.md" in exc.message,
                  f"{exc.code}: {exc.message}")
            # F4 — the generic advice ("move or remove it") would tell the user
            # to delete hand-authored guidance. The mirror message must not.
            check("the mirror collision names the real situation, never "
                  "'remove it'",
                  "DO NOT delete it" in exc.message
                  and "move or remove it" not in exc.message, exc.message)
            check("the foreign mirror is byte-identical after the refusal",
                  (mt3 / "AGENTS.md").read_text()
                  == "rendered by the OLD installer\n")

        print("\nF1 — the basis FLIP never deletes the user's file")
        mt5 = tmp / "workspace7"
        mt5.mkdir()
        (mt5 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        do_install(mt5, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False, guidance_basis="CLAUDE.md")
        # The user switches: AGENTS.md becomes the file they author by hand
        # (same NAME the book still carries as our generated mirror), CLAUDE.md
        # goes away.
        authored = "# Authored by hand, under the old mirror's name\n"
        (mt5 / "AGENTS.md").write_text(authored, encoding="utf-8")
        (mt5 / "CLAUDE.md").unlink()
        authored_hash = hashlib.sha256((mt5 / "AGENTS.md").read_bytes()).hexdigest()
        res5 = do_install(mt5, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                          dry_run=False, guidance_basis="AGENTS.md")
        check("the flipped-to basis is NOT in the delete set",
              res5["deleted"] == [], str(res5["deleted"]))
        check("the hand-authored file survives the flip byte-for-byte",
              (mt5 / "AGENTS.md").is_file()
              and hashlib.sha256((mt5 / "AGENTS.md").read_bytes()).hexdigest()
              == authored_hash)
        check("the flip renders the other name from the new basis",
              res5["written"] == ["CLAUDE.md"]
              and authored in (mt5 / "CLAUDE.md").read_text(),
              str(res5["written"]))
        check("the book no longer claims the basis as a generated file",
              "AGENTS.md" not in read_state(mt5)["guidance_files"]
              and "CLAUDE.md" in read_state(mt5)["guidance_files"],
              str(read_state(mt5)["guidance_files"]))

        print("\nF2 — a missing basis names its recovery, and a flag recovers")
        mt6 = tmp / "workspace8"
        mt6.mkdir()
        (mt6 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        do_install(mt6, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False, guidance_basis="CLAUDE.md")
        (mt6 / "CLAUDE.md").unlink()          # basis gone; AGENTS.md remains
        try:
            do_install(mt6, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False)
            check("a missing basis refuses", False, "no refusal raised")
        except Refuse as exc:
            check("a missing basis refuses",
                  exc.code == "guidance-basis-missing", exc.code)
            check("the refusal names BOTH recoveries (repoint, or turn off)",
                  "--guidance-basis AGENTS.md" in exc.message
                  and f"--guidance-basis {BASIS_NONE}" in exc.message,
                  exc.message)
        res6 = do_install(mt6, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                          dry_run=False, guidance_basis="AGENTS.md")
        check("repointing the basis at the surviving file recovers the run",
              res6["written"] == ["CLAUDE.md"]
              and read_state(mt6)["guidance_basis"] == "AGENTS.md",
              str(res6["written"]))

        print("\nF3 — an uninstall is never blocked by a mirror problem")
        mt7 = tmp / "workspace9"
        mt7.mkdir()
        (mt7 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        do_install(mt7, catalog, ["fixmod/goodcomp", "fixmod/codexcomp"],
                   list(HARNESSES), dry_run=False, guidance_basis="CLAUDE.md")
        (mt7 / "CLAUDE.md").unlink()          # basis gone AFTER the install
        res7 = do_uninstall(mt7, catalog, ["fixmod/codexcomp"], dry_run=False)
        check("the partial uninstall succeeds with a missing basis",
              res7["ok"] and read_state(mt7)["components"].keys()
              == {"fixmod/goodcomp"}, str(res7))
        check("it reports the skip instead of pretending it mirrored",
              res7["report"]["guidance_mirror"]["skipped"]
              == "guidance-basis-missing",
              str(res7["report"]["guidance_mirror"]))
        check("neither root guidance file was deleted by the skip",
              (mt7 / "AGENTS.md").is_file() and "AGENTS.md" not in res7["deleted"],
              str(res7["deleted"]))

        print("\nF6 — a non-UTF-8 basis refuses cleanly")
        mt8 = tmp / "workspace10"
        mt8.mkdir()
        (mt8 / "CLAUDE.md").write_bytes(b"\xff\xfe not text at all\x00")
        try:
            do_install(mt8, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False, guidance_basis="CLAUDE.md")
            check("a non-UTF-8 basis refuses", False, "no refusal raised")
        except Refuse as exc:
            check("a non-UTF-8 basis refuses",
                  exc.code == "guidance-basis-unreadable", exc.code)
            check("the unreadable-basis refusal wrote nothing",
                  not (mt8 / "AGENTS.md").exists()
                  and not (mt8 / ".claude").exists())

        print("\nR1 — the mirror is RECURSIVE, and the walk skips what it must")
        mtr = tmp / "workspace11"
        bodies = {
            "CLAUDE.md": "# root\n\nRoot guidance.\n",
            "sub/CLAUDE.md": "# sub\n\nSub guidance.\n",
            "sub/deep/CLAUDE.md": "# deep\n\nDeep guidance.\n",
            "vendor/CLAUDE.md": "# a nested repo's own guidance\n",
            ".rbtv/goals/g1/CLAUDE.md": "# a scaffold-owned goal router\n",
            "node_modules/pkg/CLAUDE.md": "# vendored junk\n",
            "skipme/CLAUDE.md": "# excluded by flag\n",
            "sub/notes.md": "# not guidance\n",
        }
        for rel, body in bodies.items():
            (mtr / rel).parent.mkdir(parents=True, exist_ok=True)
            (mtr / rel).write_text(body, encoding="utf-8")
        (mtr / "vendor" / ".git").mkdir()      # nested git repo
        base_hashes = {rel: hashlib.sha256((mtr / rel).read_bytes()).hexdigest()
                       for rel in bodies}
        resr = do_install(mtr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                          dry_run=False, guidance_basis="CLAUDE.md",
                          guidance_excludes=["skipme"])
        mirrors_on_disk = sorted(p.relative_to(mtr).as_posix()
                                 for p in mtr.rglob("AGENTS.md"))
        check("one mirror beside every eligible CLAUDE.md, and only those",
              mirrors_on_disk == ["AGENTS.md", "sub/AGENTS.md",
                                  "sub/deep/AGENTS.md"], str(mirrors_on_disk))
        check("a nested git repo's guidance is NEVER touched",
              not (mtr / "vendor/AGENTS.md").exists())
        check(".rbtv/goals is carved out (both routers are scaffold-owned)",
              not (mtr / ".rbtv/goals/g1/AGENTS.md").exists())
        check("node_modules is never walked",
              not (mtr / "node_modules/pkg/AGENTS.md").exists())
        check("--guidance-exclude skips its subtree and is persisted",
              not (mtr / "skipme/AGENTS.md").exists()
              and read_state(mtr)["guidance_excludes"] == ["skipme"],
              str(read_state(mtr).get("guidance_excludes")))
        check("each mirror is generated from ITS OWN directory's basis",
              (mtr / "sub/deep/AGENTS.md").read_text().endswith(
                  bodies["sub/deep/CLAUDE.md"])
              and "mirrors sub/deep/CLAUDE.md"
              in (mtr / "sub/deep/AGENTS.md").read_text()
              and (mtr / "sub/AGENTS.md").read_text().endswith(
                  bodies["sub/CLAUDE.md"]))
        check("EVERY basis file is byte-identical after the run",
              all(hashlib.sha256((mtr / rel).read_bytes()).hexdigest() == h
                  for rel, h in base_hashes.items()))
        check("every nested mirror is booked",
              read_state(mtr)["guidance_files"] == sorted(
                  ["AGENTS.md", "sub/AGENTS.md", "sub/deep/AGENTS.md"]),
              str(read_state(mtr)["guidance_files"]))
        check("the report counts the mirrors it rendered",
              resr["report"]["guidance_mirror"]["count"] == 3,
              str(resr["report"]["guidance_mirror"]))
        resr2 = do_install(mtr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                           dry_run=False)
        check("a recursive re-run is idempotent, flags and all",
              resr2["written"] == [] and resr2["deleted"] == []
              and resr2["report"]["guidance_mirror"]["count"] == 3,
              str(resr2["written"] + resr2["deleted"]))

        print("\nR2 — the basis flip protects EVERY directory's basis, not the "
              "root's alone")
        for rel in ("CLAUDE.md", "sub/CLAUDE.md", "sub/deep/CLAUDE.md"):
            (mtr / rel).unlink()              # the user now authors AGENTS.md
        (mtr / "sub/AGENTS.md").write_text(
            (mtr / "sub/AGENTS.md").read_text() + "\nHand-edited after the flip.\n",
            encoding="utf-8")
        flipped = {rel: hashlib.sha256((mtr / rel).read_bytes()).hexdigest()
                   for rel in mirrors_on_disk}
        resr3 = do_install(mtr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                           dry_run=False, guidance_basis="AGENTS.md")
        check("NO basis is deleted by the flip, at any depth",
              resr3["deleted"] == [], str(resr3["deleted"]))
        check("every flipped-to basis survives byte-for-byte",
              all(hashlib.sha256((mtr / rel).read_bytes()).hexdigest() == h
                  for rel, h in flipped.items()))
        check("the flip renders the other name at every depth",
              sorted(resr3["written"]) == ["CLAUDE.md", "sub/CLAUDE.md",
                                           "sub/deep/CLAUDE.md"],
              str(resr3["written"]))
        check("a generated banner is STRIPPED, never stacked (7.623a)",
              (mtr / "sub/CLAUDE.md").read_text().count(
                  "GENERATED by install2.py") == 1
              and "Hand-edited after the flip."
              in (mtr / "sub/CLAUDE.md").read_text()
              and resr3["report"]["guidance_mirror"]["banner_stripped"]
              == ["AGENTS.md", "sub/AGENTS.md", "sub/deep/AGENTS.md"],
              str(resr3["report"]["guidance_mirror"].get("banner_stripped")))
        resr4 = do_install(mtr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                           dry_run=False)
        check("re-mirroring a mirror is stable — no banner growth per run",
              resr4["written"] == [], str(resr4["written"]))
        check("full uninstall takes every nested mirror and no basis",
              do_uninstall(mtr, catalog, ["fixmod/goodcomp"], dry_run=False)
              and sorted(p.relative_to(mtr).as_posix()
                         for p in mtr.rglob("CLAUDE.md"))
              == [".rbtv/goals/g1/CLAUDE.md", "node_modules/pkg/CLAUDE.md",
                  "skipme/CLAUDE.md", "vendor/CLAUDE.md"]
              and sorted(p.relative_to(mtr).as_posix()
                         for p in mtr.rglob("AGENTS.md"))
              == ["AGENTS.md", "sub/AGENTS.md", "sub/deep/AGENTS.md"],
              str(sorted(p.relative_to(mtr).as_posix()
                         for p in mtr.rglob("*.md"))))

        print("\nR3 — a foreign mirror DEEP in the tree refuses too")
        mtd = tmp / "workspace12"
        (mtd / "a" / "b").mkdir(parents=True)
        (mtd / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        (mtd / "a/b/CLAUDE.md").write_text("# deep\n", encoding="utf-8")
        (mtd / "a/b/AGENTS.md").write_text("rendered by the OLD installer\n",
                                           encoding="utf-8")
        try:
            do_install(mtd, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False, guidance_basis="CLAUDE.md")
            check("a foreign nested AGENTS.md refuses", False, "no refusal")
        except Refuse as exc:
            check("a foreign nested AGENTS.md refuses",
                  exc.code == "guidance-mirror-collision"
                  and "a/b/AGENTS.md" in exc.message, f"{exc.code}: {exc.message}")
            check("the deep refusal wrote nothing, anywhere",
                  not (mtd / "AGENTS.md").exists()
                  and (mtd / "a/b/AGENTS.md").read_text()
                  == "rendered by the OLD installer\n"
                  and not (mtd / ".claude").exists())

        print("\nR4 — ADOPTION: a PROVABLY-generated foreign mirror is taken "
              "over; an unproven one is still refused")
        mta = tmp / "workspace13"
        (mta / "deep").mkdir(parents=True)
        (mta / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        (mta / "deep/CLAUDE.md").write_text("# deep\n\nDeep guidance.\n",
                                            encoding="utf-8")
        # Byte-for-byte the shape install.py's model_mirror renders.
        old_mirror = (
            "<!-- AUTO-GENERATED MIRROR — DO NOT EDIT. Generated by rbtv "
            "mirror.py from CLAUDE.md. -->\n\n"
            "> [!danger] GENERATED FILE — DO NOT EDIT\n"
            "> This `AGENTS.md` is an auto-generated mirror of `CLAUDE.md`.\n"
            "\n---\n\n# Stale body from a month ago\n")
        (mta / "AGENTS.md").write_text(old_mirror, encoding="utf-8")
        (mta / "deep/AGENTS.md").write_text(
            old_mirror.replace("CLAUDE.md", "deep/CLAUDE.md"), encoding="utf-8")
        basis_hashes = {rel: hashlib.sha256((mta / rel).read_bytes()).hexdigest()
                        for rel in ("CLAUDE.md", "deep/CLAUDE.md")}
        resa = do_install(mta, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                          dry_run=False, guidance_basis="CLAUDE.md")
        check("the old installer's mirror is ADOPTED, not refused, at any depth",
              resa["adopted"] == ["AGENTS.md", "deep/AGENTS.md"],
              str(resa.get("adopted")))
        check("an adopted mirror is regenerated fresh from its own basis",
              {"AGENTS.md", "deep/AGENTS.md"} <= set(resa["written"])
              and (mta / "AGENTS.md").read_text().endswith(basis_body)
              and "Stale body from a month ago"
              not in (mta / "AGENTS.md").read_text(),
              str(resa["written"]))
        check("the adopted file carries exactly ONE banner — ours",
              (mta / "AGENTS.md").read_text().count("DO NOT EDIT") == 1
              and "AUTO-GENERATED MIRROR" not in (mta / "AGENTS.md").read_text())
        check("adopted mirrors are booked, so uninstall can take them back",
              {"AGENTS.md", "deep/AGENTS.md"}
              <= set(read_state(mta)["guidance_files"]),
              str(read_state(mta)["guidance_files"]))
        check("adoption never touches a basis, at any depth",
              all(hashlib.sha256((mta / rel).read_bytes()).hexdigest() == h
                  for rel, h in basis_hashes.items()))
        check("the run AFTER an adoption is idempotent",
              do_install(mta, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                         dry_run=False)["written"] == [])
        # The other side of the boundary: no banner → no proof → still refused.
        mtb = tmp / "workspace14"
        (mtb / "deep").mkdir(parents=True)
        (mtb / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        (mtb / "deep/CLAUDE.md").write_text("# deep\n", encoding="utf-8")
        hand = "# AGENTS.md I wrote by hand\n\nDo not clobber this.\n"
        (mtb / "deep/AGENTS.md").write_text(hand, encoding="utf-8")
        try:
            do_install(mtb, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False, guidance_basis="CLAUDE.md")
            check("a HAND-AUTHORED mirror-named file is never adopted", False,
                  "no refusal raised — it was adopted")
        except Refuse as exc:
            check("a HAND-AUTHORED mirror-named file is never adopted",
                  exc.code == "guidance-mirror-collision"
                  and "deep/AGENTS.md" in exc.message, f"{exc.code}")
            check("the hand-authored file is byte-identical after the refusal",
                  (mtb / "deep/AGENTS.md").read_text() == hand
                  and not (mtb / "AGENTS.md").exists())

        print("\nH — the mirror is HARNESS-KEYED (CMP-12 agents.md row)")
        def _mk(name: str, harnesses: list[str], basis: str,
                extra: dict | None = None):
            """A fresh workspace with a root + nested basis, installed for
            *harnesses* only. Returns (path, result)."""
            ws = tmp / name
            (ws / "sub").mkdir(parents=True)
            (ws / basis).write_text(basis_body, encoding="utf-8")
            (ws / "sub" / basis).write_text("# sub\n\nSub guidance.\n",
                                            encoding="utf-8")
            for rel, body in (extra or {}).items():
                (ws / rel).parent.mkdir(parents=True, exist_ok=True)
                (ws / rel).write_text(body, encoding="utf-8")
            return ws, do_install(ws, catalog, ["fixmod/goodcomp"], harnesses,
                                  dry_run=False, guidance_basis=basis)

        h1, r1 = _mk("ws-claude-only", ["claude"], "CLAUDE.md")
        h1_hash = hashlib.sha256((h1 / "CLAUDE.md").read_bytes()).hexdigest()
        check("H1 — claude-only + basis CLAUDE.md writes NO mirror, anywhere",
              not list(h1.rglob("AGENTS.md"))
              and r1["report"]["guidance_mirror"]["targets"] == []
              and r1["report"]["guidance_mirror"]["count"] == 0
              and read_state(h1)["guidance_files"] == [],
              str(r1["report"]["guidance_mirror"]))
        check("H1 — and the basis is untouched, at every depth",
              hashlib.sha256((h1 / "CLAUDE.md").read_bytes()).hexdigest()
              == h1_hash
              and (h1 / "sub/CLAUDE.md").read_text() == "# sub\n\nSub "
              "guidance.\n")
        check("H1 — the block claude needs is REPORTED for the basis, "
              "never written",
              sorted(r1["report"]["guidance_manual"]) == ["CLAUDE.md"]
              and "Step 0" not in r1["report"]["guidance_manual"]["CLAUDE.md"],
              str(sorted(r1["report"]["guidance_manual"])))
        check("H1 — a claude-only re-run stays a no-op",
              do_install(h1, catalog, ["fixmod/goodcomp"], ["claude"],
                         dry_run=False)["written"] == [])

        h2, r2 = _mk("ws-codex-only", ["codex"], "CLAUDE.md")
        check("H2 — selecting codex renders AGENTS.md, recursively",
              sorted(q.relative_to(h2).as_posix()
                     for q in h2.rglob("AGENTS.md"))
              == ["AGENTS.md", "sub/AGENTS.md"]
              and r2["report"]["guidance_mirror"]["targets"] == ["AGENTS.md"],
              str(r2["report"]["guidance_mirror"]))
        check("H2 — the forced Step-0 read is IN the generated guidance file, "
              "at the ROOT only (F4)",
              "Step 0" in (h2 / "AGENTS.md").read_text()
              and "`.agents/behavior-rules/fixrule.md`"
              in (h2 / "AGENTS.md").read_text()
              and "fixguide" in (h2 / "AGENTS.md").read_text()
              and "Step 0" not in (h2 / "sub/AGENTS.md").read_text(),
              (h2 / "AGENTS.md").read_text()[:400])
        check("H2 — the generated body still ends with the basis body",
              (h2 / "AGENTS.md").read_text().endswith(basis_body))

        h3, r3 = _mk("ws-agents-share", ["codex", "opencode"],
                     "CLAUDE.md")
        check("H3 — remaining AGENTS.md harnesses get ONE file per folder",
              r3["report"]["guidance_mirror"]["targets"] == ["AGENTS.md"]
              and r3["report"]["guidance_mirror"]["count"] == 2,
              str(r3["report"]["guidance_mirror"]))

        h4, r4 = _mk("ws-no-forced", ["claude", "opencode"], "CLAUDE.md")
        check("H4 — opencode takes NO forced read (CMP-12 gives it no separate "
              "rule type; it reads .claude/)",
              (h4 / "AGENTS.md").is_file()
              and "Step 0" not in (h4 / "AGENTS.md").read_text()
              and not (h4 / ".agents/behavior-rules").exists()
              and (h4 / ".claude/rules/fixrule.md").is_file(),
              str(sorted(q.relative_to(h4).as_posix()
                         for q in h4.rglob("*") if q.is_file())))

        h5, r5 = _mk("ws-basis-agents", ["claude", "codex"], "AGENTS.md")
        check("H5 — basis AGENTS.md + claude installed renders CLAUDE.md",
              r5["report"]["guidance_mirror"]["targets"] == ["CLAUDE.md"]
              and (h5 / "CLAUDE.md").is_file()
              and "Step 0" not in (h5 / "CLAUDE.md").read_text()
              and "Step 0" in r5["report"]["guidance_manual"]["AGENTS.md"],
              str(r5["report"]["guidance_mirror"]))

        print("\nH6 — the retired exposure index is cleaned by the machinery")
        h6, _ = _mk("ws-retire", ["claude", "codex"], "CLAUDE.md")
        stale_rel = f".agents/{LEGACY_PREFIX}exposure.md"
        (h6 / stale_rel).parent.mkdir(parents=True, exist_ok=True)
        (h6 / stale_rel).write_text("# the old invented index\n",
                                    encoding="utf-8")
        st = read_state(h6)                    # book it, as the old code did
        st["guidance_files"] = sorted(st["guidance_files"] + [stale_rel])
        write_state(h6, st)
        r6 = do_install(h6, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                        dry_run=False)
        check("H6 — an existing rbtv2-exposure.md is DELETED by the next run",
              stale_rel in r6["deleted"] and not (h6 / stale_rel).exists()
              and stale_rel not in read_state(h6)["guidance_files"],
              str(r6["deleted"]))

        print("\nH7 — the exposure block never stacks across a basis flip")
        h7, _ = _mk("ws-flip-block", ["claude", "codex"], "CLAUDE.md")
        (h7 / "CLAUDE.md").unlink()
        (h7 / "sub/CLAUDE.md").unlink()
        r7 = do_install(h7, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                        dry_run=False, guidance_basis="AGENTS.md")
        # The flipped-to basis carried OUR AGENTS.md block (codex's, with the
        # Step-0). Mirroring it back must strip that one and render CLAUDE.md's
        # own block instead — exactly one fence, and no forced read, because
        # claude auto-injects `.claude/rules/`.
        check("H7 — the flipped file's fenced block is stripped, not stacked",
              (h7 / "CLAUDE.md").read_text().count(f"{FENCE_ID}:start") == 1
              and (h7 / "CLAUDE.md").read_text().count("Step 0") == 0
              and "Step 0" in r7["report"]["guidance_manual"]["AGENTS.md"],
              (h7 / "CLAUDE.md").read_text()[:400])
        check("H7 — and the flipped run is idempotent",
              do_install(h7, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                         dry_run=False)["written"] == [])

        print("\nRF1 — Step-0 names ONLY the rule files that harness reads")
        rf = tmp / "ws-mixed-harness"
        rf.mkdir()
        (rf / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        # goodcomp's rule lands under `.claude/rules/` ONLY (claude-only);
        # codexcomp then arrives for codex, whose forced read must enumerate
        # its OWN `.agents/behavior-rules/` file and nothing else.
        do_install(rf, catalog, ["fixmod/goodcomp"], ["claude"],
                   dry_run=False, guidance_basis="CLAUDE.md")
        rrf = do_install(rf, catalog, ["fixmod/codexcomp"], ["codex"],
                         dry_run=False)
        agents_md = (rf / "AGENTS.md").read_text()
        check("RF1 — the claude-only rule is NOT enumerated to codex",
              "fixrule" not in agents_md
              and ".claude/rules" not in agents_md,
              agents_md[:600])
        check("RF1 — codex's own rule IS enumerated, at the path written",
              "Step 0" in agents_md
              and "`.agents/behavior-rules/codexrule.md`" in agents_md
              and (rf / ".agents/behavior-rules/codexrule.md").is_file(),
              agents_md[:600])
        check("RF1 — every path the Step-0 names EXISTS on disk",
              all((rf / line.split("`")[1]).is_file()
                  for line in agents_md.splitlines()
                  if line[:2] in ("1.", "2.", "3.") and "`" in line),
              agents_md[:600])
        check("RF1 — and the unrealized path was never created",
              not (rf / ".agents/behavior-rules/fixrule.md").exists()
              and (rf / ".claude/rules/fixrule.md").is_file())

        print("\nRF2 — a DRY RUN still reports the block the human must place")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_result(do_install(rf, catalog, ["fixmod/codexcomp"],
                                    ["codex"], dry_run=True))
        out = buf.getvalue()
        check("RF2 — the dry run prints the guidance-mirror summary",
              "guidance mirror:" in out and "would generate" in out, out[-600:])
        check("RF2 — and the manual block, flush (never a 4-space code block)",
              "Add this block to CLAUDE.md" in out
              and "\n# rbtv exposure" in out
              and "\n    # rbtv exposure" not in out, out[-600:])

        print("\nRF3 — a flip into an empty-target config de-banners the basis")
        fb = tmp / "ws-flip-empty"
        fb.mkdir()
        (fb / "AGENTS.md").write_text(basis_body, encoding="utf-8")
        do_install(fb, catalog, ["fixmod/goodcomp"], ["claude"],
                   dry_run=False, guidance_basis="AGENTS.md")
        check("RF3 — setup: claude's CLAUDE.md was generated from AGENTS.md",
              "GENERATED by install2.py" in (fb / "CLAUDE.md").read_text())
        rfb = do_install(fb, catalog, ["fixmod/goodcomp"], ["claude"],
                         dry_run=False, guidance_basis="CLAUDE.md")
        cleaned = (fb / "CLAUDE.md").read_text()
        check("RF3 — the file the human now authors carries NO stale banner",
              "GENERATED by install2.py" not in cleaned
              and "DO NOT EDIT" not in cleaned
              and f"{FENCE_ID}:start" not in cleaned
              and rfb["report"]["guidance_debannered"] == ["CLAUDE.md"],
              cleaned[:400])
        check("RF3 — the guidance BODY survives the cleaning",
              cleaned.rstrip() == basis_body.rstrip(), repr(cleaned[:200]))
        check("RF3 — a hand-authored basis is never rewritten by the cleaner",
              do_install(fb, catalog, ["fixmod/goodcomp"], ["claude"],
                         dry_run=False)["report"]["guidance_debannered"] == []
              and (fb / "CLAUDE.md").read_text() == cleaned)

        print("\n7.622 — a DRY RUN prints the report rows a real run prints")
        rr = tmp / "ws-report-rows"
        rr.mkdir()
        rr_dry = do_install(rr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                            dry_run=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_result(rr_dry)
        dry_out = buf.getvalue()
        rr_real = do_install(rr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                             dry_run=False)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_result(rr_real)
        real_out = buf.getvalue()
        check("7.622 — setup: the fixture HAS rows of both kinds to print",
              bool(rr_dry["report"]["skipped_inventory_rows"])
              and bool(rr_dry["report"]["no_realization"]),
              str(rr_dry["report"]))
        check("7.622 — every skipped-inventory row is named in the dry run",
              all(f"`{row['method']}` row {row['component']}/{row['part']}"
                  in dry_out
                  for row in rr_dry["report"]["skipped_inventory_rows"]),
              dry_out)
        check("7.622 — every no-realization row is named in the dry run",
              all(f"{row['harness']} has no realization for method "
                  f"{row['method']} ({row['component']}/{row['part']})"
                  in dry_out
                  for row in rr_dry["report"]["no_realization"]),
              dry_out)
        check("7.622 — the dry run carries the SAME row count as the real run",
              sum(1 for ln in dry_out.splitlines() if ln.startswith("  · "))
              == sum(1 for ln in real_out.splitlines()
                     if ln.startswith("  · ")),
              f"dry={dry_out}\nreal={real_out}")
        check("7.622 — planned rows read as planned, real rows as done",
              "would skip `pool` row" in dry_out
              and "would mint nothing" in dry_out
              and "skipped `pool` row" in real_out
              and "nothing minted" in real_out,
              dry_out + "\n=====\n" + real_out)
        check("7.622 — the JSON shape is untouched by the printing change",
              set(rr_dry["report"]) == set(rr_real["report"])
              and rr_dry["report"]["skipped_inventory_rows"]
              == rr_real["report"]["skipped_inventory_rows"],
              str(sorted(set(rr_dry["report"]) ^ set(rr_real["report"]))))

        print("\n7.623(b) — an interactive basis typo RE-PROMPTS")
        answers = ["CLAUDE.MD", "claude.md", "CLAUDE.md"]
        asked: list[str] = []

        def _ask(prompt: str) -> str:
            asked.append(prompt)
            return answers[len(asked) - 1]

        check("7.623b — two typos then a good answer returns the basis",
              prompt_basis(ask=_ask, tries=3) == "CLAUDE.md"
              and len(asked) == 3, str(asked))
        try:
            prompt_basis(ask=lambda _p: "CLAUDE.MD", tries=1)
            single = "no refusal"
        except Refuse as exc:
            single = exc.code
        check("7.623b — RED ARM: with no retry (the pre-fix shape) the same "
              "typo refuses",
              single == "guidance-basis-invalid", single)
        tried: list[int] = []
        try:
            prompt_basis(ask=lambda _p: tried.append(1) or "nope", tries=3)
            bounded = "no refusal"
        except Refuse as exc:
            bounded = exc.code
        check("7.623b — the retry is BOUNDED: the last try still refuses",
              bounded == "guidance-basis-invalid" and len(tried) == 3,
              f"{bounded} after {len(tried)} prompt(s)")
        check("7.623b — a blank answer still means `none`, not a retry",
              prompt_basis(ask=lambda _p: "", tries=3) == BASIS_NONE)
        try:
            resolve_basis(None, "CLAUDE.MD")
            direct = "no refusal"
        except Refuse as exc:
            direct = exc.code
        check("7.623b — NON-interactive resolve_basis is unchanged: no retry "
              "exists there", direct == "guidance-basis-invalid", direct)

        print("\nS — D15: a _skills/ folder is copied WHOLE, not thin-loaded")
        sk = tmp / "ws-skill-folder"
        sk.mkdir()
        rsk = do_install(sk, catalog, ["_hub/skills/vendored"],
                         ["claude", "codex"], dry_run=False)
        src = tree / SKILLS_DIR / "vendored"
        want_sk = {f"{root}/{member}"
                   for root in (".claude/skills/vendored",
                                ".agents/skills/vendored")
                   for member in ("SKILL.md", "LICENSE.txt",
                                  "references/deep.md", "logo.png")}
        on_disk = {q.relative_to(sk).as_posix()
                   for q in sk.rglob("*") if q.is_file()} - {STATE_REL.as_posix()}
        check("S1 — every member lands under every harness's skills dir",
              on_disk == want_sk,
              f"missing={sorted(want_sk - on_disk)} extra={sorted(on_disk - want_sk)}")
        check("S1 — __pycache__ (and its junk) is never copied",
              not any("__pycache__" in rel for rel in on_disk), str(on_disk))
        check("S2 — non-SKILL.md members are BYTE-IDENTICAL to the source",
              (sk / ".claude/skills/vendored/logo.png").read_bytes()
              == (src / "logo.png").read_bytes()
              and (sk / ".claude/skills/vendored/references/deep.md").read_text()
              == (src / "references/deep.md").read_text(),
              "a verbatim copy is not verbatim")
        check("S2 — the copied SKILL.md is the ONE file we stamp",
              MANAGED_MARK in (sk / ".claude/skills/vendored/SKILL.md").read_text()
              and (sk / ".claude/skills/vendored/SKILL.md").read_text()
              .startswith("---\nname: vendored\n")
              and MANAGED_MARK not in (sk / ".claude/skills/vendored/"
                                       "references/deep.md").read_text())
        check("S3 — the whole folder is OURS through that one marker",
              all(_is_ours(sk, rel) for rel in want_sk),
              str(sorted(rel for rel in want_sk if not _is_ours(sk, rel))))
        check("S3 — the source folder is never modified",
              MANAGED_MARK not in (src / SKILL_FILE).read_text())
        check("S4 — it is booked and reported like any other unit",
              rec_files(read_state(sk)["components"]["_hub/skills/vendored"])
              == want_sk
              and rsk["report"]["skill_folders"][0]["files"] == 4
              and "vendored" in read_state(sk)["components"]
              ["_hub/skills/vendored"]["parts"],
              str(rsk["report"]["skill_folders"]))
        check("S5 — a re-install is idempotent, binary and all",
              do_install(sk, catalog, ["_hub/skills/vendored"],
                         ["claude", "codex"], dry_run=False)["written"] == [])
        rsk2 = do_uninstall(sk, catalog, ["_hub/skills/vendored"], dry_run=False)
        check("S6 — uninstall takes the WHOLE folder and prunes the dirs",
              set(rsk2["deleted"]) == want_sk
              and not (sk / ".claude/skills/vendored").exists()
              and not (sk / ".agents/skills/vendored").exists(),
              str(sorted(set(rsk2["deleted"]) ^ want_sk)))
        # RELEASE, folder-wide: strip the one marker and the whole copy is the
        # human's — uninstall must not delete any of it.
        do_install(sk, catalog, ["_hub/skills/vendored"], ["claude"],
                   dry_run=False)
        taken = (sk / ".claude/skills/vendored/SKILL.md").read_text().replace(
            MANAGED_BANNER, "")
        (sk / ".claude/skills/vendored/SKILL.md").write_text(taken,
                                                             encoding="utf-8")
        rsk3 = do_uninstall(sk, catalog, ["_hub/skills/vendored"], dry_run=False)
        check("S7 — stripping the one marker RELEASES the whole folder",
              rsk3["deleted"] == []
              and sorted(rsk3["released"]) == sorted(
                  rel for rel in want_sk if rel.startswith(".claude/"))
              and (sk / ".claude/skills/vendored/logo.png").exists(),
              str(rsk3["released"]))

        print("\nH — _hub/<method>/<name> discovery, refusals, R6 rewrite")
        expect_hub = {
            "skill": "_hub/skills/hubskill",
            "command": "_hub/command/hubcmd",
            "rule": "_hub/rules/hubrule",
            "hook": "_hub/hook/hubhook",
            "sub-agent": "_hub/sub-agent/hubagent",
            "agents.md": "_hub/agents.md/hubguide",
            "config": "_hub/config/hubmcp",
            "path": "_hub/path/hubbin.py",
        }
        for method, cid in expect_hub.items():
            rec = catalog.get(cid) or {}
            check(f"H-discover-{method} — id {cid}",
                  rec.get("kind") == "hub" and rec.get("method") == method
                  and rec.get("module") == HUB_DIR
                  and not rec.get("hub_refusal")
                  and is_installable(rec),
                  str(rec))
        check("H-discover-path-file — suffix kept; PATH name is the part-id",
              catalog["_hub/path/hubbin.py"]["component"] == "hubbin.py")
        check("H-refuse-pool — discovered and named, not skipped",
              catalog["_hub/pool/hubpool"].get("hub_refusal")
              == "hub-pool-inexpressible"
              and not is_installable(catalog["_hub/pool/hubpool"])
              and "_hub/pool/hubpool" in data["hub_refusals"],
              str(catalog.get("_hub/pool/hubpool")))
        check("H-refuse-path-dir — discovered and named, not skipped",
              catalog["_hub/path/hubbindir"].get("hub_refusal")
              == "hub-path-directory"
              and not is_installable(catalog["_hub/path/hubbindir"])
              and "_hub/path/hubbindir" in data["hub_refusals"],
              str(catalog.get("_hub/path/hubbindir")))
        hp = tmp / "ws-hub-pool"
        hp.mkdir()
        try:
            do_install(hp, catalog, ["_hub/pool/hubpool"], ["claude"],
                       dry_run=False)
            check("H-refuse-pool-install — typed refusal", False, "no refusal")
        except Refuse as exc:
            check("H-refuse-pool-install — typed refusal",
                  exc.code == "hub-pool-inexpressible"
                  and not (hp / STATE_REL).exists(), exc.code)
        hd = tmp / "ws-hub-pathdir"
        hd.mkdir()
        try:
            do_install(hd, catalog, ["_hub/path/hubbindir"], ["claude"],
                       dry_run=False)
            check("H-refuse-path-dir-install — typed refusal", False,
                  "no refusal")
        except Refuse as exc:
            check("H-refuse-path-dir-install — typed refusal",
                  exc.code == "hub-path-directory"
                  and not (hd / STATE_REL).exists(), exc.code)
        hub_keys = {part_key(cid, catalog[cid]["component"])
                    for cid, c in catalog.items()
                    if c["module"] == HUB_DIR and is_installable(c)}
        check("H-alias — -m hub maps to module _hub (the one mapping)",
              resolve_selection(_sel(verb="add", module=["hub"]), catalog, None)
              == hub_keys
              and module_id("hub") == HUB_DIR
              and module_id("_hub") == HUB_DIR
              and module_id("core") == "core")

        hw = tmp / "ws-hub-realize"
        hw.mkdir()
        hr = do_install(hw, catalog, [
            "_hub/skills/hubskill", "_hub/command/hubcmd",
            "_hub/rules/hubrule", "_hub/sub-agent/hubagent",
            "_hub/hook/hubhook", "_hub/config/hubmcp",
            "_hub/agents.md/hubguide", "_hub/path/hubbin.py",
        ], ["claude"], dry_run=False)
        check("H-realize-skill — verbatim folder copy",
              (hw / ".claude/skills/hubskill/SKILL.md").is_file()
              and MANAGED_MARK in (hw / ".claude/skills/hubskill/SKILL.md")
              .read_text())
        check("H-realize-command — pointer/loader via MATRIX",
              (hw / ".claude/commands/hubcmd.md").is_file()
              and "Read `" in (hw / ".claude/commands/hubcmd.md").read_text())
        check("H-realize-rule — copy-verbatim + marker",
              "# HUB RULE" in (hw / ".claude/rules/hubrule.md").read_text()
              and MANAGED_MARK in (hw / ".claude/rules/hubrule.md").read_text())
        check("H-realize-sub-agent — pointer/loader via MATRIX",
              (hw / ".claude/agents/hubagent.md").is_file()
              and "Read `" in (hw / ".claude/agents/hubagent.md").read_text())
        check("H-realize-hook — shared claim, not a whole file",
              "SessionStart" in json.loads(
                  (hw / ".claude/settings.json").read_text()).get("hooks", {}))
        check("H-realize-config — MCP key claimed",
              "hubfix" in json.loads((hw / ".mcp.json").read_text())
              .get("mcpServers", {}))
        check("H-realize-path — catalogued, nothing under target, linked by part-id",
              not any(r["method"] == "path"
                      for r in hr["report"]["skipped_inventory_rows"])
              and not (hw / "hubbin.py").exists()
              and "hubbin.py" in read_state(hw)["components"]
              ["_hub/path/hubbin.py"]["parts"]
              and (bin_dir() / "hubbin.py").is_symlink()
              and (bin_dir() / "hubbin.py").resolve()
              == Path(catalog["_hub/path/hubbin.py"]["path"]).resolve())
        check("H-realize-agents.md — fragment rides the guidance report",
              any(p[0] == "hubguide"
                  for p in hr["report"].get("agents_parts") or []))

        print("\nH-rewrite — R6 _skills book key becomes _hub/skills on load")
        rw = tmp / "ws-r6-rewrite"
        rw.mkdir()
        (rw / STATE_REL).parent.mkdir(parents=True)
        legacy_four = ["claude", "codex", "opencode", "kimi"]
        three = ["claude", "codex", "opencode"]
        (rw / STATE_REL).write_text(json.dumps({
            "schema": 1, "installer": "install2.py",
            "components": {
                "_skills/vendored": {
                    "module": "_skills", "component": "vendored",
                    "harnesses": legacy_four, "files": [
                        ".claude/skills/vendored/SKILL.md"],
                    "tree": "repo", "tree_root": str(tree),
                },
                "_skills/hubskill": {
                    "module": "_skills", "component": "hubskill",
                    "harnesses": three, "files": [
                        ".claude/skills/hubskill/SKILL.md"],
                    "tree": "repo", "tree_root": str(tree),
                },
            },
        }), encoding="utf-8")
        raw_before = (rw / STATE_REL).read_text(encoding="utf-8")
        rst = read_state(rw)
        check("H-rewrite — keys move, module becomes _hub, kimi stripped",
              set(rst["components"])
              == {"_hub/skills/vendored", "_hub/skills/hubskill"}
              and rst["components"]["_hub/skills/vendored"]["module"] == HUB_DIR
              and rst["components"]["_hub/skills/vendored"]["harnesses"]
              == three
              and rst["components"]["_hub/skills/hubskill"]["harnesses"]
              == three
              and "_skills/vendored" not in rst["components"],
              str(sorted(rst["components"])))
        check("H-rewrite — file on disk unchanged until the next write",
              (rw / STATE_REL).read_text(encoding="utf-8") == raw_before)
        try:
            rrw = do_install(rw, catalog, ["_hub/skills/vendored"],
                             three, dry_run=False)
            vanished = False
        except Refuse as exc:
            rrw = None
            vanished = exc.code == "component-vanished"
            check("H-rewrite — install after rewrite", False,
                  f"{exc.code}: {exc.message}")
        if rrw is not None:
            persisted = json.loads((rw / STATE_REL).read_text(encoding="utf-8"))
            check("H-rewrite — no component-vanished; persisted under new key",
                  not vanished
                  and "_hub/skills/vendored" in persisted["components"]
                  and "_skills/vendored" not in persisted["components"]
                  and persisted["components"]["_hub/skills/vendored"]
                  ["harnesses"] == three,
                  str(sorted(persisted["components"])))

        hx = tmp / "ws-hub-coll"
        hx.mkdir()
        (hx / STATE_REL).parent.mkdir(parents=True)
        (hx / STATE_REL).write_text(json.dumps({
            "schema": 1, "installer": "install2.py",
            "components": {
                "_skills/vendored": {
                    "module": "_skills", "component": "vendored",
                    "harnesses": ["claude"], "files": []},
                "_hub/skills/vendored": {
                    "module": "_hub", "component": "vendored",
                    "harnesses": ["claude"], "files": []},
            },
        }), encoding="utf-8")
        try:
            read_state(hx)
            check("H-rewrite-collision — both keys refuse", False, "no refusal")
        except Refuse as exc:
            check("H-rewrite-collision — both keys refuse",
                  exc.code == "hub-id-collision", exc.code)

        print("\nM — D12: the marker is what says `this file is mine`")
        mk = tmp / "ws-marker"
        mk.mkdir()
        rule_rel = ".claude/rules/fixrule.md"
        (mk / rule_rel).parent.mkdir(parents=True)
        # An UNBOOKED file at a planned path, carrying OUR marker: provably a
        # run of ours (a lost book, a copied workspace) — adopted, not refused.
        (mk / rule_rel).write_text(MANAGED_BANNER + "# a stale body\n",
                                   encoding="utf-8")
        resm = do_install(mk, catalog, ["fixmod/goodcomp"], ["claude"],
                          dry_run=False)
        check("M1 — a marked file outside the book is ADOPTED and regenerated",
              resm["adopted"] == [rule_rel]
              and "a stale body" not in (mk / rule_rel).read_text()
              and rule_rel in rec_files(read_state(mk)["components"][
                  "fixmod/goodcomp"]),
              str(resm.get("adopted")))

        # The other side: the same path, hand-authored, no marker → refused.
        mk2 = tmp / "ws-marker-hand"
        (mk2 / ".claude/rules").mkdir(parents=True)
        hand_rule = "# my own rule\n"
        (mk2 / rule_rel).write_text(hand_rule, encoding="utf-8")
        try:
            do_install(mk2, catalog, ["fixmod/goodcomp"], ["claude"],
                       dry_run=False)
            check("M2 — an UNMARKED file at a planned path refuses", False,
                  "no refusal raised — it was overwritten")
        except Refuse as exc:
            check("M2 — an UNMARKED file at a planned path refuses",
                  exc.code == "collision"
                  and (mk2 / rule_rel).read_text() == hand_rule, exc.code)

        # RELEASE — a booked file a human took over (marker gone) is dropped
        # from the book, never deleted.
        (mk / rule_rel).write_text("# I own this now\n", encoding="utf-8")
        resm2 = do_uninstall(mk, catalog, ["fixmod/goodcomp"], dry_run=False)
        check("M3 — a booked file whose marker is gone is RELEASED, not deleted",
              resm2["released"] == [rule_rel]
              and (mk / rule_rel).read_text() == "# I own this now\n"
              and rule_rel not in resm2["deleted"], str(resm2["released"]))

        # MIGRATION — files a pre-marker run minted under the `rbtv2-` prefix
        # carry no marker at all; the legacy-name clause keeps them ours, so
        # the first unprefixed run cleans them up instead of orphaning them.
        mk3 = tmp / "ws-legacy"
        mk3.mkdir()
        do_install(mk3, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
        legacy_rel = f".claude/rules/{LEGACY_PREFIX}fixrule.md"
        (mk3 / legacy_rel).write_text("# THE RULE\n\nAlways do the thing.\n",
                                      encoding="utf-8")
        st3 = read_state(mk3)
        st3["components"]["fixmod/goodcomp"]["files"] = (
            sorted(rec_files(st3["components"]["fixmod/goodcomp"]))
            + [legacy_rel])
        write_state(mk3, st3)
        resm3 = do_install(mk3, catalog, ["fixmod/goodcomp"], ["claude"],
                           dry_run=False)
        check("M4 — yesterday's rbtv2- file is deleted as stale, not orphaned",
              resm3["deleted"] == [legacy_rel]
              and not (mk3 / legacy_rel).exists()
              and resm3["released"] == [], str(resm3["deleted"]))

        print("\nG — D14: the .gitignore block keeps our artifacts out of git")
        gi = tmp / "ws-gitignore"
        gi.mkdir()
        (gi / ".git").mkdir()
        (gi / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        (gi / ".gitignore").write_text("# theirs\nnode_modules/\n",
                                       encoding="utf-8")
        rgi = do_install(gi, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                         dry_run=False, guidance_basis="CLAUDE.md")
        body = (gi / ".gitignore").read_text()
        booked = sorted(rec_files(read_state(gi)["components"]["fixmod/goodcomp"]))
        check("G1 — every per-component artifact and the book are listed",
              all(rel in body for rel in booked)
              and STATE_REL.as_posix() in body
              and rgi["report"]["gitignore"]["count"] == len(booked) + 1,
              str(rgi["report"]["gitignore"]))
        check("G1 — the guidance mirror is NOT listed (workspace content)",
              "\nAGENTS.md" not in body, body)
        check("G1 — the foreign lines survive, and the block is fenced",
              "node_modules/" in body and f"# {FENCE_ID}:start" in body
              and f"# {FENCE_ID}:end" in body, body)
        check("G1 — the claim is booked like any other shared-file claim",
              _claim_id(".gitignore", None)
              in read_state(gi)["shared_claims"],
              str(read_state(gi)["shared_claims"]))
        check("G2 — a re-run is idempotent, block and all",
              do_install(gi, catalog, ["fixmod/goodcomp"],
                         ["claude", "codex"], dry_run=False)["written"] == []
              and (gi / ".gitignore").read_text() == body)
        # A shrinking set shrinks the block — the whole point of D14.
        rgi2 = do_install(gi, catalog, ["fixmod/goodcomp"], ["claude"],
                          dry_run=False)
        check("G3 — re-install with fewer harnesses MERGES, does not drop",
              ".agents/behavior-rules/fixrule.md"
              in (gi / ".gitignore").read_text()
              and ".claude/rules/fixrule.md" in (gi / ".gitignore").read_text()
              and rgi2["deleted"] == [],
              str(rgi2["deleted"]))
        do_uninstall(gi, catalog, ["fixmod/goodcomp"], dry_run=False)
        check("G4 — the last uninstall takes the block, leaves their lines",
              (gi / ".gitignore").read_text() == "# theirs\nnode_modules/\n",
              (gi / ".gitignore").read_text())

        ng = tmp / "ws-not-a-repo"
        ng.mkdir()
        rng = do_install(ng, catalog, ["fixmod/goodcomp"], ["claude"],
                         dry_run=False)
        check("G5 — off a git repo, no .gitignore is ever minted",
              not (ng / ".gitignore").exists()
              and rng["report"]["gitignore"] == {"claimed": False,
                                                 "reason": "not a git repo"},
              str(rng["report"]["gitignore"]))

        gf = tmp / "ws-foreign-fence"
        gf.mkdir()
        (gf / ".git").mkdir()
        foreign = f"# {FENCE_ID}:start\nsomething-else\n# {FENCE_ID}:end\n"
        (gf / ".gitignore").write_text(foreign, encoding="utf-8")
        try:
            do_install(gf, catalog, ["fixmod/goodcomp"], ["claude"],
                       dry_run=False)
            check("G6 — a foreign rbtv2 fence refuses", False, "no refusal")
        except Refuse as exc:
            check("G6 — a foreign rbtv2 fence refuses",
                  exc.code == "collision"
                  and ".gitignore" in exc.message
                  and (gf / ".gitignore").read_text() == foreign, exc.code)

        gt = tmp / "ws-tracked"
        gt.mkdir()
        import subprocess
        if subprocess.run(["git", "-C", str(gt), "init", "-q"],
                          capture_output=True).returncode == 0:
            (gt / ".claude" / "rules").mkdir(parents=True)
            (gt / ".claude/rules/fixrule.md").write_text("theirs\n",
                                                         encoding="utf-8")
            subprocess.run(["git", "-C", str(gt), "add",
                            ".claude/rules/fixrule.md"], capture_output=True)
            (gt / ".claude/rules/fixrule.md").unlink()
            rgt = do_install(gt, catalog, ["fixmod/goodcomp"], ["claude"],
                             dry_run=False)
            check("G7 — a path git ALREADY TRACKS is reported, not silently "
                  "ignored",
                  rgt["report"]["gitignore"]["tracked"]
                  == [".claude/rules/fixrule.md"],
                  str(rgt["report"]["gitignore"]))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                print_result(rgt)
            check("G7 — and the human is told, with the fix",
                  "ALREADY TRACKED" in buf.getvalue()
                  and "git rm --cached" in buf.getvalue(), buf.getvalue()[-400:])

        print("\nV — a VANISHED booked component is removable without the tree")
        vn = tmp / "ws-vanished"
        vn.mkdir()
        do_install(vn, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
        gone_rel = ".claude/rules/goner.md"
        (vn / gone_rel).write_text(MANAGED_BANNER + "# from a folder now gone\n",
                                   encoding="utf-8")
        stv = read_state(vn)
        stv["components"]["gonemod/gonecomp"] = {
            "tree": "mirror", "tree_root": str(vn / ".rbtv/mirror"),
            "module": "gonemod", "component": "gonecomp",
            "harnesses": ["claude"], "files": [gone_rel]}
        write_state(vn, stv)
        try:
            do_install(vn, catalog, ["fixmod/goodcomp"], ["claude"],
                       dry_run=False)
            check("V1 — a vanished component blocks the run", False,
                  "no refusal raised")
        except Refuse as exc:
            check("V1 — a vanished component blocks the run",
                  exc.code == "component-vanished", exc.code)
            check("V1 — and the refusal names a door that actually opens",
                  "uninstall --component gonemod/gonecomp" in exc.message,
                  exc.message)
        try:
            resolve_selection(_sel(verb="add", component=["gonemod/gonecomp"]),
                              catalog, None)
            catalog_only = "no refusal"
        except Refuse as exc:
            catalog_only = exc.code
        check("V2 — the trees alone cannot name it (that was the trap)",
              catalog_only == "component-unknown", catalog_only)
        check("V2 — the BOOK can",
              resolve_selection(
                  _sel(verb="rm", component=["gonemod/gonecomp"]),
                  catalog, read_state(vn)["components"])
              == {"gonemod/gonecomp#gonecomp"})
        resv = do_uninstall(vn, catalog, ["gonemod/gonecomp"], dry_run=False)
        check("V3 — uninstalling it needs no tree, and takes its file",
              resv["deleted"] == [gone_rel] and not (vn / gone_rel).exists()
              and "gonemod/gonecomp" not in read_state(vn)["components"],
              str(resv["deleted"]))
        check("V3 — the target is unblocked: the next install runs clean",
              do_install(vn, catalog, ["fixmod/goodcomp"], ["claude"],
                         dry_run=False)["written"] == [])

        print("\nP — part-level install / remove (schema 2)")
        pdup = tmp / "ws-dup"
        pdup.mkdir()
        try:
            do_install(pdup, catalog, ["fixmod/dupcomp"], ["claude"],
                       dry_run=False)
            check("D-dup — duplicate part-id refuses", False, "no refusal")
        except Refuse as exc:
            check("D-dup — duplicate part-id refuses",
                  exc.code == "part-id-duplicate", exc.code)
            check("D-dup — zero files written",
                  not any(pdup.rglob("*.md")) and not (pdup / STATE_REL).exists())

        try:
            _select_parts(catalog["fixmod/goodcomp"], None, ["no-such-part"])
            pu = "no refusal"
        except Refuse as exc:
            pu = exc.code
        except Exception as exc:
            pu = type(exc).__name__
        check("P-unknown — unknown part-id refuses",
              pu == "part-unknown", pu)

        pws = tmp / "ws-parts"
        pws.mkdir()
        rp = do_install(pws, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                        dry_run=False, parts=["fixskill"])
        pdisk = {q.relative_to(pws).as_posix()
                 for q in pws.rglob("*") if q.is_file()}
        check("P-add — only the requested part's files land",
              ".claude/skills/fixskill/SKILL.md" in pdisk
              and ".claude/rules/fixrule.md" not in pdisk
              and not (pws / ".mcp.json").exists(),
              str(sorted(pdisk)))
        prec = read_state(pws)["components"]["fixmod/goodcomp"]
        check("P-add — book carries only that part",
              set(prec["parts"]) == {"fixskill"}, str(sorted(prec["parts"])))
        rp2 = do_install(pws, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                         dry_run=False)
        check("P-add — re-add with no parts list refreshes booked, does not fill",
              set(read_state(pws)["components"]["fixmod/goodcomp"]["parts"])
              == {"fixskill"}
              and not (pws / ".claude/rules/fixrule.md").exists()
              and rp2["written"] == [],
              str(sorted(read_state(pws)["components"]["fixmod/goodcomp"]["parts"])))
        do_install(pws, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False, parts=["fixrule", "fixmcp", "fixhook"])
        check("P-add — later add MERGES parts",
              set(read_state(pws)["components"]["fixmod/goodcomp"]["parts"])
              == {"fixskill", "fixrule", "fixmcp", "fixhook"})

        print("\nC — part-level claim release")
        mcp_before = json.loads((pws / ".mcp.json").read_text())
        check("C-setup — MCP key is present before the part rm",
              "fix" in mcp_before.get("mcpServers", {}), str(mcp_before))
        do_uninstall(pws, catalog, ["fixmod/goodcomp"], dry_run=False,
                     parts=["fixmcp"])
        pst = read_state(pws)
        check("C-leak — rm of the config part releases the MCP key",
              (not (pws / ".mcp.json").exists()
               or "fix" not in json.loads(
                   (pws / ".mcp.json").read_text()).get("mcpServers", {}))
              and _claim_id(".mcp.json", ["mcpServers", "fix"])
              not in pst["shared_claims"],
              str(pst["shared_claims"]))
        check("C-leak — sibling hook claim stays, skill file stays",
              (pws / ".claude/skills/fixskill/SKILL.md").is_file()
              and _claim_id(".claude/settings.json", ["hooks", "PreToolUse"])
              in pst["shared_claims"]
              and "fixmcp" not in pst["components"]["fixmod/goodcomp"]["parts"]
              and "fixhook" in pst["components"]["fixmod/goodcomp"]["parts"])
        hook_claims = pst["components"]["fixmod/goodcomp"]["parts"]["fixhook"].get(
            "claims") or []
        check("C-leak — claims are tagged on the part that minted them",
              any("hooks" in c for c in hook_claims), str(hook_claims))

        do_uninstall(pws, catalog, ["fixmod/goodcomp"], dry_run=False,
                     parts=["fixskill", "fixrule", "fixhook"])
        check("P-rm — removing the last parts unbooks the component",
              "fixmod/goodcomp" not in (read_state(pws).get("components") or {})
              or not (pws / STATE_REL).exists())

        print("\nC2 — vanished-component part rm still releases claims")
        pv = tmp / "ws-vanish-part"
        pv.mkdir()
        do_install(pv, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
        gone_cat = {k: v for k, v in catalog.items() if k != "fixmod/goodcomp"}
        do_uninstall(pv, gone_cat, ["fixmod/goodcomp"], dry_run=False,
                     parts=["fixmcp"])
        pvst = read_state(pv)
        check("C2 — vanished folder, rm config part: MCP key gone, rest stays",
              (not (pv / ".mcp.json").exists()
               or "fix" not in json.loads(
                   (pv / ".mcp.json").read_text()).get("mcpServers", {}))
              and (pv / ".claude/skills/fixskill/SKILL.md").is_file()
              and "fixmcp" not in pvst["components"]["fixmod/goodcomp"]["parts"]
              and "fixskill" in pvst["components"]["fixmod/goodcomp"]["parts"],
              str(sorted(pvst["components"]["fixmod/goodcomp"]["parts"])))
        check("C2-rebuild — vanished part-rm keeps sibling hook claim",
              _claim_id(".claude/settings.json", ["hooks", "PreToolUse"])
              in pvst["shared_claims"],
              str(pvst["shared_claims"]))

        vu = tmp / "ws-v1-part"
        vu.mkdir()
        do_install(vu, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
        st = read_state(vu)
        rec = st["components"]["fixmod/goodcomp"]
        rec.pop("parts", None)
        rec["files"] = sorted(rec_files(rec)) if "files" not in rec else rec["files"]
        write_state(vu, st)
        gone_vu = {k: v for k, v in catalog.items() if k != "fixmod/goodcomp"}
        try:
            do_uninstall(vu, gone_vu, ["fixmod/goodcomp"], dry_run=False,
                         parts=["fixskill"])
            check("P-unbooked-v1 — vanished v1 part-rm refuses", False,
                  "no refusal")
        except Refuse as exc:
            check("P-unbooked-v1 — vanished v1 part-rm refuses",
                  exc.code == "part-unbooked", exc.code)

        print("\nU-live — v1→v2 upgrade against a COPY of the real book")
        live_book = Path("/home/henri/ht-wkdir/second-brain") / STATE_REL
        if live_book.is_file():
            before = live_book.read_bytes()
            dest_root = tmp / "ws-live-upgrade"
            dest = dest_root / STATE_REL
            dest.parent.mkdir(parents=True)
            dest.write_bytes(before)
            raw = json.loads(dest.read_text(encoding="utf-8"))
            old_claims = list(raw.get("shared_claims") or [])
            src_harnesses = {
                cid: list(rec.get("harnesses") or [])
                for cid, rec in raw["components"].items()}
            src_parts = {
                cid: set((rec.get("parts") or {}))
                for cid, rec in raw["components"].items()}
            src_files = {cid: rec_files(rec)
                         for cid, rec in raw["components"].items()}
            rewrite_legacy_skill_ids(raw)
            old_ids = set(raw["components"])
            vault = live_book.parents[2]
            live_cat, _ = scan_all(vault / ".rbtv" / "mirror",
                                   Path(__file__).resolve().parent)
            upgraded = upgrade_book(raw, catalog_parts_map(live_cat))
            write_state(dest_root, upgraded)
            got = json.loads(dest.read_text(encoding="utf-8"))
            check("U-live live file untouched",
                  live_book.read_bytes() == before)
            check("U-live schema 2, prefix gone",
                  got["schema"] == SCHEMA and "prefix" not in got)
            present = [cid for cid in old_ids if cid in live_cat]
            check("U-live still-present cids keep their parts maps",
                  present
                  and all("parts" in got["components"][cid]
                          and set(got["components"][cid]["parts"])
                          == src_parts.get(cid, set())
                          for cid in present),
                  str(present[:5]))
            check("U-live shared_claims unchanged",
                  got["shared_claims"] == old_claims)
            dropped = old_ids - set(got["components"])
            check("U-live empty uncatalogued already flushed (no leftover drop)",
                  dropped == set(),
                  str(sorted(dropped)))
            try:
                plan_files(got["components"], live_cat)
                live_refuse = None
            except Refuse as exc:
                live_refuse = f"{exc.code}: {exc.message}"
            check("U-live plan_files refuses nothing after the drop",
                  live_refuse is None, str(live_refuse))
            check("U-live known_files dual-read equals booked files ∪ guidance",
                  known_files(got) == set().union(*src_files.values())
                  | set(raw.get("guidance_files") or []))
            legacy_four = ["claude", "codex", "opencode", "kimi"]
            three = ["claude", "codex", "opencode"]
            hub_skills = {
                cid: hs for cid, hs in src_harnesses.items()
                if cid.startswith(f"{HUB_DIR}/{HUB_ID_FOLDER['skill']}/")}
            check("U-live every booked record listed kimi; upgrade leaves the three",
                  hub_skills
                  and all(hs == legacy_four for hs in src_harnesses.values())
                  and all(got["components"][cid]["harnesses"] == three
                          and "kimi" not in got["components"][cid]["harnesses"]
                          for cid in got["components"])
                  and all(got["components"][cid].get("module") == HUB_DIR
                          for cid in hub_skills)
                  and len(got["components"]) == len(src_harnesses),
                  str({cid: got["components"].get(cid, {}).get("harnesses")
                       for cid in list(hub_skills)[:3]}))
        else:
            check("U-live live book present", False, str(live_book))

        print("\nCLI — parser, selectors, index, R7 guard")
        for verb in ("add", "rm", "ls", "li", "dupe-artifacts", "doctor",
                     "selftest", "interactive"):
            argv = [verb] if verb != "add" else ["add", "-A"]
            ns = build_parser().parse_args(argv)
            check(f"CLI-reach-{verb}", ns.verb == verb
                  and verb in _HANDLERS, ns.verb)
        empty = tmp / "ws-cli-empty"
        empty.mkdir()
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            rc_ls = cmd_ls(build_parser().parse_args(["ls"]), empty, catalog, [])
            rc_li = cmd_li(build_parser().parse_args(["li"]), empty, catalog, [])
            rc_dupe = cmd_dupe(build_parser().parse_args(["dupe-artifacts"]),
                               empty, catalog, [])
            rc_add = cmd_add(
                build_parser().parse_args(["add", "-c", "fixmod/goodcomp",
                                           "--dry-run"]),
                empty, catalog, [])
            try:
                cmd_rm(build_parser().parse_args(
                    ["rm", "-c", "fixmod/goodcomp", "--dry-run"]),
                       empty, catalog, [])
                rc_rm = "ok"
            except Refuse as exc:
                rc_rm = exc.code
            rc_doc = cmd_doctor(None, empty, catalog, [])
        check("CLI-reach-handler-ls", rc_ls == 0)
        check("CLI-reach-handler-li", rc_li == 0)
        check("CLI-reach-handler-dupe", rc_dupe == 0)
        check("CLI-reach-handler-add", rc_add == 0)
        check("CLI-reach-handler-rm", rc_rm == "not-installed", str(rc_rm))
        check("CLI-reach-handler-doctor", rc_doc == 0, str(rc_doc))

        for flag, meth in (("-xs", "skill"), ("-xr", "rule"),
                           ("-xc", "command"), ("-xsa", "sub-agent")):
            a = build_parser().parse_args(["add", flag])
            b = build_parser().parse_args(["add", "-x", meth])
            check(f"CLI-alias-{flag}", a.method == b.method == [meth],
                  f"{a.method} vs {b.method}")

        SEL_CAT = {
            "core/communication": {
                "module": "core", "component": "communication",
                "manifest": True, "kind": "component", "rows": [
                    {"part-id": "audio", "method": "path"},
                    {"part-id": "plain-language", "method": "rule"},
                    {"part-id": "non-technical-user", "method": "rule"},
                    {"part-id": "concise-chat", "method": "rule"},
                    {"part-id": "audio-aware", "method": "skill"}]},
            "core/sub-agents": {
                "module": "core", "component": "sub-agents",
                "manifest": True, "kind": "component", "rows": [
                    {"part-id": "cast", "method": "path"},
                    {"part-id": "sub-agents", "method": "skill"},
                    {"part-id": "swarm", "method": "skill"},
                    {"part-id": "panel", "method": "skill"}]},
            "web/browse": {
                "module": "web", "component": "browse",
                "manifest": True, "kind": "component", "rows": [
                    {"part-id": "browse", "method": "skill"},
                    {"part-id": "chrome-devtools", "method": "config"}]},
            "web/capture": {
                "module": "web", "component": "capture",
                "manifest": True, "kind": "component", "rows": [
                    {"part-id": "capture", "method": "skill"}]},
            "_hub/skills/ponytail": {
                "module": "_hub", "component": "ponytail",
                "manifest": False, "kind": "hub"},
            "badmod/silent": {
                "module": "badmod", "component": "silent",
                "manifest": False, "kind": "component"},
        }
        SEL_BOOK = {
            "core/communication": {
                "module": "core", "component": "communication",
                "parts": {"audio-aware": {"method": "skill"},
                          "plain-language": {"method": "rule"}}},
            "web/browse": {"module": "web", "component": "browse"},
            "ghost/gone": {"module": "ghost", "component": "gone"},
        }

        def R(verb="add", book=None, **kw):
            return resolve_selection(_sel(verb=verb, **kw), SEL_CAT, book)

        check("SEL-and",
              R(module=["core"], method=["skill"]) == {
                  "core/communication#audio-aware",
                  "core/sub-agents#sub-agents",
                  "core/sub-agents#swarm",
                  "core/sub-agents#panel"})
        check("SEL-or",
              R(component=["core/communication", "web/browse"],
                method=["skill", "rule"]) == {
                  "core/communication#plain-language",
                  "core/communication#non-technical-user",
                  "core/communication#concise-chat",
                  "core/communication#audio-aware",
                  "web/browse#browse"})
        check("SEL-exclude",
              R(all=True, exclude_module=["core"], method=["skill"]) == {
                  "web/browse#browse",
                  "web/capture#capture",
                  "_hub/skills/ponytail#ponytail"})
        # -nx must SUBTRACT, not merely trigger the confirmation prompt.
        # Without this arm, neutering the method-exclusion filter left the whole
        # suite green: N-confirm asserts the prompt fired and that answering "n"
        # changed nothing, which passes whether or not the filter ever ran.
        _all_parts = R(all=True)
        _no_skill = R(all=True, exclude_method=["skill"])
        check("SEL-exclude-method — -nx subtracts the method",
              _no_skill < _all_parts
              and "web/browse#browse" not in _no_skill
              and "_hub/skills/ponytail#ponytail" not in _no_skill
              and "core/communication#plain-language" in _no_skill,
              f"kept={sorted(_no_skill - _all_parts)} "
              f"dropped={sorted(_all_parts - _no_skill)}")
        _all = R(all=True)
        _no_browse = R(all=True, exclude_component=["web/browse"])
        check("SEL-exclude-component — -nc subtracts the component",
              _no_browse < _all
              and "web/browse#browse" not in _no_browse
              and "web/browse#chrome-devtools" not in _no_browse
              and "core/communication#audio-aware" in _no_browse,
              f"dropped={sorted(_all - _no_browse)}")
        check("SEL-rm-booked",
              R(verb="rm", book=SEL_BOOK, component=["core/communication"])
              == {"core/communication#audio-aware",
                  "core/communication#plain-language"})
        try:
            R(component=["no/comp"])
            unk = "no refusal"
        except Refuse as exc:
            unk = exc.code
        check("SEL-refuse-unknown", unk == "component-unknown", unk)
        try:
            R(module=["core"], component=["web/browse"])
            empty_and = "no refusal"
        except Refuse as exc:
            empty_and = exc.code
        check("SEL-refuse-empty-and", empty_and == "selection-empty", empty_and)
        try:
            R(verb="rm", book=SEL_BOOK, component=["web/capture"])
            not_in = "no refusal"
        except Refuse as exc:
            not_in = exc.code
        check("SEL-refuse-not-installed", not_in == "not-installed", not_in)

        idx_ws = tmp / "ws-index"
        idx_ws.mkdir()
        write_index(idx_ws, SEL_CAT)
        other = dict(SEL_CAT)
        other["zz/extra"] = {
            "module": "zz", "component": "extra", "manifest": True,
            "kind": "component",
            "rows": [{"part-id": "x", "method": "skill"}]}
        try:
            resolve_selection(
                _sel(verb="add", component=["1"], index=read_index(idx_ws)),
                other, None)
            stale = "no refusal"
        except Refuse as exc:
            stale = exc.code
        check("index-stale", stale == "index-stale", stale)

        try:
            resolve_selection(_sel(verb="add", component=["1"]), SEL_CAT, None)
            im = "no refusal"
        except Refuse as exc:
            im = exc.code
        except Exception as exc:
            im = type(exc).__name__
        check("index-missing", im == "index-missing", im)

        idx = write_index(idx_ws, SEL_CAT)
        try:
            resolve_selection(
                _sel(verb="add", component=["999"], index=idx), SEL_CAT, None)
            iu = "no refusal"
        except Refuse as exc:
            iu = exc.code
        except Exception as exc:
            iu = type(exc).__name__
        check("index-unknown", iu == "index-unknown", iu)

        try:
            resolve_selection(
                _sel(verb="add", component=["1"], index=idx), SEL_CAT, None)
            ik = "no refusal"
        except Refuse as exc:
            ik = exc.code
        except Exception as exc:
            ik = type(exc).__name__
        check("index-kind-mismatch — slot 1 is module, not component",
              ik == "index-kind-mismatch", ik)

        nws = tmp / "ws-nconfirm"
        nws.mkdir()
        do_install(nws, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
        book_before = (nws / STATE_REL).read_bytes()
        skill_p = nws / ".claude/skills/fixskill/SKILL.md"
        rule_p = nws / ".claude/rules/fixrule.md"
        asked: list[str] = []

        def _say_n(prompt: str) -> str:
            asked.append(prompt)
            return "n"

        with contextlib.redirect_stdout(io.StringIO()):
            rc_n = cmd_rm(
                build_parser().parse_args(
                    ["rm", "-A", "-nx", "skill"]),
                nws, catalog, [], ask=_say_n)
        check("N-confirm-n — disk AND book untouched",
              rc_n == 0 and asked
              and (nws / STATE_REL).read_bytes() == book_before
              and skill_p.is_file() and rule_p.is_file(),
              f"rc={rc_n} asked={asked}")

        asked.clear()

        def _boom(prompt: str) -> str:
            asked.append(prompt)
            raise AssertionError("dry-run must not ask")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_dry = cmd_rm(
                build_parser().parse_args(
                    ["rm", "--dry-run", "-A", "-nx", "skill"]),
                nws, catalog, [], ask=_boom)
        check("N-dry-run — prints and never asks",
              rc_dry == 0 and not asked
              and "would remove" in buf.getvalue()
              and (nws / STATE_REL).read_bytes() == book_before
              and skill_p.is_file(),
              f"rc={rc_dry} asked={asked} out={buf.getvalue()[:200]!r}")

        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            rc_usage = main(["add", "--target", str(empty)])
            rc_refuse = main(["add", "--target", str(empty), "-c", "no/comp"])
        check("CLI-usage-exit-2", rc_usage == 2, str(rc_usage))
        check("CLI-refuse-exit-1", rc_refuse == 1, str(rc_refuse))

        print("\nL — PATH links (part-id name, book-aware, rebound bindir)")

        def _lsnap(root: Path) -> set[str]:
            if not root.exists():
                return set()
            return {p.relative_to(root).as_posix()
                    for p in root.rglob("*")
                    if p.is_file() or p.is_symlink()}

        def _lcomp(root: Path, mod: str, name: str, pid: str, entry: str,
                   body: str = "print(1)\n") -> dict[str, dict]:
            cdir = root / mod / name
            cdir.mkdir(parents=True)
            dest = cdir / Path(entry)
            if not str(entry).startswith(WS_PREFIX):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(body, encoding="utf-8")
            (cdir / EXPOSURE_NAME).write_text(
                "part-id,part-kind,method,rbtv-cli,entry-point,description,"
                "write-roots\n"
                f"{pid},tool,path,,{entry},,\n", encoding="utf-8")
            cat, _ = scan_all(tmp / "no-mirror-l", root)
            return cat

        lsrc = tmp / "lsrc"
        lws = tmp / "ws-path-add"
        lws.mkdir()
        lcat = _lcomp(lsrc, "lmod", "ladd", "ladd-bin", "impl.py")
        before_home_rc = _RUNTIME["rc"].exists()
        lr = do_install(lws, lcat, ["lmod/ladd"], ["claude"], dry_run=False)
        check("L-add — link on add, name is the part-id not the basename",
              (bin_dir() / "ladd-bin").is_symlink()
              and not (bin_dir() / "impl.py").exists()
              and (bin_dir() / "ladd-bin").resolve()
              == (lsrc / "lmod/ladd/impl.py").resolve()
              and not (lws / "ladd-bin").exists()
              and read_state(lws)["components"]["lmod/ladd"]["path_links"]
              == ["ladd-bin"]
              and "ladd-bin" in (lr["report"].get("path") or {}).get(
                  "linked", []),
              str(lr["report"].get("path")))
        check("L-no-flag — shell-startup append does not happen without "
              "--write-path",
              not before_home_rc and not Path(_RUNTIME["rc"]).exists())

        do_uninstall(lws, lcat, ["lmod/ladd"], dry_run=False)
        check("L-rm — unlink on rm; directory kept if anything else remains",
              not (bin_dir() / "ladd-bin").exists()
              and bin_dir().is_dir(),
              str(list(bin_dir().iterdir()) if bin_dir().is_dir() else None))

        cws = tmp / "ws-path-coll"
        cws.mkdir()
        csrc = tmp / "csrc"
        ccat = _lcomp(csrc, "cmod", "ccoll", "hitfile", "x.py")
        bin_dir().mkdir(parents=True, exist_ok=True)
        (bin_dir() / "hitfile").write_text("not a symlink\n", encoding="utf-8")
        snap_c, snap_b = _lsnap(cws), _lsnap(bin_dir())
        try:
            do_install(cws, ccat, ["cmod/ccoll"], ["claude"], dry_run=False)
            check("L-collision — path-collision on a regular file", False,
                  "no refusal")
        except Refuse as exc:
            check("L-collision — path-collision on a regular file",
                  exc.code == "path-collision"
                  and _lsnap(cws) == snap_c
                  and _lsnap(bin_dir()) == snap_b
                  and not (cws / STATE_REL).exists()
                  and (bin_dir() / "hitfile").is_file()
                  and not (bin_dir() / "hitfile").is_symlink(),
                  exc.code)
        (bin_dir() / "hitfile").unlink()

        stranger = bin_dir() / "unbooked-stranger"
        (tmp / "stranger-tgt").write_text("x\n", encoding="utf-8")
        stranger.symlink_to(tmp / "stranger-tgt")
        uws = tmp / "ws-path-unbooked"
        uws.mkdir()
        do_install(uws, lcat, ["lmod/ladd"], ["claude"], dry_run=False)
        check("L-unbooked — an unbooked symlink is left untouched",
              stranger.is_symlink()
              and stranger.resolve() == (tmp / "stranger-tgt").resolve()
              and "unbooked-stranger" not in
              (read_state(uws)["components"]["lmod/ladd"].get("path_links")
               or []))
        do_uninstall(uws, lcat, ["lmod/ladd"], dry_run=False)
        check("L-unbooked-survives-rm — still there after we unlink ours",
              stranger.is_symlink() and bin_dir().is_dir())

        # unlink_one must REFUSE a non-symlink sitting at a booked name rather
        # than delete it. Without this arm, neutering that refusal left the suite
        # green: L-collision covers the PRE-WRITE gate on add, and nothing covered
        # the REMOVE path — the destructive one, where a user's real file has
        # replaced a link we once booked.
        usurper = bin_dir() / "usurper"
        bin_dir().mkdir(parents=True, exist_ok=True)
        usurper.write_text("a real file, not ours\n", encoding="utf-8")
        try:
            unlink_one(bin_dir(), "usurper", dry=False)
            ucode = "no refusal"
        except Refuse as exc:
            ucode = exc.code
        check("L-unlink-refuses-regular-file — a booked name now holding a real "
              "file is never deleted",
              ucode == "path-collision"
              and usurper.is_file()
              and not usurper.is_symlink()
              and usurper.read_text() == "a real file, not ours\n",
              f"code={ucode} exists={usurper.exists()}")
        usurper.unlink()

        bindir = bin_dir()
        bindir.mkdir(parents=True, exist_ok=True)
        victim = bindir / "gate-drop"
        victim.write_text("real file\n", encoding="utf-8")
        try:
            gate_path_links(bindir, {}, {"gate-drop"})
            check("L-gate-drop-refuses-regular", False, "no refusal")
        except Refuse as exc:
            check("L-gate-drop-refuses-regular",
                  exc.code == "path-collision" and victim.is_file()
                  and victim.read_text() == "real file\n", exc.code)
        victim.unlink()

        n1 = tmp / "n1src"
        n2 = tmp / "n2src"
        nws = tmp / "ws-path-twoname"
        nws.mkdir()
        cat1 = _lcomp(n1, "amod", "acomp", "samename", "a.py", "A\n")
        cat2 = _lcomp(n2, "bmod", "bcomp", "samename", "b.py", "B\n")
        both = {**cat1, **cat2}
        snap_n, snap_nb = _lsnap(nws), _lsnap(bin_dir())
        try:
            do_install(nws, both, ["amod/acomp", "bmod/bcomp"], ["claude"],
                       dry_run=False)
            check("L-name-collision — two components, one name", False,
                  "no refusal")
        except Refuse as exc:
            check("L-name-collision — two components, one name",
                  exc.code == "path-name-collision"
                  and _lsnap(nws) == snap_n
                  and _lsnap(bin_dir()) == snap_nb
                  and not (nws / STATE_REL).exists(),
                  exc.code)

        wsrc = tmp / "wsrc"
        wws = tmp / "ws-path-ws"
        wws.mkdir()
        (wws / "tools").mkdir()
        (wws / "tools" / "from-ws.py").write_text("print('ws')\n",
                                                  encoding="utf-8")
        wcat = _lcomp(wsrc, "wmod", "wcomp", "wsbin", "ws:tools/from-ws.py")
        wr = do_install(wws, wcat, ["wmod/wcomp"], ["claude"], dry_run=False)
        check("L-ws — ws: entry-point resolves workspace-root-relative",
              (bin_dir() / "wsbin").is_symlink()
              and (bin_dir() / "wsbin").resolve()
              == (wws / "tools/from-ws.py").resolve()
              and not (wsrc / "wmod/wcomp" / "ws:tools").exists(),
              str(wr["report"].get("path")))
        do_uninstall(wws, wcat, ["wmod/wcomp"], dry_run=False)

        esrc = tmp / "esrc"
        ews = tmp / "ws-path-esc"
        ews.mkdir()
        ecat = _lcomp(esrc, "emod", "ecomp", "escbin", "ws:../secret.py")
        (tmp / "secret.py").write_text("nope\n", encoding="utf-8")
        snap_e = _lsnap(ews)
        try:
            do_install(ews, ecat, ["emod/ecomp"], ["claude"], dry_run=False)
            check("L-escape — .. refuse", False, "no refusal")
        except Refuse as exc:
            check("L-escape — .. refuse",
                  exc.code == "entry-point-escape"
                  and _lsnap(ews) == snap_e
                  and not (ews / STATE_REL).exists()
                  and not (bin_dir() / "escbin").exists(),
                  exc.code)

        fws = tmp / "ws-path-flag"
        fws.mkdir()
        do_install(fws, lcat, ["lmod/ladd"], ["claude"], dry_run=False,
                   write_path=True)
        rc_txt = Path(_RUNTIME["rc"]).read_text(encoding="utf-8") \
            if Path(_RUNTIME["rc"]).is_file() else ""
        check("L-flag — --write-path appends a fenced bootstrap block",
              PATH_FENCE_START in rc_txt and PATH_BOOTSTRAP in rc_txt
              and PATH_FENCE_END in rc_txt
              and rc_txt.index(PATH_BOOTSTRAP)
              > rc_txt.index(PATH_FENCE_START))
        do_uninstall(fws, lcat, ["lmod/ladd"], dry_run=False)
        rc_after = Path(_RUNTIME["rc"]).read_text(encoding="utf-8") \
            if Path(_RUNTIME["rc"]).is_file() else ""
        check("L-flag-teardown — full rm removes the fenced block",
              PATH_FENCE_START not in rc_after
              and PATH_BOOTSTRAP not in rc_after)

        print("\nSURF — ls / li / doctor / --pretty / --json")

        vend_files = sum(1 for q in (tree / SKILLS_DIR / "vendored").rglob("*")
                         if q.is_file())
        ls_data = build_ls(catalog, [
            {"id": "fixmod/goodcomp",
             "winner_path": "/mirror/fixmod/goodcomp",
             "shadowed_path": "/repo/fixmod/goodcomp"}],
            read_state(target))
        vend_e = next(e for e in ls_data["components"]
                      if e["id"] == "_hub/skills/vendored")
        good_e = next(e for e in ls_data["components"]
                      if e["id"] == "fixmod/goodcomp")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_ls(ls_data)
        ls_txt = buf.getvalue()
        check("SURF-ls-reports — SHADOWED prints; no no-manifest section",
              "SHADOWED: fixmod/goodcomp exists on both trees" in ls_txt
              and "no exposure manifest" not in ls_txt
              and "no_manifest" not in ls_data,
              ls_txt[-400:])
        check("SURF-ls-parts-are-rows — vendored parts is 1, not file count",
              vend_e["parts"] == 1
              and len(vend_e["items"]) == 1
              and vend_files > 1
              and good_e["parts"] == len(good_e["items"]) == 9
              and f"{vend_files}" not in
              [str(e["parts"]) for e in ls_data["components"]
               if e["id"] == "_hub/skills/vendored"],
              f"parts={vend_e['parts']} files={vend_files} "
              f"good={good_e['parts']}")

        pws = tmp / "ws-surf-li"
        pws.mkdir()
        do_install(pws, catalog, ["fixmod/goodcomp"], ["claude"],
                   dry_run=False,
                   parts=["fixmod/goodcomp#fixskill",
                          "fixmod/goodcomp#fixrule"])
        do_install(pws, catalog, ["fixmod/codexcomp"], ["claude"],
                   dry_run=False)
        ls_in = build_ls(catalog, [], read_state(pws))
        good = next(e for e in ls_in["components"] if e["id"] == "fixmod/goodcomp")
        inn = {i["part_id"]: i["in"] for i in good["items"]}
        check("SURF-ls-in-column — booked True, sibling False",
              inn.get("fixskill") is True and inn.get("fixrule") is True
              and inn.get("fixcmd") is False,
              str(inn))
        raw_sk = {"components": {
            "_skills/vendored": {"parts": {"vendored": {"method": "skill"}}}}}
        check("ls-in-legacy-skills-key — leftover _skills/ counts as in",
              _part_in(raw_sk, "_hub/skills/vendored", "vendored") is True)
        raw_v1 = {"components": {
            "fixmod/goodcomp": {"files": [".claude/rules/fixrule.md"]}}}
        check("ls-in-schema1-whole — missing parts map means every pid is in",
              _part_in(raw_v1, "fixmod/goodcomp", "fixrule") is True
              and _part_in(raw_v1, "fixmod/goodcomp", "fixcmd") is True)
        ls_nc = build_ls(catalog, [], {}, exclude_components=["fixmod/goodcomp"])
        check("SURF-ls-exclude-component",
              all(e["id"] != "fixmod/goodcomp" for e in ls_nc["components"]),
              str([e["id"] for e in ls_nc["components"]][:8]))
        ls_nx = build_ls(catalog, [], {}, exclude_methods=["skill"])
        check("SURF-ls-exclude-method",
              all(i["method"] != "skill"
                  for e in ls_nx["components"] for i in e["items"]))
        li0 = do_list(pws, catalog)
        args_nc = argparse.Namespace(
            module=[], component=[], method=[],
            exclude_module=[], exclude_component=["fixmod/goodcomp"],
            exclude_method=[])
        check("SURF-li-exclude-component",
              "fixmod/goodcomp" not in _li_filter(li0, catalog, args_nc)["components"])
        li_data = do_list(pws, catalog)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_li(li_data)
        li_txt = buf.getvalue()
        part_rec = li_data["components"]["fixmod/goodcomp"]
        full_rec = li_data["components"]["fixmod/codexcomp"]
        check("SURF-li-full-vs-part — partial has out:, full does not",
              part_rec["status"] == "part"
              and full_rec["status"] == "full"
              and "out:" in li_txt
              and any(line.startswith("1") or "part" in line
                      for line in li_txt.splitlines())
              and any("full" in line and "fixmod/codexcomp" in line
                      for line in li_txt.splitlines())
              and any("part" in line and "fixmod/goodcomp" in line
                      for line in li_txt.splitlines())
              and "out: " in li_txt
              and "fixcmd" in part_rec["missing"]
              and not full_rec["missing"],
              f"part={part_rec['status']} miss={part_rec['missing']} "
              f"full={full_rec['status']}")
        # Retargeted TWICE on 2026-08-22. The original was
        # `endswith("@  (none)") or "@  " in li_txt` — an OR whose right arm
        # matched any line containing "@  ". The first retarget asserted the
        # real payload was listed, but THIS FIXTURE OWNS NOTHING (claims,
        # guidance and links are all empty), so every `all(... for x in [])`
        # was vacuously true and a mutant that stopped printing items entirely
        # still passed. The renderer is now driven with a payload that HAS one
        # of each, which is the only way the listing behaviour can be observed.
        _labels = ("guidance files written",
                   "keys held in shared config files",
                   "commands linked onto PATH")
        _probe = {"guidance_files": ["AGENTS.md"],
                  "shared_claims": ['.mcp.json::["mcpServers", "probe"]'],
                  "path_links": [{"name": "probe-cli"}],
                  "components": {}, "target": str(pws),
                  "state_file": str(pws / STATE_REL),
                  "marker": MANAGED_MARK, "guidance_basis": BASIS_NONE,
                  "schema": SCHEMA}
        _pbuf = io.StringIO()
        with contextlib.redirect_stdout(_pbuf):
            print_li(_probe)
        _ptxt = _pbuf.getvalue()
        _plisted = [ln[2:] for ln in _ptxt.splitlines()
                    if ln.startswith("  ") and ln.strip()]
        check("SURF-li-ownership-footer — every owned thing is listed under a "
              "named section",
              all(f"\n{lab}:" in _ptxt for lab in _labels)
              and "AGENTS.md" in _plisted
              and '.mcp.json::["mcpServers", "probe"]' in _plisted
              and "probe-cli" in _plisted
              # and the real render still labels all three, empty or not
              and all(f"\n{lab}:" in li_txt for lab in _labels),
              f"listed={_plisted} "
              f"labels_missing={[l for l in _labels if chr(10) + l + ':' not in _ptxt]}")

        by_name = {c["name"]: c for c in do_doctor(
            pws, DISCOVER_CWD, catalog, [], tree,
            pws / ".rbtv" / "mirror")["checks"]}
        check("SURF-doctor-names — every check has a stable name",
              set(by_name) == {
                  "target", "book", "tree-repo", "tree-mirror", "bin-dir",
                  "bin-on-path", "local-bin-shadow", "path-unbooked",
                  "path-collision", "path-not-executable", "add-collisions",
                  "guidance-basis"},
              str(sorted(by_name)))

        notdir = tmp / "ws-doc-notdir"
        notdir.write_text("x\n", encoding="utf-8")
        tfail = {c["name"]: c for c in do_doctor(
            notdir, DISCOVER_FLAG, {}, [], tree,
            notdir / ".rbtv" / "mirror")["checks"]}
        check("SURF-doctor-target-fail — names the path",
              tfail["target"]["level"] == "fail"
              and str(notdir) in tfail["target"]["detail"]
              and "not a directory" in tfail["target"]["detail"]
              and doctor_exit(list(tfail.values())) == 1,
              tfail["target"]["detail"])

        bws = tmp / "ws-doc-badbook"
        bws.mkdir()
        (bws / STATE_REL).parent.mkdir(parents=True)
        (bws / STATE_REL).write_text("{not-json", encoding="utf-8")
        bfail = {c["name"]: c for c in do_doctor(
            bws, DISCOVER_CWD, catalog, [], tree,
            bws / ".rbtv" / "mirror")["checks"]}
        check("SURF-doctor-book-fail — unreadable book is named",
              bfail["book"]["level"] == "fail"
              and "unreadable" in bfail["book"]["detail"]
              and doctor_exit(list(bfail.values())) == 1,
              bfail["book"]["detail"])

        rtree = tmp / "doc-repo-tree"
        rtree.mkdir()
        _fixture(rtree)
        mtree = tmp / "doc-mirror-tree"
        mtree.mkdir()
        (mtree / "fixmod" / "goodcomp").mkdir(parents=True)
        (mtree / "fixmod" / "goodcomp" / EXPOSURE_NAME).write_text(
            ",".join(EXPOSURE_COLS) + "\n", encoding="utf-8")
        tws = tmp / "ws-doc-trees"
        tws.mkdir()
        tchecks = {c["name"]: c for c in do_doctor(
            tws, DISCOVER_CWD, {}, [], rtree, mtree)["checks"]}
        repo_n = len(scan_tree(rtree, "repo"))
        mir_n = len(scan_tree(mtree, "mirror"))
        check("SURF-doctor-trees — counts come from the trees given",
              tchecks["tree-repo"]["level"] == "ok"
              and tchecks["tree-mirror"]["level"] == "ok"
              and f"{repo_n} components" in tchecks["tree-repo"]["detail"]
              and str(rtree) in tchecks["tree-repo"]["detail"]
              and f"{mir_n} components" in tchecks["tree-mirror"]["detail"]
              and str(mtree) in tchecks["tree-mirror"]["detail"]
              and repo_n != mir_n,
              f"repo={tchecks['tree-repo']['detail']} "
              f"mir={tchecks['tree-mirror']['detail']}")

        saved_bin, saved_path = _RUNTIME["bin"], os.environ.get("PATH")
        ghost = tmp / "ghost-bin"
        _RUNTIME["bin"] = ghost
        os.environ["PATH"] = "/usr/bin"
        dmiss = {c["name"]: c for c in do_doctor(
            tws, DISCOVER_CWD, {}, [], rtree, mtree)["checks"]}
        check("SURF-doctor-bin-missing — names the bindir",
              dmiss["bin-dir"]["level"] == "warn"
              and str(ghost) in dmiss["bin-dir"]["detail"]
              and "missing" in dmiss["bin-dir"]["detail"]
              and dmiss["path-unbooked"]["detail"] == "no directory"
              and doctor_exit(list(dmiss.values())) == 0,
              dmiss["bin-dir"]["detail"])
        check("SURF-doctor-bin-on-path — says not on PATH",
              dmiss["bin-on-path"]["level"] == "warn"
              and "not on PATH" in dmiss["bin-on-path"]["detail"],
              dmiss["bin-on-path"]["detail"])

        ghost.mkdir()
        os.environ["PATH"] = str(ghost) + os.pathsep + str(local_bin())
        (local_bin()).mkdir(parents=True, exist_ok=True)
        (local_bin() / "shadowme").write_text("x\n", encoding="utf-8")
        (ghost / "shadowme").symlink_to(tmp / "fake-bashrc")
        Path(_RUNTIME["rc"]).write_text("x\n", encoding="utf-8")
        dsh = {c["name"]: c for c in do_doctor(
            tws, DISCOVER_CWD, {}, [], rtree, mtree)["checks"]}
        check("SURF-doctor-local-shadow — names the shadowed command",
              dsh["local-bin-shadow"]["level"] == "warn"
              and "shadowme" in dsh["local-bin-shadow"]["detail"]
              and "shadows" in dsh["local-bin-shadow"]["detail"],
              dsh["local-bin-shadow"]["detail"])
        (ghost / "stranger").symlink_to(tmp / "fake-bashrc")
        dun = {c["name"]: c for c in do_doctor(
            tws, DISCOVER_CWD, {}, [], rtree, mtree)["checks"]}
        check("SURF-doctor-unbooked — names the leftover link",
              dun["path-unbooked"]["level"] == "warn"
              and "stranger" in dun["path-unbooked"]["detail"],
              dun["path-unbooked"]["detail"])
        (ghost / "hitfile").write_text("not a link\n", encoding="utf-8")
        coll_cat = {
            "amod/acomp": {
                "id": "amod/acomp", "module": "amod",
                "component": "acomp", "kind": "component",
                "manifest": True, "tree": "repo",
                "path": str(tmp),
                "rows": [{"part-id": "hitfile", "method": "path"}]}}
        dcol = {c["name"]: c for c in do_doctor(
            tws, DISCOVER_CWD, coll_cat, [], rtree, mtree)["checks"]}
        check("SURF-doctor-path-collision — names the regular file",
              dcol["path-collision"]["level"] == "warn"
              and "hitfile" in dcol["path-collision"]["detail"]
              and "not a symlink" in dcol["path-collision"]["detail"],
              dcol["path-collision"]["detail"])
        nox = tmp / "not-exec.py"
        nox.write_text("print(1)\n", encoding="utf-8")
        nox.chmod(0o644)
        (ghost / "noexec").symlink_to(nox)
        nexec_cat = {
            "amod/acomp": {
                "id": "amod/acomp", "module": "amod",
                "component": "acomp", "kind": "component",
                "manifest": True, "tree": "repo",
                "path": str(tmp),
                "rows": [{"part-id": "noexec", "method": "path"}]}}
        dnx = {c["name"]: c for c in do_doctor(
            tws, DISCOVER_CWD, nexec_cat, [], rtree, mtree)["checks"]}
        check("SURF-doctor-not-exec — names the non-executable dest",
              dnx["path-not-executable"]["level"] == "warn"
              and "noexec" in dnx["path-not-executable"]["detail"]
              and "not executable" in dnx["path-not-executable"]["detail"],
              dnx["path-not-executable"]["detail"])
        _RUNTIME["bin"] = saved_bin
        if saved_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = saved_path

        cws = tmp / "ws-doc-addcoll"
        cws.mkdir()
        (cws / ".claude/skills/fixskill").mkdir(parents=True)
        (cws / ".claude/skills/fixskill/SKILL.md").write_text(
            "hand authored, no marker\n", encoding="utf-8")
        dadd = {c["name"]: c for c in do_doctor(
            cws, DISCOVER_CWD, {"fixmod/goodcomp": catalog["fixmod/goodcomp"]},
            [], tree, cws / ".rbtv" / "mirror")["checks"]}
        check("SURF-doctor-add-collisions — names the unbooked file",
              dadd["add-collisions"]["level"] == "warn"
              and "fixskill" in dadd["add-collisions"]["detail"]
              and "collision" in dadd["add-collisions"]["detail"]
              and doctor_exit(list(dadd.values())) == 0,
              dadd["add-collisions"]["detail"])

        gws = tmp / "ws-doc-basis"
        gws.mkdir()
        write_state(gws, {"components": {}, "guidance_basis": "WAT.md",
                          "shared_claims": []})
        dbas = {c["name"]: c for c in do_doctor(
            gws, DISCOVER_CWD, {}, [], tree,
            gws / ".rbtv" / "mirror")["checks"]}
        check("SURF-doctor-guidance-basis — names the bad value",
              dbas["guidance-basis"]["level"] == "warn"
              and "WAT.md" in dbas["guidance-basis"]["detail"]
              and "guidance-basis-invalid" in dbas["guidance-basis"]["detail"],
              dbas["guidance-basis"]["detail"])

        buf_p, buf_j = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_p), \
             contextlib.redirect_stderr(io.StringIO()):
            cmd_ls(build_parser().parse_args(["ls"]), pws, catalog, [])
        with contextlib.redirect_stdout(buf_j), \
             contextlib.redirect_stderr(io.StringIO()):
            cmd_ls(build_parser().parse_args(["ls", "--pretty"]),
                   pws, catalog, [])
        plain_ls, pretty_ls = buf_p.getvalue(), buf_j.getvalue()
        check("SURF-pretty-off-is-plain — default has no ANSI",
              "\033[" not in plain_ls
              and "\033[" in pretty_ls,
              f"plain_esc={'\\033[' in plain_ls} "
              f"pretty_esc={'\\033[' in pretty_ls}")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
             contextlib.redirect_stderr(io.StringIO()):
            cmd_ls(build_parser().parse_args(["ls", "--json"]),
                   pws, catalog, [])
        lsj = json.loads(buf.getvalue())
        check("SURF-json-ls-keys — today's keys plus items/index",
              set(lsj) >= {"ok", "components", "shadowed",
                           "hub_refusals", "index"}
              and "no_manifest" not in lsj
              and set(lsj["components"][0]) >= {
                  "id", "tree", "module", "kind", "manifest", "methods",
                  "parts", "note", "items"}
              and lsj["ok"] is True,
              str(sorted(lsj)))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
             contextlib.redirect_stderr(io.StringIO()):
            cmd_li(build_parser().parse_args(["li", "--json"]),
                   pws, catalog, [])
        lij = json.loads(buf.getvalue())
        check("SURF-json-li-keys — today's keys plus path_links/status",
              set(lij) >= {"ok", "target", "schema", "state_file", "marker",
                           "guidance_basis", "components", "guidance_files",
                           "shared_claims", "path_links"}
              and lij["components"]["fixmod/goodcomp"]["status"] == "part"
              and "missing" in lij["components"]["fixmod/goodcomp"],
              str(sorted(lij)))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
             contextlib.redirect_stderr(io.StringIO()):
            cmd_doctor(build_parser().parse_args(["doctor", "--json"]),
                       pws, catalog, [])
        dj = json.loads(buf.getvalue())
        check("SURF-json-doctor-keys — envelope + named checks",
              set(dj) >= {"ok", "version", "target", "why", "checks"}
              and {c["name"] for c in dj["checks"]}
              == set(by_name)
              and all("level" in c and "detail" in c and "ok" in c
                      for c in dj["checks"]),
              str(sorted(dj)))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
             contextlib.redirect_stderr(io.StringIO()):
            rc_ref = main(["add", "--target", str(pws), "-c", "no/comp",
                           "--json"])
        env = json.loads(buf.getvalue())
        check("SURF-json-refuse-keys — refusal envelope kept",
              rc_ref == 1 and env.get("ok") is False
              and "refusal" in env and "code" in env["refusal"]
              and "message" in env["refusal"],
              str(env))

        print("\nuninstall")
        res = do_uninstall(target, catalog, ["fixmod/goodcomp"], dry_run=False)
        left = sorted(p.relative_to(target).as_posix()
                      for p in target.rglob("*") if p.is_file())
        check("only the foreign content survives",
              left == sorted(set(legacy) | {".claude/settings.json",
                                            ".mcp.json"}), str(left))
        check("the old installer's rbtv- artifacts are byte-identical",
              all((target / rel).read_text() == body
                  for rel, body in legacy.items()))
        check("foreign JSON keys survive, ours are gone",
              json.loads((target / ".claude/settings.json").read_text())
              == {"foreignKey": 1}
              and json.loads((target / ".mcp.json").read_text())
              == {"mcpServers": {"foreign": {"url": "https://x.invalid"}}})
        check("shared files we fully owned are gone",
              not (target / ".codex").exists()
              and not (target / "opencode.json").exists()
              and not (target / ".agents").exists())
        check("the book is gone once nothing of ours remains",
              not (target / STATE_REL).exists())
        check("uninstall reported every deletion",
              set(res["deleted"]) == expect,
              str(sorted(set(res["deleted"]) ^ expect)))
        _RUNTIME["bin"] = None
        _RUNTIME["rc"] = None
        _RUNTIME["local"] = None

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# ── cli ─────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rbtv install",
        description=(
            "Install rbtv components from exposure manifests. "
            "Unit is the exposed part; any subset may be installed."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog="exit codes: 0 success · 1 refusal · 2 usage")

    def tree_flags(dest, *, on_verb: bool) -> None:
        sup = argparse.SUPPRESS
        dest.add_argument(
            "--target", default=(sup if on_verb else None),
            help="install root (default: walk up from cwd for "
                 ".rbtv/config/install.json, then any .rbtv/, then cwd)")
        dest.add_argument(
            "--json", action="store_true",
            default=(sup if on_verb else False),
            help="machine output")
        dest.add_argument(
            "--pretty", action="store_true",
            default=(sup if on_verb else False),
            help="human colour + alignment (never TTY-derived)")
        dest.add_argument(
            "--dry-run", action="store_true",
            default=(sup if on_verb else False),
            help="plan and print; write nothing")

    class MethodsAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            cur = getattr(namespace, self.dest) or []
            for part in str(values).split(","):
                part = part.strip()
                if not part:
                    continue
                if part not in CANONICAL_METHODS:
                    parser.error(
                        f"unknown method {part!r} (want "
                        + " · ".join(CANONICAL_METHODS) + ")")
                cur.append(part)
            setattr(namespace, self.dest, cur)

    def selectors(dest) -> None:
        dest.add_argument(
            "-A", action="store_true", dest="all",
            help="everything")
        dest.add_argument(
            "-m", action="append", default=[], dest="module",
            metavar="MOD",
            help="module (repeatable, OR). -m hub = _hub")
        dest.add_argument(
            "-c", action="append", default=[], dest="component",
            metavar="COMP",
            help="component (repeatable, OR). name or last ls/li number")
        dest.add_argument(
            "-x", action=MethodsAction, default=[], dest="method",
            metavar="METH",
            help="method[,method] (repeatable, OR). "
                 + " · ".join(CANONICAL_METHODS))
        for flag, meth in (("-xs", "skill"), ("-xr", "rule"),
                           ("-xc", "command"), ("-xsa", "sub-agent")):
            dest.add_argument(
                flag, action="append_const", const=meth, dest="method",
                help=f"alias: -x {meth}")
        dest.add_argument(
            "-nx", action=MethodsAction, default=[], dest="exclude_method",
            metavar="METH",
            help="exclude method[,method]")
        dest.add_argument(
            "-nm", action="append", default=[], dest="exclude_module",
            metavar="MOD",
            help="exclude module")
        dest.add_argument(
            "-nc", action="append", default=[], dest="exclude_component",
            metavar="COMP",
            help="exclude component")

    tree_flags(p, on_verb=False)
    p.add_argument(
        "--harness", default=None,
        help="comma-separated subset of " + ",".join(HARNESSES)
             + " (attaches to the component record, never rewrites the book)")
    p.add_argument(
        "--artifact", default=None, choices=(*GUIDANCE_NAMES, BASIS_NONE),
        help="which root guidance file you author; the other is generated. "
             "none = author-nothing, generate-nothing. persisted")
    sub = p.add_subparsers(dest="verb", metavar="VERB")

    s_add = sub.add_parser(
        "add",
        help="install / refresh (replan). refuses a locally-modified vendor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog=(
            "selectors AND across kinds, OR within a kind.\n"
            "exclusion: -nx skill  -nm core  -nc web/browse"))
    selectors(s_add)
    s_add.add_argument(
        "--harness", default=argparse.SUPPRESS,
        help="comma-separated subset of " + ",".join(HARNESSES)
             + " (attaches to the component record, never rewrites the book)")
    s_add.add_argument(
        "--artifact", default=argparse.SUPPRESS,
        choices=(*GUIDANCE_NAMES, BASIS_NONE),
        help="which root guidance file you author; the other is generated. "
             "none = author-nothing, generate-nothing. persisted")
    s_add.add_argument(
        "--write-path", action="store_true",
        help="append the PATH bootstrap line to the shell startup file "
             "(fenced; teardown can remove it). never happens without this flag")

    s_rm = sub.add_parser(
        "rm", help="remove. -A = every booked part")
    selectors(s_rm)

    s_ls = sub.add_parser(
        "ls", help="what is AVAILABLE (absorbs scan: shadowed)")
    selectors(s_ls)
    s_li = sub.add_parser(
        "li", help="what is INSTALLED; marks partials and names parts in")
    selectors(s_li)

    s_dupe = sub.add_parser(
        "dupe-artifacts",
        help="regenerate harness guidance files from the base artifact")
    s_dupe.add_argument(
        "--artifact", default=argparse.SUPPRESS,
        choices=(*GUIDANCE_NAMES, BASIS_NONE),
        help="basis to regenerate from (default: whatever the book holds)")

    s_doc = sub.add_parser(
        "doctor",
        help="can this tool work here: target, trees, PATH, collisions")
    sub.add_parser(
        "selftest",
        help="fixture tree + install/uninstall + new surface")
    s_inter = sub.add_parser(
        "interactive", help="the human flow (also: no arguments)")

    for s in (s_add, s_rm, s_ls, s_li, s_dupe, s_doc, s_inter):
        tree_flags(s, on_verb=True)
    return p


def _emit(data: dict, as_json: bool) -> None:
    print(json.dumps(data, indent=2)) if as_json else print_result(data)


def _ls_filters(args, catalog: dict, target: Path) -> dict:
    comps = list(getattr(args, "component", None) or [])
    drop_c = list(getattr(args, "exclude_component", None) or [])
    fp = scan_fingerprint(catalog)
    idx = read_index(target)
    if any(t.isdigit() for t in comps):
        comps = _expand_nums(comps, "component", idx, fp)
    if any(t.isdigit() for t in drop_c):
        drop_c = _expand_nums(drop_c, "component", idx, fp)
    return dict(
        modules=list(getattr(args, "module", None) or []),
        methods=list(getattr(args, "method", None) or []),
        components=comps,
        exclude_modules=list(getattr(args, "exclude_module", None) or []),
        exclude_methods=list(getattr(args, "exclude_method", None) or []),
        exclude_components=drop_c,
    )


def _li_filter(data: dict, catalog: dict, args) -> dict:
    want_m = {module_id(m) for m in (getattr(args, "module", None) or [])}
    want_c = {_norm_comp(c) for c in (getattr(args, "component", None) or [])}
    drop_m = {module_id(m) for m in (getattr(args, "exclude_module", None) or [])}
    drop_c = {_norm_comp(c) for c in (getattr(args, "exclude_component", None) or [])}
    want_x = set(getattr(args, "method", None) or [])
    drop_x = set(getattr(args, "exclude_method", None) or [])
    if not (want_m or want_c or drop_m or drop_c or want_x or drop_x):
        return data
    kept = {}
    for cid, rec in data["components"].items():
        mod = rec.get("module") or cid.split("/")[0]
        if want_m and module_id(mod) not in want_m:
            continue
        if drop_m and module_id(mod) in drop_m:
            continue
        if want_c and cid not in want_c:
            continue
        if drop_c and cid in drop_c:
            continue
        rec = dict(rec)
        if want_x or drop_x:
            parts = {pid: p for pid, p in (rec.get("parts") or {}).items()
                     if isinstance(p, dict)
                     and (not want_x or p.get("method") in want_x)
                     and p.get("method") not in drop_x}
            rec["parts"] = parts
        kept[cid] = rec
    out = dict(data)
    out["components"] = kept
    return out


def cmd_ls(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    del ask
    state = read_state(target)
    data = build_ls(catalog, shadowed, state, **_ls_filters(args, catalog, target))
    write_visible_index(target, data["index"])
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        print_ls(data, pretty=bool(getattr(args, "pretty", False)))
    return 0


def cmd_li(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    del ask, shadowed
    data = do_list(target, catalog)
    data = _li_filter(data, catalog, args)
    n, k = {}, 1
    for cid in data["components"]:
        n[str(k)] = {"kind": "component", "id": cid}
        k += 1
    for cid, rec in data["components"].items():
        for pid in sorted(rec.get("parts") or {}):
            n[str(k)] = {"kind": "part", "id": part_key(cid, pid)}
            k += 1
    write_visible_index(target, {"fingerprint": scan_fingerprint(catalog),
                                 "n": n})
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        print_li(data, pretty=bool(getattr(args, "pretty", False)))
    return 0


def cmd_add(args, target: Path, catalog: dict, shadowed: list,
            *, ask=None) -> int:
    del ask, shadowed
    if not (args.all or args.module or args.component or args.method
            or args.exclude_module or args.exclude_component
            or args.exclude_method):
        raise SystemExit(2)
    args.index = read_index(target)
    keys = resolve_selection(args, catalog, None)
    picked, parts = _split_part_keys(keys)
    harnesses = _parse_harnesses(
        getattr(args, "harness", None) or ",".join(HARNESSES))
    if not harnesses:
        raise Refuse("harness-unknown", "--harness selected no harness")
    data = do_install(
        target, catalog, picked, harnesses,
        bool(getattr(args, "dry_run", False)),
        guidance_basis=getattr(args, "artifact", None),
        parts=parts,
        write_path=bool(getattr(args, "write_path", False)))
    _emit(data, bool(getattr(args, "json", False)))
    return 0


def cmd_rm(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    del shadowed
    if not (args.all or args.module or args.component or args.method
            or args.exclude_module or args.exclude_component
            or args.exclude_method):
        raise SystemExit(2)
    args.index = read_index(target)
    book = read_state(target).get("components")
    keys = resolve_selection(args, catalog, book)
    dry = bool(getattr(args, "dry_run", False))
    if _has_negative(args):
        if not confirm_removal(keys, dry_run=dry, ask=ask):
            print("cancelled")
            return 0
    picked, parts = _split_part_keys(keys)
    data = do_uninstall(target, catalog, picked, dry, parts=parts)
    _emit(data, bool(getattr(args, "json", False)))
    return 0


def cmd_dupe(args, target: Path, catalog: dict, shadowed: list,
             *, ask=None) -> int:
    del ask, shadowed
    state = read_state(target)
    records = state.get("components") or {}
    picked = sorted(records)
    hs = installed_harnesses(records) or list(HARNESSES)
    data = do_install(
        target, catalog, picked, hs,
        bool(getattr(args, "dry_run", False)),
        guidance_basis=getattr(args, "artifact", None))
    _emit(data, bool(getattr(args, "json", False)))
    return 0


def cmd_doctor(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    del ask
    why = getattr(args, "_why", DISCOVER_CWD) if args else DISCOVER_CWD
    repo_tree = Path(__file__).resolve().parent
    mirror_tree = target / ".rbtv" / "mirror"
    data = do_doctor(target, why, catalog, shadowed, repo_tree, mirror_tree)
    if args and getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        print(render_doctor(data["checks"],
                            pretty=bool(args and getattr(args, "pretty", False))))
    return doctor_exit(data["checks"])


def cmd_interactive(args, target: Path, catalog: dict, shadowed: list,
                    *, ask=None) -> int:
    del args, shadowed, ask
    return interactive(target, catalog)


def cmd_selftest(args, target: Path, catalog: dict, shadowed: list,
                 *, ask=None) -> int:
    del args, target, catalog, shadowed, ask
    return selftest()


_HANDLERS = {
    "add": cmd_add,
    "rm": cmd_rm,
    "ls": cmd_ls,
    "li": cmd_li,
    "dupe-artifacts": cmd_dupe,
    "doctor": cmd_doctor,
    "interactive": cmd_interactive,
    "selftest": cmd_selftest,
}


def main(argv: list[str] | None = None, *, ask=None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    if args.verb == "selftest":
        return selftest()

    as_json = bool(getattr(args, "json", False))
    if getattr(args, "target", None) is None:
        target, why = discover_target(Path.cwd())
        if args.verb != "doctor":
            print(f"target: {target}  (discovered by {why}; pass --target to "
                  f"override)", file=sys.stderr)
    else:
        target = Path(args.target).expanduser()
        why = DISCOVER_FLAG
    args._why = why
    repo_tree = Path(__file__).resolve().parent
    mirror_tree = target / ".rbtv" / "mirror"

    try:
        catalog, shadowed = scan_all(mirror_tree, repo_tree)
        if args.verb in (None, "interactive"):
            if as_json:
                raise Refuse("usage", "interactive mode has no --json output")
            return interactive(target, catalog)
        handler = _HANDLERS.get(args.verb)
        if handler is None:
            parser.error(f"unknown verb {args.verb!r}")
        if args.verb in ("add", "rm") and not (
                args.all or args.module or args.component or args.method
                or args.exclude_module or args.exclude_component
                or args.exclude_method):
            parser.error(f"{args.verb} needs -A or -m/-c/-x")
        return handler(args, target, catalog, shadowed, ask=ask)
    except Refuse as exc:
        if as_json:
            print(json.dumps(exc.payload(), indent=2))
        else:
            print(f"REFUSED [{exc.code}] {exc.message}", file=sys.stderr)
            if exc.path:
                print(f"  at: {exc.path}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        return int(exc.code or 0)
    except KeyboardInterrupt:
        print("\ncancelled", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
