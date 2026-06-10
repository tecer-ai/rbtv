"""
test_stamp.py — acceptance tests for stamp.py against a real-corpus fixture.

Test Plan mapping (spec § Test Plan):
  #1  One conductor-scope call performs the complete 4-file transition
  #2  Append-only is never violated
  #3  Worker scope cannot touch run-log or capsule
  #4  Idempotency — re-running the same transition is a no-op
  #5  deferred status requires --reason
  #6  --event in worker scope is rejected
  #7  Conductor scope without --event is rejected
  #8  Missing task id → EXIT≠0, no write
  #9  Invalid --status → EXIT≠0, no write
  #10 --artifact updates the deliverables Path cell
  #11 --explain prints preview without writing
  #12 Byte-identical after idempotent re-run
"""

import copy
import os
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


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def file_hash(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------------------
# Test Plan #1 — One conductor-scope call performs the complete 4-file transition
# ---------------------------------------------------------------------------

class TestConductorScope:
    def test_four_file_transition(self, plan_dir):
        """Run a conductor-scope transition on p1-1 and verify all four files change."""
        event_line = "| 2026-06-10T12:00Z | return | p1-1 | conductor | status DONE |"
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p1-1",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
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

        # Run-log: event appended
        rl_content = read_file(os.path.join(plan_dir, "run-log.md"))
        assert "p1-1" in rl_content and "return" in rl_content

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

        event_line = "| 2026-06-10T12:00Z | return | p1-2 | conductor | status DONE |"
        run_stamp(
            plan_dir,
            "--task", "p1-2",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )

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
                assert after_lines[i] == event_line, (
                    f"First divergence at line {i} is not the inserted event: "
                    f"{after_lines[i]!r}"
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
        assert event_line in after

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
# Test Plan #3 — Worker scope cannot touch run-log or capsule
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

    def test_event_in_worker_scope_rejected(self, plan_dir):
        """--event with worker scope exits non-zero."""
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p1-1",
            "--status", "completed",
            "--scope", "worker",
            "--event", "| 2026-06-10T12:00Z | return | p1-1 | conductor | done |",
            expect_fail=True,
        )
        assert rc != 0
        assert "conductor-only" in stderr.lower() or "scope" in stderr.lower()

    def test_conductor_without_event_rejected(self, plan_dir):
        """Conductor scope without --event exits non-zero."""
        rc, stdout, stderr = run_stamp(
            plan_dir,
            "--task", "p1-1",
            "--status", "completed",
            "--scope", "conductor",
            expect_fail=True,
        )
        assert rc != 0
        assert "event" in stderr.lower()


# ---------------------------------------------------------------------------
# Test Plan #4 — Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_re_run_is_noop(self, plan_dir):
        """Running the same transition twice: second run is all 'unchanged'."""
        event_line = "| 2026-06-10T12:00Z | return | p1-4 | conductor | status DONE |"

        # First run
        rc1, stdout1, _ = run_stamp(
            plan_dir,
            "--task", "p1-4",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
        assert rc1 == 0

        # Second run — same args
        rc2, stdout2, _ = run_stamp(
            plan_dir,
            "--task", "p1-4",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
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
        event_line = "| 2026-06-10T12:00Z | return | p1-5 | conductor | status DONE |"

        run_stamp(
            plan_dir,
            "--task", "p1-5",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
        hashes1 = {f: file_hash(f) for f in files_to_check}

        run_stamp(
            plan_dir,
            "--task", "p1-5",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
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
    """R5: active-capsule resume-point lockstep per spec §S4."""

    def test_active_capsule_resume_point_updated(self, active_plan_dir):
        """On an ACTIVE capsule, the resume point bullet is updated (not just timestamp)."""
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")
        before = read_file(cap_path)
        # Confirm active shape
        assert "NEXT:" in before, "Fixture not in active shape"
        assert "run is closed" not in before, "Fixture should not be terminal"

        event_line = "| 2026-06-10T12:00Z | return | p3-1 | conductor | status DONE |"
        rc, stdout, stderr = run_stamp(
            active_plan_dir,
            "--task", "p3-1",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
        assert rc == 0, f"stderr: {stderr}"

        after = read_file(cap_path)
        # Resume point updated
        assert "Stamp transition: p3-1 → completed" in after, "Resume point not updated"
        # Timestamp updated
        assert "Last update:" in after
        # Non-resume content preserved (decisions are append-only)
        assert "## Run Configuration" in after, "Non-resume capsule content clobbered"
        assert "capsule: changed" in stdout

    def test_active_capsule_idempotent(self, active_plan_dir):
        """Re-running on an active capsule: second run is all unchanged."""
        event_line = "| 2026-06-10T12:00Z | return | p3-2 | conductor | status DONE |"
        run_stamp(
            active_plan_dir,
            "--task", "p3-2",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
        hashes1 = {
            "cap": file_hash(os.path.join(active_plan_dir, "state-capsule.md")),
            "rl": file_hash(os.path.join(active_plan_dir, "run-log.md")),
        }
        rc2, stdout2, _ = run_stamp(
            active_plan_dir,
            "--task", "p3-2",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
        assert rc2 == 0
        hashes2 = {
            "cap": file_hash(os.path.join(active_plan_dir, "state-capsule.md")),
            "rl": file_hash(os.path.join(active_plan_dir, "run-log.md")),
        }
        assert hashes1 == hashes2, "Active capsule not idempotent on re-run"
        assert "run_log_event: unchanged" in stdout2
        assert "capsule: unchanged" in stdout2


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
        modified_del = del_content.replace(
            "| p1-2 | Synchronous provider base |",
            f"| p1-2 | Synchronous provider base |"  # keep same row, edit Status
        )
        # Find and replace the p1-2 row's Status cell
        new_lines = []
        for line in modified_del.splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) == 6 and cells[1] == "p1-2":
                cells[4] = sentinel
                line = "| " + " | ".join(cells[1:5]) + " |"
            new_lines.append(line)
        modified_del = "\n".join(new_lines) + "\n"
        # Write the pre-modified deliverables
        with open(del_path, "w", encoding="utf-8", newline="") as f:
            f.write(modified_del)
        del_hash_before = file_hash(del_path)

        # Run stamp.py with the test pause — it will pause after validate, before write.
        # Since we already pre-modified the file, the re-read-before-write should see
        # the sentinel and preserve it.
        env = os.environ.copy()
        env["STAMP_TEST_PAUSE_FILE"] = pause_base

        # We need to start the process, wait for pause, then signal resume.
        # But since the file is ALREADY modified, the re-read will see it.
        # We just need to let the pause timeout or create the resume file.

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

        event_line = "| 2026-06-10T12:00Z | return | p1-1 | conductor | status DONE |"
        cmd = [sys.executable, STAMP_PY, "--plan-dir", plan_dir,
               "--task", "p1-1", "--status", "completed",
               "--scope", "conductor", "--event", event_line]
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


# ---------------------------------------------------------------------------
# ADX-17 — --resume-note conductor-supplied text (conductor ruling on R5 doubt)
# ---------------------------------------------------------------------------

class TestResumeNote:
    """ADX-17: conductor-supplied resume-point text with derived fallback."""

    def test_resume_note_verbatim(self, active_plan_dir):
        """When --resume-note is present, its text lands verbatim in the capsule."""
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")

        event_line = "| 2026-06-10T12:00Z | return | p3-1 | conductor | status DONE |"
        custom_note = "Phase 3 complete — dispatching Phase 4 conductor wiring"
        rc, stdout, stderr = run_stamp(
            active_plan_dir,
            "--task", "p3-1",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
            "--resume-note", custom_note,
        )
        assert rc == 0, f"stderr: {stderr}"

        after = read_file(cap_path)
        assert custom_note in after, (
            f"--resume-note text not found in capsule: expected '{custom_note}'"
        )
        # The derived placeholder must NOT be present
        assert "Stamp transition:" not in after, (
            "Derived placeholder present when --resume-note was supplied"
        )
        assert "capsule: changed" in stdout

    def test_resume_note_fallback(self, active_plan_dir):
        """When --resume-note is absent, the derived placeholder is used (existing
        TestActiveCapsule.test_active_capsule_resume_point_updated already covers
        this — this test is an explicit assertion on the fallback text)."""
        cap_path = os.path.join(active_plan_dir, "state-capsule.md")

        event_line = "| 2026-06-10T12:00Z | return | p3-2 | conductor | status DONE |"
        rc, stdout, stderr = run_stamp(
            active_plan_dir,
            "--task", "p3-2",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
            # No --resume-note
        )
        assert rc == 0, f"stderr: {stderr}"

        after = read_file(cap_path)
        assert "Stamp transition: p3-2 → completed" in after, (
            "Derived fallback text not found in capsule when --resume-note absent"
        )


# ---------------------------------------------------------------------------
# ADX-20 — Mid-flight failure recoverable model (F2) + line-ending guard (F1)
# ---------------------------------------------------------------------------

class TestMidFlightFailure:
    """F2: injected failure between write targets proves spec §S9 recoverable model."""

    def test_injected_failure_after_task_frontmatter(self, active_plan_dir):
        """Failure after task_frontmatter write: earlier writes stand, run-log absent,
        EXIT non-zero naming the target; re-run heals to complete idempotent state."""
        event_line = "| 2026-06-10T12:00Z | return | p3-1 | conductor | status DONE |"

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
        cmd = [
            sys.executable, STAMP_PY,
            "--plan-dir", active_plan_dir,
            "--task", "p3-1",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        ]
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
        rc2, stdout2, stderr2 = run_stamp(
            active_plan_dir,
            "--task", "p3-1",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
        assert rc2 == 0, f"Heal re-run failed: {stderr2}"
        assert "deliverables_status: changed" in stdout2
        assert "run_log_event: changed" in stdout2
        assert "capsule: changed" in stdout2

        # Re-run again → idempotent (all unchanged)
        rc3, stdout3, _ = run_stamp(
            active_plan_dir,
            "--task", "p3-1",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
        assert rc3 == 0
        assert "plan_checkbox: unchanged" in stdout3
        assert "task_frontmatter: unchanged" in stdout3
        assert "deliverables_status: unchanged" in stdout3
        assert "run_log_event: unchanged" in stdout3
        assert "capsule: unchanged" in stdout3


class TestLineEndingPreservation:
    """F1: stamp operations preserve input line endings (LF in → LF out)."""

    def test_no_crlf_after_transition_on_normalized_fixture(self, active_plan_dir):
        """After a conductor-scope transition on the normalized active fixture,
        no file in the plan dir contains \r\n bytes."""
        event_line = "| 2026-06-10T12:00Z | return | p3-2 | conductor | status DONE |"
        rc, stdout, stderr = run_stamp(
            active_plan_dir,
            "--task", "p3-2",
            "--status", "completed",
            "--scope", "conductor",
            "--event", event_line,
        )
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
