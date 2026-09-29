"""m7 — the six probe cases, each run in BOTH write regimes.

Every test below is parameterised over `regime`, and the regime's name is carried
into the assertion message, because the milestone this suite serves is not done
if a criterion holds in one regime and not the other.

Nothing here touches a live destination: `harness.Scratch` builds a bare remote
and a clone of it under a scratch root outside the workspace, and deletes them.
"""

from __future__ import annotations

import json
import signal
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import harness as H          # noqa: E402
import publish_job as P      # noqa: E402

REGIMES = ["git", "vault"]


@pytest.fixture(params=REGIMES)
def world(request):
    """A scratch world with this regime's destination repo already built."""
    scratch = H.Scratch()
    regime = request.param
    repo = H.REGIME_REPO[regime]
    scratch.repo(repo)
    scratch.regime = regime
    scratch.repo_name = repo
    scratch.checkout = scratch.checkouts / repo
    scratch.job_names = ({"first": "alpha-first", "second": "alpha-second"} if regime == "git"
                         else {"first": "clinic-first", "second": "clinic-second"})
    yield scratch
    scratch.clean()


def cycle(world, job, summarizer, bus=None, transcripts=("meet",)):
    return P.run_cycle(job, config_root=H.CONFIG_ROOT, checkout_root=world.checkouts,
                       state=world.state, transcripts=H.transcripts(*transcripts),
                       summarize=summarizer, bus=bus or H.Bus())


def summary_text(key, note="body"):
    return f"# resumo\n\nmeeting-key: {key}\n\n{note}\n"


def filed_files(world) -> list[str]:
    """Every markdown file this layer could have filed, repo-relative."""
    return sorted(str(p.relative_to(world.checkout))
                  for p in world.checkout.rglob("*.md")
                  if ".git" not in p.parts and p.name != "README.md")


def commits_touching(world, path: str) -> list[str]:
    proc = H.git(world.checkout, "log", "--format=%H", "--", path)
    return [line for line in proc.stdout.split() if line]


def git_call_sites(path: Path) -> list[list[str]]:
    """Every `git(...)` invocation in the layer, as its literal argument words.

    Only literal words are collected; a non-literal argument is kept as '?' so a
    call can never disappear from the tally by being computed.
    """
    import ast
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "git":
            words = []
            for arg in node.args[1:]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    words.append(arg.value)
                elif isinstance(arg, ast.Starred):
                    words.append("*")
                else:
                    words.append("?")
            found.append(words)
    return found


# ------------------------------------------------------- case (a) idempotence
def test_case_a_second_run_writes_nothing_new(world):
    job = H.job(world.job_names["first"])
    key = job["meeting-key"]
    first = cycle(world, job, H.Summarizer(summary_text(key)))
    assert first["outcome"] == "filed", world.regime

    after_first = filed_files(world)
    head_after_first = H.git(world.checkout, "rev-parse", "HEAD").stdout.strip()

    second_summarizer = H.Summarizer(summary_text(key))
    second = cycle(world, job, second_summarizer)

    assert second["wrote"] == [], f"{world.regime}: the second run wrote {second['wrote']}"
    assert second_summarizer.calls == [], \
        f"{world.regime}: the second run summarized again"
    assert filed_files(world) == after_first, f"{world.regime}: a second file appeared"
    assert len(after_first) == 2, f"{world.regime}: expected summary + 1 transcript, got {after_first}"
    assert H.git(world.checkout, "rev-parse", "HEAD").stdout.strip() == head_after_first, \
        f"{world.regime}: the second run committed"
    assert second["precheck"]["disposition"] == "already-done"


def test_case_a_precheck_precedes_summarize(world):
    """The ordering, shown: the destination is synced and searched BEFORE text is asked for."""
    job = H.job(world.job_names["first"])
    summarizer = H.Summarizer(summary_text(job["meeting-key"]))
    result = cycle(world, job, summarizer)
    trace = result["trace"]
    assert trace.index("sync") < trace.index("precheck") < trace.index("summarize"), \
        f"{world.regime}: ordering was {trace}"
    # and the summarizer was handed a decision that already existed
    assert summarizer.calls[0]["disposition"] == "new", world.regime


def test_case_a_precheck_sees_a_summary_only_the_remote_had(world):
    """The sync is not decoration: a summary filed by someone else is found."""
    job = H.job(world.job_names["first"])
    key = job["meeting-key"]
    first = cycle(world, job, H.Summarizer(summary_text(key)))
    # a second checkout of the same remote, standing for another runner
    other = world.root / "other"
    subprocess.run(["git", "clone", str(world.remotes / f"{world.repo_name}.git"), str(other)],
                   capture_output=True, check=True)
    assert (other / first["destination"]["path"]).exists(), \
        f"{world.regime}: the filed summary never reached the remote"


