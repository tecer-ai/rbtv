import shutil

import pytest

from server.recompose import BLANK_SECTION, RecomposeError, recompose, split_sections

# ---------------------------------------------------------------------------
# split_sections — basic behaviour
# ---------------------------------------------------------------------------


def test_split_sections_empty():
    assert split_sections("") == []


def test_split_sections_no_sections():
    assert split_sections("<html><body><p>Hello</p></body></html>") == []


def test_split_sections_basic():
    html = "<section>A</section><section>B</section>"
    spans = split_sections(html)
    assert len(spans) == 2
    assert html[spans[0][0] : spans[0][1]] == "<section>A</section>"
    assert html[spans[1][0] : spans[1][1]] == "<section>B</section>"


# ---------------------------------------------------------------------------
# Edge cases — comments, nesting, zero sections
# ---------------------------------------------------------------------------


def test_split_sections_comments_ignored():
    html = (
        "<!-- <section>fake</section> -->"
        "<section>real</section>"
        "<!-- </section> -->"
    )
    spans = split_sections(html)
    assert len(spans) == 1
    assert html[spans[0][0] : spans[0][1]] == "<section>real</section>"


def test_split_sections_multiline_comment():
    html = """<!--
    <section>inside comment</section>
    --><section>real</section>"""
    spans = split_sections(html)
    assert len(spans) == 1
    assert html[spans[0][0] : spans[0][1]] == "<section>real</section>"


def test_split_sections_nested():
    html = "<section>outer<section>inner</section></section>"
    spans = split_sections(html)
    assert len(spans) == 1
    assert (
        html[spans[0][0] : spans[0][1]]
        == "<section>outer<section>inner</section></section>"
    )


def test_split_sections_deeply_nested():
    html = (
        "<section>a<section>b<section>c</section></section></section>"
    )
    spans = split_sections(html)
    assert len(spans) == 1
    assert html[spans[0][0] : spans[0][1]] == html


def test_recompose_zero_sections_raises():
    with pytest.raises(RecomposeError, match="no <section> slides found"):
        recompose("<html></html>", [])


# ---------------------------------------------------------------------------
# recompose — behaviour rows 1-3 (reorder, remove, duplicate)
# ---------------------------------------------------------------------------


def test_recompose_reorder():
    html = "PREFIX<section>A</section>MIDDLE<section>B</section>SUFFIX"
    result = recompose(
        html,
        [
            {"kind": "existing", "index": 1},
            {"kind": "existing", "index": 0},
        ],
    )
    assert result == "PREFIX<section>B</section><section>A</section>SUFFIX"


def test_recompose_remove():
    html = "PREFIX<section>A</section>MIDDLE<section>B</section>SUFFIX"
    result = recompose(html, [{"kind": "existing", "index": 0}])
    assert result == "PREFIX<section>A</section>SUFFIX"


def test_recompose_duplicate():
    html = "PREFIX<section>A</section><section>B</section>SUFFIX"
    result = recompose(
        html,
        [
            {"kind": "existing", "index": 0},
            {"kind": "existing", "index": 0},
        ],
    )
    assert result == "PREFIX<section>A</section><section>A</section>SUFFIX"


# ---------------------------------------------------------------------------
# recompose — blank purity (behaviour row 6)
# ---------------------------------------------------------------------------


def test_recompose_blank_has_no_hyp_markers():
    html = "<section>A</section>"
    result = recompose(html, [{"kind": "blank"}])
    # The blank section itself must be marker-free.
    spans = split_sections(result)
    blank_markup = result[spans[0][0] : spans[0][1]]
    assert "hyp-" not in blank_markup
    assert "data-hyp-" not in blank_markup


def test_blank_section_constant_plain():
    assert "hyp-" not in BLANK_SECTION
    assert "data-hyp-" not in BLANK_SECTION
    assert "<section" in BLANK_SECTION
    assert "</section>" in BLANK_SECTION


