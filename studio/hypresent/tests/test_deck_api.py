import pathlib
import shutil

import pytest

from server.deck_api import (
    handle_deck_load,
    handle_deck_save,
    handle_dialog_open_path,
    handle_dialog_save_path,
)
from server import api
from server.recompose import split_sections

REAL_DECK_SRC = "tecer-gsmm-introduction-test-v3.html"
REAL_DECK_SECTION_COUNT = 10
FIXTURE_LIB = "tests/e2e/fixtures/builder-lib"


def _write_deck_with_assets(tmp_path, sections, assets):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    assets_dir = src_dir / "assets"
    assets_dir.mkdir()
    for name, content in assets.items():
        target = assets_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    source = src_dir / "deck.html"
    source.write_text(
        "<html><body>" + "\n".join(sections) + "</body></html>",
        encoding="utf-8",
    )
    return source


def _write_deck_with_head_and_assets(tmp_path, head, sections, assets):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    assets_dir = src_dir / "assets"
    assets_dir.mkdir()
    for name, content in assets.items():
        target = assets_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    source = src_dir / "deck.html"
    source.write_text(
        "<html><head>"
        + head
        + "</head><body>"
        + "\n".join(sections)
        + "</body></html>",
        encoding="utf-8",
    )
    return source


def _save_existing_sections(source, out, indexes):
    return handle_deck_save(
        {
            "source_path": str(source),
            "out_path": str(out),
            "items": [{"kind": "existing", "index": i} for i in indexes],
            "libraries": {},
        }
    )


# ---------------------------------------------------------------------------
# deck-load
# ---------------------------------------------------------------------------


def test_deck_load_returns_ok_and_ordered_sections(tmp_path):
    dst = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, dst)
    status, resp = handle_deck_load({"path": str(dst)})
    assert status == 200
    assert resp["ok"] is True
    assert resp["name"] == "deck.html"
    assert resp["dir"] == str(tmp_path)
    assert len(resp["sections"]) == REAL_DECK_SECTION_COUNT
    for i, sec in enumerate(resp["sections"]):
        assert sec["index"] == i
        assert sec["html"].startswith("<section")
        assert sec["html"].endswith("</section>")


def test_deck_load_head_has_no_scripts(tmp_path):
    dst = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, dst)
    html = dst.read_text(encoding="utf-8")
    head_close = html.lower().find("</head>")
    html = (
        html[:head_close]
        + '<script>alert("x")</script>'
        + html[head_close:]
    )
    dst.write_text(html, encoding="utf-8")

    status, resp = handle_deck_load({"path": str(dst)})
    assert status == 200
    assert "<script>" not in resp["head"]
    assert "alert" not in resp["head"]


def test_deck_load_non_conforming_file(tmp_path):
    dst = tmp_path / "no-sections.html"
    dst.write_text("<html><body><p>Hello</p></body></html>", encoding="utf-8")
    status, resp = handle_deck_load({"path": str(dst)})
    assert status == 500
    assert "error" in resp
    assert "no <section>" in resp["error"]


def test_deck_load_missing_path():
    status, resp = handle_deck_load({})
    assert status == 500
    assert "error" in resp


def test_deck_load_file_not_found(tmp_path):
    status, resp = handle_deck_load({"path": str(tmp_path / "missing.html")})
    assert status == 500
    assert "error" in resp


# ---------------------------------------------------------------------------
# deck-save — core behaviour
# ---------------------------------------------------------------------------


def test_deck_save_reorder(tmp_path):
    src = tmp_path / "source.html"
    shutil.copy(REAL_DECK_SRC, src)
    out = tmp_path / "out.html"

    items = [{"kind": "existing", "index": i} for i in range(REAL_DECK_SECTION_COUNT)]
    # Swap first two
    items[0], items[1] = items[1], items[0]

    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": items,
            "libraries": {},
        }
    )
    assert status == 200
    assert resp["ok"] is True
    assert out.exists()

    result_html = out.read_text(encoding="utf-8")
    result_spans = split_sections(result_html)
    assert len(result_spans) == REAL_DECK_SECTION_COUNT

    src_html = src.read_text(encoding="utf-8")
    src_spans = split_sections(src_html)
    # First result section should be original section 1
    assert (
        result_html[result_spans[0][0] : result_spans[0][1]]
        == src_html[src_spans[1][0] : src_spans[1][1]]
    )


