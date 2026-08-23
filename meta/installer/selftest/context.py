"""The one frame every check section shares.

`selftest()` used to be a single 3,000-line function, so its sections simply
shared locals. Split across modules they cannot, and the danger is silent: a
section that loses its grip on `ok` still prints PASS/FAIL lines while
contributing nothing to the verdict. This object holds that state instead, and
`frame()` / `keep()` hand it to a section and take it back — which reproduces
the single frame exactly, in the order `runner.ORDER` runs them.
"""
from __future__ import annotations

# The names a section leaves behind for a later section to read. Measured, not
# guessed: these are the locals whose value crosses a section boundary. Adding
# a new cross-section name here is the ONLY way to carry one.
CARRIED = ("catalog", "data", "legacy", "expect", "basis_body",
           "mirrors_on_disk", "mtr", "_mk", "rf", "pws")


class Ctx:
    """Shared state plus the two report verbs. One instance per run."""

    def __init__(self) -> None:
        self.ok = True
        self.tmp = None
        self.tree = None
        self.target = None
        self.shadowed: list = []
        self._carried: dict = {}

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}"
              + (f" — {detail}" if detail and not condition else ""))
        self.ok = self.ok and condition

    def skip(self, label: str, why: str) -> None:
        """A precondition this MACHINE cannot supply — not a verdict.

        Only for an arm that needs something outside the fixture tree (an
        installed workspace to read). Never for an arm whose inputs this
        suite builds itself: there, "cannot run" is a defect.
        """
        print(f"  [SKIP] {label} — {why}")

    def frame(self) -> tuple:
        """The carried names, in CARRIED order. Absent ones come back None."""
        return tuple(self._carried.get(name) for name in CARRIED)

    def keep(self, scope: dict) -> None:
        """Take back every carried name the section's locals hold."""
        for name in CARRIED:
            if name in scope:
                self._carried[name] = scope[name]
