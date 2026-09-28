"""Routing cases for the destination resolver.

Every case here is driven RED alone before it is trusted green — a case that has
only ever been observed green proves the assertion was reachable, not that the
code is right. The driver that does it lives with the build record, not in the
product tree; this file is what it runs.

No owner destination name and no owner path segment appears in this file or in
the fixture tree beside it. The entities are invented. That is not tidiness: the
milestone's central check is a grep over this whole tree for the owner's
destination surface, and a fixture carrying a real destination name would defeat
the only check that can falsify "no routing map is hardcoded".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

import destination_resolver as dr  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONFIG = FIXTURES / "config"
JOBS = FIXTURES / "jobs"
DEST = FIXTURES / "dest"


def job(name: str) -> dict:
    return json.loads((JOBS / f"{name}.json").read_text(encoding="utf-8"))


def resolve(name: str) -> dict:
    return dr.resolve(job(name), override=CONFIG)


def write_routing(tmp_path: Path, routes: list, timezone: str = "America/Sao_Paulo") -> Path:
    """A throwaway config-module home carrying a hand-built route table."""
    (tmp_path / "destination-repos.json").write_text(
        (CONFIG / "destination-repos.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "destination-routing.json").write_text(
        json.dumps({"config-key": "destination-routing", "timezone": timezone, "routes": routes}),
        encoding="utf-8",
    )
    return tmp_path


# --------------------------------------------------------- the four fixtures
def test_entity_a_resolves():
    answer = resolve("a-business")
    assert answer["kind"] == "routed"
    assert answer["entity"] == "alpha"
    assert answer["destination"]["repo"] == "alpha-works"
    assert answer["destination"]["path"] == "notes/meetings/2026/2026-03-11-alpha-sync-resumo.md"


def test_clinical_resolves():
    answer = resolve("clinical")
    assert answer["kind"] == "routed"
    assert answer["entity"] == "clinic-a"
    assert answer["destination"]["repo"] == "wellbeing-vault"
    assert answer["destination"]["path"] == "areas/wellbeing/2026/encontros/2026-03-12-sessao-resumo.md"


def test_entity_b_resolves_without_a_code_change():
    """Entity B is in the declared source and nowhere in the code."""
    answer = resolve("b-business")
    assert answer["kind"] == "routed"
    assert answer["entity"] == "beta"
    assert answer["destination"]["repo"] == "beta-labs"
    assert answer["destination"]["path"] == "docs/encontros/2026/2026-05-20-beta-review-resumo.md"
    source = (TOOLS / "destination_resolver.py").read_text(encoding="utf-8")
    assert "beta" not in source.lower().replace("beta-", "")  # no entity name in the mechanism


def test_unroutable_returns_the_typed_value():
    answer = resolve("unroutable")
    assert answer["kind"] == "unroutable"
    assert "destination" not in answer
    assert answer["meeting-key"] == "mtg-fixture-u1"


def test_unroutable_is_not_an_exception_a_caller_can_swallow():
    """Clause 7: a caller must not be able to turn no-route into a default by
    catching something. `resolve` RETURNS the unroutable record."""
    answer = dr.resolve(job("unroutable"), override=CONFIG)
    assert isinstance(answer, dict) and answer["kind"] == "unroutable"


def test_the_cli_exits_zero_on_unroutable_and_prints_the_typed_value(capsys):
    """An unroutable meeting is an ANSWER, so the process succeeds. A non-zero
    exit would read to a caller as a failure to answer."""
    code = dr.main(["--config-root", str(CONFIG), "resolve", "--job", str(JOBS / "unroutable.json")])
    assert code == dr.EXIT_OK
    assert json.loads(capsys.readouterr().out)["kind"] == "unroutable"


# --------------------------------------------------------- delegated placement
def test_a_route_without_a_template_delegates_placement_and_invents_no_path():
    """Owner ruling: a route carries a REPO; where the file lands inside it is the
    destination repo's own rule. The resolver must answer with the repo and NO
    path rather than inventing one."""
    answer = resolve("delegated")
    assert answer["kind"] == "routed"
    assert answer["destination"]["repo"] == "gamma-corp"
    assert answer["destination"]["placement"] == "delegated"
    assert "path" not in answer["destination"]


# --------------------------------------------------------- clause 7 at load
def test_a_catch_all_route_is_refused_at_load(tmp_path):
    home = write_routing(tmp_path, [{"entity": "any", "match": {}, "destination": {"repo": "alpha-works"}}])
    with pytest.raises(dr.Refused):
        dr.load_routing(home)


def test_a_route_naming_an_undeclared_repo_is_refused(tmp_path):
    home = write_routing(
        tmp_path,
        [{"entity": "x", "match": {"title-matches": ["x"]}, "destination": {"repo": "not-declared"}}],
    )
    with pytest.raises(dr.Refused):
        dr.load_routing(home)


def test_a_route_shadowed_by_an_earlier_broader_route_is_refused(tmp_path):
    """Routes are first-match-wins. A broad route above a narrow one silently
    swallows it, and the narrow routes are the ones carrying clinical traffic."""
    home = write_routing(
        tmp_path,
        [
            {"entity": "broad", "match": {"title-matches": ["sessao"]},
             "destination": {"repo": "wellbeing-vault"}},
            {"entity": "narrow", "match": {"title-matches": ["sessao"],
                                           "participants-any": ["Dora Marques"]},
             "destination": {"repo": "wellbeing-vault"}},
        ],
    )
    with pytest.raises(dr.Refused):
        dr.load_routing(home)


def test_the_shipped_table_loads_so_the_shadow_guard_is_not_refusing_everything():
    """The mirror of the case above. Without it, the shadow guard could pass by
    refusing every table, including correct ones. The two clinic routes are the
    pair that exercises it: same predicate kinds, disjoint values, so neither
    shadows the other and both must survive the load."""
    routing = dr.load_routing(CONFIG)
    assert [route["entity"] for route in routing["routes"]][:2] == ["clinic-a", "clinic-b"]
    assert not dr._shadows(routing["routes"][0]["match"], routing["routes"][1]["match"])


# ------------------------------------- the clinical fallthrough (owner ruling)
# r-owner-ruling-batch-0926 item 3: the catch-all route on the owner's own
# account is GONE. A meeting on that account matching neither clinician is no
# longer filed as an ordinary non-clinical meeting — it resolves to the typed
# `unroutable` value, which is what makes the summarize job ask the owner. The
# word this comment avoids is one of the owner path segments the milestone's
# standing grep over this tree forbids; it is not a style rule.


def test_an_own_account_meeting_matching_neither_clinician_is_unroutable():
    """RED arm: with the catch-all route in the table this resolved to
    `{"kind": "routed", "entity": "own-other"}` and the summary was filed with
    no owner involvement."""
    answer = resolve("own-other")
    assert answer["kind"] == "unroutable"
    assert "destination" not in answer
    assert "entity" not in answer
    # the ask carries the signals the owner needs to answer with a destination
    assert answer["signals"]["title"] == "Conversa com amigo"
    assert answer["signals"]["participants"]


def test_the_clinician_routes_still_file_without_asking():
    """The discriminating half: removing the catch-all must not have made the
    clinical meetings ask too."""
    answer = resolve("clinical")
    assert answer["kind"] == "routed"
    assert answer["entity"] in ("clinic-a", "clinic-b")
    assert answer["destination"]["path"]


def test_there_is_no_account_predicate_at_all():
    """Owner ruling r-route-by-content-not-account (2026-09-27): clinical, business and
    personal meetings share one account, so a route keyed on it is refused at load."""
    assert "account-any" not in dr.PREDICATE_KINDS
    for route in dr.load_routing(CONFIG)["routes"]:
        assert "account-any" not in route["match"], route["entity"]


# --------------------------------------------------------- the config binding
def test_the_source_location_is_bound_to_a_config_key():
    """The declared source's location is COMPUTED from its key, never typed."""
    assert dr.config_path(dr.ROUTING_KEY, CONFIG) == CONFIG / "destination-routing.json"
    assert dr.config_path(dr.REPOS_KEY, CONFIG) == CONFIG / "destination-repos.json"


