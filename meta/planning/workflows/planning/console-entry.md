# planning — the console entry point

**You are reading this because a user invoked the planning entry skill in a plain interactive
session.** Your job is orientation and setup, not planning: you get the user from "I want to plan
X" to **one command they type in a real terminal**. You never run the planning workflow yourself,
and you never plan the goal yourself — the workflow's own seats do that.

Written to be read cold. Nothing below assumes you saw an earlier turn.

---

## The three things you own

```
ORIENT ──▶ SCAFFOLD + MATERIALIZE ──▶ HAND OVER THE COMMAND
(is there                (turn the workflow into      (the user types it;
 a goal                   a taskforce of seats          you do not)
 already?)                on disk)
```

What runs is never the workflow — it is the **taskforce**: the workflow is the program, the
taskforce is its running instance with a harness and model bound to each seat. Materializing is the
deterministic first step, not a decision.

---

## Step 0 — resolve the two paths you will need

| What | How |
|------|-----|
| Workspace root | the folder containing `rbtv.json` (walk up from the working directory) |
| rbtv repo | `<workspace>/<rbtv_path>` — read `rbtv_path` from `rbtv.json` |
| Goals root | `<workspace>/.rbtv/goals/` |
| This component | `<workspace>/3-resources/tools/rbtv/meta/planning/` |

Never hardcode any of them.

---

## Step 1 — ORIENT

Ask the user which goal this is, or take the one they named. Then, for an existing goal:

```
rbtv run <workspace>/.rbtv/goals/<goal> --status
```

Read-only. No daemon, no profile, and it works before the goal has ever run. It prints done /
in-flight / **ready (next)** / waiting, and names any seat **held for you**. It refuses cleanly on a
path that is not a goal folder and on a goal with no `taskforce.csv`.

- It printed a seat list → the goal is already set up. **Skip to step 3.**
- It refused with *"no taskforce"* → the goal folder exists but has no seats. Do step 2b only.
- The goal folder does not exist → do step 2 whole.

Report what you found in one line before doing anything else. Do not re-scaffold a goal that
already has seats — materialization is create-only and refuses rather than merging.

---

## Step 2 — SCAFFOLD + MATERIALIZE

### 2a. Create the goal folder

The contract is the goal's radius in the user's own words — write it to a file first, then:

```
rbtv goal scaffold <goal-name> --contract <path-to-contract-file>
```

`<goal-name>` is lowercase kebab-case. The verb is create-only and reindexes `goals.csv` itself.

### 2b. Set the execution mode — from the WORKFLOW's default, then the room

The mode gates all agent-initiated owner contact. In `autonomous`, a seat's question to the owner
parks instead of reaching them. This is a per-goal file, not a system setting: the system-wide rule
that an ABSENT `execution-mode` means `autonomous` is untouched — you are simply never leaving it
absent.

**First resolve the workflow's own default** (owner ruling 2026-08-10). It lives in the workflow's
scaffolding, and you read it rather than assume it:

- `default-execution-mode:` in the workflow definition's frontmatter — for planning,
  `<workspace>/3-resources/tools/rbtv/meta/planning/workflows/planning/workflow.md`.
- Where the workflow declares none, derive it from its manifest: any row whose **Modality** column
  reads `interactive` means `interactive`; none means `autonomous`.

Then write it:

- **Default `autonomous` → write `autonomous`, silently.** That workflow has no seat whose job is
  to reach the owner, so there is nothing here to ask about and nothing gained by asking.

  ```
  printf 'autonomous\n' > <workspace>/.rbtv/goals/<goal>/execution-mode
  ```

- **Default `interactive` → write `interactive`, without asking.** A console-started goal has the
  user present, so the goal is interactive by definition (console-run design ruling 6). If the user
  says they want to walk away, write `autonomous` instead and say so.

  ```
  printf 'interactive\n' > <workspace>/.rbtv/goals/<goal>/execution-mode
  ```

One word plus a newline, and nothing else in the file: the reader trims and compares the whole
file, so a comment line would read as "not interactive" and make the goal autonomous by accident.

