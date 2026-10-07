"""An amendment by a later source: a filed summary is written again, whole, at its own path.

The per-meeting-job seam says what an amendment is (`disposition: amend` — "a summary exists and
must be rewritten in place"; `amend.summary` — "never a second file"). Detection emits that job and
publication files it. These cases hold the step between the two: `per_meeting_job.py` handed an
`amend` job for a meeting that is already settled and processed.

No summarizer is invoked. A stand-in writes the summary where the PROMPT says, so a prompt that
stops naming the filed path fails here.

The last case walks the whole path through the tools' real command lines, as the cycle skill gives
them, against a scratch git remote: file from the first source, the second source arrives,
detection asks for an amendment, the per-meeting job writes it, publication pushes it, and
detection then has nothing left to do.

Every value is a fixture's: no owner account, folder, participant or destination appears here.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import detection_cycle                     # noqa: E402
import per_meeting_job                     # noqa: E402
import publish_job                         # noqa: E402
from harness import FIXTURES, materialise  # noqa: E402

SEAMS = HERE.parent.parent / "seams"
KEY = "mtg-m6-a"
FILED = {"repo": "alpha-works", "path": "notes/meetings/2026/2026-03-11-alpha-sync-1002-resumo.md"}
OLD = "# EXAMPLE summary, from the first source alone\n"
FILED_LINE = "A summary of this meeting is ALREADY FILED"


def whole_job() -> dict:
    return json.loads((FIXTURES / "jobs" / "case-a.json").read_text("utf-8"))


class Writer:
    """Stands in for the summarizer turn. It writes the summary where the PROMPT says, so the
    prompt is what these cases test. `elsewhere` makes it disobey, as a model can; `says` is the
    outcome word it reports."""

    def __init__(self, elsewhere: Path | None = None, says: str | None = None):
        self.prompts: list[str] = []
        self.elsewhere = elsewhere
        self.says = says

    def write(self, prompt: str) -> tuple[Path, str]:
        self.prompts.append(prompt)
        said = dict(line.split(": ", 1) for line in prompt.splitlines() if ": " in line)
        if FILED_LINE in said:
            target, outcome = Path(said[FILED_LINE]), "amended"
        else:
            target, outcome = Path(said["Destination folder"]) / said["Summary filename"], "filed"
        target = self.elsewhere or target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# EXAMPLE summary, writing {len(self.prompts)}\n", encoding="utf-8")
        return target, self.says or outcome

    def __call__(self, prompt, cwd, log_dir, timeout):
        target, outcome = self.write(prompt)
        return {"exit": 0, "text": "", "report": {"SUMMARY": str(target), "OUTCOME": outcome}}


def amend_case(tmp_path: Path) -> tuple[dict, dict, Path]:
    """Case a as detection hands it over when its Tactiq transcript arrives after the summary was
    filed from the Meet transcript alone: settled, processed, and now to be amended."""
    case = materialise("case-a", tmp_path)
    job = {**whole_job(), "disposition": "amend",
           "amend": {"summary": dict(FILED), "coverage": ["meet"]}}
    filed = case["checkout"] / FILED["repo"] / FILED["path"]
    filed.parent.mkdir(parents=True, exist_ok=True)
    filed.write_text(OLD, encoding="utf-8")
    case["state"].mkdir(parents=True, exist_ok=True)
    per_meeting_job.append_jsonl(case["state"] / per_meeting_job.OUTCOMES, {
        "kind": "per-meeting-outcome", "meeting-key": KEY, "outcome": "filed",
        "at": "2026-03-11T14:00:00Z", "destination": dict(FILED)})
    record_processed(case["state"], ["meet"])
    return case, job, filed


def record_processed(state: Path, sources: list[str]) -> None:
    """What publication records once a summary covering these sources is filed."""
    for source in sources:
        per_meeting_job.append_jsonl(state / publish_job.PROCESSED, {
            "transcript-ref": f"drv:file/FIXTURE-a-{source}", "account": "work-a@fixture.invalid",
            "source": source, "meeting-key": KEY, "processed-at": "2026-03-11T14:05:00+00:00",
            "summary": dict(FILED), "coverage": sorted(sources)})


def run(case: dict, job: dict, invoke) -> dict:
    return per_meeting_job.run(
        job, artifacts=case["binding"], config_root=case["config"],
        checkout_root=case["checkout"], channel_root=case["channel"], state=case["state"],
        work=case["work"], seams=SEAMS, store=case["channel"] / "stores" / "map.jsonl",
        invoke=invoke)


def settlements(case: dict) -> list[dict]:
    return [row for row in per_meeting_job.read_jsonl(case["state"] / per_meeting_job.OUTCOMES)
            if row["meeting-key"] == KEY]


def summaries_in(repo: Path) -> list[str]:
    return sorted(path.relative_to(repo).as_posix() for path in repo.rglob("*-resumo.md"))


def reroute(case: dict, routes: list[dict]) -> None:
    path = case["config"] / "destination-routing.json"
    routing = json.loads(path.read_text(encoding="utf-8"))
    routing["routes"] = routes
    path.write_text(json.dumps(routing, ensure_ascii=False, indent=2), encoding="utf-8")


# ------------------------------------------------------------- the amendment
def test_an_amendment_is_written_again_whole_at_the_filed_path(tmp_path):
    case, job, filed = amend_case(tmp_path)
    writer = Writer()
    result = run(case, job, writer)

    assert (result["action"], result["outcome"]) == ("summarized", "amended")
    assert result["summary-file"] == str(filed) and result["destination"] == FILED
    assert result["awaiting-publication"] is True
    assert len(writer.prompts) == 1
    prompt = writer.prompts[0]
    assert f"{FILED_LINE}: {filed}" in prompt
    assert "replacing its entire text" in prompt and "Never a second file" in prompt
    # The filed path is the destination: no placement line competes with it.
    assert "Destination folder" not in prompt and "Summary filename" not in prompt
    assert filed.read_text(encoding="utf-8") != OLD
    assert summaries_in(case["checkout"] / FILED["repo"]) == [FILED["path"]]
    assert [row["outcome"] for row in settlements(case)] == ["filed", "amended"]
    assert settlements(case)[-1]["destination"] == FILED


def test_an_amendment_is_settled_as_amended_whatever_word_the_summarizer_reports(tmp_path):
    case, job, _filed = amend_case(tmp_path)
    result = run(case, job, Writer(says="filed"))
    assert result["outcome"] == "amended"
    assert settlements(case)[-1]["outcome"] == "amended"


def test_an_amendment_already_written_waits_for_publication_and_is_not_written_twice(tmp_path):
    """Detection hands the same job over every tick until publication records the coverage."""
    case, job, filed = amend_case(tmp_path)
    writer = Writer()
    run(case, job, writer)
    again = run(case, job, writer)

    assert len(writer.prompts) == 1
    assert (again["action"], again["outcome"]) == ("already-settled", "amended")
    assert again["awaiting-publication"] is True and again["summary-file"] == str(filed)
    assert again["wrote-summary"] is False
    assert [row["outcome"] for row in settlements(case)] == ["filed", "amended"]


def test_a_further_source_after_a_published_amendment_is_amended_again(tmp_path):
    case, job, _filed = amend_case(tmp_path)
    writer = Writer()
    run(case, job, writer)
    record_processed(case["state"], ["meet", "tactiq"])          # the amendment is published
    third = {**job, "amend": {"summary": dict(FILED), "coverage": ["meet", "tactiq"]},
             "source-set": job["source-set"] + [{
                 **job["source-set"][0], "source": "gemini-notes",
                 "drive-ref": "drv:file/FIXTURE-a-gemini"}]}
    result = run(case, third, writer)

    assert len(writer.prompts) == 2
    assert (result["action"], result["outcome"]) == ("summarized", "amended")
    assert [row["outcome"] for row in settlements(case)] == ["filed", "amended", "amended"]


def test_a_settled_meeting_that_is_not_an_amendment_is_left_alone(tmp_path):
    """The guard an amendment passes still holds for every other job."""
    case, job, filed = amend_case(tmp_path)
    writer = Writer()
    result = run(case, {**whole_job(), "disposition": "new"}, writer)

    assert result["action"] == "already-settled" and "awaiting-publication" not in result
    assert writer.prompts == [] and filed.read_text(encoding="utf-8") == OLD
    assert len(settlements(case)) == 1


def test_an_amendment_written_to_another_file_fails_and_is_not_settled(tmp_path):
    case, job, filed = amend_case(tmp_path)
    stray = filed.with_name("2026-03-11-alpha-sync-1002-v2-resumo.md")
    result = run(case, job, Writer(elsewhere=stray))

    assert (result["action"], result["outcome"]) == ("summarize-failed", "failed")
    assert result["messages"] == 1 and "awaiting-publication" not in result
    assert [row["outcome"] for row in settlements(case)] == ["filed"]
    assert not (case["state"] / "runs" / KEY / per_meeting_job.AMENDED_FILE).exists()
    assert filed.read_text(encoding="utf-8") == OLD


def test_an_amendment_keeps_the_route_the_first_filing_settled(tmp_path):
    """A meeting routed by its CONTENT carries no fact a fresh resolve can match: the pick was
    made once. An amendment reuses it, and never asks a model where the meeting belongs again —
    the stand-in fails on any prompt that is not the amendment's own."""
    case, job, filed = amend_case(tmp_path)
    reroute(case, [{"entity": "alpha", "match": {}, "content": "an EXAMPLE content route",
                    "destination": {"repo": "alpha-works"}}])
    per_meeting_job.append_jsonl(case["state"] / per_meeting_job.OUTCOMES, {
        "meeting-key": KEY, "outcome": "filed", "content-entity": "alpha",
        "at": "2026-03-11T14:01:00Z"})
    writer = Writer()
    result = run(case, job, writer)

    assert len(writer.prompts) == 1 and f"{FILED_LINE}: {filed}" in writer.prompts[0]
    assert (result["action"], result["outcome"]) == ("summarized", "amended")
    assert "content-routing" not in result and result["asked"] is False
    assert settlements(case)[-1]["content-entity"] == "alpha"


