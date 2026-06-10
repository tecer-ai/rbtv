"""driver — the rbtv mirror driver's public render/uninstall orchestrator.

The driver renders, into a target workspace, exactly the artifacts an elected set
of CLI worker packages (codex / kimi / qwen) consumes — guidance files beside
every ``CLAUDE.md``, the shared ``.agents/`` skill+rule library, and per-model
config dirs — all from ``.claude/`` + the workspace's ``CLAUDE.md`` files alone,
with no manifest reads.  Re-running changes nothing; uninstalling a worker removes
only what no remaining worker needs.

This package composes the three render legs (already built + committed):
  - ``guidance.py``      → guidance files (``AGENTS.md`` / ``QWEN.md``)
  - ``library.py``       → ``.agents/behavior-rules/`` + ``.agents/skills/``
  - ``config_assets.py`` → ``.codex/`` / ``.kimi/`` / ``.qwen/`` config dirs
and ``state.py`` (the ``model_mirror`` block of ``rbtv.json`` + ref-counted
deletion).

Public API
----------
    render(target_root, elected, *, check) -> RenderResult
    uninstall(target_root, deselected, remaining_elected) -> UninstallResult

Source-agnostic by design: NO module-manifest.json / sb-os.json read anywhere.
The per-package facts below (guidance filename, config dir, banner label,
guidance-group owner) are the driver's OWN constants — they mirror the spec's
"Per-model facts" table and each package's ``mirror-config.yaml`` banner label,
not a manifest.
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

    guidance_filename: str  # sibling file rendered beside each CLAUDE.md
    config_dir: str         # config tree rendered into the target root
    banner_label: str       # interpolated into the DO-NOT-EDIT banner
    guidance_owner: str     # owner tag for the guidance-filename group


#: Packages the driver knows how to mirror.  ``claude-cli`` is intentionally
#: absent — it loads ``CLAUDE.md`` natively and is mirror-less (it is skipped,
#: never an error).  Banner labels are byte-identical to each package's
#: ``mirror-config.yaml`` so a single-package guidance file matches ``mirror.py``.
PACKAGE_FACTS: dict[str, PackageFacts] = {
    "codex": PackageFacts(
        guidance_filename="AGENTS.md",
        config_dir=".codex",
        banner_label="the Codex CLI worker",
        guidance_owner="agents-md",
    ),
    "kimi": PackageFacts(
        guidance_filename="AGENTS.md",
        config_dir=".kimi",
        banner_label="the Kimi CLI worker",
        guidance_owner="agents-md",
    ),
    "qwen": PackageFacts(
        guidance_filename="QWEN.md",
        config_dir=".qwen",
        banner_label="the Qwen Code CLI worker",
        guidance_owner="qwen-md",
    ),
}

#: Packages that load their guidance file natively and need no mirror.
NATIVE_PACKAGES: frozenset[str] = frozenset({"claude-cli"})


def _mirrorable(packages) -> list[str]:
    """Return the elected packages that the driver actually mirrors.

    Drops native packages (claude-cli) and unknown ids silently — an unknown id
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
# Guidance-filename grouping
# ---------------------------------------------------------------------------


def _group_banner_label(filename: str, packages: list[str]) -> str:
    """Compose the banner label for a guidance-filename group.

    When exactly one elected package maps to ``filename`` the label is that
    package's exact ``banner_label`` (guaranteeing byte-identity with
    ``mirror.py`` for the single-package case the byte-identical test exercises).

    When 2+ packages share the filename (e.g. codex + kimi both elect
    ``AGENTS.md``) the group is rendered ONCE, so the label honestly names every
    consuming worker, joined deterministically.
    """
    members = [p for p in packages if PACKAGE_FACTS[p].guidance_filename == filename]
    members.sort()
    labels = [PACKAGE_FACTS[p].banner_label for p in members]
    if len(labels) == 1:
        return labels[0]
    # "the Codex CLI worker and the Kimi CLI worker"
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def _elected_guidance_groups(packages: list[str]) -> dict[str, str]:
    """Return ``{guidance_filename: group_banner_label}`` for the elected set.

    Deduplicates by filename so a shared filename (``AGENTS.md`` for codex∪kimi)
    is rendered exactly once.
    """
    groups: dict[str, str] = {}
    for filename in sorted({PACKAGE_FACTS[p].guidance_filename for p in packages}):
        groups[filename] = _group_banner_label(filename, packages)
    return groups


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
    state_created: bool = False  # True when no model_mirror block existed before this render
    files_written: bool = False  # True when at least one managed file was written to disk


