# Review 01 — Fix Map (RBTV Slide-Library Convention v1)

**Fix-cycle agent.** Date: 2026-06-06. Inputs: `review-01-contract.md` (5 BLOCKER · 7 MAJOR · 6 MINOR, verdict NO-GO). Edited in place: `slide-library/docs/convention-spec.md`, `slide-library/docs/fixture-spec.md`. Live source verified READ-ONLY: `5-workbench/tecer-biz/slide-library/assemble.py`, `manifest.md`, `presets.md`. tecer-biz strictly read-only; ADX section untouched.

**Binding directions applied:** orchestrator directions OVERRIDE the reviewer where they differ (noted per row). All grammar/parse rules verified against live `assemble.py` behavior.

---

## BLOCKERs

| RV | What changed | Where (file · section) | Verification |
|----|--------------|------------------------|--------------|
| **RV-1** | PINNED a normative "library-YAML subset" grammar (one fenced grammar block) shared by presets AND as-built entries: plain scalars; double-quoted scalars unwrap to content; inline flow lists `[a,b,c]` of plain scalars (`:` FORBIDDEN in elements); block lists where each `- ` line is ONE PLAIN STRING never re-parsed as a sub-mapping; `#`/blank ignored. Stated the ENGINE implements a FRESH parser to this grammar (NOT a port of tecer's `_parse_yaml_block`); the writer emits only constructs in the grammar. `engine_version: "1.0"` quoting round-trips (unwraps to `1.0`). Empty deviation set is `deviations: -` (NOT `[]`). Added round-trip invariant `parse(write(entry))==entry`. Updated § 3.1 to reference the shared grammar. | convention-spec § 4.1 (new grammar block + 7 rules + round-trip invariant); § 3.1 (preset parse refs grammar); § 4.5 (hand-parse note); § 8 check-23; § 8.1 divergence #2; § 9.1 (as-built extraction in subset); § 9.5 (round-trip migration validation). fixture-spec § D (seed `deviations: -`); § H step 11 (round-trip self-check); § I rule 23 (`:`-in-flow-element negative). | Read live `_parse_yaml_block` (assemble.py:146-181): confirmed list-parse ONLY for `slides`, every other key `result[key]=value` scalar, quotes kept literally — so tecer cannot round-trip block lists/quoted scalars. Wrote a reference parser to the PINNED grammar and hand-parsed the § 4.5 example, fixture seed, both presets: all consistent; `deviations: -`→"none"; `engine_version`→`1.0`; `:`-in-flow-element rejected. (BINDING direction's grammar adopted verbatim; reviewer's option-(a)/(b) superseded.) |
| **RV-2** | FORBADE literal `|` in every manifest cell (incl. `\|` — no escaping for v1). Parse failure die()s naming the offending row id or line. `--check`/validation enumerates it. Migration scans all 57 tecer rows for pipes before conversion. | convention-spec § 2.1 (forbid-pipe parse rule); § 2.5 (invalid); § 8 check-5; § 8.1 #3; § 9.1 (57-row pipe scan); § 9.5 (pipe-scan validation). fixture-spec § H step 10; § I rule 5 (mutation: insert `\|` into `cover-nimbus.en` summary → die naming row). | Read `_split_row` (assemble.py:64-72): splits on `|` before any unescape → an in-cell pipe over-counts or silently shifts. Ran a pipe scan over live `manifest.md`: 57 data rows, 0 backslash-pipes — corpus is pipe-free (matches § 9.1 claim). |
| **RV-3** | ADDED entry keys `title`/`accent`/`client_logo` (recorded with RESOLVED values actually used; present when non-default; `client_logo` = copied asset leaf name; `-` when default). § 4.4 reproduction replays them. § 4.5 example shows all three. README templates note they get logged. | convention-spec § 4.2 (3 new keys); § 4.4 step 1 (replay); § 4.5 (example + parse note); § 5.1 README § 4 (logged-fields note); § 8.1 #4. fixture-spec § D (seed `title`/`accent`/`client_logo`); fixture README § 4. | Read README line 346 / assemble.py:272-283,301-303: `--title`/`--accent`/`--client-logo` all affect output. Example hand-parse confirms `accent: "#B8875A"`→`#B8875A`, `client_logo: acme-logo.png`, `title` plain scalar. (BINDING direction adopted.) |
| **RV-4** | PINNED all enum-like values lowercase + matched CASE-SENSITIVELY (exact string): `kind`∈{ready,template}; `lang` lowercase ISO-639-1 token; `section` exact-match a `library.json` `sections` entry. Headings (`## Slides`/`## Assets`/`## Presets`/`## As-built log`) and column headers case-sensitive. Validation rejects miscased/unknown. Migration lowercases tecer's values. | convention-spec § 2.1 (case-sensitive heading + enum rules); § 2.5 (invalids); § 8 checks 2,7,8,9; § 8.1 #5,#6; § 9.1/§ 9.2 (lowercase tecer values). fixture-spec § H steps 9,10; § I rules 2a,2b,7,8,9. | Read assemble.py:91 `stripped.lower()=="## slides"` — live is case-INsensitive; pinned the divergence (engine must be case-SENSITIVE). (BINDING direction adopted; promoted to the strict rule the reviewer + ORCH wanted.) |
| **RV-5 (+RV-12)** | REWROTE § 4.4 DT5 bar as a MECHANICAL property procedure: (1) slide ids+order == entry `slides`; (2) per-slide tag/class skeleton equality vs original, text of token-bearing nodes EXCLUDED; (3) asset-filename-set parity + all refs resolve; (4) `--check` reports exactly the expected unfilled tokens; (5) headed render, theme applied, zero console errors. "Upgraded canonical copy" deviation acceptable ONLY with git-evidenced fragment change in-window; EMPTY by construction immediately post-migration. NO golden-byte files — property-based. Seed `output` documented as HISTORICAL SENTINEL (file need not exist). RV-12: `output` defined library-root-relative; default OUTPUT_PATH `../decks/{slug}/{deck}.html` for the cold agent; as-built confirmation step added. | convention-spec § 4.2 (`output` relative + sentinel); § 4.4 (full mechanical bar); § 5.1 README § 4 (default OUTPUT_PATH + confirm-log step); § 8.1 #9. fixture-spec § D (seed sentinel note, no committed expected-output); fixture README § 4. | ADX-1 A4 reconciliation checked (see FLAGGED §): byte-exact stays a non-goal, structural parity preserved, "visual" survives as the headed-render check (5) — the rewrite REFINES A4 (removes the rubber-stamp escape) without contradicting it; BINDING RV-5 direction mandates exactly this. |

---

## MAJORs (7 applied)

| RV | What changed | Where | Verification |
|----|--------------|-------|--------------|
| **RV-6** | Demoted engine-filled `reordered` (non-decidable prose) to: engine emits `order: true` only (set equal, sequence differs); actual order is always `slides`. Prose `reordered:` kept as agent-only MAY. Engine never fabricates `modified`/`bespoke`/`reordered`. | convention-spec § 4.2 (`order` key); § 4.3 (vocabulary + engine-fills rule); § 4.5 (example `order: true`); § 8.1 #10. | Example hand-parse: `order: true` scalar; engine-decidable `removed: proof-metrics` matches set diff. |
| **RV-7** | Added explicit "DIVERGENCE FROM TECER — do NOT copy-port" callout: engine keys extra-root on literal `@root/` PREFIX, NEVER `/`-presence; a bare `path/with/slash` resolves from `assets/`. | convention-spec § 2.4 (callout); § 8.1 #11,#12. | Read `resolve_asset_source` assemble.py:206 `("/" in entry)`→REPO_ROOT — confirmed the live `/`-heuristic; pinned the inversion. |
| **RV-8** | Added § 8 "Validation Rules (consolidated)" table (24 rows: check · decidable method · ERROR/WARNING · origin), closing the § 7→§ 9 gap. Reconciled fragment-purity set: § 2.5 now lists the full `<head`/`<style`/`<script`/`<html`/`<body` substring-scan set (matches § 6.3). Noted live engine implements none of purity/version/round-trip checks. | convention-spec § 2.5 (full purity set + pointer to § 8); new § 8 table. fixture-spec § H step 7; § I (every § 8 rule → mutation). | Cross-checked § 2.5 set against § 6.3 invariant — now identical 5-element set. |
| **RV-9** | Extended § 6.5 lang precedence to all modes (table): `--preset` = flag>preset>default_lang; `--slides` = flag>default_lang; `--catalog` = default_lang. Added "do NOT copy-port" divergence (live hardcodes `pt`, no `library.json`). | convention-spec § 6.5 (mode table + divergence); § 8.1 #13. | Read assemble.py:424,430,378 — confirmed hardcoded `"pt"` in all three modes, no `default_lang`/`library.json`. |
| **RV-10** | Stated `--lang` NEVER selects/rewrites ids; presets/`--slides` MUST list fully-qualified ids; unsuffixed ids language-neutral; GUI filter rule: match if `lang`==selected OR id has no `.{lang}` suffix. | convention-spec § 2.2 row 1 (`id`); § 5.1 README § 3; § 8.1 #14. fixture README § 3. | Read assemble.py:272 — `--lang` fills `{{LANG}}` only, no id rewriting; pinned consistent with live. |
| **RV-11** | Made title-backfill a deterministic 4-rule fallback chain (`.slide-title` → `.cover-title`/`.divider-statement`/first label → `summary` truncated at first `.`/`;`/`:` or 6 words → humanized id), never blocks; output is a DRAFT with a one-pass human-quality review of all 57 before commit. | convention-spec § 9.1 (manifest row); § 9.5 (chain + review). | Verified against live: `cover-client` (manifest.md:9) has no `.slide-title`→rule 2; dividers→`.divider-statement`. (BINDING: ≤6-word cap + human review adopted.) |
| **RV-F8-misc** | Resolved year-only `date` (3 entries: `tecer-institucional`=2026, `small-deck-v3`/`v3-1`=2026-05) → backfill from the git commit date that introduced each entry line; added optional `retroactive: true` (MAY). Noted manifest row 48 (`cover-investor`) cutover rewrite per ADX-3. Confirmed `bespoke:`-only line (id-less) survives § 4.3; confirmed preset-orphan library slide (`intro-anchors.en`) is not rejected. | convention-spec § 4.2 (`retroactive`); § 4.3 (id-less `bespoke`); § 9.1 (retro extraction); § 9.3 (row-48 cutover edit); § 9.5 (date backfill + bespoke/orphan survival). | Read presets.md:68,90,117 (year/month-only dates), :110 (`bespoke: v3 drops the-ask`), manifest.md:11 (`intro-anchors.en` orphan), :48 (`cover-investor` cross-root). (BINDING: git-commit-date source + `retroactive` adopted.) |

---

## MINORs (6 applied)

| RV | What changed | Where |
|----|--------------|-------|
| **RV-13** | Separator row pinned POSITIONAL (2nd table row), not content-based. Divergence from tecer's `set(...)<=set("-: ")` guard noted. | convention-spec § 2.1; § 8 check-3; § 8.1 #7. |
| **RV-14** | Reject empty MUST cells; named non-empty-required set `id,file,section,title,lang,kind,summary` (`audience`/`assets` sentinels; `provenance` MAY be `-`). | convention-spec § 2.5; § 8 check-6; § 8.1 #8. fixture § H step 10; § I rule 6. |
| **RV-15** | One line: asset filenames have no commas; cells are single physical lines (no embedded newlines, no multi-line handling). | convention-spec § 2.4; § 8 check-16; fixture § I rule 16. |
| **RV-16** | Noted CDN `<link>` block is non-contractual chrome; only the 5 markers are contractual. | fixture-spec § E.1 note. |
| **RV-17** | Fixed fixture "3 ready"→"4 ready" (matrix coverage row + prose count); `nimbus-divider` is the 4th ready. | fixture-spec § matrix (ready row); § 38 prose. |
| **RV-18** | Closed § 8 numbering gap (new § 8 validation table). Added § 5.1 executor note: the README's `## 1`–`## 6` headings are the README's own, copy verbatim, NOT this spec's sections. | convention-spec § 5.1 (executor note); § 8 (gap closed). |

---

## FLAGGED (not applied as-is — ADX reconciliation)

- **RV-5 vs ADX-1 A4 — RECONCILED, applied (not blocked).** ADX-1 A4 ratifies "DT5 bar = structural + visual parity, byte-exact non-goal." The BINDING RV-5 direction mandates a mechanical property bar with NO golden-byte files and no visual-judgment escape. These do NOT conflict: (1) byte-exact remains an explicit non-goal in the rewritten § 4.4 (preserves A4); (2) structural parity is preserved and tightened; (3) the "visual" element of A4 survives as mechanical check #5 (headed render, theme applied, zero console errors) — a binary visual sanity, not a subjective diff. The rewrite REMOVES only the "upgraded canonical copy excuses any diff" rubber-stamp, which A4 never ratified (A4 ratified the *bar*, not the escape). Applied per BINDING direction; no ADX entry altered. No other review fix touches what ADX-1/2/3 rule.
- **No findings were dropped for ADX conflict.** All 5 BLOCKER + 7 MAJOR + 6 MINOR are applied (RV-16 is a documentation note; the reviewer marked it "None required / optionally note" — the optional note was added).

---

## CROSS-ARTIFACT landings (multi-file rules)

Every place each multi-file rule landed, for coherence audit:

| Rule | convention-spec | fixture-spec | README template (in spec § 5.1) | Migration appendix (§ 9) |
|------|-----------------|--------------|--------------------------------|--------------------------|
| **RV-1 grammar** | § 4.1 (block), § 3.1, § 4.5, § 8 chk-23, § 8.1 #2 | § D seed (`deviations: -`), § H step 11, § I rule 23 | (grammar is engine-facing; README unaffected) | § 9.1 (as-built in subset), § 9.5 (round-trip validation) |
| **RV-2 pipes** | § 2.1, § 2.5, § 8 chk-5, § 8.1 #3 | § H step 10, § I rule 5 | — | § 9.1, § 9.5 (57-row scan) |
| **RV-3 title/accent/client_logo** | § 4.2, § 4.4 step 1, § 4.5, § 8.1 #4 | § D seed (all 3 keys) | § 5.1 README § 4 (logged-fields) + fixture README § 4 | — (entry schema flows via § 9.1) |
| **RV-4 enum case** | § 2.1, § 2.5, § 8 chk-2/7/8/9, § 8.1 #5/#6 | § H steps 9,10, § I rules 2a/2b/7/8/9 | — | § 9.1, § 9.2 (lowercase tecer) |
| **RV-5/12 DT5 + output** | § 4.2, § 4.4, § 8.1 #9 | § D (sentinel; no expected-output) | § 5.1 README § 4 + fixture README § 4 (OUTPUT_PATH + confirm-log) | § 9.4 (cutover refs § 4.4 bar) |
| **RV-6 reordered/order** | § 4.2, § 4.3, § 4.5, § 8.1 #10 | (seed has no deviations) | — | § 9.1 (deviation lines preserved) |
| **RV-7 @root prefix** | § 2.4, § 8.1 #11/#12 | (fixture § B exercises `@root/partner-mark.png`) | — | § 9.3 (ADX-3 cutover, row-48) |
| **RV-8 validation table** | § 2.5, § 8 (24 rows) | § H (self-checks), § I (mutation per rule) | — | — |
| **RV-9 lang precedence** | § 6.5, § 8.1 #13 | § I rules 20-22 (version), default_lang via library.json | — | § 9.1 (library.json default_lang: pt) |
| **RV-10 lang≠id-selection** | § 2.2 row 1, § 8.1 #14 | fixture README § 3 | § 5.1 README § 3 | § 9.2 (lang row) |
| **RV-11 title backfill** | § 9.1, § 9.5 | (fixture titles authored, not backfilled) | — | § 9.1, § 9.5 (chain + human review) |
| **RV-F8-misc** | § 4.2 (`retroactive`), § 4.3 (id-less bespoke) | § I rule references | — | § 9.1, § 9.3 (row-48), § 9.5 (date/bespoke/orphan) |
| **Divergences table** | § 8.1 (19 rows — all RV + ADX divergences) | (engine-port reads § 8.1) | — | § 9 references § 8.1 |
| **§ 9.3 ADX-3 alignment** | § 8.1 #12 | — | — | § 9.1 (library.json row), § 9.3 (BINDING vendor path, ALTERNATIVE removed) |

---

## Self-verification results

- **Grammar hand-parse (§ 4.1 vs § 4.5 vs fixture):** PASS. Reference parser of the pinned grammar parsed the § 4.5 example, fixture seed, and both fixture presets consistently. `engine_version: "1.0"`→`1.0` (quotes stripped); `accent: "#B8875A"`→`#B8875A`; `deviations:` block list = 3 verbatim strings; seed `deviations: -`→"none" (NOT `[]`/`['']`); `:`-in-flow-element correctly rejected. **Coherence:** § 4.5 `removed: proof-metrics` ⇔ `proof-metrics` absent from `slides`, and `slides` set == `product-intro` preset minus `proof-metrics`. **Seed↔preset:** seed `slides` == `nimbus-intro-en` preset `slides` (7 ids) — AGREE.
- **10-column header grep:** 4 occurrences, all character-identical column sequence — convention-spec:143 (manifest table), convention-spec:391 (README § 5.1 inline), fixture-spec:113 (manifest table), fixture-spec:747 (fixture README inline). Two table-form + two inline-code-form; sequence identical across all.
- **Stale-language sweep:** no `deviations: []` outside the explanatory rule that forbids it; the old engine-fills-`reordered` prose is fully replaced; § 2.2 schema header intact (`id`@1 … `provenance`@10).
- **Live-source basis:** RV-1/2/4/7/9/10/11/F8 verified by reading `assemble.py` (`_parse_yaml_block` 146-181, `_split_row` 64-72, `resolve_asset_source` 188-210, heading match :91, lang fallbacks :424/:430/:378, `--lang` fill :272) + `manifest.md` (57 rows, row-48 cross-root) + `presets.md` (11 retro entries, year-only dates, id-less bespoke, orphan slide). tecer-biz strictly read-only.
