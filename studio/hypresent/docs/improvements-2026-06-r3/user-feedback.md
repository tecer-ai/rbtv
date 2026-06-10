# Improvements 2026-06 — Round 3: User Feedback

Session 3 input document. Captured 2026-06-05 from the owner's test pass against `tecer-gsmm-introduction-test.html` (saved with the editor at ~11:26 local). All agents working this round read THIS file — do not re-derive scope from conversation.

## Symptoms reported

### S1 — Resize amplification (BUG, P0 → R10)

Slightly resizing the "A Tecer · estrutura·concilia·aprende" box (flow-diagram row, "Uma plataforma inteligente" slide) resized it by MUCH more than the drag distance.

- Evidence: `C:\Users\henri\Pictures\Screenshots\Captura de tela 2026-06-05 112213.png` (post-bug state: box stretched across nearly the full row, selection handles visible).
- Counter-example that worked correctly: resizing the left column of the 2×2 card grid on the "O que entendemos da GSMM" slide — `C:\Users\henri\Pictures\Screenshots\Captura de tela 2026-06-05 112531.png`.
- Implication: amplification is context-dependent — plausibly different code paths (`width` vs `flex-basis` vs grid tracks). Diagnosis must separate them.

### S2 — Inconsistent resize anchoring (BUG/UX, P2 → R12)

On the "A Tecer se adapta ao cliente" slide (`C:\Users\henri\Pictures\Screenshots\Captura de tela 2026-06-05 112725.png`):

- Leftmost box: dragging the right border resizes only to that side (one-sided — expected).
- Center box: same gesture grows the element to BOTH sides (center stays fixed).
- Owner hypothesis confirmed as desirable feature: symmetric resize is legitimate, but the user must have BOTH options, predictably — not as a layout accident.

### S3 — No guide lines during resize (FEATURE/REGRESSION, P1 → R11)

Guiding/snap lines (like those during move) do not appear when resizing, so elements can't be matched to nearby positions/sizes. NOTE: README §How-to-use claims alignment guides appear during resize — treat as present-but-broken until diagnosis says otherwise.

### S4 — Agent-comment legibility doubt (P4 → R14)

Owner added one agent-tagged comment and inspected the saved `<head>` block. Doubt: can an agent reliably resolve WHICH element a comment targets? Orchestrator inspection confirms the doubt:

- Current anchor line: `anchor: body:1/section:1/div:2 | id="" | "Operações Financeiras Autônomas"` — path notation is undefined in-block (agent must guess nth-child vs nth-of-type semantics), `id=""` is noise, and structural paths go stale the moment the agent's own first edit shifts the DOM (fatal for multi-instruction files).

### S5 — Comments not editable (FEATURE, P3 → R13)

Once posted, a comment cannot be edited. Owner wants post-hoc editing.

## Decisions (locked with owner, 2026-06-05)

| # | Decision |
|---|----------|
| D1 | Resize anchor model: dragged edge tracks the cursor 1:1 (kills amplification). Hold **Alt** = symmetric resize from center on any element. Auto-centered elements still mirror without Alt — honest layout behavior, no compensation CSS. |
| D2 | Resize guides: same alignment-line + magnetic-snap set as move (sibling edges/centers, slide bounds) PLUS equal-size matching (snap + visual hint when width/height equals a nearby element's). |
| D3 | Comments: edit AND delete, for root comments AND replies. Edits propagate to the saved JSON island and the `<head>` agent block when agent-tagged. |
| D4 | Agent anchors: stamp `data-hyp-agent="<id>"` on the target element in the SAVED file; `<head>` block references that attribute (querySelector one-liner). Attribute removed on save once the comment is resolved/deleted. Accepted cost: one attribute of residue per agent comment. |
| D5 | Scope: R10–R14 ALL must-have for session exit. |
| D6 | Logistics: owner AFK after live-debug; Kimi starts/owns the server; per-fix commits on `master`; no push. |

## Worklist (scorecard numbering continues from Session 2's R1–R9)

| ID | Item | Priority |
|----|------|----------|
| R10 | Resize amplification fix — dragged edge tracks cursor exactly in every layout context (width / flex-basis / grid track) | P0 |
| R11 | Resize guides: move-parity alignment lines + magnetic snapping + equal-size hints | P1 |
| R12 | Alt-held symmetric resize (explicit, any element) | P2 |
| R13 | Comment edit + delete (comments & replies), island + agent-block sync | P3 |
| R14 | Agent-anchor robustness: `data-hyp-agent` stamping + rewritten head block + fresh-agent legibility verification | P4 |

## Exit condition (owner-defined)

All R10–R14 checked off in `changelog.md`, each implemented + tested + committed individually, AND Kimi reports a clean, error-free run of the local Python server with the test HTML.
