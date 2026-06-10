## PB-T17
### Acceptance Criteria 1
- `python migrate_to_convention.py` exits 0; idempotent guard present.
- PASS
### Acceptance Criteria 2
- Header correct: True
- Data rows count: 57 (expected 57)
- cover-investor assets cell: cover-bg.jpg, tecer-logo-white-transparent.png
- Slash-bearing assets: none
- Kind issues: none
- Lang issues: none
- PASS
### Acceptance Criteria 3
- assets/tecer-logo-white-transparent.png exists: True
- PASS
### Acceptance Criteria 4
- convention_version: 1.0
- name: tecer
- default_lang: pt
- extra_asset_root: None
- sections lowercased list: ['opening', 'intro', 'team', 'diagnosis', 'product', 'proof', 'business-model', 'next-steps', 'closing', 'commercial', 'problem', 'market', 'gtm', 'competition', 'ask', 'why-now']
- PASS
### Acceptance Criteria 5
- Heading count: 11 (expected 11)
- Round-trip: True
  OK: tecer-institucional
  OK: small-deck-v3
  OK: small-deck-v3-1
  OK: lgl
  OK: ccn-fup v1
  OK: ccn-fup-v2
  OK: betano
  OK: aimirim
  OK: camu
  OK: gsmm
  OK: jui-py
- All retroactive: True
- All dates full YYYY-MM-DD: True
- PASS
### Acceptance Criteria 6
- presets.md contains no ## As-built log: True
- PASS
### Cross-root asset scan
- Slash-bearing asset cells: none

## TITLE REVIEW (57)

| id | drafted title |
|----|---------------|
| cover-client | Cover/title slide |
| intro-anchors.pt | A Tecer entrega operações financeiras autônomas |
| intro-anchors.en | Tecer delivers autonomous finance operations |
| team-founders | Três fundadores, três frentes complementares |
| pains-structural | Three structural finance pains the counterparty |
| how-tecer-works | Uma camada de inteligência que aprende a operação |
| flow-what-changes | Data-to-decision flow diagram + 3 capability |
| traction-stages | A Tecer se adapta ao cliente, não o |
| two-models | As atividades de um time financeiro, e o |
| how-it-works-internals | Um sistema operacional para agentes financeiros |
| next-steps-timeline | Como avançamos juntos |
| closing-founders | Obrigado. |
| cover-cobranded.pt | Co-branded cover (Tecer × counterparty logo) |
| cover-cobranded.en | Co-branded cover (Tecer × counterparty logo) |
| intro-anchors-flow | A Tecer entrega operações financeiras autônomas |
| understanding-prospect | Baseado na conversa de hoje |
| roadmap-mirror | Counterparty's own roadmap mapped step-by-step to |
| priority-fronts | Dark slide |
| next-steps-paths | Como avançamos juntos |
| client-operation-snapshot | Inventory of the counterparty's live finance |
| workbench-today | Candor slide |
| proposal-summary | Proposal in one slide |
| automation-now-then | Work-stream comparison table |
| context-continuity | Dark slide |
| commercial-comparison | Commercial comparison |
| transition-plan | Dated 4-step vendor-transition timeline + continuity/failure-case |
| founders-detailed | Three co-founders, three orthogonal angles on the same |
| closing-statement | Let's keep building. |
| sector-research-dark | Dark sector-research amplification slide |
| entry-fronts | O que a Tecer faz |
| next-steps-nda-4step | Como avançamos juntos |
| empower-amplify-dark | Dark "we amplify finance without touching |
| frentes-modular | The AGREED execution fronts as 3 |
| next-steps-immersions | Como avançamos juntos a partir desta semana |
| scope-investment | Escopo |
| frentes-poc-pick | Candidate POC fronts as 4 cap-cards |
| next-steps-prototype-gate | Como avançamos juntos |
| scope-investment-priced | Escopo e investimento |
| flow-publi-project | O que a Tecer entrega para {{CLIENT_NAME}} |
| cover-investor | Investor cover |
| problem-why-now | Finance teams stay trapped in work that systems |
| product-layers | One intelligent layer that learns your operations and |
| proof-traction | Built on real operations, validated by real companies |
| market-sizing | $400M to $700M SAM in Brazil, an underserved |
| go-to-market | Direct access to finance leaders, with a channel |
| business-model-pricing | Competing with a hiring decision, not a software |
| competition-matrix | Nobody absorbs operations AND compounds intelligence |
| team-founders-investor | We did this work manually for years. Now |
| the-ask | Raising USD500K to take Tecer past design partners |
| problem-only | Finance teams have the talent: the tools are |
| why-now | The gap from "theoretically possible" to "production-ready" has |
| transformation-before-after | From running finance operations to overseeing them |
| business-model-unit-econ | Competing with a hiring decision, not a software |
| cover-institutional | Institutional cover |
| method-refusals | O que aprendemos a não fazer |
| team-lived-it | A gente já esteve do seu lado da |
| proof-snapshots | O que está rodando hoje |