def test_a_missing_declared_source_refuses_rather_than_defaulting(tmp_path):
    with pytest.raises(dr.Refused):
        dr.load_routing(tmp_path)


def test_a_declared_source_without_a_timezone_refuses(tmp_path):
    """Owner ruling 2026-08-28 lives in configuration with NO default: a missing
    timezone must not pass as correct."""
    home = write_routing(tmp_path, [], timezone="")
    with pytest.raises(dr.Refused):
        dr.load_routing(home)


# --------------------------------------------------------- the date rulings
def test_dates_are_computed_in_the_declared_timezone():
    answer = resolve("a-business")
    assert "/2026-03-11-" in answer["destination"]["path"]


def test_the_year_slot_crosses_at_local_midnight_not_utc():
    """01:30 UTC on 1 Jan 2026 is still 2025-12-31 locally."""
    answer = resolve("midnight")
    assert answer["destination"]["path"] == "notes/meetings/2025/2025-12-31-alpha-sync-resumo.md"


def test_the_meeting_start_is_the_earliest_of_its_paired_sources():
    signals = dr.meeting_signals(job("a-business"))
    assert signals["start"].isoformat() == "2026-03-11T10:02:00-03:00"


# --------------------------------------------------------- the discovery walk
def test_the_walk_finds_a_summary_filed_under_a_non_resumo_name():
    names = {record["path"] for record in dr.walk_summaries(DEST)}
    assert "alpha-works/notes/meetings/2026/reuniao-alpha-11-marco.md" in names


