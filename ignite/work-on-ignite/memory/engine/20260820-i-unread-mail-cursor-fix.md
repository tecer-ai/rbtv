# 20260820-i-unread-mail-cursor-fix — Unread mail cursor fix

kind: issue
component: engine
date: 2026-08-20
commit: 2233233a
deployed: yes
pin: engine/probes/probe-reconcile.js (D35 arms)
seeded: true

## Observed
On 2026-08-20 the resolve-and-refresh RCA (s1 census) measured `classB=["leader"]` on every reconcile pass of both live production goals — 144 passes / 6 h — while meet's leader had already named the parse (bus escalation #597 at 10:12Z; stools #161 still open). First observable sitting was 2026-08-19 21:29:05Z, six minutes after `808902df` introduced `checkinOf`. Live unread counts were 238 messages on meet and 72 on stools. Class B is the watcher predicate that treats unread staff-chair mail as owed work and enqueues the chair itself (`unread:<seat>:<lastNum>`) on the ~300 s `CADENCE_MS` tick. The same day's panel-diag briefing, quoted by `system-problems.md` §4, costed a 356-sitting / 806M-token burn to this type mismatch; class A also fired on 100% of those 144 passes, so a B-only fix was already known not to stop the loop. At measurement the deployed engine still ran `Number(checkin)`. After `2233233a` (16:21:41Z) and the ~16:22Z restart the daemon loaded the stamp compare. HEAD still carries that compare; the same filter later gained D70's `SYSTEM_MAIL_SENDER` exclusion.

## Mechanism
`coord.py` `session_checkin` has only ever written `sessions.csv.checkin` as a minute timestamp (`now()`, `"%Y-%m-%d %H:%M"`, e.g. `2026-08-19 12:30`). `checkinOf` as landed in `808902df` did `const n = Number(raw); return Number.isFinite(n) && n >= 0 ? n : 0`. `Number("2026-08-19 12:30")` is `NaN`, so every chair's cursor was permanently `0`. The class-B filter then treated unread as `m.num > cursor`, so every historical message to the chair compared `> 0` and re-owed the chair on every pass. The only selftest fixture at landing was `checkin: '0'`, which hid the type error. RCA s8 found no alternate read-cursor anywhere.

## Attempts
First attempt held — checked: `git log --before=2026-08-20` on `reconcile.js` (four commits; `checkinOf` appears only in `808902df` and then in `2233233a`); `redesign-plan/decisions.md` D-entries before D35; `fix-inventory.csv` (only the D35 row names this bug). The RCA design table (row 7) listed four paper options the owner then ruled among — not earlier code trials.

## Fix
D35 (owner, D32–D38 block): unread mail for a chair = messages recorded after that chair's last check-in timestamp. `checkinOf` now returns the raw `checkin` string, or `started` if that cell is empty, or `''` if there is no row — no numeric coercion. The class-B filter compares with the module's existing `tsAfter(m.ts, since)`; `!since` still means all mail, the pre-D35 empty-cursor behaviour kept on purpose. Chosen over asking coord for a read cursor (premise unverified — s8 found none), adding a `mail-cursor` column stamped at checkout, or storing a cursor on the bus: it reads the column the way its one writer already writes it and invents no new home. Accepted cost, named in the ruling: one redundant wake for mail that arrived mid-sitting. Landed in `2233233a` with D33a and D34 in the same deploy (D38 sequencing; sibling `20260820-i-watcher-retry-policy.md` owns D34).

## Consequences
The same commit also split class-A by word (D33a), changed the strike counter to measure no-progress (D34), and deleted the dead `classC` parse that read a `sessions.csv` reason column the file never had — those are not this bug. D35 did not end the burn class it caused: `dead-sittings-diagnosis-2026-08-21.md` measured the cleanest 5-minute run entirely after the fix, with `classB:[]` on every pass — 18 meet-leader sittings, 27.2M input tokens, owed set unchanged for 17 passes — ended only when D42 (`e3fc940f`, 19:23:47Z) made owed-ness consumable via HOLD. Stools' 5-min cadence broke at D35 + the 16:22Z restart; meet's burn ended 2 h 2 min later. The same diagnosis named the missing durable guard — one typed contract for every ledger cell the watcher consumes, plus a fixture fed from real `session_checkin` output — and it was not built here. Later `affceae2` (D70, 2026-08-22) excluded system-written mail from the same unread filter so the brake's own `stuck` note could not re-arm class B.

## Verification
`reconcile.selftest.js` D35 block: four fixtures (checkin between messages / after all / no checkin + `started` fallback / no row) assert unread counts 1 / 0 / 2 / 3. Immediate red-by-mutation arm restores `m.num > (Number(since) || 0)` and asserts all 3 messages unread. Commit self-report: `probe-reconcile` PASS, `probe-suite --only reconcile` GREEN, `--only verdict-vocabulary` GREEN. Commit 2026-08-20 16:21:41Z; deployed yes (same-day ~16:22Z restart; the 2026-08-21 diagnosis confirms deployed tree = repo = `ac1c08d8` and `checkinOf` returning a stamp). Pin: `engine/probes/probe-reconcile.js` (D35 arms).

## ATTENTION
- Closing D35 does not close the "watcher burns tokens without progress" class. After `classB:[]`, class A (non-terminal last rows) and later EROFS `exited` rows reproduced the same 300 s cadence; the 18-sitting / 27.2M post-fix run ended only at D42 (`e3fc940f`). A similar future symptom is a sibling driver until proven otherwise, not evidence this stamp compare regressed.
- `coord.py` `session_checkin` and `reconcile.js` `checkinOf` still agree on the `checkin` cell's format only by convention. There is no shared schema. A writer-side change of that stamp (precision, timezone, empty meaning) silently reopens either a NaN-style collapse or the `!since` → all-mail hole. The RCA's recommended fixture drawn from the real writer's output was not part of this commit.
- One extra wake for mail that arrives mid-sitting is the cost D35 accepted in exchange for not adding a cursor column. It is not an incomplete watermark.
- The unread filter later also drops `SYSTEM_MAIL_SENDER` (D70, `affceae2`). Removing that exclusion makes the brake's own `--as ignite-daemon` `stuck` note look like new mail and re-arms class B on the chair it is reporting on.
