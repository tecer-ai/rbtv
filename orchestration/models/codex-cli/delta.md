# `codex` package delta

Per-model delta for the **codex** CLI worker (OpenAI Codex CLI, `codex exec`). Codex is invocable today and live-proven ONCE as a **separate-process worker**: in investor run **B4D** (`1-projects/rbtv-evolution/orchestration/rbtv-plan-orchestration/cp-rbtv-plan-orchestration-nested-subagent-isolation-validation.md`, row B4D/p4-4), the refuter's opt-in Codex backend ran as a **separate OS process** and delivered the live context-isolation that an in-harness Claude sub-agent could not (the nesting wall). That separate-process isolation is the ONE validated fact. The full headless worker contract — return parsing, exit semantics, confinement-as-the-orchestrator's-job, resume inside a dispatch loop — is **UNPILOTED**: it is authored here from the live `codex exec --help` (CLI **0.137.0**, verified on this machine) and the schema, NOT from a pilot run. Areas that the corpus does not prove are marked **UNPILOTED** inline, and the manifest carries `evidence_status: probe-pending`. The p5-2 smoke probe is the first real `codex exec` dispatch through this manual.

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit codex behavior HERE; never in the rendered manual.

<!-- RENDER:DELTA model-binding-delta -->
**Codex-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What codex is bound to |
|------------|------------------------|
| **Sandbox + approval are the confinement, and they are the conductor's to set (UNPILOTED enforcement)** | Codex has a real native sandbox (`-s/--sandbox`: `read-only` · `workspace-write` · `danger-full-access`) and an approval policy. On Codex CLI **0.137.0** `codex exec` has NO `-a/--ask-for-approval` flag (it was removed from the `exec` subcommand — verified absent in `codex exec --help`, p5-2 smoke probe); the approval policy is set via the config override `-c approval_policy="never"` (a `-c` dotted-path TOML override — `approval_policy` is a recognized key, confirmed under `--strict-config`). A non-interactive dispatch MUST set `-c approval_policy="never"` (so the model never pauses for a human) paired with the TIGHTEST sandbox the task needs — `read-only` for analysis/research leaves, `workspace-write` for code that edits the work-dir, NEVER `danger-full-access` and NEVER `--dangerously-bypass-approvals-and-sandbox` unless the task explicitly sanctions it. The pairing `-c approval_policy="never"` + `--sandbox workspace-write` is the bounded-write default. The sandbox is real but its reliability as a confinement boundary for THIS orchestrator is UNPILOTED — back it with the same post-run `git diff --name-only` vs the allowlist that every CLI worker gets. |
| **Workspace scope is `-C`/`--cd` + `--add-dir`; the launch root is the ORCHESTRATOR root, never the work-target** | Set `-C <orchestrator-root>` (or run from that cwd) — the launch root codex auto-reads its `AGENTS.md` + rules from — and pass the actual **work-target** via `--add-dir <work-target>` (+ further minimal extra dirs only when needed). NEVER root codex at a nested-repo work-target: the mirror skips nested repos, so a worker rooted there loads zero behavior-rules (the a3e217d defect class). The work-target's own local `CLAUDE.md`/`AGENTS.md` conventions are NOT auto-loaded from `--add-dir` — the conductor inlines the load-bearing ones or marks them `[FULL READ]`. Files created/modified outside the work-target allowlist are an out-of-allowlist write the conductor catches on the post-run diff run in the WORK-TARGET's git (`git -C <work-target> diff --name-only HEAD`) — surface, never auto-revert. `--skip-git-repo-check` is required ONLY when the launch root is not a git repo (codex refuses to run outside a repo otherwise). |
| **No self-commit unless the task grants it (default OFF)** | Codex MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only`. NEVER push, NEVER force-reset, NEVER amend. The commit subject MUST carry the run's mandated `[<task-id>]` convention; the returned hash MUST match `git log`. Absent an explicit grant, codex does NOT commit (the conductor commits via `rbtv-commit`). This authorization, and the commit message convention's survival across a codex run, are UNPILOTED — verify the hash and the subject string on return. |
| **Project trust is a pre-flight, not a runtime grant** | Codex records per-project `trust_level` in `~/.codex/config.toml` (`[projects.'<path>']`). An untrusted target project triggers a first-run interactive trust prompt — a USER-EXECUTED-ONLY pre-flight (run codex once interactively in the workspace, or pre-set trust) before any headless dispatch. Do NOT attempt to clear a trust prompt programmatically. |
| **Stray-file ban** | Create files ONLY where the allowlist directs. NEVER write scratch notes, logs, or summary files into the repo root or anywhere outside the allowlist — the post-run diff treats any such file as an out-of-allowlist write. Use `-o/--output-last-message <file>` to land the structured return at a known path INSIDE the allowlist rather than scraping stdout. |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the scoped work-dir, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions a mocked/local one, no `--dangerously-bypass-*` flags unless the task names them. |
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**Codex return surface:** run headless with `codex exec` (alias `codex e`). The final assistant message goes to stdout; pass `-o/--output-last-message <file>` to ALSO write that final message to a file on disk (the durable copy — prefer it over stdout scraping). `--json` streams events as JSONL (one JSON object per line) for machine parsing — the final result is the last `agent_message`/assistant event. The worker carries the five return fields in that final message; treat the message as a HINT, never the truth. Codex runs autonomously to completion under `-c approval_policy="never"`, so a dropped or garbled final turn is possible (UNPILOTED failure surface — codex's exact behavior on a mid-return connection drop is not corpus-validated; treat it like the kimi exit-75 class and reconcile from disk). The conductor reconciles every codex return against `git status` / `git log` of the work-dir and the cited evidence files on disk — disk wins on any disagreement. For a strictly-shaped final response, `--output-schema <file>` constrains the model's final JSON to a supplied JSON Schema.
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The codex CLI dispatch manual — the exact command shapes, flags, sandbox/approval grammar, exit handling, resume, and the codex task contract. Verified against **Codex CLI 0.137.0** (`codex --version` → `codex-cli 0.137.0`) on this machine. Re-verify with `codex --help` / `codex exec --help` / `codex --version` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build. Evidence boundary: the separate-process isolation property is live-proven (B4D); the p5-2 smoke probe then ran one real `codex exec` dispatch through this manual on 0.137.0 — it caught that `--ask-for-approval` was removed from the `exec` subcommand (now `-c approval_policy="never"`), and exercised the stdin-pipe transport (now the `!`-dispatch form under Shape B), `--sandbox workspace-write`, `--output-last-message`, and the five-field return (exit 0, file landed byte-correct). Facets NOT yet exercised — the non-zero exit taxonomy, resume inside a dispatch loop, self-commit — remain **UNPILOTED** and are marked where it matters. The 2026-07-02 poc-1-build run added: Shape-B file-pointer transport VALIDATED (five dispatches), and a NEW Windows boundary — codex's sandbox CANNOT reach WSL (`wsl -d <distro> …` fails with `WSL_E_DISTRO_NOT_FOUND` inside codex exec while the identical command works outside it): route WSL-executing tasks to another worker and split in-WSL validations to conductor-run exit-probes.

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `codex --version` (`codex-cli 0.137.0`) | Absent/older → re-verify flags against `codex exec --help`. |
| **Pinned-flag existence** (routing §4 gate) | `codex exec --help` grepped for every non-trivial flag this dispatch pins (`--sandbox`, `-C`/`--cd`, `--output-last-message`, `--add-dir`); the `-c approval_policy` override key confirmed via `codex exec --strict-config` | Runs EVERY dispatch (NOT only on a version mismatch — a flag can vanish at the SAME version family the manual pinned). Subcommand-aware: verify `codex exec --help`, never `codex --help`. Any pinned flag absent → STOP, do not dispatch; re-resolve at THIS delta, re-render (`../render-manuals.py`), re-run the gate — NEVER hand-edit the rendered manual or pass an ad-hoc flag. A removed/renamed flag is a hard `unexpected argument` exit-2 pre-spend if dispatched (p5-2: `--ask-for-approval` was removed from `exec` at 0.137.0 → `-c approval_policy="never"`). |
| Auth | `codex login status` (this machine → `Logged in using ChatGPT`) | Login is interactive (`codex login`, ChatGPT sign-in) OR `printenv OPENAI_API_KEY \| codex login --with-api-key`. First-time interactive login → USER-EXECUTED-ONLY; if unauthenticated, halt and ask the owner to run it; never automate the browser sign-in. |
| Project trust | target project has `trust_level = "trusted"` in `~/.codex/config.toml` `[projects.'<path>']`? | Untrusted → first-run interactive trust prompt (USER-EXECUTED-ONLY). Pre-trust the workspace or run codex once interactively there before headless dispatch. Trust resolves up the directory tree — a trusted ancestor (e.g. `c:\users\henri`) covers nested repos beneath it, so a nested git root under a trusted root is NOT separately untrusted. |
| Guidance file | the LAUNCH ROOT (orchestrator root — the `-C`/`--cd` value) has `AGENTS.md`? | Checked at the launch root, NEVER the work-target (the work-target needs no guidance file — the mirror skips nested repos by design). Absent at the launch root → offer to generate it via the mirror (`mirror_entry: codex-mirror`, see the codex `mirror-config.yaml`). Codex natively reads `AGENTS.md` from its working root. |

### The invocation shape — `codex exec` (non-interactive)

`codex exec` (alias `codex e`) runs Codex non-interactively. The prompt reaches the worker as a CLI argument OR via stdin (use `-` as the prompt, or pipe; if stdin is piped AND a prompt arg is given, stdin is appended as a `<stdin>` block).

**Stdin-EOF guard — MANDATORY on EVERY headless dispatch.** Because codex reads stdin whenever it is non-TTY, a dispatch from the PowerShell/Bash tool or any background harness HANGS forever on "Reading additional input from stdin..." unless stdin EOFs — even when the prompt is passed as a CLI arg. This was the live-diagnosed multi-minute "stall" (root cause: stdin, NOT project trust). Force the EOF: **Bash dispatch → suffix `< /dev/null`** (PREFERRED — the command still BEGINS with `codex`, preserving the §1 D17 binary-first allowlist match; live-verified exit 0 / `SMOKE_OK`). **PowerShell dispatch → prefix `$null |`** (live-verified exit 0, 39s) — but the line then begins with `$null`, so it breaks the `PowerShell(codex:*)` binary-first prefix and carries the stdin-pipe permission caveat (valid under auto-mode/`!` dispatch, not the strict in-session classifier). The shapes below are PowerShell-fenced; apply the matching guard for the shell you dispatch from.

**Shape A — prompt as CLI argument (small prompts):**

```powershell
$null | codex exec --cd "<orchestrator-root>" --add-dir "<work-target>" --sandbox workspace-write -c approval_policy="never" `
  --output-last-message "<work-target>/.codex-runs/<task-id>.txt" "<task_prompt>"
```

