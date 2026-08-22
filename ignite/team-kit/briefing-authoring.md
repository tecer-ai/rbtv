# team-kit — briefing authoring rules

**Read this ONLY while authoring a run's briefings or seat descriptors** — the run assembler at
bootstrap, or a live run's seat-authoring role, at the moment it writes one. An executing seat never
loads it. Split out of `protocol.md` (beside this file) so that ~1 seat per run pays for it instead
of all of them; `protocol.md` remains the protocol every seat follows and carries the evidence-pointer
scheme (`P-n`, `S§n`, `PROP-n`) the rules below cite.

## Briefing authoring rules (for whoever assembles a run)

Before authoring any briefing, settle the ROSTER's shape: `team-kit.md` § Roster assembly
(partition by surface, then cover every surface with a checker) and § Run capacity (what the box
can actually run). Both are decided once, per run, and the briefings below only encode the result.

- **R-isolation (P3).** One worker = one briefing. A briefing NEVER cites another worker's
  briefing, not even as a pre-read — shared pre-reads are hoisted into the run package `CLAUDE.md`
  or inlined as file paths. Only leader reads workers' briefings, lazily (on first contact).
- **Folder form (preferred):** one folder per seat, `workers/<agent>/`, holding `agent.md` (the
  briefing), a thin `CLAUDE.md` + `AGENTS.md` loader pair (so any harness landing in the folder
  reads briefing + memory + package protocol), `memory.md` (written by the seat's own `checkout
  --renew --handoff`, and by a closer on the leader-initiated failure close; persistent seats
  only), and `transcripts/` (export target). The legacy flat `workers/<agent>.md` still launches.
- Briefings carry `agent:` frontmatter (the roster signature `launch` discovers), plus optional
  `harness:` (claude | codex | opencode; default claude), `model:` (claude alias, or the
  provider/model slug for opencode — REQUIRED there; omitted on codex = plan default),
  `effort:` (EVERY harness that has a dial, written as that harness's OWN word — read from the
  profile's `effort.rungs` in `spawn-profiles.yaml`, never a cross-harness vocabulary, and the
  ladders differ per MODEL not per harness: `claude-fable` has five rungs while `claude-haiku`
  has none, and `zai-coding-plan/glm-5.2` has two. **There is NO default any more** — a seat cast
  onto a profile with a real ladder and no `effort:` is REFUSED at launch, and one whose profile
  declares an inert dial accepts the word and applies nothing, reporting it rather than dropping
  it), `cwd:` (launch dir; folder-form default is the seat's
  own folder), `window: yes` (own tmux window/tab instead of a tiled pane — use for ephemeral/
  loop seats; long-lived core seats stay panes in the leader window: the hybrid layout),
  `ephemeral: yes` (memoryless one-pass seat: relaunched fresh, departs itself, never closed/
  renewed, no memory.md), `observer: yes` (full-log read), `auto-wake: yes` (woken immediately on
  every message its own `read` shows — never for traffic outside its inbox), `broadcast:`
  (`none` | `all` | a type list — which `to: all` types reach this seat; absent keeps the default),
  `senders:` (a comma-separated allow-list of the ONLY seats whose messages reach this one; absent
  means unbounded), and `ctx-refresh: N` (this seat's own context-refresh threshold %, enforced by
  the deterministic watch layer). Observer status is for seats whose
  job is watching, never a convenience for a worker.
- **Declared outputs — the seat's done contract (7.676/D3).** The ONE surface is the io-spec
  `## Outputs` block in the briefing BODY — `<io-spec>` … `## Outputs` … `</io-spec>` — read by
  BOTH readers through one shared resolver: the done-contract grading at `checkout`
  (`coord.py#iospec_outputs`) and the caged-launch admission gate
  (`engine/cage-admission.js#parseDeclaredOutputs`). A declared output is a BACKTICKED
  goal-relative token carrying a `/` and an extension: `` `seats/<seat>/plan.md` ``, or
  `` `./plan.md` `` for a file in the seat's own cwd. Semantics: these are the paths the seat
  must have PRODUCED. PRESENT means a file that exists AND is non-empty (a zero-byte file is
  what a crashed writer leaves, and does not count); relative tokens resolve against `cwd:` —
  the seat's own folder in folder form.
  Checkout consequence: a plain `checkout` computes it and REFUSES to record `done` while any
  declared token is absent or empty — it names each missing path, and nothing is written, nothing
  exported, the roster row still ACTIVE. The seat either produces them and re-runs `checkout`, or
  ends honestly with `checkout --incomplete "<why they are unmet>"`. `--incomplete` and `--renew`
  skip the check (neither asserts completion). Omitting the block is allowed and never refused:
  the seat's disposition record then reads `none-declared` and that `done` is unverified.
  ⚠ **A PROSE `## Outputs` section is LOUDLY ungradeable.** A section that names no backticked
  path token yields ZERO declared outputs; the check-out records `outputs-undeclarable: zero
  tokens` (measured 2026-08-18: 23 of 26 meet-transcript-summarizer dones were graded against
  nothing because their prose blocks declared nothing a machine could check), and
  materialize-seats.py warns at materialize. Write the token, not a description of it.
  ⚠ **The `outputs:` FRONTMATTER KEY IS RETIRED (D3, 2026-08-18).** A descriptor still carrying
  it — any shape — is REFUSED BY NAME at its check-out and at materialize, never read, never
  silently dropped. Two surfaces with two readers is the defect the retirement closes: a seat
  declaring on one was invisible to the other.
  ⚠ **Declared outputs are NOT `surfaces:`.** The briefing's owned-surfaces claim is what a seat
  may WRITE (a permission, single-writer arbitration — still prose; the `surfaces:` key is
  unbuilt, G-57). A declared output is what a seat must have PRODUCED (a debt, checked at the
  ending). Often the same paths, never the same question.
- Every briefing states: mission, owned surfaces, pre-reads (paths only), execution contract,
  done gate (pre-declared criteria a checker can judge against), and what the agent must never do.
- Factual claims a briefing makes about the target system are the FIRST thing its worker verifies
  (R-audit-premises) — author them as commands-to-run, not assertions, wherever possible.
- **Production-regime fixture gate (briefing diff 1).** A briefing that asks for a fix to a
  detection/matching/parsing mechanic MUST require the fix be exercised against a fixture captured
  from the REAL regime it fails in — real captured input, at real size, at the real width/shape —
  and MUST forbid a hand-authored fixture as the evidence. P35 shipped green TWICE on fixtures
  that hard-coded the exact assumption under test: round 1 asserted the wake was the pane's last
  line (it never is), round 2 matched the full wake text against one captured line (a production
  wake always wraps). Both were caught only when someone captured a live pane.
- **Pre-registered fix→verify bars (briefing diff 4).** For every fix a briefing commissions,
  state the acceptance bar BEFORE the fix is attempted — the exact observation that will count as
  proof, and the observations that will NOT. A bar written after the fix is written to the fix.
  The verifier judges against that bar and nothing else.