### 2b-bis. ASK the user which LANE runs this goal — daemon or console

This is the ONE question in this step, and you ASK it rather than defaulting it (owner ruling
`d-daemon-lane-button`, 2026-08-10). Put it plainly:

> **Who should run this goal — the daemon, or you at this terminal?**
> **(a) daemon** — the ignite daemon picks it up by itself within a tick and runs its seats
> unattended. You can walk away; you get no terminal output.
> **(b) console** — nothing runs until you type the `rbtv run` command I hand you in Step 3, and it
> runs in front of you, dying with the terminal.
> Recommendation: **(b) console**, because you are here — that is why this entry exists.

Then write the answer:

```
rbtv goal lane <goal-name> --set console                          # (b)
rbtv goal lane <goal-name> --set daemon --profile <profile-name>  # (a)
```

- **`--profile` is REQUIRED for the daemon** and is a launch profile BY NAME (the same names
  `rbtv run --profile` takes — they are the `profiles:` keys in
  `3-resources/tools/rbtv/ignite/config/spawn-profiles.yaml`, and the CLI's own refusal prints the
  valid set; `rbtv-bindings catalog` supersedes this once that capability lands). The command refuses
  rather than guessing — do not invent one, ask.
- **Absent means `console`,** so answer (b) technically needs no file at all. Write it anyway: an
  explicit `console` is what tells the next reader the question was asked and answered.
- **The switch is live.** Flipping this file mid-goal is supported and is the point — a goal can
  start in one lane and finish in the other, and the goal's execution record makes the receiving
  lane skip every seat the other one already finished. If the user picks daemon now and wants the
  terminal later, one `rbtv goal lane <goal> --set console` is the whole act.
- If the answer is **daemon**, Step 3's hand-over command still applies as the manual override, but
  say plainly that nothing needs to be typed for the goal to start.

### 2c. Make sure the workflow has a casting sheet — ONLY IF IT HAS NONE

Materialization needs one **bindings** file: the casting sheet naming, per seat, which harness,
model and effort it runs on. It is not per goal — **one file per workflow**, reused by every later
goal — and it is authored only through the `bindings` tool. Never hand-write the JSON.

```
<rbtv-repo>/ignite/capabilities/bindings/tool/rbtv-bindings inspect \
  <workspace>/3-resources/tools/rbtv/meta/planning/workflows/planning/planning.csv
```

That one command shows you the workflow's seats, each seat's definition file, its staffing hints,
and whether a sheet already exists at

```
<workspace>/.rbtv/config/modules/meta/planning/bindings/plan.json
```

- It printed a path and no `(ABSENT)` marker, with `uncast: none` → **the sheet is done. Skip to 2d.**
  Do not re-cast it: `scaffold` is create-only and refuses, and re-casting a workflow other goals
  already run is not a setup step.
- It printed `(ABSENT)`, or named uncast seats → author them:

```
rbtv-bindings catalog                       # every harness+model this box can spawn, effort NUMBERED
rbtv-bindings scaffold <planning.csv>       # create the sheet, every seat uncast
rbtv-bindings set <planning.csv> <seat> <harness> <model> <effort-number>   # once per uncast seat
```

`catalog` is also the validator — a pair or effort number it does not list is refused here rather
than at goal creation, where nobody is watching. The effort operand is a NUMBER (claude: 1=low …
5=max); the file stores the harness's own level string.

### 2d. Materialize the workflow into the goal folder

```
python3 <rbtv-repo>/ignite/team-kit/materialize-seats.py \
  --package <workspace>/.rbtv/goals/<goal> \
  --workflow planning \
  --catalog-root <workspace>/3-resources/tools/rbtv/meta \
  --root \
  --bindings <bindings.json> \
  --conduct <conduct.md> --claude-md <CLAUDE.md> --budget-json <budget.json>
```

- `--catalog-root` is the MODULE folder (`meta`), not the component folder — the workflow is
  resolved as `<catalog-root>/<component>/workflows/planning/planning.csv` and catalogs merge
  across the root.