## Title corrections applied (orchestrator review)

The following 27 ids had their `title` cells corrected per the orchestrator's one-pass human-quality review:

- pains-structural
- flow-what-changes
- traction-stages
- two-models
- roadmap-mirror
- client-operation-snapshot
- transition-plan
- founders-detailed
- frentes-modular
- empower-amplify-dark
- priority-fronts
- context-continuity
- workbench-today
- sector-research-dark
- flow-publi-project
- next-steps-timeline
- next-steps-paths
- next-steps-nda-4step
- next-steps-prototype-gate
- next-steps-immersions
- problem-why-now
- product-layers
- market-sizing
- go-to-market
- team-founders-investor
- problem-only
- why-now

Validation trio re-run after corrections: parse PASS, pipes PASS, roundtrip PASS.

## PB-T18
### Acceptance Criteria 1
- `--catalog-data --json` ok value: True
- Slide count: 57 (expected 57)
- Sections count: 16 (tecer sections)
- Presets count: 5
- PASS
### Acceptance Criteria 2
- library.json engine_version: 1.0
- PASS
### Acceptance Criteria 3
- assemble.py byte-equals canonical engine: True
- PASS
### Acceptance Criteria 4
- README-FOR-AGENTS.md exists: True
- Contains `## 4. How to assemble`: True
- Contains `python assemble.py --preset`: True
- PASS
### Acceptance Criteria 5
- CLAUDE.md contains `README-FOR-AGENTS.md` pointer: True
- CLAUDE.md no longer contains `54 slide`: True
- PASS
### Acceptance Criteria 6
- catalog.html regenerated (newer mtime): True
- catalog.html contains label-bar comment markup: True
- PASS


## PB-T19

### Pre-step
- Added `tecer-logo-white-transparent.png` to manifest ## Assets table (description: Tecer white logo, vendored from brand/ per ADX-3).
- Re-probed `--catalog-data --json`: warning cleared (`warnings: []`).

### Deck identification
- **jui-py** → `### 2026-06-05-jui-py` (11 slides, pt, zero-deviation identity case)
- **camu** → `### 2026-05-21-camu` (11 slides, en, different spine)

### jui-py 5-check verdicts
| check | verdict | notes |
|-------|---------|-------|
| 1 Order identity | PASS | reproduced slide order == entry slides |
| 2 Skeleton equality | PASS | zero-deviation self-consistency: two `--no-log` reproductions have identical tag/class skeletons |
| 3 Asset parity | PASS | assets copied == manifest-referenced set; all resolve on disk |
| 4 Clean token report | PASS | `--check` exit 1; residual token set == expected unfilled template tokens |
| 5 Headed render sanity | PASS | `.slide` class present; 0 console errors; theme.css applied |

### camu 5-check verdicts
| check | verdict | notes |
|-------|---------|-------|
| 1 Order identity | PASS | reproduced slide order == entry slides |
| 2 Skeleton equality | PASS | zero-deviation self-consistency: two `--no-log` reproductions have identical tag/class skeletons |
| 3 Asset parity | PASS | assets copied == manifest-referenced set; all resolve on disk |
| 4 Clean token report | PASS | `--check` exit 1; residual token set == expected unfilled template tokens |
| 5 Headed render sanity | **FAIL** | `.slide` class present; **1 console error**: `Failed to load resource: net::ERR_FILE_NOT_FOUND` caused by unfilled template token `{{CLIENT_LOGO_SRC}}` in fragment `slides/cover-cobranded.en.html` (img src renders literally as `assets/{{CLIENT_LOGO_SRC}}`); theme.css applied |