def test_deck_save_fragment_and_blank_with_assets(tmp_path):
    # Build a temporary library with an asset-referencing fragment.
    lib = tmp_path / "mylib"
    lib.mkdir()
    slides_dir = lib / "slides"
    slides_dir.mkdir()
    assets_dir = lib / "assets"
    assets_dir.mkdir()

    fragment = '<section class="slide"><img src="assets/logo.png"></section>'
    (slides_dir / "test.html").write_text(fragment, encoding="utf-8")
    (assets_dir / "logo.png").write_bytes(b"PNG")

    src = tmp_path / "source.html"
    shutil.copy(REAL_DECK_SRC, src)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"

    items = [
        {"kind": "blank"},
        {"kind": "library", "library_path": str(lib), "slide_id": "test"},
        {"kind": "existing", "index": 0},
    ]

    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": items,
            "libraries": {str(lib): True},
        }
    )
    assert status == 200
    assert resp["ok"] is True
    assert "assets/logo.png" in resp["assets_copied"]
    assert "assets_skipped" not in resp

    result = out.read_text(encoding="utf-8")
    assert fragment in result

    result_spans = split_sections(result)
    # First section is the blank — must be marker-free.
    blank_markup = result[result_spans[0][0] : result_spans[0][1]]
    assert "hyp-" not in blank_markup
    assert "data-hyp-" not in blank_markup

    assert (out_dir / "assets" / "logo.png").exists()
    assert (out_dir / "assets" / "logo.png").read_bytes() == b"PNG"


def test_deck_save_overwrite_in_place(tmp_path):
    src = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, src)

    items = [{"kind": "existing", "index": 0}]
    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(src),
            "items": items,
            "libraries": {},
        }
    )
    assert status == 200
    assert resp["ok"] is True
    assert src.exists()

    spans = split_sections(src.read_text(encoding="utf-8"))
    assert len(spans) == 1


def test_deck_save_original_root_deck_never_touched(tmp_path):
    import os

    before_bytes = open(REAL_DECK_SRC, "rb").read()
    before_mtime = os.path.getmtime(REAL_DECK_SRC)

    src = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, src)
    out = tmp_path / "out.html"

    items = [
        {"kind": "blank"},
        {"kind": "existing", "index": 0},
        {"kind": "existing", "index": 0},
    ]
    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": items,
            "libraries": {},
        }
    )
    assert status == 200

    after_bytes = open(REAL_DECK_SRC, "rb").read()
    assert after_bytes == before_bytes
    assert os.path.getmtime(REAL_DECK_SRC) == before_mtime


# ---------------------------------------------------------------------------
# deck-save — edge cases & errors
# ---------------------------------------------------------------------------


def test_deck_save_missing_parent_dir(tmp_path):
    src = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, src)
    out = tmp_path / "nonexistent" / "out.html"

    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": [{"kind": "existing", "index": 0}],
            "libraries": {},
        }
    )
    assert status == 500
    assert "error" in resp
    assert "Parent directory" in resp["error"]
    assert not out.exists()


def test_deck_save_out_of_range_index(tmp_path):
    src = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, src)
    out = tmp_path / "out.html"

    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": [{"kind": "existing", "index": 99}],
            "libraries": {},
        }
    )
    assert status == 500
    assert "error" in resp
    assert "out of range" in resp["error"]
    assert not out.exists()


def test_deck_save_missing_fragment(tmp_path):
    src = tmp_path / "deck.html"
    shutil.copy(REAL_DECK_SRC, src)
    out = tmp_path / "out.html"

    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": [
                {
                    "kind": "library",
                    "library_path": str(tmp_path / "nolib"),
                    "slide_id": "nope",
                }
            ],
            "libraries": {},
        }
    )
    assert status == 500
    assert "error" in resp
    assert not out.exists()