@dataclass
class UninstallResult:
    """Outcome of an ``uninstall`` call."""

    deleted: list[str] = field(default_factory=list)
    spared: list[str] = field(default_factory=list)
    kept_records: list[dict] = field(default_factory=list)


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

    Mirrors the prefix semantics ``guidance.py._is_excluded`` uses (``rel ==
    prefix`` OR ``rel.startswith(prefix + "/")``), applied to a guidance FILE's
    workspace-relative path (e.g. ``sub/x/AGENTS.md`` under prefix ``sub/x``).
    """
    rel_norm = state._normalize_rel_path(rel_path)
    for prefix in excluded_prefixes:
        prefix = state._normalize_rel_path(prefix)
        if not prefix:
            continue
        if rel_norm == prefix or rel_norm.startswith(prefix + "/"):
            return True
    return False


def _prune_newly_excluded_guidance(
    target_root: Path,
    prior_block: dict | None,
    new_records: list[dict],
    excluded_paths: list[str],
) -> list[str]:
    """Delete guidance files orphaned by a NEWLY-excluded path.

    A guidance file that was previously managed (recorded in ``prior_block``'s
    ``managed_files``) but now falls under an excluded prefix — and is therefore
    NOT in the freshly-rendered ``new_records`` set — is a stale orphan: the walk
    skipped it, so ``render`` never refreshes or removes it. Delete it through the
    driver's EXISTING banner-guarded ``state.apply_deletions`` (a hand-authored,
    banner-less file is spared, never destroyed).

    Returns the workspace-relative paths actually deleted. NEVER called in check
    mode (callers gate on ``check``).
    """
    if not prior_block:
        return []

    prior_records = prior_block.get("managed_files", []) or []
    new_paths = {r["path"] for r in new_records}

    orphans = [
        rec
        for rec in prior_records
        if rec.get("kind") == "guidance"
        and rec["path"] not in new_paths
        and _path_under_any_exclusion(rec["path"], excluded_paths)
    ]
    if not orphans:
        return []

    deleted, _spared = state.apply_deletions(target_root, orphans)
    return deleted


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
      - its guidance files render beside every non-excluded ``CLAUDE.md``
        (deduped by guidance filename — ``AGENTS.md`` once for codex∪kimi);
      - the shared ``.agents/`` library renders once (when any worker is elected);
      - the package's config dir renders.

    The merged managed-file set (deduped by ``path``) is written to
    ``rbtv.json``'s ``model_mirror`` block — and ONLY that block; every other key
    is preserved.

    Parameters
    ----------
    target_root:
        Workspace root.  All managed-file paths are relative to it; the state
        file is ``{target_root}/rbtv.json``.
    elected:
        Iterable of package ids to render (native ids like ``claude-cli`` and
        unknown ids are skipped silently).
    check:
        Read-only drift mode — renders nothing, writes nothing; reports whether
        any managed file (or the state block) is missing/stale.  ``RenderResult.stale``
        is True on any drift.
    excluded_paths:
        Workspace-relative path prefixes to skip when walking for ``CLAUDE.md``.
        When None, the value recorded in ``rbtv.json``'s ``model_mirror`` block is
        reused (so ``--check`` and ``--mirror`` honor the install-time exclusions).

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

    # --- 1. Shared .agents/ library (rendered once when any worker is elected) ---
    rule_records = library.render_behavior_rules(target_root, check=check)
    skill_records, skipped = library.render_skills(target_root, check=check)
    all_records.extend(rule_records)
    all_records.extend(skill_records)
    result.skipped_commands = skipped

    # --- 2. Guidance files (deduped by filename across the elected set) ---
    for filename, banner_label in _elected_guidance_groups(packages).items():
        guidance_records = guidance.render_guidance(
            target_root,
            filename,
            check=check,
            excluded_paths=excluded_paths,
            banner_label=banner_label,
        )
        all_records.extend(guidance_records)

    # --- 3. Per-model config dirs ---
    for pkg in packages:
        config_records = config_assets.render_config(target_root, pkg, check=check)
        all_records.extend(config_records)

    # --- 3b. Prune-on-exclude: delete guidance orphaned by a NEWLY-excluded path ---
    # A path that became excluded since the prior render leaves its previously
    # rendered guidance file (AGENTS.md / QWEN.md) on disk — the walk skips it, so
    # neither render nor uninstall reaches it. Delete such orphans through the
    # existing banner-guarded deletion (hand-authored files are spared). NEVER in
    # check mode — a --check run reports drift, it never mutates disk.
    if not check:
        _prune_newly_excluded_guidance(
            target_root, prior_block, all_records, excluded_paths
        )

    # --- 4. Drift detection (check mode) ---
    if check:
        stale_any = _detect_drift(target_root, all_records)

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
    return result


def _detect_drift(target_root: Path, rendered: list[dict]) -> bool:
    """Return True if any rendered managed file is missing on disk OR the recorded
    state's managed-file set differs from what a render would now produce.

    In check mode the render modules already report per-file staleness via their
    own prints; this adds the state-level drift signal (files present on disk but
    no longer expected, or expected but absent).
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


def uninstall(
    target_root: Path | str,
    deselected,
    remaining_elected,
) -> UninstallResult:
    """Remove the artifacts a deselected worker set no longer needs.

    Ref-counted by guidance-filename (design §6 / spec Behavior #7):
      - the deselected package's config dir is removed;
      - a guidance-filename group (``AGENTS.md`` / ``QWEN.md``) is removed ONLY
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
        Package ids being removed (e.g. ``["codex"]``).
    remaining_elected:
        Package ids that remain elected after this uninstall.

    Returns
    -------
    UninstallResult
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

    deleted, spared = state.apply_deletions(target_root, to_delete)

    # A guidance record that was spared (hand-authored, banner-less) must NOT be
    # dropped from state silently as deleted — but it is also no longer ours to
    # manage.  Keep only records that are still on disk and owned: the survivors
    # are to_keep plus any spared guidance files (left as-is, no longer tracked).
    # Spared files are intentionally dropped from managed_files (we don't manage a
    # file we won't overwrite/delete), so kept state == to_keep.
    state.write_managed_records(target_root, to_keep)

    return UninstallResult(deleted=deleted, spared=spared, kept_records=to_keep)
