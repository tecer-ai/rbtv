"""driver — the rbtv mirror driver's public render/uninstall orchestrator.

The driver renders, into a target workspace, the artifacts an elected set of CLI
worker packages (codex / kimi / opencode) consumes — the shared ``.agents/``
skill+rule library and per-model config dirs — from ``.claude/`` alone, with no
manifest reads.  Re-running changes nothing; uninstalling a worker removes only
what no remaining worker needs.

GUIDANCE FILES ARE RETIRED (owner ruling ``d-hard-guard-retire-model-mirror``,
2026-08-10): this driver renders NO ``AGENTS.md``/``QWEN.md`` — see step 2 of
``render`` and the note at the head of ``guidance.py``.  Only the teardown side
still knows the word (legacy records from a pre-retirement render).

This package composes the render legs:
  - ``library.py``       → ``.agents/behavior-rules/`` + ``.agents/skills/``
  - ``config_assets.py`` → ``.codex/`` / ``.kimi/`` config dirs (a package with
    no ``mirror-assets`` seed, e.g. opencode, has ``config_dir=None`` and renders
    no config dir)
  - ``guidance.py``      → retired; exports only ``ALWAYS_EXCLUDED_PREFIXES``
and ``state.py`` (the ``model_mirror`` block of ``rbtv.json`` + ref-counted
deletion).

Public API
----------
    render(target_root, elected, *, check) -> RenderResult
    uninstall(target_root, deselected, remaining_elected) -> UninstallResult

Source-agnostic by design: NO module-manifest.json / sb-os.json read anywhere.
The per-package facts below (config dir, guidance-group owner) are the driver's
OWN constants — they mirror the spec's "Per-model facts" table, not a manifest.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import config_assets, guidance, library, state

# ---------------------------------------------------------------------------
# Per-package facts (the driver's own constants — NOT a manifest read)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PackageFacts:
    """Static, source-agnostic facts about one CLI worker package."""

    config_dir: str | None  # config tree rendered into the target root; None = the package ships no mirror-assets config
    guidance_owner: str     # owner tag of the guidance-filename group this package USED to render — kept for ref-counted teardown of legacy records only (rendering is retired)


#: Packages the driver knows how to mirror.  ``claude-code-cli`` is intentionally
#: absent — it loads ``CLAUDE.md`` natively and is mirror-less (it is skipped,
#: never an error).
PACKAGE_FACTS: dict[str, PackageFacts] = {
    "codex-cli": PackageFacts(
        config_dir=".codex",
        guidance_owner="agents-md",
    ),
    "kimi-code-cli": PackageFacts(
        config_dir=".kimi",
        guidance_owner="agents-md",
    ),
    "opencode": PackageFacts(
        config_dir=None,        # opencode ships no mirror-assets — providers live in the machine-global opencode config
        guidance_owner="agents-md",
    ),
}

#: Packages that load their guidance file natively and need no mirror.
NATIVE_PACKAGES: frozenset[str] = frozenset({"claude-code-cli"})

#: The shared worker library dir rendered once for any elected worker.
SHARED_LIBRARY_DIR = ".agents"


def _mirrorable(packages) -> list[str]:
    """Return the elected packages that the driver actually mirrors.

    Drops native packages (claude-code-cli) and unknown ids silently — an unknown id
    is not the driver's to validate (the installer owns selection); the driver
    simply renders nothing for it.
    """
    return [p for p in packages if p in PACKAGE_FACTS]


def owner_to_guidance_group() -> dict[str, str]:
    """Map every known package id → its guidance-group owner tag.

    Handed to ``state.plan_uninstall_deletions`` so ref-counting can decide
    whether any remaining package still needs a guidance-filename group.
    """
    return {pkg: facts.guidance_owner for pkg, facts in PACKAGE_FACTS.items()}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class RenderResult:
    """Outcome of a ``render`` call."""

    managed_files: list[dict] = field(default_factory=list)
    skipped_commands: list[str] = field(default_factory=list)
    state_changed: bool = False
    stale: bool = False  # only meaningful in check mode: any drift detected
    # Check mode only: the managed files whose CONTENT drifted from their source
    # (present on disk but out of date). Empty on a write run.
    stale_paths: list[str] = field(default_factory=list)
    state_created: bool = False  # True when no model_mirror block existed before this render
    files_written: bool = False  # True when at least one managed file was written to disk


@dataclass
class UninstallResult:
    """Outcome of an ``uninstall`` call."""

    deleted: list[str] = field(default_factory=list)
    spared: list[str] = field(default_factory=list)
    #: Recorded managed files dropped from the delete set because they lie under
    #: ``guidance.ALWAYS_EXCLUDED_PREFIXES`` — someone else's files that a
    #: pre-exclusion render had recorded. Left on disk AND dropped from state.
    #: Distinct from ``spared`` (hand-authored, banner-less): these DO carry the
    #: sentinel, so the banner-guard cannot protect them.
    protected: list[str] = field(default_factory=list)
    kept_records: list[dict] = field(default_factory=list)
    #: Known worker dirs that survived this uninstall because they still hold
    #: files rbtv did not create (tool-written leftovers / prior-install orphans).
    #: Each entry: ``{"dir": <workspace-rel posix>, "files": [<rel posix>, ...]}``.
    #: Surfaced to the owner so they can delete the dir by hand — rbtv never
    #: deletes a file it did not create (per the owner's delete-managed-then-prune
    #: policy), so a foreign file legitimately keeps its dir alive.
    leftover_dirs: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _mtime(path: Path) -> "float | None":
    """Return the mtime of *path* if it exists, else None."""
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _path_under_any_exclusion(rel_path: str, excluded_prefixes: list[str]) -> bool:
    """True if *rel_path* equals or lies under any normalized excluded prefix.

    Prefix semantics: ``rel == prefix`` OR ``rel.startswith(prefix + "/")``,
    applied to a recorded file's workspace-relative path (e.g.
    ``.rbtv/goals/g/AGENTS.md`` under prefix ``.rbtv/goals``).  Used by
    ``uninstall`` to protect legacy guidance records it must never delete.
    """
    rel_norm = state._normalize_rel_path(rel_path)
    for prefix in excluded_prefixes:
        prefix = state._normalize_rel_path(prefix)
        if not prefix:
            continue
        if rel_norm == prefix or rel_norm.startswith(prefix + "/"):
            return True
    return False


# ---------------------------------------------------------------------------
# Public API — render
# ---------------------------------------------------------------------------


def render(
    target_root: Path | str,
    elected,
    *,
    check: bool = False,
    excluded_paths: list[str] | None = None,
) -> RenderResult:
    """Render every artifact the ``elected`` worker set consumes into ``target_root``.

    For each elected (mirrorable) package:
      - the shared ``.agents/`` library renders once (when any worker is elected);
      - the package's config dir renders.

    NO guidance file (``AGENTS.md``/``QWEN.md``) is ever written: that leg is
    retired (``d-hard-guard-retire-model-mirror``, 2026-08-10) — the run prints a
    one-line skip instead.

    The merged managed-file set (deduped by ``path``) is written to
    ``rbtv.json``'s ``model_mirror`` block — and ONLY that block; every other key
    is preserved.

    Parameters
    ----------
    target_root:
        Workspace root.  All managed-file paths are relative to it; the state
        file is ``{target_root}/rbtv.json``.
    elected:
        Iterable of package ids to render (native ids like ``claude-code-cli`` and
        unknown ids are skipped silently).
    check:
        Read-only drift mode — renders nothing, writes nothing; reports whether
        any managed file (or the state block) is missing/stale.  ``RenderResult.stale``
        is True on any drift.
    excluded_paths:
        Workspace-relative path prefixes, preserved in the ``model_mirror`` state
        block for compatibility.  INERT for rendering since the guidance retirement
        (they only ever constrained the ``CLAUDE.md`` walk); the library and config
        legs render fixed paths.  When None, the recorded value is reused.

    Returns
    -------
    RenderResult
    """
    target_root = Path(target_root).resolve()
    packages = _mirrorable(elected)

    # --- Pre-render: read prior state block (for excluded_paths + verb detection) ---
    prior_doc = state.read_document(target_root)
    prior_block = prior_doc.get(state.MIRROR_KEY) if isinstance(
        prior_doc.get(state.MIRROR_KEY), dict) else None
    prior_block_exists = prior_block is not None

    if excluded_paths is None:
        excluded_paths = (prior_block or {}).get("excluded_paths", [])

    result = RenderResult()

    if not packages:
        # No mirrorable worker elected — render nothing.  In a non-check run this
        # is equivalent to a full uninstall of the mirror; we leave existing
        # state untouched here (the installer drives deselection via uninstall()).
        return result

    # Snapshot managed-file mtimes BEFORE rendering so we can detect
    # whether any file was refreshed (content changed on disk) even when
    # the managed-file record set stays identical (same paths, same owners).
    prior_managed_paths: set[str] = {
        r["path"] for r in (prior_block or {}).get("managed_files", [])
    }
    pre_render_mtimes: dict[str, float | None] = {
        p: (_mtime(target_root / p)) for p in prior_managed_paths
    }

    all_records: list[dict] = []
    stale_any = False

    # Content-drift sink. `_detect_drift` below sees only MISSING files and
    # managed-set changes — never a mirrored file that exists but has fallen
    # behind its source. Each render module appends the paths it found stale so
    # content drift reaches the exit code instead of being printed and dropped.
    content_stale: list[str] = []

    # --- 1. Shared .agents/ library (rendered once when any worker is elected) ---
    rule_records = library.render_behavior_rules(
        target_root, check=check, stale_sink=content_stale
    )
    skill_records, skipped = library.render_skills(
        target_root, check=check, stale_sink=content_stale
    )
    all_records.extend(rule_records)
    all_records.extend(skill_records)
    result.skipped_commands = skipped

    # --- 2. Guidance files — RETIRED, renders nothing ---
    # Owner ruling `d-hard-guard-retire-model-mirror` (2026-08-10,
    # 1-projects/rbtv-sb-merge-refactor-core-build/decisions.md): installer-1 no
    # longer renders ANY guidance file (AGENTS.md / QWEN.md). install2 owns them
    # (d-s17 / d-s17bis) and an election here used to overwrite its output
    # workspace-wide. The render leg was DELETED from guidance.py, not gated —
    # no election, flag or state can bring it back. The skip is announced (once
    # per render) rather than raising, so --mirror stays usable for the live
    # artifacts below.
    print(
        "  guidance files: skipped — installer-1's guidance mirror is retired "
        "(ruling d-hard-guard-retire-model-mirror); the modern installer owns them."
    )

    # --- 3. Per-model config dirs (skipped for a config-less package, e.g. opencode) ---
    for pkg in packages:
        if PACKAGE_FACTS[pkg].config_dir is None:
            continue
        config_records = config_assets.render_config(
            target_root, pkg, check=check, stale_sink=content_stale
        )
        all_records.extend(config_records)

    # --- 3b. Prune-on-exclude: REMOVED with the guidance retirement ---
    # It existed only to delete guidance files orphaned by a newly-excluded path.
    # With rendering retired (see step 2) a render never produces or reaches a
    # guidance file, and DELETING one would be installer-1 claiming ownership it
    # no longer has. Legacy `kind: "guidance"` records simply drop out of
    # managed_files on the next render (they are not in all_records); the files
    # stay on disk for install2 to own. Teardown of installer-1's OWN past output
    # remains available through `uninstall` (banner-guarded).

    # --- 4. Drift detection (check mode) ---
    # Two independent signals, OR-ed: CONTENT drift (a managed file exists but
    # differs from its source — collected by the render modules above) and
    # STATE drift (a managed file is missing, or the expected set changed).
    if check:
        stale_any = _detect_drift(target_root, all_records) or bool(content_stale)

    # --- 5. Detect files-written (post-render, pre-state-write) ---
    # A file was written when: a new path appeared, OR an existing path's mtime
    # advanced (write_if_changed / _write_if_changed_binary touch mtime on write).
    post_paths: set[str] = {r["path"] for r in all_records}
    files_written = False
    if not check:
        new_paths = post_paths - prior_managed_paths
        if new_paths:
            files_written = True
        else:
            for p in post_paths:
                pre = pre_render_mtimes.get(p)
                post = _mtime(target_root / p)
                if pre != post:
                    files_written = True
                    break

    # --- 6. Persist the model_mirror block ---
    changed, persisted = state.write_mirror_block(
        target_root,
        managed=all_records,
        excluded_paths=excluded_paths,
        check=check,
    )

    result.managed_files = persisted
    result.state_changed = changed
    result.state_created = (not prior_block_exists) and (not check)
    result.files_written = files_written
    result.stale = stale_any or (check and changed)
    result.stale_paths = sorted(set(content_stale))
    return result


def _detect_drift(target_root: Path, rendered: list[dict]) -> bool:
    """Return True if any rendered managed file is missing on disk OR the recorded
    state's managed-file set differs from what a render would now produce.

    This is the STATE-level drift signal only. It deliberately does NOT detect
    content drift — a file that exists but no longer matches its source is
    invisible here, because this function never re-composes expected content.
    That half is collected by the render modules into ``render``'s
    ``content_stale`` sink and OR-ed in by the caller; the two together are what
    ``RenderResult.stale`` means. Do not "simplify" by relying on this alone —
    that was the bug where a drifted mirror check-passed with exit 0.
    """
    target_root = Path(target_root).resolve()
    expected_paths = {r["path"] for r in rendered}

    # 1. Any expected file missing on disk?
    for rec in rendered:
        abs_path = target_root / rec["path"]
        if not abs_path.exists():
            return True

    # 2. State drift: recorded managed set vs freshly-expected set.
    recorded_paths = {r["path"] for r in state.managed_files(target_root)}
    if recorded_paths != expected_paths:
        return True

    return False


# ---------------------------------------------------------------------------
# Public API — uninstall
# ---------------------------------------------------------------------------


def _worker_config_dirs() -> dict[str, str]:
    """Map every known mirrorable package id → its config-dir name (``.codex`` …).

    A config-less package (``config_dir=None``, e.g. opencode) is omitted — it has
    no worker dir to render, scan, or surface.
    """
    return {pkg: facts.config_dir for pkg, facts in PACKAGE_FACTS.items() if facts.config_dir is not None}


def _detect_leftover_worker_dirs(
    target_root: Path,
    deselected: list[str],
    remaining_elected: list[str],
) -> list[dict]:
    """Return known worker dirs that survive the uninstall holding non-rbtv files.

    Run AFTER ``state.apply_deletions`` (managed files removed, emptied dirs
    pruned). A worker dir that is still present therefore holds only files rbtv
    did not create — tool-written leftovers or prior-install orphans — which the
    owner's delete-managed-then-prune policy leaves in place. These are surfaced
    so the owner can remove the dir by hand.

    Scope:
      - a config dir (``.codex``/``.kimi``) is in scope when its package
        was deselected and is NOT needed by a remaining elected package;
      - on a FULL teardown (no worker remains) EVERY known config dir plus the
        shared ``.agents/`` library is in scope — so a never-managed stray (e.g. a
        ``.kimi/`` the kimi CLI created without rbtv ever electing it) is surfaced
        by a full ``--mirror --uninstall`` too.

    Each entry is ``{"dir": <rel posix>, "files": [<rel posix>, ...]}``; a dir with
    no remaining files is omitted (it was fully removed or is empty).
    """
    config_dirs = _worker_config_dirs()
    remaining = set(remaining_elected)
    full_teardown = not remaining

    in_scope: set[str] = set()
    for pkg in deselected:
        if pkg in config_dirs and pkg not in remaining:
            in_scope.add(config_dirs[pkg])
    if full_teardown:
        in_scope.update(config_dirs.values())
        in_scope.add(SHARED_LIBRARY_DIR)

    leftovers: list[dict] = []
    for rel_dir in sorted(in_scope):
        dir_path = target_root / rel_dir
        if not dir_path.is_dir():
            continue
        files = sorted(
            f.relative_to(target_root).as_posix()
            for f in dir_path.rglob("*")
            if f.is_file()
        )
        if files:
            leftovers.append({"dir": rel_dir, "files": files})
    return leftovers


def uninstall(
    target_root: Path | str,
    deselected,
    remaining_elected,
) -> UninstallResult:
    """Remove the artifacts a deselected worker set no longer needs.

    Ref-counted by guidance-filename (design §6 / spec Behavior #7):
      - the deselected package's config dir is removed;
      - a guidance-filename group (``AGENTS.md``) is removed ONLY
        when no remaining elected package still maps to it;
      - the shared ``.agents/`` library is removed ONLY when no worker remains;
      - a guidance file lacking the DO-NOT-EDIT banner is SPARED (banner-guard).

    The surviving managed-file records are written back to ``model_mirror``; when
    none remain, the ``model_mirror`` block is dropped entirely.  No other
    ``rbtv.json`` key is touched.

    Parameters
    ----------
    target_root:
        Workspace root (state file is ``{target_root}/rbtv.json``).
    deselected:
        Package ids being removed (e.g. ``["codex-cli"]``).
    remaining_elected:
        Package ids that remain elected after this uninstall.

    Returns
    -------
    UninstallResult
        ``leftover_dirs`` names any known worker dir left on disk because it still
        holds files rbtv did not create (the owner deletes those by hand).
    """
    target_root = Path(target_root).resolve()

    deselected = list(deselected)
    remaining_elected = _mirrorable(remaining_elected)

    state_records = state.managed_files(target_root)

    to_delete, to_keep = state.plan_uninstall_deletions(
        state_records,
        deselected,
        remaining_elected,
        owner_to_guidance_group=owner_to_guidance_group(),
    )

    # A record under ALWAYS_EXCLUDED_PREFIXES is someone else's file that only a
    # PRE-exclusion render could have recorded (the walk no longer emits those
    # paths). On such a workspace an uninstall running before the first
    # post-upgrade render would delete it, and the banner-guard cannot help — the
    # goals-tree scaffold's own router header carries the SAME DO-NOT-EDIT
    # sentinel ``state.BANNER_SENTINEL`` keys on. So drop these from the delete
    # set here: they stay on disk, and — like a spared file — they are dropped
    # from ``managed_files`` (they are not in ``to_keep``), which un-manages them.
    always_excluded = list(guidance.ALWAYS_EXCLUDED_PREFIXES)
    protected = [
        rec for rec in to_delete
        if _path_under_any_exclusion(rec["path"], always_excluded)
    ]
    if protected:
        to_delete = [rec for rec in to_delete if rec not in protected]

    deleted, spared = state.apply_deletions(target_root, to_delete)

    # After deletion + empty-dir prune: any known worker dir still on disk holds
    # only files rbtv did not create. Surface them so the owner can delete the dir
    # by hand (the policy is delete-managed-then-prune; foreign files are never
    # rbtv's to remove).
    leftover_dirs = _detect_leftover_worker_dirs(
        target_root, deselected, remaining_elected
    )

    # A guidance record that was spared (hand-authored, banner-less) must NOT be
    # dropped from state silently as deleted — but it is also no longer ours to
    # manage.  Keep only records that are still on disk and owned: the survivors
    # are to_keep plus any spared guidance files (left as-is, no longer tracked).
    # Spared files are intentionally dropped from managed_files (we don't manage a
    # file we won't overwrite/delete), so kept state == to_keep.
    state.write_managed_records(target_root, to_keep)

    return UninstallResult(
        deleted=deleted,
        spared=spared,
        protected=sorted(rec["path"] for rec in protected),
        kept_records=to_keep,
        leftover_dirs=leftover_dirs,
    )