def test_deck_save_zero_sections_source(tmp_path):
    src = tmp_path / "bad.html"
    src.write_text("<html><body><p>no slides</p></body></html>", encoding="utf-8")
    out = tmp_path / "out.html"

    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": [],
            "libraries": {},
        }
    )
    assert status == 500
    assert "no <section>" in resp["error"]
    assert not out.exists()


def test_deck_save_asset_collision_skip(tmp_path):
    lib = tmp_path / "mylib"
    lib.mkdir()
    slides_dir = lib / "slides"
    slides_dir.mkdir()
    assets_dir = lib / "assets"
    assets_dir.mkdir()

    fragment = '<section class="slide"><img src="assets/logo.png"></section>'
    (slides_dir / "test.html").write_text(fragment, encoding="utf-8")
    (assets_dir / "logo.png").write_bytes(b"PNG")

    src = tmp_path / "source.html"
    shutil.copy(REAL_DECK_SRC, src)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"
    # Pre-create the asset to trigger collision.
    (out_dir / "assets").mkdir()
    (out_dir / "assets" / "logo.png").write_bytes(b"OLD")

    items = [
        {"kind": "library", "library_path": str(lib), "slide_id": "test"},
    ]

    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": items,
            "libraries": {str(lib): True},
        }
    )
    assert status == 200
    assert resp["ok"] is True
    assert "assets/logo.png" in resp["assets_skipped"]
    assert (out_dir / "assets" / "logo.png").read_bytes() == b"OLD"


def test_deck_save_refuses_multi_section_fragment(tmp_path):
    lib = tmp_path / "mylib"
    slides_dir = lib / "slides"
    slides_dir.mkdir(parents=True)
    (slides_dir / "two.html").write_text(
        "<section>A</section>\n<section>B</section>", encoding="utf-8"
    )

    src = tmp_path / "source.html"
    shutil.copy(REAL_DECK_SRC, src)
    out = tmp_path / "out" / "deck.html"
    out.parent.mkdir()

    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": [
                {"kind": "library", "library_path": str(lib), "slide_id": "two"}
            ],
            "libraries": {str(lib): True},
        }
    )
    assert status == 500
    assert "exactly one top-level section" in resp["error"]
    assert not out.exists()


def test_deck_save_copies_own_asset_to_new_dir(tmp_path):
    source = _write_deck_with_assets(
        tmp_path,
        ['<section><img src="assets/own.png"></section>'],
        {"own.png": b"OWN"},
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0])

    assert status == 200
    assert resp["ok"] is True
    assert resp["assets_copied"] == ["assets/own.png"]
    assert resp["assets_missing"] == []
    assert "assets_renamed" not in resp
    assert (out_dir / "assets" / "own.png").read_bytes() == b"OWN"
    result = out.read_text(encoding="utf-8")
    assert '<section><img src="assets/own.png"></section>' in result


def test_deck_save_reports_missing_own_asset_without_copying(tmp_path):
    source = _write_deck_with_assets(
        tmp_path,
        ['<section><img src="assets/missing.png"></section>'],
        {},
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0])

    assert status == 200
    assert resp["ok"] is True
    assert resp["assets_copied"] == []
    assert resp["assets_missing"] == ["assets/missing.png"]
    assert not (out_dir / "assets").exists()
    result = out.read_text(encoding="utf-8")
    assert '<section><img src="assets/missing.png"></section>' in result


def test_deck_save_copies_head_css_own_asset_to_new_dir(tmp_path):
    head = '<style>.cover{background-image:url("assets/bg.jpg")}</style>'
    section = "<section><p>Keep me</p></section>"
    source = _write_deck_with_head_and_assets(
        tmp_path,
        head,
        [section],
        {"bg.jpg": b"BG"},
    )
    source_html = source.read_text(encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0])

    assert status == 200
    assert resp["ok"] is True
    assert resp["assets_copied"] == ["assets/bg.jpg"]
    assert resp["assets_missing"] == []
    assert "assets_renamed" not in resp
    assert (out_dir / "assets" / "bg.jpg").read_bytes() == b"BG"
    assert out.read_text(encoding="utf-8") == source_html