def test_the_walk_does_not_filter_on_the_conventional_suffix():
    records = dr.walk_summaries(DEST)
    assert {record["suffix-conventional"] for record in records} == {True, False}
    assert not any(record["path"].endswith(".txt") for record in records)


# --------------------------------------------------------- participant matching
def test_a_participant_route_matches_a_name_fragment_not_only_the_exact_display_name(tmp_path):
    """The route key is a distinguishing fragment of a person's name, because the
    display name a transcript carries is not stable. Equality would drop the
    match and let the meeting fall through to a broader route."""
    home = write_routing(
        tmp_path,
        [
            {"entity": "by-person", "match": {"participants-any": ["Marques"]},
             "destination": {"repo": "wellbeing-vault"}},
        ],
    )
    variants = ["Dora Marques", "Dora Marques de Souza", "DORA MARQUES", "Dora Marqués"]
    for display in variants:
        meeting = {"meeting-key": "k", "source-set": [
            {"account": "a@b.invalid", "source": "meet", "drive-ref": "d", "title": "t",
             "start-time": "2026-03-12T19:00:00-03:00", "participants": ["Henrique", display]}]}
        assert dr.resolve(meeting, override=home)["kind"] == "routed", display


def test_a_participant_route_does_not_match_an_unrelated_name(tmp_path):
    """The mirror of the case above: the fragment must still discriminate."""
    home = write_routing(
        tmp_path,
        [
            {"entity": "by-person", "match": {"participants-any": ["Marques"]},
             "destination": {"repo": "wellbeing-vault"}},
        ],
    )
    meeting = {"meeting-key": "k", "source-set": [
        {"account": "a@b.invalid", "source": "meet", "drive-ref": "d", "title": "t",
         "start-time": "2026-03-12T19:00:00-03:00", "participants": ["Henrique", "Romeu"]}]}
    assert dr.resolve(meeting, override=home)["kind"] == "unroutable"


# ------------------------------------------------ routing by content, never by account
def _content_table() -> dict:
    """Shaped on the owner's 2026-09-27 table: clinical by participant, the rest by content."""
    from zoneinfo import ZoneInfo
    return {"tzinfo": ZoneInfo("America/Sao_Paulo"), "routes": [
        {"entity": "EXAMPLE-clinic", "match": {"participants-any": ["EXAMPLE-Kal"]},
         "content": "a clinical session", "destination": {"repo": "EXAMPLE-private"}},
        {"entity": "EXAMPLE-biz", "match": {}, "content": "the company's business",
         "destination": {"repo": "EXAMPLE-biz-repo"}},
    ]}


def _meeting(participants: list, content_entity=None) -> dict:
    meeting = {"meeting-key": "mtg-EXAMPLE", "source-set": [{
        "account": "owner@EXAMPLE-biz.test", "source": "tactiq", "drive-ref": "drv:file/x",
        "title": "EXAMPLE call", "start-time": "2026-09-29T10:00:00-03:00",
        "participants": participants}]}
    if content_entity:
        meeting["content-entity"] = content_entity
    return meeting


def test_a_clinicians_name_routes_on_any_account_and_outranks_the_content():
    table = _content_table()
    answer = dr.resolve(_meeting(["EXAMPLE-Kal Silva"], content_entity="EXAMPLE-biz"),
                        routing=table)
    assert answer["entity"] == "EXAMPLE-clinic"


def test_without_a_fact_the_content_pick_routes_and_no_pick_is_asked():
    table = _content_table()
    assert dr.resolve(_meeting(["EXAMPLE-Ana"], content_entity="EXAMPLE-biz"),
                      routing=table)["entity"] == "EXAMPLE-biz"
    # The account alone routes nothing: no pick, no fact -> unroutable, i.e. asked.
    assert dr.resolve(_meeting(["EXAMPLE-Ana"]), routing=table)["kind"] == "unroutable"
    assert [c["entity"] for c in dr.content_routes(routing=table)] == ["EXAMPLE-clinic",
                                                                       "EXAMPLE-biz"]