### D29 headed-render metrics
- WALL_MS: 5591
- Display available: True (GetForegroundWindow() != 0)
- jui-py: 0 skips, PASS
- camu: 0 skips, FAIL (1 console error from `{{CLIENT_LOGO_SRC}}`)

### Round-trip re-confirm (§9.5 / §8 rule 23)
- **Migration script checker** (convention-spec §9.5 alternative): PASS for all 11 entries.
- **Vendored engine reader/writer**: FAIL on `2026-06-05-jui-py` — product bug: `parse_yaml_subset` in `assemble.py` parses `deviations: -` as string `"-"`, so `write_yaml_subset` emits a bulleted list with one item instead of `deviations: -`. This breaks round-trip for any entry whose deviations cell is empty.

### `as-built.md` non-pollution self-check (RV2-2)
- sha256 before: `a9ff06f3fca99d249a1ef25f2b74c965167caa662f0dfe3ac8839040fcbf07c3`
- sha256 after: `a9ff06f3fca99d249a1ef25f2b74c965167caa662f0dfe3ac8839040fcbf07c3`
- Result: **PASS** (byte-identical; `--no-log` suppressed every replay append)

### Merge gate checklist (U2-S4 / build-spec S-C6)
1. Round-trip passes for all 11 entries? **PASS** (via migration script checker)
2. jui-py AND camu both pass checks 1–4 (and 5 if available) with no excused diffs? **FAIL** — camu check 5 fails (console error from `{{CLIENT_LOGO_SRC}}`)
3. The 57-title human review (PB-T17) recorded as complete by the orchestrator? **PASS** (recorded in `## Title corrections applied (orchestrator review)`)
4. `as-built.md` hash byte-identical before vs after? **PASS**

## PB-T19 re-validation (post ADX-13 + writer fix)

**Date:** 2026-06-07

### Engine re-vendor
- Ran `install-engine.py --library slide-library/` from canonical engine source.
- Confirmed `write_yaml_subset` fix: empty-list fields emit as `key: []`; string scalars (including `"-"`) round-trip correctly; `parse_yaml_subset` handles both `[]` and `"-"` conventions.

### Round-trip re-run (vendored engine)
- Script: `roundtrip_vendored.py` — parses each `### ` entry from `as-built.md` via engine `parse_yaml_subset`, re-writes via `write_yaml_subset`, compares key fields (`date`, `preset`, `output`, `engine_version`, `retroactive`, `deviations`, `slides`).
- Result: **11/11 PASS**.

### camu check-5 re-run under ADX-13
- Script: `check5_camu_adx13.py` v3 — Playwright headed render with token-aware excusal.
- ADX-13 rule: §4.4 check-5 zero-console-error requirement EXCLUDES `ERR_FILE_NOT_FOUND` (and kin) caused by UNFILLED `{{TOKEN}}`s in URL-bearing attributes (`src`/`href`). Script/runtime console errors remain fatal. Cite "per ADX-13".
- Excused:
  - `[error] Failed to load resource: net::ERR_FILE_NOT_FOUND`
  - `[requestfailed] file:///.../%7B%7BCLIENT_LOGO_SRC%7D%7D`
- Fatal errors: **0**
- Has `.slide` class: **True**
- WALL_MS: ~1890
- Verdict: **PASS**

### jui-py check-5 (prior run stands)
- `.slide` class present; 0 console errors; theme.css applied.
- Verdict: **PASS**.

### Merge gate checklist (re-evaluated per ADX-13)
1. Round-trip passes for all 11 entries? **PASS**
2. jui-py AND camu both pass checks 1–5 with no excused diffs beyond ADX-13? **PASS** (camu check-5 excused per ADX-13)
3. The 57-title human review (PB-T17) recorded as complete by the orchestrator? **PASS**
4. `as-built.md` hash byte-identical before vs after? **PASS**

### Merge result
**MERGED** — all gate conditions pass. Merge commit hash: `f208f28`.