def test_deck_save_reports_missing_head_css_own_asset(tmp_path):
    head = '<style>.cover{background-image:url("assets/bg.jpg")}</style>'
    source = _write_deck_with_head_and_assets(
        tmp_path,
        head,
        ["<section><p>Keep me</p></section>"],
        {},
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0])

    assert status == 200
    assert resp["ok"] is True
    assert resp["assets_copied"] == []
    assert resp["assets_missing"] == ["assets/bg.jpg"]
    assert not (out_dir / "assets").exists()


def test_deck_save_skips_head_css_asset_already_copied_by_section(tmp_path):
    head = '<style>.cover{background-image:url("assets/bg.jpg")}</style>'
    section = '<section><img src="assets/bg.jpg"></section>'
    source = _write_deck_with_head_and_assets(
        tmp_path,
        head,
        [section],
        {"bg.jpg": b"BG"},
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0])

    assert status == 200
    assert resp["ok"] is True
    assert resp["assets_copied"] == ["assets/bg.jpg"]
    assert resp["assets_skipped"] == ["assets/bg.jpg"]
    assert resp["assets_missing"] == []
    assert (out_dir / "assets" / "bg.jpg").read_bytes() == b"BG"


def test_deck_save_copies_existing_and_reports_missing_own_asset(tmp_path):
    section = (
        '<section><img src="assets/own.png">'
        '<img src="assets/missing.png"></section>'
    )
    source = _write_deck_with_assets(
        tmp_path,
        [section],
        {"own.png": b"OWN"},
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0])

    assert status == 200
    assert resp["ok"] is True
    assert resp["assets_copied"] == ["assets/own.png"]
    assert resp["assets_missing"] == ["assets/missing.png"]
    assert (out_dir / "assets" / "own.png").read_bytes() == b"OWN"
    result = out.read_text(encoding="utf-8")
    assert section in result


def test_deck_save_deduplicates_missing_own_assets_in_first_seen_order(tmp_path):
    source = _write_deck_with_assets(
        tmp_path,
        [
            '<section><img src="assets/first.png"><img src="assets/second.png"></section>',
            '<section><img src="assets/second.png"><img src="assets/first.png"></section>',
        ],
        {},
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0, 1])

    assert status == 200
    assert resp["assets_missing"] == [
        "assets/first.png",
        "assets/second.png",
    ]
    assert not (out_dir / "assets").exists()


def test_deck_save_skips_own_asset_from_dropped_slide(tmp_path):
    source = _write_deck_with_assets(
        tmp_path,
        [
            '<section><img src="assets/keep.png"></section>',
            '<section><img src="assets/drop.png"></section>',
        ],
        {"keep.png": b"KEEP", "drop.png": b"DROP"},
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0])

    assert status == 200
    assert resp["assets_copied"] == ["assets/keep.png"]
    assert (out_dir / "assets" / "keep.png").read_bytes() == b"KEEP"
    assert not (out_dir / "assets" / "drop.png").exists()
    assert "assets/drop.png" not in out.read_text(encoding="utf-8")


def test_deck_save_same_dir_leaves_own_asset_refs_byte_identical(tmp_path):
    section = '<section><img src="assets/own.png"></section>'
    source = _write_deck_with_assets(tmp_path, [section], {"own.png": b"OWN"})
    out = source.parent / "saved.html"

    status, resp = _save_existing_sections(source, out, [0])

    assert status == 200
    assert resp["assets_copied"] == []
    assert "assets_renamed" not in resp
    result = out.read_text(encoding="utf-8")
    result_spans = split_sections(result)
    assert result[result_spans[0][0] : result_spans[0][1]] == section


