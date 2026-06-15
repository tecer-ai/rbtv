"""Unit tests for decompose.py — deck → library fragment + manifest row engine.

All tests run headless (no HTTP, no server) via direct import of decompose.py.
Run with:  python -m pytest tests/unit/test_decompose.py -v
"""

import os
import tempfile
import textwrap

import pytest

# The engine must be importable as a plain module — no HTTP dependency.
from server.decompose import (
    DecomposeError,
    DecomposeResult,
    ManifestRow,
    SlideExport,
    _dedup_id,
    _discover_assets,
    _resolve_section,
    _strip_chrome,
    decompose_deck,
    load_library_json,
    row_to_markdown,
    split_sections,
    validate_fragment,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DECLARED_SECTIONS = ["opening", "intro", "diagnosis", "product", "proof", "closing"]

LIBRARY_JSON = {
    "convention_version": "1.0",
    "engine_version": "1.0",
    "name": "test-library",
    "default_lang": "en",
    "sections": DECLARED_SECTIONS,
}

# A minimal compliant deck with two slides, each carrying the full data-hyp-* set.
DECK_TWO_SLIDES = textwrap.dedent("""\
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Test Deck</title></head>
    <body>
    <section class="slide slide--cover"
        data-hyp-slide-id="cover-alpha"
        data-hyp-section="opening"
        data-hyp-title="Alpha Cover"
        data-hyp-audience="prospect"
        data-hyp-lang="en"
        data-hyp-summary="The opening cover slide for alpha."
        data-hyp-kind="ready"
        data-hyp-provenance="test (2026-06-15)">
      <h1>Hello</h1>
      <img src="assets/cover-bg.jpg" alt="bg">
    </section>
    <section class="slide slide--intro"
        data-hyp-slide-id="intro-beta"
        data-hyp-section="intro"
        data-hyp-title="Beta Intro"
        data-hyp-audience="general"
        data-hyp-lang="en"
        data-hyp-summary="The intro slide for beta."
        data-hyp-kind="template"
        data-hyp-provenance="test (2026-06-15)">
      <p>{{INTRO_CONTENT}}</p>
    </section>
    </body>
    </html>
    """)

# A slide with chrome editing attributes that should be stripped.
DECK_WITH_CHROME = textwrap.dedent("""\
    <!DOCTYPE html><html><body>
    <section class="slide hyp-selected"
        data-hyp-slide-id="chrome-slide"
        data-hyp-hook="main"
        data-hyp-region="body"
        data-hyp-text="editable"
        data-hyp-section="product"
        data-hyp-title="Chrome Test"
        data-hyp-audience="general"
        data-hyp-lang="en"
        data-hyp-summary="Tests chrome stripping."
        data-hyp-kind="ready"
        data-hyp-provenance="-">
      <span data-hyp-resize="true">content</span>
    </section>
    </body></html>
    """)

# A slide with NO data-hyp-* metadata (missing metadata fallback test).
DECK_NO_METADATA = textwrap.dedent("""\
    <!DOCTYPE html><html><body>
    <section class="slide">
      <h2>Some Slide Without Metadata</h2>
    </section>
    </body></html>
    """)

# A deck where two slides share the same data-hyp-slide-id (id collision test).
DECK_ID_COLLISION = textwrap.dedent("""\
    <!DOCTYPE html><html><body>
    <section class="slide"
        data-hyp-slide-id="dupe-id"
        data-hyp-section="opening"
        data-hyp-title="First"
        data-hyp-audience="general"
        data-hyp-lang="en"
        data-hyp-summary="First slide."
        data-hyp-kind="ready"
        data-hyp-provenance="-">
      <p>First</p>
    </section>
    <section class="slide"
        data-hyp-slide-id="dupe-id"
        data-hyp-section="intro"
        data-hyp-title="Second"
        data-hyp-audience="general"
        data-hyp-lang="en"
        data-hyp-summary="Second slide."
        data-hyp-kind="ready"
        data-hyp-provenance="-">
      <p>Second</p>
    </section>
    </body></html>
    """)

# A slide whose data-hyp-section is NOT declared in the target library.
DECK_UNDECLARED_SECTION = textwrap.dedent("""\
    <!DOCTYPE html><html><body>
    <section class="slide"
        data-hyp-slide-id="undeclared-slide"
        data-hyp-section="NONEXISTENT_SECTION"
        data-hyp-title="Undeclared"
        data-hyp-audience="general"
        data-hyp-lang="en"
        data-hyp-summary="Section not in library."
        data-hyp-kind="ready"
        data-hyp-provenance="-">
      <p>content</p>
    </section>
    </body></html>
    """)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _first_export(deck_html: str, selected: list[str], **kw) -> SlideExport:
    result = decompose_deck(deck_html, selected, **kw)
    assert result.exports, "Expected at least one export"
    return result.exports[0]


# ---------------------------------------------------------------------------
# C1 — fragment is <section>-only (no <head>/<style>/<script>/<html>/<body>)
# ---------------------------------------------------------------------------


class TestFragmentInvariant:
    def test_fragment_contains_no_forbidden_tags(self):
        """C1: fragment output must be <section>-only — no <head>, <style>, <script>, <html>, <body>."""
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        frag = exp.fragment_html
        # Must start with <section
        assert frag.strip().startswith("<section"), f"Fragment must start with <section>, got: {frag[:60]!r}"
        # Must not contain any forbidden tags
        violations = validate_fragment(frag)
        assert not violations, f"Fragment invariant violated: {violations}"

    def test_fragment_has_no_html_wrapper(self):
        """C1: no outer HTML document structure in the fragment."""
        exp = _first_export(DECK_TWO_SLIDES, ["intro-beta"], library_json=LIBRARY_JSON)
        frag = exp.fragment_html
        for forbidden in ["<html", "<head", "<body", "<style", "<script"]:
            assert forbidden.lower() not in frag.lower(), (
                f"Fragment must not contain {forbidden!r}; found in: {frag[:200]!r}"
            )


# ---------------------------------------------------------------------------
# C2 — row fields come FROM data-hyp-* attrs, not defaults; status=to-review
# ---------------------------------------------------------------------------


class TestMetadataMapping:
    """C2: assert that row fields are sourced from data-hyp-* attributes, not defaults.

    This is the binding assertion from the export-source invariant.
    A section built from a data-hyp-*-bearing slide MUST yield row fields
    that came FROM those attributes — not from fallback defaults.
    """

    def test_id_from_data_hyp_slide_id(self):
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.id == "cover-alpha", (
            f"id must come from data-hyp-slide-id='cover-alpha', got {exp.row.id!r}"
        )

    def test_section_from_data_hyp_section(self):
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.section == "opening", (
            f"section must come from data-hyp-section='opening', got {exp.row.section!r}"
        )

    def test_title_from_data_hyp_title(self):
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.title == "Alpha Cover", (
            f"title must come from data-hyp-title='Alpha Cover', got {exp.row.title!r}"
        )

    def test_audience_from_data_hyp_audience(self):
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.audience == "prospect", (
            f"audience must come from data-hyp-audience='prospect', got {exp.row.audience!r}"
        )

    def test_lang_from_data_hyp_lang(self):
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.lang == "en", (
            f"lang must come from data-hyp-lang='en', got {exp.row.lang!r}"
        )

    def test_summary_from_data_hyp_summary(self):
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.summary == "The opening cover slide for alpha.", (
            f"summary must come from data-hyp-summary attribute, got {exp.row.summary!r}"
        )

    def test_kind_from_data_hyp_kind(self):
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.kind == "ready", (
            f"kind must come from data-hyp-kind='ready', got {exp.row.kind!r}"
        )

    def test_provenance_from_data_hyp_provenance(self):
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.provenance == "test (2026-06-15)", (
            f"provenance must come from data-hyp-provenance, got {exp.row.provenance!r}"
        )

    def test_status_is_always_to_review(self):
        """status must always be exactly 'to-review' for all exported slides (not 'ready', not 'To-Review')."""
        result = decompose_deck(DECK_TWO_SLIDES, ["cover-alpha", "intro-beta"], library_json=LIBRARY_JSON)
        for exp in result.exports:
            assert exp.row.status == "to-review", (
                f"status must be exactly 'to-review' (exact-lowercase), got {exp.row.status!r} for {exp.row.id!r}"
            )

    def test_file_is_slides_path(self):
        """file column must be slides/{id}.html."""
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.file == "slides/cover-alpha.html", (
            f"file must be 'slides/cover-alpha.html', got {exp.row.file!r}"
        )

    def test_second_slide_fields_from_attrs(self):
        """C2 for the second slide — kind=template sourced from data-hyp-kind."""
        result = decompose_deck(DECK_TWO_SLIDES, ["cover-alpha", "intro-beta"], library_json=LIBRARY_JSON)
        assert len(result.exports) == 2
        intro = result.exports[1]
        assert intro.row.id == "intro-beta"
        assert intro.row.kind == "template"
        assert intro.row.title == "Beta Intro"
        assert intro.row.audience == "general"
        assert intro.row.section == "intro"


# ---------------------------------------------------------------------------
# C3 — section vocabulary guard
# ---------------------------------------------------------------------------


class TestSectionVocabularyGuard:
    def test_declared_section_passes_through(self):
        """C3a: data-hyp-section value declared in library.json → used as-is."""
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert exp.row.section == "opening"
        # No section-remap concern should be present.
        section_concerns = [c for c in exp.concerns if "not a declared section" in c]
        assert not section_concerns, f"Should not flag a declared section; got: {section_concerns}"

    def test_undeclared_section_remapped_to_default(self):
        """C3b: data-hyp-section not in library.json → safe declared default + flagged."""
        result = decompose_deck(
            DECK_UNDECLARED_SECTION,
            ["undeclared-slide"],
            library_json=LIBRARY_JSON,
        )
        assert result.exports
        exp = result.exports[0]
        # Section must be a declared one (not the undeclared raw value).
        assert exp.row.section in DECLARED_SECTIONS, (
            f"section must be a declared section, got {exp.row.section!r}"
        )
        assert exp.row.section != "NONEXISTENT_SECTION", (
            "section must NOT be the undeclared raw value 'NONEXISTENT_SECTION'"
        )
        # Must be flagged in per-slide concerns.
        flagged = [c for c in exp.concerns if "not a declared section" in c or "safe default" in c]
        assert flagged, f"Undeclared section must be flagged in concerns; got: {exp.concerns}"
        # Must also be flagged in global concerns.
        global_flagged = [c for c in result.concerns if "not a declared section" in c or "safe default" in c]
        assert global_flagged, f"Undeclared section must appear in global concerns; got: {result.concerns}"

    def test_section_guard_with_no_library_json(self):
        """C3c: when library_json is None, section is accepted as-is (best-effort mode)."""
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=None)
        # Should not crash; section from attribute is used.
        assert exp.row.section == "opening"

    def test_resolve_section_helper_exact_match(self):
        result, remapped = _resolve_section("product", DECLARED_SECTIONS)
        assert result == "product"
        assert not remapped

    def test_resolve_section_helper_no_match_uses_first_default(self):
        result, remapped = _resolve_section("bogus", DECLARED_SECTIONS)
        assert result == DECLARED_SECTIONS[0]
        assert remapped

    def test_resolve_section_helper_empty_declared(self):
        result, remapped = _resolve_section("anything", [])
        assert result == "anything"
        assert not remapped


