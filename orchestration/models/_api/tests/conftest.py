"""Test scaffolding for the _api tests.

Puts the _api dir on sys.path so `clients.manus`, `clients.base`, and the
runner module (`run`) import exactly as they do under the real CLI runner
(run.py inserts its own dir at the front of sys.path).
"""
import pathlib
import sys

_API_DIR = pathlib.Path(__file__).resolve().parent.parent

if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))
