import importlib.util
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TOOLS_DIR = Path(__file__).parent


def load_hypresent():
    spec = importlib.util.spec_from_file_location("hypresent", TOOLS_DIR / "hypresent.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture_text(name):
    return (TOOLS_DIR / "fixtures" / name).read_text(encoding="utf-8")


def source_threads(text):
    soup = BeautifulSoup(text, "lxml")
    tag = soup.find("script", id="hyp-comments")
    if tag is None or not tag.get_text().strip():
        return []
    return json.loads(tag.get_text())


def digest_threads(text):
    soup = BeautifulSoup(text, "lxml")
    hypresent = load_hypresent()
    parsed = hypresent.extract_digest_threads(soup)
    assert parsed is not None
    return parsed


@pytest.mark.parametrize(
    "fixture",
    [
        "basic.html",
        "dense.html",
        "tiny.html",
        "empty-island.html",
        "no-island.html",
        "edge-island.html",
    ],
)
def test_dehydrate_never_grows_for_all_fixtures(fixture):
    hypresent = load_hypresent()
    src = fixture_text(fixture)
    lean, stats = hypresent.dehydrate(src)
    assert len(lean) <= len(src)
    assert len(lean.encode("utf-8")) <= len(src.encode("utf-8"))
    assert stats["lean_chars"] <= stats["src_chars"]
    assert stats["lean_bytes"] <= stats["src_bytes"]


def test_digest_is_lossless_field_by_field_on_dense_fixture():
    hypresent = load_hypresent()
    src = fixture_text("dense.html")
    lean, stats = hypresent.dehydrate(src)
    assert stats["fallback"] is False
    assert digest_threads(lean) == source_threads(src)
    for thread in digest_threads(lean):
        assert set(thread) >= {
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
        }
        assert set(thread["anchor"]) == {
            "hook",
            "path",
            "nativeId",
            "contentHash",
            "siblingIndex",
        }
        for reply in thread["replies"]:
            assert {"author", "body", "createdAt"} <= set(reply)


def test_digest_preserves_types_nulls_and_absent_keys_on_edge_fixture():
    # Guards the exact real-deck round-trip failure modes: a boolean
    # agentInstruction (must NOT become the string "False"), a null anchor
    # field, an absent editedAt key, an explicit null editedAt, a non-dict
    # (null) anchor, a non-standard anchor key, a typed reply extra field, and
    # an integer thread extra key. dense.html carries volume; this carries the
    # tricky JSON shapes without any vault path.
    hypresent = load_hypresent()
    src = fixture_text("edge-island.html")
    lean, stats = hypresent.dehydrate(src)
    assert stats["fallback"] is False
    src_threads = source_threads(src)
    dug = digest_threads(lean)
    assert dug == src_threads  # exact content identity, field by field

    by_id = {t["id"]: t for t in dug}
    assert by_id["1"]["agentInstruction"] is False  # bool, not "False"
    assert by_id["1"]["anchor"]["hook"] is None  # null, not ""
    assert "editedAt" not in by_id["2"]  # absent key stays absent
    assert by_id["3"]["editedAt"] is None  # explicit null preserved
    assert by_id["3"]["anchor"]["customAnchorKey"] == "extra-anchor-value"
    assert by_id["3"]["replies"][0]["edited"] is True  # typed reply extra
    assert by_id["3"]["replies"][0]["revision"] == 2  # int reply extra
    assert by_id["4"]["anchor"] is None  # non-dict anchor
    assert by_id["4"]["customThreadKey"] == 42  # int thread extra


def test_data_hyp_cid_and_agent_instruction_survive():
    hypresent = load_hypresent()
    src = fixture_text("basic.html")
    lean, stats = hypresent.dehydrate(src)
    assert stats["fallback"] is False
    assert 'data-hyp-cid="c-basic"' in lean
    assert "HYPRESENT AGENT INSTRUCTIONS" in lean
    # The real island element must be gone. Check the parsed tree, not a raw
    # substring: basic.html's agent-instruction head comment quotes the island
    # tag as literal text, and that comment is kept verbatim by design — a
    # substring test would wrongly trip on it.
    assert BeautifulSoup(lean, "lxml").find("script", id="hyp-comments") is None


def test_empty_and_missing_island_produce_zero_comment_digest():
    hypresent = load_hypresent()
    for fixture in ["empty-island.html", "no-island.html"]:
        lean, stats = hypresent.dehydrate(fixture_text(fixture))
        assert stats["fallback"] is False
        assert digest_threads(lean) == []
        assert stats["comments_preserved"] == 0


def test_tiny_fixture_falls_back_to_source_to_preserve_never_grow():
    hypresent = load_hypresent()
    src = fixture_text("tiny.html")
    lean, stats = hypresent.dehydrate(src)
    assert lean == src
    assert stats["fallback"] is True


def test_corrupted_island_refuses_without_writing_output(tmp_path):
    hypresent = load_hypresent()
    source = TOOLS_DIR / "fixtures" / "corrupted-island.html"
    out = tmp_path / "bad.lean.html"
    code = hypresent.main(["dehydrate", "--file", str(source), "--out", str(out)])
    assert code != 0
    assert not out.exists()


def test_cli_writes_default_out_and_summary(tmp_path, capsys):
    hypresent = load_hypresent()
    source = tmp_path / "deck.html"
    source.write_text(fixture_text("basic.html"), encoding="utf-8")
    code = hypresent.main(["dehydrate", "--file", str(source)])
    assert code == 0
    assert (tmp_path / "deck.lean.html").exists()
    stdout = capsys.readouterr().out
    assert "dehydrate:" in stdout
    assert "comments preserved:" in stdout


def test_cli_out_override_and_json(tmp_path, capsys):
    hypresent = load_hypresent()
    source = tmp_path / "deck.html"
    out = tmp_path / "other.html"
    source.write_text(fixture_text("basic.html"), encoding="utf-8")
    code = hypresent.main(["dehydrate", "--file", str(source), "--out", str(out), "--json"])
    assert code == 0
    assert out.exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["out"] == str(out)


def test_fallback_output_is_byte_identical_to_crlf_source(tmp_path, capsys):
    # Fallback path (composing would grow) must emit the source VERBATIM at the
    # byte level. A CRLF source is the trap: text-mode read/write would silently
    # translate newlines and change the on-disk bytes. Mirror tiny.html (which
    # the existing test proves falls back) but author it with CRLF endings.
    hypresent = load_hypresent()
    source = tmp_path / "crlf.html"
    source.write_bytes(b"<html><body>x</body></html>\r\n")
    out = tmp_path / "crlf.lean.html"
    code = hypresent.main(
        ["dehydrate", "--file", str(source), "--out", str(out), "--json"]
    )
    assert code == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["fallback"] is True
    assert out.read_bytes() == source.read_bytes()


def test_ondisk_output_never_grows_and_matches_reported_lean_bytes(tmp_path, capsys):
    # Non-fallback path: the on-disk output must never exceed the source in
    # bytes, and the reported lean_bytes stat must match the actual disk size.
    hypresent = load_hypresent()
    source = TOOLS_DIR / "fixtures" / "basic.html"
    out = tmp_path / "basic.lean.html"
    code = hypresent.main(
        ["dehydrate", "--file", str(source), "--out", str(out), "--json"]
    )
    assert code == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["fallback"] is False
    assert len(out.read_bytes()) <= len(source.read_bytes())
    assert len(out.read_bytes()) == stats["lean_bytes"]


def test_file_not_found_returns_nonzero(capsys):
    hypresent = load_hypresent()
    code = hypresent.main(["dehydrate", "--file", "does-not-exist.html"])
    assert code != 0
    assert "file not found" in capsys.readouterr().err
