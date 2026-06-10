"""
state-stamp script — performs a complete 4-file semantic state transition
for an orchestrated plan run (plan checkbox, task frontmatter, deliverables row,
run-log event + capsule lockstep).

Spec: 1-projects/rbtv-evolution/orchestration/token-efficiency/token-efficiency-refactor/specs/state-stamp-spec.md
"""

import argparse
import glob
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Status → glyph/value maps (spec §S2)
# ---------------------------------------------------------------------------

CHECKBOX_MAP = {
    "in_progress": "~",
    "completed": "x",
    "deferred": "⏸",
}

FRONTMATTER_MAP = {
    "in_progress": "in_progress",
    "completed": "completed",
    "deferred": "cancelled",
}

DELIVERABLES_MAP = {
    "in_progress": "in-progress",
    "completed": "✅",
    "deferred": "⏸ deferred",
}

VALID_STATUSES = {"in_progress", "completed", "deferred"}


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="State-stamp script for orchestrated plan runs")
    p.add_argument("--plan-dir", required=True, help="Plan folder root")
    p.add_argument("--task", required=True, help="Task id (e.g. p1-3)")
    p.add_argument("--status", required=True, choices=sorted(VALID_STATUSES),
                   help="Target status")
    p.add_argument("--scope", default="worker", choices=["worker", "conductor"],
                   help="Audience scope (default: worker)")
    p.add_argument("--event", default=None,
                   help="Run-log event line (conductor scope only)")
    p.add_argument("--artifact", default=None,
                   help="Deliverables Path cell value")
    p.add_argument("--reason", default=None,
                   help="Reason for deferral (required when --status deferred)")
    p.add_argument("--resume-note", default=None,
                   help="Capsule resume-point bullet text (conductor scope; falls back to derived text if absent)")
    p.add_argument("--explain", action="store_true",
                   help="Preview mode — resolve targets, print diffs, exit without writing")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------

def resolve_plan_file(plan_dir):
    """Find the single *-plan.md at the plan-dir root."""
    matches = sorted(glob.glob(os.path.join(plan_dir, "*-plan.md")))
    if len(matches) == 0:
        return None, "No *-plan.md found in plan-dir"
    if len(matches) > 1:
        return None, f"Multiple *-plan.md files found: {matches}"
    return matches[0], None


def find_task_file(plan_dir, task_id):
    """Find {task-id}.task.md under phase-*/."""
    pattern = os.path.join(plan_dir, "phase-*", f"{task_id}.task.md")
    matches = sorted(glob.glob(pattern))
    if len(matches) == 0:
        return None, f"Task file {task_id}.task.md not found under phase-*/"
    if len(matches) > 1:
        return None, f"Multiple task files match {task_id}: {matches}"
    return matches[0], None


def resolve_deliverables(plan_dir):
    path = os.path.join(plan_dir, "deliverables.md")
    if not os.path.isfile(path):
        return None, f"deliverables.md not found at {path}"
    return path, None


def resolve_run_log(plan_dir):
    path = os.path.join(plan_dir, "run-log.md")
    if not os.path.isfile(path):
        return None, f"run-log.md not found at {path}"
    return path, None


def resolve_capsule(plan_dir):
    path = os.path.join(plan_dir, "state-capsule.md")
    if not os.path.isfile(path):
        return None, f"state-capsule.md not found at {path}"
    return path, None


# ---------------------------------------------------------------------------
# Target validation (spec §S9 — all-or-nothing)
# ---------------------------------------------------------------------------

def validate_checkbox_line(content, task_id):
    """Find the checkbox line for task_id. Returns (line_index, current_glyph, error)."""
    pattern = re.compile(r"^(\s*[-*]\s+)\[([ x~⏸])\](\s+`" + re.escape(task_id) + r"`)")
    for i, line in enumerate(content.splitlines()):
        m = pattern.match(line)
        if m:
            return i, m.group(2), None
    return None, None, f"Checkbox line for task '{task_id}' not found in plan file"


