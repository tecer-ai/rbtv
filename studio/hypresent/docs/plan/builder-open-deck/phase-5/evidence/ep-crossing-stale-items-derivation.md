# Exit-probe finding — stale-items crossing save corrupts the deck (conductor derivation)

**Found by:** conductor exit probes (verification §5), 2026-06-10. **Status:** product defect, root cause derived from data; code-level confirmation + fix dispatched to debug role.

## Observation

- `ep-probe-save1-frozen.html` (builder save-#1, frozen immediately): `[sec1, sec1, sec0, sec2..sec9]` — CORRECT (P3 held, hash-order proof).
- `ep-probe-save.html` (the SECOND save — fired by "Switch to editor"'s Save-As, which consumed the stale test-dialog path and overwrote save-#1's path): `[sec1, sec1, sec1, sec0, sec2..sec8]` — **sec1 ×3, sec9 ("Obrigado") silently DROPPED**. Section count preserved (11), masking the loss from any count check.
- `ep-probe-crossback.html` (editor round-trip of that file): same structure + typed marker — the editor was faithful; the corruption pre-dated it.
- The cold verifier's session-2 `c1-s2-r2-crossback.html` carries the SAME defect shape: `[sec1 ×3, sec3..sec9, blank, lib]` — sec0 replaced by a third sec1. Undetected because the crossback was asserted marker-only.

## Mechanism (index re-application, computed)

After save-new, the builder re-points the current deck to the NEW file but keeps the tray model's stale `index` values (positions in the PRE-save deck). The next save (the crossing's Save-As) sends those stale items against the NEW source:

Conductor probe — old items `[1,1,0,2,3,4,5,6,7,8,9]` applied to new deck (order `sec1,sec1,sec0,sec2..sec9`):
`new[1]=sec1, new[1]=sec1, new[0]=sec1, new[2]=sec0, new[3]=sec2, … new[9]=sec8` → `[sec1×3, sec0, sec2..sec8]`, `new[10]=sec9` never referenced → dropped. **Byte-exact match to `ep-probe-save.html`.**

Verifier session 2 — old items `[1,1,0,3..9,blank,lib]` applied to its new deck (`sec1,sec1,sec0,sec3..sec9,blank,lib`):
`new[1],new[1],new[0]=sec1×3, new[3..9]=sec3..sec9, blank, lib` → **exact match to `c1-s2-r2-crossback.html`'s structure.**

## Why every earlier gate missed it

- p4-checkpoint (B12) round trip crossed WITHOUT a prior save-new — first save maps against the original deck, correct.
- B15 verifier asserted the crossback by MARKER ONLY (a single-token check on a content/order/identity criterion — the count-only weakening class again).
- Suite tests: no test performs save-new followed by a second save in one session.

## Impact

Owner-visible data loss: save a restructured deck, then save again / cross to the editor → a slide silently vanishes and a duplicated slide gains an extra copy. Severity: HIGH (silent data loss on the v1 happy path).