# ---------------------------------------------------------------------------
# recompose — fragments
# ---------------------------------------------------------------------------


def test_recompose_fragment():
    html = "PREFIX<section>A</section>SUFFIX"
    result = recompose(
        html, [{"kind": "fragment", "html": '<section class="lib">L</section>'}]
    )
    assert result == 'PREFIX<section class="lib">L</section>SUFFIX'


# ---------------------------------------------------------------------------
# Edge case — out-of-range index
# ---------------------------------------------------------------------------


def test_recompose_out_of_range_high():
    html = "<section>A</section><section>B</section>"
    with pytest.raises(RecomposeError, match="out of range"):
        recompose(html, [{"kind": "existing", "index": 2}])


def test_recompose_out_of_range_negative():
    html = "<section>A</section><section>B</section>"
    with pytest.raises(RecomposeError, match="out of range"):
        recompose(html, [{"kind": "existing", "index": -1}])


# ---------------------------------------------------------------------------
# Real deck tests (copied to tmp_path — root decks are READ-ONLY)
# ---------------------------------------------------------------------------

REAL_DECK_SRC = "tecer-gsmm-introduction-test-v3.html"
REAL_DECK_SECTION_COUNT = 10


def test_real_deck_section_count(tmp_path):
    dst = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, dst)
    html = dst.read_text(encoding="utf-8")
    spans = split_sections(html)
    assert len(spans) == REAL_DECK_SECTION_COUNT


def test_real_deck_reorder_byte_identity(tmp_path):
    """Rotate section 2 to front; verify prefix, suffix, and moved spans
    are byte-identical to the source."""
    dst = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, dst)
    html = dst.read_text(encoding="utf-8")
    spans = split_sections(html)

    items = [{"kind": "existing", "index": 2}] + [
        {"kind": "existing", "index": i} for i in range(10) if i != 2
    ]
    result = recompose(html, items)

    # Prefix and suffix must be byte-identical.
    assert result[: spans[0][0]] == html[: spans[0][0]]
    suffix_len = len(html) - spans[-1][1]
    assert result[-suffix_len:] == html[spans[-1][1] :]

    # Result spans must match original spans in the new order.
    result_spans = split_sections(result)
    assert len(result_spans) == REAL_DECK_SECTION_COUNT
    expected_order = [2, 0, 1, 3, 4, 5, 6, 7, 8, 9]
    for res_idx, orig_idx in enumerate(expected_order):
        assert (
            result[result_spans[res_idx][0] : result_spans[res_idx][1]]
            == html[spans[orig_idx][0] : spans[orig_idx][1]]
        )


def test_real_deck_remove_and_duplicate(tmp_path):
    """Remove section 1, duplicate section 0."""
    dst = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, dst)
    html = dst.read_text(encoding="utf-8")
    spans = split_sections(html)

    items = [
        {"kind": "existing", "index": 0},
        {"kind": "existing", "index": 0},
    ] + [{"kind": "existing", "index": i} for i in range(2, 10)]
    result = recompose(html, items)

    result_spans = split_sections(result)
    assert len(result_spans) == REAL_DECK_SECTION_COUNT

    # First two result sections must both be original section 0.
    assert (
        result[result_spans[0][0] : result_spans[0][1]]
        == html[spans[0][0] : spans[0][1]]
    )
    assert (
        result[result_spans[1][0] : result_spans[1][1]]
        == html[spans[0][0] : spans[0][1]]
    )


def test_real_deck_blank_purity(tmp_path):
    """A blank inserted at the front must carry no hyp- markers."""
    dst = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, dst)
    html = dst.read_text(encoding="utf-8")

    items = [{"kind": "blank"}] + [
        {"kind": "existing", "index": i} for i in range(REAL_DECK_SECTION_COUNT)
    ]
    result = recompose(html, items)

    result_spans = split_sections(result)
    blank_markup = result[result_spans[0][0] : result_spans[0][1]]
    assert "hyp-" not in blank_markup
    assert "data-hyp-" not in blank_markup
