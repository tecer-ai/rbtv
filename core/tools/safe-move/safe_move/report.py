"""Report files + compact summaries: the agent-facing output surface.

``consult``/``act`` write their FULL result envelope to a report file under
``{workspace_root}/.rbtv/runtime/safe-move/`` and print only a compact summary
(counts, warnings, and the records the caller must decide on) plus the report
path. The report file is a disposable convenience artifact — ``act`` still
re-derives everything from scratch and trusts only the hash handshake; a stale
report can never corrupt an apply. ``show`` slices a report back out without
re-streaming the whole envelope.
"""

from __future__ import annotations

import fnmatch
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safe_move import scope

#: Cap for match/proposed text on a summary line; full text lives in the report.
_SNIPPET_MAX = 80


class ReportError(Exception):
    """Raised when a report file cannot be read or does not parse."""


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def resolve_report_dir(scope_root: Path) -> Path:
    """Return the report directory for a run scoped at ``scope_root``.

    Reports live at the WORKSPACE root (the git top level containing the scope
    root), not the scan subtree, so a ``--scope-root``-narrowed run still files
    its report in the one predictable place. Outside any git repo, the scope
    root itself is the base.
    """
    base = scope.git_toplevel(scope_root) or Path(scope_root).resolve()
    return base / ".rbtv" / "runtime" / "safe-move"