# --------------------------------------------- case (b) same-day collision
def test_case_b_same_day_collision_concurrently(world):
    """Two meetings, one client, one day — run as two PROCESSES that overlap."""
    arms = [world.job_names["first"], world.job_names["second"]]
    procs = [subprocess.Popen(
        [sys.executable, str(HERE / "concurrent_case.py"), str(world.root), name, "2", f"arm{i}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for i, name in enumerate(arms)]
    outs = [p.communicate() for p in procs]
    for (out, err), proc in zip(outs, procs):
        assert proc.returncode == 0, f"{world.regime}: arm failed: {err}"
    results = [json.loads(out)["result"] for out, _ in outs]
    windows = [(json.loads(out)["started-at"], json.loads(out)["finished-at"]) for out, _ in outs]

    # The overlap is asserted, not assumed: each arm began before the other ended.
    assert windows[0][0] < windows[1][1] and windows[1][0] < windows[0][1], \
        f"{world.regime}: the two arms did not overlap: {windows}"

    paths = [r["destination"]["path"] for r in results]
    assert len(set(paths)) == 2, f"{world.regime}: both meetings resolved to {paths}"
    assert len({r["discriminator"] for r in results}) == 2, \
        f"{world.regime}: the discriminators collided"

    H.git(world.checkout, "fetch", "origin", "main")
    H.git(world.checkout, "merge", "--ff-only", "FETCH_HEAD", check=False)
    for result in results:
        key = result["meeting-key"]
        path = result["destination"]["path"]
        # each file holds ITS OWN meeting's text — an overwrite would show here
        assert f"meeting-key: {key}" in world.remote_text(world.repo_name, path), \
            f"{world.regime}: {path} does not carry {key}"
        # zero overwrites, counted: exactly one commit ever touched each path
        assert len(commits_touching(world, path)) == 1, \
            f"{world.regime}: {path} was written more than once"
        # the discriminator is on the transcripts too, identically
        stem = Path(path).stem
        transcripts = [f for f in filed_files(world) if f"{stem}{P.TRANSCRIPT_INFIX}" in f]
        assert transcripts, f"{world.regime}: no transcript shares the stem of {path}"

    assert len(filed_files(world)) == 4, \
        f"{world.regime}: expected 2 summaries + 2 transcripts, got {filed_files(world)}"


# --------------------------------------------- case (c) late second source
def test_case_c_late_twin_amends_in_place(world):
    job = H.job(world.job_names["first"])
    key = job["meeting-key"]
    first = cycle(world, job, H.Summarizer(summary_text(key, "first wording")))
    path = first["destination"]["path"]
    before = filed_files(world)

    twin = json.loads(json.dumps(job))
    twin["source-set"].append({**job["source-set"][0], "source": "tactiq",
                               "drive-ref": job["source-set"][0]["drive-ref"] + "-tq",
                               "start-time": "2026-03-11T09:18:00-03:00"
                               if world.regime == "vault" else "2026-03-11T10:05:00-03:00"})
    bus = H.Bus()
    amended = cycle(world, twin, H.Summarizer(summary_text(key, "second wording")),
                    bus=bus, transcripts=("meet", "tactiq"))

    assert amended["outcome"] == "amended", world.regime
    assert amended["destination"]["path"] == path, \
        f"{world.regime}: the amendment moved the file to {amended['destination']['path']}"
    assert "second wording" in (world.checkout / path).read_text(encoding="utf-8"), \
        f"{world.regime}: the file was not rewritten"
    summaries = [f for f in filed_files(world) if P.TRANSCRIPT_INFIX not in f]
    assert summaries == [f for f in before if P.TRANSCRIPT_INFIX not in f], \
        f"{world.regime}: a second summary file appeared: {summaries}"
    assert len(bus.of_kind("amendment")) == 1, \
        f"{world.regime}: expected one amendment one-liner, got {bus.posted}"


def test_case_c_amend_refuses_a_non_matching_key(world):
    """The amendment is keyed on the meeting key: another meeting's file is refused."""
    job = H.job(world.job_names["first"])
    other = H.job(world.job_names["second"])
    first = cycle(world, job, H.Summarizer(summary_text(job["meeting-key"])))
    path = first["destination"]["path"]

    with pytest.raises(P.Refused) as raised:
        P.amend_target(world.state, other["meeting-key"], world.repo_name, path)
    assert job["meeting-key"] in str(raised.value), world.regime
    # and the file is untouched
    assert f"meeting-key: {job['meeting-key']}" in (world.checkout / path).read_text(encoding="utf-8")


# --------------------------------------------- case (d) unreachable remote
def test_case_d_unreachable_remote_notes_the_cause_and_keeps_the_job(world):
    job = H.job(world.job_names["first"])
    key = job["meeting-key"]
    world.unreachable(world.repo_name)
    bus = H.Bus()
    result = cycle(world, job, H.Summarizer(summary_text(key)), bus=bus)

    assert result["outcome"] == "failed", world.regime
    assert result["retryable"] is True, world.regime
    notes = bus.of_kind("failure-event")
    assert len(notes) == 1, f"{world.regime}: expected one failure note, got {bus.posted}"
    assert notes[0]["cause"], f"{world.regime}: the note names no cause"
    assert "no-such-remote" in notes[0]["cause"] or "not a git repository" in notes[0]["cause"].lower(), \
        f"{world.regime}: the cause does not name what failed: {notes[0]['cause']}"
    # the job is retried, not lost: it is still in the journal, and unprocessed
    assert P.reached(world.state, key) == "committed", world.regime
    assert P.processed_for(world.state, key) == [], \
        f"{world.regime}: a fully-processed record was written for a job that never published"

    # and it completes once the remote comes back
    H.git(world.checkout, "remote", "set-url", "origin",
          str(world.remotes / f"{world.repo_name}.git"))
    again = cycle(world, job, H.Summarizer(summary_text(key)))
    assert again["outcome"] in ("filed", "amended"), world.regime
    assert again["published"]["pushed"] is True, world.regime


# ------------------------------- case (e) the owner's edit is never clobbered
OWNER_LINE = "Esta linha foi escrita pelo dono, a mao, entre o pull e o push.\n"


def test_case_e_owner_line_survives(world, request):
    """The owner commits to the remote BETWEEN this cycle's pull and its push."""
    job = H.job(world.job_names["first"])
    key = job["meeting-key"]
    owner_file = "OWNER-NOTES.md"

    real_commit = P.commit

    def commit_then_owner_writes(target, checkout, paths, message):
        done = real_commit(target, checkout, paths, message)
        # the owner's own commit lands on the remote now — after our pull, before our push
        world.owner_commits(world.repo_name, owner_file, OWNER_LINE)
        return done

    P.commit = commit_then_owner_writes
    try:
        result = cycle(world, job, H.Summarizer(summary_text(key)))
    finally:
        P.commit = real_commit

    assert result["outcome"] == "filed", f"{world.regime}: {result.get('cause')}"
    # The race actually happened: in regime git the first push WAS rejected.
    # Without this the case could pass having never reached the code that keeps
    # the owner's line. A vault never pushes directly (its HEAD carries peers'
    # unpushed commits): it always fetches and publishes from a worktree based on
    # the remote, so the owner's line is kept by construction — asserted below.
    if world.regime == "git":
        assert result["published"]["trail"], \
            f"{world.regime}: the push was never rejected — this case proved nothing"
        assert "rejected" in result["published"]["trail"][0]["error"], world.regime

    # THE criterion, asserted positively and FIRST: the owner's own text is there.
    landed = world.remote_text(world.repo_name, owner_file)
    assert OWNER_LINE.strip() in landed, \
        f"{world.regime}: the owner's own line is GONE from the remote. Remote holds: {landed!r}"

    if world.regime == "vault":
        assert result["published"]["via"] == "worktree", \
            "the shared tree was published from itself instead of from a worktree outside it"
        assert not H.git(world.checkout, "log", "--merges", "--format=%H").stdout.strip(), \
            "the shared working tree was merged into"
    else:
        assert result["published"]["attempts"] >= 2, world.regime
    # and our own artifact is there too — the integration kept both sides
    assert world.remote_text(world.repo_name, result["destination"]["path"]), \
        f"{world.regime}: our summary never reached the remote"


# --------------------------------------------- case (f) partial-filing recovery
def test_case_f_killed_cycle_resumes_and_flag_is_written_last(world):
    job_name = world.job_names["first"]
    job = H.job(job_name)
    key = job["meeting-key"]

    killed = subprocess.run([sys.executable, str(HERE / "kill_case.py"), str(world.root), job_name],
                            capture_output=True, text=True)
    # POSIX reports death by signal as -9; Windows TerminateProcess exits with the signal number.
    expected = -9 if hasattr(signal, "SIGKILL") else signal.SIGTERM
    assert killed.returncode == expected, f"{world.regime}: the victim was not killed: {killed.returncode}"

    # the killed run wrote NO fully-processed record
    assert P.processed_for(world.state, key) == [], \
        f"{world.regime}: 'fully processed' was written by a run that never pushed"
    assert P.reached(world.state, key) == "committed", \
        f"{world.regime}: the journal says {P.reached(world.state, key)}"
    assert world.remote_text(world.repo_name,
                             "notes" if world.regime == "git" else "areas") == ""

    resumed = cycle(world, job, H.Summarizer(summary_text(key)))
    assert resumed["outcome"] in ("filed", "amended"), world.regime
    assert resumed["published"]["pushed"] is True, world.regime
    assert "resume-skip-summarize" in resumed["trace"], \
        f"{world.regime}: the resumed run re-summarized: {resumed['trace']}"
    assert world.remote_text(world.repo_name, resumed["destination"]["path"]), \
        f"{world.regime}: the resumed run did not complete the push"

    # the ordering of the flag: processed is the LAST stage, after noted
    stages = [row["stage"] for row in P.journal_rows(world.state, key)]
    assert stages[-1] == "processed", f"{world.regime}: stages ended {stages}"
    for earlier in ("written", "committed", "published", "noted"):
        assert stages.index(earlier) < stages.index("processed"), \
            f"{world.regime}: '{earlier}' was not reached before 'processed': {stages}"
    assert P.processed_for(world.state, key), world.regime


# --------------------------------------------- the standing criteria
def test_transcripts_are_filed_beside_the_summary_sharing_its_stem(world):
    job = H.job(world.job_names["first"])
    result = cycle(world, job, H.Summarizer(summary_text(job["meeting-key"])),
                   transcripts=("meet", "tactiq"))
    summary = Path(result["destination"]["path"])
    filed = result["wrote"]
    assert len(filed) == 3, f"{world.regime}: {filed}"
    for source in ("meet", "tactiq"):
        expected = (summary.parent / f"{summary.stem}{P.TRANSCRIPT_INFIX}{source}{summary.suffix}")
        assert expected.as_posix() in filed, f"{world.regime}: {source} not filed beside the summary"
        assert (world.checkout / expected).exists(), world.regime
    assert result["discriminator"] in summary.stem, world.regime


def test_every_outcome_comes_from_the_enum(world):
    job = H.job(world.job_names["first"])
    seen = {cycle(world, job, H.Summarizer(summary_text(job["meeting-key"])))["outcome"]}
    world.unreachable(world.repo_name)
    other = H.job(world.job_names["second"])
    seen.add(cycle(world, other, H.Summarizer(summary_text(other["meeting-key"])))["outcome"])
    assert seen <= set(P.OUTCOMES), f"{world.regime}: {seen - set(P.OUTCOMES)}"


def test_nothing_was_force_pushed_and_no_history_rewritten(world):
    """Criterion 12, as a property of the layer's own vocabulary and its reflog."""
    # Read off the layer's own git call sites rather than off a substring scan:
    # `worktree remove --force` is a scratch-worktree teardown and has nothing to
    # do with a force PUSH, and a check that cannot tell them apart is a check
    # that will be silenced the first time it cries wolf.
    calls = git_call_sites(HERE.parent.parent / "tools" / "publish_job.py")
    assert calls, "no git call sites were found — this check would pass vacuously"
    forbidden_verbs = {"rebase", "reset", "clean", "stash", "filter-branch", "checkout"}
    for args in calls:
        verb = args[0] if args else ""
        assert verb not in forbidden_verbs, f"the layer runs `git {' '.join(args)}`"
        if verb == "push":
            assert not {"-f", "--force", "--force-with-lease", "--mirror"} & set(args), \
                f"the layer force-pushes: `git {' '.join(args)}`"

    job = H.job(world.job_names["first"])
    cycle(world, job, H.Summarizer(summary_text(job["meeting-key"])))
    world.owner_commits(world.repo_name, "OWNER-NOTES.md", OWNER_LINE)
    other = H.job(world.job_names["second"])
    result = cycle(world, other, H.Summarizer(summary_text(other["meeting-key"])))
    assert result["outcome"] == "filed", f"{world.regime}: {result.get('cause')}"
    assert OWNER_LINE.strip() in world.remote_text(world.repo_name, "OWNER-NOTES.md"), world.regime
    reflog = H.git(world.checkout, "reflog", "--date=iso").stdout
    assert "reset" not in reflog.lower(), f"{world.regime}: a reset appears in the reflog:\n{reflog}"


def test_a_peers_uncommitted_work_in_the_tree_survives_a_cycle(world):
    """Nothing this layer does sweeps a working tree it shares with someone else."""
    canary = world.checkout / "PEER-WORK-IN-PROGRESS.md"
    text = "Trabalho nao commitado de outra sessao. Nao pode sumir.\n"
    canary.write_text(text, encoding="utf-8")

    job = H.job(world.job_names["first"])
    cycle(world, job, H.Summarizer(summary_text(job["meeting-key"])))
    world.owner_commits(world.repo_name, "OWNER-NOTES.md", OWNER_LINE)
    other = H.job(world.job_names["second"])
    result = cycle(world, other, H.Summarizer(summary_text(other["meeting-key"])))

    assert result["outcome"] == "filed", f"{world.regime}: {result.get('cause')}"
    assert canary.exists(), f"{world.regime}: the peer's uncommitted file was deleted"
    assert canary.read_text(encoding="utf-8") == text, \
        f"{world.regime}: the peer's uncommitted file was rewritten"
    # and it was not swept into this layer's commits either
    tracked = H.git(world.checkout, "ls-files", "--", canary.name).stdout.strip()
    assert tracked == "", f"{world.regime}: the peer's file was committed by this layer"


def test_the_summarizers_recorded_propagation_rides_in_the_commit_and_a_peers_does_not(world):
    """Owner ruling r-tecer-propagation-committed (2026-09-27): the paths a summarize
    sitting changed (CRM records, the meeting index) are committed WITH the summary,
    and nothing else in the tree is."""
    job = H.job(world.job_names["first"])
    key = job["meeting-key"]
    propagated = world.checkout / "crm" / "EXAMPLE-client.md"
    propagated.parent.mkdir(parents=True, exist_ok=True)
    propagated.write_text("- met on the meeting's day\n", encoding="utf-8")
    peer = world.checkout / "PEER-WORK-IN-PROGRESS.md"
    peer.write_text("not this meeting's\n", encoding="utf-8")
    record = world.state / "runs" / key / P.PROPAGATED_FILE
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"paths": ["crm/EXAMPLE-client.md"]}), encoding="utf-8")

    result = cycle(world, job, H.Summarizer(summary_text(key)))

    assert result["outcome"] == "filed", f"{world.regime}: {result.get('cause')}"
    assert "crm/EXAMPLE-client.md" in result["wrote"]
    tracked = H.git(world.checkout, "ls-files", "--", "crm/EXAMPLE-client.md",
                    peer.name).stdout.split()
    assert tracked == ["crm/EXAMPLE-client.md"], f"{world.regime}: {tracked}"


