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

COEXISTENCE. `install.py` + `admin/install/` are untouched and keep working.
This tool never reads or writes their state file (`rbtv.json` at the target
root); its own book is `{target}/.rbtv/config/install.json`. It tolerates files
at the install root it did not write — see D6 and D12.

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

D2  WHAT A COMPONENT IS — a directory at depth 1 or 2 under a tree root that
    holds `component.md` or `exposure.csv`. Its id is its tree-relative posix
    path (`meta/planning`, `browse`); its module is the first segment. Depth 1
    is not theoretical: today `.rbtv/mirror/browse/` is a component at a tree
    root and `<repo>/ignite/exposure.csv` sits at a module root (both flagged
    INTERIM in their own headers). `module.md` is NOT the marker — it exists
    nowhere on either real tree.

D3  TREES + PRECEDENCE — two roots, scanned together: `mirror` =
    `{target}/.rbtv/mirror`, `repo` = the directory holding this file. Both
    overridable (`--mirror-tree`, `--repo-tree`). On the same id in both, the
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

D8  `agents.md` AND THE ROOT GUIDANCE SURFACE — this installer NEVER writes the
    target's hand-authored root guidance file. Instead every `agents.md` row and
    every `rule` copy is named in ONE installer-owned, prefix-named file,
    `.agents/rbtv2-exposure.md`, carrying CMP-12's forced-read preamble (kimi
    gets the enumerated Step-0 the matrix requires). The run reports the single
    line to add to the root guidance file.

