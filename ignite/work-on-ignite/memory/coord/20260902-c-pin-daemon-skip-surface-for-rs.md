# 20260902-c-pin-daemon-skip-surface-for-rs — pin daemon-skip surface for RS-4b (RS-4 unamended)

kind: creation
component: coord
date: 2026-09-02
commit: 57706361f02c9e13a0d79121d8b0b0f34db46197
deployed: yes
pin: ignite/coord/coord_selftest.py
components: supervisor

## Motivation
`freeze-scope`'s owner-ruled requirement `dag-10 RS-4` says a registered-but-folderless seat must
still read READY (never flip the verdict), but judge-supervisor's clause-5 FAIL demanded proof
that the additive daemon-skip surface shipped in `f6c5a808` — a `daemon-skip` note naming
`blocked-by-uninstalled-milestone`, carried alongside READY rather than replacing it — was actually
pinned by a selftest assertion, not merely shipped. `freeze-scope`'s own sittings wrote and verified
the two RS-4b check arms twice but could not commit them: on both attempts `coord_selftest.py`
carried a sibling seat's uncommitted hunks, and publishing someone else's unreviewed work under this
message was correctly refused (the parallel-sessions commit-collision discipline). The orchestrator
held the diff as a patch file (`seats/freeze-scope/rs4b-full.patch`) and landed it once the file was
quiet.

## Design
No new mechanism — the daemon-skip surface itself was already built and shipped in `f6c5a808`; this
commit only adds the two selftest check arms that prove it, inside the SAME `dag-10 RS-4` block so a
future edit to the READY-vs-`daemon-skip` split cannot silently regress one without the suite
flagging it. Landing it as an orchestrator-applied patch (rather than a re-verification from a fresh
sitting) was the only option once a peer's own re-verification runs kept colliding with concurrent
edits to the same file; the patch's provenance (RS-4b arms authored and behaviourally proven by
`freeze-scope`) is preserved in the commit message rather than re-derived.

## How it works
The two RS-4b arms sit alongside `dag-10 RS-4`'s existing assertions in `coord_selftest.py`: one
proves that with `lane-skips.json` present, a registered-but-folderless seat still reads READY (RS-4
unamended) AND now carries an additive `daemon-skip` note naming `blocked-by-uninstalled-milestone`;
the other proves that with no `lane-skips.json` ever written, `daemon-skip` is `None` on every seat
and never raises. Both are read-only assertions against the same fixture shape RS-4 already used —
no production code changed in this commit, only the test file.

## Consequences
Nothing in production code changed; the daemon-skip surface (`f6c5a808`) and the RS-4 verdict logic
are both untouched. What changed is that a regression to either is now caught. The commit message
discloses that verification was split: `freeze-scope` proved it behaviourally twice (full suite once,
a scoped synchronous harness on relaunch: RS-4 4/4 + RS-4b 2/2, ALL PASS, honestly omitting one RS-4
assertion that lives in `messages.py` and was mid-edit by a sibling); the orchestrator independently
confirmed the patch applies clean, the file compiles (`compile()`, not `ast.parse()` — the parked
lesson from `ast.parse is not a syntax check`), and the diff is exactly +27/-0. It was NOT re-run
against the shared suite at commit time, because `coord.py selftest` was at that moment aborting
before reaching `dag-10`/RS-4 at all (a 15-minute bound kill) — a separate suite defect, filed
elsewhere, not fixed here.

## Verification
Behavioural (by `freeze-scope`, twice, before this commit landed): full suite first sitting, then a
scoped synchronous harness on relaunch — RS-4 4/4 + RS-4b 2/2, ALL PASS. Orchestrator, independently,
at landing time: `git apply --check` clean, `compile()` succeeds, diff exactly +27/-0, both RS-4b
checks present in the applied file. Not independently re-run against the full suite at commit time
(suite-abort defect, filed separately). Deployed — branch `ignite/core-daemon`, carried on live
deploy tree `e8524c31`.

## ATTENTION
1. This commit adds test coverage only — the daemon-skip surface it pins shipped in `f6c5a808`,
   a separate, earlier commit. Do not read this commit as the feature's introduction.
2. At the time this landed, `coord.py selftest`'s full run was aborting before reaching `dag-10`/RS-4
   (15-minute kill), so RS-4b's pin has not been confirmed against the CURRENT full suite — only
   against the scoped synchronous harness and the orchestrator's static checks. Re-run the full
   suite and confirm RS-4/RS-4b both still execute (not just "present in the file") before trusting
   this pin blind.
3. `dag-10 RS-4`'s own census assertion lives in `messages.py`, which was mid-edit by a sibling seat
   at the time RS-4b was proven — a future editor of that assertion should re-run RS-4b alongside it.