def test_deck_save_renames_colliding_own_asset_and_rewrites_safe_refs(tmp_path):
    section = (
        '<section><img src="assets/logo.png">'
        '<a href="assets/logo.png.bak">bak</a>'
        '<style>.hero{background:url(assets/logo.png)}</style></section>'
    )
    source = _write_deck_with_assets(
        tmp_path,
        [section],
        {"logo.png": b"OWN"},
    )
    out_dir = tmp_path / "out"
    (out_dir / "assets").mkdir(parents=True)
    (out_dir / "assets" / "logo.png").write_bytes(b"OLD")
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0])

    assert status == 200
    assert resp["assets_copied"] == []
    assert resp["assets_renamed"] == [
        {"from": "assets/logo.png", "to": "assets/logo-1.png"}
    ]
    assert (out_dir / "assets" / "logo.png").read_bytes() == b"OLD"
    assert (out_dir / "assets" / "logo-1.png").read_bytes() == b"OWN"
    result = out.read_text(encoding="utf-8")
    assert 'src="assets/logo-1.png"' in result
    assert "url(assets/logo-1.png)" in result
    assert 'href="assets/logo.png.bak"' in result


def test_deck_save_reuses_one_rename_for_duplicate_own_section(tmp_path):
    source = _write_deck_with_assets(
        tmp_path,
        ['<section><img src="assets/logo.png"></section>'],
        {"logo.png": b"OWN"},
    )
    out_dir = tmp_path / "out"
    (out_dir / "assets").mkdir(parents=True)
    (out_dir / "assets" / "logo.png").write_bytes(b"OLD")
    out = out_dir / "deck.html"

    status, resp = _save_existing_sections(source, out, [0, 0])

    assert status == 200
    assert resp["assets_renamed"] == [
        {"from": "assets/logo.png", "to": "assets/logo-1.png"}
    ]
    assert (out_dir / "assets" / "logo.png").read_bytes() == b"OLD"
    assert (out_dir / "assets" / "logo-1.png").read_bytes() == b"OWN"
    result = out.read_text(encoding="utf-8")
    assert result.count('src="assets/logo-1.png"') == 2
    assert 'src="assets/logo.png"' not in result


def test_deck_save_with_fixture_library_no_assets(tmp_path):
    """Using the real e2e fixture library (fragments reference no assets)."""
    src = tmp_path / "source.html"
    shutil.copy(REAL_DECK_SRC, src)
    out = tmp_path / "out.html"

    items = [
        {"kind": "library", "library_path": FIXTURE_LIB, "slide_id": "intro-e2e"},
        {"kind": "existing", "index": 0},
    ]

    status, resp = handle_deck_save(
        {
            "source_path": str(src),
            "out_path": str(out),
            "items": items,
            "libraries": {FIXTURE_LIB: True},
        }
    )
    assert status == 200
    assert resp["ok"] is True
    assert resp["assets_copied"] == []
    assert "assets_skipped" not in resp

    result = out.read_text(encoding="utf-8")
    fixture_fragment = (
        pathlib.Path(FIXTURE_LIB) / "slides" / "intro-e2e.html"
    ).read_text(encoding="utf-8")
    assert fixture_fragment in result


# ---------------------------------------------------------------------------
# dialog path endpoints
# ---------------------------------------------------------------------------


def test_dialog_open_path_returns_path():
    api.set_dialog_launcher(lambda kind: r"C:\test\file.html")
    try:
        status, resp = handle_dialog_open_path()
        assert status == 200
        assert resp["path"] == r"C:\test\file.html"
    finally:
        api.set_dialog_launcher(None)


def test_dialog_open_path_cancelled():
    api.set_dialog_launcher(lambda kind: None)
    try:
        status, resp = handle_dialog_open_path()
        assert status == 200
        assert resp.get("cancelled") is True
    finally:
        api.set_dialog_launcher(None)


def test_dialog_save_path_returns_path():
    api.set_dialog_launcher(lambda kind: r"C:\test\save.html")
    try:
        status, resp = handle_dialog_save_path()
        assert status == 200
        assert resp["path"] == r"C:\test\save.html"
    finally:
        api.set_dialog_launcher(None)


def test_dialog_save_path_cancelled():
    api.set_dialog_launcher(lambda kind: None)
    try:
        status, resp = handle_dialog_save_path()
        assert status == 200
        assert resp.get("cancelled") is True
    finally:
        api.set_dialog_launcher(None)
