# 20260831-i-parked-wait-is-incomplete-not — Parked wait is incomplete not renew

kind: issue
component: coord
date: 2026-08-31
commit: 86e276df
deployed: no
pin: ignite/coord/probes/probe-checkout-disposition.py

## Observed

On 2026-08-19 ~00:42–00:47, goal `system-health` seat `plan-completeness-reviewer` parked an owner ratification ask and chose `checkout --renew` because protocol offered only done/incomplete/renew. The lifecycle executor's renew path relaunched immediately (no delay, no wake). Four ~70s full-session cycles ran before the owner interrupted. Separately, paneless daemon-lane sittings that polled for a relay or "stayed up until X" died `failed`/`crash` after check-in and spent a relaunch-budget attempt (`stools-canvas-audio-elevenlabs-close` reach-prover/key-steward; `meet-transcript-summarizer-planning` leader `eb4e4a39`). Deployed daemon copy is inert until deploy; this landed on repo HEAD `86e276df`.

## Mechanism

`cmd_checkout --renew` always called `fork_lifecycle_renewal` with no delay and no wake-on-event. `--incomplete` stamped seat-voice incomplete `armed=1`, which class-A relaunches. A posted unanswered owner ask gated only the `done` path (D8, and only `fallback: block-and-queue`). Protocol never named a parked wait, so seats either busy-renewed or stayed up until the harness ended the turn.

## Attempts

First attempt held — checked: D8 already refuses `done` on posted owner asks and points at `--incomplete`; D33(a) relaunches armed incomplete; D44 stuck after two attempts; `writers.js` forbids a seat stamping incomplete disarmed (`blocked-on-human` is system-voice, named_event `ask-answered`). Delayed renew was rejected because it still burns sittings and does not cover paneless stay-up. A new `--park` flag was rejected so `--incomplete` and `--renew` stay the only opposite pair.

## Fix

One mechanism: parked wait is `--incomplete`, never `--renew`, never stay-up. `--renew` is refused while this seat has posted open owner asks. That `--incomplete` stamps system-voice `blocked-on-human` (armed=0 until `ask-answered`). Relay/ending-stamp waits without an owner-ask row stay ordinary armed incomplete (leader/watcher re-runs; sitting ended, not crashed). Protocol, briefing-authoring, briefing-template, and checkout help agree. Owner-status scaffolding was not seeded (new convention, owner-gated).

## Consequences

`--renew` for context-refresh is unchanged when no posted owner ask exists (probe R41 red-shape still forks immediately). D8's done-hold stays `block-and-queue` only. `lifecycle_exec.py` was not edited (no delay, no placement). Paneless `--renew` successor placement remains task 4.

## Verification

`python3 -B probes/probe-checkout-disposition.py` 17/17 green (R41 refuse+park+one re-arm per reap; R159 incomplete not failed/crash). `coord.py selftest` arms `park-wait 41` and `park-wait 159` all ok; the suite later ABORTED at the pre-existing `capg/seat.md` FileNotFoundError (same abort finish-no-leader already recorded). Not deployed.

## ATTENTION

- A seat may not stamp incomplete disarmed; owner-wait park must go through `stamp_system` + listed diagnostic `blocked-on-human`, or the store refuses.
- `int(row.get("armed") or 1) == 0` is always false when armed is 0; test armed with an explicit None check.
- Do not fold paneless `--renew` placement or owner-status scaffold-seeding into this door.
- Seat cannot stamp incomplete disarmed; owner-wait park is stamp_system blocked-on-human.
- int(armed or 1)==0 is always false when armed is 0.
- Do not fold paneless --renew placement or owner-status scaffold-seeding into this door.