Use when the prompt fits comfortably under the host shell's single-argument limit (Windows PowerShell ~32 KB). Default for short dispatches. The leading `$null |` is the PowerShell stdin-EOF guard (see above); from the Bash tool use `codex exec … "<task_prompt>" < /dev/null` instead.

**Shape B — large brief via a FILE POINTER (default in autonomous mode; command BEGINS with `codex`):**

For a prompt too large to inline (PowerShell ~32 KB single-arg ceiling), write it to a file inside the scoped workspace and point codex at it with a SHORT prompt arg:

```powershell
codex exec --cd "<orchestrator-root>" --add-dir "<work-target>" --sandbox workspace-write -c approval_policy="never" `
  --output-last-message "<work-target>/.codex-runs/<task-id>.txt" `
  "Read the file '<prompt-path>' and execute the task it contains exactly; create only the files it allowlists."
```

Codex loads the brief via its own file tool, so the command stays short AND begins with `codex` (the in-session permission requirement — generic packaging §1 D17 row; the file-pointer read is VALIDATED for codex (2026-07-02, poc-1-build run: five Shape-B dispatches on 0.137.0/gpt-5.5 — each read its on-disk prompt file via the short pointer arg and executed the inlined task; exit 0; --output-last-message return files landed five-field-conformant)). Do **not** pipe the brief with `cat prompt.md | codex exec … -` for an in-session dispatch: the pipe makes the command line BEGIN with `cat`, which does not match the `codex:*` prefix rule and falls to the permission classifier. The same binary-first rule governs the mandatory stdin-EOF guard: the PowerShell `$null |` prefix likewise begins the line with a non-`codex` token (so it is auto-mode/`!`-dispatch only), whereas the Bash `< /dev/null` SUFFIX EOFs stdin while keeping the line beginning with `codex` — the in-session binary-first-safe guard. So a strict in-session Shape-B dispatch runs from the Bash tool: `codex exec --cd "<orchestrator-root>" --add-dir "<work-target>" … "Read the file '<prompt-path>' …" < /dev/null`. The stdin-pipe form (`cat prompt.md | codex exec --cd "<orchestrator-root>" --add-dir "<work-target>" … -`, trailing `-` = read prompt from stdin) remains the p5-2-VALIDATED transport (Git Bash, exit 0, prompt reached the worker, file landed) — use it for owner-typed `!` dispatches. **Both shapes** apply the same launch-root/work-target scope, the same sandbox + approval policy, and pass the same allowlist + forbidden-ops checks on return. The composed **header + payload** (generic packaging §1) is written to `prompt.md` on disk and dispatched FROM that file — the same prompt file is the reuse surface on resume.

