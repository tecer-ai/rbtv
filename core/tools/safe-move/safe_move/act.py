"""Act assembly: verify requested hashes, move, rewrite selected refs, and log."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from safe_move import classify, scope
from safe_move.consult import ConsultError, build_consult_result
from safe_move.move import MoveError, perform_move
from safe_move.scope import ScopeError


class ActError(Exception):
    """Raised when act input cannot be interpreted."""


class _ApplySiteError(OSError):
    """Raised when a requested edit site cannot be applied."""

    def __init__(self, ref_id: str, message: str) -> None:
        self.ref_id = ref_id
        super().__init__(message)


@dataclass(slots=True)
class ActResult:
    """Result of an act run, including the printable action log."""

    moved: dict[str, str] | None = None
    auto_fixed: list[dict[str, str]] = field(default_factory=list)
    surfaced: list[dict[str, str]] = field(default_factory=list)
    drifted: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 1 if self.drifted or self.errors else 0


def run_act(
    old: str,
    new: str,
    *,
    apply: str,
    scope_root: str | Path | None = None,
    exclude: list[str] | tuple[str, ...] = (),
    read_only: list[str] | tuple[str, ...] = (),
    include_archive: bool = False,
    descend_nested_repos: bool = False,
    generated: list[str] | tuple[str, ...] = (),
) -> ActResult:
    """Re-derive current refs, move, apply verified requested ids, and return a log."""
    requested = parse_apply(apply)
    result = ActResult()

    root = scope.resolve_scope_root(old, scope_root)
    # ``old`` may sit OUTSIDE ``root`` (a --scope-root subtree that does not
    # contain it). ``consult`` already tolerates this (matchers._normalize_old
    # falls back to the absolute path), surfacing in-scope refs + a
    # ``moved-folder-out-of-scope`` warning. ``act`` must agree rather than
    # hard-erroring on ``relative_to`` — so ``old`` gets the same external
    # fallback ``new`` already uses.
    old_rel = _normalize_path_for_scope(old, root, allow_external=True)
    new_rel = _normalize_path_for_scope(new, root, allow_external=True)
    old_abs = (root / old_rel).resolve()
    new_abs = (root / new_rel).resolve()

    consult_result = build_consult_result(
        old,
        new,
        scope_root=root,
        exclude=exclude,
        read_only=read_only,
        include_archive=include_archive,
        descend_nested_repos=descend_nested_repos,
        generated=generated,
    )
    result.warnings.extend(consult_result["warnings"])

    current_refs = {ref["id"]: ref for ref in consult_result["references"]}

    # Requested ids that no longer exist in the fresh derivation → drift.
    for ref_id in requested:
        if ref_id not in current_refs:
            reason = "vanished" if _looks_like_ref_id(ref_id) else "unknown"
            result.drifted.append({"id": ref_id, "file": "", "reason": reason})

    # Decide each current reference by CLASS and explicit request:
    #   * protected  → never applied, even when requested (surfaced; warn if asked);
    #   * requested  → drift-guarded by hash regardless of class (apply or drift);
    #   * auto        → applied automatically even when absent from --apply;
    #   * everything else → surfaced for the caller to decide.
    apply_refs: list[dict[str, Any]] = []
    for ref in consult_result["references"]:
        ref_id = ref["id"]
        ref_class = ref.get("class")

        if ref_class == classify.CLASS_PROTECTED:
            result.surfaced.append(_surfaced_row(ref))
            if ref_id in requested:
                result.warnings.append(
                    {
                        "kind": "protected-not-applied",
                        "message": "requested reference is protected and was not applied",
                        "file": ref["file"],
                        "ref_id": ref_id,
                    }
                )
            continue

        if ref_id in requested:
            if ref["hash"] != requested[ref_id]:
                result.drifted.append(
                    {"id": ref_id, "file": ref["file"], "reason": "drifted"}
                )
            else:
                apply_refs.append(ref)
            continue

        if ref_class == classify.CLASS_AUTO:
            apply_refs.append(ref)
        else:
            result.surfaced.append(_surfaced_row(ref))

    try:
        method, move_warnings = perform_move(old_abs, new_abs, root)
        result.moved = {"old": old_rel, "new": new_rel, "method": method}
        result.warnings.extend(move_warnings)
        result.warnings = _deduplicate_warnings(result.warnings)
    except MoveError as exc:
        result.errors.append(str(exc))
        return result

    fixed, edit_errors = _apply_refs(root, apply_refs, old_rel=old_rel, new_rel=new_rel)
    result.auto_fixed.extend(fixed)
    result.errors.extend(edit_errors)

    return result


def parse_apply(raw: str) -> dict[str, str]:
    """Parse comma-separated ``id:hash`` pairs into an order-independent map."""
    if raw == "":
        return {}

    parsed: dict[str, str] = {}
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if ":" not in item:
            raise ActError(f"invalid --apply pair: {item!r}")
        ref_id, ref_hash = item.split(":", 1)
        if not ref_id or not ref_hash:
            raise ActError(f"invalid --apply pair: {item!r}")
        parsed[ref_id] = ref_hash
    return parsed


def _surfaced_row(ref: dict[str, Any]) -> dict[str, str]:
    """Return the action-log row for a reference left to the caller."""
    return {
        "id": ref["id"],
        "file": ref["file"],
        "old": ref["match"],
        "new": ref["proposed"],
    }


def format_action_log(result: ActResult) -> str:
    """Return the frozen five-section action log."""
    lines: list[str] = []
    lines.append("moved")
    if result.moved is None:
        lines.append("- none")
    else:
        lines.append(
            f"- {result.moved['old']} -> {result.moved['new']} "
            f"(method: {result.moved['method']})"
        )

    lines.append("auto-fixed")
    _extend_ref_rows(lines, result.auto_fixed)

    lines.append("surfaced")
    _extend_ref_rows(lines, result.surfaced)

    lines.append("drifted")
    if not result.drifted:
        lines.append("- none")
    else:
        for row in result.drifted:
            file_part = f" {row['file']}" if row.get("file") else ""
            lines.append(f"- {row['id']}{file_part} reason: {row['reason']}")

    lines.append("warnings")
    warning_rows = list(result.warnings)
    warning_rows.extend(
        {"kind": "error", "message": error, "file": None, "ref_id": None}
        for error in result.errors
    )
    if not warning_rows:
        lines.append("- none")
    else:
        for warning in warning_rows:
            file_part = f" file={warning['file']}" if warning.get("file") else ""
            ref_part = f" ref={warning['ref_id']}" if warning.get("ref_id") else ""
            lines.append(f"- {warning['kind']}: {warning['message']}{file_part}{ref_part}")

    return "\n".join(lines)


def _apply_refs(
    root: Path,
    refs: list[dict[str, Any]],
    *,
    old_rel: str,
    new_rel: str,
) -> tuple[list[dict[str, str]], list[str]]:
    fixed: list[dict[str, str]] = []
    errors: list[str] = []

    refs_by_file: dict[str, list[dict[str, Any]]] = {}
    for ref in refs:
        ref_file = ref["file"]
        if ref_file == old_rel:
            edit_file = new_rel
        elif ref_file.startswith(old_rel + "/"):
            edit_file = new_rel + ref_file[len(old_rel):]
        else:
            edit_file = ref_file
        refs_by_file.setdefault(edit_file, []).append(ref)

    for edit_file, file_refs in refs_by_file.items():
        path = (root / edit_file).resolve()
        try:
            content = path.read_text(encoding="utf-8")
            updated, applied = _replace_sites_for_file(content, file_refs, edit_file)
            if updated != content:
                path.write_text(updated, encoding="utf-8")
        except _ApplySiteError as exc:
            errors.append(f"edit failed for {exc.ref_id} {edit_file}: {exc}")
            continue
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"edit failed for {edit_file}: {exc}")
            continue
        fixed.extend(applied)
    return fixed, errors


def _replace_sites_for_file(
    content: str,
    refs: list[dict[str, Any]],
    edit_file: str,
) -> tuple[str, list[dict[str, str]]]:
    updated = content
    applied: list[dict[str, str]] = []

    refs_by_context: dict[str, list[dict[str, Any]]] = {}
    for ref in refs:
        refs_by_context.setdefault(ref["context"], []).append(ref)

    for context, context_refs in refs_by_context.items():
        changed_refs = [
            ref for ref in context_refs
            if ref["proposed"] != "" and ref["proposed"] != ref["match"]
        ]
        if changed_refs:
            if context not in updated:
                ref_ids = ", ".join(ref["id"] for ref in context_refs)
                raise _ApplySiteError(
                    context_refs[0]["id"],
                    f"context vanished for {ref_ids} in {edit_file}",
                )
            new_context = _replace_context_matches(context, changed_refs, edit_file)
            updated = updated.replace(context, new_context, 1)
        for ref in changed_refs:
            applied.append(
                {
                    "id": ref["id"],
                    "file": edit_file,
                    "old": ref["match"],
                    "new": ref["proposed"],
                }
            )

    return updated, applied


def _deduplicate_warnings(warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any, Any]] = set()
    for warning in warnings:
        key = (
            warning.get("kind"),
            warning.get("message"),
            warning.get("file"),
            warning.get("ref_id"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(warning)
    return deduplicated


def _replace_context_matches(
    context: str,
    refs: list[dict[str, Any]],
    edit_file: str,
) -> str:
    spans_by_site: dict[tuple[int, int], list[tuple[int, int, dict[str, Any]]]] = {}
    for ref in refs:
        offset = ref.get("offset", 0)
        if offset > len(context):
            offset = 0
        start = context.find(ref["match"], offset)
        if start == -1:
            raise _ApplySiteError(ref["id"], f"match vanished for {ref['id']} in {edit_file}")
        end = start + len(ref["match"])
        span = (start, end, ref)
        spans_by_site.setdefault((start, end), []).append(span)

    collapsed_spans: list[tuple[int, int, dict[str, Any]]] = []
    for site_spans in spans_by_site.values():
        first = site_spans[0][2]
        conflict = next(
            (span[2] for span in site_spans[1:] if span[2]["proposed"] != first["proposed"]),
            None,
        )
        if conflict is not None:
            raise _ApplySiteError(
                first["id"],
                "DOUBT_ESCALATED overlapping matches "
                f"for {first['id']} ({first['match']!r}) and "
                f"{conflict['id']} ({conflict['match']!r}) in {edit_file}"
            )
        collapsed_spans.append(site_spans[0])

    ordered = sorted(collapsed_spans, key=lambda item: (item[0], item[1]))
    for previous, current in zip(ordered, ordered[1:]):
        if previous[1] > current[0]:
            first = previous[2]
            second = current[2]
            raise _ApplySiteError(
                first["id"],
                "DOUBT_ESCALATED overlapping matches "
                f"for {first['id']} ({first['match']!r}) and "
                f"{second['id']} ({second['match']!r}) in {edit_file}"
            )

    new_context = context
    for start, end, ref in sorted(collapsed_spans, key=lambda item: item[0], reverse=True):
        new_context = new_context[:start] + ref["proposed"] + new_context[end:]
    return new_context


def _extend_ref_rows(lines: list[str], rows: list[dict[str, str]]) -> None:
    if not rows:
        lines.append("- none")
        return
    for row in rows:
        lines.append(f"- {row['id']} {row['file']} {row['old']} -> {row['new']}")


def _normalize_path_for_scope(path: str, root: Path, *, allow_external: bool = False) -> str:
    value = Path(path).expanduser()
    if value.is_absolute():
        resolved = value.resolve()
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            if allow_external:
                return resolved.as_posix()
            raise
    return value.as_posix()


def _looks_like_ref_id(ref_id: str) -> bool:
    if not ref_id.startswith("ref-"):
        return False
    suffix = ref_id.removeprefix("ref-")
    return len(suffix) == 4 and suffix.isdigit()


__all__ = [
    "ActError",
    "ActResult",
    "format_action_log",
    "parse_apply",
    "run_act",
]