def test_the_discriminator_is_never_applied_twice():
    targets = {"discriminator": {"format": "%H%M", "insert-before": "-resumo"}}
    once = P.discriminate("a/2026-09-27-x-resumo.md", "0954", targets)
    assert once == "a/2026-09-27-x-0954-resumo.md"
    assert P.discriminate(once, "0954", targets) == once
    appended = P.discriminate("a/x-summary.md", "0954", targets)
    assert appended == "a/x-summary-0954.md"
    assert P.discriminate(appended, "0954", targets) == appended


def test_a_vault_publishes_only_its_own_commit_never_a_peers_unpushed_one(world):
    """Found 2026-09-27: `remote..HEAD` in the shared vault held two sessions'
    unpushed commits, and the worktree push would have published them too."""
    if world.regime != "vault":
        pytest.skip("only a shared vault carries other sessions' unpushed commits")
    peer = world.checkout / "PEER-UNPUSHED.md"
    peer.write_text("a peer's commit, not yet theirs to publish\n", encoding="utf-8")
    H.git(world.checkout, "add", "--", peer.name)
    H.git(world.checkout, "commit", "-m", "peer: unpushed work", "--", peer.name)

    job = H.job(world.job_names["first"])
    result = cycle(world, job, H.Summarizer(summary_text(job["meeting-key"])))

    assert result["outcome"] == "filed", result.get("cause")
    assert world.remote_text(world.repo_name, result["destination"]["path"])
    assert not world.remote_text(world.repo_name, peer.name), \
        "the peer's unpushed commit was published by this cycle"