def validate_frontmatter(content):
    """Extract the status: line from YAML frontmatter. Returns (line_index, current_value) or error."""
    in_frontmatter = False
    for i, line in enumerate(content.splitlines()):
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
            else:
                break
        if in_frontmatter and stripped.startswith("status:"):
            current = stripped.split(":", 1)[1].strip()
            return i, current, None
    return None, None, "No 'status:' key found in task frontmatter"


def validate_deliverables_row(content, task_id):
    """Find the deliverables row keyed by task_id. Returns (line_index, cells) or error.

    The canonical 4-column row `| id | artifact | path | status |` splits on '|'
    into exactly 6 elements (leading empty + 4 data cells + trailing empty). A row
    whose id matches but whose shape is NOT the 4-column shape is an unrecognized
    structure — the script must REFUSE, not guess-edit a boundary cell as Status
    (spec §S3 / Behavior #9 / Edge: "deliverables table is not the 4-column shape
    → EXIT≠0 unrecognized-structure error; NO guess-edit").
    """
    for i, line in enumerate(content.splitlines()):
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 2 and cells[1] == task_id:
            if len(cells) != 6:
                return None, None, (
                    f"Unrecognized structure: deliverables row for task '{task_id}' "
                    f"is not the 4-column `| id | artifact | path | status |` shape "
                    f"(found {len(cells) - 2} data columns) in deliverables.md"
                )
            return i, cells, None
    return None, None, f"Deliverables row for task '{task_id}' not found"


def _event_log_section_bounds(lines):
    """Return (start, end) line indices bounding the '## Event Log' section body.

    start = first line AFTER the '## Event Log' heading; end = the next '## '
    heading (or len(lines)). The section is anchored on the heading — NOT on a
    '| Timestamp' header substring, which is not unique (the Exit Scorecard
    carries a second 5-col '| Timestamp | Event | … |' table). Spec §S4 names
    the Event Log table specifically; this scopes every run-log operation to it
    so a later table is never mistaken for the Event Log. Returns (None, None)
    if no '## Event Log' heading exists.
    """
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## Event Log":
            start = i + 1
            break
    if start is None:
        return None, None
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return start, end


def validate_event_log_table(content):
    """Find the Event Log table. Returns (last_row_index, header_line_index) or error."""
    lines = content.splitlines()
    start, end = _event_log_section_bounds(lines)
    if start is None:
        return None, None, "No '## Event Log' section found in run-log.md"
    in_table = False
    header_idx = None
    last_row_idx = None
    for i in range(start, end):
        stripped = lines[i].strip()
        if stripped.startswith("| Timestamp") and "Event" in stripped:
            header_idx = i
            in_table = True
            continue
        if in_table and stripped.startswith("|-----------"):
            continue
        if in_table and stripped.startswith("|"):
            last_row_idx = i
        elif in_table and not stripped.startswith("|"):
            # End of table
            break
    if header_idx is None:
        return None, None, "No Event Log table found in run-log.md"
    return last_row_idx, header_idx, None


def validate_capsule(content):
    """Check that the capsule has resume-point content. Returns error or None."""
    if "Resume Point" not in content and "resume" not in content.lower():
        return "state-capsule.md has no resume-point content"
    return None


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def write_file_atomic(path, new_content):
    """Write content to file. Returns error or None.

    newline="" disables Python's platform newline translation so the LF line
    endings the rewrite functions emit ("\\n".join(...)) are written verbatim.
    Without this, text-mode writes on Windows translate every "\\n"→"\\r\\n",
    flipping LF plan-folder files to CRLF and producing a whole-file diff on
    every stamp (spec §S7 / done-gate "a stamp that flips line endings corrupts
    diffs"). The plan-folder corpus is LF; this preserves it.
    """
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new_content)
        return None
    except OSError as e:
        return f"Failed to write {path}: {e}"


