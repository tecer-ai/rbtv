# V4-T10 Post-Commit Review — R14 agent-anchor stamping + legible head block

## Scope
- Commit A: `12d44ae4c08aa53a918b11b18c49ffb38a084948` — `[v4-t10]` agent-anchor stamping + legible head block (transient live-stamp, self-cleanup directive).
- Commit B: `045fbb39b27e43888829cde4eee228e7d2516cf5` — `[v4-t10-fix]` D4-aware amendment of two pre-existing test gates.
- Reviewer mode: READ-ONLY on code; read-only git; no mutations. Halt chain: changelog rows 218→224; ADX-7 = row 221.
- Date: 2026-06-05.

**VERDICT: CLEAN** — all findings ≤ MINOR. Both commits faithfully implement R14 spec contracts 1–8 and the ADX-7 / V4-T10c test-side resolution. The two amended gates retain every tooth except the single intentional `data-hyp-agent` exemption mandated by D4.

---

## 1. Transient live-stamp in `serialize()` (spec §R14 contract 4, S3-13, I4)

**1.1 — Stamp-before-clone by anchor identity. PASS.**
`serializer.js:253` builds `stampMap = agentStampMap()` (DOM reads only, no mutation) BEFORE the `try`. Inside the try, `:257-260` clears every live `[data-hyp-agent]` (stale/reopened residue), `:262-264` stamps current ids (`liveEl.setAttribute("data-hyp-agent", ids.join(" "))`), and `:266` `cloneNode(true)` follows. Stamp is applied to the LIVE element by identity (the exact `agentStampMap` element), never via `resolveCloneNode` index walk (spec §R14 review-F3 prohibition honored). `agentStampMap` (`comments.js:638-648`) resolves each unresolved agent thread via `matchAnchorHighConfidence` — levels 1 (`data-hyp-hook`, unique) and 2 (`nativeId`+path-walk+`contentHash`) ONLY, with `return null` on fall-through (`comments.js:634`). This is the G6 high-confidence gate: no fuzzy level-3/4/5 match can stamp. Verified strict equivalent of spec change-map row for `agentStampMap`.

**1.2 — Strip-exemption for `data-hyp-agent` ONLY. PASS (quoted).**
`stripClone` Phase-B attribute loop, `serializer.js:180-184`:
```js
for (const attr of attrs) {
  if (attr.name.startsWith("data-hyp-") && attr.name !== "data-hyp-agent") {
    el.removeAttribute(attr.name);
  }
}
```
Exactly one attribute is exempted. `data-hyp-id` is still removed by `stripIds(clone)` at `:169` (unchanged) AND would be caught by this loop; `data-hyp-hook` and any other `data-hyp-*` are removed here. No other `data-hyp-*` survives. Confirmed: no second exemption anywhere in the file.

**1.3 — `finally`-unstamp on ALL exit paths incl. mid-serialize exception. PASS.**
The `try` opens at `:256`; the clear+stamp mutations (`:257-264`), clone (`:266`), strip (`:275`), island re-embed (`:279-289`), agent-block insert (`:293-300`), and the node-count-guard `return null` (`:316`) are ALL inside the try. `finally` (`:318-323`) unconditionally removes every live `[data-hyp-agent]`. Traced exit paths: (a) guard-fail `return null` → finally runs; (b) exception in `cloneNode`/`stripClone`/`insertAdjacentHTML`/`getCommentJson` → finally runs; (c) normal completion → finally runs, then `:326` returns the string. The only pre-try statement (`:253` `agentStampMap()`) performs no mutation, so an early throw there leaves nothing to clean. Live DOM is provably zero-residue on every path (spec contract 4, I4 history-safety).

**1.4 — Post-save live DOM provably clean (test asserts count 0). PASS.**
`test_r14_agent_stamping.py:251-252` (E-R14-4): `doc.querySelectorAll('[data-hyp-agent]').length` asserted `== 0` immediately after save. E-R14-8 repeats the live-clean assertion at `:368-369` BEFORE reopen. Both are DOM-scoped `querySelectorAll` counts on the live iframe document — the honest probe.

## 2. Head-block format vs spec §R14 contract 3 / S3-15

**2.1 — Per-thread entry shape. PASS.**
`comments.js:671-698` emits, per unresolved agent thread, in order: `[agent:<id>]` (`:673`), `target: [data-hyp-agent~="<id>"]` (`:686`), `context: <tag> .<classes> | "<≤80 excerpt>"` (`:687-691`), `instruction: <body>` (`:692`), `reply: <body> — <author>` per reply (`:693-695`), `author:` (`:696`), `date:` ISO (`:697`). Exact match to spec contract-3 ordering. `context:` tag+non-`hyp` classes built at `:676-685` via `matchAnchor`; unresolved → `context: (unresolved) | "<excerpt>"` (`:690`). Verified against fixture: `<p class="lead" id="p-lead">` yields `context: p .lead | "..."`, asserted literally by E-R14-5 `:264`.