### Sandbox + approval grammar — the confinement axis

| Flag | Values | Use |
|------|--------|-----|
| `-s` / `--sandbox` | `read-only` · `workspace-write` · `danger-full-access` | The blast-radius control. `read-only` = analysis/research leaf (no file writes). `workspace-write` = code that edits the scoped work-dir (the bounded default for code). `danger-full-access` = NEVER unless the task explicitly sanctions it. |
| `-c approval_policy="<policy>"` | `untrusted` · `on-request` · `never` (config override; `codex exec` has NO `--ask-for-approval` flag on 0.137.0) | Headless MUST set `-c approval_policy="never"` (the model never pauses for human approval; failures return to the model). `untrusted`/`on-request` stall a headless run waiting for input. Set it as a `-c` dotted-path TOML override — the `--ask-for-approval` flag was removed from the `exec` subcommand (p5-2 smoke probe: `error: unexpected argument '--ask-for-approval'`). |
| `--dangerously-bypass-approvals-and-sandbox` | (flag) | Skips ALL approvals AND sandboxing. EXTREMELY DANGEROUS — only for an externally-sandboxed environment the task names. Forbidden by default. |
| `-C` / `--cd <dir>` | path | The agent's working root = the LAUNCH ROOT — always the orchestrator root (guidance/`AGENTS.md` loads from here), never a nested-repo work-target. |
| `--add-dir <dir>` | path (repeatable) | The work-target rides here, plus any minimal extra writable dirs. Keep minimal. |
| `--skip-git-repo-check` | (flag) | Required only when the work-dir is NOT a git repo (codex refuses outside a repo otherwise). |
| `--ignore-rules` | (flag) | Do NOT load user/project execpolicy `.rules` files. Use only when a workspace `.rules` file would wrongly block a sanctioned dispatch. |
| `--ignore-user-config` | (flag) | Do NOT load `~/.codex/config.toml` (auth still uses `CODEX_HOME`). Use for a clean, reproducible dispatch independent of the machine's personal codex config. |

