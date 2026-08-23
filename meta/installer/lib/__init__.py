"""The installer's modules. Importing the package makes `discovery` reachable.

`meta/installer/` goes on the import path here, once, so every module of this
package can `import discovery` no matter which entry reached it — the entry
script, the selftest, or a direct `import lib.x` from this directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

_INSTALLER_DIR = str(Path(__file__).resolve().parent.parent)
if _INSTALLER_DIR not in sys.path:
    sys.path.insert(0, _INSTALLER_DIR)
