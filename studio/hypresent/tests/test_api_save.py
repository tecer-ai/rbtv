from server import api


def _write_open_deck(tmp_path, html, assets):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    assets_dir = src_dir / "assets"
    assets_dir.mkdir()
    for name, content in assets.items():
        target = assets_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    source = src_dir / "deck.html"
    source.write_text(html, encoding="utf-8")
    return source


def test_save_as_copies_own_asset_to_new_dir(tmp_path):
    html = '<html><body><img src="assets/x.png"></body></html>'
    source = _write_open_deck(tmp_path, html, {"x.png": b"X"})
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "saved.html"
    api.set_open_path(str(source))

    try:
        status, resp = api.handle_save_as({"path": str(out), "html": html})
    finally:
        api.set_open_path(None)

    assert status == 200
    assert resp["ok"] is True
    assert resp["assets_copied"] == ["assets/x.png"]
    assert resp["assets_missing"] == []
    assert "assets_skipped" not in resp
    assert (out_dir / "assets" / "x.png").read_bytes() == b"X"
    assert out.read_text(encoding="utf-8") == html


def test_save_as_reports_missing_own_asset_to_new_dir(tmp_path):
    html = '<html><body><img src="assets/x.png"></body></html>'
    source = _write_open_deck(tmp_path, html, {})
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "saved.html"
    api.set_open_path(str(source))

    try:
        status, resp = api.handle_save_as({"path": str(out), "html": html})
    finally:
        api.set_open_path(None)

    assert status == 200
    assert resp["ok"] is True
    assert resp["assets_copied"] == []
    assert resp["assets_missing"] == ["assets/x.png"]
    assert "assets_skipped" not in resp
    assert not (out_dir / "assets").exists()
    assert out.read_text(encoding="utf-8") == html


def test_save_as_skips_existing_destination_asset(tmp_path):
    html = '<html><body><img src="assets/x.png"></body></html>'
    source = _write_open_deck(tmp_path, html, {"x.png": b"X"})
    out_dir = tmp_path / "out"
    (out_dir / "assets").mkdir(parents=True)
    (out_dir / "assets" / "x.png").write_bytes(b"OLD")
    out = out_dir / "saved.html"
    api.set_open_path(str(source))

    try:
        status, resp = api.handle_save_as({"path": str(out), "html": html})
    finally:
        api.set_open_path(None)

    assert status == 200
    assert resp["assets_copied"] == []
    assert resp["assets_skipped"] == ["assets/x.png"]
    assert resp["assets_missing"] == []
    assert (out_dir / "assets" / "x.png").read_bytes() == b"OLD"
    assert out.read_text(encoding="utf-8") == html


def test_save_as_same_dir_keeps_existing_response_shape(tmp_path):
    html = '<html><body><img src="assets/x.png"></body></html>'
    source = _write_open_deck(tmp_path, html, {"x.png": b"X"})
    out = source.parent / "saved.html"
    api.set_open_path(str(source))

    try:
        status, resp = api.handle_save_as({"path": str(out), "html": html})
    finally:
        api.set_open_path(None)

    assert status == 200
    assert resp == {"ok": True, "path": str(out)}
    assert out.read_text(encoding="utf-8") == html


def test_save_as_without_open_file_keeps_existing_response_shape(tmp_path):
    html = '<html><body><img src="assets/x.png"></body></html>'
    out = tmp_path / "saved.html"
    api.set_open_path(None)

    status, resp = api.handle_save_as({"path": str(out), "html": html})

    assert status == 200
    assert resp == {"ok": True, "path": str(out)}
    assert out.read_text(encoding="utf-8") == html


def test_save_silent_overwrite_keeps_existing_response_shape(tmp_path):
    html = '<html><body><img src="assets/x.png"></body></html>'
    source = _write_open_deck(tmp_path, "<html></html>", {"x.png": b"X"})
    api.set_open_path(str(source))

    try:
        status, resp = api.handle_save({"html": html})
    finally:
        api.set_open_path(None)

    assert status == 200
    assert resp == {"ok": True, "path": str(source)}
    assert source.read_text(encoding="utf-8") == html


def test_dialog_save_as_colocates_before_repointing_open_path(tmp_path):
    html = '<html><body><img src="assets/x.png"></body></html>'
    source = _write_open_deck(tmp_path, html, {"x.png": b"X"})
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "saved.html"
    api.set_open_path(str(source))
    api.set_dialog_launcher(lambda kind: str(out))

    try:
        status, resp = api.handle_dialog_save_as({"html": html})
        open_path_after_save = api.get_open_path()
    finally:
        api.set_dialog_launcher(None)
        api.set_open_path(None)

    assert status == 200
    assert resp["assets_copied"] == ["assets/x.png"]
    assert resp["assets_missing"] == []
    assert (out_dir / "assets" / "x.png").read_bytes() == b"X"
    assert open_path_after_save == str(out.resolve())