**`allow_git_writes` is NOT a recognized key on 0.137.0 — never pin it.** `-c sandbox_workspace_write.allow_git_writes=true` errors under `--strict-config` and is silently ignored otherwise (TESTED 2026-07-08Z, codex-cli 0.137.0). Under `--sandbox workspace-write` codex POLICY-blocks all writes into the MAIN repo's `.git` (see the known-failure row below), and no config lever re-enables them — escaping requires `danger-full-access`/`--dangerously-bypass-approvals-and-sandbox`, forbidden by default. Do NOT expect a codex worker to create branches/worktrees in the main repo.

**Confinement is the orchestrator's job (UNPILOTED reliability):** the sandbox is real, but its reliability as the sole confinement boundary for this orchestrator is not corpus-validated. ALWAYS back it with the post-run `git -C <work-target> diff --name-only HEAD` of every changed path against the task's `allowlist` — run in the WORK-TARGET's git, never the launch-root's; the same reliable enforcement every CLI worker gets. Out-of-allowlist edit = halt + surface; NEVER auto-revert silently.

**Windows: `workspace-write` DOES spawn subprocesses — the boundary is codex's approval classifier, NOT a spawn-capability limit. Split only python/pytest-validated or live-call leaves, not every capability-run.** A headless `codex exec --sandbox workspace-write -c approval_policy="never"` worker on Windows EDITS files AND spawns subprocesses normally. TESTED 2026-06-14 (codex-cli 0.137.0, Windows 11, `[windows] sandbox = "elevated"`, two probes — `2-areas/rbtv/orchestration/codex-windows-subprocess/captures/`): `git` (incl. `git init` / `status --porcelain`), `node` (incl. `node -e "…"`), `pwsh` (cmdlets AND `-Command` invocations that spawn external `git`), `cmd /c`, and `where.exe` all EXECUTE and return (exit 0). The blanket "cannot spawn a subprocess" claim (originally encoded from the 2026-06-12 design-module-closeout run, rbtv `f4c4fba`) is REFUTED — it rested entirely on `python --version` as the canary, which is a special case (see below).

The ONE consistent block observed is the **`python` / `python -c` interpreter** → declined by codex's **approval router** (`approval required by policy, but AskForApproval is set to Never`). This is an APPROVAL classification, not a sandbox spawn failure: the same error family appears under `danger-full-access` (the approval router is orthogonal to the sandbox mode), and codex declines `python` BEFORE resolving it (codex's PATH lacks the installed python — `where.exe python` returns not-found inside codex — but the decline is the approval router, not a not-found). The exact auto-approve-vs-needs-approval classification is codex-internal and not fully enumerable from this probe; `python` is the confirmed-blocked class, `git`/`node`/`pwsh`/`cmd`/`where` the confirmed-allowed class. The node `spawn setup refresh` infra failure from the design-module-closeout does NOT reproduce — node spawns fine under the current elevated Windows sandbox.

