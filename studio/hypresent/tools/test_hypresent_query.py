import importlib.util
import json
from pathlib import Path

from bs4 import BeautifulSoup

TOOLS_DIR = Path(__file__).parent
FIXTURES_DIR = TOOLS_DIR / "fixtures"


def load_hypresent():
    spec = importlib.util.spec_from_file_location("hypresent", TOOLS_DIR / "hypresent.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture_path(name):
    return FIXTURES_DIR / name


def fixture_text(name):
    return fixture_path(name).read_text(encoding="utf-8")


def json_stdout(capsys):
    return json.loads(capsys.readouterr().out)


def test_read_comment_self_resolves_every_thread_id_that_has_a_matching_cid(capsys):
    hypresent = load_hypresent()
    soup = BeautifulSoup(fixture_text("query-nested.html"), "lxml")
    ids = {
        token
        for element in soup.select("[data-hyp-cid]")
        for token in element["data-hyp-cid"].split()
    }
    for cid in ids:
        code = hypresent.main(
            ["read", "--file", str(fixture_path("query-nested.html")), "--comment", cid, "--self", "--json"]
        )
        assert code == 0
        payload = json_stdout(capsys)
        assert payload["kind"] == "element"
        assert payload["comment_id"] == cid
        assert payload["matches"]
        for match in payload["matches"]:
            assert cid in match["attrs"]["data-hyp-cid"].split()
            assert match["html"]


def test_read_parent_and_siblings_return_adjacent_nested_context(capsys):
    hypresent = load_hypresent()
    path = str(fixture_path("query-nested.html"))

    assert hypresent.main(["read", "--file", path, "--comment", "c-nested", "--parent", "--json"]) == 0
    parent = json_stdout(capsys)
    assert parent["matches"][0]["attrs"]["id"] == "card-a"
    assert "Alpha target phrase lives here." in parent["matches"][0]["html"]

    assert hypresent.main(["read", "--file", path, "--comment", "c-nested", "--sibling", "--json"]) == 0
    siblings = json_stdout(capsys)
    sibling_ids = {match["attrs"]["id"] for match in siblings["matches"]}
    assert {"inner-before", "inner-after"} <= sibling_ids


def test_read_combined_relation_flags_return_union_of_contexts_in_one_call(capsys):
    hypresent = load_hypresent()
    path = str(fixture_path("query-nested.html"))

    code = hypresent.main(
        ["read", "--file", path, "--comment", "c-nested", "--self", "--parent", "--sibling", "--json"]
    )
    assert code == 0
    payload = json_stdout(capsys)
    assert payload["kind"] == "element-set"
    assert payload["comment_id"] == "c-nested"
    assert payload["relations"] == ["self", "parent", "sibling"]
    contexts = {context["relation"]: context for context in payload["contexts"]}
    assert set(contexts) == {"self", "parent", "sibling"}
    assert "c-nested" in contexts["self"]["matches"][0]["attrs"]["data-hyp-cid"].split()
    assert contexts["parent"]["matches"][0]["attrs"]["id"] == "card-a"
    sibling_ids = {match["attrs"]["id"] for match in contexts["sibling"]["matches"]}
    assert {"inner-before", "inner-after"} <= sibling_ids

    # Human rendering of the combined payload labels each relation block.
    assert hypresent.main(["read", "--file", path, "--comment", "c-nested", "--self", "--parent"]) == 0
    human = capsys.readouterr().out
    assert "element: ok c-nested [self]" in human
    assert "element: ok c-nested [parent]" in human


def test_read_unanchored_thread_reports_explicitly_and_exits_zero(capsys):
    hypresent = load_hypresent()
    code = hypresent.main(
        [
            "read",
            "--file",
            str(fixture_path("query-nested.html")),
            "--comment",
            "c-missing",
            "--self",
            "--json",
        ]
    )
    assert code == 0
    payload = json_stdout(capsys)
    assert payload["status"] == "unanchored"
    assert payload["matches"] == []


def test_read_duplicate_cid_reports_all_matches_and_flags_anomaly(capsys):
    hypresent = load_hypresent()
    code = hypresent.main(
        [
            "read",
            "--file",
            str(fixture_path("query-nested.html")),
            "--comment",
            "c-multi",
            "--self",
            "--json",
        ]
    )
    assert code == 0
    payload = json_stdout(capsys)
    assert payload["anomaly"] == "multiple-elements"
    assert {match["attrs"]["id"] for match in payload["matches"]} == {"multi-one", "multi-two"}


def test_read_missing_comment_lists_available_ids(capsys):
    hypresent = load_hypresent()
    code = hypresent.main(
        ["read", "--file", str(fixture_path("query-nested.html")), "--comment", "absent"]
    )
    assert code != 0
    assert "available ids: c-nested, c-resolved, c-multi, c-missing" in capsys.readouterr().err


def test_selector_read_match_zero_match_and_invalid_selector(capsys):
    hypresent = load_hypresent()
    path = str(fixture_path("query-nested.html"))

    assert hypresent.main(["read", "--file", path, "--selector", "#selector-only", "--json"]) == 0
    match = json_stdout(capsys)
    assert match["kind"] == "selector"
    assert match["matches"][0]["attrs"]["id"] == "selector-only"

    assert hypresent.main(["read", "--file", path, "--selector", ".does-not-exist", "--json"]) == 0
    empty = json_stdout(capsys)
    assert empty["status"] == "empty"
    assert empty["matches"] == []

    assert hypresent.main(["read", "--file", path, "--selector", "[", "--json"]) != 0
    assert "invalid selector" in capsys.readouterr().err


def test_read_modes_and_thread_filters(capsys):
    hypresent = load_hypresent()
    path = str(fixture_path("query-nested.html"))

    assert hypresent.main(["read", "--file", path, "--mode", "comments", "--state", "open", "--json"]) == 0
    comments = json_stdout(capsys)
    assert comments["kind"] == "comments"
    assert [thread["id"] for thread in comments["threads"]] == ["c-nested", "c-multi", "c-missing"]

    assert hypresent.main(["read", "--file", path, "--mode", "comments", "--agent", "with", "--json"]) == 0
    agent = json_stdout(capsys)
    assert [thread["id"] for thread in agent["threads"]] == ["c-nested"]

    assert hypresent.main(["read", "--file", path, "--mode", "corpus", "--json"]) == 0
    corpus = json_stdout(capsys)
    assert corpus["kind"] == "corpus"
    assert "Alpha target phrase lives here." in corpus["text"]
    assert "hyp-comments" not in corpus["text"]

    assert hypresent.main(["read", "--file", path, "--mode", "doc", "--json"]) == 0
    doc = json_stdout(capsys)
    assert doc["kind"] == "doc"
    assert len(doc["threads"]) == 4
    assert "Needle appears once." in doc["corpus"]["text"]


def test_read_comments_reports_zero_threads_when_island_missing(capsys):
    hypresent = load_hypresent()
    assert (
        hypresent.main(["read", "--file", str(fixture_path("no-island.html")), "--mode", "comments", "--json"])
        == 0
    )
    payload = json_stdout(capsys)
    assert payload["count"] == 0
    assert payload["threads"] == []


def test_search_finds_case_insensitive_hits_with_location_context(capsys):
    hypresent = load_hypresent()
    code = hypresent.main(
        ["search", "--file", str(fixture_path("query-nested.html")), "--query", "needle", "--json"]
    )
    assert code == 0
    payload = json_stdout(capsys)
    assert payload["query"] == "needle"
    assert payload["case_sensitive"] is False
    assert payload["count"] == 3
    assert all(hit["snippet"] for hit in payload["hits"])
    assert all(hit["line"] for hit in payload["hits"])
    assert all(hit["location"]["nearest_id"] for hit in payload["hits"])
    assert all(hit["location"]["class_chain"] for hit in payload["hits"])


def test_search_zero_hits_exits_zero_with_explicit_empty_result(capsys):
    hypresent = load_hypresent()
    code = hypresent.main(
        ["search", "--file", str(fixture_path("query-nested.html")), "--query", "not-present", "--json"]
    )
    assert code == 0
    payload = json_stdout(capsys)
    assert payload["status"] == "empty"
    assert payload["hits"] == []


def test_search_and_read_path_does_not_import_browser_or_server_machinery():
    source = (TOOLS_DIR / "deck_query.py").read_text(encoding="utf-8")
    banned = ("playwright", "selenium", "subprocess", "http.server", "socketserver")
    assert all(term not in source for term in banned)


def test_read_comment_thread_returns_full_content_and_every_island_field(capsys):
    hypresent = load_hypresent()
    path = str(fixture_path("query-nested.html"))
    assert hypresent.main(["read", "--file", path, "--comment", "c-nested", "--json"]) == 0
    payload = json_stdout(capsys)
    assert payload["kind"] == "comment"
    thread = payload["thread"]
    for field in (
        "id",
        "anchor",
        "contextText",
        "author",
        "createdAt",
        "editedAt",
        "body",
        "resolved",
        "replies",
        "agentInstruction",
    ):
        assert field in thread, f"island field dropped: {field}"
    assert thread["id"] == "c-nested"
    assert thread["agentInstruction"] == "Follow up."
    assert thread["anchor"]["nativeId"] == "deck-root"
    reply = thread["replies"][0]
    assert reply["author"] == "Agent"
    assert reply["body"] == "Working on it."
    assert reply["createdAt"] == "2026-07-06T10:05:00Z"


def test_search_hit_in_commented_subtree_carries_suggested_selector(capsys):
    hypresent = load_hypresent()
    code = hypresent.main(
        ["search", "--file", str(fixture_path("query-nested.html")), "--query", "alpha", "--json"]
    )
    assert code == 0
    payload = json_stdout(capsys)
    # 'alpha' occurs only inside commented <p> elements (c-nested + c-multi x2).
    assert payload["count"] == 3
    assert all(hit["location"]["suggested_selector"] for hit in payload["hits"])


def test_search_and_corpus_work_on_deck_with_no_island(capsys):
    hypresent = load_hypresent()
    no_island = str(fixture_path("no-island.html"))

    assert hypresent.main(["read", "--file", no_island, "--mode", "corpus", "--json"]) == 0
    corpus = json_stdout(capsys)
    assert corpus["kind"] == "corpus"
    assert "No island" in corpus["text"]

    assert hypresent.main(["search", "--file", no_island, "--query", "island", "--json"]) == 0
    search = json_stdout(capsys)
    assert search["count"] == 1