def rewrite_checkbox_line(content, task_id, new_glyph):
    """Replace the checkbox glyph for task_id. Returns (new_content, old_glyph)."""
    pattern = re.compile(r"^(\s*[-*]\s+)\[([ x~⏸])\](\s+`" + re.escape(task_id) + r"`)(.*)$")
    lines = content.splitlines()
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            old_glyph = m.group(2)
            lines[i] = m.group(1) + "[" + new_glyph + "]" + m.group(3) + m.group(4)
            return "\n".join(lines) + "\n", old_glyph
    raise ValueError(f"Checkbox line for '{task_id}' disappeared between validate and write")


def rewrite_frontmatter(content, new_status):
    """Replace the status: value in YAML frontmatter. Returns (new_content, old_value)."""
    lines = content.splitlines()
    in_frontmatter = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            if not in_frontmatter:
                break
        if in_frontmatter and stripped.startswith("status:"):
            old = stripped.split(":", 1)[1].strip()
            indent = line[:len(line) - len(line.lstrip())]
            lines[i] = indent + "status: " + new_status
            return "\n".join(lines) + "\n", old
    raise ValueError("status: frontmatter line disappeared between validate and write")


def rewrite_deliverables_row(content, task_id, new_status_cell, new_path=None):
    """Rewrite the deliverables row's Status cell (and optionally Path). Returns (new_content, old_cells)."""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.split("|")]
        # Match the canonical 4-column shape only (6 split-elements); a row whose
        # shape changed since validation fails loud here rather than guess-writing
        # a boundary cell (spec §S3 / §S7 re-read-before-write).
        if len(cells) == 6 and cells[1] == task_id:
            old_cells = list(cells)
            cells[4] = new_status_cell
            if new_path is not None:
                cells[3] = new_path
            # Reconstruct preserving original spacing: | cell1 | cell2 | cell3 | cell4 |
            new_line = "| " + " | ".join(cells[1:5]) + " |"
            lines[i] = new_line
            return "\n".join(lines) + "\n", old_cells
    raise ValueError(f"Deliverables row for '{task_id}' disappeared between validate and write")


def append_run_log_event(content, event_line):
    """Append a new event row after the last Event Log table row. Returns new_content.

    Scoped to the '## Event Log' section (see _event_log_section_bounds) so the
    append never lands in a later 5-col table such as the Exit Scorecard, whose
    header also starts '| Timestamp | Event | …'. Spec §S4: append ONE row at the
    END of the Event Log table — never above it, never in another table.
    """
    lines = content.splitlines()
    start, end = _event_log_section_bounds(lines)
    if start is None:
        raise ValueError("No '## Event Log' section found in run-log.md")
    last_row_idx = None
    in_table = False
    for i in range(start, end):
        stripped = lines[i].strip()
        if stripped.startswith("| Timestamp") and "Event" in stripped:
            in_table = True
            last_row_idx = None  # Reset — table header seen
            continue
        if in_table and stripped.startswith("|-----------"):
            continue
        if in_table and stripped.startswith("|"):
            last_row_idx = i
        elif in_table and not stripped.startswith("|") and stripped != "":
            # End of table (non-empty non-table line)
            in_table = False

    if last_row_idx is None:
        raise ValueError("Event Log table has no rows to append after")

    # Insert after last_row_idx
    lines.insert(last_row_idx + 1, event_line)
    return "\n".join(lines) + "\n"


def check_run_log_dedup(content, event_line):
    """Check if the exact event line already exists in the Event Log."""
    event_stripped = event_line.strip()
    for line in content.splitlines():
        if line.strip() == event_stripped:
            return True
    return False