**Routing implication:** codex CAN self-validate a capability-run leaf on Windows whose check uses `git`/`node`/`pwsh`/`cmd` (e.g. a `git status` clean-tree check or a `node` smoke), AND can make a real outbound network/API call when dispatched with `-c sandbox_workspace_write.network_access=true` through an auto-approved client (TESTED — see the live-call sub-point below). The author/validate split is therefore NO LONGER the blanket default — apply it ONLY when validation requires a class the approval router declines (notably **`python`/`pytest`-based** test or build runs), OR a **live-call** that cannot be granted network egress or must run through an approval-declined binary (`python`). In those cases **split the dispatch** — codex authors the edit ONLY, and the CONDUCTOR runs the validation as an exit-probe (the Invariant-4 decide→resume shape; codex still authors any follow-on fix) — or route the leaf to kimi-code-cli. Do NOT blanket-split every codex capability-run or every live-call on Windows. Two sub-points on the wider sandbox grammar:

- **Live-call / network WORKS under `workspace-write` when network egress is granted (TESTED 2026-06-14, codex-cli 0.137.0, Windows 11).** `-c sandbox_workspace_write.network_access=true` governs outbound network *within* the sandbox: with the flag set, codex completed a REAL outbound HTTPS round-trip — `node -e "fetch('https://example.com')…"` returned `NODE_FETCH_STATUS 200` (captures `net-on.md`). Without the flag (default `network_access=false`) the SAME fetch fails (`fetch failed`) and `git`/HTTPS is refused at the sandbox egress layer (`Failed to connect to github.com port 443`, captures `net-off.md`) — so the flag is the actual lever, not a sandbox-mode change. `--sandbox danger-full-access` is therefore NOT required for a live call. Two caveats: (1) the call MUST run through an AUTO-APPROVED binary — `node` is confirmed; `python` stays approval-router-declined regardless of sandbox/network mode, so a python-based HTTP client does NOT inherit this. (2) `git`-over-HTTPS additionally failed with a Windows schannel credential error (`SEC_E_NO_CREDENTIALS`) ORTHOGONAL to the sandbox (a git-credential-helper quirk inside the codex environment, not a network denial) — prefer `node` or another non-git client for a live/network canary. The earlier design-module-closeout "live API call blocked" report is explained: it lacked `network_access=true`. **Routing consequence:** a live/network-call leaf NO LONGER requires the author/validate split SOLELY for network — dispatch codex with `-c sandbox_workspace_write.network_access=true` (+ an auto-approved client) and it makes the call. The split stays the default ONLY when the live call cannot be granted network egress, or must run through an approval-declined binary (`python`/`pytest`).
- `--sandbox danger-full-access` does NOT change the `python` approval-decline (TESTED 2026-06-13: headless `danger-full-access` + `approval_policy="never"` still refused `python --version`, `approval required by policy, but AskForApproval is set to Never`) — consistent with the decline being the approval router, not the sandbox. Disabling the sandbox is not a workaround for the approval classifier; for a python/pytest-validated leaf the split (or kimi-code-cli) remains the default.
- **The `python` decline is PLATFORM-INDEPENDENT and token-keyed — `python3` is the clean workaround (TESTED 2026-07-18, codex-cli 0.144.5, Ubuntu Linux — sysdef-archive run D67; refutes the Windows-only framing above).** The decline reproduces on Linux where `/usr/bin/python` EXISTS (same interpreter `python3` resolves to) — so it is purely the approval classifier keyed on the literal token `python`, not interpreter resolution and not a Windows quirk. `python3` and `python3 -c` are ACCEPTED and run normally (4/5 workers in the same wave validated with `python3` → EXIT 0). Binding consequences for every codex brief: (a) pin `python3` explicitly and forbid bare `python`; (b) instruct any multi-file rule/corpus read as `cat`, ONE FILE PER CALL — never a `python - <<'PY'` bulk heredoc (opens with the rejected token AND truncates silently mid-corpus); (c) state that a harness rejection is a HARNESS refusal, never evidence the worker's file is wrong, and never justifies returning `BLOCKED` with no deliverable — write the file, then report the refusal in `validation`. With the `python3` pin, a python-validated leaf no longer requires the author/validate split by default; the split remains for `pytest`-style runs only where `pytest` itself is declined on the target box (probe before assuming).