D13 THE GUIDANCE MIRROR (owner ruling 9, 2026-08-10 — amends D8) — one of
    `CLAUDE.md` / `AGENTS.md` at the install root is the BASIS (hand-authored,
    NEVER written by this installer); the OTHER is generated FROM it so the
    harnesses that read the other name see the same guidance. The basis is asked
    once in `interactive`, settable/overridable by `--guidance-basis`, and
    persisted as `guidance_basis` in the state file — so later runs never re-ask.
    UNSET IS THE DEFAULT AND MEANS NO MIRROR: a non-interactive run never
    prompts, never guesses a basis, and refuses a basis value outside the two
    names. The generated mirror is a normal installer-owned file — booked,
    collision-gated (a mirror file that exists and is not in our book, e.g. one
    the old installer's `model_mirror` renders, refuses the run pre-write) and
    removed on full uninstall.

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

    NOT PORTED — the old driver's root forced-read PREAMBLE. D8 already puts the
    forced read in `.agents/rbtv2-exposure.md` and reports the ONE pointer line
    for the human to place in the basis; the pointer therefore lives IN the
    basis and mirrors automatically. Recursion does not change that: the old
    driver prepended its preamble at the root only, which is exactly where the
    basis-carried pointer already sits.

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

D12 THE `rbtv2-` PREFIX (owner amendment, 2026-08-09) — every NAMED artifact
    this installer creates carries the `rbtv2-` prefix, and every delete path
    filters on that prefix AND the book, never on directory membership. The old
    installer sweeps `.claude/{rules,commands,agents,skills}` for names starting
    `rbtv-` (`admin/install/installer/generator.py::clear_previous_install`);
    `"rbtv2-".startswith("rbtv-")` is False, so neither installer can sweep the
    other's work. Files that CANNOT carry a prefix — the shared config files of
    D7 — translate the rule to key/block ownership: a JSON file is edited at the
    exact key paths the book records (`mcpServers.<name>`, `hooks.<event>`, …)
    and a text file through a fenced `rbtv2:start … rbtv2:end` block; uninstall
    removes exactly those keys or that block and deletes the file ONLY when
    nothing at all is left in it.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import sys
import tempfile
from pathlib import Path

VERSION = "2.0.0-coexistence"
PREFIX = "rbtv2-"                       # D12 — every named artifact carries it
EXPOSURE_NAME = "exposure.csv"
COMPONENT_NAME = "component.md"
STATE_REL = Path(".rbtv") / "config" / "install.json"
GUIDANCE_REL = f".agents/{PREFIX}exposure.md"
FENCE_ID = "rbtv2"

# D13 — basis → the mirror rendered FROM it. Keys are the only accepted basis
# values; `none` (or an absent key) means no mirror at all.
GUIDANCE_MIRROR = {"CLAUDE.md": "AGENTS.md", "AGENTS.md": "CLAUDE.md"}
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
# install-root-relative; `{name}` is the PREFIXED part-id (D12). None = this
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
        "opencode": ".agents/behavior-rules/{name}.md",
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
    return (path / COMPONENT_NAME).is_file() or (path / EXPOSURE_NAME).is_file()


def scan_tree(root: Path, tree: str) -> dict[str, dict]:
    """Every component under one tree root, by id (D2). {} when the root is absent."""
    found: dict[str, dict] = {}
    if not root.is_dir():
        return found

    def record(dir_path: Path) -> None:
        rel = dir_path.relative_to(root).as_posix()
        found[rel] = {
            "id": rel,
            "tree": tree,
            "tree_root": str(root),
            "module": rel.split("/")[0],
            "component": rel.split("/")[-1],
            "path": str(dir_path),
            "manifest": (dir_path / EXPOSURE_NAME).is_file(),
        }

    for top in sorted(root.iterdir()):
        if not top.is_dir() or top.name.startswith("."):
            continue
        if _is_component_dir(top):
            record(top)
            continue
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


def _content_for(rel: str, method: str, part: str, desc: str, entry: str,
                 comp_dir: Path, entry_rel: str) -> str:
    if method == "rule":
        # Verbatim copy — CMP-12's fallback row is a mirror, not a pointer.
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


def _guidance_index(agents_parts: list[tuple[str, str, str]],
                    rule_parts: list[tuple[str, str]]) -> str:
    """The installer-owned guidance surface (D8), itself prefix-named (D12).

    Carries CMP-12's fallback mechanics for the harnesses that auto-inject no
    rule folder: the read is FORCED by naming each file, and kimi additionally
    gets the mandatory enumerated Step-0 (bulk reads truncate the
    alphabetically-last rules).
    """
    out = ["<!-- Generated by install2.py — regenerated on every install/",
           "     uninstall, never hand-edited. Point your workspace guidance",
           "     file (CLAUDE.md / AGENTS.md) at this file with one line. -->",
           "", "# rbtv exposure — installed components", ""]
    if rule_parts:
        out += [
            "## Step 0 — MANDATORY, before anything else",
            "",
            "Read EACH of these behavior-rule files, one at a time, IN THIS "
            "ORDER. They are always-on rules; no harness here auto-injects the "
            "folder, so this enumeration is the read. Do not bulk-read them — "
            "a bulk read truncates the last entries.",
            "",
        ]
        for i, (pid, desc) in enumerate(rule_parts, 1):
            suffix = f" — {desc}" if desc else ""
            out.append(f"{i}. `.agents/behavior-rules/{pid}.md`{suffix}")
        out.append("")
    if agents_parts:
        out += ["## Guidance parts", ""]
        for pid, desc, entry in agents_parts:
            suffix = f" — {desc}" if desc else ""
            out.append(f"- **{pid}**: read `{entry}`{suffix}")
        out.append("")
    return "\n".join(out)


# ── guidance mirror (D13) ───────────────────────────────────────────────────

def resolve_basis(stored, override: str | None) -> str | None:
    """The basis in force for this run: the override when one was passed, else
    what the book holds. Returns None for "no mirror"; refuses anything that is
    neither a known basis name nor `none` — including a hand-edited book."""
    value = override if override is not None else stored
    if value is None or value == BASIS_NONE or value == "":
        return None
    if value not in GUIDANCE_MIRROR:
        raise Refuse(
            "guidance-basis-invalid",
            f"guidance basis {value!r} is neither {BASIS_NONE!r} nor one of "
            + " · ".join(GUIDANCE_MIRROR)
            + " — refusing before any write (D13)")
    return value


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


def plan_mirror(target: Path, basis: str | None,
                excludes: list[str] | tuple[str, ...] = ()
                ) -> tuple[dict[str, str], frozenset[str], list[str]]:
    """The mirror files the basis implies, one beside EVERY basis file in the
    tree (D13, recursive). Returns `(files, bases, stripped)` — `bases` is the
    set of basis paths that must never be written or deleted; `stripped` names
    the bases whose own generated banner was removed before mirroring."""
    if basis is None:
        return {}, frozenset(), []
    root_source = target / basis
    if not root_source.is_file():
        other = GUIDANCE_MIRROR[basis]
        raise Refuse(
            "guidance-basis-missing",
            f"the recorded guidance basis {basis!r} does not exist at the "
            "install root, so there is nothing to mirror. Recover with ONE of: "
            f"restore {basis}; or `--guidance-basis {other}` to make the file "
            f"you do have the basis; or `--guidance-basis {BASIS_NONE}` to turn "
            "the mirror off. Nothing was written",
            str(root_source))
    mirror = GUIDANCE_MIRROR[basis]
    files: dict[str, str] = {}
    bases: set[str] = set()
    stripped: list[str] = []
    for source in walk_bases(target, basis, excludes):
        rel = source.relative_to(target).as_posix()
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
        text = (f"<!-- GENERATED by install2.py — DO NOT EDIT.\n"
                f"     {mirror} mirrors {rel}, per the guidance basis recorded "
                f"in {STATE_REL.as_posix()}.\n"
                f"     Edit {rel}; re-run the installer to refresh this file. "
                "-->\n\n") + body
        mrel = (source.parent / mirror).relative_to(target).as_posix()
        files[mrel] = text if text.endswith("\n") else text + "\n"
        bases.add(rel)
    return files, frozenset(bases), sorted(stripped)


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
    report: dict = {"skipped_inventory_rows": [], "no_realization": []}

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

    for cid in sorted(records):
        rec = records[cid]
        comp = catalog.get(cid)
        if comp is None:
            raise Refuse(
                "component-vanished",
                f"component {cid!r} is recorded as installed but no longer "
                f"exists under {rec.get('tree_root')!r} — restore the tree, or "
                "uninstall it with the tree present, before this target can be "
                "rebuilt",
                str(rec.get("tree_root", "")))
        comp_dir = Path(comp["path"])
        harnesses = [h for h in HARNESSES if h in rec["harnesses"]]

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
            named = PREFIX + pid

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
                    # D12: the server registration is a NAMED artifact.
                    key = PREFIX + name
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

            realized = 0
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
                realized += 1
            if method == "rule" and realized:
                rule_parts.append((named, desc))

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

    if agents_parts or rule_parts:
        files[GUIDANCE_REL] = _guidance_index(agents_parts, rule_parts)
        owners[GUIDANCE_REL] = ["<aggregate>"]

    report["shared_files"] = sorted({c["path"] for c in claims})
    report["guidance_pointer"] = (
        f"Read `{GUIDANCE_REL}` and follow it." if GUIDANCE_REL in files else ""
    )
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
    state["prefix"] = PREFIX
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

    collisions = sorted(rel for rel in files
                        if rel not in ours_files and (target / rel).exists())
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
                   if rel.rsplit("/", 1)[-1] in GUIDANCE_MIRROR]
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

    stale_files = sorted(ours_files - set(files) - protect)
    planned_claims = {_claim_id(c["path"], c["key"]) for c in claims}
    stale_claims = sorted(ours_claims - planned_claims)

    if dry_run:
        return {"written": [], "skipped": sorted(files), "deleted": stale_files,
                "shared": sorted(planned_claims),
                "shared_removed": stale_claims, "dry_run": True}

    written, skipped = [], []
    for rel in sorted(files):
        path = target / rel
        if path.is_file() and path.read_text(encoding="utf-8") == files[rel]:
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[rel], encoding="utf-8", newline="\n")
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
            "dry_run": False}


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
                      modules: list[str]) -> list[str]:
    picked: list[str] = []
    for cid in components:
        if cid not in catalog:
            raise Refuse(
                "component-unknown",
                f"no component {cid!r} on either tree — run `scan` to see what "
                "is installable")
        picked.append(cid)
    for module in modules:
        hits = [cid for cid, c in catalog.items() if c["module"] == module]
        if not hits:
            raise Refuse(
                "module-unknown",
                f"no module {module!r} on either tree — run `scan` to see what "
                "is installable")
        picked += hits
    return sorted(set(picked))


