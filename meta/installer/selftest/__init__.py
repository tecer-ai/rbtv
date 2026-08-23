"""The installer's runnable check — `rbtv install selftest`.

One module per subject; `runner.py` owns the order they run in and the shared
frame they run against. Importing `lib` first is what puts `meta/installer/`
on the import path, so `discovery` and `lib.*` resolve however this package
was reached.
"""
from __future__ import annotations

import lib  # noqa: F401  — imported for its import-path bootstrap, not its API
