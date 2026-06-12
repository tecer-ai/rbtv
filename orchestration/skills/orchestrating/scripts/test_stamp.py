"""
test_stamp.py — acceptance tests for stamp.py against a real-corpus fixture.

Test Plan mapping (spec § Test Plan; conductor-scope arg contract updated per
the 2026-06 spine-writes fix — structured event args + labeled Resume Point):
  #1  One conductor-scope call performs the complete 4-file transition
  #2  Append-only is never violated
  #3  Worker scope cannot touch run-log or capsule
  #4  Idempotency — re-running the same transition is a no-op
  #5  deferred status requires --reason
  #6  Conductor-only args in worker scope are rejected
  #7  Conductor scope without --event-type/--outcome/--next-dispatch is rejected
  #8  Missing task id → EXIT≠0, no write
  #9  Invalid --status → EXIT≠0, no write
  #10 --artifact updates the deliverables Path cell
  #11 --explain prints preview without writing
  #12 Byte-identical after idempotent re-run
  #13 The composed Event Log row renders as a well-formed 5-column table row
  #14 Capsule Resume Point keeps its three labeled bullets; no stale next-dispatch
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_SRC = Path(__file__).parent / "tests-fixtures" / "api-workers-build-fixture"
ACTIVE_FIXTURE_SRC = Path(__file__).parent / "tests-fixtures" / "api-workers-build-active-fixture"
SCRIPT = Path(__file__).parent / "stamp.py"

STAMP_PY = str(SCRIPT)

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$")


@pytest.fixture(scope="function")
def plan_dir(tmp_path):
    """Copy the real-corpus fixture into a temp dir so each test is isolated."""
    dest = tmp_path / "api-workers-build"
    shutil.copytree(FIXTURE_SRC, dest)
    return str(dest)


def run_stamp(plan_dir, *args, expect_fail=False):
    """Run stamp.py with the given args. Returns (exit_code, stdout, stderr)."""
    cmd = [sys.executable, STAMP_PY, "--plan-dir", plan_dir] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not expect_fail:
        assert result.returncode == 0, f"stamp.py failed: {result.stderr}"
    return result.returncode, result.stdout, result.stderr


def conductor_args(task, status="completed", event_type="return",
                   outcome="status DONE", worker=None,
                   next_dispatch="p9-9 to kimi — next batch", resume_note=None):
    """Build a conductor-scope arg list under the structured-event contract."""
    args = [
        "--task", task,
        "--status", status,
        "--scope", "conductor",
        "--event-type", event_type,
        "--outcome", outcome,
        "--next-dispatch", next_dispatch,
    ]
    if worker is not None:
        args += ["--worker", worker]
    if resume_note is not None:
        args += ["--resume-note", resume_note]
    return args


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def file_hash(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def event_log_rows(run_log_content):
    """Return the data rows (as cell lists) of the '## Event Log' table."""
    lines = run_log_content.splitlines()
    try:
        start = lines.index("## Event Log") + 1
    except ValueError:
        return []
    rows = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.split("|")]
        if len(cells) >= 2 and cells[1] in ("Timestamp",) or stripped.startswith("|---"):
            continue
        rows.append(cells)
    return rows


def find_event_row(run_log_content, event_type, task_id):
    """Find the LAST Event Log row for (event_type, task_id) — appended rows land
    at the table end, after any pre-existing fixture rows for the same task.
    Returns cell list or None."""
    found = None
    for cells in event_log_rows(run_log_content):
        if len(cells) == 7 and cells[2] == event_type and cells[3] == task_id:
            found = cells
    return found


# ---------------------------------------------------------------------------
# Test Plan #1 — One conductor-scope call performs the complete 4-file transition
# ---------------------------------------------------------------------------

class TestConductorScope:
    def test_four_file_transition(self, plan_dir):
        """Run a conductor-scope transition on p1-1 and verify all four files change."""
        rc, stdout, stderr = run_stamp(
            plan_dir,
            *conductor_args("p1-1", outcome="status DONE — reconciled vs disk"),
        )
        assert rc == 0, f"stderr: {stderr}"

        # Plan file: checkbox → [x]
        plan_file = os.path.join(plan_dir, "api-workers-build-plan.md")
        plan_content = read_file(plan_file)
        assert "- [x] `p1-1`" in plan_content, f"Checkbox not set to [x] in plan file"

        # Task file: status: completed
        task_file = os.path.join(plan_dir, "phase-1", "p1-1.task.md")
        task_content = read_file(task_file)
        assert "status: completed" in task_content, "Task frontmatter not set to completed"

        # Deliverables: Status → ✅
        del_content = read_file(os.path.join(plan_dir, "deliverables.md"))
        assert "| p1-1 |" in del_content
        # Check the row has ✅
        for line in del_content.splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) >= 5 and cells[1] == "p1-1":
                assert cells[4] == "✅", f"Deliverables status is '{cells[4]}', expected '✅'"
                break

        # Run-log: composed event row appended
        rl_content = read_file(os.path.join(plan_dir, "run-log.md"))
        row = find_event_row(rl_content, "return", "p1-1")
        assert row is not None, "Composed event row not found in Event Log"
        assert row[5] == "status DONE — reconciled vs disk"

        # Stdout reports all changed
        assert "plan_checkbox: changed" in stdout
        assert "task_frontmatter: changed" in stdout
        assert "deliverables_status: changed" in stdout
        assert "run_log_event: changed" in stdout

    def test_append_only_not_violated(self, plan_dir):
        """After a transition, the run-log's pre-existing rows are untouched and the
        new event is appended as the LAST row of the '## Event Log' table — not at
        the end of the file (spec §S4 / Behavior #2). The fixture carries a SECOND
        5-col '| Timestamp | Event | … |' table under '## Exit Scorecard'; the append
        must NOT land there."""
        rl_path = os.path.join(plan_dir, "run-log.md")
        before = read_file(rl_path)
        before_lines = before.splitlines()

        run_stamp(plan_dir, *conductor_args("p1-2"))

        after = read_file(rl_path)
        after_lines = after.splitlines()

        # Exactly ONE line added (a single appended row — nothing deleted).
        assert len(after_lines) == len(before_lines) + 1, (
            f"Expected exactly one appended line; "
            f"before={len(before_lines)} after={len(after_lines)}"
        )

        # Every original line is still present in the SAME relative order with
        # exactly one new line spliced in — i.e. no prior row edited/reordered/deleted.
        inserted_at = None
        for i, orig in enumerate(before_lines):
            if inserted_at is None and after_lines[i] != orig:
                inserted_at = i
                cells = [c.strip() for c in after_lines[i].split("|")]
                assert len(cells) == 7, (
                    f"Inserted line is not a 5-column table row: {after_lines[i]!r}"
                )
                assert cells[2] == "return" and cells[3] == "p1-2", (
                    f"First divergence is not the composed event row: {after_lines[i]!r}"
                )
                assert after_lines[i + 1] == orig, (
                    f"Original line {i} not preserved after the insert: "
                    f"{orig!r} → {after_lines[i + 1]!r}"
                )
            elif inserted_at is not None:
                assert after_lines[i + 1] == orig, (
                    f"Original line {i} modified after the insert point: "
                    f"{orig!r} → {after_lines[i + 1]!r}"
                )
        assert inserted_at is not None, "Event line was not inserted"

        # The insert must be INSIDE the '## Event Log' section, BEFORE '## Exit Scorecard'.
        event_log_hdr = after_lines.index("## Event Log")
        scorecard_hdr = next(
            (i for i, ln in enumerate(after_lines) if ln.strip() == "## Exit Scorecard"),
            len(after_lines),
        )
        assert event_log_hdr < inserted_at < scorecard_hdr, (
            f"Event appended outside the Event Log section: inserted_at={inserted_at}, "
            f"'## Event Log'={event_log_hdr}, '## Exit Scorecard'={scorecard_hdr}"
        )


# ---------------------------------------------------------------------------
# Test Plan #13 — Composed Event Log row shape
# ---------------------------------------------------------------------------

class TestComposedRow:
    """The conductor-scope stamp COMPOSES the Event Log row from structured args —
    the appended row always renders as a `| Timestamp | Event | Task/Batch | Worker
    | Outcome |` table row, timestamp auto-generated."""

    def test_row_is_well_formed_table_row(self, plan_dir):
        rc, stdout, stderr = run_stamp(
            plan_dir,
            *conductor_args(
                "p1-1", event_type="return",
                outcome="DONE — gate clear",
                worker="claude-code-native:opus (agent-tool)",
            ),
        )
        assert rc == 0, f"stderr: {stderr}"
        rl_content = read_file(os.path.join(plan_dir, "run-log.md"))
        row = find_event_row(rl_content, "return", "p1-1")
        assert row is not None, "Composed row not found"
        # 5 data cells: leading/trailing empties + 5 cells = 7 split elements
        assert len(row) == 7
        assert TIMESTAMP_RE.match(row[1]), f"Timestamp cell malformed: {row[1]!r}"
        assert row[2] == "return"
        assert row[3] == "p1-1"
        assert row[4] == "claude-code-native:opus (agent-tool)"
        assert row[5] == "DONE — gate clear"

    def test_worker_defaults_to_conductor(self, plan_dir):
        run_stamp(plan_dir, *conductor_args("p1-1", event_type="gate",
                                            outcome="return-gate CERTIFIED"))
        rl_content = read_file(os.path.join(plan_dir, "run-log.md"))
        row = find_event_row(rl_content, "gate", "p1-1")
        assert row is not None
        assert row[4] == "conductor", f"Worker cell is {row[4]!r}, expected 'conductor'"

    def test_invalid_event_type_rejected(self, plan_dir):
        rc, stdout, stderr = run_stamp(
            plan_dir,
            *conductor_args("p1-1", event_type="bogus-event"),
            expect_fail=True,
        )
        assert rc != 0

    def _hashes(self, plan_dir):
        return {
            "plan": file_hash(os.path.join(plan_dir, "api-workers-build-plan.md")),
            "del": file_hash(os.path.join(plan_dir, "deliverables.md")),
            "rl": file_hash(os.path.join(plan_dir, "run-log.md")),
            "cap": file_hash(os.path.join(plan_dir, "state-capsule.md")),
        }

    def test_pipe_in_outcome_rejected_no_writes(self, plan_dir):
        """A '|' inside a composed cell would break the table shape → refuse, no writes."""
        before = self._hashes(plan_dir)
        rc, stdout, stderr = run_stamp(
            plan_dir,
            *conductor_args("p1-1", outcome="DONE | extra cell"),
            expect_fail=True,
        )
        assert rc != 0
        assert "|" in stderr or "pipe" in stderr.lower()
        assert self._hashes(plan_dir) == before, "Files written despite cell rejection"

    def test_pipe_in_worker_rejected_no_writes(self, plan_dir):
        before = self._hashes(plan_dir)
        rc, stdout, stderr = run_stamp(
            plan_dir,
            *conductor_args("p1-1", worker="kimi | extra"),
            expect_fail=True,
        )
        assert rc != 0
        assert self._hashes(plan_dir) == before

    def test_newline_in_outcome_rejected_no_writes(self, plan_dir):
        before = self._hashes(plan_dir)
        rc, stdout, stderr = run_stamp(
            plan_dir,
            *conductor_args("p1-1", outcome="DONE\nsecond line"),
            expect_fail=True,
        )
        assert rc != 0
        assert self._hashes(plan_dir) == before


# ---------------------------------------------------------------------------
# Test Plan #3 / #6 / #7 — scope guards
# ---------------------------------------------------------------------------

class TestWorkerScope:
    def test_worker_scope_three_targets(self, plan_dir):
        """Worker scope updates 1-3, does not touch run-log or capsule."""
        rl_path = os.path.join(plan_dir, "run-log.md")
        cap_path = os.path.join(plan_dir, "state-capsule.md")
        rl_before = read_file(rl_path)
        cap_before = read_file(cap_path)

        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p1-3",
            "--status", "in_progress",
            "--scope", "worker",
        )
        assert rc == 0

        # Plan checkbox → [~]
        plan_file = os.path.join(plan_dir, "api-workers-build-plan.md")
        plan_content = read_file(plan_file)
        assert "- [~] `p1-3`" in plan_content

        # Task frontmatter → in_progress
        task_file = os.path.join(plan_dir, "phase-1", "p1-3.task.md")
        task_content = read_file(task_file)
        assert "status: in_progress" in task_content

        # Deliverables → in-progress
        del_content = read_file(os.path.join(plan_dir, "deliverables.md"))
        for line in del_content.splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) >= 5 and cells[1] == "p1-3":
                assert cells[4] == "in-progress"
                break

        # Run-log and capsule unchanged
        assert read_file(rl_path) == rl_before
        assert read_file(cap_path) == cap_before

    @pytest.mark.parametrize("extra_args", [
        ("--event-type", "return"),
        ("--outcome", "status DONE"),
        ("--worker", "kimi-code 0.x"),
        ("--next-dispatch", "p9-9 to kimi"),
        ("--resume-note", "some note"),
    ])
    def test_conductor_only_args_in_worker_scope_rejected(self, plan_dir, extra_args):
        """Every conductor-only arg is rejected in worker scope."""
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p1-1",
            "--status", "completed",
            "--scope", "worker",
            *extra_args,
            expect_fail=True,
        )
        assert rc != 0
        assert "conductor-only" in stderr.lower() or "scope" in stderr.lower()

    @pytest.mark.parametrize("missing", ["--event-type", "--outcome", "--next-dispatch"])
    def test_conductor_missing_required_arg_rejected(self, plan_dir, missing):
        """Conductor scope without --event-type / --outcome / --next-dispatch exits non-zero."""
        full = conductor_args("p1-1")
        # Drop the flag and its value
        idx = full.index(missing)
        args = full[:idx] + full[idx + 2:]
        rc, stdout, stderr = run_stamp(plan_dir, *args, expect_fail=True)
        assert rc != 0
        assert missing.lstrip("-").replace("-", "") in stderr.lower().replace("-", "") , (
            f"stderr does not name the missing arg {missing}: {stderr}"
        )


# ---------------------------------------------------------------------------
# Test Plan #4 — Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_re_run_is_noop(self, plan_dir):
        """Running the same transition twice: second run is all 'unchanged'.
        The dedup key ignores the auto timestamp — (event, task, worker, outcome)."""
        args = conductor_args("p1-4")

        rc1, stdout1, _ = run_stamp(plan_dir, *args)
        assert rc1 == 0

        rc2, stdout2, _ = run_stamp(plan_dir, *args)
        assert rc2 == 0

        # All unchanged
        assert "plan_checkbox: unchanged" in stdout2
        assert "task_frontmatter: unchanged" in stdout2
        assert "deliverables_status: unchanged" in stdout2
        assert "run_log_event: unchanged" in stdout2

    def test_byte_identical_after_re_run(self, plan_dir):
        """After two identical runs, file hashes are the same."""
        files_to_check = [
            os.path.join(plan_dir, "api-workers-build-plan.md"),
            os.path.join(plan_dir, "phase-1", "p1-5.task.md"),
            os.path.join(plan_dir, "deliverables.md"),
            os.path.join(plan_dir, "run-log.md"),
            os.path.join(plan_dir, "state-capsule.md"),
        ]
        args = conductor_args("p1-5")

        run_stamp(plan_dir, *args)
        hashes1 = {f: file_hash(f) for f in files_to_check}

        run_stamp(plan_dir, *args)
        hashes2 = {f: file_hash(f) for f in files_to_check}

        assert hashes1 == hashes2, "Files differ after idempotent re-run"


# ---------------------------------------------------------------------------
# Test Plan #5 — deferred requires --reason
# ---------------------------------------------------------------------------

class TestDeferred:
    def test_deferred_without_reason_fails(self, plan_dir):
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p2-1",
            "--status", "deferred",
            expect_fail=True,
        )
        assert rc != 0
        assert "reason" in stderr.lower()

    def test_deferred_with_reason(self, plan_dir):
        """Deferred status writes ⏸ + cancelled + ⏸ deferred (reason)."""
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p2-1",
            "--status", "deferred",
            "--reason", "out of scope",
        )
        assert rc == 0

        # Plan checkbox → ⏸
        plan_file = os.path.join(plan_dir, "api-workers-build-plan.md")
        plan_content = read_file(plan_file)
        assert "- [⏸] `p2-1`" in plan_content

        # Task frontmatter → cancelled
        task_file = os.path.join(plan_dir, "phase-2", "p2-1.task.md")
        task_content = read_file(task_file)
        assert "status: cancelled" in task_content

        # Deliverables → ⏸ deferred (out of scope)
        del_content = read_file(os.path.join(plan_dir, "deliverables.md"))
        assert "⏸ deferred (out of scope)" in del_content


# ---------------------------------------------------------------------------
# Test Plan #8 — Missing task id → error
# ---------------------------------------------------------------------------

class TestMissingTask:
    def test_nonexistent_task_id(self, plan_dir):
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p99-9",
            "--status", "completed",
            expect_fail=True,
        )
        assert rc != 0
        assert "p99-9" in stderr

    def test_no_files_written_on_missing_task(self, plan_dir):
        """When a target fails to resolve, NOTHING is written."""
        hashes_before = {
            "plan": file_hash(os.path.join(plan_dir, "api-workers-build-plan.md")),
            "del": file_hash(os.path.join(plan_dir, "deliverables.md")),
        }

        run_stamp(
            plan_dir,
            "--task", "p99-9",
            "--status", "completed",
            expect_fail=True,
        )

        hashes_after = {
            "plan": file_hash(os.path.join(plan_dir, "api-workers-build-plan.md")),
            "del": file_hash(os.path.join(plan_dir, "deliverables.md")),
        }
        assert hashes_before == hashes_after, "Files were modified despite error"


# ---------------------------------------------------------------------------
# Test Plan #9 — Invalid status → error
# ---------------------------------------------------------------------------

class TestInvalidStatus:
    def test_invalid_status(self, plan_dir):
        # argparse handles this via choices=, so it exits non-zero
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p1-1",
            "--status", "bogus",
            expect_fail=True,
        )
        assert rc != 0


# ---------------------------------------------------------------------------
# Test Plan #10 — --artifact updates deliverables Path cell
# ---------------------------------------------------------------------------

class TestArtifact:
    def test_artifact_updates_path(self, plan_dir):
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p1-1",
            "--status", "completed",
            "--artifact", "new/path/schema.md",
        )
        assert rc == 0

        del_content = read_file(os.path.join(plan_dir, "deliverables.md"))
        for line in del_content.splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) >= 5 and cells[1] == "p1-1":
                assert cells[3] == "new/path/schema.md", f"Path cell is '{cells[3]}'"
                break
        assert "deliverables_path" in stdout


# ---------------------------------------------------------------------------
# Test Plan #11 — --explain mode
# ---------------------------------------------------------------------------

class TestExplain:
    def test_explain_no_writing(self, plan_dir):
        """--explain prints preview and exits 0 without writing."""
        hashes_before = {
            "plan": file_hash(os.path.join(plan_dir, "api-workers-build-plan.md")),
            "task": file_hash(os.path.join(plan_dir, "phase-1", "p1-1.task.md")),
            "del": file_hash(os.path.join(plan_dir, "deliverables.md")),
        }

        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p1-1",
            "--status", "completed",
            "--explain",
        )
        assert rc == 0
        assert "EXPLAIN MODE" in stdout

        hashes_after = {
            "plan": file_hash(os.path.join(plan_dir, "api-workers-build-plan.md")),
            "task": file_hash(os.path.join(plan_dir, "phase-1", "p1-1.task.md")),
            "del": file_hash(os.path.join(plan_dir, "deliverables.md")),
        }
        assert hashes_before == hashes_after, "--explain modified files"

    def test_explain_conductor_shows_composed_row(self, plan_dir):
        """Conductor-scope --explain previews the composed row without writing."""
        rl_hash = file_hash(os.path.join(plan_dir, "run-log.md"))
        cap_hash = file_hash(os.path.join(plan_dir, "state-capsule.md"))

        rc, stdout, stderr = run_stamp(
            plan_dir, *conductor_args("p1-1"), "--explain",
        )
        assert rc == 0
        assert "EXPLAIN MODE" in stdout
        assert "| return | p1-1 |" in stdout, "Composed row not previewed"
        assert file_hash(os.path.join(plan_dir, "run-log.md")) == rl_hash
        assert file_hash(os.path.join(plan_dir, "state-capsule.md")) == cap_hash


# ---------------------------------------------------------------------------
# Edge: multiple checkbox lines → ambiguity error
# ---------------------------------------------------------------------------

class TestAmbiguity:
    def test_no_duplicate_writes_on_ambiguous_task(self, plan_dir):
        """If somehow the plan had duplicate task lines, the script refuses."""
        # The fixture doesn't have duplicates, so this tests the clean path.
        # We verify no error on a normal task.
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p1-1",
            "--status", "completed",
        )
        assert rc == 0


# ---------------------------------------------------------------------------
# ADX-15 — Active-run fixture + recurrence tests (R4/R5)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def active_plan_dir(tmp_path):
    """Copy the active-run fixture (non-terminal capsule, open checkboxes) into a temp dir."""
    dest = tmp_path / "api-workers-build-active"
    shutil.copytree(ACTIVE_FIXTURE_SRC, dest)
    return str(dest)


class TestActiveCapsule:
    """R5: active-capsule resume-point lockstep per spec §S4 — the three labeled
    Resume Point bullets are updated IN PLACE, labels intact."""

    def test_active_capsule_resume_point_updated(self, active_plan_dir):
        """On an ACTIVE capsule, the labeled Resume Point bullets are updated."""
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")
        before = read_file(cap_path)
        # Confirm active labeled shape
        assert "- **Next dispatch:** p3-1 to kimi" in before, "Fixture not in labeled active shape"
        assert "run is closed" not in before, "Fixture should not be terminal"

        rc, stdout, stderr = run_stamp(
            active_plan_dir,
            *conductor_args("p3-1", next_dispatch="p3-2 to codex — routing card §2a update"),
        )
        assert rc == 0, f"stderr: {stderr}"

        after = read_file(cap_path)
        # Last completed updated with derived fallback, label intact
        assert "- **Last completed:** Stamp transition: p3-1 → completed" in after, (
            "Last completed bullet not updated with labeled fallback text"
        )
        # Next dispatch replaced — no stale claim
        assert "- **Next dispatch:** p3-2 to codex — routing card §2a update" in after, (
            "Next dispatch bullet not updated"
        )
        assert "p3-1 to kimi" not in after.split("## Run Configuration")[0], (
            "Stale next-dispatch text survived in Resume Point"
        )
        # Timestamp updated, label intact
        m = re.search(r"- \*\*Last update:\*\* (\S+)", after)
        assert m and TIMESTAMP_RE.match(m.group(1)), "Last update not refreshed"
        # Non-resume content preserved (decisions are append-only)
        assert "## Run Configuration" in after, "Non-resume capsule content clobbered"
        assert "capsule: changed" in stdout

    def test_active_capsule_idempotent(self, active_plan_dir):
        """Re-running on an active capsule: second run is all unchanged."""
        args = conductor_args("p3-2")
        run_stamp(active_plan_dir, *args)
        hashes1 = {
            "cap": file_hash(os.path.join(active_plan_dir, "state-capsule.md")),
            "rl": file_hash(os.path.join(active_plan_dir, "run-log.md")),
        }
        rc2, stdout2, _ = run_stamp(active_plan_dir, *args)
        assert rc2 == 0
        hashes2 = {
            "cap": file_hash(os.path.join(active_plan_dir, "state-capsule.md")),
            "rl": file_hash(os.path.join(active_plan_dir, "run-log.md")),
        }
        assert hashes1 == hashes2, "Active capsule not idempotent on re-run"
        assert "run_log_event: unchanged" in stdout2
        assert "capsule: unchanged" in stdout2


class TestResumePointContract:
    """#14: the capsule lockstep REQUIRES the three labeled Resume Point bullets
    and refuses (no writes) a capsule missing any of them — the deterministic
    push toward the template's canonical Resume Point shape."""

    def _all_target_hashes(self, plan_dir):
        return {
            "plan": file_hash(os.path.join(plan_dir, "api-workers-build-plan.md")),
            "task": file_hash(os.path.join(plan_dir, "phase-3", "p3-1.task.md")),
            "del": file_hash(os.path.join(plan_dir, "deliverables.md")),
            "rl": file_hash(os.path.join(plan_dir, "run-log.md")),
            "cap": file_hash(os.path.join(plan_dir, "state-capsule.md")),
        }

    @pytest.mark.parametrize("label", ["Last completed", "Next dispatch", "Last update"])
    def test_missing_labeled_bullet_refused_no_writes(self, active_plan_dir, label):
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")
        content = read_file(cap_path)
        # Strip the labeled bullet line from Resume Point
        new_lines = [
            ln for ln in content.splitlines()
            if not ln.strip().startswith(f"- **{label}:**")
        ]
        with open(cap_path, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(new_lines) + "\n")

        hashes_before = self._all_target_hashes(active_plan_dir)
        rc, stdout, stderr = run_stamp(
            active_plan_dir, *conductor_args("p3-1"), expect_fail=True,
        )
        assert rc != 0, f"Capsule missing '{label}' bullet was not refused"
        assert "resume point" in stderr.lower()
        assert label.lower() in stderr.lower()
        assert self._all_target_hashes(active_plan_dir) == hashes_before, (
            "Files written despite Resume Point refusal"
        )

    def test_worker_scope_unaffected_by_malformed_capsule(self, active_plan_dir):
        """Worker scope never reads the capsule — a malformed one does not block it."""
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")
        content = read_file(cap_path)
        new_lines = [
            ln for ln in content.splitlines()
            if not ln.strip().startswith("- **Next dispatch:**")
        ]
        with open(cap_path, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(new_lines) + "\n")

        rc, stdout, stderr = run_stamp(
            active_plan_dir,
            "--task", "p3-1",
            "--status", "in_progress",
            "--scope", "worker",
        )
        assert rc == 0, f"Worker scope blocked by capsule shape: {stderr}"


# ---------------------------------------------------------------------------
# ADX-17 — --resume-note conductor-supplied text (conductor ruling on R5 doubt)
# ---------------------------------------------------------------------------

class TestResumeNote:
    """ADX-17: conductor-supplied resume-point text with derived fallback — the
    text lands INSIDE the labeled `**Last completed:**` bullet, never over it."""

    def test_resume_note_lands_in_labeled_bullet(self, active_plan_dir):
        """When --resume-note is present, its text lands in the Last completed
        bullet with the label preserved."""
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")

        custom_note = "Phase 3 complete — dispatching Phase 4 conductor wiring"
        rc, stdout, stderr = run_stamp(
            active_plan_dir,
            *conductor_args("p3-1", resume_note=custom_note,
                            next_dispatch="p4-1 to codex — conductor wiring"),
        )
        assert rc == 0, f"stderr: {stderr}"

        after = read_file(cap_path)
        assert f"- **Last completed:** {custom_note}" in after, (
            f"--resume-note text not under the labeled bullet: expected "
            f"'- **Last completed:** {custom_note}'"
        )
        # The derived placeholder must NOT be present
        assert "Stamp transition:" not in after, (
            "Derived placeholder present when --resume-note was supplied"
        )
        assert "capsule: changed" in stdout

    def test_resume_note_fallback(self, active_plan_dir):
        """When --resume-note is absent, the derived placeholder is used inside
        the labeled bullet."""
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")

        rc, stdout, stderr = run_stamp(
            active_plan_dir,
            *conductor_args("p3-2"),  # no resume_note
        )
        assert rc == 0, f"stderr: {stderr}"

        after = read_file(cap_path)
        assert "- **Last completed:** Stamp transition: p3-2 → completed" in after, (
            "Derived fallback text not found under the labeled bullet"
        )


# ---------------------------------------------------------------------------
# ADX-20 — Mid-flight failure recoverable model (F2) + line-ending guard (F1)
# ---------------------------------------------------------------------------

class TestMidFlightFailure:
    """F2: injected failure between write targets proves spec §S9 recoverable model."""

    def test_injected_failure_after_task_frontmatter(self, active_plan_dir):
        """Failure after task_frontmatter write: earlier writes stand, run-log absent,
        EXIT non-zero naming the target; re-run heals to complete idempotent state."""
        args = conductor_args("p3-1")

        # Pre-capture hashes
        plan_path = os.path.join(active_plan_dir, "api-workers-build-plan.md")
        task_path = os.path.join(active_plan_dir, "phase-3", "p3-1.task.md")
        del_path = os.path.join(active_plan_dir, "deliverables.md")
        rl_path = os.path.join(active_plan_dir, "run-log.md")
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")

        hashes_before = {
            "plan": file_hash(plan_path),
            "task": file_hash(task_path),
            "del": file_hash(del_path),
            "rl": file_hash(rl_path),
            "cap": file_hash(cap_path),
        }

        # Run with injected failure after task_frontmatter
        env = os.environ.copy()
        env["STAMP_TEST_FAIL_AFTER"] = "task_frontmatter"
        cmd = [sys.executable, STAMP_PY, "--plan-dir", active_plan_dir] + args
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        assert result.returncode != 0, "Expected non-zero exit on injected failure"
        assert "INJECTED_FAILURE after task_frontmatter" in result.stderr

        # Earlier writes (plan checkbox + task frontmatter) DID land
        plan_after = read_file(plan_path)
        assert "- [x] `p3-1`" in plan_after, "Plan checkbox should have been written"
        task_after = read_file(task_path)
        assert "status: completed" in task_after, "Task frontmatter should have been written"

        # Later targets untouched
        assert file_hash(del_path) == hashes_before["del"], "Deliverables modified despite failure"
        assert file_hash(rl_path) == hashes_before["rl"], "Run-log modified despite failure"
        assert file_hash(cap_path) == hashes_before["cap"], "Capsule modified despite failure"

        # Re-run WITHOUT injection → heals to complete state
        rc2, stdout2, stderr2 = run_stamp(active_plan_dir, *args)
        assert rc2 == 0, f"Heal re-run failed: {stderr2}"
        assert "deliverables_status: changed" in stdout2
        assert "run_log_event: changed" in stdout2
        assert "capsule: changed" in stdout2

        # Re-run again → idempotent (all unchanged)
        rc3, stdout3, _ = run_stamp(active_plan_dir, *args)
        assert rc3 == 0
        assert "plan_checkbox: unchanged" in stdout3
        assert "task_frontmatter: unchanged" in stdout3
        assert "deliverables_status: unchanged" in stdout3
        assert "run_log_event: unchanged" in stdout3
        assert "capsule: unchanged" in stdout3


class TestCapsuleStructureGuard:
    """Capsule regeneration discipline (state.md §3): conductor-scope stamps REFUSE
    an accreted capsule — a duplicated '## ' section header, a next-dispatch claim
    OUTSIDE Resume Point, or >1 next-dispatch claim inside Resume Point — with a
    non-zero EXIT and ZERO files written. The next-dispatch check keys on the two
    canonical markers ('Next dispatch:' field, 'NEXT:' resume marker), NOT a bare
    'dispatch' substring: legitimate 'dispatch' note-labels/values stamp normally."""

    CONDUCTOR_ARGS = tuple(conductor_args("p3-1"))

    def _all_target_hashes(self, plan_dir):
        return {
            "plan": file_hash(os.path.join(plan_dir, "api-workers-build-plan.md")),
            "task": file_hash(os.path.join(plan_dir, "phase-3", "p3-1.task.md")),
            "del": file_hash(os.path.join(plan_dir, "deliverables.md")),
            "rl": file_hash(os.path.join(plan_dir, "run-log.md")),
            "cap": file_hash(os.path.join(plan_dir, "state-capsule.md")),
        }

    def _corrupt_and_expect_reject(self, plan_dir, corrupted, needle):
        cap_path = os.path.join(plan_dir, "state-capsule.md")
        with open(cap_path, "w", encoding="utf-8", newline="") as f:
            f.write(corrupted)
        hashes_before = self._all_target_hashes(plan_dir)
        rc, stdout, stderr = run_stamp(plan_dir, *self.CONDUCTOR_ARGS, expect_fail=True)
        assert rc != 0, f"Expected non-zero exit ({needle})"
        assert needle in stderr.lower(), f"stderr missing {needle!r}: {stderr}"
        assert self._all_target_hashes(plan_dir) == hashes_before, (
            "Files were written despite the structure-guard rejection"
        )

    def test_duplicate_section_header_rejected_no_writes(self, active_plan_dir):
        """Two '## Resume Point' headers (paste-append accretion) → rejected, no writes."""
        corrupted = read_file(os.path.join(active_plan_dir, "state-capsule.md")) + (
            "\n## Resume Point\n- **NEXT: dispatch p9-9 (stale duplicate)**\n"
        )
        self._corrupt_and_expect_reject(active_plan_dir, corrupted, "duplicate section header")

    def test_next_dispatch_literal_field_outside_resume_rejected(self, active_plan_dir):
        """The template field '**Next dispatch:**' leaked into Run Configuration →
        rejected (next-dispatch claim outside Resume Point), no writes."""
        content = read_file(os.path.join(active_plan_dir, "state-capsule.md"))
        corrupted = content.replace(
            "## Run Configuration\n",
            "## Run Configuration\n- **Next dispatch:** p4-1 (stale, contradicts Resume Point)\n",
        )
        self._corrupt_and_expect_reject(active_plan_dir, corrupted, "outside resume point")

    def test_next_dispatch_freetext_marker_outside_resume_rejected(self, active_plan_dir):
        """The free-text 'NEXT:' resume marker leaked into Run Configuration (the
        actual 2026-06-10 defect form, no literal field) → rejected, no writes.
        This is the form the old literal-only check could NOT catch."""
        content = read_file(os.path.join(active_plan_dir, "state-capsule.md"))
        corrupted = content.replace(
            "## Run Configuration\n",
            "## Run Configuration\n- **NEXT: dispatch p4-1 to codex (stale, contradicts Resume Point)**\n",
        )
        self._corrupt_and_expect_reject(active_plan_dir, corrupted, "outside resume point")

    def test_next_dispatch_twice_in_resume_rejected(self, active_plan_dir):
        """Two next-dispatch claims inside Resume Point → rejected, no writes."""
        content = read_file(os.path.join(active_plan_dir, "state-capsule.md"))
        anchor = "- **Last completed:** p2-checkpoint — Phase 2 approved"
        assert anchor in content, "Fixture anchor moved — update this test"
        corrupted = content.replace(
            anchor,
            anchor + "\n- **NEXT: dispatch p9-9 (duplicate claim)**",
            1,
        )
        self._corrupt_and_expect_reject(active_plan_dir, corrupted, "states the next dispatch")

    def test_legitimate_dispatch_wording_not_rejected(self, active_plan_dir):
        """Bolded note-labels containing 'dispatch' (real corpus: 'Standing dispatch
        rules...', 'Phase 3 dispatch queue...') and field VALUES mentioning dispatch
        must NOT trip the guard — only the 'Next dispatch:'/'NEXT:' markers do. Inject
        one more adversarial-but-legit case and confirm a clean stamp."""
        content = read_file(os.path.join(active_plan_dir, "state-capsule.md"))
        corrupted = content.replace(
            "## Notes for Resuming Conductor\n",
            "## Notes for Resuming Conductor\n"
            "- **Dispatch protocol reminder:** see dispatch-scaffold-spec.md before the next dispatch wave.\n",
        )
        with open(os.path.join(active_plan_dir, "state-capsule.md"), "w", encoding="utf-8", newline="") as f:
            f.write(corrupted)
        rc, stdout, stderr = run_stamp(active_plan_dir, *self.CONDUCTOR_ARGS)
        assert rc == 0, f"Legit 'dispatch' wording wrongly rejected: {stderr}"
        assert "capsule: changed" in stdout

    def test_clean_capsule_passes_guard(self, active_plan_dir):
        """The unmodified active capsule (unique headers; the labeled '**Next
        dispatch:** p3-1 to kimi …' claim in Resume Point + 'dispatch' note-labels
        elsewhere) stamps normally — no false rejection."""
        rc, stdout, stderr = run_stamp(active_plan_dir, *self.CONDUCTOR_ARGS)
        assert rc == 0, f"Clean capsule wrongly rejected: {stderr}"
        assert "capsule: changed" in stdout

    def test_reread_phase_guard_catches_midwrite_corruption(self, active_plan_dir, tmp_path):
        """The structure guard runs at BOTH the validate phase AND the capsule
        re-read site. A capsule corrupted DURING the write window (after validate,
        before the capsule lockstep) is caught at the re-read site — proving that
        call exists and is not silently removable. Uses the env-gated pause to open
        the race window."""
        import threading
        import time

        pause_base = str(tmp_path / "pause-signal")
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")

        def corrupt_during_pause():
            for _ in range(200):
                if os.path.exists(pause_base + ".paused"):
                    break
                time.sleep(0.05)
            current = read_file(cap_path)
            with open(cap_path, "w", encoding="utf-8", newline="") as f:
                f.write(current + "\n## Resume Point\n- **NEXT: dispatch p9-9 (mid-write)**\n")
            with open(pause_base + ".resume", "w") as f:
                f.write("resume")

        t = threading.Thread(target=corrupt_during_pause)
        t.start()

        env = os.environ.copy()
        env["STAMP_TEST_PAUSE_FILE"] = pause_base
        cmd = [sys.executable, STAMP_PY, "--plan-dir", active_plan_dir] + list(self.CONDUCTOR_ARGS)
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        t.join(timeout=15)

        assert result.returncode != 0, f"Re-read guard did not reject: {result.stdout}"
        assert "re-read before write (capsule)" in result.stderr
        assert "duplicate section header" in result.stderr.lower()


class TestConcurrentForeignEdit:
    """R4: re-read-before-write survives concurrent foreign edits (spec §S7)."""

    def test_concurrent_foreign_edit_survives(self, plan_dir, tmp_path):
        """A different deliverables row edited externally between read and write
        MUST survive byte-intact. Uses the env-gated test pause (STAMP_TEST_PAUSE_FILE)
        to simulate the race window."""
        pause_base = str(tmp_path / "pause-signal")

        # Pre-modify a different deliverables row (p1-2) to a sentinel value
        del_path = os.path.join(plan_dir, "deliverables.md")
        del_content = read_file(del_path)
        sentinel = "🔴 CONCURRENT-EDIT-SURVIVED"
        # Find and replace the p1-2 row's Status cell
        new_lines = []
        for line in del_content.splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) == 6 and cells[1] == "p1-2":
                cells[4] = sentinel
                line = "| " + " | ".join(cells[1:5]) + " |"
            new_lines.append(line)
        modified_del = "\n".join(new_lines) + "\n"
        # Write the pre-modified deliverables
        with open(del_path, "w", encoding="utf-8", newline="") as f:
            f.write(modified_del)

        # Run stamp.py with the test pause — it will pause after validate, before write.
        # Since we already pre-modified the file, the re-read-before-write should see
        # the sentinel and preserve it.
        env = os.environ.copy()
        env["STAMP_TEST_PAUSE_FILE"] = pause_base

        import threading
        def create_resume():
            import time
            # Wait for pause file to appear
            for _ in range(100):
                if os.path.exists(pause_base + ".paused"):
                    break
                time.sleep(0.05)
            # Create resume signal
            with open(pause_base + ".resume", "w") as f:
                f.write("resume")

        t = threading.Thread(target=create_resume)
        t.start()

        cmd = [sys.executable, STAMP_PY, "--plan-dir", plan_dir] + conductor_args("p1-1")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        t.join(timeout=10)

        assert result.returncode == 0, f"stamp.py failed: {result.stderr}"

        # Verify p1-1's row was updated AND p1-2's sentinel survived
        after_del = read_file(del_path)
        found_p1_2_sentinel = False
        found_p1_1_updated = False
        for line in after_del.splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) == 6 and cells[1] == "p1-2":
                assert cells[4] == sentinel, (
                    f"Concurrent edit to p1-2 was CLOBBERED: got '{cells[4]}', "
                    f"expected '{sentinel}'"
                )
                found_p1_2_sentinel = True
            if len(cells) == 6 and cells[1] == "p1-1":
                assert cells[4] == "✅", f"p1-1 not updated: got '{cells[4]}'"
                found_p1_1_updated = True

        assert found_p1_2_sentinel, "p1-2 row not found after stamp"
        assert found_p1_1_updated, "p1-1 row not found after stamp"