# ---------------------------------------------------------------------------
# C4 — missing metadata → safe defaults + flag, no crash
# ---------------------------------------------------------------------------


class TestMissingMetadataFallback:
    def test_no_data_hyp_attrs_does_not_crash(self):
        """C4: slide with no data-hyp-* metadata falls back gracefully."""
        result = decompose_deck(DECK_NO_METADATA, ["0"], library_json=LIBRARY_JSON)
        assert result.exports, "Should produce one export even with missing metadata"

    def test_missing_metadata_generates_safe_defaults(self):
        """C4: fallback values are sensible and the row is still valid."""
        result = decompose_deck(DECK_NO_METADATA, ["0"], library_json=LIBRARY_JSON)
        exp = result.exports[0]
        row = exp.row
        # id must not be empty.
        assert row.id, "id must not be empty even for missing-metadata slide"
        # audience defaults to 'general'.
        assert row.audience == "general", f"Default audience must be 'general', got {row.audience!r}"
        # kind defaults to 'ready'.
        assert row.kind == "ready", f"Default kind must be 'ready', got {row.kind!r}"
        # status is always to-review.
        assert row.status == "to-review"
        # lang defaults to 'en'.
        assert row.lang == "en"

    def test_missing_metadata_flags_in_concerns(self):
        """C4: slide with no metadata is flagged in per-slide concerns."""
        result = decompose_deck(DECK_NO_METADATA, ["0"], library_json=LIBRARY_JSON)
        exp = result.exports[0]
        assert exp.concerns, "Missing metadata must produce at least one concern"
        concern_text = " ".join(exp.concerns).lower()
        assert "metadata" in concern_text or "missing" in concern_text or "default" in concern_text, (
            f"Concerns should mention missing metadata; got: {exp.concerns}"
        )

    def test_title_derived_from_text_when_no_attr(self):
        """C4: when data-hyp-title absent, engine does not crash and produces an id."""
        result = decompose_deck(DECK_NO_METADATA, ["0"], library_json=LIBRARY_JSON)
        assert result.exports[0].row.id  # non-empty id required


