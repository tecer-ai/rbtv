# 20260902-c-stools-send-as-owner-wrapper-e — stools send-as-owner wrapper enforces grant gate

kind: creation
component: meta-planning
date: 2026-09-02
commit: c10bbc189cc44d632c4dfc3eb3a4be9d028db36a
deployed: not-applicable
pin: NONE

## Motivation
Owner ruling `d-slack-identity-a` (`redesign-continue-1/slack-send-identity-design.md`, option a):
agents send to Slack as the bot by default; sending as the owner (Henrique, `--workspace ignite-
owner`, an `xoxp` user token) needed to require an active, owner-recorded grant checked at send
time. Before this change, `stools.py` (the Slack CLI) let any caller send as the owner with no gate
at all.

## Design
A new wrapper, `meta/planning/capabilities/stools-wrapper/tool/stools_wrapper.py`, sits in front of
`stools.py` rather than editing it — the design's read-only constraint on `stools.py`/`auth.py`. On
write verbs (`send`/`upload`/`react`/`canvas`) targeting a workspace marked `writes: false` in local
`config.yaml`, the wrapper checks `.rbtv/config/stools-as-owner-grants.yaml` for a matching active
grant scoped to the calling sitting's current working directory; an ungranted write exits 2 (`as-
owner-write-refused`) with no exec and no network call. `--dry-run` and every read verb
(`search:read` included) pass straight through ungated. `exposure.csv`'s `stools` row and
`meta/master/references/slack-message-format.md` (the skill's actual source) now point at the
wrapper instead of `stools.py` directly, pinned to `--workspace ignite`, with the grant exception
documented.

## How it works
`config.yaml` under `ignite-owner` carries `writes: false`. `.rbtv/config/stools-as-owner-
grants.yaml` (gitignored, transcribed from `decisions.md`, the human record staying in
`decisions.md`) holds grant rows; the wrapper matches the calling sitting's cwd against an active
row before letting a gated write verb through to the real `stools.py`.

## Consequences
The sandbox mechanism (`spawn.js#resolveExposedCliGrants`) ro-binds only an exposed CLI's own
directory. The wrapper lives in `meta/planning/capabilities/stools-wrapper/tool/`, a different
directory from the real `stools.py` tree it execs into — a CAGED seat granted `stools` would have
the wrapper's directory ro-bound but not `3-resources/tools/stools/`, so its exec into the real
script would fail inside a cage. This build seat ran uncaged, so this gap is untested and unresolved
— flagged as a follow-up needing a `spawn.js` change or another mechanism (out of this fix's scope;
`spawn.js` was not touched). `exposure.csv` is a repo source; caged/daemon-lane seats resolve entry
points via a derived mirror tree, so this fix needs a deploy before it is visible to them.

## Verification
Red-first (called `stools.py` directly, bypassing the wrapper): an ungranted as-owner send succeeded
— confirming the pre-fix gap was real. Granted send via the wrapper: succeeded, confirmed posted as
the owner by reading the message back. Ungranted refusal from outside the grant's scope: exits 2
with `as-owner-write-refused`; confirmed no network call precedes it by pointing
`HTTP_PROXY`/`HTTPS_PROXY` at an unroutable address — byte-identical output, exit 2, 0.128s wall
time (a real network attempt through a black-holed proxy would hang, not return instantly). Bot
sends (`--workspace ignite`) unaffected from both in-scope and out-of-scope cwd. `search --workspace
ignite-owner` (a read verb) ungated, works from an out-of-scope cwd with no grant. Daemon
token/chat-bridge config files confirmed untouched (mtimes predate this session). Not deployed.

## ATTENTION
1. A caged seat granted `stools` will currently fail to exec into the real `stools.py` tree, because
   the wrapper's directory and `stools.py`'s directory are ro-bound separately by `spawn.js`'s
   single-directory bind rule — untested, unresolved, needs an orchestrator/owner call before
   caged seats are trusted to hit this gate. 2. `exposure.csv`'s pointer change only takes effect
   for caged/daemon-lane seats after `rbtv ignite daemon deploy` — the mirror tree they resolve
   entry points from is derived, not live. 3. `stools.py`/`auth.py` are deliberately unmodified —
   the gate lives entirely in the wrapper in front of them; do not add a second gate inside
   `stools.py` itself.
- caged seat granted stools cannot exec the real stools.py tree (spawn.js ro-binds only the wrapper dir)
