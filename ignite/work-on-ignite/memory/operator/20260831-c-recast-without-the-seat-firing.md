# 20260831-c-recast-without-the-seat-firing — recast without the seat firing request

kind: creation
component: operator
date: 2026-08-31
commit: c7673276
deployed: no
pin: ignite/operator/master-profile/probes/probe-master-profile.py

## Motivation

`request` stages into the seat's own sandbox-scoped `settings-requests` inbox and is run only by that seat. A sitting that crashes before any tool call (~7s, pre-checkin) can never fire `request`, so recovering its harness/model/effort was structurally impossible without an out-of-band sheet edit. Task 99 of redesign-continue-1; evidence in scaffolding-blockers meet-merged.md. Distinct from task 164 (alias vs pin).

## Design

A new `recast` verb on the same tool: validate + `bindings.cast_seat` + `_repass` with `--bindings`, no inbox, no `add-job`. Leader or owner invokes it from a console. `request` is unchanged. Rejected: letting another actor fire `request` into the crashed seat's inbox (that folder is the seat's write scope). Rejected: teaching spawn to read the sheet (D2).

## How it works

`rbtv-master-profile recast <harness> <model> [--effort N] [--package P] [--bindings F] [--seat S]`. Defaults aim at this workspace's standing `_channel-master` package. A re-render rc≠0 returns `ok: false` with the sheet already written — same fail-loud rule as `apply`. Next launch reads the new `seat.md` frontmatter via `launchSpecForSeat`.

## Consequences

The self-fire path (`request` → daemon `apply`) is untouched; probe checks 1–11 still pass. Recast does not enqueue a fire-tool job. A named seat other than channel-master needs `--package` and `--bindings` from the caller — this tool still does not invent a workflow sheet path (`rbtv-bindings set` remains the workflow writer).

## Verification

Probe check 13: empty inbox (no request file), `recast opencode xai/grok-4.6`, sheet updated, stub materializer ran with `--bindings --refresh`. Full `probe-master-profile.py` PASS. Deployed: no.

## ATTENTION

- `recast` writes the sheet immediately. It is a leader/owner console verb, not a caged-seat verb. Do not route it through the seat's `request` inbox.
- The next sitting is live only after the `--bindings` re-render returns 0. `show` will already display the new sheet.
- recast writes the sheet immediately — leader/owner console verb, not a caged-seat verb
- the next sitting is live only after the --bindings re-render returns 0
