import os
import sys
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))   # hypresent/
FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction.html")
sys.path.insert(0, os.path.join(REPO, "server"))
import api  # noqa: E402


class DialogSeamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Fail loud if the canonical fixture is absent (gitignored per U10a; never skip-green, R07).
        if not os.path.exists(FIXTURE):
            raise AssertionError(
                f"Required fixture missing: {FIXTURE} (gitignored per U10a; restore it locally before running tests)"
            )

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.copy = os.path.join(self.tmp, "copy.html")
        shutil.copy(FIXTURE, self.copy)
        api.set_open_path(None)            # reset between tests
        api.set_dialog_launcher(None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        api.set_open_path(None)
        api.set_dialog_launcher(None)

    def test_dialog_open_returns_file(self):                 # U-DLG-1
        api.set_dialog_launcher(lambda kind: self.copy)
        status, resp = api.handle_dialog_open()
        self.assertEqual(status, 200)
        self.assertIn("html", resp)
        self.assertEqual(resp["name"], "copy.html")
        self.assertEqual(api.get_open_path(), os.path.abspath(self.copy))

    def test_dialog_open_cancel(self):                        # U-DLG-2
        api.set_dialog_launcher(lambda kind: None)
        status, resp = api.handle_dialog_open()
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("cancelled"))
        self.assertIsNone(api.get_open_path())

    def test_dialog_save_as_writes(self):                     # U-DLG-3
        out = os.path.join(self.tmp, "out.html")
        api.set_dialog_launcher(lambda kind: out)
        status, resp = api.handle_dialog_save_as({"html": "<html>x</html>"})
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("ok"))
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "<html>x</html>")

    def test_dialog_save_as_cancel(self):                     # U-DLG-4
        api.set_dialog_launcher(lambda kind: None)
        status, resp = api.handle_dialog_save_as({"html": "x"})
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("cancelled"))

    def test_save_overwrites_open(self):                      # U-DLG-5
        api.set_open_path(self.copy)
        status, resp = api.handle_save({"html": "<new/>"})
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("ok"))
        with open(self.copy, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "<new/>")

    def test_save_no_open_file(self):                         # U-DLG-6
        api.set_open_path(None)
        status, resp = api.handle_save({"html": "x"})
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("no_open_file"))

    def test_filter_includes_htm(self):                       # U-DLG-7
        self.assertIn("*.html;*.htm", api._OPEN_PS)
        self.assertIn("*.html;*.htm", api._SAVE_PS)

    def test_dialog_open_reuses_handle_open(self):            # U-DLG-8
        api.set_dialog_launcher(lambda kind: self.copy)
        _, resp = api.handle_dialog_open()
        with open(self.copy, encoding="utf-8") as fh:
            self.assertEqual(resp["html"], fh.read())

    def test_ps_args_flag_contract(self):                     # U-DLG-9 (R02)
        args = api._ps_args("pwsh", "SCRIPT")
        self.assertEqual(args[0], "pwsh")
        self.assertIn("-STA", args)
        self.assertIn("-NoProfile", args)
        self.assertIn("-NonInteractive", args)
        self.assertEqual(args[-2:], ["-Command", "SCRIPT"])


if __name__ == "__main__":
    unittest.main()