### Model selection → variants

The codex manifest declares routable variants — ONE row per MODEL (effort is the post-pin dial stored in `reasoning_modes`, never a separate row). Route on `(codex-cli, variant)`:

| Variant | reasoning · coding · cost · evidence | Effort invocation (post-pin dial) | When |
|---------|---------------------------------------|-----------------------------------|------|
| `gpt-5.5` | 7 · 7 · 7 · **validated** | `-c model_reasoning_effort="low|medium|high"` | Top-tier reasoning + coding; unbounded and judgment-dense work; the one exercised variant (2026-06-11 done-gate at medium). |
| `gpt-5.4` | 6 · 6 · 5 · probe-pending | `-m gpt-5.4 -c model_reasoning_effort="low|medium|high"` | Prior-gen counterpart; model-diversity alternative for bounded/partially-bounded work. |

**One row per MODEL — effort is the post-pin dial.** The low/medium/high `model_reasoning_effort` levels are stored in `reasoning_modes` as the post-pin effort dial (`effort = f(boundedness)`, set AFTER the capability pin) — NOT separate rows. All efforts of one model share its capability integers (all gpt-5.5 efforts are 7/7; all gpt-5.4 efforts are 6/6). The configured model on this machine is `gpt-5.5` at `medium` effort (`~/.codex/config.toml`); a re-pointed model changes the variant row.

**gpt-5.4 (owner-confirmed access 2026-06-11):** live-probed at all three efforts through this same codex 0.137.0 in the 2026-06-11 reasoning-test battery (`codex exec -m gpt-5.4 -c model_reasoning_effort=<low|medium|high>`, exit 0, correct output). That battery was CONDUCT-ONLY (no grading); gpt-5.4 carries `evidence_status: probe-pending` — verify against a graded run before trusting the routing placement. gpt-5.4's exact context window are NOT separately confirmed (re-confirm before routing large context).

`-m/--model <id>` overrides the configured model per dispatch (the gpt-5.4 variant pins `-m gpt-5.4`); `-c model_reasoning_effort="<low|medium|high>"` overrides reasoning effort (a `-c` dotted-path config override, TOML-parsed). `-p/--profile <name>` layers a `$CODEX_HOME/<name>.config.toml` profile on top of the base config. Re-confirm against the live config before routing.

### Exit handling

Codex `exec` returns a process exit code; `0` = success. A non-zero exit means the run did not complete cleanly — halt and surface; do NOT blind-retry. The precise non-zero exit-code taxonomy (which codes are retryable rate-limit/throttle vs non-retryable config/auth) is **UNPILOTED** on this machine — unlike kimi's documented exit-75, codex's retry semantics are not corpus-validated. Until a probe establishes them: on any non-zero exit, reconcile disk state, and if uncommitted in-allowlist work landed without the structured return, apply the disk-state recovery pattern below rather than re-running.

```powershell
codex exec --cd "<orchestrator-root>" --add-dir "<work-target>" --sandbox workspace-write -c approval_policy="never" `
  --output-last-message "<work-target>/.codex-runs/<task-id>.txt" "<task>"; $code = $LASTEXITCODE
if ($code -ne 0) { <reconcile disk; recover-or-surface — do NOT blind-retry> }
```

### Disk-state recovery (work landed, return/commit lost) — UNPILOTED, judgment-only

Mirrors the kimi exit-75 recovery in shape; codex's exact drop behavior is unvalidated, so treat this as a candidate protocol, valid only under a high-reasoning conductor (a lower-reasoning conductor halts + surfaces). Trigger only when ALL hold: codex exited non-zero with NO structured return (no `status`, no commit hash) in the `--output-last-message` file/stdout; `git -C "<repo>" status --porcelain` shows uncommitted changes inside the allowlist; `git -C "<repo>" log -1 --pretty=%s` does NOT show the expected `[<task-id>]` prefix. Steps: (1) verify on-disk state against the task's Implementation Requirements; (2) run the declared `test_command` / smoke checks; (3) verify allowlist compliance (`git diff --name-only HEAD` — every changed path in the allowlist, else halt + surface); (4) verify forbidden-ops compliance; (5) commit manually with the mandatory `(orchestrator-recovered)` subject suffix:

```bash
git -C "<repo>" add <files-in-allowlist>
git -C "<repo>" commit -m "[<task-id>] <description> (orchestrator-recovered)" \
  -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