def update_capsule(content, new_resume_point, new_timestamp):
    """Update the capsule's resume-point and timestamp fields. Returns new_content.

    Anchors to the first ``- **…**`` bullet under ``## Resume Point`` — not
    terminal-only text — so the lockstep works on ACTIVE capsules whose resume
    point reads ``- **NEXT: dispatch p3-2 …**`` instead of ``NONE … run is closed``.
    Spec §S4: the capsule's RESUME fields are mutable; decisions are append-only.
    """
    lines = content.splitlines()
    new_lines = []
    i = 0
    in_resume_section = False
    resume_point_updated = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Enter Resume Point section
        if stripped == "## Resume Point":
            in_resume_section = True
            new_lines.append(line)
            i += 1
            continue

        # Exit Resume Point section (next ## heading)
        if in_resume_section and stripped.startswith("## "):
            in_resume_section = False

        # First bullet under Resume Point → update resume point
        if (in_resume_section and not resume_point_updated
                and stripped.startswith("- **")):
            new_lines.append(f"- **{new_resume_point}**")
            resume_point_updated = True
            i += 1
            # Skip continuation lines (indented content belonging to this bullet)
            while i < len(lines) and lines[i].startswith("    ") and lines[i].strip():
                i += 1
            continue

        # Last update line → update timestamp
        if stripped.startswith("- **Last update:**"):
            new_lines.append(f"- **Last update:** {new_timestamp}")
            i += 1
            continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines) + "\n"


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main(argv=None):
    args = parse_args(argv)
    plan_dir = args.plan_dir
    task_id = args.task
    status = args.status
    scope = args.scope
    event = args.event
    artifact = args.artifact
    reason = args.reason
    resume_note = args.resume_note
    explain = args.explain

    errors = []
    results = {}

    # --- Pre-flight checks ---

    # deferred requires reason
    if status == "deferred" and not reason:
        print(f"ERROR: --status deferred requires --reason", file=sys.stderr)
        sys.exit(1)

    # worker scope cannot have --event
    if scope == "worker" and event is not None:
        print(f"ERROR: --event is conductor-only; scope '{scope}' cannot use --event", file=sys.stderr)
        sys.exit(1)

    # conductor scope requires --event
    if scope == "conductor" and event is None:
        print(f"ERROR: conductor scope requires --event", file=sys.stderr)
        sys.exit(1)

    # --- Resolve targets ---

    plan_file, err = resolve_plan_file(plan_dir)
    if err:
        errors.append(f"PLAN_FILE: {err}")
    task_file, err = find_task_file(plan_dir, task_id)
    if err:
        errors.append(f"TASK_FILE: {err}")
    deliverables_file, err = resolve_deliverables(plan_dir)
    if err:
        errors.append(f"DELIVERABLES: {err}")

    run_log_file = None
    capsule_file = None
    if scope == "conductor":
        run_log_file, err = resolve_run_log(plan_dir)
        if err:
            errors.append(f"RUN_LOG: {err}")
        capsule_file, err = resolve_capsule(plan_dir)
        if err:
            errors.append(f"CAPSULE: {err}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Read all target files fresh ---

    with open(plan_file, "r", encoding="utf-8") as f:
        plan_content = f.read()
    with open(task_file, "r", encoding="utf-8") as f:
        task_content = f.read()
    with open(deliverables_file, "r", encoding="utf-8") as f:
        deliverables_content = f.read()

    run_log_content = None
    capsule_content = None
    if scope == "conductor":
        with open(run_log_file, "r", encoding="utf-8") as f:
            run_log_content = f.read()
        with open(capsule_file, "r", encoding="utf-8") as f:
            capsule_content = f.read()

    # --- Validate all targets ---

    # 1. Plan checkbox
    checkbox_idx, current_glyph, err = validate_checkbox_line(plan_content, task_id)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)
    target_glyph = CHECKBOX_MAP[status]
    checkbox_changed = current_glyph != target_glyph

    # 2. Task frontmatter
    fm_idx, current_fm, err = validate_frontmatter(task_content)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)
    target_fm = FRONTMATTER_MAP[status]
    fm_changed = current_fm != target_fm

    # 3. Deliverables row
    del_idx, del_cells, err = validate_deliverables_row(deliverables_content, task_id)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)
    target_del_status = DELIVERABLES_MAP[status]
    if status == "deferred" and reason:
        target_del_status = f"⏸ deferred ({reason})"
    del_status_changed = del_cells[4] != target_del_status
    del_path_changed = artifact is not None and (len(del_cells) < 4 or del_cells[3] != artifact)

    # 4. Run-log dedup check (conductor only)
    run_log_dedup_hit = False
    if scope == "conductor":
        rl_idx, rl_header, err = validate_event_log_table(run_log_content)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            sys.exit(1)
        run_log_dedup_hit = check_run_log_dedup(run_log_content, event)

    # 4b. Capsule validation (conductor only)
    if scope == "conductor":
        cap_err = validate_capsule(capsule_content)
        if cap_err:
            print(f"ERROR: {cap_err}", file=sys.stderr)
            sys.exit(1)

    # --- Check for duplicates (ambiguous matches) ---
    # Re-validate for duplicates
    checkbox_count = len(re.findall(
        r"^(\s*[-*]\s+)\[([ x~⏸])\](\s+`" + re.escape(task_id) + r"`)",
        plan_content, re.MULTILINE
    ))
    if checkbox_count > 1:
        print(f"ERROR: Multiple checkbox lines match task '{task_id}' in plan file", file=sys.stderr)
        sys.exit(1)

    del_count = 0
    for line in deliverables_content.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) == 6 and cells[1] == task_id:
            del_count += 1
    if del_count > 1:
        print(f"ERROR: Multiple deliverables rows match task '{task_id}'", file=sys.stderr)
        sys.exit(1)

    # --- Explain mode ---
    if explain:
        print(f"=== EXPLAIN MODE — no files will be written ===")
        print(f"Plan file: {plan_file}")
        print(f"  checkbox: [{current_glyph}] → [{target_glyph}]  ({'changed' if checkbox_changed else 'unchanged'})")
        print(f"Task file: {task_file}")
        print(f"  status: {current_fm} → {target_fm}  ({'changed' if fm_changed else 'unchanged'})")
        print(f"Deliverables: {deliverables_file}")
        print(f"  Status: {del_cells[4]} → {target_del_status}  ({'changed' if del_status_changed else 'unchanged'})")
        if artifact:
            old_path = del_cells[3] if len(del_cells) > 3 else "(empty)"
            print(f"  Path: {old_path} → {artifact}  ({'changed' if del_path_changed else 'unchanged'})")
        if scope == "conductor":
            print(f"Run-log: {run_log_file}")
            if run_log_dedup_hit:
                print(f"  event: DEDUP HIT — would skip append (unchanged)")
            else:
                print(f"  event: would APPEND: {event}")
            print(f"Capsule: {capsule_file}")
            print(f"  resume-point + timestamp: would update")
        sys.exit(0)

    # --- Test hook: pause before write (env-gated per rbtv-build-for-agent-testability) ---
    _pause_file = os.environ.get("STAMP_TEST_PAUSE_FILE")
    if _pause_file:
        import time as _time
        with open(_pause_file + ".paused", "w", encoding="utf-8") as _pf:
            _pf.write("paused")
        _timeout = 30
        _start = _time.time()
        while not os.path.exists(_pause_file + ".resume"):
            if _time.time() - _start > _timeout:
                print("ERROR: Test pause timed out waiting for resume file", file=sys.stderr)
                sys.exit(1)
            _time.sleep(0.1)
        os.remove(_pause_file + ".paused")
        os.remove(_pause_file + ".resume")

    # --- Perform writes (run-log LAST for recoverability, spec §S9) ---
    # Per spec §S7 / Behavior #10–11: re-read each target immediately before
    # writing it, re-locate the exact anchor in the just-read content, fail-loud
    # if the anchor was concurrently removed or mangled.  This prevents clobbering
    # concurrent foreign edits that landed between the validate-phase read and the
    # write (the workspace's daily parallel-session reality).  All-or-nothing is
    # preserved: if ANY re-locate fails, no further writes happen; targets 1–3 are
    # convergent (safe to re-run), and the run-log has not yet been touched.

    def _inject_failure_after(target):
        """Env-gated mid-flight failure injection — inert by default."""
        if os.environ.get("STAMP_TEST_FAIL_AFTER") == target:
            print(f"ERROR: INJECTED_FAILURE after {target}", file=sys.stderr)
            sys.exit(1)

    # 1. Plan checkbox
    if checkbox_changed:
        with open(plan_file, "r", encoding="utf-8", newline="") as f:
            fresh_plan = f.read()
        _, _, err = validate_checkbox_line(fresh_plan, task_id)
        if err:
            print(f"ERROR: re-read before write (plan checkbox): {err}", file=sys.stderr)
            sys.exit(1)
        new_plan, old = rewrite_checkbox_line(fresh_plan, task_id, target_glyph)
        err = write_file_atomic(plan_file, new_plan)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            sys.exit(1)
        results["plan_checkbox"] = "changed"
    else:
        results["plan_checkbox"] = "unchanged"
    _inject_failure_after("plan_checkbox")

    # 2. Task frontmatter
    if fm_changed:
        with open(task_file, "r", encoding="utf-8", newline="") as f:
            fresh_task = f.read()
        _, _, err = validate_frontmatter(fresh_task)
        if err:
            print(f"ERROR: re-read before write (task frontmatter): {err}", file=sys.stderr)
            sys.exit(1)
        new_task, old = rewrite_frontmatter(fresh_task, target_fm)
        err = write_file_atomic(task_file, new_task)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            sys.exit(1)
        results["task_frontmatter"] = "changed"
    else:
        results["task_frontmatter"] = "unchanged"
    _inject_failure_after("task_frontmatter")

    # 3. Deliverables row
    del_path_arg = artifact if del_path_changed else None
    if del_status_changed or del_path_changed:
        with open(deliverables_file, "r", encoding="utf-8", newline="") as f:
            fresh_del = f.read()
        _, _, err = validate_deliverables_row(fresh_del, task_id)
        if err:
            print(f"ERROR: re-read before write (deliverables): {err}", file=sys.stderr)
            sys.exit(1)
        new_del, old = rewrite_deliverables_row(fresh_del, task_id, target_del_status, del_path_arg)
        err = write_file_atomic(deliverables_file, new_del)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            sys.exit(1)
        if del_path_changed:
            results["deliverables_status"] = "changed"
            results["deliverables_path"] = "path-updated"
        else:
            results["deliverables_status"] = "changed"
    else:
        results["deliverables_status"] = "unchanged"
        if artifact and not del_path_changed:
            results["deliverables_path"] = "unchanged"
    _inject_failure_after("deliverables")

    # 4. Run-log append (conductor only, LAST)
    if scope == "conductor":
        if run_log_dedup_hit:
            results["run_log_event"] = "unchanged"
        else:
            with open(run_log_file, "r", encoding="utf-8", newline="") as f:
                fresh_rl = f.read()
            _, _, err = validate_event_log_table(fresh_rl)
            if err:
                print(f"ERROR: re-read before write (run-log): {err}", file=sys.stderr)
                sys.exit(1)
            new_rl = append_run_log_event(fresh_rl, event)
            err = write_file_atomic(run_log_file, new_rl)
            if err:
                print(f"ERROR: {err}", file=sys.stderr)
                sys.exit(1)
            results["run_log_event"] = "changed"
        _inject_failure_after("run_log")

        # 4b. Capsule lockstep (only when event was actually appended)
        if not run_log_dedup_hit:
            with open(capsule_file, "r", encoding="utf-8", newline="") as f:
                fresh_cap = f.read()
            cap_err = validate_capsule(fresh_cap)
            if cap_err:
                print(f"ERROR: re-read before write (capsule): {cap_err}", file=sys.stderr)
                sys.exit(1)
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
            # ADX-17: conductor-supplied resume text with derived fallback
            resume_text = resume_note if resume_note else f"Stamp transition: {task_id} → {status}"
            new_capsule = update_capsule(fresh_cap, resume_text, now)
            err = write_file_atomic(capsule_file, new_capsule)
            if err:
                print(f"ERROR: {err}", file=sys.stderr)
                sys.exit(1)
            results["capsule"] = "changed"
        else:
            results["capsule"] = "unchanged"

    # --- Report ---
    for target, outcome in results.items():
        print(f"{target}: {outcome}")

    sys.exit(0)


if __name__ == "__main__":
    main()
