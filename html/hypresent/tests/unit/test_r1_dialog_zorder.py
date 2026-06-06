import ctypes
import os
import sys
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))   # hypresent/
sys.path.insert(0, os.path.join(REPO, "server"))
import api  # noqa: E402

OPEN_TITLE = "Open Presentation"


def _enum_find_by_title(substr):
    """EnumWindows → (hwnd, ex_style) of the first visible top-level window whose title contains substr."""
    user32 = ctypes.windll.user32
    found = {"hwnd": None, "ex": 0}
    GWL_EXSTYLE = -20
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        if substr.lower() in buf.value.lower():
            found["hwnd"] = hwnd
            found["ex"] = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            return False
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found["hwnd"], found["ex"]


@unittest.skipUnless(sys.platform == "win32", "R1 z-order test is Windows-only")
class DialogZOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Documented headless skip: ONLY when no interactive desktop session exists.
        # On an interactive Windows 11 + Chrome session there IS a foreground window,
        # so this does NOT skip and the test runs.
        if ctypes.windll.user32.GetForegroundWindow() == 0:
            raise unittest.SkipTest(
                "No interactive desktop session (headless CI) — the R1 real-dialog z-order test "
                "requires a desktop. On an interactive Windows 11 session it runs."
            )

    def test_real_open_dialog_is_topmost_and_foreground(self):
        WS_EX_TOPMOST = 0x00000008
        WM_CLOSE = 0x0010
        result = {"path": "__unset__"}

        def run_dialog():
            # Real PowerShell -STA dialog WITH the TopMost owner Form (V3-S1).
            result["path"] = api._run_ps_dialog_default("open")

        t = threading.Thread(target=run_dialog, daemon=True)
        t.start()

        hwnd, ex = None, 0
        deadline = time.time() + 8
        while time.time() < deadline:
            hwnd, ex = _enum_find_by_title(OPEN_TITLE)
            if hwnd:
                break
            time.sleep(0.2)

        if hwnd is None:
            # Make sure the PS process does not hang the suite if the window never appeared.
            t.join(timeout=1)
            self.fail("real Open dialog window did not appear within 8s (title 'Open Presentation')")

        fg = ctypes.windll.user32.GetForegroundWindow()
        is_topmost = bool(ex & WS_EX_TOPMOST)
        try:
            self.assertTrue(
                fg == hwnd or is_topmost,
                f"dialog not on top: foreground={fg} dialog={hwnd} ws_ex_topmost={is_topmost}",
            )
        finally:
            # Always tear the dialog down so the PS process returns.
            ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            t.join(timeout=8)

        self.assertFalse(t.is_alive(), "PowerShell dialog process did not exit after WM_CLOSE")
        self.assertIsNone(result["path"], "closing the dialog (cancel) should make the launcher return None")


if __name__ == "__main__":
    unittest.main()
