"""Tests for deck export registering stamped deck themes into a library."""

import json
import pathlib
import sys

# Ensure studio/hypresent is importable regardless of invocation cwd.
_TEST_ROOT = pathlib.Path(__file__).resolve().parent
_HYPRESENT_ROOT = _TEST_ROOT.parent
if str(_HYPRESENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_HYPRESENT_ROOT))

from server.builder_api import handle_deck_export


CONTRACT_THEME_CSS = """
:root {
  --bg: #fff;
  --bg-soft: #f7f7f7;
  --fg: #111;
  --fg-invert: #fff;
  --muted: #666;
  --brand: #0a66ff;
  --client-accent: #0a66ff;
}
@page { size: 1280px 720px; }
body { margin: 0; }
.slide, .slide--soft, .slide--dark, .slide--cover, .slide--closing,
.dark-bg-overlay, .slide-header, .kicker, .slide-title, .slide-subtitle,
.slide-body, .grid-3, .card, .card-icon, .card-title, .card-body,
.aside-note, .dark-callout, .cover-logos, .cover-mark, .cover-logos-sep,
.cover-client, .cover-title, .cover-subtitle, .cover-date,
.divider-statement, .sources-line, .partner-mark, .closing-statement,
.closing-contacts, .closing-wordmark, .slide-number { box-sizing: border-box; }
"""