def write_report(
    kind: str,
    old: str,
    new: str,
    scope_root: Path,
    result: Any,
) -> Path:
    """Persist the full ``result`` envelope; return the report's absolute path.

    Creates ``.rbtv/runtime/`` on first use with a self-ignoring ``.gitignore``
    (``*``) so runtime artifacts never show up as untracked repo content.
    """
    report_dir = resolve_report_dir(scope_root)
    report_dir.mkdir(parents=True, exist_ok=True)

    runtime_dir = report_dir.parent
    gitignore = runtime_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(Path(old).name)
    token = uuid.uuid4().hex[:6]
    path = report_dir / f"{kind}-{stamp}-{slug}-{token}.json"

    payload = {
        "tool": "safe-move",
        "subcommand": kind,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "old": str(old),
        "new": str(new),
        "scope_root": str(Path(scope_root).resolve()),
        "result": result,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _slugify(name: str) -> str:
    cleaned = "".join(c if c.isalnum() else "-" for c in name).strip("-").lower()
    return cleaned[:40] or "move"


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def format_consult_summary(
    result: dict[str, Any],
    old: str,
    new: str,
    report_path: Path | None,
) -> str:
    """Compact consult output: counts, surfaced records inline, report path.

    ``surface`` records are the only ones the caller must decide on, so they
    print inline as ready-to-paste ``id:hash`` pairs; ``auto``/``protected``
    collapse to counts. Everything else is in the report.
    """
    references = result["references"]
    by_class: dict[str, list[dict[str, Any]]] = {}
    for ref in references:
        by_class.setdefault(ref.get("class", "?"), []).append(ref)

    auto = by_class.get("auto", [])
    surface = by_class.get("surface", [])
    protected = by_class.get("protected", [])

    lines = [
        f"consult: {old} -> {new}",
        f"move method: {result['git_move_method']}",
        (
            f"references: {len(references)}"
            f" (auto {len(auto)}, surface {len(surface)}, protected {len(protected)})"
        ),
    ]

    cascade = result.get("folder_cascade")
    if cascade:
        lines.append(f"folder cascade: {len(cascade)} moved paths (see report)")

    if surface:
        lines.append("surface (pass id:hash to act --apply to also fix):")
        for ref in surface:
            lines.append(
                f"- {ref['id']}:{ref['hash']}  {ref['file']}:{ref['line']}"
                f"  {ref['syntax']}  {_snippet(ref['match'])} -> {_snippet(ref['proposed'])}"
            )
    if protected:
        lines.append(f"protected: {len(protected)} (never edited; see report)")

    _extend_warning_lines(lines, result["warnings"])

    if report_path is not None:
        lines.append(f"report: {report_path}")
        lines.append(
            f'records: python -m safe_move show "{report_path}"'
            " [--id <ref-id>] [--class auto|surface|protected] [--file <glob>]"
        )
    return "\n".join(lines)


def format_act_summary(result: Any, report_path: Path | None) -> str:
    """Compact act output: move line, auto count, actionable rows, report path.

    ``surfaced``/``drifted``/error rows stay inline — they are the caller's
    remaining work; ``auto-fixed`` collapses to a count (full rows in the
    report).
    """
    lines: list[str] = []
    if result.moved is None:
        lines.append("moved: none")
    else:
        lines.append(
            f"moved: {result.moved['old']} -> {result.moved['new']}"
            f" (method: {result.moved['method']})"
        )

    lines.append(f"auto-fixed: {len(result.auto_fixed)}")

    if result.surfaced:
        lines.append("surfaced (yours to resolve):")
        for row in result.surfaced:
            lines.append(
                f"- {row['id']}  {row['file']}"
                f"  {_snippet(row['old'])} -> {_snippet(row['new'])}"
            )
    if result.drifted:
        lines.append("drifted (re-run consult for fresh hashes):")
        for row in result.drifted:
            file_part = f" {row['file']}" if row.get("file") else ""
            lines.append(f"- {row['id']}{file_part} reason: {row['reason']}")
    for error in result.errors:
        lines.append(f"error: {error}")

    _extend_warning_lines(lines, result.warnings)

    if report_path is not None:
        lines.append(f"report: {report_path}")
    return "\n".join(lines)


def _extend_warning_lines(lines: list[str], warnings: list[dict[str, Any]]) -> None:
    if not warnings:
        return
    lines.append("warnings:")
    for warning in warnings:
        file_part = f" file={warning['file']}" if warning.get("file") else ""
        ref_part = f" ref={warning['ref_id']}" if warning.get("ref_id") else ""
        lines.append(f"- {warning['kind']}: {warning['message']}{file_part}{ref_part}")


def _snippet(text: str) -> str:
    text = "" if text is None else str(text)
    flat = text.replace("\n", "\\n")
    if len(flat) > _SNIPPET_MAX:
        flat = flat[: _SNIPPET_MAX - 1] + "…"
    return f"'{flat}'"


# ---------------------------------------------------------------------------
# show — slice a report back out
# ---------------------------------------------------------------------------


def load_report(path: str | Path) -> dict[str, Any]:
    """Read and validate a report file written by ``write_report``."""
    report_path = Path(path).expanduser()
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReportError(f"cannot read report: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReportError(f"report is not valid JSON: {report_path}") from exc
    if not isinstance(payload, dict) or payload.get("tool") != "safe-move":
        raise ReportError(f"not a safe-move report: {report_path}")
    return payload


def run_show(
    path: str | Path,
    *,
    ids: list[str] = (),
    ref_class: str | None = None,
    file_glob: str | None = None,
    warnings_only: bool = False,
) -> tuple[str, int]:
    """Return ``(output, exit_code)`` for the ``show`` subcommand.

    No filters → re-print the compact summary. ``--warnings`` → the warnings
    list as JSON. Record filters (AND-combined; ``--id`` values OR-combined) →
    the matching FULL records as JSON. An unknown ``--id`` is reported and
    exits 1 so a typo never reads as "no references".
    """
    payload = load_report(path)
    result = payload["result"]

    if warnings_only:
        return json.dumps(result.get("warnings", []), indent=2), 0

    has_filters = bool(ids) or ref_class is not None or file_glob is not None
    if not has_filters:
        if payload["subcommand"] == "consult":
            summary = format_consult_summary(
                result, payload["old"], payload["new"], Path(path)
            )
        else:
            summary = _format_act_report_summary(result, Path(path))
        return summary, 0

    references = result.get("references")
    if references is None:
        raise ReportError(
            "record filters apply to consult reports; this is an act report "
            "(use it without filters, or with --warnings)"
        )

    matched = references
    if ids:
        wanted = set(ids)
        matched = [ref for ref in matched if ref["id"] in wanted]
        missing = wanted - {ref["id"] for ref in matched}
        if missing:
            raise ReportError(
                f"id(s) not in report: {', '.join(sorted(missing))}"
            )
    if ref_class is not None:
        matched = [ref for ref in matched if ref.get("class") == ref_class]
    if file_glob is not None:
        matched = [ref for ref in matched if fnmatch.fnmatch(ref["file"], file_glob)]

    return json.dumps(matched, indent=2), 0


def _format_act_report_summary(result: dict[str, Any], report_path: Path) -> str:
    """Summary for a stored act report (dict form of ``ActResult``)."""

    class _Row:  # minimal duck-type over the stored dict
        moved = result.get("moved")
        auto_fixed = result.get("auto_fixed", [])
        surfaced = result.get("surfaced", [])
        drifted = result.get("drifted", [])
        warnings = result.get("warnings", [])
        errors = result.get("errors", [])

    return format_act_summary(_Row, report_path)


__all__ = [
    "ReportError",
    "format_act_summary",
    "format_consult_summary",
    "load_report",
    "resolve_report_dir",
    "run_show",
    "write_report",
]