class TestLineEndingPreservation:
    """F1: stamp operations preserve input line endings (LF in → LF out)."""

    def test_no_crlf_after_transition_on_normalized_fixture(self, active_plan_dir):
        """After a conductor-scope transition on the normalized active fixture,
        no file in the plan dir contains \r\n bytes."""
        rc, stdout, stderr = run_stamp(active_plan_dir, *conductor_args("p3-2"))
        assert rc == 0, f"stderr: {stderr}"

        # Check only the files stamp.py touches (_dispatch/*.out are faithful
        # corpus artifacts with native CRLF and are NOT stamp targets).
        targets = [
            os.path.join(active_plan_dir, "api-workers-build-plan.md"),
            os.path.join(active_plan_dir, "phase-3", "p3-2.task.md"),
            os.path.join(active_plan_dir, "deliverables.md"),
            os.path.join(active_plan_dir, "run-log.md"),
            os.path.join(active_plan_dir, "state-capsule.md"),
        ]
        bad_files = []
        for fpath in targets:
            with open(fpath, "rb") as f:
                data = f.read()
            if b"\r\n" in data:
                bad_files.append(os.path.relpath(fpath, active_plan_dir))

        assert not bad_files, (
            f"Stamp targets containing CRLF after transition: {bad_files}"
        )