def test_an_amendment_whose_meeting_now_routes_to_another_repository_is_refused(tmp_path):
    case, job, filed = amend_case(tmp_path)
    reroute(case, [{"entity": "alpha", "match": {"title-matches": ["alpha"]},
                    "destination": {"repo": "beta-labs",
                                    "path-template": "docs/encontros/{year}/{date}-{slug}-resumo.md"},
                    "vars": {"slug": "alpha-sync"}}])
    writer = Writer()
    result = run(case, job, writer)

    assert (result["action"], result["outcome"]) == ("amend-unroutable", "failed")
    assert result["messages"] == 1 and writer.prompts == []
    assert filed.read_text(encoding="utf-8") == OLD and len(settlements(case)) == 1


def test_a_filed_summary_that_was_moved_or_renamed_is_left_alone_and_said_once(tmp_path):
    """A person curating the destination renamed the file after it was filed. Writing to the
    recorded path would leave two summaries of one meeting. By owner ruling the summary is left as
    it is: nothing is started, nothing is written, and the owner is told once."""
    case, job, filed = amend_case(tmp_path)
    renamed = filed.with_name("2026-03-11-alpha-sync-resumo.md")
    filed.rename(renamed)
    writer = Writer()
    first, later = run(case, job, writer), run(case, job, writer)

    assert first["action"] == later["action"] == "left-alone"
    assert first["first-report"] is True and "first-report" not in later
    assert first["destination"] == FILED and "awaiting-publication" not in first
    assert writer.prompts == [] and first["wrote-summary"] is False
    assert summaries_in(case["checkout"] / FILED["repo"]) == [
        "notes/meetings/2026/2026-03-11-alpha-sync-resumo.md"]
    assert renamed.read_text(encoding="utf-8") == OLD and len(settlements(case)) == 1
    # A source that arrives later still is news, and is said once too.
    third = {**job, "source-set": job["source-set"] + [{
        **job["source-set"][0], "source": "gemini-notes", "drive-ref": "drv:file/FIXTURE-a-gemini"}]}
    assert run(case, third, writer)["first-report"] is True
    assert "first-report" not in run(case, third, writer) and writer.prompts == []


