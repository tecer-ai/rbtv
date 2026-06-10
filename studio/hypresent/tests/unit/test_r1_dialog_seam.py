import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))   # hypresent/
FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction.html")
sys.path.insert(0, os.path.join(REPO, "server"))
import api  # noqa: E402


class DialogSeamRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(FIXTURE):
            raise AssertionError(
                f"Required fixture missing: {FIXTURE} (gitignored per U10a; restore it locally before running tests)"
            )

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.copy = os.path.join(self.tmp, "copy.html")
        shutil.copy(FIXTURE, self.copy)
        api.set_open_path(None)
        api.set_dialog_launcher(None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        api.set_open_path(None)
        api.set_dialog_launcher(None)

    def test_dialog_open_returns_file(self):                 # U-R1S-1
        api.set_dialog_launcher(lambda kind: self.copy)
        status, resp = api.handle_dialog_open()
        self.assertEqual(status, 200)
        self.assertIn("html", resp)
        self.assertEqual(resp["name"], "copy.html")
        self.assertEqual(api.get_open_path(), os.path.abspath(self.copy))

    def test_dialog_open_cancel(self):                        # U-R1S-2
        api.set_dialog_launcher(lambda kind: None)
        status, resp = api.handle_dialog_open()
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("cancelled"))

    def test_dialog_save_as_writes(self):                     # U-R1S-3
        out = os.path.join(self.tmp, "out.html")
        api.set_dialog_launcher(lambda kind: out)
        status, resp = api.handle_dialog_save_as({"html": "<html>x</html>"})
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("ok"))
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "<html>x</html>")

    def test_save_no_open_file(self):                         # U-R1S-4
        api.set_open_path(None)
        status, resp = api.handle_save({"html": "x"})
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("no_open_file"))

    def test_ps_scripts_have_topmost_owner_and_no_showhelp(self):   # U-R1S-5 (V3-S1 contract lock)
        for script in (api._OPEN_PS, api._SAVE_PS):
            self.assertIn("$d.ShowDialog($owner)", script, "dialog must be shown WITH the owner form")
            self.assertIn("TopMost = $true", script, "owner form must be TopMost")
            self.assertNotIn("ShowHelp", script, "the unreliable ShowHelp hack must be removed (V3-S1)")


if __name__ == "__main__":
    unittest.main()