def _make_library(tmp_path, themes=None, theme_files=None):
    lib = tmp_path / "library"
    lib.mkdir()
    (lib / "slides").mkdir()
    (lib / "assets").mkdir()
    (lib / "theme.css").write_text(CONTRACT_THEME_CSS, encoding="utf-8")
    (lib / "library.json").write_text(
        json.dumps(
            {
                "convention_version": "1.0",
                "engine_version": "1.1",
                "name": "Export Theme Test",
                "default_lang": "en",
                "sections": ["general"],
                "themes": themes or [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (lib / "manifest.md").write_text(
        "\n".join(
            [
                "# Export Theme Test",
                "",
                "## Slides",
                "",
                "| id | file | section | title | audience | lang | kind | summary | assets | provenance | status |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for rel_path, content in (theme_files or {}).items():
        path = lib / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return lib


def _make_deck(tmp_path, *, theme_name=None, contract="1.0", css=CONTRACT_THEME_CSS):
    theme_attrs = ""
    html_attrs = ""
    if theme_name:
        theme_attrs = f' data-theme="{theme_name}" data-theme-contract="{contract}"'
        html_attrs = f' data-theme="{theme_name}" data-theme-contract="{contract}"'
    deck_html = f"""<!doctype html>
<html{html_attrs}>
<head>
  <style{theme_attrs}>
{css}
  </style>
</head>
<body>
  <section
    class="slide"
    data-hyp-slide-id="alpha"
    data-hyp-section="general"
    data-hyp-title="Alpha"
    data-hyp-audience="general"
    data-hyp-lang="en"
    data-hyp-summary="Alpha summary"
    data-hyp-kind="ready"
    data-hyp-provenance="test">
    <h1 class="slide-title">Alpha</h1>
  </section>
</body>
</html>
"""
    deck = tmp_path / "deck.html"
    deck.write_text(deck_html, encoding="utf-8")
    return deck


def _export(deck, lib):
    return handle_deck_export(
        {
            "deck_path": str(deck),
            "selected_ids": ["alpha"],
            "library_path": str(lib),
        }
    )


def test_export_registers_new_theme(tmp_path):
    lib = _make_library(tmp_path)
    deck = _make_deck(tmp_path, theme_name="nimbus", contract="1.0")

    status, resp = _export(deck, lib)

    assert status == 200
    assert resp["ok"] is True
    assert resp["theme"]["status"] == "registered"
    assert resp["theme"]["name"] == "nimbus"
    assert resp["theme"]["file"] == "themes/nimbus.css"
    assert resp["theme"]["lint_warnings"] == []

    css_path = lib / "themes" / "nimbus.css"
    assert css_path.read_text(encoding="utf-8") == CONTRACT_THEME_CSS.strip() + "\n"

    library_json = json.loads((lib / "library.json").read_text(encoding="utf-8"))
    assert library_json["themes"] == [
        {
            "name": "nimbus",
            "file": "themes/nimbus.css",
            "label": "nimbus",
            "contract_version": "1.0",
        }
    ]


def test_export_existing_theme_does_not_overwrite_or_duplicate(tmp_path):
    existing = ".slide { color: old; }\n"
    lib = _make_library(
        tmp_path,
        themes=[
            {
                "name": "nimbus",
                "file": "themes/nimbus.css",
                "label": "Nimbus",
                "contract_version": "1.0",
            }
        ],
        theme_files={"themes/nimbus.css": existing},
    )
    deck = _make_deck(tmp_path, theme_name="nimbus", contract="1.0")

    status, resp = _export(deck, lib)

    assert status == 200
    assert resp["ok"] is True
    assert resp["theme"] == {
        "status": "skipped",
        "reason": "already_present",
        "name": "nimbus",
    }
    assert (lib / "themes" / "nimbus.css").read_text(encoding="utf-8") == existing
    library_json = json.loads((lib / "library.json").read_text(encoding="utf-8"))
    assert [theme["name"] for theme in library_json["themes"]] == ["nimbus"]


def test_export_legacy_deck_with_no_theme_stamp_skips_registration(tmp_path):
    lib = _make_library(tmp_path)
    deck = _make_deck(tmp_path, theme_name=None)

    status, resp = _export(deck, lib)

    assert status == 200
    assert resp["ok"] is True
    assert resp["theme"] == {"status": "skipped", "reason": "no_stamp"}
    assert not (lib / "themes").exists()
    library_json = json.loads((lib / "library.json").read_text(encoding="utf-8"))
    assert library_json["themes"] == []
    assert (lib / "slides" / "alpha.html").exists()


def test_export_registers_theme_and_flags_contract_lint_failure(tmp_path):
    bad_css = ".slide { color: red; }"
    lib = _make_library(tmp_path)
    deck = _make_deck(
        tmp_path,
        theme_name="broken",
        contract="1.0",
        css=bad_css,
    )

    status, resp = _export(deck, lib)

    assert status == 200
    assert resp["ok"] is True
    assert resp["theme"]["status"] == "registered"
    assert resp["theme"]["name"] == "broken"
    assert resp["theme"]["file"] == "themes/broken.css"
    assert resp["theme"]["lint_warnings"]
    assert "--bg" in resp["theme"]["lint_warnings"][0]
    assert ".slide-title" in resp["theme"]["lint_warnings"][0]

    assert (lib / "themes" / "broken.css").read_text(encoding="utf-8") == bad_css + "\n"
    library_json = json.loads((lib / "library.json").read_text(encoding="utf-8"))
    assert library_json["themes"] == [
        {
            "name": "broken",
            "file": "themes/broken.css",
            "label": "broken",
            "contract_version": "1.0",
        }
    ]


def test_export_preserves_existing_library_fields_and_appends_theme(tmp_path):
    existing_theme_css = ".slide { color: existing; }\n"
    lib = _make_library(
        tmp_path,
        themes=[
            {
                "name": "graphite",
                "file": "themes/graphite.css",
                "label": "Graphite",
                "contract_version": "1.0",
            }
        ],
        theme_files={"themes/graphite.css": existing_theme_css},
    )
    original = {
        "convention_version": "1.0",
        "engine_version": "1.1",
        "name": "Export Theme Test",
        "sections": ["general", "appendix"],
        "default_lang": "pt",
        "themes": [
            {
                "name": "graphite",
                "file": "themes/graphite.css",
                "label": "Graphite",
                "contract_version": "1.0",
            }
        ],
        "default_theme": "graphite",
        "extra_field": {"kept": ["byte", "value", "intact"]},
    }
    (lib / "library.json").write_text(
        json.dumps(original, indent=2) + "\n",
        encoding="utf-8",
    )
    deck = _make_deck(tmp_path, theme_name="nimbus", contract="1.0")

    status, resp = _export(deck, lib)

    assert status == 200
    assert resp["ok"] is True
    assert resp["theme"]["status"] == "registered"

    library_json = json.loads((lib / "library.json").read_text(encoding="utf-8"))
    for key in (
        "convention_version",
        "engine_version",
        "name",
        "sections",
        "default_lang",
        "default_theme",
        "extra_field",
    ):
        assert library_json[key] == original[key]
    assert library_json["themes"] == original["themes"] + [
        {
            "name": "nimbus",
            "file": "themes/nimbus.css",
            "label": "nimbus",
            "contract_version": "1.0",
        }
    ]
    assert (lib / "themes" / "graphite.css").read_text(encoding="utf-8") == existing_theme_css


def test_export_implicit_default_theme_skips_registration(tmp_path):
    lib = _make_library(tmp_path)
    before = json.loads((lib / "library.json").read_text(encoding="utf-8"))
    deck = _make_deck(tmp_path, theme_name="default", contract="1.0")

    status, resp = _export(deck, lib)

    assert status == 200
    assert resp["ok"] is True
    assert resp["theme"] == {
        "status": "skipped",
        "reason": "already_present",
        "name": "default",
    }
    assert not (lib / "themes").exists()
    assert json.loads((lib / "library.json").read_text(encoding="utf-8")) == before