def test_an_amend_job_that_names_no_filed_summary_is_refused(tmp_path):
    case, job, _filed = amend_case(tmp_path)
    del job["amend"]
    with pytest.raises(SystemExit) as refused:
        run(case, job, Writer())
    assert refused.value.code == per_meeting_job.EXIT_REFUSED



def test_three_failed_runs_of_the_command_line_park_the_meeting_and_retry_un_parks(
        tmp_path, monkeypatch, capsys):
    """No tick sees a job the agent runs: the command line records its own outcome in
    detection's attempts store. The third consecutive failure parks the meeting and says so in
    that verdict; the owner's `retry --meeting-key` is what un-parks it."""
    case = materialise("case-a", tmp_path)
    # Detection's verbs find the agent's state/ from the agent folder a turn names.
    monkeypatch.setenv(detection_cycle.AGENT_HOME_ENV, str(case["root"]))
    settings = case["config"] / "summarize.json"
    settings.write_text(json.dumps({
        **json.loads(settings.read_text(encoding="utf-8")),
        "invocation": {"harness": "EXAMPLE-harness", "model": "EXAMPLE-model", "effort": 2}}),
        encoding="utf-8")
    monkeypatch.setattr(per_meeting_job, "invoke_agent",
                        lambda prompt, cwd, log_dir, timeout, invocation: {"exit": 1, "text": ""})
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps({**whole_job(), "disposition": "new"}), encoding="utf-8")

    def per_meeting() -> dict:
        code = per_meeting_job.main([
            "--job", str(job_file), "--artifacts", str(case["root"] / "artifacts" / "binding.json"),
            "--config-root", str(case["config"]), "--checkout-root", str(case["checkout"]),
            "--channel", str(case["channel"]), "--state", str(case["state"]),
            "--work", str(case["work"])])
        return {"exit": code, **json.loads(capsys.readouterr().out)}

    def detection(*verb: str) -> dict:
        assert detection_cycle.main([*verb, "--config-dir", str(case["config"])]) == 0
        return json.loads(capsys.readouterr().out)

    runs = [per_meeting() for _ in range(3)]
    assert [run["outcome"] for run in runs] == ["failed"] * 3
    assert ["parked" in run for run in runs] == [False, False, True]
    assert detection("status")["parked"] == [KEY]
    row = detection_cycle.read_attempts(detection_cycle.attempts_store(case["config"]))[KEY]
    assert (row["consecutive-failures"], row["awaiting"]) == (3, "retry")

    assert detection("retry", "--meeting-key", KEY)["parked"] is False
    assert detection("status")["parked"] == []


