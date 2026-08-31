# 20260831-i-uncaged-audio-bare-name-path-g — uncaged audio bare-name: PATH gap and echo-tail grading

kind: issue
component: meta-planning
date: 2026-08-31
commit: 899694e7
deployed: no
pin: NONE
components: meta-leader

## Observed
Task 169 (redesign-continue-1 seed): on `stools-canvas-audio-elevenlabs-close` M5, a relay script
called bare `audio language` from an uncaged `leader` chair and got exit 127 ×4
(`audio: command not found`) four times before a human caught it; the wrapper script still exited
0 because it ended on `echo`, which would have certified the clause green off a total miss. Manual
patch at the time: the leader put a disclosed one-line PATH shim for the duration and graded the
script's PER-STEP exits by hand, not the wrapper's own exit. Re-verified 2026-08-31 from an uncaged
leader-class chair on the current tree: `command -v audio` → not found, `audio language` → exit
127, confirming the recurrence still stood.

## Mechanism
Two independent facts compound into this trap:
1. `core/communication/references/audio-io.md` (committed since 2026-08-28/30, `ccae8263`) already
   documents the correct fix for the DOCS half: it states the two-vantage table (caged-declared
   works via `~/.rbtv-bin`, everything else 127) and tells every reader to default to the
   `python3 <full path>` form, which is correct in both vantages. That half was NOT the recurring
   gap — grepping `meta/leader/prompts/leader.md`, `meta/planning/prompts/dod-judge.md` and
   `meta/planning/prompts/verifier.md` for `wrapper`/`exit code` found nothing minting a bare-name
   grading script.
2. The PATH-provisioning half was genuinely missing, and NOT for the reason the seed assumed
   ("uncaged chairs have no `audio` on PATH" full stop). `audio` IS already symlinked — at
   `~/.rbtv/bin/audio` (`meta/installer/lib/pathlinks.py`'s exposure-driven installer step, from
   `core/communication/exposure.csv`'s `audio,tool,path,…` row, linked since 2026-08-23) — but
   `~/.rbtv/bin` is never added to PATH for a daemon-spawned uncaged sitting: that requires
   `pathlinks.py#_write_shell_path` to have run for an INTERACTIVE shell that sources `.bashrc`/
   `.zshrc`, which a systemd/tmux-spawned sitting does not do, and grepping the shell rc files
   found no `rbtv` PATH fence on this box. The mechanism that DOES reach a daemon-spawned uncaged
   staff sitting is `ignite/supervisor/spawn/spawn.js`'s `local-bin: true` grant (fixed
   2026-08-26, commit `af326d61`, memory `supervisor/20260826-i-uncaged-staff-seats-never-got`) —
   and it composes PATH from `~/.local/bin` ONLY, never `~/.rbtv/bin`. `ignite/deploy/link-tools.py`
   is the script that owns `~/.local/bin`, and its own docstring scopes it to "the ignite module
   ONLY … every `method=path` tool whose `exposure.csv` row leaves `rbtv-cli` empty" — `audio`
   lives under `core/communication/`, a different module with its own owner, so it was never a
   candidate for that TOOLS dict by the script's own stated rule. Net effect: two PATH-link
   mechanisms exist (`~/.rbtv/bin` via `pathlinks.py`, `~/.local/bin` via `link-tools.py`), the one
   uncaged staff seats actually get on PATH is `~/.local/bin`, and `audio`'s only symlink sat in
   the OTHER one.

## Attempts
First attempt held on the PATH-composition side of this defect — checked: `git log -S'local-bin'
-- ignite/supervisor/spawn/spawn.js` and `git log ignite/deploy/link-tools.py` show `af326d61`
(the uncaged-staff PATH fix) and `8aa5bff6` (three operator doors added to `link-tools.py`'s
`TOOLS`), neither of which touched `audio` or unified the two PATH mechanisms; `8aa5bff6`'s own
memory entry ATTENTION explicitly records the two mechanisms as "not one thing" and that "a fix in
one does nothing for the other" — this is that other shoe dropping for `audio` specifically.

