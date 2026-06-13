import os
import sys
import shutil
import tempfile
import pathlib
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8811
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DECK_FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html")


class PB11DeckSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        H.stop_server(cls.proc)

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 720})

    def tearDown(self):
        self.page.close()

    def _copy_deck(self):
        """Return the absolute path of a temp copy of the test deck."""
        d = tempfile.mkdtemp()
        dst = os.path.join(d, "deck.html")
        shutil.copy(DECK_FIXTURE, dst)
        return dst

    def _open_deck(self, deck_path):
        """Open a deck via the dialog and wait for tray to populate."""
        H.set_fake_dialog(self.base, deck_path)
        self.page.goto(self.base + "/app/builder.html")
        self.page.click("#open-deck-btn")
        self.page.wait_for_selector(".tray-row", timeout=10000)

    def _pick_lib(self):
        """Pick the e2e fixture library."""
        lib = B.e2e_lib_path()
        B.pick_library_ui(self.page, self.base, lib)
        return lib

    def _tray_count(self):
        return self.page.eval_on_selector_all(".tray-row", "els=>els.length")

    def _tray_kinds(self):
        return self.page.eval_on_selector_all(
            ".tray-row",
            "els=>els.map(e=>e.querySelector('.tray-badge').textContent)"
        )

    def _deck_chip_name(self):
        return self.page.locator("#deck-chip-name").text_content()

    # ── PB11-1: new-file save with full restructure + reopen intact ────────
    def test_new_file_save(self):
        # Guard: record root deck bytes BEFORE anything
        root_bytes = pathlib.Path(DECK_FIXTURE).read_bytes()

        deck_path = self._copy_deck()
        self._open_deck(deck_path)
        self.assertEqual(self._tray_count(), 10, "deck should have 10 slides")

        # Remove slide 3 (third row)
        self.page.locator(".tray-row:nth-child(3) .tray-remove").click()
        self.page.wait_for_timeout(150)
        self.assertEqual(self._tray_count(), 9)

        # Duplicate first row
        self.page.click(".tray-row:nth-child(1) .tray-duplicate")
        self.page.wait_for_timeout(150)
        self.assertEqual(self._tray_count(), 10)

        # Add blank
        self.page.click("#add-blank-btn")
        self.page.wait_for_timeout(100)
        self.assertEqual(self._tray_count(), 11)

        # Add library slide
        lib = self._pick_lib()
        card_ids = self.page.eval_on_selector_all(".slide-card", "els=>els.map(e=>e.dataset.slideId)")
        self.assertTrue(len(card_ids) >= 1, "fixture needs at least 1 library card")
        added_slide_id = card_ids[0]
        self.page.click(f".slide-card[data-slide-id='{added_slide_id}']")
        self.page.wait_for_timeout(100)
        self.assertEqual(self._tray_count(), 12)
        # Resolve the exact fragment markup we expect to be spliced (for the disk proof).
        added_fragment = pathlib.Path(
            os.path.join(lib, "slides", added_slide_id + ".html")
        ).read_text(encoding="utf-8")

        # Save as new-file — inject the dialog path
        save_dir = tempfile.mkdtemp()
        save_path = os.path.join(save_dir, "saved-deck.html")
        H.set_fake_dialog(self.base, save_path)
        self.page.click("#save-new-btn")

        # Wait for success status
        self.page.wait_for_selector(".shell-status.success", timeout=10000)
        status_text = self.page.locator("#builder-status").text_content()
        self.assertIn("Saved:", status_text)

        # Saved file must exist
        self.assertTrue(os.path.exists(save_path), "saved file must exist")

        # ── prove the restructure on disk (count alone cannot — sections survive
        #    recompose byte-for-byte, so order/removal/duplication ARE verifiable) ──
        sys.path.insert(0, os.path.join(REPO, "server"))
        from recompose import split_sections  # noqa: E402
        saved_html = pathlib.Path(save_path).read_bytes().decode("utf-8")
        saved_spans = split_sections(saved_html)
        self.assertEqual(len(saved_spans), 12, "saved file must hold 12 sections")
        saved_secs = [saved_html[s:e] for s, e in saved_spans]
        # Removal: the dropped slide (source index 2, unique kicker) must be absent.
        self.assertNotIn(
            "Baseado na conversa", saved_html,
            "removed slide 3 (index 2) must not appear in the saved deck"
        )
        # Duplication + order: the cover (source index 0) was duplicated to the front,
        # so the first TWO sections are both the cover (positional proof, not a count).
        self.assertIn("slide--cover", saved_secs[0], "first section must be the cover")
        self.assertIn("slide--cover", saved_secs[1], "second section must be the cover duplicate")
        # The duplicate is the deck's OWN cover markup, byte-identical to section 0.
        self.assertEqual(
            saved_secs[0], saved_secs[1],
            "duplicated cover must be byte-identical to the original cover section"
        )
        # Added blank present as a marker-free <section> (recompose BLANK_SECTION).
        self.assertEqual(
            sum(1 for sec in saved_secs if "Blank Slide" in sec), 1,
            "exactly one blank section must be present"
        )
        # The added library fragment landed last (added after the blank in this flow)
        # and was spliced verbatim — its <section> span must appear in the saved deck.
        frag_spans = split_sections(added_fragment)
        self.assertEqual(len(frag_spans), 1, "fixture fragment is a single section")
        fs, fe = frag_spans[0]
        # Verbatim modulo platform line-endings (write normalizes EOL; markup unchanged).
        self.assertEqual(
            saved_secs[-1].replace("\r\n", "\n"), added_fragment[fs:fe].replace("\r\n", "\n"),
            "last saved section must be the spliced library fragment, verbatim"
        )
        # Saved deck stays clean: no hyp- markers leaked (decisions.md clean-output rule).
        self.assertNotIn("data-hyp-", saved_html, "saved deck must carry no data-hyp-* markers")

        # ── reopen the saved file and verify tray reflects the restructure ──
        self.page.goto(self.base + "/app/builder.html")
        H.set_fake_dialog(self.base, save_path)
        self.page.click("#open-deck-btn")
        self.page.wait_for_selector(".tray-row", timeout=10000)

        self.assertEqual(self._tray_count(), 12, "reopened saved deck should have 12 slides")
        kinds = self._tray_kinds()
        # After save+reopen, ALL sections appear as "deck" kind because recompose
        # writes blanks and library fragments as plain <section> elements; the
        # deck loader treats every <section> as an existing deck slide.
        self.assertEqual(len(kinds), 12, "all 12 sections should be present")
        self.assertTrue(all(k == "deck" for k in kinds), "all rows should be deck kind after reopen")

        # Root deck must be byte-unchanged
        self.assertEqual(
            pathlib.Path(DECK_FIXTURE).read_bytes(), root_bytes,
            "root deck must be byte-unchanged after new-file save"
        )

    # ── PB11-1a: own asset copied beside save-to-new-dir deck ─────────────
    def test_new_file_save_colocates_preserved_own_asset(self):
        sys.path.insert(0, os.path.join(REPO, "server"))
        from recompose import split_sections  # noqa: E402

        deck_path = self._copy_deck()
        deck_dir = pathlib.Path(deck_path).parent
        rel_asset = "assets/own-e2e.txt"
        asset_bytes = b"pb11 own asset colocation\n"
        asset_path = deck_dir / rel_asset
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(asset_bytes)

        deck_html = pathlib.Path(deck_path).read_text(encoding="utf-8")
        spans = split_sections(deck_html)
        self.assertTrue(spans, "fixture deck must contain sections")
        first_start, first_end = spans[0]
        first_section = deck_html[first_start:first_end]
        own_ref = '<a class="pb11-own-asset" href="assets/own-e2e.txt">own asset</a>'
        self.assertIn("</section>", first_section, "first section must be closed")
        first_section = first_section.replace("</section>", own_ref + "</section>", 1)
        deck_html = deck_html[:first_start] + first_section + deck_html[first_end:]
        pathlib.Path(deck_path).write_text(deck_html, encoding="utf-8")

        self._open_deck(deck_path)
        self.assertEqual(self._tray_count(), 10, "deck should have 10 slides")

        # Remove a later slide so the deck is restructured while preserving slide 1,
        # which carries the own asset reference.
        self.page.locator(".tray-row:nth-child(3) .tray-remove").click()
        self.page.wait_for_timeout(150)
        self.assertEqual(self._tray_count(), 9)

        save_dir = tempfile.mkdtemp()
        save_path = os.path.join(save_dir, "saved-own-asset.html")
        H.set_fake_dialog(self.base, save_path)
        self.page.click("#save-new-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)

        saved_asset_path = pathlib.Path(save_dir) / rel_asset
        self.assertTrue(saved_asset_path.exists(), "own asset must be copied beside saved deck")
        self.assertEqual(
            saved_asset_path.read_bytes(), asset_bytes,
            "copied own asset bytes must match the source asset"
        )

        saved_html = pathlib.Path(save_path).read_text(encoding="utf-8")
        self.assertIn(
            'href="assets/own-e2e.txt"', saved_html,
            "non-colliding own asset ref should remain unchanged"
        )

    # ── PB11-1b: colliding own asset renamed + surfaced in status bar ──────
    def test_new_file_save_surfaces_renamed_own_asset(self):
        sys.path.insert(0, os.path.join(REPO, "server"))
        from recompose import split_sections  # noqa: E402

        deck_path = self._copy_deck()
        deck_dir = pathlib.Path(deck_path).parent
        rel_asset = "assets/logo.png"
        asset_path = deck_dir / rel_asset
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(b"pb11 own asset to be renamed\n")

        deck_html = pathlib.Path(deck_path).read_text(encoding="utf-8")
        spans = split_sections(deck_html)
        self.assertTrue(spans, "fixture deck must contain sections")
        first_start, first_end = spans[0]
        first_section = deck_html[first_start:first_end]
        own_ref = '<img class="pb11-own-asset" src="assets/logo.png">'
        self.assertIn("</section>", first_section, "first section must be closed")
        first_section = first_section.replace("</section>", own_ref + "</section>", 1)
        deck_html = deck_html[:first_start] + first_section + deck_html[first_end:]
        pathlib.Path(deck_path).write_text(deck_html, encoding="utf-8")

        self._open_deck(deck_path)
        self.assertEqual(self._tray_count(), 10, "deck should have 10 slides")

        # Restructure while preserving slide 1 (carries the own-asset ref).
        self.page.locator(".tray-row:nth-child(3) .tray-remove").click()
        self.page.wait_for_timeout(150)
        self.assertEqual(self._tray_count(), 9)

        # Pre-seed a DIFFERENT file at the destination asset path so the save
        # must rename the deck's own asset to avoid clobbering it.
        save_dir = tempfile.mkdtemp()
        existing = pathlib.Path(save_dir) / rel_asset
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_bytes(b"pre-existing unrelated asset\n")

        save_path = os.path.join(save_dir, "saved-renamed-asset.html")
        H.set_fake_dialog(self.base, save_path)
        self.page.click("#save-new-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)

        status_text = self.page.locator("#builder-status").text_content()
        self.assertIn(
            "Renamed: assets/logo.png → assets/logo-1.png", status_text,
            "status bar must surface the colliding-asset rename"
        )
        # Renamed copy landed; the pre-existing file was not clobbered.
        self.assertEqual(
            (pathlib.Path(save_dir) / "assets" / "logo-1.png").read_bytes(),
            b"pb11 own asset to be renamed\n",
        )
        self.assertEqual(existing.read_bytes(), b"pre-existing unrelated asset\n")

    # ── PB11-2: overwrite save + reopen intact ─────────────────────────────
    def test_overwrite_save(self):
        root_bytes = pathlib.Path(DECK_FIXTURE).read_bytes()

        deck_path = self._copy_deck()
        self._open_deck(deck_path)
        self.assertEqual(self._tray_count(), 10)

        # Remove slide 5
        self.page.locator(".tray-row:nth-child(5) .tray-remove").click()
        self.page.wait_for_timeout(150)
        self.assertEqual(self._tray_count(), 9)

        # Overwrite (writes to state.deck.path = deck_path)
        self.page.click("#save-overwrite-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)

        # Reopen the overwritten deck
        self.page.goto(self.base + "/app/builder.html")
        H.set_fake_dialog(self.base, deck_path)
        self.page.click("#open-deck-btn")
        self.page.wait_for_selector(".tray-row", timeout=10000)

        self.assertEqual(self._tray_count(), 9, "reopened overwritten deck should have 9 slides")

        # Root deck unchanged
        self.assertEqual(
            pathlib.Path(DECK_FIXTURE).read_bytes(), root_bytes,
            "root deck must be byte-unchanged after overwrite"
        )

    # ── PB11-3: save disabled when tray empty ─────────────────────────────
    def test_save_disabled_empty_tray(self):
        deck_path = self._copy_deck()
        self._open_deck(deck_path)
        self.assertEqual(self._tray_count(), 10)

        # Remove all rows
        while self._tray_count() > 0:
            self.page.locator(".tray-row:first-child .tray-remove").click()
            self.page.wait_for_timeout(100)

        self.assertEqual(self._tray_count(), 0)

        # Save buttons should be disabled
        new_disabled = self.page.get_attribute("#save-new-btn", "disabled")
        overwrite_disabled = self.page.get_attribute("#save-overwrite-btn", "disabled")
        self.assertIsNotNone(new_disabled, "New file button should be disabled when tray empty")
        self.assertIsNotNone(overwrite_disabled, "Overwrite button should be disabled when tray empty")

    # ── PB11-4: cancel new-file dialog → no write, no error ───────────────
    def test_cancel_new_file_no_write(self):
        deck_path = self._copy_deck()
        self._open_deck(deck_path)

        # Set dialog to None (cancel)
        H.set_fake_dialog(self.base, None)
        self.page.click("#save-new-btn")
        self.page.wait_for_timeout(500)

        # No success status should appear
        status_class = self.page.get_attribute("#builder-status", "class") or ""
        self.assertNotIn("success", status_class, "no success status after cancel")

    # ── PB11-5: new-file save re-points state.deck.path ───────────────────
    def test_new_file_repoints_deck_path(self):
        """After a new-file save, subsequent overwrite writes to the new path."""
        root_bytes = pathlib.Path(DECK_FIXTURE).read_bytes()

        deck_path = self._copy_deck()
        self._open_deck(deck_path)
        self.assertEqual(self._tray_count(), 10)

        # Remove one slide
        self.page.locator(".tray-row:nth-child(1) .tray-remove").click()
        self.page.wait_for_timeout(150)
        self.assertEqual(self._tray_count(), 9)

        # Save as new-file
        save_dir = tempfile.mkdtemp()
        save_path = os.path.join(save_dir, "renamed-deck.html")
        H.set_fake_dialog(self.base, save_path)
        self.page.click("#save-new-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)

        # Deck chip should now show the new filename
        chip_name = self._deck_chip_name()
        self.assertEqual(chip_name, "renamed-deck.html", "deck chip should show new filename")

        # Now overwrite — should write to save_path, not the original deck_path
        self.page.click("#save-overwrite-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)

        # The saved file should exist (overwrite wrote to the new path)
        self.assertTrue(os.path.exists(save_path), "overwrite should write to the new path")

        # Original temp copy should still exist (wasn't overwritten)
        # (it would have 10 slides if untouched, 9 if overwritten)
        self.assertTrue(os.path.exists(deck_path), "original temp copy should still exist")

        # Root deck unchanged
        self.assertEqual(
            pathlib.Path(DECK_FIXTURE).read_bytes(), root_bytes,
            "root deck must be byte-unchanged"
        )

    # ── PB11-8: crossing/second save after restructure stays faithful ─────
    #    Regression for the stale-index re-application defect: after a save-new
    #    of a reordered+duplicated deck, the builder re-points the deck source to
    #    the new file but the tray model kept PRE-save indices. The NEXT save (the
    #    "Switch to editor" crossing's Save-As, or any second save) re-applied those
    #    stale indices against the new source → a slide was silently DROPPED and the
    #    duplicate gained an extra copy (section count preserved, masking it).
    #    Fix: after save-new, the tray rebases to identity indices against the saved
    #    file, so the second save recomposes faithfully (byte-identical structure to
    #    save-#1). Assertions are content/order/identity-level — NEVER count-only.
    def _reorder_first_two(self, uid_src, uid_dst):
        """Drag the row with uid_src to sit before the row with uid_dst.
        Mirrors the exit-probe drag (pointer events through the hand-rolled sorter),
        with the same retry — headless drag occasionally does not 'take'."""
        for _ in range(3):
            g = self.page.query_selector(
                f"#tray-list .tray-row[data-uid='{uid_src}'] .grip"
            ).bounding_box()
            t = self.page.query_selector(
                f"#tray-list .tray-row[data-uid='{uid_dst}']"
            ).bounding_box()
            sx, sy = g["x"] + g["width"] / 2, g["y"] + g["height"] / 2
            tx, ty = t["x"] + t["width"] / 2, t["y"] - 6
            self.page.mouse.move(sx, sy)
            self.page.mouse.down()
            self.page.wait_for_timeout(250)
            for k in range(19):
                self.page.mouse.move(sx + (tx - sx) * k / 18, sy + (ty - sy) * k / 18)
                self.page.wait_for_timeout(25)
            self.page.wait_for_timeout(250)
            self.page.mouse.up()
            self.page.wait_for_timeout(600)
            try:
                self.page.wait_for_function(
                    f"() => document.querySelectorAll('#tray-list .tray-row')[0].dataset.uid==='{uid_src}'",
                    timeout=3000,
                )
                return True
            except Exception:
                continue
        return False

    def test_second_save_after_restructure_faithful(self):
        root_bytes = pathlib.Path(DECK_FIXTURE).read_bytes()
        sys.path.insert(0, os.path.join(REPO, "server"))
        from recompose import split_sections  # noqa: E402

        deck_path = self._copy_deck()
        self._open_deck(deck_path)
        self.assertEqual(self._tray_count(), 10, "deck should have 10 slides")

        # Owner restructure: reorder slide 2 (deck-section-1) before slide 1
        # (deck-section-0), then duplicate that reordered slide — the exact gesture
        # the exit probe used to expose the defect.
        uids = self.page.eval_on_selector_all(
            ".tray-row",
            "els=>els.map(e=>({uid:e.dataset.uid, sid:e.dataset.slideId}))",
        )
        uid0 = next(u["uid"] for u in uids if u["sid"] == "deck-section-0")
        uid1 = next(u["uid"] for u in uids if u["sid"] == "deck-section-1")
        reordered = self._reorder_first_two(uid1, uid0)
        self.assertTrue(reordered, "reorder (sec1 before sec0) must take")

        # Duplicate the now-first row (deck-section-1).
        self.page.click(f".tray-row[data-uid='{uid1}'] .tray-duplicate")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._tray_count(), 11, "after duplicate the tray holds 11 rows")

        # First save-new — this one is correct (maps against the original source).
        save_dir = tempfile.mkdtemp()
        save1_path = os.path.join(save_dir, "restructured.html")
        H.set_fake_dialog(self.base, save1_path)
        self.page.click("#save-new-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)
        self.assertTrue(os.path.exists(save1_path), "first save file must exist")

        # Freeze save-#1 bytes immediately — this is the faithful reference.
        save1_html = pathlib.Path(save1_path).read_bytes().decode("utf-8")
        s1_spans = split_sections(save1_html)
        s1_secs = [save1_html[s:e] for s, e in s1_spans]
        self.assertEqual(len(s1_secs), 11, "save-#1 must hold 11 sections")
        # Identity/order proof on save-#1: [sec1, sec1, sec0, sec2..sec9].
        self.assertEqual(s1_secs[0], s1_secs[1], "save-#1: rows 0,1 are the sec1 duplicate")
        self.assertIn("Uma plataforma inteligente", s1_secs[0], "save-#1 row0 is sec1")
        self.assertIn("slide--cover", s1_secs[2], "save-#1 row2 is sec0 (cover)")
        self.assertIn("Obrigado.", save1_html, "save-#1 must still contain the closing 'Obrigado' slide")

        # SECOND save — the crossing save. state.deck.path is now save1_path. Without
        # the fix, stale indices re-apply here and drop a slide. Save to a SECOND path
        # so we can compare bytes against the frozen save-#1.
        save2_path = os.path.join(save_dir, "crossing.html")
        H.set_fake_dialog(self.base, save2_path)
        self.page.click("#save-new-btn")
        # The save-#1 success status is still on screen, so wait on the distinct
        # on-disk signal (the second file appearing) rather than the status selector.
        for _ in range(100):
            if os.path.exists(save2_path):
                break
            self.page.wait_for_timeout(100)
        self.assertTrue(os.path.exists(save2_path), "second save file must exist")

        save2_html = pathlib.Path(save2_path).read_bytes().decode("utf-8")
        s2_spans = split_sections(save2_html)
        s2_secs = [save2_html[s:e] for s, e in s2_spans]

        # ── The regression assertions (content/order/identity, never count-only) ──
        self.assertEqual(len(s2_secs), 11, "second save must still hold 11 sections")
        # The dropped slide ('Obrigado', source sec9) MUST be present — the defect dropped it.
        self.assertIn(
            "Obrigado.", save2_html,
            "REGRESSION: closing slide 'Obrigado' was silently dropped by the second save"
        )
        # The duplicate (sec1) must sit at EXACTLY positions 0 and 1 — not spread to a third.
        self.assertEqual(s2_secs[0], s2_secs[1], "second save: duplicate must be at positions 0,1")
        self.assertIn("Uma plataforma inteligente", s2_secs[0], "second save row0 is sec1")
        self.assertNotEqual(
            s2_secs[1], s2_secs[2],
            "REGRESSION: sec1 leaked into a THIRD position (stale-index re-application)"
        )
        self.assertIn("slide--cover", s2_secs[2], "second save row2 is sec0 (cover)")
        # The decisive proof: the second save is structurally byte-identical to save-#1.
        self.assertEqual(
            [s.replace("\r\n", "\n") for s in s2_secs],
            [s.replace("\r\n", "\n") for s in s1_secs],
            "REGRESSION: second save bytes diverge from the faithful save-#1 (stale-index corruption)"
        )

        # Root deck must be byte-unchanged.
        self.assertEqual(
            pathlib.Path(DECK_FIXTURE).read_bytes(), root_bytes,
            "root deck must be byte-unchanged after restructure + two saves"
        )

    # ── PB11-6: save pane visible in deck mode, assemble hidden ───────────
    def test_deck_mode_save_pane_visible(self):
        deck_path = self._copy_deck()
        self._open_deck(deck_path)

        # Save pane should be visible (not hidden)
        save_pane_hidden = self.page.get_attribute("#deck-save-pane", "hidden")
        self.assertIsNone(save_pane_hidden, "save pane should be visible in deck mode")

        # Assemble button's parent (.assemble) should be hidden
        assemble_hidden = self.page.get_attribute(".assemble", "hidden")
        self.assertIsNotNone(assemble_hidden, "assemble panel should be hidden in deck mode")

    # ── PB11-7: root deck is NEVER written to ─────────────────────────────
    def test_root_deck_never_written(self):
        """Dedicated test: the root deck fixture is byte-unchanged across all operations."""
        root_bytes_before = pathlib.Path(DECK_FIXTURE).read_bytes()

        # Exercise both save modes
        deck_path = self._copy_deck()
        self._open_deck(deck_path)

        # Restructure
        self.page.locator(".tray-row:nth-child(2) .tray-remove").click()
        self.page.wait_for_timeout(100)
        self.page.click("#add-blank-btn")
        self.page.wait_for_timeout(100)

        # New-file save
        save_dir = tempfile.mkdtemp()
        save_path = os.path.join(save_dir, "test.html")
        H.set_fake_dialog(self.base, save_path)
        self.page.click("#save-new-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)

        # Overwrite
        self.page.click("#save-overwrite-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)

        root_bytes_after = pathlib.Path(DECK_FIXTURE).read_bytes()
        self.assertEqual(
            root_bytes_before, root_bytes_after,
            "root deck must be byte-unchanged after all save operations"
        )


if __name__ == "__main__":
    unittest.main()