**2.2 — `target:` carries a copy-pasteable `[data-hyp-agent~="<id>"]` selector. PASS.**
`:686` emits the `~=` whitespace-token selector for every entry. Single-id and multi-id elements both resolve identically (spec contract 2). Asserted: E-R14-1 `:164`, F5-7 `:169`, legibility-1 resolves each extracted `target:` via `querySelector` on a fresh `file://` page (`:162-169`).

**2.3 — Self-cleanup directive. PASS.**
Block preamble `:668-670`: `"After applying an instruction, remove the data-hyp-agent token for that id from the target element and delete this entry."` Instructs BOTH attribute-token removal AND entry deletion (spec S3-15). Asserted: E-R14-1 `:165`, E-R14-5 `:269`, legibility-2 `:213`, and legibility-2 `:243-264` actually executes a per-id token removal and proves it is non-destructive to the sibling id (`post0==0`, `post1==1`).

**2.4 — Multi-thread same element = space-separated ids + `~=` selectors. PASS.**
`agentStampMap` (`comments.js:643-645`) pushes multiple ids under one element key → `ids.join(" ")` → `data-hyp-agent="id0 id1"`. E-R14-2 `:194` asserts the attribute value equals `"{id0} {id1}"` exactly, `:198` asserts two `[agent:` entries, and `:203-206` asserts each `~=` selector resolves the single shared element. S3-14 satisfied.

## 3. Idempotence + resolve/delete removal (spec contract 5 & 6)

**3.1 — Two consecutive saves produce identical stamping (no accumulation). PASS.**
E-R14-6 (`test_r14_agent_stamping.py:272-311`): save → fresh-page `querySelectorAll('[data-hyp-agent]').length == 1` (`:286`); reopen the saved file; save again → fresh-page count `== 1` (`:301`); attribute value `== id0` (`:308`); exactly one `[agent:` entry (`:311`). Code basis: `serialize()` step-1 clear (`:257-260`) removes the reopened file's prior stamp BEFORE cloning; step-2 re-applies only current-unresolved ids; stable island id re-derives the same value. No id accumulation. Matches spec contract 6.

**3.2 — Resolve-then-save and delete-then-save remove stamp AND block entry. PASS (quoted).**
E-R14-3 (`:208-243`):
- Resolve id0 → `self.assertNotIn(f'data-hyp-agent="{id0}"', textR)` (`:227`), `self.assertNotIn(f'data-hyp-agent~="{id0}"', textR)` (`:228`), `self.assertNotIn(f"[agent:{id0}]", blockR)` (`:230`); id1 still present (`:231`).
- Delete id1 → `self.assertNotIn(f'data-hyp-agent="{id1}"', textD)` (`:240`), `self.assertNotIn(f'data-hyp-agent~="{id1}"', textD)` (`:241`), `self.assertNotIn(f"[agent:{id1}]", blockD)` (`:243`).
Code basis: both `buildAgentBlock` (`comments.js:656`) and `agentStampMap` (`comments.js:641`) filter `agentInstruction === true && resolved !== true`; a resolved/deleted thread is absent from both sets and the clone is rebuilt each save (spec S3-16, contract 5). R13 delete path (`comments.js:545-563` `deleteComment`) removes the thread from `threadStore` so the next save's map/block omit it. F5-11 (`test_f5_comments.py:223-240`) independently asserts a resolved agent thread removes the whole block (delete-path twin: F5-8 `:181-187`).

## 4. ADX-7 test edits (changelog row 221) — strict-equivalent, not weakening

**4.1 — DOM-scoped stamp assertions are strict equivalents. PASS.**
The old `text.count("data-hyp-agent") == 1` (per BUG.md §1) over-counted the 3 legitimate substrings (attribute + `target:` selector + cleanup directive) — an impossible constraint given the spec REQUIRES all three. The replacement loads the saved file in a fresh `file://` page and asserts `querySelectorAll('[data-hyp-agent]').length == 1` (E-R14-1 `:147-149`, E-R14-6 `:284-286`/`:299-301`). This is STRICTER than the substring count (it proves exactly one DOM element bears the attribute, not merely a substring tally) and is the honest fresh-agent modality. Not a weakening. E-R14-8 `:367-369` correctly splits the previously conflated saved-stamp (count 1) vs live-clean (count 0) into two distinct DOM states (BUG.md §3 contradiction resolved).

