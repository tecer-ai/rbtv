#!/usr/bin/env python3
"""install2.py — the exposure-manifest rbtv installer (supersedes install.py).

Installs components into a workspace by reading their EXPOSURE MANIFESTS
(`exposure.csv`) and realizing each row's canonical method per harness, at the
INSTALL ROOT only. Python 3 stdlib only.

    install2.py scan                    what is installable (+ the no-manifest report)
    install2.py list                    what is installed (from the state file)
    install2.py install --component <module>/<component> [--harness a,b] [--target D]
    install2.py install --module <module>
    install2.py install --component <id> --guidance-basis CLAUDE.md|AGENTS.md|none
                                         [--guidance-exclude 4-archives,vendor]
    install2.py uninstall --component <id> | --module <name>
    install2.py interactive             the human flow (also: no arguments)
    install2.py selftest                the runnable check

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

D2  WHAT A COMPONENT IS — THE NEW STANDARD ONLY (owner amendment, 2026-08-21)
    — a `<module>/<component>` directory holding `component.md`: the component
    folder the KG ratifies (`concepts/component.md` § component-first layout,
    `d-component-first-layout`), whose id is its tree-relative posix path
    (`meta/planning`) and whose module is the first segment. An exposure
    manifest is NOT the marker and neither is `module.md`: a directory carrying
    `exposure.csv` WITHOUT `component.md`, or carrying either at depth 1 (the
    module-root manifests of `<repo>/core`, `<repo>/ignite`,
    `<repo>/orchestration`, each flagged INTERIM in its own header) is the OLD
    standard's shape and is invisible here — `install.py` + `admin/install/`
    manage that tree, and the two installers are separate entities over
    disjoint sets. A component.md-less folder is therefore never reported as
    "no exposure manifest"; it is not a component of this installer's world at
    all. When the CMP-5 component tree materializes in the repo, the folders it
    mints carry `component.md` and become visible here with no code change.

D3  TREES + PRECEDENCE — two roots, scanned together: `mirror` =
    `{target}/.rbtv/mirror`, `repo` = the directory holding this file, which
    is NOT overridable — the file and its tree ship together, so a flag
    pointing one at another's tree only ever named a broken pair (owner
    ruling, 2026-08-21). `--mirror-tree` stays. On the same id in both, the
    MIRROR WINS (workspace-local staging is the newer copy by construction) and
    the shadowing is reported, never silent.

D4  HARNESSES — all four by default (claude, codex, opencode, kimi); `--harness`
    filters. CON-2 bounds the registry BUILD to three, but the owner's spec for
    this tool names four and kimi was measured on this box (see MATRIX notes).

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
    qwen `QWEN.md`, kimi `AGENTS.md`, opencode `AGENTS.md`-or-`CLAUDE.md`).
    There is no index file: the earlier `.agents/rbtv2-exposure.md` was an
    invented artifact in no CMP-12 cell, auto-loaded by no harness, and is
    RETIRED — an existing one is removed by the ordinary booked-file machinery
    on the next install or uninstall. Every `agents.md` row and every forced
    rule read is carried by the GENERATED guidance file (D13), inside one fenced
    `rbtv2:start … rbtv2:end` block at its head. The BASIS is still never
    written: whatever block the basis itself would need is REPORTED for the
    human to place, and mirrors from there.

    THE FORCED READ (CMP-12 § Fallback mechanics) is for the harnesses that
    auto-inject no rule folder — Codex, Qwen and Kimi ONLY. It is emitted into a
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
    share a filename (codex + kimi + opencode all read `AGENTS.md`) get ONE
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

D15 `_skills/` — WHOLE-FOLDER SKILLS (owner ruling, 2026-08-21) — a tree-root
    `_skills/` directory holds skills that are NOT rbtv parts: vendored or
    third-party skill folders (`cli-creator/`, `improve-codebase-architecture/`)
    that carry their own `SKILL.md` plus references, agents and licence files.
    They have no component, no manifest and no entry point to point AT, so the
    thin-loader realization of every other skill row is wrong for them: the
    CONTENT is the skill, and it must land in the harness's skills directory
    whole. Each `_skills/<name>/` is therefore its own installable unit, id
    `_skills/<name>` — module `_skills`, component `<name>` — so `--component
    _skills/cli-creator`, `--module _skills`, the book, the harness filter, the
    collision gate and uninstall all work unchanged.

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

D9  `path` ROWS MINT NOTHING — tool inventory only
    (`decisions.md#d-tool-inventory-exposure-rows`). Skipped, and counted in the
    report so the skip is visible.

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
import sys
import tempfile
from pathlib import Path

VERSION = "2.0.0-coexistence"
# D12 — ownership is a marker in the file, never a prefix on its name.
MANAGED_MARK = "rbtv2-managed"
MANAGED_BANNER = (f"<!-- {MANAGED_MARK} — generated by install2.py; edits are "
                  "overwritten on the next run -->\n")
# The prefix runs before 2026-08-21 minted. Nothing writes it; the ownership
# test still recognizes it so the first unprefixed run cleans those files up.
LEGACY_PREFIX = "rbtv2-"
EXPOSURE_NAME = "exposure.csv"
COMPONENT_NAME = "component.md"
# D15 — the tree-root folder of WHOLE skill folders, copied verbatim.
SKILLS_DIR = "_skills"
SKILL_FILE = "SKILL.md"
SKILL_FOLDER_SKIP = frozenset({".git", "node_modules", "__pycache__"})
STATE_REL = Path(".rbtv") / "config" / "install.json"
FENCE_ID = "rbtv2"

# D8/D13 — CMP-12's `agents.md` row: each harness's per-folder guidance
# FILENAME. The mirror is keyed by this map and nothing else: targets = the
# installed harnesses' filenames minus the basis. (CMP-12 also models qwen =
# QWEN.md; qwen is not one of D4's harnesses, so no run can select it and
# nothing is minted for it.)
GUIDANCE_FILE = {"claude": "CLAUDE.md", "codex": "AGENTS.md",
                 "opencode": "AGENTS.md", "kimi": "AGENTS.md"}
# The names this installer recognizes as guidance files — the accepted basis
# values, and the only filenames the mirror collision/adoption gates apply to.
GUIDANCE_NAMES = tuple(sorted(set(GUIDANCE_FILE.values())))
# CMP-12 § Fallback mechanics — the harnesses that auto-inject no rule folder,
# so their guidance file must FORCE the rule read. Not claude (`.claude/rules/`
# auto-injects) and not opencode (reads `.claude/` natively). Qwen is on this
# list in CMP-12 and absent from D4's harnesses.
FORCED_READ_HARNESSES = ("codex", "kimi")
BASIS_NONE = "none"
# Directory names the recursive mirror walk never descends into.
GUIDANCE_SKIP_DIRS = frozenset({".git", "node_modules"})
# Prefixes excluded however the workspace is configured: `.rbtv/goals` routers
# (BOTH names) are written by the goals-tree scaffold, in every workspace.
GUIDANCE_ALWAYS_EXCLUDED = (".rbtv/goals",)
# A file whose head carries one of these is somebody's GENERATED mirror, not
# authored guidance — it can never be a basis (banner-over-banner).
GENERATED_MARKERS = ("AUTO-GENERATED MIRROR", "GENERATED by install2.py")

HARNESSES = ("claude", "codex", "opencode", "kimi")

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
# that `materialize-seats.py` carries. The KIMI column is MEASURED on this box,
# not taken from CMP-12's reference modelling — kimi-cli 1.48.0, package at
# `~/.local/share/uv/tools/kimi-cli/lib/python3.13/site-packages/kimi_cli`:
#
#   skill      NATIVE, and it already reads OUR files: `skill/__init__.py`
#              discovers project brand dirs `.kimi/skills` > `.claude/skills` >
#              `.codex/skills` and generic `.agents/skills`, rooted at the
#              nearest `.git` ancestor of the work dir. So the claude and codex
#              files below ARE kimi's realization; minting a `.kimi/skills`
#              copy would only SHADOW `.claude/skills` when
#              `merge_all_available_skills` is false. Nothing extra is written.
#   command    NONE. No file-based command discovery exists in the package
#              (slash commands are built in, `soul/slash.py`) — CMP-12's
#              "no command file (CLI only)" reading confirmed.
#   rule       NO native rule folder → CMP-12's fallback: the same verbatim
#              `.agents/behavior-rules/` copy codex and opencode take, forced
#              from the guidance index by an enumerated Step-0.
#   sub-agent  NO project-local definition directory. `--agent-file` names the
#              WHOLE-SESSION agent spec (`agentspec.py`: `DEFAULT_AGENT_FILE`
#              lives inside the package), and `subagents/store.py` is
#              per-session runtime state. CMP-12 models this column as "native
#              (--agent-file yaml)"; measured, that is not a sub-agent catalog.
#              Nothing minted.
MATRIX: dict[str, dict[str, str | None]] = {
    "skill": {
        "claude": ".claude/skills/{name}/SKILL.md",
        # opencode natively reads `.claude/` (CMP-12, widest claude-compat) —
        # same file, deduped by path.
        "opencode": ".claude/skills/{name}/SKILL.md",
        "codex": ".agents/skills/{name}/SKILL.md",
        "kimi": ".claude/skills/{name}/SKILL.md",
    },
    "command": {
        "claude": ".claude/commands/{name}.md",
        "codex": ".codex/prompts/{name}.md",
        "opencode": ".opencode/commands/{name}.md",
        "kimi": None,
    },
    "rule": {
        "claude": ".claude/rules/{name}.md",
        "codex": ".agents/behavior-rules/{name}.md",
        # CMP-12 gives opencode NO separate rule type — it reads `.claude/`
        # natively, so claude's own file IS its realization (same dedupe by path
        # as the `skill` row above). It therefore takes no forced read either.
        "opencode": ".claude/rules/{name}.md",
        "kimi": ".agents/behavior-rules/{name}.md",
    },
    "sub-agent": {
        "claude": ".claude/agents/{name}.md",
        "opencode": ".opencode/agents/{name}.md",
        "codex": None,
        "kimi": None,
    },
}

# Methods that do not land as a per-part file: they claim keys or blocks inside
# files shared with the whole installed set (D7/D12), or mint nothing (D9).
AGGREGATE_METHODS = ("hook", "config", "agents.md")
INVENTORY_METHODS = ("path", "pool")

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


# ── discovery ───────────────────────────────────────────────────────────────

def _is_component_dir(path: Path) -> bool:
    """D2 — the NEW-STANDARD component folder: `component.md` present. An
    `exposure.csv` alone is the old/interim shape and belongs to install.py."""
    return (path / COMPONENT_NAME).is_file()


def scan_tree(root: Path, tree: str) -> dict[str, dict]:
    """Every NEW-STANDARD component under one tree root, by id (D2) — a
    `<module>/<component>` folder holding `component.md`. {} when the root is
    absent. Old-standard folders (module-root manifests, `exposure.csv` with no
    `component.md`) are invisible here by design: install.py manages those."""
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

    for top in sorted(root.iterdir()):
        if not top.is_dir() or top.name.startswith("."):
            continue
        if top.name == SKILLS_DIR:
            # D15 — whole skill folders, not components: no manifest, no
            # component.md, the content itself is the skill.
            for sub in sorted(top.iterdir()):
                if sub.is_dir() and (sub / SKILL_FILE).is_file():
                    record(sub, kind="skill-folder")
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
    return [dict(r) for r in csv.DictReader(lines)]


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
    hooks: dict[str, list] = {}
    hook_harnesses: set[str] = set()
    agents_parts: list[tuple[str, str, str]] = []
    rule_parts: list[tuple[str, str]] = []
    report: dict = {"skipped_inventory_rows": [], "no_realization": [],
                    "skill_folders": []}

    def claim_file(rel: str, content: str, cid: str) -> None:
        if rel in files and files[rel] != content:
            raise Refuse(
                "part-collision",
                f"components {owners[rel][0]!r} and {cid!r} both realize "
                f"{rel!r} with different content — two components exposing the "
                "same part id is a manifest conflict, not something to resolve "
                "by write order",
                rel)
        files[rel] = content
        owners.setdefault(rel, []).append(cid)

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
                claim_file(f"{root_rel}/{member}", body, cid)
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

        if comp.get("kind") == "skill-folder":
            claim_skill_folder(comp, cid, harnesses)
            continue

        for row in exposure_rows(comp):
            pid = (row.get("part-id") or "").strip()
            method = (row.get("method") or "").strip()
            entry_rel = (row.get("entry-point") or "").strip()
            desc = (row.get("description") or "").strip()
            if not pid:
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
                # D9 — inventory only, mints nothing, but the skip is visible.
                report["skipped_inventory_rows"].append(
                    {"component": cid, "part": pid, "method": method,
                     "entry_point": entry_rel})
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
                    entry_abs, comp_dir, entry_file), cid)
                realized[harness] = rel
            if method == "rule" and realized:
                # The REALIZED path per harness, not the part id: a component
                # installed for claude only put no file under
                # `.agents/behavior-rules/`, so codex's forced read must not
                # enumerate one (a MANDATORY Step 0 pointing at a missing file).
                rule_parts.append((named, desc, realized))

    # ── D7/D12: shared-file claims, recomputed from the whole set ──
    claims: list[dict] = []

    def claim_json(rel: str, key: list[str], value) -> None:
        claims.append({"path": rel, "fmt": "json", "key": key, "value": value})

    if servers:
        if "claude" in server_harnesses:
            for name in sorted(servers):
                claim_json(".mcp.json", ["mcpServers", name], servers[name])
            # measured 2026-08-08, claude 2.1.226: without the flag every
            # project server sits "Pending approval".
            claim_json(".claude/settings.json",
                       ["enableAllProjectMcpServers"], True)
        if "codex" in server_harnesses:
            claims.append({"path": ".codex/config.toml", "fmt": "text",
                           "comment": "#", "key": None,
                           "value": _codex_mcp_toml_block(servers)})
        if "opencode" in server_harnesses:
            for name in sorted(servers):
                claim_json("opencode.json", ["mcp", name],
                           _opencode_mcp_entry(servers[name]))
        # kimi: no project-local MCP auto-load (measured — `cli/mcp.py` stores
        # servers at `~/.kimi/mcp.json`). The root `.mcp.json` above IS its
        # realization, passed at launch: `kimi --mcp-config-file .mcp.json`.
    if hooks:
        for event in sorted(hooks):
            if "claude" in hook_harnesses:
                claim_json(".claude/settings.json", ["hooks", event],
                           hooks[event])
            if "codex" in hook_harnesses:
                # codex 0.144.5 measured shape: the claude `hooks` object
                # verbatim (d-seat-exposes-frontmatter measurement amendment).
                claim_json(".codex/hooks.json", ["hooks", event], hooks[event])
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
        return {"schema": 1, "installer": "install2.py", "components": {},
                "shared_claims": []}
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(target: Path, state: dict) -> None:
    path = target / STATE_REL
    state["schema"] = 1
    state["installer"] = "install2.py"
    state["version"] = VERSION
    state["marker"] = MANAGED_MARK
    state["installed_at"] = _dt.datetime.now().isoformat(timespec="seconds")
    state["target"] = str(target.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def known_files(state: dict) -> set[str]:
    out = set(state.get("guidance_files") or [])
    for rec in (state.get("components") or {}).values():
        out |= set(rec.get("files") or [])
    return out


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

def resolve_selection(catalog: dict[str, dict], components: list[str],
                      modules: list[str], book: dict[str, dict] | None = None
                      ) -> list[str]:
    """Resolve the selection against the trees — and, for UNINSTALL, against
    the book as well (`book` = the state file's `components`).

    A booked component whose folder was renamed or deleted upstream exists in
    no catalog, and `plan_files` refuses `component-vanished` on it, blocking
    EVERY later run at that target. Without this the refusal's own advice
    ("uninstall it with the tree present") names a door that cannot be opened —
    the tree copy is gone. Its files are in the book, so removing it needs no
    tree at all."""
    known = dict(catalog)
    for cid, rec in (book or {}).items():
        known.setdefault(cid, {"module": rec.get("module", cid.split("/")[0])})
    picked: list[str] = []
    for cid in components:
        if cid not in known:
            raise Refuse(
                "component-unknown",
                f"no component {cid!r} on either tree — run `scan` to see what "
                "is installable")
        picked.append(cid)
    for module in modules:
        hits = [cid for cid, c in known.items() if c["module"] == module]
        if not hits:
            raise Refuse(
                "module-unknown",
                f"no module {module!r} on either tree — run `scan` to see what "
                "is installable")
        picked += hits
    return sorted(set(picked))


def is_installable(comp: dict) -> bool:
    """A unit this installer can act on: a component with an exposure manifest,
    or a D15 whole-skill folder (which has no manifest by construction)."""
    return bool(comp["manifest"]) or comp.get("kind") == "skill-folder"


def do_scan(catalog: dict[str, dict], shadowed: list[dict]) -> dict:
    entries = []
    for cid in sorted(catalog):
        c = catalog[cid]
        folder = c.get("kind") == "skill-folder"
        rows = exposure_rows(c) if c["manifest"] else []
        entries.append({
            "id": cid, "tree": c["tree"], "module": c["module"],
            "kind": c.get("kind", "component"),
            "manifest": c["manifest"],
            "methods": ["skill-folder"] if folder else
                       sorted({(r.get("method") or "").strip() for r in rows
                               if (r.get("part-id") or "").strip()}),
            "parts": (sum(1 for q in Path(c["path"]).rglob("*") if q.is_file())
                      if folder
                      else len([r for r in rows
                                if (r.get("part-id") or "").strip()])),
            "note": "" if is_installable(c) else
                    "component has no exposure manifest",
        })
    return {"ok": True, "components": entries, "shadowed": shadowed,
            "no_manifest": [e["id"] for e in entries if e["note"]]}


def _rebook(state: dict, records: dict, files: dict, owners: dict,
            claims: list[dict], report: dict) -> None:
    for cid in records:
        records[cid]["files"] = sorted(
            rel for rel, own in owners.items() if cid in own)
    state["components"] = records
    state["guidance_files"] = sorted(
        rel for rel, own in owners.items() if own == ["<aggregate>"])
    state["shared_claims"] = sorted(
        _claim_id(c["path"], c["key"]) for c in claims)
    state["shared_files"] = report["shared_files"]


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


def do_install(target: Path, catalog: dict[str, dict], picked: list[str],
               harnesses: list[str], dry_run: bool,
               guidance_basis: str | None = None,
               guidance_excludes: list[str] | None = None) -> dict:
    state = read_state(target)
    records = dict(state.get("components") or {})
    for cid in picked:
        c = catalog[cid]
        records[cid] = {"tree": c["tree"], "tree_root": c["tree_root"],
                        "module": c["module"], "component": c["component"],
                        "harnesses": list(harnesses), "files": []}
    files, owners, claims, report = plan_files(records, catalog)
    protect = _add_mirror(target, state, files, owners, report, guidance_basis,
                          installed_harnesses(records), guidance_excludes)
    _add_gitignore(target, owners, claims, report)
    result = apply(target, files, claims, state, dry_run, protect)
    _clean_bases(target, report, dry_run)
    if not dry_run:
        _rebook(state, records, files, owners, claims, report)
        if guidance_basis is not None:
            state["guidance_basis"] = guidance_basis
        if guidance_excludes is not None:
            state["guidance_excludes"] = list(guidance_excludes)
        write_state(target, state)
    return {"ok": True, "installed": picked, "harnesses": harnesses,
            "files": sorted(files), **result, "report": report}


def do_uninstall(target: Path, catalog: dict[str, dict], picked: list[str],
                 dry_run: bool) -> dict:
    state = read_state(target)
    records = dict(state.get("components") or {})
    missing = [cid for cid in picked if cid not in records]
    if missing:
        raise Refuse("not-installed",
                     "not installed at this target: " + ", ".join(missing))
    for cid in picked:
        records.pop(cid)
    files, owners, claims, report = plan_files(records, catalog)
    protect: frozenset[str] = frozenset()
    if records:
        # Components remain → the mirror stays. A full uninstall takes it with
        # everything else (it is installer-owned output, not the basis).
        try:
            protect = _add_mirror(target, state, files, owners, report, None,
                                  installed_harnesses(records))
        except Refuse as exc:
            # Removing a component must NEVER be blocked by a mirror problem
            # (a deleted basis, a hand-edited book). Skip the replan, and keep
            # EVERY guidance file the book holds, under either name and at any
            # depth, off the delete set — un-managed on disk beats deleted, and
            # the next install re-books whatever is real.
            protect = frozenset(GUIDANCE_NAMES) | frozenset(
                rel for rel in known_files(state)
                if rel.rsplit("/", 1)[-1] in GUIDANCE_NAMES)
            report["guidance_mirror"] = {"basis": None, "targets": [],
                                         "skipped": exc.code}
    _add_gitignore(target, owners, claims, report)
    result = apply(target, files, claims, state, dry_run, protect)
    _clean_bases(target, report, dry_run)
    if not dry_run:
        if records:
            _rebook(state, records, files, owners, claims, report)
            write_state(target, state)
        else:
            # Nothing left of ours — take the book away too. Only OUR artifacts
            # were removed above; anything foreign at the root is still there.
            path = target / STATE_REL
            if path.is_file():
                path.unlink()
            _prune(target, path.parent)
    return {"ok": True, "uninstalled": picked, "remaining": sorted(records),
            **result, "report": report}


def do_list(target: Path) -> dict:
    state = read_state(target)
    return {"ok": True, "target": str(target.resolve()),
            "state_file": str(target / STATE_REL),
            "marker": MANAGED_MARK,
            "guidance_basis": state.get("guidance_basis"),
            "components": state.get("components") or {},
            "guidance_files": state.get("guidance_files") or [],
            "shared_claims": state.get("shared_claims") or []}


# ── human output ────────────────────────────────────────────────────────────

def print_scan(data: dict) -> None:
    print(f"{'COMPONENT':<34} {'TREE':<7} {'PARTS':>5}  METHODS / NOTE")
    for e in data["components"]:
        note = e["note"] or ", ".join(e["methods"]) or "(manifest has no rows)"
        if e.get("kind") == "skill-folder":
            note = "skill-folder — whole folder copied verbatim (D15)"
        print(f"{e['id']:<34} {e['tree']:<7} {e['parts']:>5}  {note}")
    if data["no_manifest"]:
        print(f"\n{len(data['no_manifest'])} component(s) have NO exposure "
              "manifest (normal during the transition — nothing installs from "
              "them):")
        for cid in data["no_manifest"]:
            print(f"  - {cid}: component has no exposure manifest")
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
              f"exposure manifest, and no {SKILLS_DIR}/ folder exists.")
        return 1
    installed = set(read_state(target).get("components") or {})
    print("\nComponents:\n")
    for i, cid in enumerate(installable, 1):
        mark = "*" if cid in installed else " "
        print(f" {mark}{i:>3}. {cid}  [{catalog[cid]['tree']}]")
    for cid in sorted(catalog):
        if not is_installable(catalog[cid]):
            print(f"     ---  {cid}  — component has no exposure manifest")
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
    (good / COMPONENT_NAME).write_text("# goodcomp\n", encoding="utf-8")
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
    (codexc / COMPONENT_NAME).write_text("# codexcomp\n", encoding="utf-8")
    (codexc / "rule-entry.md").write_text("# CODEX RULE\n", encoding="utf-8")
    (codexc / "guide.md").write_text("# codex guidance part\n", encoding="utf-8")
    (codexc / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "codexrule,reference,rule,,rule-entry.md,the codex-side rule,\n"
        "codexguide,prompt,agents.md,,guide.md,,\n", encoding="utf-8")

    bare = root / "fixmod" / "barecomp"
    bare.mkdir(parents=True)
    (bare / COMPONENT_NAME).write_text("# barecomp — no manifest\n",
                                       encoding="utf-8")

    res = root / "fixmod" / "reservedcomp"
    res.mkdir(parents=True)
    (res / COMPONENT_NAME).write_text("# reservedcomp\n", encoding="utf-8")
    (res / "skill-entry.md").write_text("# the skill\n", encoding="utf-8")
    (res / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "rbtv-legacy,prompt,skill,,skill-entry.md,,\n", encoding="utf-8")

    # THE OLD STANDARD (D2) — a module-root manifest and a component folder
    # with a manifest but no `component.md`. Neither is visible to this
    # installer; install.py manages that shape.
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

    bad = root / "badmod" / "badcomp"
    bad.mkdir(parents=True)
    (bad / COMPONENT_NAME).write_text("# badcomp\n", encoding="utf-8")
    (bad / "x.md").write_text("x\n", encoding="utf-8")
    (bad / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "boom,capability,telepathy,,x.md,,\n", encoding="utf-8")


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
        tree = tmp / "tree"
        tree.mkdir()
        _fixture(tree)
        target = tmp / "workspace"
        target.mkdir()
        catalog, shadowed = scan_all(tmp / "no-mirror", tree)

        print("scan")
        data = do_scan(catalog, shadowed)
        check("discovers every NEW-STANDARD component on the tree",
              sorted(catalog) == ["_skills/vendored", "badmod/badcomp",
                                  "fixmod/barecomp", "fixmod/codexcomp",
                                  "fixmod/goodcomp", "fixmod/reservedcomp"],
              str(sorted(catalog)))
        check("a _skills/ folder is discovered as a skill-folder unit (D15)",
              catalog["_skills/vendored"]["kind"] == "skill-folder"
              and catalog["_skills/vendored"]["module"] == SKILLS_DIR
              and not catalog["_skills/vendored"]["manifest"],
              str(catalog["_skills/vendored"]))
        check("it is INSTALLABLE despite having no manifest, and says so",
              is_installable(catalog["_skills/vendored"])
              and "_skills/vendored" not in data["no_manifest"]
              and [e for e in data["components"]
                   if e["id"] == "_skills/vendored"][0]["methods"]
              == ["skill-folder"], str(data["no_manifest"]))
        check("reports the manifest-less component",
              data["no_manifest"] == ["fixmod/barecomp"],
              str(data["no_manifest"]))

        print("\nD2 — only NEW-STANDARD component folders are visible")
        check("a module-root exposure.csv is NOT a component (old standard)",
              "oldmod" not in catalog and "oldmod/oldcomp" not in catalog,
              str(sorted(catalog)))
        check("neither is a folder with a manifest but no component.md",
              not any(cid.endswith("oldcomp") for cid in catalog),
              str(sorted(catalog)))

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

        print("\ngreen arm — install all four harnesses")
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
        check("`path` and `pool` rows minted nothing",
              not (target / ".claude/skills/fixtool").exists()
              and not (target / ".claude/skills/fixpool").exists()
              and sorted(r["method"] for r
                         in res["report"]["skipped_inventory_rows"])
              == ["path", "pool"],
              str(res["report"]["skipped_inventory_rows"]))
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
              set(rec["files"]) == expect - set(state["guidance_files"]),
              str(sorted(set(rec["files"]) ^ (expect - set(state["guidance_files"])))))
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
        do_install(mt7, catalog, ["fixmod/goodcomp", "fixmod/barecomp"],
                   list(HARNESSES), dry_run=False, guidance_basis="CLAUDE.md")
        (mt7 / "CLAUDE.md").unlink()          # basis gone AFTER the install
        res7 = do_uninstall(mt7, catalog, ["fixmod/barecomp"], dry_run=False)
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

        h3, r3 = _mk("ws-three-share", ["codex", "opencode", "kimi"],
                     "CLAUDE.md")
        check("H3 — three harnesses sharing AGENTS.md get ONE file per folder",
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
        rsk = do_install(sk, catalog, ["_skills/vendored"],
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
              set(read_state(sk)["components"]["_skills/vendored"]["files"])
              == want_sk
              and rsk["report"]["skill_folders"][0]["files"] == 4,
              str(rsk["report"]["skill_folders"]))
        check("S5 — a re-install is idempotent, binary and all",
              do_install(sk, catalog, ["_skills/vendored"],
                         ["claude", "codex"], dry_run=False)["written"] == [])
        rsk2 = do_uninstall(sk, catalog, ["_skills/vendored"], dry_run=False)
        check("S6 — uninstall takes the WHOLE folder and prunes the dirs",
              set(rsk2["deleted"]) == want_sk
              and not (sk / ".claude/skills/vendored").exists()
              and not (sk / ".agents/skills/vendored").exists(),
              str(sorted(set(rsk2["deleted"]) ^ want_sk)))
        # RELEASE, folder-wide: strip the one marker and the whole copy is the
        # human's — uninstall must not delete any of it.
        do_install(sk, catalog, ["_skills/vendored"], ["claude"],
                   dry_run=False)
        taken = (sk / ".claude/skills/vendored/SKILL.md").read_text().replace(
            MANAGED_BANNER, "")
        (sk / ".claude/skills/vendored/SKILL.md").write_text(taken,
                                                             encoding="utf-8")
        rsk3 = do_uninstall(sk, catalog, ["_skills/vendored"], dry_run=False)
        check("S7 — stripping the one marker RELEASES the whole folder",
              rsk3["deleted"] == []
              and sorted(rsk3["released"]) == sorted(
                  rel for rel in want_sk if rel.startswith(".claude/"))
              and (sk / ".claude/skills/vendored/logo.png").exists(),
              str(rsk3["released"]))

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
              and rule_rel in read_state(mk)["components"][
                  "fixmod/goodcomp"]["files"],
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
        st3["components"]["fixmod/goodcomp"]["files"] = sorted(
            st3["components"]["fixmod/goodcomp"]["files"] + [legacy_rel])
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
        booked = sorted(read_state(gi)["components"]["fixmod/goodcomp"]["files"])
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
        check("G3 — dropping a harness drops its paths from the block",
              ".agents/behavior-rules/fixrule.md"
              not in (gi / ".gitignore").read_text()
              and ".claude/rules/fixrule.md" in (gi / ".gitignore").read_text(),
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
            resolve_selection(catalog, ["gonemod/gonecomp"], [])
            catalog_only = "no refusal"
        except Refuse as exc:
            catalog_only = exc.code
        check("V2 — the trees alone cannot name it (that was the trap)",
              catalog_only == "component-unknown", catalog_only)
        check("V2 — the BOOK can",
              resolve_selection(catalog, ["gonemod/gonecomp"], [],
                                book=read_state(vn)["components"])
              == ["gonemod/gonecomp"])
        resv = do_uninstall(vn, catalog, ["gonemod/gonecomp"], dry_run=False)
        check("V3 — uninstalling it needs no tree, and takes its file",
              resv["deleted"] == [gone_rel] and not (vn / gone_rel).exists()
              and "gonemod/gonecomp" not in read_state(vn)["components"],
              str(resv["deleted"]))
        check("V3 — the target is unblocked: the next install runs clean",
              do_install(vn, catalog, ["fixmod/goodcomp"], ["claude"],
                         dry_run=False)["written"] == [])

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

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# ── cli ─────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="install2.py",
        description="Install rbtv components into a workspace from their "
                    "exposure manifests (CMP-12 adapter matrix). Coexists with "
                    "install.py: it manages ONLY new-standard component "
                    "folders (`<module>/<component>/component.md`), every "
                    "artifact it writes carries the `rbtv2-managed` marker, "
                    "state lives at {target}/.rbtv/config/install.json, and "
                    "nothing outside that book or marker is ever written or "
                    "deleted.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="exit codes: 0 success · 1 refusal · 2 usage")
    def tree_flags(dest, *, on_verb: bool) -> None:
        # The three flags are accepted BEFORE and AFTER the verb. The
        # verb-level copies default to SUPPRESS so they only set the
        # attribute when explicitly given — otherwise argparse would
        # overwrite a pre-verb value with the verb-level default.
        sup = argparse.SUPPRESS
        dest.add_argument("--target", default=(sup if on_verb else None),
                          help="install root (default: discovered by walking "
                               "up from the cwd for .rbtv/config/install.json, "
                               "then for any .rbtv/ directory, then cwd)")
        dest.add_argument("--mirror-tree", default=(sup if on_verb else None),
                          help="workspace mirror tree "
                               "(default: {target}/.rbtv/mirror)")

    tree_flags(p, on_verb=False)
    sub = p.add_subparsers(dest="verb")

    s_scan = sub.add_parser("scan", help="what is installable, per tree, "
                                         "incl. the no-manifest report")
    s_scan.add_argument("--json", action="store_true")
    s_list = sub.add_parser("list", help="what is installed, from the "
                                         "state file")
    s_list.add_argument("--json", action="store_true")
    s_inter = sub.add_parser("interactive",
                             help="the human flow (also: no arguments)")
    sub.add_parser("selftest", help="build a fixture tree and verify the "
                                    "install/uninstall round trip")

    verbed = [s_scan, s_list, s_inter]
    for verb, helptext in (("install", "install components"),
                           ("uninstall", "remove components")):
        s = sub.add_parser(verb, help=helptext)
        s.add_argument("--component", action="append", default=[],
                       metavar="<module>/<component>")
        s.add_argument("--module", action="append", default=[], metavar="NAME")
        if verb == "install":
            s.add_argument("--harness", default=",".join(HARNESSES),
                           help="comma-separated subset of "
                                + ",".join(HARNESSES))
            s.add_argument("--guidance-basis", default=None,
                           choices=(*GUIDANCE_NAMES, BASIS_NONE),
                           help="which root guidance file you author; the "
                                "other is generated from it (D13). Persisted "
                                "— pass it once. Default: whatever the state "
                                "file holds; unset means no mirror and no "
                                "prompt.")
            s.add_argument("--guidance-exclude", default=None,
                           metavar="A,B",
                           help="comma-separated root-relative paths the "
                                "recursive guidance mirror skips (D13). "
                                "Persisted; passing it REPLACES the recorded "
                                f"list. {'/'.join(GUIDANCE_ALWAYS_EXCLUDED)} is "
                                "always skipped, as are nested git repos.")
        s.add_argument("--dry-run", action="store_true")
        s.add_argument("--json", action="store_true")
        verbed.append(s)
    for s in verbed:
        tree_flags(s, on_verb=True)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    as_json = bool(getattr(args, "json", False))

    if args.verb == "selftest":
        return selftest()

    if args.target is None:
        target, why = discover_target(Path.cwd())
        print(f"target: {target}  (discovered by {why}; pass --target to "
              f"override)", file=sys.stderr)
    else:
        target = Path(args.target).expanduser()
    repo_tree = Path(__file__).resolve().parent
    mirror_tree = (Path(args.mirror_tree).expanduser() if args.mirror_tree
                   else target / ".rbtv" / "mirror")

    try:
        catalog, shadowed = scan_all(mirror_tree, repo_tree)

        if args.verb in (None, "interactive"):
            if as_json:
                raise Refuse("usage", "interactive mode has no --json output")
            return interactive(target, catalog)

        if args.verb == "scan":
            data = do_scan(catalog, shadowed)
            print(json.dumps(data, indent=2)) if as_json else print_scan(data)
            return 0

        if args.verb == "list":
            data = do_list(target)
            if as_json:
                print(json.dumps(data, indent=2))
            else:
                comps = data["components"]
                basis = data["guidance_basis"] or "(unset — no mirror)"
                print(f"target: {data['target']}  marker: {data['marker']}  "
                      f"guidance basis: {basis}")
                if not comps:
                    print("nothing installed by install2.py")
                for cid in sorted(comps):
                    rec = comps[cid]
                    print(f"  {cid}  [{rec['tree']}]  "
                          f"harnesses={','.join(rec['harnesses'])}  "
                          f"files={len(rec['files'])}")
                for claim in data["shared_claims"]:
                    print(f"  ~ {claim}")
            return 0

        if not args.component and not args.module:
            parser.error(f"{args.verb} needs --component or --module")
        picked = resolve_selection(
            catalog, args.component, args.module,
            book=(read_state(target).get("components")
                  if args.verb == "uninstall" else None))

        if args.verb == "install":
            harnesses = _parse_harnesses(args.harness)
            if not harnesses:
                raise Refuse("harness-unknown", "--harness selected no harness")
            excludes = (None if args.guidance_exclude is None else
                        [p for p in args.guidance_exclude.split(",") if p.strip()])
            data = do_install(target, catalog, picked, harnesses, args.dry_run,
                              guidance_basis=args.guidance_basis,
                              guidance_excludes=excludes)
        else:
            data = do_uninstall(target, catalog, picked, args.dry_run)
        print(json.dumps(data, indent=2)) if as_json else print_result(data)
        return 0

    except Refuse as exc:
        if as_json:
            print(json.dumps(exc.payload(), indent=2))
        else:
            print(f"REFUSED [{exc.code}] {exc.message}", file=sys.stderr)
            if exc.path:
                print(f"  at: {exc.path}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ncancelled", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
