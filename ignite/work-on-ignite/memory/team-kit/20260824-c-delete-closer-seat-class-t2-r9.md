# 20260824-c-delete-closer-seat-class-t2-r9 — delete closer-* seat class [T2-R9]

kind: change
component: team-kit
date: 2026-08-24
commit: 4930e6a9
deployed: no
pin: NONE

## Motivation
[T2-R9] (redesign baseline v2, subsystem 8 of an 11-subsystem deletion batch): "the `closer-*`
seat class is deleted; only the daemon acts on other seats." `close <agent> [--renew]` spawned a
sonnet `closer-<target>` seat — a distinct occupant class with its own pane and prompt template —
that co-wrote a stuck/memoryless seat's `memory.md` before running `close-seat` to kill it. That
extra hop through a spawned reviewer seat is what the ruling removes; the daemon or leader now
closes a seat directly.

## Design
Deletion, not a replacement: this batch's stated shape is delete-only ("impl-envelope"/"impl-slack"
replacements are separate future seats' work). `close-seat` (the mechanical kill/checkout/relaunch
verb) and `checkout --renew --handoff` (a seat's own self-renewal) are the two SURVIVING paths and
were left untouched. Where `close`'s body branched on `close: mechanical` (G-23) to skip spawning a
closer for a memoryless seat, that routing logic went with the verb — `close-seat` never spawned a
closer either way, so calling it directly on a mechanical seat already gets the same outcome with
no dedicated branch needed.

## How it works
Deleted whole from `ignite/team-kit/coord.py`: `cmd_close`, its argparse registration, `closer_prompt`,
`closer_placement`, `resolve_closer_pane`, `mechanical_close_seat` (only caller was `cmd_close`),
`ns_like` (only caller was `cmd_close`), and the now-dead `CLOSER_MODEL`/`CLOSERS_WINDOW` constants.
Deleted `ignite/team-kit/closer-prompt.md` (the template file). Every user-facing string that taught
`close <agent>` as the remedy (refusal texts in the self-renew path, `checkout`'s and
`export-transcript`'s `-h` epilogs, the `next:` hints) now teaches `close-seat <agent> --renew`
instead. `roles.md`, `team-kit.md`, `protocol.md`, `briefing-authoring.md`, `briefing-template.md`
had their closer-role/closer-ceremony sections removed or updated to say a healthy seat renews
itself and a stuck one is closed directly, no agent in the path. `system-design.md` design-log rows
that described the closer as a currently-live mechanism were marked `RETIRED [T2-R9]` in place
(kept, not deleted, per the file's own historical-record convention) — the deleted D7 owner ruling
("closer stays as-is, zero code change") is now explicitly noted as superseded by [T2-R9].

## Consequences
Selftest lost exactly 9 checks that directly exercised the deleted spawn path (closer-prompt
filling, close --dry-run output, closer_placement's pure decision fn, two G-11/G-21 closer-boot-
failure guards, two closer-window-placement checks) — none replaced, since there is no surviving
mechanism for them to cover. One check (G-23 "`close` on a mechanical seat spawns no closer pane")
was rewritten to exercise `close-seat` directly instead of deleted outright, since it still proves
something real (a mechanical seat closes cleanly with no pane opened for it). `HELP_EPILOG` had a
stale `close` line removed (T6's parser-vs-epilog coverage check would otherwise catch this — and
did, on the first selftest run: `documented but not accepted: ['close']`).

## Verification
`python3 -B -c "import py_compile; py_compile.compile('ignite/team-kit/coord.py', doraise=True)"`
clean. `python3 -B ignite/team-kit/coord.py selftest`: PASS, 1054 ok (down from subsystem-7's 1063
baseline by exactly the 9 removed checks, 0 failures). Grep floor run clean: no `closer-prompt`,
`cmd_close` (bare), or `closer-[a-z]` production-code hits remain outside historical/doc-record
prose and one unrelated scratch-fixture filename reused for a different coverage test. Deployed: no
(this worktree has not been synced to the live ignite tree yet).

## ATTENTION
1. `is_closer(name)` (checks a `closer-` name prefix) and its one caller in `broadcast_scope` were
   LEFT LIVE, not deleted — they are generic message-routing infra a prior subsystem (T2-R10)
   explicitly preserved for "non-gating purposes", and now that no code ever spawns a `closer-*`
   name, that branch is permanently unreachable in production (though still exercised by a selftest
   using a synthetic name). Flagged for the redesign owner rather than removed unasked — deleting it
   changes `broadcast_scope`'s public behavior, one step beyond this subsystem's "delete the seat
   CLASS" remit.
2. `closing_reaches`/`inbox_scope_line` still carry a `f"closer-{seat}"` fallback default and
   "closer exception" rationale describing the now-deleted co-write ceremony. The CLOSING state
   MECHANISM survives (self-renewal mutes a seat's own inbox via `set_closing(base, me, me)`), but
   with `closer-*` gone, that fallback and its rationale describe a case that can no longer occur.
   Left untouched: changing it touches live message-routing behavior beyond this subsystem's scope.
3. A DIFFERENT "chief-of-staff and closer" RETIRED-ROLES note lives in
   `ignite/team-kit/starter-set/CLAUDE.md` and is cited (stale) from `meta/module.md:22` via a
   `conduct.md § 4` path that no longer exists (`conduct.md` was abolished by a separate commit,
   `3dd27f2c`). That "closer" is a META-PLANNING role (goal/milestone scaffolding), unrelated to the
   team-kit `closer-<target>` tmux seat this entry deletes — confirmed by reading both files. Not
   touched; flagged only because the name collision could mislead a future reader searching "closer".