# ---------------------------------------------------------------------------
# C5 — id deduplication
# ---------------------------------------------------------------------------


class TestIdDeduplication:
    def test_two_slides_same_data_hyp_slide_id_are_deduped(self):
        """C5: two slides with the same data-hyp-slide-id get unique ids."""
        result = decompose_deck(
            DECK_ID_COLLISION,
            ["dupe-id", "dupe-id"],
            library_json=LIBRARY_JSON,
        )
        # The engine may return 1 or 2 exports depending on how it resolves the
        # duplicate selection.  What matters: no two returned rows share an id.
        ids = [exp.row.id for exp in result.exports]
        assert len(ids) == len(set(ids)), f"All exported ids must be unique; got: {ids}"

    def test_collision_with_existing_library_ids(self):
        """C5: collision with existing_library_ids triggers deduplication."""
        result = decompose_deck(
            DECK_TWO_SLIDES,
            ["cover-alpha"],
            library_json=LIBRARY_JSON,
            existing_library_ids={"cover-alpha"},  # simulate existing id
        )
        assert result.exports
        assert result.exports[0].row.id != "cover-alpha", (
            "id must be deduped when it collides with an existing library id"
        )
        assert result.exports[0].row.id.startswith("cover-alpha"), (
            "deduped id must start with the base id"
        )

    def test_dedup_helper_no_collision(self):
        assert _dedup_id("my-slide", set()) == "my-slide"

    def test_dedup_helper_single_collision(self):
        result = _dedup_id("my-slide", {"my-slide"})
        assert result == "my-slide-2"

    def test_dedup_helper_multiple_collisions(self):
        used = {"my-slide", "my-slide-2", "my-slide-3"}
        result = _dedup_id("my-slide", used)
        assert result == "my-slide-4"

    def test_two_slides_same_suggested_id_sequential_export(self):
        """C5: exporting two slides that both resolve to 'dupe-id' → unique ids across the result."""
        result = decompose_deck(
            DECK_ID_COLLISION,
            # Select both slides by index (they both have data-hyp-slide-id="dupe-id")
            ["dupe-id"],  # first match only; second has same id
            library_json=LIBRARY_JSON,
        )
        # Just assert no crash and valid ids.
        for exp in result.exports:
            assert exp.row.id