- `--bindings` is the casting sheet from step 2c — `<workspace>/.rbtv/config/modules/meta/planning/bindings/plan.json`.
  It names **every** seat in `planning.csv` and no others; a missing or extra key is a refusal,
  never a default. That is exactly what `rbtv-bindings` keeps true, which is why the file is never
  hand-edited.
- `--conduct` / `--claude-md` / `--budget-json` are caller-supplied base texts, byte-copied into
  the created package. `budget.json` must declare a positive integer `floors.launch_refuse_mb`.
- Run it with `--dry-run` first. It prints the complete write plan and touches nothing; a refusal
  leaves zero files either way.

Materialization emits one `seats/<seat>/seat.md` per row plus the `taskforce.csv` rows. A seat whose
definition declares `human-interactive:` carries that flag into its `seat.md` — that is the flag
step 1's status verb reads.

### 2e. Nothing to arm — this workflow does not fork

`planning.csv` is five linear rows: every `after` is a bare seat-id, with no guard and no
alternate. The same is true of `d13-replan.csv` and `forge.csv`. So there is **no edge to
discharge** and nothing to arm here — no `coordination/edge-fastpath.json`, no edge-runner, no
`args_allowlist:` entry, on either lane.

The old planning DAG did fork (a `planning-mode` guard and a `use-case` alternate), and this step
used to hand over the arming file that discharged them. Both forks are retired along with the
17-row per-milestone splice; if you find an arm file or an edge-runner allowlist entry left behind
for this workflow, it is dead configuration, not a prerequisite.

---

## Step 3 — HAND OVER THE COMMAND

Give the user **exactly one line to type**, and stop:

```
rbtv run <workspace>/.rbtv/goals/<goal> --profile <profile-name>
```

Pick the profile by NAME from the shared launch-profile config
(`<rbtv-repo>/ignite/config/spawn-profiles.yaml`) and say which one you picked and why. There is no
(harness, model) → profile derivation; a profile is chosen by name or not at all.

**⚠ You cannot run this command for them, and you must not try.** It boots the engine attached to a
real terminal. From inside a session it has no tty, and once the goal has human-interactive seats it
needs one. Hand it over; the `!` prefix works if they want to fire it from inside their session.

Tell them, in the same message:

- **Ctrl-C at any point is safe.** The attached run dies with the terminal. Re-running the same
  command RESUMES — seeding is create-only and a seat that already ran is never re-fired. Nothing
  is replayed.
- **Exit codes:** `0` complete · `1` refused, or nothing can advance · `3` a seat asked a question
  and handed the run back to them.
- **There is no watcher for this lane, by ruling.** A run that dies unattended stays dead until
  they notice. Re-running the command is the recovery — do not wait for anything to restart it.
- **To orient again later**, from any fresh session, on any machine: the step-1 status command.

---

## What you MUST disclose, every time

- **A seat the user works themselves has no cage.** Seats the engine dispatches run as caged,
  detached children (bwrap + systemd). A seat occupied by the user's own session has neither
  sandbox nor unit — it runs with that session's authority. Accepted for v1; say it out loud rather
  than letting them discover it.
- **POSIX only.** Attached execution refuses a non-POSIX host with a typed
  `E_SUBSTRATE_UNSUPPORTED` naming the four unbuilt sites. It is a refusal, not a fallback, because
  falling through would report a successful kill having killed nothing.
- **The foreground carrier is NOT built yet** (console-run design wave B, item B1). Today the
  engine dispatches every ready seat as a detached child, *including* one flagged
  `human-interactive` — the flag is visible in `--status` and it gates owner-addressed messages
  through the chat bridge, but it does not yet stop the engine and hand the terminal over. So: if
  `--status` names a seat as **held for you**, tell the user that seat needs them live and that the
  automatic hand-over does not exist yet, rather than implying the run will pause for them.

---

## The workflow you are setting up

`workflow.md` in this folder is the planning workflow's own orientation — its five seats, its four
lean stages, and its regression loop. Read it when the user asks what planning will actually do,
not to perform these three steps.
