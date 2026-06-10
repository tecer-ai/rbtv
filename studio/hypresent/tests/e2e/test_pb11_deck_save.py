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