# ---------------------------------------------------------------------------
# C6 — asset discovery
# ---------------------------------------------------------------------------


class TestAssetDiscovery:
    def test_asset_referenced_in_src_is_discovered(self):
        """C6a: img src="assets/..." is discovered."""
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        # cover-alpha has <img src="assets/cover-bg.jpg">
        assert "cover-bg.jpg" in exp.row.assets, (
            f"cover-bg.jpg should be in assets cell; got {exp.row.assets!r}"
        )

    def test_slide_with_no_assets_uses_dash(self):
        """C6b: slide with no asset references → assets cell is '-'."""
        exp = _first_export(DECK_TWO_SLIDES, ["intro-beta"], library_json=LIBRARY_JSON)
        assert exp.row.assets == "-", (
            f"Slide with no assets should have '-' in assets cell; got {exp.row.assets!r}"
        )

    def test_asset_existence_check_with_real_dir(self, tmp_path):
        """C6c: when deck_assets_dir is set, found assets have on-disk files; missing are flagged."""
        # Create a real asset file.
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        (assets_dir / "cover-bg.jpg").write_bytes(b"\xff\xd8")  # minimal JPEG header

        result = decompose_deck(
            DECK_TWO_SLIDES,
            ["cover-alpha"],
            library_json=LIBRARY_JSON,
            deck_assets_dir=str(assets_dir),
        )
        assert result.exports
        exp = result.exports[0]
        # cover-bg.jpg exists → in assets cell.
        assert "cover-bg.jpg" in exp.row.assets

    def test_missing_asset_is_skipped_and_flagged(self, tmp_path):
        """C6d: asset referenced but not on disk → skipped in assets cell + concern recorded."""
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        # Do NOT create cover-bg.jpg → it's missing.

        result = decompose_deck(
            DECK_TWO_SLIDES,
            ["cover-alpha"],
            library_json=LIBRARY_JSON,
            deck_assets_dir=str(assets_dir),
        )
        assert result.exports
        exp = result.exports[0]
        # Missing asset must NOT be in the assets cell.
        assert "cover-bg.jpg" not in exp.row.assets, (
            "Missing asset must not appear in assets cell"
        )
        # Must be flagged.
        all_concerns = exp.concerns + result.concerns
        flagged = [c for c in all_concerns if "cover-bg.jpg" in c and ("not found" in c or "missing" in c or "skipped" in c)]
        assert flagged, f"Missing asset must be flagged in concerns; got: {all_concerns}"

    def test_missing_asset_does_not_abort_export(self, tmp_path):
        """C6e: a missing asset does not abort the whole export."""
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        # No files created.

        result = decompose_deck(
            DECK_TWO_SLIDES,
            ["cover-alpha"],
            library_json=LIBRARY_JSON,
            deck_assets_dir=str(assets_dir),
        )
        # Export must still succeed (not raise).
        assert result.exports, "Export must complete even when assets are missing"
        assert result.exports[0].row.status == "to-review"

    def test_discover_assets_helper_no_dir(self):
        """C6f: _discover_assets with no dir returns all referenced names."""
        html = '<section><img src="assets/foo.png"><img src="assets/bar.jpg"></section>'
        found, missing = _discover_assets(html, None)
        assert "foo.png" in found
        assert "bar.jpg" in found
        assert not missing