# ------------------------------------------------- the whole path, command by command
def _publish_harness():
    spec = importlib.util.spec_from_file_location(
        "publish_harness", HERE.parent / "publish" / "harness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_late_source_reaches_the_filed_summary_and_detection_is_then_done(
        tmp_path, monkeypatch, capsys):
    """Every step is the command line the cycle skill gives the agent, in its order."""
    world = _publish_harness().Scratch(tmp_path / "world")
    world.repo("alpha-works")
    case = materialise("case-a", tmp_path / "case")
    # The command line starts its summarizer as the config says; the turn itself is the stand-in.
    settings = case["config"] / "summarize.json"
    settings.write_text(json.dumps({
        **json.loads(settings.read_text(encoding="utf-8")),
        "invocation": {"harness": "EXAMPLE-harness", "model": "EXAMPLE-model", "effort": 2}}),
        encoding="utf-8")
    writer = Writer()

    def turn(prompt, cwd, log_dir, timeout, invocation):
        target, outcome = writer.write(prompt)
        return {"exit": 0, "text": f"SUMMARY: {target}\nOUTCOME: {outcome}\n"}

    monkeypatch.setattr(per_meeting_job, "invoke_agent", turn)
    roots = ["--config-root", str(case["config"]), "--checkout-root", str(world.checkouts),
             "--state", str(world.state)]

    def job_file(job: dict) -> str:
        path = tmp_path / "jobs" / f"{job['disposition']}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(job), encoding="utf-8")
        return str(path)

    def said(code: int) -> dict:
        return {"exit": code, **json.loads(capsys.readouterr().out)}

    def per_meeting(job: dict) -> dict:
        return said(per_meeting_job.main([
            "--job", job_file(job), "--artifacts", str(case["root"] / "artifacts" / "binding.json"),
            *roots, "--channel", str(case["channel"]), "--work", str(case["work"])]))

    def publish(job: dict, summary: str) -> dict:
        check = said(publish_job.main(["precheck", "--job", job_file(job), *roots]))
        cycle = said(publish_job.main(["cycle", "--job", job_file(job), "--summary", summary,
                                       *roots]))
        return {**cycle, "checked-as": check["disposition"]}

    def detect() -> dict:
        return detection_cycle.job_for({"meeting-key": KEY, "source-set": whole_job()["source-set"]},
                                       publish_job.processed_records(world.state))

    # 1 · the meeting is filed from its first source alone, and published
    first = {**whole_job(), "source-set": whole_job()["source-set"][:1], "disposition": "new"}
    filed = per_meeting(first)
    assert (filed["exit"], filed["outcome"]) == (0, "filed")
    assert "awaiting-publication" not in filed
    assert publish(first, filed["summary-file"])["outcome"] == "filed"
    path = filed["destination"]["path"]
    first_text = world.remote_text("alpha-works", path)
    assert first_text.startswith("# EXAMPLE summary, writing 1")

    # 2 · its second source arrives: detection asks for an amendment of that file
    job = detect()
    assert job["disposition"] == "amend"
    assert job["amend"] == {"summary": {"repo": "alpha-works", "path": path}, "coverage": ["meet"]}

    # 3 · the per-meeting job writes the summary again at the same path
    amended = per_meeting(job)
    assert (amended["exit"], amended["action"], amended["outcome"]) == (0, "summarized", "amended")
    assert amended["awaiting-publication"] is True
    assert amended["summary-file"] == filed["summary-file"]

    # ... and the same job, handed over again before publication, starts no second writing
    again = per_meeting(detect())
    assert (again["action"], again["awaiting-publication"]) == ("already-settled", True)
    assert again["summary-file"] == filed["summary-file"] and len(writer.prompts) == 2

    # 4 · publication files it as an amendment: the remote holds the new text, at one path
    published = publish(job, amended["summary-file"])
    assert (published["checked-as"], published["outcome"]) == ("amend", "amended")
    assert world.remote_text("alpha-works", path).startswith("# EXAMPLE summary, writing 2")
    assert summaries_in(world.checkouts / "alpha-works") == [path]

    # 5 · every source is covered: detection has nothing left to do, and neither has the job
    done = detect()
    assert done["disposition"] == "already-done"
    assert per_meeting(done)["action"] == "nothing-to-do" and len(writer.prompts) == 2