(6) log to the run-log: exit code, files verified + smoke result, the recovery commit hash, why not retrying, and that the reviewer MUST FULLY re-validate. The recovery commit is reversible (`git revert <hash>`). **Hung dispatch (codex never exits):** orchestrator kills it, evaluates disk state, then recover-commits (same steps) OR re-dispatches fresh.

### Resume mechanics

| Mechanism | Command | Use |
|-----------|---------|-----|
| Resume a specific session | `codex exec resume <SESSION_ID> "<follow-up>"` | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id (UUID or thread name). Add `-` as the prompt to read the follow-up from stdin. |
| Resume the most recent | `codex exec resume --last "<follow-up>"` | Pick up the newest recorded session for the cwd without tracking an id. `--all` disables cwd filtering. |
| Run without persisting | `codex exec --ephemeral …` | A dispatch that should leave NO session files on disk (no resume possible afterward). |

Resume is session-id based (`codex exec resume`). Resume reliability inside an autonomous dispatch loop is UNPILOTED — verify the session id round-trips before depending on resume for recovery; fall back to a fresh re-dispatch (the prompt file is the reuse surface) if resume does not engage.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Headless stalls waiting for approval | ALWAYS set `-c approval_policy="never"` for a non-interactive dispatch; any other policy blocks. (`codex exec` has NO `--ask-for-approval` flag on 0.137.0 — passing it errors `unexpected argument`, p5-2.) |
| Headless HANGS reading non-TTY stdin (the real stall) | `codex exec` reads stdin whenever it is piped/non-TTY — EVEN with a prompt arg (help: "stdin is appended as a `<stdin>` block"). Under a non-interactive harness (the PowerShell/Bash tool, a background dispatch) stdin is an open pipe that never EOFs → codex blocks forever on "Reading additional input from stdin...". This was the observed multi-minute "stall" (NOT trust — trust resolves via a trusted ancestor). Force an immediate stdin EOF on EVERY headless dispatch: **Bash → suffix `< /dev/null`** (preferred: the line still BEGINS with `codex`, so the `Bash(codex:*)` D17 allowlist matches — live-verified exit 0); **PowerShell → prefix `$null \|`** (live-verified exit 0, 39s) BUT the line then begins with `$null`, breaking the `PowerShell(codex:*)` binary-first match, so it carries the same broad/`!`-dispatch permission caveat as the stdin-pipe transport. An owner's interactive terminal has a TTY stdin → no guard needed. |
| Refuses to run outside a git repo | Pass `--skip-git-repo-check` when the work-dir is not a repo. |
| First-run project trust prompt | Pre-trust the workspace (`[projects.'<path>'] trust_level`) or run codex once interactively there — USER-EXECUTED-ONLY; never clear it programmatically. |
| Interactive login required | `codex login` (ChatGPT) or `--with-api-key` via stdin is USER-EXECUTED-ONLY; halt + ask the owner. |
| Sandbox reliability as sole confinement (UNPILOTED) | Always back the sandbox with the post-run `git diff` vs allowlist; the sandbox is not corpus-validated as the only boundary for this orchestrator. |
| **Windows `workspace-write`: only `python`/`pytest` needs the split; subprocesses + granted live-calls RUN** | On Windows the sandbox edits files AND spawns subprocesses — `git`, `node` (incl. `node -e`), `pwsh`, `cmd`, `where.exe` all execute (TESTED 2026-06-14, two probes). The only block is codex's APPROVAL ROUTER declining `python`/`python -c` (`approval required by policy, AskForApproval=Never`), NOT a spawn-capability limit; the node `spawn setup refresh` infra failure no longer reproduces. So codex CAN self-validate a git/node/pwsh/cmd-based check — SPLIT the dispatch (codex edits only; conductor runs validation as an exit-probe) or route to kimi-code-cli ONLY for python/pytest-validated leaves, never every capability-run. `danger-full-access` does NOT change the python decline (TESTED 2026-06-13 — the approval router is orthogonal to sandbox mode). **Live-call / network WORKS** under `workspace-write` with `-c sandbox_workspace_write.network_access=true` (TESTED 2026-06-14: `node` fetch → HTTP 200; without the flag, egress is refused) — through an auto-approved client (node; NOT python). So a live/network-call leaf needs the split ONLY when egress cannot be granted or must run through python. See the sandbox-grammar section above. |
| **`workspace-write` POLICY-blocks writes into the MAIN repo's `.git` — no branch/worktree creation there** | Under `--sandbox workspace-write` codex blocks all writes into the main repo's `.git`: `git worktree add` / branch creation fails on the ref lock (`refs/heads/<branch>.lock` Permission denied) EVEN with `.git` added to `sandbox_workspace_write.writable_roots` (the banner confirmed the root was added); a direct `.git`-write probe was "rejected: blocked by policy". Do NOT expect a codex worker to create branches/worktrees in the main repo. `-c sandbox_workspace_write.allow_git_writes=true` is NOT a recognized key (errors under `--strict-config`, silently ignored otherwise) — NEVER pin it. Escaping needs `danger-full-access`/`--dangerously-bypass-approvals-and-sandbox` (forbidden by default). (TESTED 2026-07-08Z, codex-cli 0.137.0.) |
| `cd` does not persist between shell calls | Each shell command is an independent subprocess — set `--cd`; never rely on `cd` chaining in the prompt. |
| Non-zero exit retry semantics (UNPILOTED) | Codex's exit-code taxonomy is not validated on this machine — on any non-zero exit reconcile disk + recover-or-surface, never blind-retry. |
| Final-message drop on a dropped turn (UNPILOTED) | Prefer `--output-last-message <file>` for a durable return; reconcile from disk on any garbled/absent return. |
| Machine config leaks into a reproducible dispatch | Use `--ignore-user-config` (and `--ignore-rules` if a workspace `.rules` wrongly blocks) for a clean, deterministic run. |

