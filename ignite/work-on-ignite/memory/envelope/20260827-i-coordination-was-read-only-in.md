# 20260827-i-coordination-was-read-only-in — coordination/ was read-only in every caged seat

kind: issue
component: envelope
date: 2026-08-27
commit: 8f299bc6
deployed: no
pin: ignite/envelope/envelope-compiler.selftest.js
components: supervisor,coord

## Observed
Every caged seat on the daemon lane died on its own coordination protocol. On
`scratch-tool-reach-note` (2026-08-27, HEAD 348ebf7e, deployed and live) the
`plan-understander` sitting recorded `OSError: [Errno 30] Read-only file system` on
`<goal>/coordination/workers.md.tmp` at `coordinate checkin`, then the same error on
`coordination/messages.md` at `coordinate send leader --type completion`, then
`refused [coord state]: 'plan-understander' has no ACTIVE roster row` at `coordinate
checkout` — because it had never been able to check in. `/proc/self/mountinfo` inside
the cage showed `coordination/` as its own **ro** bind nested inside the **rw**
goal-folder bind. The sitting finished its work on disk and could not declare it; the
goal's own `issues.md` carries the full trail as `#G-plan-understander-0827-1630` plus
the `#-1643` correction that replaced its first (wrong) diagnosis. The same seat's
protocol item 1 — "check in FIRST" — was unsatisfiable for every caged seat in the
system, unconditionally, not per-seat.

## Mechanism
`ignite/envelope/daemon-owned-records.yaml` listed `coordination` under `directories:`.
`ignite/envelope/compiler.js:188-192` walks that list and pushes an `ro` bind for each
entry under the goal folder, after the family-1 `rw` bind of the goal folder itself;
input order is output order and the last covering entry decides, so the nested `ro`
won. Staff seats (`leader`, `goal-master`, `channel-master`) were unaffected only
because they are not caged at all — `envelope/launch.js:11` `STAFF` and
`supervisor/spawn/spawn.js:1284` return `{uncaged:true}` before any bwrap flag is
composed — which is why the defect read as a seat-grant question for a day.

## Attempts
`#G-plan-understander-0827-1630` was the first attempt at a cause and was RETRACTED by
its own author the same day: it read the symptom as "this seat declares none of the
seven cage grants — no `bus-write`". Acting on it would have added `bus-write: true` to
a seat and changed nothing, because `composeCageFor` builds binds from `admitLaunch` →
`compiler.js` and never mentions `busWrite`. The corrected diagnosis (`#-1643`, a
`diagnoser` fan-out that read the live cage's own bwrap argv off `ps`) is the one this
entry fixes. Checked before editing: 570131d9 (the commit that introduced the list),
`ignite/work-on-ignite/memory/server/20260824-c-plan-time-envelope-compiler.md` and
`20260824-i-envelope-launch-never-punched.md`.

## Fix
`coordination` is removed from `daemon-owned-records.yaml#directories`, so the goal
folder's own `rw` family-1 bind is the innermost one covering it. This is not a
loosening: it RESTORES D3 (2026-08-19), which the sibling files already state three
times — `supervisor/spawn/cage.js`'s header ("D3 rules coordination ledgers writable",
"record forgery is a NON-goal"), `supervisor/spawn/spawn.js:1245`, and
`envelope/spawn-profiles.yaml:135` ("(5) coordination ledgers, WRITABLE"). The ro entry
rode in with the record FILES when the plan-time compiler landed and was never held
against the ruling. `seats` STAYS in the list: peer seat folders are masked absent
(D48), which is a real wall and is separately enforced by `cage.js`'s `ro-mask`.
Rejected: a narrower carve for `messages.md`/`workers.md` alone (those two files ARE
the whole directory on every live goal, so the carve would be the same opening spelled
twice, and it would break the next ledger the protocol adds); adding a per-seat
`bus-write` grant (that vocabulary has zero call sites — the goal's `#-1643` Defect 2);
teaching `coordinate` to refuse politely on a read-only bus (that dresses the symptom).

## Consequences
Every caged seat can now write its own goal's `coordination/` — check-in, check-out,
notes, completions. Nothing outside the goal folder changed: the deny list, the
vault-wide read floor, the credential exclusions and the `seats` mask are untouched,
and staff seats were never caged. `cage-admission.js`'s published rule for a caged
producer's declared output (`coordination/<producer>-<artifact>` when a successor reads
it) becomes satisfiable rather than self-contradictory. The three seat-facing texts
that describe the write surface still need re-reading against this (the goal's `#-1643`
Defect 2 names a "Your write surface" descriptor section that claims to be derived from
the cage and is not) — not touched here.

## Verification
`node ignite/envelope/envelope-compiler.selftest.js` → `PASS planning-zero-fill-in`,
`PASS compiler`. Its pinning row is INVERTED (`coordination dir ro` →
`coordination dir NOT ro`) and paired with a new positive assertion, `innermostAccess(plan,
<goal>/coordination) === 'rw'` — absence of an ro row alone would also read green if the
path stopped being bound at all, which is the same EROFS. RED-CONFIRMED: putting
`- coordination` back makes that arm throw. `node ignite/envelope/probes/probe-cage-
workspace-grammar.js` exit 0; `envelope-launch`, `envelope-shims`, `wall-report`
selftests exit 0; all 25 `ignite/supervisor/spawn/probes/probe-*.js` unchanged
(`probe-tmux-seat-live` is red BEFORE and AFTER this change — pre-existing, "no
ungranted path was present inside the live seat"). Deployed: NO — this is daemon code
and needs `rbtv-ignite` restarted.

## ATTENTION
- The ro bind was invisible to the seat that hit it. `coordinate` answered with a bare
  `atomic_write` traceback, not a named refusal, so the seat could not tell a cage wall
  from a bug in the CLI — and the first diagnosis was wrong because of it.
- Do NOT re-add `coordination` to `daemon-owned-records.yaml` to "protect the bus". The
  bus is append-only and record forgery is a stated NON-goal (D3); what the ro bind
  actually protected against was the seat participating in the run at all.
- `cage.js`'s `SeatBinds` template is NOT the live composer — `composeCageFor` builds
  binds from `admitLaunch` → `compiler.js`. Reading the template to answer "what is
  writable in this cage" gives the wrong answer, and did.
- A seat's own descriptor carries a "Your write surface" section asserting it is derived
  from the cage. For `coordination/` it was simply wrong, and a measured-looking section
  that is not measured is worse than none.
- cage.js SeatBinds is not the live composer — compiler.js is