def do_scan(catalog: dict[str, dict], shadowed: list[dict]) -> dict:
    entries = []
    for cid in sorted(catalog):
        c = catalog[cid]
        rows = exposure_rows(c) if c["manifest"] else []
        entries.append({
            "id": cid, "tree": c["tree"], "module": c["module"],
            "manifest": c["manifest"],
            "methods": sorted({(r.get("method") or "").strip() for r in rows
                               if (r.get("part-id") or "").strip()}),
            "parts": len([r for r in rows if (r.get("part-id") or "").strip()]),
            "note": "" if c["manifest"] else "component has no exposure manifest",
        })
    return {"ok": True, "components": entries, "shadowed": shadowed,
            "no_manifest": [e["id"] for e in entries if not e["manifest"]]}


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
                report: dict, override: str | None,
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
    mirrors, bases, stripped = plan_mirror(target, basis, excludes)
    for rel, content in mirrors.items():
        files[rel] = content
        owners[rel] = ["<aggregate>"]
    report["guidance_mirror"] = (
        {"basis": basis, "mirror": GUIDANCE_MIRROR[basis],
         "count": len(mirrors), "excludes": excludes,
         "banner_stripped": stripped} if basis
        else {"basis": None, "mirror": None})
    return bases


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
                          guidance_excludes)
    result = apply(target, files, claims, state, dry_run, protect)
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
            protect = _add_mirror(target, state, files, owners, report, None)
        except Refuse as exc:
            # Removing a component must NEVER be blocked by a mirror problem
            # (a deleted basis, a hand-edited book). Skip the replan, and keep
            # EVERY guidance file the book holds, under either name and at any
            # depth, off the delete set — un-managed on disk beats deleted, and
            # the next install re-books whatever is real.
            protect = frozenset(GUIDANCE_MIRROR) | frozenset(
                rel for rel in known_files(state)
                if rel.rsplit("/", 1)[-1] in GUIDANCE_MIRROR)
            report["guidance_mirror"] = {"basis": None, "mirror": None,
                                         "skipped": exc.code}
    result = apply(target, files, claims, state, dry_run, protect)
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
            "prefix": PREFIX,
            "guidance_basis": state.get("guidance_basis"),
            "components": state.get("components") or {},
            "guidance_files": state.get("guidance_files") or [],
            "shared_claims": state.get("shared_claims") or []}