### The codex task contract (plugs into the shared authoring core)

A codex-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with codex-specific frontmatter and body sections. The orchestrator validates a `executor: codex` task against this contract BEFORE dispatch; a missing required field = halt + report the malformed task — NEVER infer or mutate a field into shape (task shaping belongs to planning).

**Required frontmatter:**

```yaml
execution_kind: code            # or research/analysis for a read-only leaf
executor: codex
allowed_workdir: <work-target repo path — passed via --add-dir; --cd is the orchestrator-root launch root, never this>
allowlist:
  - <file-or-folder-glob>
sandbox: read-only | workspace-write   # the tightest the task needs (never danger-full-access by default)
commit_policy: local-only | none       # none = conductor commits via rbtv-commit
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
  - --dangerously-bypass-approvals-and-sandbox
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for codex-produced code is Opus (external-CLI code) — non-overridable
```

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (all task-specific context inlined — never make codex infer from broad PRDs) · Allowed Paths (the allowlist in human-readable form) · Forbidden Paths · Sandbox + Approval (the `--sandbox` value and the mandatory `-c approval_policy="never"`) · Implementation Requirements (exact behavior — interfaces, data shapes, error semantics, every edge case enumerated) · Validation (the exact commands codex runs before returning) · Commit Rule (local-only after validation, or none) · Return Format (the five-field return schema; land it via `--output-last-message`).

**Review gates** every codex coding task passes (verification card owns the gate): codex self-report → orchestrator diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until owner/final-workflow publishes. Any gate fails → halt or route a fix task; never proceed on "close enough". Codex is a SEPARATE-PROCESS worker (its one validated property, B4D) — the cold verifier and review pins apply exactly as for any external-CLI code worker.

### Recipes

Every recipe below requires the stdin-EOF guard (PowerShell `$null |` prefix, or Bash `< /dev/null` suffix — see the Stdin-EOF guard above); it is omitted from these snippets for brevity but is MANDATORY on dispatch.

```powershell
# Bounded code edit, durable return file (Shape A) — launch root = orchestrator root, work-target via --add-dir:
codex exec --cd "<orchestrator-root>" --add-dir "5-workbench/inni-cte-recon" --sandbox workspace-write -c approval_policy="never" `
  --output-last-message "5-workbench/inni-cte-recon/.codex-runs/t1.txt" "<inlined task file content>"
```
```powershell
# Large brief via a FILE POINTER (Shape B — default autonomous/Windows; command BEGINS with `codex`):
codex exec --cd "<orchestrator-root>" --add-dir "<work-target>" --sandbox workspace-write -c approval_policy="never" `
  --output-last-message "<work-target>/.codex-runs/t1.txt" "Read the file '<prompt-path>' and execute the task it contains exactly"
```
```powershell
# Read-only analysis/research leaf (no writes), JSONL events for parsing:
codex exec --cd "<orchestrator-root>" --add-dir "<work-target>" --sandbox read-only -c approval_policy="never" --json "<analysis task>"
```
```powershell
# High reasoning effort, clean of machine config:
codex exec --cd "<orchestrator-root>" --add-dir "<work-target>" --sandbox workspace-write -c approval_policy="never" `
  -c model_reasoning_effort="high" --ignore-user-config "<task>"
```
```powershell
# Resume a halted session with the resolution:
codex exec resume <SESSION_ID> "<resolution to the open question>"
```
<!-- RENDER:DELTA-END invocation -->
