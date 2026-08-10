"""guidance.py — RETIRED render leg; now only the shared exclusion constant.

RETIREMENT (owner ruling ``d-hard-guard-retire-model-mirror``, 2026-08-10, in
``1-projects/rbtv-sb-merge-refactor-core-build/decisions.md``): installer-1's
guidance-file rendering is GONE. This module used to walk a workspace for every
``CLAUDE.md`` and write a sibling ``AGENTS.md``/``QWEN.md``; on the rbtv vault
that path fought install2, which now owns every guidance file (``d-s17`` /
``d-s17bis``), and no election, flag or state may resurrect it. ``render_guidance``
and its walk/compose helpers were deleted — NOT disabled behind a flag — so there
is nothing left to re-enable. Do not reinstate a render path here; if a workspace
needs guidance files, install2 renders them.

Still live and deliberately kept:

- ``ALWAYS_EXCLUDED_PREFIXES`` — read by ``driver.uninstall`` to protect
  goal-folder routers recorded by a PRE-retirement render (row 7.597). Legacy
  ``kind: "guidance"`` records can still exist in an old workspace's
  ``rbtv.json``; the uninstall/banner-guard arm that tears down installer-1's own
  past output is untouched by this retirement.
- ``mirror.py``'s standalone engine (one directory up) is a separate,
  operator-invoked tool (documented for worktrees in the opencode manual) and is
  outside this ruling's scope — nothing in ``install.py`` reaches it.
"""
from __future__ import annotations

#: Path prefixes the mirror never manages.  ``.rbtv/goals`` holds goal folders
#: whose routers — BOTH ``CLAUDE.md`` and ``AGENTS.md`` — are written by the
#: goals-tree scaffold (owner ruling Q18, 2026-08-09).
#:
#: ``driver.uninstall`` consults this set (row 7.597): a workspace whose
#: ``rbtv.json`` still records such a router from a pre-retirement render must
#: NOT have it deleted on teardown — the banner-guard cannot spare it (the
#: scaffold's own header carries the same DO-NOT-EDIT sentinel), so uninstall
#: drops it from the delete set and un-manages it instead.
ALWAYS_EXCLUDED_PREFIXES: tuple[str, ...] = (".rbtv/goals",)