**4.2 — Legibility tests load via `file://` with a page-load assertion. PASS.**
Legibility-1 `:154-157` navigates `file://<abspath>` (`wait_until="networkidle"`) and asserts `body_exists` page-load BEFORE any selector resolution. The dead `/doc/` 404-fallback (BUG.md §4 — `page.goto` does not throw on 404, so the file:// branch never ran) is gone; navigation is `file://`-first. Legibility-2 `:230` already used direct `file://`. Page-load assertion present in both.

**4.3 — Harness proves head-block-ALONE resolution (no island parsing). PASS.**
Legibility-1 `:137-146` extracts ids + `target:` + `instruction:` by regex from the EXTRACTED HEAD BLOCK ONLY (`_extract_head_block` `:121-123` slices the `===== ... =====` comment region). It never reads `#hyp-comments`. Each extracted `target:` is then run as `document.querySelectorAll(sel)` on the fresh page and asserted to resolve to exactly one element whose `outerHTML`/`textContent` matches the intended anchor (`:160-176`). Criterion-4 (`:178-197`) injects a sibling `<p>` into `#sec-ops` and re-asserts every selector still resolves to the one correct element — proving position-independence (attribute selector, not structural path). This is a genuine standalone-agent proof.

## 5. Amended gates kept their teeth (commit B / V4-T10c)

**5.1 — `test_exit_smoke` chrome-free gate still fatal on any other residue. PASS (quoted).**
`test_exit_smoke.py:242-247`:
```python
all_data_hyp = set(re.findall(r'data-hyp-[a-z-]+', text))
leaked = all_data_hyp - {"data-hyp-agent"}
self.assertEqual(leaked, set(), f"saved file must not contain non-agent data-hyp- residue: {leaked}")
```
The set-difference exempts ONLY `data-hyp-agent`; ANY `data-hyp-id`/`data-hyp-hook`/etc. lands in `leaked` and fails. The other gate teeth are UNTOUCHED: `id="hyp-comments"` count `== 1` (`:250`), zero `class="…hyp-…"` tokens (`:253-255`), zero `/runtime/js/runtime-main.js` (`:258`), sample inline `onerror=` preserved (`:262`). Injected-script/style removal is enforced by the runtime-script and hyp-class checks (the only chrome the serializer injects is `hyp-`-classed/ided per I3). The exemption is a no-op when no unresolved agent thread exists (no `data-hyp-agent` is produced → `leaked` trivially empty) — a closed exemption, not a hole; the test always seeds one agent-tagged comment (`:227-231`) to exercise it.

**5.2 — `test_f5_comments` format-only update, same strictness. PASS (diff-verified).**
`git diff 12d44ae..045fbb3 -- test_f5_comments.py` changes EXACTLY two lines (`:169-170`): `assertIn("anchor:", html)` → `assertIn("target: [data-hyp-agent~=", html)` and `assertIn('| id="', html)` → `assertIn("context:", html)`. Every other assertion in `test_save_as_includes_agent_block_first_in_head` is untouched: sentinel (`:163`), preamble (`:164-167`), `[agent:` (`:168`), `instruction: Replace bullets` (`:171`), `author:`/`date:` (`:172-173`), and the head-first ordering `agent_idx < link_idx` / `< style_idx` (`:175-179`). Format update only; strictness preserved; no other test method touched.

## 6. Regression sweep

**6.1 — Serializer node-count guard unaffected. PASS.**
Guard block (`serializer.js:303-317`) is byte-identical to pre-R14 logic, now merely relocated inside the `try`. Stamping sets ATTRIBUTES; `countAllNodes` (`:61-68`) counts nodes via `TreeWalker`, so `preCount`/`postCount`/`expectedPostCount` are unchanged (Risk-3). E-R14-7 (`:313-331`) saves with 3 agent stamps, asserts `#shell-status` contains "Saved" and the file is non-empty (`:323-326`) — i.e. no guard abort — and finds 3 stamp attributes (`:330-331`). Run evidence: full unscoped suite 155 passed / 1 skipped / 0 failures (`v4-t10-run.txt:17-20`).

**6.2 — Non-agent save residue. PASS with MINOR coverage note (F-1).**
Code path is provably inert for a no-agent save: `agentStampMap` returns an empty `Map` (loop body never runs) → no stamp applied; `buildAgentBlock` returns `null` when `agentThreads.length === 0` (`comments.js:658`) → no block inserted; the `finally` is a no-op. F5-8 (`test_f5_comments.py:181-187`) proves a non-agent save emits NO agent block. **Gap:** no test asserts that a pure no-agent-comment save contains ZERO `data-hyp-agent` attribute residue or is byte-identical to pre-R14 output. The existing chrome-free gate (5.1) always seeds an agent comment, and E-R14-3 only asserts absence for a *specific resolved/deleted id*, not a clean no-agent baseline. Severity MINOR — the absence is guaranteed by the empty-map / null-block code paths and indirectly covered by F5-8, but it is not directly asserted.

---

## Findings table

| # | Finding | Severity |
|---|---------|----------|
| F-1 | No test asserts a pure no-agent-comment save has zero `data-hyp-agent` residue / byte-identity to pre-R14. The behavior is guaranteed by the empty-`agentStampMap` and `null`-`buildAgentBlock` code paths and indirectly covered by F5-8 (no block emitted), but not directly pinned. Optional hardening: add an assertion to an existing no-agent save test (e.g. F5-8) that `assertNotIn("data-hyp-agent", html)`. | MINOR |

No MAJOR or BLOCKER findings. Both commits are spec-faithful and the test resolutions (ADX-7 + V4-T10c) are legitimate strict-equivalents, not gate weakenings.

## Verdict
**CLEAN.**