## Fix
Two parts, deliberately kept separate and both minimal:
1. **PATH**: symlinked `~/.local/bin/audio -> core/communication/capabilities/audio/audio.py` on
   this box (the ignite VPS), matching the existing precedent of `stools` (also a non-ignite-module
   tool, also manually placed in `~/.local/bin`, also relied on today by uncaged staff). Rejected:
   adding `audio` to `ignite/deploy/link-tools.py`'s `TOOLS` dict — its own docstring and inline
   comment explicitly scope it to ignite-module tools ("Other repos' PATH names … have the same
   gap and their own owners; each module exposes its own"), and its `IGNITE`-relative path
   resolution assumes every target lives under `ignite/`, which `audio.py` does not; forcing it in
   would contradict the script's stated scope for a one-tool convenience. Rejected: teaching
   `spawn.js`'s `local-bin: true` grant to ALSO compose `~/.rbtv/bin` — that blurs a grant whose
   name and every comment tie it specifically to `~/.local/bin`, is a change to live daemon-spawn
   code affecting every uncaged staff seat, and is out of size for an #d/easy recurrence fix; noted
   below as a loose end rather than built here. This symlink is a MANUAL, per-box fix — exactly the
   anti-pattern `link-tools.py`'s own docstring warns against ("someone made `~/.local/bin`
   symlinks BY HAND … a redeploy or a second machine leaves the name unresolvable") — disclosed as
   such, not hidden.
2. **Grading discipline**: `meta/planning/prompts/dod-judge.md` step 2 now states explicitly that a
   clause graded off a script's exit code must be graded on the PER-STEP exit of the command the
   clause names, never a wrapper's own tail exit, naming the echo-tail failure mode by name. Landed
   in the same commit as the task-170 fix (`899694e7`) since both are guidance the same
   evidence-trial seat needs at the same procedure step.

## Consequences
The symlink is HOST STATE, not a repo change — it does not appear in `git status` and is not
covered by the repo's commit. It survives until this box is rebuilt or the `~/.local/bin` directory
is recreated; a second machine or a fresh clone does NOT get it. `core/communication/references/audio-io.md`'s
own vantage table ("ANY UNCAGED chair → exits 127") is now slightly stale FOR THIS BOX ONLY — left
UNCHANGED deliberately: the doc's own design (ruled `p-m6-section-scope`) is that the full-path
form is "the one form correct in BOTH vantages" and a portable, reproducible reference should not
assert a fact that is true on one box today and false on a fresh one tomorrow. A durable, scripted
fix — a `core/communication`-owned linking step analogous to `ignite/deploy/link-tools.py`, or
teaching `pathlinks.py`'s `~/.rbtv/bin` output onto a daemon-spawned uncaged seat's PATH — is real
follow-up work, not built here (scope/size; see loose ends in the seat report).

## Verification
Red confirmed before the fix: `command -v audio` → not found (exit 1), `audio language` → exit 127,
from this uncaged leader-class chair, 2026-08-31. Green confirmed after: same commands →
`/home/henri/.local/bin/audio` and exit 0 with the CLI's real JSON output
(`{"config": …, "language": "pt", …}`). Caged behaviour re-checked untouched: `git -C
3-resources/tools/rbtv diff -- ignite/supervisor/spawn/spawn.js` is 0 bytes (no edit made there),
and `RBTV_BIN_DIRNAME`/`exposed-clis` are unchanged in the file. `dod-judge.md`'s wording change
verified by re-reading the committed diff. No daemon restart performed or required — the symlink is
host PATH state the daemon does not read at boot, and the prompt-file edit is read at sitting-start
from the repo, not the deploy tree (undeployed at filing time — see the sibling task-170 entry's
commit hash, same commit).

## ATTENTION
1. Two PATH-link mechanisms exist for this workspace and are easy to confuse: `~/.rbtv/bin`
   (`meta/installer/lib/pathlinks.py`, exposure-driven, every component's `method=path` rows) and
   `~/.local/bin` (`ignite/deploy/link-tools.py`, hardcoded, ignite-module-only). A tool symlinked
   in one is invisible from the other, and `~/.rbtv/bin` is NOT on PATH for a daemon-spawned
   uncaged staff sitting today (`spawn.js`'s `local-bin: true` grant composes `~/.local/bin` only).
   Before concluding "granted but unreachable" for any bare name, check BOTH bin dirs and which one
   the calling seat's PATH actually carries.
2. The `~/.local/bin/audio` symlink added here is manual, host-scoped state — it is not created by
   any script and will not exist on a second machine or after this box's `~/.local/bin` is rebuilt.
   Anyone hardening this properly should give `core/communication` (or a shared, exposure-driven
   `~/.local/bin` step) its own linking mechanism rather than repeating this by hand a second time.
3. `core/communication/references/audio-io.md`'s vantage table still says every uncaged chair gets
   127 — true everywhere except this one box after this fix. Do not "correct" that table to declare
   bare `audio` universally reachable; the full-path form is still the only one correct on every
   machine, and the doc's own ruling (`p-m6-section-scope`) chose portability over this box's
   current convenience.
- audio was linked at ~/.rbtv/bin (pathlinks.py) but uncaged staff PATH only carries ~/.local/bin (spawn.js local-bin grant) — two PATH mechanisms, not one