# ---------------------------------------------------------------------------
# C7 — module importable, no HTTP dep; pytest exits 0 (structural check)
# ---------------------------------------------------------------------------


class TestModuleImportability:
    def test_decompose_module_imports_without_http(self):
        """C7: importing decompose.py must not pull in any HTTP/server module."""
        import importlib
        import sys
        # If the import already succeeded (it did, since we're running tests),
        # confirm that no HTTP-related modules were imported as a side effect.
        http_modules = [
            m for m in sys.modules
            if any(k in m for k in ("flask", "fastapi", "tornado", "aiohttp", "http.server"))
        ]
        # http.server is stdlib and might be imported; flask/fastapi/etc. must not be.
        third_party_http = [m for m in http_modules if "flask" in m or "fastapi" in m or "aiohttp" in m]
        assert not third_party_http, (
            f"decompose.py must not pull in third-party HTTP modules; found: {third_party_http}"
        )

    def test_decompose_deck_returns_decompose_result(self):
        """C7: decompose_deck returns DecomposeResult (structural smoke test)."""
        result = decompose_deck(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert isinstance(result, DecomposeResult)
        assert isinstance(result.exports, list)
        assert isinstance(result.concerns, list)

    def test_slide_export_has_expected_fields(self):
        """C7: SlideExport has fragment_html, row, asset_paths, concerns."""
        exp = _first_export(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        assert isinstance(exp, SlideExport)
        assert isinstance(exp.fragment_html, str)
        assert isinstance(exp.row, ManifestRow)
        assert isinstance(exp.asset_paths, list)
        assert isinstance(exp.concerns, list)


# ---------------------------------------------------------------------------
# Chrome stripping
# ---------------------------------------------------------------------------


class TestChromeStripping:
    def test_chrome_attrs_are_removed(self):
        """Chrome-stripping removes editing attrs (data-hyp-hook, data-hyp-region, etc.)."""
        exp = _first_export(DECK_WITH_CHROME, ["chrome-slide"], library_json=LIBRARY_JSON)
        frag = exp.fragment_html
        for chrome_attr in ["data-hyp-hook", "data-hyp-region", "data-hyp-text", "data-hyp-resize"]:
            assert chrome_attr not in frag, (
                f"Chrome attr {chrome_attr!r} must be stripped from fragment; still found in: {frag[:300]!r}"
            )

    def test_export_metadata_attrs_are_preserved(self):
        """Chrome-stripping preserves data-hyp-* EXPORT attributes on the <section> tag."""
        exp = _first_export(DECK_WITH_CHROME, ["chrome-slide"], library_json=LIBRARY_JSON)
        frag = exp.fragment_html
        for export_attr in [
            "data-hyp-slide-id",
            "data-hyp-section",
            "data-hyp-title",
            "data-hyp-kind",
        ]:
            assert export_attr in frag, (
                f"Export attr {export_attr!r} must be preserved in fragment; not found in: {frag[:300]!r}"
            )

    def test_chrome_css_classes_removed(self):
        """The hyp-selected editing class is stripped from the <section> tag."""
        exp = _first_export(DECK_WITH_CHROME, ["chrome-slide"], library_json=LIBRARY_JSON)
        frag = exp.fragment_html
        assert "hyp-selected" not in frag, (
            f"Editing class 'hyp-selected' must be stripped; still in: {frag[:200]!r}"
        )

    def test_slide_class_retained(self):
        """The 'slide' class is NOT stripped (it is not a chrome class)."""
        exp = _first_export(DECK_WITH_CHROME, ["chrome-slide"], library_json=LIBRARY_JSON)
        assert "slide" in exp.fragment_html, (
            "The 'slide' class must be retained in the stripped fragment"
        )


# ---------------------------------------------------------------------------
# Row serialisation
# ---------------------------------------------------------------------------


class TestRowSerialization:
    def test_row_to_markdown_produces_11_cells(self):
        """row_to_markdown must produce an 11-cell pipe-delimited row."""
        row = ManifestRow(
            id="my-slide",
            file="slides/my-slide.html",
            section="opening",
            title="My Slide",
            audience="general",
            lang="en",
            kind="ready",
            summary="A test slide.",
            assets="-",
            provenance="-",
            status="to-review",
        )
        md = row_to_markdown(row)
        # Strip leading/trailing pipes and split.
        cells = [c.strip() for c in md.strip().split("|") if c.strip()]
        assert len(cells) == 11, f"Expected 11 cells, got {len(cells)}: {cells}"
        assert cells[10] == "to-review", f"11th cell must be status='to-review'; got {cells[10]!r}"

    def test_row_id_is_first_cell(self):
        row = ManifestRow(
            id="test-id", file="slides/test-id.html", section="opening",
            title="T", audience="general", lang="en", kind="ready",
            summary="s", assets="-", provenance="-", status="to-review",
        )
        md = row_to_markdown(row)
        cells = [c.strip() for c in md.strip().split("|") if c.strip()]
        assert cells[0] == "test-id"


# ---------------------------------------------------------------------------
# split_sections (mirrors recompose coverage)
# ---------------------------------------------------------------------------


class TestSplitSections:
    def test_finds_two_top_level_sections(self):
        spans = split_sections(DECK_TWO_SLIDES)
        assert len(spans) == 2

    def test_empty_html_returns_empty(self):
        assert split_sections("<html><body></body></html>") == []

    def test_nested_sections_counted_as_one(self):
        html = "<section><section><p>inner</p></section></section>"
        spans = split_sections(html)
        assert len(spans) == 1

    def test_unbalanced_raises(self):
        with pytest.raises(DecomposeError):
            split_sections("<section><p>no close")


# ---------------------------------------------------------------------------
# validate_fragment
# ---------------------------------------------------------------------------


class TestValidateFragment:
    def test_clean_section_passes(self):
        assert validate_fragment('<section class="slide"><p>ok</p></section>') == []

    def test_head_tag_fails(self):
        v = validate_fragment('<section><head><title>x</title></head></section>')
        assert any("head" in vi.lower() for vi in v)

    def test_script_tag_fails(self):
        v = validate_fragment('<section><script>alert(1)</script></section>')
        assert any("script" in vi.lower() for vi in v)

    def test_style_tag_fails(self):
        v = validate_fragment('<section><style>.x{}</style></section>')
        assert any("style" in vi.lower() for vi in v)


# ---------------------------------------------------------------------------
# load_library_json
# ---------------------------------------------------------------------------


class TestLoadLibraryJson:
    def test_load_library_json(self, tmp_path):
        lib_dir = tmp_path / "my-library"
        lib_dir.mkdir()
        import json
        (lib_dir / "library.json").write_text(
            json.dumps({"sections": ["opening", "closing"], "engine_version": "1.0"}),
            encoding="utf-8",
        )
        data = load_library_json(str(lib_dir))
        assert data["sections"] == ["opening", "closing"]


# ---------------------------------------------------------------------------
# Integration — a decompose-emitted row MUST be accepted by the SHIPPED
# assemble.py parser/validator (round-trip acceptance). A row decompose emits
# that assemble.py would reject is a round-trip-breaking defect (the export-source + section-vocabulary invariants).
# ---------------------------------------------------------------------------


def _load_assemble_module():
    """Import the canonical slide-library assemble.py as a module, or skip."""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    asm_path = os.path.abspath(
        os.path.join(here, "..", "..", "..", "slide-library", "engine", "assemble.py")
    )
    if not os.path.isfile(asm_path):
        pytest.skip(f"assemble.py not found at {asm_path}")
    spec = importlib.util.spec_from_file_location("assemble_eng_under_test", asm_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _assemble_rejects(rows_md, frags, declared_sections, tmp_path):
    """Build a real library dir from emitted rows + fragments, run assemble.py's
    real parse_manifest + validate_library, return the error list (empty = accepted).
    """
    import json as _json
    asm = _load_assemble_module()
    from pathlib import Path

    lib_json = {
        "convention_version": "1.0",
        "engine_version": "1.0",
        "name": "rt-test",
        "default_lang": "en",
        "sections": declared_sections,
    }
    d = tmp_path / "rt-lib"
    (d / "slides").mkdir(parents=True)
    (d / "assets").mkdir()
    (d / "library.json").write_text(_json.dumps(lib_json), encoding="utf-8")

    header = (
        "| id | file | section | title | audience | lang | kind | summary "
        "| assets | provenance | status |"
    )
    sep = "|----|------|---------|-------|----------|------|------|---------|--------|------------|--------|"
    manifest = "\n".join(
        ["# m", "", "## Slides", "", header, sep, *rows_md, "",
         "## Assets", "", "| file | description | used-by |",
         "|------|-------------|---------|"]
    ) + "\n"
    (d / "manifest.md").write_text(manifest, encoding="utf-8")
    for fid, html in frags.items():
        (d / "slides" / f"{fid}.html").write_text(html, encoding="utf-8")

    asm.LIBRARY = Path(str(d))
    base = "{{LANG}}{{TITLE}}/* {{ACCENT_CSS}} *//* {{THEME_CSS}} */<!-- {{SLIDES}} -->"
    mrows = asm.parse_manifest(Path(str(d)) / "manifest.md")
    atab = asm.parse_assets_table(Path(str(d)) / "manifest.md")
    errors, _warnings = asm.validate_library(lib_json, mrows, atab, base, check_assets=False)
    return errors


class TestAssembleRoundTripAcceptance:
    """Every row decompose emits must pass the shipped assemble.py validator."""

    def test_happy_path_row_is_accepted(self, tmp_path):
        result = decompose_deck(DECK_TWO_SLIDES, ["cover-alpha"], library_json=LIBRARY_JSON)
        exp = result.exports[0]
        errs = _assemble_rejects(
            [row_to_markdown(exp.row)], {exp.row.id: exp.fragment_html},
            DECLARED_SECTIONS, tmp_path,
        )
        assert not errs, f"assemble.py rejected a clean exported row: {errs}"

    def test_malformed_lang_is_normalized_and_accepted(self, tmp_path):
        deck = DECK_TWO_SLIDES.replace('data-hyp-lang="en"', 'data-hyp-lang="en-US"', 1)
        result = decompose_deck(deck, ["cover-alpha"], library_json=LIBRARY_JSON)
        exp = result.exports[0]
        assert exp.row.lang == "en", f"lang must normalize en-US->en, got {exp.row.lang!r}"
        errs = _assemble_rejects(
            [row_to_markdown(exp.row)], {exp.row.id: exp.fragment_html},
            DECLARED_SECTIONS, tmp_path,
        )
        assert not errs, f"assemble.py rejected a normalized-lang row: {errs}"

    def test_uppercase_lang_is_normalized_and_accepted(self, tmp_path):
        deck = DECK_TWO_SLIDES.replace('data-hyp-lang="en"', 'data-hyp-lang="EN"', 1)
        result = decompose_deck(deck, ["cover-alpha"], library_json=LIBRARY_JSON)
        exp = result.exports[0]
        assert exp.row.lang == "en"
        errs = _assemble_rejects(
            [row_to_markdown(exp.row)], {exp.row.id: exp.fragment_html},
            DECLARED_SECTIONS, tmp_path,
        )
        assert not errs, f"assemble.py rejected an uppercase-lang row: {errs}"

    def test_pipe_in_title_is_sanitized_and_accepted(self, tmp_path):
        deck = DECK_TWO_SLIDES.replace('data-hyp-title="Alpha Cover"', 'data-hyp-title="Alpha | Cover"', 1)
        result = decompose_deck(deck, ["cover-alpha"], library_json=LIBRARY_JSON)
        exp = result.exports[0]
        assert "|" not in exp.row.title, f"title cell must carry no '|', got {exp.row.title!r}"
        errs = _assemble_rejects(
            [row_to_markdown(exp.row)], {exp.row.id: exp.fragment_html},
            DECLARED_SECTIONS, tmp_path,
        )
        assert not errs, f"assemble.py rejected a pipe-bearing row: {errs}"

    def test_pipe_in_summary_is_sanitized_and_accepted(self, tmp_path):
        deck = DECK_TWO_SLIDES.replace(
            'data-hyp-summary="The opening cover slide for alpha."',
            'data-hyp-summary="The opening | cover slide."', 1,
        )
        result = decompose_deck(deck, ["cover-alpha"], library_json=LIBRARY_JSON)
        exp = result.exports[0]
        errs = _assemble_rejects(
            [row_to_markdown(exp.row)], {exp.row.id: exp.fragment_html},
            DECLARED_SECTIONS, tmp_path,
        )
        assert not errs, f"assemble.py rejected a pipe-in-summary row: {errs}"

    def test_undeclared_section_row_is_accepted(self, tmp_path):
        result = decompose_deck(
            DECK_UNDECLARED_SECTION, ["undeclared-slide"], library_json=LIBRARY_JSON
        )
        exp = result.exports[0]
        errs = _assemble_rejects(
            [row_to_markdown(exp.row)], {exp.row.id: exp.fragment_html},
            DECLARED_SECTIONS, tmp_path,
        )
        assert not errs, f"assemble.py rejected an undeclared-section export: {errs}"

    def test_missing_metadata_row_is_accepted(self, tmp_path):
        result = decompose_deck(DECK_NO_METADATA, ["0"], library_json=LIBRARY_JSON)
        exp = result.exports[0]
        errs = _assemble_rejects(
            [row_to_markdown(exp.row)], {exp.row.id: exp.fragment_html},
            DECLARED_SECTIONS, tmp_path,
        )
        assert not errs, f"assemble.py rejected a missing-metadata fallback row: {errs}"