# ── human output ────────────────────────────────────────────────────────────

def print_scan(data: dict) -> None:
    print(f"{'COMPONENT':<34} {'TREE':<7} {'PARTS':>5}  METHODS / NOTE")
    for e in data["components"]:
        note = e["note"] or ", ".join(e["methods"]) or "(manifest has no rows)"
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
    for row in report.get("skipped_inventory_rows") or []:
        print(f"  · skipped `{row['method']}` row {row['component']}/"
              f"{row['part']} ({row['entry_point']}) — inventory only, "
              "mints nothing")
    for row in report.get("no_realization") or []:
        print(f"  · {row['harness']} has no realization for method "
              f"{row['method']} ({row['component']}/{row['part']}) — nothing "
              "minted")
    mirror = report.get("guidance_mirror")
    if mirror and mirror.get("skipped"):
        print(f"  · guidance mirror: SKIPPED ({mirror['skipped']}) — not "
              "re-rendered; both root guidance files were left untouched. Fix "
              "the basis on the next install.")
    elif mirror and mirror.get("basis"):
        print(f"  · guidance mirror: {mirror['count']} × {mirror['mirror']} "
              f"generated from {mirror['basis']} (one beside every "
              f"{mirror['basis']} in the tree; no basis file is ever written)"
              + (f"; excluding {', '.join(mirror['excludes'])}"
                 if mirror.get("excludes") else ""))
        if mirror.get("banner_stripped"):
            print("    a generated banner was stripped from these bases before "
                  "mirroring (never stacked): "
                  + ", ".join(mirror["banner_stripped"]))
    elif mirror:
        print("  · guidance mirror: OFF — no basis recorded. Set one with "
              "`--guidance-basis CLAUDE.md|AGENTS.md` (D13).")
    if report.get("guidance_pointer"):
        print("\nAdd this line to the workspace guidance file "
              "(CLAUDE.md / AGENTS.md) — this installer never writes it:\n"
              f"    {report['guidance_pointer']}")


# ── interactive ─────────────────────────────────────────────────────────────

def interactive(target: Path, catalog: dict[str, dict]) -> int:
    print("rbtv installer (install2) — interactive\n")
    answer = input(f"Target workspace [{target}]: ").strip()
    if answer:
        target = Path(answer).expanduser()
        catalog, _ = scan_all(target / ".rbtv" / "mirror",
                              Path(__file__).resolve().parent)
    if not target.is_dir():
        raise Refuse("target-missing", f"target is not a directory: {target}")

    installable = [cid for cid in sorted(catalog) if catalog[cid]["manifest"]]
    if not installable:
        print("Nothing installable — no component on either tree carries an "
              "exposure manifest.")
        return 1
    installed = set(read_state(target).get("components") or {})
    print("\nComponents:\n")
    for i, cid in enumerate(installable, 1):
        mark = "*" if cid in installed else " "
        print(f" {mark}{i:>3}. {cid}  [{catalog[cid]['tree']}]")
    for cid in sorted(catalog):
        if not catalog[cid]["manifest"]:
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
        braw = input(f"Basis [{'/'.join(GUIDANCE_MIRROR)}/{BASIS_NONE}] "
                     f"[{BASIS_NONE}]: ").strip()
        basis = resolve_basis(None, braw or BASIS_NONE) or BASIS_NONE

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
        "part-id,part-kind,method,rbtv-cli,entry-point,description\n"
        "fixskill,capability,skill,exhibit,skill-entry.md,A fixture skill: with a colon\n"
        "fixcmd,workflow,command,,cmd-entry.md,\n"
        "fixrule,reference,rule,,rule-entry.md,the fixture rule\n"
        "fixagent,prompt,sub-agent,,agent-entry.md,\n"
        "fixhook,capability,hook,,hooks.json,\n"
        "fixmcp,plugin/MCP,config,,mcp.json,\n"
        "fixguide,prompt,agents.md,exhibit,guide.md,\n"
        "fixtool,tool,path,,tool/thing.py,\n"
        "fixpool,prompt,pool,,guide.md,a pool member — shopped, never minted\n",
        encoding="utf-8")

    bare = root / "fixmod" / "barecomp"
    bare.mkdir(parents=True)
    (bare / COMPONENT_NAME).write_text("# barecomp — no manifest\n",
                                       encoding="utf-8")

    bad = root / "badmod" / "badcomp"
    bad.mkdir(parents=True)
    (bad / COMPONENT_NAME).write_text("# badcomp\n", encoding="utf-8")
    (bad / "x.md").write_text("x\n", encoding="utf-8")
    (bad / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description\n"
        "boom,capability,telepathy,,x.md,\n", encoding="utf-8")


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
        check("discovers all three components",
              sorted(catalog) == ["badmod/badcomp", "fixmod/barecomp",
                                  "fixmod/goodcomp"], str(sorted(catalog)))
        check("reports the manifest-less component",
              data["no_manifest"] == ["fixmod/barecomp"],
              str(data["no_manifest"]))

        print("\nD12 — the old installer's sweep cannot reach our names")
        check("'rbtv2-x'.startswith('rbtv-') is False",
              not (PREFIX + "x").startswith("rbtv-"))

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
            f".claude/skills/{PREFIX}fixskill/SKILL.md",
            f".agents/skills/{PREFIX}fixskill/SKILL.md",
            f".claude/commands/{PREFIX}fixcmd.md",
            f".codex/prompts/{PREFIX}fixcmd.md",
            f".opencode/commands/{PREFIX}fixcmd.md",
            f".claude/rules/{PREFIX}fixrule.md",
            f".agents/behavior-rules/{PREFIX}fixrule.md",
            f".claude/agents/{PREFIX}fixagent.md",
            f".opencode/agents/{PREFIX}fixagent.md",
            GUIDANCE_REL,
        }
        shared = {".claude/settings.json", ".codex/hooks.json", ".mcp.json",
                  ".codex/config.toml", "opencode.json"}
        on_disk = {p.relative_to(target).as_posix()
                   for p in target.rglob("*") if p.is_file()}
        want = expect | shared | set(legacy) | {STATE_REL.as_posix()}
        check("every CMP-12 realization landed, prefixed, and nothing else",
              on_disk == want,
              f"missing={sorted(want - on_disk)} extra={sorted(on_disk - want)}")
        check("every named artifact carries the rbtv2- prefix",
              all(Path(rel).name.startswith(PREFIX)
                  or Path(rel).parent.name.startswith(PREFIX)
                  for rel in expect), str(sorted(expect)))
        check("`path` and `pool` rows minted nothing",
              not (target / f".claude/skills/{PREFIX}fixtool").exists()
              and not (target / f".claude/skills/{PREFIX}fixpool").exists()
              and sorted(r["method"] for r
                         in res["report"]["skipped_inventory_rows"])
              == ["path", "pool"],
              str(res["report"]["skipped_inventory_rows"]))
        check("skill loader carries a YAML-safe description",
              '"A fixture skill: with a colon"'
              in (target / f".claude/skills/{PREFIX}fixskill/SKILL.md").read_text())
        check("rule copied VERBATIM",
              (target / f".claude/rules/{PREFIX}fixrule.md").read_text()
              == (tree / "fixmod/goodcomp/rule-entry.md").read_text())
        check("guidance index forces the rule read + names the agents.md part",
              "Step 0" in (target / GUIDANCE_REL).read_text()
              and f"`.agents/behavior-rules/{PREFIX}fixrule.md`"
              in (target / GUIDANCE_REL).read_text()
              and f"{PREFIX}fixguide" in (target / GUIDANCE_REL).read_text())
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
              == sorted([PREFIX + "fix", "foreign"]))
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
                  _claim_id(".mcp.json", ["mcpServers", PREFIX + "fix"]),
                  _claim_id("opencode.json", ["mcp", PREFIX + "fix"]),
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
        (fresh / f".claude/rules/{PREFIX}fixrule.md").write_text(
            "hand-placed\n", encoding="utf-8")
        (fresh / ".mcp.json").write_text(json.dumps(
            {"mcpServers": {PREFIX + "fix": {"url": "https://squatter.invalid"}}}),
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
                  f".claude/rules/{PREFIX}fixrule.md" in exc.message
                  and ".mcp.json::mcpServers." + PREFIX + "fix" in exc.message,
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
                  [GUIDANCE_REL, "AGENTS.md", "sub/AGENTS.md",
                   "sub/deep/AGENTS.md"]),
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
                    "install.py: every artifact is named `rbtv2-*`, state lives "
                    "at {target}/.rbtv/config/install.json, and nothing outside "
                    "that book is ever written or deleted.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="exit codes: 0 success · 1 refusal · 2 usage")
    def tree_flags(dest, *, on_verb: bool) -> None:
        # The three flags are accepted BEFORE and AFTER the verb. The
        # verb-level copies default to SUPPRESS so they only set the
        # attribute when explicitly given — otherwise argparse would
        # overwrite a pre-verb value with the verb-level default.
        sup = argparse.SUPPRESS
        dest.add_argument("--target", default=(sup if on_verb else "."),
                          help="install root (default: cwd)")
        dest.add_argument("--mirror-tree", default=(sup if on_verb else None),
                          help="workspace mirror tree "
                               "(default: {target}/.rbtv/mirror)")
        dest.add_argument("--repo-tree", default=(sup if on_verb else None),
                          help="rbtv repo tree (default: this file's "
                               "directory)")

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
                           choices=(*GUIDANCE_MIRROR, BASIS_NONE),
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

    target = Path(args.target).expanduser()
    repo_tree = (Path(args.repo_tree).expanduser() if args.repo_tree
                 else Path(__file__).resolve().parent)
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
                print(f"target: {data['target']}  prefix: {data['prefix']}  "
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
        picked = resolve_selection(catalog, args.component, args.module)

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
